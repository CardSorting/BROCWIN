'use strict';

// Real D3D9 host command publication with a texture whose guest pages have
// discontiguous backing. This is a compatibility regression, not game evidence.
const assert = require('node:assert/strict');
const {Bridge} = require('../tools/wine-assembly/lib/d3d9-host');
const {OPCODES} = require('../tools/wine-assembly/lib/d3d-command-stream');
const tick = () => new Promise(resolve => setImmediate(resolve));

(async () => {
  const memory = new ArrayBuffer(1 << 20), view = new DataView(memory);
  const bytes = new Uint8Array(memory), commands = [], gates = [];
  const desc = 64, program = 1024, vertices = 30000, texture = 40000;
  const mip = texture + 64, guestBase = 0x800000, texels = guestBase + 4080;
  const backing = [0x20000, 0x29000, 0x30000, 0x2b000, 0x24000];
  let translations = 0, missingPage = -1;
  const g2w = p => {
    if (p < guestBase || p >= guestBase + 5 * 4096) return p;
    translations++;
    const page = Math.floor((p - guestBase) / 4096);
    return page === missingPage ? 0xf0 : backing[page] + p % 4096;
  };
  const set = (p, n) => view.setUint32(p, n, true);
  [7, program, 32000, 2, 2, 1, 4, 1, vertices, 16].forEach((n, i) => set(desc + i * 4, n));
  set(program + 12, 0x42); view.setFloat32(program + 1696, 1, true);
  set(program + 21784, 0x80000000);
  bytes.fill(0x31, vertices, vertices + 48);
  set(texture + 12, 3); set(texture + 24, 64); set(texture + 28, 64);
  set(texture + 32, 1); set(texture + 36, 21);
  set(mip, 64); set(mip + 4, 64); set(mip + 8, 256);
  set(mip + 12, 64 * 64 * 4); set(mip + 16, texels); set(mip + 28, 1);
  set(program + 1700, texture);
  bytes.fill(0xee, 0x20000, 0x31000);
  const expected = new Uint8Array(64 * 64 * 4);
  for (let i = 0; i < 4096; i++) {
    const r = i & 255, g = (i >>> 4) ^ 55, b = (i >>> 7) ^ 126;
    set(g2w(texels + i * 4), (0xff000000 | r << 16 | g << 8 | b) >>> 0);
    expected.set([r, g, b, 255], i * 4);
  }
  // Endpoints are affine while the interior pages are not.
  assert.equal(g2w(texels + expected.length - 1), g2w(texels) + expected.length - 1);
  const consumer = {ready: Promise.resolve(),
    execute(command) {
      commands.push(command);
      const completion = new Promise(resolve => gates.push(resolve));
      return {completion, value: completion};
    }, async cancel() { while (gates.length) gates.shift()(1); }};
  const bridge = new Bridge({backend: 'software', createSoftwareWorker: () => consumer,
    getMemory: () => memory, guestToWasm: g2w, maxDeferredCommands: 32});
  const flush = async () => {
    for (let i = 0; i < 4; i++) { while (gates.length) gates.shift()(1); await tick(); }
  };
  const draw = async () => { assert.equal(bridge.call(0x30001, desc, 0), 1, bridge.lastError?.message); await flush(); };
  await tick();
  await draw();
  const first = bridge._textureSnapshots.get(mip).pixels;
  assert.deepEqual(first, expected, 'every pixel comes from its actual guest page');
  const published = commands.filter(c => c.opcode === OPCODES.DRAW)[0].payload.textures[0].levels[0].pixels;
  assert.deepEqual(published, expected, 'the actual queued draw carries the correct snapshot');
  assert.notEqual(published, first, 'queued pixels have independent ownership');
  translations = 0;
  await draw();
  assert.equal(translations, 0, 'an unchanged cached level does not translate texels');
  assert.equal(bridge._textureSnapshots.get(mip).pixels, first);

  set(g2w(texels + 8192), 0xff030201);
  expected.set([3, 2, 1, 255], 8192);
  set(mip + 28, 2);
  await draw();
  assert.deepEqual(bridge._textureSnapshots.get(mip).pixels, expected, 'dirty sequence refreshes the split level');
  const last = expected.length - 256; // a sampled chunk in the final guest page
  set(g2w(texels + last), 0xff090807);
  expected.set([9, 8, 7, 255], last);
  set(program + 25596, 1);
  await draw();
  assert.deepEqual(bridge._textureSnapshots.get(mip).pixels, expected, 'reused texture address fingerprints guest bytes');

  missingPage = 2; set(mip + 28, 3);
  assert.equal(bridge.call(0x30001, desc, 0), -1, 'an unmapped interior page fails explicitly');
  assert.match(bridge.lastError.message, /invalid texture memory range/);
  await bridge.close();
  console.log('PASS sparse D3D9 texture publication, dirty/cache lifetime, and unmapped pages');
})().catch(error => { console.error(error); process.exitCode = 1; });
