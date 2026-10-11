'use strict';

// The only launch route. The compiled client, all its data, and reconstructed
// platform services share one WineAssembly process in this browser page.
const statusEl = document.querySelector('#status');
const logEl = document.querySelector('#log');
const startEl = document.querySelector('#start');
const stopEl = document.querySelector('#stop');
const records = [];
let manifest;
let client;
let networkWire;
let statePoll;
let renderer;
let runtimeCache;
const runningApps = [];
window.theseus = { records, get client() { return client; },
  get network() { return networkWire?.snapshot() || null; }, state: 'preparing' };

function record(kind, message, detail = null) {
  // Host input diagnostics include character/key codes, including passwords.
  // Keep message routing evidence without retaining the typed values.
  message = String(message).replace(/(\[input\][^\n]*?wParam=)0x[\da-f]+/gi, '$1[redacted]');
  const row = { time: new Date().toISOString(), kind, message, detail };
  records.push(row);
  if (records.length > 10000) records.shift();
  logEl.textContent = records.slice(-100).map(r => `${r.time} [${r.kind}] ${r.message}`).join('\n');
  logEl.scrollTop = logEl.scrollHeight;
}

function fail(error) {
  clearInterval(statePoll);
  runningApps.length = 0;
  networkWire?.close();
  window.theseus.state = 'stopped-incomplete';
  statusEl.textContent = 'Stopped — compatibility work required';
  record('incomplete', error.stack || error.message || error);
  stopEl.disabled = true;
  startEl.disabled = false;
}

async function checkedBytes(url, hash) {
  if (runtimeCache && hash) return runtimeCache.bytes(url, hash);
  const response = await fetch(url);
  if (!response.ok) throw new Error(`${url}: HTTP ${response.status}`);
  const bytes = new Uint8Array(await response.arrayBuffer());
  if (hash) {
    const digest = await crypto.subtle.digest('SHA-256', bytes);
    const actual = Array.from(new Uint8Array(digest), b => b.toString(16).padStart(2, '0')).join('');
    if (actual !== hash) throw new Error(`Input changed since prepare: ${url}`);
  }
  return bytes;
}

async function boot() {
  if (!crossOriginIsolated) throw new Error('Shared Wasm memory requires the Theseus server isolation headers.');
  manifest = await (await fetch('manifest.json')).json();
  if (typeof BrocwinRuntimeCache !== 'undefined') {
    runtimeCache = await BrocwinRuntimeCache.open(manifest,
      new URLSearchParams(location.search).get('runtimePolicy'));
    window.theseus.runtimeCache = runtimeCache;
    record('runtime-policy', 'Validated startup cache policy',
      {configuration:runtimeCache.policy,identity:runtimeCache.identity,
        deviceMemory:navigator.deviceMemory ?? null,hardwareConcurrency:navigator.hardwareConcurrency});
  }
  window.theseus.manifest = manifest;
  window.WINE_SOURCE_VERSION = manifest.runtime.commit;
  window.WINE_THREADS = true;
  window.WINE_D3DIM_LAZY_SYNC = true;
  for (const entry of [...manifest.runtime.scripts,
    {url: 'local_server_wire.js', sha256: manifest.runtime.integration['local_server_wire.js']}]) {
    // Dependencies use classic-script globals and require their manifest order.
    await new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = `${entry.url}?v=${manifest.runtime.commit}`;
      script.integrity = 'sha256-' + btoa(entry.sha256.match(/../g).map(byte => String.fromCharCode(parseInt(byte, 16))).join(''));
      script.onload = resolve;
      script.onerror = () => reject(new Error(`Cannot load ${entry.url}`));
      document.head.append(script);
    });
  }
  // Pin the code actually instantiated, not just the name in the download log.
  WineAssembly._wasmModulePromise = runtimeCache
    ? runtimeCache.module(manifest.runtime.wasm.url, manifest.runtime.wasm.sha256)
    : WebAssembly.compile(await checkedBytes(manifest.runtime.wasm.url, manifest.runtime.wasm.sha256));
  await WineAssembly._wasmModulePromise;
  runtimeCache?.installResourceFetch(manifest);
  if (runtimeCache && manifest.runtime.sourceFiles['lib/validated-artifact-cache.js']) {
    const entry = 'lib/validated-artifact-cache.js';
    await new Promise((resolve,reject) => {
      const script=document.createElement('script');script.src=entry;
      script.integrity='sha256-'+btoa(manifest.runtime.sourceFiles[entry].match(/../g)
        .map(byte=>String.fromCharCode(parseInt(byte,16))).join(''));
      script.onload=resolve;script.onerror=()=>reject(new Error('Cannot load runtime artifact cache'));
      document.head.append(script);
    });
    window.theseus.artifacts = await ValidatedArtifactCache.forManifest(manifest);
    window.theseus.artifacts.install(window.D3D9Shader, window.D3D9Texture);
  }
  // DOM input is a page-lifetime binding. Reuse its renderer across launches;
  // WineAssembly.stop clears the stopped process's windows and publishers.
  renderer = new Win98Renderer(document.querySelector('#game'));
  renderer.transparentDesktop = true;
  window.browserInput.wireCanvasInput(document.querySelector('#game'), renderer, {runningApps});
  record('provenance', `Wine-Assembly ${manifest.runtime.commit}; Wasm ${manifest.runtime.wasm.sha256}`);
  const adapters = manifest.runtime.platformDlls.filter(f => f.provenance === 'reconstructed-wasm-export-adapter').length;
  const components = manifest.runtime.platformDlls.length - adapters;
  record('inputs', `${manifest.files.length} local inputs, including ${adapters} reconstructed platform adapters and ${components} local compiled platform components; ${manifest.modules.length} inspected original PE modules`);
  statusEl.textContent = 'Ready to execute original client in WebAssembly';
  window.theseus.state = 'ready';
  startEl.disabled = false;
}

async function launch() {
  startEl.disabled = true;
  stopEl.disabled = false;
  try {
    clearInterval(statePoll);
    if (client) client.stop();
    networkWire?.close();
    window.theseus.frames = 0;
    window.theseus.frameKinds = {};
    window.theseus.state = 'loading';
    statusEl.textContent = 'Loading client and runtime libraries';
    client = new WineAssembly();
    runningApps.splice(0, runningApps.length, {wine: client});
    client.onStopped = stopped => { if (stopped === client) runningApps.length = 0; };
    const networkResponse = await fetch('network.json');
    if (!networkResponse.ok) throw new Error('Cannot load local server transport configuration');
    const networkConfiguration = await networkResponse.json();
    networkWire = new TheseusLocalServerWire(networkConfiguration,
      state => record('network', `Local byte transport ${state}`));
    await networkWire.ready;
    client.joinVlan(networkWire, networkConfiguration.clientIp);
    // Capture 20261008T074033Z exhausted the 316 MiB sparse backing pool
    // repeatedly during real resource loading, after its corruption was fixed.
    client.bigMemory = true;
    // Select the original D3DX SSE math path, covered by native-reference
    // matrix, quaternion and skinning comparisons. Workers inherit this policy.
    client.cpuSSE = true;
    // The original FX assets require programmable shaders. This enables the
    // existing compatibility profile; device creation/rendering need validation.
    client.d3d9Programmable = true;
    client.verbose = new URLSearchParams(location.search).get('trace') === '1';
    window.__waTraceCategories = new URLSearchParams(location.search).get('traceFs') === '1' ? new Set(['fs']) : null;
    client.strictDllInit = true;
    client.threads = true;
    client.renderer = renderer;
    renderer._exited = false;
    renderer.inputQueue.length = 0;
    client.onGuestFrame = frame => {
      window.theseus.frames++;
      const kind = frame?.kind || 'unspecified';
      window.theseus.frameKinds[kind] = (window.theseus.frameKinds[kind] || 0) + 1;
    };
    client.logToUI = message => record('runtime', message);
    await client.init(document.querySelector('#game'));
    for (const port of networkConfiguration.loopbackPorts) {
      if (!client.instance.exports.set_vlan_loopback_port(port, 1)) throw new Error(`Cannot route local server port ${port}`);
    }
    record('network', 'Configured TCP/UDP routes for the original local services',
      {ports: networkConfiguration.loopbackPorts, serverExecution: networkConfiguration.serverExecution,
        udpImplemented: networkConfiguration.udpImplemented, udpPorts: networkConfiguration.udpPorts,
        udpTargets: networkConfiguration.udpTargets, gameExchangeVerified: false});
    client.instance.exports.theseus_set_pointer_cookie(crypto.getRandomValues(new Uint32Array(1))[0]);
    const exe = manifest.files.find(f => f.url === manifest.exe);
    const bytes = await checkedBytes(exe.url, exe.sha256);
    await client.loadExe(manifest.exe, { bytes, guestPath: manifest.exeGuestPath, args: manifest.args });
    // The original VS2010 client targets NT, not the dependency's Win98 default.
    // This selects the compatibility ABI; it does not alter the host OS.
    await client.callGuest('set_winver', 0x1db10106); // Windows 7 SP1, build 7601
    await client.loadFiles(manifest.files.filter(f => f.url !== manifest.exe).map(f => ({
      url: f.url, vfsPath: f.vfsPath, size: f.size, loadMode: f.loadMode,
    })), { required: true });
    // The inherited launcher starts in client/data. Its browser equivalent is
    // the directory containing the mapped EXE, not the VFS default C:\ root.
    const workingDirectory = manifest.exeGuestPath.slice(0, manifest.exeGuestPath.lastIndexOf('\\'));
    const vfs = client._helpCtx?.vfs;
    if (!vfs?.setCurrentDirectory(workingDirectory)) throw new Error(`Cannot set guest working directory: ${workingDirectory}`);
    record('working-directory', vfs.getCurrentDirectory());
    const dlls = [];
    for (const url of [...manifest.runtime.platformDlls.map(f => f.url), ...manifest.dlls]) {
      const file = manifest.files.find(f => f.url === url);
      dlls.push({ name: url.split('/').pop(), bytes: await checkedBytes(url, file.sha256), path: file.vfsPath });
    }
    await client.loadDlls(dlls);
    const entryState = {};
    for (const name of ['eip', 'esp', 'ebp', 'eax', 'ecx', 'edx', 'fs_base', 'image_base', 'code_start', 'code_end']) {
      entryState[name] = (await client.callGuest('get_' + name)) >>> 0;
    }
    record('entry-state', 'Original executable startup state', entryState);
    const actualEntryWord = (await client.callGuest('guest_read32', entryState.eip)) >>> 0;
    const entryRva = entryState.eip - entryState.image_base;
    const entrySection = peLib.readPE(bytes).sections.find(section =>
      entryRva >= section.rva && entryRva + 4 <= section.rva + section.rawSize);
    if (!entrySection) throw new Error('Executable entry is outside initialized PE sections');
    const originalEntryWord = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength)
      .getUint32(entrySection.rawOff + entryRva - entrySection.rva, true);
    record('entry-bytes', 'Mapped executable entry compared with original file',
      { address: entryState.eip, actualEntryWord, originalEntryWord });
    if (actualEntryWord !== originalEntryWord) throw new Error('Mapped entry bytes differ from the original executable');
    record('execute', `x2.exe ${exe.sha256}; entry 0x${manifest.modules[0].entryPoint.toString(16)}`);
    const watch = new URLSearchParams(location.search).get('watch');
    if (watch) {
      if (!/^[0-9a-fA-F]{1,8}$/.test(watch)) throw new Error('watch requires a hexadecimal guest address');
      const address = parseInt(watch, 16);
      if (address < 0x10000 || address > 0x7ffffffc) throw new Error('watch address is outside the guest user range');
      await client.callGuest('set_watchpoint_size', 4);
      await client.callGuest('set_watchpoint', address);
      // New workers inherit debug settings from the host instance.
      client.instance.exports.set_watchpoint_size(4);
      client.instance.exports.set_watchpoint(address);
      record('diagnostic', 'Watching original guest memory; debug mode changes execution timing', { address });
    }
    const codeTrace = new URLSearchParams(location.search).get('traceCode');
    if (codeTrace) {
      const parts = codeTrace.split(':');
      if (parts.length !== 2 || !parts.every(part => /^[0-9a-fA-F]{1,8}$/.test(part))) {
        throw new Error('traceCode requires two hexadecimal addresses separated by a colon');
      }
      window.__waProfileEipHit = (eip, tid) => record('code-block',
        `Original block 0x${eip.toString(16)}`, { eip, tid });
      await client.callGuest('set_trace_eip_range', 1, parseInt(parts[0], 16), parseInt(parts[1], 16));
    }
    window.theseus.state = 'executing';
    statusEl.textContent = 'Executing original code — port incomplete';
    client.run();
    clearInterval(statePoll);
    statePoll = setInterval(() => {
      if (window.theseus.state === 'executing' && client && !client.running) {
        fail(new Error('Original client execution ended; full port acceptance remains incomplete. See runtime log.'));
        clearInterval(statePoll);
      }
    }, 250);
    document.querySelector('#game').focus();
  } catch (error) {
    if (client) client.stop();
    fail(error);
  }
}

startEl.addEventListener('click', launch);
stopEl.addEventListener('click', () => {
  clearInterval(statePoll);
  if (client) client.stop();
  networkWire?.close();
  window.theseus.state = 'stopped';
  statusEl.textContent = 'Stopped';
  startEl.disabled = false;
  stopEl.disabled = true;
  record('stop', 'Browser execution stopped by user');
});
document.querySelector('#export').addEventListener('click', () => {
  const blob = new Blob([JSON.stringify({ schema: 'theseus.execution/v1',
    runtime: manifest?.runtime, state: window.theseus.state,
    verifiedGameplay: false, userAgent: navigator.userAgent, records }, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const link = Object.assign(document.createElement('a'), { href: url, download: 'theseus-execution.json' });
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
});
window.addEventListener('error', event => record('error', event.error?.stack || event.message));
window.addEventListener('unhandledrejection', event => record('error', event.reason?.stack || event.reason));
boot().catch(fail);
