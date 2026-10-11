// Capture-only scheduling: every selected Worker must be armed before it runs.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const calls = [];
const timers = [];
function link(slot) {
  return {slot, async breakpointSnapshots(points) {
    calls.push({slot, points: structuredClone(points)});
    return {count: points.length};
  }};
}
const main = link(0), existing = link(1);
const guest = {
  breakpointSnapshots: main.breakpointSnapshots.bind(main),
  threadLinks: new Map([[1, existing]]),
  async spawnThread(slot) {
    const child = link(slot);
    this.threadLinks.set(slot, child);
    return child;
  },
};
function WineAssembly() {}
function TheseusLocalServerWire() { this.accept = true; }
TheseusLocalServerWire.prototype.send = function(bytes) {
  if (this.fail) throw this.fail;
  this.lastBytes = bytes;
  return this.accept;
};
let exitCalls = 0;
const oomCalls = [];
WineAssembly.prototype.getImports = function() {
  return {host: {exit: code => { exitCalls++; this.memory = null; return code + 7; },
    heap_oom_trace: (...args) => { oomCalls.push(args); return 17; }}};
};
const window = {theseus: {client: {guestWorker: guest}}, createHostImports: () => ({host: {}})};
vm.runInNewContext(fs.readFileSync(__dirname + '/capture_probe.js', 'utf8'),
  {window, WineAssembly, TheseusLocalServerWire, structuredClone, performance, console,
   RegionMap: {BASE: {REGFILE: 256, HEAP_ARENAS: 2048}, SIZE: {REGFILE: 1024, VSOCK_TABLE: 0, HEAP_ARENAS: 80}}, TextDecoder,
   setTimeout: callback => timers.push(callback)});
(async () => {
  const probe = window.theseusCaptureProbe, points = [{address: 0x32919890}];
  const wire = new TheseusLocalServerWire();
  function frame(kind, payload = Buffer.alloc(0), port = 49155) {
    const b = Buffer.alloc(28 + payload.length);
    [0x314e4c56, kind, 0x0a000001, port, 0x7f000001, 9300, payload.length]
      .forEach((v, i) => b.writeUInt32LE(v, i * 4));
    payload.copy(b, 28); return b;
  }
  function packet(serial) {
    const b = Buffer.alloc(30, 0xa7);
    b.writeUInt16LE(b.length, 0); b.writeUInt16LE(0x1234, 2); b.writeUInt32LE(serial, 4);
    return b;
  }
  const first = packet(5), combined = Buffer.concat([first, packet(6)]);
  wire.send(frame(1));
  wire.send(frame(3, combined.subarray(0, 1)));
  wire.send(frame(3, combined.subarray(1, 5)));
  const rest = frame(3, combined.subarray(5)), wireBefore = Buffer.from(rest);
  wire.accept = false;
  assert.equal(wire.send(rest), false);
  assert.equal(probe.runtime().sentHeaders.recent.length, 0, 'refused bytes must not advance parsing');
  wire.accept = true;
  assert.equal(wire.send(rest), true);
  assert.equal(wire.lastBytes, rest, 'original send receives the original argument');
  assert.deepEqual(rest, wireBefore, 'observer does not mutate transport bytes');
  assert.deepEqual(Array.from(probe.runtime().sentHeaders.recent, r => r.serial), [5, 6]);
  wire.fail = new Error('original send error');
  assert.throws(() => wire.send(frame(3, packet(7))), e => e === wire.fail);
  wire.fail = null;
  assert.equal(probe.runtime().sentHeaders.recent.length, 2);
  for (let i = 0; i < 100; i++) wire.send(frame(3, packet(6)));
  let headers = probe.runtime().sentHeaders;
  assert.equal(headers.recent.length, 64); assert.equal(headers.anomalies.length, 16);
  assert.equal(headers.streams[0].nonIncreasing, 100);
  assert.equal(headers.anomalies[0].previousSerial, 6);
  wire.send(frame(1)); wire.send(frame(3, packet(1)));
  assert.equal(probe.runtime().sentHeaders.streams[0].nonIncreasing, 0, 'new connection resets serial comparison');
  for (let p = 50000; p < 50030; p++) wire.send(frame(1, Buffer.alloc(0), p));
  assert.equal(probe.runtime().sentHeaders.streams.length, 16, 'stream bookkeeping is bounded');
  const invalid = frame(3, Buffer.from([1, 0, 0, 0, 0, 0, 0, 0]));
  assert.equal(wire.send(invalid), true, 'invalid diagnostic interpretation does not reject transport');
  assert.equal(probe.runtime().sentHeaders.streams[0].invalid, true);
  console.log('PASS capture sent headers: fragmented/coalesced packets, refusal/error preservation, no writes, bounds/reset');
  await probe.breakpoints(points, 'all');
  assert.deepEqual(calls.map(c => c.slot), [0, 1]);
  await guest.spawnThread(2);
  assert.equal(calls.at(-1).slot, 2);
  assert.deepEqual(calls.at(-1).points, points);
  await probe.breakpoints([]);
  assert.deepEqual(calls.slice(-3).map(c => [c.slot, c.points.length]), [[0, 0], [1, 0], [2, 0]]);
  const count = calls.length;
  await guest.spawnThread(3);
  assert.equal(calls.length, count, 'cleared plans must not arm future threads');
  await assert.rejects(probe.breakpoints(points, 'invalid'), /Invalid breakpoint scope/);
  assert.equal(calls.length, count);
  console.log('PASS capture breakpoint scope: existing/new Workers, clear, invalid scope');

  // A secondary thread calls ExitProcess. Memory disappears in the original
  // import, so the evidence must be captured first and retain its real caller.
  const process = new WineAssembly();
  process.memory = {buffer: new ArrayBuffer(8192)};
  process._guestToWasmAddress = x => x;
  process.threadManager = {_runningThreadHandle: 42, threads: new Map([[42, {tid: 3}]])};
  process.guestWorker = {audioRpcSlot: 6};
  const data = new DataView(process.memory.buffer), regs = 256 + 3 * 64;
  data.setUint32(regs + 16, 4104, true);
  data.setUint32(regs + 20, 4200, true);
  data.setUint32(4096, 0x12345678, true);
  data.setUint32(4100, 0xffffffff, true);
  data.setUint32(4204, 0x23456789, true);
  const imports = process.getImports();
  // Read the actual shared table before teardown; do not ask a failed Worker
  // for exports, alter guest bytes, or replace the real import's result.
  data.setUint32(2048, 5000, true); // corrupt count still bounded by capacity
  [0x60000000, 0x60100000, 0x600ffff8, 0].forEach((v, i) =>
    data.setUint32(2064 + i * 4, v, true));
  const heapBefore = Buffer.from(new Uint8Array(process.memory.buffer));
  assert.equal(imports.host.heap_oom_trace(1048576, 4), 17);
  const heap = probe.observations.at(-1);
  assert.equal(heap.kind, 'heap-failure');
  assert.equal(heap.reason, 4);
  assert.equal(heap.records.length, 4);
  assert.equal(heap.records[0][2], 0x600ffff8);
  assert.equal(heap.records[0][3], 0);
  assert.deepEqual(Buffer.from(new Uint8Array(process.memory.buffer)), heapBefore);
  imports.host.heap_oom_trace(21328, 1);
  const heapCount = probe.observations.length;
  imports.host.heap_oom_trace(21272, 1);
  assert.equal(probe.observations.length, heapCount, 'OOM snapshots bounded to two');
  assert.deepEqual(oomCalls, [[1048576, 4], [21328, 1], [21272, 1]]);
  console.log('PASS capture heap failure: bounded original shared records, no writes, original import/result');
  assert.equal(imports.host.exit(-1), 6);
  assert.equal(exitCalls, 1);
  assert.equal(process.memory, null);
  const observed = probe.observations.at(-1);
  assert.equal(observed.kind, 'process-exit');
  assert.equal(observed.tid, 3);
  assert.equal(observed.rpcSlot, 6);
  assert.equal(observed.stack.words[0], 0x12345678);
  assert.equal(observed.stack.words[1], 0xffffffff);
  assert.equal(observed.stack.frames[0].returnAddress, 0x23456789);
  // Missing memory must never suppress the application exit or its result.
  assert.equal(imports.host.exit(9), 16);
  assert.equal(exitCalls, 2);
  assert.equal(probe.observations.at(-1).kind, 'exit-probe-error');
  console.log('PASS capture exit: caller stack before teardown, original result, diagnostic failure isolation');

  // A stuck Worker cannot answer readExports. The timeout must still retain
  // its shared handshake and saved caller without another request or writes.
  const memory = {buffer: new SharedArrayBuffer(8192)};
  const rpcWords = new Int32Array(memory.buffer, 1536, 64);
  rpcWords[0] = 1; rpcWords[1] = 2;
  const saved = new DataView(memory.buffer);
  saved.setUint32(256 + 16, 4096, true);
  saved.setUint32(4096, 0x12345678, true);
  let requests = 0;
  const stuck = {slot: 0, _pending: new Map([[1, {}]])};
  window.GuestRpc = {SLOT: {STATUS: 0, FN: 1}, views: () => ({i32: rpcWords})};
  window.theseus.client = {memory, _guestToWasmAddress: x => x,
    guestWorker: {link: stuck, threadLinks: new Map(), broker: {names: ['a', 'b', 'net_frame_peek']},
      readExports() { requests++; return new Promise(() => {}); }},
    threadManager: {threads: new Map()}};
  const before = Buffer.from(new Uint8Array(memory.buffer));
  const pending = probe.sample();
  timers.pop()();
  const timeout = await pending;
  assert.equal(timeout.timedOut, true);
  const row = timeout.runtime.threads.threads[0];
  assert.equal(row.statusBefore, 1);
  assert.equal(row.statusAfter, 1);
  assert.equal(row.importName, 'net_frame_peek');
  assert.equal(row.pendingRequests, 1);
  assert.equal(row.savedStack.words[0], 0x12345678);
  assert.equal(requests, 1);
  assert.deepEqual(Buffer.from(new Uint8Array(memory.buffer)), before);
  rpcWords[0] = 0;
  assert.equal(probe.runtime().threads.threads[0].statusBefore, 0, 'idle previous import must remain distinguishable');
  window.theseus.client.memory = null;
  assert.equal(probe.runtime().threads, null, 'released memory is unavailable');
  console.log('PASS capture unresponsive Worker: shared handshake/saved caller retained, no guest writes or extra RPC');
})().catch(error => { console.error(error); process.exitCode = 1; });
