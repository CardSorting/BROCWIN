"""Carry the guest's vln/1 TCP/UDP bytes to fixed local original services.

No game packets are interpreted, fabricated, or logged. The browser executes
the client; these sockets connect only to the recovered local server stack.
"""
from __future__ import annotations

import asyncio
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import datetime, timezone
from http import HTTPStatus
from pathlib import Path
import struct
import json
import socket
import sys
import threading

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools/python'))
from websockets.asyncio.server import serve
from websockets.exceptions import ConnectionClosed

MAGIC = 0x314E4C56
HEADER = struct.Struct('<7I')
WINDOW = 16384
MAX_PAYLOAD = 4096
MAX_DATAGRAM = 65507
UDP_MAPPING = 9  # Host-only transport metadata; never delivered to guest Winsock.
CLIENT_IP = 0x0A000001
LOOPBACK = 0x7F000001
PORTS = (9100, 9200, 9201, 9300, 9301, 9400, 9401, 9500)
UDP_SERVICES = {9101: 'CenterServer', 9201: 'LoginServer', 9301: 'GameServer',
                9401: 'ChannelServer', 9501: 'GlobalServer'}


def local_udp_targets():
    """Resolve only UDP listeners owned by the existing local runtime receipt.

    The recovered services bind UDP to their selected local interface even
    though the isolated database advertises loopback. Verify process identity
    and local address ownership; never accept destinations from a browser.
    """
    if sys.platform != 'win32':
        return {}
    import ctypes as C
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from runtime import alive, receipt
    owners = alive(receipt())
    class Row(C.Structure):
        _fields_ = [('address', C.c_uint32), ('port', C.c_uint32), ('pid', C.c_uint32)]
    get = C.WinDLL('iphlpapi').GetExtendedUdpTable
    get.argtypes = [C.c_void_p, C.POINTER(C.c_uint32), C.c_int, C.c_uint32, C.c_int, C.c_uint32]
    size = C.c_uint32()
    get(None, C.byref(size), 0, socket.AF_INET, 1, 0)  # UDP_TABLE_OWNER_PID
    for _ in range(4):
        table = C.create_string_buffer(size.value)
        error = get(table, C.byref(size), 0, socket.AF_INET, 1, 0)
        if error != 122:
            break
    if error:
        raise OSError(error, 'Cannot inspect owned local UDP listeners')
    targets = {}
    for i in range(C.c_uint32.from_buffer(table).value):
        row = Row.from_buffer(table, 4 + i * C.sizeof(Row))
        port = socket.ntohs(row.port & 0xffff)
        owner = owners.get(UDP_SERVICES.get(port))
        if not owner or owner['pid'] != row.pid:
            continue
        address = socket.inet_ntoa(struct.pack('<I', row.address))
        if address == '0.0.0.0':
            address = '127.0.0.1'
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as proof:
            proof.bind((address, 0))
        targets[port] = (address, port)
    return targets


def frame(kind, source, source_port, destination, destination_port, payload=b''):
    return HEADER.pack(MAGIC, kind, source, source_port, destination, destination_port, len(payload)) + payload


def decode(data):
    if not isinstance(data, bytes) or not HEADER.size <= len(data) <= HEADER.size + MAX_DATAGRAM:
        raise ValueError('Invalid vln/1 frame extent')
    magic, kind, sip, sport, dip, dport, size = HEADER.unpack_from(data)
    if magic != MAGIC or size != len(data) - HEADER.size or kind not in (1, 3, 4, 5, 6, 8):
        raise ValueError('Invalid vln/1 frame header')
    if size > (MAX_DATAGRAM if kind == 6 else MAX_PAYLOAD):
        raise ValueError('Invalid transport payload extent')
    if not (1 <= sport <= 65535 and 1 <= dport <= 65535) or sip not in (CLIENT_IP, LOOPBACK):
        raise ValueError('Invalid guest endpoint')
    if (kind in (1, 4, 5) and size) or (kind == 8 and size != 4):
        raise ValueError('Invalid control frame payload')
    return kind, (sip, sport, dip, dport), data[HEADER.size:]


@dataclass
class Stream:
    endpoints: tuple
    writes: asyncio.Queue = field(default_factory=lambda: asyncio.Queue(258))
    condition: asyncio.Condition = field(default_factory=asyncio.Condition)
    writer: object = None
    tasks: list = field(default_factory=list)
    tx_inflight: int = 0
    rx_inflight: int = 0
    remote_eof: bool = False
    guest_eof: bool = False
    write_finished: bool = False
    closed: bool = False


class DatagramPeer:
    def __init__(self, session, source, sock):
        self.session, self.source = session, source
        self.socket = sock
        self.routes = {}
        self.replies = asyncio.Queue(32)

    def datagram_received(self, data, address):
        endpoints = self.routes.get(address)
        if (endpoints is None or len(data) > MAX_DATAGRAM or self.replies.full()
                or self.session.udp_queued_bytes + len(data) + HEADER.size > 4 * 1024 * 1024):
            return
        self.session.udp_queued_bytes += len(data) + HEADER.size
        self.replies.put_nowait((endpoints, data))

    async def receive(self):
        # Python 3.11 DatagramTransport discards zero-byte packets on Windows.
        # Raw async socket I/O preserves them in both directions.
        loop = asyncio.get_running_loop()
        while not self.session.closed:
            try:
                data, address = await loop.sock_recvfrom(self.socket, MAX_DATAGRAM)
            except OSError:
                # No invented application reply on UDP loss/unreachable peer.
                await asyncio.sleep(.01)
                continue
            self.datagram_received(data, address)

    async def deliver(self):
        while True:
            endpoints, data = await self.replies.get()
            try:
                await self.session.send(6, endpoints, data)
            except ConnectionClosed:
                return
            finally:
                self.session.udp_queued_bytes -= len(data) + HEADER.size


class Session:
    def __init__(self, ws, targets, udp_targets=None):
        self.ws = ws
        # Keys are guest ports; values are native loopback ports. Production
        # constructs this from PORTS. Tests use temporary local listeners.
        self.targets = targets
        self.udp_targets = udp_targets or {}
        self.datagrams = {}
        self.datagram_tasks = []
        self.udp_queued_bytes = 0
        self.streams = {}
        self.tasks = set()
        self.closed = False

    def task(self, coroutine, stream=None):
        task = asyncio.create_task(coroutine)
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)
        if stream is not None:
            stream.tasks.append(task)
        return task

    async def close_writer(self, writer):
        with suppress(OSError, TimeoutError):
            await asyncio.wait_for(writer.wait_closed(), 2)

    async def send(self, kind, endpoints, payload=b''):
        sip, sport, dip, dport = endpoints
        await self.ws.send(frame(kind, dip, dport, sip, sport, payload))

    def retire(self, stream):
        if stream.closed:
            return
        stream.closed = True
        if self.streams.get(stream.endpoints) is stream:
            del self.streams[stream.endpoints]
        if stream.writer:
            stream.writer.close()
            self.task(self.close_writer(stream.writer))
        for task in stream.tasks:
            if task is not asyncio.current_task():
                task.cancel()

    async def connect(self, stream):
        try:
            reader, writer = await asyncio.wait_for(asyncio.open_connection(
                '127.0.0.1', self.targets[stream.endpoints[3]]), 5)
            if stream.closed:
                writer.close()
                await writer.wait_closed()
                return
            stream.writer = writer
            await self.send(2, stream.endpoints)
            self.task(self.write_stream(stream), stream)
            while not stream.closed:
                async with stream.condition:
                    await stream.condition.wait_for(lambda: stream.closed or WINDOW - stream.tx_inflight >= 64)
                if stream.closed:
                    return
                data = await reader.read(min(MAX_PAYLOAD, WINDOW - stream.tx_inflight))
                if not data:
                    stream.remote_eof = True
                    await self.send(4, stream.endpoints)
                    if stream.write_finished:
                        self.retire(stream)
                    return
                stream.tx_inflight += max(len(data), 64)
                await self.send(3, stream.endpoints, data)
        except (OSError, TimeoutError, ConnectionClosed):
            if not self.closed and not stream.closed:
                with suppress(ConnectionClosed):
                    await self.send(5, stream.endpoints)
            self.retire(stream)
        except asyncio.CancelledError:
            self.retire(stream)
            raise

    async def write_stream(self, stream):
        try:
            while not stream.closed:
                payload = await stream.writes.get()
                if payload is None:
                    stream.writer.write_eof()
                    await stream.writer.drain()
                    stream.write_finished = True
                    if stream.remote_eof:
                        self.retire(stream)
                    return
                stream.writer.write(payload)
                await stream.writer.drain()
                charge = max(len(payload), 64)
                stream.rx_inflight -= charge
                await self.send(8, stream.endpoints, struct.pack('<I', charge))
        except (OSError, ConnectionClosed):
            if not self.closed and not stream.closed:
                with suppress(ConnectionClosed):
                    await self.send(5, stream.endpoints)
            self.retire(stream)
        except asyncio.CancelledError:
            raise

    async def accept(self, data):
        kind, endpoints, payload = decode(data)
        if kind == 6:
            if endpoints[2] == CLIENT_IP:
                # X2 probes its own server-observed UDP source port. The
                # native socket's ephemeral port belongs to this session's
                # existing mapping, not to a second guest-bound socket.
                # Reflect only that mapping's own source. No native packet,
                # foreign session, arbitrary listener or game reply is made.
                peer = next((p for p in self.datagrams.values()
                             if p.source[:2] == endpoints[:2]
                             and p.socket.getsockname()[1] == endpoints[3]), None)
                if peer is not None:
                    await self.send(6, endpoints, payload)
                return
            target = self.udp_targets.get(endpoints[3]) if endpoints[2] == LOOPBACK else None
            if target is None:
                return
            key = (*endpoints[:2], target[0])
            peer = self.datagrams.get(key)
            if peer is None:
                if len(self.datagrams) >= 128:
                    return
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                try:
                    sock.bind((target[0], 0))
                    sock.setblocking(False)
                except OSError:
                    sock.close()
                    return
                peer = DatagramPeer(self, key, sock)
                self.datagrams[key] = peer
                self.datagram_tasks.append(self.task(peer.deliver()))
                self.datagram_tasks.append(self.task(peer.receive()))
                if endpoints[0] == CLIENT_IP:
                    # Publish the actual owned mapping before sending to the
                    # service that may report its observed port to the game.
                    await self.ws.send(frame(UDP_MAPPING, endpoints[0], endpoints[1],
                                             endpoints[0], sock.getsockname()[1]))
            peer.routes[target] = endpoints
            with suppress(OSError):
                await asyncio.get_running_loop().sock_sendto(peer.socket, payload, target)
            return
        if endpoints[2] != LOOPBACK or endpoints[3] not in self.targets:
            if kind != 5:
                await self.send(5, endpoints)
            return
        stream = self.streams.get(endpoints)
        if kind == 1:
            if stream or len(self.streams) >= 128:
                await self.send(5, endpoints)
                if stream:
                    self.retire(stream)
                return
            stream = Stream(endpoints)
            self.streams[endpoints] = stream
            self.task(self.connect(stream), stream)
            return
        if not stream:
            if kind not in (5, 8):
                await self.send(5, endpoints)
            return
        if kind == 5:
            self.retire(stream)
        elif kind == 8:
            credit, = struct.unpack('<I', payload)
            if credit > stream.tx_inflight:
                raise ValueError('Credit exceeds outstanding bytes')
            stream.tx_inflight -= credit
            async with stream.condition:
                stream.condition.notify_all()
        elif kind == 4:
            if not stream.guest_eof:
                stream.guest_eof = True
                stream.writes.put_nowait(None)
        elif kind == 3:
            charge = max(len(payload), 64)
            if not stream.writer or stream.guest_eof or stream.rx_inflight + charge > WINDOW:
                raise ValueError('Stream data outside its receive window')
            stream.rx_inflight += charge
            stream.writes.put_nowait(payload)

    async def run(self):
        rejection = None
        try:
            async for data in self.ws:
                await self.accept(data)
        except (ValueError, asyncio.QueueFull) as error:
            # Transport metadata only. Never retain or decode game payloads.
            rejection = {'type': type(error).__name__, 'message': str(error)}
            if isinstance(data, bytes) and len(data) >= HEADER.size:
                magic, kind, sip, sport, dip, dport, size = HEADER.unpack_from(data)
                rejection['frame'] = {'magic': magic, 'kind': kind,
                    'endpoints': [sip, sport, dip, dport], 'payloadBytes': size,
                    'frameBytes': len(data)}
                if kind == 8 and len(data) == HEADER.size + 4:
                    rejection['frame']['creditBytes'] = struct.unpack_from('<I', data, HEADER.size)[0]
            await self.ws.close(1008, 'Invalid guest stream')
        except ConnectionClosed:
            pass
        finally:
            print(json.dumps({'event': 'theseus-transport-close',
                'at': datetime.now(timezone.utc).isoformat(), 'connection': str(self.ws.id),
                'code': self.ws.close_code, 'reason': self.ws.close_reason,
                'rejection': rejection,
                'streams': [{'endpoints': s.endpoints, 'txInflight': s.tx_inflight,
                    'rxInflight': s.rx_inflight, 'remoteEof': s.remote_eof,
                    'guestEof': s.guest_eof} for s in self.streams.values()]}),
                file=sys.stderr, flush=True)
            self.closed = True
            for task in self.datagram_tasks:
                task.cancel()
            await asyncio.gather(*self.datagram_tasks, return_exceptions=True)
            for peer in self.datagrams.values():
                peer.socket.close()
            streams = list(self.streams.values())
            for stream in streams:
                self.retire(stream)
            # Retired connections can still own cancellation/close tasks.
            # Include them, and any cleanup they schedule while unwinding.
            while self.tasks:
                await asyncio.gather(*list(self.tasks), return_exceptions=True)


class NetworkService:
    def __init__(self, http_port, port=0, targets=None, udp_targets=None):
        self.http_port, self.port = http_port, port
        self.targets = dict(targets if targets is not None else ((p, p) for p in PORTS))
        self.udp_targets = dict(udp_targets if udp_targets is not None else
                                (local_udp_targets() if targets is None else {}))
        self.ready = threading.Event()
        self.error = None
        self.thread = threading.Thread(target=self.run_thread, name='theseus-local-network', daemon=True)

    def start(self):
        self.thread.start()
        if not self.ready.wait(10):
            raise RuntimeError('Local network transport did not start')
        if self.error:
            raise self.error
        return self

    def run_thread(self):
        try:
            asyncio.run(self.run())
        except Exception as error:
            self.error = error
            self.ready.set()

    async def run(self):
        self.loop = asyncio.get_running_loop()
        self.stop_event = asyncio.Event()
        def request(connection, request):
            host = request.headers.get('Host', '').split(':')[0]
            if request.path != '/vln' or host not in ('127.0.0.1', 'localhost'):
                return connection.respond(HTTPStatus.FORBIDDEN, 'Forbidden\n')
        async def handler(ws):
            await Session(ws, self.targets, self.udp_targets).run()
        async with serve(handler, '127.0.0.1', self.port, origins=[
                f'http://127.0.0.1:{self.http_port}', f'http://localhost:{self.http_port}'],
                subprotocols=['theseus-vln1'], process_request=request,
                max_size=HEADER.size + MAX_DATAGRAM, max_queue=32, compression=None,
                close_timeout=2) as server:
            self.port = server.sockets[0].getsockname()[1]
            self.ready.set()
            await self.stop_event.wait()

    def close(self):
        if hasattr(self, 'loop') and not self.loop.is_closed():
            self.loop.call_soon_threadsafe(self.stop_event.set)
        self.thread.join(10)
        if self.thread.is_alive():
            raise RuntimeError('Local network transport did not stop')

    def configuration(self):
        return {'webSocketUrl': f'ws://127.0.0.1:{self.port}/vln', 'clientIp': '10.0.0.1',
                'loopbackPorts': list(self.targets), 'serverExecution': 'original-local-native-services',
                'udpImplemented': True, 'udpPorts': list(self.udp_targets),
                'udpTargets': {str(p): {'address': target[0], 'port': target[1]}
                               for p, target in self.udp_targets.items()}}
