"""Run the shipped JS wire and real Wasm Winsock against a local TCP peer."""
import asyncio
from contextlib import suppress
from pathlib import Path
import socket
from network import NetworkService


async def main():
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp.bind(('127.0.0.1', 0)); udp.setblocking(False)
    async def echo_udp():
        loop = asyncio.get_running_loop()
        while True:
            data, address = await loop.sock_recvfrom(udp, 65535)
            await loop.sock_sendto(udp, data, address)
    udp_task = asyncio.create_task(echo_udp())
    async def echo(reader, writer):
        try:
            while data := await reader.read(4096):
                writer.write(data)
                await writer.drain()
            writer.write(b'after-eof')
            await writer.drain()
        except OSError:
            pass
        finally:
            writer.close()
            with suppress(OSError):
                await writer.wait_closed()
    async with await asyncio.start_server(echo, '127.0.0.1', 0) as tcp:
        service = NetworkService(8766, targets={9200: tcp.sockets[0].getsockname()[1]},
                                 udp_targets={9401: udp.getsockname()}).start()
        try:
            process = await asyncio.create_subprocess_exec('node', str(Path(__file__).with_suffix('.cjs')),
                                                          service.configuration()['webSocketUrl'])
            code = await asyncio.wait_for(process.wait(), 180)
            if code:
                raise SystemExit(code)
        finally:
            await asyncio.to_thread(service.close)
            udp_task.cancel()
            await asyncio.gather(udp_task, return_exceptions=True)
            udp.close()


if __name__ == '__main__':
    asyncio.run(main())
