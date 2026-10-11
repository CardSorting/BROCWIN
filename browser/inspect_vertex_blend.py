"""Native fixed vertex blending needed before advertising four blend matrices."""
from pathlib import Path
import base64
import ctypes as C
import hashlib
import json
import struct
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'theseus/browser'))
from inspect_texture_update import PP,Locked,P,U,H,method,release,check
user=C.WinDLL('user32')
user.CreateWindowExW.argtypes=[U,C.c_wchar_p,C.c_wchar_p,U,C.c_int,C.c_int,C.c_int,C.c_int,P,P,P,P]
user.CreateWindowExW.restype=P;user.DestroyWindow.argtypes=[P]
window=user.CreateWindowExW(0,'STATIC','Theseus fixed blending API reference',0,0,0,32,32,None,None,None,None)
assert window
dll=C.WinDLL('d3d9');dll.Direct3DCreate9.argtypes=[U];dll.Direct3DCreate9.restype=P
d3d=dll.Direct3DCreate9(32);device=P();objects=[];rows=[]
api=json.loads((ROOT/'theseus/tools/wine-assembly/src/api_table.json').read_text())
start=next(a['id'] for a in api if a['name']=='IDirect3DDevice9_QueryInterface')
slots={a['name'].split('_',1)[1]:a['id']-start for a in api if start<=a['id']<start+119}
identity=[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1]
worlds=[
    [.8,0,0,0,0,1.1,0,0,0,0,.9,0,-.1,.1,.01,1],
    [.9,.3,0,0,-.2,.7,0,0,0,0,1.2,0,.2,-.1,.08,1],
    [1,0,.1,0,.2,.8,0,0,0,.1,1,0,-.2,-.1,.03,1],
    [.7,-.2,0,0,.3,1.2,0,0,.1,0,.8,0,.1,.2,-.04,1]]
view=identity.copy();view[12:15]=[.1,-.08,.02]
material=[.8,.7,.6,1]+[0,0,0,1]*3+[0]
light=struct.pack('<I25f',3,*([.7,.9,.5,1]+[0,0,0,0]*2+[0,0,0]+[.25,-.5,1]+[1000,0,1,0,0,0,0]))
try:
    pp=PP(width=32,height=32,format=22,count=1,swap=1,window=window,windowed=1,interval=0x80000000)
    check(method(d3d,16,H,U,U,P,U,C.POINTER(PP),C.POINTER(P))(d3d,0,1,window,0x20,C.byref(pp),C.byref(device)))
    def call(name,types,*args):
        return method(device,slots[name],H,*types)(device,*args)&0xffffffff
    target,readback=P(),P()
    check(call('CreateRenderTarget',[U,U,U,U,U,U,C.POINTER(P),P],32,32,21,0,0,0,C.byref(target),None));objects.append(target)
    check(call('CreateOffscreenPlainSurface',[U,U,U,U,C.POINTER(P),P],32,32,21,2,C.byref(readback),None));objects.append(readback)
    check(call('SetRenderTarget',[U,P],0,target))
    for rs,value in [(7,0),(22,1),(27,0),(15,0),(28,0),(29,0),(141,0),(145,0),(146,0),(147,0),(148,0),(139,0),(167,0)]:
        check(call('SetRenderState',[U,U],rs,value))
    for ts,value in [(1,2),(2,0),(4,2),(5,0)]:
        check(call('SetTextureStageState',[U,U,U],0,ts,value))
    check(call('SetTextureStageState',[U,U,U],1,1,1))
    for index,matrix in [(2,view),(3,identity)]+[(256+i,m) for i,m in enumerate(worlds)]:
        check(call('SetTransform',[U,P],index,(C.c_float*16)(*matrix)))
    check(call('SetMaterial',[P],(C.c_float*17)(*material)))
    check(call('SetLight',[U,P],0,C.create_string_buffer(light)))
    check(call('LightEnable',[U,U],0,1))
    for count in [1,2,3]:
        weights=[[.15,.25,.35][:count],[.6,.1,.05][:count],[-.15,.35,.4][:count]]
        vertices=b''.join(struct.pack('<'+('f'*(6+count))+'I',*p,*w,.2,.4,-.8,0xffb06030)
            for p,w in zip([[-.6,-.6,.3],[.7,-.5,.3],[-.3,.7,.3]],weights))
        stride=28+count*4;fvf=(4+count*2)|0x50
        check(call('SetFVF',[U],fvf))
        check(call('SetRenderState',[U,U],151,count))
        for lighting in [0,1]:
            for normalize in [0,1]:
                check(call('SetRenderState',[U,U],137,lighting))
                check(call('SetRenderState',[U,U],143,normalize))
                check(call('Clear',[U,P,U,U,C.c_float,U],0,None,1,0xff102030,1,0))
                check(call('BeginScene',[]))
                hr=call('DrawPrimitiveUP',[U,U,P,U],4,1,C.create_string_buffer(vertices),stride)
                check(call('EndScene',[]));check(hr)
                check(call('GetRenderTargetData',[P,P],target,readback))
                locked=Locked();check(method(readback,13,H,C.POINTER(Locked),P,U)(readback,C.byref(locked),None,16))
                bgra=b''.join(C.string_at(locked.bits+y*locked.pitch,128) for y in range(32))
                check(method(readback,14,H)(readback))
                rgba=b''.join(bytes((bgra[i+2],bgra[i+1],bgra[i],bgra[i+3])) for i in range(0,len(bgra),4))
                row={'weights':count,'lighting':lighting,'normalize':normalize,'fvf':fvf,'stride':stride,'result':hr,
                    'vertices':base64.b64encode(vertices).decode(),'rgba':base64.b64encode(rgba).decode(),
                    'nonBackgroundPixels':sum(rgba[i:i+4]!=bytes([16,32,48,255]) for i in range(0,len(rgba),4))}
                rows.append(row);print(json.dumps({k:v for k,v in row.items() if k not in ('vertices','rgba')}))
finally:
    for obj in reversed(objects):release(obj)
    if device.value:release(device)
    release(d3d);user.DestroyWindow(window)
report={'scope':__doc__,'pointerBits':C.sizeof(P)*8,'worlds':worlds,'view':view,'projection':identity,
    'material':material,'light':base64.b64encode(light).decode(),'deviceFlags':0x20,'size':32,'cases':rows,
    'dllSha256':hashlib.sha256(Path('C:/Windows/System32/d3d9.dll').read_bytes()).hexdigest(),
    'reference':'https://learn.microsoft.com/en-us/windows/win32/direct3d9/geometry-blending',
    'limits':'Fixed-function API coverage fixture; not a substitute game or game acceptance evidence.'}
(HERE/'reference/fixed-vertex-blending.json').write_text(json.dumps(report,indent=2)+'\n')
