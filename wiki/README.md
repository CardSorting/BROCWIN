# BROCWIN maintainer wiki

**Frozen closeout, 2026-10-11:** the current work session is closed at the user's direction. See [closeout](closeout.md) for the prepared/source distinction, source-only reservation fix and unresolved validation. Engineering and environment changes require the user to reopen work; next actions below are handoff instructions.

**HEAV3NS-COMBO is the browser client. BROCWIN is the internal protocol/project identity.** These names were commissioned on 2026-10-09; earlier Theseus records retain their original names, identifiers and authorship. Wiki edition: **1.4.1**. Current client-port acceptance is **BLOCKED**; see the [final eleven-step report](acceptance-session.md). The current packet repair passes the earlier area gate; independent revival and two winning cycles remain incomplete.

Institutional scope: HEAV3NS-BROCWIN / HEAV3NS-COMBO, under Operation Last Light.

Historical 2026-10-11 runtime mandate: engineering work targeted the BROCWIN environment, preserving the original client and visible session. See [runtime performance](performance.md) and [change 0013](changes/0013-runtime-startup-cache.md). Earlier gameplay acceptance records remain historical; no additional gameplay investigation is authorized by this pass.

Scope clarification, 2026-10-10: this is the browser **client** port. Original servers and SQL stay native and locally maintained apart from it. Client interoperability is required; server porting is outside the commission. Earlier sealed records retain the scope wording in force when written.

Edition inventories live in `releases/`; local archives live in `theseus/checkpoints/brocwin-knowledge-VERSION.zip`. Verify this edition with `python theseus/knowledge.py --verify-release 1.4.1`; the sealed 1.4.0, 1.3.0, 1.2.0, 1.1.0 and 1.0.0 editions remain immutable and separately verifiable by version. Edition archives contain the wiki, selected evidence records, integration sources, native reference JSON and dependency patch; large original evidence and game/platform inputs remain separately preserved in this workspace.

Start with the [eleven-step acceptance report](acceptance-session.md), [chair briefing](chair-briefing.md), [newcomer orientation](orientation.md), and [build/recovery runbook](build-recovery.md). The [compatibility matrix](compatibility.md) distinguishes application observations from API tests. The [issues register](issues.md) sets the maintenance queue.

| System | Maintainer reference |
| --- | --- |
| x86 / Wasm execution | [Execution](execution.md) |
| PE loading, DLL lifecycle, Windows contracts | [Loading](loading.md) |
| Windows API compatibility and native oracles | [Windows contracts](windows-contracts.md) |
| Scheduling, TLS, shared and sparse memory | [Threads and memory](threads-memory.md) |
| D3D9, WebGL, shaders, textures, text | [Graphics](graphics.md) |
| Winsock, local transport, original services | [Networking](network.md) |
| DirectInput, DOM input, FMOD / DirectSound / WebAudio | [Audio and input](audio-input.md) |
| Files, archives and persistent state | [Storage](storage.md) |
| Reproduction, diagnosis and evidence | [Troubleshooting](troubleshooting.md), [validation](validation.md) |
| Technical change record | [Changelog](CHANGELOG.md), [latest original send serialization](changes/0012-session-send-serialization.md), [draw snapshot correction](changes/0011-draw-snapshot-copy.md), [heap arena correction](changes/0010-heap-arena-locality.md), [modifier repair](changes/0001-modifier-identity.md), [live keyboard state](changes/0002-directinput-live-state.md), [font phantom coordinates](changes/0003-font-phantom-coordinates.md) |
| Authorship, source distinctions and handoff | [Provenance](provenance.md), [maintenance contract](maintenance.md) |

The [generated index](generated/INDEX.md) records exact implementation/test paths, source hashes, dependency pin, current module identities and preserved review records. Generate it with `python theseus/knowledge.py --write`; verify freshness and links with `python theseus/knowledge.py --check`. [catalog.json](catalog.json) is the small maintained routing table, not a second API implementation list.

Original evidence stays in `theseus/reports/`, native references in `theseus/browser/reference/`, and the accumulated discovery log in [elsword-theseus.md](../tools/wine-assembly/docs/re-notes/elsword-theseus.md). The generated evidence copies preserve selected JSON records byte-for-byte for offline reading; their referenced images, frozen sources and logs remain in the original local reports. Do not interpret a missing artifact in a transferred checkout as a verified claim.

This wiki supersedes old **scope statements**, not historical observations. In particular the combat-only replacement gates in the original [Theseus README](../README.md) are archival and do not narrow the integrated MMORPG commission. New foundational research, additional infrastructure, expenses or weaker security controls require new authority. Future fixes, local reference checks and integrated regression work require reopening the frozen environment.
