# Alley Kingz -- RENDER MODE CANON

> Captured 2026-07-17 from Rich's voice brief. This is the organizing law that
> sits ABOVE the per-system design docs (WORLD_DESIGN, PVP_CLANS_ARCHITECTURE,
> AK_STORY_MODE_DESIGN, FORTNITE_ELEMENTS_ARCHITECTURE, etc.). Read this first,
> then the per-mode doc.

## THE ONE LAW

**One canonical game state. Many render modes. State reflects across every mode.**

Alley Kingz is not one game with one look. It is ONE persistent world-state
(your base, your buildings, your walls, your progress, your bloodline) rendered
through DIFFERENT engines for DIFFERENT modes. Each mode is a SEPARATE build-out
(different graphics, different maps, different camera) but every mode reads and
writes the SAME underlying state. What you change in one mode shows up in the
others. That reflection is the whole point.

## THE RENDER-MODE MATRIX

| Mode | View / Engine | Look and Feel | Reference |
|------|---------------|---------------|-----------|
| **RPG Overworld** (district + world map) | **3D** | WoW / RuneScape. This IS the game's home view. You walk your character through a real 3D district. | the WoW/RuneScape target |
| **Building Interiors** | **MP4 video** | Enter a building, play a cinematic video. Fine as-is, no 3D needed. | current hub behavior |
| **Base / Dungeon Defense** (builder mode) | **2D top-down** | **Clash of Clans.** Their artwork style: rocks and stones for barricades, movable/adjustable buildings placed on a grid, walls you lay down. This 2D base layout is what protects your base during raids. | PVP_CLANS_ARCHITECTURE.md |
| **Story Mode** | Comics + branching visual novel | "Surviving High School" style: decision points, branch trees. This is Crown Bloodline. | AK_STORY_MODE_DESIGN.md, STORYLINE_CANON.md |
| **Boss Battles** | (own build-out) | Set-piece encounters. | COMBAT_FEEL_SPEC.md |
| **Mini-games** | Lane-push card battler | **Clash Royale** style. | -- |
| **Gulag** | **First-person shooter** | FPS mode, the Warzone-gulag moment. | FORTNITE_ELEMENTS_ARCHITECTURE.md |

## THE PERSISTENCE RULE (the non-negotiable)

The modes are NOT isolated. State flows between them:

- You enter **Defense mode** (2D Clash-style), move your buildings, lay down a
  wall, rearrange your base for raid protection.
- You **exit** back to the **RPG Overworld** (3D WoW/RuneScape).
- **The RPG view now reflects those changes.** Your buildings are in their new
  positions. The wall you built in 2D is now viewable, standing, in the 3D
  world. Same base, two renders, one truth.

> "the layout and base layout in defense that we do clash of clan style is the
> 2D... but when we're actually playing the game and we're doing the RPG we're
> doing the wow/runescape look... it's all reflective of the same build."

This means there is a **shared world-state layer** (building list, positions,
walls, upgrades, tier) that every renderer subscribes to. The 2D defense editor
WRITES it. The 3D overworld READS it. So does the raid sim. No mode owns the
truth; the state layer does.

## THE PER-HERO-MODEL RULE (added from Rich's GLB note, 2026-07-17)

The 3D model that walks the overworld is NOT hardcoded to one dog. **Whoever the
player has selected as their hero loads THAT hero's GLB.**

> "whoever's using that hero uses that GLB. Since I'm not using jagged anymore
> and I'm using bcardd, we need to use bcardd. But if someone else was using
> jagged as their hero, now we have jagged as their anim."

- Rich runs **$BCARDD** so the overworld loads `assets/models/bcardd.glb`.
- A player who picked **Jagged** loads `assets/models/jagged.glb`.
- `jagged.glb` is NOT dead. It is Jagged's animation set, valid for anyone who
  picks Jagged as their hero.

Implemented in `game/systems/hub3d.js` as a `HERO_MODELS` registry + `heroModel()`
resolver keyed on the selected hero (`window.AK_HERO`, or the player object's
`heroId` / `avatarCard`), defaulting to $BCARDD until a hero-selector sets it.
**Add one row to `HERO_MODELS` per new hero GLB.** Same principle applies to the
2D avatar (card image + idle/walk MP4s), which are still hardcoded `bcardd_*` in
index.html and should later resolve from the selected hero the same way.

## BUILD IMPLICATIONS

1. **Separate build-outs, shared spine.** Each mode gets its own graphics/maps
   pipeline. Do NOT try to make one engine do all of it. But every mode plugs
   into the same state schema, so design that schema first.
2. **The state schema is the priority artifact.** Buildings (id, type, tier,
   grid-x, grid-y), walls (segments), and progression must be defined ONCE and
   consumed by both the 2D builder and the 3D overworld. This is what makes
   "build a wall in 2D, see it in 3D" possible.
3. **Every mode exits to the DISTRICT MAP** (per real-life-logic law). The RPG
   overworld is home base; all modes launch from it and return to it.
4. **Order of build:** the RPG 3D overworld and the 2D Clash defense are the two
   that must share state first, they are the reflection pair. Story/boss/Royale/
   Gulag are additive modes that read the same state but do not have the tight
   round-trip dependency.

## CURRENT STATE (2026-07-17)

- **RPG 3D:** partial. The *character* is 3D (hub3d.js model-viewer overlay,
  $BCARDD live at 14MB, HTTP 200). The *world/districts* are still Canvas2D. The
  full 3D overworld (WebGL terrain, kitbash building meshes x tiers, 3D camera)
  is the next big wave, not yet built.
- **Per-hero model resolver:** LIVE in hub3d.js (registry + resolver, defaults to
  $BCARDD). Rides the next ship.
- **Defense 2D Clash-style:** design exists (PVP_CLANS_ARCHITECTURE.md), not yet
  the shared-state reflection round-trip described above.
- **Interiors MP4:** working (current hub behavior).
- **Story / Boss / Royale-minigame / Gulag-FPS:** specced in their docs, staged.

The gate before the world-3D push: prove the character (done, $BCARDD walks the
district live), then build the shared state schema so 2D-defense and 3D-overworld
reflect each other.

## WHY THE HERO STILL FEELS LIKE A VIDEO (2026-07-17 diagnosis)

Rich: "he's supposed to stand still when I'm standing still, move left when I move
left, move right when I move right, spin when I spin, like WoW/Skyrim/RuneScape
real-time motion, not a recorded video." Right now it does NOT do that. Two
separate causes, both real:

### Cause 1: he is probably seeing the 2D MP4 fallback, not the 3D model at all
- `index.html:428` loads model-viewer from the **jsdelivr CDN** (`type="module"`).
  There is NO self-hosted copy. If that external module fails to register (mobile
  webview, slow/blocked module load, or the 14MB glb never fires `load`),
  `hub3d.js` keeps `.active=false` and the hub keeps drawing the 2D avatar.
- The 2D avatar (`index.html:2291-2298`) is literal video: `bcardd_walk.mp4`,
  `bcardd_walk_front.mp4`, `bcardd_walk_back.mp4`, `bcardd_idle.mp4`. So "it's
  still just a video" is the fallback path showing exactly what it says.
- **Fix:** self-host model-viewer under `assets/vendor/` (kill the jsdelivr
  dependency so it ALWAYS registers), and expose a visible active/fallback signal
  so we can tell which path is live.

### Cause 2: even when the 3D IS active, the hub only feeds it left/right + moving
- `index.html:2173` computes ONLY `faceDir = +1/-1` (from dx) and `avMoving`
  (moved or not). No heading angle. No spin. No up/down.
- `hub3d.js` therefore can only: swap idle/walk clip, and `scaleX(-1)` mirror-flip
  for left/right. Camera is locked (`camera-orbit: 0deg 90deg`). That is a fixed
  side view of a baked walk-loop, mirrored L/R. It reads as a video because it
  effectively is a looping clip from one camera angle.
- **Fix (the real one):**
  1. At `index.html:2173`, compute the true travel heading:
     `var faceAngle = Math.atan2(dy, dx);` and pass it into
     `__hero3d.pos(X, Y, avMoving, faceDir, r, faceAngle)`.
  2. In `hub3d.js`, DELETE the `scaleX` flip. Instead drive the model's **yaw**
     from `faceAngle` every frame (rotate via `camera-orbit` theta or a model
     rotation), so the dog turns to face ANY direction and spins in real-time.
  3. Optional WoW feel: a slight camera orbit/tilt for 3rd-person depth.

### HARD LAW on this fix
Do NOT blind-ship 3D changes from the phone. Per the render-UI-on-e5 law, this
must be rendered and eyeballed on e5 chromium (`render_on_e5.sh`) and confirmed to
turn/spin correctly BEFORE it ships. 3D motion cannot be verified on proot.

**Order:** (1) self-host model-viewer so 3D reliably activates, (2) plumb
`faceAngle` through and replace the flip with real yaw, (3) e5 render test, (4)
ship. Only after this does the character actually move like WoW/Skyrim.

### STATUS: SHIPPED 2026-07-17 (cache stamp v=1784345517)
Steps 1, 2, 4 done and LIVE. Step 3 (e5 headless render) was BLOCKED: e5 root
disk is 100% full (192MB free / 49GB), so playwright chromium (187MB) could not
install. No safe cleanup available without deleting real data, so the visual
render was not run.
- **Self-hosted engine:** `assets/vendor/model-viewer.min.js` LIVE (HTTP 200,
  935194 bytes, verified self-contained: 0 relative/dynamic imports). Replaces the
  jsdelivr CDN dependency at `index.html:428`. This removes the silent-fallback-to-
  MP4 failure mode.
- **Real yaw:** `index.html` now computes the true heading
  `faceAngle = atan2(dy,dx)` (L2173) and passes it to `__hero3d.pos()` (L2278).
  `hub3d.js` replaced the `scaleX` mirror with camera-orbit yaw so the hero turns
  to face travel direction and spins in real time.
- **Tuning knobs (in `hub3d.js`, top of IIFE):** `THETA_BASE=90`, `THETA_SIGN=-1`,
  `PHI=72`. If, on play, the dog turns the wrong way or faces a wrong offset, flip
  `THETA_SIGN` and/or adjust `THETA_BASE` by 90deg steps. Non-breaking: even if the
  offset is off, it is still real 3D turning, not a flat flip.
- **Still owed:** an actual eyes-on render (e5 once disk is freed, or Rich in play)
  to confirm the turn direction; and infra: e5 root disk needs freeing (100% full
  is a live risk to the services on it).

### HERO ANIMATION STATE MACHINE -- SHIPPED 2026-07-17 (cache stamp v=1784351669)
The 3D hero now runs idle/walk/run off player input, RENDER-VERIFIED on e5.
- **Clips identified by render.** The GLB has 4 UNNAMED clips (NlaTrack.*). Each
  was rendered on e5 (freed npm cache to install chromium-headless-shell). Result:
  clip3 (17.6s, lowest motion) = relaxed IDLE/wait pose; clip0 + clip1 = the two
  gaits; clip2 = turn/power (unused, the camera yaw covers turning). Mapping lives
  in `hub3d.js` `CLIP_IDX = {idle:3, walk:1, run:0}`, live-overridable via
  `window.AK_HERO_CLIPS = {idle,walk,run}`.
- **Bug fixed:** old code mapped idle=clip0, walk=clip1 -- so standing still played
  a walk-in-place. Now: no stick = idle(clip3), stick = walk, double-tap-and-hold
  stick (or Shift) = run at **1.75x** speed + run clip.
- **Run trigger:** `index.html` -- 2nd tap-within-320ms on the floating stick arms
  run; `me.spd * 1.75` while held; `running` passed to `__hero3d.pos(...)`.
- **Glow removed on the 3D hero:** the gold ring/circle and the wheel-spin glow
  arcs are gated off when `__hero3d.active` (they still draw for the 2D fallback).
- **Concurrency note:** another build fork edited `hub3d.js` in parallel and did a
  motion-magnitude analysis; both methods AGREE idle=clip3. They disagreed on
  which gait is walk vs run (my render read clip0=walk; their metric said
  clip0=run). Deferred to their more-rigorous metric (`CLIP_IDX` walk:1/run:0). If
  walk/run feel swapped in play, flip via `AK_HERO_CLIPS` -- one line, no redeploy.
- **Verified:** e5 render (engine registers + GLB loads + all 4 clips render) and a
  live smoke test (deployed page parses clean, `__hero3d.pos` present, no JS errors
  from these changes). NOT verified headlessly: the in-zone feel (idle-when-still,
  glow-gone on the live hero) -- needs Rich in play, but the logic is deterministic.
- **Incidental finding (not mine):** live console shows `systems/juice.js` 404s
  (served as HTML, refused as script). Pre-existing missing-file drift, worth a fix.
