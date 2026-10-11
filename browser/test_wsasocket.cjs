'use strict';
const assert=require('node:assert/strict'),path=require('node:path');
const root=path.resolve(__dirname,'../tools/wine-assembly');
const {bootRenderHarness}=require(path.join(root,'test/render-helper'));
const {createHostImports}=require(path.join(root,'lib/host-imports'));
const apis=require(path.join(root,'src/api_table.json'));
const reference=require('./reference/winsock-overlapped.json');
(async()=>{
  const h=await bootRenderHarness({fonts:'none',extraWat:`
    (func (export "socket_init")
      (global.set $image_base (i32.const 0x00400000))
      (call $heap_init (i32.const 0x01000000)))
    (func (export "socket_thread")
      (global.set $image_base (i32.const 0x00400000))
      (global.set $reg_base (region.addr $REGFILE 256)))
    (func (export "socket_call") (param i32 i32 i32 i32 i32 i32)
      (call $dispatch_api_table (local.get 0) (local.get 1) (local.get 2) (local.get 3) (local.get 4) (local.get 5) (i32.const 0)))
  `});
  const e=h.exports;e.socket_init();e.set_api_log(0);
  const stack=e.guest_alloc(128),data=e.guest_alloc(512);
  const call=(name,args=[],ex=e)=>{
    const api=apis.find(a=>a.name===name);assert(api,name);
    ex.clear_yield();ex.set_esp(stack);
    args.forEach((v,i)=>ex.guest_write32(stack+4+i*4,v));
    ex.socket_call(api.id,...Array.from({length:5},(_,i)=>args[i]||0));
    assert.equal(ex.get_esp()>>>0,stack+4+api.nargs*4,`${name} stdcall`);
    return ex.get_eax()>>>0;
  };
  for(const row of reference.cases.filter(r=>r.api==='create')) {
    if(row.case==='original')assert.equal(call('WSAStartup',[0x202,data]),0);
    call('WSASetLastError',[0x1234]);
    const result=call('WSASocketW',[row.af,row.type,row.protocol,0,0,row.flags]);
    assert.equal(result!==0xffffffff,row.success,row.case);
    assert.equal(call('WSAGetLastError'),row.error,row.case+' Winsock error');
    assert.equal(call('GetLastError'),row.error,row.case+' Win32 error');
    if(row.success)assert.equal(call('closesocket',[result]),0);
  }
  call('SetLastError',[0x7654]);assert.equal(call('WSAGetLastError'),0x7654,'Win32 and Winsock share thread error');
  const ctx={getMemory:()=>h.memory.buffer,onExit(){}};const imports=createHostImports(ctx);imports.host.memory=h.memory;
  const second=new WebAssembly.Instance(h.module,imports).exports;ctx.exports=second;second.socket_thread();second.set_api_log(0);
  const socket=call('WSASocketW',[2,1,6,0,0,1],second);
  assert.notEqual(socket,0xffffffff,'WSAStartup applies to other guest instances');
  assert.equal(call('WSAStartup',[0x202,data],second),0);
  assert.equal(call('WSACleanup',[],e),0);
  assert.equal(call('closesocket',[socket],second),0,'one remaining startup retains sockets');
  assert.equal(call('WSACleanup',[],second),0);
  assert.equal(call('WSASocketW',[2,1,6,0,0,1]),0xffffffff);
  assert.equal(call('WSAGetLastError'),10093,'last cleanup releases process startup');
  assert.equal(call('WSACleanup'),0xffffffff,'extra cleanup does not underflow');
  console.log('PASS WSASocketW native creation/errors, six-argument ABI, shared startup/cleanup and thread last-error');
})().catch(error=>{console.error(error);process.exitCode=1;});
