# Historical README snapshot

Preserved for continuity on 2026-10-11. Scope and status statements below are historical; the current README and corrected wiki closeout govern.

# JoySword Theseus

**Frozen closeout, 2026-10-11:** work is closed; knowledge edition 1.4.0 preserves current findings and explicit integration gaps. Read the [closeout](../../wiki/closeout.md). Client acceptance remains BLOCKED. Build, preparation and environment-changing instructions below apply only after work is reopened.

From 2026-10-09, this project's internal identity is **BROCWIN** and the browser client is **HEAV3NS-COMBO**. The living [maintainer wiki](../../wiki/README.md) is the entry point for architecture, implementation/test locations, build and recovery, evidence, compatibility and the maintenance queue. Earlier Theseus records remain under their original names. Operation Last Light keeps the integrated game in active maintenance; a documentation edition is not port completion.

The active objective is the full browser port described in [browser/README.md](../../browser/README.md). The browser application executes the original client code in WebAssembly, with its original libraries and resource archives. It is under construction; native combat evidence below does not verify browser gameplay. The older combat-only replacement gates below are historical and do not narrow the full-game mandate.

This directory records the progressive reconstruction of the copied JoySword implementation. The inherited native client, server binaries, Lua combat scripts, and KOM assets remain the baseline. Actual native combat is verified: movement, jump, four-hit combos, dealing/taking damage, enemy defeat, loot and experience. See `baseline.json` and the screenshots under `reports/`. This is a working checkpoint, not a claim that modernization is finished.

The source is commit `4c39249b939d79c229e1fd4f63dfd462a90f9060` of CardSorting/JoySwordOnline. This workspace was physically copied from `C:\Users\media\Downloads\JoySwordOffline - Copy` to `C:\Users\media\Downloads\JoySword-Theseus`. Its `data` junction points to its own `client/data`. Dependency caches, generated build/installers, private environment files, stale process records, and log files were excluded. Git history was copied without shared objects.

The recovery database is a physical copy of the inactive `joyswordoffline-copy_mssql-data` volume, mounted read-only during copying. The independent destination is `joyswordtheseus-baseline-sql`, exposed by `joysword-theseus-sql` only on `127.0.0.1:15433`. The inherited root Docker Compose file and general start/stop scripts are not isolated: do not run those until reviewed. Use Theseus-specific commands.

## Asset recovery

Run `python theseus/assets.py --extract` from this workspace. It uses the inherited KOM checksum and Lua XOR code, validates compression and sizes, and catalogs each payload's SHA-256, archive offset, original metadata, and category. Recovered files keep archive namespaces to avoid collisions. Original bytes remain available; recognized XOR Lua bytecode is also saved separately. `theseus/asset-catalog.json` maps assets back to the packed originals for later reskinning.

Run `python theseus/test_assets.py` for corruption and Windows path traversal checks. Generated catalogs and recovered assets are local build artifacts.

## Replacement gates

1. Prove the isolated native client can log in, load a combat arena, move, jump, attack, land a combo, take damage, and finish/restart a fight. Record the actual result and evidence.
2. Preserve the preceding binary, script and asset hashes before each significant replacement.
3. Replace the launch and account flow using the existing game. Verify the same combat sequence after each change.
4. Remove online services, economy and world dependencies only once runtime evidence shows combat no longer needs them.
5. Mark the reconstruction complete only when the standalone experience runs without the original installation or its services.
