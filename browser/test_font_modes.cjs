'use strict';
const fs = require('fs'), path = require('path'), assert = require('assert');
const runtime = path.resolve(__dirname, '../tools/wine-assembly');
const {bootRenderHarness} = require(path.join(runtime, 'test/render-helper'));
(async () => {
  const state = ['inst_control', 'pc', 'opcode', 'program', 'program_len', 'stack', 'stack_top',
    'point_count', 'real_count', 'rp0', 'rp1', 'rp2', 'zp0', 'zp1', 'zp2'];
  const shiftSeam = String.raw`
    (func (export "probe_zone_base") (param $zone i32) (result i32)
      (select (global.get $tth_points)
        (i32.add (global.get $tth_sc) (global.get $TTH_SC_TWILIGHT)) (local.get $zone)))
    (func (export "probe_shift") (param $op i32) (param $zone i32)
        (param $ref_zone i32) (param $diagonal i32) (result i32)
      (global.set $tth_error (i32.const 0))
      (global.set $tth_stack_top (i32.const 0))
      (global.set $tth_real_count (i32.const 3))
      (global.set $tth_point_count (i32.const 7))
      (i32.store offset=28 (global.get $tth_sc) (i32.const 3))
      (global.set $tth_zp0 (local.get $ref_zone))
      (global.set $tth_zp1 (local.get $ref_zone))
      (global.set $tth_rp1 (i32.const 1))
      (global.set $tth_rp2 (i32.const 2))
      (global.set $tth_pvx (i32.const 16384))
      (global.set $tth_pvy (i32.const 0))
      (global.set $tth_fvx (select (i32.const 11585) (i32.const 16384) (local.get $diagonal)))
      (global.set $tth_fvy (select (i32.const 11585) (i32.const 0) (local.get $diagonal)))
      (global.set $tth_opcode (local.get $op))
      (drop (call $tth_push (local.get $zone)))
      (call $tth_op_shift))`;
  const {exports: e, memory} = await bootRenderHarness({fonts: 'none', extraWat:
    state.map(name => `(func (export "probe_${name}") (result i32) (global.get $tth_${name}))`).join('\n') + shiftSeam});
  const wa = p => e.guest_to_wasm(p) >>> 0, alloc = n => e.guest_alloc(n) >>> 0;
  const compact = wa(alloc(512 * 6)), rows = [];
  for (const file of ['tahoma.ttf', 'blambotprol.ttf']) {
    const bytes = fs.readFileSync(path.resolve(__dirname, '../../client/data', file));
    const at = wa(alloc(bytes.length)); new Uint8Array(memory.buffer).set(bytes, at);
    for (const ppem of [7, 8, 9, 10, 11, 12, 16]) for (const char of ['H', 'g', 'W', 'S', '\u00e9']) {
      const gid = e.test_tt_glyph_index(at, bytes.length, char.charCodeAt(0));
      const count = e.test_tt_glyph_load_outline(at, bytes.length, gid, compact, 512);
      const results = [];
      for (const gray of [0, 1, 0, 1]) {
        const hinted = e.test_tth_hint_outline_mode(at, bytes.length, gid, ppem, compact, count, gray) >>> 0;
        if (!hinted) {
          const failure = {file, char, ppem, gray, count, error: e.test_tth_last_error(),
            phase: e.test_tth_last_phase(), state: Object.fromEntries(state.map(k => [k, e['probe_' + k]()]))};
          const dv = new DataView(memory.buffer), top = failure.state.stack_top;
          failure.stack = Array.from({length: Math.min(24, top)}, (_, i) => dv.getInt32(failure.state.stack + (top - i - 1) * 4, true));
          if (process.argv[2]) fs.writeFileSync(process.argv[2], JSON.stringify({rows, failure}, null, 2) + '\n');
          assert.fail(JSON.stringify(failure));
        }
        results.push({gray, control: e.probe_inst_control(), phase: e.test_tth_last_phase(),
          points: Array.from({length: count}, (_, i) => [e.test_tth_point_x(hinted, i), e.test_tth_point_y(hinted, i)]),
          advance: e.test_tth_last_advance()});
      }
      assert.deepEqual({...results[0], phase: 0}, {...results[2], phase: 0}, 'monochrome cache survives a grayscale request');
      assert.deepEqual({...results[1], phase: 0}, {...results[3], phase: 0}, 'grayscale cache survives a monochrome request');
      rows.push({file, char, ppem, count, mono: results[0], gray: results[1]});
    }
  }
  const h = rows.find(r => r.file === 'tahoma.ttf' && r.char === 'H' && r.ppem === 10);
  console.log(JSON.stringify({fontModeCases: rows.length, hintedTahomaH10: h.mono.control === 0}));
  if (process.argv[2]) fs.writeFileSync(process.argv[2], JSON.stringify({rows}, null, 2) + '\n');
  assert.equal(h.mono.control & 1, 0, 'original Tahoma enables hinting for one-bit output');
  const tiny = rows.find(r => r.file === 'tahoma.ttf' && r.char === 'H' && r.ppem === 7);
  assert.equal(tiny.mono.control & 1, 1, 'original Tahoma inhibits instructions at 7ppem');
  // Controlled prep isolates GETINFO from a font's own size thresholds. It
  // inhibits glyph instructions exactly when GETINFO reports grayscale.
  const font = fs.readFileSync(path.resolve(__dirname, '../../client/data/tahoma.ttf'));
  const at = wa(alloc(font.length)); new Uint8Array(memory.buffer).set(font, at);
  const tag = 0x70726570;
  const prep = e.test_tt_table_off(at, font.length, tag) >>> 0;
  const prepSize = e.test_tt_table_len(at, font.length, tag) >>> 0;
  const program = [0xb0, 0x20, 0x88, 0xb8, 0x10, 0x00, 0x54, 0xb0, 0x01, 0x8e];
  assert(prep && prepSize >= program.length);
  const data = new Uint8Array(memory.buffer);
  data.fill(0, at + prep, at + prep + prepSize); // SVTCA[y], no stack effect
  data.set(program, at + prep);
  const gid = e.test_tt_glyph_index(at, font.length, 72);
  const count = e.test_tt_glyph_load_outline(at, font.length, gid, compact, 512);
  for (const gray of [1, 0, 1, 0]) {
    assert(e.test_tth_hint_outline_mode(at, font.length, gid, 10, compact, count, gray));
    assert.equal(e.probe_inst_control() & 1, gray, 'GETINFO request mode and cached prep are isolated');
  }
  // Specification/reference invariants: both SHZ opcodes and zones, unchanged
  // reference/phantoms/touch flags, and projection different from freedom.
  const dv = new DataView(memory.buffer);
  let shiftCases = 0;
  for (const op of [0x36, 0x37]) for (const zone of [0, 1])
    for (const refZone of [0, 1]) for (const diagonal of [0, 1]) {
      const expected = [];
      const refIndex = op === 0x37 ? 1 : 2, distance = refIndex === 1 ? 64 : 96;
      for (const z of [0, 1]) for (let i = 0; i < 7; i++) {
        const point = e.probe_zone_base(z) + i * 28;
        const original = [i * 128, i * 192];
        const current = [original[0] + (z === refZone ? (i === 1 ? 64 : i === 2 ? 96 : 0) : 0), original[1]];
        const values = [...current, ...original, 3 | ((i & 3) << 2), 0, 0];
        values.forEach((v, field) => dv.setInt32(point + field * 4, v, true));
        if (z === zone && i < 3 && !(z === refZone && i === refIndex)) {
          values[0] += distance; values[1] += diagonal ? distance : 0;
        }
        expected.push({point, values});
      }
      assert.equal(e.probe_shift(op, zone, refZone, diagonal), 1);
      for (const {point, values} of expected)
        assert.deepEqual(values.map((_, field) => dv.getInt32(point + field * 4, true)), values,
          `SHZ ${op.toString(16)} target=${zone} reference=${refZone} diagonal=${diagonal}`);
      shiftCases++;
    }
  assert.equal(e.probe_shift(0x37, 2, 1, 0), 0, 'invalid zone is rejected');
  assert.equal(e.test_tth_last_error(), 4);
  console.log(`PASS original-font modes/cache/composites and ${shiftCases} SHZ zone/vector cases plus invalid zone`);
})().catch(error => {console.error(error); process.exitCode = 1;});
