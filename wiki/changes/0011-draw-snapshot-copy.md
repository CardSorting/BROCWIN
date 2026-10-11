# 0011 - Reduce draw snapshot construction overhead

[Wiki](../README.md) · [Graphics](../graphics.md) · [Acceptance](../acceptance-session.md)

Date: 2026-10-11. Contributor: Codex /root; no delegated agents. Scope: the existing browser client and the eleven-step acceptance route, principally BRC-004's execution cost. Original game code, native servers, SQL, assets and gameplay rules remain unchanged.

## Observation and correction

The sealed 123040 town profile attributes 7.70894% of page sampling self time to the recursive command snapshot copier. It defines every shader-descriptor property separately. The [bounded probe](../../reports/draw-snapshot-copy-20261011T132600Z/probe-result.json) rehydrates 27 retained original draw descriptors and their captured typed buffers. Across seven alternating rounds of 300 copies, the old median is 349.753 ms and the candidate median 145.709 ms. This measures descriptor copying in Node, not game speed or complete rendered frames; textures were omitted from the source capture.

[d3d-command-stream.js](../../tools/wine-assembly/lib/d3d-command-stream.js) now builds ordinary objects and arrays with temporary null prototypes and direct own-property assignment, restores their original final prototypes, then freezes them. This avoids inherited setters and `__proto__` mutation while preserving the existing snapshot shape. Source accessor rejection, cycle/host-object rejection, copy ownership, alias handling, byte accounting, bounds and queue/resource ordering remain intact. No new queue, transport, interpreter/JIT variant or compatibility feature was added.

The amended [neutral-command test](../../tools/wine-assembly/test/test-d3d-neutral-command-stream.js) exercises named array properties, hostile inherited setters, `__proto__`, final prototypes/descriptors, frozen arrays and exact budget boundaries. It passes against both the preserved control and candidate. The old shared-render mock also omitted its actual single implicit backbuffer; that fixture fails identically with both implementations. Initializing that existing field restores both passes without relaxing assertions or changing production behavior.

## Verification and integrated outcome

[Validation](../../reports/draw-snapshot-copy-20261011T132600Z/validation.json) preserves controls, raw output and hashes for neutral commands, D3D shared rendering, render lifetime, real render Worker protocol, runtime, 208 native StretchRect HRESULT/pixel cases, canonical build, preparation and bootstrap. Two existing guest-render/park-batch checks cannot run because their required `test/binaries/calc.exe` fixture is missing; they are not passes. The [capture-observer regression](../../reports/draw-snapshot-copy-20261011T132600Z/capture-observer.json) passes after the newly observed serial anomaly, including fragmentation, coalescing, failed sends, original argument identity and bounded anomaly reporting.

Main Wasm remains `c38c94850b55c6adc2981f4a277d80a3732f5b4f8c275d246949c92fe810eb3d`; compatibility remains `c2380511aeb9632886c0ff2790276dbfdf6c1c89193b20174dd5d0acaaae8ef8`. The tested patch is `66e4c7ccc9456315ea5e9ffc8c35fdd52fa794c4a17a038cd1c158851e882e5f`, on dependency commit `d7854bc6c6bd0319ca33b5f31a465602e2ce0686`. All 248 identities were copied before launch and [audited before releasing the capture freeze](../../reports/browser/20261011T133104Z/source-audit.json). No source edit, build or prepare occurred during capture.

**BLOCKED.** [133104](../../reports/browser/20261011T133104Z/review.json) contains 39 individually reviewed images, 1,759.953 seconds and 4,868 presentations. Login, the existing character, Ruben movement/menu, Tree of El entry, basic attacks, repeated Flame Geyser, Roll and first-area clear are observed. The original process terminates at that area's gate; no full dungeon victory, rewards, revival, return or second cycle is established. SQL remains level 12, EXP 69,567 and ED 2,237 after exit. Native services retain their PIDs and remain ready, but no matching native logout-statistics block is available.

The [town sample](../../reports/browser/20261011T133104Z/town-profile/profile-detail.json) has 20 presentations in 15.29086 seconds; page `copy` self time is 5.00397%. These separate historical/current sample windows are not a controlled overall performance comparison. Profiling ended before dungeon entry; no breakpoints or profiler ran during combat.

## Remaining blocker

[Final verification](../../reports/draw-snapshot-copy-20261011T132600Z/final-validation.json) checks current and preserved build/source identities, all 39 reviewed image hashes, seven original/reference identities and retained regression logs. The pre-replay validation's pending label is preserved as historical; this later record supplies the blocked integrated outcome.

[The failure record](../../reports/browser/20261011T133104Z/exit-failure.json) establishes original event 676, `EGS_TRAFFIC_ATTACKER_NOT`, and `TerminateProcess(-1)` at 14:00:27.602 UTC. Unlike earlier captures, two distinct outgoing packets (74 and 58 bytes) both carry serial 241. The duplicate is observed 26.435 ms before the exit observation. Existing original server evidence identifies the authentication threshold and monotonic-serial rule; a native authentication verdict and payload were not captured.

[Bounded static follow-up](../../reports/serial-duplicate-20261011T140500Z/diagnosis.json) confirms separate original serial read/increment operations and a context-lookup lock released before they run. It does not identify the live callers or establish a BROCWIN synchronization defect. The smallest unresolved observation is the originating guest thread/caller and security-context value for each duplicated packet. A relay serial rewrite, fabricated ACK, suppressed termination or server change would conceal the failure and is excluded.

Earlier revival failure remains historical, unresolved evidence; this attempt exits before reaching it. Small text, dark effect surfaces, low frame cadence and short-input/focus reliability remain limits. See [network](../network.md), [compatibility](../compatibility.md), [issues](../issues.md), [changelog](../CHANGELOG.md) and [chair briefing](../chair-briefing.md).

Provenance: original game/fork developers and Wine-Assembly/WATX/platform contributors retain attribution. Tools: existing canonical build, Node, Edge/Playwright/CDP, Python, pefile/Capstone and guarded read-only native/SQL observers.
