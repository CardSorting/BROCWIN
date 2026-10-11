'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const runtime = path.resolve(__dirname, '../tools/wine-assembly');
const { bootRenderHarness } = require(path.join(runtime, 'test/render-helper'));
const { loadDll, _test: { findDllExport } } = require(path.join(runtime, 'lib/dll-loader'));

const extraWat = String.raw`
  (func (export "test_fonts_init")
    (global.set $image_base (i32.const 0x00400000))
    (global.set $exe_size_of_image (i32.const 0x00200000))
    (global.set $thunk_guest_base
      (i32.add (i32.sub (global.get $THUNK_BASE) (global.get $GUEST_BASE)) (global.get $image_base)))
    (call $heap_init (i32.const 0x01000000)))
`;

(async () => {
  let expectedUnsupported = false, observedUnsupported = false;
  const { exports: e, memory, hostCtx } = await bootRenderHarness({ extraWat, fonts: 'all',
    extraHostOverrides: { crash_unimplemented: () => {
      assert.ok(expectedUnsupported, 'unexpected unsupported API');
      observedUnsupported = true;
    } },
  });
  e.test_fonts_init();
  e.set_api_log(0);
  const text = e.guest_alloc(2048) >>> 0;
  const stack = e.guest_alloc(1024) >>> 0;
  const bytes = new Uint8Array(memory.buffer);
  const wa = at => e.guest_to_wasm(at) >>> 0;
  const put = (value, wide) => {
    bytes.set(Buffer.from(value + '\0', wide ? 'utf16le' : 'latin1'), wa(text));
    return text;
  };
  const readA = at => {
    let end = at;
    while (bytes[end]) end++;
    return Buffer.from(bytes.subarray(at, end)).toString('latin1');
  };
  const gdi = loadDll(e, memory.buffer, fs.readFileSync(path.join(__dirname, 'generated/platform/gdi32.dll')),
    'C:\\WINDOWS\\SYSTEM\\gdi32.dll');
  const call = (api, value) => {
    const address = findDllExport(e, memory.buffer, gdi.loadAddr, api);
    assert.ok(address, api);
    const sp = stack + 512;
    e.guest_write32(sp, 0);
    e.guest_write32(sp + 4, value === null ? 0 : put(value, api.endsWith('W')));
    e.set_esp(sp);
    e.set_eip(address);
    e.run(1000000);
    assert.equal(e.get_eip(), 0, api + ' returns through its x86 caller');
    assert.equal(e.get_esp(), sp + 8, api + ' cleans one stdcall argument');
    return e.get_eax() | 0;
  };
  const registered = family => {
    put(family, false);
    const out = e.test_tt_reg_path(wa(text), 400, 0) >>> 0;
    return out ? readA(out) : null;
  };
  const dc = e.test_call_CreateCompatibleDC(0) >>> 0;
  const metrics = e.guest_alloc(64) >>> 0;
  const measuredHeight = (family, height) => {
    const font = e.test_call_CreateFontW(height, 0, 0, 0, 500, 0, 0, 0,
      1, 0, 0, 4, 0, put(family, true)) >>> 0;
    assert.ok(font);
    const old = e.test_call_SelectObject(dc, font) >>> 0;
    assert.equal(e.test_call_GetTextMetricsA(dc, metrics), 1);
    const value = e.guest_read32(metrics) >>> 0;
    e.test_call_SelectObject(dc, old);
    e.test_call_DeleteObject(font);
    return value;
  };
  assert.equal(measuredHeight('Tahoma', 9), 13, 'control: bundled bitmap alias without registration');
  hostCtx.vfs.dirs.add('c:\\joysword');
  hostCtx.vfs.setCurrentDirectory('c:\\joysword');
  for (const [file, family] of [['tahoma.ttf', 'Tahoma'], ['blambotprol.ttf', 'Blambot Pro Lite']]) {
    const data = fs.readFileSync(path.resolve(__dirname, '../../client/data', file));
    hostCtx.vfs.files.set('c:\\joysword\\' + file, { data: new Uint8Array(data), attrs: 0x20 });
    assert.equal(call('AddFontResourceW', file), 1, file + ' registers from the original bytes');
    assert.equal(registered(family), file, 'family comes from the original font name table');
    const face = e.test_tt_face_open(put(file, false));
    assert.ok(face >= 0);
    assert.equal(e.test_tt_face_size(face), data.length, 'font data is retained by the renderer');
    assert.ok(e.test_tt_face_char_width(face, 'A'.charCodeAt(0), 16) > 0, 'real glyph metrics are available');
    for (const height of [9, 10, 11, 12]) {
      // Native original-font TextOut/GetTextExtent sequence: all four cell
      // heights equal the positive LOGFONT request (font-atlas-native-small).
      assert.equal(measuredHeight(family, height), height,
        `${family} ${height}px registered face outranks the bundled bitmap alias`);
    }
    assert.equal(call('AddFontResourceA', file), 1, 'A and W share the registration');
    assert.equal(call('RemoveFontResourceW', file), 1);
    assert.equal(registered(family), file, 'one add remains');
    assert.equal(call('RemoveFontResourceA', file), 1);
    assert.equal(registered(family), null, 'last remove retires registration');
    assert.equal(call('RemoveFontResourceW', file), 0, 'unregistered removal fails');
  }
  assert.equal(measuredHeight('Tahoma', 9), 13, 'last removal restores the bundled alias');
  e.test_call_DeleteDC(dc);
  const original = hostCtx.vfs.files.get('c:\\joysword\\tahoma.ttf');
  hostCtx.vfs.files.set('c:\\joysword\\caf\u00e9.ttf', original);
  assert.equal(call('AddFontResourceW', 'caf\u00e9.ttf'), 1, 'lossless non-ASCII byte-range path');
  assert.equal(registered('Tahoma'), 'caf\u00e9.ttf');
  assert.equal(call('RemoveFontResourceW', 'caf\u00e9.ttf'), 1);
  hostCtx.vfs.files.set('c:\\joysword\\invalid.ttf', { data: new Uint8Array([1, 2, 3]), attrs: 0x20 });
  for (const value of [null, '', 'missing.ttf', 'invalid.ttf']) {
    assert.equal(call('AddFontResourceW', value), 0, 'does not fabricate a font: ' + value);
  }
  expectedUnsupported = true;
  assert.throws(() => call('AddFontResourceW', '\uac00.ttf'), WebAssembly.RuntimeError,
    'unsupported wider paths stop explicitly instead of truncating the filename');
  assert.equal(observedUnsupported, true);
  console.log('PASS original Tahoma/Blambot data, small-font metrics with actual bundled fonts, A/W registration lifetime and explicit path limits');
})().catch(error => { console.error(error); process.exitCode = 1; });
