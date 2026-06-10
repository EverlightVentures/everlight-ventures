# ARENA CAMERA-TILT BRIEF -- PHASE 2 (the Clash-Royale "depth" pass)

> Companion to `ARENA_LAYOUT_BRIEF.md` (Phase 1 = full-bleed flat arena). **Do Phase 1
> first and ship it.** This is the bigger, riskier pass: adding the slight tilted-camera
> depth that makes Clash Royale's board read as 3D instead of flat top-down.
>
> CLI handoff when ready: `read ARENA_CAMERA_TILT_BRIEF_PHASE2.md and implement it`.

---

## GOAL
Give the battlefield a shallow forward tilt so the near (player) end feels closer/larger
and the far (enemy) end recedes -- the Clash Royale "looking down a tilted table" look --
WITHOUT breaking deploy targeting, ranges, or the section-pan camera.

## WHY THIS IS PHASE 2, NOT PHASE 1
The flat-but-full-bleed fix (Phase 1) removes the black dead-space and is ~90% of the
"feels cheap" problem for low risk. The tilt is the last 10% of polish but it touches the
**coordinate transform that every draw call and the deploy-tap math depend on.** Get the
inverse wrong and troops deploy where you did NOT tap. That is why it is isolated here.

## PREREQUISITE (hard gate)
Phase 1 merged and verified: arena is full-bleed, towers scaled + corner/back-center
pinned, `node tests/full_match_test.js` green, deploys land correctly at zoom=1.

---

## THE COORDINATE SYSTEM YOU ARE MODIFYING (read before touching anything)
All in `game/index.html`. The camera today is **affine only** (offset + uniform zoom, no
rotation, no perspective):

```
function scaleX(){ return canvas.width  / ARENA_W; }      // ARENA_W,ARENA_H from engine (AK.ARENA_*)
function scaleY(){ return canvas.height / ARENA_H; }
function cam(){ return AK.game.camera || {offX:0,offY:0,zoom:1}; }
toX(gx) = (gx - cam.offX) * scaleX() * cam.zoom            // arena -> screen X  (linear)
toY(gy) = (gy - cam.offY) * scaleY() * cam.zoom            // arena -> screen Y  (linear)

// deploy tap -> arena (EXACT inverse of toX/toY; this is the make-or-break):
canvasToArena(clientX,clientY):
  nx = (clientX-rect.left)/rect.width;  ny = (clientY-rect.top)/rect.height;
  gx = nx*ARENA_W/cam.zoom + cam.offX;  gy = ny*ARENA_H/cam.zoom + cam.offY;
```

The section-pan beat (`game.camera.offY`) and the new convoy-journey overlay both ride on
this. Anything you add must collapse back to the current behavior when the tilt strength is 0.

---

## THE ONE DECISION (make this before writing code)
Two ways to get the look. Pick ONE; do not blend.

### PATH B1 -- CSS 3D tilt on the whole canvas  *(RECOMMENDED: cheapest convincing win)*
Keep ALL the 2D drawing exactly as-is. Tilt the rendered canvas bitmap with the GPU:
```css
#boardwrap { perspective: 1100px; }            /* tune 900-1400 */
#stage canvas { transform: rotateX(18deg);     /* tune 12-22deg */
                transform-origin: 50% 100%; }   /* pivot at the near/bottom edge */
```
- **Pros:** zero changes to `toX/toY` and every draw call; the whole field + units + baked
  background tilt together on the GPU for free; instantly reads as depth.
- **The trap you MUST solve:** the deploy tap now lands on a *tilted* plane, so
  `canvasToArena` must un-project the click through the inverse of that `rotateX`. A raw
  `getBoundingClientRect` ratio will be increasingly wrong toward the top of the screen.
  Implement a ray-to-tilted-plane un-projection (perspective + rotateX inverse) and verify
  taps at the TOP edge (far towers) land exactly. This is the entire risk of Path B1.
- **Cosmetic cost:** unit tokens tilt WITH the board (they "lie back" ~18deg) instead of
  standing up. For round token art this is acceptable. If it looks wrong, that pushes you to B2.

### PATH B2 -- in-canvas perspective warp  *(true Clash look, much bigger blast radius)*
Warp `toY`/`toX` so far rows compress toward a vanishing point, and draw unit sprites
**billboarded** (upright) on the tilted ground plane.
- **Pros:** troops stand up like real Clash; the ground tilts but characters do not.
- **Cons / blast radius:** `toX/toY` become non-linear -> you must rewrite `canvasToArena`
  as the matching non-linear inverse, AND audit every primitive that assumed linear space:
  range/AOE/Golden-Hour **circles become ellipses**, HP bars, the river/bridge rects, the
  deploy ghost, particle sizes. Each needs a per-y scale factor. High effort, high regression
  surface. Only take this if B1's lying-down tokens are a dealbreaker.

**Recommendation:** ship **B1**. It is a contained CSS + one-function-inverse change. Treat
B2 as a separate future epic, not part of this brief.

---

## SCOPE OF CHANGE (Path B1)
1. Add a single tunable `const TILT_DEG` (start 18) and `const PERSP_PX` (start 1100) near the
   render constants. A `TILT_DEG === 0` MUST be visually + behaviorally identical to today
   (free rollback switch).
2. Apply the perspective+rotateX via CSS on the canvas / its wrapper (above). Pivot at the
   bottom edge so the near row barely moves and the far row recedes.
3. Rewrite **`canvasToArena`** to un-project: take the normalized click, cast it onto the
   tilted plane using the same `PERSP_PX` + `TILT_DEG`, THEN apply the existing
   `/zoom + offX/offY` camera step. Keep the current linear math as the `TILT_DEG===0` branch.
4. Re-fit on resize/orientation: the tilt is CSS so `resize()` is mostly unaffected, but
   confirm the canvas backing size + `transform-origin` still pin the near edge after an
   orientation flip.
5. HUD: the energy bar / card tray / phase banners are DOM overlays OUTSIDE the canvas -- they
   should stay flat (correct). Confirm they are not children of the tilted element.

## ACCEPTANCE CRITERIA
- The board reads with clear depth (far end smaller/receded), full-bleed, no black margins.
- **Deploy taps land exactly under the finger across the WHOLE field** -- explicitly test the
  top 20% (far towers) and all four corners, both portrait sizes. This is the pass/fail gate.
- Section-pan (45/90/135s transitions) + the convoy-journey overlay still animate correctly
  with the tilt on.
- `TILT_DEG = 0` reverts to pixel-identical current behavior.
- `node tests/full_match_test.js` -> "FULL MATCH RAN CLEAN (no freeze)".
- No em-dash characters in any edited file. Bump the `?v=` cache version.

## TEST PLAN
1. Harness: `node tests/full_match_test.js` (no throw, peak units sane).
2. Manual on a real phone (the harness cannot verify tilt visuals OR tap alignment):
   deploy a card targeting the FAR enemy princess tower -- the troop must spawn there, not
   short of it. Repeat at each corner and mid-river. Misalignment toward the top = the
   un-projection inverse is wrong; fix before shipping.
3. Toggle `TILT_DEG` 0 -> 18 and confirm 0 is identical to pre-change.

## ROLLBACK
Set `TILT_DEG = 0` (and remove the CSS transform). Because nothing in `toX/toY` or the draw
calls changed under Path B1, this is a clean revert with no data/asset migration.

## OUT OF SCOPE (do NOT do here)
- Billboarded upright sprites / true 3D (that is Path B2, a separate epic).
- New art, new backgrounds, lighting/shadows from the tilt.
- Any engine-side (`engine.js`) change -- this is renderer + input only.
- Gathering Clash reference screenshots (that is a Perplexity/Gemini image-search job, not a
  Claude Code one -- keep the CLI on implementation).

## STOP-AND-ASK (the bot must pause and confirm with the operator before coding)
Confirm **Path B1 vs B2** with the operator first. B2 changes placement math and has a large
regression surface; do not start it without an explicit go.
