# HEAV3NS-BROCWIN publication edition 1.0.1

11 October 2026 · Commissioned by MAJO, Executive Chair · Prepared by Dr. GPT

The engineering experiment is closed. These publications explain and preserve existing work; they introduce no runtime experiments and confer no new engineering authorization. Corrected knowledge closeout 1.4.1 governs the technical baseline.

| Publication | Markdown source | PDF publication copy |
| --- | --- | --- |
| I. Curatorial research | [The Environment as an Executable Artifact](01-environment-as-executable-artifact.md) | [PDF](01-environment-as-executable-artifact.pdf) |
| II. Stakeholder handoff | [Research State, Technical Handoff, and Continuation Roadmap](02-handoff-and-roadmap.md) | [PDF](02-handoff-and-roadmap.pdf) |
| III. Academic technical report | [Browser-Hosted Execution of a Legacy Windows MMO Client](03-technical-white-paper.md) | [PDF](03-technical-white-paper.pdf) |

[Shared evidence index](evidence-index.md) · [Index PDF](evidence-index.pdf) · [Evidence hashes](evidence-ledger.json) · [Common facts](publication-facts.json) · [Archival manifest](archival-manifest.json) · [Archive record](archive-record.json) · [Complete publication ZIP](brocwin-publications-1.0.1.zip)

The bundle contains Markdown sources, searchable PDF copies, static HTML reading copies, an authored SVG architecture diagram and Mermaid source, an evidence ledger, extracted facts and production/verification scripts. It excludes original game/platform binaries, game screenshots, database contents, credentials and large reports. Repository citations resolve in the retained workspace; external references link to primary sources. The PDFs are publication copies, with no PDF/A certification claimed.

Verify the complete local handoff from the repository root:

```powershell
python theseus/publications/2026-10-11-v1.0.1/verify_publications.py
python theseus/knowledge.py --check
python theseus/knowledge.py --verify-release 1.4.1
```

For a separately transferred publication folder without its original repository holdings, use `verify_publications.py --archive-only`. The manifest and archive-record files are hash records, not externally signed attestations. Integrity checking requires trust in the delivered baseline.

No public hosting, deployment or journal submission occurred. The local publication commission is delivered through these files. Future corrections require a new edition; sealed engineering and knowledge artifacts retain their existing versions.

Publication revision 1.0.1 places the Python byte relay outside the browser boundary in the vector diagram. The earlier local 1.0.0 archive remains preserved. This is an editorial correction; runtime sources and evidence are unchanged. Keep archive-record.json beside the ZIP as its external checksum receipt.
