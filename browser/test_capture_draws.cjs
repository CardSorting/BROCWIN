// A diagnostic must retain submitted bytes without changing the live command.
'use strict';
const assert = require('node:assert/strict'), fs = require('node:fs'), vm = require('node:vm');
const {OPCODES} = require('../tools/wine-assembly/lib/d3d-command-stream');
const submitted = [], entry = {}, result = {original: true};
const bridge = {options: {}, devices: new Map(), _submit(e, op, p) { submitted.push(p); return result; }};
const original = bridge._submit;
function WineAssembly() {}
WineAssembly.prototype.getImports = () => ({});
const window = {D3DCommandStream: {OPCODES}, theseus: {client: {hostCtx: {d3d9Bridge: bridge}}},
  createHostImports: () => ({host: {}})};
vm.runInNewContext(fs.readFileSync(__dirname + '/capture_probe.js', 'utf8'),
  {window, WineAssembly, structuredClone, performance, console, btoa});
const probe = window.theseusCaptureProbe;
const draw = {vertices: new Uint8Array([1, 2, 3, 4]), vertexShader: new Uint8Array([8, 9]),
  vertexConstants: new Float32Array([1, 2]), textures: [{pixels: new Uint8Array(2048)}]};
probe.inspect({drawCapture: {maxDraws: 2, maxBytes: 16}});
assert.throws(() => probe.inspect({drawCapture: {}}), /already active/);
assert.equal(bridge._submit(entry, OPCODES.DRAW, draw), result);
bridge._submit(entry, OPCODES.PRESENT, {});
bridge._submit({}, OPCODES.DRAW, draw); // Another device is outside this frame.
bridge._submit(entry, OPCODES.DRAW, {vertices: new Uint8Array(100)}); // Fixed VS omitted.
assert.equal(bridge._submit(entry, OPCODES.DRAW, draw), result);
draw.vertices.fill(55); draw.vertexConstants.fill(99); // Reused live scratch.
bridge._submit(entry, OPCODES.PRESENT, {});
let r = probe.inspect({drawCapture: true}).drawCapture;
assert.equal(r.state, 'complete'); assert.equal(r.draws.length, 1);
assert.equal(r.seenDraws, 2); assert.equal(r.binaryBytes, 14);
assert.equal(Buffer.from(r.draws[0].payload.vertices.base64, 'base64').toString('hex'), '01020304');
assert.equal(Buffer.from(r.draws[0].payload.vertexConstants.base64, 'base64').readFloatLE(0), 1);
assert.equal(r.draws[0].payload.textures, undefined);
assert.equal(submitted[4], draw); assert.equal(bridge._submit, original);
probe.inspect({drawCapture: {maxDraws: 1, maxBytes: 1}});
bridge._submit(entry, OPCODES.PRESENT, {});
bridge._submit(entry, OPCODES.DRAW, draw);
r = probe.inspect({drawCapture: true}).drawCapture;
assert.equal(r.state, 'truncated'); assert.equal(r.draws.length, 0);
assert.equal(bridge._submit, original);
probe.inspect({drawCapture: {maxDraws: 1, maxBytes: 100, programmableOnly: false}});
bridge._submit(entry, OPCODES.PRESENT, {});
bridge._submit(entry, OPCODES.DRAW, {vertices: new Uint8Array(2)});
bridge._submit(entry, OPCODES.DRAW, {vertices: new Uint8Array(2)});
assert.equal(probe.inspect({drawCapture: true}).drawCapture.state, 'truncated');
assert.equal(bridge._submit, original);
assert.throws(() => probe.inspect({drawCapture: {maxDraws: 513}}), /Invalid/);
assert.throws(() => probe.inspect({drawCapture: {maxBytes: 33554433}}), /Invalid/);
const failure = new Error('original failure');
bridge._submit = () => { throw failure; };
probe.inspect({drawCapture: {}});
assert.throws(() => bridge._submit(entry, OPCODES.DRAW, draw), error => error === failure);
console.log('PASS draw observation: frame bounds, immutable bytes, limits, device selection, unchanged result/error');

// Observe a real pending command queue without retiring it or consuming the
// application's completion token. A stalled producer needs these facts intact.
const {CommandQueue} = require('../tools/wine-assembly/lib/d3d-command-stream');
let executed = 0;
const queue = new CommandQueue({deviceId: 91, capacityBytes: 4 * 1048576,
  consumer: {execute() { executed++; return {consumed: new Promise(() => {}),
    completion: new Promise(() => {}), value: new Promise(() => {})}; }}});
const queued = {primitive: 2, primitiveCount: 12, vertices: new Uint8Array(1100000),
  textures: [{pixels: new Uint8Array(10)}]};
queued.vertices[0] = 73;
queue.submit(OPCODES.DRAW, queued);
const device = {queue, kind: 'webgl', async: true, sharedWorker: true};
bridge.devices.set(91, device);
bridge.requests = new Map([[-7, {entry: device, generation: 1, done: false,
  consume() { throw Error('diagnostic consumed token'); },
  finalize() { throw Error('diagnostic finalized command'); }}]]);
bridge.presentWaits = new Set([{}]);
window.theseus.client._d3dMainWait = {token: -7, done: false};
const before = JSON.stringify(queue.snapshot()), callsBefore = executed;
const observed = probe.inspect({renderState: true}).renderState;
assert.equal(JSON.stringify(queue.snapshot()), before);
assert.equal(executed, callsBefore);
assert.equal(bridge.requests.size, 1);
assert.equal(observed.requests[0].token, -7);
assert.equal(observed.mainWait.done, false);
assert.equal(observed.presentWaits, 1);
const pending = observed.devices[0].pendingCommands[0];
assert.equal(pending.name, 'DRAW'); assert.equal(pending.primitiveCount, 12);
assert.equal(pending.payload.textures, undefined);
assert.ok(pending.payload.vertices.capturedBytes <= 1048576);
assert.equal(pending.payload.vertices.byteLength, 1100000);
assert.equal(Buffer.from(pending.payload.vertices.base64, 'base64')[0], 73);
assert.equal(probe.runtime().graphics.renderState.devices[0].pendingCommands[0].payload, undefined);
assert.equal(queued.vertices[0], 73);
console.log('PASS pending render observation: bounded bytes, preserved queue/token, metadata-only routine samples');
