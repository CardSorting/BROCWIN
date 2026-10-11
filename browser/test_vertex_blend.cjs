'use strict';
// Full WAT D3D9 calls and the production command bridge, using measured native
// pixels. This is API conformance evidence for the integrated runtime.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const runtime=path.resolve(__dirname,'../tools/wine-assembly');
const {bootRenderHarness}=require(path.join(runtime,'test/render-helper'));
const {Bridge}=require(path.join(runtime,'lib/d3d9-host'));
const {OPCODES}=require(path.join(runtime,'lib/d3d-command-stream'));
const names=['CreateDevice','SetTransform','SetRenderState','SetTextureStageState','SetMaterial',
  'SetLight','LightEnable','SetFVF','Clear','BeginScene','DrawPrimitiveUP','EndScene','Release',
  'GetDeviceCaps','CreateVertexDeclaration','SetVertexDeclaration','DrawIndexedPrimitiveUP','DeclarationRelease'];
const extraWat=names.map(name=>`(func (export "${name}")
  (param $a i32) (param $b i32) (param $c i32) (param $d i32)
  (param $f i32) (param $g i32) (param $h i32) (param $j i32) (param $k i32) (result i32)
  (i32.store offset=16 (global.get $reg_base) (i32.const 0x074ff000))
  (call $gs32 (i32.const 0x074ff018) (local.get $g))
  (call $gs32 (i32.const 0x074ff01c) (local.get $h))
  (call $gs32 (i32.const 0x074ff020) (local.get $j))
  (call $gs32 (i32.const 0x074ff024) (local.get $k))
  (call $handle_IDirect3D${name==='DeclarationRelease'?'Shader9_Release':(name==='CreateDevice'?'9':'Device9')+'_'+name}
    (local.get $a) (local.get $b) (local.get $c) (local.get $d) (local.get $f) (i32.const 0))
  (i32.load (global.get $reg_base)))`).join('\n');
function compare(actual,want,size){
  const bg=[16,32,48,255],isBg=(b,p)=>bg.every((v,k)=>b[p*4+k]===v);
  let coverage=0,interiorMax=0,interiorPixels=0;
  for(let p=0;p<size*size;p++){
    const a=isBg(actual,p),b=isBg(want,p);if(a!==b){coverage++;continue;}if(a)continue;
    let edge=false;const x=p%size,y=p/size|0;
    for(let dy=-1;dy<=1;dy++)for(let dx=-1;dx<=1;dx++){
      const q=(y+dy)*size+x+dx;
      if(x+dx<0||x+dx>=size||y+dy<0||y+dy>=size||isBg(want,q))edge=true;
    }
    if(!edge){interiorPixels++;for(let k=0;k<4;k++)interiorMax=Math.max(interiorMax,Math.abs(actual[p*4+k]-want[p*4+k]));}
  }
  return {coverage,interiorMax,interiorPixels};
}
(async()=>{
  const ref=JSON.parse(fs.readFileSync(path.join(__dirname,'reference/fixed-vertex-blending.json')));
  let bridge;const {exports:e,memory}=await bootRenderHarness({fonts:'none',extraWat,
    extraHostOverrides:{gpu_gl_call:(...args)=>bridge.call(...args)}});
  e.d3dim_worker_init(0x400000);e.init_dx_com_thunks();
  bridge=new Bridge({backend:'software',enableProgrammable:true,getExports:()=>e,
    getMemory:()=>memory.buffer,guestToWasm:p=>e.guest_to_wasm(p)>>>0});
  const draws=[],issue=bridge._issue;
  bridge._issue=function(entry,op,payload){if(op===OPCODES.DRAW)draws.push(structuredClone(payload));return issue.call(this,entry,op,payload);};
  const alloc=data=>{const bytes=Buffer.isBuffer(data)?data:Buffer.from(new Float32Array(data).buffer),p=e.guest_alloc(bytes.length);
    for(let i=0;i<bytes.length;i++)e.guest_write8(p+i,bytes[i]);return p;};
  const call=async(name,...args)=>{let hr=e[name](...args)>>>0;
    while(e.get_d3d_render_token()){await bridge.wait(e.get_d3d_render_token());hr=e[name](...args)>>>0;}
    assert.equal(hr,0,`${name}: ${bridge.lastError||''}`);};
  const out=e.guest_alloc(320),pp=e.guest_alloc(56);
  [32,32,22,1,0,0,1,1,1,0,0,0,0,0x80000000].forEach((v,i)=>e.guest_write32(pp+i*4,v));
  await call('CreateDevice',0,0,1,1,0x20,pp,out);const device=e.guest_read32(out)>>>0;
  await call('GetDeviceCaps',device,out);const matrices=e.guest_read32(out+168)>>>0;
  for(const [rs,value]of[[7,0],[22,1],[27,0],[15,0],[28,0],[29,0],[141,0],[145,0],[146,0],[147,0],[148,0],[139,0],[167,0]])
    await call('SetRenderState',device,rs,value);
  for(const [ts,value]of[[1,2],[2,0],[4,2],[5,0]])await call('SetTextureStageState',device,0,ts,value);
  await call('SetTextureStageState',device,1,1,1);
  for(const [index,matrix]of[[2,ref.view],[3,ref.projection],...ref.worlds.map((m,i)=>[256+i,m])])
    await call('SetTransform',device,index,alloc(matrix));
  await call('SetMaterial',device,alloc(ref.material));
  await call('SetLight',device,0,alloc(Buffer.from(ref.light,'base64')));await call('LightEnable',device,0,1);
  assert.equal(matrices,4,'only implemented nonindexed blending advertised');
  const results=[],declarations=[];
  for(const [referenceIndex,row] of ref.cases.entries())for(const route of ['fvf','declaration','index16','index32']){
    const bytes=Buffer.from(row.vertices,'base64'),vertices=alloc(bytes);
    await call('SetFVF',device,row.fvf);await call('SetRenderState',device,151,row.weights);
    if(route!=='fvf'){
      const elements=Buffer.alloc(40);
      for(const [i,[offset,type,usage]]of [[0,2,0],[12,row.weights-1,1],[12+row.weights*4,2,3],[24+row.weights*4,4,10]].entries()){
        elements.writeUInt16LE(offset,i*8+2);elements[i*8+4]=type;elements[i*8+6]=usage;
      }
      elements.writeUInt16LE(255,32);elements[36]=17;
      await call('CreateVertexDeclaration',device,alloc(elements),out);const declaration=e.guest_read32(out)>>>0;
      declarations.push(declaration);await call('SetVertexDeclaration',device,declaration);
    }
    await call('SetRenderState',device,137,row.lighting);await call('SetRenderState',device,143,row.normalize);
    await call('Clear',device,0,0,1,0xff102030,0x3f800000,0);await call('BeginScene',device);
    if(route.startsWith('index')){
      const width=route==='index16'?2:4,indices=Buffer.alloc(width*3);
      for(let i=0;i<3;i++)indices[width===2?'writeUInt16LE':'writeUInt32LE'](i,width*i);
      await call('DrawIndexedPrimitiveUP',device,4,0,3,1,alloc(indices),width===2?101:102,vertices,row.stride);
    }else await call('DrawPrimitiveUP',device,4,1,vertices,row.stride);
    await call('EndScene',device);
    for(let i=0;i<bytes.length;i++)assert.equal(e.guest_read8(vertices+i),bytes[i],'snapshot transformation must not change guest vertices');
    const backend=[...bridge.devices.values()][0].device,bgra=backend.present().pixels,rgba=Buffer.from(bgra);
    for(let i=0;i<rgba.length;i+=4){rgba[i]=bgra[i+2];rgba[i+2]=bgra[i];}
    const result={referenceIndex,route,weights:row.weights,lighting:row.lighting,normalize:row.normalize,
      ...compare(rgba,Buffer.from(row.rgba,'base64'),ref.size)};
    results.push(result);console.log(JSON.stringify(result));
  }
  const encode=(_,v)=>ArrayBuffer.isView(v)?{$type:v.constructor.name,data:Array.from(v)}:v;
  if(process.env.THESEUS_VERTEX_BLEND_REPORT)fs.writeFileSync(process.env.THESEUS_VERTEX_BLEND_REPORT,JSON.stringify({matrices,results,draws},encode,2)+'\n');
  await call('SetFVF',device,0x52);
  for(const d of declarations)await call('DeclarationRelease',d);
  await call('Release',device);
  assert(results.every(r=>r.interiorPixels>20&&r.interiorMax<=2&&r.coverage<=3),'native pixel conformance');
  console.log('PASS fixed blending through real WAT APIs, immutable guest vertices and software rasterizer');
})().catch(error=>{console.error(error);process.exitCode=1;});
