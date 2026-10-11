"""Native D3D9 StretchRect reference in a hidden test window; never runs the game."""
import ctypes as C
import hashlib
import json
from pathlib import Path

from inspect_texture_update import P, U, H, PP, Locked, method, check, release


class Rect(C.Structure):
    _fields_ = [(name, C.c_int32) for name in ['left', 'top', 'right', 'bottom']]


def main():
    user = C.WinDLL('user32')
    user.CreateWindowExW.argtypes = [U, C.c_wchar_p, C.c_wchar_p, U, C.c_int, C.c_int,
                                    C.c_int, C.c_int, P, P, P, P]
    user.CreateWindowExW.restype = P
    user.DestroyWindow.argtypes = [P]
    window = user.CreateWindowExW(0, 'STATIC', 'Theseus StretchRect reference', 0,
                                 0, 0, 16, 16, None, None, None, None)
    if not window:
        raise RuntimeError('Hidden reference window unavailable')
    dll = C.WinDLL('d3d9')
    dll.Direct3DCreate9.argtypes = [U]
    dll.Direct3DCreate9.restype = P
    root = dll.Direct3DCreate9(32)
    device = P()
    objects, cases = [], []
    try:
        pp = PP(width=16, height=16, format=22, count=1, swap=1, window=window,
                windowed=1, flags=1, interval=0x80000000)
        check(method(root, 16, H, U, U, P, U, C.POINTER(PP), C.POINTER(P))(
            root, 0, 1, window, 0x20, C.byref(pp), C.byref(device)))
        identifier = C.create_string_buffer(1104)
        check(method(root, 5, H, U, U, P)(root, 0, 0, identifier))
        adapter = {'driver': identifier.raw[:512].split(b'\0')[0].decode('ascii'),
                   'description': identifier.raw[512:1024].split(b'\0')[0].decode('ascii'),
                   'deviceName': identifier.raw[1024:1056].split(b'\0')[0].decode('ascii'),
                   'driverVersion': int.from_bytes(identifier.raw[1056:1064], 'little')}

        def surface(width, height, fmt=21, kind='target', pool=0):
            result = P()
            if kind == 'target':
                check(method(device, 28, H, U, U, U, U, U, U, C.POINTER(P), P)(
                    device, width, height, fmt, 0, 0, 1, C.byref(result), None))
            elif kind == 'texture':
                texture = P()
                check(method(device, 23, H, U, U, U, U, U, U, C.POINTER(P), P)(
                    device, width, height, 1, 1, fmt, pool, C.byref(texture), None))
                objects.append(texture)
                check(method(texture, 18, H, U, C.POINTER(P))(texture, 0, C.byref(result)))
            elif kind == 'backbuffer':
                check(method(device, 18, H, U, U, U, C.POINTER(P))(
                    device, 0, 0, 0, C.byref(result)))
            else:
                check(method(device, 36, H, U, U, U, U, C.POINTER(P), P)(
                    device, width, height, fmt, pool, C.byref(result), None))
            objects.append(result)
            return {'object': result, 'width': width, 'height': height,
                    'format': fmt, 'kind': kind, 'pool': pool}

        def write(s, pixels):
            if s['kind'] == 'texture':
                upload = surface(s['width'], s['height'], s['format'], 'offscreen', 2)
                write(upload, pixels)
                check(method(device, 30, H, P, P, P, P)(
                    device, upload['object'], None, s['object'], None))
                return
            locked = Locked()
            obj = s['object']
            check(method(obj, 13, H, C.POINTER(Locked), P, U)(obj, C.byref(locked), None, 0))
            for y in range(s['height']):
                for x in range(s['width']):
                    C.c_uint32.from_address(locked.bits + y * locked.pitch + x * 4).value = pixels[y * s['width'] + x]
            check(method(obj, 14, H)(obj))

        def read(s):
            if s['kind'] != 'offscreen':
                copy = surface(s['width'], s['height'], s['format'], 'offscreen', 2)
                check(method(device, 32, H, P, P)(device, s['object'], copy['object']))
                s = copy
            obj, locked = s['object'], Locked()
            check(method(obj, 13, H, C.POINTER(Locked), P, U)(obj, C.byref(locked), None, 16))
            pixels = [C.c_uint32.from_address(locked.bits + y * locked.pitch + x * 4).value
                      for y in range(s['height']) for x in range(s['width'])]
            check(method(obj, 14, H)(obj))
            return pixels

        def spec(s):
            return {k: v for k, v in s.items() if k != 'object'}

        def run(name, sw=4, sh=4, dw=4, dh=4, src_rect=None, dst_rect=None,
                filt=0, sf=21, df=21, sk='target', dk='target', sp=0, dp=0,
                same=False, lock=None, scene=False):
            s = surface(sw, sh, sf, sk, sp)
            d = s if same else surface(dw, dh, df, dk, dp)
            pixels = [((((x * 31 + y * 17 + 33) & 255) << 24) |
                       (((x * 47 + y * 23 + 11) & 255) << 16) |
                       (((x * 13 + y * 59 + 7) & 255) << 8) |
                       ((x * 71 + y * 37 + 19) & 255)) for y in range(sh) for x in range(sw)]
            before = [0x7f172b41] * (dw * dh)
            write(s, pixels)
            if not same:
                write(d, before)
            before = read(d)
            src = Rect(*src_rect) if src_rect is not None else None
            dst = Rect(*dst_rect) if dst_rect is not None else None
            locked = Locked()
            locked_object = s['object'] if lock == 'source' else d['object']
            if lock:
                check(method(locked_object, 13, H, C.POINTER(Locked), P, U)(
                    locked_object, C.byref(locked), None, 0))
            if scene:
                check(method(device, 41, H)(device))
            hr = method(device, 34, H, P, P, P, P, U)(device, s['object'],
                C.byref(src) if src is not None else None, d['object'],
                C.byref(dst) if dst is not None else None, filt) & 0xffffffff
            if scene:
                check(method(device, 42, H)(device))
            if lock:
                check(method(locked_object, 14, H)(locked_object))
            cases.append({'name': name, 'source': spec(s), 'destination': spec(d),
                'sourceRect': src_rect, 'destinationRect': dst_rect, 'filter': filt,
                'same': same, 'lock': lock, 'scene': scene, 'input': pixels,
                'before': before, 'hr': hr, 'pixels': read(d)})

        for filt in [0, 1, 2]:
            run(f'same-size-filter-{filt}', filt=filt)
            run(f'upscale-filter-{filt}', sw=2, sh=2, dw=5, dh=3, filt=filt)
            run(f'downscale-filter-{filt}', dw=3, dh=2, filt=filt)
            run(f'subrect-filter-{filt}', dw=6, dh=4, src_rect=[1, 1, 3, 3], dst_rect=[1, 0, 5, 3], filt=filt)
        run('linear-integer-upscale', sw=2, sh=2, dw=4, dh=4, filt=2)
        run('linear-odd-downscale', sw=5, sh=5, dw=2, dh=3, filt=2)
        for size in [1, 3, 4]:
            for filt in [1, 2]:
                run(f'upscale-{size}-to-5-filter-{filt}', sw=size, sh=size, dw=5, dh=5, filt=filt)
        run('linear-mixed-scale', sw=3, sh=5, dw=5, dh=2, filt=2)
        run('linear-offset-subrect', sw=6, sh=6, dw=7, dh=7,
            src_rect=[2, 2, 5, 5], dst_rect=[2, 2, 7, 7], filt=2)
        run('xrgb-to-argb', sf=22, filt=2)
        run('argb-to-xrgb', df=22, filt=2)
        run('xrgb-linear', sf=22, df=22, dw=3, dh=2, filt=2)
        run('backbuffer-to-texture', sw=16, sh=16, sf=22, sk='backbuffer', dk='texture', dw=7, dh=5, filt=2)
        run('texture-to-backbuffer', dw=16, dh=16, df=22, dk='backbuffer', sk='texture', filt=2)
        run('offscreen-source', sk='offscreen', dw=3, dh=2, filt=2)
        run('offscreen-destination', dk='offscreen')
        run('offscreen-stretch-destination', dk='offscreen', dw=3, dh=2, filt=2)
        run('offscreen-to-offscreen', sk='offscreen', dk='offscreen')
        run('offscreen-to-offscreen-stretch', sk='offscreen', dk='offscreen', dw=3, dh=2, filt=2)
        run('system-source', sk='offscreen', sp=2)
        run('system-destination', dk='offscreen', dp=2)
        run('same-surface', same=True)
        run('same-surface-disjoint', same=True, src_rect=[0, 0, 2, 2], dst_rect=[2, 2, 4, 4])
        run('locked-source', lock='source')
        run('locked-destination', lock='destination')
        run('inside-scene', scene=True, filt=2)
        for name, rect in [('negative', [-1, 0, 2, 2]), ('outside', [0, 0, 5, 4]),
                           ('empty', [1, 1, 1, 2]), ('inverted', [2, 1, 1, 2])]:
            run('source-' + name, src_rect=rect)
            run('destination-' + name, dst_rect=rect)
        for filt in [3, 4, 5, 6, 0xffffffff]:
            run(f'invalid-filter-{filt}', filt=filt)
    finally:
        for obj in reversed(objects):
            release(obj)
        if device.value:
            release(device)
        if root:
            release(root)
        user.DestroyWindow(window)
    dll_path = Path('C:/Windows/System32/d3d9.dll')
    report = {'scope': __doc__, 'pointerBits': C.sizeof(P) * 8, 'adapter': adapter,
              'sourceSha256': hashlib.sha256(dll_path.read_bytes()).hexdigest(),
              'scriptSha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'cases': cases}
    dest = Path(__file__).resolve().parent / 'reference/stretch-rect.json'
    dest.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'report': str(dest), 'cases': [
        {'name': row['name'], 'hr': f"{row['hr']:08x}"} for row in cases]}))


if __name__ == '__main__':
    main()
