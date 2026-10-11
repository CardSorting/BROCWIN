# Repository walkthrough

This directory is the BROCWIN research project. HEAV3NS-COMBO is its browser integration. The engineering cycle is closed and runtime acceptance remains BLOCKED. The repository can explain the experiment without supplying proprietary payloads or launching a game.

## 1. Read the result

Start with [README](../README.md), then the [publication collection](../publications/2026-10-11-v1.0.1/README.md). The curatorial paper addresses preservation and the environment as medium; the stakeholder paper explains custody and continuation; the white paper documents architecture, methodology and limits. Cold/warm control login is 440.703 / 438.797 seconds. Full gameplay, 3× overall improvement and sustained reliability remain unverified.

The [closeout](../wiki/closeout.md) identifies prepared modules, source-only reservation cleanup and final observer differences. Corrected knowledge edition 1.4.1 supersedes the earlier summary, preserving twelve final passing source suites and incomplete observer validation. Older captures belong to their own builds.

## 2. Understand the layout

| Path | Purpose | Public/source preparation treatment |
| --- | --- | --- |
| `browser/` | Integration sources, dependency declarations and browser tests | Review eligible source; local generated/reference/patch directories ignored |
| `wiki/` | Maintainer explanations, findings and historical links | Authored documentation; copied generated evidence and source snapshots ignored |
| `publications/` | Standalone papers, figures, PDFs and integrity records | Retain reviewed authored sources/PDFs; exclude archives/HTML by default |
| `LICENSE`, `LICENSES/`, `NOTICE` | Project terms, retained notices and provenance boundaries | Include with any eligible source distribution |
| `.github/` | Issue/PR forms and documentation CI | GitHub recognizes these when this directory is the repository root |
| `scripts/check_repository.py` | Standard-library community-document checks | Safe for a clean source checkout; no runtime dependencies |
| `reports/`, `checkpoints/`, `tools/`, `runtime/`, `recovered/`, `recovery/` | Large evidence, sealed holdings, third-party installs and private/native state | Local custody, excluded from source staging |

The project lives inside a larger JoySword workspace. Existing runtime helpers resolve paths against that parent workspace and expect original local inputs. A standalone source checkout is **not currently demonstrated as a self-contained runnable installation**. Publication and wiki links may name local reports absent from a public clone; their absence must remain visible as a reproduction requirement.

## 3. Verify documentation safely

From this directory:

```powershell
python scripts/check_repository.py
```

It checks required community files, the newly authored guide/community links, template/workflow presence and byte-exact copied notices. It does not validate all historical wiki links in a source-only clone or build the runtime. It prints filenames and counts, not private file contents.

In the retained **parent workspace**, existing read-only archival checks remain available:

```powershell
python theseus/knowledge.py --check
python theseus/knowledge.py --verify-release 1.4.1
python theseus/publications/2026-10-11-v1.0.1/verify_publications.py
```

The last check requires cited evidence holdings. A transferred publication folder can use its `--archive-only` mode with the archive and checksum receipt. These checks verify scoped bytes and records; they do not establish gameplay compatibility.

## 4. Follow the architecture

Read the [architecture explanation](../wiki/orientation.md), then [execution](../wiki/execution.md), [loading](../wiki/loading.md), [graphics](../wiki/graphics.md) and [networking](../wiki/network.md). The client executes original x86 in Wasm; D3D9 reaches WebGL; input/audio use browser adapters; original packet bytes reach native local services through a constrained relay. No original game source rewrite is claimed.

The preserved dependency pin and patch reconstruct a prepared candidate, while frozen source snapshots preserve later source-only differences. They need separate provenance. The pinned Wine-Assembly license declarations disagree; see the licensing inventory before distributing upstream code.

## 5. Propose a contribution

Read [CONTRIBUTING](../CONTRIBUTING.md) and [GOVERNANCE](../GOVERNANCE.md). Documentation/citation/preservation proposals are within the current phase. For an experimental defect, describe the retained evidence rather than initiating a new replay. Runtime builds, tests, preparation, captures and service changes require explicit reopening. The [existing build/recovery runbook](../wiki/build-recovery.md) is a historical/conditional procedure, not a present quickstart.

## 6. Prepare a source release

Follow [the release guide](open-source-release.md). `.gitignore` excludes local/private/binary holdings and keeps source/documentation visible. It does not remove already tracked objects or prove redistribution rights. Preserve sealed archives locally; prepare a separate reviewed source tree rather than changing the frozen originals.
