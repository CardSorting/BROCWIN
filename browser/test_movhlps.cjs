'use strict';
const assert = require('node:assert/strict'), fs = require('node:fs'), path = require('node:path');
const runtime = path.resolve(__dirname, '../tools/wine-assembly');
const {compileSrcWasm} = require(path.join(runtime, 'test/compile-src'));
const {createHostImports} = require(path.join(runtime, 'lib/host-imports'));
(async () => {
  const init = `(func (export "probe_init")
    (global.set $image_base (i32.const 0x00400000))
    (global.set $exe_size_of_image (i32.const 0x00200000))
    (call $heap_init (i32.const 0x01000000)))`;
  const wasm = compileSrcWasm((file, source) => {
    return file === '13-exports.wat' ? source + '\n' + init : source;
  });
  const memory = new WebAssembly.Memory({initial: 8192, maximum: 8192, shared: true});
  const ctx = {getMemory: () => memory.buffer};
  const {host} = createHostImports(ctx);
  Object.assign(host, {memory, log() {}, log_i32() {}, exit() {}});
  const {instance} = await WebAssembly.instantiate(wasm, {host}), e = ctx.exports = instance.exports;
  e.probe_init(); e.set_cpu_sse(1);
  const base = e.get_image_base(), input = base + 0x80000, out = input + 256, sp = base + 0xd00000;
  const le = n => [n & 255, n >>> 8 & 255, n >>> 16 & 255, n >>> 24];
  const registers = Array.from({length: 8}, (_, r) => [0x7fc10000 + r, 0x80000000 + r, 0xff810010 + r, 0xdead0010 + r]);
  registers.flat().forEach((v, i) => e.guest_write32(input + i * 4, v));
  let count = 0;
  for (const uop of [0, 1]) for (let dst = 0; dst < 8; dst++) for (let src = 0; src < 8; src++) {
    e.set_uop(uop); e.set_uop_trace_heads(uop);
    const code = [];
    for (let r = 0; r < 8; r++) code.push(0x0f, 0x10, 5 + r * 8, ...le(input + r * 16));
    code.push(0x68, ...le(0x8d7), 0x9d, 0x9c, 0x58, 0xa3, ...le(out + 132),
      0x0f, 0x12, 0xc0 + dst * 8 + src, 0x9c, 0x58, 0xa3, ...le(out + 128));
    for (let r = 0; r < 8; r++) code.push(0x0f, 0x11, 5 + r * 8, ...le(out + r * 16));
    code.push(0xc3);
    const pc = base + 0x1000 + 256 * count++;
    code.forEach((v, i) => e.guest_write8(pc + i, v));
    e.guest_write32(sp, 0); e.set_esp(sp); e.set_eip(pc); e.run(10000);
    assert.equal(e.get_eip(), 0); assert.equal(e.get_esp() >>> 0, sp + 4);
    assert.equal(e.guest_read32(out + 128), e.guest_read32(out + 132), 'observed flags preserved');
    for (let r = 0; r < 8; r++) {
      const expected = r === dst ? [...registers[src].slice(2), ...registers[dst].slice(2)] : registers[r];
      const actual = Array.from({length: 4}, (_, i) => e.guest_read32(out + r * 16 + i * 4) >>> 0);
      assert.deepEqual(actual, expected, `uop=${uop} xmm${dst},xmm${src}: output xmm${r}`);
    }
  }
  console.log(`PASS MOVHLPS: ${count} register/alias/uop cases; exact NaN/sign bits, all XMM registers and flags`);
})().catch(error => { console.error(error); process.exitCode = 1; });
