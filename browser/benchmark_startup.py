"""Startup/login-idle comparison; no login/gameplay input or guest-memory reads."""
from __future__ import annotations
import argparse
import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
import hashlib
from http.server import ThreadingHTTPServer
import json
import math
from pathlib import Path
import shutil
import struct
import sys
import threading
import time

from prepare import HERE, ROOT, sha256
from serve import Handler, routes
from network import NetworkService
sys.path.insert(0, str(ROOT / 'theseus/tools/python'))
from playwright.sync_api import sync_playwright


def save(path, obj):
    path.write_text(json.dumps(obj, indent=2) + '\n', encoding='utf-8')


def retain(rows, value, limit=360):
    rows.append(value)
    if len(rows) > limit:
        del rows[:-limit]


def verify_inputs(manifest):
    return {item['source']: {'expected': item['sha256'],
            'actual': sha256(ROOT / item['source'])} for item in manifest['files']}


STATE_EXPRESSION = '''({state:theseus.state,running:!!theseus.client?.running,
    frames:theseus.frames||0,gpu:theseus.frameKinds?.gpu||0,visibility:document.visibilityState})'''

# Whitelist host scalars only. Never return guest registers, identifiers, memory,
# resource keys, command payloads, or invoke the bridge's sharedWorker getter.
HOST_SNAPSHOT = '''() => {
  const c=window.theseus?.client, renderer=c?.renderer || window.theseus?.renderer;
  const number=x=>typeof x==='number' && Number.isFinite(x)?x:null;
  const flag=x=>typeof x==='boolean'?x:null;
  const size=x=>x==null?null:number(x.size);
  const select=(o,names)=>Object.fromEntries(names.map(k=>[k,number(o?.[k])]));
  const slice=c?._workerLastSlice, stats=c?.guestWorker?.sliceStats;
  const transport=c?._renderWorkerManager, bridge=c?.hostCtx?.d3d9Bridge;
  const ends=stats?.ends, histogram={};
  if(ends) for(const k of ['s',...Array.from({length:17},(_,i)=>String(i))])
    histogram[k]=number(ends[k]) ?? 0;
  const devices=[];
  if(bridge?.devices instanceof Map) for(const entry of bridge.devices.values()) {
    if(devices.length===64)break;
    const q=entry?.queue;
    devices.push({residentBytes:number(entry?.residentBytes),residentCount:size(entry?.resident),
      deferredCount:size(entry?.deferred),dead:flag(entry?.dead),lost:flag(entry?.lost),
      releasing:flag(entry?.releasing),deferredErrorPresent:entry?!!entry.deferredError:null,
      queue:{present:!!q,...select(q,['bytes','capacityBytes','inflight','submitted','consumed','completed','maxCommands']),
        errorPresent:q?!!q.error:null}});
  }
  return {schema:'brocwin.passive-host/v1',clientPresent:!!c,guestWorkerPresent:!!c?.guestWorker,
    scope:'Main-page existing host scalars only; absent worker-owned state is unavailable, not zero',
    adaptive:{present:!!c && c._workerAdaptiveSteps!==undefined,guestWorkerPresent:!!c?.guestWorker,
      interpretation:'Configured host controller fields; zero currentSteps can precede initialization; samples do not reconstruct every adjustment',
      configuredSteps:number(c?.stepsPerSlice),ceiling:number(c?._workerAdaptiveCeiling),
      currentSteps:number(c?._workerAdaptiveSteps),inputBurstSlices:number(c?._workerInputBurstSlices),
      lastSlice:{present:!!slice,...select(slice,['blocks','ms','yield']),trapped:slice?!!slice.trapped:null}},
    sliceStats:{present:!!stats,...select(stats,['slices','guestMs','rpcSync','rpcAsync','rpcLocal']),
      ends:ends?histogram:null,
      otherEndCount:ends?Object.entries(ends).reduce((sum,[k,v])=>sum+(k in histogram?0:number(v)||0),0):null,
      guestMsMeaning:'Worker elapsed slice time including waits; not CPU time'},
    renderTransport:{present:!!transport,
      ...select(transport,['queuedBytes','maxQueuedBytes','maxQueuedCommands','maxEndpoints']),
      pendingCount:size(transport?.pending),endpointCount:size(transport?.ports),closingCount:size(transport?.closing),
      stopped:flag(transport?.stopped),retired:flag(transport?._retired),
      bytesMeaning:'Charged transport payload budget; not total process memory'},
    d3d9:{present:!!bridge,backend:typeof bridge?.backend==='string'?bridge.backend:null,
      asyncSoftware:flag(bridge?.asyncSoftware),closed:flag(bridge?.closed),errorPresent:bridge?!!bridge.lastError:null,
      deviceCount:size(bridge?.devices),requestCount:size(bridge?.requests),presentWaitCount:size(bridge?.presentWaits),
      textureSnapshotCount:size(bridge?._textureSnapshots),textureSnapshotBytes:number(bridge?._textureSnapshotBytes),
      ...select(bridge,['maxRequests','maxTextureSnapshotBytes','maxResidentTextureBytes','maxDeferred']),
      textureSnapshotLimitMeaning:'Hard retained RGBA snapshot byte cap',
      residentLimitMeaning:'Eviction target per device, NOT a hard cap; active draw textures can exceed it',
      devices,inspectedDevices:devices.length,
      devicesTruncated:bridge?.devices instanceof Map?bridge.devices.size>devices.length:null,
      deviceMeaning:'Deidentified host entries only; no resource keys, IDs or payloads; queue bytes are charged payload bytes'},
    presentation:{rendererPresent:!!renderer,inputQueueLength:number(renderer?.inputQueue?.length),
      windowCount:renderer?.windows?Object.keys(renderer.windows).length:null,
      guestSliceDepth:number(renderer?._workerGuestSliceDepth),lastCompositeAt:number(renderer?._workerLastCompositeAt)}};
}'''


def canvas_clip(box, viewport):
    """Visible CSS-pixel bounds, rounded outward; never scroll or resize the page."""
    if not box or not viewport:
        raise ValueError('Canvas is hidden/missing or viewport dimensions are unavailable')
    values = [box.get(k) for k in ('x', 'y', 'width', 'height')] + [viewport.get(k) for k in ('width', 'height')]
    if any(not isinstance(v, (int, float)) or not math.isfinite(v) for v in values):
        raise ValueError('Invalid canvas/viewport dimensions')
    if box['width'] <= 0 or box['height'] <= 0:
        raise ValueError('Canvas has no visible area')
    left, top = max(0, math.floor(box['x'])), max(0, math.floor(box['y']))
    right = min(viewport['width'], math.ceil(box['x'] + box['width']))
    bottom = min(viewport['height'], math.ceil(box['y'] + box['height']))
    if right <= left or bottom <= top:
        raise ValueError('Canvas is outside the viewport')
    return {'x': left, 'y': top, 'width': right - left, 'height': bottom - top}


def capture_canvas(page, path, timeout_ms=5000):
    """Bound bbox resolution and page capture by one deadline; no stability wait."""
    began = time.monotonic()
    row = {'file': Path(path).name, 'ok': False, 'budgetMilliseconds': timeout_ms,
        'method': 'Locator.bounding_box then Page.screenshot clip; no element stability wait',
        'scale': 'css', 'geometryCaveat': 'Visible viewport intersection at bounding-box observation; layout may move before capture'}
    try:
        if timeout_ms <= 0:
            raise ValueError('Capture timeout must be positive')
        row['canvasBounds'] = page.locator('#game').bounding_box(timeout=timeout_ms)
        row['viewport'] = page.viewport_size
        row['clip'] = canvas_clip(row['canvasBounds'], row['viewport'])
        remaining = timeout_ms - (time.monotonic() - began) * 1000
        if remaining <= 0:
            raise TimeoutError('Canvas capture deadline reached while resolving bounds')
        png = page.screenshot(path=str(path), type='png', clip=row['clip'], timeout=remaining,
            full_page=False, animations='allow', caret='initial', scale='css')
        if png[:8] != b'\x89PNG\r\n\x1a\n':
            raise RuntimeError('Canvas capture did not return PNG bytes')
        width, height = struct.unpack('>II', png[16:24])
        if width != row['clip']['width'] or height != row['clip']['height']:
            raise RuntimeError('Canvas capture PNG dimensions differ from the recorded CSS clip')
        row.update(ok=True, pngWidth=width, pngHeight=height, sha256=hashlib.sha256(png).hexdigest())
    except Exception as error:
        row['error'] = str(error)
    row['elapsedSeconds'] = time.monotonic() - began
    return row


def record_canvas_capture(page, directory, name, result, required=True, timeout_ms=5000):
    row = capture_canvas(page, directory / name, timeout_ms)
    retain(result['captures'], row, 68)
    if required and not row['ok']:
        raise RuntimeError('Canvas capture failed: ' + row.get('error', 'unknown error'))
    return row


class SteadyObservation:
    """A login-workload evidence gate, never a guest scheduling adjustment."""
    def __init__(self, started, frames, stall_seconds=60):
        self.started = self.last_progress = self.last_observation = started
        self.initial_frames = self.frames = frames
        self.stall_seconds = stall_seconds
        self.max_no_progress = self.max_observation_gap = 0
        self.failure = None
        self.completed = False

    def reject(self, message):
        self.failure = message
        raise RuntimeError(message)

    def observe(self, at, state):
        self.max_observation_gap = max(self.max_observation_gap, at - self.last_observation)
        self.last_observation = at
        if state['state'] != 'executing' or not state['running']:
            self.reject('Login observation stopped: state must be executing and client.running must be true')
        if state['frames'] < self.frames:
            self.reject('Login observation frame counter regressed')
        if state['frames'] > self.frames:
            self.frames = state['frames']
            self.last_progress = at
        else:
            gap = at - self.last_progress
            self.max_no_progress = max(self.max_no_progress, gap)
            if gap >= self.stall_seconds:
                self.reject(f'Login workload stalled: no observed frame progress for {gap:.3f}s (limit {self.stall_seconds}s)')

    def complete(self, at, requested_seconds):
        if self.failure:
            self.reject(self.failure)
        if at - self.started < requested_seconds:
            self.reject('Login observation ended before the requested duration')
        if requested_seconds > 0 and self.frames == self.initial_frames:
            self.reject('Login observation ended without any observed frame progress')
        self.completed = True

    def snapshot(self, at):
        return {'completed': self.completed, 'elapsedSeconds': at - self.started,
            'stallCriterionSeconds': self.stall_seconds, 'initialFrames': self.initial_frames,
            'finalFrames': self.frames, 'frameAdvances': self.frames - self.initial_frames,
            'maximumObservedNoProgressSeconds': self.max_no_progress,
            'maximumObservationGapSeconds': self.max_observation_gap, 'failure': self.failure,
            'scope': 'Observed login frame progression and host lifecycle only; no gameplay or runtime scheduling changes'}


class ProcessMemorySampler:
    """Read process counters for browser-owned CDP PIDs; no process-memory reads."""
    scope = {'provider': 'Windows GetProcessMemoryInfo(PROCESS_MEMORY_COUNTERS_EX)',
        'processSelection': 'Every process returned by this browser SystemInfo.getProcessInfo',
        'coverage': 'Browser, renderer/worker, GPU and utility process allocations; no per-worker attribution or dedicated GPU VRAM measurement',
        'workingSetCaveat': 'Working sets include shared resident pages; summing processes can double-count shared backing',
        'privateBytesMeaning': 'Private committed memory, not resident memory; inaccessible/exited processes report errors, never invented zeroes'}

    def __init__(self):
        self.error = None
        if sys.platform != 'win32':
            self.error = 'Windows process memory counters are unavailable on this platform'
            return
        try:
            class Counters(ctypes.Structure):
                _fields_ = [('cb', wintypes.DWORD), ('PageFaultCount', wintypes.DWORD)] + [
                    (name, ctypes.c_size_t) for name in ('PeakWorkingSetSize', 'WorkingSetSize',
                    'QuotaPeakPagedPoolUsage', 'QuotaPagedPoolUsage', 'QuotaPeakNonPagedPoolUsage',
                    'QuotaNonPagedPoolUsage', 'PagefileUsage', 'PeakPagefileUsage', 'PrivateUsage')]
            self.Counters = Counters
            self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
            self.psapi = ctypes.WinDLL('psapi', use_last_error=True)
            self.kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
            self.kernel.OpenProcess.restype = wintypes.HANDLE
            self.kernel.CloseHandle.argtypes = [wintypes.HANDLE]
            self.kernel.CloseHandle.restype = wintypes.BOOL
            self.psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
            self.psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
        except (AttributeError, OSError) as error:
            self.error = str(error)

    def sample(self, processes):
        rows = []
        for process in processes:
            row = {'pid': process['id'], 'type': process['type'], 'available': False}
            rows.append(row)
            if self.error:
                row['error'] = self.error
                continue
            # PROCESS_QUERY_LIMITED_INFORMATION is sufficient on supported Windows.
            handle = self.kernel.OpenProcess(0x1000, False, int(process['id']))
            if not handle:
                row['error'] = 'OpenProcess failed'
                row['winError'] = ctypes.get_last_error()
                continue
            try:
                counters = self.Counters()
                counters.cb = ctypes.sizeof(counters)
                if not self.psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb):
                    row['error'] = 'GetProcessMemoryInfo failed'
                    row['winError'] = ctypes.get_last_error()
                else:
                    row.update(available=True, workingSetBytes=counters.WorkingSetSize,
                        peakWorkingSetBytes=counters.PeakWorkingSetSize, privateBytes=counters.PrivateUsage)
            finally:
                self.kernel.CloseHandle(handle)
        return rows


class BoundedProfiler:
    """Sampling only, through Playwright's existing CDP transport.

    Nonflattened child sessions use the public Target message bridge; this
    avoids private Playwright objects and a second browser debugging listener.
    Worker names identify CDP targets, never guest thread slots or addresses.
    """
    def __init__(self, cdp, page, directory, origin, started, seconds):
        self.cdp, self.page, self.directory = cdp, page, directory
        self.origin, self.started, self.seconds = origin, started, seconds
        self.sequence, self.pending, self.sessions = 0, {}, []
        self.closed, self.began = False, None
        self.metadata = {'scope': 'Bounded host/worker CPU sampling; no guest memory, input, or breakpoints',
            'intervalMicroseconds': 1000, 'requestedSeconds': seconds,
            'measurementCondition': 'Profiler overhead applies; not comparable to unprofiled timings',
            'targets': [], 'errors': []}
        self.cdp.on('Target.receivedMessageFromTarget', self.receive)

    def receive(self, event):
        message = json.loads(event['message'])
        key = (event['sessionId'], message.get('id'))
        if key in self.pending:
            self.pending[key] = message

    def send(self, session, method, params=None):
        self.sequence += 1
        key = (session, self.sequence)
        self.pending[key] = None
        try:
            self.cdp.send('Target.sendMessageToTarget', {'sessionId': session,
                'message': json.dumps({'id': self.sequence, 'method': method, 'params': params or {}})})
            deadline = time.monotonic() + 12
            while self.pending[key] is None:
                if time.monotonic() >= deadline:
                    raise TimeoutError('CPU profiler CDP timeout: ' + method)
                self.page.wait_for_timeout(10)
            response = self.pending[key]
            if 'error' in response:
                raise RuntimeError(method + ': ' + json.dumps(response['error']))
            return response.get('result', {})
        finally:
            self.pending.pop(key, None)

    def start(self):
        self.began = time.monotonic()
        self.metadata['startFromClickSeconds'] = self.began - self.started
        self.directory.mkdir()
        targets = self.cdp.send('Target.getTargets')['targetInfos']
        targets = sorted((target for target in targets if target['type'] in ('page', 'worker')
            and target['url'].startswith(self.origin + '/')), key=lambda target: target['targetId'])
        # Capture the targets that exist at the selected boundary. Do not pause
        # or auto-attach newly spawned workers, which would alter initialization.
        self.metadata['targetSelection'] = 'Existing page and worker targets at interval start; no auto-attach'
        for target in targets:
            row = {'target': target, 'name': target['type'] + '-' + target['targetId']}
            self.metadata['targets'].append(row)
            try:
                session = self.cdp.send('Target.attachToTarget',
                    {'targetId': target['targetId'], 'flatten': False})['sessionId']
                self.sessions.append((session, row))
                self.send(session, 'Profiler.enable')
                self.send(session, 'Profiler.setSamplingInterval', {'interval': 1000})
                self.send(session, 'Profiler.start')
                row['startFromClickSeconds'] = time.monotonic() - self.started
            except Exception as error:
                row['error'] = str(error)
                self.metadata['errors'].append(str(error))
        if not targets:
            self.metadata['errors'].append('No matching targets existed at the selected interval')
        save(self.directory / 'metadata.json', self.metadata)

    def stop(self):
        if self.closed:
            return self.metadata
        self.closed = True
        try:
            for session, row in self.sessions:
                try:
                    if 'startFromClickSeconds' in row:
                        profile = self.send(session, 'Profiler.stop')['profile']
                        row['stopFromClickSeconds'] = time.monotonic() - self.started
                        row['profile'] = row['name'] + '.cpuprofile'
                        row['profileWallSeconds'] = (profile['endTime'] - profile['startTime']) / 1e6
                        save(self.directory / row['profile'], profile)
                    self.send(session, 'Profiler.disable')
                except Exception as error:
                    row['error'] = str(error)
                    self.metadata['errors'].append(str(error))
                finally:
                    try:
                        self.cdp.send('Target.detachFromTarget', {'sessionId': session})
                    except Exception as error:
                        self.metadata['errors'].append(str(error))
        finally:
            self.cdp.remove_listener('Target.receivedMessageFromTarget', self.receive)
            self.metadata['stopFromClickSeconds'] = time.monotonic() - self.started
            save(self.directory / 'metadata.json', self.metadata)
        return self.metadata


def run(args):
    out = ROOT / 'theseus/reports/performance' / args.label
    out.mkdir(parents=True, exist_ok=False)
    # Runtime scripts/modules are immutable for each benchmark. Original payload
    # paths are shared read-only, and no files in the existing host are replaced.
    source_routes = routes()
    if args.snapshot:
        retained=Path(args.snapshot)
        for url in list(source_routes):
            candidate=retained / ('index.html' if url=='/' else url.lstrip('/'))
            if candidate.is_file():source_routes[url]=candidate
        # Baseline has no cache helper and should retain its exact route set.
        source_routes={url:path for url,path in source_routes.items()
            if url.startswith('/payload/') or path.is_relative_to(retained)}
    frozen = {}
    hashes = {}
    for url, path in source_routes.items():
        if url.startswith('/payload/'):
            frozen[url] = path
            continue
        destination = out / 'host' / ('index.html' if url == '/' else url.lstrip('/'))
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, destination)
        frozen[url] = destination
        hashes[url] = hashlib.sha256(destination.read_bytes()).hexdigest()
    manifest = json.loads(frozen['/manifest.json'].read_text())
    observer = out / 'observer'
    observer.mkdir()
    observer_hashes = {}
    for source in (Path(__file__), HERE / 'startup_telemetry.js', HERE / 'serve.py',
                   HERE / 'network.py', HERE / 'prepare.py'):
        shutil.copyfile(source, observer / source.name)
        observer_hashes[source.name] = sha256(observer / source.name)
    input_check = verify_inputs(manifest)
    identity = {'runtime': manifest['runtime'], 'served': hashes, 'observer': observer_hashes,
        'originalInputs': {f['source']: f['sha256'] for f in manifest['files']},
        'inputVerificationBefore': input_check,
        'clientModified': any(row['actual'] != row['expected'] for row in input_check.values())}
    if args.profile_start is not None:
        build = ROOT / 'theseus/tools/wine-assembly/build'
        if sha256(build / 'wine-assembly.wasm') == manifest['runtime']['wasm']['sha256']:
            shutil.copyfile(build / 'combined.wat', observer / 'combined.wat')
            identity['profileFunctionSource'] = {'path': 'observer/combined.wat',
                'sha256': sha256(observer / 'combined.wat'),
                'matchingLocalWasmSha256': manifest['runtime']['wasm']['sha256']}
        else:
            identity['profileFunctionSource'] = None
    save(out / 'identity.json', identity)
    if identity['clientModified']:
        raise RuntimeError('An input differs from the retained manifest; benchmark was not launched')
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    server.paths = frozen
    server.network = NetworkService(args.port).start()
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print(json.dumps({'benchmark': str(out), 'url': f'http://127.0.0.1:{args.port}'}), flush=True)
    failed = False
    try:
        with sync_playwright() as p:
            for ordinal in range(args.runs):
                run_dir = out / f'run-{ordinal + 1:02d}'
                run_dir.mkdir()
                result = {'schema': 'brocwin.startup-benchmark/v1', 'utc': datetime.now(timezone.utc).isoformat(),
                    'ordinal': ordinal + 1, 'cacheCondition': 'cold-profile' if ordinal == 0 else 'warm-profile',
                    'headed': args.headed, 'environment': 'Isolated browser profile; existing native services preserved; no gameplay input',
                    'cpu': [], 'heap': [], 'processMemory': [], 'hostSnapshots': [],
                    'errors': [], 'snapshots': [], 'captures': [], 'lastKnownState': None,
                    'steadyCompleted': False, 'passed': False,
                    'startupTimeoutSeconds': args.timeout, 'requestedSteadySeconds': args.steady_seconds,
                    'steadyStallCriterionSeconds': 60,
                    'processMemoryScope': ProcessMemorySampler.scope,
                    'sampling': {'intervalSeconds': 10, 'retainedRowsPerSeries': 360,
                        'completeSeries': 'samples.jsonl'},
                    'cpuProfiling': {'enabled': args.profile_start is not None,
                        'requestedStartFromClickSeconds': args.profile_start,
                        'requestedSeconds': args.profile_seconds,
                        'timingComparableToUnprofiled': args.profile_start is None}}
                started = time.monotonic()
                context = p.chromium.launch_persistent_context(str(out / 'profile'), channel='msedge',
                    headless=not args.headed, viewport={'width': 1280, 'height': 1100})
                result['browserLaunchSeconds'] = time.monotonic() - started
                browser = context.browser
                result['browserVersion'] = browser.version
                page = context.pages[0]
                page.add_init_script(path=str(observer / 'startup_telemetry.js'))
                page.on('pageerror', lambda error: retain(result['errors'], str(error), 128))
                result['dependencies']=[]
                result['compiler']=[]
                def dependency(message):
                    text=message.text
                    if '[LoadLibrary]' in text and len(result['dependencies'])<128:
                        result['dependencies'].append({'atSeconds':time.monotonic()-started,
                            'name':text.split('[LoadLibrary]',1)[1].strip().split(' ',1)[0]})
                    if text.startswith('[brocwin-compiler] ') and len(result['compiler'])<64:
                        result['compiler'].append({'atSeconds':time.monotonic()-started,
                            **json.loads(text.split(' ',1)[1])})
                page.on('console',dependency)
                cdp = context.new_cdp_session(page)
                browser_cdp = browser.new_browser_cdp_session()
                cdp.send('Performance.enable')
                profiler = None
                steady = None
                memory_sampler = ProcessMemorySampler()
                try:
                    page.goto(f'http://127.0.0.1:{args.port}/', wait_until='domcontentloaded')
                    page.wait_for_function('window.theseus && ["ready","stopped-incomplete"].includes(theseus.state)', timeout=120000)
                    result['readySeconds'] = time.monotonic() - started
                    if page.evaluate('theseus.state') != 'ready': raise RuntimeError('Runtime failed to initialize')
                    # Count API names at the existing broker boundary, not guest PCs.
                    page.evaluate('''() => { const original = GuestRpc.createMainBroker;
                      GuestRpc.createMainBroker = function(m,h,s,o) {
                        return original(m,h,s,Object.assign({},o,{countCalls:true})); }; }''')
                    page.evaluate('''() => {
                      const data=brocwinTelemetry;data.presents=[];data.composites=[];
                      data.totals.presents=0;data.totals.composites=0;
                      const init=WineAssembly.prototype.init;
                      WineAssembly.prototype.init=function(...args){
                        const present=this.onGuestFrame;
                        this.onGuestFrame=function(frame){
                          data.lastPresent=performance.now();
                          data.totals.presents++;
                          data.presents.push({at:data.lastPresent,kind:frame?.kind});
                          if(data.presents.length>2048)data.presents.shift();
                          return present?.apply(this,arguments);
                        };return init.apply(this,args);
                      };
                      const repaint=Win98Renderer.prototype.repaint;
                      Win98Renderer.prototype.repaint=function(...args){
                        const before=this._workerLastCompositeAt,start=performance.now();
                        const result=repaint.apply(this,args);
                        if(before!==this._workerLastCompositeAt){
                          data.totals.composites++;
                          data.composites.push({at:start,duration:performance.now()-start,
                            fromLatestPresent:data.lastPresent===undefined?null:start-data.lastPresent});
                          if(data.composites.length>2048)data.composites.shift();
                        }return result;
                      };
                    }''')
                    page.locator('#start').click()
                    launch_at = time.monotonic()
                    result['startClickedSeconds'] = launch_at - started
                    first_gpu = None
                    first_visible = None
                    after_gpu_image = False
                    next_sample = 0
                    next_image = 60
                    while ((first_visible is None and time.monotonic() - launch_at < args.timeout)
                           or (first_visible is not None and time.monotonic() - first_visible < args.steady_seconds)):
                        page.wait_for_timeout(500)
                        elapsed = time.monotonic() - launch_at
                        if args.profile_start is not None and elapsed >= args.profile_start and profiler is None:
                            profiler = BoundedProfiler(browser_cdp, page, run_dir / 'cpu-profile',
                                f'http://127.0.0.1:{args.port}', launch_at, args.profile_seconds)
                            profiler.start()
                        if profiler and not profiler.closed and time.monotonic() - profiler.began >= args.profile_seconds:
                            result['cpuProfiling']['capture'] = profiler.stop()
                        state = page.evaluate(STATE_EXPRESSION)
                        result['lastKnownState'] = {'elapsed': time.monotonic() - launch_at, **state}
                        if state['gpu'] and first_gpu is None:
                            first_gpu = time.monotonic()
                            result['firstGPUSeconds'] = first_gpu - started
                            result['firstGPUFromClickSeconds'] = first_gpu - launch_at
                        if state['gpu'] and first_visible is None:
                            visible=page.locator('#game').evaluate('''canvas=>{
                              const ctx=canvas.getContext('2d'),w=canvas.width,h=canvas.height;
                              const p=ctx.getImageData(0,0,w,h).data;let colored=0,total=0;
                              for(let y=40;y<h-10;y+=16)for(let x=8;x<w-8;x+=16){
                                const i=(y*w+x)*4,r=p[i],g=p[i+1],b=p[i+2];total++;
                                if(Math.max(r,g,b)-Math.min(r,g,b)>24 && Math.max(r,g,b)>40)colored++;
                              }return {coloredFraction:colored/total};}''')
                            if visible['coloredFraction']>.08:
                                first_visible=time.monotonic()
                                steady=SteadyObservation(first_visible,state['frames'])
                                result['firstVisibleSceneSeconds']=first_visible-started
                                result['visibleDetection']=visible
                                record_canvas_capture(page, run_dir, 'first-visible-scene.png', result)
                        if state['state'] in ('stopped', 'stopped-incomplete'):
                            raise RuntimeError('Client execution stopped: ' + state['state'])
                        if steady:
                            steady.observe(time.monotonic(), state)
                        if elapsed >= next_sample:
                            cpu = {'elapsed': elapsed, 'processes': browser_cdp.send('SystemInfo.getProcessInfo')['processInfo']}
                            heap = {'elapsed': elapsed, **cdp.send('Runtime.getHeapUsage'),
                                'metrics': cdp.send('Performance.getMetrics')['metrics']}
                            retain(result['cpu'], cpu)
                            retain(result['heap'], heap)
                            process_memory = {'elapsed': elapsed, 'processes': memory_sampler.sample(cpu['processes'])}
                            retain(result['processMemory'], process_memory)
                            host = {'elapsed': time.monotonic() - launch_at, **page.evaluate(HOST_SNAPSHOT)}
                            retain(result['hostSnapshots'], host)
                            state['host'] = host
                            with (run_dir / 'samples.jsonl').open('a', encoding='utf-8') as stream:
                                stream.write(json.dumps({'cpu': cpu, 'heap': heap, 'state': state,
                                    'processMemory': process_memory}) + '\n')
                            save(run_dir / 'progress.json', {k: result.get(k) for k in
                                ['readySeconds', 'firstGPUSeconds', 'firstVisibleSceneSeconds', 'cpu', 'heap',
                                 'processMemory', 'hostSnapshots', 'lastKnownState', 'captures', 'errors']})
                            print(json.dumps({'run': ordinal + 1, 'elapsed': round(elapsed),
                                **{k: v for k, v in state.items() if k != 'host'}}), flush=True)
                            next_sample = elapsed + 10
                        if len(result['snapshots']) < 64 and (elapsed >= next_image or
                                (first_gpu and not after_gpu_image and time.monotonic() - first_gpu > 15)):
                            name = f'canvas-{int(elapsed):04d}.png'
                            record_canvas_capture(page, run_dir, name, result)
                            result['snapshots'].append(name)
                            if first_gpu: after_gpu_image = True
                            next_image = elapsed + 120
                    result['steadySeconds'] = time.monotonic() - first_visible if first_visible else 0
                    result['timedOutBeforeGPU'] = first_gpu is None
                    result['timedOutBeforeVisibleScene'] = first_visible is None
                    if first_visible is None:
                        retain(result['errors'], 'Startup deadline reached before a visible scene', 128)
                    if steady:
                        state = page.evaluate(STATE_EXPRESSION)
                        result['lastKnownState'] = {'elapsed': time.monotonic() - launch_at, **state}
                        steady.observe(time.monotonic(), state)
                        steady.complete(time.monotonic(), args.steady_seconds)
                    result['telemetry'] = page.evaluate('brocwinTelemetry.finish()')
                    result['records'] = page.evaluate('theseus.records.filter(r=>!["input","entry-state","entry-bytes"].includes(r.kind))')
                    result['frames'] = page.evaluate('({total:theseus.frames,kinds:theseus.frameKinds})')
                    result['caches'] = page.evaluate('({runtime:theseus.runtimeCache?.stats||null,artifacts:theseus.artifacts?.stats||null})')
                    record_canvas_capture(page, run_dir, 'final-canvas.png', result)
                except Exception as error:
                    retain(result['errors'], str(error), 128)
                    # Retain the last successful host observation even when the
                    # page cannot evaluate. Recovery capture has its own bound.
                    result['failureCapture'] = record_canvas_capture(page, run_dir,
                        'failure-canvas.png', result, required=False, timeout_ms=3000)
                finally:
                    if profiler and not profiler.closed:
                        result['cpuProfiling']['capture'] = profiler.stop()
                    if args.profile_start is not None and profiler is None:
                        result['cpuProfiling']['notCaptured'] = 'Run ended before the requested profile interval'
                    if steady:
                        result['steadyObservation'] = steady.snapshot(time.monotonic())
                        result['steadyCompleted'] = steady.completed
                    result['elapsedSeconds'] = time.monotonic() - started
                    result['passed'] = bool(result['steadyCompleted'] and not result['errors']
                        and not result.get('timedOutBeforeVisibleScene')
                        and not result['cpuProfiling'].get('notCaptured')
                        and not result['cpuProfiling'].get('capture', {}).get('errors'))
                    save(run_dir / 'result.json', result)
                    context.close()
                failed = failed or not result['passed']
                print(json.dumps({'completed': str(run_dir), 'firstGPUSeconds': result.get('firstGPUSeconds'), 'errors': result['errors']}), flush=True)
    finally:
        server.shutdown()
        server.server_close()
        server.network.close()
        identity['inputVerificationAfter'] = verify_inputs(manifest)
        identity['clientModified'] = identity['clientModified'] or any(
            row['actual'] != row['expected'] for row in identity['inputVerificationAfter'].values())
        save(out / 'identity.json', identity)
        if identity['clientModified']:
            raise RuntimeError('An input changed during the benchmark; retained results are invalid')
    if failed:
        raise RuntimeError('One or more benchmark runs failed; inspect the retained result.json files')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    parser.add_argument('--port', type=int, default=8767)
    parser.add_argument('--runs', type=int, default=2)
    parser.add_argument('--timeout', type=int, default=900, help='Startup deadline before a visible scene, seconds')
    parser.add_argument('--steady-seconds', type=float, default=30,
        help='Separate login-idle observation duration after the first visible scene')
    parser.add_argument('--profile-start', type=float,
        help='Opt-in bounded CPU profile start, seconds after Start client; diagnostic timing only')
    parser.add_argument('--profile-seconds', type=float, default=20, help='Bounded CPU profile duration, 1..30 seconds')
    parser.add_argument('--headed', action='store_true')
    parser.add_argument('--snapshot', help='Retained baseline host directory; never edit its files')
    args = parser.parse_args()
    if args.timeout <= 0 or not math.isfinite(args.steady_seconds) or args.steady_seconds < 0 or args.runs < 1:
        parser.error('timeout/runs must be positive and steady-seconds must be nonnegative')
    if not 1 <= args.profile_seconds <= 30 or (args.profile_start is not None and
            (not math.isfinite(args.profile_start) or args.profile_start < 0)):
        parser.error('profile-seconds must be 1..30 and profile-start must be nonnegative')
    run(args)
