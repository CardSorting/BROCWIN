# Licensing scope and third-party inventory

The existing parent repository uses MIT. [LICENSE](../LICENSE) preserves its notice and applies the same terms to eligible local project source and documentation. This preparation does not replace upstream licenses or claim rights in supplied game/platform inputs. [NOTICE](../NOTICE) records attribution boundaries.

| Material | Retained declaration | Distribution treatment |
| --- | --- | --- |
| Inherited JoySword project source | MIT; CardSorting / JoySword Online Contributors | Retain [original notice](CardSorting-MIT.txt); license applies only to works its licensors can license |
| Eligible BROCWIN integration and authored documentation | MIT; existing notices remain applicable | Include project LICENSE and NOTICE; do not alter sealed publication archives to add notices |
| Wine-Assembly pinned dependency | LICENSE: MIT, Vladimir Grichina, 2026; package.json: ISC | [Retained MIT text](Wine-Assembly-MIT.txt). **Unresolved metadata discrepancy:** confirm applicable terms before vendoring/distributing its source or local patch |
| websockets 17.1 | BSD-3-Clause | [Exact installed license](websockets-BSD-3-Clause.txt); installed package excluded from source repository |
| pefile 2024.8.26 | MIT | [Exact installed license](pefile-MIT.txt); research tool, not vendored source |
| Capstone 5.0.7 | BSD-style notices, including incorporated work | [Complete installed text](capstone-LICENSE.txt); do not reduce the package to one guessed copyright line |
| Playwright 1.55.0 | Apache-2.0 | [Exact installed license](playwright-Apache-2.0.txt); tooling/browser payloads excluded |
| Lua 5.1.5, Emscripten 4.0.15 and upstream npm/transitive tools | Declared research/build dependencies | Not distributed here. Any future binary/vendor release must inventory exact resolved versions and their notices; these are not covered by the project MIT license |
| Original client, native servers, KOM archives, game artwork/fonts and logos | No redistribution grant established by project provenance | Excluded; project license grants no rights to these materials |
| Installed/derived Microsoft DLL and shader-validator bytes | Separate platform provenance; redistribution grant not established | Excluded; local derivation is not a new open-source license |
| Raw captures, SQL backups and private configuration | Mixed provenance/private holdings | Kept in local custody; not automatically licensed for public release |

This inventory covers license files actually available in the local audit. It is **not** a complete transitive binary-distribution bill of materials. The upstream npm manifest declares pngjs, wabt, marked, Puppeteer, skia-canvas, v86 and optional native OpenGL packages; those installed trees remain excluded. If a release begins including them, obtain exact resolved license/NOTICE inventories first.

The documentation PDFs and Markdown are publication copies of authored research. Citations do not relicense the referenced sources, vendor trademarks or linked images. A source license does not confer rights in the entire original workspace.

`inventory.json` records the origin and SHA-256 of copied notices. Upstream/local originals were read without modification. Repository preparation is not a completed legal clearance review or a public release.
