# Troubleshooting by observed failure

[Wiki home](README.md) · [Issues](issues.md) · [Validation](validation.md)

| Symptom | First evidence to retain | Diagnostic path |
| --- | --- | --- |
| Ready page never enables Start | Page/HTTP errors, module/script hashes, crossOriginIsolated | Manifest routes and headers → original/local inputs → dependency build; run `test_server.py` |
| Blank output during startup | Current guest phase/EIP, D3D errors, memory commitment, actual screenshot | File/working directory → DLL init → resource allocation → shader/Reset; blank image alone does not identify renderer failure |
| Wasm trap / startup exit | Executing worker ID, EIP/registers/stack, halt/yield reason, last error | Exact source/module → unsupported API/ABI or loader failure; never return fake success |
| World load freezes | Live thread state, pending DLL callback/lock, TLS vector, resource queue | Thread attach scheduling → module TLS → resource ownership; retained exited stack is not a blocked live worker |
| First return loses terrain | Before/after `.Y` registry/readiness, worker lifetime, draws | Resource loading/TLS before shaders; exclude changed vector entries |
| No server response dialog | Original event ID, request timing, pending record, receive/readable state, guest progress | Follow BRC-001; do not count receive-head growth as queued bytes |
| Skill fails / stuck key | DOM down/up timestamps, side identity, focus, original binding, animation/MP/cooldown | Physical state → Wasm poll/message timeline → original skill conditions; compare standalone modifier test |
| White/distorted frame | Complete adjacent reviewed frames and original draw/shader/constant bytes | Object lifetime → transfer/RPC ordering → transform/shader → composition; no isolated-render acceptance claim |
| Bad text | Font file identity, face/size/mode, glyph/extent and bitmap sample | Registration → NT cell/advance → hint/cache → raster; keep known corpus mismatches |
| Silence | Trusted gesture, AudioContext state, FMOD device, sample changes | DirectSound callback/identity → buffers/worker ownership → WebAudio; nonzero PCM is not audible verification |
| Progress not saved | Read-only before/defeat/town/closure rows and original UI | Original save/transition timing → native server logs; do not modify rows to create a passing result |

The maintenance workflow is to reproduce an existing failure, preserve a control, fix a measured contract, run focused tests, and replay the original path. Use [build recovery](build-recovery.md) for environment faults. Restore a matched candidate in a separate selected workspace if comparison is needed; avoid deleting or rolling back the active dirty worktree.

Failed approaches already ruled out: more Wasm memory alone did not solve the stale callback scan; the earlier shader constant-span repair did not fix character preview displacement; a synchronous DLL attach runner cannot accommodate a real wait; aliased static TLS indices cannot provide independent per-module storage; right modifiers cannot be represented by duplicating one generic physical state. Each finding remains linked to its original record via the source/evidence index and archived research notes.
