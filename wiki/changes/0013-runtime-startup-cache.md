# 0013 - Observe and cache the BROCWIN startup boundary

Date: 2026-10-11. Authority: Executive Chair MAJO's runtime optimization mandate. Initial implementation: Codex /root. Evidence audit and documentation correction: Codex /root/evidence_audit. Original developers, Wine-Assembly and earlier maintainers retain attribution.

The engineering target is approximately one-third of control elapsed time. It is not an acceptance claim. Work is confined to the compatibility environment: no new original-client probes, disassembly, binary patches, gameplay inputs or native service changes. These retained runs report preserving the previously visible browser and host; they do not establish that those processes are still running.

## Observation and bounded changes

The first GPU frame was an empty surface, not the login screen. The discarded exploratory measurement is retained in `reports/performance/baseline-20261011`. Corrected [cold control](../../reports/performance/baseline-visible-20261011/run-01/result.json) and [warm control](../../reports/performance/baseline-visible-20261011/run-02/result.json) measure first visible scene, followed by manual image review. Browser ready is under two seconds; login takes 435.265 / 432.641 seconds. Renderer CPU time grows through the delay. Main-module compilation and browser launch are small contributors, not the established bottleneck.

Changes are bounded independently by their contracts. End-to-end measurements compare the combined candidate; they do not attribute its whole elapsed-time difference to an individual pass.

- [Startup observation](../../browser/startup_telemetry.js) and [runner](../../browser/benchmark_startup.py) record capped resource/API/compiler/frame observations, process CPU and page heap samples. The runner snapshots served runtime files, gives each condition a separate browser profile, and supplies only Start client. No gameplay or guest-memory instrumentation is installed.
- [Resource cache](../../browser/runtime_cache.js) verifies SHA-256 before reuse, coalesces identical requests, bounds persistent storage, and invalidates against prepared runtime identities. Storage failures fall back to the original operation. Full resource requests with cancellation signals and range requests retain the original transport. The original payload remains read-only.
- [Server](../../browser/serve.py) validates ETags for eligible runtime files. A correct content hash allows immutable browser caching; a mismatched query does not. Network configuration and ranged payloads retain their original policies and isolation headers.
- [Preparation](../../browser/prepare.py) mounts audio files with the existing sized lazy/range provider rather than downloading all music before execution. Paths, lengths and original hashes are retained. This changes resource timing, not audio APIs or content. No new media provider is introduced.
- [Artifact cache](../../tools/wine-assembly/lib/validated-artifact-cache.js) persists pure shader translation and small DXT conversion results. Typed input identity, compiler-source namespace, output digest and defensive copies prevent stale/corrupt/mutable results from being reused. Guest state and GPU objects are excluded. Memory and persistent serialized data are capped; large textures use the existing residency path.
- [WebGL backend](../../tools/wine-assembly/lib/gpu-backend.js) compiles both stages before linking. Successful creation asks for link status once; the failure path retains stage diagnostics and object retirement. [Worker integration](../../tools/wine-assembly/lib/d3d-render-worker.js) installs the same cache at the existing graphics boundary.

The adaptive scope is deliberately small: recorded hardware capacity selects one of two fixed cache budgets. `?runtimePolicy=balanced-v1` or `?runtimePolicy=conservative-v1` replays the choice; unknown policies fail explicitly. Neither policy changes guest scheduling, synchronization, gameplay or networking. No unverified scheduling configuration is enabled to pursue the target. Browser/OS jitter remains outside deterministic control.

Edge rejects IndexedDB cloning of compiled Wasm modules. This capability failure is remembered, and validated byte storage plus content-addressed streaming compilation is used on subsequent launches. A streaming path is not proof of an engine cache hit. Persisted shader artifacts are translated source, not GPU driver binaries. The artifact budget is eight million serialized code units and 128 memory entries, not a measurement of physical heap bytes; the resource-cache budget counts actual raw bytes. See [WebGL status-query guidance](https://developer.mozilla.org/en-US/docs/Web/API/WebGL_API/WebGL_best_practices) for the synchronization contract.

## Verification and handoff

The [performance report](../performance.md) and [six-run summary](../../reports/performance/validation-20261011/summary.json) record the completed startup comparison. Candidate cold/warm login takes 450.000 / 459.922 seconds. The completed [repeated cold control](../../reports/performance/control-repeat-20261011/run-01/result.json) and [repeated warm control](../../reports/performance/control-repeat-20261011/run-02/result.json), with the same presentation hooks, take 483.406 / 464.813 seconds. The candidate is 6.9% / 1.1% faster than that repeat but slower than the first control pair, so these single samples do not establish a reproducible startup improvement or the 3x target. Transfer and sampled backing-memory reductions remain measured benefits; translated-shader and decoded-texture caches record no login-workload hits.

Each benchmark keeps immutable served-host snapshots and raw observations under `reports/performance`. The timed candidate predates the Request-cancellation guard. The later [twelve-check validation](../../reports/performance/validation-20261011/validation.json), [existing fixture limitations](../../reports/performance/validation-20261011/existing-fixture-limits.json), and [visible login observation](../../reports/performance/validation-20261011/visible-runtime.json) retain their own bounds. They do not qualify subsequently changed sources. No sealed current-build application review is supplied by this pass; `currentBuildEvidence` remains `null`. Historical gameplay records belong to their earlier candidates; no new gameplay acceptance is inferred.

The measured runner observes only about 30 seconds after login; raising its startup timeout does not produce a duration test. Its served-file identities omit diagnostic runner/telemetry/HTTP-handler source hashes, and its page/process samples do not profile worker execution or broker service/wait costs. Kernel profiling, stronger matched startup comparisons, and long-duration resource/progress measurements remain required. This cache pass does not establish reduced underlying kernel overhead or 24/7 stability.

Reproduce from the repository root after bootstrap checks:

```powershell
python theseus/browser/benchmark_startup.py --label fresh-control --snapshot theseus/reports/performance/baseline-20261011/host --runs 2 --timeout 900
python theseus/browser/benchmark_startup.py --label fresh-candidate --runs 2 --timeout 900
```

Run sequentially with the same browser version and unchanged workload. Labels must be new. Cold means a new browser profile, not an emptied OS disk cache. Keep the existing visible session constant. Do not run builds or competing benchmarks during a timing comparison.
