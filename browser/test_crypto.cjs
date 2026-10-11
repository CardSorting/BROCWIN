'use strict';
// Native-reference contracts through actual API dispatch, plus real Worker RPC,
// fragmented guest memory, context exhaustion/reuse and entropy-source failure.
const assert = require('node:assert/strict');
const path = require('node:path');
const {Worker} = require('node:worker_threads');
const root = path.resolve(__dirname, '../tools/wine-assembly');
const {bootRenderHarness} = require(path.join(root, 'test/render-helper'));
const RPC = require(path.join(root, 'lib/guest-rpc'));
const R = require(path.join(root, 'lib/region-map.generated'));
const sigs = require(path.join(root, 'lib/host-import-sigs.generated.json')).sigs;
const apis = require(path.join(root, 'src/api_table.json'));
const reference = require('./reference/crypto.json');
for (const name of ['crypto-x86.json', 'crypto-pinvoke-x64.json']) {
  const native = require('./reference/' + name);
  assert.equal(native.cases.length, reference.cases.length);
  native.cases.forEach((row, i) => Object.keys(row).forEach(key =>
    assert.equal(row[key], reference.cases[i][key], `${name} ${row.case} ${key}`)));
}
const extraWat = `
  (func (export "crypto_test_init")
    (global.set $image_base (i32.const 0x00400000))
    (global.set $exe_size_of_image (i32.const 0x00200000))
    (call $heap_init (i32.const 0x01000000)))
  (func (export "crypto_test_thread")
    (global.set $image_base (i32.const 0x00400000))
    (global.set $reg_base (region.addr $REGFILE 256)))
  (func (export "crypto_test_call") (param $id i32) (param $a i32) (param $b i32)
      (param $c i32) (param $d i32) (param $f i32) (result i32)
    (global.set $last_error (i32.const 0x1234))
    (i32.store offset=16 (global.get $reg_base) (i32.const 0x074ff000))
    (call $dispatch_api_table (local.get $id) (local.get $a) (local.get $b) (local.get $c)
      (local.get $d) (local.get $f) (i32.const 0))
    (i32.load (global.get $reg_base)))
  (func (export "crypto_test_error") (result i32) (global.get $last_error))
  (func (export "crypto_test_map") (param $guest i32) (param $backing i32)
    (call $guest_page_publish_range (local.get $guest) (i32.const 4096) (local.get $backing) (i32.const 4)))
`;
(async () => {
  const h = await bootRenderHarness({extraWat, fonts:'none'}), e = h.exports;
  e.crypto_test_init();e.set_api_log(0);
  const call = (name, args, ex=e) => {
    const api = apis.find(a=>a.name===name);
    const result = ex.crypto_test_call(api.id,...args)>>>0;
    assert.equal(ex.get_esp()>>>0,0x074ff000+4+api.nargs*4,`${name} stdcall cleanup`);
    return result;
  };
  const out=e.guest_alloc(4)>>>0, strings=e.guest_alloc(1024)>>>0;
  const write=(at,s)=>{if(s===null)return 0; Buffer.from(s+'\0').forEach((b,i)=>e.guest_write8(at+i,b));return at;};
  const acquire=()=>{assert.equal(call('CryptAcquireContextA',[out,0,0,1,0xf0000000]),1);return e.guest_read32(out)>>>0;};
  for(const row of reference.cases.filter(r=>r.api==='acquire')) {
    e.guest_write32(out,0x1234);
    const result=call('CryptAcquireContextA',[row.nullOutput?0:out,write(strings,row.container),
      write(strings+512,row.provider),row.type,row.flags]);
    assert.equal(result,row.result,row.case);
    assert.equal(e.crypto_test_error()>>>0,row.error,row.case+' error');
    if(result) assert.equal(call('CryptReleaseContext',[e.guest_read32(out),0]),1);
    else assert.equal(e.guest_read32(out)>>>0,row.output??0,row.case+' output');
  }
  const handle=acquire(), size=131089, buffer=e.guest_alloc(size+2)>>>0;
  const bytes=new Uint8Array(h.memory.buffer,e.guest_to_wasm(buffer)>>>0,size+2);
  for(const row of reference.cases.filter(r=>r.api==='random'&&r.case!=='released')) {
    bytes.fill(0xa5);
    const invalid=row.case.startsWith('invalid'), empty=row.case.includes('zero'), nullOut=row.case.includes('null');
    assert.equal(call('CryptGenRandom',[invalid?0:handle,empty?0:row.case==='large'?size:16,nullOut?0:buffer+1]),row.result,row.case);
    assert.equal(e.crypto_test_error()>>>0,row.error,row.case+' error');
    assert.equal(bytes.some(v=>v!==0xa5),row.changed,row.case+' changed');
    assert.equal(bytes[0],0xa5);assert.equal(bytes.at(-1),0xa5);
  }
  for(const row of reference.cases.filter(r=>r.api==='release'&&r.case!=='fresh')) {
    assert.equal(call('CryptReleaseContext',[row.case==='null'?0:handle,row.flags]),row.result,row.case);
    assert.equal(e.crypto_test_error()>>>0,row.error,row.case+' error');
  }
  assert.equal(call('CryptGenRandom',[handle,16,buffer]),0,'released provider is invalid');
  assert.equal(e.crypto_test_error()>>>0,87);
  const fresh=reference.cases.find(r=>r.case==='fresh');
  assert.equal(call('CryptReleaseContext',[acquire(),0]),fresh.result);
  assert.equal(e.crypto_test_error()>>>0,fresh.error);
  const live=Array.from({length:128},acquire);
  assert.equal(new Set(live).size,128);
  assert.equal(call('CryptAcquireContextA',[out,0,0,1,0xf0000000]),0,'bounded registry reports exhaustion');
  assert.equal(e.crypto_test_error()>>>0,0x8009000e);
  live.forEach(v=>assert.equal(call('CryptReleaseContext',[v,0]),1));
  const cross=acquire();assert(!live.includes(cross),'reused slot rejects stale handle');
  const ga=0x68000000, backing=R.BASE.VIRTUAL_BACKING_BASE;
  const memory=new Uint8Array(h.memory.buffer);
  for(let i=0;i<3;i++) {e.crypto_test_map(ga+i*4096,backing+i*8192);memory.fill(0xa5,backing+i*8192,backing+i*8192+8192);}
  assert.equal(call('CryptGenRandom',[cross,4101,ga+4093]),1);
  const gathered=Uint8Array.from({length:4101},(_,i)=>e.guest_read8(ga+4093+i));
  assert(gathered.some(v=>v!==0xa5));
  assert.equal(e.guest_read8(ga+4092),0xa5);assert.equal(e.guest_read8(ga+8194),0xa5);
  for(let i=0;i<3;i++)assert(memory.subarray(backing+i*8192+4096,backing+(i+1)*8192).every(v=>v===0xa5),'neighboring physical pages untouched');
  assert.equal(call('CryptGenRandom',[cross,16,0xfffffffc]),0,'overflow rejected');
  assert.equal(e.crypto_test_error()>>>0,998);
  // A real thread instantiates the same module/memory and uses the shipped RPC.
  // Its release must invalidate the main thread's provider, without resetting it.
  const worker = new Worker(`
    const {parentPort,workerData:d}=require('node:worker_threads');
    const RPC=require(d.rpc);
    const proxy=RPC.createWorkerImports(d.memory,d.sigs,m=>parentPort.postMessage(m),{slot:3});
    proxy.imports.host.memory=d.memory;
    const ex=new WebAssembly.Instance(d.module,proxy.imports).exports;
    ex.crypto_test_thread();
    const random=ex.crypto_test_call(d.random,d.handle,32,d.buffer,0,0);
    const release=ex.crypto_test_call(d.release,d.handle,0,0,0,0);
    parentPort.postMessage({done:true,random,release});
  `,{eval:true,workerData:{rpc:path.join(root,'lib/guest-rpc'),sigs,module:h.module,memory:h.memory,
    random:apis.find(a=>a.name==='CryptGenRandom').id,release:apis.find(a=>a.name==='CryptReleaseContext').id,
    handle:cross,buffer:buffer+1}});
  const broker=RPC.createMainBroker(h.memory,h.host,sigs);
  try {
    const result=await new Promise((resolve,reject)=>{
      const timer=setTimeout(()=>reject(new Error('Worker entropy RPC timed out')),15000);
      worker.on('error',error=>{clearTimeout(timer);reject(error);});
      worker.on('message',m=>{if(m.t==='rpc')broker.serveRpc(m.slot);else if(m.done){clearTimeout(timer);resolve(m);}});
    });
    assert.deepEqual(result,{done:true,random:1,release:1});
  } finally {await worker.terminate();}
  assert.equal(call('CryptGenRandom',[cross,32,buffer+1]),0,'worker release invalidates shared provider');
  const secure=globalThis.crypto, original=secure.getRandomValues;
  const failureHandle=acquire();bytes.fill(0xa5);
  try {
    secure.getRandomValues=()=>{throw new Error('injected entropy failure');};
    assert.equal(call('CryptGenRandom',[failureHandle,32,buffer+1]),0);
    assert.equal(e.crypto_test_error()>>>0,0x80090020);
    assert(bytes.every(v=>v===0xa5),'failed entropy does not fabricate bytes');
  } finally {secure.getRandomValues=original;call('CryptReleaseContext',[failureHandle,0]);}
  console.log('PASS CryptoAPI native cases, secure entropy, stdcall dispatch, provider lifetime/reuse, sparse pages and real Worker RPC');
})().catch(error=>{console.error(error);process.exitCode=1;});
