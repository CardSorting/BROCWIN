'use strict';
// Native HRESULT/pixel reference through actual WAT COM handlers, then both
// software command consumers, through direct imports and the guest RPC broker.
const assert=require('node:assert/strict'),path=require('node:path'),{Worker}=require('node:worker_threads');
const base=path.resolve(__dirname,'../tools/wine-assembly');
const {bootRenderHarness}=require(path.join(base,'test/render-helper'));
const {Bridge}=require(path.join(base,'lib/d3d9-host'));
const {createHostImports}=require(path.join(base,'lib/host-imports'));
const {WorkerConsumer}=require(path.join(base,'lib/d3d-command-stream'));
const RPC=require(path.join(base,'lib/guest-rpc'));
const sigs=require(path.join(base,'lib/host-import-sigs.generated.json')).sigs;
const native=require('./reference/stretch-rect.json');
(async()=>{
  let bridge,productionImport,copies=0,failCopy=false;
  const api={Device9:['GetBackBuffer','GetRenderTargetData','UpdateSurface','Release','BeginScene','EndScene'],
    Surface9:['LockRect','UnlockRect','Release'],Texture9:['GetSurfaceLevel','Release']};
  const {exports:e,memory,module}=await bootRenderHarness({fonts:'none',extraHostOverrides:{gpu_gl_call:(op,...args)=>{
    if(op===0x30017){copies++;if(failCopy)return 0;}return productionImport(op,...args);
  }},extraWat:`
    (func (export "create") (param $pp i32) (param $out i32) (result i32)
      (i32.store offset=16 (global.get $reg_base) (i32.const 0x074ff000))
      (call $gs32 (i32.const 0x074ff018) (local.get $pp)) (call $gs32 (i32.const 0x074ff01c) (local.get $out))
      (call $handle_IDirect3D9_CreateDevice (i32.const 0) (i32.const 0) (i32.const 1) (i32.const 1) (i32.const 0) (i32.const 0))
      (i32.load (global.get $reg_base)))
    (func (export "surface") (param $d i32) (param $w i32) (param $h i32) (param $fmt i32)
      (param $pool i32) (param $usage i32) (param $out i32) (result i32)
      (call $d3d9_color_create (local.get $d) (local.get $w) (local.get $h) (local.get $fmt)
        (local.get $pool) (local.get $usage) (i32.const 1) (local.get $out))
      (i32.load (global.get $reg_base)))
    (func (export "texture") (param $d i32) (param $w i32) (param $h i32) (param $fmt i32) (param $out i32) (result i32)
      (call $d3d9_texture_create (local.get $d) (local.get $w) (local.get $h) (i32.const 1)
        (i32.const 1) (local.get $fmt) (i32.const 0) (local.get $out)) (i32.load (global.get $reg_base)))
    (func (export "stretch") (param $d i32) (param $s i32) (param $sr i32) (param $t i32) (param $tr i32) (param $f i32) (result i32)
      (i32.store offset=16 (global.get $reg_base) (i32.const 0x074ff000))
      (call $gs32 (i32.const 0x074ff018) (local.get $f))
      (call $handle_IDirect3DDevice9_StretchRect (local.get $d) (local.get $s) (local.get $sr) (local.get $t) (local.get $tr) (i32.const 0))
      (i32.load (global.get $reg_base)))
    ${Object.entries(api).flatMap(([type,names])=>names.map(name=>`
    (func (export "${type}_${name}") (param $a i32) (param $b i32) (param $c i32) (param $d i32) (param $f i32) (result i32)
      (i32.store offset=16 (global.get $reg_base) (i32.const 0x074ff000))
      (call $handle_IDirect3D${type}_${name} (local.get $a) (local.get $b) (local.get $c) (local.get $d) (local.get $f) (i32.const 0))
      (i32.load (global.get $reg_base)))`)).join('\n')}`});
  e.d3dim_worker_init(0x400000);e.init_dx_com_thunks();
  const read=p=>e.guest_read32(p)>>>0,wa=p=>e.guest_to_wasm(p)>>>0;
  const directImport=createHostImports({getMemory:()=>memory.buffer,exports:e,d3d9Bridge:{call:(...a)=>bridge.call(...a)}}).host.gpu_gl_call;
  const rpcSigs={gpu_gl_call:sigs.gpu_gl_call};
  const broker=RPC.createMainBroker(memory,{gpu_gl_call:directImport},rpcSigs);
  const guest=RPC.createWorkerImports(memory,rpcSigs,message=>{
    assert.equal(message.t,'rpc');broker.serveRpc(message.slot);
  },{slot:0});
  const alloc=n=>e.guest_alloc(n)>>>0,out=alloc(64),pp=alloc(56),lock=alloc(8),sr=alloc(16),dr=alloc(16);
  const write=(p,words)=>words.forEach((v,i)=>e.guest_write32(p+i*4,v));
  write(pp,[16,16,22,1,0,0,1,1,1,0,0,1,0,0x80000000]);
  const results=[];
  for(const brokered of[false,true])for(const threaded of[false,true]){
    productionImport=brokered?guest.imports.host.gpu_gl_call:directImport;
    bridge=new Bridge({backend:'software',enableProgrammable:true,getExports:()=>e,getMemory:()=>memory.buffer,guestToWasm:wa,
      ...(threaded?{createSoftwareWorker:()=>new WorkerConsumer(new Worker(path.join(base,'lib/d3d-render-worker.js')),
        {module,memory,sigs,imageBase:e.get_image_base()>>>0,reclaimHeap:h=>e.d3d_render_adopt_free_list(h)})}:{})});
    const call=async(name,...args)=>{
      let value=e[name](...args),parks=0;
      while(e.get_d3d_render_token()){
        if(name==='stretch')assert.equal(e.get_esp()>>>0,0x074ff000,'pending transfer retains stack');
        parks++;await bridge.wait(e.get_d3d_render_token());value=e[name](...args);
      }
      if(name==='stretch')assert.equal(e.get_esp()>>>0,0x074ff01c,'six-argument stdcall pops exactly once');
      return {hr:value>>>0,parks};
    };
    const ok=async(name,...args)=>{const r=await call(name,...args);assert.equal(r.hr,0,`${name}: ${bridge.lastError||''}`);return r;};
    await ok('create',pp,out);const device=read(out);
    let count=0,maxDifference=0,totalParks=0;
    try{
      for(const row of native.cases){
        const objects=[];
        const surface=async spec=>{
          let texture=0;
          if(spec.kind==='backbuffer')await ok('Device9_GetBackBuffer',device,0,0,0,out);
          else if(spec.kind==='texture'){
            await ok('texture',device,spec.width,spec.height,spec.format,out);texture=read(out);
            objects.push(['Texture9_Release',texture]);await ok('Texture9_GetSurfaceLevel',texture,0,out);
          }else await ok('surface',device,spec.width,spec.height,spec.format,spec.pool,spec.kind==='target'?1:0,out);
          const object=read(out);objects.push(['Surface9_Release',object]);return {...spec,object};
        };
        const put=async(s,words)=>{
          if(s.kind==='texture'){
            const upload=await surface({...s,kind:'offscreen',pool:2});await put(upload,words);
            await ok('Device9_UpdateSurface',device,upload.object,0,s.object,0);return;
          }
          await ok('Surface9_LockRect',s.object,lock,0,0);const pitch=read(lock),bits=read(lock+4);
          for(let y=0;y<s.height;y++)write(bits+y*pitch,words.slice(y*s.width,(y+1)*s.width));
          await ok('Surface9_UnlockRect',s.object);
        };
        const get=async s=>{
          if(s.kind!=='offscreen'){
            const copy=await surface({...s,kind:'offscreen',pool:2});
            await ok('Device9_GetRenderTargetData',device,s.object,copy.object);s=copy;
          }
          await ok('Surface9_LockRect',s.object,lock,0,16);const pitch=read(lock),bits=read(lock+4);
          const pixels=Array.from({length:s.width*s.height},(_,i)=>read(bits+Math.floor(i/s.width)*pitch+(i%s.width)*4));
          await ok('Surface9_UnlockRect',s.object);return pixels;
        };
        try{
          const s=await surface(row.source),d=row.same?s:await surface(row.destination);
          await put(s,row.input);if(!row.same)await put(d,row.before);
          if(row.sourceRect)write(sr,row.sourceRect);if(row.destinationRect)write(dr,row.destinationRect);
          if(row.lock)await ok('Surface9_LockRect',row.lock==='source'?s.object:d.object,lock,0,0);
          if(row.scene)await ok('Device9_BeginScene',device);
          const before=copies,r=await call('stretch',device,s.object,row.sourceRect?sr:0,d.object,row.destinationRect?dr:0,row.filter);
          assert.equal(r.hr,row.hr,row.name+' HRESULT');
          assert.equal(copies-before,row.hr?0:1,row.name+' submits one immutable copy');totalParks+=r.parks;
          if(row.scene)await ok('Device9_EndScene',device);
          if(row.lock)await ok('Surface9_UnlockRect',row.lock==='source'?s.object:d.object);
          const pixels=await get(d);
          for(let i=0;i<pixels.length;i++)for(const shift of(d.format===22?[0,8,16]:[0,8,16,24])){
            const difference=Math.abs(((pixels[i]>>>shift)&255)-((row.pixels[i]>>>shift)&255));
            maxDifference=Math.max(maxDifference,difference);
            assert(difference<=(row.filter===2&&!row.hr?1:0),`${row.name} pixel ${i} channel ${shift}: ${pixels[i].toString(16)} / ${row.pixels[i].toString(16)}`);
          }
          if(!row.hr&&!row.same){
            failCopy=true;
            try{assert.equal((await call('stretch',device,s.object,0,d.object,0,0)).hr,0x8876086c,'copy failure reaches guest');}
            finally{failCopy=false;}
          }
          count++;
        }finally{for(const[name,object]of objects.reverse())await call(name,object);}
      }
      assert.equal(bridge.requests.size,0,'no abandoned render tokens');
      if(threaded)assert(totalParks>0,'worker transfers actually park and resume');
      results.push({guestTransport:brokered?'production-rpc':'direct-import',
        renderConsumer:threaded?'software-worker':'software-direct',cases:count,maxChannelDifference:maxDifference,parks:totalParks});
    }finally{await call('Device9_Release',device);await bridge.close();}
  }
  console.log(JSON.stringify({test:'native StretchRect through WAT',results}));
})().catch(error=>{console.error(error);process.exitCode=1;});
