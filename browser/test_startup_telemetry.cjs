'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
let poll, observe, clock = 0;
const context = {
  URL, location: {href: 'http://127.0.0.1:8767/'},
  performance: {now: () => clock, setResourceTimingBufferSize() {}, getEntriesByType: () => []},
  setInterval: callback => {poll = callback; return 1;}, clearInterval() {},
  PerformanceObserver: class {constructor(callback) {observe = callback;} observe() {}},
  WebAssembly: Object.fromEntries(['compile','instantiate','compileStreaming','instantiateStreaming']
    .map(name => [name, async () => ({})])),
  window: {fetch: async () => ({status: 200}), theseus: {state: 'executing', frames: 0, frameKinds: {gpu: 0}}}
};
vm.runInNewContext(fs.readFileSync(path.join(__dirname, 'startup_telemetry.js'), 'utf8'), context);
for (let index = 1; index <= 2500; index++) {
  clock = index;
  context.window.theseus.frames = index;
  context.window.theseus.frameKinds.gpu = index;
  poll();
  observe({getEntries: () => [{startTime: index, duration: 60}]});
}
const result = context.window.brocwinTelemetry.finish();
assert.equal(result.frames.length, 2048);
assert.equal(result.longTasks.length, 2048);
assert.equal(result.frames[0].total, 453);
assert.equal(result.frames.at(-1).total, 2500);
assert.equal(result.longTasks[0].start, 453);
assert.equal(result.longTasks.at(-1).start, 2500);
assert.equal(result.totals.frameSamples, 2500);
assert.equal(result.totals.longTasks, 2500);
assert.equal(result.totals.longTaskDurationMs, 150000);
assert.equal(result.marks.executing, 1);
assert.equal(result.marks.firstGPU, 1);
console.log('PASS: late telemetry retained beyond capacity, total counters exact, startup markers unchanged');
