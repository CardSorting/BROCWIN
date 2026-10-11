"""Measure local D3D9 Reset parameter writeback in a hidden reference window."""
import ctypes as C
import hashlib
import json
from pathlib import Path
from inspect_texture_update import PP, P, U, H, method, release, check


def main():
    user = C.WinDLL('user32')
    user.CreateWindowExW.argtypes = [U, C.c_wchar_p, C.c_wchar_p, U, C.c_int, C.c_int, C.c_int, C.c_int, P, P, P, P]
    user.CreateWindowExW.restype = P
    user.DestroyWindow.argtypes = [P]
    window = user.CreateWindowExW(0, 'STATIC', 'Theseus Reset reference', 0, 0, 0, 320, 240, None, None, None, None)
    if not window:
        raise RuntimeError('Hidden reference window unavailable')
    dll = C.WinDLL('d3d9'); dll.Direct3DCreate9.argtypes = [U]; dll.Direct3DCreate9.restype = P
    root = dll.Direct3DCreate9(32); device = P(); rows = []
    def values(pp):
        return {name: getattr(pp, name) for name, _ in PP._fields_ if name != 'window'}
    try:
        pp = PP(width=320, height=240, format=22, count=1, swap=1, window=window, windowed=1, interval=0x80000000)
        check(method(root, 16, H, U, U, P, U, C.POINTER(PP), C.POINTER(P))(root, 0, 1, window, 0x20, C.byref(pp), C.byref(device)))
        for name, width, height, fmt, count, flags in [
                ('explicit', 320, 240, 22, 1, 0), ('automatic', 0, 0, 0, 0, 0),
                ('different-extent', 128, 96, 21, 2, 0), ('captured-flags', 0, 0, 22, 2, 3)]:
            pp = PP(width=width, height=height, format=fmt, count=count, swap=1, window=window,
                    windowed=1, depth=1, depthFormat=77, flags=flags, interval=0x80000000)
            before = values(pp)
            hr = method(device, 16, H, C.POINTER(PP))(device, C.byref(pp)) & 0xffffffff
            stored = PP(); chain = P()
            check(method(device, 14, H, U, C.POINTER(P))(device, 0, C.byref(chain)))
            try:
                check(method(chain, 9, H, C.POINTER(PP))(chain, C.byref(stored)))
            finally:
                release(chain)
            rows.append({'case': name, 'before': before, 'result': hr, 'after': values(pp), 'stored': values(stored)})
    finally:
        if device.value: release(device)
        if root: release(root)
        user.DestroyWindow(window)
    source = Path('C:/Windows/System32/d3d9.dll')
    report = {'scope': __doc__, 'pointerBits': C.sizeof(P) * 8,
              'sourceSha256': hashlib.sha256(source.read_bytes()).hexdigest(), 'cases': rows}
    dest = Path(__file__).resolve().parent / 'reference/reset-parameters.json'
    dest.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report))


if __name__ == '__main__': main()
