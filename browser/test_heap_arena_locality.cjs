'use strict';
// Allocator validation regression, through the canonical full-source compiler.
// Optional preserved 10-helpers.wat reproduces the single-hint scan cost.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '../tools/wine-assembly');
const {compileSrcWasm} = require(path.join(root, 'test/compile-src'));
const sigs = require(path.join(root, 'lib/host-import-sigs.generated.json')).sigs;
const extra = `
  (global $locality_scans (mut i64) (i64.const 0))
  (func (export "locality_scans") (result i64) (global.get $locality_scans))
  (func (export "locality_find") (param i32) (result i32) (call $heap_arena_find (local.get 0)))
  (func (export "locality_init")
    (local $i i32) (local $base i32) (local $rec i32)
    (global.set $image_base (i32.const 0))
    (call $zero_memory (global.get $HEAP_ARENAS) (global.get $HEAP_ARENAS_SIZE))
    (loop $records
      (local.set $base (i32.add (i32.const 0x100000) (i32.shl (local.get $i) (i32.const 12))))
      (local.set $rec (call $heap_arena_register (local.get $base) (i32.add (local.get $base) (i32.const 4096))))
      (i32.atomic.store offset=8 (local.get $rec) (i32.add (local.get $base) (i32.const 4096)))
      (i32.atomic.store offset=12 (local.get $rec) (i32.const 16))
      (i32.store (call $g2w (local.get $base)) (i32.const 16))
      (local.set $i (i32.add (local.get $i) (i32.const 1)))
      (br_if $records (i32.lt_u (local.get $i) (i32.const 1000))))
    (global.set $locality_scans (i64.const 0)))
  (func (export "locality_pairs") (param $a i32) (param $b i32) (param $n i32) (result i32)
    (local $i i32) (local $ok i32)
    (loop $pairs
      (drop (call $heap_free_impl (i32.add (local.get $a) (i32.const 4)) (i32.const 0)))
      (local.set $ok (i32.add (local.get $ok) (i32.eq (call $heap_alloc (i32.const 8)) (i32.add (local.get $a) (i32.const 4)))))
      (drop (call $heap_free_impl (i32.add (local.get $b) (i32.const 4)) (i32.const 0)))
      (local.set $ok (i32.add (local.get $ok) (i32.eq (call $heap_alloc (i32.const 8)) (i32.add (local.get $b) (i32.const 4)))))
      (local.set $i (i32.add (local.get $i) (i32.const 1)))
      (br_if $pairs (i32.lt_u (local.get $i) (local.get $n))))
    (local.get $ok))
`;
(async () => {
  const wasm = compileSrcWasm((file, source) => {
    if (file !== '10-helpers.wat') return source;
    const s = process.argv[2] ? fs.readFileSync(process.argv[2], 'utf8') : source;
    const begin = s.indexOf('(func $heap_arena_find '), end = s.indexOf('\n  ;; Live allocated bytes', begin);
    assert(begin > 0 && end > begin);
    const fn = s.slice(begin, end);
    const anchor = '(br_if $done (i32.ge_u (local.get $i) (local.get $count)))';
    assert.equal(fn.split(anchor).length, 2);
    const counted = fn.replace(anchor, anchor + '\n      (global.set $locality_scans (i64.add (global.get $locality_scans) (i64.const 1)))');
    return s.slice(0, begin) + counted + s.slice(end) + extra;
  });
  const memory = new WebAssembly.Memory({initial:8192, maximum:8192, shared:true});
  const host = {memory};
  for (const [name, sig] of Object.entries(sigs)) host[name] = sig.results?.length ? () => 0 : () => {};
  const module = await WebAssembly.compile(wasm);
  const e = (await WebAssembly.instantiate(module, {host})).exports;
  e.locality_init();
  const a = 0x100000 + 998*4096, b = a + 4096;
  assert.equal(e.locality_pairs(a, b, 1000), 2000, 'all freed blocks are reused exactly');
  const scans = e.locality_scans();
  assert.equal(e.locality_pairs(a, b, 1000), 2000);
  const warmScans = Number(e.locality_scans() - scans);
  const recA = e.locality_find(a), recB = e.locality_find(b);
  const words = new Int32Array(memory.buffer);
  const write = (at, value) => Atomics.store(words, at >>> 2, value);
  // A is the secondary hint. Reclamation/re-registration must invalidate it.
  write(recA, 0); assert.equal(e.locality_find(a), 0, 'unpublished secondary rejected');
  write(recA+8, a+0x1000000+4096); write(recA, a+0x1000000);
  assert.equal(e.locality_find(a), 0, 'old address rejected after record reuse');
  assert.equal(e.locality_find(a+0x1000000), recA, 'new record extent found');
  write(recA, a); write(recA+8, a);
  assert.equal(e.locality_find(a), 0, 'shortened allocated extent rejected');
  write(recA+8, a+4096); assert.equal(e.locality_find(a), recA);
  assert.equal(e.locality_find(a+1), 0, 'unaligned header rejected');
  assert.equal(e.locality_find(b+4096), 0, 'exclusive upper bound rejected');
  assert.equal(e.locality_find(b), recB);
  write(recB, 0); assert.equal(e.locality_find(b), 0, 'unpublished primary rejected');
  write(recB, b);
  const peer = (await WebAssembly.instantiate(module, {host})).exports;
  assert.equal(peer.locality_find(a), recA, 'new instance needs no inherited hints');
  assert.equal(peer.locality_find(b), recB);
  console.log('PASS allocator reuse and stale/recycled/shortened hints, alignment, bounds, peer instance');
  console.log(JSON.stringify({warmScanRecords:warmScans, freeReusePairs:1000}));
  assert.equal(warmScans, 0, 'alternating known arenas must not rescan the full metadata table');
  console.log('PASS bounded two-arena lookup locality');
})().catch(error => {console.error(error); process.exitCode = 1;});
