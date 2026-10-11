'use strict';

// Sparse allocations below a high image are still owned heap blocks.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const runtime = path.resolve(__dirname, '../tools/wine-assembly');
const {compileSrcWasm} = require(path.join(runtime, 'test/compile-src'));
const R = require(path.join(runtime, 'lib/region-map.generated'));
const sigs = require(path.join(runtime, 'lib/host-import-sigs.generated.json')).sigs;
const extra = String.raw`
  (func (export "high_realloc") (param $ptr i32) (param $size i32) (param $flags i32) (result i32)
    (call $handle_HeapReAlloc (global.get $PROCESS_HEAP_HANDLE) (local.get $flags)
      (local.get $ptr) (local.get $size) (i32.const 0) (i32.const 0))
    (i32.load (global.get $reg_base)))
`;

(async () => {
  const module = await WebAssembly.compile(compileSrcWasm((name, source) => {
    if (name === '09a0-handlers-base.wat' && process.argv[2]) source = fs.readFileSync(process.argv[2], 'utf8');
    return name === '13-exports.wat' ? source + '\n' + extra : source;
  }));
  const memory = new WebAssembly.Memory({initial:8192, maximum:8192, shared:true});
  const host = {memory};
  for (const [name,sig] of Object.entries(sigs)) host[name] = sig.results?.length ? () => 0 : () => {};
  const e = (await WebAssembly.instantiate(module, {host})).exports;
  const base = 0x32830000;
  e.init_thread(0, base, 0, 0, 0, 0, 0);
  e.heap_init(base + 0x2000000);
  new DataView(memory.buffer).setUint32(R.BASE.VIRTUAL_MAP_STATE + 8, base + 0x7000000, true);
  const p = e.guest_alloc(0x200000) >>> 0;
  assert(p && p < base, 'fixture gets a real sparse allocation below the image');
  e.guest_write32(p, 0x51a227b8);
  assert.equal(e.high_realloc(p, 0x100000, 0x10) >>> 0, p,
    'in-place shrink recognizes an owned block below the low-heap base');
  assert.equal(e.guest_read32(p) >>> 0, 0x51a227b8);
  const usable = (e.guest_read32(p - 4) >>> 0) - 4;
  const q = e.high_realloc(p, usable + 4096, 8) >>> 0;
  assert(q, 'growth succeeds');
  assert.equal(e.guest_read32(q) >>> 0, 0x51a227b8, 'old content retained');
  for (let i = 0; i < 4096; i += 4) assert.equal(e.guest_read32(q + usable + i), 0, 'grown tail zeroed');
  e.guest_free(q);
  console.log('PASS high-image owned realloc: in-place shrink, preserved data, zeroed growth, free');
})().catch(error => {console.error(error); process.exitCode = 1;});
