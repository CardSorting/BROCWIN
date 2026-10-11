'use strict';

// The production interpreter's elapsed-time accounting must not wait for the
// browser page just to read a clock also available in its own Worker.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const Module = require('node:module');
const { Worker } = require('node:worker_threads');
const runtime = path.resolve(__dirname, '../tools/wine-assembly');
const rpcPath = path.join(runtime, 'lib/guest-rpc.js');
const source = fs.readFileSync(process.argv[2] || rpcPath, 'utf8');
function loadRpc(text) {
  const mod = new Module(rpcPath);
  mod.filename = rpcPath;
  mod.paths = Module._nodeModulePaths(path.dirname(rpcPath));
  mod._compile(text, rpcPath);
  return mod.exports;
}

async function main() {
  const RPC = loadRpc(source);
  const memory = new WebAssembly.Memory({ initial: 8192, maximum: 8192, shared: true });
  const sigs = {
    real_time_ms: { params: [], results: ['i32'] },
    get_ticks: { params: [], results: ['i32'] },
  };
  let clock = 0;
  const broker = RPC.createMainBroker(memory, { real_time_ms: () => clock & 0x7fffffff }, sigs);
  const workerImports = RPC.createWorkerImports(memory, sigs,
    message => broker.serveRpc(message.slot), { slot: 1 });
  broker.publish({ tickMs: 123 });
  const originalNow = Date.now;
  try {
    Date.now = () => clock;
    for (const value of [0, 1, 0x7fffffff, 0x80000000, 0xffffffff, 1791710400123]) {
      clock = value;
      assert.equal(workerImports.imports.host.real_time_ms(), value & 0x7fffffff);
      assert.equal(workerImports.imports.host.get_ticks(), 123,
        'wall clock must not replace the independently published guest clock');
    }
  } finally { Date.now = originalNow; }

  const wasm = await WebAssembly.compile(fs.readFileSync(path.join(runtime, 'build/wine-assembly.wasm')));
  const ready = new Int32Array(new SharedArrayBuffer(16));
  const code = `
    const {parentPort, workerData} = require('node:worker_threads');
    const fs = require('node:fs');
    const path = require('node:path');
    const Module = require('node:module');
    const mod = new Module(workerData.rpcPath);
    mod.filename = workerData.rpcPath;
    mod.paths = Module._nodeModulePaths(path.dirname(mod.filename));
    mod._compile(workerData.source, mod.filename);
    const RPC = mod.exports;
    const built = RPC.createWorkerImports(workerData.memory, workerData.sigs,
      message => parentPort.postMessage(message), {slot: 2});
    const host = {memory: workerData.memory};
    for (const item of WebAssembly.Module.imports(workerData.wasm)) {
      if (item.kind === 'function') host[item.name] = () => {throw Error('Unexpected import '+item.name)};
    }
    host.real_time_ms = built.imports.host.real_time_ms;
    (async () => {
      const e = (await WebAssembly.instantiate(workerData.wasm, {host})).exports;
      e.set_current_thread_id(2);
      const state = new Int32Array(workerData.ready);
      parentPort.postMessage({ready:true});
      Atomics.wait(state, 0, 0);
      const before = Date.now();
      e.theseus_time_enter();
      e.theseus_time_enter();
      Atomics.wait(state, 3, 0, 40);
      e.theseus_time_leave();
      e.theseus_time_leave();
      const after = Date.now();
      const slot = e.theseus_get_thread_time_state() + 64;
      const elapsed = Number(new DataView(workerData.memory.buffer).getBigUint64(slot, true));
      Atomics.store(state, 1, 1);
      Atomics.notify(state, 1);
      parentPort.postMessage({done:true, elapsed, actualElapsed:after-before, stats:built.stats});
    })().catch(error => parentPort.postMessage({error:error.stack}));
  `;
  const worker = new Worker(code, { eval: true, workerData: {
    rpcPath, source, memory, sigs, wasm, ready: ready.buffer,
  }});
  let completedWithoutPage = false;
  try {
    const outcome = await new Promise((resolve, reject) => {
      const timeout = setTimeout(() => reject(Error('Worker clock regression timed out')), 10000);
      worker.on('error', reject);
      worker.on('message', message => {
        if (message.error) { clearTimeout(timeout); reject(Error(message.error)); }
        else if (message.ready) {
          Atomics.store(ready, 0, 1);
          Atomics.notify(ready, 0);
          // A page occupied for 200 ms cannot answer queued Worker RPCs.
          Atomics.wait(ready, 1, 0, 200);
          completedWithoutPage = Atomics.load(ready, 1) === 1;
        } else if (message.t === 'rpc') {
          clock = Date.now();
          broker.serveRpc(message.slot);
        } else if (message.done) { clearTimeout(timeout); resolve(message); }
      });
    });
    assert.equal(completedWithoutPage, true,
      'compiled interpreter accounting must finish while the page cannot answer RPC');
    assert.equal(outcome.stats.sync, 0, 'wall-clock accounting needs no synchronous host request');
    assert.equal(workerImports.stats.sync, 0, 'wall-clock value/wrap probes stay local');
    assert(outcome.elapsed >= 30 && outcome.elapsed <= outcome.actualElapsed + 5,
      'nested interpreter calls account the elapsed interval once');
    console.log(JSON.stringify({pass:true, completedWithoutPage, ...outcome}));
  } finally { await worker.terminate(); }
}
main().catch(error => { console.error(error.stack); process.exitCode = 1; });
