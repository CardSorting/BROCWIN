'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { Worker } = require('node:worker_threads');
const runtime = path.resolve(__dirname, '../tools/wine-assembly');
const { callDllMain } = require(path.join(runtime, 'lib/dll-loader.js'));
const { ThreadManager } = require(path.join(runtime, 'lib/thread-manager.js'));
const trace = message => { if (process.env.THESEUS_TEST_TRACE) console.log(message); };

function checkDllFailurePolicy() {
  const memory = new WebAssembly.Memory({ initial: 128 });
  let eip = 0x401000, esp = 0x420000, eax = 1;
  const map = address => address - 0x400000 + 0x12000;
  const exports = {
    memory, get_image_base: () => 0x400000, get_fs_base: () => 0,
    get_eip: () => eip, get_esp: () => esp, get_eax: () => eax,
    set_eip: value => { eip = value; }, set_esp: value => { esp = value; },
    guest_to_wasm: map,
    run: () => { throw new Error('unsupported platform call'); },
  };
  assert.throws(() => callDllMain(exports, 0x500000, 0x501000, null, { strict: true }), /DllMain failed/);
  assert.equal(eip, 0x401000);
  assert.equal(esp, 0x420000);
  exports.run = () => { eip = 0; eax = 0; };
  assert.throws(() => callDllMain(exports, 0x500000, 0x501000, null, { strict: true }), /did not initialize/);
  exports.run = () => { eip = 0; eax = 1; };
  assert.doesNotThrow(() => callDllMain(exports, 0x500000, 0x501000, null, { strict: true }));
  assert.equal(eip, 0x401000);
  assert.equal(esp, 0x420000);
}

async function checkPointerEncoding() {
  const module = await WebAssembly.compile(fs.readFileSync(path.join(runtime, 'build/wine-assembly.wasm')));
  const memory = new WebAssembly.Memory({ initial: 8192, maximum: 8192, shared: true });
  const imports = { host: { memory } };
  for (const item of WebAssembly.Module.imports(module)) {
    if (item.kind === 'function') imports.host[item.name] = () => { throw new Error(`Unexpected host import ${item.name}`); };
  }
  const first = (await WebAssembly.instantiate(module, imports)).exports;
  assert.throws(() => first.theseus_encode_pointer(10), WebAssembly.RuntimeError);
  first.theseus_set_pointer_cookie(0x97e562bd);
  // Another guest thread's instance must decode the same process's pointers.
  const second = (await WebAssembly.instantiate(module, imports)).exports;
  assert.throws(() => second.theseus_set_pointer_cookie(1), WebAssembly.RuntimeError);
  const pointers = [0, 1, 0xffffffff, 0x80000000, 0x32830000];
  const random = crypto.randomBytes(4000);
  for (let i = 0; i < random.length; i += 4) pointers.push(random.readUInt32LE(i));
  for (const pointer of pointers) {
    const encoded = first.theseus_encode_pointer(pointer);
    assert.equal(second.theseus_decode_pointer(encoded) >>> 0, pointer >>> 0);
  }
  assert.notEqual(first.theseus_encode_pointer(0), 0);

  let now = 100;
  imports.host.real_time_ms = () => now;
  imports.host.log = () => {};
  imports.host.log_i32 = () => {};
  const timed = (await WebAssembly.instantiate(module, imports)).exports;
  const base = timed.theseus_get_thread_time_state();
  const counters = new DataView(memory.buffer);
  timed.theseus_time_enter();
  now = 102;
  timed.theseus_time_enter();
  now = 106;
  timed.theseus_time_leave();
  now = 110;
  timed.theseus_time_leave();
  assert.equal(counters.getBigUint64(base, true), 10n, 'nested interpreter calls count once');
  now = 500;
  timed.theseus_time_enter();
  now = 507;
  timed.theseus_time_leave();
  assert.equal(counters.getBigUint64(base, true), 17n, 'parked time is excluded');
  timed.set_current_thread_id(2);
  timed.theseus_time_enter();
  now = 512;
  timed.theseus_time_leave();
  assert.equal(counters.getBigUint64(base + 64, true), 5n, 'worker time is independent');
  assert.equal(counters.getBigUint64(base, true), 17n);

  const manager = Object.create(ThreadManager.prototype);
  manager.memory = memory;
  manager.threads = new Map([[0xe1000, { tid: 1 }]]);
  manager._pendingThreads = [];
  manager._threadHandleAliases = new Map();
  manager._mainThreadState = { tid: 0 };
  manager._threadTimes = new Map([[0, { created: 1000, exited: 0 }], [1, { created: 2000, exited: 2500 }]]);
  const out = base + 16;
  assert.equal(manager.getThreadTimes(-2, 1, out), 0);
  assert.equal(counters.getBigUint64(out, true), 116444736010000000n);
  assert.equal(counters.getBigUint64(out + 8, true), 0n);
  assert.equal(counters.getBigUint64(out + 24, true), 170000n);
  assert.equal(manager.getThreadTimes(0xe1000, 1, out), 0);
  assert.equal(counters.getBigUint64(out + 8, true), 116444736025000000n);
  assert.equal(counters.getBigUint64(out + 24, true), 50000n);
  assert.equal(manager.getThreadTimes(12345, 1, out), 6);

  const head = first.get_image_base() + 0x2000;
  // Offsets verified against the installed Windows SHLWAPI implementation.
  assert.equal(first.theseus_path_extension_w(0), 0);
  for (const [name, offset] of [['', 0], ['c:\\joysword\\x2.exe', 28],
    ['c:\\dir.ext\\file', 30], ['a.b.c', 6], ['x2.', 4], ['.hidden', 0],
    ['a.b c', 10], ['a.b/c', 2], ['게임.데이터', 4], ['📁게임.kom', 8]]) {
    const address = head + 0x1000;
    const bytes = Buffer.from(name + '\0', 'utf16le');
    new Uint8Array(memory.buffer, first.guest_to_wasm(address), bytes.length).set(bytes);
    assert.equal(first.theseus_path_extension_w(address), address + offset, name);
  }
  assert.equal(first.theseus_path_filename(0, 1), 0);
  for (const [name, offset] of [['', 0], ['c:\\joysword\\x2.exe', 24], ['C:foo.txt', 4],
    ['C:', 0], ['C:\\', 0], ['C:\\\\', 0], ['/a/b', 6], ['/a/', 2], ['a:b:c', 0],
    ['\\\\server\\share\\file', 30], ['a//b', 6], ['a\\\\b', 6], ['게임/📁.dat', 6],
    ['xx/a:b:c', 6], ['C:\\a:b', 10], ['a:b:c/d:e', 16], ['a:b:c//', 0]]) {
    const address = head + 0x1000;
    const bytes = Buffer.from(name + '\0', 'utf16le');
    new Uint8Array(memory.buffer, first.guest_to_wasm(address), bytes.length).set(bytes);
    assert.equal(first.theseus_path_filename(address, 1), address + offset, name);
    if (/^[\x00-\x7f]*$/.test(name)) {
      const ansiBytes = Buffer.from(name + '\0', 'ascii');
      new Uint8Array(memory.buffer, first.guest_to_wasm(address), ansiBytes.length).set(ansiBytes);
      assert.equal(first.theseus_path_filename(address, 0), address + offset / 2, name + ' ANSI');
    }
  }
  const dbcsPath = head + 0x1000;
  new Uint8Array(memory.buffer, first.guest_to_wasm(dbcsPath), 4).set([0x81, 0x5c, 0x61, 0]);
  first.set_ansi_code_page(932);
  assert.equal(first.theseus_path_filename(dbcsPath, 0), dbcsPath, 'DBCS trail byte is not a separator');
  first.set_ansi_code_page(1252);
  const referencePaths = JSON.parse(fs.readFileSync(path.join(__dirname, 'reference/windows-paths.json'), 'utf8'));
  for (const reference of referencePaths.records) {
    const address = head + 0x1000;
    const wide = Buffer.from(reference.path + '\0', 'utf16le');
    new Uint8Array(memory.buffer, first.guest_to_wasm(address), wide.length).set(wide);
    assert.equal(first.theseus_path_extension_w(address) - address, reference.PathFindExtensionW);
    assert.equal(first.theseus_path_filename(address, 1) - address, reference.PathFindFileNameW);
    if (reference.PathFindFileNameA !== undefined) {
      const narrow = Buffer.from(reference.path + '\0', 'ascii');
      new Uint8Array(memory.buffer, first.guest_to_wasm(address), narrow.length).set(narrow);
      assert.equal(first.theseus_path_filename(address, 0) - address, reference.PathFindFileNameA);
    }
  }
  const entry = head + 0x100;
  assert.equal(first.theseus_slist(head, 0, 0), 0);
  assert.equal(first.theseus_slist(head, 0, 2), 0);
  assert.equal(first.theseus_slist(head, entry, 1), 0);
  assert.equal(second.theseus_slist(head, entry + 8, 1), entry);
  assert.equal(first.theseus_slist(head, 0, 4), 2);
  assert.equal(first.theseus_slist(head, 0, 2), entry + 8);
  assert.equal(first.theseus_slist(head, 0, 3), entry);
  assert.equal(first.theseus_slist(head, 0, 4), 0);

  timed.set_current_thread_id(1);
  // Production initializes this in the PE loader; this low-level test has no PE.
  timed.heap_init(first.get_image_base() + 0x200000);
  trace(`FLS: heap initialized at ${(first.get_image_base() + 0x200000).toString(16)}`);
  second.set_current_thread_id(2);
  let fls = timed.theseus_fls_alloc(0);
  trace(`FLS: allocated index ${fls}`);
  assert(fls >= 0);
  assert.equal(timed.theseus_fls_get(fls), 0);
  assert.equal(timed.theseus_fls_set(fls, 101), 1);
  assert.equal(second.theseus_fls_get(fls), 0, 'new threads see a zero FLS value');
  assert.equal(second.theseus_fls_set(fls, 202), 1);
  assert.equal(timed.theseus_fls_get(fls), 101);
  trace('FLS: independent thread values verified');
  assert.equal(timed.theseus_fls_free(fls), 1);
  assert.equal(timed.theseus_fls_free(fls), 0, 'freed indices are invalid');
  fls = timed.theseus_fls_alloc(0);
  assert.equal(second.theseus_fls_get(fls), 0, 'index reuse clears every thread');
  timed.theseus_fls_free(fls);
  trace('FLS: index reuse verified');

  // Execute an actual x86 FLS destructor, rather than mocking its invocation:
  // LFENCE; MFENCE; SFENCE; mov eax,[esp+4]; inc dword ptr[eax]; ret 4.
  const callback = head + 0x11000, counter = head + 0x12000;
  const code = new Uint8Array([0x0f, 0xae, 0xe8, 0x0f, 0xae, 0xf0, 0x0f, 0xae, 0xf8,
    0x8b, 0x44, 0x24, 0x04, 0xff, 0x00, 0xc2, 0x04, 0x00]);
  new Uint8Array(memory.buffer, timed.guest_to_wasm(callback), code.length).set(code);
  timed.set_esp(head + 0x13000);
  timed.guest_write32(counter, 0);
  fls = timed.theseus_fls_alloc(callback);
  timed.theseus_fls_set(fls, counter);
  second.theseus_fls_set(fls, counter);
  trace('FLS: running native destructors');
  assert.equal(timed.theseus_fls_free(fls), 1);
  assert.equal(timed.guest_read32(counter), 2, 'FlsFree calls the destructor for every nonzero value');
  assert.equal(timed.get_esp(), head + 0x13000, 'callback restores caller stack');
  fls = timed.theseus_fls_alloc(callback);
  timed.theseus_fls_set(fls, counter);
  timed.theseus_fls_cleanup();
  assert.equal(timed.guest_read32(counter), 3, 'thread exit runs the destructor');
  timed.theseus_fls_cleanup();
  assert.equal(timed.guest_read32(counter), 3, 'cleanup does not repeat a cleared value');
  timed.theseus_fls_free(fls);
  trace('FLS: destructors verified');

  const outer = timed.theseus_actctx_push();
  const moduleBase = head + 0x50000, resourceRoot = moduleBase + 0x1000;
  assert.equal(timed.theseus_manifest_resource_status(moduleBase, 0, 2), 1812);
  assert.equal(timed.theseus_manifest_resource_status(moduleBase, 0x1000, 2), 1813);
  timed.guest_write32(resourceRoot + 12, 1 << 16); // one integer resource type
  timed.guest_write32(resourceRoot + 16, 24);
  timed.guest_write32(resourceRoot + 20, 0x80000020);
  assert.equal(timed.theseus_manifest_resource_status(moduleBase, 0x1000, 2), 1814);
  timed.guest_write32(resourceRoot + 0x20 + 12, 1 << 16);
  timed.guest_write32(resourceRoot + 0x20 + 16, 2);
  timed.guest_write32(resourceRoot + 0x20 + 20, 0x80000040);
  assert.equal(timed.theseus_manifest_resource_status(moduleBase, 0x1000, 2), 1815);
  timed.guest_write32(resourceRoot + 0x40 + 12, 1 << 16);
  timed.guest_write32(resourceRoot + 0x40 + 16, 0x409);
  timed.guest_write32(resourceRoot + 0x40 + 20, 0x60);
  assert.equal(timed.theseus_manifest_resource_status(moduleBase, 0x1000, 2), 0,
    'a present manifest is not misrepresented as a missing resource');
  const inner = timed.theseus_actctx_push();
  assert(outer && inner && outer !== inner);
  assert.equal(timed.theseus_actctx_pop(0, outer) >>> 0, 0xc015000f, 'out-of-order deactivation is observable');
  assert.equal(second.theseus_actctx_pop(0, inner) >>> 0, 0xc0150010, 'cookies belong to one thread');
  assert.equal(timed.theseus_actctx_pop(1, inner), 87, 'force-early is invalid for the top frame');
  assert.equal(timed.theseus_actctx_pop(1, outer), 0, 'force-early removes the entire suffix');
  assert.equal(timed.theseus_actctx_pop(0, inner) >>> 0, 0xc0150010);
  const finalContext = timed.theseus_actctx_push();
  assert.equal(timed.theseus_actctx_pop(0, finalContext), 0);

  // Concurrent publication must not lose entries or report an inconsistent
  // depth. Exercise the very same Wasm CAS loop with independent instances.
  await Promise.all(Array.from({ length: 4 }, (_, index) => new Promise((resolve, reject) => {
    const worker = new Worker(`
      const { parentPort, workerData: d } = require('node:worker_threads');
      const host = { memory: d.memory };
      for (const item of WebAssembly.Module.imports(d.module))
        if (item.kind === 'function') host[item.name] = () => { throw Error(item.name); };
      const e = new WebAssembly.Instance(d.module, { host }).exports;
      for (let n = 0; n < 1000; n++) e.theseus_slist(d.head, d.start + n * 8, 1);
      parentPort.postMessage('done');
    `, { eval: true, workerData: { module, memory, head, start: head + 0x100 + index * 8000 } });
    worker.on('error', reject);
    worker.on('exit', code => code ? reject(new Error(`SList worker exit ${code}`)) : resolve());
  })));
  assert.equal(first.theseus_slist(head, 0, 4), 4000);
  const seen = new Set();
  let node;
  while ((node = first.theseus_slist(head, 0, 2)) !== 0) {
    assert(!seen.has(node), 'list entry must occur only once');
    seen.add(node);
  }
  assert.equal(seen.size, 4000);
  assert.equal(first.theseus_slist(head, 0, 4), 0);
}

(async () => {
  checkDllFailurePolicy();
  await checkPointerEncoding();
  console.log('PASS: DLL failure policy, pointer encoding, thread timing, concurrent SLists, x86 FLS callbacks/fences, activation stacks/resources, and Windows path reference cases');
})().catch(error => { console.error(error); process.exitCode = 1; });
