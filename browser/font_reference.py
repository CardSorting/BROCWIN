"""Measure local GDI using a uniquely named diagnostic copy of each original font.

Only the name table and SFNT checksums change. Original game files are untouched.
Selected bytes and every unchanged table are checked before measuring any glyph.
The aliases are test inputs, never mounted in the browser application.
"""
import argparse
import base64
import ctypes as C
import hashlib
import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def tables(data):
    return {tag.decode('ascii'): (slot, off, size)
            for slot in range(12, 12 + struct.unpack_from('>H', data, 4)[0] * 16, 16)
            for tag, _, off, size in [struct.unpack_from('>4sIII', data, slot)]}


def checksum(data):
    data = data + bytes((-len(data)) % 4)
    return sum(struct.unpack('>' + 'I' * (len(data) // 4), data)) & 0xffffffff


def diagnostic_alias(source, before, after):
    assert len(before) == len(after)
    result = bytearray(source)
    entries = tables(source)
    _, off, size = entries['name']
    names = bytes(result[off:off + size])
    for encoding in ('ascii', 'utf-16-be'):
        names = names.replace(before.encode(encoding), after.encode(encoding))
    assert names != source[off:off + size]
    result[off:off + size] = names
    head = entries['head'][1]
    struct.pack_into('>I', result, head + 8, 0)
    for tag in ('head', 'name'):
        slot, off, size = entries[tag]
        struct.pack_into('>I', result, slot + 4, checksum(bytes(result[off:off + size])))
    struct.pack_into('>I', result, head + 8, (0xb1b0afba - checksum(bytes(result))) & 0xffffffff)
    unchanged = {}
    for tag, (_, off, size) in entries.items():
        if tag in ('head', 'name'):
            continue
        assert result[off:off + size] == source[off:off + size], tag
        unchanged[tag] = hashlib.sha256(source[off:off + size]).hexdigest()
    return bytes(result), unchanged


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    gdi, user = C.WinDLL('gdi32'), C.WinDLL('user32')
    P, I, U = C.c_void_p, C.c_int32, C.c_uint32

    def api(name, types, result):
        fn = getattr(gdi, name)
        fn.argtypes, fn.restype = types, result
        return fn

    add = api('AddFontResourceExW', [C.c_wchar_p, U, P], I)
    remove = api('RemoveFontResourceExW', [C.c_wchar_p, U, P], I)
    dcnew = api('CreateCompatibleDC', [P], P)
    bitmapnew = api('CreateCompatibleBitmap', [P, I, I], P)
    select = api('SelectObject', [P, P], P)
    delete = api('DeleteObject', [P], I)
    deletedc = api('DeleteDC', [P], I)
    fontnew = api('CreateFontW', [I, I, I, I, I, U, U, U, U, U, U, U, U, C.c_wchar_p], P)
    fontdata = api('GetFontData', [P, U, U, P, U], U)
    textout = api('TextOutW', [P, I, I, C.c_wchar_p, I], I)
    pixel = api('GetPixel', [P, I, I], U)
    extent = api('GetTextExtentPoint32W', [P, C.c_wchar_p, I, P], I)
    metrics = api('GetTextMetricsW', [P, P], I)
    color = api('SetTextColor', [P, U], U)
    background = api('SetBkColor', [P, U], U)
    clear = api('PatBlt', [P, I, I, I, I, U], I)
    user.GetDC.argtypes, user.GetDC.restype = [P], P
    user.ReleaseDC.argtypes = [P, P]
    screen = user.GetDC(None)
    dc = dcnew(None)
    bitmap = bitmapnew(screen, 129, 129)
    assert bitmap
    old_bitmap = select(dc, bitmap)
    rows, inputs = [], []
    try:
        for file, family, alias in [('tahoma.ttf', 'Tahoma', 'ThsM01'),
                                    ('blambotprol.ttf', 'Blambot Pro Lite', 'ThsM002 Pro Lite')]:
            source = (ROOT / 'client/data' / file).read_bytes()
            derived, unchanged = diagnostic_alias(source, family.split()[0], alias.split()[0])
            path = args.out / ('diagnostic-' + file)
            path.write_bytes(derived)
            expected = hashlib.sha256(derived).hexdigest()
            inputs.append({'file': file, 'family': family, 'alias': alias,
                           'originalSha256': hashlib.sha256(source).hexdigest(),
                           'diagnosticSha256': expected, 'unchangedTables': unchanged})
            assert add(str(path.resolve()), 16, None)
            try:
                for quality in (3, 4):
                    for height in (9, 10, 11, 12, 16):
                        font = fontnew(height, 0, 0, 0, 500, 0, 0, 0, 1, 0, 0, quality, 0, alias)
                        assert font
                        old = select(dc, font)
                        try:
                            size = fontdata(dc, 0, 0, None, 0)
                            assert size != 0xffffffff
                            selected = (C.c_ubyte * size)()
                            assert fontdata(dc, 0, 0, selected, size) == size
                            actual = hashlib.sha256(bytes(selected)).hexdigest()
                            assert actual == expected, (file, height, quality, actual, expected)
                            tm = (C.c_ubyte * 60)()
                            assert metrics(dc, tm)
                            text_metrics = dict(zip(('height', 'ascent', 'descent', 'internalLeading',
                                                      'externalLeading', 'averageWidth', 'maximumWidth', 'weight'),
                                                     struct.unpack_from('<8i', tm)))
                            color(dc, 255)
                            background(dc, 0)
                            for char in 'HgpyW8':
                                dimensions = (I * 2)()
                                assert clear(dc, 0, 0, 129, 129, 0x42)
                                assert extent(dc, char, 1, dimensions)
                                assert textout(dc, 0, 0, char, 1)
                                w, h = min(dimensions[0], height), min(dimensions[1], height)
                                pixels = bytes(pixel(dc, x, y) & 255 for y in range(h) for x in range(w))
                                rows.append({'font': file, 'family': family, 'height': height,
                                             'weight': 500, 'quality': quality, 'character': char,
                                             'selectedSha256': actual, 'extent': list(dimensions),
                                             'textMetrics': text_metrics,
                                             'size': [w, h], 'pixels': base64.b64encode(pixels).decode()})
                        finally:
                            select(dc, old)
                            delete(font)
            finally:
                remove(str(path.resolve()), 16, None)
    finally:
        select(dc, old_bitmap)
        delete(bitmap)
        deletedc(dc)
        user.ReleaseDC(None, screen)
    report = {'scope': __doc__, 'inputs': inputs, 'cases': rows}
    (args.out / 'font-reference.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'cases': len(rows), 'selectedFontIdentityVerified': True,
                      'output': str(args.out / 'font-reference.json')}))


if __name__ == '__main__':
    main()
