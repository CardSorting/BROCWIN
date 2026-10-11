# Build and recovery runbook

**Frozen closeout, 2026-10-11:** the current work session is closed at the user's direction. See [closeout](closeout.md) for the prepared/source distinction, source-only reservation fix and unresolved validation. Engineering and environment changes require the user to reopen work; next actions below are handoff instructions.

For the 2026-10-11 runtime mandate, preserve the already visible session. Run [startup comparisons](changes/0013-runtime-startup-cache.md) on a separate port/profile and sequentially. Start an updated host on an unused local port if the existing host has an older route table; do not restart the original session to install caches. Fixed cache-policy overrides support replay; the [performance report](performance.md) retains exact conditions.

[Wiki home](README.md) · [Validation](validation.md) · [Maintenance contract](maintenance.md)

Commands below run from the **JoySword-Theseus repository root** in PowerShell unless a different directory is stated. Current measured versions and hashes come from [generated identity](generated/identity.json), the dependency lock and retained reports, not a manually maintained installation matrix. Local prerequisites include Python, Node.js, Git/Bash, the existing browser, original game payload, installed platform DLL inputs and the isolated native backend. Full bootstrap may download pinned existing dependencies; it does not authorize paid services or new infrastructure.

## Inspect an existing checkout

```powershell
git status --short
python theseus/browser/bootstrap.py --check
python theseus/knowledge.py --check
python theseus/runtime.py status --json
```

These do not provision accounts or start the Windows game. Status inspects owned process identities/listeners without opening non-protocol game connections. `knowledge.py --check` detects stale generated facts, missing linked sources and changed preserved evidence. Missing ignored payloads/reports are recovery requirements, not reasons to discard their records.

## Build a runtime change

Read the dependency's `AGENTS.md` / `CLAUDE.md`, read the recent append-only message board, establish ownership, and check no capture freeze is active. Never reset another contributor's work.

```powershell
Push-Location theseus/tools/wine-assembly
& 'C:/Program Files/Git/bin/bash.exe' tools/build.sh
Pop-Location
python theseus/browser/prepare.py --runtime-only
python theseus/browser/bootstrap.py --check
```

Check each exit code. The build uses the vendored WATX compiler and `src/main.watx`; **do not invoke wat2wasm**. Preparation retains unchanged game-input hashes and updates runtime scripts, modules, platform adapters and source patch. If original files or served configs changed, run full `python theseus/browser/prepare.py` instead. Preparation is a mutation and must not run during a capture freeze.

The patch includes tracked modifications and local `src/`, `lib/`, `test/` source additions. The first BROCWIN maintenance pass corrected omission of six untracked regression/helper files. A successful local test alone is insufficient if its source cannot be restored from the handoff.

## Restore the pinned dependency

In a separate, intentionally selected clean workspace with the preserved integration and original local inputs:

```powershell
python theseus/browser/bootstrap.py
```

Bootstrap checks the exact pin, applies the preserved patch, installs pinned tools locally, builds and runs its selected integration regressions, then prepares game inputs. It refuses mismatched/conflicting existing checkouts rather than replacing them. Do not copy private `.env` content into logs or publish local Microsoft/game binaries. A test fixture absent from the copied installation is explicitly unavailable; do not mark that test passed.

## Start the integrated application

For the current acceptance replay, keep the existing native services and SQL running with their existing configuration. Verify their retained process identities, then start only the browser host:

```powershell
python theseus/runtime.py status --json
python theseus/browser/serve.py --port 8766
```

Open `http://127.0.0.1:8766/` and use **Start client**. The browser page is HEAV3NS-COMBO. Use the existing local account and character; the [current acceptance report](acceptance-session.md) records the tested route, exact build identities and blocked outcome. If port 8766 is already serving this matching build, use that instance. The host command runs in the foreground; if automation starts a helper process, keep its window hidden and retain its PID/log. Do not launch `runtime.py client`/`play` for browser acceptance; those are native-client paths. Do not run the inherited general root launch scripts or provisioning helpers against this isolated database.

For a single visible Edge window that stays open for human observation, run `python theseus/browser/capture.py --headed --keep-open` against the existing host. This mode starts the client without installing capture probes, ignores the capture duration, and waits until the window closes. It does not script gameplay. Its report retains `observation.json` and one image after the first presentation. Closing the window ends this observation helper; a browser disconnect also ends it. Ordinary `--headed` captures retain their normal duration and diagnostic capture behavior.

## Recover without losing evidence

1. Stop the specific capture/client cleanly, retain final state, then release its freeze. Preserve its existing report before attempting another run.
2. Compare dependency pin, source patch and generated manifest. Recover missing runtime files from the matching snapshot or clean bootstrap; do not combine a new Wasm with old scripts/manifest.
3. Check original input hashes against the manifest and native checkpoint. Keep files in their original namespaces. Reprepare after legitimate input changes.
4. Check owned native service status and the dedicated container identity. Use the Theseus-specific runtime commands only for the intended stack. Never infer a stale PID belongs to this workspace.
5. Database rollback is a destructive state change. Select the exact preserved backup and obtain authority if rollback was not already requested. `snapshot.py NAME` creates new backups/checkpoints; it is not a read-only diagnosis command. Routine diagnostics use guarded **read-only** SQL.

The wiki release inventory is reproducible with `python theseus/knowledge.py --seal-release VERSION` after freshness checks. It refuses to overwrite an existing release. Git remains the normal source history; a sealed local edition also records exact content hashes in this currently uncommitted workspace. Original large evidence stays in local reports and checkpoints.
