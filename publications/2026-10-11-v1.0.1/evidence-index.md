# Shared evidence index

HEAV3NS-BROCWIN publication edition 1.0.1 · 11 October 2026

This index supports all three papers. E-identifiers are shared across them. The [machine-readable ledger](evidence-ledger.json) records SHA-256 and size for every local source below. The [fact ledger](publication-facts.json) extracts the common control figures directly from retained JSON. Source files remain in their original locations; they are not silently relocated or republished.

## Evidence hierarchy and reading rules

Raw result records and their matching audits govern experimental claims. Wiki pages explain contracts and route readers to implementation. Corrected closeout 1.4.1 supersedes the earlier 1.4.0 summary: twelve final reservation suites pass, and the final observer refinements remain untested. Measured control, prepared allocator candidate, older gameplay builds and final working-source differences are separate conditions. File counts represent different enumerations, not compatibility scores.

## Local records

### E01. Final control raw measurements

- [theseus/reports/performance/heap-control-20261011/run-01/result.json](../../reports/performance/heap-control-20261011/run-01/result.json)
- [theseus/reports/performance/heap-control-20261011/run-02/result.json](../../reports/performance/heap-control-20261011/run-02/result.json)

### E02. Final control integrity and review

- [theseus/reports/performance/heap-control-20261011/source-audit-review.json](../../reports/performance/heap-control-20261011/source-audit-review.json)
- [theseus/reports/performance/heap-control-20261011/identity.json](../../reports/performance/heap-control-20261011/identity.json)

### E03. Four retained control image files

- [theseus/reports/performance/heap-control-20261011/run-01/first-visible-scene.png](../../reports/performance/heap-control-20261011/run-01/first-visible-scene.png)
- [theseus/reports/performance/heap-control-20261011/run-01/final-canvas.png](../../reports/performance/heap-control-20261011/run-01/final-canvas.png)
- [theseus/reports/performance/heap-control-20261011/run-02/first-visible-scene.png](../../reports/performance/heap-control-20261011/run-02/first-visible-scene.png)
- [theseus/reports/performance/heap-control-20261011/run-02/final-canvas.png](../../reports/performance/heap-control-20261011/run-02/final-canvas.png)

### E04. Allocator profile, contracts, microbenchmarks and candidate limits

- [theseus/reports/performance/kernel-profile-control-20261011/source-audit-review.json](../../reports/performance/kernel-profile-control-20261011/source-audit-review.json)
- [theseus/reports/performance/kernel-profile-control-20261011/profile-summary.json](../../reports/performance/kernel-profile-control-20261011/profile-summary.json)
- [theseus/reports/performance/heap-free-20261011/final-source-validation.json](../../reports/performance/heap-free-20261011/final-source-validation.json)
- [theseus/reports/performance/heap-free-20261011/compiled-validation.json](../../reports/performance/heap-free-20261011/compiled-validation.json)
- [theseus/reports/performance/heap-free-20261011/microbenchmark-summary.json](../../reports/performance/heap-free-20261011/microbenchmark-summary.json)
- [theseus/reports/performance/heap-candidate-20261011/source-audit-review.json](../../reports/performance/heap-candidate-20261011/source-audit-review.json)
- [theseus/reports/performance/heap-candidate-20261011/run-01/result.json](../../reports/performance/heap-candidate-20261011/run-01/result.json)
- [theseus/reports/performance/heap-candidate-20261011/run-02/result.json](../../reports/performance/heap-candidate-20261011/run-02/result.json)
- [theseus/wiki/changes/0014-heap-free-ownership.md](../../wiki/changes/0014-heap-free-ownership.md)

### E05. Corrected closeout and observer limits

- [theseus/wiki/closeout.md](../../wiki/closeout.md)
- [theseus/reports/frozen-closeout-20261011/independent-review.json](../../reports/frozen-closeout-20261011/independent-review.json)
- [theseus/reports/frozen-closeout-20261011/validation-1.4.1.json](../../reports/frozen-closeout-20261011/validation-1.4.1.json)

### E06. Frozen source inventory and retained differences

- [theseus/reports/frozen-closeout-20261011/frozen-state.json](../../reports/frozen-closeout-20261011/frozen-state.json)
- [theseus/wiki/frozen-sources/benchmark_startup.py](../../wiki/frozen-sources/benchmark_startup.py)
- [theseus/wiki/frozen-sources/test_benchmark_observation.py](../../wiki/frozen-sources/test_benchmark_observation.py)
- [theseus/wiki/frozen-sources/10-helpers.wat](../../wiki/frozen-sources/10-helpers.wat)
- [theseus/wiki/frozen-sources/test-heap-reservation-rollback.js](../../wiki/frozen-sources/test-heap-reservation-rollback.js)

### E07. Source-only reservation rollback

- [theseus/reports/performance/heap-reservation-20261011/control.json](../../reports/performance/heap-reservation-20261011/control.json)
- [theseus/reports/performance/heap-reservation-20261011/candidate-source.json](../../reports/performance/heap-reservation-20261011/candidate-source.json)
- [theseus/reports/performance/heap-reservation-20261011/source-suites.json](../../reports/performance/heap-reservation-20261011/source-suites.json)
- [theseus/wiki/changes/0015-heap-reservation-rollback.md](../../wiki/changes/0015-heap-reservation-rollback.md)

### E08. Historical final gameplay route and revival failure

- [theseus/reports/browser/20261011T145806Z/review.json](../../reports/browser/20261011T145806Z/review.json)
- [theseus/reports/browser/20261011T145806Z/revival-failure.json](../../reports/browser/20261011T145806Z/revival-failure.json)
- [theseus/wiki/acceptance-session.md](../../wiki/acceptance-session.md)

### E09. Acceptance and open contracts

- [theseus/wiki/compatibility.md](../../wiki/compatibility.md)
- [theseus/wiki/issues.md](../../wiki/issues.md)

### E10. Execution/loading implementation and account

- [theseus/wiki/execution.md](../../wiki/execution.md)
- [theseus/wiki/loading.md](../../wiki/loading.md)
- [theseus/tools/wine-assembly/src/main.watx](../../tools/wine-assembly/src/main.watx)
- [theseus/tools/wine-assembly/src/07-decoder.wat](../../tools/wine-assembly/src/07-decoder.wat)
- [theseus/tools/wine-assembly/src/04-cache.wat](../../tools/wine-assembly/src/04-cache.wat)
- [theseus/tools/wine-assembly/lib/pe.js](../../tools/wine-assembly/lib/pe.js)
- [theseus/tools/wine-assembly/lib/dll-loader.js](../../tools/wine-assembly/lib/dll-loader.js)
- [theseus/tools/wine-assembly/host.js](../../tools/wine-assembly/host.js)
- [theseus/browser/main.js](../../browser/main.js)

### E11. Graphics and input/audio account

- [theseus/wiki/graphics.md](../../wiki/graphics.md)
- [theseus/wiki/audio-input.md](../../wiki/audio-input.md)

### E12. Local native network boundary

- [theseus/wiki/network.md](../../wiki/network.md)
- [theseus/browser/local_server_wire.js](../../browser/local_server_wire.js)
- [theseus/browser/network.py](../../browser/network.py)
- [theseus/compose.yml](../../compose.yml)

### E13. Resource and persistence account

- [theseus/wiki/storage.md](../../wiki/storage.md)
- [theseus/browser/serve.py](../../browser/serve.py)

### E14. Memory contracts

- [theseus/wiki/threads-memory.md](../../wiki/threads-memory.md)
- [theseus/tools/wine-assembly/src/10-helpers.wat](../../tools/wine-assembly/src/10-helpers.wat)
- [theseus/tools/wine-assembly/src/09a-handlers2-runtime.wat](../../tools/wine-assembly/src/09a-handlers2-runtime.wat)

### E15. Earlier cache measurements and variation

- [theseus/wiki/performance.md](../../wiki/performance.md)
- [theseus/wiki/changes/0013-runtime-startup-cache.md](../../wiki/changes/0013-runtime-startup-cache.md)
- [theseus/reports/performance/validation-20261011/summary.json](../../reports/performance/validation-20261011/summary.json)
- [theseus/reports/performance/baseline-visible-20261011/run-01/result.json](../../reports/performance/baseline-visible-20261011/run-01/result.json)
- [theseus/reports/performance/baseline-visible-20261011/run-02/result.json](../../reports/performance/baseline-visible-20261011/run-02/result.json)
- [theseus/reports/performance/candidate-20261011/run-01/result.json](../../reports/performance/candidate-20261011/run-01/result.json)
- [theseus/reports/performance/candidate-20261011/run-02/result.json](../../reports/performance/candidate-20261011/run-02/result.json)
- [theseus/reports/performance/control-repeat-20261011/run-01/result.json](../../reports/performance/control-repeat-20261011/run-01/result.json)
- [theseus/reports/performance/control-repeat-20261011/run-02/result.json](../../reports/performance/control-repeat-20261011/run-02/result.json)

### E16. Dependency/provenance and supplied installation

- [theseus/provenance.json](../../provenance.json)
- [theseus/browser/provenance.json](../../browser/provenance.json)
- [theseus/browser/dependencies.json](../../browser/dependencies.json)
- [theseus/wiki/provenance.md](../../wiki/provenance.md)

### E17. Mapped guest send intervention

- [theseus/wiki/changes/0012-session-send-serialization.md](../../wiki/changes/0012-session-send-serialization.md)
- [theseus/reports/serial-ownership-20261011T142300Z/candidate-integration-validation.json](../../reports/serial-ownership-20261011T142300Z/candidate-integration-validation.json)

### E18. Recovery and prepared identity/custody

- [theseus/wiki/build-recovery.md](../../wiki/build-recovery.md)
- [theseus/wiki/generated/identity.json](../../wiki/generated/identity.json)
- [theseus/wiki/releases/1.4.1.json](../../wiki/releases/1.4.1.json)
- [theseus/checkpoints/brocwin-knowledge-1.4.1.zip](../../checkpoints/brocwin-knowledge-1.4.1.zip)
- [theseus/browser/generated/manifest.json](../../browser/generated/manifest.json)
- [theseus/browser/patches/wine-assembly.patch](../../browser/patches/wine-assembly.patch)

### E19. Actual retained observer implementation and sampling

- [theseus/reports/performance/heap-control-20261011/observer/benchmark_startup.py](../../reports/performance/heap-control-20261011/observer/benchmark_startup.py)
- [theseus/reports/performance/heap-control-20261011/observer/startup_telemetry.js](../../reports/performance/heap-control-20261011/observer/startup_telemetry.js)
- [theseus/reports/performance/heap-control-20261011/run-01/samples.jsonl](../../reports/performance/heap-control-20261011/run-01/samples.jsonl)
- [theseus/reports/performance/heap-control-20261011/run-02/samples.jsonl](../../reports/performance/heap-control-20261011/run-02/samples.jsonl)

## Interpretation and provenance

Publication I offers curatorial interpretation. Publication II proposes conditional future research. Publication III synthesizes retained technical evidence. None records new runtime experiments. MAJO supplies the commission and institutional framing; Dr. GPT prepares these publications. Original developers, CardSorting/JoySwordOnline contributors, Wine-Assembly human and agent contributors, Microsoft platform contributors, websockets contributors and Codex integration maintainers retain credit. The corrected rollback record identifies Codex /root/kernel_audit as implementer, /root/evidence_audit as independent reviewer and /root as closeout coordinator. The commissioning label is not a claim of academic credentials or exclusive engineering authorship.

Publication-time visual inspection examined the cold first-visible and warm final-canvas images in E03. Their visible empty credential fields and login buttons are consistent with the retained audit. The four audit records contain two unique image hashes; the record does not identify every reviewer. Image pixels and logos remain attributed to the original game; no game imagery is copied into this publication bundle.

## External primary references

External literature supplies context, not BROCWIN results. Consulted 11 October 2026. Links and bibliographic metadata are preserved; full external texts are not archived here.

- Rothenberg, Jeff (1999), *Avoiding Technological Quicksand*, CLIR report 77. [Publication](https://www.clir.org/pubs/reports/rothenberg/), [research agenda](https://www.clir.org/pubs/reports/rothenberg/research/).
- UNESCO (2003), *Charter on the Preservation of Digital Heritage*, adopted 15 October. [Primary text](https://www.unesco.org/en/legal-affairs/charter-preservation-digital-heritage).
- Variable Media Network, *The Variable Media Approach*. [Primary institutional account](https://www.variablemedia.net/e/welcome.html). The 2003 *Permanence Through Change* volume is identified as context; its PDF was not retrieved in full.
- Bellard, Fabrice (2005), “QEMU, a Fast and Portable Dynamic Translator,” FREENIX/USENIX ATC, pp. 41–46. [Primary paper](https://www.usenix.org/events/usenix05/tech/freenix/full_papers/bellard/bellard.pdf).
- WebAssembly Community Group, *Core Specification*, displayed 3.0 (2026-10-09). [Primary specification](https://webassembly.github.io/spec/core/). This is contextual, not BROCWIN conformance evidence.
- Microsoft, *PE Format*, Win32 documentation. [Primary documentation](https://learn.microsoft.com/en-us/windows/win32/debug/pe-format).
- Khronos WebGL Working Group, *WebGL Specification 1.0.3*. [Fixed-version specification](https://registry.khronos.org/webgl/specs/1.0.3/).
- Wine Project, *About Wine*. [Primary project description](https://www.winehq.org/about). No Wine performance claims are transferred to BROCWIN.
- Wine-Assembly contributors, dependency commit d7854bc6c6bd0319ca33b5f31a465602e2ce0686. [Pinned repository](https://github.com/vgrichina/wine-assembly/tree/d7854bc6c6bd0319ca33b5f31a465602e2ce0686). Local records establish the pin and patch; upstream online contents were not independently re-audited.

## Archive and access

The [archival manifest](archival-manifest.json) inventories the publication files and cited-source hashes. The publication ZIP includes authored documents, PDF/HTML copies, vector figure, ledgers and production/verification scripts. Original game/platform payloads, credentials, SQL contents and large report artifacts are excluded. Relative repository links require the original directory structure. URLs in PDF/HTML and the printed paths in this index provide alternative citation routes. No external upload or public hosting occurred.
