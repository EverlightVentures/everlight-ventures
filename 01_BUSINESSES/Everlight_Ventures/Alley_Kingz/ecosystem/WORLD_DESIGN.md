# ALLEY KINGZ -- THE WALKABLE WORLD: Design + Build Plan (deep-dive 2026-06-19)
Studied Sunflower Land + Pokemon + Monopoly Go, mapped onto AK's ACTUAL systems (hub_proto v2, pass.js, quests.js, social.js, economy.js, drip.js, ak_account.js, codex.js, engine.js, lobby.js, the maps host).

North-star (HARD LAW): AK = fun/feel/finish; core = a TAP-FAST card battler (engine.js, juiced). The world is flavor WRAPPED around it -- NEVER gates a fight; battle always one tap away. We build a navigation+life SKIN, not a new game.

## TECH VERDICT (reconciled)
Phase 0-2 ship in **canvas2D** (the working proto IS canvas2D + shares engine.js's render stack -- zero new framework, fits the perf budget, no Three.js). The 2.5D-Phaser-iso LOOK = the **V3 art-ceiling upgrade** (re-skin the same scene graph when credits/art re-up). Small+dense beats big+empty.

## 1. WORLD STRUCTURE -- HUB-AND-ZONE (not one open map)
Sunflower = home base + teleport-connected rooms; Pokemon = a ring of distinct nodes joined by short routes. AK takes both -- multiple ZONES joined by screen transitions (this is the answer to "it's still one screen"):
- **HOME TURF** (spawn; the screen you return to; **visibly levels up with rank** graffiti->neon->chrome; holds account-upgrade fixtures)
- **DOWNTOWN** (live-ops plaza = Sunflower's Pumpkin Plaza: The Drop rotating shop + Hit List board + Alley Pass kiosk + daily chest)
- **THE ARENA district** (the apex / the "gym objective"; biggest, glowing; one tap = fight)
- **FACTION ROW** (AK's 4 factions + 6 commanders = 1:1 with Sunflower's 4 faction houses; each = a clubhouse + commander NPC + faction-mark shop + weekly faction competition)
- **THE DOCKS** (minigame/arcade zone; reuses rain_docks art)
- **THE BLACK MARKET** (cash-out scrap/dupes, raffle, VIP-gated vendors = Sunflower's Goblin Retreat; ties to AK VIP)

## 1b. TRAVERSAL (the Sunflower macro/micro split)
- **MICRO (inside a zone):** camera-follow scrolling world bigger than the screen (proto v2 already does this -- props scroll, roads form a spine). Tap-to-move primary on mobile + joystick + WASD/arrows/vim.
- **MACRO (between zones):** Stardew-style **fade-to-black scene transitions** at zone edges/portals. **ONE heavy scene in memory at a time** (hub OR shop OR match) = the hard perf cap. AK maps already lazy-load as separate scenes.

## 1c. RADAR (keep minimal -- Sunflower ships a billion sessions with just a corner fast-travel button)
Two jobs only: (1) orientation (player dot + building blips + waypoint arrow -- proto has these); (2) **fast-travel** -- tap a blip / open a visual district map -> teleport instant/free/no-gate (Sunflower's #1 friction-killer), wired to the existing ev_nav.js Cmd-K rail, + a hard FIGHT NOW jump.

## 1d. ART REUSE
The 4 painted cities (the_lot/neon_night/golden_industrial/rain_docks) = zone backdrops, already on the deploy-isolated maps host (ACAO:*). Unpainted -> graceful procedural fallback, so ship with 4 zones + add as art lands. PII-never-to-CDN holds (backdrops only).

## 2. THE NON-BATTLE LOOP (log in, never fight, still progress) -- the retention engine
Sunflower's core: the NPC-fronted delivery/quest loop drives daily retention -- and needs NO combat.
- **NPCs = named handlers/commanders** (the ask has a FACE/voice -- stickier than a quest list). Proto already has Ol' Scraps.
  - Ol' Scraps (Home, onboarding) | the 6 Commanders (Faction Row, daily deliveries+chores) | The Fixer (Downtown, Hit List bounties) | The Quartermaster (Black Market, scrap->currency+raffle) | The Hustler (Docks, arcade access)
- **Mini-missions, 3 cadences** (all on EXISTING rails: quests.js=Hit List, pass.js=Alley Pass XP, economy.js=rewards):
  - Daily Deliveries (NPC asks for item/action -> gold+gems+Pass XP; two-tier refresh anti-grind cap; reset anchored ET morning, displayed PT)
  - Weekly Chores (consistency tasks)
  - Weekly Bounties (Hit List board, tougher cross-system asks)
- Play-without-battling progression feeds account upgrades + the economy -> then grind the battler when ready.

## 3. SEASONAL / EVENTS (rotate on the Alley Pass clock; Monopoly-Go cadence + micro-games) -- tie to pass.js seasons + Hit List; rotating themes/awards; event micro-games in the Docks. (Full detail: task wvvzru3e2.)

## 4. CORE-TIER INTEGRATION
The battler stays the apex ("gym/Arena"); the world FUNNELS into it (waypoint + FIGHT NOW) without gating it (battle always one tap). World progress (deliveries/quests) feeds the same economy/Pass the battler does.

## 5. BUILD PLAN (from the current proto; sole-deployer + checkpoints; verify in a real browser)
P0 (DONE): scrolling-world feel-proto v2 (camera + radar + roads + props + NPC + FIGHT NOW). ->
P1: wire the radar fast-travel + 1 real zone-transition (Home Turf <-> Downtown, fade-to-black) + buildings open the real screens. ->
P2: the NPC delivery loop on quests.js/pass.js (daily deliveries, Ol' Scraps + 1 commander). ->
P3: more zones (Faction Row, Arena district, Docks) as backdrops/art land. ->
P4: seasonal events on the Pass clock. (Full phasing: task wvvzru3e2.)
