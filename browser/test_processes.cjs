'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const runtime = path.resolve(__dirname, '../tools/wine-assembly');
const {bootRenderHarness} = require(path.join(runtime, 'test/render-helper'));
const {loadDll, _test: {findDllExport}} = require(path.join(runtime, 'lib/dll-loader'));
const apis = require(path.join(runtime, 'src/api_table.json'));
const extraWat = String.raw`
  (func (export "test_processes_init")
    (global.set $image_base (i32.const 0x00400000))
    (global.set $exe_size_of_image (i32.const 0x00200000))
    (global.set $thunk_guest_base
      (i32.add (i32.sub (global.get $THUNK_BASE) (global.get $GUEST_BASE)) (global.get $image_base)))
    (call $heap_init (i32.const 0x01000000)))
  (func (export "test_processes_error") (param $error i32) (result i32)
    (local $old i32) (local.set $old (global.get $last_error))
    (global.set $last_error (local.get $error)) (local.get $old))
  (func (export "test_processes_dispatch") (param i32 i32 i32 i32)
    (call $dispatch_api_table (local.get 0) (local.get 1) (local.get 2) (local.get 3)
      (i32.const 0) (i32.const 0) (i32.const 0)))`;

(async () => {
  const {exports: e, memory} = await bootRenderHarness({extraWat, fonts: 'none'});
  e.test_processes_init(); e.set_api_log(0); e.set_process_id(0x6314);
  const buffer = e.guest_alloc(65540) >>> 0, needed = e.guest_alloc(4) >>> 0;
  const stack = e.guest_alloc(1024) >>> 0, sp = stack + 512;
  const dll = loadDll(e, memory.buffer, fs.readFileSync(path.join(__dirname, 'generated/platform/kernel32.dll')),
    'C:\\WINDOWS\\SYSTEM\\kernel32.dll');
  const mappedCall = findDllExport(e, memory.buffer, dll.loadAddr, 'K32EnumProcesses');
  assert.ok(mappedCall, 'actual platform adapter exposes K32EnumProcesses');
  const reference = require('./reference/processes.json');
  assert.ok(reference.cases.find(row => row.bytes === 65536 && row.containsCaller));
  for (const route of ['EnumProcesses', 'K32EnumProcesses', 'mapped K32EnumProcesses']) {
    for (const row of reference.cases) {
      new Uint8Array(memory.buffer, e.guest_to_wasm(buffer) >>> 0, 65540).fill(0xa5);
      e.guest_write32(needed, 0xdeadbeef); e.test_processes_error(0x1234); e.set_esp(sp);
      const args = [row.hasOutput ? buffer : 0, row.bytes, row.hasNeeded ? needed : 0];
      if (route.startsWith('mapped')) {
        e.guest_write32(sp, 0); args.forEach((arg, i) => e.guest_write32(sp + 4 + i * 4, arg));
        e.set_eip(mappedCall); e.run(1000); assert.equal(e.get_eip(), 0);
      } else {
        e.test_processes_dispatch(apis.find(row => row.name === route).id, ...args);
      }
      assert.equal(e.get_esp(), sp + 16, `${route} stdcall removes three arguments`);
      assert.equal(e.get_eax(), row.value, `${route} native return`);
      assert.equal(e.test_processes_error(0), row.error, `${route} native last error`);
      // The runtime has one guest PID, while native Windows has more processes.
      const copied = Math.min(row.writtenEntries, 1);
      assert.equal(e.guest_read32(buffer) >>> 0, copied ? e.get_process_id() : 0xa5a5a5a5,
        'enumeration contains the actual guest PID, including write-before-error behavior');
      for (let offset = copied * 4; offset < 20; offset += 4)
        assert.equal(e.guest_read32(buffer + offset) >>> 0, 0xa5a5a5a5, 'remaining output untouched');
      assert.equal(e.guest_read32(needed) >>> 0,
        row.value ? Math.min(row.returnedBytes, 4) : 0xdeadbeef, 'bytes copied, not required capacity');
    }
  }
  // The source of identity is shared by threads and consumed at call time.
  e.set_process_id(0x7248);
  e.set_esp(sp); e.test_processes_dispatch(apis.find(row => row.name === 'EnumProcesses').id, buffer, 4, needed);
  assert.equal(e.guest_read32(buffer), 0x7248);
  assert.equal(e.guest_read32(needed), 4);
  // A second API must recognize exactly the process that enumeration returned.
  e.set_esp(sp); e.test_processes_dispatch(apis.find(row => row.name === 'OpenProcess').id, 0x410, 0, e.guest_read32(buffer));
  const processHandle = e.get_eax() >>> 0;
  assert.ok(processHandle);
  e.set_esp(sp); e.test_processes_dispatch(apis.find(row => row.name === 'OpenProcess').id, 0x410, 0, 0x7249);
  assert.equal(e.get_eax(), 0); assert.equal(e.test_processes_error(0), 87);
  console.log('PASS EnumProcesses: 30 native contracts across PSAPI/kernel32/mapped x86 routes; actual guest PID');
})().catch(error => {console.error(error); process.exitCode = 1;});
