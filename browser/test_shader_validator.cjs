'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const runtime = path.resolve(__dirname, '../tools/wine-assembly');
const { bootRenderHarness } = require(path.join(runtime, 'test/render-helper'));
const { loadDll, patchDllImports, callDllMain, _test: { findDllExport } } =
  require(path.join(runtime, 'lib/dll-loader'));
const extraWat = String.raw`
  (func (export "test_validator_init")
    (global.set $image_base (i32.const 0x00400000))
    (global.set $exe_size_of_image (i32.const 0x00200000))
    (global.set $thunk_guest_base
      (i32.add (i32.sub (global.get $THUNK_BASE) (global.get $GUEST_BASE)) (global.get $image_base)))
    (call $heap_init (i32.const 0x01000000)))`;

(async () => {
  const { exports: e, memory } = await bootRenderHarness({ extraWat, fonts: 'none' });
  e.test_validator_init();
  e.set_api_log(0);
  const alloc = size => e.guest_alloc(size) >>> 0;
  const stack = alloc(1024 * 1024), sp = stack + 1024 * 1024 - 64;
  const teb = alloc(4096);
  e.set_fs_base(teb);
  e.guest_write32(teb, 0xffffffff);
  e.guest_write32(teb + 4, sp + 64);
  e.guest_write32(teb + 8, stack);
  e.guest_write32(teb + 0x18, teb);
  e.set_esp(sp);
  const writeBytes = (at, bytes) => {
    for (let i = 0; i < bytes.length; i++) e.guest_write8(at + i, bytes[i]);
  };
  const readA = at => {
    if (!at) return null;
    let value = '';
    for (let i = 0; i < 4096; i++) {
      const ch = new Uint8Array(memory.buffer)[e.guest_to_wasm(at + i) >>> 0];
      if (!ch) return value;
      value += String.fromCharCode(ch);
    }
    throw new Error('unterminated validator diagnostic');
  };
  const dlls = ['kernel32.dll', 'd3d9.dll', 'theseus-validator.dll'].map(name => ({
    name, bytes: fs.readFileSync(path.join(__dirname, 'generated/platform', name)),
  }));
  const mapped = dlls.map(d => ({ name: d.name, ...loadDll(e, memory.buffer, d.bytes,
    'C:\\WINDOWS\\SYSTEM\\' + d.name) }));
  patchDllImports(e, memory.buffer, dlls, mapped, () => {});
  const component = mapped[2];
  assert.notEqual(component.loadAddr, 0x10000000, 'component relocations exercised');
  callDllMain(e, component.loadAddr, component.dllMain, console.log, { strict: true, lpReserved: 1 });
  const cookie = e.guest_read32(component.loadAddr + 0x175340) >>> 0;
  assert.notEqual(cookie, 0xbb40e64e, 'original cookie initializer ran');
  assert.equal(e.guest_read32(component.loadAddr + 0x175344) >>> 0, (~cookie) >>> 0);
  const factory = findDllExport(e, memory.buffer, mapped[1].loadAddr, 'Direct3DShaderValidatorCreate9');
  assert.ok(factory, 'public D3D9 factory is exposed through integrated adapter');
  const call = (address, args = []) => {
    e.guest_write32(sp, 0);
    args.forEach((arg, i) => e.guest_write32(sp + 4 + i * 4, arg));
    e.set_esp(sp);
    e.set_eip(address);
    try { e.run(2000000); }
    catch (error) {
      throw new Error(`validator call ${address.toString(16)} at EIP=${(e.get_eip() >>> 0).toString(16)} ESP=${(e.get_esp() >>> 0).toString(16)}: ${error.message}`);
    }
    assert.equal(e.get_eip(), 0, `call ${address.toString(16)} returns`);
    assert.equal(e.get_esp(), sp + 4 + args.length * 4, 'stdcall frame preserved');
    assert.equal(e.guest_read32(teb) >>> 0, 0xffffffff, 'native SEH frame unwound');
    return e.get_eax() >>> 0;
  };
  const scratch = alloc(4096), count = alloc(4), entries = alloc(32 * 2336);
  const callback = alloc(256), code = [];
  const emit = (...bytes) => code.push(...bytes);
  const dword = n => { const b = Buffer.alloc(4); b.writeUInt32LE(n >>> 0); emit(...b); };
  // A real guest stdcall callback snapshots text before the validator reuses
  // its diagnostic buffer. No host callback substitutes validation behavior.
  emit(0x56, 0x57, 0x53, 0xa1); dword(count);
  emit(0x69, 0xc0); dword(2336);
  emit(0x05); dword(entries);
  emit(0x89, 0xc3, 0xff, 0x05); dword(count);
  for (let i = 0; i < 6; i++) emit(0x8b, 0x44, 0x24, 16 + i * 4, 0x89, 0x43, i * 4);
  for (const [arg, offset, limit] of [[0, 32, 255], [4, 288, 2047]]) {
    emit(0x8b, 0x74, 0x24, 16 + arg * 4, 0x8d, 0xbb); dword(offset);
    emit(0xb9); dword(limit);
    emit(0x85, 0xf6, 0x74, 9); // null source -> terminator
    emit(0xac, 0x84, 0xc0, 0x74, 4, 0xaa, 0x49, 0x75, 0xf7);
    emit(0x31, 0xc0, 0xaa);
  }
  emit(0x5b, 0x5f, 0x5e, 0x31, 0xc0, 0xc2, 0x18, 0x00);
  writeBytes(callback, code);
  writeBytes(scratch, Buffer.from('fixture.fx\0'));
  const reference = JSON.parse(fs.readFileSync(path.join(__dirname, 'reference/shader-validator.json'), 'utf8'));
  for (const fixture of reference.cases) {
    const obj = call(factory);
    assert.ok(obj, 'native factory allocates object');
    const vt = e.guest_read32(obj) >>> 0;
    const method = (slot, args = []) => call(e.guest_read32(vt + slot * 4) >>> 0, [obj, ...args]);
    for (const row of fixture.actions) {
      e.guest_write32(count, 0);
      let result;
      if (row.op === 'begin') result = method(3, [row.args[0] ? callback : 0, 0x1234, row.args[1]]);
      else if (row.op === 'instruction') {
        row.args[0].forEach((value, i) => e.guest_write32(scratch + 512 + i * 4, value));
        result = method(4, [scratch, 17, scratch + 512, row.args[0].length]);
      } else if (row.op === 'query') {
        const h = row.args[0].replaceAll('-', '');
        const iid = Buffer.from(h, 'hex');
        iid.subarray(0, 4).reverse(); iid.subarray(4, 6).reverse(); iid.subarray(6, 8).reverse();
        writeBytes(scratch + 128, iid);
        e.guest_write32(scratch + 256, 0x1234);
        result = method(0, [scratch + 128, scratch + 256]);
        const out = e.guest_read32(scratch + 256) >>> 0;
        assert.equal(out === 0, row.outputNull);
        assert.equal(out === obj, row.sameIdentity);
        if (result === 0) assert.equal(method(2), row.release);
      } else if (row.op === 'addref') {
        result = method(1);
        assert.equal(method(2), row.release);
      } else result = method(5);
      const label = `${fixture.name}/${row.op}`;
      assert.equal(result, row.result, label);
      const n = e.guest_read32(count) >>> 0;
      assert.ok(n <= 32, 'bounded diagnostic capture');
      const diagnostics = Array.from({ length: n }, (_, i) => {
        const at = entries + i * 2336;
        return { file: e.guest_read32(at) ? readA(at + 32) : null,
          line: e.guest_read32(at + 4) | 0, severity: e.guest_read32(at + 8) >>> 0,
          id: e.guest_read32(at + 12) >>> 0,
          message: e.guest_read32(at + 16) ? readA(at + 288) : null,
          context: e.guest_read32(at + 20) >>> 0 };
      });
      assert.deepEqual(diagnostics, row.diagnostics, label);
    }
    assert.equal(method(2), fixture.finalReferences, fixture.name);
    console.log(`PASS native validator ${fixture.name}`);
  }
  console.log(`PASS ${reference.cases.length} native-reference validator cases through integrated D3D9 adapter and x86 Wasm`);
})().catch(error => { console.error(error); process.exitCode = 1; });
