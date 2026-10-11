'use strict';
const assert = require('node:assert/strict');
const path = require('node:path');
const runtime = path.resolve(__dirname, '../tools/wine-assembly');
const {compileSrcWasm} = require(path.join(runtime, 'test/compile-src'));
const {createHostImports} = require(path.join(runtime, 'lib/host-imports'));
const apiTable = require(path.join(runtime, 'src/api_table.json'));
const {TheseusLocalServerWire} = require('./local_server_wire');
// Node doesn't supply an Origin. Use its documented WebSocketInit headers in
// this contract test; the real browser supplies Origin itself.
const NativeWebSocket = WebSocket;
global.WebSocket = class extends NativeWebSocket {
  constructor(url, protocols) { super(url, {protocols, headers: {Origin: 'http://127.0.0.1:8766'}}); }
};
const extra = String.raw`
  (func (export "network_init")
    (global.set $image_base (i32.const 0x00400000))
    (call $heap_init (i32.const 0x01000000)))
  (func (export "network_call") (param i32 i32 i32 i32 i32 i32)
    (call $dispatch_api_table (local.get 0) (local.get 1) (local.get 2)
      (local.get 3) (local.get 4) (local.get 5) (i32.const 0)))
  (func (export "network_route") (param i32 i32) (result i32)
    (call $vsock_route_to_wire (local.get 0) (local.get 1)))
`;

(async () => {
  const module = await WebAssembly.compile(compileSrcWasm((name, source) => name === '13-exports.wat' ? source + extra : source));
  const memory = new WebAssembly.Memory({initial: 8192, maximum: 8192, shared: true});
  const wire = new TheseusLocalServerWire({webSocketUrl: process.argv[2],udpPorts:[9401]});
  await wire.ready;
  try {
    const ctx = {getMemory: () => memory.buffer, vlanWire: wire, onExit() {}};
    const imports = createHostImports(ctx);
    imports.host.memory = memory;
    const instance = await WebAssembly.instantiate(module, imports), e = instance.exports;
    ctx.exports = e;
    e.network_init(); e.set_api_log(0);
    const stack = e.guest_alloc(256) >>> 0, data = e.guest_alloc(131072) >>> 0;
    const call = (name, args = []) => {
      const api = apiTable.find(a => a.name === name);
      e.set_esp(stack);
      args.forEach((v, i) => e.guest_write32(stack + 4 + 4 * i, v));
      e.network_call(api.id, ...Array.from({length: 5}, (_, i) => args[i] || 0));
      assert.equal(e.get_esp(), stack + 4 + 4 * api.nargs, `${name} ABI`);
      return e.get_eax() | 0;
    };
    assert.equal(call('WSAStartup', [0x202, data]), 0);
    const address = data + 512, output = data + 1024, one = data + 1200;
    function sockaddr(ip = 0x0100007f, port = 9200) {
      e.guest_write16(address, 2);
      e.guest_write16(address + 2, (port >> 8) | (port << 8));
      e.guest_write32(address + 4, ip);
    }
    const socket = () => {
      const s = call('socket', [2, 1, 6]);
      e.guest_write32(one, 1);
      assert.equal(call('ioctlsocket', [s, 0x8004667e, one]), 0);
      return s;
    };
    const refusal = () => {
      const s = socket(), before = wire.stats.sentFrames;
      assert.equal(call('connect', [s, address, 16]), -1);
      assert.equal(call('WSAGetLastError'), 10061);
      assert.equal(wire.stats.sentFrames, before, 'unconfigured loopback never reaches host');
      call('closesocket', [s]);
    };
    sockaddr(); refusal();
    for (const invalid of [0, -1, 65536]) assert.equal(e.set_vlan_loopback_port(invalid, 1), 0);
    assert.equal(e.set_vlan_loopback_port(9200, 1), 1);
    assert.equal(e.set_vlan_loopback_port(9200, 1), 1);
    const other = (await WebAssembly.instantiate(module, imports)).exports;
    assert.equal(other.network_route(0x7f000001, 9200), 1, 'another Wasm instance shares configured ports');
    for (const ip of [0x7f000002, 0x0a000001, 0]) assert.equal(other.network_route(ip, 9200), 0);
    const listener = socket();
    assert.equal(call('bind', [listener, address, 16]), 0);
    assert.equal(call('listen', [listener, 2]), 0);
    assert.equal(other.network_route(0x7f000001, 9200), 0, 'guest listener wins');
    const local = socket(), before = wire.stats.sentFrames;
    assert.equal(call('connect', [local, address, 16]), 0);
    const accepted = call('accept', [listener, 0, 0]);
    assert.notEqual(accepted, -1);
    assert.equal(wire.stats.sentFrames, before);
    for (const s of [local, accepted, listener]) call('closesocket', [s]);
    e.set_vlan_loopback_port(9200, 0); refusal();
    e.set_vlan_loopback_port(9200, 1);
    sockaddr(0x0200007f); refusal(); sockaddr();
    const s = socket(), event = call('WSACreateEvent');
    call('WSAEventSelect', [s, event, 0x33]);
    assert.equal(call('connect', [s, address, 16]), -1);
    assert.equal(call('WSAGetLastError'), 10035);
    const tick = async () => { await new Promise(r => setTimeout(r, 3)); e.vlan_pump(); };
    let connected = false;
    for (let i = 0; i < 2000; i++) {
      await tick();
      call('WSAEnumNetworkEvents', [s, event, output]);
      if (e.guest_read32(output) & 16) { assert.equal(e.guest_read32(output + 20), 0); connected = true; break; }
    }
    assert.ok(connected, 'TCP connect completed through Wasm and the JS wire');
    const body = Buffer.alloc(76813);
    for (let i = 0; i < body.length; i++) body[i] = i & 255;
    const sendBuffer = data + 4096, recvBuffer = data + 90000;
    new Uint8Array(memory.buffer, e.guest_to_wasm(sendBuffer), body.length).set(body);
    let offset = 0, fin = false, eof = false;
    const received = [];
    for (let iteration = 0; iteration < 10000 && !eof; iteration++) {
      await tick();
      if (offset < body.length) {
        const n = call('send', [s, sendBuffer + offset, body.length - offset, 0]);
        if (n < 0) assert.equal(call('WSAGetLastError'), 10035); else offset += n;
      } else if (!fin) { assert.equal(call('shutdown', [s, 1]), 0); fin = true; }
      while (true) {
        const n = call('recv', [s, recvBuffer, 16384, 0]);
        if (n < 0) { assert.equal(call('WSAGetLastError'), 10035); break; }
        if (n === 0) { eof = true; break; }
        received.push(Buffer.from(new Uint8Array(memory.buffer, e.guest_to_wasm(recvBuffer), n)));
      }
    }
    assert.ok(eof, 'ordered remote EOF after all bytes');
    assert.deepEqual(Buffer.concat(received), Buffer.concat([body, Buffer.from('after-eof')]));
    call('closesocket', [s]); call('WSACloseEvent', [event]);
    // Exercise the same bridge with the original client's event-based
    // overlapped APIs. While waiting, the guest calls only kernel waits;
    // actual browser scheduler pumping must still move the TCP stream.
    const vm=require('node:vm'),fs=require('node:fs');
    const hostContext={console,setTimeout,clearTimeout,performance};
    vm.runInNewContext(fs.readFileSync(path.join(runtime,'host.js'),'utf8')+'\n;globalThis.WineAssembly=WineAssembly;',hostContext);
    const scheduler=new hostContext.WineAssembly();scheduler.running=true;scheduler.instance=instance;scheduler.hostCtx=ctx;
    const asyncSocket=socket(),connectEvent=call('WSACreateEvent');
    call('WSAEventSelect',[asyncSocket,connectEvent,16]);assert.equal(call('connect',[asyncSocket,address,16]),-1);
    connected=false;
    for(let i=0;i<2000;i++) {
      await tick();call('WSAEnumNetworkEvents',[asyncSocket,connectEvent,output]);
      if(e.guest_read32(output)&16){assert.equal(e.guest_read32(output+20),0);connected=true;break;}
    }
    assert(connected);call('WSAEventSelect',[asyncSocket,0,0]);call('WSACloseEvent',[connectEvent]);
    const txEvent=call('WSACreateEvent'),rxEvent=call('WSACreateEvent');
    const txOv=data+2048,rxOv=data+2080,txVec=data+2128,rxVec=data+2160,bytes=data+2200,rxFlags=data+2204;
    for(let i=0;i<20;i+=4){e.guest_write32(txOv+i,0);e.guest_write32(rxOv+i,0);}
    e.guest_write32(txOv+16,txEvent);e.guest_write32(rxOv+16,rxEvent);e.guest_write32(rxFlags,0);
    e.guest_write32(txVec,40000);e.guest_write32(txVec+4,sendBuffer);e.guest_write32(txVec+8,body.length-40000);e.guest_write32(txVec+12,sendBuffer+40000);
    e.guest_write32(rxVec,16384);e.guest_write32(rxVec+4,recvBuffer);
    assert.equal(call('WSARecv',[asyncSocket,rxVec,1,bytes,rxFlags,rxOv,0]),-1);assert.equal(call('WSAGetLastError'),997);
    assert.equal(call('WSASend',[asyncSocket,txVec,2,bytes,0,txOv,0]),-1);assert.equal(call('WSAGetLastError'),997);
    const asyncReceived=[];fin=false;eof=false;
    for(let iteration=0;iteration<10000&&!eof;iteration++) {
      await new Promise(resolve=>setTimeout(resolve,3));
      await scheduler._pumpSocketIoAtBoundary();
      if(!fin&&call('WaitForSingleObject',[txEvent,0])===0) {
        assert.equal(call('WSAGetOverlappedResult',[asyncSocket,txOv,bytes,0,rxFlags]),1);
        assert.equal(e.guest_read32(bytes),body.length);assert.equal(call('shutdown',[asyncSocket,1]),0);fin=true;
      }
      if(call('WaitForSingleObject',[rxEvent,0])!==0)continue;
      assert.equal(call('WSAGetOverlappedResult',[asyncSocket,rxOv,bytes,0,rxFlags]),1);
      const n=e.guest_read32(bytes);if(!n){eof=true;break;}
      asyncReceived.push(Buffer.from(new Uint8Array(memory.buffer,e.guest_to_wasm(recvBuffer),n)));
      const result=call('WSARecv',[asyncSocket,rxVec,1,bytes,rxFlags,rxOv,0]);
      if(result<0)assert.equal(call('WSAGetLastError'),997);else assert.equal(result,0);
    }
    assert(eof,'overlapped EOF while scheduler pumps parked guest waits');
    assert.deepEqual(Buffer.concat(asyncReceived),Buffer.concat([body,Buffer.from('after-eof')]));
    for(const h of [txEvent,rxEvent])call('WSACloseEvent',[h]);call('closesocket',[asyncSocket]);
    const udp=call('socket',[2,2,17]),udpStorage=e.guest_alloc(140000)>>>0;
    e.guest_write32(one,1);call('ioctlsocket',[udp,0x8004667e,one]);
    sockaddr(0x0100007f,9401);
    for(const size of [0,15,4096,4097,65507]) {
      const payload=Buffer.from(Array.from({length:size},(_,i)=>(i*19+size)&255));
      payload.forEach((b,i)=>e.guest_write8(udpStorage+i,b));
      const split=Math.floor(size/3);
      e.guest_write32(txVec,split);e.guest_write32(txVec+4,udpStorage);
      e.guest_write32(txVec+8,size-split);e.guest_write32(txVec+12,udpStorage+split);
      assert.equal(call('WSASendTo',[udp,txVec,2,bytes,0,address,16,0,0]),0);assert.equal(e.guest_read32(bytes),size);
      let n=-1;
      for(let i=0;i<2000;i++) {await tick();e.guest_write32(output+32,16);
        n=call('recvfrom',[udp,udpStorage+70000,65507,0,output,output+32]);
        if(n>=0)break;assert.equal(call('WSAGetLastError'),10035);}
      assert.equal(n,size,'one UDP packet returned through the shipped wire');
      assert.deepEqual(Buffer.from(Array.from({length:n},(_,i)=>e.guest_read8(udpStorage+70000+i))),payload);
      assert.equal(e.guest_read32(output+4)>>>0,0x0100007f);
      assert.equal((e.guest_read32(output+2)&0xffff),0xb924);assert.equal(e.guest_read32(output+32),16);
    }
    // A native service observes the bridge's ephemeral source port. The game
    // then probes itself at that port; exercise the actual guest receive path.
    const mappings = wire.snapshot().udpMappings;
    assert.equal(mappings.length, 1);
    const mappedPort = mappings[0].nativePort, mappedRead = call('WSACreateEvent');
    assert.equal(call('WSAEventSelect', [udp, mappedRead, 1]), 0);
    const beforeMapped = wire.stats.sentFrames;
    for (const size of [0, 2, 10, 4097, 65507]) {
      sockaddr(0x0100000a, mappedPort);
      const payload = Buffer.from(Array.from({length:size}, (_,i)=>(i*23+size)&255));
      payload.forEach((b,i)=>e.guest_write8(udpStorage+i,b));
      e.guest_write32(txVec,size); e.guest_write32(txVec+4,udpStorage);
      assert.equal(call('WSASendTo',[udp,txVec,1,bytes,0,address,16,0,0]),0);
      let ready = false;
      for (let i=0;i<2000;i++) {
        await tick(); call('WSAEnumNetworkEvents',[udp,mappedRead,output]);
        if (e.guest_read32(output)&1) {ready=true;break;}
      }
      assert(ready,'mapped self-probe signals FD_READ'); e.guest_write32(output+32,16);
      assert.equal(call('recvfrom',[udp,udpStorage+70000,65507,0,output,output+32]),size);
      assert.deepEqual(Buffer.from(Array.from({length:size},(_,i)=>e.guest_read8(udpStorage+70000+i))),payload);
      assert.equal(e.guest_read32(output+4)>>>0,0x0100000a);
      assert.equal(e.guest_read32(output+2)&0xffff,((mappedPort&255)<<8)|(mappedPort>>>8),
        'NAT self-probe returns from the observed public port');
    }
    assert.equal(wire.stats.sentFrames,beforeMapped+5);
    assert.equal(wire.stats.mappedSelfDatagrams,5);
    assert.equal(wire.stats.locallyDeliveredDatagrams,0);
    call('WSAEventSelect',[udp,0,0]);call('WSACloseEvent',[mappedRead]);
    assert.equal(wire.stats.unsupportedDatagrams,0);call('closesocket',[udp]);
    // X2 sends UDP to its own advertised address while entering a field.
    // Exercise the real recvfrom/event path, including a distinct local socket.
    const self=call('socket',[2,2,17]),peer=call('socket',[2,2,17]);
    for(const [s,port] of [[self,8772],[peer,8773]]) {
      sockaddr(0x0100000a,port);assert.equal(call('bind',[s,address,16]),0);
      e.guest_write32(one,1);assert.equal(call('ioctlsocket',[s,0x8004667e,one]),0);
    }
    const readEvent=call('WSACreateEvent');assert.equal(call('WSAEventSelect',[self,readEvent,1]),0);
    const sentBefore=wire.stats.sentFrames;
    for(const [size,receiver,port] of [[0,self,8772],[10,self,8772],[4097,peer,8773],[65507,self,8772]]) {
      sockaddr(0x0100000a,port);
      const payload=Buffer.from(Array.from({length:size},(_,i)=>(i*31+size)&255));
      payload.forEach((b,i)=>e.guest_write8(udpStorage+i,b));
      const split=Math.floor(size/2);
      e.guest_write32(txVec,split);e.guest_write32(txVec+4,udpStorage);
      e.guest_write32(txVec+8,size-split);e.guest_write32(txVec+12,udpStorage+split);
      assert.equal(call('WSASendTo',[self,txVec,2,bytes,0,address,16,0,0]),0);
      assert.equal(e.guest_read32(bytes),size);e.vlan_pump();
      if(receiver===self){
        call('WSAEnumNetworkEvents',[self,readEvent,output]);
        assert.equal(e.guest_read32(output)&1,1,'local UDP signals FD_READ');
      }
      e.guest_write32(output+32,16);
      assert.equal(call('recvfrom',[receiver,udpStorage+70000,65507,0,output,output+32]),size);
      assert.deepEqual(Buffer.from(Array.from({length:size},(_,i)=>e.guest_read8(udpStorage+70000+i))),payload);
      assert.equal(e.guest_read32(output+4)>>>0,0x0100000a);
      assert.equal(e.guest_read32(output+2)&0xffff,0x4422,'source port remains 8772');
    }
    assert.equal(wire.stats.sentFrames,sentBefore,'self-unicast does not reach native network');
    assert.equal(wire.stats.locallyDeliveredDatagrams,4);assert.equal(wire.stats.unsupportedDatagrams,0);
    call('WSAEventSelect',[self,0,0]);call('WSACloseEvent',[readEvent]);
    call('closesocket',[self]);call('closesocket',[peer]);sockaddr();
    // Transport loss must signal the guest; a later connect must be refused.
    wire.close(); e.vlan_pump();
    const lost = socket();
    assert.equal(call('connect', [lost, address, 16]), -1);
    e.vlan_pump();
    assert.equal(call('connect', [lost, address, 16]), -1);
    assert.equal(call('WSAGetLastError'), 10061);
    call('closesocket', [lost]);
    console.log('PASS actual Wasm Winsock -> shipped JS wire -> local TCP/UDP: stream duplex/credit/EOF/scheduler, UDP scatter/zero/4097/65507-byte datagrams and recvfrom source addresses, isolation and disconnect');
  } finally { wire.close(); }
})().catch(error => {console.error(error); process.exitCode = 1;});
