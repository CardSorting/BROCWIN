"""Record local PSAPI buffer/error behavior without inspecting another process."""
import ctypes
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
kernel = ctypes.WinDLL('kernel32', use_last_error=True)
query = kernel.K32EnumProcessModules
query.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong, ctypes.c_void_p]
query.restype = ctypes.c_int
width = ctypes.sizeof(ctypes.c_void_p)
modules = (ctypes.c_void_p * 256)()
needed = ctypes.c_ulong()
cases = []
spec = [(-1, True, n, True) for n in (0, 1, width - 1, width, width + 1, 256 * width)]
spec += [(-1, False, n, True) for n in (0, 1, width)]
spec += [(0, True, width, True), (123, True, width, True), (-1, True, width, False)]
for process, has_output, size, has_needed in spec:
    ctypes.set_last_error(0x1234)
    needed.value = 0
    ctypes.memset(modules, 0xa5, ctypes.sizeof(modules))
    value = query(process, modules if has_output else None, size,
                  ctypes.byref(needed) if has_needed else None)
    sentinel = int.from_bytes(b'\xa5' * width, 'little')
    cases.append({'process': process, 'hasOutput': has_output, 'bytes': size,
                  'hasNeeded': has_needed, 'value': value, 'error': ctypes.get_last_error(),
                  'needed': needed.value,
                  'writtenEntries': sum(int(p or 0) != sentinel for p in modules)})
source = Path('C:/Windows/System32/kernel32.dll')
report = {'metadataSource': str(source), 'sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
          'pointerWidth': width, 'scope': 'This Python process only; Wasm tests use 4-byte guest HMODULE values',
          'cases': cases}
filename_cases = []
for suffix in ('A', 'W'):
    fn = getattr(kernel, 'K32GetModuleFileNameEx' + suffix)
    fn.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong]
    fn.restype = ctypes.c_ulong
    for size in (0, 1, 2, 6, 260):
        output = (ctypes.c_ushort * 300)(*[0x5555] * 300)
        ctypes.set_last_error(0x1234)
        returned = fn(-1, None, output, size)
        filename_cases.append({'suffix': suffix, 'size': size, 'returned': returned,
                               'error': ctypes.get_last_error(), 'firstBytes': bytes(output)[:16].hex()})
report['filenameBufferCases'] = filename_cases
(HERE / 'reference/process-modules.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(f'Recorded {len(cases)} native module-enumeration buffer/error cases')
