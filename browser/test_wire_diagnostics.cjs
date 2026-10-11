'use strict';
const assert = require('node:assert/strict');
class Socket extends EventTarget {
  static OPEN = 1;
  constructor() { super(); this.readyState = 1; this.bufferedAmount = 0; this.sent = [];
    queueMicrotask(() => this.dispatchEvent(new Event('open'))); }
  send(bytes) { this.sent.push(bytes); }
  close() { this.readyState = 3; this.dispatchEvent(new Event('close')); }
}
global.WebSocket = Socket;
const {TheseusLocalServerWire} = require('./local_server_wire');
const frame = (ip, port) => {
  const bytes = new Uint8Array(31), view = new DataView(bytes.buffer);
  [0x314e4c56, 6, 0x0a000001, 8577, ip, port, 3].forEach((v, i) => view.setUint32(i * 4, v, true));
  bytes.set([6, 7, 8], 28); return bytes;
};
(async () => {
  const wire = new TheseusLocalServerWire({webSocketUrl: 'ws://127.0.0.1:20763/vln', udpPorts: [9301]});
  await wire.ready;
  const first = frame(0x7f000001, 9301), second = frame(0x0a000002, 9301);
  wire.send(first); wire.send(first); wire.send(second);
  let s = wire.snapshot();
  assert.equal(wire.socket.sent[0], first); assert.equal(wire.socket.sent[2], second);
  assert.equal(s.datagramRoutes[0].attempts, 2); assert.equal(s.datagramRoutes[0].payloadBytes, 6);
  assert.equal(s.datagramRoutes[0].supported, true); assert.equal(s.datagramRoutes[1].supported, false);
  assert.equal(s.unsupportedDatagrams, 1);
  s.datagramRoutes[0].attempts = 1000;
  assert.equal(wire.snapshot().datagramRoutes[0].attempts, 2);
  for (let i = 0; i < 40; i++) wire.send(frame(0x7f000001, 10000 + i));
  s = wire.snapshot(); assert.equal(s.datagramRoutes.length, 32);
  assert.equal(s.untrackedDatagramAttempts, 10); assert.equal(s.unsupportedDatagrams, 41);
  assert.equal(wire.socket.sent.length, 43);
  assert.ok(s.datagramRoutes.every(r => !('payload' in r) && !('bytes' in r)));
  const self = frame(0x0a000001, 8577), before = Buffer.from(self);
  let delivered = 0; wire.onDeliver = () => delivered++;
  assert.equal(wire.send(self), true); self.fill(0);
  assert.deepEqual(Buffer.from(wire.peek()), before, 'own datagram survives send scratch reuse');
  assert.equal(delivered, 1); assert.equal(wire.socket.sent.length, 43, 'self-unicast never leaves guest');
  assert.equal(wire.snapshot().locallyDeliveredDatagrams, 1);
  assert.equal(wire.stats.unsupportedDatagrams, 41, 'self-unicast is supported');
  wire.commit(); assert.equal(wire.queuedBytes, 0);
  wire.queuedBytes = 8 * 1024 * 1024;
  assert.equal(wire.send(frame(0x0a000001, 8577)), false, 'full local receive queue applies backpressure');
  assert.equal(wire.peek(), null); wire.queuedBytes = 0;
  const mapping = (guestPort, nativePort) => {
    const bytes = new Uint8Array(28), view = new DataView(bytes.buffer);
    [0x314e4c56, 9, 0x0a000001, guestPort, 0x0a000001, nativePort, 0]
      .forEach((v, i) => view.setUint32(i * 4, v, true));
    return bytes;
  };
  const receive = (target, bytes) => target.socket.dispatchEvent(new MessageEvent('message', {data: bytes.buffer}));
  receive(wire, mapping(8577, 57362));
  assert.equal(wire.peek(), null, 'mapping metadata never reaches guest Winsock');
  const mapped = frame(0x0a000001, 57362);
  assert.equal(wire.send(mapped), true);
  assert.equal(wire.peek(), null, 'mapped self-probe waits for transport reflection');
  assert.equal(wire.socket.sent.at(-1), mapped, 'mapped self-probe bytes stay unchanged');
  assert.equal(wire.snapshot().mappedSelfDatagrams, 1);
  s = wire.snapshot(); s.udpMappings[0].guestPort = 1;
  assert.equal(wire.snapshot().udpMappings[0].guestPort, 8577);
  wire.socket.bufferedAmount = 1024 * 1024;
  assert.equal(wire.send(mapped), false, 'mapped self-probe obeys transport backpressure');
  wire.socket.bufferedAmount = 0;
  for (let i = 1; i < 128; i++) receive(wire, mapping(8577, 57362 + i));
  assert.equal(wire.udpMappings.size, 128);
  receive(wire, mapping(8577, 57362)); // Duplicate is idempotent at capacity.
  assert.equal(wire.state, 'open');
  receive(wire, mapping(8577, 57362 + 128));
  assert.equal(wire.state, 'closed', 'unbounded mapping announcements are rejected');
  assert.equal(wire.snapshot().localCloseReason, 'invalid-udp-mapping');
  assert.equal(wire.udpMappings.size, 0, 'transport loss retires mappings');
  wire.close();
  assert.equal(wire.snapshot().localCloseReason, 'invalid-udp-mapping', 'cleanup preserves first cause');
  for (const change of [
    b => new DataView(b.buffer).setUint32(8, 0x08080808, true),
    b => new DataView(b.buffer).setUint32(16, 0x08080808, true),
    b => new DataView(b.buffer).setUint32(12, 0, true),
    b => new DataView(b.buffer).setUint32(20, 65536, true),
  ]) {
    const target = new TheseusLocalServerWire({webSocketUrl: 'ws://127.0.0.1:20763/vln'});
    await target.ready; const bytes = mapping(8577, 57362); change(bytes); receive(target, bytes);
    assert.equal(target.state, 'closed', 'invalid mapping rejected');
  }
  const remote = new TheseusLocalServerWire({webSocketUrl: 'ws://127.0.0.1:20763/vln'});
  await remote.ready;
  const closed = new Event('close');
  Object.assign(closed, {code: 1008, reason: 'Invalid guest stream', wasClean: true});
  remote.socket.dispatchEvent(closed);
  s = remote.snapshot();
  assert.equal(s.localCloseReason, null, 'remote closure is distinct from local validation');
  assert.equal(s.closeInfo.code, 1008); assert.equal(s.closeInfo.reason, 'Invalid guest stream');
  assert.equal(s.closeInfo.wasClean, true); assert.ok(s.closeInfo.at);
  s.closeInfo.code = 0;
  assert.equal(remote.snapshot().closeInfo.code, 1008, 'close snapshot is immutable');
  console.log('PASS bounded UDP endpoint metadata, immutable snapshot and unchanged transmitted bytes');
})().catch(error => { console.error(error); process.exitCode = 1; });
