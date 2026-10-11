'use strict';

const assert = require('node:assert/strict');
const path = require('node:path');
const runtime = path.resolve(__dirname, '../tools/wine-assembly');
const { compileSrcWasm } = require(path.join(runtime, 'test/compile-src'));
const { createHostImports } = require(path.join(runtime, 'lib/host-imports'));
const { ThreadManager } = require(path.join(runtime, 'lib/thread-manager'));
const { LoopbackSegment } = require(path.join(runtime, 'lib/vlan-wire'));
const apiTable = require(path.join(runtime, 'src/api_table.json'));
const reference = require('./reference/winsock-events.json');
const extra = String.raw`
  (func (export "events_init")
    (global.set $image_base (i32.const 0x00400000))
    (call $heap_init (i32.const 0x01000000)))
  (func (export "events_call") (param i32 i32 i32 i32 i32 i32)
    (call $dispatch_api_table (local.get 0) (local.get 1) (local.get 2)
      (local.get 3) (local.get 4) (local.get 5) (i32.const 0)))
`;

(async () => {
  const wasm = compileSrcWasm((name, source) => name === '13-exports.wat' ? source + extra : source);
  const module = await WebAssembly.compile(wasm);
  for (const backend of ['single-thread', 'thread-manager']) {
    const memory = new WebAssembly.Memory({ initial: 8192, maximum: 8192, shared: true });
    const ctx = { getMemory: () => memory.buffer, onExit() {} };
    const wire = new LoopbackSegment();
    ctx.vlanWire = wire.attach();
    const remoteWire = wire.attach();
    const imports = createHostImports(ctx);
    imports.host.memory = memory;
    let manager;
    if (backend === 'thread-manager') {
      imports.host.create_event = (manual, initial) => manager.createEvent(manual, initial);
      imports.host.set_event = handle => manager.setEvent(handle);
      imports.host.reset_event = handle => manager.resetEvent(handle);
      imports.host.wait_single = (handle, timeout) => manager.waitSingle(handle, timeout);
      imports.host.sync_handle_type = handle => manager.syncHandleType(handle);
      ctx.closeSyncHandle = handle => manager.closeSyncHandle(handle);
    }
    const instance = await WebAssembly.instantiate(module, imports);
    const e = instance.exports;
    ctx.exports = e;
    e.events_init();
    e.set_api_log(0);
    if (backend === 'thread-manager') manager = new ThreadManager(module, memory, instance, () => imports, { log() {} });
    const stack = e.guest_alloc(256) >>> 0;
    const call = (name, args = []) => {
      const api = apiTable.find(item => item.name === name);
      assert.ok(api, name);
      e.set_esp(stack);
      args.forEach((value, index) => e.guest_write32(stack + 4 + index * 4, value));
      e.events_call(api.id, ...Array.from({ length: 5 }, (_, i) => args[i] || 0));
      assert.equal(e.get_esp(), stack + 4 + api.nargs * 4, `${backend}: ${name} stack`);
      return e.get_eax() >>> 0;
    };
    let event;
    for (const row of reference.cases) {
      call('WSASetLastError', [0x1234]);
      let result;
      if (row.operation === 'create-before-startup') {
        event = call('WSACreateEvent');
        assert.equal(!!event, row.hasHandle);
        assert.equal(imports.host.sync_handle_type(event), 1);
      } else {
        if (row.operation === 'set') result = call('SetEvent', [event]);
        else if (row.operation === 'reset') result = call('ResetEvent', [event]);
        else if (row.operation.startsWith('wait')) result = call('WaitForSingleObject', [event, 0]);
        else result = call('WSACloseEvent', [row.operation === 'close-null' ? 0 : row.operation === 'close-invalid' ? 0x1234 : event]);
        assert.equal(result, row.result, `${backend}: ${row.operation}`);
      }
      assert.equal(call('WSAGetLastError'), row.error, `${backend}: ${row.operation} error`);
    }
    const a = call('WSACreateEvent'), b = call('WSACreateEvent');
    assert.notEqual(a, b, 'unnamed events have separate identities');
    assert.equal(call('SetEvent', [a]), 1);
    assert.equal(call('WaitForSingleObject', [b, 0]), 258);
    assert.equal(call('CloseHandle', [a]), 1);
    assert.equal(call('WSACloseEvent', [a]), 0, 'a kernel close ends the Winsock event lifetime');
    assert.equal(call('WSAGetLastError'), 6);
    assert.equal(call('WSACloseEvent', [b]), 1);
    const data = e.guest_alloc(32768) >>> 0;
    const output = data + 2048;
    assert.equal(call('WSAStartup', [0x202, data]), 0);
    const probe = call('socket', [2, 1, 6]);
    const probeEvent = call('WSACreateEvent');
    for (const row of reference.socketEventContracts) {
      let result;
      const targets = {'null-event': 0, 'invalid-event': 0x1234, 'valid-event': probeEvent,
        'invalid-mask': probeEvent, 'cancel-invalid-event': 0x1234, 'cancel-null': 0};
      if (row.case.startsWith('enum')) {
        const target = row.case === 'enum-null-event' ? 0 : row.case === 'enum-invalid-event' ? 0x1234 : probeEvent;
        result = call('WSAEnumNetworkEvents', [probe, target, row.case === 'enum-null-output' ? 0 : output]);
        if (result === 0) assert.equal(e.guest_read32(output), row.mask);
      } else {
        const mask = row.case.startsWith('cancel') ? 0 : row.case === 'invalid-mask' ? 0x400 : 1;
        result = call('WSAEventSelect', [probe, targets[row.case], mask]);
      }
      assert.equal(result | 0, row.result, `${backend}: ${row.case}`);
      assert.equal(call('WSAGetLastError'), row.error, `${backend}: ${row.case} error`);
    }
    assert.equal(call('closesocket', [probe]), 0);
    assert.equal(call('WSACloseEvent', [probeEvent]), 1);
    const address = data + 512;
    e.guest_write16(address, 2);
    e.guest_write16(address + 2, 0x7188); // Port 34929, in network byte order.
    e.guest_write32(address + 4, 0x0100000a);
    const listener = call('socket', [2, 1, 6]), client = call('socket', [2, 1, 6]);
    const events = [call('WSACreateEvent'), call('WSACreateEvent'), call('WSACreateEvent')];
    assert.equal(call('bind', [listener, address, 16]), 0);
    assert.equal(call('listen', [listener, 2]), 0);
    assert.equal(call('WSAEventSelect', [listener, events[0], 8]), 0);
    assert.equal(call('WSAEventSelect', [client, events[1], 0x33]), 0);
    const observe = (label, socket, event) => {
      const row = reference.loopbackTransitions.find(item => item.case === label);
      assert.equal(call('WaitForSingleObject', [event, 0]), row.wait, `${backend}: ${label} signal`);
      e.guest_write32(output + 44, 0xa5a5a5a5);
      assert.equal(call('WSAEnumNetworkEvents', [socket, event, output]), row.result);
      assert.equal(e.guest_read32(output), row.mask, `${backend}: ${label} mask`);
      assert.equal(e.guest_read32(output + 44) >>> 0, 0xa5a5a5a5);
      for (const [bit, error] of Object.entries(row.errors)) assert.equal(e.guest_read32(output + 4 + 4 * Number(bit)), error);
    };
    assert.equal(call('connect', [client, address, 16]), 0);
    observe('listener-ready', listener, events[0]);
    const peer = call('accept', [listener, 0, 0]);
    assert.notEqual(peer, 0xffffffff);
    assert.equal(call('recv', [peer, data + 1100, 1, 0]) | 0, -1);
    assert.equal(call('WSAGetLastError'), reference.acceptedSocketReceiveError, 'accept inherits nonblocking mode');
    observe('connected', client, events[1]);
    assert.equal(call('WSAEventSelect', [peer, events[2], 0x23]), 0);
    observe('accepted-write-ready', peer, events[2]);
    new Uint8Array(memory.buffer, e.guest_to_wasm(data + 1024) >>> 0, 7).set(Buffer.from('abcdefg'));
    assert.equal(call('send', [client, data + 1024, 7, 0]), 7);
    observe('read-ready', peer, events[2]);
    observe('enum-does-not-rearm-read', peer, events[2]);
    assert.equal(call('recv', [peer, data + 1100, 3, 0]), 3);
    assert.equal(Buffer.from(memory.buffer, e.guest_to_wasm(data + 1100) >>> 0, 3).toString(), 'abc');
    observe('partial-read-rearms', peer, events[2]);
    assert.equal(call('recv', [peer, data + 1100, 4, 0]), 4);
    observe('drained', peer, events[2]);
    assert.equal(call('send', [client, data + 4096, 16384, 0]), 16384);
    observe('read-ready', peer, events[2]);
    assert.equal(call('WaitForSingleObject', [events[1], 0]), 258, 'WRITE does not repeat after a successful send');
    assert.equal(call('send', [client, data + 1024, 1, 0]) | 0, -1);
    assert.equal(call('WSAGetLastError'), 10035);
    assert.equal(call('recv', [peer, data + 4096, 1, 0]), 1);
    assert.equal(call('WaitForSingleObject', [events[1], 0]), 0, 'freed capacity wakes a blocked sender');
    assert.equal(call('WSAEnumNetworkEvents', [client, events[1], output]), 0);
    assert.equal(e.guest_read32(output), 2, 'WRITE is re-armed after WSAEWOULDBLOCK');
    observe('partial-read-rearms', peer, events[2]);
    assert.equal(call('recv', [peer, data + 4096, 16383, 0]), 16383);
    observe('drained', peer, events[2]);
    e.guest_write32(data + 600, 0);
    assert.equal(call('ioctlsocket', [peer, 0x8004667e, data + 600]) | 0, -1, 'event registration keeps nonblocking mode');
    assert.equal(call('WSAGetLastError'), 10022);
    assert.equal(call('shutdown', [client, 1]), 0);
    observe('orderly-close', peer, events[2]);
    assert.equal(call('WSAEventSelect', [peer, 0, 0]), 0);
    assert.equal(call('ioctlsocket', [peer, 0x8004667e, data + 600]), 0, 'cancel permits blocking mode');
    for (const socket of [listener, peer, client]) assert.equal(call('closesocket', [socket]), 0);
    for (const event of events) assert.equal(call('WSACloseEvent', [event]), 1);
    // Reuse socket slots after close. Accepted sockets inherit the listener's
    // event and mask but receive independent network-event records.
    const again = call('socket', [2, 1, 6]), connector = call('socket', [2, 1, 6]);
    const inheritedEvent = call('WSACreateEvent');
    assert.equal(call('bind', [again, address, 16]), 0);
    assert.equal(call('listen', [again, 2]), 0);
    assert.equal(call('WSAEventSelect', [again, inheritedEvent, 9]), 0);
    assert.equal(call('connect', [connector, address, 16]), 0);
    assert.equal(call('WSAEnumNetworkEvents', [again, inheritedEvent, output]), 0);
    assert.equal(e.guest_read32(output), 8);
    const accepted = call('accept', [again, 0, 0]);
    assert.equal(call('send', [connector, data + 1024, 1, 0]), 1);
    assert.equal(call('WaitForSingleObject', [inheritedEvent, 0]), 0);
    assert.equal(call('WSAEnumNetworkEvents', [accepted, inheritedEvent, output]), 0);
    assert.equal(e.guest_read32(output), 1, 'accepted socket inherits read notification');
    assert.equal(call('WSAEventSelect', [accepted, inheritedEvent, 0x21]), 0);
    assert.equal(call('recv', [accepted, data + 1100, 1, 0]), 1);
    call('WSAEnumNetworkEvents', [accepted, inheritedEvent, output]);
    assert.equal(call('closesocket', [connector]), 0);
    assert.equal(call('WaitForSingleObject', [inheritedEvent, 0]), 0);
    assert.equal(call('WSAEnumNetworkEvents', [accepted, inheritedEvent, output]), 0);
    assert.equal(e.guest_read32(output), 32);
    assert.equal(e.guest_read32(output + 24), 10054, 'abortive close preserves its error');
    for (const socket of [again, accepted]) call('closesocket', [socket]);
    call('WSACloseEvent', [inheritedEvent]);
    const datagram = call('socket', [2, 2, 17]), udpEvent = call('WSACreateEvent');
    assert.equal(call('bind', [datagram, address, 16]), 0);
    assert.equal(call('WSAEventSelect', [datagram, udpEvent, 0x21]), 0);
    const packet = Buffer.alloc(31);
    [0x314e4c56, 6, 0x0a000002, 4500, 0x0a000001, 34929, 3]
      .forEach((value, index) => packet.writeUInt32LE(value, 4 * index));
    packet.write('xyz', 28);
    remoteWire.send(packet);
    remoteWire.send(packet);
    e.vlan_pump();
    for (let index = 0; index < 2; index++) {
      assert.equal(call('WaitForSingleObject', [udpEvent, 0]), 0, 'wire datagrams signal READ');
      assert.equal(call('WSAEnumNetworkEvents', [datagram, udpEvent, output]), 0);
      assert.equal(e.guest_read32(output), 1);
      assert.equal(call('recvfrom', [datagram, data + 1100, 3, 0, 0, 0]), 3);
      assert.equal(Buffer.from(memory.buffer, e.guest_to_wasm(data + 1100) >>> 0, 3).toString(), 'xyz');
    }
    assert.equal(call('WaitForSingleObject', [udpEvent, 0]), 258, 'last datagram drains READ readiness');
    call('closesocket', [datagram]);
    call('WSACloseEvent', [udpEvent]);
    assert.equal(ctx.wsaEvents.size, 0, 'closed sockets leave no event registrations');
    console.log(`PASS ${backend}: native Winsock events, TCP transitions/backpressure, UDP wire notifications, inheritance, reuse and ABI`);
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
