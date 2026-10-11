# Newcomer orientation

**Frozen closeout, 2026-10-11:** the current work session is closed at the user's direction. See [closeout](closeout.md) for the prepared/source distinction, source-only reservation fix and unresolved validation. Engineering and environment changes require the user to reopen work; next actions below are handoff instructions.

[Wiki home](README.md) · [Build/recovery](build-recovery.md) · [Issues](issues.md)

The scoped [maintainer instructions](../AGENTS.md) make this knowledge and maintenance contract an entry point for future work in the Theseus tree.

The application is the supplied `client/data/x2.exe`, its original DLLs, scripts and KOM archives. Source code for the game is unavailable. Wine-Assembly interprets its x86 instructions in WebAssembly and supplies reconstructed Windows services. The browser renders locally through WebGL and receives normal DOM input. Five original native server programs and the isolated SQL database still provide backend behavior through a local byte relay. This is one integrated application; a successful standalone API test is supporting evidence, not game acceptance.

## First hour

1. Read the [chair briefing](chair-briefing.md), [compatibility matrix](compatibility.md), and prioritized [issues](issues.md). Do not infer full parity from a login screenshot or presentation count.
2. Run the read-only checks in the build runbook. Verify the pinned dependency, current manifest and source hashes before changing anything. The root workspace contains unrelated inherited changes; do not reset it.
3. Follow one subsystem through the generated index: original call → WAT handler → host/RPC → browser or fixed local service. The dependency's `src/api_table.json` and `src/main.watx` own API IDs and compilation order.
4. Read one failure and its correction: `022355` lost first-return terrain; executable TLS initialization exposed `033829`'s synchronous DLL-attach wait failure; scheduled callbacks and separate DLL TLS later passed returning sessions. This chain explains why fixes need both contract tests and a full client replay.
5. Reproduce the smallest existing regression for the issue, then replay its actual game path. Follow [validation](validation.md) and the [maintenance contract](maintenance.md) to retain build identity and update this wiki.

## Terms and boundaries

- **Guest** means original x86 instructions, addresses and Windows objects inside Wasm. **Host** means JS/browser adapters or the local relay. A guest address is not necessarily a contiguous Wasm address.
- **Reconstructed** means compatibility behavior we implement; it does not mean recovered game source. **Recovered** means inspected original bytes or data, with a source hash.
- **Contract pass** is a bounded API or renderer comparison. **Application observation** identifies a particular original-client route, build and reviewed artifact. Neither implies every game route works.
- **Native reference** means a measured Windows API/COM result or the inherited native game checkpoint. Launching the Windows game does not test the browser port.
- **BROCWIN** is not a new game network packet protocol. The relay still carries existing `vln/1` transport frames and unchanged original game payloads.

Runtime sources live in an ignored pinned dependency checkout. The portable preservation mechanism is the dependency pin plus `theseus/browser/patches/wine-assembly.patch`, including local regression sources. Reports, original binaries, generated adapters, private environment settings and SQL backups are local inputs, not public source artifacts. Preserve them on institutional storage already authorized for this workspace; no external publication is implied.
