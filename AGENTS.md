# BROCWIN maintenance continuity

**Frozen by user on 2026-10-11.** The runtime engineering run is terminated. Read [the closeout](wiki/closeout.md) before further work. Runtime/integration edits, builds, preparation, captures, runtime tests and service changes require the user to reopen the environment. Documentation reconciliation and knowledge verification remain within the closeout scope. The instructions below describe the maintenance workflow after reopening, not authorization to resume now.

User directive, 2026-10-11: the environment is frozen and the current work is closed. Follow [frozen closeout](wiki/closeout.md). Do not build, prepare, edit runtime/integration sources, start captures or change services until the user reopens work. Read-only documentation verification remains available. Earlier routine-maintenance authorization below is suspended during this freeze.

This directory is the BROCWIN project; the browser client is HEAV3NS-COMBO. The names begin on 2026-10-09. Preserve earlier Theseus names, evidence and contributor credits.

Before changing runtime or integration code, read [the maintainer orientation](wiki/orientation.md), [current compatibility](wiki/compatibility.md), [issues register](wiki/issues.md), and the relevant subsystem page linked from [the wiki](wiki/README.md). Follow [the maintenance contract](wiki/maintenance.md) and [build/recovery runbook](wiki/build-recovery.md). The dependency also has its own build and coordination instructions.

The original compiled game remains the authoritative application in one browser-native runtime. API fixtures support maintenance; they are not game acceptance. Do not replace original gameplay with demonstrations, a rewritten game or streaming. The old combat-only replacement gates are historical and do not narrow the full-game commission.

User clarification on 2026-10-10: port the client only. Original servers and SQL stay native, locally maintained apart from the browser port. Their native execution is the intended deployment boundary, not an incomplete port requirement. Client networking must continue to interoperate with them.

Maintain the established architecture. Operation Last Light closes open-ended foundational research; pursue bounded diagnosis, existing native/reference comparisons, regression repair and integrated refinement. Escalate changes to the commissioned objective, new infrastructure/expenses or weaker security controls; routine authorized maintenance proceeds.

Keep priorities in order: intermittent execution/network timeouts, skill inputs, rendering/text, victory/defeat/revival, then broader parity. Record a measured cause separately from hypotheses, preserve the failing evidence, and verify the original path affected by the repair. A passing route does not close an intermittent failure without evidence of its cause and correction.

For each meaningful runtime change, preserve build/source identities and regression results, update the affected wiki page and compatibility/issues status, and add a numbered change record and concise chair briefing. Preserve contributors and tools; no exclusive authorship is implied by the stewardship assignment. Run the knowledge generation/check commands after preparation. Keep current-candidate evidence separate from the broader historical gameplay baseline.

Do not build, prepare or edit frozen runtime/integration sources during an active capture. Seal its reviewed evidence and source audit before releasing its freeze. Existing copied evidence and sealed editions are immutable; add a correction or new version instead of rewriting them. A documentation release is not full-port completion.

Use only the isolated Theseus backend commands and retained process identities. General root launch scripts are not the browser-port runbook. `profile.py` provisions data and must not be imported for diagnostics. Use guarded read-only observations for diagnosis and keep credentials out of logs and documentation archives.
