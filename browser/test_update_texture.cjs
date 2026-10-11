'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {Worker} = require('node:worker_threads');
const base = path.resolve(__dirname, '../tools/wine-assembly');
const {bootRenderHarness} = require(path.join(base, 'test/render-helper'));
const {Bridge} = require(path.join(base, 'lib/d3d9-host'));
const {WorkerConsumer} = require(path.join(base, 'lib/d3d-command-stream'));
const sigs = require(path.join(base, 'lib/host-import-sigs.generated.json')).sigs;
const INVALID = 0x8876086c;
(async () => {
  let bridge, failUpload = false;
  const api = {Device9:['UpdateTexture','ColorFill','Release','SetRenderTarget','GetRenderTargetData'],
    Texture9:['LockRect','UnlockRect','GetSurfaceLevel','Release','AddDirtyRect'],
    CubeTexture9:['GetCubeMapSurface','AddDirtyRect'], Surface9:['LockRect','UnlockRect','Release']};
  const {exports:e, memory, module} = await bootRenderHarness({fonts:'none',
    extraHostOverrides:{gpu_gl_call:(op,...a) => failUpload && op===0x30011 ? 0 : bridge.call(op,...a)},
    extraWat:`
    (func (export "create") (param $pp i32) (param $out i32) (result i32)
      (i32.store offset=16 (global.get $reg_base) (i32.const 0x074ff000))
      (call $gs32 (i32.const 0x074ff018) (local.get $pp))
      (call $gs32 (i32.const 0x074ff01c) (local.get $out))
      (call $handle_IDirect3D9_CreateDevice (i32.const 0) (i32.const 0) (i32.const 1) (i32.const 1) (i32.const 0) (i32.const 0))
      (i32.load (global.get $reg_base)))
    (func (export "texture") (param $d i32) (param $w i32) (param $h i32) (param $levels i32)
      (param $fmt i32) (param $pool i32) (param $kind i32) (param $usage i32) (param $out i32) (result i32)
      (call $d3d9_texture_create_kind (local.get $d) (local.get $w) (local.get $h) (local.get $levels)
        (local.get $usage) (local.get $fmt) (local.get $pool) (local.get $out) (local.get $kind))
      (i32.load (global.get $reg_base)))
    (func (export "offscreen") (param $d i32) (param $size i32) (param $out i32) (result i32)
      (call $d3d9_color_create (local.get $d) (local.get $size) (local.get $size)
        (i32.const 21) (i32.const 2) (i32.const 0) (i32.const 1) (local.get $out))
      (i32.load (global.get $reg_base)))
    ${Object.entries(api).flatMap(([type,names])=>names.map(name=>`
    (func (export "${type}_${name}") (param $a i32) (param $b i32) (param $c i32) (param $d i32) (param $f i32) (result i32)
      (i32.store offset=16 (global.get $reg_base) (i32.const 0x074ff000))
      (call $handle_IDirect3D${type}_${name} (local.get $a) (local.get $b) (local.get $c) (local.get $d) (local.get $f) (i32.const 0))
      (i32.load (global.get $reg_base)))`)).join('\n')}`});
  e.d3dim_worker_init(0x400000); e.init_dx_com_thunks();
  const wa = p => e.guest_to_wasm(p) >>> 0, read = p => e.guest_read32(p) >>> 0;
  const pp=e.guest_alloc(56), out=e.guest_alloc(64), lock=e.guest_alloc(8);
  [8,8,22,1,0,0,1,1,1,0,0,0,0,0x80000000].forEach((x,i)=>e.guest_write32(pp+i*4,x));
  const mip=(t,i)=>t+64+i*32, bytes=(t,i)=>{
    const p=mip(t,i), data=read(p+16), size=read(p+12);
    return Array.from({length:size},(_,j)=>new Uint8Array(memory.buffer)[wa(data+j)]);
  };
  const fill=(t,i,value)=>{
    const p=mip(t,i), data=read(p+16), size=read(p+12);
    for(let j=0;j<size;j++)e.guest_write8(data+j,value);
  };
  for(const threaded of [false,true]) {
    bridge=new Bridge({backend:'software',enableProgrammable:true,getExports:()=>e,getMemory:()=>memory.buffer,guestToWasm:wa,
      ...(threaded?{createSoftwareWorker:()=>new WorkerConsumer(new Worker(path.join(base,'lib/d3d-render-worker.js')),
        {module,memory,sigs,imageBase:e.get_image_base()>>>0,reclaimHeap:h=>e.d3d_render_adopt_free_list(h)})}:{})});
    const call=async(name,...args)=>{
      let value=e[name](...args), parks=0;
      while(e.get_d3d_render_token()) {
        if(name==='Device9_UpdateTexture')assert.equal(e.get_esp()>>>0,0x074ff000,'pending transfer preserves arguments');
        parks++; await bridge.wait(e.get_d3d_render_token()); value=e[name](...args);
      }
      if(name==='Device9_UpdateTexture')assert.equal(e.get_esp()>>>0,0x074ff010,'transfer pops arguments once');
      return {hr:value>>>0,parks};
    };
    const ok=async(name,...args)=>{const r=await call(name,...args);assert.equal(r.hr,0,`${name}: ${bridge.lastError||''}`);return r;};
    const textures=[];
    assert.equal(e.create(pp,out),0);const device=read(out);
    assert.equal(e.create(pp,out),0);const other=read(out);
    const tex=(w,h,levels,fmt,pool,kind=3,usage=0,owner=device)=>{
      assert.equal(e.texture(owner,w,h,levels,fmt,pool,kind,usage,out),0);
      const t=read(out);textures.push(t);return t;
    };
    let completed=false;
    try {
      for(const kind of [3,5])for(const fmt of [21,22,23,50,51,81,0x31545844,0x33545844,0x35545844]) {
        const s=tex(8,8,4,fmt,2,kind),d=tex(8,8,4,fmt,0,kind),n=kind===5?24:4;
        for(let i=0;i<n;i++)fill(s,i,17+i);
        await ok('Device9_UpdateTexture',device,s,d);
        for(let i=0;i<n;i++)assert.deepEqual(bytes(d,i),bytes(s,i),'all faces and mip bytes copied exactly');
        assert.equal(read(s+60),0,'source dirtiness consumed');
        fill(s,0,99);const seq=read(mip(d,0)+28);
        await ok('Device9_UpdateTexture',device,s,d);
        assert.equal(bytes(d,0)[0],17,'clean source leaves destination intact');
        assert.equal(read(mip(d,0)+28),seq,'clean source leaves snapshot cache intact');
        for(const flags of [0x10,0x8000]) {
          await ok('Texture9_LockRect',s,0,lock,0,flags);
          await ok('Texture9_UnlockRect',s,0);
          assert.equal(read(s+60),0,'READONLY and NO_DIRTY_UPDATE do not dirty upload source');
        }
        await ok('Texture9_LockRect',s,1,lock,0,0);await ok('Texture9_UnlockRect',s,1);
        assert.equal(read(s+60),0,'sublevel lock does not automatically dirty level zero');
        await ok('Texture9_LockRect',s,0,lock,0,0);
        await ok('Device9_UpdateTexture',device,s,d);
        assert.equal(bytes(d,0)[0],99,'native UpdateTexture accepts locked source');
        await ok('Texture9_UnlockRect',s,0);
        await ok('Texture9_AddDirtyRect',s,0);
        await ok('Texture9_LockRect',d,n-1,lock,0,0);
        await ok('Device9_UpdateTexture',device,s,d);
        assert.equal(read(s+60),0,'native UpdateTexture accepts locked destination');
        await ok('Texture9_UnlockRect',d,n-1);
        await ok('Device9_UpdateTexture',device,s,d);
        assert.equal(bytes(d,0)[0],99);
        assert.equal(read(mip(d,0)+28),seq+2,'copied mip invalidates decoded snapshot');
        if(kind===5) {
          fill(s,8,201);fill(s,4,202);
          await ok('CubeTexture9_AddDirtyRect',s,2,0);
          await ok('Device9_UpdateTexture',device,s,d);
          assert.equal(bytes(d,8)[0],201,'dirty cube face copied');
          assert.equal(bytes(d,4)[0],21,'clean cube face preserved');
        }
      }
      const s=tex(8,4,4,21,2),d=tex(2,1,2,21,0);
      for(let i=0;i<4;i++)fill(s,i,40+i);
      await ok('Device9_UpdateTexture',device,s,d);
      assert.deepEqual(bytes(d,0),bytes(s,2));assert.deepEqual(bytes(d,1),bytes(s,3));
      const invalid=[tex(2,2,2,21,0),tex(2,1,1,21,0),tex(2,1,2,22,0),
        tex(2,1,2,21,1),tex(2,2,2,21,0,5),tex(2,1,2,21,0,3,0,other)];
      for(const t of invalid)assert.equal((await call('Device9_UpdateTexture',device,s,t)).hr,INVALID,'mismatched texture rejected');
      assert.equal((await call('Device9_UpdateTexture',device,d,s)).hr,INVALID,'wrong pools rejected');
      assert.equal((await call('Device9_UpdateTexture',device,s,s)).hr,INVALID);
      assert.equal((await call('Device9_UpdateTexture',device,0,d)).hr,INVALID);
      const native=JSON.parse(fs.readFileSync(path.join(__dirname,'reference/texture-update.json'),'utf8'));
      const ns=tex(4,4,3,21,2),nd=tex(4,4,3,21,0,3,1),nativeRows=[];
      const writePixel=async(t,level,value,flags=0)=>{
        await ok('Texture9_LockRect',t,level,lock,0,flags);e.guest_write32(read(lock+4),value);
        await ok('Texture9_UnlockRect',t,level);
      };
      const pixel=async(t,level,size)=>{
        await ok('Texture9_GetSurfaceLevel',t,level,out);const surf=read(out);
        assert.equal(e.offscreen(device,size,out),0);const copy=read(out);
        await ok('Device9_GetRenderTargetData',device,surf,copy);
        await ok('Surface9_LockRect',copy,lock,0,16);const value=read(read(lock+4));
        await ok('Surface9_UnlockRect',copy);await ok('Surface9_Release',copy);await ok('Surface9_Release',surf);
        return value;
      };
      const nativeUpdate=async(target=nd)=>(await call('Device9_UpdateTexture',device,ns,target)).hr;
      await writePixel(ns,0,0xff123456);await writePixel(ns,1,0xff567890);
      nativeRows.push({case:'initial',result:await nativeUpdate(),top:await pixel(nd,0,4),mip1:await pixel(nd,1,2)});
      await writePixel(ns,0,0xffabcdef,0x8000);
      nativeRows.push({case:'no-dirty-update',result:await nativeUpdate(),top:await pixel(nd,0,4)});
      await writePixel(ns,1,0xff010203);
      nativeRows.push({case:'sublevel-only',result:await nativeUpdate(),mip1:await pixel(nd,1,2)});
      await ok('Texture9_AddDirtyRect',ns,0);
      nativeRows.push({case:'explicit-dirty',result:await nativeUpdate(),top:await pixel(nd,0,4),mip1:await pixel(nd,1,2)});
      await ok('Texture9_LockRect',ns,0,lock,0,0);
      nativeRows.push({case:'source-locked',result:await nativeUpdate(),top:await pixel(nd,0,4)});
      await ok('Texture9_UnlockRect',ns,0);
      const dynamic=tex(4,4,3,21,0,3,512);
      await ok('Texture9_LockRect',dynamic,0,lock,0,0);await ok('Texture9_AddDirtyRect',ns,0);
      nativeRows.push({case:'destination-locked',result:await nativeUpdate(dynamic)});
      await ok('Texture9_UnlockRect',dynamic,0);
      const tail=tex(2,2,2,21,0,3,1);await ok('Texture9_AddDirtyRect',ns,0);
      nativeRows.push({case:'matching-tail',result:await nativeUpdate(tail),top:await pixel(tail,0,2)});
      nativeRows.push({case:'wrong-pools',result:(await call('Device9_UpdateTexture',device,nd,ns)).hr});
      assert.deepEqual(nativeRows,native.cases,'native return and GPU readback reference');
      // Force render-target color identities to exist before UpdateTexture;
      // readback must observe ordered uploads, not stale backend pixels.
      const rs=tex(4,4,3,21,2,5),rd=tex(4,4,3,21,0,5,1),surfaces=[];
      for(let face=0;face<6;face++)for(let level=0;level<3;level++) {
        await ok('CubeTexture9_GetCubeMapSurface',rd,face,level,out);const surface=read(out);surfaces.push(surface);
        await ok('Device9_ColorFill',device,surface,0,0xff102030);
        fill(rs,face*3+level,80+face*3+level);
      }
      failUpload=true;
      assert.equal((await call('Device9_UpdateTexture',device,rs,rd)).hr,INVALID,'backend failure is visible');
      assert.equal(read(rs+60),63,'failed upload does not consume source dirtiness');
      failUpload=false;
      const uploaded=await ok('Device9_UpdateTexture',device,rs,rd);
      if(threaded)assert.equal(uploaded.parks,18,'one real pending upload per face/mip');
      const copies=[4,2,1].map(size=>{assert.equal(e.offscreen(device,size,out),0);return read(out);});
      for(let i=0;i<18;i++) {
        const copy=copies[i%3];
        await ok('Device9_GetRenderTargetData',device,surfaces[i],copy);
        await ok('Surface9_LockRect',copy,lock,0,16);
        assert.equal(read(read(lock+4)),((80+i)*0x01010101)>>>0,'backend readback matches transfer');
        await ok('Surface9_UnlockRect',copy);await ok('Surface9_Release',surfaces[i]);
      }
      for(const copy of copies)await ok('Surface9_Release',copy);
      console.log(`PASS UpdateTexture ${threaded?'worker':'direct'}: 18 format/kind combinations, dirty state, mip matching, rejection, failure recovery and 18 rendered mip uploads`);
      completed=true;
    } finally {
      failUpload=false;
      try {
        if(completed) {
          for(const t of textures.reverse())assert.equal((await call('Texture9_Release',t)).hr,0);
          assert.equal((await call('Device9_Release',device)).hr,0);
          assert.equal((await call('Device9_Release',other)).hr,0);
        }
      } finally { await bridge.close(); }
    }
  }
})().catch(error=>{console.error(error);process.exitCode=1;});
