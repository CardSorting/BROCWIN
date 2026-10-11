'use strict';

// Exercise the production host's color command boundary with sparse guest
// storage. The consumer records bytes; it does not stand in for game rendering.
const assert = require('node:assert/strict');
const {Bridge} = require('../tools/wine-assembly/lib/d3d9-host');
const {OPCODES} = require('../tools/wine-assembly/lib/d3d-command-stream');
const tick = () => new Promise(resolve => setImmediate(resolve));

async function fixture() {
  const memory = new ArrayBuffer(1 << 20), v = new DataView(memory), bytes = new Uint8Array(memory);
  const desc = 64, program = 1024, vertices = 30000, surface = 40000, target = 41000;
  const guestBase = 0x800000, bits = guestBase + 4080, size = 64 * 64 * 4;
  const pages = [0x20000, 0x29000, 0x30000, 0x2b000, 0x24000], commands = [];
  const g2w = p => p >= guestBase && p < guestBase + 5 * 4096
    ? pages[Math.floor((p - guestBase) / 4096)] + p % 4096 : p;
  const set = (p, n) => v.setUint32(p, n, true);
  [7, program, 0x40000, 64, 64, 1, 4, 1, vertices, 16].forEach((n, i) => set(desc + i * 4, n));
  set(program + 12, 0x42); v.setFloat32(program + 1696, 1, true);
  set(program + 21784, 0x80000000);
  bytes.fill(0x31, vertices, vertices + 48);
  const header = (p, id) => {
    set(p + 8, 7); set(p + 12, 0xd3d90006); set(p + 20, 64); set(p + 24, 64);
    set(p + 28, 22); set(p + 36, id); set(p + 40, bits); set(p + 48, 256); set(p + 52, size);
  };
  header(surface, 33); header(target, 34);
  bytes.fill(0xa5, 0x20000, 0x31000);
  const source = Uint8Array.from({length: size}, (_, i) => (i * 17 + 3) & 255);
  const readback = Uint8Array.from({length: size}, (_, i) => (i * 13 + 7) & 255);
  for (let i = 0; i < size; i++) bytes[g2w(bits + i)] = source[i];
  const guard = bytes.slice(0x21000, 0x22000);
  const consumer = {ready: Promise.resolve(), execute(command) {
    commands.push(command);
    const value = Promise.resolve(command.opcode === OPCODES.READBACK ? {pixels: readback} : 1);
    return {value, completion: value};
  }, async cancel() {}};
  const bridge = new Bridge({backend: 'software', createSoftwareWorker: () => consumer,
    getMemory: () => memory, guestToWasm: g2w, maxDeferredCommands: 32});
  const flush = async () => { for (let i = 0; i < 4; i++) await tick(); };
  const run = async (op, address = desc, aux = 0) => {
    let result = bridge.call(op, address, aux);
    if (result <= -2) { await bridge.wait(result); result = bridge.call(0x30007, 0, result); }
    assert.equal(result, 1, bridge.lastError?.message); await flush();
  };
  await tick(); await run(0x30001);
  const createColor = async () => {
    set(desc + 24, surface); set(desc + 28, 0); set(desc + 32, 0); set(desc + 36, 0);
    set(desc + 44, 64); set(desc + 48, 64);
    await run(0x30014);
  };
  return {bridge, bytes, bits, size, set, desc, surface, target, commands, source, readback, run,
    createColor, gather: () => Uint8Array.from({length: size}, (_, i) => bytes[g2w(bits + i)]),
    guard: () => assert.deepEqual(bytes.slice(0x21000, 0x22000), guard, 'live neighboring backing remains intact')};
}

(async () => {
  const failures = [];
  for (const mode of ['create', 'upload', 'readback', 'backbuffer-readback', 'update-surface']) {
    const f = await fixture();
    try {
      await f.createColor();
      if (mode === 'create') {
        const c = f.commands.find(c => c.opcode === OPCODES.RESOURCE_CREATE && c.payload.kind === 'color');
        assert.deepEqual(c.payload.pixels, f.source, 'resource creation gathers all guest pages');
      } else if (mode === 'upload') {
        await f.run(0x30011, f.surface, 7);
        const c = f.commands.filter(c => c.opcode === OPCODES.RESOURCE_UPDATE).at(-1);
        assert.deepEqual(c.payload.pixels, f.source, 'unlock upload gathers all guest pages');
      } else if (mode === 'update-surface') {
        f.set(f.desc + 24, f.surface); f.set(f.desc + 28, f.bits); f.set(f.desc + 32, 256);
        f.set(f.desc + 36, 0); f.set(f.desc + 44, 0); f.set(f.desc + 48, 64);
        f.set(f.desc + 52, 64); f.set(f.desc + 56, 22);
        await f.run(0x30015);
        const c = f.commands.filter(c => c.opcode === OPCODES.RESOURCE_UPDATE).at(-1);
        assert.deepEqual(c.payload.pixels, f.source, 'UpdateSurface uses its guest source pointer');
      } else {
        await f.run(mode === 'readback' ? 0x30010 : 0x30012,
          mode === 'readback' ? f.surface : f.desc, mode === 'readback' ? 7 : f.target);
        f.guard();
        assert.deepEqual(f.gather(), f.readback, 'readback scatters into all guest pages');
      }
      console.log('PASS sparse color ' + mode);
    } catch (error) { failures.push(mode + ': ' + error.message.slice(0, 240)); }
    await f.bridge.close();
  }
  assert.deepEqual(failures, [], failures.join('\n'));
})().catch(error => { console.error(error); process.exitCode = 1; });
