# 0001 — Preserve physical modifier identity

[Wiki home](../README.md) · [Input subsystem](../audio-input.md) · [Issues BRC-002 / BRC-009](../issues.md)

Date: 2026-10-09. Contributor: Codex `/root`; no delegated agents. Status: implementation and contract tests complete; original gameplay skill reliability remains open. Evidence directory: [modifier-input-20261009T160349Z](../../reports/browser/modifier-input-20261009T160349Z/).

## Failure and cause

The earlier original-client replay had inconsistent skill/jump effects and did not isolate modifier behavior. Maintenance inspection found a concrete independent defect: `handleKeyDown/Up` stored only generic VK_CONTROL/VK_SHIFT/VK_MENU physical state, the DIK table mapped both sides to those generic values, and buffered scanning suppressed the right-hand codes. A new regression on the preserved control fails immediately because ShiftLeft has no side-specific physical state (`before-test.log`). This is not proof that modifier aliasing caused every failed skill.

Local `MapVirtualKeyW(MAPVK_VSC_TO_VK_EX)` measurements return six distinct VKs for the Set-1 modifier scan codes. `inspect_keyboard_modifiers.py` only queries mappings, records OS/bitness/DLL hash, and does not inject desktop input. Official DirectInput keyboard constants distinguish the corresponding device offsets. See [reference JSON](../../browser/reference/keyboard-modifiers.json).

## Change

`lib/renderer-input.js` now uses DOM code/location (or explicit side VK) for physical side state and ORs the two sides for the generic state. A release leaves the other held side intact. Numeric legacy callers use the left side. `src/09a8-handlers-directx.wat` maps six DIKs to their distinct physical VKs and scans right-side modifiers for buffered transitions. Immediate state uses strict DIK lookup, preventing unmapped offsets from aliasing newly populated side VKs. Numpad Enter remains a separate known limitation.

The shipped application title and prepared manifest adopt HEAV3NS-COMBO / BROCWIN without renaming historical records. Patch generation now includes local `test/` source additions; otherwise the restored dependency lacked six tests/helpers needed to maintain prior TLS/thread/audio repairs.

## Verification and repair instructions

`test_keyboard_modifiers.cjs` exercises real renderer physical state, actual Wasm DirectInput dispatch and stdcall cleanup, real Worker RPC, and the published Worker key bitmap. Its 108 transition checks cover both sides individually, held overlap, one-side release, repeat, buffered peek/consume and no phantom DIK bytes. `test_input_web.py` drives actual Edge DOM events on the prepared application and verifies both sides plus the generic aggregate. Existing message-ordering and DirectInput-device tests guard related behavior.

The first Worker test attempt omitted the scheduler's generation publication and therefore retained a cached press. The test harness was corrected to publish the same generation/bitmap boundaries as production; no scheduler behavior was changed to satisfy it. Preserve that failed attempt separately from the successful final test.

Run the canonical build, prepare and bootstrap check as in the runbook. Final build, command logs and identities are in `validation.json` in the evidence directory. This change is incorporated into the same runtime used by the original client. It adds no skill remapping, key-hold extension or guest instruction patch.

The subsequent [original-client replay](../../reports/browser/20261009T161827Z/review.json) verifies login, saved-character selection, Ruben terrain/buildings and left/right movement, plus System/Options opening and closing on this candidate. It finishes intentionally while executing after 1,485.828 seconds / 5,252 presentations. All 240 source identities, both modules and patch match before freeze release. Its 22 manual/final images were reviewed; automatic captures were not. Existing Lua exceptions and the font-bundle 404 remain. This run does not test dungeon combat, skill activation, new progression persistence, victory or revival.

## Limits

Native mapping agreement is not native injected DirectInput timing parity. Polled buffered input can still miss complete presses between polls; event-snapshot/focus semantics, Numpad Enter and broader Win32 side-state behavior need separate coverage. Successful contract tests and a ready-page DOM test do not prove awakening or all skills work in the original game. Keep BRC-002 open until the affected original paths are observed on the new build.
