"""Capture Windows path API pointer offsets as portable Wasm test references."""
from __future__ import annotations

import ctypes
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import random

HERE = Path(__file__).resolve().parent


def inspect():
    library = ctypes.WinDLL('shlwapi')
    functions = {name: getattr(library, name) for name in
                 ('PathFindExtensionW', 'PathFindFileNameW', 'PathFindFileNameA')}
    for function in functions.values():
        function.argtypes = [ctypes.c_void_p]
        function.restype = ctypes.c_void_p
    paths = ['', 'c:\\joysword\\x2.exe', 'c:\\dir.ext\\file', 'C:foo.txt',
             'C:', 'C:\\', 'C:\\\\', '/a/', 'a:b:c', 'a:b:c/d:e',
             'a.b c', 'a.b/c', '게임.데이터', '📁게임.kom', '게임/📁.dat']
    randomizer = random.Random(0x74686573)
    alphabet = 'abc.\\/ :게임📁'
    paths.extend(''.join(randomizer.choice(alphabet) for _ in range(randomizer.randrange(1, 36)))
                 for _ in range(512))
    records = []
    for path in paths:
        wide = ctypes.create_unicode_buffer(path)
        base = ctypes.addressof(wide)
        row = {'path': path}
        for name in ('PathFindExtensionW', 'PathFindFileNameW'):
            row[name] = functions[name](base) - base
        if path.isascii():
            narrow = ctypes.create_string_buffer(path.encode('ascii'))
            base = ctypes.addressof(narrow)
            row['PathFindFileNameA'] = functions['PathFindFileNameA'](base) - base
        records.append(row)
    system = Path('C:/Windows/System32')
    output = {'schema': 'theseus.windows-path-reference/v1',
              'observedAt': datetime.now(timezone.utc).isoformat(),
              'platform': platform.platform(), 'contributor': 'Codex /root',
              'method': 'Direct SHLWAPI calls; offsets measured in bytes from the supplied buffer',
              'dllSha256': {name: hashlib.sha256((system / name).read_bytes()).hexdigest()
                            for name in ('shlwapi.dll', 'kernelbase.dll')},
              'records': records}
    destination = HERE / 'reference/windows-paths.json'
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(json.dumps(output, indent=2, ensure_ascii=True) + '\n', encoding='utf-8')
    print(f'{destination}: {len(records)} reference paths')


if __name__ == '__main__':
    inspect()
