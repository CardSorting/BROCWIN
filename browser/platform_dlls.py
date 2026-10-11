"""Generate PE export adapters for the browser's reconstructed Windows APIs.

Only names and ordinals come from data-only inspection of local system DLLs.
No Microsoft code is copied into these adapters. Each export is an x86 indirect
jump to a Wasm handler, except the shader-validator export, which imports the
separately documented local compiled component from shader_validator.py. Missing
handlers keep the runtime's explicit unimplemented-API failure.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import struct


LIBRARIES = ('kernel32.dll', 'user32.dll', 'gdi32.dll', 'd3d9.dll')


def align(value, boundary):
    return (value + boundary - 1) & -boundary


def build_adapter(name, symbols, implementations=None):
    base = 0x10000000
    # Preserve the ordinal table, including holes and name aliases.
    by_ordinal = {}
    for symbol in symbols:
        by_ordinal.setdefault(symbol['ordinal'], symbol['name'])
    ordinals = sorted(by_ordinal)
    first, last = min(ordinals), max(ordinals)
    named = sorted((s['name'], s['ordinal']) for s in symbols if s['name'])
    text_rva = 0x1000
    code = bytearray(len(ordinals) * 8)
    data_rva = align(text_rva + len(code), 0x1000)
    data = bytearray(40)

    def alloc(content):
        offset = len(data)
        data.extend(content)
        return data_rva + offset

    def zero(size):
        return alloc(bytes(size))

    def put(rva, fmt, *values):
        struct.pack_into(fmt, data, rva - data_rva, *values)

    dll_name = alloc(name.encode('ascii') + b'\0')
    while len(data) % 4:
        data.append(0)
    eat = zero((last - first + 1) * 4)
    names = zero(len(named) * 4)
    name_ordinals = zero(len(named) * 2)
    index = {ordinal: i for i, ordinal in enumerate(ordinals)}
    for i, (export_name, ordinal) in enumerate(named):
        put(names + 4 * i, '<I', alloc(export_name.encode('ascii') + b'\0'))
        put(name_ordinals + 2 * i, '<H', ordinal - first)
    for ordinal, i in index.items():
        put(eat + (ordinal - first) * 4, '<I', text_rva + i * 8)
    struct.pack_into('<IIHHIIIIIII', data, 0, 0, 0, 0, 0, dll_name, first,
                     last - first + 1, len(named), eat, names, name_ordinals)
    export_size = len(data)
    while len(data) % 4:
        data.append(0)
    implementations = implementations or {}
    groups = {}
    for ordinal in ordinals:
        target = by_ordinal[ordinal] or f'TheseusUnsupported_{name}_{ordinal}'
        library = implementations.get(target, 'theseus-win32.dll')
        groups.setdefault(library, []).append((ordinal, target))
    imports_size = (len(groups) + 1) * 20
    imports = zero(imports_size)
    iats = {}
    for group, (library, entries) in enumerate(groups.items()):
        host_name = alloc(library.encode('ascii') + b'\0')
        while len(data) % 4:
            data.append(0)
        ilt = zero((len(entries) + 1) * 4)
        iat = zero((len(entries) + 1) * 4)
        for j, (ordinal, target) in enumerate(entries):
            hint = alloc(b'\0\0' + target.encode('ascii') + b'\0')
            if len(data) % 2:
                data.append(0)
            put(ilt + j * 4, '<I', hint)
            put(iat + j * 4, '<I', hint)
            iats[ordinal] = iat + j * 4
        put(imports + group * 20, '<IIIII', ilt, 0, 0, host_name, iat)
    relocation_pages = {}
    for ordinal, i in index.items():
        code[i * 8:i * 8 + 8] = b'\xff\x25' + struct.pack('<I', base + iats[ordinal]) + b'\x90\x90'
        rva = text_rva + i * 8 + 2
        relocation_pages.setdefault(rva & ~0xfff, []).append(0x3000 | (rva & 0xfff))
    reloc = bytearray()
    for page, entries in sorted(relocation_pages.items()):
        if len(entries) % 2:
            entries.append(0)
        reloc.extend(struct.pack('<II', page, 8 + len(entries) * 2))
        reloc.extend(struct.pack('<' + 'H' * len(entries), *entries))
    reloc_rva = align(data_rva + len(data), 0x1000)
    sections = [(b'.text', text_rva, code, 0x60000020),
                (b'.data', data_rva, data, 0xc0000040),
                (b'.reloc', reloc_rva, reloc, 0x42000040)]
    out = bytearray(0x200)
    out[:2] = b'MZ'
    struct.pack_into('<I', out, 0x3c, 0x80)
    out[0x80:0x84] = b'PE\0\0'
    struct.pack_into('<HHIIIHH', out, 0x84, 0x14c, 3, 0, 0, 0, 0xe0, 0x2102)
    opt = 0x98
    struct.pack_into('<H', out, opt, 0x10b)
    struct.pack_into('<III', out, opt + 4, align(len(code), 0x200),
                     align(len(data), 0x200) + align(len(reloc), 0x200), 0)
    struct.pack_into('<IIIIII', out, opt + 16, 0, text_rva, data_rva, base, 0x1000, 0x200)
    struct.pack_into('<HH', out, opt + 40, 6, 1)
    struct.pack_into('<HH', out, opt + 48, 6, 1)
    struct.pack_into('<II', out, opt + 56, align(reloc_rva + len(reloc), 0x1000), 0x200)
    struct.pack_into('<HH', out, opt + 68, 2, 0x100)  # GUI, NX compatible
    struct.pack_into('<IIIIII', out, opt + 72, 0x100000, 0x1000, 0x100000, 0x1000, 0, 16)
    for which, rva, size in [(0, data_rva, export_size), (1, imports, imports_size),
                             (5, reloc_rva, len(reloc))]:
        struct.pack_into('<II', out, opt + 96 + which * 8, rva, size)
    for i, (section_name, rva, content, flags) in enumerate(sections):
        at = opt + 0xe0 + i * 40
        out[at:at + 8] = section_name.ljust(8, b'\0')
        struct.pack_into('<IIII', out, at + 8, len(content), rva, align(len(content), 0x200), len(out))
        struct.pack_into('<I', out, at + 36, flags)
        out.extend(content)
        out.extend(bytes(align(len(out), 0x200) - len(out)))
    return bytes(out)


def prepare_adapters(directory, root):
    import pefile
    from shader_validator import prepare_component, NAME, EXPORT
    directory.mkdir(exist_ok=True)
    results = []
    for name in LIBRARIES:
        source = Path('C:/Windows/SysWOW64') / name
        original = source.read_bytes()
        pe = pefile.PE(data=original, fast_load=True)
        pe.parse_data_directories(directories=[0])
        symbols = [{'name': s.name.decode('ascii') if s.name else None,
                    'ordinal': s.ordinal} for s in pe.DIRECTORY_ENTRY_EXPORT.symbols]
        overrides = {EXPORT: NAME} if name == 'd3d9.dll' else {}
        adapter = build_adapter(name, symbols, overrides)
        # Reparse independently before publishing a loader input.
        parsed = pefile.PE(data=adapter)
        actual = [(s.name.decode('ascii') if s.name else None, s.ordinal)
                  for s in parsed.DIRECTORY_ENTRY_EXPORT.symbols]
        expected = [(s['name'], s['ordinal']) for s in symbols]
        assert sorted(actual, key=lambda x: (x[1], x[0] or '')) == sorted(expected, key=lambda x: (x[1], x[0] or ''))
        expected_libraries = {b'theseus-win32.dll'} | {s.encode() for s in overrides.values()}
        assert {d.dll for d in parsed.DIRECTORY_ENTRY_IMPORT} == expected_libraries
        for d in parsed.DIRECTORY_ENTRY_IMPORT:
            if d.dll == NAME.encode():
                assert [s.name for s in d.imports] == [EXPORT.encode()]
        assert parsed.OPTIONAL_HEADER.AddressOfEntryPoint == 0
        path = directory / name
        path.write_bytes(adapter)
        results.append({'url': 'platform/' + name, 'source': path.relative_to(root).as_posix(),
                        'vfsPath': 'c:\\windows\\system\\' + name, 'loadMode': 'required',
                        'size': len(adapter), 'sha256': hashlib.sha256(adapter).hexdigest(),
                        'provenance': 'reconstructed-wasm-export-adapter',
                        'metadataSource': str(source),
                        'metadataSourceSha256': hashlib.sha256(original).hexdigest(),
                        'exportCount': len(symbols)})
    results.append(prepare_component(directory, root))
    return results
