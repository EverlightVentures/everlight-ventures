# Alley Kingz -- 2D to 3D Asset Migration Audit

Operator directive (2026-07-14): "Everything that's 2D needs to be 3D. Even the maps,
everything. The story mode, all of that stuff, 3D. It's 2026, there's no reason not to."

Total live 2D library: **1,701 assets** across 26 categories. This is the full manifest:
every category, its count, what it becomes in 3D, the method, and the priority wave.
Priorities follow the blueprint's slice-first order (P1 = vertical slice, P4 = art
scale-out, P-late = after v1).

Method key: **MESH** = AI image-to-3D (TRELLIS2/Hunyuan self-host if the AceMagician has
an NVIDIA GPU, else fal.ai ~$0.40/model) + shared Mixamo rig. **KITBASH** = modular
parametric pieces (Sloyd) + landmark meshes, snapped on a grid. **REBUILD** = native
Unity VFX/UI (not converted, re-authored). **CARRY** = keep as-is (video/audio play in
engine). **STAY-2D** = deliberately kept 2D (see the one exception below).

---

| Category | Count | Becomes in 3D | Method | Wave |
|---|---:|---|---|---|
| cards | 425 | 106 rigged hero dogs (multiple arts -> 1 model each) | MESH + shared rig | P1 pilot (3-5), P4 batch |
| maps | 400 | ~4 base building meshes x 10 themes x tier decoration | KITBASH | P3-P4 |
| story | 387 | Comic panels -- see the STAY-2D note | STAY-2D (your call) | -- |
| units | 48 | Silhouette/proportion refs for the hero rigs | (reference only) | P1 |
| icons | 69 | UI icons stay flat 2D (correct for UI) | STAY-2D | -- |
| ui | 57 | HUD/menus rebuilt as Unity UI Toolkit | REBUILD | P2-P5 |
| hub | 31 | The walkable district as a real 3D environment | KITBASH + MESH | P3 |
| portraits | 25 | Auto-generated: render each finished rig to a headshot | (free byproduct) | P4 |
| cardfx | 22 | Deploy/hit/ability effects as Unity particle systems | REBUILD | P2 |
| interiors_mp4 | 20 | Building interiors as real 3D rooms | KITBASH | P3 (or CARRY interim) |
| interiors | 20 | Interior backdrops -> 3D room shells | KITBASH | P3 |
| cinematics | 17 | Carry as video now; re-shoot in-engine later | CARRY -> REBUILD | P-late |
| shop | 14 | Shop UI + hero product renders (rotating 3D card) | REBUILD | P5 |
| sprites | 12 | Misc battle sprites -> particle/decal or small meshes | REBUILD | P2-P3 |
| arena | 12 | The battle board as a 3D lane diorama | KITBASH | P1 |
| bosses | 11 | 11 boss dogs as premium hero rigs (extra polish) | MESH + hero pass | P3-P4 |
| cosmetics | 10 | Socket-attached 3D parts (drip.js sockets map 1:1) | MESH parts | P4 |
| avatar | 9 | Player-lead 3D model (reuses the 0001 pilot pipeline) | MESH | P1 |
| spells | 8 | Spell VFX as Unity particles/shaders | REBUILD | P2 |
| specials | 8 | Ultimate/special effects as VFX Graph | REBUILD | P2-P3 |
| handlers | 6 | 6 commander portraits -> 3D commander models | MESH | P3 |
| world | 6 | World-map strategic view as a 3D map | KITBASH | P3 |
| tutorial_mp4 | 5 | Re-shot as in-engine guided moments | CARRY -> REBUILD | P-late |
| ui_mp4 | 4 | UI motion -> native Unity transitions | REBUILD | P2 |

(`_bg_backup` 74 and `_arttest` 1 are backups/scratch -- ignore.)

---

## The one honest exception -- your call, not mine

**story (387 panels) -- the Chronicles/manga comic reader.** The research flagged this
as the single thing where 2D is a *strength, not a limitation*: it is a deliberate art
medium, like a graphic novel embedded in the game, and it is already 1.3MB of finished
per-card story. Converting hand-inked comic panels into 3D would spend real money to make
them look *worse* and generic.

So the recommendation is: the **story MODE** (boss encounters, the walkable world, the
cutscene beats) goes fully 3D like everything else -- but the **comic-panel READER stays
2D** as a stylistic layer inside the 3D game (think Spider-Verse: a 3D world that drops
into comic panels for story). You said "story mode 3D," and the gameplay of it will be.
This is just flagging that the *comic pages themselves* are worth keeping as art, not
geometry. If you want them 3D too, say so and they go in the P4 batch -- but I'd bet the
comic layer becomes a signature look people screenshot.

Everything else on the list: 3D. Maps, hub, interiors, arena, world, bosses, handlers,
cosmetics, the player avatar -- all of it.

---

## What this changes about cost + time

- **Zero quadrupeds.** All 106 cards are bipedal (4 rig families: bruiser/sprinter/
  tech_ops/turret_util), so the entire roster rides the FREE Mixamo humanoid path. No
  ~$50/mo animal-rig tool needed. Confirmed from canon.js rig data.
- **Buildings are kitbash, not 400 models.** The 400 map tiles are tier *reference* for
  ~4 base structures per theme -- a fraction of the work the raw count implies.
- **Portraits are free.** The 25 portrait slots (and the 0/106 in-battle portrait gap)
  auto-fill by rendering each finished rig to a headshot.
- **Real 3D-model work for v1 = ~24 hero cards + a handful of buildings + the arena.**
  Not 1,701 assets. The rest is reference, reuse, particle rebuilds, or carried video.

The GPU on the AceMagician is the one unknown that swings the mesh batch between $0 and
~$170. One power-on answers it (Step 0 of the runbook).
