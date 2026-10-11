'use strict';
// Actual CreateDevice/Reset/GetBackBuffer/Present handlers and ordered render
// consumers. The default parameters are from x2.exe's captured Reset call.
const assert = require('node:assert/strict');
const path = require('node:path');
const {Worker} = require('node:worker_threads');
const base = path.resolve(__dirname, '../tools/wine-assembly');
const {bootRenderHarness} = require(path.join(base, 'test/render-helper'));
const {Bridge} = require(path.join(base, 'lib/d3d9-host'));
const {WorkerConsumer} = require(path.join(base, 'lib/d3d-command-stream'));
const sigs = require(path.join(base, 'lib/host-import-sigs.generated.json')).sigs;
const INVALID = 0x8876086c;
const resetReference = require('./reference/reset-parameters-x86.json');
(async () => {
  let bridge;
  const api = {Device9:['Reset','GetBackBuffer','Present','Release','ColorFill','SetRenderTarget'],
    SwapChain9:['GetBackBuffer','GetPresentParameters'], Surface9:['Release','LockRect','UnlockRect']};
  const {exports:e, memory, module} = await bootRenderHarness({fonts:'none',
    extraHostOverrides:{gpu_gl_call:(...a) => bridge.call(...a), get_window_client_size:() => 12 | (10 << 16)},
    extraWat:`
      (func (export "create") (param $pp i32) (param $out i32) (result i32)
        (i32.store offset=16 (global.get $reg_base) (i32.const 0x074ff000))
        (call $gs32 (i32.const 0x074ff018) (local.get $pp))
        (call $gs32 (i32.const 0x074ff01c) (local.get $out))
        (call $handle_IDirect3D9_CreateDevice (i32.const 0) (i32.const 0) (i32.const 1) (i32.const 65537) (i32.const 0) (i32.const 0))
        (i32.load (global.get $reg_base)))
      (func (export "program") (param $d i32) (result i32) (call $d3d9_program_state (local.get $d)))
      ${Object.entries(api).flatMap(([type,names]) => names.map(name => `
      (func (export "${type}_${name}") (param $a i32) (param $b i32) (param $c i32) (param $d i32) (param $f i32) (result i32)
        (i32.store offset=16 (global.get $reg_base) (i32.const 0x074ff000))
        (call $handle_IDirect3D${type}_${name} (local.get $a) (local.get $b) (local.get $c) (local.get $d) (local.get $f) (i32.const 0))
        (i32.load (global.get $reg_base)))`)).join('\n')}`});
  e.d3dim_worker_init(0x400000); e.init_dx_com_thunks();
  const wa = p => e.guest_to_wasm(p) >>> 0;
  const pp = e.guest_alloc(56), out = e.guest_alloc(56), lock = e.guest_alloc(8);
  const words = [0,0,22,2,0,0,1,65537,1,1,77,3,0,0];
  const params = (overrides = {}) => words.map((v,i) => overrides[i] ?? v).forEach((v,i) => e.guest_write32(pp+i*4,v));
  const read = (p,n) => Array.from({length:n},(_,i) => e.guest_read32(p+i*4) >>> 0);
  const freed = p => {
    let at=e.get_free_list()>>>0; const seen=new Set();
    while(at) { assert(!seen.has(at) && seen.size<100000); seen.add(at);
      if(p>=at+4 && p<at+(e.guest_read32(at)>>>0))return true;
      at=e.guest_read32(at+4)>>>0; }
    return false;
  };
  const results=[];
  for (const threaded of [false,true]) {
    bridge=new Bridge({backend:'software',enableProgrammable:true,getExports:()=>e,getMemory:()=>memory.buffer,guestToWasm:wa,
      ...(threaded ? {createSoftwareWorker:()=>new WorkerConsumer(new Worker(path.join(base,'lib/d3d-render-worker.js')),
        {module,memory,sigs,imageBase:e.get_image_base()>>>0,reclaimHeap:h=>e.d3d_render_adopt_free_list(h)})} : {})});
    const call = async (name,...args) => {
      let value=e[name](...args);
      while(e.get_d3d_render_token()) {await bridge.wait(e.get_d3d_render_token()); value=e[name](...args);}
      return value>>>0;
    };
    try {
      params(); assert.equal(e.create(pp,out),0); const d=read(out,1)[0];
      for (const row of resetReference.cases) {
        const input=[...row.before.slice(0,7),65537,...row.before.slice(7)];
        input.forEach((v,i)=>e.guest_write32(pp+i*4,v));
        assert.equal(await call('Device9_Reset',d,pp),row.result,`native Reset ${row.name}`);
        const expected=[...row.after.slice(0,7),65537,...row.after.slice(7)];
        if (!input[0]) expected[0]=12;
        if (!input[1]) expected[1]=10;
        assert.deepEqual(read(pp,14),expected,`native Reset parameter writeback ${row.name}`);
        assert.equal(await call('SwapChain9_GetPresentParameters',d,out),0);
        assert.deepEqual(read(out,14),expected,`native retained parameters ${row.name}`);
      }
      params(); assert.equal(await call('Device9_Reset',d,pp),0,'captured x2 Reset: two backbuffers, lockable + depth-discard, D24X8, zero windowed dimensions');
      assert.equal(await call('SwapChain9_GetPresentParameters',d,out),0);
      assert.deepEqual(read(out,14),[12,10,...words.slice(2)],'reports actual retained presentation parameters');
      const buffers=[];
      for(let i=0;i<2;i++) {
        assert.equal(await call('Device9_GetBackBuffer',d,0,i,0,out),0); buffers.push(read(out,1)[0]);
        assert.equal(await call('SwapChain9_GetBackBuffer',d,i,0,out),0);
        assert.equal(read(out,1)[0],buffers[i],'device and chain share surface identity');
        await call('Surface9_Release',buffers[i]);
      }
      assert.notEqual(buffers[0],buffers[1],'independent backbuffer identities');
      for(const args of [[d,0,2,0,out],[d,1,0,0,out],[d,0,0,1,out]]) {
        e.guest_write32(out,0xdeadbeef); assert.equal(await call('Device9_GetBackBuffer',...args),INVALID);
        assert.equal(read(out,1)[0],0xdeadbeef,'invalid query preserves output');
      }
      const pixel=async s=>{
        assert.equal(await call('Surface9_LockRect',s,lock,0,16),0);
        const p=read(lock+4,1)[0],value=read(p,1)[0];
        assert.equal(await call('Surface9_UnlockRect',s),0); return value;
      };
      assert.equal(await call('Device9_ColorFill',d,buffers[0],0,0xffff0000),0);
      assert.equal(await call('Device9_ColorFill',d,buffers[1],0,0xff00ff00),0);
      assert.equal(await pixel(buffers[0]),0xffff0000); assert.equal(await pixel(buffers[1]),0xff00ff00);
      assert.equal(await call('Surface9_LockRect',buffers[1],lock,0,16),0);
      assert.equal(await call('Device9_Present',d),INVALID,'locked queued backbuffer blocks presentation');
      assert.equal(await call('Surface9_UnlockRect',buffers[1]),0);
      assert.equal(await call('Device9_Present',d),0);
      assert.equal(await pixel(buffers[0]),0xff00ff00,'next queued image becomes backbuffer zero after Present');
      assert.equal(await call('Device9_SetRenderTarget',d,0,buffers[1]),0,'queued surface is renderable');
      params(); assert.equal(await call('Device9_Reset',d,pp),INVALID,'external backbuffer references prevent Reset');
      await call('Surface9_Release',buffers[0]); await call('Surface9_Release',buffers[1]);
      params({3:3,13:0x80000000}); assert.equal(await call('Device9_Reset',d,pp),0);
      assert(freed(buffers[1]),'Reset releases old extra backbuffer including bound RT reference');
      const triple=[];
      for(let i=0;i<3;i++) {assert.equal(await call('Device9_GetBackBuffer',d,0,i,0,out),0); triple.push(read(out,1)[0]);}
      assert.equal(new Set(triple).size,3);
      for(let i=0;i<3;i++)assert.equal(await call('Device9_ColorFill',d,triple[i],0,[0xffff0000,0xff00ff00,0xff0000ff][i]),0);
      assert.equal(await call('Device9_Present',d),0); assert.equal(await pixel(triple[0]),0xff00ff00); assert.equal(await pixel(triple[1]),0xff0000ff);
      assert.equal(await call('Device9_Present',d),0); assert.equal(await pixel(triple[0]),0xff0000ff);
      for(const s of triple)await call('Surface9_Release',s);
      for(const overrides of [{3:4},{3:2,6:3},{11:4},{10:70},{10:82}]) {
        params(overrides); assert.equal(await call('Device9_Reset',d,pp),INVALID,JSON.stringify(overrides));
      }
      params({3:0,6:3}); assert.equal(await call('Device9_Reset',d,pp),0,'zero count is one COPY buffer');
      assert.equal(await call('Device9_GetBackBuffer',d,0,0,0,out),0); const one=read(out,1)[0];
      assert.equal(await call('Device9_ColorFill',d,one,0,0xff112233),0);
      assert.equal(await call('Device9_Present',d),0); assert.equal(await pixel(one),0xff112233,'COPY retains pixels');
      await call('Surface9_Release',one);
      assert.equal(await call('Device9_Release',d),0);
      await bridge.close();
      for(const s of triple.slice(1))assert(freed(s),'retired triple-buffer storage is reclaimed');
      results.push({threaded,status:'passed'});
    } finally {await bridge.close();}
  }
  console.log(JSON.stringify({test:'captured-x2-reset-and-backbuffer-queue',results}));
})().catch(error=>{console.error(error);process.exitCode=1;});
