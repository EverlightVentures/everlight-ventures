# Alley Kingz - The 3D Completion Plan

_Synthesized 2026-07-29 from direct code reads (every file:line verified) + the 6-agent audit + operator's vision dump. Sibling to AK_MULTIVIEW_MODE_ARCHITECTURE.md and AK_PROTOTYPE2_REBUILD_HANDOFF.md._

## The diagnosis (one sentence)

The heroes became GLB. Everything else that walks and fights is still a 2D JPEG/sprite. And every mode wears the same camera and the same HUD, so five different games read as one spammed screen.

**The key unlock (not new tech, just wiring):** the 3D-unit renderer that would put your GLB heroes on the map already ships and was NEVER called once:
- `window.__ak3d.unit(key, url, x, y, opts)` at `systems/hub3d.js:352` - pins any GLB at a screen position, auto-plays walk/idle/run clips, CAP 4 units (1 hero + 4 = 5 WebGL contexts, phone budget ~8), returns false past the cap so the caller falls back to 2D (graceful, never black-screens). Built 2026-07-18, zero callers.

That single dead function is why your 6 GLB heroes are "nowhere to be found" on the map. Deployed dogs, NPCs, roamers, and lane units all fall back to 2D card art because nothing routes them through it.

## What already exists (so we wire, not rebuild)

- **3D unit renderer** - `__ak3d.unit()` (hub3d.js:352). BUILT, DEAD.
- **Per-player building hero** - `profile.buildingDogs[bid]` + `assignedFor(bid)` / `setAssigned(bid,name)` (index.html:1417-1424). The infirmary already knows whose hero to show, per player. WIRED (data).
- **Raid walk/engage flag** - `al._mv` already flips as a deployed dog walks vs engages, comment says "drives the walk/engage clip" (index.html:2347). Drives 2D today. HALF.
- **Raid player hero** - already a GLB via `__hero3d`; only the crew + defenders are flat.
- **Camera modes** - `CAM_MODES` tpp/fpp/map + `setMode()` (world3d.js:153-163, 284). HALF.
- **6 GLB heroes + real buildings** - bcardd/balboa/jagged/rottweiler/bulldog/malamute + townhall/silo/ward/block/infirmary/drop. WIRED.
- **Per-player storyline** - story.js branches + buildingDogs + handler focus. Ending wired this session; needs surfacing. HALF.

## The rule: 2D or 3D? Be intelligent about it

GLB (walks / fights in real time):
- Hero in world, raids, gulag
- NPCs / roamers (Guild Masters, Fang) on the street
- Wild encounters (Pokemon-style)
- Deployed crew in raids
- Tower-defense lane units (walk down lane, then fight)
- The keeper INSIDE a shop = the hero the player assigned

Stays flat (card / menu / backdrop):
- The card-battle screen (the Pokemon / tower-card layer)
- Shop interior BACKGROUNDS (keep the MP4)
- Comics, HUD chips, menus, icons
- Any card in hand / deck / collection

## The plan - six phases, in build order

### Phase 1 - GLB avatars on the street  (the big one)
Goal: walk the city and see real 3D characters, not 2D JPEGs.
- Route the nearest N roamers/NPCs/encounters through `__ak3d.unit()` (2D draw sites: `akDrawSystems`, `_roamers`, encounters.js). CAP 4 = closest render GLB, rest stay 2D/cull.
- Feed each the same world pos the 2D draw uses (wx/wy projection); pool auto-plays walk clip while moving.
- Mission-giver roamer (Fang / Guild Master) becomes a standing GLB you walk up to (WoW vibe). Fang GLB pending from operator; heroes available now.

### Phase 2 - Real characters in raids  (flag already exists)
Goal: 3D dogs walk in and throw real punches, not sprites looping.
- Player hero is already 3D. Route deployed crew + nearest defenders through `__ak3d.unit()` at the raid draw (index.html ~2340).
- Bind `al._mv` to the walk clip; fire the measured jab/hook/kick clip on a landed hit, ease back to walk. CAP 4 picks player's own + closest fighters.
- Past CAP 4 keeps existing 2D draw.

### Phase 3 - The shop keeper is YOUR hero  (data already exists)
Goal: enter the infirmary, the dog is the one you assigned; Player B sees Fang.
- Keep the interior MP4 background. Over it, pin the GLB of `assignedFor(building.id)`.
- In `enterInterior()` (index.html:1627) resolve the assigned hero GLB, pin `__hero3d`/`__ak3d` over the MP4. Fall back to the current keeper card when nothing assigned.

### Phase 4 - Tower-defense lane in 3D  (2D tokens now)
Goal: units walk the lane as GLBs, fight in real time in the stadium.
- game.html draws lane units as 2D tokens (`drawUnit`, game.html:3842); arena3d.js is the 3D stadium shell.
- Give game.html its own capped 3D-unit pool (mirror __ak3d) inside arena3d. Walk clip while advancing, combat clip on engage. Hero-GLB-backed cards render 3D first; others stay 2D (graceful).

### Phase 5 - One camera + one HUD per mode  (modes exist)
Goal: stop spamming every button on every screen; each mode = its own game.
- Switch `setMode()` + a HUD-visibility matrix by mode:
  - Districts: isometric mid (Clash/Sunflower) - show resources/build/upgrade, hide fight rail/gun
  - Street/Mobs: over-shoulder (GTA/Prototype-2) - show move/jump/punch/run, hide build/resource chips
  - Gulag: first-person (survival FPS) - show gun-hands/health/ammo, hide the rest
  - Tower: top-down lane (Clash Royale) - show hand/elixir/deploy, hide move/jump/emotes
  - Interior: framed on keeper (Sims) - show collect/upgrade/assign, hide combat/movement
- Reconcile with AK_MULTIVIEW_MODE_ARCHITECTURE.md.

### Phase 6 - Open the streets + the WoW look  (polish)
Goal: fewer fake buildings, real ones, a depth/glow pass.
- Reduce the ~112 generated backdrop boxes (`akworldgen` targetMax) to the real GLB buildings + a thin decor ring; opens streets for the Prototype/WoW walk.
- Bloom + FXAA post-processing on the shared renderer (deferred Increment 2), quality-tiered, fallback-safe so it can never black-screen live.
- Lighting already lifted this session (AK-LIGHTUP2 + AK-CAMSCALE).

## The workflow (how it ships)

File-disjoint lanes (no two agents touch the same file), one deploy at the end, render playtest per mode:
- Lane A: world avatars (hub3d + world draw)
- Lane B: raid avatars (index.html raid loop)
- Lane C: interiors (enterInterior)
- Lane D: tower 3D (game.html + arena3d)
- Lane E: camera + HUD matrix (world3d + index.html HUD gates)
- Lane F: streets + look (akworldgen + world3d bloom/FXAA)

Lanes B, C, E all touch index.html, so those run SEQUENTIALLY (one index.html owner), while A/D/F parallelize. Ship once, then render-verify each mode.

## Status / gates
- Research agents hit temporary API 500s mid-run; this plan is from direct code reads (verified file:line). Workflow fires when the API settles.
- Art-gen (Malamute portrait 0127 + missing comic panels) queued on the free Cloudflare Workers-AI token permission (deploy token lacks Workers AI scope; 2-min free dashboard add) or funding.
- No desktop build machine required: this runs on the live web map with the GLBs already built.
