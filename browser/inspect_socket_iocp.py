"""Native socket completion-port contracts on temporary loopback endpoints."""
import ctypes as C
import hashlib
import json
from pathlib import Path
import socket
import struct


def main():
    w=C.WinDLL('ws2_32');k=C.WinDLL('kernel32');P=C.c_void_p;U=C.c_uint32;S=C.c_size_t
    class Buffer(C.Structure):_fields_=[('length',U),('pointer',P)]
    class Overlapped(C.Structure):_fields_=[('internal',S),('count',S),('offset',U),('offsetHigh',U),('event',P)]
    w.WSARecv.argtypes=[S,C.POINTER(Buffer),U,C.POINTER(U),C.POINTER(U),C.POINTER(Overlapped),P]
    w.WSASend.argtypes=[S,C.POINTER(Buffer),U,C.POINTER(U),U,C.POINTER(Overlapped),P]
    k.CreateIoCompletionPort.argtypes=[P,P,S,U];k.CreateIoCompletionPort.restype=P
    k.GetQueuedCompletionStatus.argtypes=[P,C.POINTER(U),C.POINTER(S),C.POINTER(P),U]
    k.CloseHandle.argtypes=[P];k.WaitForSingleObject.argtypes=[P,U];k.WaitForSingleObject.restype=U
    k.SetLastError.argtypes=[U];k.GetLastError.restype=U
    w.WSACreateEvent.restype=P;w.WSACloseEvent.argtypes=[P];k.ResetEvent.argtypes=[P]
    rows=[]
    port=k.CreateIoCompletionPort(P(-1),None,0,0);assert port
    event=w.WSACreateEvent()
    def dequeue(label, ov, timeout=2000):
        count,key,out=U(0x1234),S(0x2345),P(0x3456);k.SetLastError(0x4567)
        ok=k.GetQueuedCompletionStatus(port,C.byref(count),C.byref(key),C.byref(out),timeout)
        error=k.GetLastError()
        rows.append({'case':label,'result':ok,'error':error,'count':count.value,'key':key.value,
            'overlapped':'original' if out.value==C.addressof(ov) else out.value,
            'internal':ov.internal,'transferred':ov.count,'event':k.WaitForSingleObject(event,0)})
    try:
        ov=Overlapped(event=event);dequeue('empty',ov,0)
        with socket.socket() as listener:
            listener.bind(('127.0.0.1',0));listener.listen(1)
            with socket.socket() as client:
                client.connect(listener.getsockname())
                with listener.accept()[0] as peer:
                    raw=client.fileno();assert k.CreateIoCompletionPort(raw,port,0xabc123,0)==port
                    k.SetLastError(0x4567);rebind=k.CreateIoCompletionPort(raw,port,0xdef456,0);error=k.GetLastError()
                    rows.append({'case':'rebind-same-port','success':bool(rebind),'error':error})
                    other=k.CreateIoCompletionPort(P(-1),None,0,0)
                    try:
                        k.SetLastError(0x4567);rebind=k.CreateIoCompletionPort(raw,other,0xdef456,0);error=k.GetLastError()
                        rows.append({'case':'rebind-other-port','success':bool(rebind),'error':error})
                    finally:k.CloseHandle(other)
                    storage=C.create_string_buffer(b'abcd');vec=Buffer(4,C.addressof(storage));count,flags=U(),U()
                    assert w.WSARecv(raw,C.byref(vec),1,C.byref(count),C.byref(flags),C.byref(ov),None)==-1
                    dequeue('pending',ov,0);peer.sendall(b'1234');dequeue('receive',ov)
                    ov=Overlapped(event=event);k.ResetEvent(event)
                    assert w.WSASend(raw,C.byref(vec),1,C.byref(count),0,C.byref(ov),None)==0
                    assert peer.recv(4)==b'1234';dequeue('send',ov)
                    ov=Overlapped(event=event|1);k.ResetEvent(event)
                    assert w.WSASend(raw,C.byref(vec),1,C.byref(count),0,C.byref(ov),None)==0
                    assert peer.recv(4)==b'1234';assert k.WaitForSingleObject(event,2000)==0
                    dequeue('tagged-event',ov,0)
                    import threading
                    ov=Overlapped(event=event);k.ResetEvent(event)
                    issued=[]
                    def issue_then_exit():
                        issued.append(w.WSARecv(raw,C.byref(vec),1,C.byref(count),C.byref(flags),C.byref(ov),None))
                    thread=threading.Thread(target=issue_then_exit);thread.start();thread.join()
                    assert issued==[-1];dequeue('thread-exit',ov)
                    ov=Overlapped(event=event);k.ResetEvent(event)
                    assert w.WSARecv(raw,C.byref(vec),1,C.byref(count),C.byref(flags),C.byref(ov),None)==-1
                    client.close();dequeue('close-abort',ov)
        with socket.socket() as listener:
            listener.bind(('127.0.0.1',0));listener.listen(1)
            with socket.socket() as client:
                client.connect(listener.getsockname());peer=listener.accept()[0]
                assert k.CreateIoCompletionPort(client.fileno(),port,0xabc123,0)==port
                ov=Overlapped(event=event);k.ResetEvent(event)
                assert w.WSARecv(client.fileno(),C.byref(vec),1,C.byref(count),C.byref(flags),C.byref(ov),None)==-1
                peer.setsockopt(socket.SOL_SOCKET,socket.SO_LINGER,struct.pack('HH',1,0));peer.close();dequeue('remote-reset',ov)
    finally:w.WSACloseEvent(event);k.CloseHandle(port)
    result={'scope':__doc__,'pointerBits':C.sizeof(P)*8,'cases':rows,
        'sources':{name:hashlib.sha256(Path('C:/Windows/System32',name).read_bytes()).hexdigest() for name in ['ws2_32.dll','kernel32.dll']}}
    (Path(__file__).parent/'reference/socket-iocp.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))


if __name__=='__main__':main()
