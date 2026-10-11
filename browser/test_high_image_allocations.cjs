'use strict';

// The original X2 image is based at0x32830000. Repeated dungeon loading let
// downward sparse reservations enter its direct affine window and guest writes
// hit runtime-private HEAP_ARENAS. Exercise the shipped module, not a JS model.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const runtime = path.resolve(__dirname, '../tools/wine-assembly');
const R = require(path.join(runtime, 'lib/region-map.generated'));
const sigs = require(path.join(runtime, 'lib/host-import-sigs.generated.json')).sigs;
const modulePath = path.resolve(process.argv[2] || path.join(runtime, 'build/wine-assembly.wasm'));

(async () => {
  const module = await WebAssembly.compile(fs.readFileSync(modulePath));
  const rows = [], failures = [];
  for (const imageBase of [0x00400000, 0x10000000, 0x32830000]) {
    for (const route of ['view', 'section', 'heap']) {
      const memory = new WebAssembly.Memory({initial:8192, maximum:8192, shared:true});
      const host = {memory};
      for (const [name, sig] of Object.entries(sigs)) host[name] = sig.results?.length ? () => 0 : () => {};
      const e = (await WebAssembly.instantiate(module, {host})).exports;
      e.init_thread(0, imageBase, 0, 0, 0, 0, 0);
      e.heap_init(imageBase + 0x02000000);
      const dv = new DataView(memory.buffer);
      const low = imageBase - R.BASE.GUEST_BASE;
      // DIRECT_WINDOW ends at the pinned sparse backing start; the generated
      // JS mirror contains allocated regions, not region.span declarations.
      const directEnd = R.BASE.VIRTUAL_BACKING_BASE;
      const high = low + directEnd;
      const alias = low + R.BASE.HEAP_ARENAS;
      const size = 0x200000;
      const top = (Math.ceil(alias / 65536) * 65536 + 0x100000) >>> 0;
      // Same internal cursor boundary as repeated-area loading, without an
      // hour-long replay or a large synthetic heap. Pending ownership is real.
      dv.setUint32(R.BASE.VIRTUAL_MAP_STATE + 8, top, true);
      const p = (route === 'view' ? e.guest_map_alloc(size) :
        route === 'section' ? e.guest_section_reserve(size) : e.guest_alloc(size)) >>> 0;
      const overlap = p < high && p + size > Math.max(0, low);
      const before = dv.getUint32(R.BASE.HEAP_ARENAS, true);
      // A byte inside the returned allocation must never name an allocator
      // record. Retain the exact float1.0 symptom on the defective control.
      const target = p <= alias && alias + 4 <= p + size ? alias : p + 0x10000;
      let translated = null, after = before;
      if (p && route !== 'section') {
        translated = e.guest_to_wasm(target) >>> 0;
        e.guest_write32(target, 0x3f800000);
        after = dv.getUint32(R.BASE.HEAP_ARENAS, true);
      }
      const row = {imageBase, route, pointer:p, size, directLow:low, directHigh:high,
        overlap, target, translated, arenaCountBefore:before, arenaCountAfter:after};
      rows.push(row);
      try {
        assert(p, 'reservation succeeds outside the occupied direct window');
        assert(!overlap, 'sparse reservation must not alias the direct window');
        assert.equal(after, before, 'guest data must not overwrite HEAP_ARENAS');
        if (route !== 'section') {
          assert(translated >= directEnd, 'data uses sparse backing');
          assert.equal(e.guest_read32(target) >>> 0, 0x3f800000, 'data round trips');
        }
        if (imageBase === 0x32830000) assert(p + size <= low,
          'skip the occupied band and retain address capacity below the high image');
      } catch (error) { failures.push({imageBase, route, error:error.message}); }
    }
  }
  console.log(JSON.stringify({modulePath, rows, failures}, null, 2));
  assert.equal(failures.length, 0, 'high-image sparse placement regressions');
})().catch(error => {console.error(error); process.exitCode = 1;});
