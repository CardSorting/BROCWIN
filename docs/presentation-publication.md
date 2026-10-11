# Presentation publication boundary

The commissioned poster-session delivery, edition 1.0.0, is selected for Git publication after the original source/documentation export. Its [index](../presentations/README.md) links the finished 14:45 video, conference poster, production book, transcript, captions, storyboard, glossary, Q&A and source slate.

## Selected immutable edition

The publication copies the 110 files enumerated in the original delivery manifest, the manifest itself, the sealed ZIP and its external receipt: 113 files in total. No raw utterance clips, temporary encoding files, new runtime captures or extra private holdings are selected. A directory-specific Git attribute preserves the original bytes, including text line endings. A single archive exception leaves other ZIP exclusions in place.

The ZIP's SHA-256 is `94f730473137123d2dca8185cb3c15ef732bdea10e7aae4ce46151a5303dcb63`. The delivery manifest's SHA-256 is `628099aea4f08289b6ff03e3a1cfe52d6c3f2a06bc73435285cb76f650864fed`. The [receipt](../presentations/2026-10-11-poster-session-v1.0.0/archive-record.json) records both. These inventories are unsigned.

The sealed local README, source slate and verification record continue to describe the state in which they were issued. Their historical statements that the local production package was not a public release precede this Git publication. The new index and this note document the later publication; the sealed originals are unchanged.

## Attribution and distribution scope

The selected illustrated presentation includes two archived login screenshots and their appearances in the poster, slides, video and production book. The original game interface, artwork and logos remain credited to their original developers and respective rights holders. Their inclusion in this commissioned presentation does not place them under the project's MIT license or establish a general redistribution grant. The [source slate](../presentations/2026-10-11-poster-session-v1.0.0/source-and-attribution-slate.md) identifies their custody paths and the unchanged architecture figure.

The ordinary source-release exclusions still cover original client/server binaries, resource archives, platform bytes, installed dependencies, raw report trees, account data, SQL backups and secrets. The illustrated presentation is a specific later selection, rather than a change to those general exclusions. The [release-preparation guide](open-source-release.md) and older source-publication records remain historical records of the narrower source export.

Narration uses Microsoft David Desktop; the simulated audience uses Microsoft Zira Desktop. These synthesized voices and the AI presenter designation are disclosed in the edition. No live conference appearance, new runtime demonstration, external endorsement or independent replication is claimed.

## Independent examination

Run `python scripts/check_presentation.py --archive` from the repository root to verify the distributed files and every ZIP payload. This standard-library check works in the standalone checkout and makes no runtime or service changes. Its scope differs from the original production verifier, whose historical paths and private source references require the retained parent workspace.

Examining the finished artifacts does not require restoration of the application. Repeating the computational experiment would require matching dependencies, original resources, authorized native services, excluded evidence and suitable permissions. The [frozen closeout](../wiki/closeout.md) records unresolved validation gates. Publication preserves the result and enables inquiry; it does not reopen engineering or promise that HEAV3NS will complete further investigations.
