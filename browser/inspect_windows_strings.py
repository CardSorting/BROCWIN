"""Capture local Windows SHLWAPI behavior; never load the game executable."""
import ctypes
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
shell = ctypes.WinDLL('shlwapi')
cases = []
for name in ('StrCpyW', 'StrCatW', 'StrStrW'):
    fn = getattr(shell, name)
    fn.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    fn.restype = ctypes.c_void_p
    pairs = [('', ''), ('abc', ''), ('', 'a'), ('abc', 'bc'), ('AbC', 'bc'),
             ('ababa', 'aba'), ('ababa', 'bab'), ('abc', 'abcd'),
             ('\uac00\ub098\ub2e4', '\ub098'), ('e\u0301', '\u00e9'),
             ('\U0001f680abc\U0001f680', 'abc\U0001f680'),
             ('\ud800\udc00z', '\udc00'), ('abc\0ignored', 'ignored')]
    if name == 'StrStrW':
        pairs += [(None, 'a'), ('a', None), (None, None)]
    for left, right in pairs:
        dst = ctypes.create_unicode_buffer(left, 512) if left is not None else None
        src = ctypes.create_unicode_buffer(right, 512) if right is not None else None
        out = fn(ctypes.addressof(dst) if dst is not None else None,
                 ctypes.addressof(src) if src is not None else None)
        row = {'api': name, 'left': left, 'right': right,
               'resultOffset': None if not out else (out - ctypes.addressof(dst)) // 2}
        if name != 'StrStrW':
            row['output'] = dst.value
        cases.append(row)

source = Path('C:/Windows/System32/shlwapi.dll')
report = {'source': str(source), 'sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
          'queries': 'Read-only string operations in local scratch buffers', 'cases': cases}
(HERE / 'reference/shell-strings.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(f'Recorded {len(cases)} native SHLWAPI string cases')
