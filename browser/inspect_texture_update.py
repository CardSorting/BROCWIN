"""Local D3D9 UpdateTexture reference using a hidden test window, never the game."""
import ctypes as C
import hashlib
import json
from pathlib import Path

P, U, H = C.c_void_p, C.c_uint32, C.c_long
class PP(C.Structure):
    _fields_ = [(n,U) for n in ['width','height','format','count','ms','quality','swap']] + [
        ('window',P),('windowed',U),('depth',U),('depthFormat',U),('flags',U),('refresh',U),('interval',U)]
class Locked(C.Structure):
    _fields_ = [('pitch',C.c_int32),('bits',P)]

def method(obj, slot, restype, *args):
    address = C.cast(obj,C.POINTER(C.POINTER(P))).contents[slot]
    return C.WINFUNCTYPE(restype,P,*args)(address)
def release(obj):
    return method(obj,2,U)(obj)
def check(hr):
    if hr & 0x80000000:
        raise RuntimeError(f'Native reference failed: {hr & 0xffffffff:08x}')

def main():
    user=C.WinDLL('user32')
    user.CreateWindowExW.argtypes=[U,C.c_wchar_p,C.c_wchar_p,U,C.c_int,C.c_int,C.c_int,C.c_int,P,P,P,P]
    user.CreateWindowExW.restype=P
    user.DestroyWindow.argtypes=[P]
    window=user.CreateWindowExW(0,'STATIC','Theseus texture reference',0,0,0,16,16,None,None,None,None)
    if not window: raise RuntimeError('Hidden reference window unavailable')
    dll=C.WinDLL('d3d9');dll.Direct3DCreate9.argtypes=[U];dll.Direct3DCreate9.restype=P
    root=dll.Direct3DCreate9(32);device=P();objects=[];rows=[]
    try:
        pp=PP(width=16,height=16,format=22,count=1,swap=1,window=window,windowed=1,interval=0x80000000)
        check(method(root,16,H,U,U,P,U,C.POINTER(PP),C.POINTER(P))(root,0,1,window,0x20,C.byref(pp),C.byref(device)))
        def texture(size,levels,pool,usage=0):
            t=P();check(method(device,23,H,U,U,U,U,U,U,C.POINTER(P),P)(device,size,size,levels,usage,21,pool,C.byref(t),None));objects.append(t);return t
        def update(s,d):return method(device,31,H,P,P)(device,s,d)&0xffffffff
        def write(t,level,value,flags=0):
            locked=Locked();check(method(t,19,H,U,C.POINTER(Locked),P,U)(t,level,C.byref(locked),None,flags))
            C.c_uint32.from_address(locked.bits).value=value
            check(method(t,20,H,U)(t,level))
        def surface(t,level):
            s=P();check(method(t,18,H,U,C.POINTER(P))(t,level,C.byref(s)));objects.append(s);return s
        def read(t,level,size):
            src=surface(t,level);dst=P()
            check(method(device,36,H,U,U,U,U,C.POINTER(P),P)(device,size,size,21,2,C.byref(dst),None));objects.append(dst)
            check(method(device,32,H,P,P)(device,src,dst))
            locked=Locked();check(method(dst,13,H,C.POINTER(Locked),P,U)(dst,C.byref(locked),None,16))
            value=C.c_uint32.from_address(locked.bits).value;check(method(dst,14,H)(dst));return value
        src=texture(4,3,2);dst=texture(4,3,0,1)
        write(src,0,0xff123456);write(src,1,0xff567890)
        rows.append({'case':'initial','result':update(src,dst),'top':read(dst,0,4),'mip1':read(dst,1,2)})
        write(src,0,0xffabcdef,0x8000)
        rows.append({'case':'no-dirty-update','result':update(src,dst),'top':read(dst,0,4)})
        write(src,1,0xff010203)
        rows.append({'case':'sublevel-only','result':update(src,dst),'mip1':read(dst,1,2)})
        check(method(src,21,H,P)(src,None))
        rows.append({'case':'explicit-dirty','result':update(src,dst),'top':read(dst,0,4),'mip1':read(dst,1,2)})
        locked=Locked();check(method(src,19,H,U,C.POINTER(Locked),P,U)(src,0,C.byref(locked),None,0))
        rows.append({'case':'source-locked','result':update(src,dst),'top':read(dst,0,4)})
        check(method(src,20,H,U)(src,0))
        dynamic=texture(4,3,0,512)
        check(method(dynamic,19,H,U,C.POINTER(Locked),P,U)(dynamic,0,C.byref(locked),None,0))
        check(method(src,21,H,P)(src,None))
        rows.append({'case':'destination-locked','result':update(src,dynamic)})
        check(method(dynamic,20,H,U)(dynamic,0))
        small=texture(2,2,0,1)
        check(method(src,21,H,P)(src,None))
        rows.append({'case':'matching-tail','result':update(src,small),'top':read(small,0,2)})
        rows.append({'case':'wrong-pools','result':update(dst,src)})
    finally:
        for obj in reversed(objects):release(obj)
        if device.value:release(device)
        if root:release(root)
        user.DestroyWindow(window)
    source=Path('C:/Windows/System32/d3d9.dll')
    report={'scope':__doc__,'pointerBits':C.sizeof(P)*8,'sourceSha256':hashlib.sha256(source.read_bytes()).hexdigest(),'cases':rows}
    dest=Path(__file__).resolve().parent/'reference/texture-update.json'
    dest.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report))

if __name__=='__main__':main()
