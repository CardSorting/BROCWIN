"""Observation gates and native process-counter lifetime; never launches a game."""
import ctypes
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import sys
import time
import unittest
from unittest.mock import Mock, patch

import benchmark_startup as benchmark
from benchmark_startup import ProcessMemorySampler, SteadyObservation, canvas_clip, capture_canvas


def state(frames, running=True, phase='executing'):
    return {'frames': frames, 'running': running, 'state': phase}


class ObservationTests(unittest.TestCase):
    def test_capture_geometry_clips_without_scrolling(self):
        self.assertEqual(canvas_clip({'x': -10.5, 'y': 20.25, 'width': 100, 'height': 200},
            {'width': 80, 'height': 180}), {'x': 0, 'y': 20, 'width': 80, 'height': 160})
        for box in (None, {'x': 800, 'y': 0, 'width': 20, 'height': 20},
                    {'x': 0, 'y': 0, 'width': float('nan'), 'height': 20}):
            with self.subTest(box=box), self.assertRaises(ValueError):
                canvas_clip(box, {'width': 800, 'height': 600})

    def test_capture_uses_remaining_deadline_and_retains_failure(self):
        page = Mock(viewport_size={'width': 800, 'height': 600})
        page.locator.return_value.bounding_box.return_value = {'x': 10, 'y': 20, 'width': 200, 'height': 100}
        page.screenshot.return_value = b'\x89PNG\r\n\x1a\n' + b'\0' * 8 + struct.pack('>II', 200, 100)
        with patch.object(benchmark.time, 'monotonic', side_effect=[0, 2, 3]):
            result = capture_canvas(page, Path('synthetic.png'), timeout_ms=5000)
        self.assertTrue(result['ok'], result)
        self.assertEqual(page.screenshot.call_args.kwargs['timeout'], 3000)
        self.assertEqual(page.screenshot.call_args.kwargs['scale'], 'css')
        page.screenshot.reset_mock()
        with patch.object(benchmark.time, 'monotonic', side_effect=[0, 6, 6]):
            result = capture_canvas(page, Path('synthetic.png'), timeout_ms=5000)
        self.assertFalse(result['ok'])
        self.assertIn('deadline', result['error'])
        page.screenshot.assert_not_called()
        retained = {'captures': [], 'lastKnownState': {'state': 'executing', 'frames': 2}, 'errors': ['original failure']}
        page.locator.return_value.bounding_box.side_effect = RuntimeError('synthetic unavailable canvas')
        result = benchmark.record_canvas_capture(page, Path('.'), 'failure.png', retained, required=False)
        self.assertFalse(result['ok'])
        self.assertEqual(retained['lastKnownState']['frames'], 2)
        self.assertEqual(retained['errors'], ['original failure'])
        self.assertEqual(retained['captures'], [result])

    def test_stopped_and_nonrunning_cannot_pass(self):
        for sample in (state(12, phase='stopped'), state(12, phase='stopped-incomplete'), state(12, running=False)):
            with self.subTest(sample=sample):
                watch = SteadyObservation(0, 10)
                with self.assertRaises(RuntimeError):
                    watch.observe(5, sample)
                with self.assertRaises(RuntimeError):
                    watch.complete(30, 30)
                self.assertFalse(watch.snapshot(30)['completed'])

    def test_stall_boundary_and_frame_regression(self):
        watch = SteadyObservation(0, 10)
        watch.observe(59.9, state(10))
        with self.assertRaisesRegex(RuntimeError, 'no observed frame progress'):
            watch.observe(60, state(10))
        self.assertFalse(watch.completed)
        with self.assertRaisesRegex(RuntimeError, 'counter regressed'):
            SteadyObservation(0, 10).observe(1, state(9))

    def test_duration_and_short_no_progress_cannot_pass(self):
        watch = SteadyObservation(0, 10)
        watch.observe(2, state(11))
        with self.assertRaisesRegex(RuntimeError, 'before the requested duration'):
            watch.complete(29, 30)
        watch = SteadyObservation(0, 10)
        watch.observe(30, state(10))
        with self.assertRaisesRegex(RuntimeError, 'without any observed frame progress'):
            watch.complete(30, 30)

    def test_progress_and_complete_flags(self):
        watch = SteadyObservation(100, 10)
        watch.observe(130, state(12))
        watch.observe(180, state(12))
        watch.observe(190, state(15))
        watch.complete(190, 90)
        result = watch.snapshot(190)
        self.assertTrue(result['completed'])
        self.assertEqual(result['frameAdvances'], 5)
        self.assertEqual(result['maximumObservedNoProgressSeconds'], 50)
        self.assertEqual(result['elapsedSeconds'], 90)

    def test_unavailable_is_not_zero(self):
        sampler = ProcessMemorySampler()
        sampler.error = 'Expected unavailable fixture'
        result = sampler.sample([{'id': 123, 'type': 'renderer'}])[0]
        self.assertFalse(result['available'])
        self.assertNotIn('workingSetBytes', result)
        self.assertNotIn('privateBytes', result)
        self.assertIn('error', result)

    @unittest.skipUnless(sys.platform == 'win32', 'Windows native counters')
    def test_native_counters_and_closed_handles(self):
        sampler = ProcessMemorySampler()
        self.assertIsNone(sampler.error)
        kernel = sampler.kernel
        kernel.GetProcessHandleCount.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
        kernel.GetProcessHandleCount.restype = ctypes.c_int
        before, after = ctypes.c_ulong(), ctypes.c_ulong()
        self.assertTrue(kernel.GetProcessHandleCount(ctypes.c_void_p(-1), ctypes.byref(before)))
        for _ in range(128):
            result = sampler.sample([{'id': os.getpid(), 'type': 'test-process'}])[0]
            self.assertTrue(result['available'], result)
            self.assertGreater(result['privateBytes'], 0)
            self.assertGreater(result['workingSetBytes'], 0)
        self.assertTrue(kernel.GetProcessHandleCount(ctypes.c_void_p(-1), ctypes.byref(after)))
        self.assertEqual(before.value, after.value, 'Sampler leaked process handles')
        failed = sampler.sample([{'id': 0xFFFFFFFF, 'type': 'missing'}])[0]
        self.assertFalse(failed['available'])
        self.assertNotIn('privateBytes', failed)
        self.assertIn('winError', failed)


def headed_smoke():
    """Visible synthetic evidence only; no game, native backend, or guest state."""
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    directory = benchmark.ROOT / 'theseus/reports/performance' / ('observation-repair-' + stamp)
    directory.mkdir()
    observer = directory / 'observer'
    observer.mkdir()
    identities = {}
    for source in (Path(benchmark.__file__), Path(__file__)):
        shutil.copyfile(source, observer / source.name)
        identities[source.name] = hashlib.sha256(source.read_bytes()).hexdigest()
    summary = {'passed': False, 'headed': True, 'scope': 'Synthetic observer fixtures only; no original client or native backend',
        'observer': identities, 'captures': [], 'hostSnapshotChecks': []}
    html = '''<!doctype html><title>BROCWIN capture repair fixture</title>
      <style>body{margin:0}canvas{position:absolute;left:80px;top:100px;width:240px;height:160px}
      @keyframes drift{from{transform:translateX(0)}to{transform:translateX(100px)}}
      .moving{animation:drift 1s linear infinite}</style>
      <p>Synthetic canvas only. No game or native backend.</p><canvas id="game" width="240" height="160"></canvas>
      <script>const g=document.querySelector('#game');const c=g.getContext('2d');
      c.fillStyle='#20a0e0';c.fillRect(0,0,240,160);window.rafCallbacks=0;</script>'''
    (directory / 'fixture.html').write_text(html, encoding='utf-8')
    try:
        with benchmark.sync_playwright() as playwright:
            context = playwright.chromium.launch_persistent_context(str(directory / 'profile'), channel='msedge',
                headless=False, viewport={'width': 800, 'height': 600}, device_scale_factor=1.5)
            try:
                summary['browserVersion'] = context.browser.version
                page = context.pages[0]
                page.goto((directory / 'fixture.html').as_uri())
                cdp = context.new_cdp_session(page)
                for mode in ('moving-layout', 'paused-animation-frames'):
                    if mode == 'moving-layout':
                        page.evaluate("document.querySelector('#game').className='moving'")
                    else:
                        page.evaluate("document.querySelector('#game').className=''; requestAnimationFrame(()=>rafCallbacks++)")
                        cdp.send('Emulation.setVirtualTimePolicy', {'policy': 'pause'})
                        baseline = page.evaluate('rafCallbacks')
                        page.evaluate('requestAnimationFrame(()=>rafCallbacks++)')
                    began = time.monotonic()
                    old_error = None
                    try:
                        # Preserved old operation; shorten only its timeout for the fixture.
                        page.locator('#game').screenshot(path=str(directory / (mode + '-old.png')), timeout=800)
                    except Exception as error:
                        old_error = str(error)
                    old_elapsed = time.monotonic() - began
                    assert old_error and 'Timeout' in old_error, (mode, old_error)
                    assert old_elapsed < 3, (mode, old_elapsed)
                    capture = capture_canvas(page, directory / (mode + '-new.png'), timeout_ms=2500)
                    assert capture['ok'], (mode, capture)
                    assert capture['elapsedSeconds'] < 4, capture
                    assert capture['canvasBounds']['width'] == 240 and capture['canvasBounds']['height'] == 160, capture
                    assert capture['pngWidth'] == capture['clip']['width'] and capture['pngHeight'] == capture['clip']['height'], capture
                    assert 240 <= capture['pngWidth'] <= 241 and capture['pngHeight'] == 160, capture
                    row = {'mode': mode, 'oldCaptureRejected': True, 'oldError': old_error,
                        'oldElapsedSeconds': old_elapsed, 'newCapture': capture}
                    if mode == 'paused-animation-frames':
                        row['rafCallbacksDuringPause'] = page.evaluate('rafCallbacks') - baseline
                        assert row['rafCallbacksDuringPause'] == 0, row
                        cdp.send('Emulation.setVirtualTimePolicy', {'policy': 'advance'})
                    summary['captures'].append(row)
                absent = page.evaluate(benchmark.HOST_SNAPSHOT)
                assert not absent['clientPresent'] and not absent['d3d9']['present']
                assert absent['adaptive']['currentSteps'] is None and absent['d3d9']['deviceCount'] is None
                summary['hostSnapshotChecks'].append({'case': 'absent-host', 'snapshot': absent})
                page.evaluate('''() => {
                  const forbidden=()=>{throw new Error('Observer accessed forbidden synthetic field')};
                  const queue={bytes:10,capacityBytes:20,inflight:2,submitted:9,consumed:7,completed:6,maxCommands:8};
                  const devices=new Map(Array.from({length:65},(_,i)=>['SECRET_KEY_'+i,
                    {residentBytes:100,resident:new Map([['SECRET_TEXTURE',{}]]),queue,deferred:new Set([1]),
                     dead:false,lost:false,releasing:false,deferredError:null}]));
                  const bridge={backend:'webgl',asyncSoftware:false,closed:false,lastError:null,devices,
                    requests:new Map(),presentWaits:new Set(),_textureSnapshots:new Map(),_textureSnapshotBytes:12,
                    maxTextureSnapshotBytes:32,maxResidentTextureBytes:0,maxRequests:8,maxDeferred:4};
                  Object.defineProperty(bridge,'sharedWorker',{get:forbidden});
                  const slice={blocks:6000,ms:12,yield:0,trapped:false};
                  Object.defineProperty(slice,'eip',{get:forbidden});Object.defineProperty(slice,'regs',{get:forbidden});
                  const client={stepsPerSlice:100000,_workerAdaptiveSteps:6000,_workerAdaptiveCeiling:100000,
                    _workerInputBurstSlices:2,_workerLastSlice:slice,
                    guestWorker:{sliceStats:{slices:9,guestMs:123,rpcSync:2,rpcAsync:3,rpcLocal:4,ends:{s:1,0:2,SECRET_END:4}}},
                    hostCtx:{d3d9Bridge:bridge},renderer:{inputQueue:[1,2],windows:{secretWindow:{}},
                      _workerGuestSliceDepth:1,_workerLastCompositeAt:123},
                    _renderWorkerManager:{queuedBytes:10,maxQueuedBytes:20,pending:new Map(),maxQueuedCommands:8,
                      ports:new Map([['SECRET_PORT',{}]]),maxEndpoints:4,closing:new Map(),stopped:false,_retired:false}};
                  Object.defineProperty(client,'memory',{get:forbidden});window.theseus={client};
                }''')
                present = page.evaluate(benchmark.HOST_SNAPSHOT)
                assert present['adaptive']['currentSteps'] == 6000 and present['adaptive']['lastSlice']['trapped'] is False
                assert present['sliceStats']['otherEndCount'] == 4 and present['sliceStats']['ends']['s'] == 1
                assert present['d3d9']['deviceCount'] == 65 and present['d3d9']['inspectedDevices'] == 64
                assert present['d3d9']['devicesTruncated'] and present['d3d9']['maxResidentTextureBytes'] == 0
                assert present['d3d9']['devices'][0]['residentBytes'] == 100
                assert present['presentation']['windowCount'] == 1 and present['renderTransport']['endpointCount'] == 1
                assert 'SECRET' not in json.dumps(present) and 'NOT a hard cap' in present['d3d9']['residentLimitMeaning']
                summary['hostSnapshotChecks'].append({'case': 'present-deidentified-capped-over-target', 'snapshot': present})
                page.evaluate("theseus.client._workerLastSlice.trapped='SECRET_SYNTHETIC_TRAP'")
                trapped = page.evaluate(benchmark.HOST_SNAPSHOT)
                assert trapped['adaptive']['lastSlice']['trapped'] is True
                assert 'SECRET' not in json.dumps(trapped)
                summary['hostSnapshotChecks'].append({'case': 'trap-presence-without-error-payload', 'snapshot': trapped})
                page.evaluate('delete theseus.client._workerLastSlice; delete theseus.client.hostCtx.d3d9Bridge.devices')
                partial = page.evaluate(benchmark.HOST_SNAPSHOT)
                assert partial['adaptive']['lastSlice']['blocks'] is None and partial['d3d9']['deviceCount'] is None
                assert partial['d3d9']['devicesTruncated'] is None
                summary['hostSnapshotChecks'].append({'case': 'missing-nested-fields', 'snapshot': partial})
            finally:
                context.close()
        summary['passed'] = True
    finally:
        benchmark.save(directory / 'result.json', summary)
        print(json.dumps({'evidence': str(directory), 'passed': summary['passed']}), flush=True)


if __name__ == '__main__':
    if sys.argv[1:] == ['--headed-smoke']:
        headed_smoke()
    else:
        unittest.main()
