"""Native Winsock overlapped contracts, using only temporary loopback sockets."""
import ctypes as C
import hashlib
import json
from pathlib import Path


def main():
    w = C.WinDLL('ws2_32'); k = C.WinDLL('kernel32')
    U, P, S = C.c_uint32, C.c_void_p, C.c_size_t
    class Buffer(C.Structure):
        _fields_ = [('length', U), ('buffer', P)]
    class Overlapped(C.Structure):
        _fields_ = [('internal', S), ('bytes', S), ('offset', U), ('offsetHigh', U), ('event', P)]
    w.WSASocketW.argtypes = [C.c_int, C.c_int, C.c_int, P, U, U]; w.WSASocketW.restype = S
    w.closesocket.argtypes = [S]; w.WSAGetLastError.restype = C.c_int; w.WSASetLastError.argtypes = [C.c_int]
    w.WSASend.argtypes = [S, C.POINTER(Buffer), U, C.POINTER(U), U, C.POINTER(Overlapped), P]
    w.WSARecv.argtypes = [S, C.POINTER(Buffer), U, C.POINTER(U), C.POINTER(U), C.POINTER(Overlapped), P]
    w.WSAGetOverlappedResult.argtypes = [S, C.POINTER(Overlapped), C.POINTER(U), C.c_int, C.POINTER(U)]
    w.WSACreateEvent.restype = P; w.WSACloseEvent.argtypes = [P]
    k.WaitForSingleObject.argtypes = [P, U]; k.WaitForSingleObject.restype = U
    k.ResetEvent.argtypes = [P]
    rows = []
    def created(label, af=2, kind=1, proto=6, flags=1):
        w.WSASetLastError(0x1234)
        s = w.WSASocketW(af, kind, proto, None, 0, flags)
        error = w.WSAGetLastError(); ok = s != S(-1).value
        rows.append({'api':'create', 'case':label, 'af':af,'type':kind,'protocol':proto,'flags':flags,'success':ok,'error':error})
        if ok: w.closesocket(s)
    created('before-startup')
    data = C.create_string_buffer(512)
    assert w.WSAStartup(0x202, data) == 0
    for label, af, kind, proto, flags in [('original',2,1,6,1),('synchronous',2,1,6,0),('default-protocol',2,1,0,1),
            ('udp',2,2,17,1),('wrong-protocol',2,1,17,1),('invalid-type',2,99,6,1),('invalid-family',999,1,6,1),
            ('multipoint',2,1,6,3),('unknown-flag',2,1,6,0x40000000)]:
        created(label,af,kind,proto,flags)
    import socket  # Only after the startup contract above.
    with socket.socket() as listener:
        listener.bind(('127.0.0.1',0)); listener.listen(1)
        raw = w.WSASocketW(2,1,6,None,0,1)
        with socket.socket(socket.AF_INET,socket.SOCK_STREAM,socket.IPPROTO_TCP,fileno=raw) as client:
            client.connect(listener.getsockname())
            with listener.accept()[0] as peer:
                peer.settimeout(2)
                event = w.WSACreateEvent(); ov = Overlapped(event=event)
                storage = C.create_string_buffer(32); vec = (Buffer*2)(Buffer(3,C.addressof(storage)), Buffer(5,C.addressof(storage)+3))
                count, flags = U(0x1234), U(0)
                def take(label, result):
                    error=w.WSAGetLastError()
                    rows.append({'api':'io','case':label,'result':result,'error':error,'count':count.value,
                        'flags':flags.value,'internal':ov.internal,'transferred':ov.bytes,'event':k.WaitForSingleObject(event,0)})
                try:
                    w.WSASetLastError(0x1234)
                    take('receive-pending',w.WSARecv(raw,vec,2,C.byref(count),C.byref(flags),C.byref(ov),None))
                    count.value=0x1234;flags.value=0x4321;w.WSASetLastError(0x1234)
                    take('pending-query',w.WSAGetOverlappedResult(raw,C.byref(ov),C.byref(count),0,C.byref(flags)))
                    # The provider captures WSABUF descriptors before returning.
                    vec[0].length=0; vec[1].length=0
                    peer.sendall(b'abcdef')
                    assert k.WaitForSingleObject(event,2000)==0
                    w.WSASetLastError(0x1234)
                    take('receive-complete',w.WSAGetOverlappedResult(raw,C.byref(ov),C.byref(count),0,C.byref(flags)))
                    assert storage.raw[:6]==b'abcdef'
                    ov.internal=ov.bytes=0;count.value=0x1234;flags.value=0
                    vec[0].length=3;vec[1].length=3
                    k.ResetEvent(event);w.WSASetLastError(0x1234)
                    take('send-complete',w.WSASend(raw,vec,2,C.byref(count),0,C.byref(ov),None))
                    assert peer.recv(6)==b'abcdef'
                    count.value=0x1234;flags.value=0x4321;w.WSASetLastError(0x1234)
                    take('send-query',w.WSAGetOverlappedResult(raw,C.byref(ov),C.byref(count),0,C.byref(flags)))
                    ov.internal=ov.bytes=0;count.value=0x1234;flags.value=0
                    k.ResetEvent(event);vec[0].length=0;vec[1].length=0;w.WSASetLastError(0x1234)
                    take('zero-receive-pending',w.WSARecv(raw,vec,2,C.byref(count),C.byref(flags),C.byref(ov),None))
                    peer.sendall(b'Z');assert k.WaitForSingleObject(event,2000)==0
                    w.WSASetLastError(0x1234)
                    take('zero-receive-complete',w.WSAGetOverlappedResult(raw,C.byref(ov),C.byref(count),0,C.byref(flags)))
                    assert client.recv(1)==b'Z'
                    ov.internal=ov.bytes=0;count.value=0x1234;flags.value=0;k.ResetEvent(event);vec[0].length=3
                    w.WSASetLastError(0x1234)
                    take('close-pending',w.WSARecv(raw,vec,1,C.byref(count),C.byref(flags),C.byref(ov),None))
                    client.close();assert k.WaitForSingleObject(event,2000)==0
                    count.value=0x1234;flags.value=0x4321;w.WSASetLastError(0x1234)
                    take('close-query',w.WSAGetOverlappedResult(raw,C.byref(ov),C.byref(count),0,C.byref(flags)))
                finally: w.WSACloseEvent(event)
    # Failed initiation must not manufacture a completion notification. Record
    # OVERLAPPED and caller output bytes as well as the public error code.
    error_rows=[]
    def failed(label, raw, receive, *, initial=0, count_arg=1, event_override=None):
        event=w.WSACreateEvent()
        ov=Overlapped(internal=0x12345678,bytes=0x23456789,event=event if event_override is None else event_override)
        storage=C.create_string_buffer(b'abcd');vec=Buffer(4,C.addressof(storage))
        count,flags=U(0x1234),U(0)
        if initial:k.SetEvent(P(event))
        w.WSASetLastError(0x1234)
        ret=(w.WSARecv(raw,C.byref(vec),count_arg,C.byref(count),C.byref(flags),C.byref(ov),None) if receive
             else w.WSASend(raw,C.byref(vec),count_arg,C.byref(count),0,C.byref(ov),None))
        error=w.WSAGetLastError()
        error_rows.append({'case':label,'receive':receive,'initialEvent':initial,'result':ret,'error':error,
            'count':count.value,'flags':flags.value,'internal':ov.internal,'transferred':ov.bytes,'event':k.WaitForSingleObject(event,0)})
        w.WSACloseEvent(event)
    raw=w.WSASocketW(2,1,6,None,0,1)
    try:
        for receive in (False,True):
            failed('unconnected-'+('receive' if receive else 'send'),raw,receive)
            failed('unconnected-signaled-'+('receive' if receive else 'send'),raw,receive,initial=1)
        failed('invalid-socket',S(-1).value,True)
    finally:w.closesocket(raw)
    with socket.socket() as listener:
        listener.bind(('127.0.0.1',0));listener.listen(1)
        with socket.socket() as client:
            client.connect(listener.getsockname())
            with listener.accept()[0] as peer:
                failed('zero-buffer-count',client.fileno(),True,count_arg=0)
                failed('invalid-event',client.fileno(),True,event_override=0x1234)
                client.shutdown(socket.SHUT_WR)
                failed('send-shutdown',client.fileno(),False)
                client.shutdown(socket.SHUT_RD)
                failed('receive-shutdown',client.fileno(),True)
    # Abortive remote close delivers an error completion, unlike an immediate
    # API failure. Only temporary local endpoints participate in this probe.
    import struct
    with socket.socket() as listener:
        listener.bind(('127.0.0.1',0));listener.listen(1)
        with socket.socket() as client:
            client.connect(listener.getsockname());peer=listener.accept()[0]
            event=w.WSACreateEvent();ov=Overlapped(event=event)
            storage=C.create_string_buffer(8);vec=Buffer(8,C.addressof(storage));count,flags=U(0x1234),U(0)
            assert w.WSARecv(client.fileno(),C.byref(vec),1,C.byref(count),C.byref(flags),C.byref(ov),None)==-1
            assert w.WSAGetLastError()==997
            peer.setsockopt(socket.SOL_SOCKET,socket.SO_LINGER,struct.pack('HH',1,0));peer.close()
            assert k.WaitForSingleObject(event,2000)==0
            flags.value=0x4321;w.WSASetLastError(0x1234)
            ret=w.WSAGetOverlappedResult(client.fileno(),C.byref(ov),C.byref(count),0,C.byref(flags))
            error=w.WSAGetLastError()
            error_rows.append({'case':'reset-query','result':ret,'error':error,'count':count.value,'flags':flags.value,
                'internal':ov.internal,'transferred':ov.bytes,'event':k.WaitForSingleObject(event,0)})
            w.WSACloseEvent(event)
    dll=Path('C:/Windows/System32/ws2_32.dll')
    result={'scope':__doc__,'pointerBits':C.sizeof(P)*8,'sourceSha256':hashlib.sha256(dll.read_bytes()).hexdigest(),'cases':rows,'errors':error_rows}
    (Path(__file__).parent/'reference/winsock-overlapped.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))


if __name__=='__main__':main()
