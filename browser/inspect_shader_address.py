"""Measure VS 1.1 MOV address rounding with native D3D9 ProcessVertices."""
import ctypes as C
import hashlib
import json
from pathlib import Path
from inspect_texture_update import PP, P, U, H, method, release, check

def main():
    user = C.WinDLL('user32')
    user.CreateWindowExW.argtypes = [U,C.c_wchar_p,C.c_wchar_p,U,C.c_int,C.c_int,C.c_int,C.c_int,P,P,P,P]
    user.CreateWindowExW.restype = P
    user.DestroyWindow.argtypes = [P]
    hwnd = user.CreateWindowExW(0, 'STATIC', 'Theseus shader reference', 0, 0, 0, 16, 16, None, None, None, None)
    dll = C.WinDLL('d3d9'); dll.Direct3DCreate9.argtypes = [U]; dll.Direct3DCreate9.restype = P
    root = dll.Direct3DCreate9(32); device = P(); objects = []
    values = [-2.75,-2.5,-2.25,-1.75,-1.5,-1.25,-0.75,-0.5,-0.25,0,0.25,0.49,0.5,0.51,0.75,1,1.25,1.5,1.75,2.5,2.75]
    # mov a0.x, c0.x; mov oPos, c[a0.x + 10]
    tokens = [0xfffe0101,1,0xb0010000,0xa0000000,1,0xc00f0000,0xa0e4200a,0xffff]
    try:
        pp = PP(width=16,height=16,format=22,count=1,swap=1,window=hwnd,windowed=1,interval=0x80000000)
        check(method(root,16,H,U,U,P,U,C.POINTER(PP),C.POINTER(P))(root,0,1,hwnd,0x20,C.byref(pp),C.byref(device)))
        def vb(size, fvf):
            out=P();check(method(device,26,H,U,U,U,U,C.POINTER(P),P)(device,size,0,fvf,2,C.byref(out),None));objects.append(out);return out
        source, dest = vb(len(values)*12,2), vb(len(values)*16,4)
        bits=P();check(method(source,11,H,U,U,C.POINTER(P),U)(source,0,0,C.byref(bits),0))
        floats=(C.c_float*(len(values)*3)).from_address(bits.value)
        for i,value in enumerate(values): floats[i*3:i*3+3]=[value,0,0]
        check(method(source,12,H)(source))
        code=(U*len(tokens))(*tokens);shader=P()
        check(method(device,91,H,C.POINTER(U),C.POINTER(P))(device,code,C.byref(shader)));objects.append(shader)
        check(method(device,89,H,U)(device,2))
        check(method(device,92,H,P)(device,shader))
        constants=(C.c_float*(96*4))()
        for i in range(96): constants[i*4:i*4+4]=[(i-10)/32,0,0.25,1]
        check(method(device,94,H,U,P,U)(device,0,constants,96))
        check(method(device,100,H,U,P,U,U)(device,0,source,0,12))
        for i,value in enumerate(values):
            address=(C.c_float*4)(value,0,0,0)
            check(method(device,94,H,U,P,U)(device,0,address,1))
            check(method(device,85,H,U,U,U,P,P,U)(device,i,i,1,dest,None,0))
        check(method(dest,11,H,U,U,C.POINTER(P),U)(dest,0,0,C.byref(bits),16))
        result=(C.c_float*(len(values)*4)).from_address(bits.value)
        rows=[{'input':value,'screen':list(result[i*4:i*4+4]),
               'addressOffset':(result[i*4]-8)*4} for i,value in enumerate(values)]
        check(method(dest,12,H)(dest))
    finally:
        for obj in reversed(objects): release(obj)
        if device.value: release(device)
        if root: release(root)
        if hwnd: user.DestroyWindow(hwnd)
    source=Path('C:/Windows/System32/d3d9.dll')
    report={'scope':__doc__,'source':str(source),'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
            'pointerBits':C.sizeof(P)*8,'tokens':tokens,'device':'HAL with software vertex processing; hidden 16x16 API-test window','cases':rows}
    dest=Path(__file__).resolve().parent/'reference/shader-address.json'
    dest.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(rows))

if __name__=='__main__': main()
