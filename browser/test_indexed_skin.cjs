'use strict';

// Execute the supplied D3DX DLL against the same Wasm D3D9 services as X2.
// This is a compatibility regression, not an alternate rendering application.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const browser = __dirname;
const runtime = path.resolve(browser, '../tools/wine-assembly');
const {bootRenderHarness} = require(path.join(runtime, 'test/render-helper'));
const {loadDll, patchDllImports, callDllMain, _test: {findDllExport}} =
  require(path.join(runtime, 'lib/dll-loader'));
const extraWat = String.raw`
  (func (export "test_mesh_init")
    (global.set $image_base (i32.const 0x00400000))
    (global.set $exe_size_of_image (i32.const 0x00200000))
    (global.set $thunk_guest_base
      (i32.add (i32.sub (global.get $THUNK_BASE) (global.get $GUEST_BASE)) (global.get $image_base)))
    (call $heap_init (i32.const 0x01000000)))
  (func (export "test_mesh_d3d") (result i32)
    (call $handle_Direct3DCreate9 (i32.const 32) (i32.const 0) (i32.const 0)
      (i32.const 0) (i32.const 0) (i32.const 0))
    (i32.load (global.get $reg_base)))`;

(async () => {
  const {Bridge}=require(path.join(runtime,'lib/d3d9-host'));
  let logMemory, bridge;
  const {exports: e, memory} = await bootRenderHarness({extraWat, fonts: 'none',
    extraHostOverrides: {gpu_gl_call:(o,p,a)=>bridge.call(o,p,a), log: (at, size) => console.log(new TextDecoder().decode(new Uint8Array(logMemory.buffer, at, size)))}});
  logMemory = memory;
  bridge=new Bridge({backend:'software',enableProgrammable:true,getExports:()=>e,getMemory:()=>memory.buffer,guestToWasm:p=>e.guest_to_wasm(p)>>>0});
  e.test_mesh_init();
  e.theseus_set_pointer_cookie(0x12345678);
  e.init_dx_com_thunks();
  e.set_api_log(0);
  const alloc = n => e.guest_alloc(n) >>> 0;
  const stack = alloc(1024 * 1024), sp = stack + 1024 * 1024 - 64;
  const teb = alloc(4096);
  e.set_fs_base(teb);
  for (const [offset, value] of [[0, 0xffffffff], [4, sp + 64], [8, stack], [0x18, teb]])
    e.guest_write32(teb + offset, value);
  e.set_esp(sp);
  const dlls = ['kernel32.dll', 'user32.dll', 'gdi32.dll'].map(name => ({name,
    bytes: fs.readFileSync(path.join(browser, 'generated/platform', name))}));
  dlls.push({name: 'msvcrt.dll', bytes: fs.readFileSync('C:/Windows/SysWOW64/msvcrt.dll')});
  dlls.push({name: 'd3dx9_43.dll', bytes: fs.readFileSync(path.resolve(browser, '../../client/data/d3dx9_43.dll'))});
  const mapped = dlls.map(d => ({name: d.name, ...loadDll(e, memory.buffer, d.bytes,
    'C:\\WINDOWS\\SYSTEM\\' + d.name)}));
  patchDllImports(e, memory.buffer, dlls, mapped, () => {});
  for (const dll of mapped) if (dll.dllMain) {
    console.log('Initialize ' + dll.name);
    callDllMain(e, dll.loadAddr, dll.dllMain, () => {}, {strict: true, lpReserved: 1});
  }
  const d3dx = mapped.at(-1);
  let tracePoints = [];
  const call = (address, args) => {
    e.guest_write32(sp, 0);
    args.forEach((arg, i) => e.guest_write32(sp + 4 + i * 4, arg));
    e.set_esp(sp); e.set_eip(address);
    for (let i = 0; i < 40 && e.get_eip(); i++) {
      e.run(1000000);
      if (tracePoints.length && e.get_last_run_halt() === 5 && e.get_eip() === tracePoints[0]) {
        const bp = e.get_ebp() >>> 0;
        const words = (p,n) => Array.from({length:n},(_,j) => (e.guest_read32(p+j*4)>>>0).toString(16));
        console.log(JSON.stringify({point:(e.get_eip()-d3dx.loadAddr).toString(16), eax:(e.get_eax()>>>0).toString(16),
          edi:(e.get_edi()>>>0).toString(16), args:words(bp+8,10), position:words(bp-0x40,1),
          vb:words(e.guest_read32(bp+8)>>>0,16), ib:words(e.guest_read32(bp+12)>>>0,16)}));
        tracePoints.shift(); e.set_bp(tracePoints[0] || 0);
      }
    }
    assert.equal(e.get_eip(), 0, `call 0x${address.toString(16)} returns`);
    assert.equal(e.get_esp(), sp + 4 + args.length * 4, 'stdcall frame');
    return e.get_eax() >>> 0;
  };
  const com = (obj, slot, args = []) => call(e.guest_read32(e.guest_read32(obj) + slot * 4) >>> 0, [obj, ...args]);
  const create = findDllExport(e, memory.buffer, d3dx.loadAddr, 'D3DXCreateMeshFVF');
  const out = alloc(32), pp = alloc(56), d3d = e.test_mesh_d3d() >>> 0;
  [16,16,22,1,0,0,1,65537,1,0,0,0,0,0].forEach((v,i) => e.guest_write32(pp+i*4,v));
  assert.equal(com(d3d, 16, [0,1,65537,0x20,pp,out]), 0, 'CreateDevice');
  const device = e.guest_read32(out) >>> 0;
  const caps=alloc(304); assert.equal(com(device,7,[caps]),0);
  assert.equal(e.guest_read32(caps+168)>>>0,4,'implemented nonindexed matrix count');
  assert.equal(e.guest_read32(caps+172)>>>0,0,'indexed fixed blending stays unadvertised');

  const reference = require('./reference/indexed-skin-mesh.json'), rows=[];
  const write=(p,b)=>{for(let i=0;i<b.length;i++)e.guest_write8(p+i,b[i]);};
  const read=(p,n)=>Buffer.from(Array.from({length:n},(_,i)=>e.guest_read8(p+i)));
  const createSkin=findDllExport(e,memory.buffer,d3dx.loadAddr,'D3DXCreateSkinInfoFVF');
  for (const row of reference.cases) {
    const input=fs.readFileSync(path.resolve(browser,'../recovered/models/data033',row.source));
    assert.equal(crypto.createHash('sha256').update(input).digest('hex'),row.sourceSha256);
    const at=input.readUInt32LE(32+row.bone*84+72);
    const h=Array.from({length:14},(_,i)=>input.readUInt32LE(at+i*4));
    assert.equal(call(create,[h[7],h[5],0x220|(h[2]&1),h[1],device,out]),0);
    const mesh=e.guest_read32(out)>>>0;
    for(const [lock,unlock,offset,n] of [[15,16,h[6],h[5]*32],[17,18,h[8],h[7]*3*(h[2]&1?4:2)],[24,25,h[9],h[7]*4]]){
      assert.equal(com(mesh,lock,[0,out]),0);write(e.guest_read32(out)>>>0,input.subarray(offset,offset+n));
      assert.equal(com(mesh,unlock),0);
    }
    const adjacency=alloc(h[7]*12),adjacencyOut=alloc(h[7]*12);
    assert.equal(com(mesh,22,[0,adjacency]),0);
    assert.equal(call(createSkin,[h[5],h[1],h[10],out]),0);
    const skin=e.guest_read32(out)>>>0;
    for(let i=0;i<h[10];i++){
      const at=h[11]+i*76,n=input.readUInt32LE(at+68),offset=input.readUInt32LE(at+72),p=alloc(n*8);
      write(p,input.subarray(offset,offset+n*8));
      assert.equal(com(skin,3,[i,n,p,p+n*4]),0);
    }
    const fields=alloc(16);
    const hr=com(skin,26,[mesh,0x220,h[12],adjacency,adjacencyOut,0,0,fields,fields+4,fields+8,fields+12]);
    const output=e.guest_read32(fields+12)>>>0,combination=e.guest_read32(fields+8)>>>0;
    const result={source:row.source,bone:row.bone,result:hr,maxVertexInfluences:e.guest_read32(fields)>>>0,groups:e.guest_read32(fields+4)>>>0};
    if(!hr){
      result.outputFVF=com(output,6);result.outputStride=com(output,8);result.outputVertices=com(output,5);
      assert.equal(com(output,15,[16,out]),0);
      const vertices=read(e.guest_read32(out)>>>0,result.outputStride*result.outputVertices);
      assert.equal(com(output,16),0);
      result.vertexBytesMatch=vertices.equals(Buffer.from(row.vertexBytes,'base64'));
      result.vertexBytes=vertices.toString('base64');
    }
    result.metadataMatch=['result','maxVertexInfluences','groups','outputFVF','outputStride','outputVertices'].every(k=>result[k]===row[k]);
    rows.push(result);console.log(JSON.stringify({...result,vertexBytes:undefined}));
    for(const obj of [output,combination,skin,mesh])if(obj)com(obj,2);
  }
  if(process.env.THESEUS_INDEXED_SKIN_REPORT)fs.writeFileSync(process.env.THESEUS_INDEXED_SKIN_REPORT,
    JSON.stringify({scope:'Supplied x86 D3DX conversion using the unmodified shared runtime capabilities',controlledCapsOverride:null,cases:rows},null,2)+'\n');
  assert.ok(rows.every(r=>r.metadataMatch&&r.vertexBytesMatch),'original indexed-mesh conversion differs from native reference');
  console.log('PASS original indexed skin-mesh conversion: '+rows.length+' cases');
})().catch(error=>{console.error(error);process.exitCode=1;});
