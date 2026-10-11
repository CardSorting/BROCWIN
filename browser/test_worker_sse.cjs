'use strict';

// CPU feature selection belongs to the process, including fresh Wasm instances
// in real Workers. A missing inheritance rule silently changed DLL dispatch.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const Module = require('node:module');
const { Worker } = require('node:worker_threads');
const runtime = path.resolve(__dirname, '../tools/wine-assembly');
const importsPath = path.join(runtime, 'lib/worker-imports.js');
const source = fs.readFileSync(process.argv[2] || importsPath, 'utf8');

function loadImports() {
  const mod = new Module(importsPath);
  mod.filename = importsPath;
  mod.paths = Module._nodeModulePaths(path.dirname(importsPath));
  mod._compile(source, importsPath);
  return mod.exports;
}

async function main() {
  const rules = loadImports();
  const wasm = await WebAssembly.compile(fs.readFileSync(path.join(runtime, 'build/wine-assembly.wasm')));
  const memory = new WebAssembly.Memory({ initial: 8192, maximum: 8192, shared: true });
  const host = { memory };
  for (const item of WebAssembly.Module.imports(wasm)) {
    if (item.kind === 'function') host[item.name] = () => { throw Error('Unexpected import ' + item.name); };
  }
  const mainExports = (await WebAssembly.instantiate(wasm, { host })).exports;
  const cases = [];
  for (const [name, current, recorded, initial, expected] of [
    ['capture-enabled', 1, null, 0, 1],
    ['capture-disabled', 0, null, 1, 0],
    ['recorded-enabled', 0, 1, 0, 1],
    ['recorded-disabled', 1, 0, 1, 0],
  ]) {
    mainExports.set_cpu_sse(current);
    const state = rules.captureInheritedWasmGlobals(mainExports);
    const configuration = rules.createInheritedWasmGlobals();
    if (recorded !== null) rules.recordInheritedWasmGlobal(configuration, 'set_cpu_sse', [recorded]);
    rules.mergeInheritedWasmGlobals(state, configuration);
    const target = (await WebAssembly.instantiate(wasm, { host })).exports;
    target.set_cpu_sse(initial);
    rules.applyInheritedWasmGlobals(target, state);
    cases.push({ name, initial, expected, state, cooperative: target.get_cpu_sse() });
  }

  const worker = new Worker(`
    const { parentPort, workerData: d } = require('node:worker_threads');
    const Module = require('node:module');
    const path = require('node:path');
    const mod = new Module(d.importsPath);
    mod.filename = d.importsPath;
    mod.paths = Module._nodeModulePaths(path.dirname(mod.filename));
    mod._compile(d.source, mod.filename);
    (async () => {
      const host = { memory: d.memory };
      for (const item of WebAssembly.Module.imports(d.wasm)) {
        if (item.kind === 'function') host[item.name] = () => { throw Error('Unexpected import ' + item.name); };
      }
      const results = [];
      for (const test of d.cases) {
        const e = (await WebAssembly.instantiate(d.wasm, { host })).exports;
        e.set_cpu_sse(test.initial);
        mod.exports.applyInheritedWasmGlobals(e, test.state);
        results.push({ name: test.name, actual: e.get_cpu_sse() });
      }
      parentPort.postMessage({ results });
    })().catch(error => parentPort.postMessage({ error: error.stack }));
  `, { eval: true, workerData: { importsPath, source, wasm, memory, cases } });
  try {
    const results = await new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(Error('Worker SSE inheritance timed out')), 10000);
      worker.once('error', error => { clearTimeout(timer); reject(error); });
      worker.once('message', message => {
        clearTimeout(timer);
        if (message.error) reject(Error(message.error));
        else resolve(message.results);
      });
    });
    const observations = cases.map((test, i) => ({ name: test.name, expected: test.expected,
      cooperative: test.cooperative, worker: results[i].actual }));
    console.log(JSON.stringify({ observations }));
    for (const test of observations) {
      assert.equal(test.worker, test.expected, test.name + ': fresh Worker must inherit the process CPU policy');
      assert.equal(test.cooperative, test.expected, test.name + ': cooperative instance must inherit the process CPU policy');
    }
    console.log('PASS 8 compiled-instance SSE inheritance checks, including explicit disable overrides');
  } finally { await worker.terminate(); }
}

main().catch(error => { console.error(error.stack); process.exitCode = 1; });
