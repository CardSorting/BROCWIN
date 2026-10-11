# Maintenance contract

**Frozen closeout, 2026-10-11:** the current work session is closed at the user's direction. See [closeout](closeout.md) for the prepared/source distinction, source-only reservation fix and unresolved validation. Engineering and environment changes require the user to reopen work; next actions below are handoff instructions.

[Wiki home](README.md) · [Changelog](CHANGELOG.md) · [Issues](issues.md)

For every meaningful runtime change, the maintainer must leave the following concrete record in a new change page and its evidence folder:

Use the [change template](changes/TEMPLATE.md) for the next numbered record.

1. Observed failure and reproduction, including the exact candidate and original-client path. Separate measured cause from unresolved hypotheses.
2. Implementation files and contract changed, with original/native references. Preserve original game behavior and explicit unsupported failures.
3. Regression command/results and control evidence. Include worker/render/backend routes relevant to the actual application.
4. Exact tested build/module/patch/source identities, native reference identities, environment and relevant reviewed artifacts. Do not substitute a current hash for an older tested one.
5. Verified behavior and remaining limits, updated subsystem page, compatibility/issue status, concise changelog and chair briefing.

The current [catalog](catalog.json) maps subsystem ownership to real source/tests/evidence. `knowledge.py` extracts hashes and manifest facts, copies selected review records exactly, checks local links, and detects stale generated output. It does not infer support from an API name or passing compilation. Run it after preparation and before sealing a wiki edition:

`currentBuildEvidence` must identify a review with matching Wasm, compatibility module and patch identities. Set it to `null` while a new candidate has no application review; the generated index will say so. Keep `gameplayBaselineEvidence` separately pointed at the retained broader baseline. The check refuses to attribute an older run to a changed build.

```powershell
python theseus/knowledge.py --write
python theseus/knowledge.py --check
python theseus/knowledge.py --seal-release 1.0.0
python theseus/knowledge.py --verify-release 1.0.0
```

A release is immutable: choose a new version after changes. Existing copied evidence may not be silently overwritten if its source changes. Preserve the original report and add an explicit correction/new ID. The generated index owns source hashes/counts; prose owns explanations, bounds and diagnosis. Avoid manually copying those changing facts into many pages.

Release verification checks the archive hash, member inventory, every included file and its embedded release record. It can validate an old edition after the working tree has advanced, without treating that old edition as current runtime evidence.

The [verification implementation](../knowledge.py), [eight guard regressions](../test_knowledge.py), and historical [validation record](generated/evidence/knowledge-validation.json) make these checks reproducible. Run `python theseus/test_knowledge.py` after changing the automation. The tests cover stale output, altered evidence, invalid paths/links, capture/build misattribution, edition overwrite, archive corruption, frozen source/record mutation and exact prepared/frozen drift pairs.

Edition 1.4.0 adds an explicit `frozenState` record to the catalog. Its digest and every inventoried file must match. Prepared-manifest checks remain strict by default; a frozen edition permits only the two exact old/new source hash pairs recorded in that immutable inventory, while retaining strict module and patch checks. Restoring the old observer or changing it again also fails the frozen drift check. This records an unprepared working source accurately without changing the runtime manifest or attributing older capture results to it.

The chair briefing answers what improved, what remains broken and whether it affects the mission. The maintainer page includes enough paths, commands, contracts and failure evidence to resume without the conversation. Maintenance remains open until the institution closes it; completion of an edition is not completion of the game port.
