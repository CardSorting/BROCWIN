"""Prepare a local compiled D3D9 shader validator for the Wasm guest.

This is an explicitly derived component, not an original game file or a
reimplementation of its validation rules. Original mapped sections (including
code, data, relocations, imports and security-cookie machinery) stay byte exact.
Only the public export directory and component initialization are replaced.
The initializer calls the original cookie initializer; the full graphics-driver
DLL initialization is outside the extracted component's scope.
"""
from __future__ import annotations

import hashlib
import struct
from pathlib import Path

SOURCE = Path('C:/Windows/SysWOW64/d3d9.dll')
SOURCE_SHA256 = '210e52314d24bdc8492e5185674626225af2c030ff51d13c01155aedb2d248ad'
NAME = 'theseus-validator.dll'
EXPORT = 'Direct3DShaderValidatorCreate9'
FACTORY_RVA = 0xff710
COOKIE_INIT_RVA = 0x796c5


def align(n, boundary):
    return (n + boundary - 1) & -boundary


def build_component(original):
    import pefile
    if hashlib.sha256(original).hexdigest() != SOURCE_SHA256:
        raise RuntimeError('Local shader-validator DLL changed; inspect the new binary before extracting it')
    pe = pefile.PE(data=original)
    assert pe.FILE_HEADER.Machine == 0x14c
    assert pe.OPTIONAL_HEADER.ImageBase == 0x10000000
    assert pe.OPTIONAL_HEADER.AddressOfEntryPoint == 0x78d80
    assert pe.OPTIONAL_HEADER.DATA_DIRECTORY[9].VirtualAddress == 0  # no TLS initializer
    assert pe.get_data(0x78d80, 16) == bytes.fromhex('8bff558bec837d0c017505e835090000')
    assert pe.get_data(FACTORY_RVA, 12) == bytes.fromhex('6a04b80f3c0810e8a114f8ff')
    assert next(s.address for s in pe.DIRECTORY_ENTRY_EXPORT.symbols
                if s.name == EXPORT.encode()) == FACTORY_RVA

    rva = pe.OPTIONAL_HEADER.SizeOfImage
    data = bytearray(40)
    def alloc(blob):
        at = rva + len(data)
        data.extend(blob)
        return at
    dll_name = alloc(NAME.encode() + b'\0')
    symbol_name = alloc(EXPORT.encode() + b'\0')
    while len(data) % 4:
        data.append(0)
    eat = alloc(struct.pack('<I', FACTORY_RVA))
    names = alloc(struct.pack('<I', symbol_name))
    ordinals = alloc(struct.pack('<H', 0))
    struct.pack_into('<IIHHIIIIIII', data, 0, 0, 0, 0, 0, dll_name, 1, 1, 1, eat, names, ordinals)
    export_size = len(data)
    while len(data) % 16:
        data.append(0)
    entry = rva + len(data)
    # DllMain(hModule, reason, reserved): process attach runs the original
    # cookie initializer. The other notifications need no component state.
    code = bytearray.fromhex('837c2408017505e800000000b801000000c20c00')
    struct.pack_into('<i', code, 8, COOKIE_INIT_RVA - (entry + 12))
    data.extend(code)

    # A derived image cannot retain the original file's Authenticode signature.
    # The certificate overlay is omitted; PE execution/security flags and the
    # mapped load configuration are preserved. Nothing is changed on the OS.
    raw_end = max(s.PointerToRawData + s.SizeOfRawData for s in pe.sections)
    out = bytearray(original[:raw_end])
    file_align = pe.OPTIONAL_HEADER.FileAlignment
    out.extend(bytes(align(len(out), file_align) - len(out)))
    raw = len(out)
    out.extend(data)
    out.extend(bytes(align(len(out), file_align) - len(out)))
    opt = pe.OPTIONAL_HEADER.get_file_offset()
    section_at = pe.sections[-1].get_file_offset() + 40
    assert section_at + 40 <= pe.OPTIONAL_HEADER.SizeOfHeaders
    assert original[section_at:section_at + 40] == bytes(40)
    struct.pack_into('<H', out, pe.FILE_HEADER.get_file_offset() + 2, len(pe.sections) + 1)
    struct.pack_into('<I', out, opt + 4, pe.OPTIONAL_HEADER.SizeOfCode + align(len(data), file_align))
    struct.pack_into('<I', out, opt + 16, entry)
    struct.pack_into('<I', out, opt + 56, align(rva + len(data), pe.OPTIONAL_HEADER.SectionAlignment))
    struct.pack_into('<I', out, opt + 64, 0)  # derived checksum
    struct.pack_into('<II', out, opt + 96, rva, export_size)
    struct.pack_into('<II', out, opt + 96 + 4 * 8, 0, 0)  # no derived signature
    out[section_at:section_at + 8] = b'.thval\0\0'
    struct.pack_into('<IIIIIIHHI', out, section_at + 8,
                     len(data), rva, align(len(data), file_align), raw, 0, 0, 0, 0, 0x60000060)

    parsed = pefile.PE(data=bytes(out))
    assert parsed.OPTIONAL_HEADER.DllCharacteristics == pe.OPTIONAL_HEADER.DllCharacteristics
    assert len(parsed.DIRECTORY_ENTRY_EXPORT.symbols) == 1
    assert parsed.DIRECTORY_ENTRY_EXPORT.symbols[0].address == FACTORY_RVA
    for section in pe.sections:
        start, size = section.PointerToRawData, section.SizeOfRawData
        assert out[start:start + size] == original[start:start + size]
    return bytes(out), {
        'factoryRva': FACTORY_RVA, 'cookieInitializerRva': COOKIE_INIT_RVA,
        'originalEntryRva': pe.OPTIONAL_HEADER.AddressOfEntryPoint, 'componentEntryRva': entry,
        'preservedSections': [{'name': s.Name.rstrip(b'\0').decode(),
                               'rva': s.VirtualAddress,
                               'sha256': hashlib.sha256(s.get_data()).hexdigest()} for s in pe.sections],
        'initialization': 'Reconstructed component DllMain calls unchanged native security-cookie initializer; graphics-driver initialization is outside component scope.',
        'signature': 'Derived local guest image is unsigned; source certificate overlay omitted; original mapped sections and DLL security flags preserved.',
    }


def prepare_component(directory, root):
    original = SOURCE.read_bytes()
    component, derivation = build_component(original)
    path = directory / NAME
    path.write_bytes(component)
    return {'url': 'platform/' + NAME, 'source': path.relative_to(root).as_posix(),
            'vfsPath': 'c:\\windows\\system\\' + NAME, 'loadMode': 'required',
            'size': len(component), 'sha256': hashlib.sha256(component).hexdigest(),
            'provenance': 'local-os-compiled-shader-validator-component',
            'codeSource': str(SOURCE), 'codeSourceSha256': SOURCE_SHA256,
            'exportCount': 1, 'derivation': derivation}
