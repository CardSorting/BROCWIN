'use strict';
// Original font bytes through the same GDI entry points used by the game atlas.
const fs = require('node:fs'), path = require('node:path');
const assert = require('node:assert/strict'), crypto = require('node:crypto');
const root = path.resolve(__dirname, '../..');
const runtime = path.join(root, 'theseus/tools/wine-assembly');
const {bootRenderHarness} = require(path.join(runtime, 'test/render-helper'));
const reference = JSON.parse(fs.readFileSync(path.join(__dirname, 'reference/font-cells.json')));

(async () => {
  const apis = [['SetTextColor', 2], ['SetBkColor', 2], ['TextOutW', 5],
    ['GetTextExtentPoint32W', 4], ['GetTextMetricsW', 2], ['GetPixel', 3]];
  const extraWat = apis.map(([name, n]) => {
    return `(func (export "probe_${name}") ${Array.from({length: n}, (_, i) => `(param $p${i} i32)`).join(' ')} (result i32)
      (call $handle_${name} ${Array.from({length: 5}, (_, i) => i < n ? `(local.get $p${i})` : '(i32.const 0)').join(' ')} (i32.const 0))
      (i32.load (global.get $reg_base)))`;
  }).join('\n') + `
    (func (export "probe_hdmx") (param $d i32) (param $s i32) (param $g i32)
      (param $p i32) (result i32)
      (call $tt_hdmx_advance (local.get $d) (local.get $s) (local.get $g) (local.get $p)))`;
  const {exports: e, memory, hostCtx} = await bootRenderHarness({fonts: 'all', extraWat});
  e.set_winver(0x1db10106);
  const bytes = new Uint8Array(memory.buffer), wa = p => e.guest_to_wasm(p) >>> 0;
  const alloc = n => e.guest_alloc(n) >>> 0;
  const put = (s, wide = false) => {
    const b = Buffer.from(s + '\0', wide ? 'utf16le' : 'latin1'), p = alloc(b.length);
    bytes.set(b, wa(p)); return p;
  };
  // Malformed device metrics must fall back without reading another table.
  const source = fs.readFileSync(path.join(root, 'client/data/blambotprol.ttf'));
  const ptr = wa(alloc(source.length)); bytes.set(source, ptr);
  const tag = 0x68646d78, table = e.test_tt_table_off(ptr, source.length, tag) >>> 0;
  const gid = e.test_tt_glyph_index(ptr, source.length, 87);
  assert.equal(e.probe_hdmx(ptr, source.length, gid, 9), 8);
  let slot;
  for (let i = 12; i < 12 + source.readUInt16BE(4) * 16; i += 16)
    if (source.readUInt32BE(i) === tag) slot = i;
  assert(slot);
  const invalid = [
    {name: 'absent ppem', gid, ppem: 7}, {name: 'invalid glyph', gid: -1, ppem: 9},
    {name: 'version', edit: b => b.writeUInt16BE(1, table)},
    {name: 'zero stride', edit: b => b.writeUInt32BE(0, table + 4)},
    {name: 'short stride', edit: b => b.writeUInt32BE(2, table + 4)},
    {name: 'overflow stride', edit: b => b.writeUInt32BE(0xffffffff, table + 4)},
    {name: 'excess records', edit: b => b.writeUInt16BE(65535, table + 2)},
    {name: 'short header', edit: b => b.writeUInt32BE(7, slot + 12)},
    {name: 'out of file', edit: b => b.writeUInt32BE(source.length - 1, slot + 8)},
  ];
  for (const c of invalid) {
    const b = Buffer.from(source); c.edit?.(b); bytes.set(b, ptr);
    assert.equal(e.probe_hdmx(ptr, b.length, c.gid ?? gid, c.ppem ?? 9) >>> 0,
      0x80000000, c.name);
  }
  hostCtx.vfs.dirs.add('c:\\joysword'); hostCtx.vfs.setCurrentDirectory('c:\\joysword');
  for (const input of reference.inputs) {
    const b = fs.readFileSync(path.join(root, 'client/data', input.file));
    assert.equal(crypto.createHash('sha256').update(b).digest('hex'), input.originalSha256);
    hostCtx.vfs.files.set('c:\\joysword\\' + input.file, {data: new Uint8Array(b), attrs: 32});
    assert.equal(e.test_call_AddFontResourceA(put(input.file)), 1);
  }
  const screen = e.test_call_GetDC(0) >>> 0, dc = e.test_call_CreateCompatibleDC(0) >>> 0;
  const bm = e.test_call_CreateCompatibleBitmap(screen, 129, 129) >>> 0;
  const oldbm = e.test_call_SelectObject(dc, bm), extent = alloc(8), metrics = alloc(60);
  const blank = put('                    ', true), results = [];
  // Revisit positive cells after their equal-ppem negative counterparts.
  const cases = [...reference.cases, ...reference.cases.filter(c => c.height === 9 || c.height === 12)];
  for (const c of cases) {
    const label = `${c.font} ${c.height} ${JSON.stringify(c.character)}`;
    const font = e.test_call_CreateFontW(c.height, 0, 0, 0, c.weight, 0, 0, 0,
      1, 0, 0, c.quality, 0, put(c.family, true)) >>> 0;
    assert(font, label);
    const old = e.test_call_SelectObject(dc, font);
    e.probe_SetTextColor(dc, 255); e.probe_SetBkColor(dc, 0);
    // Clear the complete sampled cell, including the rows below short fonts.
    for (let y = 0; y < 24; y += 4) assert.equal(e.probe_TextOutW(dc, 0, y, blank, 20), 1);
    const text = put(c.character, true);
    assert.equal(e.probe_GetTextExtentPoint32W(dc, text, 1, extent), 1);
    assert.equal(e.probe_GetTextMetricsW(dc, metrics), 1);
    const actualExtent = [e.guest_read32(extent) >>> 0, e.guest_read32(extent + 4) >>> 0];
    assert.deepEqual(actualExtent, c.extent, label + ' extent');
    for (const [i, key] of ['height', 'ascent', 'descent', 'internalLeading'].entries())
      assert.equal(e.guest_read32(metrics + i * 4) | 0, c.textMetrics[key], label + ' ' + key);
    assert.equal(e.probe_TextOutW(dc, 0, 0, text, 1), 1);
    const pixels = Buffer.alloc(24 * 24);
    for (let y = 0; y < 24; y++) for (let x = 0; x < 24; x++)
      pixels[y * 24 + x] = e.probe_GetPixel(dc, x, y) & 255;
    const pixelsEqual = pixels.equals(Buffer.from(c.pixels, 'base64'));
    const exact = (c.font === 'tahoma.ttf' && c.height === 9 && c.character === 'H') ||
      (c.font === 'blambotprol.ttf' && ((c.height === 9 && c.character === ';') ||
        (c.height === 10 && c.character === 'R')));
    if (exact) assert(pixelsEqual, label + ' native terminal-cap/tangent bitmap');
    results.push({font: c.font, height: c.height, character: c.character, pixelsEqual});
    e.test_call_SelectObject(dc, old); e.test_call_DeleteObject(font);
  }
  e.test_call_SelectObject(dc, oldbm); e.test_call_DeleteObject(bm); e.test_call_DeleteDC(dc);
  const report = {cases: results.length, malformedHdmxCases: invalid.length,
    nativeExtentsAndCellMetrics: 'pass',
    nativePixelMatches: results.filter(r => r.pixelsEqual).length,
    remainingPixelMismatches: results.filter(r => !r.pixelsEqual),
    scope: 'NT cell/advance and measured monochrome stub correction; full raster and antialiasing parity remain unverified'};
  if (process.argv[2]) fs.writeFileSync(process.argv[2], JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify(report));
})().catch(error => {console.error(error); process.exitCode = 1;});
