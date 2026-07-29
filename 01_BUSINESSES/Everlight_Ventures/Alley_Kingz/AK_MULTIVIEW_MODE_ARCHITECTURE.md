# ALLEY KINGZ -- MULTI-VIEW MODE ARCHITECTURE (HANDOFF)

_Owner: Rich / Lucrex. Captured 2026-07-28 from the 7-image reference read + multi-view handoff._
_Companion to [AK_PROTOTYPE2_REBUILD_HANDOFF.md](AK_PROTOTYPE2_REBUILD_HANDOFF.md): that doc owns movement, visuals, and the engine ceiling; THIS doc owns the camera-and-mode architecture that sits on top of it._

---

## 0. The core insight (locked)

Alley Kingz does not have one broken camera. It has **four different games wearing one isometric camera.** FPS survival, base-building, vehicle combat, and third-person brawling physically cannot share an isometric view, and forcing them to is the root cause of "it feels off." The fix is **contextual mode-switching**: four purpose-built cameras that swap automatically on context, each hiding the UI that does not belong to it.

This maps directly onto systems the game ALREADY has (districts, gulag, arena, garage), so it is a re-architecture of presentation, not four games from scratch.

---

## 1. The four modes (each reference image -> a mode -> an existing system)

| Reference | Mode | Feel | Maps onto (existing) |
|---|---|---|---|
| #4 Road to Vostok (snowy FPS) | **GULAG** | First-person survival realism | The live `gulagFPS` in `systems/modes.js` (already first-person) |
| #5 Fantasy Village (warm stylized) | **DISTRICTS** | Hand-painted, warm, readable base-building | The hub / district-control world (`index.html` + `world3d.js`) |
| #6 Post-Apocalyptic Racing | **VEHICLE** | Third-person chase, desert speed | The Garage (`garage.js` rigs) -- the missing gameplay half |
| #7 UE5 Endless Runner | **MOBS** | Over-shoulder third-person brawling | Raid / arena combat + the hero GLB boxing clips |

---

## 2. The six diagnosed issues (from screenshots 1-3)

1. Camera too high/far -- the hero reads as a speck, no sense of scale.
2. Flat dark visuals -- everything is one blue-grey value, no hierarchy. (Partially addressed: the live build just got a brightness pass, but the value-range problem remains.)
3. No art direction -- reads as greybox, not a stylized world. (See ART_BIBLE.md + a per-mode style bible.)
4. Cluttered UI -- 20+ elements on screen at once.
5. Navigation unreadable -- streets and rooftops blend into one value.
6. One camera for everything -- the structural cause of 1, 4, and 6.

Mode-switching + contextual UI fixes 1, 4, and 6 in a single move. Art direction + color-as-information fixes 2, 3, and 5.

---

## 3. Mode-switch triggers + camera specs

| Trigger | Enters | Camera |
|---|---|---|
| Walk the hub / hold territory | DISTRICTS | Isometric, warm key light, pulled IN closer than today (raise scale) |
| Enter your customized car | VEHICLE | Third-person chase, behind-car, speed blur + dust, higher FOV |
| Cross into a restricted zone | GULAG | Fade to black, then first-person, breath SFX, tight FOV |
| Enemy within ~5m | MOBS | Camera drops to over-shoulder, combat UI slides in |

Each transition is a deliberate beat (fade / camera sweep / UI swap), not a hard cut. Exact FOV / distance / damping values live in the original multi-view doc; treat the above as the contract, tune the numbers in-engine.

---

## 4. The five hard rules (canon for the dev/bot)

1. **NEVER one camera for all modes.** That is why it feels broken now.
2. **Color = information.** Safe districts = warm amber. Danger zones = red neon. Neutral = green. (This is also the Prototype-2 zone-decay idea from the companion doc, arriving from a second direction -- districts should read their safety at a glance.)
3. **Contextual UI only.** Districts = hide combat buttons. FPS = hide everything except health + ammo. Never 20 buttons at once.
4. **Generate against a style bible.** Every Tripo prompt carries the same descriptor ("hand-painted, stylized-realism, warm interior light") or assets will not match. Fold into PROMPT_BIBLE.md / ART_BIBLE.md.
5. **AccuRig gets ~80%.** The hero's jacket and tail need manual weight-paint in Blender. Do not skip it.

---

## 5. Sequencing (the honest correction to the 8-week plan)

The four references are four different engines' worth of games. The 8-week table is the **menu, not the order.** Shipping all four in 8 weeks yields four half-modes.

- **Build ONE mode to reference quality first: MOBS (over-shoulder brawler).** It is closest to the hero-GLB combat, and its movement core is ALREADY landing in the live web build (momentum lead-camera, sprint acceleration, `me.z` jump/glide shipped 2026-07-28). Prove the pipeline there, then open the next mode.
- **Step 0 is not Week 1. Step 0 is standing up a desktop build machine.** UE5/Unity + Tripo -> AccuRig -> Mixamo -> Blender -> engine cannot run on the phone or the headless e5 server. Nothing in weeks 1-8 starts until that machine exists. This is the same gate the companion doc flags.

---

## 6. What is already true in the live build (do not rebuild these)

- Districts, gulag (first-person), arena, and garage all exist as systems today.
- The Mobs-mode movement feel is being built into the live browser game now: a momentum camera that leads travel, sprint acceleration, and real jump/glide via `world3d.project()`'s height arg. So the brawler's movement is not a from-scratch ask.
- Contextual UI can begin on the CURRENT build cheaply: gate the existing HUD groups per `state` (IN_ZONE / RAID / gulag) and pull the district camera closer, before any engine rebuild. That is the fastest visible win from this whole plan.

---

_This doc is the single source of truth for the camera-and-mode architecture. Movement, visuals, engine choice, and the asset pipeline live in the companion Prototype-2 handoff. Sequence over parallelize; prove one mode before opening the next._
