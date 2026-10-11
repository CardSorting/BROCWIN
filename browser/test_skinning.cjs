'use strict';
// Compare supplied x86 D3DX execution with native results. No substitute game.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'../..'),runtime=path.join(root,'theseus/tools/wine-assembly');
const {bootRenderHarness}=require(path.join(runtime,'test/render-helper'));
const {loadDll,patchDllImports,callDllMain,_test:{findDllExport}}=require(path.join(runtime,'lib/dll-loader'));
const extraWat=String.raw`
  (func (export "init_math_probe")
    (global.set $image_base (i32.const 0x00400000))
    (global.set $exe_size_of_image (i32.const 0x00200000))
    (global.set $thunk_guest_base (i32.add (i32.sub (global.get $THUNK_BASE) (global.get $GUEST_BASE)) (global.get $image_base)))
    (call $heap_init (i32.const 0x01000000)))`;
(async()=>{
 let logMemory;
 const {exports:e,memory}=await bootRenderHarness({extraWat,fonts:'none',extraHostOverrides:{log:(at,size)=>console.log(new TextDecoder().decode(new Uint8Array(logMemory.buffer,at,size))),log_i32:v=>console.log('i32='+v)}});
 logMemory=memory;
 e.init_math_probe(); e.theseus_set_pointer_cookie(0x12345678);e.set_api_log(0);
 for(const name of ['set_cpu_sse','set_cpu_mmx','set_uop','set_uop_trace_heads','set_x87_pipeline4_fusion','set_x87_affine_fusion'])e[name]?.(1);
 if(process.env.THESEUS_SKIN_NO_SSE)e.set_cpu_sse(0);
 const alloc=n=>e.guest_alloc(n)>>>0, stack=alloc(1024*1024),sp=stack+1024*1024-64,teb=alloc(4096);
 e.set_fs_base(teb);
 for(const [o,v]of[[0,0xffffffff],[4,sp+64],[8,stack],[0x18,teb]])e.guest_write32(teb+o,v);
 e.set_esp(sp);
 const dlls=['kernel32.dll','user32.dll','gdi32.dll'].map(name=>({name,bytes:fs.readFileSync(path.join(root,'theseus/browser/generated/platform',name))}));
 dlls.push({name:'msvcrt.dll',bytes:fs.readFileSync('C:/Windows/SysWOW64/msvcrt.dll')},
  {name:'d3dx9_43.dll',bytes:fs.readFileSync(path.join(root,'client/data/d3dx9_43.dll'))});
 const mapped=dlls.map(d=>({name:d.name,...loadDll(e,memory.buffer,d.bytes,'C:\\WINDOWS\\SYSTEM\\'+d.name)}));
 patchDllImports(e,memory.buffer,dlls,mapped,()=>{});
 for(const d of mapped)if(d.dllMain)callDllMain(e,d.loadAddr,d.dllMain,()=>{},{strict:true,lpReserved:1});
 const dll=mapped.at(-1),out=alloc(64),a=alloc(64),b=alloc(64),det=alloc(4);
 const bits=new DataView(new ArrayBuffer(4));
 const word=f=>{bits.setFloat32(0,f,true);return bits.getUint32(0,true);};
 const read=(p,n)=>Array.from({length:n},(_,i)=>{bits.setUint32(0,e.guest_read32(p+i*4)>>>0,true);return bits.getFloat32(0,true);});
 const call=(name,args)=>{
  e.guest_write32(sp,0);args.forEach((v,i)=>e.guest_write32(sp+4+i*4,v));e.set_esp(sp);
  e.set_eip(findDllExport(e,memory.buffer,dll.loadAddr,name));
  for(let i=0;i<40&&e.get_eip();i++)e.run(1000000);
  assert.equal(e.get_eip(),0,name+' returns');assert.equal(e.get_esp(),sp+4+args.length*4,name+' stdcall');
  return e.get_eax()>>>0;
 };

 const com=(obj,slot,args=[])=>{
  e.guest_write32(sp,0);[obj,...args].forEach((v,i)=>e.guest_write32(sp+4+i*4,v));e.set_esp(sp);
  const fn=e.guest_read32(e.guest_read32(obj)+slot*4)>>>0;e.set_eip(fn);
  try { for(let i=0;i<80&&e.get_eip();i++)e.run(1000000); } catch(error) { console.log(JSON.stringify({slot,eip:(e.get_eip()>>>0).toString(16),dllBase:dll.loadAddr.toString(16),esp:(e.get_esp()>>>0).toString(16)})); throw error; }
  assert.equal(e.get_eip(),0,`COM slot ${slot} returns`);assert.equal(e.get_esp(),sp+8+args.length*4,'stdcall');
  return e.get_eax()>>>0;
 };
 const bytes=p=>Buffer.from(p,'base64'),write=(p,data)=>{for(let i=0;i<data.length;i++)e.guest_write8(p+i,data[i]);};
 const floatBuffer=values=>{const p=alloc(values.length*4);values.forEach((v,i)=>e.guest_write32(p+i*4,word(v)));return p;};
 const ref=require('./reference/skinning.json'),results=[];
 for(const row of ref.cases){
  const original=fs.readFileSync(path.join(root,'theseus/recovered/models/data033',row.source));
  assert.equal(require('node:crypto').createHash('sha256').update(original).digest('hex'),row.sha256);
  assert.equal(call('D3DXCreateSkinInfoFVF',[row.vertices,row.fvf,row.skins.length,out]),0);
  const obj=e.guest_read32(out)>>>0;
  row.skins.forEach((skin,i)=>{
   const ids=alloc(skin.indices.length*4);skin.indices.forEach((v,j)=>e.guest_write32(ids+j*4,v));
   assert.equal(com(obj,3,[i,skin.indices.length,ids,floatBuffer(skin.weights)]),0,'SetBoneInfluence');
   assert.equal(com(obj,16,[i,floatBuffer(skin.matrix)]),0,'SetBoneOffsetMatrix');
  });
  const input=bytes(row.sourceBytes),expected=bytes(row.outputBytes),source=alloc(input.length),dest=alloc(input.length+32);
  write(source,input);write(dest,Buffer.alloc(input.length+32,0xa5));
  const hr=com(obj,24,[floatBuffer(row.transforms),floatBuffer(row.normalTransforms),source,dest+16]);
  assert.equal(hr,row.result,'UpdateSkinnedMesh HRESULT');
  const actual=Buffer.from(Array.from({length:input.length},(_,i)=>e.guest_read8(dest+16+i)));
  let max=0,bad=0;
  for(let i=0;i<input.length;i+=4){
   const error=Math.abs(actual.readFloatLE(i)-expected.readFloatLE(i))/(1+Math.abs(expected.readFloatLE(i)));
   max=Math.max(max,error);if(!Number.isFinite(error)||error>2e-5)bad++;
  }
  const guards=Array.from({length:16},(_,i)=>[e.guest_read8(dest+i),e.guest_read8(dest+16+input.length+i)]).flat().every(v=>v===0xa5);
  const uv=Array.from({length:row.vertices},(_,i)=>actual.subarray(i*32+24,i*32+32).equals(expected.subarray(i*32+24,i*32+32))).every(Boolean);
  results.push({source:row.source,bone:row.bone,mode:row.mode,vertices:row.vertices,hr,maxNormalizedAbsoluteError:max,badFloatCount:bad,guards,exactUVs:uv,pass:!bad&&guards&&uv});
  console.log(JSON.stringify(results.at(-1)));
  assert.equal(com(obj,2),0,'Release');
 }
 assert.equal(results.filter(r=>!r.pass).length,0,'native/Wasm skinning mismatch');
 console.log('PASS original D3DX software skinning: '+results.length+' cases');
})().catch(e=>{console.error(e);process.exit(1);});
