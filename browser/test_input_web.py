"""Real DOM events must reach the shipped application's renderer input bridge.

Checks the prepared app at its ready screen; does not launch an original client.
"""
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'tools/python'))
from playwright.sync_api import sync_playwright
from capture import apply_input

with sync_playwright() as p:
    browser = p.chromium.launch(channel='msedge', headless=True)
    try:
        page = browser.new_page()
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto('http://127.0.0.1:8766/')
        page.wait_for_function('window.theseus?.state === "ready"', timeout=60000)
        assert page.evaluate('window.browserInput.isWired()'), 'DOM input is connected'
        page.evaluate('''() => {
          window.inputCalls=[];
          for (const name of ['handleMouseMove','handleMouseDown','handleMouseUp',
                              'handleKeyDown','handleKeyUp','handleKeyPress']) {
            const original=Win98Renderer.prototype[name];
            Win98Renderer.prototype[name]=function(...args) {
              inputCalls.push({name,args}); return original.apply(this,args);
            };
          }
        }''')
        canvas = page.locator('#game')
        box = canvas.bounding_box()
        page.mouse.click(box['x'] + box['width'] * 0.5, box['y'] + box['height'] * 0.5)
        canvas.focus()
        page.keyboard.type('a', delay=80)
        calls = page.evaluate('inputCalls')
        for name in ['handleMouseDown', 'handleMouseUp', 'handleKeyDown', 'handleKeyUp']:
            assert sum(row['name'] == name for row in calls) == 1, (name, calls)
        assert [row['args'][0] for row in calls if row['name'] == 'handleKeyPress'] == [97], calls
        assert any(row['name'] == 'handleMouseDown' and row['args'][:2] == [512, 384]
                   for row in calls), calls
        assert page.title() == 'HEAV3NS-COMBO'
        modifier_checks = 0
        for generic, left, right, left_vk, right_vk in (
            (16, 'ShiftLeft', 'ShiftRight', 160, 161),
            (17, 'ControlLeft', 'ControlRight', 162, 163),
            (18, 'AltLeft', 'AltRight', 164, 165),
        ):
            def keys():
                return page.evaluate('keys => keys.map(k => renderer.peekKeyDownState(k))',
                                     [generic, left_vk, right_vk])
            page.keyboard.down(right)
            assert keys() == [32768, 0, 32768], (right, keys())
            page.keyboard.down(left)
            assert keys() == [32768, 32768, 32768], (left, keys())
            page.keyboard.up(right)
            assert keys() == [32768, 32768, 0], (right, keys())
            page.keyboard.up(left)
            assert keys() == [0, 0, 0], (left, keys())
            modifier_checks += 4
        page.evaluate("record('runtime', '[input] hwnd=0x10001 msg=0x102 wParam=0x61')")
        recorded = page.evaluate('window.theseus.records.at(-1).message')
        assert 'wParam=[redacted]' in recorded and '0x61' not in recorded, recorded
        page.evaluate('''() => {
          window.heldClickEdges=[];
          for (const type of ['mousedown','mouseup']) {
            window.addEventListener(type, event =>
              heldClickEdges.push({type,button:event.button,time:performance.now()}), true);
          }
        }''')
        held = apply_input(page, [{'type': 'click', 'x': 512, 'y': 384,
                                   'holdMilliseconds': 1000}])
        edges = page.evaluate('heldClickEdges')
        assert [edge['type'] for edge in edges] == ['mousedown', 'mouseup'], edges
        assert edges[1]['time'] - edges[0]['time'] >= 900, edges
        assert held[0]['holdMilliseconds'] == 1000 and held[0]['button'] == 'left', held
        calls = page.evaluate('inputCalls')
        for name in ['handleMouseDown', 'handleMouseUp']:
            assert sum(row['name'] == name for row in calls) == 2, (name, calls)
        page.add_script_tag(path=str(HERE / 'capture_probe.js'))
        observation = page.evaluate('theseusCaptureProbe.inspect({memory:[{address:0x400000,size:16}],files:true})')
        assert observation['unavailable'] and not observation['runtime']['memoryAvailable'], observation
        assert page.evaluate('theseusCaptureProbe.sample()') == {'unavailable': True}
        assert not errors, errors
        print(json.dumps({'test': 'prepared app DOM input wiring', 'browser': browser.version,
                          'mouse': 'canvas coordinates and one held down/up pair preserved',
                          'holdMilliseconds': edges[1]['time'] - edges[0]['time'],
                          'physicalModifierChecks': modifier_checks,
                          'character': 'once', 'status': 'passed'}))
    finally:
        browser.close()
