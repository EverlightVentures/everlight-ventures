# ALLEY KINGZ -- LIVING WORLD (hub V1.5 design; operator 2026-06-19)
> The leap from "walkable menu" to a living overworld -- Sunflower Land dynamics, but dogs. Operator feedback after first walking the live hub. Companion to AK_WORLD_BIBLE.md + AK_RAID_DEFENSE_SYSTEM.md. The battler (game.html) + the shop sections are the DONE base; this is the world layer wrapped around them.

## ALREADY WORKING (verified in code 2026-06-19, hard-refresh to see)
- DEEP-LINK: each building opens its OWN shop section (shop.js auto-opens on load via data-akshop-standalone + reads the #hash -> activeTab). Garage->Deck Lab, Kennel->Handlers, Crew Yard->Crew, Fixer->Hit List, Pass House->Alley Pass, Wardrobe->Drip, Archive->Codex, Street->Street Code. (THE DROP = the generic shop on purpose; point it at #gems.)
- EXIT: "<- BACK TO THE ALLEY" (top-left, every shop screen) -> ../ = the world map (the hub). game.html result-nav also has a Map button -> hub.
- SPAWN: fixed -- empty tile (1300,950) + 0.8s grace, no auto-enter.

## TO BUILD (operator's living-world asks, in priority order)
1. LIVE FX / IMMERSION (the map feels too static). Quick wins: drifting ambient particles (embers/dust/fog), neon flicker, animated NPC + critters wandering, subtle vignette, building glow pulse. Bigger: parallax layers, day/night, weather. START HERE (cheap, high impact).
2. THE ARENA = MODE SELECT (not straight-to-match). Entering the Arena/Town Hall opens a chooser: PvP | 2v2 | Story (continue). Then routes into game.html with the chosen mode. game.html already has a 10-city x 10-level WORLD MAP/ladder (story) -- wire the chooser in front of it.
3. ROAMING ENEMIES on the map edges (outer radius): ghost dogs / strays / wild animals that wander, detect the player, give chase, and on contact instigate a battle (random encounter -> game.html match, themed). Designated "wild" zones near the map border; safe in the central districts.
4. ACTIVITY PATCHES / GATHER NODES (not buildings): Sunflower-Land-style but dog-version -- dig for bones, chase the rat, mark the hydrant (territory), sniff-out caches, junkyard scavenge. Each = a node you walk to + a quick mini-mission -> rewards (gold/fragments/bones).
5. PIN -> ART NODE: replace the plain building/marker dots with CUSTOM ART nodes scattered on the map; players "hit" them (walk into / tap) to trigger little missions or open a cache. (Replaces the simple drop-pin look with art + interaction.)

## ART NEEDS (queue to art factory; gritty dog-gang house style)
- Roaming enemies: ghost dog, alley stray pack, sewer rat-king, junkyard mutant, wild boar/raccoon -- top-down sprites + a couple frames for idle/chase.
- Gather/activity nodes: bone-dig spot, hydrant (territory), trash cache, rat hole, scrap pile -- node art + a "hit/collect" pop.
- Ambient critters + FX: drifting embers/dust sprite, fog wisp, pigeon/rat critter walk-cycle.
- Arena mode-select panel art (PvP/2v2/Story tiles).

## LOGIC NEEDS (module tie-ins)
- M01 SPAWN/overworld: enemy spawner + wander/chase AI, gather-node placement + collect, encounter trigger -> match handoff.
- M03 RAID/COMBAT: random-encounter match (themed enemy as opponent deck).
- M06 ECONOMY: gather/encounter rewards via ak_grants rail.
- M07 PROGRESSION: mode-select (PvP/2v2/Story) state; story = the existing 10x10 ladder in game.html.
- Hub FX: a screen-space particle/atmosphere layer in index.html draw loop (perf-gated; do NOT strip glows per operator -- pre-render if FPS dips).

## OPERATOR QUOTES (intent)
"It shouldn't go to the main menu every building -- it should go into that specific section... and a way to exit back to the world map." (already built; cache) | "The Town Hall is where you actually go in and select PvP / 2v2 / story mode." | "On the external map radius there should be ghosts/zombies/wild animals that attack and instigate battles." | "Designated patches... live animation effects... more real, more immersive, real-life vibe." | "Like Sunflower Land -- areas with missions like fishing/gathering, but a dog version." | "Drop pins replaced by custom artwork that get hit by players and cause little missions." | "That's all gonna take graphics and logic."

## V2 ARCHITECTURE (operator 2026-06-19, the bigger picture -- supersedes the single-stacked-map shape)
1. MULTI-MAP DISTRICTS (not one stacked 2600x2600 map): each district is its OWN full-screen map. Walk to the screen EDGE -> transition -> a whole new district map loads. Districts are separate zones (Zelda/Pokemon screen-to-screen), spaced apart, not crammed together. Buildings currently too grid-aligned -> scatter organically.
2. TWO LAYERS (Clash-of-Clans split):
   - YOUR BASE / CITY: your buildings; where you build, upgrade, and DEFEND. This is "home."
   - THE WORLD MAP: leave your base -> travel -> see OTHER players' bases (visit / raid). Few real players now -> generate BOT BASES that resemble the player's, each with its own custom loadout.
3. NIGHT PvE DEFENSE (Dark War Survival, whole-base/whole-city scale): at NIGHT, wolves / zombie dog-packs / strays spawn at the map edges and march on your BUILDINGS. Your deck/troops AUTO-SPAWN and defend. If enemies break through -> building damage (ties into AK_RAID_DEFENSE_SYSTEM targeted damage + repair). Day/night cycle drives it.
4. MOVEMENT FEEL: the joystick walk is finicky (deadzone/drift, tap-vs-joystick conflict, no smoothing) -> fix the control feel.
5. ART GAPS: ARENA hero facade (Seedance) + any building still on a colored rect -> generate.

BUILD NOTE: this is a foundational shift. Sequence TBD with operator (see the priority question). The current single-map hub becomes "your base" map; the world-map + multi-district transitions + bot bases are the new structural layer; night-defense is the signature gameplay on the base map.
