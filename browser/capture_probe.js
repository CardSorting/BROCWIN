// Observation of the integrated client. Loaded by capture.py after boot and
// before launch; never substitutes guest instructions or return values. Optional
// watchpoints use the existing debugger and change scheduling, not guest bytes.
(() => {
  const observations = [];
  let traceWindows = false;
  let heapFailureCount = 0;
  const breakpointHosts = new WeakMap();
  let drawCapture = null;
  // Observe the original native session's length/header/serial fields only.
  // No game payload, credentials, decryption, packet changes or extra RPC.
  // Native static references: KSkSession::OnRecvCompleted 0x538a60 and
  // authentication serial read 0xce33ae (GameServer identity in report).
  const sentHeaders = {streams: new Map(), recent: [], anomalies: [], errors: [], ignoredStreams: 0};
  function observeSentHeader(bytes) {
    if (bytes.length < 28) return;
    const d = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
    const kind = d.getUint32(4, true);
    if (d.getUint32(0, true) !== 0x314e4c56 || d.getUint32(16, true) !== 0x7f000001 ||
        d.getUint32(20, true) !== 9300 || ![1, 3].includes(kind)) return;
    const sourcePort = d.getUint32(12, true), key = d.getUint32(8, true) + ':' + sourcePort;
    let s = sentHeaders.streams.get(key);
    if (!s && sentHeaders.streams.size >= 16) { sentHeaders.ignoredStreams++; return; }
    if (kind === 1) {
      s = {sourcePort, header: new Uint8Array(8), offset: 0, length: 0, packets: 0,
        previousSerial: null, nonIncreasing: 0, invalid: false, connection: (s?.connection || 0) + 1};
      sentHeaders.streams.set(key, s);
      return;
    }
    // Without the connection's beginning, a transport fragment has no known
    // game-packet boundary. Do not guess a header from an arbitrary byte.
    if (!s || s.invalid) return;
    let at = 28;
    while (at < bytes.length) {
      if (s.offset < 8) {
        const n = Math.min(8 - s.offset, bytes.length - at);
        s.header.set(bytes.subarray(at, at + n), s.offset); at += n; s.offset += n;
        if (s.offset >= 2 && !s.length) {
          s.length = s.header[0] | s.header[1] << 8;
          if (s.length < 8) {
            s.invalid = true;
            if (sentHeaders.errors.length < 8) sentHeaders.errors.push({sourcePort, length: s.length,
              packet: s.packets + 1, reason: 'short packet; header interpretation stopped'});
            return;
          }
        }
        if (s.offset < 8) continue;
      }
      const n = Math.min(s.length - s.offset, bytes.length - at);
      at += n; s.offset += n;
      if (s.offset !== s.length) continue;
      const h = new DataView(s.header.buffer), serial = h.getUint32(4, true);
      const row = {time: performance.now(), sourcePort, connection: s.connection,
        packet: ++s.packets, length: s.length, prefixWord: h.getUint16(2, true), serial};
      if (s.previousSerial !== null && serial <= s.previousSerial && s.previousSerial !== 0xffffffff) {
        s.nonIncreasing++;
        if (sentHeaders.anomalies.length < 16) sentHeaders.anomalies.push({...row, previousSerial: s.previousSerial});
      }
      s.previousSerial = serial;
      sentHeaders.recent.push(row);
      if (sentHeaders.recent.length > 64) sentHeaders.recent.shift();
      s.offset = 0; s.length = 0;
    }
  }
  if (typeof TheseusLocalServerWire !== 'undefined') {
    const send = TheseusLocalServerWire.prototype.send;
    TheseusLocalServerWire.prototype.send = function(...args) {
      const accepted = send.apply(this, args);
      if (accepted) try { observeSentHeader(args[0]); }
      catch (error) {
        if (sentHeaders.errors.length < 8) sentHeaders.errors.push({reason: String(error)});
      }
      return accepted;
    };
  }
  function sentHeaderState() {
    return {scope: 'Accepted TCP9300 length/header/serial metadata only; no payload or authentication verdict',
      guestMemoryWrites: false, streams: [...sentHeaders.streams.values()].map(s => ({
        sourcePort: s.sourcePort, connection: s.connection, packets: s.packets,
        previousSerial: s.previousSerial, nonIncreasing: s.nonIncreasing,
        pendingBytes: s.offset, pendingLength: s.length, invalid: s.invalid})),
      recent: sentHeaders.recent.map(r => ({...r})), anomalies: sentHeaders.anomalies.map(r => ({...r})),
      errors: sentHeaders.errors.map(r => ({...r})), ignoredStreams: sentHeaders.ignoredStreams};
  }
  function captureDraws(options) {
    if (drawCapture && ['waiting-for-present', 'capturing'].includes(drawCapture.state))
      throw new Error('A draw capture is already active');
    const maxDraws = options.maxDraws ?? 256, maxBytes = options.maxBytes ?? 16777216;
    if (!Number.isInteger(maxDraws) || maxDraws < 1 || maxDraws > 512 ||
        !Number.isInteger(maxBytes) || maxBytes < 1 || maxBytes > 33554432)
      throw new Error('Invalid draw capture bounds');
    const bridge = window.theseus.client?.hostCtx?.d3d9Bridge;
    if (!bridge || !window.D3DCommandStream) throw new Error('Draw capture requires the running D3D9 bridge');
    const op = window.D3DCommandStream.OPCODES, real = bridge._submit;
    const record = drawCapture = {schema: 'theseus.draw-observation/v1',
      scope: 'Actual submitted draw geometry, shaders and constants; texture pixels omitted; not a scene replay',
      state: 'waiting-for-present', maxDraws, maxBytes, binaryBytes: 0,
      programmableOnly: options.programmableOnly !== false, seenDraws: 0, draws: [],
      timingAltered: true, guestMemoryWrites: false};
    let device;
    const byteSize = value => {
      if (ArrayBuffer.isView(value)) return value.byteLength;
      if (value instanceof ArrayBuffer) return value.byteLength;
      if (!value || typeof value !== 'object') return 0;
      return Object.values(value).reduce((n, v) => n + byteSize(v), 0);
    };
    const encode = value => {
      if (ArrayBuffer.isView(value) || value instanceof ArrayBuffer) {
        const bytes = ArrayBuffer.isView(value) ? new Uint8Array(value.buffer, value.byteOffset, value.byteLength) : new Uint8Array(value);
        let binary = '';
        for (let p = 0; p < bytes.length; p += 16384) binary += String.fromCharCode(...bytes.subarray(p, p + 16384));
        return {type: value.constructor.name, byteLength: bytes.length, base64: btoa(binary)};
      }
      if (Array.isArray(value)) return value.map(encode);
      if (!value || typeof value !== 'object') return value;
      return Object.fromEntries(Object.entries(value).map(([k, v]) => [k, encode(v)]));
    };
    bridge._submit = function(entry, opcode, payload) {
      try {
        if (opcode === op.PRESENT && record.state === 'waiting-for-present') {
          device = entry;
          record.state = 'capturing'; record.startedAt = performance.now();
        } else if (entry === device && record.state === 'capturing') {
          if (opcode === op.PRESENT) {
            record.state = 'complete'; record.endedAt = performance.now(); this._submit = real;
          } else if (opcode === op.DRAW) {
            const ordinal = record.seenDraws++;
            if (!record.programmableOnly || payload.vertexShader) {
              const {textures, textureReleases, ...data} = payload;
              const size = byteSize(data);
              if (record.draws.length >= maxDraws || record.binaryBytes + size > maxBytes) {
                record.state = 'truncated'; record.endedAt = performance.now(); this._submit = real;
              } else {
                record.draws.push({ordinal, payload: encode(data)});
                record.binaryBytes += size;
              }
            }
          }
        }
      } catch (error) {
        record.state = 'probe-error'; record.error = String(error); this._submit = real;
      }
      // Observe before reusable scratch arrays can change. Never replace the
      // command, its result, or a runtime exception with a diagnostic result.
      return real.call(this, entry, opcode, payload);
    };
    return record;
  }
  function renderState(client, includePayloads = false) {
    const bridge = client?.hostCtx?.d3d9Bridge;
    if (!bridge) return null;
    const error = value => value ? String(value) : null;
    const first = map => map ? Array.from(map).slice(0, 64) : [];
    // Read queue bookkeeping only. Never poll/consume a render token, submit a
    // command, wait on GL, or invoke guest execution to collect this snapshot.
    let remaining = 1048576;
    const encode = (value, depth = 0) => {
      if (depth > 12 || remaining <= 0) return {omitted: 'observation limit'};
      if (ArrayBuffer.isView(value) || value instanceof ArrayBuffer) {
        const bytes = ArrayBuffer.isView(value) ? new Uint8Array(value.buffer, value.byteOffset, value.byteLength) : new Uint8Array(value);
        const length = Math.min(bytes.length, remaining); remaining -= length;
        let binary = '';
        for (let at = 0; at < length; at += 16384) binary += String.fromCharCode(...bytes.subarray(at, Math.min(at + 16384, length)));
        return {type: value.constructor.name, byteLength: bytes.length, capturedBytes: length, base64: btoa(binary)};
      }
      if (!value || typeof value !== 'object') { remaining -= 8; return value; }
      if (Array.isArray(value)) return value.slice(0, 512).map(v => encode(v, depth + 1));
      return Object.fromEntries(Object.entries(value).slice(0, 128)
        .filter(([k]) => k !== 'textures' && k !== 'textureReleases')
        .map(([k, v]) => [k, encode(v, depth + 1)]));
    };
    const names = Object.fromEntries(Object.entries(window.D3DCommandStream?.OPCODES || {}).map(([k, v]) => [v, k]));
    const manager = client._renderWorkerManager, wait = client._d3dMainWait;
    return {scope: 'Read-only render bookkeeping; asynchronous observations are not atomic',
      payloadScope: includePayloads ? 'Pending payloads only, texture data omitted, at most one MiB of binary data' : null,
      closed: !!bridge.closed, presentWaits: bridge.presentWaits?.size ?? null,
      mainWait: wait ? {token: wait.token, done: wait.done} : null,
      requests: first(bridge.requests).map(([token, r]) => ({token, done: r.done,
        generation: r.generation, deviceId: r.entry?.queue?.deviceId, error: error(r.error)})),
      manager: manager ? {stopped: manager.stopped, sequence: manager.sequence,
        queuedBytes: manager.queuedBytes, pending: first(manager.pending), failure: error(manager._failure),
        ports: first(manager.ports).map(([id, p]) => ({id, closed: p.closed, requests: p.requests?.size ?? null}))} : null,
      devices: first(bridge.devices).map(([id, e]) => {
        const q = e.queue, state = q?.snapshot();
        return {id, kind: e.kind, async: !!e.async, sharedWorker: !!e.sharedWorker,
          dead: !!e.dead, lost: !!e.lost, deferred: e.deferred?.size ?? 0,
          deferredError: error(e.deferredError), queue: state ? {...state, error: error(state.error)} : null,
          workerPending: first(e.workerConsumer?.pending).map(([key]) => key),
          pendingCommands: first(q?._entries).map(([sequence, r]) => ({sequence,
            opcode: r.command.opcode, name: names[r.command.opcode], status: r.status,
            consumed: r.consumed, retired: r.retired,
            primitive: r.command.payload?.primitive, primitiveCount: r.command.payload?.primitiveCount,
            ...(includePayloads ? {payload: encode(r.command.payload)} : {})}))};
      })};
  }
  function windowState(win) {
    if (!win) return null;
    const layer = win._gpuFrameLayer || win._dxFrameLayer;
    return {hwnd: win.hwnd, x: win.x, y: win.y, w: win.w, h: win.h,
      style: win.style, visible: win.visible, clientRect: win.clientRect ? {...win.clientRect} : null,
      frame: layer?.canvas ? {width: layer.canvas.width, height: layer.canvas.height, kind: layer.kind} : null};
  }
  function threadState(client) {
    const guest = client?.guestWorker, rpc = window.GuestRpc, r = reader(client);
    if (!guest || !rpc?.views || !r) return null;
    const metadata = Array.from(client.threadManager?.threads || []);
    const links = [guest.link, ...Array.from(guest.threadLinks?.values() || [])].filter(Boolean).slice(0, 16);
    const census = guest.broker?.stats?.();
    return {scope: 'Read-only shared RPC and saved registers; no request to the Worker. Registers may predate the stall.',
      memoryObservationAtomic: false, guestMemoryWrites: false,
      broker: census ? {served: census.served, missing: census.missing,
        calls: census.calls.slice(0, 32), callKinds: census.calls.length} : null,
      threads: links.map(link => {
        const [handle, thread] = metadata.find(([, t]) => t.link === link) || [0, null];
        const tid = link.slot === 0 ? 0 : thread?.tid;
        const v = rpc.views(client.memory, link.slot).i32;
        const statusBefore = Atomics.load(v, rpc.SLOT.STATUS), fn = Atomics.load(v, rpc.SLOT.FN);
        const row = {slot: link.slot, handle, tid: tid ?? null, state: thread?.state ?? null,
          statusBefore, importId: fn, importName: guest.broker?.names?.[fn] ?? null,
          statusAfter: Atomics.load(v, rpc.SLOT.STATUS),
          // An idle slot retains its previous import ID; it is not an active call.
          pendingRequests: link._pending?.size ?? null, sliceStats: link.sliceStats ? {...link.sliceStats, ends: {...link.sliceStats.ends}} : null,
          parkedWait: thread?.parkedWait ? {...thread.parkedWait} : null};
        if (Number.isInteger(tid) && tid >= 0 && tid < RegionMap.SIZE.REGFILE / 64) {
          const base = RegionMap.BASE.REGFILE + tid * 64;
          row.savedRegisters = Array.from({length: 8}, (_, i) => r.dv.getUint32(base + i * 4, true));
          row.savedStack = stack(r, row.savedRegisters[4], row.savedRegisters[5]);
        }
        return row;
      })};
  }
  function audioState(client) {
    const voices = client?.hostCtx?._voices || client?._helpCtx?._voices;
    if (!voices) return null;
    const ac = voices._ac, buffer = client?.memory?.buffer;
    const dv = buffer ? new DataView(buffer) : null;
    const entries = Object.entries(voices._map || {});
    return {contextState: ac?.state ?? null, sampleRate: ac?.sampleRate ?? null,
      currentTime: ac?.currentTime ?? null, voiceCount: entries.length,
      scope: 'Read-only voice state, shared PCM and submitted AudioBuffer samples; not proof of audible quality or fidelity',
      memoryObservationAtomic: false,
      voices: entries.slice(0, 32).map(([id, v]) => {
        const ptr = v.ringPtr, len = v.ringLen;
        let pcm = null;
        if (dv && Number.isInteger(ptr) && Number.isInteger(len) && ptr >= 0 && len > 0 &&
            ptr + len <= dv.byteLength && [8, 16].includes(v.bits)) {
          const stride = v.bits / 8, count = Math.min(32768, Math.floor(len / stride));
          let peak = 0, nonzero = 0;
          for (let i = 0; i < count; i++) {
            const value = v.bits === 16 ? dv.getInt16(ptr + i * stride, true) : dv.getUint8(ptr + i) - 128;
            peak = Math.max(peak, Math.abs(value));
            if (value) nonzero++;
          }
          pcm = {sampledValues: count, nonzero, peak, byteLength: len};
        }
        let submitted = null;
        const audioBuffer = v.currentSrc?.buffer;
        if (audioBuffer) {
          const channels = [];
          for (let channel = 0; channel < Math.min(8, audioBuffer.numberOfChannels); channel++) {
            const samples = audioBuffer.getChannelData(channel);
            const count = Math.min(16384, samples.length);
            let peak = 0, nonzero = 0, nonfinite = 0;
            for (let i = 0; i < count; i++) {
              const value = samples[i];
              if (!Number.isFinite(value)) { nonfinite++; continue; }
              peak = Math.max(peak, Math.abs(value));
              if (value) nonzero++;
            }
            channels.push({channel, sampledValues: count, nonzero, nonfinite, peak});
          }
          submitted = {sampleRate: audioBuffer.sampleRate, length: audioBuffer.length,
            duration: audioBuffer.duration, channels};
        }
        return {id: Number(id), rate: v.rate, channels: v.channels, bits: v.bits,
          mode: v.mode, paused: v.paused, snapshotPlaying: v.snapshotPlaying,
          worklet: !!v.workletNode, source: !!v.currentSrc, gain: v.gainValue,
          bytesWritten: v.bytesWritten, pcm, submitted};
      })};
  }
  const hex = n => '0x' + (n >>> 0).toString(16).padStart(8, '0');
  function reader(client = window.theseus.client) {
    if (!client?.memory?.buffer) return null;
    const dv = new DataView(client.memory.buffer);
    const address = ga => client._guestToWasmAddress(ga >>> 0) >>> 0;
    const valid = ga => ga && address(ga) !== 0xf0 && address(ga) + 4 <= dv.byteLength;
    const u32 = ga => valid(ga) ? dv.getUint32(address(ga), true) : null;
    const u8 = ga => valid(ga) ? dv.getUint8(address(ga)) : null;
    const words = (ga, n) => Array.from({length: n}, (_, i) => u32((ga + i * 4) >>> 0));
    const string = (ga, max = 512) => {
      const bytes = [];
      for (let i = 0; i < max; i++) {
        const b = u8(ga + i);
        if (b === null || b === 0) break;
        bytes.push(b);
      }
      return new TextDecoder().decode(new Uint8Array(bytes));
    };
    return {dv, address, valid, u32, u8, words, string};
  }
  function stack(r, esp, ebp) {
    const frames = [];
    const seen = new Set();
    while (r.valid(ebp) && !seen.has(ebp) && frames.length < 20) {
      seen.add(ebp);
      frames.push({ebp, returnAddress: r.u32(ebp + 4), args: r.words(ebp + 8, 6)});
      const next = r.u32(ebp);
      if (next <= ebp || next - ebp > 0x10000) break;
      ebp = next;
    }
    return {esp, words: r.words(esp, 96), frames};
  }
  // This decoder is specific to the unmodified input SHA below. Field offsets
  // come from X2's x86 luaV_execute (0x331a1f20) and Lua 5.1.5 lstate/lobject.h.
  // They are observations, not a replacement implementation of the game's Lua.
  function lua(r, L, pc = null) {
    if (!r.valid(L) || r.u8(L + 4) !== 8) return null;
    const top = r.u32(L + 8), base = r.u32(L + 12), ci = r.u32(L + 20);
    if (!r.valid(top - 16) || !r.valid(base) || !r.valid(ci)) return null;
    const value = p => {
      const type = r.u32(p + 8), data = r.u32(p);
      return {type, data, words: r.words(p, 4),
        text: type === 4 && r.valid(data) ? r.string(data + 16) : undefined};
    };
    const calls = [];
    const baseCi = r.u32(L + 40);
    for (let p = ci; p >= baseCi && calls.length < 12; p -= 24) {
      const func = r.u32(p + 4), closure = r.u32(func);
      const isC = r.u8(closure + 6), proto = r.u32(closure + 16);
      const entry = {ci: p, words: r.words(p, 6), func, closure, isC};
      if (isC === 0 && r.valid(proto)) {
        const code = r.u32(proto + 12), source = r.u32(proto + 32);
        Object.assign(entry, {proto, code, codeWords: r.u32(proto + 44),
          source: r.valid(source) ? r.string(source + 16) : null,
          protoWords: r.words(proto, 19), firstCode: r.words(code, 12)});
      }
      calls.push(entry);
    }
    return {L, words: r.words(L, 30), top, base, pc, topValue: value(top - 16),
      firstValues: Array.from({length: Math.min(8, Math.max(0, (top - base) / 16))}, (_, i) => value(base + i * 16)), calls};
  }
  const originalInput = () => window.theseus.manifest?.files?.some(f =>
    f.url === window.theseus.manifest.exe && f.sha256 === 'fe84cc1a95fc38b6d0d441997298828b133c7645e10a879978903e504d52d2f1');
  const original = window.createHostImports;
  window.createHostImports = function(ctx) {
    const result = original(ctx);
    const realThrow = result.host.cxx_throw;
    result.host.cxx_throw = (...args) => {
      realThrow(...args);
      try {
        const r = reader(), [argp, eip, esp] = args;
        const obj = r.u32(argp + 4), jump = r.u32(obj);
        const observation = {kind: 'cxx-throw-memory', time: performance.now(), eip, esp,
          args: r.words(argp, 4), object: r.words(obj, 8), stack: stack(r, esp, 0)};
        if (originalInput() && jump) {
          for (const candidate of r.words(esp, 1024)) {
            if (candidate && r.u32(candidate + 112) === jump) {
              const state = lua(r, candidate);
              if (state) { observation.lua = state; break; }
            }
          }
        }
        observations.push(observation);
        console.log('[capture exception] ' + JSON.stringify(observation));
      } catch (error) { observations.push({kind: 'probe-error', message: String(error)}); }
    };
    return result;
  };
  // Host.getImports replaces create_window after createHostImports returns.
  // Observe the final import table so geometry includes that actual route.
  const realImports = WineAssembly.prototype.getImports;
  WineAssembly.prototype.getImports = function(...options) {
    const result = realImports.apply(this, options);
    // OOM may be followed by invalid original control flow before the next
    // sample. Retain the bounded shared arena table at the existing import,
    // while its caller is parked; other workers can still change these bytes.
    const realHeapOom = result.host?.heap_oom_trace;
    if (typeof realHeapOom === 'function') result.host.heap_oom_trace = (...args) => {
      if (heapFailureCount++ < 2) try {
        const r = reader(this);
        if (!r) throw new Error('Heap failure memory unavailable');
        const base = RegionMap.BASE.HEAP_ARENAS;
        const capacity = (RegionMap.SIZE.HEAP_ARENAS - 16) / 16;
        const count = r.dv.getUint32(base, true), records = [];
        for (let i = 0; i < Math.min(count, capacity); i++) {
          const at = base + 16 + i * 16;
          records.push(Array.from({length: 4}, (_, j) => r.dv.getUint32(at + j * 4, true)));
        }
        const observation = {kind: 'heap-failure', time: performance.now(),
          size: args[0] >>> 0, reason: args[1], memoryObservationAtomic: false,
          guestMemoryWrites: false, count, capacity, records,
          threads: threadState(this)};
        observations.push(observation);
        console.log('[capture heap failure] ' + JSON.stringify(observation));
      } catch (error) { observations.push({kind: 'heap-probe-error', message: String(error)}); }
      return realHeapOom(...args);
    };
    // ExitProcess releases the process memory synchronously. Observe its
    // caller before invoking the real import; a later sample cannot recover
    // this stack. The RPC caller is parked, while other threads may still run.
    const realExit = result.host?.exit;
    if (typeof realExit === 'function') result.host.exit = (...args) => {
      try {
        const r = reader(this), tm = this.threadManager;
        const handle = tm?._runningThreadHandle || 0;
        const tid = handle ? tm.threads.get(handle)?.tid : 0;
        // REGFILE_STRIDE is the 64-byte thread-register ABI in 01-header.wat.
        if (!r || !Number.isInteger(tid) || tid < 0 || tid >= RegionMap.SIZE.REGFILE / 64)
          throw new Error('Exit caller register file unavailable');
        const base = RegionMap.BASE.REGFILE + tid * 64;
        const regs = Array.from({length: 8}, (_, i) => r.dv.getUint32(base + i * 4, true));
        const observation = {kind: 'process-exit', time: performance.now(), code: args[0],
          threadHandle: handle, tid, rpcSlot: this.guestWorker?.audioRpcSlot ?? null,
          memoryObservationAtomic: false, registers: regs,
          // The Win32 handler already popped its return address and argument.
          stack: stack(r, (regs[4] - 8) >>> 0, regs[5]),
          runtime: window.theseusCaptureProbe.runtime(), files: window.theseusCaptureProbe.files()};
        observations.push(observation);
        console.log('[capture exit] ' + JSON.stringify(observation));
      } catch (error) { observations.push({kind: 'exit-probe-error', message: String(error)}); }
      return realExit(...args);
    };
    if (traceWindows) for (const name of ['create_window', 'move_window', 'sync_window_client', 'show_window']) {
      const real = result.host[name];
      if (typeof real !== 'function') continue;
      result.host[name] = (...args) => {
        const before = windowState(this.renderer?.windows?.[args[0]]);
        const value = real(...args);
        const entry = {kind: 'window-geometry', operation: name, time: performance.now(), args,
          before, after: windowState(this.renderer?.windows?.[args[0]])};
        if (name === 'move_window') {
          const r = reader(this), regs = RegionMap.BASE.REGFILE;
          entry.mainThreadStack = stack(r, r.dv.getUint32(regs + 16, true), r.dv.getUint32(regs + 20, true));
          entry.memoryObservationAtomic = false;
        }
        observations.push(entry);
        console.log('[capture window] ' + JSON.stringify(entry));
        return value;
      };
    }
    return result;
  };
  window.theseusCaptureProbe = {
    observations,
    configure(options) { traceWindows = !!options.traceWindows; },
    async breakpoints(points, scope = 'main') {
      const client = window.theseus.client;
      if (!client?.guestWorker?.breakpointSnapshots) throw new Error('Breakpoint snapshots require a running guest Worker');
      if (!['main', 'all'].includes(scope)) throw new Error('Invalid breakpoint scope');
      const guest = client.guestWorker;
      // Validate on the main Worker before replacing the plan for other threads.
      const result = await guest.breakpointSnapshots(points);
      let state = breakpointHosts.get(guest);
      if (!state && scope === 'all') {
        state = {points: null};
        breakpointHosts.set(guest, state);
        const spawn = guest.spawnThread;
        guest.spawnThread = async function(...args) {
          const link = await spawn.apply(this, args);
          // ThreadManager cannot run the new guest thread until spawn returns.
          // Arm here, rather than polling after its first loading instructions.
          const points = state.points;
          if (points?.length) {
            await link.breakpointSnapshots(points);
            observations.push({kind: 'breakpoint-thread-armed', slot: link.slot,
              time: performance.now(), count: points.length, schedulingAltered: true});
          }
          return link;
        };
      }
      if (state) {
        state.points = scope === 'all' && points.length ? structuredClone(points) : null;
        await Promise.all([...guest.threadLinks.values()].map(link =>
          link.breakpointSnapshots(state.points || [])));
      }
      observations.push({kind: 'breakpoint-plan', time: performance.now(), points, scope,
        slots: scope === 'all' ? [0, ...guest.threadLinks.keys()] : [0], schedulingAltered: true});
      return result.count;
    },
    watchPointer({pointerAddress, offset = 0}) {
      if (!Number.isInteger(pointerAddress) || pointerAddress < 0x10000 || pointerAddress > 0x7ffffffc ||
          !Number.isInteger(offset) || offset < 0 || offset > 0x100000) throw new Error('Invalid pointer watch');
      const timer = setInterval(async () => {
        if (window.theseus.state !== 'executing') return;
        const r = reader();
        if (!r) return;
        const object = r.u32(pointerAddress);
        if (!object || object < 0x10000 || object + offset > 0x7ffffffc || !r.valid(object + offset)) return;
        clearInterval(timer);
        const client = window.theseus.client, address = object + offset;
        try {
          await client.callGuest('set_watchpoint_size', 4);
          await client.callGuest('set_watchpoint', address);
          client.instance.exports.set_watchpoint_size(4);
          client.instance.exports.set_watchpoint(address);
          const observation = {kind: 'watchpoint-armed', pointerAddress, object, address, time: performance.now(),
            schedulingAltered: true, objectWords: r.words(object, 128)};
          observations.push(observation);
          console.log('[capture watchpoint] ' + JSON.stringify(observation));
        } catch (error) { observations.push({kind: 'probe-error', message: String(error)}); }
      }, 25);
    },
    inspect(request) {
      if (request.drawCapture && typeof request.drawCapture === 'object') captureDraws(request.drawCapture);
      const draws = {...(request.drawCapture ? {drawCapture} : {}),
        ...(request.renderState ? {renderState: renderState(window.theseus.client, true)} : {})};
      const r = reader();
      if (!r) return {unavailable: 'guest memory released or not initialized', memory: [],
        observations, runtime: this.runtime(), files: request.files ? this.files() : undefined, ...draws};
      let total = 0;
      const memory = (request.memory || []).map(({address, size}) => {
        address >>>= 0;
        size >>>= 0;
        total += size;
        if (total > 1048576) throw new Error('Probe read exceeds one MiB');
        return {address, size, bytes: Array.from({length: size}, (_, i) => r.u8(address + i))};
      });
      return {memory, observations, runtime: this.runtime(), files: request.files ? this.files() : undefined, ...draws};
    },
    runtime() {
      const client = window.theseus.client, bridge = client?.hostCtx?.d3d9Bridge;
      const r = reader(client), sockets = [];
      for (let i = 0; r && i < RegionMap.SIZE.VSOCK_TABLE / 128; i++) {
        const p = RegionMap.BASE.VSOCK_TABLE + i * 128, state = r.dv.getUint32(p, true);
        if (state) sockets.push({index: i, state, words: Array.from({length: 16}, (_, j) => r.dv.getUint32(p + j * 4, true))});
      }
      return {memoryAvailable: !!r, graphics: bridge ? {backend: bridge.backend,
        programmable: bridge.options.enableProgrammable, probed: bridge.probed ?? null,
        deviceCount: bridge.devices.size, lastError: bridge.lastError ? String(bridge.lastError) : null,
        failureDetail: bridge.lastError?.diagnostic ?? null, renderState: renderState(client)} : null,
        sockets, network: window.theseus.network, sentHeaders: sentHeaderState(),
        audio: audioState(client), threads: threadState(client),
        input: {browserWired: !!window.browserInput?.isWired(),
          queuedEvents: client?.renderer?.inputQueue?.length ?? null},
        windows: Object.values(client?.renderer?.windows || {}).map(windowState),
        canvas: client?.renderer?.canvas ? {width: client.renderer.canvas.width, height: client.renderer.canvas.height} : null};
    },
    async sample() {
      const client = window.theseus.client, guest = client?.guestWorker;
      if (!guest?.readExports) return {unavailable: true};
      const names = ['eip', 'esp', 'ebp', 'eax', 'ebx', 'ecx', 'edx', 'esi', 'edi',
        'last_run_halt', 'yield_reason', 'd3d_render_token', 'dll_count', 'wait_handle', 'wait_timeout',
        'heap_ptr', 'heap_end', 'heap_sparse_ptr', 'heap_sparse_end', 'virtual_alloc_top',
        'd3d9_shader_made', 'd3d9_shader_refused', 'd3d9_shader_refused_vs', 'd3d9_shader_refused_ps',
        'd3d9_shader_error_vs', 'd3d9_shader_error_ps', 'd3d9_shader_error_at', 'd3d9_shader_error_token',
        'd3d9_shader_error_copy', 'd3d9_shader_error_copy_words',
        'd3d9_shader_refused_vs11', 'd3d9_shader_refused_vs20', 'd3d9_shader_refused_ps1x',
        'd3d9_shader_refused_ps20', 'd3d9_shader_refused_other'];
      let sample;
      try {
        sample = await Promise.race([
          guest.readExports(names.map(n => 'get_' + n)),
          new Promise(resolve => setTimeout(() => resolve({timedOut: true}), 2000))
        ]);
      } catch (error) { return {unavailable: String(error), runtime: this.runtime()}; }
      // Preserve host/shared state even when the Worker cannot answer. Asking
      // that same Worker for more exports would lose the failure-time evidence.
      if (sample.timedOut) return {...sample, runtime: this.runtime()};
      const r = reader(client);
      if (!r) return {...sample, unavailable: 'guest memory released', runtime: this.runtime()};
      sample.memoryObservationAtomic = false;
      sample.stack = stack(r, sample.get_esp, sample.get_ebp);
      sample.registerMemory = Object.fromEntries(['eax', 'ebx', 'ecx', 'edx', 'esi', 'edi']
        .map(n => [n, {address: sample['get_' + n], words: r.words(sample['get_' + n], 16)}]));
      const map = RegionMap.BASE, state = map.VIRTUAL_MAP_STATE;
      const count = r.dv.getUint32(state, true);
      let live = 0;
      for (let i = 0; i < Math.min(count, RegionMap.SIZE.VIRTUAL_MAP_TABLE / 16); i++)
        live += r.dv.getUint32(map.VIRTUAL_MAP_TABLE + i * 16 + 4, true);
      sample.memory = {wasmBytes: r.dv.byteLength, committedRecords: count,
        liveSparseBytes: live, primaryCursor: r.dv.getUint32(state + 4, true),
        primaryCapacity: RegionMap.SIZE.VIRTUAL_BACKING_BASE,
        totalSparseCapacity: RegionMap.SIZE.VIRTUAL_BACKING_BASE + Math.max(0, r.dv.byteLength - 0x20000000),
        reservationRecords: r.dv.getUint32(state + 16, true),
        // Unlike get_virtual_alloc_top, this includes other workers' progress.
        sharedReservationCursor: r.dv.getUint32(state + 8, true)};
      // Read-only, asynchronous census of the separate arena metadata limit.
      // Empty/full extents are candidates, not proof that reclamation is safe:
      // the allocator also checks ownership and sparse address bounds.
      const arenaCount = r.dv.getUint32(map.HEAP_ARENAS, true);
      const arenas = {count: arenaCount, capacity: (RegionMap.SIZE.HEAP_ARENAS - 16) / 16,
        published: 0, unpublished: 0, emptyFullExtents: 0, liveBytes: 0};
      for (let i = 0; i < Math.min(arenaCount, arenas.capacity); i++) {
        const rec = map.HEAP_ARENAS + 16 + i * 16;
        if (!r.dv.getUint32(rec, true)) { arenas.unpublished++; continue; }
        arenas.published++;
        const bytes = r.dv.getUint32(rec + 12, true);
        arenas.liveBytes += bytes;
        if (!bytes && r.dv.getUint32(rec + 4, true) === r.dv.getUint32(rec + 8, true))
          arenas.emptyFullExtents++;
      }
      sample.memory.heapArenas = arenas;
      sample.runtime = this.runtime();
      if (originalInput() && sample.get_eip >= 0x331a1f20 && sample.get_eip < 0x331a30d4)
        sample.lua = lua(r, sample.get_ebx, r.u32(sample.get_ebp + 8));
      // Original callback dispatch loop observed late in capture 074033Z.
      // Preserve its vector bounds rather than inferring them from loop counts.
      if (originalInput() && sample.get_eip >= 0x328545e0 && sample.get_eip < 0x32854621) {
        const begin = r.u32(sample.get_esi + 0x18c), end = r.u32(sample.get_esi + 0x190);
        sample.callbackVector = {object: sample.get_esi, begin, end,
          capacity: r.u32(sample.get_esi + 0x194), first: r.words(begin, 32),
          current: r.words(begin + sample.get_edi * 4, 8), objectWords: r.words(sample.get_esi + 0x170, 24)};
      }
      return sample;
    },
    files() {
      const result = [];
      for (const [path, entry] of window.theseus.client?._helpCtx?.vfs?.files || []) {
        if (entry._provider || !/\.(log|txt|err)$/i.test(path)) continue;
        const data = entry.data;
        if (data?.length <= 1048576) result.push({path, size: data.length,
          text: new TextDecoder().decode(data)});
      }
      return result;
    }
  };
})()
