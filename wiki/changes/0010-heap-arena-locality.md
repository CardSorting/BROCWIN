# 0010 - Reuse the preceding validated heap arena record

[Wiki](../README.md) · [Memory](../threads-memory.md) · [Acceptance](../acceptance-session.md)

Date: 2026-10-11. Contributor: Codex /root; no delegated agents. Scope: reduce a measured client execution cost on the existing gameplay path. Original game code, assets, input rules, native servers and SQL implementation are unchanged.

## Observation and bounded correction

The [105626 town profile](../../reports/browser/20261011T105626Z/execution-observations.json) attributes 21.04% of sampled main-worker time to `heap_free_impl`. The existing single-record `heap_arena_find` hint misses repeatedly when validation alternates between a freed block and free-list links in another arena. The [preserved control](../../reports/heap-free-locality-20261011T122400Z/validation.json) passes correctness checks but scans 1,999,000 records in the alternating warm workload.

[10-helpers.wat](../../tools/wine-assembly/src/10-helpers.wat) retains one additional per-instance record hint. The primary path is unchanged. A secondary hit swaps the two hints; a scan hit retains the preceding primary. Each lookup re-reads the published base and allocated end atomically. Alignment, exclusive-end checks, authoritative fallback, placement and reclamation remain unchanged. A new Worker starts with empty hints; no inheritance entry or new runtime region is needed. The [exact diff](../../reports/heap-free-locality-20261011T122400Z/allocator-change.diff) is retained.

[test_heap_arena_locality.cjs](../../browser/test_heap_arena_locality.cjs) compiles the canonical include closure. It verifies ordinary reuse, unpublished/recycled primary and secondary records, changed base and allocated end, alignment/bounds and a fresh peer instance. The candidate performs zero warm table scans in the control workload. [prepare.py](../../browser/prepare.py) preserves this test in integration identities. No interpreter/JIT instruction variant was introduced.

## Verification and limits

[Validation](../../reports/heap-free-locality-20261011T122400Z/validation.json) retains the expected control failure, 13 passing candidate/regression/preparation checks and successful canonical build. Eight existing heap suites pass, including randomized operations and shared instances; actual compiled runtime and SSE-Worker checks also pass. The synthetic [timing probe](../../reports/heap-free-locality-20261011T122400Z/probe-result.json) is an allocator workload, not a game-speed claim. Both existing native-code extraction routes were attempted; [D8 and SpiderMonkey are unavailable](../../reports/heap-free-locality-20261011T122400Z/native-code-availability.json). No generated native assembly was inspected or inferred from an older variant.

The real-browser [town profile comparison](../../reports/browser/20261011T123040Z/town-profile-comparison.json) measures heap-free self time at 5.82% on the candidate, with 19 presentations in 15.334 seconds. The prior window measured 21.04%, with 16 in 15.714 seconds. These are separate scene/sampling windows, not a controlled whole-game speed comparison. Profiling ends before dungeon entry and death.

The tested main Wasm is `c38c94850b55c6adc2981f4a277d80a3732f5b4f8c275d246949c92fe810eb3d`; compatibility module `c2380511aeb9632886c0ff2790276dbfdf6c1c89193b20174dd5d0acaaae8ef8`; patch `0b77ba556ef26837f40180143ff4771e2a0cbc511bb6173082848be1bee10e3d`. [The audit](../../reports/browser/20261011T123040Z/source-audit.json) matches 245 source/integration files, both modules and patch. Copies were preserved after replay against matching prepared/captured identities, before releasing the source freeze. No runtime sources changed during capture.

## Integrated result

**BLOCKED.** [123040](../../reports/browser/20261011T123040Z/review.json) seals 56 reviewed images over 2,471.734 seconds and 9,559 presentations. Original login, character selection, town, Forest entry, basic sword action, Flame Geyser, Roll, failure result and automatic town return work within the recorded limits. Incidental Lake Noahs portal travel returns to Ruben. Native totals: one attempt, zero wins, zero revival stones; final saved gains are 908 EXP and 20 ED. No earlier victory is credited to this build.

[Revival still fails](../../reports/browser/20261011T123040Z/revival-failure.json). The final dead state arrives 16.144833 seconds after the first sampled death state with continue already disabled, initialization/countdown zero, and all nine stones retained. Six ordinary Z pulses fail. All 128 live state samples are revalidated; the first post-teardown read is excluded. This differs from 105626's initialized countdown; neither is success.

The unchanged [native client reference](../../reports/native-revival-20261011T120600Z/review.json) reaches initialized continue in 4.670260 sampled seconds and revives with ordinary Z, consuming one stone. Different resolution/input/sampling prevents a controlled FPS comparison. Its [persistence addendum](../../reports/native-revival-20261011T120600Z/persistence-addendum.json) corrects a stale immediate-exit SELECT without changing the sealed review. Read-only [original server code](../../reports/native-revival-20261011T120600Z/original-death-timer.json) arms a 15-second death allowance; [the expiration target is confirmed as KDungeonRoom::EndPlay](../../reports/native-revival-20261011T120600Z/timer-target-addendum.json). The live server timer origin was not sampled in this browser run.

The remaining dependency is timely original death/continue execution before authoritative encounter closure. The exact remaining BROCWIN cost is not isolated; this patch reduces a measured cost but does not establish the complete timing cause. No timer, policy, input-state, event or server bypass is used. Full combat fidelity, successful revival, winning rewards and two winning cycles remain unverified.

Tools and provenance: existing Wine-Assembly/WATX build, Node, Edge/Playwright/CDP, Python, local PE/Capstone and read-only native/SQL observers. Original game/fork developers, platform contributors and prior maintainers retain attribution.
