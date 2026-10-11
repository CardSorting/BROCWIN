"""Compare resource-miss behavior with Windows, without executing game code."""
from __future__ import annotations

import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform

ROOT = Path(__file__).resolve().parents[2]


class ActCtxW(ctypes.Structure):
    _fields_ = [('size', wintypes.ULONG), ('flags', wintypes.DWORD),
                ('source', wintypes.LPCWSTR), ('architecture', wintypes.WORD),
                ('language', wintypes.WORD), ('directory', wintypes.LPCWSTR),
                ('resource', ctypes.c_void_p), ('application', wintypes.LPCWSTR),
                ('module', wintypes.HMODULE)]


def inspect():
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.LoadLibraryExW.argtypes = [wintypes.LPCWSTR, wintypes.HANDLE, wintypes.DWORD]
    kernel.LoadLibraryExW.restype = wintypes.HMODULE
    kernel.CreateActCtxW.argtypes = [ctypes.POINTER(ActCtxW)]
    kernel.CreateActCtxW.restype = wintypes.HANDLE
    kernel.ReleaseActCtx.argtypes = [wintypes.HANDLE]
    kernel.ReleaseActCtx.restype = None
    kernel.FreeLibrary.argtypes = [wintypes.HMODULE]
    records = []
    for name in ('mfc100u.dll', 'x2.exe'):
        path = ROOT / 'client/data' / name
        # LOAD_LIBRARY_AS_DATAFILE | LOAD_LIBRARY_AS_IMAGE_RESOURCE. Windows
        # maps resources without resolving imports or invoking DllMain/entrypoint.
        module = kernel.LoadLibraryExW(str(path), None, 0x22)
        if not module:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            for resource in (2, 60000):
                context = ActCtxW()
                context.size = ctypes.sizeof(context)
                context.flags = 0x88
                context.source = str(path)
                context.module = module
                context.resource = resource
                ctypes.set_last_error(0)
                handle = kernel.CreateActCtxW(ctypes.byref(context))
                error = ctypes.get_last_error()
                success = handle != ctypes.c_void_p(-1).value
                if success:
                    kernel.ReleaseActCtx(handle)
                records.append({'module': name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                                'resource': resource, 'flags': context.flags,
                                'success': success, 'lastError': error})
        finally:
            kernel.FreeLibrary(module)
    output = {'schema': 'theseus.windows-api-reference/v1',
              'observedAt': datetime.now(timezone.utc).isoformat(),
              'platform': platform.platform(), 'pythonPointerBits': ctypes.sizeof(ctypes.c_void_p) * 8,
              'contributor': 'Codex /root', 'gameCodeExecuted': False,
              'method': 'LoadLibraryExW with data/image-resource flags; CreateActCtxW resource lookup',
              'records': records}
    destination = ROOT / 'theseus/reports/browser/native-activation-contexts.json'
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(output, indent=2) + '\n', encoding='utf-8')
    print(destination)
    for record in records:
        print(f'{record["module"]} resource={record["resource"]}: success={record["success"]}, error={record["lastError"]}')


if __name__ == '__main__':
    inspect()
