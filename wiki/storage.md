# Filesystem, archives and persistence

[Change 0013](changes/0013-runtime-startup-cache.md) adds bounded digest-validated runtime-resource and pure-artifact caches. Original payloads remain read-only; guest state is excluded. Prepared audio uses the existing sized lazy/range provider, preserving file paths/lengths/content. Cache storage failure remains a miss. Cancellation and range transport are unchanged. See [performance](performance.md) for measured loading/memory effects and cold/warm limits.

[Wiki home](README.md) · [Implementation and tests](generated/INDEX.md#storage)

`prepare.py` builds an explicit file manifest with source hashes, guest paths and loading modes. Original DLLs and required files are mounted before entry; KOM archives are fetched lazily through HTTP ranges. `serve.py` serves only approved routes, enforces loopback/origin checks and emits cross-origin isolation headers required by shared-memory execution. This is not a workspace directory export.

The original launcher starts in `client/data`; the browser mounts its equivalent at `c:\joysword` and sets that working directory before running the original EXE. Earlier startup failed because the working directory was wrong. Font registration, `GameHelper.ini` reads, shader compilation and map/resource loads depend on these names and original bytes.

`assets.py` reuses inherited KOM checksum/Lua XOR logic, validates offsets, compression, sizes and traversal, and catalogs payload hashes and namespaces. Recovery outputs do not replace live game algorithms. The inherited catalog contains 88,829 entries from 145 archives; that is inherited recovery, not work newly claimed by BROCWIN. Keep original packed files alongside extracted evidence.

## What persists

Current [133104 read-only observations](../reports/browser/20261011T133104Z/database-observations.json) remain level 12, EXP 69,567, ED 2,237 and LastPosition 0 before launch and after original event-676 termination. No winning reward/result is reached, and no matching native logout-statistics block is available. These unchanged rows are not proof that a completed gameplay cycle persisted; the current acceptance attempt is blocked earlier.

Server-side character/progression data persists in the isolated original SQL backend through normal game actions. `053844`'s visible 9,190 EXP / 157 ED reward matched sampled balances and level 9→10 after closure. `064427` retained +2,726 EXP / +53 ED, but its reward panel amount was not visually established. Immediate post-defeat rows can precede persistence; distinguish them from later town/closure observations.

The dependency has opt-in mutable VFS persistence, but this integration does not configure a persisted-file list in `main.js`. Do not promise browser-local settings or save files survive reload. A working backend save does not prove browser VFS persistence, offline operation or migration between installations.

## Reproduce, recover, repair

Use `test_server.py` for explicit routes/ranges/isolation, `test_assets.py` for archive corruption/traversal, and the path references for Windows naming behavior. Verify input hashes before using `prepare.py --runtime-only`; use full preparation after game/config input changes. Diagnose missing file → guest path/case/working directory → manifest route → response/range → archive entry, retaining original bytes.

`isolate.py` guards the dedicated container, volume and database scope. `checkpoint.py` verifies inherited source identity; `snapshot.py` makes native checkpoints and database backups and therefore has side effects. See the [recovery runbook](build-recovery.md) before using them. `profile.py` is a provisioner, not a module to import during diagnostics. Never print/import credentials as a shortcut or issue diagnostic SQL writes. Do not use inherited root start/stop scripts against this isolated installation.
