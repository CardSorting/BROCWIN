'use strict';
const assert = require('node:assert/strict'), path = require('node:path'), fs = require('node:fs');
const runtime = path.resolve(__dirname, '../tools/wine-assembly');
const {bootRenderHarness} = require(path.join(runtime, 'test/render-helper'));
const {Bridge} = require(path.join(runtime, 'lib/d3d9-host'));
const wrappers = ['IDirect3DDevice9_GetSoftwareVertexProcessing', 'IDirect3DDevice9_SetSoftwareVertexProcessing',
  'IDirect3DDevice9_BeginStateBlock', 'IDirect3DDevice9_EndStateBlock', 'IDirect3DStateBlock9_Apply',
  'IDirect3DStateBlock9_Release', 'IDirect3DDevice9_Reset', 'IDirect3DDevice9_Release'];
const apis = JSON.parse(fs.readFileSync(path.join(runtime, 'src/api_table.json')));
const extraWat = wrappers.map(name => `(func (export "${name}") (param $a i32) (param $b i32) (result i32)
  (i32.store offset=16 (global.get $reg_base) (i32.const 0x074ff000))
  (call $handle_${apis.find(a => a.name === name).handler || name} (local.get $a) (local.get $b) (i32.const 0) (i32.const 0) (i32.const 0) (i32.const 0))
  (i32.load (global.get $reg_base)))`).join('\n') + `
  (func (export "create") (param $flags i32) (param $pp i32) (param $out i32) (result i32)
    (i32.store offset=16 (global.get $reg_base) (i32.const 0x074ff000))
    (call $gs32 (i32.const 0x074ff018) (local.get $pp))
    (call $gs32 (i32.const 0x074ff01c) (local.get $out))
    (call $handle_IDirect3D9_CreateDevice (i32.const 0) (i32.const 0) (i32.const 1)
      (i32.const 1) (local.get $flags) (i32.const 0))
    (i32.load (global.get $reg_base)))`;
(async () => {
  let bridge;
  const {exports: e, memory} = await bootRenderHarness({fonts: 'none', extraWat,
    extraHostOverrides: {gpu_gl_call: (o, p, a) => bridge.call(o, p, a)}});
  e.d3dim_worker_init(0x400000); e.init_dx_com_thunks();
  bridge = new Bridge({backend: 'software', enableProgrammable: true, getExports: () => e,
    getMemory: () => memory.buffer, guestToWasm: p => e.guest_to_wasm(p) >>> 0});
  const out = e.guest_alloc(4), pp = e.guest_alloc(56), results = [];
  const call = async (name, a, b = 0) => {
    const fn = e[name]; let value = fn(a, b);
    while (e.get_d3d_render_token()) { await bridge.wait(e.get_d3d_render_token()); value = fn(a, b); }
    return value >>> 0;
  };
  const get = d => e.IDirect3DDevice9_GetSoftwareVertexProcessing(d, 0) >>> 0;
  const set = (d, n) => e.IDirect3DDevice9_SetSoftwareVertexProcessing(d, n) >>> 0;
  for (const row of require('./reference/software-vertex-processing.json').cases) {
    [16, 16, 22, 1, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0x80000000].forEach((v, i) => e.guest_write32(pp + i * 4, v));
    assert.equal(e.create(row.flags, pp, out), 0); const device = e.guest_read32(out) >>> 0;
    assert.equal(get(device), row.initial, `initial flags=${row.flags}`);
    for (const op of row.sets) {
      assert.equal(set(device, op.input), op.hr, 'native Set HRESULT');
      assert.equal(e.get_esp() >>> 0, 0x074ff00c, 'Set stdcall cleanup');
      assert.equal(get(device), op.get, 'native Get state');
      assert.equal(e.get_esp() >>> 0, 0x074ff008, 'Get stdcall cleanup');
    }
    if (row.afterRecordedApply !== undefined) {
      assert.equal(await call(wrappers[2], device), 0); assert.equal(set(device, 1), 0);
      assert.equal(await call(wrappers[3], device, out), 0); const block = e.guest_read32(out) >>> 0;
      assert.equal(set(device, 0), 0); assert.equal(await call(wrappers[4], block), 0);
      assert.equal(get(device), row.afterRecordedApply, 'mode is not recorded');
      await call(wrappers[5], block); assert.equal(set(device, 1), 0);
    }
    assert.equal(get(device), row.beforeReset);
    assert.equal(await call(wrappers[6], device, pp), row.reset);
    assert.equal(get(device), row.afterReset, 'successful Reset restores creation mode');
    await call(wrappers[7], device); results.push({flags: row.flags, pass: true});
  }
  console.log('PASS native software/hardware/mixed VP state, BOOL inputs, rejected transitions, stateblock exclusion and Reset');
})().catch(error => { console.error(error); process.exitCode = 1; });
