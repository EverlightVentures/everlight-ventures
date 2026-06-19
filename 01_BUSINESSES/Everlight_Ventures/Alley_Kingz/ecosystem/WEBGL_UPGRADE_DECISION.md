# Alley Kingz x WebGL/Three.js -- Upgrade Decision (deep-dive, 2026-06-18)

8-agent parallel deep-dive (research + codebase + adversarial verify + synthesis). Question: can AK go
WebGL/Three.js for the "next-level" feel of the Japanese/Awwwards sites, and is it worth it?

## VERDICT
**Targeted juice layer in Canvas2D FIRST -> then a feature-flagged PixiJS renderer swap ONLY IF fun + art are
already handled. NOT a Three.js port. NOT a from-scratch rebuild.** ~80% of the "another level" feel (bloom,
impact flash, particle density, screen-space FX) is buyable in the existing Canvas2D without leaving the engine.

## WHY (honest)
- The thing tanking mobile FPS (37 `ctx.shadowBlur` + 29 `ctx.shadowColor` calls) is exactly what the GPU does
  for free -- but it's ALSO fixable in Canvas2D by pre-baking the glows. That's the clunk you feel.
- "Wow" is NOT your stated problem. You said the game "sucks" AFTER every juice feature shipped. The bottleneck
  is the core loop + missing card art -- a renderer port moves zero inches on that.
- PixiJS's headline win (batching THOUSANDS of sprites) doesn't apply -- AK runs ~150 sprites, not draw-call bound.
- Three.js is the wrong tool outright (3D engine; its Sprites can't even instance). 
- The port is technically clean (engine is render-agnostic, ~4,600 lines untouched; Canvas2D coupling ~800 lines
  in one module) BUT regression risk on a LIVE game is real (drawUnit ~260 lines, CSS tilt, clip-masking, AKDrip
  recolor, TILT2 warp all need re-validation).

## "WOW" TECHNIQUES ranked by impact-vs-effort
| # | Technique | Impact | Effort | Canvas2D? |
|---|-----------|--------|--------|-----------|
| 1 | Pre-bake glow/bloom to sprite sheets (shadowBlur once offscreen, blit at runtime) | Huge -- fixes FPS + keeps the glows you vetoed removing | Low | yes |
| 2 | Additive-blend particle bursts (`globalCompositeOperation='lighter'`) on cast/impact | High -- reads as bloom free | Low | yes |
| 3 | Fake chromatic aberration on heavy hits (board offset +/-1px R/B, 1 frame) | High -- instant impact cue | Low | yes |
| 4 | Tune existing hit-stop + screen-shake | High -- feel is timing | Low | yes |
| 5 | Pre-baked foil/holo rarity overlay (sprite) | Medium -- premium cards | Low-Med | yes |
| 6 | Selective bloom (true GPU) | High ceiling | High | PixiJS |
| 7 | GPGPU particle bursts (tens of thousands) | Spectacle, overkill at 150 units | High | PixiJS/WebGPU |
| 8 | Radial shockwave / heat-haze distortion shaders | Med-high, premium | High | shader |

Skip entirely (scroll-site-only, zero ROI): 3D hero models, vehicle-physics worlds, PBR configurators, wireframe-scroll.

## RECOMMENDED PATH
- **Phase 0 -- Canvas2D juice pass (THIS WEEK):** techniques #1-#5. ~12-20 hrs, $0, LOW risk, no engine touch.
- **Phase 1 -- finish card art + core-loop fun (PARALLEL, highest leverage):** your actual stated problem; gate everything behind it.
- **Phase 2 -- feature-flagged PixiJS renderer swap (ONLY if Phase 0 wow falls short AND Phase 1 is handled):**
  replace the ~800-line Canvas2D module with a PixiJS renderer reading the same `AK.game` contract; engine untouched.
  ~2-3 weeks, $0 licensing (~476KB bundle), MED-HIGH risk -> mitigate with the feature flag (Canvas2D fallback stays shippable) + real-browser verification.
- **Never:** Three.js port or ground-up rewrite.

## WHAT IT FIXES vs WON'T
Fixes: mobile FPS clunk (Phase 0, pre-bake glows), premium impact feel, the "be second" differentiation.
Won't fix: a not-fun game (renders the same loop prettier), a draw-call problem we don't have, 2D wins via Three.js.

## FASTEST PATH to ~80% of the feel (this week, $0, zero rewrite)
1. Pre-bake glow/bloom to sprite sheets (biggest single win; recovers FPS + keeps the vetoed glows).
2. Additive-blend particle bursts on cast/impact (free "bloom").
3. Fake chromatic aberration on heavy hits (+/-1px R/B, 1 frame).
4. Tune hit-stop + screen-shake (already in engine).
5. Pre-baked foil/holo rarity overlay.
6. Finish the card art -- the actual stated problem; highest-leverage hours.

Renderer LAST, not first. Note: pre-baking the glows is also the operator-sanctioned fix for the shadowBlur FPS cost
(do NOT strip the effects -- pre-render them).
