# Original-client session acceptance

## Final tested build: 145806 - BLOCKED

**The client is not complete or reliably playable.** [Replay 145806](../reports/browser/20261011T145806Z/review.json) integrates [change 0012](changes/0012-session-send-serialization.md), which serializes original packet construction and sending using the existing socket lock. Login, character selection, town, Tree of El, two skills, first-area clear, the previously failing gate, area-two combat, the original failed-attempt reward interface and automatic town return execute in one browser session. **Independent revival still fails. Native totals are one attempt, zero wins and zero stones used.** No historical victory or native-reference revival counts toward this build.

| Acceptance step | Current-build result | Reviewed request images |
| --- | --- | --- |
| 1. Launch | Pass: original compiled X2, frozen integrated build. | 000-008 |
| 2. Login | Pass: existing account and original Genesis/channel flow. | 009-014 |
| 3. Character | Pass: existing level-12 TheseusOne enters Ruben. | 015-019 |
| 4. Town | Pass with limitations: movement, System/Graphics/Dungeon menus. Dungeon selector needed three clicks. | 019-025 |
| 5. Dungeon | Pass: original Tree of El / Normal entry, first-area gate and area-two loading/gameplay. | 025-028, 039-043 |
| 6. Combat | Partial: Z damage/combos, repeated Flame Geyser MP/cooldown/cut-in/effects, distinct Roll cooldown/displacement, movement/jump and enemy removal. Slow cadence, short-input/focus and effect fidelity remain unaccepted. | 029-050 |
| 7. Victory | Not verified: first-area clear only; failed revival in area two, native wins 0. | 039, 051-056 |
| 8. Rewards | Partial: original failed-attempt reward/item interface, native statistics and SQL observed. No winning reward or verified item persistence. | 057 |
| 9. Revival | **Failed:** six ordinary Z pulses; nine stones unchanged, native stones used 0. | 051-056 |
| 10. Return | Pass: automatic Ruben return, movement and System menu in the same client; no restart/manual recovery. | 058-060 and final browser image |
| 11. Repeat | Not verified: no first winning cycle or second winning cycle. | Same-session record |

The replay finishes intentionally in responsive Ruben after **2, 576.688 seconds / 4, 907 presentations**. [All 61 requested images and final browser PNG](../reports/browser/20261011T145806Z/reviewed-images-final.json) were individually reviewed. Other timed PNGs are unreviewed; totals are not FPS benchmarks. [Source audit](../reports/browser/20261011T145806Z/source-audit.json): **248 matching identities**, copied before launch, with no edits/build/preparation during capture. No profiler or breakpoints were armed. Read-only memory/header/native observations and screenshots still impose overhead.

### Reproducible build and exact launch

| Artifact | SHA-256 / pin |
| --- | --- |
| Original `client/data/x2.exe` | `fe84cc1a95fc38b6d0d441997298828b133c7645e10a879978903e504d52d2f1` |
| Wine-Assembly commit | `d7854bc6c6bd0319ca33b5f31a465602e2ce0686` |
| Main Wasm | `c38c94850b55c6adc2981f4a277d80a3732f5b4f8c275d246949c92fe810eb3d` |
| Compatibility Wasm | `c2380511aeb9632886c0ff2790276dbfdf6c1c89193b20174dd5d0acaaae8ef8` |
| Runtime patch | `00924af439b7248b11b70c394b2ca9f57844f0702592cae0962023496b6e206b` |

The [frozen manifest](../reports/browser/20261011T145806Z/frozen-manifest.json), [patch](../reports/browser/20261011T145806Z/runtime.patch), both compiled modules and source copies are retained together. The [runbook](build-recovery.md) covers restoration into a separate checkout without resetting existing edits. With the existing original local payload and unchanged native services available, run from the repository root in PowerShell and check every exit code:

```powershell
Push-Location theseus/tools/wine-assembly
& 'C:/Program Files/Git/bin/bash.exe' tools/build.sh
Pop-Location
python theseus/browser/prepare.py --runtime-only
python theseus/browser/bootstrap.py --check
python theseus/runtime.py status --json
python theseus/browser/serve.py --port 8766
```

Open `http://127.0.0.1:8766/`, select **Start client**, log in with the existing local account, select **Genesis**, its available channel, then **TheseusOne > Start Game**. In Ruben use **Escape > Options** and select **Unit Low / Background Low**; Texture/Effect were already Low, resolution 800x600. Close Options. Choose **Dungeon > Tree of El > Normal > Start with current members**. Arrows move/jump, **Z** attacks, **A** activates Flame Geyser and **S** activates Roll. Clear area one, attack its barrier and move through. An existing matching host on 8766 may be reused. Long loading and long/repeated input holds remain limitations; these commands reproduce a blocked build.

### Exact blocker and attempted corrections

[Validated observations](../reports/browser/20261011T145806Z/untraced-revival-result.json) begin with death state 7 and policy 0 at 15:37:24.043843 UTC. Final-dead state 4 is first sampled **15.567354 seconds later**, already with policy 1, initialization 1, countdown 9.985714 and nine stones. Three Z pulses were sent during sampled death animation and three after final-dead state; none revives. The controller retires at request 80, whose failed identity check is excluded. Original results and automatic return follow. [Failure record](../reports/browser/20261011T145806Z/revival-failure.json) contains the exact encounter, helper provenance, attempts and limits.

The historical [native reference](../reports/native-revival-20261011T120600Z/review.json) reaches initialized continue in 4.670260 sampled seconds and revives through ordinary Z. Original [CenterServer code](../reports/native-revival-20261011T120600Z/original-death-timer.json) arms a 15-second allowance and reaches [EndPlay](../reports/native-revival-20261011T120600Z/timer-target-addendum.json) on expiration. This replay did not sample its live timer origin/expiry; the observation interval is not an exact server duration or controlled native/browser speed comparison.

Earlier Worker clock/SSE inheritance, allocator locality and draw-copy corrections remain installed. Current original Low graphics settings still do not make revival succeed. The new send wrapper closes the demonstrated unsynchronized construction path, with **407 increasing outgoing game serials, zero parser anomalies/errors and no original process exit** through the gate, death/result and return. [Live wrapper read-back](../reports/browser/20261011T145806Z/installed-wrapper.json) matches the candidate. The earlier duplicate's exact native authentication verdict was never captured; this route does not close other historical intermittent timeouts.

**Smallest unresolved dependency:** timely execution of the original death/continue update and input before authoritative encounter closure. The remaining BROCWIN execution/scheduling cost has not been isolated. Timer, eligibility, end-event, authentication or server bypasses would not satisfy acceptance. Work stops at this reproducibly blocked result; broader compatibility work is deferred.

### Server evidence, regressions and remaining differences

[Native logout statistics](../reports/browser/20261011T145806Z/native-log-observation.json) confirm one single-player attempt, zero wins, zero stones and zero dungeon ED. [SQL before/after](../reports/browser/20261011T145806Z/database-observations-final.json) remains UnitUID 20098, level 12, EXP 69, 567, ED 2, 237 and LastPosition 0. The zero-result screen is not a victory. [Native state observations](../reports/browser/20261011T145806Z/server-state-observations.json) retain town 7, room 8 and returned town 7; [five services](../reports/browser/20261011T145806Z/native-runtime-status.json) retain their PIDs and readiness. [Seven original/reference files](../reports/browser/20261011T145806Z/original-inputs-after.json) match their starting hashes. Native server/SQL implementations and schemas are unchanged; diagnostic SQL is SELECT-only.

[Seven affected checks pass](../reports/serial-ownership-20261011T142300Z/candidate-validation.json): actual installed-wrapper/original-PE fingerprints and all-or-nothing guards; contended guest queue/ABI/null/early-return/recursive-lock/SEH and real RtlUnwind checks; existing War Wind and Baldur profile checks; critical-section threading; unwind handlers; canonical build; integrated runtime. The wrapper test uses a bounded body fixture, not replacement gameplay. [Integration validation](../reports/serial-ownership-20261011T142300Z/candidate-integration-validation.json) preserves the sealed review and unchanged test-log hashes. No extra component tests are represented as gameplay acceptance.

Blocking limitations remain combat cadence/input/effect fidelity, failed revival and unverified victory/winning rewards/two cycles. Nonblocking differences observed on this route are purple background regions and damaged small HUD/dialog text that did not prevent navigation. Browser-local settings persistence remains unconfigured; audible fidelity is unverified. These are deferred, not claimed fixed. The capture retains 54 original nonfatal Lua throws. No cosmetic work outside the route, new backend or server changes were made.

Provenance: original game/fork developers, Wine-Assembly/WATX/platform contributors and earlier maintainers retain attribution. Codex /root used the existing build, Edge/Playwright, Node, Python, PE/Capstone and read-only native/SQL tools; no delegated agents. Earlier sealed evidence below remains immutable and belongs to its own build.

## Historical tested build: 133104 - BLOCKED

**The browser client is not complete or reliably playable.** [Replay 133104](../reports/browser/20261011T133104Z/review.json) tests the integrated [draw snapshot correction](changes/0011-draw-snapshot-copy.md) against the unchanged local native services. It reaches original login, the existing character, Ruben, Tree of El, two distinct skills and first-area clear. **The original client terminates at that area's exit gate with event 676.** Two outgoing packets carry the same serial immediately before termination. No historical victory, revival or return is counted as current-build acceptance.

| Acceptance step | Result on this final build | Reviewed request images |
| --- | --- | --- |
| 1. Launch | Pass: original compiled X2 on the preserved integrated browser build. | 000-003 |
| 2. Login | Pass: existing account, original Genesis and channel flow. | 004-008 |
| 3. Character | Pass: existing level-12 TheseusOne enters Ruben. | 009-012 |
| 4. Town | Pass for this route, with limitations: rendering, movement and original Dungeon menu; selector needed three clicks. | 012-017 |
| 5. Dungeon | Pass: Tree of El / Normal through Start with current members. | 017-019 |
| 6. Combat | Partial: Z sword damage/combos, repeated Flame Geyser activation with MP/cooldown/damage, distinct Roll, all first-area enemies defeated. Low cadence, input/focus and effect fidelity remain unresolved. | 020-037 |
| 7. Victory | **Blocked:** first-area clear only; original termination before the next area. | 033-037; final browser image |
| 8. Rewards | Not reached: no result/reward UI or winning reward. Post-exit SQL unchanged. | No reward image |
| 9. Revival | Not reached on this build: character alive at termination. Prior browser failure and successful native reference remain historical. | No current death/continue image |
| 10. Return | **Failed:** process terminates at the first-area gate; no town return. | Final browser image |
| 11. Repeat | Not reached: no completed first winning cycle or second winning cycle. | Same-session record |

The capture ends through original `TerminateProcess(-1)` after **1,759.953 seconds / 4,868 presentations**, not through an intentional stop. [All 38 requested PNGs and the final browser PNG](../reports/browser/20261011T133104Z/reviewed-images-final.json) were individually reviewed. Other automatic images are unreviewed. Request 46's control wait expired after the original exit and was not resubmitted; it is not a demonstrated runtime hang. [The source audit](../reports/browser/20261011T133104Z/source-audit.json) matches 245 source/integration files, both modules and the patch: **248 identities**, physically copied before launch. No runtime/source edit, rebuild or preparation occurred during the capture.

### Reproducible build and exact launch

| Artifact | SHA-256 / pin |
| --- | --- |
| Original `client/data/x2.exe` | `fe84cc1a95fc38b6d0d441997298828b133c7645e10a879978903e504d52d2f1` |
| Wine-Assembly commit | `d7854bc6c6bd0319ca33b5f31a465602e2ce0686` |
| Main Wasm | `c38c94850b55c6adc2981f4a277d80a3732f5b4f8c275d246949c92fe810eb3d` |
| Compatibility Wasm | `c2380511aeb9632886c0ff2790276dbfdf6c1c89193b20174dd5d0acaaae8ef8` |
| Runtime patch | `66e4c7ccc9456315ea5e9ffc8c35fdd52fa794c4a17a038cd1c158851e882e5f` |

The [frozen manifest](../reports/browser/20261011T133104Z/frozen-manifest.json), [runtime patch](../reports/browser/20261011T133104Z/runtime.patch), source copies and both compiled modules accompany the capture. Restore the dependency pin plus this patch using the [build/recovery runbook](build-recovery.md); do not reset unrelated workspace edits. With the existing original local payload and native services available, run these commands from the repository root in PowerShell, checking each exit code:

```powershell
Push-Location theseus/tools/wine-assembly
& 'C:/Program Files/Git/bin/bash.exe' tools/build.sh
Pop-Location
python theseus/browser/prepare.py --runtime-only
python theseus/browser/bootstrap.py --check
python theseus/runtime.py status --json
python theseus/browser/serve.py --port 8766
```

Open `http://127.0.0.1:8766/`, select **Start client**, authenticate with the existing local account, choose **Genesis**, its available channel, and **TheseusOne → Start Game**. From Ruben choose **Dungeon → Tree of El → Normal → Start with current members**. Use arrows for movement/jump, **Z** for basic sword attacks, **A** for Flame Geyser and **S** for Roll. Defeat all enemies, approach the first-area gate, attack it with Z/X, then move through it. The latest run terminates here; the exact occurrence is intermittent. Long startup/loading and mouse holds remain limitations. This launches a reproducible blocked build, not a completed port. An already-running matching host on 8766 can be reused.

### Exact failure, diagnosis and attempted correction

[The exit record](../reports/browser/20261011T133104Z/exit-failure.json) retains the original failure-time stack with event **676 / EGS_TRAFFIC_ATTACKER_NOT** and code **-1**, at **2026-10-11 14:00:27.602 UTC**. The same original EXE's preserved dispatch/reference identifies `KERNEL32.TerminateProcess`; the generic host label alone is not the basis for this conclusion.

The accepted TCP-9300 header observer sees packet 241 (74 bytes) and packet 242 (58 bytes) both carrying **serial 241**, 1.545 ms apart. The second is **26.435 ms before the process-exit observation**. The preceding serials increase; no parser error is recorded. [The observer regression](../reports/draw-snapshot-copy-20261011T132600Z/capture-observer.json) passes fragmentation/coalescing, failed-send exclusion, exact argument/byte preservation and bounds. Closure follows with WebSocket code 1005 and local cause `requested`; these facts do not identify a transport rejection.

[Original server evidence](../reports/traffic-event-20261011T053300Z/original-notification-boundary.json) maps packet-authentication failure above the configured threshold to reason 34/event 676, and identifies the enabled increasing-serial check. This is not evidence of a rate limit. [New bounded original-client inspection](../reports/serial-duplicate-20261011T140500Z/diagnosis.json) finds separate counter read/increment instructions and a context-lookup lock released before those operations. The actual generating callers, their enclosing synchronization and the native authentication verdict were not captured. A construction race is a hypothesis; memory or transport ownership causes are not excluded.

The snapshot-copy correction reduces a measured page-side cost and preserves its contracts. The real town profile records 20 presentations/15.29086 seconds and 5.00397% page-copy self time, versus historical 7.70894% in a separate window. It does not fix the termination or establish playable cadence. Profiling ended before dungeon entry; combat had no profiler, breakpoints or guest gameplay writes. Existing shared-wire and allocator repairs were not reopened without evidence of a failed contract.

**Smallest unresolved dependency:** identify the originating guest thread/caller and security-context counter for the two duplicated packets, then correct the demonstrated client runtime ownership/synchronization defect. Rewriting serials in the relay, suppressing event 676 or changing native authentication would hide the failure. Earlier death/continue timing remains unresolved and must be retested after the earlier fatal failure is fixed.

### Server observations, regressions and remaining differences

[Final identity/log verification](../reports/draw-snapshot-copy-20261011T132600Z/final-validation.json) links the completed blocked replay to its earlier component validation, preserving the pre-replay record unchanged.

[Read-only native state](../reports/browser/20261011T133104Z/server-state-observations.json) observes the identified account in town state 7. [All five native services](../reports/browser/20261011T133104Z/native-runtime-status.json) remain ready under the same retained PIDs. [Seven original/reference identities](../reports/browser/20261011T133104Z/original-inputs-after.json) remain unchanged. [SQL observations](../reports/browser/20261011T133104Z/database-observations.json) before launch and after exit both show UnitUID 20098, level 12, EXP 69,567, ED 2,237 and LastPosition 0. [The native log slice](../reports/browser/20261011T133104Z/native-log-observation.json) has no matching logout-statistics block; no native win, attempt or stone totals are inferred. Existing native logging/database errors are retained unchanged.

[Regression records](../reports/draw-snapshot-copy-20261011T132600Z/validation.json) preserve exact commands, raw logs, controls and hashes: neutral command snapshots, D3D shared rendering, render lifetime, real render Worker protocol, runtime, 208 native StretchRect HRESULT/pixel comparisons, canonical build, prepare and bootstrap pass. Two guest-render/park-batch checks remain unavailable because `test/binaries/calc.exe` is missing. The original shared-render mock failed on both control and candidate before its missing single-backbuffer field was initialized; the correction does not relax an assertion.

Blocking differences remain termination, low cadence, combat/input/effect reliability, unverified victory/rewards, historical failed revival and absence of two winning cycles. Small HUD/menu text damage did not prevent this route's navigation. Deferred nonblocking differences for this route are browser-local settings persistence, audible fidelity and unrelated maps/menus; they are not claimed fixed. The capture also retains 54 original nonfatal Lua throw observations. No cosmetic work outside the route or server/schema changes were made.

Provenance: original game/fork developers, Wine-Assembly/WATX/platform contributors and earlier maintainers retain attribution. Codex /root used the existing build, Edge/Playwright/CDP, Node, Python, PE/Capstone and guarded read-only native/SQL tools. No delegated agents or new backend were used. Earlier sealed evidence below remains immutable and applies only to its recorded builds.

## Historical tested build: 123040 - BLOCKED

**The requested playable browser session is incomplete.** [Replay 123040](../reports/browser/20261011T123040Z/review.json) tests the integrated arena-locality correction against the unchanged original native servers. It reaches login, the existing character, town, Forest Ruins, two distinct skills, the original failure result and automatic town return. **Independent revival fails; native totals are one attempt, zero wins and zero stones used.** No historical victory or native-reference revival is counted as current browser acceptance.

| Acceptance step | Result on this final build | Reviewed request images |
| --- | --- | --- |
| 1. Launch | Pass: original compiled executable on the preserved browser build. | 000-006 |
| 2. Login | Pass: existing account authenticates through original Genesis/channel selection. | 006-013 |
| 3. Character | Pass: existing level-12 TheseusOne enters Ruben. | 014-018 |
| 4. Town | Pass for the route: terrain, character, movement and Dungeon menu. Small text and long mouse holds remain limitations. | 018-024 |
| 5. Dungeon | Pass: Forest Ruins / Normal through Start with current members. | 023-028 |
| 6. Combat | Partial: movement/jump, basic Z sword/combo, Flame Geyser with enemy removal and cooldown, distinct Roll animation/cooldown. Low rate, input/focus reliability and effect fidelity prevent full acceptance. | 029-036 |
| 7. Victory | Not verified: the attempt fails; original FAILURE result and native win count zero. | 043 |
| 8. Rewards | Partial: original failure/result screen and persisted outcomes verified. No winning reward. | 043; server/SQL below |
| 9. Revival | **Fail:** six ordinary Z pulses; final dead state has continue disabled, no initialization/countdown, nine stones unchanged. | 037-042 |
| 10. Return | Pass: original Ruben return, movement and native town state; no browser restart or manual recovery. | 045-046 |
| 11. Repeat | **Not verified:** blocked at revival, no completed winning cycle or second winning cycle. Incidental field travel is not counted. | Same-session record |

The replay ends intentionally in rendered Ruben after **2,471.734 seconds / 9,559 presentations**. [All 52 requested images, three selected timed images and the final browser image](../reports/browser/20261011T123040Z/reviewed-images.json) were individually reviewed: 56 total. Other automatic images are unreviewed. Movement after the first return also entered adjacent Lake Noahs and returned through its original portal (048-051). [The source audit](../reports/browser/20261011T123040Z/source-audit.json) matches **245 source/integration files, both Wasm modules and the patch: 248 identities**. No source edits, rebuild or preparation occurred during capture.

### Reproducible build and exact launch

| Artifact | SHA-256 / pin |
| --- | --- |
| Original `client/data/x2.exe` | `fe84cc1a95fc38b6d0d441997298828b133c7645e10a879978903e504d52d2f1` |
| Wine-Assembly commit | `d7854bc6c6bd0319ca33b5f31a465602e2ce0686` |
| Main Wasm | `c38c94850b55c6adc2981f4a277d80a3732f5b4f8c275d246949c92fe810eb3d` |
| Compatibility Wasm | `c2380511aeb9632886c0ff2790276dbfdf6c1c89193b20174dd5d0acaaae8ef8` |
| Runtime patch | `0b77ba556ef26837f40180143ff4771e2a0cbc511bb6173082848be1bee10e3d` |

The [frozen manifest](../reports/browser/20261011T123040Z/frozen-manifest.json), [patch](../reports/browser/20261011T123040Z/runtime.patch), copied source directories and compiled modules are retained with this review. [Validation](../reports/heap-free-locality-20261011T122400Z/validation.json) records exact successful build/check commands and log hashes. With the original local payload, pinned tools and existing native services available, run from the repository root in PowerShell, checking each exit code:

```powershell
Push-Location theseus/tools/wine-assembly
& 'C:/Program Files/Git/bin/bash.exe' tools/build.sh
Pop-Location
python theseus/browser/prepare.py --runtime-only
python theseus/browser/bootstrap.py --check
python theseus/runtime.py status --json
python theseus/browser/serve.py --port 8766
```

Open `http://127.0.0.1:8766/`, select **Start client**, authenticate with the existing local account, select **Genesis**, its available channel, then **TheseusOne → Start Game**. From Ruben choose **Dungeon → Forest Ruins → Normal → Start with current members**. Use arrows for movement/jump, Z for basic sword attacks, A for Flame Geyser and S for Roll. Startup/loading can take minutes; a moving guest PC alone is not completed loading. An existing matching host on 8766 can serve the prepared build. The [build/recovery runbook](build-recovery.md) covers pin/patch restoration without overwriting another checkout. This is a reproducible blocked build, not a completed port.

### Reproduced failure and attempted fixes

Walk/jump past the first crate to the Fairy Guardian/Phoru group, release movement and attacks, and let the original encounter reduce HP to zero. [The read-only observer](../reports/browser/20261011T123040Z/untraced-revival-result.json) sends six ordinary Z (900 ms)/up pulses through death and final-dead states. It validates the original actor/controller/metadata chain on **128 samples**; request 179 is excluded after the controller global becomes zero. No breakpoint, guest gameplay write or profiler runs during the encounter/death.

First sampled death state 7 has continue policy 0. Final dead state 4 arrives **16.144833 seconds later**, with policy 1, initialization 0, countdown 0 and all nine stones retained. The original failure/result and return follow. These are sampled bounds, not exact internal animation timestamps. [Diagnosis](../reports/browser/20261011T123040Z/revival-failure.json) separates this result from historical 105626, which initialized its countdown but still failed revival, and historical 092157's original event 201 caller trace.

The [unchanged native client reference](../reports/native-revival-20261011T120600Z/review.json) reaches initialized continue in **4.670260 sampled seconds**, policy 0, and revives through ordinary Z with stones 10→9. It is separate reference evidence at a different resolution/input cadence. Read-only [original CenterServer code](../reports/native-revival-20261011T120600Z/original-death-timer.json) arms a **15-second death allowance** and reaches [KDungeonRoom::EndPlay](../reports/native-revival-20261011T120600Z/timer-target-addendum.json) on expiry. The live server timer origin was not sampled here; an exact server expiry timestamp is not claimed. The native [persistence addendum](../reports/native-revival-20261011T120600Z/persistence-addendum.json) preserves the correction to its stale immediate-exit SELECT.

[Change 0008](changes/0008-worker-wall-clock.md) and [change 0009](changes/0009-sse-worker-policy.md) repair Worker clock accounting and existing SSE inheritance. [Change 0010](changes/0010-heap-arena-locality.md) adds one validated preceding arena hint. Its control reproduces 1,999,000 warm scanned records; the candidate needs zero. Thirteen candidate/regression/preparation checks and the canonical build pass, including eight existing heap suites and actual compiled runtime/Worker checks. [Real town profiles](../reports/browser/20261011T123040Z/town-profile-comparison.json) show heap-free sampled self time 21.04%→5.82%, but the candidate still presents only 19 frames/15.334 seconds. Separate windows and synthetic timings do not establish a controlled overall game-speed gain. **The integrated revival blocker persists.**

The smallest unresolved dependency is timely execution of the original death/continue update and input before authoritative encounter closure. The specific remaining BROCWIN execution/scheduling cost is not isolated. Changing gameplay timers, eligibility, end notifications or native server behavior would not satisfy this requirement. Successful revival, reliable combat, victory/rewards and two winning cycles remain required.

### Authoritative outcomes and remaining differences

[Native logout statistics](../reports/browser/20261011T123040Z/server-observation-exit.json) confirm one single-player attempt, zero wins, zero stones used and 20 dungeon ED. [Read-only SQL](../reports/browser/20261011T123040Z/database-observations.json) and those statistics agree on EXP **68,659→69,567 (+908)** and ED **2,217→2,237 (+20)**, level 12 and final LastPosition 0. The intermediate live SELECT preceded persistence. [Native FSM observations](../reports/browser/20261011T123040Z/server-state-observations.json) record room state 8 and returned field/town state 7. [All five native services remain ready under their retained PIDs](../reports/browser/20261011T123040Z/native-runtime-status.json). No native server implementation, schema or persistence implementation changed.

[Runtime observations](../reports/browser/20261011T123040Z/runtime-observations.json) retain 54 nonfatal Lua throws and no reproduced fatal crash/disconnect. That does not close historical intermittent timeout/authentication defects. Input/focus and combat effects remain acceptance issues. Small HUD/menu text defects did not prevent this route's navigation; browser-local settings persistence, audible fidelity and unrelated maps/menus remain deferred differences outside this same-session check. No cosmetic work outside the acceptance path was performed.

Provenance: original game/fork developers, Wine-Assembly/WATX/platform contributors and earlier maintenance retain attribution. Codex /root used existing build, Edge/Playwright/CDP, Node, Python, PE/Capstone and read-only native/SQL tools without delegated agents. Earlier sealed evidence below remains immutable and applies only to its identified builds.

## Historical tested build: 105626 — BLOCKED

**The required playable session is not complete.** [Replay 105626](../reports/browser/20261011T105626Z/review.json) tests the existing SSE policy and Worker inheritance repair against the unchanged native servers. One browser launches the original client, logs in, enters Forest Ruins and Tree of El, clears Tree's first area, and returns after both failed attempts. **Native totals: two attempts, zero wins and zero resurrection stones used.** Revival fails twice; no earlier victory is attributed to this build.

| Acceptance step | Result on final tested build | Reviewed request images |
| --- | --- | --- |
| 1. Launch | Pass: original compiled executable on the frozen browser build. | 000–009 |
| 2. Login | Pass: existing local account, original Genesis/channel flow. | 009–015 |
| 3. Character | Pass: existing level-12 TheseusOne enters Ruben. | 016–020 |
| 4. Town | Pass: rendering, ordinary movement, Dungeon menu/selection. Small text remains damaged. | 020–025 |
| 5. Dungeon | Pass: Forest and Tree entered through original menus; first Tree internal transition completes. | 028–032, 051–054, 068–071 |
| 6. Combat | Partial: Z/X damage/combos, repeated Flame Geyser/cooldowns, Roll animation/cooldown, first-area clear. Approximately 1fps, input/focus and effect fidelity remain unresolved. | 034–038, 055–087; Roll 036 |
| 7. Victory | Not verified: both attempts fail; native win count zero. | 091 is FAILED |
| 8. Rewards | Partial: original failure result and saved totals verified. No winning reward. | 098 |
| 9. Revival | **Fail twice:** six ordinary Z900ms pulses in Forest and ten Z2800ms pulses in Tree; initialized countdown stops with continue disabled. | 040–045, 088–097 |
| 10. Return | Pass: both original returns; first return permits another entry without restart or manual recovery. | 046–050, 099–100 |
| 11. Repeat | **Fail:** two entries/returns, zero winning cycles. Two successful cycles not demonstrated. | Same-session evidence above |

The capture ends intentionally in rendered Ruben after **3,537.063 seconds / 4,621 presentations**. [106 individually reviewed images](../reports/browser/20261011T105626Z/reviewed-images-final.json) comprise all 101 requested images, four selected timed images and `browser.png`. Other automatic images are unreviewed. The [source audit](../reports/browser/20261011T105626Z/source-audit.json) matches **244 source/integration files, both modules and the patch: 247 identities**, with no edits during capture.

### Reproducible final build and launch

| Artifact | SHA-256 / pin |
| --- | --- |
| Original `client/data/x2.exe` | `fe84cc1a95fc38b6d0d441997298828b133c7645e10a879978903e504d52d2f1` |
| Wine-Assembly commit | `d7854bc6c6bd0319ca33b5f31a465602e2ce0686` |
| Main Wasm | `8db3a988e3e761fbf44385a3a06c9d291adca50af00659e3763eed1a5392aa44` |
| Compatibility Wasm | `d9cf80483de727b809d5162a9767a02a1fbc9e51b7bdc3740c99988e169e2809` |
| Runtime patch | `c88abb6d3aa26b5391adfa88c01539c5d648ed97ea76b9ef420eac647237b389` |

The [manifest](../reports/browser/20261011T105626Z/frozen-manifest.json), [patch](../reports/browser/20261011T105626Z/runtime.patch), copied sources and modules are retained with the review. [Validation](../reports/browser/sse-policy-20261011T105000Z/validation.json) records the successful commands. From the repository root in PowerShell, with the original local payload, pinned tools and existing native services available, run each command and check its exit code:

```powershell
Push-Location theseus/tools/wine-assembly
& 'C:/Program Files/Git/bin/bash.exe' tools/build.sh
Pop-Location
python theseus/browser/prepare.py --runtime-only
python theseus/browser/bootstrap.py --check
python theseus/runtime.py status --json
python theseus/browser/serve.py --port 8766
```

Open `http://127.0.0.1:8766/`, choose **Start client**, log in with the existing local account, select TheseusOne, then **Start Game**. A matching already running host on 8766 can be reused. Use ordinary clicks to open **Dungeon**, select **Forest Ruins / Normal** or **Tree of El / Normal**, then **Start with current members**. The separate queue confirmation expires unless accepted; its observed expiration is not a runtime defect. [Build/recovery](build-recovery.md) covers restoring the retained pin and patch without replacing another checkout. This is a reproducible blocked build.

### Reproducible blocker and attempted fixes

In Forest, walk/jump past the first crate to the Guardian/Phoru group, stop fighting and allow HP to reach zero with ten stones available. The observer sends six ordinary Z keydown-900ms/up pulses during and after death. No breakpoint, watchpoint, gameplay memory write or CPU profiler is active during either death. [Validated actor/controller observations](../reports/browser/20261011T105626Z/untraced-revival-result.json) show state 8 → 4 over 15.768 sampled seconds. At the first state-4 sample, initialization is **1**, countdown **9.985714**, continue policy disabled, input/busy flags zero, stones ten. Countdown remains unchanged until original failure/return.

The second attempt clears Tree's first area and dies during second-area combat. Ten Z keydown-2800ms/up-100ms pulses again fail. [Second-death evidence](../reports/browser/20261011T105626Z/longer-input-revival-result.json) shows countdown **9.714279**, initialization 1 and disabled policy together. [Identity validation](../reports/browser/20261011T105626Z/longer-input-revival-validation.json) accepts controller requests 246–251 and excludes stale reads 252–254 after teardown. This follow-up does not revalidate actor/metadata memory; visuals and native zero-stone totals independently support the outcome.

The order of initialization versus policy disable within sampling gaps remains unresolved. **The old zero-initialization finding does not describe this build.** Historical [092157 caller evidence](../reports/browser/20261011T092157Z/revival-failure.json) identifies original `EGS_END_GAME_NOT` (201) disabling continue; the writer was not re-traced here. The changed death interval is not a controlled same-scene speed comparison.

[Change 0008](changes/0008-worker-wall-clock.md) removed a page round trip from wall-clock accounting. [Change 0009](changes/0009-sse-worker-policy.md) enables the already implemented SSE policy and repairs omitted Worker inheritance. Contract controls fail and candidates pass, but integrated revival still fails. [Current diagnosis](../reports/browser/20261011T105626Z/revival-failure.json) records the smallest unresolved dependency: original continue input/update must complete before the authoritative end-game path closes the encounter. The specific remaining client execution/scheduling operation responsible is **not isolated**. No event suppression, original timer changes, server edits or fabricated SQL state were used.

### Affected regressions and execution evidence

The [validation record](../reports/browser/sse-policy-20261011T105000Z/validation.json) retains exact commands, exit statuses, logs, identities and unavailable checks. Its log hashes cover normalized UTF-8 text before Windows newline conversion; the [identity addendum](../reports/browser/sse-policy-20261011T105000Z/log-identity-addendum.json) verifies all ten and retains exact on-disk byte hashes without changing earlier evidence.

| Check | Result |
| --- | --- |
| Compiled cooperative and real Worker SSE inheritance | Preserved control fails; candidate passes 8 checks including zero overrides. Existing 73-setter test passes. |
| Runtime contracts | DLL, pointer, thread, SList, FLS, activation and path checks pass. |
| Original D3DX native math comparison | 320 cases pass with SSE off and on; reference identities retained. |
| Skinning / MOVHLPS | 21 cases / 4,869 vertices and 128 instruction cases pass. |
| Scalar SSE | 144 assertions pass with documented existing XP winmine initializer. Upstream notepad initializer is unavailable; failure retained. |
| Canonical build / prepare / bootstrap check | Pass; final modules and source audit match. |

The original D3DX matrix workload improves from median 65.175ms to 16.874ms/10,000 calls under Node 24.14.1; **this is not browser FPS evidence**. Edge 155.0.4283.45 [bounded profiles](../reports/browser/20261011T105626Z/execution-observations.json) measure 16 presentations/15.714s in town and 17/15.393s in combat. Sampling ends before death. No new interpreter/JIT variant or controlled whole-game speedup is claimed.

### Outcomes, remaining differences and provenance

[Native exit statistics](../reports/browser/20261011T105626Z/server-observation-exit.json) confirm two attempts, zero wins, zero stones consumed and 12 dungeon ED. [Read-only SQL](../reports/browser/20261011T105626Z/database-observations.json) records EXP **67,831 → 67,839 → 68,638**, ED **3,393 → 3,405 → 3,405**. Final town totals persist. These are failed-attempt outcomes, not winning rewards. Initial zero counters in image 098 do not override saved totals. [Read-only native memory observations](../reports/browser/20261011T105626Z/server-state-observations.json) show the original account candidate in room state 8 and final field state 7.

[Runtime observations](../reports/browser/20261011T105626Z/runtime-observations.json) retain 54 nonfatal Lua throws and 575 increasing outbound TCP-9300 serials without header anomalies. No fatal crash or event-676 recurrence appears; this does not close historical authentication/ACK failures or prove payload authentication correctness.

Nonblocking/deferred differences: browser-local settings persistence is unconfigured; audible fidelity and unrelated maps/menus remain unverified. Small text damage did not prevent this route. Approximately 1fps, revival failure, input/focus uncertainty and white/dark effect frames remain acceptance issues. [Reviewed comparison](../reports/browser/20261011T105626Z/effect-comparison.json) finds dark particles in both current and historical Flame Geyser images; unmatched scenes do not establish correct fidelity or its cause. Earlier verified allocation/loading repairs remain closed without new collision evidence.

Original game/fork developers, Wine-Assembly/WATX/platform contributors and prior maintainers retain attribution. Codex /root used existing Node/WATX, Edge/Playwright, Python, local native references and read-only native/SQL observations, with no delegated agents. Native executables/configuration, SQL schema/persistence implementation, original game instructions/assets and UI are unchanged. Historical reviews below retain their own identities and scope.

## Historical worker-clock build: 092157 — BLOCKED

**The eleven-step session did not pass; the client port is incomplete.** [Replay 092157](../reports/browser/20261011T092157Z/review.json) tests change 0008 against the existing, unchanged native services. It launches, authenticates, selects the existing character, renders town, enters Forest Ruins twice and returns twice in one browser session. Independent revival fails. Native statistics confirm **two attempts, zero wins and zero resurrection stones used**. This build does not inherit the earlier build's victory or skill verification.

| Acceptance step | Result on final tested build | Reviewed images |
| --- | --- | --- |
| 1. Launch | Pass: original compiled executable on the frozen browser build. | 000–007 |
| 2. Login | Pass: original local login, Genesis and channel selection. | 008–012 |
| 3. Character | Pass: existing level-12 TheseusOne enters Ruben. | 013–016 |
| 4. Town | Pass: town renders; movement, Character panel and Dungeon menu respond. Small text defects remain. | 016–020 |
| 5. Dungeon | Pass: Forest Ruins Normal entered twice through original menus. | 019–026, 035–039 |
| 6. Combat | Partial: movement, jumping, collision, enemy attacks and damage observed. Basic attacks and multiple skills are not verified on this patch. | 024–028, 040–048 |
| 7. Victory | Not verified: both encounters exercise death; native win count is zero. | 049 is FAILED, not victory |
| 8. Rewards | Not verified: failure transition observed and saved totals checked; no winning result/reward verification on this build. | 034, 049 |
| 9. Revival | **Fail:** six ordinary Z pulses during/after death, ten available stones, no continue countdown or revival. | 029–034 |
| 10. Return | Pass: both original returns render town, and the first return permits another entry without restarting or recovering the browser. | 035–036, 053–054 |
| 11. Repeat | **Fail:** two entries and returns, but no successful winning cycle in this replay. | Same-session evidence above |

The replay ended intentionally in rendered town after 2,979.313 seconds and 4,878 presentations. [All 55 requested images, ten selected timed images and the final browser image](../reports/browser/20261011T092157Z/reviewed-images.json) were reviewed. Other automatic screenshots are not claimed reviewed. The [source audit](../reports/browser/20261011T092157Z/source-audit.json) checks 243 source/integration files, both modules and the patch: **246 matches, no changes during capture**.

### Exact build and launch

| Artifact | Identity |
| --- | --- |
| Original `client/data/x2.exe` SHA-256 | `fe84cc1a95fc38b6d0d441997298828b133c7645e10a879978903e504d52d2f1` |
| Wine-Assembly dependency commit | `d7854bc6c6bd0319ca33b5f31a465602e2ce0686` |
| Main Wasm SHA-256 | `8db3a988e3e761fbf44385a3a06c9d291adca50af00659e3763eed1a5392aa44` |
| Compatibility Wasm SHA-256 | `d9cf80483de727b809d5162a9767a02a1fbc9e51b7bdc3740c99988e169e2809` |
| Runtime patch SHA-256 | `399d8a2fc8f36a5e74e0bbe52a5c0397b480125f1b85ac9c2b60b46639d30225` |

The [frozen manifest](../reports/browser/20261011T092157Z/frozen-manifest.json), [runtime patch](../reports/browser/20261011T092157Z/runtime.patch), copied source directories and modules are retained beside the review. [Build/regression validation](../reports/worker-clock-20261011T091913Z/validation.json) records the exact successful commands and logs. With the original local payload, pinned tools and native services already available, run from the repository root in PowerShell; check each exit code:

```powershell
Push-Location theseus/tools/wine-assembly
& 'C:/Program Files/Git/bin/bash.exe' tools/build.sh
Pop-Location
python theseus/browser/prepare.py --runtime-only
python theseus/browser/bootstrap.py --check
python theseus/runtime.py status --json
python theseus/browser/serve.py --port 8766
```

Open `http://127.0.0.1:8766/`, select **Start client**, authenticate with the existing local account and select TheseusOne. An already running host on 8766 can serve the matching prepared build. The [build/recovery runbook](build-recovery.md) covers restoring the pin and preserved patch without overwriting another checkout. This is a reproducible blocked build, not a playable-session completion claim.

### Reproducible blocker and attempted fix

From Ruben choose **Forest Ruins / Normal**, walk and jump past the first crate to the Phoru/Guardian group, stop attacking and allow HP to reach zero. In the first attempt, **no breakpoint or watchpoint was armed**. The observer sent six ordinary Z keydown-900ms/up pulses beginning at death-front state 7 and continuing through final dead state 4. It revalidated live actor/controller identities before every read. [Untraced evidence](../reports/browser/20261011T092157Z/untraced-revival-failure.json) records 22.198 seconds between the first sampled death-animation state and final dead state. The continue-policy flag was already disabled 5.199 seconds before the first final-state sample. Countdown and initialization stayed zero; ten stones remained.

The second same-browser attempt used one bounded, automatically cleared breakpoint to identify the writer. [Live caller evidence and diagnosis](../reports/browser/20261011T092157Z/revival-failure.json) and the [original event mapping](../reports/browser/20261011T092157Z/end-game-dispatch-verification.json) establish `EGS_END_GAME_NOT` (201) → `32ba7d00` → `32a40280`. The store at `32a40281` disables controller `+6b8` while the actor is still in state 7. When final state 4 arrives, original policy `32cc4610` rejects continue initialization. This identifies the notification and original code path; it does not establish which specific BROCWIN operation consumes the missing execution time. The second attempt's breakpoint affects scheduling, so its performance is not normal-speed acceptance.

[Change 0008](changes/0008-worker-wall-clock.md) removes the synchronous page RPC for interpreter wall-clock accounting while preserving the same clock expression. The old real-Worker control fails; the candidate, runtime, RPC exception/nested-wait and capture-observer regressions pass, as do canonical build/preparation/pin checks. **The integrated revival failure remains.** The untraced group encounter averages approximately 0.89 presentations/second over the retained interval; this is an asynchronous interval estimate. [RPC counts](../reports/browser/20261011T092157Z/combat-rpc-census.json) measure call volume, not time cost. Change 0007's separate loading repair remains verified by historical 071553 and is not reopened.

The smallest unresolved dependency is to measure and repair the client execution/timing cost that prevents the original death/continue path from running before the authoritative end notification. Suppressing that notification, changing original gameplay timers, extending a server timeout or manufacturing SQL state would not satisfy acceptance. After that correction, the same final build still needs basic attacks, multiple skills, victory/rewards, successful independent revival and two complete winning cycles.

### Authoritative observations and remaining differences

[Native exit statistics](../reports/browser/20261011T092157Z/server-observation-exit.json) for UnitUID 20098 report two single-player attempts, zero wins, zero stones consumed and zero dungeon ED. [Read-only SQL](../reports/browser/20261011T092157Z/database-observations.json) retains EXP **67,831** and ED **3,393** before and after capture. Read-only native FSM observations record both room → field-map returns. No server executable/configuration, schema or persistence implementation was changed.

[Runtime observations](../reports/browser/20261011T092157Z/runtime-observations.json) retain 54 nonfatal Lua throw observations during startup/loading; they are not dismissed as harmless or attributed to revival without evidence. There is no reproduced fatal crash or event 676 in this capture. Its 387 increasing outbound TCP-9300 serials do not verify packet authentication content or close the historical intermittent failure.

Nonblocking for the same-session route: browser-local settings persistence remains unconfigured; audible fidelity and unrelated maps/menus are unverified and deferred. Small HUD/menu text damage did not prevent the documented navigation. An empty death speech bubble is retained as an unclassified text limitation. Low frame rate, revival failure, unverified skill reliability and historical fatal timeout/connection failures remain acceptance issues, not waived cosmetic differences.

Provenance: original game/fork developers, Wine-Assembly/WATX/platform contributors and earlier documented maintenance retain attribution. Codex /root performed this replay without delegated agents, using the existing Node/WATX, Edge/Playwright, Python, PE/Capstone and read-only native/SQL tools. Historical sealed reviews below remain unchanged and apply only to their identified builds.

## Historical integrated result: 071553

**BLOCKED; the port is incomplete.** [Replay 071553](../reports/browser/20261011T071553Z/review.json) passes the repeated-area loading path repaired by change 0007. In one browser session it makes three dungeon attempts, wins the second, returns to town after each, and independently reproduces failed revival. The unchanged native server confirms **three attempts, one win and zero resurrection stones used**. There is no second successful cycle.

| Step | Result in 071553 | Images |
| --- | --- | --- |
| 1. Launch | Pass: original compiled client, frozen reproducible build. | 000–008 |
| 2. Login | Pass: original local authentication/channel flow. | 009–015 |
| 3. Character | Pass: existing TheseusOne enters Ruben. | 016–019 |
| 4. Town | Pass: rendering, movement, inventory/character, Ann shop and dungeon menus. | 019–025, 057–065, 119–123 |
| 5. Dungeon | Pass: two Tree of El attempts and Forest Ruins, including internal area transitions. | 026–027, 066–068, 082, 097, 124–133 |
| 6. Combat | Partial: basic attacks, movement, Flame Geyser, Roll and awakening show animation, effects, cooldown and damage. Low frame rate and full input/focus reliability remain unresolved. | 028–054, 069–117; Roll 094 |
| 7. Victory | Pass: Banthus and White Giant Phoru defeated alive; original result and native win count 1. | 106, 116–118 |
| 8. Rewards | Pass: original failure and winning result panels, saved totals verified. Winning result grants zero EXP/ED; no positive winning payout is claimed. | 055, 118, 120 |
| 9. Revival | Fail: independent Forest death, repeated Z beginning during death animation, ten stones, no continue UI or revival. | 138–144 |
| 10. Return | Pass: original returns and interactive town inventory without browser restart or recovery. | 056, 119–123, 145–146 |
| 11. Repeat | Fail: one win across three attempts; two successful cycles are not demonstrated. Former loading-corruption transition passes. | 082, 097, 133 |

The [156 reviewed images](../reports/browser/20261011T071553Z/reviewed-images.json), [245-identity source audit](../reports/browser/20261011T071553Z/source-audit.json), [native statistics](../reports/browser/20261011T071553Z/server-observation-exit.json) and [read-only SQL](../reports/browser/20261011T071553Z/database-observations.json) are sealed. First failure grants 2,120 EXP / 39 ED, matching saved EXP 65,711 → 67,831 and ED 3,354 → 3,393. Those totals persist after the win and independent death. The original level-difference reward restriction is a possible explanation for the zero winning payout; its exact code path is not established.

The [revival trace](../reports/browser/20261011T071553Z/revival-failure.json) validates the live actor/controller identity on every sample. Controller `+6b8` changes from 0 to 1 before the actor reaches `GUSI_DIE` (4). Original policy `32cc4610` rejects continue when that byte is nonzero; the countdown and initialization remain zero. The writer was unresolved in this historical run; 092157 identifies it above. Breakpoints altered scheduling; no guest state, original instructions or server data were patched. Long loading eventually progresses; transient white frames and damaged small text remain. Audio fidelity and wider maps/settings persistence are deferred.

This replay used main Wasm `8db3a988e3e761fbf44385a3a06c9d291adca50af00659e3763eed1a5392aa44`, compatibility Wasm `d9cf80483de727b809d5162a9767a02a1fbc9e51b7bdc3740c99988e169e2809`, and patch `41adbcbaca4611f23066b6b5937c0cf373a3892faf653925b1af79c6361624cc`. [Change 0007 validation](../reports/high-image-20261011T071500Z/validation.json) retains exact build/prepare commands and affected regression results. The launch commands and [build runbook](build-recovery.md) apply; historical hashes belong to their labeled replay. The subsequent worker wall-clock correction is tested separately in 092157 and does not inherit this replay's acceptance.

## Historical integrated result: 053950

**BLOCKED; the port is incomplete.** [Replay 053950](../reports/browser/20261011T053950Z/review.json) completed one original Tree of El victory, rewards and interactive Ruben return on Wasm `fbdfcc7e`, compatibility module `95e2292d` and patch `9b4c5f0a`. The same browser entered a second cycle and cleared its first area, then crashed while loading the next area. Independent revival was not attempted in this run; the earlier failed revival remains open. A subsequent allocator correction is under validation and has no integrated acceptance yet.

| Step | Result in 053950 | Reviewed images |
| --- | --- | --- |
| 1. Launch | Pass: frozen original executable starts in browser Wasm. | 000–008 |
| 2. Login | Pass: original local login and channel selection. | 009–015 |
| 3. Character | Pass: existing level-11 TheseusOne enters Ruben. | 016–018 |
| 4. Town | Pass: rendered town, movement, character/inventory menus and original shop interaction. | 018–024, 090–100 |
| 5. Dungeon | Pass: Tree of El Normal entered through original menus; internal transitions complete. | 025–028, 047, 074 |
| 6. Combat | Partial: basic attacks, movement, Flame Geyser, Roll, awakening, effects, damage and enemy clears work. Full input/focus reliability remains unverified. Original mana/cooldown denials explain some unsuccessful presses. | 029–087, 104–107 |
| 7. Victory | Pass: Banthus defeat is followed by White Giant Phoru and the remaining enemies, then the original CLEAR state. | 081–088 |
| 8. Rewards | Pass: original victory result shows 4,861 EXP / 80 ED; town inventory rises from 3,251 to 3,331 ED. Final SQL retains combined rewards and subsequent loot. | 088, 091 |
| 9. Revival | Unverified in this run; historical repeated-Z failure is unresolved. | Prior 043232 evidence below |
| 10. Return | Pass: automatic Ruben return, rendered terrain, movement, menus and shop, without reconnect/reload. | 089–100 |
| 11. Repeat | Fail: second cycle starts and clears area one; next-area load crashes on allocator metadata corruption. | 101–110, browser.png |

The [112-image review](../reports/browser/20261011T053950Z/reviewed-images.json) and [source audit](../reports/browser/20261011T053950Z/source-audit.json) preserve all manual/final images and all 242 source identities plus modules/patch. No breakpoints or guest-memory writes were used. Image 082 is the White Giant Phoru introduction, not the final victory cinematic; image 083 records that correction. The summoned ally is Monster Card: Ruchi.

[Read-only SQL](../reports/browser/20261011T053950Z/database-observations.json) records EXP 60,843 → 65,711 and ED 3,251 → 3,354, a combined +4,868 EXP / +103 ED. The difference from the first victory reward is consistent with second-cycle loot; allocation per event is an inference. Intermediate reads preceded final persistence. No post-session user-statistics block was present in the [native log excerpt](../reports/browser/20261011T053950Z/server-observation-exit.json) at sealing, so no native win/stone count is claimed from it.

[Failure-time observations](../reports/browser/20261011T053950Z/loading-failure.json) show HEAP_ARENAS count `0x3f800000`, the float-1.0 bit pattern, and repeated animation matrices replacing records. This is corruption, not a legitimate 1,024-record limit. The later `setlocale` and `GetProcessWindowStation` traps follow 2,202 OOM reports. [Bounded diagnosis](../reports/high-image-20261011T071500Z/diagnosis.json) and the preserved control reproduce a valid sparse allocation aliasing private runtime storage at X2's high image base. The placement correction must pass integrated re-entry before BRC-010 can close.

The prior event-676 failure did not recur. This run observes 852 accepted outgoing TCP-9300 packets with increasing serials, no diagnostic parsing errors and no serial anomalies. That does not establish authentication-content validity or close the earlier failure. [Read-only native disassembly](../reports/traffic-event-20261011T053300Z/original-notification-boundary.json) now identifies event 676 as the result of crossing a packet-authentication failure threshold; it does not establish a traffic-rate violation or the offending packet.

Exact launch commands and baseline module hashes are retained below. Native servers, their configuration, SQL schemas and persistence implementation remain unchanged. Small damaged tooltips, transient white frames and unmeasured audio fidelity remain; unrelated maps, multiplayer and browser-local settings persistence are deferred. Mouse move/wait/click timing improved later menu interaction, but its cause is not established.

## Previous integrated result: 043232

[Wiki](README.md) · [Build and exact launch commands](build-recovery.md) · [Sealed current-build review](../reports/browser/20261011T043232Z/review.json)

**BLOCKED: the eleven-step session did not pass.** Final integrated replay `20261011T043232Z` ran for 2,954.906 seconds against the existing native local services. It cleared two Tree of El areas, died at Banthus, failed to revive, displayed the original failed-attempt rewards and terminated during return to Ruben. There was no victory or second cycle on this build. Historical victory evidence is kept below and is not inherited by this candidate.

| Step | Result on this session | Reviewed images |
| --- | --- | --- |
| 1. Launch | **Pass:** prepared build launches the original executable in browser Wasm. | 000–008 |
| 2. Login | **Pass:** original local login and channel selection. | 009–015 |
| 3. Character | **Pass:** existing level-11 TheseusOne enters Ruben. | 016–020 |
| 4. Town | **Partial:** movement and original character/inventory menus work. Dungeon selection required repeated clicks; damaged small text remains. | 021–025 |
| 5. Dungeon | **Pass:** original Tree of El Normal entry and both internal area transitions. | 025–028, 042–043, 062–063 |
| 6. Combat | **Partial:** Z/X attacks, jumps, Flame Geyser, Roll, awakening and potion use through two area clears. MP, cooldowns, damage, animation and effects are visible. Some direction/skill attempts during hit reactions were unsuccessful; white frames recur. Their causes are unresolved. | 029–068 |
| 7. Victory | **Fail:** died at Banthus; native dungeon win count is zero. | 068–070 |
| 8. Rewards | **Partial:** original failed-attempt interface shows 2,625 EXP / 59 ED, agreeing with native observations. No victory reward. | 071 |
| 9. Revival | **Fail:** repeated Z during/after death did not revive; no continue choice was seen and native resurrection-stone use is zero. This does not satisfy the independently successful revival encounter. | 068–071 |
| 10. Return | **Fail:** original return to Ruben begins, but the client terminates before interactive town recovery. | 071, browser.png |
| 11. Repeat | **Fail:** termination prevents a second gameplay cycle. | browser.png |

The [image inventory](../reports/browser/20261011T043232Z/reviewed-images.json) records 73 reviewed manual/final images. Automatic screenshots are not claimed as reviewed evidence. Input timing and read-only probe requests remain in the capture's `result.json` and control responses. Death probes altered scheduling; they were cleared before rewards/return. No guest instructions or guest memory were changed by diagnosis.

## Build and reproduction

The original EXE is `fe84cc1a95fc38b6d0d441997298828b133c7645e10a879978903e504d52d2f1`; Wine-Assembly is pinned to `d7854bc6c6bd0319ca33b5f31a465602e2ce0686` with the preserved BROCWIN patch. The [source audit](../reports/browser/20261011T043232Z/source-audit.json) verifies all 242 frozen source identities, both modules and the patch remained unchanged throughout the replay.

| Artifact | SHA-256 |
| --- | --- |
| Main Wasm | `fbdfcc7ed8107d852c4a51473dab4f63952e1b604188797a487b858d73ca5117` |
| Compatibility Wasm | `95e2292d09be2f9410101e8dd6f7b8721a51fc7ea5bef594b7f7c87ab6fab1ef` |
| Runtime patch | `9b4c5f0a5cb0a19892b1e9446ab0603889c599363e28a98caf0d1c170abfe36e` |

Use the runbook's canonical Git Bash build, `prepare.py --runtime-only` and `bootstrap.py --check`. With the existing native services already running, launch from the repository root:

```powershell
python theseus/runtime.py status --json
python theseus/browser/serve.py --port 8766
```

Open `http://127.0.0.1:8766/`, click **Start client**, authenticate using the existing local account and select TheseusOne. From Ruben choose Tree of El Normal through the original dungeon menu. The captured route uses arrows, Z/X, A (Flame Geyser), S (Roll), ControlLeft (awakening) and 1 (the existing potion). Clear both areas and fight Banthus. The retained death reproduction exhausts HP and presses Z repeatedly during/after death, then follows the original result/return transition. Exact action durations are retained in `result.json`; long diagnostic holds are not a production input fix. Native services, configuration, schemas and persistence implementation were not changed.

## Blocking diagnoses and attempted fixes

The [exit record](../reports/browser/20261011T043232Z/exit-failure.json) and [original-code reference](../reports/browser/20261011T043232Z/exit-path-reference.json) establish the immediate fatal path at **2026-10-11 05:21:50.154 UTC**: original event 676, `EGS_TRAFFIC_ATTACKER_NOT`, dispatches at `0x329f95dc` to `0x329e3b20`, which calls `KERNEL32.TerminateProcess` through IAT `0x3329e134` with code -1. The saved return address `0x329f95ee` and event value agree with this path. The host label `[ExitProcess]` alone would not establish that import. The traffic/state sequence that triggers event 676 remains unresolved; no offending game packet has been identified. Relay closure follows with code 1005 and no protocol rejection. Suppressing termination would not repair the original path.

The [revival record](../reports/browser/20261011T043232Z/revival-failure.json) preserves repeated Z input, ten stones visible before death, zero native stones consumed, and bounded original continue-path observations. Common entry `0x32a59290` was reached while alive. All-worker probes after the character-state comparison (`0x32a59344`) and at continue setup (`0x32a5968d`) did not fire through death. This does not identify which preceding eligibility condition failed. The old first-area object had changed contents by the result screen and cannot establish death-time state. The smallest unresolved dependency is a valid observation of the original character's eligibility/state at death.

Earlier input and shared-transport repairs remain in the existing runtime. The latest [change 0006](changes/0006-retire-small-arena-tails.md) fixes a reproduced allocator retirement omission for eight-byte unused tails. The preserved old-module control fails; **11 candidate validation entries pass**, including both Wasm variants, affected memory tests and the capture observer. [Exact commands, logs and identities](../reports/heap-tail-20261011T042900Z/validation.json) retain the canonical build and preparation results. No OOM or worker-slice timeout occurred in this replay, but neither older intermittent loading failure is closed by this single route. The allocator fixture does not prove the cause of the older game crash.

These are the bounded stop dependencies: determine the original revival eligibility/state failure and identify the client traffic/state that produces event 676 before implementing a compatibility correction. No server change, synthetic revival, fake acknowledgement, timeout extension or original-code bypass was used to force a pass.

## Authoritative outcome and historical limits

[Native server observations](../reports/browser/20261011T043232Z/server-observation-exit.json) record one single-player attempt, zero wins, zero resurrection stones used and 59 dungeon ED. [Read-only SQL observations](../reports/browser/20261011T043232Z/database-observations.json) show EXP **58,218 → 60,843** and ED **3,192 → 3,251**, matching the original failed-attempt reward interface. This verifies the saved outcome without diagnostic SQL writes or changes to server persistence.

Historical [010733](../reports/browser/20261011T010733Z/review.json), on different Wasm/patch identities, completed one original victory/reward/return, later failed revival and stalled on a subsequent load. Same-old-module [024047](../reports/browser/20261011T024047Z/review.json) again failed Z revival and later ended at EIP zero with metadata OOM records. Those sealed reviews remain immutable. Current event-676 evidence does not retroactively establish the cause of the historical `195820` boss exit.

Remaining nonblocking limitations outside the tested route include browser-local settings persistence being unconfigured and audible fidelity not yet compared with native output; the current capture shows a running audio context and nonzero submitted PCM. Wider menus, maps and multiplayer remain unverified and deferred. Damaged text in tested menus, white combat frames, inconsistent actions and the failures above remain acceptance issues, not waived cosmetic differences.

Provenance includes the original fork developers, Wine-Assembly/WATX/platform contributors and prior documented maintenance. Codex /root operated this replay without delegated agents. The current build and wiki are a reproducible **blocked handoff**, not a completed client port.
