# Direct3D9, WebGL and text

[Change 0013](changes/0013-runtime-startup-cache.md) caches pure shader translation and small DXT decode results with compiler identities and output digests. GPU handles and guest state are never persisted. Successful WebGL program creation checks link status after both stage compiles; failure preserves stage diagnostics and retirement. No driver-binary shader persistence or new gameplay rendering acceptance is claimed; see [performance](performance.md).

[Change 0011](changes/0011-draw-snapshot-copy.md) reduces existing neutral-command snapshot construction overhead using temporary null prototypes, retaining validated owned data, bounds, alias behavior, final prototypes and freezing. Control/candidate contract tests, shared rendering, lifetime, real Worker and native StretchRect checks pass. [Current 133104](../reports/browser/20261011T133104Z/review.json) renders town, Tree of El, sword attacks, Flame Geyser, Roll and first-area clear before an original authentication-related termination. It does not establish full effect fidelity or playable cadence: 20 town presentations/15.29086 seconds. Separate copy samples and synthetic timings are not a controlled whole-game speedup.

[Wiki home](README.md) · [Implementation and tests](generated/INDEX.md#graphics)

Original D3DX and shader-compiler code produces meshes, textures and shaders. Wasm D3D9 handlers validate objects/state and publish ordered commands; shared JS backends consume them in software or WebGL. Host composition positions the frame in the original window's client rectangle. Resource lifetime, thread ordering and command routing are as important as GLSL translation.

## Reproduced contracts and original paths

| Path | Implemented correction | Evidence boundary |
| --- | --- | --- |
| Startup / graphics recovery | Two/three distinct DISCARD backbuffers, queue rotation, normalized Reset parameters and ownership | Direct/Worker and WebGL regressions; FLIP/additional swapchains remain gaps |
| Texture setup / frame copies | Sparse transfers, matching mip tails and cube faces; ordered color StretchRect for supported surfaces | Native return/pixel references and real Worker path; volume/autogen, depth/stencil copy and some CPU-texture cases incomplete |
| Start Game shader linkage | Missing VS1.1 diffuse output defaults for the measured native cases | Preserve real/partial writes; not proof for arbitrary shader models |
| Character assembly | Nonindexed blending of 2–4 matrices, advertised capability 4 | Seven original mesh conversions match native bytes; indexed fixed palettes/tweening remain unsupported |
| Terrain shader compilation | Compact relative-address uniform arrays with bounds/local definitions preserved | 21,368 equivalent output components over 1,284 vertices / three original shaders; lower compile/link times are not an FPS result |
| Original UI text | Original font registration, NT cell sizing/advance/hint-state fixes; separate original/fitted right-phantom coordinates | 2,470/2,470 extents and 2,341/2,470 cropped monochrome bitmaps; 81 new matches, none lost; antialiasing and visible defects remain |

The texture, reset, blending and shader references live in `theseus/browser/reference/`. Preserve their source-DLL identities and OS bitness. For Reset, measured local x86/x64 writeback differs from published prose; the original DXUT reuses those output dimensions. Do not replace this observed contract with an untested assumption.

Historical [105626](../reports/browser/20261011T105626Z/review.json) renders town, both dungeons, attacks, Flame Geyser and Roll under the tested existing SSE policy. White frames and damaged small text persist. [Individually reviewed comparison](../reports/browser/20261011T105626Z/effect-comparison.json) finds dark particle surfaces in both 105626's Flame Geyser and historical 071553; different scene/awakening state prevents a full matched comparison. This is not evidence of a new SSE regression or correct fire-effect fidelity. Keep effect fidelity open on the tested combat path.

Current [123040](../reports/browser/20261011T123040Z/review.json) renders Ruben, Forest, basic sword action, Flame Geyser activation and Roll, the original failure result and town return. Small text remains damaged; these images do not establish complete effects fidelity. Adjacent Lake Noahs portal travel also renders and returns, without expanding its acceptance claim to a second dungeon cycle. No rendering redesign or cosmetic work was performed.

## Diagnose and repair

First distinguish absent game resources from a rejected draw, shader compile stall, bad transform, texture upload/lifetime error or compositor geometry error. Save the original error and the actual draw/shader/constant bytes before scratch reuse. `drawCapture` deliberately omits texture pixels, so it is not a complete scene replay. Use matching native references and direct/Worker/WebGL routes for changed commands. A missing RPC opcode range once trapped an otherwise tested StretchRect call in the actual game.

Run the relevant tests in the source index, plus the original transition that uses the operation. Keep compile-cache and browser-version differences visible in timing comparisons. Inspect final and manual screenshot sequences; automatic screenshots are not reviewed merely because files exist. Transient white combat frames recovered in `053844`; their cause remains unresolved. A running renderer and increasing presentation counter do not establish visual fidelity.

The [070137 input-maintenance replay](../reports/browser/20261010T070137Z/review.json) retains damaged small text and a white combat frame followed by scene recovery (requests 049–050). Native equivalence remains unverified. Its first town return renders terrain/buildings; this is visual coverage, not another resource-registry or TLS-liveness measurement. The `__bundle?f=fonts...` 404 is the optional bulk-fetch route: `lib/file-bundle.js` and `host.js` fall back to individual files. Keep both error records, but do not label this alone a missing-font failure or the text defect's cause.

[Change 0003](changes/0003-font-phantom-coordinates.md) repairs a measured source of distorted Tahoma outlines. Preserve the original right-phantom advance before fitted rounding; MIRP must not measure the already-rounded original bearing. The new 132-cell regression fails 81 cases on the preceding runtime and passes all 132 after repair. The broad comparison still has 129 mismatches. The original CreateFontA setup requests quality 4; the retained broad corpus uses quality 3 and cannot close the separate TextOut antialiasing gap. Keep outline bounds, bitmap equality and actual application review as separate evidence.

The [080540 font-candidate replay](../reports/browser/20261010T080540Z/review.json) reaches Ruben terrain/movement and the original Skills/help/tooltip and Options panels. The tooltip and Options labels still have visibly damaged text. All 30 manual/final images were reviewed and their hashes retained. This UI path establishes integration of the repair, not native visual equivalence; it does not exercise combat or revisit the white combat frame.
