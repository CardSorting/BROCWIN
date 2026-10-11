"""Run and capture the actual integrated browser application using local Edge."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sys
import time
from urllib.parse import urlsplit, unquote

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'theseus/tools/python'))
from playwright.sync_api import sync_playwright, Error as PlaywrightError, TimeoutError as PlaywrightTimeoutError


def capture_image(page, destination, result):
    """A missed diagnostic image must not terminate a running original client."""
    try:
        page.screenshot(path=str(destination), full_page=True, timeout=5000)
    except PlaywrightTimeoutError as error:
        failure = {'requestedName': destination.name, 'error': str(error),
                   'at': datetime.now(timezone.utc).isoformat()}
        result.setdefault('screenshotErrors', []).append(failure)
        print(json.dumps({'screenshotTimeout': failure}), flush=True)
        return False
    return True


def publish_json(destination, value):
    """Replace a complete record, allowing Windows readers to release it."""
    pending = destination.with_suffix('.tmp')
    pending.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
    for attempt in range(81):
        try:
            pending.replace(destination)
            return
        except PermissionError:
            if attempt == 80:
                raise
            time.sleep(0.025)


def read_control_request(request_file, result):
    """Retry an unavailable control file on the next ordinary capture poll."""
    try:
        return json.loads(request_file.read_text(encoding='utf-8'))
    except FileNotFoundError:
        return None
    except (PermissionError, json.JSONDecodeError) as error:
        # A Windows sharing/replacement race must not close a running game.
        # Do not consume an ID or apply input until a complete read succeeds.
        now = datetime.now(timezone.utc).isoformat()
        retries = result.setdefault('controlReadRetries', {'count': 0, 'firstAt': now})
        retries.update(count=retries['count'] + 1, lastAt=now, lastError=str(error))
        return None


def validate_input(actions, dims):
    """Reject the whole batch before any browser input is sent."""
    if not isinstance(actions, list) or len(actions) > 64:
        raise ValueError('input must be a list of at most 64 actions')
    for action in actions:
        if not isinstance(action, dict):
            raise ValueError('Each input action must be an object')
        kind = action.get('type')
        if kind in ('click', 'move'):
            x, y = action.get('x'), action.get('y')
            if not all(type(v) in (int, float) and math.isfinite(v) for v in (x, y)) or not (
                    0 <= x < dims['width'] and 0 <= y < dims['height']):
                raise ValueError('Input coordinates must be inside the game canvas, in canvas pixels')
            if kind == 'click' and action.get('button', 'left') not in ('left', 'middle', 'right'):
                raise ValueError('Invalid mouse button')
            if kind == 'click':
                hold = action.get('holdMilliseconds', 80)
                if type(hold) is not int or not 0 <= hold <= 5000:
                    raise ValueError('Click hold must be an integer from 0 to 5000 ms')
        elif kind == 'text':
            value = action.get('text')
            if not isinstance(value, str) or len(value) > 512:
                raise ValueError('Input text must contain at most 512 characters')
        elif kind in ('press', 'down', 'up'):
            key = action.get('key')
            if not isinstance(key, str) or not 1 <= len(key) <= 64:
                raise ValueError('Invalid key')
        elif kind == 'wait':
            ms = action.get('milliseconds')
            if type(ms) is not int or not 0 <= ms <= 5000:
                raise ValueError('Input wait must be an integer from 0 to 5000 ms')
        else:
            raise ValueError('Unknown input action')


def apply_input(page, actions):
    """Use browser input events, never writes to guest game state. Text is redacted in evidence."""
    dims = page.locator('#game').evaluate('(c) => ({width: c.width, height: c.height})')
    validate_input(actions, dims)
    events = []
    for action in actions:
        kind = action['type']
        if kind in ('click', 'move'):
            x, y = action['x'], action['y']
            box = page.locator('#game').bounding_box()
            px, py = box['x'] + x * box['width'] / dims['width'], box['y'] + y * box['height'] / dims['height']
            if kind == 'click':
                button = action.get('button', 'left')
                hold = action.get('holdMilliseconds', 80)
                page.mouse.click(px, py, button=button, delay=hold)
                events.append({'type': kind, 'x': x, 'y': y,
                               'button': button, 'holdMilliseconds': hold})
            else:
                page.mouse.move(px, py)
                events.append({'type': kind, 'x': x, 'y': y})
        elif kind == 'text':
            page.keyboard.type(action['text'], delay=80)
            events.append({'type': kind, 'characters': len(action['text']), 'textRedacted': True})
        elif kind in ('press', 'down', 'up'):
            getattr(page.keyboard, kind)(action['key'])
            events.append({'type': kind, 'key': action['key']})
        elif kind == 'wait':
            page.wait_for_timeout(action['milliseconds'])
            events.append({'type': kind, 'milliseconds': action['milliseconds']})
    return events


def apply_breakpoint_request(page, request, result, elapsed):
    """A rejected diagnostic plan must not terminate the running application.

    The guest Worker remains the authority for read bounds and validates the
    complete plan before installing it. No validation limit is relaxed here.
    """
    if 'breakpoints' not in request:
        return None
    scope = request.get('breakpointScope', 'main')
    try:
        count = page.evaluate('({points, scope}) => window.theseusCaptureProbe.breakpoints(points, scope)',
                              {'points': request['breakpoints'], 'scope': scope})
    except PlaywrightError as error:
        rejection = {'id': request.get('id'), 'requestError': str(error),
                     'phase': 'breakpoint-plan', 'elapsedSeconds': elapsed}
        result.setdefault('rejectedRequests', []).append(rejection)
        return rejection
    result.setdefault('breakpointPlans', []).append({'id': request.get('id'),
        'elapsedSeconds': elapsed, 'count': count, 'points': request['breakpoints'],
        'scope': scope, 'schedulingAltered': True})
    return None


def observe(url):
    """One visible client, without capture probes or an automatic close deadline."""
    out = ROOT / 'theseus/reports/browser' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out.mkdir(parents=True)
    print(json.dumps({'observationStarted': str(out), 'url': url}), flush=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='msedge', headless=False)
        page = browser.new_page(viewport={'width': 1280, 'height': 1100})
        page.bring_to_front()
        status = {'headed': True, 'keepOpen': True, 'probesInstalled': False,
                  'url': url, 'browserVersion': browser.version, 'phase': 'opening'}
        publish_json(out / 'observation.json', status)
        try:
            page.goto(url, wait_until='domcontentloaded', timeout=60000)
            page.wait_for_function('window.theseus && ["ready", "stopped-incomplete"].includes(window.theseus.state)', timeout=60000)
            if page.evaluate('window.theseus.state') == 'ready':
                page.locator('#start').click()
                page.locator('#game').focus()
                status['phase'] = 'client-started'
                publish_json(out / 'observation.json', status)
        except PlaywrightError as error:
            status.update(phase='open-with-startup-error', error=str(error))
            publish_json(out / 'observation.json', status)
            print(str(error), flush=True)
        # Human closure is the only ordinary termination condition. No timeout,
        # debugger, guest-memory probe, scripted gameplay or automatic Stop.
        photographed = False
        while browser.is_connected() and not page.is_closed():
            try:
                page.wait_for_timeout(1000)
                if not photographed and page.evaluate('(window.theseus?.frames || 0) > 0'):
                    if capture_image(page, out / 'visible-client.png', status):
                        photographed = True
                        status.update(phase='rendering', screenshot='visible-client.png')
                        publish_json(out / 'observation.json', status)
            except PlaywrightError:
                if not browser.is_connected() or page.is_closed():
                    break
        status['phase'] = 'closed-by-human'
        publish_json(out / 'observation.json', status)


def capture(url, seconds, watch_pointer=None, watch_offset=0, trace_windows=False, headed=False):
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out = ROOT / 'theseus/reports/browser' / stamp
    out.mkdir(parents=True)
    print(json.dumps({'captureStarted': str(out), 'seconds': seconds}), flush=True)
    entries = []
    observed = {}
    started = None
    result = {'schema': 'theseus.browser-evidence/v1', 'startedAt': stamp, 'url': url,
              'contributor': 'Codex /root', 'mode': 'browser-native-x86-wasm',
              'verifiedGameplay': False, 'requestedSeconds': seconds, 'records': entries}
    result['traceWindows'] = trace_windows
    result['headed'] = headed
    if watch_pointer is not None:
        result['pointerWatch'] = {'pointerAddress': watch_pointer, 'offset': watch_offset,
                                  'schedulingAltered': True}
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='msedge', headless=not headed)
        result['browserVersion'] = browser.version
        page = browser.new_page(viewport={'width': 1280, 'height': 1100})
        def console_message(msg):
            entries.append({'kind': msg.type, 'message': msg.text})
            if 'UNIMPLEMENTED' in msg.text or 'Program exited' in msg.text:
                print(msg.text.encode('ascii', errors='backslashreplace').decode('ascii'), flush=True)
        page.on('console', console_message)
        page.on('pageerror', lambda err: entries.append({'kind': 'pageerror', 'message': str(err)}))
        page.on('requestfailed', lambda req: entries.append({'kind': 'requestfailed', 'url': req.url, 'failure': req.failure}))
        page.on('response', lambda res: entries.append({'kind': 'http-error', 'url': res.url, 'status': res.status}) if res.status >= 400 else None)
        def capture_script(request):
            if not urlsplit(request.url).path.endswith('.js'):
                return
            response = request.response()
            if not response or response.status != 200:
                return
            name = unquote(urlsplit(response.url).path).lstrip('/')
            try:
                # Read immediately: multi-gigabyte asset traffic can evict old
                # script bodies from Chromium's inspector cache before teardown.
                digest = hashlib.sha256(response.body()).hexdigest()
                observed.setdefault(name, set()).add(digest)
            except Exception as error:
                entries.append({'kind': 'source-hash-error', 'url': response.url, 'message': str(error)})
        page.on('requestfinished', capture_script)
        try:
            page.goto(url, wait_until='domcontentloaded', timeout=60000)
            page.wait_for_function('window.theseus && ["ready", "stopped-incomplete"].includes(window.theseus.state)', timeout=60000)
            if page.evaluate('window.theseus.state') == 'ready':
                page.evaluate((HERE / 'capture_probe.js').read_text(encoding='utf-8'))
                page.evaluate('(options) => window.theseusCaptureProbe.configure(options)', {'traceWindows': trace_windows})
                if watch_pointer is not None:
                    page.evaluate('(config) => window.theseusCaptureProbe.watchPointer(config)',
                                  {'pointerAddress': watch_pointer, 'offset': watch_offset})
                page.locator('#start').click()
                started = time.monotonic()
                end = started + seconds
                next_sample = time.monotonic() + 10
                next_snapshot = time.monotonic() + 60
                last_request = None
                requested_image_count = 0
                while time.monotonic() < end:
                    page.wait_for_timeout(1000)
                    request = read_control_request(out / 'request.json', result)
                    if request and request.get('id') != last_request:
                        last_request = request.get('id')
                        extension = request.get('extendSeconds', 0)
                        try:
                            if type(extension) is not int or not 0 <= extension <= 3600:
                                raise ValueError('extendSeconds must be an integer from 0 to 3600')
                            dims = page.locator('#game').evaluate('(c) => ({width: c.width, height: c.height})')
                            validate_input(request.get('input', []), dims)
                        except ValueError as error:
                            rejection = {'id': last_request, 'requestError': str(error),
                                         'elapsedSeconds': time.monotonic() - started}
                            result.setdefault('rejectedRequests', []).append(rejection)
                            publish_json(out / 'response.json', rejection)
                            continue
                        rejection = apply_breakpoint_request(page, request, result, time.monotonic() - started)
                        if rejection:
                            publish_json(out / 'response.json', rejection)
                            continue
                        if extension:
                            end += extension
                            result.setdefault('durationExtensions', []).append(
                                {'id': last_request, 'seconds': extension,
                                 'elapsedSeconds': time.monotonic() - started})
                        inputs = apply_input(page, request.get('input', []))
                        if inputs:
                            result.setdefault('inputHistory', []).append({'id': last_request,
                                'elapsedSeconds': time.monotonic() - started, 'events': inputs})
                        reply = page.evaluate('(request) => window.theseusCaptureProbe.inspect(request)', request)
                        if reply.get('drawCapture'):
                            name = f'draws-{len(result.setdefault("drawSnapshots", [])):03d}.json'
                            publish_json(out / name, reply.pop('drawCapture'))
                            result['drawSnapshots'].append(name)
                            reply['drawCaptureFile'] = name
                        if request.get('screenshot'):
                            name = f'request-{requested_image_count:03d}.png'
                            requested_image_count += 1
                            if capture_image(page, out / name, result):
                                result.setdefault('requestedScreenshots', []).append(name)
                                reply['screenshot'] = name
                            else:
                                reply['screenshotError'] = result['screenshotErrors'][-1]['error']
                        reply['id'] = last_request
                        publish_json(out / 'response.json', reply)
                        if request.get('finish'):
                            result['finishedByCaptureRequest'] = last_request
                            break
                    if page.evaluate('window.theseus.state') == 'stopped-incomplete':
                        break
                    if time.monotonic() >= next_sample:
                        sample = page.evaluate('window.theseusCaptureProbe.sample()')
                        result.setdefault('executionSamples', []).append({'elapsedSeconds': time.monotonic() - started, **sample})
                        progress = page.evaluate('({state: window.theseus.state, frames: window.theseus.frames || 0, frameKinds: window.theseus.frameKinds || {}})')
                        progress.update({'schema': 'theseus.browser-progress/v1', 'verifiedGameplay': False,
                                         'samples': result['executionSamples'][-6:], 'records': entries[-24:]})
                        publish_json(out / 'progress.json', progress)
                        next_sample = time.monotonic() + 10
                    if time.monotonic() >= next_snapshot:
                        elapsed = int(time.monotonic() - started)
                        capture_image(page, out / f'at-{elapsed:06d}.png', result)
                        next_snapshot = time.monotonic() + 60
                result['elapsedSeconds'] = time.monotonic() - started
        except Exception as error:
            result['captureError'] = str(error)
        finally:
            if started is not None:
                result['elapsedSeconds'] = time.monotonic() - started
            # A stopped guest releases its memory. Collect each independent
            # artifact even if a probe or input request failed at that boundary.
            for key, expression in {
                'state': 'window.theseus?.state',
                'evidence': '({records: window.theseus?.records, frames: window.theseus?.frames || 0, frameKinds: window.theseus?.frameKinds || {}, isolated: crossOriginIsolated})',
                'runtime': 'window.theseus?.manifest?.runtime',
                'diagnostics': '({observations: window.theseusCaptureProbe?.observations, files: window.theseusCaptureProbe?.files(), runtime: window.theseusCaptureProbe?.runtime()})',
            }.items():
                try:
                    result[key] = page.evaluate(expression)
                except Exception as error:
                    result[key] = None
                    result.setdefault('collectionErrors', []).append({'artifact': key, 'error': str(error)})
            expected = (result.get('runtime') or {}).get('sourceFiles', {})
            result['observedRuntimeScripts'] = {name: sorted(values) for name, values in observed.items() if name in expected}
            result['sourceMismatches'] = ([name for name, values in observed.items() if name in expected and values != {expected[name]}]
                                         if expected else None)
            result['sourceIdentityScope'] = 'JavaScript responses observed by Playwright on this page; worker-only responses may not be exposed'
            try:
                if capture_image(page, out / 'browser.png', result):
                    result['screenshot'] = 'browser.png'
            except Exception as error:
                result.setdefault('collectionErrors', []).append({'artifact': 'browser.png', 'error': str(error)})
            try:
                browser.close()
            except Exception as error:
                result.setdefault('collectionErrors', []).append({'artifact': 'browser-close', 'error': str(error)})
    publish_json(out / 'result.json', result)
    print(json.dumps({'path': str(out), 'state': result.get('state'),
                      'error': result.get('captureError'), 'events': len(entries)}))
    for entry in entries[-16:]:
        print(entry)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:8766')
    parser.add_argument('--seconds', type=int, default=30)
    parser.add_argument('--watch-pointer', type=lambda value: int(value, 16),
                        help='Watch the DWORD at a guest pointer plus offset once initialized (hex)')
    parser.add_argument('--watch-offset', type=lambda value: int(value, 16), default=0)
    parser.add_argument('--trace-windows', action='store_true', help='Record actual window geometry imports')
    parser.add_argument('--headed', action='store_true', help='Show the Edge window controlled by this capture')
    parser.add_argument('--keep-open', action='store_true', help='Visible observation only; no probes or automatic close')
    args = parser.parse_args()
    if args.keep_open:
        if not args.headed or args.watch_pointer is not None or args.trace_windows:
            parser.error('--keep-open requires --headed and excludes diagnostic options')
        observe(args.url)
    else:
        capture(args.url, args.seconds, args.watch_pointer, args.watch_offset, args.trace_windows, args.headed)
