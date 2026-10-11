'use strict';

const assert = require('node:assert/strict');
const path = require('node:path');
const { bootRenderHarness } = require(path.resolve(__dirname,
  '../tools/wine-assembly/test/render-helper.js'));

const extraWat = String.raw`
  (func (export "test_internet_open")
    (param $agent i32) (param $access i32) (param $proxy i32)
    (param $bypass i32) (param $flags i32) (param $wide i32) (result i32)
    (call $wininet_open (local.get $agent) (local.get $access) (local.get $proxy)
      (local.get $bypass) (local.get $flags) (local.get $wide)))
  (func (export "test_internet_close") (param $handle i32) (result i32)
    (local $esp i32)
    (local.set $esp (i32.load offset=16 (global.get $reg_base)))
    (call $handle_InternetCloseHandle (local.get $handle)
      (i32.const 0) (i32.const 0) (i32.const 0) (i32.const 0) (i32.const 0))
    (i32.store offset=16 (global.get $reg_base) (local.get $esp))
    (i32.load (global.get $reg_base)))
  (func (export "test_internet_error") (result i32) (global.get $last_error))
`;

(async () => {
  const { exports: e, memory } = await bootRenderHarness({ extraWat, fonts: 'none' });
  const view = new DataView(memory.buffer);
  const address = e.guest_alloc(1024) >>> 0;
  const at = value => e.guest_to_wasm(value) >>> 0;
  const read32 = value => view.getUint32(at(value), true);
  const write = (offset, value, wide) => {
    const bytes = Buffer.from(value + '\0', wide ? 'utf16le' : 'latin1');
    new Uint8Array(memory.buffer, at(address + offset), bytes.length).set(bytes);
    return address + offset;
  };
  const read = (pointer, wide) => {
    let value = '';
    for (let i = 0; i < 512; i += wide ? 2 : 1) {
      const ch = wide ? view.getUint16(at(pointer + i), true) : view.getUint8(at(pointer + i));
      if (!ch) return value;
      value += String.fromCharCode(ch);
    }
    throw new Error('Unterminated retained session string');
  };
  for (const wide of [0, 1]) {
    const agent = write(0, wide ? 'HTTP_WRAPPER_KOG 게임' : 'HTTP_WRAPPER_KOG', wide);
    const proxy = write(256, 'proxy.local:8080', wide);
    const bypass = write(512, '<local>', wide);
    const expected = read(agent, wide);
    const handle = e.test_internet_open(agent, 3, proxy, bypass, 0x10000000, wide) >>> 0;
    assert.ok(handle);
    assert.equal(read32(handle + 4), 1);
    assert.equal(read32(handle + 16), 3);
    assert.equal(read32(handle + 28), 0x10000000);
    assert.equal(read32(handle + 32), wide);
    write(0, 'caller changed its buffer', wide);
    assert.equal(read(read32(handle + 12), wide), expected);
    assert.equal(read(read32(handle + 20), wide), 'proxy.local:8080');
    assert.equal(read(read32(handle + 24), wide), '<local>');
    assert.equal(e.test_internet_close(handle), 1);
    assert.equal(e.test_internet_close(handle), 0);
    assert.equal(e.test_internet_error(), 6);
  }
  const direct = e.test_internet_open(0, 1, 1, 1, 0, 1) >>> 0;
  assert.ok(direct, 'direct mode ignores proxy pointers');
  assert.equal(read32(direct + 20), 0);
  assert.equal(read32(direct + 24), 0);
  assert.equal(e.test_internet_close(direct), 1);
  assert.equal(e.test_internet_open(1, 0, 0, 0, 0, 1), 0);
  assert.equal(e.test_internet_error(), 87);
  assert.equal(e.test_internet_open(0, 99, 0, 0, 0, 1), 0);
  assert.equal(e.test_internet_error(), 87);
  console.log('PASS WinINet A/W session ownership, encoding, options and close errors');
})().catch(error => { console.error(error); process.exitCode = 1; });
