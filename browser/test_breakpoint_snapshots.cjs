'use strict';
// Exercise the shipped Worker and interpreter, including movement of an armed
// breakpoint. Snapshot reads must not alter the observed guest memory.
const assert = require('node:assert/strict');
const fs = require('node:fs'), path = require('node:path');
const root = path.resolve(__dirname, '../tools/wine-assembly');
const {GuestThreadHost} = require(path.join(root, 'lib/guest-thread-host'));
const {createHostImports} = require(path.join(root, 'lib/host-imports'));
const R = require(path.join(root, 'lib/region-map.generated'));

(async () => {
  const module = await WebAssembly.compile(fs.readFileSync(path.join(root, 'build/wine-assembly.wasm')));
  const memory = new WebAssembly.Memory({initial: 8192, maximum: 8192, shared: true});
  const imports = createHostImports({getMemory: () => memory.buffer,
    resourceJson: {menus: {}, dialogs: {}, strings: {}, bitmaps: {}}, onExit() {}});
  imports.host.memory = memory;
  const observations = [];
  const host = new GuestThreadHost({memory, module, hostImports: imports.host,
    sigs: require(path.join(root, 'lib/host-import-sigs.generated.json')).sigs,
    workerUrl: path.join(root, 'lib/guest-worker.js'), clockIntervalMs: 0,
    log(message) {
      const at = message.indexOf('[breakpoint-snapshot] ');
      if (at >= 0) observations.push(JSON.parse(message.slice(at + 22)));
    }});
  try {
    await host.start();
    await host.callExport('init_thread', 0, 0x400000, 0x400000, 0x600000, 0x7500000, 0x7501000, 1, 1);
    const data = new Uint8Array(memory.buffer), wa = ga => R.GUEST_BASE + ga - 0x400000;
    data.set([0xbe,0x00,0x20,0x40,0x00,0xeb,0x09],wa(0x401000)); // mov esi,402000; jmp 401010
    data.set([0x40,0xeb,0x0d],wa(0x401010)); // inc eax; jmp 401020
    data.set([0x40,0xeb,0xfd],wa(0x401020)); // inc eax; loop
    new DataView(memory.buffer).setUint32(wa(0x402000),0x403000,true);
    data.set([17,23,91,255],wa(0x403000));
    const before = Buffer.from(data.slice(wa(0x402000),wa(0x404000)));
    await host.callExport('set_eip',0x401000);
    await host.callExport('set_esp',0x405000);
    await host.callExport('set_eax',0);
    await host.breakpointSnapshots([
      {address:0x401010,memory:[{register:'esi',indirect:[0],size:4},{register:'edx',size:4}]},
      {address:0x401020,memory:[{register:'esi',size:4}]},
    ]);
    for(let i=0;i<4&&observations.length<2;i++) await host.link.slice(64,{});
    assert.equal(observations.length,2,'both first breakpoint hits are observed');
    assert.deepEqual(observations.map(x=>x.registers.eax),[0,1]);
    assert.deepEqual(observations[0].memory[0].bytes,[17,23,91,255]);
    assert.deepEqual(observations[0].memory[1].bytes,[null,null,null,null]);
    assert.equal(await host.callExport('get_bp_addr'),0,'debugging disables after the plan');
    assert.deepEqual(Buffer.from(data.slice(wa(0x402000),wa(0x404000))),before);
    await assert.rejects(host.breakpointSnapshots([{address:0x401020,memory:[{register:'esi',size:65537}]}]),/Invalid breakpoint memory read/);
    assert.equal(await host.callExport('get_bp_addr'),0,'invalid plans do not arm a breakpoint');
    console.log('PASS shipped Worker: consecutive breakpoint first hits, indirect/null reads, memory unchanged, bounds, automatic disable');
  } finally { host.stop(); }
})().catch(error=>{console.error(error);process.exitCode=1;});
