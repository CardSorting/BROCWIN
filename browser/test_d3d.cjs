'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const runtime = path.resolve(__dirname, '../tools/wine-assembly');
const { bootRenderHarness } = require(path.join(runtime, 'test/render-helper'));

const extraWat = String.raw`
  (func (export "test_d3d_init")
    (global.set $image_base (i32.const 0x00400000))
    (global.set $exe_size_of_image (i32.const 0x00200000))
    (global.set $thunk_guest_base
      (i32.add (i32.sub (global.get $THUNK_BASE) (global.get $GUEST_BASE)) (global.get $image_base)))
    (call $heap_init (i32.const 0x01000000)))
  (func (export "test_new_d3d") (result i32)
    (call $handle_Direct3DCreate9 (i32.const 32) (i32.const 0) (i32.const 0)
      (i32.const 0) (i32.const 0) (i32.const 0))
    (i32.load (global.get $reg_base)))
  (func (export "test_new_device") (result i32)
    (local $device i32)
    (local.set $device (call $dx_create_com_obj (i32.const 20) (global.get $DX_VTBL_D3DDEV9)))
    (store.field DxObject misc1 (call $dx_from_this (local.get $device)) (call $d3d9_program_alloc))
    (local.get $device))
  (func (export "test_refs") (param i32) (result i32)
    (load.field DxObject refcount (call $dx_from_this (local.get 0))))
  (func (export "test_monitor_info") (param i32 i32)
    (call $handle_GetMonitorInfoW (local.get 0) (local.get 1) (i32.const 0) (i32.const 0) (i32.const 0) (i32.const 0)))
  (func (export "test_primary_monitor") (result i32)
    (call $single_monitor_rect (i32.const 0) (i32.const 0) (i32.const 1) (i32.const 1) (i32.const 0)))
`;

function guidBytes(text) {
  const raw = Buffer.from(text.replaceAll('-', ''), 'hex');
  raw.subarray(0, 4).reverse();
  raw.subarray(4, 6).reverse();
  raw.subarray(6, 8).reverse();
  return raw;
}

(async () => {
  const { exports: e, memory } = await bootRenderHarness({ extraWat, fonts: 'none' });
  e.test_d3d_init();
  e.init_dx_com_thunks();
  e.set_api_log(0);
  const stack = e.guest_alloc(1024) >>> 0;
  const iid = e.guest_alloc(32) >>> 0;
  const out = e.guest_alloc(16) >>> 0;
  const bytes = new Uint8Array(memory.buffer);
  const d3d = e.test_new_d3d() >>> 0;
  const device = e.test_new_device() >>> 0;
  const comCall = (object, slot, args) => {
    const vtable = e.guest_read32(object) >>> 0;
    const entry = e.guest_read32(vtable + slot * 4) >>> 0;
    assert.ok(entry, 'real COM vtable slot');
    const sp = stack + 512;
    e.guest_write32(sp, 0);
    [object, ...args].forEach((arg, index) => e.guest_write32(sp + 4 + index * 4, arg));
    e.set_esp(sp);
    e.set_eip(entry);
    e.run(100000);
    assert.equal(e.get_eip(), 0);
    assert.equal(e.get_esp(), sp + 8 + args.length * 4, 'COM stdcall frame is intact');
    return e.get_eax() >>> 0;
  };
  const query = (object, guid, output = out) => {
    if (guid !== null) bytes.set(guidBytes(guid), e.guest_to_wasm(iid) >>> 0);
    e.guest_write32(out, 0xdeadbeef);
    return comCall(object, 0, [guid === null ? 0 : iid, output]);
  };
  const reference = JSON.parse(fs.readFileSync(path.join(__dirname, 'reference/d3d-interfaces.json'), 'utf8'));
  const monitorInfo = e.guest_alloc(104) >>> 0;
  for (const row of reference.monitors) {
    const adapter = row.validAdapter ? 0 : 0xffffffff;
    const monitor = comCall(d3d, 15, [adapter]);
    assert.equal(!!monitor, row.monitorNonNull, 'D3D9 adapter returns a USER monitor identity');
    if (monitor) assert.equal(monitor, e.test_primary_monitor(), 'Direct3D and USER identify the same primary monitor');
    e.guest_write32(monitorInfo, 40);
    const sp = stack + 512;
    e.set_esp(sp);
    e.test_monitor_info(monitor, monitorInfo);
    assert.equal(!!e.get_eax(), row.getMonitorInfoW, 'Direct3D HMONITOR works with GetMonitorInfoW');
    assert.equal(e.get_esp(), sp + 12, 'GetMonitorInfoW stdcall');
    if (monitor) {
      assert.equal(e.guest_read32(monitorInfo + 36) & 1, 1);
      assert.ok(e.guest_read32(monitorInfo + 12) > e.guest_read32(monitorInfo + 4));
      assert.ok(e.guest_read32(monitorInfo + 16) > e.guest_read32(monitorInfo + 8));
    }
  }
  assert.equal(comCall(d3d, 15, [1]), 0, 'second adapter is outside this runtime single-monitor configuration');
  for (const row of reference.cases) {
    const refs = e.test_refs(d3d);
    assert.equal(query(d3d, row.iid), row.result, row.iid);
    assert.equal((e.guest_read32(out) >>> 0) === 0, row.outputNull);
    assert.equal((e.guest_read32(out) >>> 0) === d3d, row.sameIdentity);
    assert.equal(e.test_refs(d3d), refs + (row.result === 0 ? 1 : 0));
    if (row.result === 0) assert.equal(comCall(d3d, 2, []), refs, 'release balances successful query');
  }
  for (const guid of ['00000000-0000-0000-c000-000000000046', 'd0223b96-bf7a-43fd-92bd-a43b0d82b9eb']) {
    assert.equal(query(device, guid), 0);
    assert.equal(e.guest_read32(out) >>> 0, device);
    assert.equal(e.test_refs(device), 2);
    assert.equal(comCall(device, 2, []), 1);
  }
  for (const guid of ['b18b10ce-2649-405a-870f-95f777d4313a', '81bdcbca-64d4-426d-ae8d-ad0147f4275c',
                     'd0223b96-bf7a-43fd-92bd-a43b0d82b9ea']) {
    assert.equal(query(device, guid), 0x80004002, 'unsupported or near-match IID');
    assert.equal(e.guest_read32(out), 0);
    assert.equal(e.test_refs(device), 1);
  }
  for (const object of [d3d, device]) {
    assert.equal(query(object, '00000000-0000-0000-c000-000000000046', 0), 0x80004003);
    assert.equal(e.guest_read32(out) >>> 0, 0xdeadbeef, 'NULL output does not touch another location');
    assert.equal(query(object, null), 0x80004003);
    assert.equal(e.guest_read32(out), 0);
    assert.equal(e.test_refs(object), 1, 'failed calls do not retain the object');
  }
  console.log('PASS native Direct3D9 interfaces and monitor identity, Device9 lifetime, Ex rejection and x86 COM ABI');
})().catch(error => { console.error(error); process.exitCode = 1; });
