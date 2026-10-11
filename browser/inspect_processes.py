"""Measure PSAPI buffer/error semantics; do not save host process identities."""
import ctypes as C
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
api = C.WinDLL('psapi', use_last_error=True).EnumProcesses
api.argtypes = [C.c_void_p, C.c_uint32, C.c_void_p]
api.restype = C.c_int
kernel = C.WinDLL('kernel32')
kernel.GetCurrentProcessId.restype = C.c_uint32
current = kernel.GetCurrentProcessId()
cases = []
for cb in (0, 1, 2, 3, 4, 5, 7, 8, 9, 65536):
    for output, needed in ((True, True), (False, True), (True, False)):
        buffer = (C.c_uint32 * 16385)(*([0xa5a5a5a5] * 16385))
        count = C.c_uint32(0xdeadbeef)
        C.set_last_error(0x1234)
        ok = api(buffer if output else None, cb, C.byref(count) if needed else None)
        changed = sum(value != 0xa5a5a5a5 for value in buffer)
        cases.append({'bytes': cb, 'hasOutput': output, 'hasNeeded': needed,
                      'value': ok, 'error': C.get_last_error(), 'returnedBytes': count.value,
                      'writtenEntries': changed,
                      'tailIntact': all(value == 0xa5a5a5a5 for value in buffer[changed:]),
                      'containsCaller': bool(ok and cb == 65536 and current in buffer[:changed])})
source = Path('C:/Windows/System32/psapi.dll')
report = {'source': str(source), 'sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
          'pointerBits': C.sizeof(C.c_void_p) * 8, 'pidBits': 32,
          'scope': 'Native host population differs from the single-process guest address space. '
                   'Compare buffer capacity, errors, write order and identity semantics; no host PIDs saved.',
          'cases': cases}
(HERE / 'reference/processes.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(f'Recorded {len(cases)} native EnumProcesses cases, without process identities')
