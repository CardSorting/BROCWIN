"""Query the local system's base Direct3D9 COM object; no game or device is run."""
import ctypes
import hashlib
import json
from pathlib import Path
import uuid

HERE = Path(__file__).resolve().parent
d3d = ctypes.WinDLL('d3d9')
d3d.Direct3DCreate9.argtypes = [ctypes.c_uint]
d3d.Direct3DCreate9.restype = ctypes.c_void_p
obj = d3d.Direct3DCreate9(32)
if not obj:
    raise RuntimeError('The local Direct3D9 reference object is unavailable')
vtable = ctypes.cast(obj, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
query = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p))(vtable[0])
release = ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)(vtable[2])
cases = []
monitors = []
try:
    for iid in ['00000000-0000-0000-c000-000000000046', '81bdcbca-64d4-426d-ae8d-ad0147f4275c',
                '02177241-69fc-400c-8ff1-93a44df6861d', 'd0223b96-bf7a-43fd-92bd-a43b0d82b9eb',
                'b18b10ce-2649-405a-870f-95f777d4313a', '81bdcbca-64d4-426d-ae8d-ad0147f4275d']:
        raw = ctypes.create_string_buffer(uuid.UUID(iid).bytes_le)
        out = ctypes.c_void_p(0x1234)
        hr = query(obj, raw, ctypes.byref(out)) & 0xffffffff
        row = {'iid': iid, 'result': hr, 'outputNull': out.value is None, 'sameIdentity': out.value == obj}
        if hr == 0:
            row['referencesAfterRelease'] = release(out)
        cases.append(row)
    count = ctypes.WINFUNCTYPE(ctypes.c_uint, ctypes.c_void_p)(vtable[4])(obj)
    get_monitor = ctypes.WINFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint)(vtable[15])
    class RECT(ctypes.Structure):
        _fields_ = [('left', ctypes.c_long), ('top', ctypes.c_long), ('right', ctypes.c_long), ('bottom', ctypes.c_long)]
    class MONITORINFO(ctypes.Structure):
        _fields_ = [('cbSize', ctypes.c_ulong), ('monitor', RECT), ('work', RECT), ('flags', ctypes.c_ulong)]
    user = ctypes.WinDLL('user32', use_last_error=True)
    user.GetMonitorInfoW.argtypes = [ctypes.c_void_p, ctypes.POINTER(MONITORINFO)]
    user.GetMonitorInfoW.restype = ctypes.c_int
    for adapter in [0, count, 0xffffffff]:
        handle = get_monitor(obj, adapter)
        info = MONITORINFO(cbSize=ctypes.sizeof(MONITORINFO))
        ok = bool(user.GetMonitorInfoW(handle, ctypes.byref(info)))
        monitors.append({'adapter': adapter, 'validAdapter': adapter < count,
            'monitorNonNull': bool(handle), 'getMonitorInfoW': ok,
            'primary': bool(info.flags & 1) if ok else None,
            'monitor': [info.monitor.left, info.monitor.top, info.monitor.right, info.monitor.bottom] if ok else None})
finally:
    release(obj)
source = Path('C:/Windows/System32/d3d9.dll')
report = {'source': str(source), 'sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
          'scope': 'Base Direct3DCreate9 COM interface and adapter-monitor queries only. No device, window, game executable or draw call.',
          'cases': cases, 'adapterCount': count, 'monitors': monitors}
(HERE / 'reference/d3d-interfaces.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(f'Recorded {len(cases)} native Direct3D9 interface queries')
