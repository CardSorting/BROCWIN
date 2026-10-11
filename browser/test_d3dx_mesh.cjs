'use strict';

// Execute the supplied D3DX DLL against the same Wasm D3D9 services as X2.
// This is a compatibility regression, not an alternate rendering application.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const runtime = path.resolve(__dirname, '../tools/wine-assembly');
const {bootRenderHarness} = require(path.join(runtime, 'test/render-helper'));
const {loadDll, patchDllImports, callDllMain, _test: {findDllExport}} =
  require(path.join(runtime, 'lib/dll-loader'));
const extraWat = String.raw`
  (func (export "test_mesh_init")
    (global.set $image_base (i32.const 0x00400000))
    (global.set $exe_size_of_image (i32.const 0x00200000))
    (global.set $thunk_guest_base
      (i32.add (i32.sub (global.get $THUNK_BASE) (global.get $GUEST_BASE)) (global.get $image_base)))
    (call $heap_init (i32.const 0x01000000)))
  (func (export "test_mesh_d3d") (result i32)
    (call $handle_Direct3DCreate9 (i32.const 32) (i32.const 0) (i32.const 0)
      (i32.const 0) (i32.const 0) (i32.const 0))
    (i32.load (global.get $reg_base)))`;

(async () => {
  let logMemory;
  const {exports: e, memory} = await bootRenderHarness({extraWat, fonts: 'none',
    extraHostOverrides: {log: (at, size) => console.log(new TextDecoder().decode(new Uint8Array(logMemory.buffer, at, size)))}});
  logMemory = memory;
  e.test_mesh_init();
  e.theseus_set_pointer_cookie(0x12345678);
  e.init_dx_com_thunks();
  e.set_api_log(0);
  const alloc = n => e.guest_alloc(n) >>> 0;
  const stack = alloc(1024 * 1024), sp = stack + 1024 * 1024 - 64;
  const teb = alloc(4096);
  e.set_fs_base(teb);
  for (const [offset, value] of [[0, 0xffffffff], [4, sp + 64], [8, stack], [0x18, teb]])
    e.guest_write32(teb + offset, value);
  e.set_esp(sp);
  const dlls = ['kernel32.dll', 'user32.dll', 'gdi32.dll'].map(name => ({name,
    bytes: fs.readFileSync(path.join(__dirname, 'generated/platform', name))}));
  dlls.push({name: 'msvcrt.dll', bytes: fs.readFileSync('C:/Windows/SysWOW64/msvcrt.dll')});
  dlls.push({name: 'd3dx9_43.dll', bytes: fs.readFileSync(path.resolve(__dirname, '../../client/data/d3dx9_43.dll'))});
  const mapped = dlls.map(d => ({name: d.name, ...loadDll(e, memory.buffer, d.bytes,
    'C:\\WINDOWS\\SYSTEM\\' + d.name)}));
  patchDllImports(e, memory.buffer, dlls, mapped, () => {});
  for (const dll of mapped) if (dll.dllMain) {
    console.log('Initialize ' + dll.name);
    callDllMain(e, dll.loadAddr, dll.dllMain, () => {}, {strict: true, lpReserved: 1});
  }
  const d3dx = mapped.at(-1);
  let tracePoints = [];
  const call = (address, args) => {
    e.guest_write32(sp, 0);
    args.forEach((arg, i) => e.guest_write32(sp + 4 + i * 4, arg));
    e.set_esp(sp); e.set_eip(address);
    for (let i = 0; i < 40 && e.get_eip(); i++) {
      e.run(1000000);
      if (tracePoints.length && e.get_last_run_halt() === 5 && e.get_eip() === tracePoints[0]) {
        const bp = e.get_ebp() >>> 0;
        const words = (p,n) => Array.from({length:n},(_,j) => (e.guest_read32(p+j*4)>>>0).toString(16));
        console.log(JSON.stringify({point:(e.get_eip()-d3dx.loadAddr).toString(16), eax:(e.get_eax()>>>0).toString(16),
          edi:(e.get_edi()>>>0).toString(16), args:words(bp+8,10), position:words(bp-0x40,1),
          vb:words(e.guest_read32(bp+8)>>>0,16), ib:words(e.guest_read32(bp+12)>>>0,16)}));
        tracePoints.shift(); e.set_bp(tracePoints[0] || 0);
      }
    }
    assert.equal(e.get_eip(), 0, `call 0x${address.toString(16)} returns`);
    assert.equal(e.get_esp(), sp + 4 + args.length * 4, 'stdcall frame');
    return e.get_eax() >>> 0;
  };
  const com = (obj, slot, args = []) => call(e.guest_read32(e.guest_read32(obj) + slot * 4) >>> 0, [obj, ...args]);
  const create = findDllExport(e, memory.buffer, d3dx.loadAddr, 'D3DXCreateMeshFVF');
  const out = alloc(32), pp = alloc(56), d3d = e.test_mesh_d3d() >>> 0;
  [16,16,22,1,0,0,1,65537,1,0,0,0,0,0].forEach((v,i) => e.guest_write32(pp+i*4,v));
  assert.equal(com(d3d, 16, [0,1,65537,0x20,pp,out]), 0, 'CreateDevice');
  const device = e.guest_read32(out) >>> 0;
  const reference = require('./reference/mesh-adjacency.json');
  for (const row of reference.nestedBufferLocks) {
    const vertex = row.kind === 'vertex';
    assert.equal(com(device, vertex ? 26 : 27, [96,0,vertex ? 0x112 : 101,1,out,0]), 0);
    const buffer = e.guest_read32(out) >>> 0;
    let first;
    for (const op of row.locks) {
      assert.equal(com(buffer, 11, [op.offset,op.size,out,op.flags]), op.result, `${row.kind} nested lock`);
      const pointer = e.guest_read32(out) >>> 0;
      first ??= pointer;
      assert.equal(pointer-first, op.pointerOffset, 'overlapping locks retain buffer identity');
    }
    for (const hr of row.unlocks) assert.equal(com(buffer, 12), hr, 'native balanced/extra Unlock');
    assert.equal(com(buffer, 11, [0,0,out,0]), 0, 'buffer reusable after extra Unlock');
    assert.equal(com(buffer, 12), 0);
    assert.equal(com(buffer, 2), 0);
  }
  for (const name of ['Motion_Elsword_LK.x', 'Motion_Elsword_Common.x']) {
    const input = fs.readFileSync(path.resolve(__dirname, '../recovered/models/data033', name));
    const bones = input.readUInt32LE(28);
    let meshOffset = 0;
    for (let i = 0; i < bones && !meshOffset; i++) meshOffset = input.readUInt32LE(32 + 84 * i + 72);
    const h = Array.from({length: 14}, (_, i) => input.readUInt32LE(meshOffset + i * 4));
    const [fvf, vertices, faces] = [h[1], h[5], h[7]];
    assert.equal(call(create, [faces, vertices, 0x220 | (h[2] & 1), fvf, device, out]), 0, 'CreateMeshFVF');
    const obj = e.guest_read32(out) >>> 0;
    const stride = com(obj, 8);
    assert.equal(stride, 32);
    const transfers = [[15, 16, h[6], vertices * stride], [17, 18, h[8], faces * 3 * (h[2] & 1 ? 4 : 2)],
      [24, 25, h[9], faces * 4]];
    for (const [lock, unlock, source, count] of transfers) {
      assert.equal(com(obj, lock, [0, out]), 0, 'mesh lock');
      const dest = e.guest_read32(out) >>> 0;
      for (let i = 0; i < count; i++) e.guest_write8(dest + i, input[source + i]);
      assert.equal(com(obj, unlock), 0, 'mesh unlock');
    }
    const adjacency = alloc(faces * 12);
    if (process.env.THESEUS_MESH_TRACE) {
      tracePoints = [0x5f03d,0x5f165,0x5f21b,0x5f57a].map(rva => d3dx.loadAddr+rva);
      e.set_bp(tracePoints[0]);
    }
    const hr = com(obj, 22, [0, adjacency]);
    console.log(`${name}: GenerateAdjacency=0x${hr.toString(16)} faces=${faces} vertices=${vertices}`);
    assert.equal(hr, 0, 'original mesh GenerateAdjacency');
    const neighbors = Array.from({length: faces * 3}, (_, i) => e.guest_read32(adjacency + i * 4) >>> 0);
    const native = reference.cases.find(row => row.name === name);
    assert.equal(crypto.createHash('sha256').update(input).digest('hex'), native.inputSha256);
    assert.deepEqual(neighbors, native.adjacency, 'same adjacency as native D3DX');
    assert.ok(neighbors.some(n => n !== 0xffffffff), 'connected original geometry');
    assert.ok(neighbors.every(n => n === 0xffffffff || n < faces), 'bounded face references');
    assert.equal(com(obj, 2), 0, 'mesh released');
  }
  console.log('PASS supplied D3DX KSM mesh adjacency through actual x86 and Wasm D3D9');
})().catch(error => { console.error(error); process.exitCode = 1; });
