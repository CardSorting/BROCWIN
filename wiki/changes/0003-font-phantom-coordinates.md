# 0003 — Preserve original NT font advance coordinates

[Wiki home](../README.md) · [Graphics](../graphics.md) · [Issues](../issues.md)

Date: 2026-10-10. Contributor: Codex /root, no delegated agents. BRC-003 remains open. This repairs one text contract in the integrated original-client runtime; it is not complete visual parity.

## Failure and measured cause

The original client's atlas builder measures and draws the shipped fonts through GDI, then reads red-channel coverage into its texture. The retained native corpus exposed distorted small Tahoma letters despite correct text extents. At positive LOGFONT height 12, the Wasm outline for `e` spanned six pixels where native GDI spanned four; `o` spanned seven where native spanned five. Several other letters were narrowed or shifted.

`tth_load_outline` rounded the advance phantom's **current** position and copied it into the **original** position. MIRP uses the original distance to decide the sign and applicability of a control value. Conflating these positions can erase or reverse the right bearing before `auto_flip`. The bounded `HeT` bytecode trace and native GGO_NATIVE outlines locate this before scan conversion. Keeping the original advance unrounded restores all 12 sampled native horizontal ranges, including the unchanged `H` and still-imperfect `&`. Range agreement does not establish complete outline equivalence.

The [sealed validation](../../reports/browser/font-followup-20261010T074425Z/validation.json) preserves the original-font identities, selected native bytes, before/after sources, complete outputs, source transforms, trace and rejected hypotheses. The [bounded original call sites](../../reports/browser/font-followup-20261010T074425Z/original-font-path.json) confirm the existing CreateFontA/extent/TextOut diagnosis; they are static evidence, not a live call trace. The original font setup requests quality 4, while this retained corpus measures quality 3. Antialiasing remains a separate gap.

## Implementation and regression

[10c1-truetype-hint.wat](../../tools/wine-assembly/src/10c1-truetype-hint.wat) now retains the unsnapped advance in the original right phantom for NT mode. The current phantom remains rounded; the established Win98 path is unchanged. Original fonts, glyph programs and game code are unchanged. There are no replacement glyph assets or host-rendered font substitutions in this repair.

[test_font_phantoms.cjs](../../browser/test_font_phantoms.cjs) calls canonical CreateFontW, GetTextExtentPoint32W, TextOutW and GetPixel using the original font bytes. Its [native fixture](../../browser/reference/font-phantoms.json) retains 81 affected cells and 51 previously matching controls, selected reproducibly from the larger corpus. All 81 affected cases fail before the repair; all 132 cases pass afterward. The reference selection script and failing result are preserved in the validation folder. [prepare.py](../../browser/prepare.py) includes the new test and reference in captured integration identities.

| Retained comparison | Before | Candidate |
| --- | --- | --- |
| Native text extents | 2,470 / 2,470 | 2,470 / 2,470 |
| Exact cropped monochrome bitmaps | 2,260 / 2,470 | 2,341 / 2,470 |
| Previously matching cases lost | — | 0 |
| Focused regression and control bitmaps | 51 / 132 | 132 / 132 |

The existing font-mode, font-cell and Win98 hinting regressions pass. The older 148-cell test still reports 136 exact bitmaps plus its known residual mismatches; its expectations were not weakened. All nine malformed-hdmx cases pass. Full canonical build, runtime preparation and pinned-patch verification pass. Exact candidate Wasm, compatibility module and patch identities are in the validation record and generated index.

Run from the repository root:

```powershell
node theseus/browser/test_font_phantoms.cjs
node theseus/browser/test_font_cells.cjs
node theseus/browser/test_font_modes.cjs
```

Run `node test/test-wat-truetype-hinting.js` from the dependency directory. Build and prepare using the [recovery runbook](../build-recovery.md), then replay the original text/UI path. Do not run retained diagnostic scripts into an already sealed evidence folder; use a new folder and preserve its source identity.

## Rejected alternatives and diagnosis cautions

Removing fitted phantom rounding lost 107 native bitmap matches with no gains. Changing the reported engine version to40 and resetting CVT/storage between top-level glyphs produced no improvement. Reversing MD opcode selection lost 104 matches. These were compiler source transforms used only in tests and are not shipped. The selected correction preserves fitted rounding and separates original coordinates instead.

A post-TextOut read of interpreter globals returned the last glyph generated for the cached strike, rather than the requested character. That report is retained but excluded from per-glyph failure conclusions. Direct hint calls and the bounded bytecode trace supplied the useful evidence. The first CVT-reset transform also rejected a nonunique source match before compilation; its failed attempt remains recorded.

Microsoft's [TrueType instruction contracts](https://learn.microsoft.com/en-us/typography/opentype/spec/tt_instructions) explain original/current points and MIRP. The [persistence contract](https://learn.microsoft.com/en-us/typography/opentype/spec/ttch01#glyph-programs-and-persistence) permits differing CVT/storage retention choices; it was a hypothesis to test, not evidence that the existing policy caused this defect. Local native results govern the measured behavior.

## Application validation and limits

The [sealed original-client replay 080540](../../reports/browser/20261010T080540Z/review.json) verifies login, channel selection, the saved level-10 character, Ruben terrain/buildings and left/right movement, Skills/help and the Flame Geyser tooltip/preview, then System/Options opening and closing. No skill allocation, binding or option is changed. The first 1.5-second help-close click leaves the overlay visible; a second 3.5-second click closes it. The Skills tooltip and Options labels still contain visibly damaged text.

The replay finishes by request while executing after 1,279.047 seconds and 3,570 presentations. All 242 frozen source identities, both modules and the patch match; all 29 requested screenshots and the final image were reviewed. Automatic images remain unreviewed. No terminal trap, ExitProcess or options timeout is recorded. All 54 original Lua throws and the two optional font-bundle 404 records remain. No execution breakpoints, watchpoints, draw capture or diagnostic guest writes were used. These presentation totals are not a performance benchmark.

The [control cautions](../../reports/browser/20261010T080540Z/control-request-cautions.json) retain an excessive wait rejected before input and a request with an ignored `inputs` field that only took a screenshot. Neither is a client execution failure. Use the preserved request-to-screenshot mapping when reproducing the manual review.

This replay does not exercise combat, dungeon transitions or progression gains. The preceding 070137 skill/awakening, defeat/reward and first-return pass belongs to the earlier live-keyboard build and remains independently preserved. A passing UI route does not close the earlier intermittent ACK failure.

129 of 2,470 retained bitmaps still differ. Full antialiasing, arbitrary sizes/glyphs/transforms, white-frame diagnosis and native visual equivalence remain incomplete. This change does not resolve intermittent ACK timeouts, complete skill reliability, victory/revival, audio or broader client parity. The native servers and SQL remain separately maintained locally, outside port scope.
