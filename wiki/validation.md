# Validation and native behavioral references

Frozen closeout, 2026-10-11: only read-only documentation verification applies while the environment is frozen. The [closeout](closeout.md) records uncompleted application/performance gates and exact prepared/source differences; the procedures below require reopening for any build, capture or environment action.

[Runtime startup validation](performance.md) is separate from gameplay acceptance. Its runner records only browser/runtime boundary observations and supplies Start client, preserving frozen routes and original inputs. Cache corruption/version/storage-failure regressions and original login images qualify the cache candidate; they do not qualify untested gameplay.

[Wiki home](README.md) · [Generated test/evidence index](generated/INDEX.md) · [Maintenance contract](maintenance.md)

## Evidence levels

1. **Source/reference:** original bytes, bounded disassembly/RTTI, native API/COM observations, or official contract documentation. Preserve image hashes, architecture/OS and helper source. This establishes a contract, not application execution.
2. **Regression:** actual Wasm handler/guest instruction, relevant Worker/RPC and renderer routes, with failure/control when practical. Synthetic fixtures isolate a subsystem but remain supporting tests of the same runtime.
3. **Original-client replay:** unchanged application code, named build, normal input, real services, reviewed route/screenshots and persistent-state observations. This establishes only that route on that build.

The inherited [native baseline](../baseline.json) remains the game behavior reference, with its original provenance; this maintenance pass did not re-run that native combat session. Native API references under `browser/reference` identify the local platform tested and do not automatically establish historical Windows 7 or Win98 behavior.

## Focused checks

Run the tests listed for the changed subsystem in the generated index. Examples from the repository root:

```powershell
node theseus/browser/test_keyboard_modifiers.cjs
python theseus/browser/test_input_web.py
node theseus/tools/wine-assembly/test/test-pe-dll-static-tls.js
node theseus/tools/wine-assembly/test/test-dll-thread-attach-wait.js
python theseus/browser/test_network.py
python theseus/browser/test_network_wasm.py
python theseus/browser/test_server.py
```

The DOM test needs the prepared application served on 8766 and does not launch the game. Other test-specific native/reference/browser prerequisites are recorded in each helper. Do not blindly run provisioning scripts. Full build gates are required after WAT changes; successful gates do not replace behavior tests.

## Capture procedure

Before `python theseus/browser/capture.py --seconds 2400`, preserve the manifest's source files, integration files, both modules and runtime patch in a unique report, hash them, and announce a source freeze on the dependency message board. Save the capture's actual manifest and compare it with the frozen candidate. No build, prepare or runtime/integration edit occurs while it runs. Wiki prose outside the frozen sources may be developed separately, without claiming unreviewed results.

The capture prints its UTC folder and accepts `request.json` with a fresh `id`. Input is the `input` array, not `actions`. Example screenshot request:

```json
{"id": 1, "screenshot": true}
```

Use ordinary browser input through the validated capture actions. Inspect `response.json` for the same ID and for `requestError`; a helper's exit code alone may not mean success. Maximum batch sizes and duration bounds are owned by `capture.py` / `test_capture_input.py`. Never print login text into logs; use the existing local credential-safe flow or type manually in an interactive browser.

Send one navigation click, then inspect the resulting screen before repeating it. A queued second click can arrive after a transition and target the next screen. Preserve unintended navigation and the ordinary Back/Cancel recovery in the record; do not remove it to make the replay appear cleaner.

Finish with a fresh `{"id": N, "finish": true, "screenshot": true}` request and wait for final `result.json`. Collect executing state before teardown. Inspect the manual/final images, retain errors, compare sources/modules/patch and publish `review.json` last. A missing response after the guest exited is not a delivered input. The same UTC folder may contain unreviewed automatic images; explicitly label them.

Read-only probes can race live mutation and add overhead. Breakpoints/watchpoints disable execution optimizations and alter scheduling. A watched shared-memory change does not identify its writer. Exclude unstable traversals and maintain separate instrumented/uninstrumented claims. Capture elapsed time and presentation totals are not performance benchmarks.

Release the source freeze only after the review/source audit is sealed. Never rewrite sealed evidence to match newer conclusions; add a new correction record and preserve the old one.
