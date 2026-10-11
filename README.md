# HEAV3NS-BROCWIN

BROCWIN is a synthetic Windows compatibility research environment developed through **HEAV3NS-COMBO**, its browser-client integration. It executes the supplied legacy MMO client's original x86 code in WebAssembly, connecting reconstructed Windows contracts to browser graphics, input, audio and local native services.

**Status: engineering closed; environment frozen; documentation and preservation phase.** Client acceptance remains **BLOCKED**. The final control reaches the original empty login screen at **440.703 seconds cold / 438.797 seconds warm**, with 321 audited original-input entries and short continued frame progression. Complete gameplay compatibility, production readiness, a 3? overall speedup and long-duration reliability are unverified.

## Start here

- [Repository walkthrough](docs/walkthrough.md): layout, safe checks, architecture and contribution path.
- [Research publications](publications/2026-10-11-v1.0.1/README.md): curatorial paper, stakeholder handoff and technical white paper, in Markdown/PDF.
- [Frozen closeout](wiki/closeout.md): corrected knowledge edition 1.4.1, prepared/source differences and open gates.
- [Maintainer wiki](wiki/README.md): subsystem contracts, historical evidence and custody references.
- [Open-source release preparation](docs/open-source-release.md): distribution boundary and host decisions.

## What this checkout contains

The source/documentation tree includes local integration/helper source, dependency declarations, authored research and repository guidance. Original game/client/server binaries, KOM content, Microsoft-derived platform bytes, installed third-party trees, raw captures, SQL backups and secrets remain separate custody objects. A public source checkout is not a demonstrated turnkey runnable game distribution. Existing runtime tools expect the parent JoySword workspace and original local inputs.

```text
browser/        Browser integration and recorded dependency declarations
wiki/           Architecture, contract records, closeout and maintainer routes
publications/   Three research papers, figures, PDFs and archival metadata
docs/           Walkthrough, release preparation and historical README
LICENSES/       Retained third-party notices and licensing scope
.github/        Prepared issue/PR templates and documentation-only CI
scripts/        Standard-library repository-document checker
```

## Documentation verification

From this directory, run:

```powershell
python scripts/check_repository.py
```

In the retained parent workspace, read-only knowledge checks use `python theseus/knowledge.py --check` and `python theseus/knowledge.py --verify-release 1.4.1`. The [walkthrough](docs/walkthrough.md) explains which checks need excluded local artifacts. Runtime builds, tests, preparation, captures and service changes require explicit reopening; historical runbooks do not authorize them now.

## Contributing and community

Read [CONTRIBUTING](CONTRIBUTING.md), [GOVERNANCE](GOVERNANCE.md), [CODE_OF_CONDUCT](CODE_OF_CONDUCT.md), [SUPPORT](SUPPORT.md) and [SECURITY](SECURITY.md). Current proposals concern documentation, citations and preservation. The source repository is [CardSorting/BROCWIN](https://github.com/CardSorting/BROCWIN); private reporting channels still require owner configuration. No live support service is claimed. [CITATION.cff](CITATION.cff) identifies the research archive; cite the specific knowledge or publication edition used.

## License and provenance

Eligible project code and authored documentation use [MIT](LICENSE), continuing the inherited parent license and retaining contributor notices. [NOTICE](NOTICE) and [LICENSES/README.md](LICENSES/README.md) distinguish third-party work and excluded game/platform/private material. Wine-Assembly's retained LICENSE says MIT while package metadata says ISC; this discrepancy must be resolved before distributing upstream code or its patch.

The supplied installation derives from CardSorting/JoySwordOnline; Wine-Assembly supplies the x86/Wasm compatibility foundation. Original developers, upstream human/agent contributors, Microsoft platform contributors and local maintainers retain credit. The Chair commissions the research; the publication researcher does not claim exclusive engineering authorship.

BROCWIN/HEAV3NS-COMBO names date from 2026-10-09. Earlier Theseus paths and contributor history remain preserved. See [repository preparation changes](CHANGELOG.md), [research changes](wiki/CHANGELOG.md) and the [historical README](docs/history/legacy-theseus-readme.md).

The [source publication status](docs/publication-status.md) records the reviewed export and local-only helper exclusions.
