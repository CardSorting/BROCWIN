"""Native D3D9 draw/reference for written and unwritten color varyings."""
import ctypes as C
import hashlib
import json
from pathlib import Path
from inspect_texture_update import PP, Locked, P, U, H, method, release, check


def main():
    user = C.WinDLL('user32')
    user.CreateWindowExW.argtypes = [U, C.c_wchar_p, C.c_wchar_p, U, C.c_int, C.c_int,
                                    C.c_int, C.c_int, P, P, P, P]
    user.CreateWindowExW.restype = P
    user.DestroyWindow.argtypes = [P]
    hwnd = user.CreateWindowExW(0, 'STATIC', 'Theseus shader linkage reference',
                                0, 0, 0, 16, 16, None, None, None, None)
    if not hwnd:
        raise RuntimeError('Hidden reference window unavailable')
    dll = C.WinDLL('d3d9')
    dll.Direct3DCreate9.argtypes = [U]
    dll.Direct3DCreate9.restype = P
    root = dll.Direct3DCreate9(32)
    api = json.loads((Path(__file__).parents[1] / 'tools/wine-assembly/src/api_table.json').read_text())
    base = next(a['id'] for a in api if a['name'] == 'IDirect3DDevice9_QueryInterface')
    slots = {a['name'].split('_', 1)[1]: a['id'] - base for a in api
             if base <= a['id'] < base + 119}
    rows = []
    try:
        for processing, flags in [('hardware', 0x40), ('software', 0x20)]:
            device = P()
            objects = []
            try:
                pp = PP(width=16, height=16, format=22, count=1, swap=1,
                        window=hwnd, windowed=1, interval=0x80000000)
                check(method(root, 16, H, U, U, P, U, C.POINTER(PP), C.POINTER(P))(
                    root, 0, 1, hwnd, flags, C.byref(pp), C.byref(device)))
                def d(name, types, *args):
                    return method(device, slots[name], H, *types)(device, *args) & 0xffffffff
                target, readback = P(), P()
                check(d('CreateRenderTarget', [U,U,U,U,U,U,C.POINTER(P),P],
                        16,16,21,0,0,0,C.byref(target),None)); objects.append(target)
                check(d('CreateOffscreenPlainSurface', [U,U,U,U,C.POINTER(P),P],
                        16,16,21,2,C.byref(readback),None)); objects.append(readback)
                check(d('SetRenderTarget', [U,P], 0,target))
                for state, value in [(7,0),(137,0),(22,1),(27,0),(15,0),(28,0)]:
                    check(d('SetRenderState', [U,U], state,value))
                check(d('SetFVF', [U], 2))
                color = (C.c_float * 8)(1,.25,.5,.75, .1,.8,.3,1)
                check(d('SetVertexShaderConstantF', [U,P,U], 0,color,2))
                check(d('SetPixelShaderConstantF', [U,P,U], 0,color,2))
                vertices = (C.c_float * 9)(-1,-1,.25, 3,-1,.25, -1,3,.25)
                for write0, write1, source in [(True,False,0), (False,False,0),
                                               (False,True,0), (False,True,1),
                                               (False,False,1), (False,False,2),
                                               (True,False,3), (False,False,3), (False,True,3)]:
                    vs = [0xfffe0101,31,0x80000000,0x900f0000,1,0xc00f0000,0x90e40000]
                    if write0: vs += [1,0xd00f0000,0xa0e40000]
                    if write1: vs += [1,0xd00f0001,0xa0e40001]
                    vs += [0xffff]
                    ps = None if source == 3 else [0xffff0101,1,0x800f0000,
                          0xa0e40000 if source == 2 else 0x90e40000 + source,0xffff]
                    shaders = []
                    for name, tokens in [('Vertex',vs),('Pixel',ps)]:
                        if tokens is None:
                            check(d('SetPixelShader', [P], None))
                            check(d('SetRenderState', [U,U], 60,0xbf4080ff))
                            for state,value in [(1,2),(2,3),(3,1),(4,2),(5,3),(6,1)]:
                                check(d('SetTextureStageState', [U,U,U], 0,state,value))
                            check(d('SetTextureStageState', [U,U,U], 1,1,1))
                            continue
                        obj=P(); code=(U*len(tokens))(*tokens)
                        hr = d('Create'+name+'Shader', [P,C.POINTER(P)], code,C.byref(obj))
                        if hr: raise RuntimeError(f'{processing} {name} shader creation: {hr:08x}')
                        objects.append(obj);shaders.append(obj)
                        check(d('Set'+name+'Shader', [P], obj))
                    check(d('Clear', [U,P,U,U,C.c_float,U], 0,None,1,0xff1f3f7f,1,0))
                    check(d('BeginScene', []))
                    hr=d('DrawPrimitiveUP', [U,U,P,U], 4,1,vertices,12)
                    check(d('EndScene', []))
                    check(d('GetRenderTargetData', [P,P], target,readback))
                    locked=Locked()
                    check(method(readback,13,H,C.POINTER(Locked),P,U)(readback,C.byref(locked),None,16))
                    bgra=list((C.c_ubyte*4).from_address(locked.bits+8*locked.pitch+8*4))
                    check(method(readback,14,H)(readback))
                    rows.append({'processing':processing,'writeDiffuse':write0,'writeSpecular':write1,
                                 'pixelSource':source,'drawResult':hr,'rgba':[bgra[2],bgra[1],bgra[0],bgra[3]],
                                 'vertexTokens':vs,'pixelTokens':ps})
            finally:
                for obj in reversed(objects): release(obj)
                if device.value: release(device)
    finally:
        if root: release(root)
        user.DestroyWindow(hwnd)
    source=Path('C:/Windows/System32/d3d9.dll')
    report={'scope':__doc__,'pointerBits':C.sizeof(P)*8,'sourceSha256':hashlib.sha256(source.read_bytes()).hexdigest(),
            'window':'hidden 16x16 API test, no game process','limitation':'local hardware/runtime observations; unwritten register values are not claimed portable','cases':rows}
    dest=Path(__file__).parent/'reference/shader-link.json'
    dest.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps([{k:v for k,v in row.items() if not k.endswith('Tokens')} for row in rows]))


if __name__ == '__main__':
    main()
