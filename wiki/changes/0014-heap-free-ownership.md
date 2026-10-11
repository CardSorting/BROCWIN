# 0014 - Claim heap free ownership in the shared block header

[Wiki](../README.md) · [Threads and memory](../threads-memory.md) · [Performance](../performance.md)

## Identity and authority

Date: 2026-10-11. Authority: Executive Chair MAJO's runtime engineering commission, following the startup observations in [0013](0013-runtime-startup-cache.md). Related issue: BRC-019. Codex /root coordinates the build and application measurements; /root/kernel_audit implements and tests the allocator correction; /root/evidence_audit independently reviews the code and evidence. Original game developers, Wine-Assembly/WATX contributors and earlier maintainers retain attribution.

This change concerns BROCWIN's allocator and renderer resource lifecycle. The original client, assets, gameplay logic, native services and SQL are unchanged. The application route under investigation is original cold startup to the empty login screen. The diagnosed ownership failures below occur in constructed allocator workloads; no duplicate free by the original client has been established.

## Observation and cause

The [bounded original-client profile](../../reports/performance/kernel-profile-control-20261011/profile-summary.json) samples approximately 30–50 seconds after Start client. Its [source audit and review](../../reports/performance/kernel-profile-control-20261011/source-audit-review.json) retain 255 matching source identities, 321 matching original input hashes, and a reviewed black startup canvas. The run intentionally ends before login. Active-worker samples attribute 521,506 microseconds of self sample weight to `heap_free_impl`; `uop_fast` remains dominant. These profiles include blocking waits and are not process CPU measurements. They establish that the allocator is exercised, without attributing total startup delay to it.

The preserved [compiled control probe](../../reports/performance/heap-free-20261011/probe.cjs) and [baseline record](../../reports/performance/heap-free-20261011/baseline-utf8.json) isolate two failures in control Wasm `c38c94850b55c6adc2981f4a277d80a3732f5b4f8c275d246949c92fe810eb3d`:

- A repeated free beneath the duplicate scan's 65-link limit increments the accepted-free count from 128 to 129 and creates a cycle.
- Two instances sharing Wasm memory accept the same free into separate private lists, then both reissue the same pointer.

The control searches only the freeing instance's private list. That cannot prove shared ownership, and its bounded search misses deeper duplicates. The same scans burden ordinary valid frees: the initial constructed 512-byte free/reallocate workload takes a median 10.766ms at depth zero and 72.543ms at depth 64 for 100,000 pairs. These exploratory timings include JS assertions and concurrent machine activity; they are not a candidate comparison or an application speedup.

Microsoft documents that repeated [HeapFree](https://learn.microsoft.com/en-us/windows/win32/api/heapapi/nf-heapapi-heapfree) calls on the same pointer can corrupt a heap and cause duplicate pointer issuance. Rejecting this invalid caller behavior is a defensive runtime invariant, not a claim that Windows guarantees successful duplicate-free handling. No new native API oracle or original-client fault is claimed.

## Implementation

[10-helpers.wat](../../tools/wine-assembly/src/10-helpers.wat) uses spare low bits of the existing aligned four-byte extent header: tag 0 is normal live, tag 1 is live Global allocation provenance, and tag 2 is free. Tags 3–7 remain malformed. Extent arithmetic masks all three low bits; payload layout and returned pointers stay unchanged.

A generic free validates the aligned resident allocation extent, then atomically changes tag 0 to tag 2. Only the successful claimant links the block, increments accepted-free statistics and subtracts live arena bytes. The three duplicate-list scans are removed. This ownership transition has constant work with respect to list depth; other free work, including page tracking, is not claimed to be independent of block size.

GlobalFree retains its exact boundary/provenance walk and changes tag 1 directly to tag 2. GlobalReAlloc has a separate existing reservation mode that temporarily changes tag 1 to tag 0. It restores live Global provenance on a same-address result or allocation failure, and frees the old block once when moving. Conflating the two modes would mark an allocation as freed before reallocation. [09a-handlers2-runtime.wat](../../tools/wine-assembly/src/09a-handlers2-runtime.wat) documents that distinction. The preserved failure behavior agrees with Microsoft's [GlobalReAlloc contract](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-globalrealloc), which keeps the original allocation valid when reallocation fails; broader Global allocation semantics are outside this change.

Allocation validates free tags in bins, ordinary lists and large arenas, preserves the tag on split remainders, clears it before returning live storage, and retains existing payload zeroing. Bin flushing validates the tail's state and size class before writing its next link. Shrinking and arena-tail retirement create ordinary live suffix headers before transferring them through the same free path, preserving existing live-byte accounting.

[09a0b-handlers-base-late.wat](../../tools/wine-assembly/src/09a0b-handlers-base-late.wat) lets structural walks traverse free extents while rejecting a free target as live. HeapCompact masks extents and preserves free state when joining blocks. [09ai-d3d-render-lifetime.wat](../../tools/wine-assembly/src/09ai-d3d-render-lifetime.wat) validates free ownership during renderer retirement/adoption and preserves markers through coalescing. Existing bounded walks, overlap/intersection rejection and conservative remote-free accounting remain. Opaque live-object validators retain strict raw-header checks so freed storage is not accepted as a live object.

## Verification

[Final source validation](../../reports/performance/heap-free-20261011/final-source-validation.json) records exact source/test hashes and sixteen passing focused regression commands, including heap ownership, bins/list validation, shrink, arena lifetime and metadata pressure, partitioning, heap API validation, Global allocation/reallocation, compaction and renderer retirement/adoption. The [canonical build log](../../reports/performance/heap-free-20261011/build.log) records successful WATX build gates. The affected integration [allocator-locality](../../reports/performance/heap-free-20261011/integration-locality.log) and [runtime contract](../../reports/performance/heap-free-20261011/integration-runtime.log) checks also pass.

The new [ownership regression](../../tools/wine-assembly/test/test-heap-free-ownership.js) runs the same operations against supplied compiled modules. It covers depth-128 bin/list/large duplicates, cross-instance ownership, and simultaneous real Node Workers. A second barrier prevents allocation until both frees finish, separating duplicate-free ownership from stale-pointer reuse. Assertions check one accepted free, one shared live-byte decrement, disjoint reissued pointers, repeated transfers and malformed pointers/links. The [final control log](../../reports/performance/heap-free-20261011/control-ownership-final.log) retains nine expected failures and two passing cases. All eleven cases pass on the candidate [main module](../../reports/performance/heap-free-20261011/ownership-main.log) and [compatibility module](../../reports/performance/heap-free-20261011/ownership-compat.log):

- Main Wasm: `1928229fb1326a2d7b5410aeb24c2ada36833b40650c8627e509058f7ac14cbe`.
- Compatibility Wasm: `1150a267e54da522264b8924d61a8dbe899ffb68ea10cbec68c13b3f91d765eb`.

The validation record explicitly preserves initial fixture mistakes. The first ownership census read the wrong generated-property path and was not a valid accounting oracle; the corrected fixture asserts a defined metadata base and positive live census. An intermediate control run ended during teardown and is superseded by the complete final control result. Renderer overlap corruption is injected after bin flushing so the test reaches overlap validation instead of the new earlier tail guard. Header assertions now include the free marker while retaining boundary, payload, retirement and overlap checks. GlobalReAlloc tests additionally assert exact live/free tags and one accepted old-block free. Earlier logs remain preserved and are not relabeled as passes.

The completed [paired allocator summary](../../reports/performance/heap-free-20261011/microbenchmark-summary.json) preserves hashes of all four raw result files from the control/candidate/candidate/control sequence. [benchmark-free.cjs](../../reports/performance/heap-free-20261011/benchmark-free.cjs) uses a 512-byte payload, 20,000 warmup pairs and five timed repetitions of 100,000 free/reallocate pairs at each depth, checking exact pointer reuse. Each table entry is the mean of the two process medians for its condition. All four processes use Node v24.14.1 / V8 13.6.233.17-node.44 on Windows x64, an Intel Core i5-6500 at 3.20GHz with four logical CPUs, and 536,870,912 bytes of shared Wasm memory.

| Retained free-list depth | Control mean of medians, ms | Candidate mean of medians, ms | Candidate/control elapsed ratio | Control/candidate speed ratio |
| --- | ---: | ---: | ---: | ---: |
| 0 | 10.458 | 11.914 | 1.139 | 0.878 |
| 8 | 19.297 | 12.465 | 0.646 | 1.548 |
| 32 | 42.469 | 13.806 | 0.325 | 3.076 |
| 64 | 67.054 | 13.131 | 0.196 | 5.107 |
| 128 | 69.492 | 12.617 | 0.182 | 5.508 |
| 512 | 68.488 | 13.264 | 0.194 | 5.164 |

The empty-list workload is 13.9% slower in the candidate. At measured depths 64–512, it is 5.1–5.5 times faster. This is a measured shallow-workload tradeoff alongside removal of depth-dependent duplicate scans. The coordinator ran the sequence before the headed browser comparison; OS activity was not controlled or measured. Two processes per condition, one payload size and included JS call/assertion costs do not establish a general allocator or original-client speedup. Raw timing outliers remain preserved. This comparison does not measure concurrent throughput, startup, frame rate or duration stability.

Runtime-only preparation (`python theseus/browser/prepare.py --runtime-only`) and the prepared dependency check (`python theseus/browser/bootstrap.py --check`) passed for the main and compatibility modules identified above. Prepared patch SHA-256 is `8b763bd478e619d1c95f37a429ecc840e04952b010d00d52007accc092638e2b`. This check is not a clean-checkout restoration replay. The [headed control pair](../../reports/performance/heap-control-20261011/source-audit-review.json) passes at 440.703 seconds cold and 438.797 seconds warm, with four reviewed empty-login images, 211 verified served/observer identities and 321 unchanged original inputs before/after. Only manifest metadata and the two Wasm modules differ between served conditions; observer and original-input identities match.

The [candidate review](../../reports/performance/heap-candidate-20261011/source-audit-review.json) records an incomplete comparison. Cold startup ends at 297.484 seconds because `Locator.screenshot` times out waiting for element stability; no login timestamp or final-state observation is available. Its last sampled state at 259.953 seconds was executing with two frames and no recorded runtime error. Two retained black startup images were reviewed. The subsequent warm-profile run reaches the original empty login screen at 457.859 seconds, with two reviewed login images and 1,070 frame advances during the 30.906-second observation. It follows an interrupted cold launch, so it is not equivalent to the control's fully primed warm profile. Its descriptive elapsed time is also longer than the control's; no startup gain is established. All 211 served/observer and 257 live source identities match, and all 321 original inputs match before/after.

The pair's observer failure remains preserved, not relabeled as an allocator failure or omitted from results. The source freeze was released after audit. Canvas capture must be corrected and matched measurements repeated; longer resource/progress testing remains outstanding. `currentBuildEvidence` remains `null` at frozen closeout.

## Remaining limits and handoff

The marker rejects a repeated free before intervening reuse. It cannot identify an invalid stale pointer after the same address has legitimately been reissued. Arbitrary guest header corruption and all concurrent arena-reclamation races are not solved. The change strengthens allocator ownership and removes the demonstrated private-list scans; it does not establish that duplicate frees explain an original-client failure, that startup is faster, or that 24/7 operation is reliable.

Reproduce from `theseus/tools/wine-assembly` after the coordinated build and outside an active source freeze:

```powershell
node test/test-heap-free-ownership.js --wasm build/wine-assembly.wasm
node test/test-heap-free-ownership.js --wasm build/wine-assembly.compat.wasm
node test/test-global-flags.js
node test/test-d3d-render-lifetime.js
```

Use the exact commands and test identities in the final validation record for the broader affected regression set. The coordinator must complete paired startup/resource measurements, reviewed visible initialization, and duration testing before widening the acceptance claim. [Performance](../performance.md), [threads and memory](../threads-memory.md), [compatibility](../compatibility.md), [issues](../issues.md), [changelog](../CHANGELOG.md) and [chair briefing](../chair-briefing.md) record the allocator correction; the final documentation reconciliation is recorded in [closeout](../closeout.md). Uncompleted measurements remain handoff work after reopening. No gameplay or revival investigation is part of this pass.
