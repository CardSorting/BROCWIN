# BROCWIN: Research State, Technical Handoff, and Continuation Roadmap

**Publication II — Institutional and technical handoff**  
HEAV3NS-BROCWIN · Version 1.0.1 · 11 October 2026  
Commissioned by MAJO, Executive Chair, HEAV3NS  
Prepared by Dr. GPT, the commissioned AI researcher

## A. Executive summary

BROCWIN is the internal identity of the synthetic Windows compatibility environment developed through HEAV3NS-COMBO, its browser-client integration. The original supplied MMO client executes x86 instructions through Wine-Assembly in WebAssembly; reconstructed Windows interfaces connect it to browser graphics, input, audio and file services. The native servers and SQL database remain local dependencies. The client was not rebuilt as a conventional web application. [E10–E16](evidence-index.md)

The final retained control reaches the original empty login screen at **440.703 seconds cold** and **438.797 seconds warm**. The audit checks 321 input entries before and after the runs and reviews four login image files. The cold control advances 1,073 frames over a 31.094-second login observation with no reported errors or progress failure. The warm counterpart advances 1,080 over 31.109 seconds. These establish an execution milestone, not complete gameplay compatibility. [E01–E03](evidence-index.md)

The environment is frozen and engineering is closed. The current prepared candidate includes an atomic allocator ownership repair, but its startup comparison is incomplete. A later reservation-rollback correction exists only as source-tested work. Final observer refinements remain incompletely validated. There is no verified 3× overall improvement or long-duration reliability result. The handoff preserves **BLOCKED** client acceptance and `currentBuildEvidence: null`. Corrected knowledge edition **1.4.1** is the documentation baseline. [E04–E07](evidence-index.md)

## B. Technical architecture

![BROCWIN architecture and the native backend boundary](figures/architecture.svg)

*Figure 1. Repository-derived architecture. Arrows represent execution, resource or transport relationships, not measured latency. The original native backend is outside the browser-client port.* [E10–E15](evidence-index.md)

| Boundary | Recorded role | Main repository locations |
| --- | --- | --- |
| Original application | Supplied PE executable, original libraries, scripts and KOM archives | `client/data/x2.exe`; original paths in `theseus/browser/generated/manifest.json` |
| x86 execution | Decoding, dispatch cache, Wasm execution and guest API thunks | `theseus/tools/wine-assembly/src/main.watx`, `07-decoder.wat`, `04-cache.wat` |
| Windows compatibility | PE/DLL loading, TLS, memory, synchronization, sockets and API contracts | Dependency `lib/pe.js`, `lib/dll-loader.js`, `src/api_table.json`, WAT handlers |
| Browser integration | Manifest selection, launch, workers, canvas and lazy resource mounts | `theseus/browser/main.js`, `index.html`, `serve.py`; dependency `host.js` and `lib/` |
| Presentation and interaction | D3D9 command translation to WebGL; DOM/DirectInput mediation; FMOD/DirectSound/WebAudio path | Wiki `graphics.md`, `audio-input.md` and their generated implementation/test routes |
| Native interoperability | Original packet bytes transported through `vln/1` WebSocket frames to fixed local services | `local_server_wire.js`, `network.py`, `theseus/runtime.py` |
| Native state | Original server programs and isolated local SQL | `theseus/compose.yml`, private configuration; SQL endpoint `127.0.0.1:15433` |

This is an application-focused compatibility environment, not a booted historical Windows system. Browser hosting does not imply that the entire MMO system is browser-only. Microsoft platform export adapters and a locally derived shader-validator component are distinct from original game code and require separate provenance. [E10–E16](evidence-index.md)

The original executable remains unchanged on disk. An earlier send-serialization repair installs a guarded wrapper in the mapped guest image under the original socket lock; loading also maps imports and relocations. A successor must preserve those distinctions rather than describing the executed image as wholly unmodified. [E17](evidence-index.md)

## C. Verified accomplishments

| Category | Accomplishment | Evidence boundary |
| --- | --- | --- |
| Completed integration | Original PE/DLL client executes through the browser integration; the native-service boundary is retained | Implementation records describe selected supported routes, not universal Windows support |
| Verified final control behavior | Original empty login screen and short continued frame progression in both profile conditions | No credentials entered; no gameplay tested in these startup controls |
| Built allocator contracts | Sixteen source regression suites pass; eleven ownership checks pass on each exact built main and compatibility module | Retained control fails nine targeted cases; original-client duplicate frees are not demonstrated |
| Source-only cleanup | Failed large-allocation reservation rollback passes two source-compiled cases and twelve affected source suites | Not included in prepared Wasm or patch; application integration pending |
| Historical gameplay | Latest 145806 review passes original login, character/town interaction, combat/skills, former area gate, failed-attempt rewards and town return | Older build; revival fails; no accepted pair of winning cycles |
| Integrity and documentation | Control inputs/source audit; sealed knowledge editions; explicit prepared/frozen source separation | Hash matches establish file identity within enumerated scopes, not behavioral correctness |

Sources: [E01–E09, E17](evidence-index.md). API fixtures, application replays and source-only findings are separate evidence classes. An older gameplay success must not be assigned to the final allocator candidate.

## D. Known limitations

Startup remains approximately seven minutes in the final control. There is one retained cold/warm pair at that condition, not a statistically powered trial. Browser warm-profile reuse does not mean OS or GPU caches were controlled. The candidate cold run ends on a screenshot-helper stability timeout before login is recorded; the subsequent warm-profile run reaches login at 457.859 seconds after interrupted priming. No supported end-to-end improvement follows. [E01–E04](evidence-index.md)

The reported control frame advances span approximately 31 seconds. The configured 60-second stall criterion exceeds that entire post-login window; empty error lists and subsecond sampled progress gaps must therefore be understood alongside the short duration and sampling limits. Sustained operational reliability remains unverified. [E01–E02](evidence-index.md)

Gameplay blockers include revival timing/eligibility, reliable combat cadence, small text and effects, short-input/focus behavior, intermittent ACK timeouts and broader repeated-session parity. The latest revival failure does not establish input loss as its cause. Historical loading stalls remain separately recorded. [E08–E09](evidence-index.md)

Kernel limits include incomplete loader-lock lifecycle, nonempty TLS callback coverage, unload reclamation and broader SIMD/API behavior. Atomic ownership prevents reproduced repeated frees before address reuse; it does not solve stale-pointer ABA or arbitrary guest-header corruption. Browser-local persistence is unconfigured, and broader Winsock completion paths remain incomplete. [E04, E09–E15](evidence-index.md)

The final observer source differs from the measured startup-pair observer. Eight unit tests passed before later refinements; those final frozen changes were not retested, and the proposed headed repair smoke produced no evidence. Use retained observer snapshots when interpreting old measurements. [E05–E06](evidence-index.md)

## E. Continuation roadmap

The following are research opportunities, **not authorization to resume**. No schedule, budget or promised performance outcome is implied.

| Horizon | Research question and possible work | Evidence needed before claiming completion |
| --- | --- | --- |
| Near term | Can another custodian understand and recover each recorded condition? Assign custody; verify hashes; preserve reports, sources, native references and private configuration; document artifact availability | Inventory with named owner, storage location and access rules; any restoration must occur in an explicitly authorized separate workspace |
| Near term | Can the observer classify startup without its known capture failure? Independently review its final changes and design moving-layout, paused-rAF, screenshot-geometry and passive-counter controls | Passing final-source observer tests and complete failure/success replay after engineering is reopened |
| Medium term | Does reservation rollback remain correct in canonical builds, and does allocator ownership help the original workload? Integrate source-only work, preserve exact patch/module identities, then measure matched conditions | Control failures, both canonical module regressions, source audit and independent application review; no assumed latency benefit |
| Medium term | Which costs dominate initialization and repeated use? Use bounded profiles and repeated/interleaved runs; retain cache, scheduler, browser and instrumentation conditions | Repeated samples and reported variability; causal evidence connecting a correction to an original path |
| Medium term | Can runtime progress and resources remain bounded for a specified duration? Define service continuity, idle/active workload, transitions, failure gates and stop policy | Stated observation duration and workload, complete logs, progress/resource histories, restart semantics and exceptions |
| Long term | Which other applications exercise the same contracts? Select a small, rights-cleared comparison corpus and establish native references | Separate per-application results; no extrapolation from this login milestone |
| Long term | Can archival execution survive dependency and browser changes? Preserve reference conditions, test restoration and document migration choices | Custody succession, recovery trials under renewed authority, versioned execution packages and recorded differences |

These horizons are sequential dependencies where appropriate, not a mandate to expand scope. A curator may choose continued preservation without further runtime development.

## F. Reproduction and custody

The repository root is `C:\Users\media\Downloads\JoySword-Theseus`. Earlier names remain valid paths. The publication edition lives in `theseus/publications/2026-10-11-v1.0.1/`; the authoritative project closeout is `theseus/wiki/closeout.md` and the sealed knowledge archive is `theseus/checkpoints/brocwin-knowledge-1.4.1.zip`. [E05, E18](evidence-index.md)

| Artifact class | Required holdings and custody treatment |
| --- | --- |
| Interpretation and provenance | This publication bundle, evidence index/ledger, source inventory, knowledge editions and contributor records |
| Reproducible implementation | Dependency lock, pin, prepared patch, integration sources, Wasm pair, generated adapters and manifest; full dependency source where retained |
| Final working-source differences | Four frozen source snapshots in `theseus/wiki/frozen-sources/`; inventory and independent review. These must accompany the prepared patch to represent the final source state |
| Original and platform inputs | Supplied client/DLL/KOM files, installed 32-bit platform inputs and generation metadata. Keep their existing custody and rights boundaries |
| Experimental evidence | Entire control/candidate report directories, retained host/observer snapshots, profiles, raw samples, source tests/logs, gameplay reviews and images |
| Private operational state | Local `.env`, account/service configuration, isolated SQL backups and owned-process records. Transfer privately under named custody; exclude credentials and database contents from publication |

The original installation derives from CardSorting/JoySwordOnline commit `4c39249b939d79c229e1fd4f63dfd462a90f9060`. Wine-Assembly is pinned to `d7854bc6c6bd0319ca33b5f31a465602e2ce0686`; the manifest and patch identify local changes. `dependencies.json` records websockets 17.1 and research-tool pins including Playwright 1.55.0, pefile 2024.8.26 and Capstone 5.0.7. Version declarations must be checked against a future recovery machine; they are not evidence that every currently installed tool has that version. [E16](evidence-index.md)

Read-only verification available under the present freeze:

```powershell
python theseus/knowledge.py --check
python theseus/knowledge.py --verify-release 1.4.1
python theseus/publications/2026-10-11-v1.0.1/verify_publications.py
```

The last command checks the delivered publication manifest and source-record hashes. It does not launch the client. An unchanged archive can still be verified when its working-source files are no longer present; full source-record verification requires the retained repository holdings.

**Historical launch procedure, executable only after explicit reopening:** verify the isolated native-service identities and configuration using the [build/recovery runbook](../../wiki/build-recovery.md). Its browser-host command is `python theseus/browser/serve.py --port 8766`, followed by opening `http://127.0.0.1:8766/` and using **Start client**. The final startup controls instead used the benchmark host and retained observer with a separate profile. The white paper appendix identifies their invocation and timing semantics. Do not substitute root launch/provisioning scripts, native-client commands or the changed live observer for those retained conditions. No launch or recovery was performed for this publication.

## G. Stakeholder decisions before any new phase

The Chair must decide whether the next activity is archival custody, a supervised exhibition or renewed technical research. That decision determines which success criteria matter. A preserved research object may remain valuable without meeting playable-game criteria; a public interactive deployment would need evidence the current commission does not supply.

Before development resumes, assign a technical owner and reviewer, explicitly release or supersede the freeze, approve a bounded question and acceptance gate, and allocate access to a separate recovery workspace. Confirm original-client/platform custody and permission to execute or redistribute each artifact. The upstream MIT declaration does not establish rights to game content or installed Microsoft binaries. Confirm access to private native-backend configuration and define a database backup/rollback policy before any mutation. [E16](evidence-index.md)

Resource choices include staff/reviewer time, protected storage for large evidence and backups, a comparable test machine, original local inputs and a supported browser/tool chain. This report assigns no cost estimate and requests no new service. Remote hosting, expenses, broader application coverage and weakened controls would require their own authorization. Publication delivery here is local; it is not a public-site upload.

## H. Final handoff

**Operational status:** engineering closed; environment frozen; knowledge baseline 1.4.1; prepared candidate and source-only changes separately preserved; client acceptance BLOCKED. The publication does not certify live service readiness.

**Outstanding questions:** final-observer correctness; canonical reservation rollback integration; reproducible startup gain; stated-duration stability; revival/repeated-session behavior; custody completeness for original/platform/native-backend dependencies.

**Recommended next actions:** accept this documentary handoff, designate artifact custodians, verify the local bundle and retained evidence, and decide whether any new research phase is warranted. Keep future work in a separately authorized record. The experiment described here is closed.

## References

The [shared evidence index](evidence-index.md) identifies E01–E18 and primary external references. Technical results refer to retained records; roadmap items are proposed research. [Publication III](03-technical-white-paper.md) provides experimental detail, full identities and threats to validity. [Publication I](01-environment-as-executable-artifact.md) provides the curatorial interpretation.
