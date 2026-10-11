"""Exercise the actual local WebSocket/TCP transport, including bounded credit."""
import asyncio
from contextlib import suppress
import logging
import struct
import socket
import unittest

from network import NetworkService, HEADER, MAGIC, CLIENT_IP, LOOPBACK, WINDOW, frame, MAX_DATAGRAM
from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed, InvalidStatus


class TransportTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.peers = set()
        self.received = []
        async def echo(reader, writer):
            self.peers.add(writer)
            body = bytearray()
            try:
                writer.write(b'hello')
                await writer.drain()
                while data := await reader.read(4096):
                    body.extend(data)
                    writer.write(data)
                    await writer.drain()
                writer.write(b'finished')
                await writer.drain()
            except OSError:
                pass
            finally:
                self.received.append(bytes(body))
                writer.close()
                with suppress(OSError):
                    await writer.wait_closed()
                self.peers.discard(writer)
        self.tcp = await asyncio.start_server(echo, '127.0.0.1', 0)
        native_port = self.tcp.sockets[0].getsockname()[1]
        self.udp_received = []
        self.udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp.bind(('127.0.0.1', 0)); self.udp.setblocking(False)
        async def echo_udp():
            loop = asyncio.get_running_loop()
            while True:
                data, address = await loop.sock_recvfrom(self.udp, 65535)
                self.udp_received.append((data, address))
                await loop.sock_sendto(self.udp, data, address)
        self.udp_task = asyncio.create_task(echo_udp())
        self.service = NetworkService(8766, targets={9200: native_port},
                                      udp_targets={9401: self.udp.getsockname()}).start()
        self.url = self.service.configuration()['webSocketUrl']

    async def asyncTearDown(self):
        await asyncio.to_thread(self.service.close)
        self.tcp.close()
        self.udp_task.cancel()
        await asyncio.gather(self.udp_task, return_exceptions=True)
        self.udp.close()
        await self.tcp.wait_closed()
        for writer in list(self.peers):
            writer.close()
        await asyncio.sleep(0)

    def websocket(self, **kwargs):
        return connect(self.url, origin=kwargs.pop('origin', 'http://127.0.0.1:8766'),
                       subprotocols=['theseus-vln1'], proxy=None, **kwargs)

    async def receive(self, ws):
        data = await asyncio.wait_for(ws.recv(), 5)
        magic, kind, sip, sport, dip, dport, size = HEADER.unpack_from(data)
        self.assertEqual((magic, sip, sport, dip, size),
                         (MAGIC, LOOPBACK, 9200, CLIENT_IP, len(data) - HEADER.size))
        return kind, data[HEADER.size:]

    async def transfer(self, ws, port, body):
        endpoints = (CLIENT_IP, port, LOOPBACK, 9200)
        await ws.send(frame(1, *endpoints))
        self.assertEqual(await self.receive(ws), (2, b''))
        offset, outstanding, received, sent_fin = 0, 0, bytearray(), False
        while True:
            while offset < len(body) and WINDOW - outstanding >= 64:
                chunk = body[offset:offset + min(4096, WINDOW - outstanding)]
                await ws.send(frame(3, *endpoints, chunk))
                offset += len(chunk)
                outstanding += max(len(chunk), 64)
            if offset == len(body) and not sent_fin:
                await ws.send(frame(4, *endpoints))
                sent_fin = True
            kind, payload = await self.receive(ws)
            if kind == 3:
                received.extend(payload)
                await ws.send(frame(8, *endpoints, struct.pack('<I', max(len(payload), 64))))
            elif kind == 8:
                credit, = struct.unpack('<I', payload)
                self.assertLessEqual(credit, outstanding)
                outstanding -= credit
            elif kind == 4:
                break
            else:
                self.fail(f'Unexpected stream frame {kind}')
        self.assertEqual(received, b'hello' + body + b'finished')
        self.assertEqual(outstanding, 0)

    async def test_duplex_credit_half_close_and_slot_reuse(self):
        async with self.websocket() as ws:
            body = bytes(range(256)) * 300 + b'partial tail'
            await self.transfer(ws, 40000, body)
            # More than the stream limit proves orderly FINs release slots.
            for i in range(130):
                await self.transfer(ws, 40001 + i, b'one byte'[:i % 8 + 1])
        self.assertEqual(self.received[0], body)
        self.assertEqual(len(self.received), 131)

    async def test_destination_boundaries_reset_and_disconnect(self):
        async with self.websocket() as ws:
            for ip, port in [(0x08080808, 9200), (LOOPBACK, 80), (0x7f000002, 9200)]:
                await ws.send(frame(1, CLIENT_IP, 40000, ip, port))
                reply = HEADER.unpack(await asyncio.wait_for(ws.recv(), 5))
                self.assertEqual(reply, (MAGIC, 5, ip, port, CLIENT_IP, 40000, 0))
            endpoints = (CLIENT_IP, 40001, LOOPBACK, 9200)
            await ws.send(frame(1, *endpoints))
            self.assertEqual(await self.receive(ws), (2, b''))
            await ws.send(frame(5, *endpoints))
        for _ in range(100):
            if not self.peers:
                break
            await asyncio.sleep(.01)
        self.assertFalse(self.peers)

    async def test_invalid_credit_and_header_close_transport(self):
        async with self.websocket() as ws:
            endpoints = (CLIENT_IP, 40000, LOOPBACK, 9200)
            await ws.send(frame(1, *endpoints))
            self.assertEqual(await self.receive(ws), (2, b''))
            await ws.send(frame(8, *endpoints, struct.pack('<I', WINDOW + 1)))
            with self.assertRaises(ConnectionClosed):
                while True:
                    await asyncio.wait_for(ws.recv(), 5)
            self.assertEqual(ws.close_code, 1008)
        async with self.websocket() as ws:
            await ws.send(b'invalid')
            with self.assertRaises(ConnectionClosed):
                await ws.recv()
            self.assertEqual(ws.close_code, 1008)

    async def test_refused_tcp_is_not_successful_connect(self):
        self.tcp.close()
        await self.tcp.wait_closed()
        async with self.websocket() as ws:
            await ws.send(frame(1, CLIENT_IP, 40000, LOOPBACK, 9200))
            self.assertEqual(await self.receive(ws), (5, b''))

    async def test_origin_and_path(self):
        for origin in (None, 'https://example.com', 'http://127.0.0.1:8765'):
            with self.assertRaises(InvalidStatus):
                async with self.websocket(origin=origin):
                    self.fail('Untrusted origin accepted')
        self.url += '/not-vln'
        with self.assertRaises(InvalidStatus):
            async with self.websocket():
                self.fail('Unexpected path accepted')

    async def test_udp_boundaries_zero_maximum_and_isolation(self):
        async with self.websocket() as ws, self.websocket() as other:
            for number, size in enumerate([0, 1, 15, 4096, 4097, MAX_DATAGRAM]):
                body = bytes((i * 17 + number) & 255 for i in range(size))
                endpoints = (CLIENT_IP, 8900, LOOPBACK, 9401)
                await ws.send(frame(6, *endpoints, body))
                reply = await asyncio.wait_for(ws.recv(), 5)
                if number == 0:
                    mapping = HEADER.unpack_from(reply)
                    self.assertEqual(mapping[:5], (MAGIC, 9, CLIENT_IP, 8900, CLIENT_IP))
                    self.assertTrue(1 <= mapping[5] <= 65535)
                    self.assertEqual(mapping[6], 0)
                    reply = await asyncio.wait_for(ws.recv(), 5)
                self.assertEqual(HEADER.unpack_from(reply), (MAGIC, 6, LOOPBACK, 9401, CLIENT_IP, 8900, size))
                self.assertEqual(reply[HEADER.size:], body)
            first_source = self.udp_received[0][1]
            self.assertEqual(mapping[5], first_source[1], 'mapping reports the actual owned native source')
            self.assertTrue(all(source == first_source for _, source in self.udp_received))
            await other.send(frame(6, CLIENT_IP, 8900, LOOPBACK, 9401, b'other-session'))
            other_mapping = HEADER.unpack_from(await asyncio.wait_for(other.recv(), 5))
            self.assertEqual(other_mapping[:5], (MAGIC, 9, CLIENT_IP, 8900, CLIENT_IP))
            self.assertEqual((await asyncio.wait_for(other.recv(), 5))[HEADER.size:], b'other-session')
            self.assertNotEqual(self.udp_received[-1][1], first_source)
            self.assertEqual(other_mapping[5], self.udp_received[-1][1][1])
            before = len(self.udp_received)
            for channel, port in [(ws, mapping[5]), (other, other_mapping[5])]:
                for size in [0, 2, 10, 4097, MAX_DATAGRAM]:
                    body = bytes((i * 29 + size) & 255 for i in range(size))
                    await channel.send(frame(6, CLIENT_IP, 8900, CLIENT_IP, port, body))
                    reply = await asyncio.wait_for(channel.recv(), 5)
                    self.assertEqual(HEADER.unpack_from(reply), (MAGIC, 6, CLIENT_IP, port, CLIENT_IP, 8900, size))
                    self.assertEqual(reply[HEADER.size:], body)
            self.assertEqual(len(self.udp_received), before, 'self-probe never reaches another native socket')
            for source_port, public_port in [(8900, other_mapping[5]), (8901, mapping[5])]:
                await ws.send(frame(6, CLIENT_IP, source_port, CLIENT_IP, public_port, b'refused'))
            with self.assertRaises(TimeoutError):
                await asyncio.wait_for(ws.recv(), .1)
            before = len(self.udp_received)
            for ip, port in [(0x08080808, 9401), (LOOPBACK, 80), (0x7f000002, 9401), (0xffffffff, 9401)]:
                await ws.send(frame(6, CLIENT_IP, 8900, ip, port, b'refused'))
            await asyncio.sleep(.1)
            self.assertEqual(len(self.udp_received), before)
            with self.assertRaises(TimeoutError):
                await asyncio.wait_for(ws.recv(), .1)


if __name__ == '__main__':
    logging.getLogger('websockets.server').setLevel(logging.CRITICAL)
    unittest.main(verbosity=2)
