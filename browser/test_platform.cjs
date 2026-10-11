'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const runtime = path.resolve(__dirname, '../tools/wine-assembly');
const { bootRenderHarness } = require(path.join(runtime, 'test/render-helper'));
const { loadDll, _test: { findDllExport } } = require(path.join(runtime, 'lib/dll-loader'));

const extraWat = String.raw`
  (func (export "test_platform_init")
    (global.set $image_base (i32.const 0x00400000))
    (global.set $exe_size_of_image (i32.const 0x00200000))
    (global.set $thunk_guest_base
      (i32.add (i32.sub (global.get $THUNK_BASE) (global.get $GUEST_BASE)) (global.get $image_base)))
    (call $heap_init (i32.const 0x01000000)))
  (func (export "test_platform_error") (result i32) (global.get $last_error))
  (func (export "test_platform_ordinal") (param i32 i32) (result i32)
    (call $system_ordinal_api_id (local.get 0) (local.get 1)))
  (func (export "test_platform_ordinal_call") (param i32 i32 i32 i32 i32)
    (call $dispatch_api_table (call $system_ordinal_api_id (local.get 0) (local.get 1))
      (local.get 2) (local.get 3) (local.get 4) (i32.const 0) (i32.const 0) (i32.const 0)))
  (func (export "test_platform_mui") (param i32 i32 i32 i32) (result i32)
    (call $theseus_thread_ui_languages (local.get 0) (local.get 1) (local.get 2) (local.get 3)))
  (func (export "test_platform_compare") (param i32 i32) (result i32)
    (call $nls_compare (local.get 0) (i32.const -1) (local.get 1) (i32.const -1) (i32.const 1) (i32.const 0)))
  (func (export "test_platform_adapters") (param i32 i32)
    (call $handle_GetAdaptersInfo (local.get 0) (local.get 1) (i32.const 0) (i32.const 0) (i32.const 0) (i32.const 0)))
  (func (export "test_platform_hostname") (param i32)
    (call $handle_gethostname (local.get 0) (i32.const 32) (i32.const 0) (i32.const 0) (i32.const 0) (i32.const 0)))
  (func (export "test_platform_hostbyname") (param i32)
    (call $handle_gethostbyname (local.get 0) (i32.const 0) (i32.const 0) (i32.const 0) (i32.const 0) (i32.const 0)))
` + ['StrCpyW', 'StrCatW', 'StrStrW'].map(name => `
  (func (export "test_platform_${name}") (param i32 i32)
    (call $handle_${name} (local.get 0) (local.get 1) (i32.const 0) (i32.const 0) (i32.const 0) (i32.const 0)))
`).join('') + ['A', 'W'].map(suffix => `
  (func (export "test_platform_filename_${suffix}") (param i32 i32 i32 i32)
    (call $handle_GetModuleFileNameEx${suffix} (local.get 0) (local.get 1) (local.get 2) (local.get 3) (i32.const 0) (i32.const 0)))
`).join('');

(async () => {
  const { exports: e, memory } = await bootRenderHarness({ extraWat, fonts: 'none' });
  e.test_platform_init();
  e.set_api_log(0);
  const buffer = e.guest_alloc(1024) >>> 0;
  const stack = e.guest_alloc(1024) >>> 0;
  const view = new DataView(memory.buffer);
  const read16 = at => view.getUint16(e.guest_to_wasm(at) >>> 0, true);
  const writeW = value => {
    for (let i = 0; i <= value.length; i++) e.guest_write16(buffer + 2 * i, value.charCodeAt(i) || 0);
  };
  const readW = (at, count) => Array.from({ length: count }, (_, i) =>
    String.fromCharCode(read16(at + i * 2))).join('');
  const modulePath = 'C:\\WINDOWS\\SYSTEM\\kernel32.dll';
  const winsockReference = JSON.parse(fs.readFileSync(path.join(__dirname, 'reference/winsock.json'), 'utf8'));
  const apiTable = require(path.join(runtime, 'src/api_table.json'));
  const writeA = (at, text) => new Uint8Array(memory.buffer, e.guest_to_wasm(at) >>> 0, text.length + 1)
    .set(Buffer.from(text + '\0', 'latin1'));
  const readA = at => {
    const bytes = new Uint8Array(memory.buffer, e.guest_to_wasm(at) >>> 0, 32);
    return Buffer.from(bytes.subarray(0, bytes.indexOf(0))).toString('ascii');
  };
  for (const [dll, reference] of Object.entries(winsockReference.exports)) {
    writeA(buffer, 'C:\\WINDOWS\\SYSTEM\\' + dll.toUpperCase());
    for (const [ordinal, name] of Object.entries(reference.ordinals)) {
      // The inherited htonl route uses the identical ntohl byte swap.
      const api = apiTable.find(row => row.name === (name === 'htonl' ? 'ntohl' : name));
      assert.equal(e.test_platform_ordinal(buffer, Number(ordinal)), api.id, `${dll}#${ordinal}: ${name}`);
    }
    const ntoaOrdinal = Number(Object.entries(reference.ordinals).find(([, name]) => name === 'inet_ntoa')[0]);
    const addrOrdinal = Number(Object.entries(reference.ordinals).find(([, name]) => name === 'inet_addr')[0]);
    for (const row of winsockReference.cases) {
      const sp = stack + 512;
      e.guest_write32(sp + 8, 0xffffffff); // Original x2 caller keeps the next call's length here.
      e.set_esp(sp);
      e.test_platform_ordinal_call(buffer, ntoaOrdinal, row.networkOrder, 0, 0);
      assert.equal(e.get_esp(), sp + 8, `${dll} inet_ntoa preserves the next call's argument`);
      assert.equal(e.guest_read32(e.get_esp()) >>> 0, 0xffffffff);
      assert.equal(readA(e.get_eax() >>> 0), row.text);
      writeA(buffer + 128, row.text);
      e.set_esp(sp);
      e.test_platform_ordinal_call(buffer, addrOrdinal, buffer + 128, 0, 0);
      assert.equal(e.get_eax() >>> 0, row.parsedNetworkOrder, `${dll} inet_addr ${row.text}`);
      assert.equal(e.get_esp(), sp + 8);
    }
    const ioctlOrdinal = Number(Object.entries(reference.ordinals).find(([, name]) => name === 'ioctlsocket')[0]);
    e.set_esp(stack + 512);
    e.test_platform_ordinal_call(buffer, ioctlOrdinal, -1, 0, 0);
    assert.equal(e.get_eax() | 0, -1, 'invalid socket is rejected');
    assert.equal(e.get_esp(), stack + 528, 'ioctlsocket removes three arguments');
  }
  const kernel = loadDll(e, memory.buffer, fs.readFileSync(path.join(__dirname, 'generated/platform/kernel32.dll')), modulePath);
  assert.equal(kernel.dllMain, 0, 'adapters have no fabricated initialization routine');
  assert.equal(read16(kernel.loadAddr), 0x5a4d, 'mapped handle points to PE headers');
  assert.notEqual(kernel.loadAddr, 0x10000000, 'test exercises relocated adapter code');
  const call = (name, args) => {
    const address = findDllExport(e, memory.buffer, kernel.loadAddr, name);
    assert.ok(address, name);
    const sp = stack + 512;
    e.guest_write32(sp, 0);
    args.forEach((arg, i) => e.guest_write32(sp + 4 + i * 4, arg));
    e.set_esp(sp);
    e.set_eip(address);
    e.run(10000);
    assert.equal(e.get_eip(), 0, `${name} returns through its original call frame`);
    assert.equal(e.get_esp(), sp + 4 + args.length * 4, `${name} cleans its stdcall arguments`);
    return e.get_eax() >>> 0;
  };
  const adapterReference = JSON.parse(fs.readFileSync(path.join(__dirname, 'reference/network-adapters.json'), 'utf8'));
  const adapter = e.guest_alloc(800) >>> 0, adapterSize = e.guest_alloc(4) >>> 0;
  const adapterBytes = new Uint8Array(memory.buffer, e.guest_to_wasm(adapter) >>> 0, 800);
  const layout = adapterReference.guestLayout;
  assert.equal(layout.size, 640);
  const adapters = (out, size) => {
    e.set_esp(stack + 512);
    e.test_platform_adapters(out, size);
    assert.equal(e.get_esp(), stack + 524, 'IP Helper stdcall removes two arguments');
    return e.get_eax() >>> 0;
  };
  const capacities = {'query-zero': 0, 'query-large': 704, 'short-zero': 0,
    'short-one': 1, 'short-last': 639, 'exact': 640, 'larger': 704};
  for (const row of adapterReference.cases) {
    adapterBytes.fill(0xa5);
    call('SetLastError', [0x1234]);
    if (row.case === 'null-size') {
      assert.equal(adapters(0, 0), row.result);
    } else {
      const capacity = capacities[row.case];
      e.guest_write32(adapterSize, capacity);
      assert.equal(adapters(row.case.startsWith('query') ? 0 : adapter, adapterSize), row.result, row.case);
      assert.equal(e.guest_read32(adapterSize), row.sizeUnchanged ? capacity : layout.size, row.case);
      assert.equal(adapterBytes.every(x => x === 0xa5), row.bufferUntouched, row.case);
      assert.ok(adapterBytes.subarray(capacity).every(x => x === 0xa5), 'caller capacity boundary');
      if (row.case === 'larger') assert.ok(adapterBytes.subarray(layout.size, capacity).every(x => x === 0));
    }
    assert.equal(e.test_platform_error(), row.lastError, row.case);
  }
  adapterBytes.fill(0xa5);
  assert.equal(adapters(adapter, 0xfffffff0), 87, 'unmapped size pointer');
  e.guest_write32(adapterSize, 640);
  assert.equal(adapters(0xfffffff0, adapterSize), 87, 'unmapped output');
  assert.ok(adapterBytes.every(x => x === 0xa5));
  for (const ip of [0x0a000001, 0x0a000007, 0x0a0000fe]) {
    e.set_vlan_local_ip(ip);
    e.guest_write32(adapterSize, 640);
    assert.equal(adapters(adapter, adapterSize), 0);
    const off = layout.offsets;
    assert.equal(readA(adapter + off.AdapterName), 'vlan0');
    assert.equal(readA(adapter + off.Description), 'Wine-Assembly Virtual LAN');
    assert.equal(e.guest_read32(adapter + off.AddressLength), 6);
    assert.deepEqual([...adapterBytes.subarray(off.Address, off.Address + 6)],
      [2, 0, ip >>> 24, (ip >>> 16) & 255, (ip >>> 8) & 255, ip & 255]);
    assert.equal(e.guest_read32(adapter + off.Index), 1);
    assert.equal(e.guest_read32(adapter + off.Type), 6);
    for (const name of ['Next', 'ComboIndex', 'DhcpEnabled', 'CurrentIpAddress', 'HaveWins',
      'LeaseObtained', 'LeaseExpires']) assert.equal(e.guest_read32(adapter + off[name]), 0, name);
    assert.equal(e.guest_read32(adapter + off.IpAddressList), 0, 'one address');
    assert.equal(readA(adapter + off.IpAddressList + 20), '255.255.255.0');
    assert.equal(readA(adapter + off.GatewayList + 4), '0.0.0.0');
    e.set_esp(stack + 512);
    e.test_platform_hostname(buffer);
    assert.equal(e.get_eax(), 0);
    e.set_esp(stack + 512);
    e.test_platform_hostbyname(buffer);
    const host = e.get_eax() >>> 0;
    assert.ok(host);
    const address = e.guest_read32(e.guest_read32(host + 12)) >>> 0;
    const bytes = new Uint8Array(memory.buffer, e.guest_to_wasm(address) >>> 0, 4);
    assert.equal(readA(adapter + off.IpAddressList + 4), [...bytes].join('.'), 'IP Helper and Winsock agree');
  }
  e.set_vlan_local_ip(0x0a000001);
  for (const row of winsockReference.cases.filter(row => row.parsedNetworkOrder !== 0xffffffff)) {
    writeA(buffer, row.text);
    e.set_esp(stack + 512);
    e.test_platform_hostbyname(buffer);
    const host = e.get_eax() >>> 0;
    assert.ok(host, `numeric gethostbyname ${row.text}`);
    const address = e.guest_read32(e.guest_read32(host + 12)) >>> 0;
    assert.equal(e.guest_read32(address) >>> 0, row.parsedNetworkOrder);
  }
  assert.equal(call('GetSystemDirectoryW', [buffer, 260]), 17);
  assert.equal(readW(buffer, 18), 'C:\\WINDOWS\\SYSTEM\0');
  e.guest_write32(buffer + 36, 0xa5a5a5a5);
  call('GetNativeSystemInfo', [buffer]);
  assert.equal(read16(buffer), 0, 'virtual native architecture is x86');
  assert.equal(e.guest_read32(buffer + 4), 4096, 'matches guest page size');
  assert.equal(e.guest_read32(buffer + 28), 65536, 'matches guest allocation granularity');
  assert.equal(e.guest_read32(buffer + 36) >>> 0, 0xa5a5a5a5, 'writes only the 36-byte x86 SYSTEM_INFO');
  for (const bytes of [0, 1, 3, 4, 5, 7, 8, 256]) {
    e.guest_write32(buffer, 0xa5a5a5a5);
    e.guest_write32(buffer + 4, 0xa5a5a5a5);
    e.guest_write32(buffer + 8, 0xa5a5a5a5);
    call('SetLastError', [0x1234]);
    assert.equal(call('K32EnumProcessModules', [-1, buffer, bytes, buffer + 512]), 1);
    assert.equal(e.guest_read32(buffer + 512), 8, 'EXE plus the one actually mapped kernel adapter');
    assert.equal(e.guest_read32(buffer) >>> 0, bytes < 4 ? 0xa5a5a5a5 : 0x00400000);
    assert.equal(e.guest_read32(buffer + 4) >>> 0, bytes < 8 ? 0xa5a5a5a5 : kernel.loadAddr);
    assert.equal(e.guest_read32(buffer + 8) >>> 0, 0xa5a5a5a5, 'does not write beyond existing modules');
    assert.equal(e.test_platform_error(), 0x1234, 'success preserves last error');
  }
  assert.equal(call('K32EnumProcessModules', [-1, 0, 3, buffer + 512]), 1);
  assert.equal(call('K32EnumProcessModules', [-1, 0, 4, buffer + 512]), 0);
  assert.equal(e.test_platform_error(), 998);
  assert.equal(call('K32EnumProcessModules', [0, buffer, 4, buffer + 512]), 0);
  assert.equal(e.test_platform_error(), 6);
  e.guest_write32(buffer, 0xa5a5a5a5);
  assert.equal(call('K32EnumProcessModules', [-1, buffer, 4, 0]), 0);
  assert.equal(e.test_platform_error(), 998);
  assert.equal(e.guest_read32(buffer), 0x00400000, 'output handles precede lpcbNeeded fault, as on Windows');
  const exeName = 'joysword\\x2.exe';
  const staging = e.get_staging();
  new Uint8Array(memory.buffer, staging, exeName.length).set(Buffer.from(exeName));
  e.set_exe_name(staging, exeName.length);
  e.set_exe_drive(0x43);
  for (const suffix of ['A', 'W']) {
    for (const [module, expected] of [[0, 'C:\\' + exeName], [0x400000, 'C:\\' + exeName], [kernel.loadAddr, modulePath]]) {
      for (const length of [0, 1, 2, 6, expected.length, expected.length + 1, 260]) {
        const wa = e.guest_to_wasm(buffer) >>> 0;
        new Uint8Array(memory.buffer, wa, 512).fill(0xa5);
        call('SetLastError', [0x1234]);
        e.set_esp(stack + 512);
        e[`test_platform_filename_${suffix}`](-1, module, buffer, length);
        assert.equal(e.get_esp(), stack + 532);
        const written = length ? Math.min(expected.length, length - 1) : 0;
        assert.equal(e.get_eax(), written);
        assert.equal(e.test_platform_error(), length ? 0x1234 : 122);
        const writesOutput = length > 0 && !(suffix === 'A' && length === 1);
        if (writesOutput) {
          const output = suffix === 'W' ? readW(buffer, written + 1) :
            Buffer.from(memory.buffer, wa, written + 1).toString('latin1');
          assert.equal(output, expected.slice(0, written) + '\0');
        } else assert.equal(e.guest_read32(buffer) >>> 0, 0xa5a5a5a5);
        const end = writesOutput ? (written + 1) * (suffix === 'W' ? 2 : 1) : 0;
        assert.equal(new Uint8Array(memory.buffer)[wa + end], 0xa5, 'does not overwrite beyond the output terminator');
      }
    }
    e[`test_platform_filename_${suffix}`](0, kernel.loadAddr, buffer, 260);
    assert.equal(e.get_eax(), 0);
    assert.equal(e.test_platform_error(), 6);
    e[`test_platform_filename_${suffix}`](-1, 123, buffer, 260);
    assert.equal(e.get_eax(), 0);
    assert.equal(e.test_platform_error(), 6);
  }
  const reference = JSON.parse(fs.readFileSync(path.resolve(__dirname,
    'reference/file-attribute-errors.json'), 'utf8'));
  for (const { path: filename, value, error } of reference) {
    writeW(filename);
    assert.equal(call('GetFileAttributesW', [buffer]), value, filename);
    assert.equal(e.test_platform_error(), error, filename);
  }
  const count = buffer + 512, size = buffer + 516;
  for (const [flags, expected, languages] of [[0x34, ['0409', '0009', '', ''].join('\0'), 2],
    [0x38, 'en-US\0en\0\0', 2], [0x44, '\0\0', 0]]) {
    e.guest_write32(size, 0);
    assert.equal(e.test_platform_mui(flags, count, 0, size), 1);
    assert.equal(e.guest_read32(size), expected.length);
    assert.equal(e.guest_read32(count), languages);
    e.guest_write32(size, expected.length - 1);
    e.guest_write32(buffer, 0xfeedbeef);
    assert.equal(e.test_platform_mui(flags, count, buffer, size), 0);
    assert.equal(e.test_platform_error(), 122);
    assert.equal(e.guest_read32(buffer) >>> 0, 0xfeedbeef);
    assert.equal(e.test_platform_mui(flags, count, buffer, size), 1);
    assert.equal(readW(buffer, expected.length), expected);
  }
  assert.equal(e.test_platform_mui(12, count, buffer, size), 0);
  assert.equal(e.test_platform_error(), 87);
  assert.equal(e.test_platform_mui(0x70, count, buffer, size), 0);
  assert.equal(e.test_platform_error(), 87);
  const comparisons = JSON.parse(fs.readFileSync(path.join(__dirname, 'reference/string-comparison.json'), 'utf8'));
  const collationGaps = [];
  for (const pair of comparisons) {
    writeW(pair.left);
    for (let i = 0; i <= pair.right.length; i++) e.guest_write16(buffer + 256 + i * 2, pair.right.charCodeAt(i) || 0);
    const actual = e.test_platform_compare(buffer, buffer + 256);
    if (/^[\x00-\x7f]*$/.test(pair.left + pair.right)) assert.equal(actual, pair.result, JSON.stringify(pair));
    else if (actual !== pair.result) collationGaps.push({ ...pair, actual });
  }
  // Keep unverified inherited NLS behavior visible rather than claiming Unicode parity.
  if (collationGaps.length) console.log('UNVERIFIED inherited Unicode collation:', JSON.stringify(collationGaps));
  const stringCases = JSON.parse(fs.readFileSync(path.join(__dirname, 'reference/shell-strings.json'), 'utf8')).cases;
  const writeAt = (at, value) => {
    for (let i = 0; i <= value.length; i++) e.guest_write16(at + 2 * i, value.charCodeAt(i) || 0);
  };
  for (const row of stringCases) {
    const lhs = row.left === null ? 0 : buffer;
    const rhs = row.right === null ? 0 : buffer + 256;
    if (lhs) writeAt(lhs, row.left);
    if (rhs) writeAt(rhs, row.right);
    e.set_esp(stack + 512);
    e[`test_platform_${row.api}`](lhs, rhs);
    assert.equal(e.get_eax() >>> 0, row.resultOffset === null ? 0 : lhs + 2 * row.resultOffset, JSON.stringify(row));
    assert.equal(e.get_esp(), stack + 524, `${row.api} stdcall cleanup`);
    if (row.output !== undefined) assert.equal(readW(lhs, row.output.length + 1), row.output + '\0');
  }
  const longBuffer = e.guest_alloc(160000) >>> 0;
  const longText = '\uac00'.repeat(33000);
  writeAt(longBuffer, longText);
  // An unsized append must not inherit the older wcslen helper's 32 Ki limit.
  writeAt(buffer, '\ub098');
  e.set_esp(stack + 512);
  e.test_platform_StrCatW(longBuffer, buffer);
  assert.equal(readW(longBuffer, 33002), longText + '\ub098\0');
  e.set_esp(stack + 512);
  e.test_platform_StrCpyW(longBuffer + 80000, longBuffer);
  assert.equal(readW(longBuffer + 80000, 33002), longText + '\ub098\0');
  const d3d = loadDll(e, memory.buffer, fs.readFileSync(path.join(__dirname, 'generated/platform/d3d9.dll')),
    'C:\\WINDOWS\\SYSTEM\\d3d9.dll');
  const debugMute = findDllExport(e, memory.buffer, d3d.loadAddr, 'DebugSetMute');
  assert.ok(debugMute);
  // Reproduce D3DX9's push/call/pop sequence. The original caller owns its
  // BOOL argument; treating this as stdcall(BOOL) would pop the return frame.
  const caller = e.guest_alloc(32) >>> 0;
  const code = Buffer.from('b800000000be0100000056ffd059c3', 'hex');
  code.writeUInt32LE(debugMute, 1);
  new Uint8Array(memory.buffer, e.guest_to_wasm(caller) >>> 0, code.length).set(code);
  e.guest_write32(stack + 512, 0);
  e.set_esp(stack + 512);
  e.set_eip(caller);
  e.run(10000);
  assert.equal(e.get_eip(), 0, 'original D3DX DebugSetMute sequence returns');
  assert.equal(e.get_esp(), stack + 516, 'caller removes its BOOL exactly once');
  assert.equal(e.get_eax() >>> 0, debugMute, 'release export writes no return value');
  assert.equal(e.get_ecx(), 1, 'caller retrieves the still-present BOOL');
  assert.equal(e.get_esi(), 1, 'callee-saved register survives');
  console.log(`PASS mapped PE adapters, relocated x86 calls, filename errors, UI languages and ${stringCases.length} native string cases`);
})().catch(error => { console.error(error); process.exitCode = 1; });
