"""Read-only local CryptoAPI contracts using ephemeral providers; no keys saved."""
import ctypes as C
import hashlib
import json
from pathlib import Path
import platform


def main():
    adv = C.WinDLL('advapi32', use_last_error=True)
    H, U, P = C.c_void_p, C.c_uint32, C.c_void_p
    adv.CryptAcquireContextA.argtypes = [C.POINTER(H), C.c_char_p, C.c_char_p, U, U]
    adv.CryptAcquireContextA.restype = C.c_int
    adv.CryptGenRandom.argtypes = [H, U, P]
    adv.CryptGenRandom.restype = C.c_int
    adv.CryptReleaseContext.argtypes = [H, U]
    adv.CryptReleaseContext.restype = C.c_int
    rows = []
    marker = 0x1234
    for name, container, provider, kind, flags, null_output in [
        ('original', None, None, 1, 0xf0000000, False),
        ('silent', None, None, 1, 0xf0000040, False),
        ('machine', None, None, 1, 0xf0000020, False),
        ('named-ephemeral', b'theseus-probe-no-persistence', None, 1, 0xf0000000, False),
        ('default-provider', None, b'Microsoft Base Cryptographic Provider v1.0', 1, 0xf0000000, False),
        ('strong-provider', None, b'Microsoft Strong Cryptographic Provider', 1, 0xf0000000, False),
        ('enhanced-provider', None, b'Microsoft Enhanced Cryptographic Provider v1.0', 1, 0xf0000000, False),
        ('aes-provider', None, b'Microsoft Enhanced RSA and AES Cryptographic Provider', 24, 0xf0000000, False),
        ('aes-default', None, None, 24, 0xf0000000, False),
        ('unknown-provider', None, b'Theseus Missing Provider', 1, 0xf0000000, False),
        ('mismatched-type', None, b'Microsoft Enhanced Cryptographic Provider v1.0', 24, 0xf0000000, False),
        ('zero-type', None, None, 0, 0xf0000000, False),
        ('unknown-type', None, None, 999, 0xf0000000, False),
        ('unconfigured-type', None, None, 255, 0xf0000000, False),
        ('bad-flags', None, None, 1, 0xf0000001, False),
        ('new-and-verify', None, None, 1, 0xf0000008, False),
        ('null-output', None, None, 1, 0xf0000000, True),
    ]:
        handle = H(0x1234)
        C.set_last_error(marker)
        ok = adv.CryptAcquireContextA(None if null_output else C.byref(handle), container, provider, kind, flags)
        error = C.get_last_error() & 0xffffffff
        rows.append({'api': 'acquire', 'case': name, 'container': container.decode() if container else None,
                     'provider': provider.decode() if provider else None, 'type': kind, 'flags': flags,
                     'nullOutput': null_output, 'result': ok, 'error': error,
                     'output': 'handle' if ok else handle.value})
        if ok: adv.CryptReleaseContext(handle, 0)
    handle = H()
    assert adv.CryptAcquireContextA(C.byref(handle), None, None, 1, 0xf0000000)
    data = (C.c_ubyte * 131089)()
    for name, h, size, output in [('zero', handle, 0, data), ('zero-null', handle, 0, None),
                                  ('null', handle, 16, None), ('invalid', H(0), 16, data),
                                  ('invalid-zero-null', H(0), 0, None), ('large', handle, len(data), data)]:
        C.memset(data, 0xa5, len(data)); C.set_last_error(marker)
        ok = adv.CryptGenRandom(h, size, output)
        rows.append({'api': 'random', 'case': name, 'result': ok, 'error': C.get_last_error() & 0xffffffff,
                     'changed': bytes(data) != b'\xa5' * len(data)})
    for name, h, flags in [('bad-flags', handle, 1), ('release', handle, 0),
                           ('double-release', handle, 0), ('null', H(0), 0)]:
        C.set_last_error(marker)
        ok = adv.CryptReleaseContext(h, flags)
        rows.append({'api': 'release', 'case': name, 'flags': flags, 'result': ok, 'error': C.get_last_error() & 0xffffffff})
    C.set_last_error(marker)
    rows.append({'api': 'random', 'case': 'released', 'result': adv.CryptGenRandom(handle, 16, data),
                 'error': C.get_last_error() & 0xffffffff})
    assert adv.CryptAcquireContextA(C.byref(handle), None, None, 1, 0xf0000000)
    C.set_last_error(marker)
    ok = adv.CryptReleaseContext(handle, 0)
    rows.append({'api': 'release', 'case': 'fresh', 'flags': 0, 'result': ok, 'error': C.get_last_error() & 0xffffffff})
    dll = Path('C:/Windows/System32/advapi32.dll')
    result = {'scope': __doc__, 'pointerBits': C.sizeof(H) * 8, 'platform': platform.platform(),
              'sourceSha256': hashlib.sha256(dll.read_bytes()).hexdigest(), 'cases': rows}
    dest = Path(__file__).parent / 'reference/crypto.json'
    dest.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result))


if __name__ == '__main__': main()
