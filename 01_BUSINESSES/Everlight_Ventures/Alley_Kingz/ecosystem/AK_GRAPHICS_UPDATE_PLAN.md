# ALLEY KINGZ -- SYSTEM-WIDE GRAPHICS UPDATE (2.5D "LIFE FEEL") MASTER PLAN
> Goal: give EVERY visual surface the documented "life feel" -- 2.5D depth + ambient motion -- reusing the photos/art already in the repo. No surface left flat.
> Source technique: `ALLEY_KINGZ_DEEP_DIVE_SYNTHESIS.md` Parts 1-2 (CSS-3D extruded photo + cinematic loops) + the live patterns already shipped (`.ak-3d` shim, canvas `BLD_DEPTH`, `drawFX`, `loops.js`).
> Status: PLAN + INVENTORY ONLY. No game code changed by this document.
> Created: 2026-06-20. Read alongside `ALLEY_KINGZ_TODO.md` + `AGENT_MAILBOX.md`.

---

## 0. HARD CONSTRAINTS (read first -- these gate every section)

1. **`engine.js` is FROZEN.** The in-match battler render (game.html `#board`, the combat canvas) is never edited. Treatment stops at the battler's DOM chrome; the canvas combat itself is excluded.
2. **Reuse existing art.** The treatment is CSS/canvas-draw depth + motion over photos/sprites we ALREADY have. It requires zero new art generation. (Art *completeness* is a separate track in `AK_ART_QUEUE.md`; missing portraits keep their glyph fallbacks.)
3. **Perf: 60fps on a $100 Android.** Transform/opacity/translate only. NO new per-frame `shadowBlur` (in fact this plan REMOVES several existing ones). `prefers-reduced-motion` + coarse-pointer guards on every DOM treatment; pre-render glows to sprites rather than blurring per frame.
4. **Do NOT strip the special effects/glows** (operator veto). If FPS dips, pre-render glow to a sprite -- never delete the glow.
5. **One deploy path: e5 `~/ak_deploy/ship.sh`.** Per `CHECKPOINTS.md` HARD RULE 1 + the AK-sole-deployer memory. The GitHub Action is treated as disabled (see Audit findings section 7); untracked assets ship only via the e5 rsync.

---

## 1. THE TECHNIQUE -- TWO TREATMENT FAMILIES + ONE SHARED LAYER

Every surface is one of two render kinds, so the treatment is one of two families. Both already exist in the codebase as proven, shipped patterns; the plan **promotes them into one reusable system-wide layer** so each later section just *includes/calls* it instead of re-implementing.

### Family A -- DOM "extruded photo" (`.ak-3d`)
The Brawl-Stars 2.5D look for any DOM photo/panel/card/chip.
- **Already built** (inline in `game/index.html` ~L85-122 + L568-599, and in `game/shop/shop.css` L602-629 + pointer shim L2594-2633):
  - `.ak-3d` = perspective scene parent (`perspective:1100px`).
  - `.ak-3d-tilt` = `preserve-3d` slab; reads `--ak-rx/--ak-ry`; dark **side + bottom extruded edges** via `::before`/`::after` (16px folded faces = thickness).
  - `.ak-3d-face` = the content/photo face. `.ak-3d-shadow` = contact shadow.
  - One delegated `pointermove` handler writes `--ak-rx/--ak-ry` (parallax tilt); `prefers-reduced-motion` and `(pointer:coarse)` fall back to a static resting tilt (phones keep the thickness, drop the steer).
  - `cardFrame()`->`wrap3d()` in `shop.js` is the proven helper; the holographic foil (`shop.css` L952-975) shifts with `--ak-ry`.
- **The gap:** this CSS lives in TWO copies (index.html inline + shop.css) and the JS shim in two copies. Section A extracts ONE shared `ak_25d.css` + `ak_25d.js` so trading.js / social.js / seasons.js / missions.js / production.js / game.html lobby can all reach the same vocabulary.

### Family B -- Canvas2D 2.5D draw-extrusion
For anything drawn in a canvas loop (hub world, world-map, raid scenes, build mode, mini-game boards, roamer sprites).
- **Already built** (`game/index.html` hub loop ~L379-420):
  - `BLD_DEPTH={dx,dy}` = extrusion vector; draws **side + bottom faces (darker fills) behind the front face** = a solid block.
  - Cheap **contact-shadow ellipse** under each object.
  - **Parallax background** that scrolls slower than the foreground.
  - `drawFX(dt)` = drifting ambient embers + mood vignette.
  - HARD: no per-frame `shadowBlur`.
- **The gap:** this is hand-rolled only in the hub. Section B extracts a tiny `ak_canvas25d.js` helper (`extrudeRect(ctx,x,y,w,h,opts)`, `contactShadow(ctx,...)`, `parallaxBg(...)`) so world-map / raid / build / arcade / encounter sprites all call the same primitive instead of drawing flat rects.

### Family C -- Cinematic loops (`loops.js` + `menu_bg.mp4`)
Low-opacity (0.1-0.4), muted, `playsInline`, max-3-concurrent video layered BEHIND DOM for ambient life.
- **Already wired:** `#interior` keeper cards (z1, screen-blend 50%) + the shop overlay (z0, 40%) + both loadscreens use `menu_bg.mp4`.
- **The gap:** `loops.js` has no knowledge of the other overlays. Section work extends `AKLoops.mount(id,parentEl,opts)` to modes.js (MOBA/GULAG), raid.js (War Map/Night Defense), encounters, season hub -- one breathing-backdrop system, perf-gated by the existing 3-video budget.

---

## 2. STEP 1 -- FULL SURFACE INVENTORY

Legend -- **State:** [DONE] done | [PART] partial | [FLAT] flat | [FROZEN] excluded | [INFRA] infra.
**Type:** DP = DOM-photo | DU = DOM-UI | C2 = Canvas2D.

### `game/index.html` (hub world, HUD, loadscreen, Town Hall, interiors)
| Surface (id / loc) | Type | State | Treatment needed |
|---|---|---|---|
| Hub world canvas `#c` buildings (`BLD_DEPTH` ~L379-420) | C2 | PART | Buildings extruded + parallax bg + `drawFX` done. Extend `extrudeRect` to props (lamps/crates) currently flat. |
| Hub ground / avatar | C2 | PART | Ground parallax + procedural walk done; keep. Add contact shadow under avatar if missing. |
| Radar / minimap `#radar` | C2 | FLAT | Add subtle depth to active-zone viewport box + pip contact dots (light). |
| Loadscreen `#loadscreen` (video+wordmark+bar+tip) | DU | PART | Video loop done; add `.ak-3d` slate frame around the core. |
| HUD resource chips `#phud` (gold/gems/bones, name, TH lvl) | DU | FLAT | `.ak-3d-face` + `.ak-3d-shadow` (small, stacked -> contact shadow over full tilt). |
| Town Hall panel `#thpanel`/`#thp-box` | DU | DONE | Full `.ak-3d` -- done. |
| Interior keeper card `#interior`/`#int-card` | DP | DONE | Full `.ak-3d` + breathing glow + shimmer + scanline -- done. |
| Interior bg `#int-bg` | DP | PART | Flat image behind card; add blur-depth / loops.js video behind it. |
| Banner `#banner`, dist label `#dist` | DU | FLAT | Low: fade/slide-in with perspective (optional polish). |
| Zone fade `#fade` | DU | FROZEN | Masking layer -- leave flat. |
| Joystick `#stick`/`#nub` | DU | FLAT | Low: `.ak-3d-face` to feel pressable. |
| AK-3D tilt shim (JS L568-599) | -- | INFRA | Promote to shared `ak_25d.js` (Section A). |

### `game/game.html` (lobby, result/reward, in-match chrome -- battler canvas frozen)
| Surface | Type | State | Treatment needed |
|---|---|---|---|
| Loadscreen `#akpl` (video+logo+bar) | DU | PART | Video done; add `.ak-3d` slate frame on `#akpl-core`. |
| Lobby hero `#lobbyhero` | DP | PART | Wrap `.ak-3d-face` + parallax tilt lean. |
| Player chip `#playerchip` (+XP bar) | DU | FLAT | `.ak-3d-face` + extrusion = raised tile. |
| Daily chip `#dailychip` | DU | PART | Button glow done; wrap chip in `.ak-3d-face`. |
| Mode tiles `.mode-tile` (Play/Deck/Shop/Map/...) | DU | FLAT | **High:** `.ak-3d-face` + extrusion on each tile (pressable/raised). |
| Play-now CTA `.play-now` | DU | FLAT | **High:** thick `.ak-3d-face` + pulse-glow. |
| Reward panel `#rewardpanel` (AK-RWALIVE halos) | DU | PART | Rarity halos done; wrap panel frame in `.ak-3d-face`. |
| Result screen `#resultscreen` | DU | PART | Text glow done; wrap content in `.ak-3d-face` (trophy card). |
| Battle board `#board` (engine.js) | C2 | FROZEN | FROZEN -- exclude. |
| Match HUD `#topbar`, `#convoybar` | DU | FLAT/PART | Low: optional contact shadow on timer pill / convoy nodes. |
| Hand cards `.card` | DU | FLAT | **CAUTION:** DOM tilt only (no logic) -- touches battler surface; treat last, verify feel unchanged. |
| Card info popover `#cardinfo` | DU | FLAT | Low: optional `.ak-3d-face`. |

### `game/shop/*` (shop.js tab renderers; `.ak-3d` infra in shop.css)
| Tab / fn | Type | State | Treatment needed |
|---|---|---|---|
| CARDS `cardsView()` | DP | DONE | `cardFrame()`->`wrap3d` -- done. |
| DECK LAB `deckView()` | DP | DONE | `cardFrame()` -- done. |
| CODEX `codexView()` | DP | DONE | `cardFrame()` -- done. |
| COLLECTION / upgrade `upgradeView()` | DP | DONE | `garageTile()`+`cardFrame()` -- done. |
| GEMS `gemTile()` | DU | FLAT | Wrap gem-pack tiles in `.ak-3d`. |
| CHESTS `chestsView()` | DP | FLAT | Wrap crate tiles in `.ak-3d`. |
| HANDLERS `handlersView()` (`.aks-hcard`) | DP | FLAT | Route through `wrap3d`/`cardFrame` equivalent. |
| STREET CODE `streetCodeView()` | DU | FLAT | Wrap perk-path cards in `.ak-3d`. |
| DRIP `dripTile()` | DU | FLAT | Wrap cosmetic cards in `.ak-3d`. |
| PASS `passTierTile()` | DU | FLAT | Wrap tier reward nodes in `.ak-3d`. |
| HIT LIST `hitQuestCard()` | DU | FLAT | Wrap quest cards in `.ak-3d`. |
| CREW HQ `crewView()` | DU | FLAT | Wrap roster/donation rows in `.ak-3d`. |
| DRAW `drawView()` | DU | FLAT | Hero banner only -- light (no card grid). |

### `game/lobby.js` (lobby renderer -- overlaps game.html `.mode-tile`)
| Surface | Type | State | Treatment |
|---|---|---|---|
| Hero carousel (L72-81) | DP | FLAT | `.ak-3d-face` + parallax on active slide. |
| Top bar (brand/auth/currency, L52-56) | DU | FLAT | Light contact shadow / chip extrusion. |
| Bottom tab bar (L100-104) | DU | FLAT | Extrude each tab; raise the center PLAY. |
| PLAY button (L91,104) | DU | FLAT | `.ak-3d-face` + keep `akpulse` glow. |
| Pass strip (L83-87), mode icon row (L95-98) | DU | FLAT | Light extrusion. |

### `game/codex.js`
| Surface | Type | State | Treatment |
|---|---|---|---|
| Living-card layer (AK-CODEX-ALIVE, L492) | DP | DONE | Independent self-drifting foil (no pointer shim). Done -- verify it reads the shared tokens after Section A; do not double-treat. |

### `game/systems/worldmap.js` (strategic map + rival bases) -- PERF-CRITICAL
| Surface (loc) | Type | State | Treatment |
|---|---|---|---|
| District tiles (L917-930) | C2 | PART | Replace `shadowBlur 16` frame -> `extrudeRect` + contact ellipse + parallax bg. |
| Building icon chips (L954-980) | C2 | FLAT | `extrudeRect` side/bottom faces (Town Hall priority). |
| Raid pins (L841-845, blur 8) | C2 | PART | Drop `shadowBlur` -> pre-rendered glow / contact shadow. |
| Rival territories (L607-629, blur 7/14) | C2 | PART | Replace blur -> `extrudeRect` + contact ellipse. |
| Home base (L587-591, blur 16) | C2 | PART | Replace blur -> `extrudeRect` + contact shadow. |
| March anim (L639-645, blur 12) | C2 | PART | Replace blur -> cheap ellipse. |
| Grid / selection ring / fog | C2 | FROZEN | UI/atmosphere -- keep flat. |

### `game/systems/raidscene.js` (raid scout view)
| Surface (loc) | Type | State | Treatment |
|---|---|---|---|
| CORE / town hall (L243-245, blur 10) | C2 | PART | `extrudeRect` + strong contact shadow; drop blur. |
| Walls wood/stone/metal/barricade (L247-253) | C2 | FLAT | `extrudeRect` side/bottom faces, preserve front patterns. |
| Producer buildings (L255-256) | C2 | FLAT | `extrudeRect` + contact shadow. |
| Base perimeter (L316, blur 12) | C2 | PART | `extrudeRect` frame or keep as atmosphere; drop blur. |
| Scout dog (L328-330) | C2 | FLAT | Contact-shadow ellipse only. |
| HP bars (L324) | C2 | FROZEN | Status overlay -- flat. |

### `game/systems/buildmode.js` (base build / placement)
| Surface (loc) | Type | State | Treatment |
|---|---|---|---|
| Placed walls/barricade (L358-389) | C2 | FLAT | `extrudeRect` side/bottom faces, preserve mortar/rivet/hazard patterns + contact ellipse. |
| Garden / planter / path (L391-412) | C2 | FLAT | Keep flat OR shallow depth (low). Planter = neon glow, not extrusion. |
| Ghost preview / range ring / grid dots / damage cracks | C2 | FROZEN | Placement UI / status -- flat. |

### `game/systems/worldverbs.js` (harvest nodes) -- keep NO-shadowBlur discipline
| Surface (loc) | Type | State | Treatment |
|---|---|---|---|
| Tree / rock / scrap / pipe nodes (L279-315) | C2 | FLAT | Contact-shadow ellipse only + keep growth-scale feedback. NO shadowBlur (enforced L21). |
| Ripe pulse ring (L316-320) | C2 | DONE | Alpha-only pulse -- correct, leave. |

### `game/systems/arcade.js` (mini-game boards)
| Surface (loc) | Type | State | Treatment |
|---|---|---|---|
| bone_dig tile grid (L354-356) | C2 | FLAT | `extrudeRect` on tiles + contact shadows (flippable-tile feel). |
| alley_dash obstacles/runner (L409-411) | C2 | FLAT | Contact shadows under obstacles + runner; light extrusion on drones. |
| whack holes/strays (L459-465) | C2 | FLAT | Recessed-pit inner shadow + stray contact shadow at rim. |
| gem_tap / forge gauges (L529-536) | C2 | FROZEN | Rhythm UI -- flat. |

### `game/systems/encounters.js`
| Surface (loc) | Type | State | Treatment |
|---|---|---|---|
| Capture mini-game overlay (L355-438) | C2 | FLAT | Portrait frame depth + stamina-bar bracket + leash-pip contact shadows; loops.js ambient behind. |
| Hostile roamer sprite (L245-282) | C2 | FLAT | `extrudeRect`/side-face + contact shadow. |
| Danger vignette (L502-520) | C2 | FROZEN | Atmosphere -- keep. |

### `game/systems/karma.js`
| Surface (loc) | Type | State | Treatment |
|---|---|---|---|
| Friendly roamer (L407-444) | C2 | FLAT | Side-face + contact shadow + glow ring. |
| Friendly NPC overlay (L475-561) | C2 | FLAT | Portrait frame depth + text-panel bracket (or convert to DOM `.ak-3d`). |

### `game/systems/missions.js` / `production.js`
| Surface (loc) | Type | State | Treatment |
|---|---|---|---|
| FIXER keeper card (missions L169-266) | DP | FLAT | DOM `.ak-3d` wrap on keeper card. |
| Producer keeper card (production L169-214) | DP | FLAT | DOM `.ak-3d` wrap. |
| Job-ready / collect pips (missions L306, prod L241-263) | C2 | FLAT | Small extruded pulsing pip + glow. |

### `game/systems/modes.js`
| Surface (loc) | Type | State | Treatment |
|---|---|---|---|
| WORLD-MOBA overlay (L252-548) | C2 | FLAT | Lane as 3D plane, hero/minion z-elevation, cores `extrudeRect`; loops.js backdrop. |
| GULAG bunker overlay (L553-705) | C2 | FLAT | Cover blocks depth faces + fighter contact shadows; loops.js backdrop. |
| Encounter router (L712-742) | C2 | FLAT | Button bevels + icon glows. |

### `game/systems/raid.js`
| Surface (loc) | Type | State | Treatment |
|---|---|---|---|
| War Map overlay (L286-417) | C2 | FLAT | Target cards depth + building level bars + loops.js backdrop. |
| Night Defense overlay (L428-564) | C2 | FLAT | THE LOT core as 3D fortress, stray z-elevation, floating HUD; loops.js. |
| Rival scout roamer (L569-603) | C2 | FLAT | Side-face + glow. |
| Siege beacon (L604-628) | C2 | FLAT | Standing turret-like `extrudeRect`. |

### `game/systems/trading.js` / `social.js` / `seasons.js`
| Surface (loc) | Type | State | Treatment |
|---|---|---|---|
| Trading Post panel + listing cards (trading L305-354) | DP | FLAT | `.ak-3d-tilt` on `#ak-trade` root + `.ak-3d` per listing. |
| Trading ember backdrop (L321-333) | C2 | PART | Add parallax depth + glow halos. |
| Broker roamer (L579-624) | C2 | FLAT | Side-face + gold-ring depth. |
| Crew HQ panel + crew cards (social L156-237) | DP | FLAT | `.ak-3d-tilt` root + `.ak-3d` per crew/donation row. |
| Chat bubbles (social L371-393) | DU | PART | Subtle perspective + soft glow edge. |
| Crew crest avatars | DU | FLAT | `.ak-3d-face` inset (slight concave). |
| Season Hub + stall cards (seasons L303-408) | DP | FLAT | `.ak-3d-tilt` root + `.ak-3d` per stall/cosmetic card. |
| Trophy Hall keeper card (seasons L460-479) | DP | FLAT | DOM `.ak-3d` wrap. |
| Seasonal particles (seasons L511-538) | C2 | PART | Parallax depth per chapter (embers rise / snow falls). |

### Infra
| Surface | State | Treatment |
|---|---|---|
| `loops.js` cinematic manager | INFRA | Extend `AKLoops.mount()` to modes/raid/encounter/season overlays (3-video budget). |
| `menu_bg.mp4` | INFRA | Already the ambient loop source; gitignored -> ships via e5 rsync only (see section 7). |

**Inventory tally:** ~80 distinct surfaces. **DONE ~8** (Town Hall panel, interior keeper card, AK-3D shim infra, shop CARDS/DECK/CODEX/COLLECTION, codex.js living-card). **PART ~14** (hub canvas, both loadscreens, reward/result panels, daily chip, lobby hero, int-bg, worldmap/raidscene blur-frames, trading/season particles, chat bubbles). **FLAT ~50** (most shop tabs, all lobby tiles, HUD, all canvas structures/roamers/overlays/mini-games, keeper/crew/season cards). **FROZEN** (engine.js board, masking/UI overlays, rhythm gauges).

---

## 3. STEP 2 -- ORDERED, DEPLOYABLE SECTIONS

Each section is independently shippable, testable, and auditable. Order = (1) leverage first, (2) highest-traffic player surface, (3) heaviest perf win, (4) deepest/least-frequent last. "Partial-done" notes prevent re-churn.

| # | Section | Surfaces | Family | Already partial/done (don't re-churn) |
|---|---|---|---|---|
| **A** | **FOUNDATION -- shared 2.5D layer** | Extract `ak_25d.css` + `ak_25d.js` (DOM) + `ak_canvas25d.js` (canvas helpers) from the two inline copies | A+B infra | `.ak-3d` shim + `BLD_DEPTH` + `drawFX` already exist in 2 places -- de-dupe, don't rebuild |
| **1** | **SHOP** | GEMS, CHESTS, HANDLERS, STREET CODE, DRIP, PASS, HIT LIST, CREW tab, DRAW banner | A (DOM) | CARDS/DECK/CODEX/COLLECTION DONE -- reuse their `cardFrame/wrap3d` |
| **2** | **LOBBY + MENUS + HUD** | game.html mode-tiles, play-now, player/daily chip, result+reward frames, both loadscreen slates; lobby.js hero/tabs/PLAY/pass; index.html HUD chips, banners | A (DOM) | reward halos (AK-RWALIVE), result text glow, daily-btn glow, loadscreen video all PART -- keep, wrap frames only |
| **3** | **CARDS + COLLECTION (verify + extend)** | Confirm all card-bearing tabs read shared foil; extend foil to HANDLERS | A (DOM) | mostly DONE -- light verification pass |
| **4** | **HUB WORLD + INTERIORS** | index.html radar, int-bg, props, joystick; keeper cards (missions/production/seasons Trophy Hall); interior loops.js backdrop | A+B+C | hub buildings/ground/avatar/`drawFX` PART; interior card DONE |
| **5** | **BUILDINGS + STRUCTURES (canvas)** | buildmode placed walls/barricade; raidscene walls/producers/CORE; production pips | B (canvas) | raidscene CORE/perimeter blur PART -> convert |
| **6** | **WORLD-MAP + RAID (+ perf win)** | worldmap tiles/chips/territories/home/pins/march (REMOVE shadowBlur); raid War Map + Night Defense + scout + beacon; raidscene scout view; roamers; loops.js backdrops | B+C | worldmap/raidscene blur-frames PART -> the perf-critical conversion |
| **7** | **MINI-GAMES** | arcade bone_dig tiles, alley_dash obstacles/runner, whack holes/strays | B (canvas) | gauges FROZEN stay flat |
| **8** | **ENCOUNTERS + KARMA + NPCs + OVERLAYS** | encounters capture overlay + hostile roamer; karma friendly roamer + NPC overlay; modes MOBA/GULAG/router; trading + social DOM panels + roamers; chat bubbles; seasonal particles; loops.js into all overlays | A+B+C | trading/season particles + chat bubbles PART |
| **9** | **PORTRAITS** | Ensure every portrait image (card/keeper/commander) sits inside an `.ak-3d-face`; standalone portrait displays get depth; glyph fallbacks remain where art is missing | A (DOM) | covered indirectly by card sections -- final sweep + art-completeness handoff to `AK_ART_QUEUE.md` |

---

## 4. STEP 3 -- PER-SECTION PIPELINE (the 5 gates, run for EVERY section)

Run all five gates, in order, for each section before moving on. Nothing is "done" until gate (e) passes on the LIVE edge.

### (a) PRODUCE the treatment
- DOM sections: apply the shared `.ak-3d` vocabulary (`ak-3d` scene -> `ak-3d-tilt` -> `ak-3d-face`) by routing the section's tile/card builder through the existing `wrap3d()`/`cardFrame()` helper (shop) or adding the classes post-build (trading/social/seasons use `mk`/`replaceChildren`-safe builders -- add classes after creation, no innerHTML).
- Canvas sections: replace flat `fillRect`/`arc` structure draws with `extrudeRect()` + `contactShadow()` from `ak_canvas25d.js`; add `parallaxBg()` where a background exists. **Delete the `shadowBlur` lines** the inventory flagged (worldmap x8, raidscene x2) and replace with pre-rendered glow sprites or contact ellipses.
- Loops: call `AKLoops.mount(id, overlayParentEl, {opacity, blend, priority})` for the section's backdrop; respect the 3-video budget.
- Keep house style: gold `#D4AF37`, isometric 3/4, dark side faces. Do NOT remove existing glows.

### (b) WIRE it in -- with graceful fallback
- Every treatment degrades cleanly: `prefers-reduced-motion` and `(pointer:coarse)` -> static resting tilt + extrusion only (no steer); the `.ak-3d-face` is the unmodified content, so if CSS fails to load the surface still renders flat-but-correct.
- Canvas helpers must no-op safely if a sprite/image is missing (glyph fallback stays).
- No data/logic change -- treatment is presentational. Battler-adjacent surfaces (game.html `.card`) get DOM tilt ONLY, never a logic touch.

### (c) DEPLOY -- properly (the ONE path)
1. Commit AK code to git on the phone (SOT) -- code/docs only.
2. rsync phone `game/` -> e5 `~/ak_deploy/game` (this carries the **untracked, rsync-only assets**: `menu_bg.mp4` and anything under `assets/portraits/` -- see section 7).
3. Ship from e5 ONLY: `ssh e5 'cd ~/ak_deploy && bash ship.sh'` (foreground, with the verify-retry loop from CHECKPOINTS.md -- `for k in $(seq 1 10); do ... | grep -q DEPLOYED && break; done`). Maps are excluded (separate `alley-kingz-maps` CF project).
4. **Bump the cache-bust `?v=`** on changed `<link>`/`<script>` tags (index.html uses `?v=1`; game.html uses a `?v=<timestamp>` -- match the timestamp convention so the new CSS/JS is fetched).
5. `sw.js` is the kill-switch SW (clears caches + unregisters) -- it must stay shipped so no stale build pins in players' browsers.
6. Treat the **GitHub Action as disabled** -- do NOT rely on it; it is a clobber risk (section 7).

### (d) TEST -- front-end AND back-end
- **Front (Playwright on e5, NOT phone /photo -- it OOM-segfaults):**
  - Visual: load `https://alleykingz.online/` (the hub root) + the section's screen; assert the treated nodes exist (`.ak-3d-face` count, canvas markers) via `eval_on_selector`.
  - JS errors: capture console -- must be ZERO errors/warnings introduced.
  - 60fps: sample `requestAnimationFrame` delta on the section's canvas/overlay; assert frame budget held (and that removed `shadowBlur` improved it).
  - Reduced-motion: re-run with `prefers-reduced-motion` emulated -> static tilt, no steer, no crash.
- **Back:** if the section touches profile/economy/Supabase (shop GEMS/PASS, crew, seasons), confirm the treatment changed NO data path -- deck/profile/level/trophies load identically; AK Supabase = `mfghdobptredxxhbjwyz` (NEVER the casino project). Most sections are presentation-only -> back-end test = "confirm no write-path touched."

### (e) AUDIT -- live truth, no stale, no clobber
- Verify the **LIVE root `/`** (follow 308s to the clean URL) matches the build -- NOT `/index.html`; the hub is the root.
- Diff live edge markers + index size vs the e5 build (`curl -s '.../?cb=$(date +%s)' | grep -c <marker>`); confirm the new section's marker is present.
- Confirm every changed file (CSS/JS + any rsync-only asset) actually reached the CDN -- spot-check the asset URL returns 200, correct size.
- Confirm no clobber: only `~/ak_deploy` shipped; no other source touched the CF project; update the CHECKPOINTS.md version row + git hash.

---

## 5. STEP 4 -- MASTER COMPLETENESS CHECKLIST

Check a box only after the surface is LIVE-verified (gate e). Excluded (FROZEN) surfaces are listed as N/A so "every surface is accounted for."

### Section A -- Foundation
- [ ] `ak_25d.css` extracted (single source of `.ak-3d*` tokens) + included by index.html, game.html, shop.html, and overlay-injecting systems
- [ ] `ak_25d.js` extracted (single pointer-tilt shim) + de-duped from index.html/shop.css
- [ ] `ak_canvas25d.js` (`extrudeRect`, `contactShadow`, `parallaxBg`) extracted from hub loop
- [ ] codex.js verified reading shared tokens (no double-treat)

### Section 1 -- Shop
- [ ] GEMS | [ ] CHESTS | [ ] HANDLERS | [ ] STREET CODE | [ ] DRIP | [ ] PASS | [ ] HIT LIST | [ ] CREW tab | [ ] DRAW banner
- [x] CARDS | [x] DECK | [x] CODEX | [x] COLLECTION (already done -- verify)

### Section 2 -- Lobby + Menus + HUD
- [ ] game.html `.mode-tile` | [ ] `.play-now` | [ ] `#playerchip` | [ ] `#dailychip` frame | [ ] `#rewardpanel` frame | [ ] `#resultscreen` frame | [ ] `#akpl` slate
- [ ] lobby.js hero | [ ] top bar | [ ] bottom tab bar | [ ] PLAY button | [ ] pass strip | [ ] mode icon row
- [ ] index.html `#phud` chips | [ ] `#loadscreen` slate | [ ] `#banner`/`#dist` (low) | [ ] `#stick` (low)

### Section 3 -- Cards + Collection (verify/extend)
- [ ] All card tabs read shared foil | [ ] HANDLERS foil extended

### Section 4 -- Hub World + Interiors
- [ ] `#radar` depth | [ ] `#int-bg` loops/blur-depth | [ ] hub props extruded | [ ] missions FIXER keeper card | [ ] production keeper card | [ ] seasons Trophy Hall keeper card | [ ] interior loops.js backdrop
- [x] hub buildings/ground/avatar/`drawFX` (verify still 60fps)

### Section 5 -- Buildings + Structures (canvas)
- [ ] buildmode walls/barricade | [ ] raidscene walls | [ ] raidscene producers | [ ] raidscene CORE (drop blur) | [ ] raidscene perimeter (drop blur) | [ ] production pips
- [ ] N/A: ghost preview, range ring, damage cracks, HP bars (status UI)

### Section 6 -- World-Map + Raid (perf win)
- [ ] worldmap district tiles (drop blur 16) | [ ] building chips | [ ] raid pins (drop blur 8) | [ ] rival territories (drop blur 7/14) | [ ] home base (drop blur 16) | [ ] march anim (drop blur 12)
- [ ] raid War Map | [ ] Night Defense | [ ] rival scout roamer | [ ] siege beacon | [ ] raidscene scout dog contact shadow | [ ] loops.js backdrops
- [ ] N/A: map grid, selection ring, fog vignette

### Section 7 -- Mini-games
- [ ] bone_dig tiles | [ ] alley_dash obstacles/runner | [ ] whack holes/strays
- [ ] N/A: gem_tap / forge gauges (rhythm UI)

### Section 8 -- Encounters + Karma + NPCs + Overlays
- [ ] encounters capture overlay | [ ] hostile roamer | [ ] karma friendly roamer | [ ] karma NPC overlay | [ ] modes WORLD-MOBA | [ ] modes GULAG | [ ] encounter router | [ ] trading panel + listings | [ ] trading ember parallax | [ ] broker roamer | [ ] social Crew HQ panel + cards | [ ] chat bubbles | [ ] crew crest avatars | [ ] season hub + stall cards | [ ] seasonal particle depth | [ ] loops.js into all overlays
- [ ] N/A: danger vignette (atmosphere)

### Section 9 -- Portraits
- [ ] Every card/keeper/commander portrait sits in `.ak-3d-face` | [ ] standalone portrait displays depth-treated | [ ] glyph fallbacks intact where art missing | [ ] missing-art list handed to `AK_ART_QUEUE.md`

### Excluded (accounted for, no treatment)
- [x] N/A: `engine.js` battle board `#board` (FROZEN) | zone `#fade` | placement/status overlays | rhythm gauges

---

## 6. FINAL SYSTEM-WIDE AUDIT (after all sections live)

1. **Every surface accounted for:** walk the section-5 checklist -- every FLAT/PART box checked or explicitly N/A. No flat surface remains unlisted.
2. **Live = build:** `curl` the live root `/` (follow 308) and every section screen; markers + index size match the e5 `~/ak_deploy` build. Spot-check 5+ rsync-only assets (incl. `menu_bg.mp4`, a portrait) return 200 at correct size on the CDN -- proving the GitHub-Action-snapshot path did NOT drop them.
3. **No stale / no clobber:** only `~/ak_deploy` shipped; no rogue cron/2nd-chat deploy; CHECKPOINTS.md updated with the final version + git hash; confirm the GitHub Action did not fire a competing deploy (or is confirmed disabled).
4. **Perf regression sweep:** Playwright fps sample across hub + world-map + a raid overlay + a mini-game = held 60fps on a throttled profile; confirm net `shadowBlur` count DOWN (removed >=12 per-frame blurs).
5. **Fallback sweep:** reduced-motion + coarse-pointer run end-to-end -> static tilt, thickness preserved, glows intact, zero JS errors.
6. **Brand + glow integrity:** gold accents consistent; NO special effect/glow was stripped (operator veto honored).
7. **Continuity:** flip the relevant `ALLEY_KINGZ_TODO.md` statuses + append an `AGENT_MAILBOX.md` entry per the session-end rule.

---

## 7. KEY AUDIT FINDINGS FROM THE INVENTORY (deploy correctness -- read before shipping)

- **`menu_bg.mp4` is gitignored** (`*.mp4` in root `.gitignore`) -> it ships ONLY via the e5 rsync, never via git. Any deploy that builds from the git tree (incl. the GitHub Action) would ship the game WITHOUT the cinematic loop. This confirms the operator's "assets untracked -> e5 rsync only" rule.
- **`assets/portraits/` has 0 tracked files** -> portraits are e5/rsync-only. A git-snapshot `pages deploy` would drop them -> glyph fallbacks everywhere. Another reason the e5 path is canonical.
- **The GitHub Action (`.github/workflows/deploy-alley-kingz.yml`) is STILL ACTIVE**, triggering on push to `main` AND `lucrex-os-engine` for any `game/**` change, and runs a full-snapshot `wrangler pages deploy`. This directly contradicts CHECKPOINTS.md HARD RULE 1 ("deploys ONLY from e5 `~/ak_deploy`") and is a live clobber risk: a routine code push during this graphics work could deploy a tree that omits the rsync-only assets and overwrite the good live build. **Before Section A ships, either truly disable this workflow (comment the `on:` triggers / add a path-ignore) or make it a no-op -- do not leave it armed.** Treat e5 `ship.sh` as the sole deployer.
- **Cache-bust convention differs:** index.html `?v=1` (bump manually) vs game.html `?v=<unix-timestamp>` (regenerate). Keep both honest when CSS/JS changes or players keep the old build.
- **Most asset subdirs ARE tracked** (cards 424, maps 400, ui 56, hub 26, world 6) -- so code+most-art are in git, but the two rsync-only holes above (mp4 + portraits) are exactly why the snapshot path is unsafe and the e5 rsync is mandatory.

---

*Prepared 2026-06-20. Inventory verified against the live codebase (index.html, game.html, shop/*, systems/*, lobby.js, codex.js, social.js, loops.js, sw.js, CHECKPOINTS.md, the deploy workflow, and the root .gitignore). Technique sourced from ALLEY_KINGZ_DEEP_DIVE_SYNTHESIS.md Parts 1-2 and the patterns already shipped in the repo. engine.js untouched and excluded.*
