"""Reference Winsock event lifetime against local Windows; no socket I/O."""
import ctypes as c
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
w = c.WinDLL('ws2_32')
k = c.WinDLL('kernel32')
w.WSACreateEvent.restype = c.c_void_p
w.WSACloseEvent.argtypes = [c.c_void_p]
w.WSAGetLastError.restype = c.c_int
w.WSASetLastError.argtypes = [c.c_int]
for name in ['SetEvent', 'ResetEvent']:
    getattr(k, name).argtypes = [c.c_void_p]
k.WaitForSingleObject.argtypes = [c.c_void_p, c.c_uint32]
k.WaitForSingleObject.restype = c.c_uint32
rows = []
w.WSASetLastError(0x1234)
event = w.WSACreateEvent()
rows.append({'operation': 'create-before-startup', 'hasHandle': bool(event), 'error': w.WSAGetLastError()})
assert event
try:
    for operation in ['wait-initial', 'set', 'wait-first', 'wait-still-signaled', 'reset', 'wait-reset']:
        w.WSASetLastError(0x1234)
        if operation == 'set': result = k.SetEvent(event)
        elif operation == 'reset': result = k.ResetEvent(event)
        else: result = k.WaitForSingleObject(event, 0)
        rows.append({'operation': operation, 'result': result, 'error': w.WSAGetLastError()})
finally:
    w.WSASetLastError(0x1234)
    rows.append({'operation': 'close', 'result': w.WSACloseEvent(event), 'error': w.WSAGetLastError()})
for operation, handle in [('close-again', event), ('close-null', None), ('close-invalid', 0x1234)]:
    w.WSASetLastError(0x1234)
    rows.append({'operation': operation, 'result': w.WSACloseEvent(handle), 'error': w.WSAGetLastError()})
source = Path('C:/Windows/System32/ws2_32.dll')
report = {'source': str(source), 'sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
          'scope': 'The first phase tests unnamed event creation, kernel wait/signal/reset, and close before WSAStartup.',
          'cases': rows}

import socket  # Python initializes Winsock; only after the first phase above.

class NetworkEvents(c.Structure):
    _fields_ = [('mask', c.c_int32), ('errors', c.c_int32 * 10)]

w.WSAEventSelect.argtypes = [c.c_size_t, c.c_void_p, c.c_int32]
w.WSAEnumNetworkEvents.argtypes = [c.c_size_t, c.c_void_p, c.POINTER(NetworkEvents)]
network = []
with socket.socket() as probe:
    event = w.WSACreateEvent()
    try:
        for name, target, mask in [('null-event', None, 1), ('invalid-event', 0x1234, 1),
                ('valid-event', event, 1), ('invalid-mask', event, 0x400),
                ('cancel-invalid-event', 0x1234, 0), ('cancel-null', None, 0)]:
            w.WSASetLastError(0x1234)
            result = w.WSAEventSelect(probe.fileno(), target, mask)
            network.append({'case': name, 'result': result, 'error': w.WSAGetLastError()})
        for name, target, output in [('enum-null-event', None, NetworkEvents()),
                ('enum-invalid-event', 0x1234, NetworkEvents()), ('enum-null-output', event, None)]:
            w.WSASetLastError(0x1234)
            result = w.WSAEnumNetworkEvents(probe.fileno(), target, c.byref(output) if output is not None else None)
            network.append({'case': name, 'result': result, 'error': w.WSAGetLastError(),
                            'mask': output.mask if output is not None and result == 0 else None})
    finally:
        w.WSACloseEvent(event)

transitions = []
def observe(label, sock, event, wait=0):
    status = k.WaitForSingleObject(event, wait)
    record = NetworkEvents()
    result = w.WSAEnumNetworkEvents(sock.fileno(), event, c.byref(record))
    transitions.append({'case': label, 'wait': status, 'result': result, 'mask': record.mask,
                        'errors': {str(bit): record.errors[bit] for bit in range(10) if record.mask & (1 << bit)}})

events = [w.WSACreateEvent() for _ in range(3)]
try:
    with socket.socket() as listener, socket.socket() as client:
        listener.bind(('127.0.0.1', 0))
        listener.listen(2)
        assert w.WSAEventSelect(listener.fileno(), events[0], 8) == 0
        assert w.WSAEventSelect(client.fileno(), events[1], 0x33) == 0
        client.setblocking(False)
        result = client.connect_ex(listener.getsockname())
        assert result in (0, 10035), result
        observe('listener-ready', listener, events[0], 2000)
        with listener.accept()[0] as peer:
            # Bound the failure path without changing the inherited blocking
            # flag: this is the kernel receive timeout, not setblocking().
            peer.setsockopt(socket.SOL_SOCKET, socket.SO_RCVTIMEO, 200)
            try:
                peer.recv(1)
                raise AssertionError('No bytes have been sent')
            except OSError as error:
                report['acceptedSocketReceiveError'] = error.winerror
            observe('connected', client, events[1], 2000)
            assert w.WSAEventSelect(peer.fileno(), events[2], 0x23) == 0
            observe('accepted-write-ready', peer, events[2], 2000)
            client.sendall(b'abcdefg')
            observe('read-ready', peer, events[2], 2000)
            observe('enum-does-not-rearm-read', peer, events[2])
            assert peer.recv(3) == b'abc'
            observe('partial-read-rearms', peer, events[2], 2000)
            assert peer.recv(4) == b'defg'
            observe('drained', peer, events[2])
            client.shutdown(socket.SHUT_WR)
            observe('orderly-close', peer, events[2], 2000)
finally:
    for event in events:
        w.WSACloseEvent(event)
report['socketEventContracts'] = network
report['loopbackTransitions'] = transitions
report['scope'] += ' Socket event contracts and one ephemeral loopback TCP pair are also observed; no external network or original client/server is used.'
(HERE / 'reference/winsock-events.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps(report, indent=2))
