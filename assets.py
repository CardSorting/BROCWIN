"""Recover existing KOM assets, retaining archive identity and original bytes.

Uses the inherited KOM checksum/XOR implementation. Does not patch game files.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path, PureWindowsPath
import struct
import sys
import xml.etree.ElementTree as ET
import zlib

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'client' / 'data'
OUTPUT = ROOT / 'theseus' / 'recovered'
MAX_ENTRY = 256 * 1024 * 1024
MAX_TABLE = 32 * 1024 * 1024


def inherited_kom():
    spec = importlib.util.spec_from_file_location('theseus_inherited_kom', ROOT / 'scripts' / 'patch-client-kom.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def safe_name(name):
    path = PureWindowsPath(name)
    if not name or path.is_absolute() or path.drive or path.root:
        raise ValueError(f'Unsafe asset name: {name!r}')
    if any(part in ('.', '..') or part.endswith((' ', '.')) or
           any(char in part for char in ':<>"|?*') or PureWindowsPath(part).is_reserved()
           for part in path.parts):
        raise ValueError(f'Unsafe asset name: {name!r}')
    return Path(*path.parts)


def category(name):
    ext = PureWindowsPath(name).suffix.lower()
    if ext in ('.dds', '.tga', '.png', '.bmp', '.jpg', '.jpeg'): return 'textures'
    if ext in ('.x', '.mesh', '.nif'): return 'models'
    if ext in ('.wav', '.ogg', '.mp3', '.wma'): return 'audio'
    if ext in ('.lua', '.luac'): return 'scripts'
    if ext in ('.fx', '.vsh', '.psh'): return 'shaders'
    if ext in ('.ttf', '.otf'): return 'fonts'
    return 'other'


def archive_entries(path):
    with path.open('rb') as stream:
        head = stream.read(4096)
        start = head.find(b'<?xml')
        if start < 4:
            raise ValueError('KOM XML header not found')
        size = struct.unpack('<I', head[start - 4:start])[0]
        if not 0 < size <= MAX_TABLE:
            raise ValueError(f'Invalid XML table length: {size}')
        stream.seek(start)
        table = stream.read(size)
        if len(table) != size:
            raise ValueError('Truncated XML table')
        root = ET.fromstring(table)
        if root.tag != 'Files':
            raise ValueError('Unexpected archive table')
        seen = set()
        for entry in root:
            attrs = entry.attrib
            name = attrs['Name']
            safe_name(name)
            key = str(PureWindowsPath(name)).casefold()
            if key in seen:
                raise ValueError(f'Duplicate asset name: {name}')
            seen.add(key)
            size = int(attrs['Size'])
            compressed_size = int(attrs['CompressedSize'])
            if not 0 <= size <= MAX_ENTRY or not 0 < compressed_size <= MAX_ENTRY:
                raise ValueError(f'Asset exceeds recovery limit: {name}')
            offset = stream.tell()
            compressed = stream.read(compressed_size)
            if len(compressed) != compressed_size:
                raise ValueError(f'Truncated asset: {name}')
            decoder = zlib.decompressobj()
            payload = decoder.decompress(compressed, size + 1)
            if len(payload) != size or not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
                raise ValueError(f'Invalid asset compression/size: {name}')
            yield attrs, offset, compressed, payload
        if stream.read(1):
            raise ValueError('Unexpected bytes after archive entries')


def write_recovered(relative, payload):
    target = OUTPUT / relative
    if not target.resolve().is_relative_to(OUTPUT.resolve()) or not OUTPUT.resolve().is_relative_to(ROOT):
        raise ValueError('Recovery path escapes workspace')
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if digest(target) != hashlib.sha256(payload).hexdigest():
            raise ValueError(f'Refusing to overwrite modified recovered asset: {relative}')
    else:
        with target.open('xb') as stream:
            stream.write(payload)


def recover(extract=False):
    kom = inherited_kom()
    report = {'format': 1, 'source': 'client/data', 'extracted': extract,
              'archives': [], 'assets': [], 'errors': []}
    counts = Counter()
    for archive in sorted(DATA.glob('*.kom')):
        archive_info = {'path': archive.relative_to(ROOT).as_posix(), 'sha256': digest(archive), 'entries': 0}
        report['archives'].append(archive_info)
        try:
            for attrs, offset, compressed, payload in archive_entries(archive):
                checksum_key = kom.checksum_attr_name(attrs)
                recorded = attrs.get(checksum_key, '').lower()
                algorithms = [kind for kind in ('crc32', 'adler32') if kom.checksum_value(compressed, kind).lower() == recorded]
                group = category(attrs['Name'])
                relative = Path(group) / archive.stem / safe_name(attrs['Name'])
                row = {'archive': archive.name, 'name': attrs['Name'], 'category': group,
                       'offset': offset, 'size': len(payload), 'compressedSize': len(compressed),
                       'sha256': hashlib.sha256(payload).hexdigest(), 'metadata': attrs,
                       'checksumMatches': algorithms, 'recoveredPath': relative.as_posix()}
                if not algorithms:
                    report['errors'].append({'archive': archive.name, 'entry': attrs['Name'], 'error': 'Unrecognized or mismatched legacy checksum'})
                if extract:
                    write_recovered(relative, payload)
                if group == 'scripts':
                    decoded = kom.xor_payload(payload)
                    if decoded.startswith(b'\x1bLua'):
                        row['encoding'] = 'legacy-xor-lua-bytecode'
                        row['decodedSha256'] = hashlib.sha256(decoded).hexdigest()
                        if extract:
                            write_recovered(Path('decoded') / archive.stem / safe_name(attrs['Name'] + '.luac'), decoded)
                report['assets'].append(row)
                counts[group] += 1
                archive_info['entries'] += 1
        except (ValueError, KeyError, OSError, ET.ParseError, zlib.error) as error:
            report['errors'].append({'archive': archive.name, 'error': str(error)})
        print(f'{archive.name}: {archive_info["entries"]} entries', flush=True)
    report['counts'] = dict(counts)
    if not report['archives']:
        report['errors'].append({'error': 'No KOM archives found'})
    output = ROOT / 'theseus' / 'asset-catalog.json'
    output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'archives': len(report['archives']), 'assets': len(report['assets']),
                      'counts': counts, 'errors': len(report['errors']), 'catalog': str(output)}))
    return 1 if report['errors'] else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--extract', action='store_true', help='Recover original assets alongside the catalog')
    args = parser.parse_args()
    return recover(args.extract)


if __name__ == '__main__':
    raise SystemExit(main())
