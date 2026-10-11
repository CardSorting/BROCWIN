'use strict';
const assert=require('node:assert/strict'),path=require('node:path');
const {Worker}=require('node:worker_threads');
const root=path.resolve(__dirname,'../tools/wine-assembly');
const {compileSrcWasm}=require(path.join(root,'test/compile-src'));
const {createHostImports}=require(path.join(root,'lib/host-imports'));
const {processSharedCtx}=require(path.join(root,'lib/worker-imports'));
const {ThreadManager}=require(path.join(root,'lib/thread-manager'));
const RPC=require(path.join(root,'lib/guest-rpc'));
const R=require(path.join(root,'lib/region-map.generated'));
const sigs=require(path.join(root,'lib/host-import-sigs.generated.json')).sigs;
const apis=require(path.join(root,'src/api_table.json'));
const native=require('./reference/winsock-overlapped.json');
for(const name of ['winsock-overlapped-x86.json','winsock-overlapped-pinvoke-x64.json']) {
  for(const row of require('./reference/'+name).cases) {
    const expected=native.cases.find(x=>x.case===row.case);assert(expected,row.case);
    for(const [key,value] of Object.entries(row))assert.equal(value,expected[key],name+' '+row.case+' '+key);
  }
}
const extra=String.raw`
  (func (export "io_init")
    (global.set $image_base (i32.const 0x00400000))
    (call $heap_init (i32.const 0x01000000)))
  (func (export "io_thread")
    (global.set $image_base (i32.const 0x00400000))
    (global.set $reg_base (region.addr $REGFILE 256))
    (global.set $current_thread_id (i32.const 2)))
  (func (export "io_call") (param i32 i32 i32 i32 i32 i32)
    (call $dispatch_api_table (local.get 0) (local.get 1) (local.get 2)
      (local.get 3) (local.get 4) (local.get 5) (i32.const 0)))
  (func (export "io_map") (param $guest i32) (param $backing i32)
    (call $guest_page_publish_range (local.get $guest) (i32.const 4096) (local.get $backing) (i32.const 4)))
  (func (export "io_ring") (param $socket i32) (param $buffer i32) (param $size i32) (param $head i32) (result i32)
    (local $rec i32) (local $old i32)
    (local.set $rec (call $vsock_rec (call $vsock_index (local.get $socket))))
    (local.set $old (load.field VSock rx_buf (local.get $rec)))
    (store.field VSock rx_buf (local.get $rec) (local.get $buffer))
    (store.field VSock rx_cap (local.get $rec) (local.get $size))
    (store.field VSock rx_head (local.get $rec) (local.get $head))
    (local.get $old))
  (func (export "io_ring_dword") (param $socket i32) (param $value i32) (result i32)
    (local $idx i32) (local.set $idx (call $vsock_index (local.get $socket)))
    (call $vsock_ring_put32 (local.get $idx) (local.get $value))
    (local.set $value (call $vsock_ring_get32 (local.get $idx) (i32.const 0)))
    (call $vsock_ring_skip (local.get $idx) (i32.const 4))
    (local.get $value))
`;
(async()=>{
  let baseline;
  if(process.env.THESEUS_SOCKET_RING_BASELINE==='1') {
    baseline=require('node:child_process').execFileSync('git',['show','HEAD:src/09d-winsock.wat'],{cwd:root,encoding:'utf8'});
  }
  const module=await WebAssembly.compile(compileSrcWasm((name,s)=>{
    if(name==='13-exports.wat')return s+extra;
    if(name==='09d-winsock.wat' && baseline) {
      const begin='  (func $vsock_ring_write ',end='  ;; Discard n bytes';
      return s.slice(0,s.indexOf(begin))+baseline.slice(baseline.indexOf(begin),baseline.indexOf(end))+s.slice(s.indexOf(end));
    }
    return s;
  }));
  for(const backend of ['single-thread','thread-manager']) {
    const memory=new WebAssembly.Memory({initial:8192,maximum:8192,shared:true});
    const ctx={getMemory:()=>memory.buffer,onExit(){}};
    const imports=createHostImports(ctx);imports.host.memory=memory;
    let manager;
    if(backend==='thread-manager') {
      for(const [host,method] of Object.entries({create_event:'createEvent',set_event:'setEvent',reset_event:'resetEvent',
        wait_single:'waitSingle',sync_handle_type:'syncHandleType'})) imports.host[host]=(...args)=>manager[method](...args);
      ctx.closeSyncHandle=h=>manager.closeSyncHandle(h);
    }
    const instance=await WebAssembly.instantiate(module,imports),e=instance.exports;ctx.exports=e;e.io_init();e.set_api_log(0);
    if(backend==='thread-manager')manager=new ThreadManager(module,memory,instance,()=>imports,{log(){}});
    const stack=e.guest_alloc(256)>>>0,work=e.guest_alloc(1024)>>>0,storage=e.guest_alloc(180000)>>>0;
    const call=(name,args=[],ex=e,park=false)=>{
      const api=apis.find(a=>a.name===name);assert(api,name);
      ex.clear_yield();ex.set_esp(stack);args.forEach((v,i)=>ex.guest_write32(stack+4+i*4,v));
      ex.io_call(api.id,...Array.from({length:5},(_,i)=>args[i]||0));
      assert.equal(ex.get_esp()>>>0,park?stack:stack+4+api.nargs*4,backend+' '+name+' stdcall');
      assert.equal(ex.get_yield_reason(),park?8:0,backend+' '+name+' park');
      return ex.get_eax()|0;
    };
    const wr=(p,v)=>e.guest_write32(p,v),rd=p=>e.guest_read32(p)>>>0;
    const put=(p,s)=>Buffer.from(s).forEach((v,i)=>e.guest_write8(p+i,v));
    const get=(p,n)=>Buffer.from(Array.from({length:n},(_,i)=>e.guest_read8(p+i)));
    const error=()=>call('WSAGetLastError');
    call('WSAStartup',[0x202,work]);
    let port=37000;
    const pair=(socketFlags=1)=>{
      const address=work+768;port++;
      e.guest_write16(address,2);e.guest_write16(address+2,((port&255)<<8)|(port>>>8));wr(address+4,0x0100000a);
      const listener=call('socket',[2,1,6]),client=call('WSASocketW',[2,1,6,0,0,socketFlags]);
      assert.equal(call('bind',[listener,address,16]),0);assert.equal(call('listen',[listener,2]),0);
      assert.equal(call('connect',[client,address,16]),0);
      const peer=call('accept',[listener,0,0]);assert(peer>0);call('closesocket',[listener]);return [client,peer];
    };
    const vec=work,ov=work+64,count=work+128,flags=work+132;
    const event=call('WSACreateEvent');
    const init=(lengths=[3,5],at=storage,overlap=ov,ev=event)=>{
      lengths.forEach((n,i)=>{wr(vec+i*8,n);wr(vec+i*8+4,at);at+=n;});
      for(let i=0;i<20;i+=4)wr(overlap+i,0);wr(overlap+16,ev);wr(count,0x1234);wr(flags,0);call('ResetEvent',[ev]);
    };
    const observe=(label,result,rows=native.cases)=>{
      const row=rows.find(x=>x.case===label);assert(row,label);
      const got={result,error:error(),count:rd(count),flags:rd(flags),internal:rd(ov),transferred:rd(ov+4),event:call('WaitForSingleObject',[event,0])};
      for(const k of Object.keys(got))assert.equal(got[k],row[k],`${backend} ${label} ${k}`);
    };
    const udp=call('socket',[2,2,17]),to=work+800,packets=[];
    let writable=true;
    ctx.vlanWire={send:b=>{if(!writable)return false;packets.push(Buffer.from(b));return true;},peek:()=>null,commit(){}};
    e.guest_write16(to,2);e.guest_write16(to+2,0xb924);wr(to+4,0x0100007f); // 9401
    for(const row of require('./reference/wsasendto.json').cases) {
      const lengths=row.case==='scatter-sync'||row.case==='scatter-overlapped'?[1,14]:
        row.case==='maximum-datagram'?[32768,32739]:row.case==='oversize-datagram'?[32768,32740]:
        row.case==='empty-datagram'?[0,0]:row.case==='empty-overlapped'?[0]:[1];
      init(lengths);wr(ov,0x12345678);wr(ov+4,0x23456789);
      let at=storage;const payload=[];
      lengths.forEach((n,i)=>{const b=Buffer.alloc(n,65+i);put(at,b);at+=n;payload.push(b);});
      const before=packets.length;
      const result=call('WSASendTo',[udp,vec,row.case==='zero-buffers'?0:lengths.length,count,0,to,
        row.case==='short-address'?8:16,row.case.includes('overlapped')?ov:0,0]);
      const got={result,error:error(),count:rd(count),internal:rd(ov),transferred:rd(ov+4),event:call('WaitForSingleObject',[event,0])};
      for(const [k,v] of Object.entries(got))assert.equal(v,row[k],`${backend} UDP ${row.case} ${k}`);
      assert.equal(packets.length-before,result===0?1:0,'one complete datagram or no send');
      if(result===0) {
        const packet=packets.at(-1);assert.equal(packet.readUInt32LE(4),6);
        assert.equal(packet.readUInt32LE(16),0x7f000001);assert.equal(packet.readUInt32LE(20),9401);
        assert.deepEqual(packet.subarray(28),Buffer.concat(payload));
      }
    }
    // Queue pressure retains captured descriptors and emits no partial packet.
    init([1,14]);put(storage,'abcdefghijklmno');writable=false;
    assert.equal(call('WSASendTo',[udp,vec,2,count,0,to,16,ov,0]),-1);assert.equal(error(),997);
    wr(vec,0);wr(vec+8,0);writable=true;e.vlan_pump();
    assert.equal(call('WSAGetOverlappedResult',[udp,ov,count,0,flags]),1);
    assert.equal(rd(count),15);assert.equal(packets.at(-1).subarray(28).toString(),'abcdefghijklmno');
    // A real Worker must carry all nine x86 arguments / eleven host RPC args.
    init([1,14]);const udpWorker=new Worker(`
      const {parentPort,workerData:d}=require('node:worker_threads'),RPC=require(d.rpc);
      const proxy=RPC.createWorkerImports(d.memory,d.sigs,m=>parentPort.postMessage(m),{slot:3});proxy.imports.host.memory=d.memory;
      const ex=new WebAssembly.Instance(d.module,proxy.imports).exports;ex.io_thread();ex.set_api_log(0);ex.set_esp(d.stack);
      d.args.forEach((v,i)=>ex.guest_write32(d.stack+4+i*4,v));ex.io_call(d.id,...d.args.slice(0,5));
      parentPort.postMessage({done:true,result:ex.get_eax(),esp:ex.get_esp()});
    `,{eval:true,workerData:{rpc:path.join(root,'lib/guest-rpc'),sigs,module,memory,stack,
      id:apis.find(a=>a.name==='WSASendTo').id,args:[udp,vec,2,count,0,to,16,ov,0]}});
    const udpBroker=RPC.createMainBroker(memory,imports.host,sigs);
    try {
      const got=await new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('UDP Worker timeout')),15000);
        udpWorker.on('error',err=>{clearTimeout(timer);reject(err);});udpWorker.on('message',m=>{
          if(m.t==='rpc')udpBroker.serveRpc(m.slot);else if(m.done){clearTimeout(timer);resolve(m);}});});
      assert.equal(got.result,0);assert.equal(got.esp,stack+40);assert.equal(rd(count),15);
      assert.equal(packets.at(-1).subarray(28).toString(),'abcdefghijklmno');
    } finally {await udpWorker.terminate();}
    call('closesocket',[udp]);delete ctx.vlanWire;
    let [client,peer]=pair();init();call('WSASetLastError',[0x1234]);
    observe('receive-pending',call('WSARecv',[client,vec,2,count,flags,ov,0]));
    wr(flags,0x4321);observe('pending-query',call('WSAGetOverlappedResult',[client,ov,count,0,flags]));
    wr(vec,0);wr(vec+8,0);put(storage+32,'abcdef');assert.equal(call('send',[peer,storage+32,6,0]),6);e.vlan_pump();
    observe('receive-complete',call('WSAGetOverlappedResult',[client,ov,count,0,flags]));assert.equal(get(storage,6).toString(),'abcdef');
    init([3,3]);observe('send-complete',call('WSASend',[client,vec,2,count,0,ov,0]));
    assert.equal(call('recv',[peer,storage+32,6,0]),6);assert.equal(get(storage+32,6).toString(),'abcdef');
    wr(count,0x1234);wr(flags,0x4321);observe('send-query',call('WSAGetOverlappedResult',[client,ov,count,0,flags]));
    init([0,0]);observe('zero-receive-pending',call('WSARecv',[client,vec,2,count,flags,ov,0]));
    put(storage+32,'Z');call('send',[peer,storage+32,1,0]);e.vlan_pump();
    observe('zero-receive-complete',call('WSAGetOverlappedResult',[client,ov,count,0,flags]));
    assert.equal(call('recv',[client,storage+32,1,0]),1);assert.equal(get(storage+32,1).toString(),'Z');
    init([3]);observe('close-pending',call('WSARecv',[client,vec,1,count,flags,ov,0]));call('closesocket',[client]);
    wr(count,0x1234);wr(flags,0x4321);observe('close-query',call('WSAGetOverlappedResult',[client,ov,count,0,flags]));call('closesocket',[peer]);
    // Error cases retain exactly the outputs observed from the native API.
    const unconnected=call('WSASocketW',[2,1,6,0,0,1]);[client,peer]=pair();
    for(const row of native.errors.filter(x=>x.case!=='reset-query')) {
      init([4]);wr(ov,0x12345678);wr(ov+4,0x23456789);
      if(row.initialEvent)call('SetEvent',[event]);
      if(row.case==='invalid-event')wr(ov+16,0x1234);
      let target=row.case.startsWith('unconnected')?unconnected:row.case==='invalid-socket'?-1:client;
      if(row.case==='send-shutdown')call('shutdown',[client,1]);
      if(row.case==='receive-shutdown')call('shutdown',[client,0]);
      observe(row.case,call(row.receive?'WSARecv':'WSASend',[target,vec,row.case==='zero-buffer-count'?0:1,count,row.receive?flags:0,ov,0]),native.errors);
    }
    call('closesocket',[unconnected]);call('closesocket',[client]);call('closesocket',[peer]);
    [client,peer]=pair();init([8]);call('WSARecv',[client,vec,1,count,flags,ov,0]);call('closesocket',[peer]);e.vlan_pump();
    wr(flags,0x4321);observe('reset-query',call('WSAGetOverlappedResult',[client,ov,count,0,flags]),native.errors);call('closesocket',[client]);
    // One large logical send must survive several receive-window refills.
    [client,peer]=pair();const size=76813;for(let i=0;i<size;i++)e.guest_write8(storage+i,(i*73+19)&255);
    init([40000,size-40000]);assert.equal(call('WSASend',[client,vec,2,count,0,ov,0]),-1);assert.equal(error(),997);
    assert.equal(rd(count),0x1234);assert.equal(call('WaitForSingleObject',[event,0]),258);
    wr(vec,0);wr(vec+8,0);let offset=0;
    while(offset<size) {const n=call('recv',[peer,storage+90000+offset,size-offset,0]);assert(n>0);offset+=n;}
    assert.deepEqual(get(storage+90000,size),get(storage,size));
    assert.equal(call('WSAGetOverlappedResult',[client,ov,count,0,flags]),1);assert.equal(rd(count),size);
    // FIFO receives, blocking retry, fWait, EOF and thread cancellation.
    const ov2=work+96,event2=call('WSACreateEvent');init([4]);call('WSARecv',[client,vec,1,count,flags,ov,0]);
    init([4],storage+8,ov2,event2);call('WSARecv',[client,vec,1,count,flags,ov2,0]);put(storage+32,'123456');call('send',[peer,storage+32,6,0]);e.vlan_pump();
    assert.equal(rd(ov+4),4);assert.equal(rd(ov2+4),2);assert.equal(get(storage,4).toString(),'1234');assert.equal(get(storage+8,2).toString(),'56');
    assert.equal(call('WaitForSingleObject',[event2,0]),0,'second (possibly odd) kernel event signaled');
    init([8]);call('WSARecv',[client,vec,1,count,flags,0,0],e,true);put(storage+32,'sync');call('send',[peer,storage+32,4,0]);
    assert.equal(call('WSARecv',[client,vec,1,count,flags,0,0]),0);assert.equal(rd(count),4);
    init([8]);call('WSARecv',[client,vec,1,count,flags,ov,0]);call('WSAGetOverlappedResult',[client,ov,count,1,flags],e,true);
    put(storage+32,'wait');call('send',[peer,storage+32,4,0]);assert.equal(call('WSAGetOverlappedResult',[client,ov,count,1,flags]),1);assert.equal(rd(count),4);
    init([8]);call('WSARecv',[client,vec,1,count,flags,ov,0]);e.vsock_io_cancel_thread(1);
    assert.equal(call('WSAGetOverlappedResult',[client,ov,count,0,flags]),0);assert.equal(error(),995);assert.equal(rd(ov),0xc0000120);
    init([8]);call('WSARecv',[client,vec,1,count,flags,ov,0]);call('shutdown',[peer,1]);e.vlan_pump();
    assert.equal(call('WSAGetOverlappedResult',[client,ov,count,0,flags]),1);assert.equal(rd(count),0);
    call('closesocket',[client]);call('closesocket',[peer]);
    // A synchronous socket ignores OVERLAPPED/completion arguments.
    [client,peer]=pair(0);init([4]);wr(work+700,1);call('ioctlsocket',[client,0x8004667e,work+700]);
    assert.equal(call('WSARecv',[client,vec,1,count,flags,0xffffffff,0xffffffff]),-1);assert.equal(error(),10035);
    call('closesocket',[client]);call('closesocket',[peer]);
    // Both user vectors and internal rings may cross nonadjacent physical pages.
    [client,peer]=pair();const ga=0x68000000,backing=R.BASE.VIRTUAL_BACKING_BASE,mem=new Uint8Array(memory.buffer);
    for(let i=0;i<8;i++){e.io_map(ga+i*4096,backing+i*8192);mem.fill(0xa5,backing+i*8192,backing+(i+1)*8192);}
    const old=e.io_ring(peer,ga,8192,8190)>>>0;
    assert.equal(e.io_ring_dword(peer,0x12345678)>>>0,0x12345678);
    const sample=Buffer.from(Array.from({length:5000},(_,i)=>(i*17+37)&255));put(ga+3*4096-3,sample);
    init([5000],ga+3*4096-3);assert.equal(call('WSASend',[client,vec,1,count,0,ov,0]),0);
    init([4998,2],ga+5*4096-2);assert.equal(call('WSARecv',[peer,vec,2,count,flags,ov,0]),0);
    assert.deepEqual(get(ga+5*4096-2,5000),sample);
    for(let i=0;i<8;i++)assert(mem.subarray(backing+i*8192+4096,backing+(i+1)*8192).every(v=>v===0xa5),'physical neighbor preserved');
    e.io_ring(peer,old,16384,0);call('closesocket',[client]);call('closesocket',[peer]);
    // Cooperative thread contexts share request ownership, while API registers
    // and last error belong to the calling instance.
    [client,peer]=pair();const ctx2={...processSharedCtx(ctx),getMemory:()=>memory.buffer,onExit(){}};
    const imports2=createHostImports(ctx2);imports2.host.memory=memory;
    for(const key of ['sync_handle_type','set_event','reset_event'])imports2.host[key]=imports.host[key];
    const second=new WebAssembly.Instance(module,imports2).exports;ctx2.exports=second;second.io_thread();second.set_api_log(0);
    init([8]);assert.equal(call('WSARecv',[client,vec,1,count,flags,ov,0],second),-1);
    put(storage+32,'thread');call('send',[peer,storage+32,6,0]);e.vlan_pump();assert.equal(rd(ov+4),6);
    // Real Worker RPC submits the original seven-argument ABI, and the main
    // process host completes that worker's event without a guest recv retry.
    init([8]);const worker=new Worker(`
      const {parentPort,workerData:d}=require('node:worker_threads');const RPC=require(d.rpc);
      const proxy=RPC.createWorkerImports(d.memory,d.sigs,m=>parentPort.postMessage(m),{slot:3});proxy.imports.host.memory=d.memory;
      const ex=new WebAssembly.Instance(d.module,proxy.imports).exports;ex.io_thread();ex.set_api_log(0);ex.set_esp(d.stack);
      d.args.forEach((v,i)=>ex.guest_write32(d.stack+4+i*4,v));ex.io_call(d.id,...d.args.slice(0,5));
      parentPort.postMessage({done:true,result:ex.get_eax(),esp:ex.get_esp()});
    `,{eval:true,workerData:{rpc:path.join(root,'lib/guest-rpc'),sigs,module,memory,stack,
      id:apis.find(a=>a.name==='WSARecv').id,args:[client,vec,1,count,flags,ov,0]}});
    const broker=RPC.createMainBroker(memory,imports.host,sigs);
    try {
      const got=await new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('Winsock Worker RPC timeout')),15000);
        worker.on('error',err=>{clearTimeout(timer);reject(err);});worker.on('message',m=>{
          if(m.t==='rpc')broker.serveRpc(m.slot);else if(m.done){clearTimeout(timer);resolve(m);}});});
      assert.equal(got.result,-1);assert.equal(got.esp,stack+32);put(storage+32,'worker');call('send',[peer,storage+32,6,0]);e.vlan_pump();
      assert.equal(rd(ov+4),6);assert.equal(call('WaitForSingleObject',[event,0]),0);assert.equal(get(storage,6).toString(),'worker');
    } finally {await worker.terminate();}
    call('closesocket',[client]);call('closesocket',[peer]);call('WSACloseEvent',[event]);call('WSACloseEvent',[event2]);
    assert.equal(ctx.socketIO.hasPending(),false);call('WSACleanup');
    console.log('PASS '+backend+': native overlapped contracts, FIFO, 76813-byte send/backpressure, sparse rings/vectors, sync retry, EOF/reset/cancel and real Worker RPC');
  }
})().catch(error=>{console.error(error);process.exitCode=1;});
