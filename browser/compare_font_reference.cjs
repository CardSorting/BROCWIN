'use strict';
// Same canonical GDI path as the original client's recovered atlas builder.
const fs = require('fs'), path = require('path'), assert = require('assert');
const crypto = require('crypto');
const root = path.resolve(__dirname, '../..');
const runtime = path.join(root, 'theseus/tools/wine-assembly');
const {bootRenderHarness} = require(path.join(runtime, 'test/render-helper'));
const out = path.resolve(process.argv[2]);
const reference = JSON.parse(fs.readFileSync(path.join(out, 'font-reference.json')));
(async () => {
  const probes = [['SetTextColor', 2], ['SetBkColor', 2], ['TextOutW', 5],
    ['GetTextExtentPoint32W', 4], ['GetPixel', 3]];
  const extraWat = probes.map(([name, n]) =>
    `(func (export "probe_${name}") ${Array.from({length: n}, (_, i) => `(param $p${i} i32)`).join(' ')} (result i32)
      (call $handle_${name} ${Array.from({length: 5}, (_, i) => i < n ? `(local.get $p${i})` : '(i32.const 0)').join(' ')} (i32.const 0))
      (i32.load (global.get $reg_base)))`).join('\n');
  const {exports: e, memory, hostCtx} = await bootRenderHarness({fonts: 'all', extraWat});
  const bytes = new Uint8Array(memory.buffer), wa = p => e.guest_to_wasm(p) >>> 0;
  const alloc = n => e.guest_alloc(n) >>> 0;
  const put = (s, wide = false) => {
    const b = Buffer.from(s + '\0', wide ? 'utf16le' : 'latin1'), p = alloc(b.length);
    bytes.set(b, wa(p)); return p;
  };
  hostCtx.vfs.dirs.add('c:\\joysword'); hostCtx.vfs.setCurrentDirectory('c:\\joysword');
  for (const input of reference.inputs) {
    const data = fs.readFileSync(path.join(root, 'client/data', input.file));
    assert.equal(crypto.createHash('sha256').update(data).digest('hex'), input.originalSha256);
    hostCtx.vfs.files.set('c:\\joysword\\' + input.file, {data: new Uint8Array(data), attrs: 32});
    assert.equal(e.test_call_AddFontResourceA(put(input.file)), 1);
  }
  const screen = e.test_call_GetDC(0) >>> 0, dc = e.test_call_CreateCompatibleDC(0) >>> 0;
  const bm = e.test_call_CreateCompatibleBitmap(screen, 129, 129) >>> 0;
  assert(bm);
  const oldbm = e.test_call_SelectObject(dc, bm), extent = alloc(8), rows = [];
  for (const c of reference.cases) {
    const font = e.test_call_CreateFontW(c.height, 0, 0, 0, c.weight, 0, 0, 0, 1, 0, 0,
      c.quality, 0, put(c.family, true)) >>> 0;
    assert(font);
    const old = e.test_call_SelectObject(dc, font);
    e.probe_SetTextColor(dc, 255); e.probe_SetBkColor(dc, 0);
    // Opaque space clears a rectangle larger than every measured glyph.
    const blank = put('                    ', true);
    assert.equal(e.probe_TextOutW(dc, 0, 0, blank, 20), 1);
    const text = put(c.character, true);
    assert.equal(e.probe_GetTextExtentPoint32W(dc, text, 1, extent), 1);
    assert.equal(e.probe_TextOutW(dc, 0, 0, text, 1), 1);
    const measured = [e.guest_read32(extent) >>> 0, e.guest_read32(extent + 4) >>> 0];
    const w = Math.min(measured[0], c.height), h = Math.min(measured[1], c.height);
    const pixels = Buffer.alloc(w * h);
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++)
      pixels[y * w + x] = e.probe_GetPixel(dc, x, y) & 255;
    rows.push({font: c.font, character: c.character, height: c.height, quality: c.quality,
      extent: measured, nativeExtent: c.extent, size: [w, h],
      pixels: pixels.toString('base64'),
      extentEqual: JSON.stringify(measured) === JSON.stringify(c.extent),
      pixelsEqual: JSON.stringify([w, h]) === JSON.stringify(c.size) &&
        pixels.equals(Buffer.from(c.pixels, 'base64'))});
    e.test_call_SelectObject(dc, old); e.test_call_DeleteObject(font);
  }
  e.test_call_SelectObject(dc, oldbm); e.test_call_DeleteObject(bm); e.test_call_DeleteDC(dc);
  const groups = [];
  for (const font of reference.inputs.map(x => x.file)) for (const quality of [3, 4]) {
    const cases = rows.filter(r => r.font === font && r.quality === quality);
    groups.push({font, quality, cases: cases.length, extentMatches: cases.filter(r => r.extentEqual).length,
      pixelMatches: cases.filter(r => r.pixelsEqual).length});
  }
  fs.writeFileSync(path.join(out, 'font-wasm.json'), JSON.stringify({
    scope: 'Original unmodified font bytes in canonical Wasm GDI compared to native name-only aliases with verified glyph/metric/hint tables. Local reference, not full text parity.',
    groups, cases: rows}, null, 2) + '\n');
  console.log(JSON.stringify({groups}));
})().catch(error => {console.error(error); process.exitCode = 1;});
