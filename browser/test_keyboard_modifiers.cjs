'use strict';
// Physical modifier identity through the real renderer, Wasm DirectInput
// dispatch, and Worker RPC. No original-client instructions are replaced.
const assert = require('node:assert/strict');
const path = require('node:path');
const {Worker} = require('node:worker_threads');
const root = path.resolve(__dirname, '../tools/wine-assembly');
const {bootRenderHarness} = require(path.join(root, 'test/render-helper'));
const RPC = require(path.join(root, 'lib/guest-rpc'));
const sigs = require(path.join(root, 'lib/host-import-sigs.generated.json')).sigs;
const apis = require(path.join(root, 'src/api_table.json'));
const reference = require('./reference/keyboard-modifiers.json');
const extraWat = `
  (func (export "modifier_init")
    (global.set $image_base (i32.const 0x00400000))
    (call $heap_init (i32.const 0x01000000)))
  (func (export "modifier_thread")
    (global.set $image_base (i32.const 0x00400000))
    (global.set $reg_base (region.addr $REGFILE 256)))
  (func (export "modifier_device") (result i32)
    (local $obj i32) (local $entry i32)
    (local.set $obj (call $dx_create_com_obj (i32.const 7) (i32.const 0x52000000)))
    (local.set $entry (call $dx_from_this (local.get $obj)))
    (store.field DxObject misc0 (local.get $entry) (i32.const 1))
    (i32.store offset=16 (local.get $entry) (i32.const 0x0800))
    (local.get $obj))
  (func (export "modifier_call") (param i32 i32 i32 i32 i32 i32) (result i32)
    (i32.store offset=16 (global.get $reg_base) (i32.const 0x074ff000))
    (call $dispatch_api_table (local.get 0) (local.get 1) (local.get 2)
      (local.get 3) (local.get 4) (local.get 5) (i32.const 0))
    (i32.load (global.get $reg_base)))
`;

(async () => {
  const h = await bootRenderHarness({extraWat, fonts:'none'}), e = h.exports, r = h.renderer;
  e.modifier_init(); e.set_api_log(0);
  const call = (name, args) => {
    const api = apis.find(a => a.name === name);
    const result = e.modifier_call(api.id, ...args) >>> 0;
    assert.equal(e.get_esp() >>> 0, 0x074ff000 + 4 + api.nargs * 4, name + ' ABI');
    return result;
  };
  const device = e.modifier_device() >>> 0, format = e.guest_alloc(24) >>> 0;
  const objects = e.guest_alloc(4096) >>> 0, state = e.guest_alloc(256) >>> 0;
  const data = e.guest_alloc(4096) >>> 0, count = e.guest_alloc(4) >>> 0;
  [24,16,2,256,256,objects].forEach((v,i) => e.guest_write32(format+i*4,v));
  for (let i=0;i<256;i++) [0,i,(0x8000000c|(i<<8))>>>0,0]
    .forEach((v,j) => e.guest_write32(objects+i*16+j*4,v));
  assert.equal(call('IDirectInputDevice_SetDataFormat',[device,format]),0);
  assert.equal(call('IDirectInputDevice_SetCooperativeLevel',[device,0x10000,6]),0);
  assert.equal(call('IDirectInputDevice_Acquire',[device]),0);
  const readState = () => Array.from({length:256},(_,i) => e.guest_read8(state+i)).flatMap((v,i)=>v?[i]:[]);
  const readData = () => Array.from({length:e.guest_read32(count)},(_,i)=>
    [e.guest_read32(data+i*16),e.guest_read32(data+i*16+4)]);
  const localPoll = (peek=0) => {
    assert.equal(call('IDirectInputDevice_GetDeviceState',[device,256,state]),0);
    e.guest_write32(count,256);
    assert.equal(call('IDirectInputDevice_GetDeviceData',[device,16,data,count,peek]),0);
    return {state:readState(),data:readData()};
  };
  const edge = (row,down) => r[down?'handleKeyDown':'handleKeyUp'](row.generic,
    {code:row.code,location:row.code.endsWith('Right')?2:1});
  let checks = 0;
  let snapshotChecks = 0;
  const exercise = async poll => {
    for (let i=0;i<reference.cases.length;i+=2) {
      const left=reference.cases[i], right=reference.cases[i+1];
      for (const row of [left,right]) {
        edge(row,true);
        assert.equal(r.peekKeyDownState(row.virtualKey),0x8000,row.code+' physical side');
        assert.equal(r.peekKeyDownState(row.generic),0x8000,row.code+' aggregate');
        assert.deepEqual(await poll(1),{state:[row.dik],data:[[row.dik,128]]},row.code+' peek');
        assert.deepEqual(await poll(),{state:[row.dik],data:[[row.dik,128]]},row.code+' consume');
        edge(row,true); // Browser autorepeat is not another physical transition.
        assert.deepEqual(await poll(),{state:[row.dik],data:[]},row.code+' repeat');
        edge(row,false);
        assert.deepEqual(await poll(),{state:[],data:[[row.dik,0]]},row.code+' release');
        checks+=4;
      }
      edge(left,true); assert.deepEqual((await poll()).data,[[left.dik,128]]);
      edge(right,true); assert.deepEqual(await poll(),{state:[left.dik,right.dik],data:[[right.dik,128]]});
      edge(left,false);
      assert.equal(r.peekKeyDownState(left.generic),0x8000,'releasing one side keeps the other held');
      assert.deepEqual(await poll(),{state:[right.dik],data:[[left.dik,0]]});
      edge(right,false); assert.deepEqual(await poll(),{state:[],data:[[right.dik,0]]});
      checks+=4;
    }
  };
  const exerciseSnapshot = async poll => {
    // A Win32 message can stay open while DirectInput polls a newer physical
    // state. Keep the message's old key snapshot intact for GetKeyState.
    r._activeInputEvent = {type:'key',keyStateSnapshot:new Uint32Array(8)};
    r.handleKeyDown(0x41,{code:'KeyA',location:0});
    assert.equal(call('GetKeyState',[0x41]),0,'message snapshot remains up');
    assert.deepEqual(await poll(),{state:[0x1e],data:[[0x1e,128]]},
      'DirectInput sees physical press despite older up message');
    const held = new Uint32Array(8); held[0x41>>>5] |= 1<<(0x41&31);
    r._activeInputEvent = {type:'key',keyStateSnapshot:held};
    r.handleKeyUp(0x41,{code:'KeyA',location:0});
    assert.equal(call('GetKeyState',[0x41]) & 0x8000,0x8000,'message snapshot remains down');
    assert.deepEqual(await poll(),{state:[],data:[[0x1e,0]]},
      'DirectInput sees physical release despite older down message');
    snapshotChecks+=2;
    r._activeInputEvent = null;
  };
  await exercise(localPoll);
  await exerciseSnapshot(localPoll);
  const worker = new Worker(`
    const {parentPort,workerData:d}=require('node:worker_threads');
    const RPC=require(d.rpc);
    const proxy=RPC.createWorkerImports(d.memory,d.sigs,m=>parentPort.postMessage(m),{slot:3});
    proxy.imports.host.memory=d.memory;
    const e=new WebAssembly.Instance(d.module,proxy.imports).exports;
    e.modifier_thread(); e.set_api_log(0);
    parentPort.on('message',m=>{
      proxy.imports.host.check_input();
      const messageState=proxy.imports.host.get_key_down_state(0x41);
      const a=e.modifier_call(d.stateId,d.device,256,d.state,0,0);
      e.guest_write32(d.count,256);
      const b=e.modifier_call(d.dataId,d.device,16,d.data,d.count,m.peek||0);
      parentPort.postMessage({done:true,a,b,messageState});
    });
  `,{eval:true,workerData:{rpc:path.join(root,'lib/guest-rpc'),sigs,module:h.module,memory:h.memory,
    device,state,data,count,stateId:apis.find(a=>a.name==='IDirectInputDevice_GetDeviceState').id,
    dataId:apis.find(a=>a.name==='IDirectInputDevice_GetDeviceData').id}});
  h.host.check_input=()=>r._activeInputEvent ? 0x100 : 0;
  const broker=RPC.createMainBroker(h.memory,h.host,sigs);
  let publishKeys = false;
  const workerPoll = (peek=0)=>new Promise((resolve,reject)=>{
      const keys = new Int32Array(8);
      for(let key=0;key<256;key++) if(r.peekKeyDownState(key)&0x8000) keys[key>>>5]|=1<<(key&31);
      // Match the application's generation publication at a slice/input edge.
      // Exercise both broker reads and the main-Worker's published bitmap.
      broker.publish({...(publishKeys ? {keys} : {}),inputPending:r._activeInputEvent?1:0});
      const timer=setTimeout(()=>{cleanup();reject(new Error('modifier Worker RPC timed out'));},15000);
      const cleanup=()=>{clearTimeout(timer);worker.off('message',message);worker.off('error',failed);};
      const failed=error=>{cleanup();reject(error);};
      const message=m=>{
        if(m.t==='rpc') broker.serveRpc(m.slot);
        else if(m.done) {cleanup();try {assert.equal(m.a,0);assert.equal(m.b,0);
          assert.equal(m.messageState,h.host.get_key_down_state(0x41),'Worker retains Win32 message state');
          resolve({state:readState(),data:readData()});} catch(error) {reject(error);}}
      };
      worker.on('message',message);worker.on('error',failed);worker.postMessage({peek});
  });
  try {
    await exercise(workerPoll);
    await exerciseSnapshot(workerPoll);
    publishKeys=true;
    await exercise(workerPoll);
    await exerciseSnapshot(workerPoll);
  } finally {await worker.terminate();}
  // Legacy numeric callers describe the left key; they must not invent a right press.
  r.pokeKeyDownState(17,true);
  assert.deepEqual(localPoll().state,[0x1d]);
  r.pokeKeyDownState(17,false);localPoll();
  // Explicit side VKs also preserve the generic aggregate.
  r.pokeKeyDownState(0xa3,true);
  assert.equal(r.peekKeyDownState(17),0x8000);
  assert.deepEqual(localPoll().state,[0x9d]);
  r.pokeKeyDownState(0xa3,false);localPoll();
  console.log(JSON.stringify({status:'passed',checks,snapshotChecks,paths:['direct Wasm','real Worker RPC','published Worker bitmap'],
    reference:reference.method,scope:'physical modifiers, live device state independent of message snapshots and polled buffered edges; no gameplay parity claim'}));
})().catch(error=>{console.error(error);process.exitCode=1;});
