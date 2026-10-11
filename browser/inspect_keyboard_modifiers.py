"""Read the local Windows scan-code mapping; never inject desktop input."""
import ctypes
import hashlib
import json
from pathlib import Path
import platform


def inspect():
    user = ctypes.WinDLL('user32', use_last_error=True)
    user.MapVirtualKeyW.argtypes = [ctypes.c_uint, ctypes.c_uint]
    user.MapVirtualKeyW.restype = ctypes.c_uint
    rows = []
    for name, scan, dik, generic in (
        ('ShiftLeft', 0x2a, 0x2a, 0x10), ('ShiftRight', 0x36, 0x36, 0x10),
        ('ControlLeft', 0x1d, 0x1d, 0x11), ('ControlRight', 0xe01d, 0x9d, 0x11),
        ('AltLeft', 0x38, 0x38, 0x12), ('AltRight', 0xe038, 0xb8, 0x12),
    ):
        rows.append(dict(code=name, scan=scan, dik=dik, generic=generic,
                         virtualKey=user.MapVirtualKeyW(scan, 3)))
    dll = Path('C:/Windows/System32/user32.dll')
    return dict(schema='brocwin.keyboard-modifiers-reference/v1',
                platform=platform.platform(), pointerBits=ctypes.sizeof(ctypes.c_void_p) * 8,
                source=dict(path=str(dll), sha256=hashlib.sha256(dll.read_bytes()).hexdigest()),
                method='MapVirtualKeyW(scan, MAPVK_VSC_TO_VK_EX)', cases=rows,
                limits=['Mapping reference only; no native DirectInput event injection or gameplay claim.'],
                references=[
                    'https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-mapvirtualkeyw',
                    'https://learn.microsoft.com/en-us/previous-versions/windows/desktop/ee418641(v=vs.85)',
                ])


if __name__ == '__main__':
    print(json.dumps(inspect(), indent=2))
