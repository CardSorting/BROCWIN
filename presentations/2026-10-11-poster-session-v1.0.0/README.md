# BROCWIN Research Poster Session

This package presents the completed BROCWIN experimental cycle for an audience encountering the project for the first time. The main result is original-client execution to login under retained browser-hosted conditions, with short frame progression and scoped input identity. It does not establish a complete port, whole-application acceleration or sustained reliability.

Commission: MAJO, Executive Chair, HEAV3NS. Presenter: Dr. GPT. Primary source: BROCWIN Technical White Paper 1.0.1, 11 October 2026. Technical baseline: corrected closeout 1.4.1.

## Deliverables

| Artifact | Use |
| --- | --- |
| [Finished narrated video](brocwin-poster-session.mp4) | 1920 × 1080 poster walkthrough with local synthesized voices, simulated Q&A, 28 chapter markers and burned captions. |
| [Complete delivery ZIP](brocwin-poster-session-package-1.0.0.zip) · [Checksum receipt](archive-record.json) | Video, mixed narration master, editable sources, poster, documents, captions, evidence and hash inventory. |
| [Production book](production-book.html) · [PDF](production-book.pdf) | Local player and complete script, storyboard, glossary, Q&A, transcript, attribution and source mapping. |
| [Conference poster PDF](research-poster.pdf) · [SVG](research-poster.svg) · [PNG](research-poster.png) | 48 × 36 inch landscape poster; vector PDF/SVG and 5760 × 4320 raster copy. |
| [Presenter script](presenter-script.md) | Exact spoken text and production direction in Dr. GPT's commissioned role. |
| [Timed storyboard](storyboard.md) · [CSV](storyboard.csv) · [Timeline](timeline.json) | Every visual and spoken segment, with waveform-derived scene timecodes. |
| [Glossary](glossary.md) · [Audience Q&A](audience-qa.md) | Plain-language terms and eight evidence-bounded answers. |
| [Captions SRT](captions.srt) · [WebVTT](captions.vtt) | Reusable caption files matching the rendered narration. |
| [Transcript](transcript.md) · [Text](transcript.txt) | Complete spoken presentation including simulated questions and credits. |
| [Source and attribution slate](source-and-attribution-slate.md) | Institution, original software, dependencies, documented research roles, and production attribution. |
| [Claim matrix](claim-source-matrix.md) · [Source hashes](source-ledger.json) | Traceability and explicit observed/interpretive boundaries. |
| [Verification record](verification-record.json) | Container, duration, captions, assets and frozen/publication integrity results. |

The commission's “1215 minutes” is interpreted as **12–15 minutes**. This edition targets **14:45**. Its “5.15.5” allocator range is resolved from the paper as **5.1–5.5×**. These interpretations are recorded rather than silently changing the measured claims.

The video is a narrated poster session, not footage of a physical conference or an avatar performance. The first spoken line is the commissioned ontological question. Original stills retain their aspect ratios and are labeled archival evidence. No experiment is reopened, no game is launched, and no native service is changed.

## Reproduction of the presentation

Run from the repository root using the installed Python environment with Pillow and the repository's existing local Markdown and Playwright packages. Static rendering uses the installed Edge channel. The speech script uses installed Microsoft David and Zira Desktop voices. FFmpeg and FFprobe must be available on PATH.

```powershell
python theseus/presentations/2026-10-11-poster-session-v1.0.0/build_package.py
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ./theseus/presentations/2026-10-11-poster-session-v1.0.0/synthesize.ps1
python theseus/presentations/2026-10-11-poster-session-v1.0.0/render_video.py
python theseus/presentations/2026-10-11-poster-session-v1.0.0/build_package.py --finalize
python theseus/presentations/2026-10-11-poster-session-v1.0.0/verify_package.py
python theseus/presentations/2026-10-11-poster-session-v1.0.0/seal_package.py
```

These are presentation-export commands, not compatibility-runtime build or recovery instructions. Preserve an already delivered edition before changing its materials. No cloud voice service, upload, publishing or public deployment is used.

Utterance timings come from synthesized WAV files. Cue subdivisions within a sentence are character-proportional estimates, documented in the storyboard. Silence between scenes and end holds is included in the actual video duration. The voice is uniformly time-adjusted to fit the duration target; the production record records that factor.

The ZIP includes the mixed narration master and production sources. Regenerable utterance clips, the raw mix and temporary rendering checks remain outside the ZIP. The manifest and external receipt are unsigned local integrity records.

## Evidence and access

The exact primary paper and source index are included in `sources`. Their original relative links require the retained repository structure; consult the printed source paths, source ledger and full original archive for recovery. This is a presentation bundle, not a complete runtime restoration kit. It excludes credentials, private database state, game/platform binaries and most large raw reports. Unchanged screenshot copies and derived charts are in `assets`.

The package is a local commission deliverable. Original game imagery and platform material carry separate rights; no redistribution permission is implied by the compatibility-source license. Contributor credit remains with inherited and newly developed work. HEAV3NS's experimental cycle is closed; future researchers need suitable access, matching artifacts, permissions and a separately authorized workspace.

THE WORK NO LONGER DEMANDS AN AUTHOR.
