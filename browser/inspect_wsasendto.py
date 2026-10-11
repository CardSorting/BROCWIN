"""Measure WSASendTo against Windows using only temporary loopback sockets."""
import ctypes as C
import hashlib
import json
from pathlib import Path
import socket


def main():
    w, k = C.WinDLL('ws2_32'), C.WinDLL('kernel32')
    U, P, S = C.c_uint32, C.c_void_p, C.c_size_t
    class Buffer(C.Structure):
        _fields_ = [('length', U), ('pointer', P)]
    class Overlapped(C.Structure):
        _fields_ = [('internal', S), ('bytes', S), ('offset', U), ('high', U), ('event', P)]
    w.WSASendTo.argtypes = [S, C.POINTER(Buffer), U, C.POINTER(U), U, P, C.c_int, C.POINTER(Overlapped), P]
    w.WSAGetOverlappedResult.argtypes = [S, C.POINTER(Overlapped), C.POINTER(U), C.c_int, C.POINTER(U)]
    w.WSACreateEvent.restype = P
    w.WSACloseEvent.argtypes = [P]
    k.WaitForSingleObject.argtypes = [P, U]
    rows = []
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as peer:
        peer.bind(('127.0.0.1', 0)); peer.settimeout(2)
        destination = C.create_string_buffer(b'\x02\0' + peer.getsockname()[1].to_bytes(2, 'big') + socket.inet_aton('127.0.0.1') + bytes(8))
        for name, lengths, use_ov, count_override, address_length in [
            ('scatter-sync', [1, 14], False, None, 16),
            ('scatter-overlapped', [1, 14], True, None, 16),
            ('empty-datagram', [0, 0], False, None, 16),
            ('empty-overlapped', [0], True, None, 16),
            ('zero-buffers', [1], False, 0, 16),
            ('short-address', [1], False, None, 8),
            ('maximum-datagram', [32768, 32739], False, None, 16),
            ('oversize-datagram', [32768, 32740], False, None, 16),
        ]:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client:
                storage = [C.create_string_buffer(bytes([65+i]) * n) for i, n in enumerate(lengths)]
                vector = (Buffer * len(lengths))(*(Buffer(n, C.addressof(b)) for n, b in zip(lengths, storage)))
                count = U(0x1234); event = w.WSACreateEvent()
                ov = Overlapped(internal=0x12345678, bytes=0x23456789, event=event)
                try:
                    w.WSASetLastError(0x4567)
                    ret = w.WSASendTo(client.fileno(), vector, len(lengths) if count_override is None else count_override,
                                     C.byref(count), 0, destination, address_length, C.byref(ov) if use_ov else None, None)
                    error = w.WSAGetLastError()
                    row = {'case': name, 'result': ret, 'error': error, 'count': count.value,
                           'internal': ov.internal, 'transferred': ov.bytes, 'event': k.WaitForSingleObject(event, 0)}
                    if ret == 0:
                        data, source = peer.recvfrom(65535)
                        assert data == b''.join(b.raw[:n] for n, b in zip(lengths, storage))
                        row.update(receivedBytes=len(data), autoBound=client.getsockname()[1] == source[1])
                    rows.append(row)
                finally:
                    w.WSACloseEvent(event)
    result = {'schema': 'theseus.native-wsasendto/v1', 'contributor': 'Codex /root',
              'pointerBytes': C.sizeof(P), 'scope': 'Temporary loopback sockets only; no original game code executed',
              'probeSha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'cases': rows}
    destination = Path(__file__).with_name('reference') / 'wsasendto.json'
    destination.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(rows))


if __name__ == '__main__':
    main()
