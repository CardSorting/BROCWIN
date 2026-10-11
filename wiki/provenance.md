# Provenance and institutional handoff

[Wiki home](README.md) · [Existing provenance](../browser/provenance.json) · [Execution history](../browser/execution-history.json)

| Contribution | Attribution and evidence |
| --- | --- |
| Original client/server algorithms and game content | Original fork authors; individual authorship cannot be established from supplied binaries |
| Inherited installation, scripts, recovery and native checkpoint | CardSorting/JoySwordOnline and prior local contributors; root/Theseus provenance retained |
| x86/Wasm and browser platform foundation | Wine-Assembly contributors at the pinned commit; upstream credits human contributors, Claude Code and Codex |
| Local compiled platform algorithms / reference results | Microsoft Windows/Direct3D contributors; installed DLL hashes and local generation metadata retained |
| WebSocket implementation | Aymeric Augustin and websockets contributors, pinned in dependencies |
| Integration, targeted compatibility repairs, captures and this wiki | Codex `/root`; no subagents spawned in this maintenance pass; exact tools/tests recorded in its change evidence |
| Commission, names, curation and objective | User's HEAV3NS mandate and Operation Last Light; names introduced on 2026-10-09 |

“Astra owns technical continuity” is the stewardship assignment. It is not evidence that Astra, HEAV3NS-CODE or any single agent authored the entire port. Keep recovered original bytes, reconstructed compatibility behavior and unverified hypotheses separate.

Tools used for these maintenance passes: PowerShell, Python/ctypes, Node.js, Git/Bash, vendored WATX build/compiler, native Windows mapping/GDI APIs, pefile/Capstone, guarded read-only SQL, Playwright/Edge, repository tools and `apply_patch`. Microsoft primary documentation informs the input and TrueType contracts; a FreeType source check informed a rejected MD-selection hypothesis, with no FreeType code incorporated. The records distinguish static original-code recovery, reconstructed compatibility, controlled regressions and observed game behavior. No new infrastructure or paid resource was commissioned. A local native reference call is not a native-game launch.

[Change 0003](changes/0003-font-phantom-coordinates.md) preserves the exact original font hashes and native selected-font verification. Its private diagnostic aliases change only font names/checksums and are never mounted in the application. The actual repair executes the original glyph programs in the shared Wasm hint engine. Rejected variants, a failed test-source transform and an inconclusive cached-state observation remain in the sealed evidence; they are not attributed as shipped functionality.

## What a successor needs

Preserve this wiki and its sealed release inventory; integration source, dependency lock and source patch; original payload and locally derived platform inputs; private local configuration through an appropriate private transfer; selected report folders with their frozen candidates, reviewed images, requests, logs and native references; isolated SQL backups/checkpoint records. The wiki index can be read without those large artifacts, but it explicitly reports where they remain necessary to verify or replay a finding.

The scoped [AGENTS.md](../AGENTS.md) directs subsequent work to the current wiki and maintenance contract. It preserves the user's original-game and authority boundaries without making the curator retain the runtime dependency graph.

Reports and tools are intentionally ignored by the root Git configuration. The working tree also contains unrelated changes. This pass does not claim a Git commit or public release that was not made. The wiki's versioned local release manifest records its exact edition; commit reviewed source changes as a scoped normal repository operation when desired. Never archive `.env`, provisioner credentials, broad database dumps or game payloads into a public documentation bundle.
