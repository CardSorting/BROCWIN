"""Native D3DX adjacency reference with a hidden API-test window; no game process."""
import ctypes as C
import hashlib
import json
from pathlib import Path
import struct
from inspect_texture_update import PP, P, U, H, method, release, check

HERE = Path(__file__).resolve().parent


def main():
    user = C.WinDLL('user32')
    user.CreateWindowExW.argtypes = [U, C.c_wchar_p, C.c_wchar_p, U, C.c_int, C.c_int, C.c_int, C.c_int, P, P, P, P]
    user.CreateWindowExW.restype = P
    user.DestroyWindow.argtypes = [P]
    window = user.CreateWindowExW(0, 'STATIC', 'Theseus mesh reference', 0, 0, 0, 16, 16, None, None, None, None)
    if not window:
        raise RuntimeError('Hidden API-test window unavailable')
    dll = C.WinDLL('d3d9')
    dll.Direct3DCreate9.argtypes = [U]
    dll.Direct3DCreate9.restype = P
    d3dx = C.WinDLL('d3dx9_43')
    d3dx.D3DXCreateMeshFVF.argtypes = [U, U, U, U, P, C.POINTER(P)]
    d3dx.D3DXCreateMeshFVF.restype = H
    root = dll.Direct3DCreate9(32)
    device = P()
    rows = []
    lock_rows = []
    try:
        pp = PP(width=16, height=16, format=22, count=1, swap=1, window=window, windowed=1, interval=0x80000000)
        check(method(root, 16, H, U, U, P, U, C.POINTER(PP), C.POINTER(P))(
            root, 0, 1, window, 0x20, C.byref(pp), C.byref(device)))
        for name in ['Motion_Elsword_LK.x', 'Motion_Elsword_Common.x']:
            data = (HERE.parent / 'recovered/models/data033' / name).read_bytes()
            bones = struct.unpack_from('<I', data, 28)[0]
            offset = next(struct.unpack_from('<I', data, 32 + i * 84 + 72)[0]
                          for i in range(bones) if struct.unpack_from('<I', data, 32 + i * 84 + 72)[0])
            h = struct.unpack_from('<14I', data, offset)
            fvf, vertices, faces = h[1], h[5], h[7]
            obj = P()
            check(d3dx.D3DXCreateMeshFVF(faces, vertices, 0x220 | (h[2] & 1), fvf, device, C.byref(obj)))
            try:
                stride = method(obj, 8, U)(obj)
                for lock, unlock, source, size in [(15, 16, h[6], vertices * stride),
                        (17, 18, h[8], faces * 3 * (4 if h[2] & 1 else 2)), (24, 25, h[9], faces * 4)]:
                    dest = P()
                    check(method(obj, lock, H, U, C.POINTER(P))(obj, 0, C.byref(dest)))
                    C.memmove(dest, data[source:source + size], size)
                    check(method(obj, unlock, H)(obj))
                adjacency = (U * (faces * 3))()
                hr = method(obj, 22, H, C.c_float, C.POINTER(U))(obj, 0.0, adjacency) & 0xffffffff
                rows.append({'name': name, 'inputSha256': hashlib.sha256(data).hexdigest(),
                             'faces': faces, 'vertices': vertices, 'stride': stride, 'result': hr,
                             'adjacency': list(adjacency) if hr == 0 else None})
            finally:
                release(obj)
        for kind in ['vertex', 'index']:
            obj = P()
            check(method(device, 26 if kind == 'vertex' else 27, H, U, U, U, U, C.POINTER(P), P)(
                device, 96, 0, 0x112 if kind == 'vertex' else 101, 1, C.byref(obj), None))
            try:
                locks = []
                first = None
                for offset, size, flags in [(0, 0, 16), (4, 8, 0), (4, 0, 16)]:
                    dest = P()
                    hr = method(obj, 11, H, U, U, C.POINTER(P), U)(obj, offset, size, C.byref(dest), flags) & 0xffffffff
                    if first is None and hr == 0:
                        first = dest.value
                    locks.append({'offset': offset, 'size': size, 'flags': flags, 'result': hr,
                                  'pointerOffset': dest.value - first if hr == 0 else None})
                unlocks = [method(obj, 12, H)(obj) & 0xffffffff for _ in range(4)]
                lock_rows.append({'kind': kind, 'locks': locks, 'unlocks': unlocks})
            finally:
                release(obj)
    finally:
        if device.value:
            release(device)
        if root:
            release(root)
        user.DestroyWindow(window)
    sources = [Path('C:/Windows/System32') / name for name in ['d3d9.dll', 'd3dx9_43.dll']]
    report = {'scope': __doc__, 'pointerBits': C.sizeof(P) * 8,
              'sources': [{'path': str(p), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in sources],
              'cases': rows, 'nestedBufferLocks': lock_rows}
    (HERE / 'reference/mesh-adjacency.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps([{k: v for k, v in row.items() if k != 'adjacency'} for row in rows]))
    print(json.dumps(lock_rows))


if __name__ == '__main__':
    main()
