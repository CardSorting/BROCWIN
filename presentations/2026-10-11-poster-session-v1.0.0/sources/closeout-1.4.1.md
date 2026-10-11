# Frozen environment closeout — 2026-10-11

[Wiki home](README.md) · [Chair briefing](chair-briefing.md) · [Frozen inventory](generated/evidence/frozen-closeout.json)

Edition 1.4.1 corrects the earlier sealed 1.4.0 closeout: the final rollback batch contains twelve passing suites, the observer refinements remain untested, and generated identities now explicitly separate prepared matches from frozen differences. Edition 1.4.0 remains immutable.

The user froze the environment and closed the current work on 2026-10-11. Knowledge edition **1.4.1** reconciles the retained findings. Runtime engineering, builds, preparation, captures and service changes are suspended until the user reopens them. This closes the work session with acceptance **BLOCKED** and unresolved issues retained for handoff.

The prepared manifest, main/compatibility modules and patch remain unchanged. The [generated identity](generated/identity.json) records their exact identities. A separate frozen inventory hashes 2,229 runtime, integration, source, test and selected evidence files. Two integration sources differ from the prepared manifest: `benchmark_startup.py` and `test_benchmark_observation.py`. The knowledge checker verifies their explicitly recorded prepared/frozen hashes and the complete frozen inventory; it does not attribute these later files to earlier captures. [Frozen source copies](frozen-sources/benchmark_startup.py) preserve the observer and [its fixture](frozen-sources/test_benchmark_observation.py). Any further unrecorded drift fails verification.

| Finding | Retained evidence and final disposition |
| --- | --- |
| Resource/artifact caching, 0013 | Loading/transfer/backing-memory savings measured; startup timing varies across six runs. Reproducible end-to-end gain and the 3x target are unproven. |
| Atomic heap ownership, 0014 | Sixteen source suites and eleven ownership checks on each built module pass. Startup profile attributes 2.589% of one active worker's sampled wall intervals to heap freeing. Deep-list microbenchmarks improve 5.1–5.5x; empty-list workload costs 13.9% more. These are bounded mechanism results. |
| Original startup comparison | Control cold/warm: 440.703 / 438.797 seconds. Candidate cold capture fails on canvas screenshot stability at 297.484 seconds. Later warm-profile login: 457.859 seconds with 1,070 frame advances over 30.906 seconds; interrupted cold priming prevents a matched comparison. No startup gain established. |
| Failed reservation rollback, 0015 | Preserved compiled control accumulates provisional reservations in both cases. Source-compiled correction passes both, with twelve affected source suites passing. Canonical builds, patch integration and original application validation are outstanding. |
| Gameplay | Latest gameplay review remains 145806 on its earlier build: former area gate, failed-attempt rewards and automatic town return pass; revival fails. No accepted two winning cycles or full visual/input parity. |
| Sustained reliability | No long-duration or 24/7 acceptance. Startup/short progress windows and synthetic fixtures cannot supply it. |

The observer repair is **partially validated**. Eight unit tests passed before the final trap-presence, Worker-presence, first-GPU ordering and PNG-dimension refinements; the final frozen files were not retested. The headed repair smoke did not run and produced no evidence directory. Moving-layout/paused-rAF controls, clipped screenshot geometry, passive-counter browser assertions and complete success/failure replay remain unverified. The earlier four visible lifecycle fixtures predate this repair. No application acceptance is transferred to these observer changes.

The [independent closeout review](../reports/frozen-closeout-20261011/independent-review.json) verifies all 2,229 inventoried files without mismatches and records agent handoffs. No owned benchmark or test process remained in the coordinator's read-only process inventory; existing host/browser processes and the unrelated Codex CLI were left untouched. The prepared module identity and frozen working-source identity are distinct: two observer files do not match the prepared manifest, and the source-only allocator edit is absent from its Wasm and patch.

`currentBuildEvidence` remains `null`; historical gameplay baseline stays `game-064427`. The [issues register](issues.md) retains BRC-019, BRC-020, BRC-021 and the gameplay blockers. Their next actions are conditional handoff work, with no execution authorized during this freeze. The [performance page](performance.md) retains measurements and observer limitations.

The source-only reservation fix and its test are preserved as [helper](frozen-sources/10-helpers.wat) and [fixture](frozen-sources/test-heap-reservation-rollback.js). The prepared dependency patch does not include them. Recovering this edition from the pin and prepared patch alone therefore restores the prepared candidate; the source snapshots are also required to reproduce the final working source. Do not build from those snapshots until work is reopened.

Read-only documentation verification from the repository root:

```powershell
python theseus/knowledge.py --check
python theseus/knowledge.py --verify-release 1.4.1
```

The edition archive is `theseus/checkpoints/brocwin-knowledge-1.4.1.zip`; its release inventory `theseus/wiki/releases/1.4.1.json` supplies the archive hash. Prior editions and copied evidence remain immutable. Credentials, database contents, original platform/game binaries, dependency checkout and large report artifacts remain outside the documentation archive and must stay in their existing local storage. The closeout does not assert current process readiness; retained PIDs and environment observations refer to the runs that recorded them. Original developers, upstream contributors and prior maintainers retain attribution. No commit, publication or deployment is part of this closeout.
