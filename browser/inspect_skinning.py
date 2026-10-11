"""Native D3DX software skinning with original KSM vertices/weights; no window or game process."""
import base64
import ctypes as C
import hashlib
import json
import math
from pathlib import Path
import struct

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
P, U, H, F = C.c_void_p, C.c_uint32, C.c_int32, C.c_float
dll = C.WinDLL('d3dx9_43')
dll.D3DXCreateSkinInfoFVF.argtypes = [U, U, U, C.POINTER(P)]
dll.D3DXCreateSkinInfoFVF.restype = H
dll.D3DXMatrixInverse.argtypes = [P, P, P]
dll.D3DXMatrixInverse.restype = P


def method(obj, slot, result, *args):
    address = C.cast(obj, C.POINTER(C.POINTER(P))).contents[slot]
    return C.WINFUNCTYPE(result, P, *args)(address)


def check(hr):
    if hr < 0:
        raise RuntimeError(f'HRESULT {hr & 0xffffffff:08x}')


identity = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
rows = []
for name in ['Motion_Elsword_LK.x', 'Motion_Elsword_Common.x']:
    data = (ROOT / 'theseus/recovered/models/data033' / name).read_bytes()
    count = struct.unpack_from('<I', data, 28)[0]
    for bone in range(count):
        offset = struct.unpack_from('<I', data, 32 + bone * 84 + 72)[0]
        if not offset:
            continue
        h = struct.unpack_from('<14I', data, offset)
        if not h[10]:
            continue
        assert h[1] == 0x112
        obj = P()
        check(dll.D3DXCreateSkinInfoFVF(h[5], h[1], h[10], C.byref(obj)))
        skins = []
        try:
            for i in range(h[10]):
                at = h[11] + i * 76
                matrix = list(struct.unpack_from('<16f', data, at))
                index, n, source = struct.unpack_from('<3I', data, at + 64)
                indices = (U * n).from_buffer_copy(data[source:source + n * 4])
                weights = (F * n).from_buffer_copy(data[source + n * 4:source + n * 8])
                check(method(obj, 3, H, U, U, P, P)(obj, i, n, indices, weights))
                check(method(obj, 16, H, U, P)(obj, i, (F * 16)(*matrix)))
                skins.append({'bone': index, 'matrix': matrix, 'indices': list(indices), 'weights': list(weights)})
            vertices = data[h[6]:h[6] + h[5] * 32]
            src = C.create_string_buffer(vertices, len(vertices))
            for mode in ['identity', 'original-offset', 'rotated-translated']:
                matrices = []
                inverses = []
                for i, skin in enumerate(skins):
                    m = identity.copy() if mode == 'identity' else skin['matrix'].copy()
                    if mode == 'rotated-translated':
                        angle = (i + 1) * 0.17
                        c, s = math.cos(angle), math.sin(angle)
                        m = [c, s, 0, 0, -s, c, 0, 0, 0, 0, 1, 0, i * .05, -.3, .7, 1]
                    a, inv = (F * 16)(*m), (F * 16)()
                    assert dll.D3DXMatrixInverse(inv, None, a)
                    matrices.extend(a)
                    inverses.extend(inv[col * 4 + row] for row in range(4) for col in range(4))
                transforms, normals = (F * len(matrices))(*matrices), (F * len(inverses))(*inverses)
                dest = C.create_string_buffer(bytes([0xa5]) * (len(vertices) + 32), len(vertices) + 32)
                hr = method(obj, 24, H, P, P, P, P)(obj, transforms, normals, src, C.addressof(dest) + 16)
                check(hr)
                assert dest.raw[:16] == dest.raw[-16:] == bytes([0xa5]) * 16
                rows.append({'source': name, 'sha256': hashlib.sha256(data).hexdigest(), 'bone': bone,
                             'mode': mode, 'vertices': h[5], 'fvf': h[1], 'skins': skins,
                             'sourceBytes': base64.b64encode(vertices).decode(),
                             'transforms': matrices, 'normalTransforms': inverses,
                             'result': hr & 0xffffffff,
                             'outputBytes': base64.b64encode(dest.raw[16:-16]).decode()})
        finally:
            method(obj, 2, U)(obj)
source = Path('C:/Windows/System32/d3dx9_43.dll')
report = {'scope': __doc__, 'pointerBits': C.sizeof(P) * 8,
          'nativeDll': {'path': str(source), 'sha256': hashlib.sha256(source.read_bytes()).hexdigest()},
          'limits': 'Original mesh vertices/influences with controlled palettes; not a captured animation frame.', 'cases': rows}
(HERE / 'reference/skinning.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'cases': len(rows), 'verticesProcessed': sum(r['vertices'] for r in rows)}))
