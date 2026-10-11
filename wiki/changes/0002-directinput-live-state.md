# 0002 — DirectInput reads current physical keyboard state

[Wiki home](../README.md) · [Input subsystem](../audio-input.md) · [Issues BRC-002 / BRC-007](../issues.md)

Date: 2026-10-10. Contributor: Codex `/root`; no delegated agents. Status: runtime change and focused regressions passed; bounded original-client replay reviewed. [Sealed contract validation](../../reports/browser/input-live-20261010T065524Z/validation.json) · [Application review](../../reports/browser/20261010T070137Z/review.json).

## Failure and measured cause

The earlier skill-input symptoms remained unresolved after correcting modifier identity. A separate regression now demonstrates that a physical A press disappears from DirectInput while an older Win32 message has an up-state snapshot. The preserved control returns neither DIK `0x1e` in `GetDeviceState` nor its transition in `GetDeviceData`.

`di_kbd_live` called `host_get_key_down_state`. That import deliberately honors `renderer._activeInputEvent.keyStateSnapshot`, and its Worker adapter tracks the open message and caches message-relative state. Sharing it with DirectInput lets an old message suppress a new physical press or retain a released key. This is a demonstrated compatibility defect, not proof that it explains every previously failed skill or the options timeout.

Microsoft describes DirectInput's [immediate keyboard state](https://learn.microsoft.com/en-us/previous-versions/windows/desktop/ee418261(v=vs.85)) and the message-relative state used by [Win32 GetKeyState](https://github.com/MicrosoftDocs/win32/blob/docs/desktop-src/LearnWin32/keyboard-input.md). This pass does not claim a native injected timing comparison.

## Implementation

- `src/01-header.wat` adds `get_key_down_state_live`; generated host-import signatures include it.
- `lib/host-window.js` reads the renderer's physical state through that import without consuming press bits or inspecting the active message.
- `lib/guest-rpc.js` reads the published physical-key bitmap even while a Win32 message is open; its unpublished fallback uses the dedicated host import. It does not reuse the message cache.
- `src/09a8-handlers-directx.wat` uses the live import for the keyboard's immediate state and existing polled transition reader. Win32 GetKeyState/GetKeyboardState retain their message behavior.

All files belong to the same original-client runtime. No game instruction, key binding, artificial key hold, timer or acknowledgement changes. Native servers and SQL stay locally maintained outside the client port, as clarified by the user on this date.

## Regression and reproduction

Run `node theseus/browser/test_keyboard_modifiers.cjs`. It retains 108 modifier transitions and adds six press/release cases under deliberately older open-message snapshots. Direct Wasm, actual Worker RPC and published Worker bitmap paths pass; the Worker also checks the message-relative answer. `control.log` records the pre-fix failure, and `candidate-keyboard.log` records the pass.

The canonical build, DirectInput-device behavior, keyboard-message ordering, SetKeyboardState, Worker focus, per-slot input events and integration-runtime regressions pass. Prepared-application DOM checks pass in Edge 155.0.4283.45. The first DOM attempt failed because port 8766 had no browser host; that log is retained, followed by the successful unchanged test after restarting the local host. See [build/recovery](../build-recovery.md) for the canonical commands.

The validation preserves both module identities, the patch, control/candidate source and command logs. The application capture uses its own frozen candidate and review; do not transfer older gameplay observations to this new build.

## Original-client dependency and replay

[Bounded original code](../../reports/browser/20261010T070137Z/original-input-path.json), reproduced by [inspect-original-input.py](../../reports/browser/20261010T070137Z/inspect-original-input.py), ties `DirectInput8Create` at `0x3286ea31` to the input stage. The update adapter at `0x3286e930` calls `0x3286e800`, which updates its devices through `0x32900350`. That device routine calls COM slots for Poll and GetDeviceState; the keyboard request is 256 bytes. Input-lost/not-acquired results lead to Acquire and retry. These are four decoded blocks from the unchanged, hash-checked executable, not a complete call graph or a live instruction trace. The immediate-state repair reaches the same compatibility handler used by this original path; a buffered-only repair would not establish correctness here.

The [2195.281-second replay](../../reports/browser/20261010T070137Z/review.json) executes original login, the saved level-10 character, Ruben, Skills, Tree of El Normal, first-area CLEAR, second-area combat/defeat, rewards and the first return. All 240 source identities, both modules and patch match. It ends intentionally while executing after 2,983 presentations, with 75 manual/final images reviewed. No execution breakpoints, watchpoints or diagnostic guest writes are used.

| Controlled input / original state | Observed outcome | Evidence |
| --- | --- | --- |
| A held alone with 300 MP | Flame Geyser cut-in; MP drops to 150; cooldown appears | Requests 039–040 and 052 |
| S held alone | Second-slot movement animation, MP change and cooldown; later use displays `Roll` | Request 041; later mixed Z/S batch 057 |
| ControlLeft held alone after first-area CLEAR | Two charged orbs consumed; awakening animation then countdown | Requests 053–055 |
| All keys released before depleted HP | FAILURE result and rewards without further input; first return with terrain and movement | Requests 058–066 |

The [input and image observations](../../reports/browser/20261010T070137Z/gameplay-observations.json) retain unsuccessful attempts too. Request 043's short A press and several attempts during enemy hits do not verify activation. The test's longer holds are observations, not a runtime hold extension. Skills UI showed two learned level-1 skills and 37 unused points; no allocation or binding was changed. The first tooltip supplies the Flame Geyser MP/cooldown context.

The original reward panel displays 2,726 EXP and 54 ED. [Read-only database observations](../../reports/browser/20261010T070137Z/database-observations.json) match those gains after the first return and browser closure. No revival or boss victory occurs. System/Options opens and closes; a one-second close click lacks a visible effect, while a second three-second click closes it. Empty sampled pending lists do not prove event 574 delivery or resolve BRC-001.

## Remaining limits

Buffered keyboard input still derives edges by comparing polled physical states. A complete press between polls can remain invisible, and Numpad Enter still aliases Return. Focus/lifecycle semantics and all skill assignments need broader coverage; animation/stun, polling and eligibility remain confounded in unsuccessful attempts. The options ACK failure, text/rendering defects and victory/revival coverage remain separate issues. The replay retains 54 original Lua throws and a font-bundle 404 with two error records. The optional bulk endpoint has a per-file fallback; its 404 alone does not establish missing fonts. Edge 155 differs from the preceding Edge 154 runs, and presentation counts are not a performance comparison.
