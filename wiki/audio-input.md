# Audio and input

Current [145806](../reports/browser/20261011T145806Z/review.json) verifies movement/jumps, Z damage/combos, repeated Flame Geyser MP/cooldown/cut-in and distinct Roll cooldown/displacement, original menus and post-return interaction. Long holds and three Dungeon clicks remain limitations. Attempts during knockdown or inadequate MP are not classified as input loss. The independent revival check sends three Z900ms pulses during sampled death animation and three after final-dead state, without success; nine stones remain and native stones-used0. Policy1 is already present at first final-dead sample15.567354 seconds after death. This is not proof of a keyboard-layer failure; execution timing and full skill/focus/effect fidelity remain unresolved.

[Wiki home](README.md) · [Implementation and tests](generated/INDEX.md#audio-input)

Browser DOM events enter `browser-input.js` and the one shared renderer. `renderer-input.js` retains message ordering and physical state; `host-window.js` and Worker RPC expose it to Windows/DirectInput calls. Original game bindings, menus and skill logic remain authoritative. Capture controls use normal browser events. A logged key press proves delivery to that layer, not a successful game action.

## Modifier maintenance

The first BROCWIN maintenance change preserves left/right Ctrl, Shift and Alt in physical key state and DirectInput DIK offsets. Previously both sides aliased a generic VK and buffered scans skipped right modifiers. Releasing one physical side now retains the other. Unmapped DIK bytes stay zero instead of acquiring phantom state through a raw VK-index fallback. Numeric-only legacy callers map generic modifiers to the left key. Win32 message order and original game bindings are not rewritten.

The [change record](changes/0001-modifier-identity.md) links the failing control, native `MapVirtualKeyW` mapping reference, real Wasm/Worker tests and prepared-application DOM test. Microsoft documents distinct keyboard-device offsets and physical state semantics ([keyboard constants](https://learn.microsoft.com/en-us/previous-versions/windows/desktop/ee418641(v=vs.85)), [DirectInput behavior](https://learn.microsoft.com/en-us/previous-versions/windows/desktop/ee418998(v=vs.85))). The native reference is a mapping measurement, not native injected DirectInput events.

The [sealed maintenance validation](generated/evidence/modifier-validation.json) preserves the successful commands, control failure, candidate identity and restoration check. It is separate from original-client replay evidence.

## Physical state during an open message

[Change 0002](changes/0002-directinput-live-state.md) separates DirectInput's current physical keyboard read from Win32's message-relative key state. A retained control loses a physical A press under an older up-message snapshot; the inverse can retain a released key. A dedicated import and Worker physical-bitmap path correct this without changing GetKeyState/GetKeyboardState. Six focused cases pass across direct Wasm, real Worker RPC and the published bitmap, alongside the existing 108 modifier cases. Original-game verification is recorded separately.

The [070137 replay](../reports/browser/20261010T070137Z/review.json) now verifies isolated A activation (Flame Geyser, MP/cooldown/cut-in), isolated S activation (movement skill, MP/cooldown) and isolated ControlLeft awakening after area CLEAR (orb consumption and countdown). Several attempts during enemy hits remain unconfirmed. The original Skills UI supplies learned-skill and resource context; no binding or point allocation was changed. Its [bounded original input path](../reports/browser/20261010T070137Z/original-input-path.json) polls a 256-byte immediate keyboard state through GetDeviceState, with Acquire/retry on device errors. Static recovery is not a live poll trace.

This repair does not resolve all inconsistent skills. Short presses can occur between polls; the current buffered implementation derives transitions from polled state, not a complete hardware-event history. Active Win32 event snapshots and focus changes also require separate coverage. Do not stretch key holds in production or remap skills to conceal these gaps. Numpad Enter still shares VK_RETURN and its buffered duplicate is suppressed. Use the failed and successful input sequences in change 0002 when reproducing, and separate animation/stun, MP/cooldown and polling from DOM delivery.

Historical [043232](../reports/browser/20261011T043232Z/review.json) confirms repeated Flame Geyser damage/MP/cooldown, Roll, one- and two-orb awakening, and potion use through two area clears. Some turn/skill attempts during hit reactions do not produce the expected action; this is not proof that the input layer lost them. Its repeated Z revival failure did not identify the preceding eligibility condition. Historical [092157](../reports/browser/20261011T092157Z/revival-failure.json) reproduces failure without armed breakpoints and separately identifies the original end-game notification disabling continue before final death state. Remapping Z or synthesizing a continue choice would not repair that ordering.

Historical [123040](../reports/browser/20261011T123040Z/review.json) verifies basic sword action, Flame Geyser activation/MP/cooldown with enemy removal, and distinct Roll animation/cooldown. Six ordinary Z pulses still fail revival with continue disabled and all nine stones retained. The unchanged native reference successfully revives through ordinary Z; this does not establish that browser input loss caused the failure. Low execution rate, short input/focus reliability and full skill-effect fidelity remain open. See the [acceptance report](acceptance-session.md) for the sampled timing and exact build.

## Audio contract

Original FMOD executes in the guest and uses DirectSound/Windows audio contracts. Reconstructed enumeration invokes real original callbacks, honors cancellation/nesting and device identity; host audio submits PCM through WebAudio/worklets. The DirectSound enumeration and ordinal regressions cover this boundary.

The integrated client has an enabled audio path, a running AudioContext and changing nonzero PCM. These observations do not establish audible quality, timing, music/effect balance or complete audio parity. For silence, check a trusted gesture/audio unlock, context state, original device selection, buffer ownership and submitted sample changes in that order. Preserve actual audio evidence before claiming an audible result.

The initial [194707 audio record](generated/evidence/audio-194707.json) was interrupted by a daemon restart after its last saved sample and has no final collection; that limitation stays attached to its FMOD/PCM observation. Later gameplay records retain the separate audible-fidelity limitation.

## Reproduce and diagnose

Run `node theseus/browser/test_keyboard_modifiers.cjs`, `python theseus/browser/test_input_web.py` (server on 8766), and the related DirectInput/message tests. The DOM test loads the same application ready page without launching the game; the Wasm test exercises actual handlers with test-created devices. Then replay the original binding/action with enough context to distinguish cooldown, MP, stun, focus and character animation. Record key down/up timing, phase and visible outcome; do not infer missing input solely from a failed skill animation.
