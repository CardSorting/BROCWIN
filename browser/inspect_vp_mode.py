"""Measure D3D9 software vertex-processing state; hidden API window only."""
import ctypes as C
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
from inspect_texture_update import PP, P, U, H, method, release, check

user = C.WinDLL('user32')
user.CreateWindowExW.argtypes = [U, C.c_wchar_p, C.c_wchar_p, U, C.c_int, C.c_int, C.c_int, C.c_int, P, P, P, P]
user.CreateWindowExW.restype = P
user.DestroyWindow.argtypes = [P]
window = user.CreateWindowExW(0, 'STATIC', 'Theseus VP state reference', 0, 0, 0, 16, 16, None, None, None, None)
assert window
dll = C.WinDLL('d3d9')
dll.Direct3DCreate9.argtypes = [U]
dll.Direct3DCreate9.restype = P
root = dll.Direct3DCreate9(32)
rows = []
try:
    for flags in [0x20, 0x40, 0x80, 0x424]:
        pp = PP(width=16, height=16, format=22, count=1, swap=1, window=window, windowed=1, interval=0x80000000)
        device = P()
        check(method(root, 16, H, U, U, P, U, C.POINTER(PP), C.POINTER(P))(
            root, 0, 1, window, flags, C.byref(pp), C.byref(device)))
        try:
            get = lambda: method(device, 78, U)(device)
            row = {'flags': flags, 'initial': get(), 'sets': []}
            for value in [0, 1, 2, 0xffffffff, 0, 1]:
                hr = method(device, 77, H, U)(device, value) & 0xffffffff
                row['sets'].append({'input': value, 'hr': hr, 'get': get()})
            if flags == 0x80:
                block = P()
                check(method(device, 60, H)(device))
                check(method(device, 77, H, U)(device, 1))
                check(method(device, 61, H, C.POINTER(P))(device, C.byref(block)))
                check(method(device, 77, H, U)(device, 0))
                check(method(block, 5, H)(block))
                row['afterRecordedApply'] = get()
                release(block)
                check(method(device, 77, H, U)(device, 1))
            row['beforeReset'] = get()
            row['reset'] = method(device, 16, H, C.POINTER(PP))(device, C.byref(pp)) & 0xffffffff
            row['afterReset'] = get()
            rows.append(row)
        finally:
            release(device)
finally:
    release(root)
    user.DestroyWindow(window)
source = Path('C:/Windows/System32/d3d9.dll')
report = {'scope': __doc__, 'pointerBits': C.sizeof(P) * 8,
          'sourceSha256': hashlib.sha256(source.read_bytes()).hexdigest(), 'cases': rows}
(HERE / 'reference/software-vertex-processing.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps(rows))
