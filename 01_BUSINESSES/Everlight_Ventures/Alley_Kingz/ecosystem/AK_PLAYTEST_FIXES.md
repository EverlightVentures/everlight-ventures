# AK PLAYTEST FIXES (operator, 2026-06-20) -- batch after the DOM graphics batch lands

Operator played the live build. "A little better" but these 6 must be fixed:

1. CURRENCY HUD -- currencies aren't shown at the top, and there's no feedback for accumulating/spending. FIX: a top HUD bar showing ALL currencies (gold, gems, scrap, keys, bones, wood, stone, metal) with a +N float / pulse on gain and a -N flash on spend, so the player SEES the economy move. (index.html #phud overhaul.)

2. WALL HP + ATTACK -- placed walls block movement (good) but need real HP + to be ATTACKABLE: when troops/raiders hit a wall it takes damage by their hit strength until it breaks. FIX: wire buildmode wall HP (wood 200 / stone 500 / metal 1200, already set) into the raid combat -- attackers damage walls, walls gate the path, breaking a wall opens the lane. (modes.js raid + raidscene + buildmode HP.)

3. GARDENS -> ECONOMY -- the Sunflower gardens / seeds / vegetables are cosmetic; they must FEED the economy. FIX: planted beds grow crops over time (growthStage) -> harvest yields food/gold/material into the economy (Sunflower-Land loop), not just decoration. (buildmode garden + worldverbs grow + economy.)

4. SCOUT -> UN-ARTED MINI-GAME -- a scout turned into a mini-game with NO artwork (looked bad). FIX: give that mini-game the gold-cyberpunk board treatment (Section 7 graphics) AND/OR fix the scout flow so scouting shows the enemy base (not a janky un-arted mini-game). (arcade.js board art + the scout/raid routing.)

5. POST-MATCH NAV -> WORLD MAP -- after a match (win / forfeit / finish), the result screen returns to the MAIN MENU; it should return OUT to the WORLD MAP (where the raid was launched), not the lobby/main screen. FIX: post-match (game.html) sets a return-to-worldmap flag; index.html opens AKWorldMap on load instead of the lobby. (game.html post-match + index.html boot.)

6. LOADING SCREEN = ONE FILE -- the loadscreen loads ~2 images BEFORE menu_bg.mp4 (wasted resources). FIX: loadscreen uses ONLY menu_bg.mp4 (drop the lobby_hero poster + any splash image bg); solid dark fallback only. (index.html #loadscreen.)

7. TOWN HALL UPGRADE UX + COST BUG -- upgrading the Town Hall didn't say what the upgrade PROVIDES, and it didn't appear to DEDUCT the resources it cost. FIX: the upgrade panel shows the caps it unlocks (card level, crew size, builders, grid) + the exact cost, and actually deducts + shows the deduction (atomic via mutateProfile). Verify upgradeTownHall deducts. (index.html #thpanel + economy.js.)

8. CONTENT NOT VISIBLE -- the player still doesn't SEE the wild encounters, the scouts, or the mini-missions (to build KARMA). The systems exist (encounters spawn, raid scout, missions, karma) but there are no discoverable entry points / indicators. FIX: surface them -- an on-screen "wild encounter" indicator when a roamer is near, a MISSIONS/KARMA HUD entry (a board or NPC) showing available missions + the district karma tier + how to raise it, and make the scout flow obvious. (index.html HUD + encounters/missions/karma.)

9. INTERIOR BACKGROUNDS = CUSTOM PER BUILDING (NOT menu_bg everywhere) -- right now EVERY building interior shows the menu_bg.mp4 backdrop. WRONG. ONLY the Town Hall (the Clash-Royale/tower-defense hub) should use menu_bg.mp4. Every OTHER building (the stores/shops) needs its OWN CUSTOM interior background per building type (chop shop, bank, infirmary, arcade, etc.), 3D + cool, with the building's handler/shop-owner standing in it talking. FIX: generate a custom interior bg per building (CF/Leonardo, now unblocked), wire each building's #int-bg to ITS bg (Town Hall keeps menu_bg), keeper/owner in front. (art-gen building interiors + index.html interior wiring + loops.js scoped to TH only.)

10. WORLD-MAP MARCH -> NO RAID LOADS -- the world map is "much better" and the crew MARCHES to the enemy, BUT on arrival NO enemy map loaded and the player couldn't raid/kill anything. The march->AK_RAIDSCENE.launch handoff isn't loading the enemy base (scout scene) + starting the raid. FIX: worldmap march arrival must open the enemy's base (raidscene scout scene rendered from their layout) -> START RAID -> the base-as-battlefield combat actually runs. (worldmap.js march -> raidscene.js -> modes.js raid.)

11-15. RESOURCE / ECONOMY SYSTEM (BIG -- design-first; the AK_2D_3D_CONCEPT secs 2+5 design exists but is NOT wired; "thought we had all of that implemented but it's not actually working"). Operator's full spec:
  - TOOLS REQUIRED to harvest (no walk-up-and-grab). Tools cost gold/gems OR are tradable for vegetation. Tool tiers set speed + bonus loot + durability.
  - TIME GATES on chop/mine/grow (Sunflower-Land + Clash-of-Clans timers, e.g. ~25 min to mine a node, not instant). Gathering + collecting takes real time.
  - BUILDERS: only X per Town Hall level; each builder IS one of the DOGS in the card collection (the cards = the people running the city). A card's LEVEL + the Town Hall LEVEL set: gather/build/upgrade/train SPEED, high-gear loot tier, what the store offers.
  - RATIO SCALE (designed, NOT random): skill <-> resource <-> time <-> gems <-> currency. What resources convert to: buildings, upgrades, trade-for-currency, trade vegetation <-> resources. A real economy ratio table.
  - AESTHETIC + PATTERNED placement: resource nodes designed TO the maps (not randomly scattered) -- patterns/aesthetics per district.
  - RESEARCH Sunflower-Land (planting, currency trading) + Clash-of-Clans (chop times, resource costs, builder huts) before designing.
  - DELIVERABLE: AK_RESOURCE_ECONOMY_DESIGN.md (the full system + the ratio/timer/tool/builder tables) -> THEN implement across worldverbs (tools+timers), buildmode (builders+gardens), economy (ratios+conversions+trading), Town Hall (builder caps + speed scaling by card/TH level).

16. MAIN GAME (battler) ONLY VIA TOWN HALL -- the Clash-Royale battler/main game should be reachable ONLY by entering the Town Hall building (Town Hall = the main-game door). Remove/redirect every OTHER battler entry (Arena building, lobby PLAY pillar, any ?go=match) so the Town Hall is the single way in. (index.html: Town Hall interior/panel launches the battler; other entries redirect to or are removed.)

17. BATTLER MENU X -> DISTRICT MAP -- the main game menu (battler / game.html) needs an X (close) button that exits the battler and returns to the DISTRICT MAP (the hub world). Reuse the post-match return-to-worldmap flag contract. (game.html: add a close X -> set ak_return_worldmap + exit to hub.)

18. PER-DISTRICT AMBIENT MUSIC -- background theme music plays while walking each district; the soundtrack/vibe REFLECTS each district (Home Turf vs Downtown vs the Yards vs Docks vs Factory Row etc.), and changes when you cross into a new district. It must NOT sound like battle/combat music -- ambient/exploration mood per district. (Reference AK_AUDIO_MASTERPLAN.md; implement per-district ambient loop that crossfades on district transition; procedural Web-Audio synth pads if no track assets, or generated/licensed loops. Hub-only, ducks under SFX, respects mute.)

19. TOWN HALL ARTWORK -- generate custom art for the Town Hall, consistent with the gritty gold-cyberpunk theme. (CF art-gen: Town Hall building exterior + interior; wire into the hub building sprite + the interior bg. Town Hall keeps menu_bg video as its interior backdrop per #9, but its building-on-the-map art + any framing should be custom.)

20. METAL HAS NO ICON + NOT SHOWN IN THE RESOURCE TASKBAR -- the metal resource is missing an icon and isn't displayed in the top HUD currency bar. FIX: add a metal icon + ensure the metal chip renders with its live value (akHud). (index.html #phud / akHud.)

21. SCRAP PICKUP DOESN'T INCREMENT (BUG) -- the resource shown with the nut/peanut emoji (scrap) does NOT increase when harvested; wood + stone DO work. Likely cause: scrap harvest banks into the rarity-keyed p.scrap.Common pocket while the HUD chip reads a flat p.scrap, so the displayed number never moves (and/or the grant path differs from wood/stone). FIX: make scrap harvest + the scrap HUD chip read/write the SAME field so a pickup visibly increments. (worldverbs harvest grant + akHud scrap chip + economy.)

## Sequencing
- The DOM graphics batch (wdju6v37q: finish-shop + lobby + hub-DOM) is landing; it edits index.html, so items 1 + 6 (index.html) wait for it to avoid a clobber.
- Then ONE fix batch: 1 (HUD) + 6 (loadscreen) in index.html; 5 (nav) in game.html; 2 (wall combat) in modes/raid/buildmode; 3 (garden economy) in buildmode/worldverbs/economy; 4 (scout mini-game art) in arcade + raid routing. Deploy via e5, test front+back, audit.
- These are GAMEPLAY/UX fixes, tracked alongside the graphics rollout (AK_GRAPHICS_UPDATE_PLAN.md).
