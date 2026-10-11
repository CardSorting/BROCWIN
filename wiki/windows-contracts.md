# Windows compatibility contracts

[Wiki home](README.md) · [Implementation and tests](generated/INDEX.md#windows) · [Reference inventory](generated/INDEX.md#native-and-original-reference-inventory) · [Loading](loading.md)

The client retains its original Windows API dependencies. Reconstructed handlers must preserve observable return values, thread errors, structure layouts, buffer sizes, callbacks, object ownership and x86 stack cleanup. Matching a function name or declaring an import resolved does not implement that contract. The original EXE selects an NT/Windows 7 compatibility value through the integration; upstream Win98 behavior must remain separately tested where it differs.

| Contract / application dependency | Implementation and diagnosis | Reference / regression |
| --- | --- | --- |
| Startup path, working directory and string operations | Shared Win32 host handlers and `src/09an-theseus-platform.wat`; wrong path/case/Unicode conversion can look like an absent archive | `inspect_windows_paths.py`, `inspect_windows_strings.py`, path/string JSON references; `test_runtime.cjs` |
| Activation contexts and original DLL startup | `src/09ap-theseus-actctx.wat`, DLL loader; track stack ownership and cleanup after failure | `inspect_activation_contexts.py`; `test_runtime.cjs` |
| Original FMOD/CRT pointer cookies, FLS and callbacks | `src/09an-theseus-platform.wat`, `src/09ao-theseus-fls.wat`; preserve actual x86 callback frame and fence semantics | `test_runtime.cjs`, native reference helpers recorded in history |
| Original module enumeration / process queries | Loaded PE registry and host process contracts; returned base/path must identify the actual mapped image | `inspect_process_modules.py`, `inspect_processes.py`, associated JSON references; `test_processes.cjs` |
| Cryptographic provider lifecycle and random bytes | `src/09aq-crypto.wat`, Web Crypto host entropy; ephemeral provider ownership shared across workers | `inspect_crypto.py` plus x86 helper; `test_crypto.cjs` |
| Window geometry / monitor identity / input | USER handlers, renderer and host-window; original DXUT reuses native-style dimensions | Reset/monitor references; `test_d3d9_composition.cjs`, `test_input_web.py` |
| Socket events / waits | Actual shared kernel events and Winsock transitions; do not fabricate signaled completion | [Networking contracts](network.md) and their native regressions |

All paths above are relative to `theseus/browser/` for integration helpers/tests and `theseus/tools/wine-assembly/` for `src/` files. The [generated index](generated/INDEX.md) supplies clickable primary source locations and hashes for the main subsystems. The reference inventory is extracted directly from the actual JSON files.

## Native reference discipline

Read the existing helper before running it. Some tools create temporary local COM/API objects, loopback sockets or reference windows. Preserve OS version, x86/x64 architecture, DLL source hash, inputs, output/error values and cleanup. Never invoke original game entry points as a substitute for browser verification. Data-only PE mappings inspect exports/resources without running the mapped module's initializer.

When local Windows behavior and documentation disagree, record both and reproduce the observed case before changing code. Reset parameter writeback is one such example. A local modern Windows measurement cannot establish every historical Windows variant. Retain unresolved comparisons, such as the known font corpus mismatches and the older golden fixture that also differed on its control.

Use existing bounded references to maintain established contracts. The standing order closes open-ended foundational discovery; a new architecture or broad unrelated research program needs renewed authorization. Fixing a demonstrated ABI, ownership or scheduling error remains ordinary maintenance.
