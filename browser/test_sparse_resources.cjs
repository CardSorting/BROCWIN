'use strict';

// Integrated X2 capture 20261008T053117Z: a 512x512 ARGB texture spans two
// physical holes. Its linear clear erased a live Lua CClosure after hole one.
// Exercise the actual resource/heap handlers with the same non-affine layout.
const assert = require('node:assert/strict');
const path = require('node:path');
const runtime = path.resolve(__dirname, '../tools/wine-assembly');
const {bootRenderHarness} = require(path.join(runtime, 'test/render-helper'));
const R = require(path.join(runtime, 'lib/region-map.generated'));
const extraWat = String.raw`
  (func (export "test_sparse_init")
    (global.set $image_base (i32.const 0x00400000))
    (global.set $exe_size_of_image (i32.const 0x00200000))
    (global.set $thunk_guest_base
      (i32.add (i32.sub (global.get $THUNK_BASE) (global.get $GUEST_BASE)) (global.get $image_base)))
    (call $heap_init (i32.const 0x01000000)))
  (func (export "test_sparse_virtual") (param $size i32) (result i32)
    (i32.store offset=16 (global.get $reg_base) (i32.const 0x00500000))
    (call $handle_VirtualAlloc (i32.const 0) (local.get $size) (i32.const 0x3000)
      (i32.const 4) (i32.const 0) (i32.const 0))
    (i32.load (global.get $reg_base)))
  (func (export "test_sparse_release") (param $p i32)
    (drop (call $virtual_map_release (local.get $p))))
  (func (export "test_sparse_device") (result i32)
    (local $device i32)
    (local.set $device (call $dx_create_com_obj (i32.const 20) (global.get $DX_VTBL_D3DDEV9)))
    (store.field DxObject misc1 (call $dx_from_this (local.get $device)) (call $d3d9_program_alloc))
    (local.get $device))
  (func (export "test_sparse_texture") (param $device i32) (param $out i32) (result i32)
    (call $d3d9_texture_create (local.get $device) (i32.const 512) (i32.const 512)
      (i32.const 1) (i32.const 0) (i32.const 21) (i32.const 1) (local.get $out))
    (i32.load (global.get $reg_base)))
  (func (export "test_sparse_buffer") (param $device i32) (param $out i32) (result i32)
    (call $d3d9_buffer_create (local.get $device) (i32.const 0x100000) (i32.const 0)
      (i32.const 0) (i32.const 1) (local.get $out) (i32.const 6))
    (i32.load (global.get $reg_base)))
  (func (export "test_sparse_color") (param $device i32) (param $out i32) (result i32)
    (call $d3d9_color_create (local.get $device) (i32.const 512) (i32.const 512)
      (i32.const 21) (i32.const 2) (i32.const 0) (i32.const 1) (local.get $out))
    (i32.load (global.get $reg_base)))
  (func (export "test_sparse_texture_pool") (param $device i32) (param $out i32) (param $pool i32) (result i32)
    (call $d3d9_texture_create (local.get $device) (i32.const 512) (i32.const 512)
      (i32.const 1) (i32.const 0) (i32.const 21) (local.get $pool) (local.get $out))
    (i32.load (global.get $reg_base)))
  (func (export "test_sparse_update_textures") (param $device i32) (param $src i32) (param $dst i32) (param $out i32) (result i32)
    (call $d3d9_texture_surface (local.get $src) (i32.const 0) (local.get $out))
    (call $d3d9_texture_surface (local.get $dst) (i32.const 0) (i32.add (local.get $out) (i32.const 4)))
    (call $d3d9_update_surface (local.get $device) (call $gl32 (local.get $out)) (i32.const 0)
      (call $gl32 (i32.add (local.get $out) (i32.const 4))) (i32.const 0))
    (i32.load (global.get $reg_base)))
  (func (export "test_force_sparse_heap")
    (call $heap_reserve_below (call $w2g (region.end $GUEST_HEAP_BASE))))
  (func (export "test_sparse_update_texture") (param $d i32) (param $s i32) (param $t i32) (result i32)
    (call $d3d9_update_texture (local.get $d) (local.get $s) (local.get $t))
    (i32.load (global.get $reg_base)))
  (func (export "test_sparse_heap_alloc") (param $size i32) (result i32)
    (call $handle_HeapAlloc (global.get $PROCESS_HEAP_HANDLE) (i32.const 8) (local.get $size)
      (i32.const 0) (i32.const 0) (i32.const 0))
    (i32.load (global.get $reg_base)))
  (func (export "test_sparse_heap_realloc") (param $p i32) (param $size i32) (result i32)
    (call $handle_HeapReAlloc (global.get $PROCESS_HEAP_HANDLE) (i32.const 8) (local.get $p)
      (local.get $size) (i32.const 0) (i32.const 0))
    (i32.load (global.get $reg_base)))
  (func (export "test_sparse_local") (param $size i32) (result i32)
    (call $handle_LocalAlloc (i32.const 0x40) (local.get $size)
      (i32.const 0) (i32.const 0) (i32.const 0) (i32.const 0))
    (i32.load (global.get $reg_base)))
  (func (export "test_sparse_global") (param $size i32) (result i32)
    (call $handle_GlobalAlloc (i32.const 0x40) (local.get $size)
      (i32.const 0) (i32.const 0) (i32.const 0) (i32.const 0))
    (i32.load (global.get $reg_base)))
  (func (export "test_sparse_com") (param $size i32) (result i32)
    (call $handle_CoTaskMemAlloc (local.get $size)
      (i32.const 0) (i32.const 0) (i32.const 0) (i32.const 0) (i32.const 0))
    (i32.load (global.get $reg_base)))
  (func (export "test_sparse_calloc") (param $count i32) (param $size i32) (result i32)
    (call $handle_calloc (local.get $count) (local.get $size)
      (i32.const 0) (i32.const 0) (i32.const 0) (i32.const 0))
    (i32.load (global.get $reg_base)))
  (func (export "test_sparse_rtlzero") (param $p i32) (param $size i32)
    (call $handle_RtlZeroMemory (local.get $p) (local.get $size)
      (i32.const 0) (i32.const 0) (i32.const 0) (i32.const 0)))
  (func (export "test_sparse_errno") (result i32)
    (if (result i32) (global.get $msvcrt_errno_ptr)
      (then (call $gl32 (global.get $msvcrt_errno_ptr))) (else (i32.const 0))))
`;

async function fixture() {
  const h = await bootRenderHarness({extraWat, fonts: 'none'}), e = h.exports;
  e.test_sparse_init();
  e.init_dx_com_thunks();
  e.set_api_log(0);
  const out = e.guest_alloc(64) >>> 0, device = e.test_sparse_device() >>> 0;
  const old = e.guest_alloc(0x8000) >>> 0;
  const bytes = new Uint8Array(h.memory.buffer);
  bytes.fill(0x5a, e.guest_to_wasm(old) >>> 0, (e.guest_to_wasm(old) >>> 0) + 0x8000);
  const sizes = [R.SIZE.VIRTUAL_BACKING_BASE - 0x400000, 0x80000, 0x10000,
    0x90000, 0x10000, 0x400000 - 0x130000];
  const blocks = sizes.map(n => e.test_sparse_virtual(n) >>> 0);
  assert(blocks.every(Boolean), 'fragmentation fixture commits the entire backing pool');
  const guards = [blocks[2], blocks[4]].map(p => {
    const wa = e.guest_to_wasm(p) >>> 0;
    bytes.fill(0xa5, wa, wa + 0x10000);
    return {p, wa};
  });
  e.test_sparse_release(blocks[1]);
  e.test_sparse_release(blocks[3]);
  return {...h, e, out, device, old, bytes, guards, filler: blocks[0]};
}

function intact(h, label) {
  for (const {wa} of h.guards)
    assert(h.bytes.subarray(wa, wa + 0x10000).every(b => b === 0xa5), label + ': live neighbor remains intact');
}

function fragmented(h, p, size) {
  assert(p, 'allocation succeeds');
  const first = h.e.guest_to_wasm(p) >>> 0, last = h.e.guest_to_wasm(p + size - 1) >>> 0;
  assert.notEqual(last, first + size - 1, 'fixture must use discontiguous backing');
}

(async () => {
  const failures = [];
  for (const mode of ['texture', 'buffer', 'color', 'heap-zero', 'heap-realloc', 'heap-split-source', 'heap-reuse',
    'local', 'global', 'com', 'calloc', 'rtlzero', 'surface-source', 'surface-destination', 'texture-update-source', 'texture-update-destination']) {
    const h = await fixture(), {e} = h;
    try {
      if (mode === 'texture') {
        assert.equal(e.test_sparse_texture(h.device, h.out), 0);
        const p = e.guest_read32(h.out) >>> 0;
        fragmented(h, p, 0x100060);
        intact(h, mode);
        assert.equal(e.guest_read32(p + 24), 512);
        assert.equal(e.guest_read32(p + 28), 512);
        const data = e.guest_read32(p + 80) >>> 0;
        for (let i = 0; i < 0x100000; i += 4096)
          assert.equal(e.guest_read32(data + i), 0, 'all texture pages initialized');
      } else if (['surface-source', 'surface-destination', 'texture-update-source', 'texture-update-destination'].includes(mode)) {
        const sourceFirst = mode.endsWith('-source');
        assert.equal(e.test_sparse_texture_pool(h.device, h.out, sourceFirst ? 2 : 0), 0);
        const split = e.guest_read32(h.out) >>> 0;
        fragmented(h, split, 0x100060);
        e.test_sparse_release(h.filler);
        assert.equal(e.test_sparse_texture_pool(h.device, h.out + 4, sourceFirst ? 0 : 2), 0);
        const flat = e.guest_read32(h.out + 4) >>> 0;
        const src = sourceFirst ? split : flat, dst = sourceFirst ? flat : split;
        const srcBits = e.guest_read32(src + 80) >>> 0, dstBits = e.guest_read32(dst + 80) >>> 0;
        for (let i = 0; i < 0x100000; i += 4) e.guest_write32(srcBits + i, (i ^ 0xc3842051) >>> 0);
        assert.equal(mode.startsWith('texture-update') ? e.test_sparse_update_texture(h.device, src, dst) :
          e.test_sparse_update_textures(h.device, src, dst, h.out + 32), 0);
        intact(h, mode);
        for (let i = 0; i < 0x100000; i += 4)
          assert.equal(e.guest_read32(dstBits + i) >>> 0, (i ^ 0xc3842051) >>> 0, 'UpdateSurface preserves every row across sparse pages');
      } else if (mode === 'color') {
        assert.equal(e.test_sparse_color(h.device, h.out), 0);
        const p = e.guest_read32(h.out) >>> 0;
        fragmented(h, p, 0x100050);
        intact(h, mode);
        const data = e.guest_read32(p + 40) >>> 0;
        for (let i = 0; i < 0x100000; i += 4096) assert.equal(e.guest_read32(data + i), 0);
      } else if (mode === 'buffer') {
        assert.equal(e.test_sparse_buffer(h.device, h.out), 0);
        const p = e.guest_read32(h.out) >>> 0;
        fragmented(h, p, 0x100040);
        intact(h, mode);
        assert.equal(e.guest_read32(p + 24), 0x100000);
        for (let i = 0; i < 0x100000; i += 4096)
          assert.equal(e.guest_read32(p + 64 + i), 0);
      } else if (mode === 'heap-split-source') {
        const size = 0x100060, old = e.guest_alloc(size) >>> 0;
        fragmented(h, old, size);
        for (let i = 0; i < size; i += 4) e.guest_write32(old + i, (i ^ 0x63478a02) >>> 0);
        e.test_sparse_release(h.filler); // room for a larger destination
        const p = e.test_sparse_heap_realloc(old, 0x180000) >>> 0;
        assert(p);
        for (let i = 0; i < size; i += 4)
          assert.equal(e.guest_read32(p + i) >>> 0, (i ^ 0x63478a02) >>> 0, 'copy preserves both source extents');
        intact(h, mode);
      } else if (mode === 'heap-reuse') {
        e.test_force_sparse_heap();
        const size = 0xc0000, old = e.guest_alloc(size) >>> 0;
        fragmented(h, old, size);
        for (let i = 0; i < size; i += 4096) e.guest_write32(old + i, 0xb6b6b6b6);
        e.guest_free(old);
        const p = e.guest_alloc(size) >>> 0;
        assert.equal(p, old, 'same free-list block is reused');
        intact(h, mode);
        for (let i = 0; i < size; i += 4096) assert.equal(e.guest_read32(p + i), 0);
        if (mode === 'calloc') {
          const privateBytes = h.bytes.slice(0xf0, 0x100);
          assert.equal(e.test_sparse_calloc(1, 0x200000), 0, 'exhausted backing returns NULL');
          assert.equal(e.test_sparse_errno(), 12, 'allocation failure records ENOMEM');
          assert.equal(e.test_sparse_calloc(0x40000001, 4), 0, 'size_t overflow cannot wrap into a small allocation');
          assert.equal(e.test_sparse_errno(), 12);
          assert.deepEqual(h.bytes.slice(0xf0, 0x100), privateBytes, 'failure never zeroes the unmapped sentinel');
          assert(e.test_sparse_calloc(0, 0xffffffff) >>> 0, 'zero elements retains the CRT allocated-empty-block behavior');
          intact(h, mode);
        }
      } else if (['local', 'global', 'com', 'calloc', 'rtlzero'].includes(mode)) {
        const size = 0x100060;
        const p = (mode === 'calloc' ? e.test_sparse_calloc(4, size / 4)
          : mode === 'rtlzero' ? e.guest_alloc(size) : e['test_sparse_' + mode](size)) >>> 0;
        fragmented(h, p, size);
        if (mode === 'rtlzero') {
          for (let i = 0; i < size; i += 4096) e.guest_write32(p + i, 0xb6b6b6b6);
          e.test_sparse_rtlzero(p, size);
        }
        intact(h, mode);
        for (let i = 0; i < size; i += 4096) assert.equal(e.guest_read32(p + i), 0);
      } else {
        const size = 0x100060;
        const p = (mode === 'heap-zero' ? e.test_sparse_heap_alloc(size)
          : e.test_sparse_heap_realloc(h.old, size)) >>> 0;
        fragmented(h, p, size);
        intact(h, mode);
        if (mode === 'heap-realloc') {
          for (let i = 0; i < 0x8000; i += 4)
            assert.equal(e.guest_read32(p + i) >>> 0, 0x5a5a5a5a, 'old data survives reallocation');
        }
        for (let i = mode === 'heap-zero' ? 0 : 0x9000; i < size; i += 4096)
          assert.equal(e.guest_read32(p + i), 0, 'requested zeroed bytes cross the physical seam');
      }
      console.log('PASS sparse ' + mode);
    } catch (error) { failures.push(mode + ': ' + error.message); }
  }
  assert.deepEqual(failures, [], failures.join('\n'));
})().catch(error => { console.error(error); process.exitCode = 1; });
