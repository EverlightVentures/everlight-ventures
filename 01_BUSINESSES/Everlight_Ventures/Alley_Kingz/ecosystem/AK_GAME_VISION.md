# ALLEY KINGZ -- GAME VISION (north-star; operator 2026-06-19)
> The full integrated game, in the operator's words. This is the END-STATE the 3 V2 builds (AK_V2_BUILD_SPEC.md) climb toward. HARD philosophy already locked: the spread-out CITY is the menu (never a one-screen button menu again); every custom graphic old + new stays, re-styled, never deleted. Companion to AK_LIVING_WORLD.md + AK_RAID_DEFENSE_SYSTEM.md + AK_WORLD_BIBLE.md.

## THE CORE LOOP (Clash Royale economy x Clash of Clans base x Brawl Stars battle)
1. BUILD + MANAGE A CARD COLLECTION: collect cards, manage them, UPGRADE them (Clash Royale). Upgrading costs GOLD.
2. GOLD ECONOMY: earn gold to build/upgrade your buildings + cards (production buildings on FACTORY ROW already seeded: Gem Mine/Gold Mint/Card Forge/Research Lab/Generator).
3. TOWN HALL GATING (Clash of Clans): the Town Hall caps everything. You can only level the Town Hall once your CARD COLLECTION is leveled enough. So: cards -> gold -> upgrades -> Town Hall unlock -> higher ceiling. Progression gate, not a paywall.

## PERSONAL BASE / ISLAND (same resources, unique setup = the differentiation)
- EVERY player has the SAME resource set available, but DECIDES: which SKINS they unlock, how their base/map is LAID OUT, their card levels, their handlers/lieutenants.
- Each player POSITIONS THEIR OWN MAP -- a personal island/base they build onto. A ~9-tile base grid (horizontal/vertical placement), spread across the district maps (collection / garage / factory / etc. are the buildings they arrange).
- Uniqueness = layout + skins + card levels + loadout. Same toolbox, different fortress. THIS is the personal-strategy layer.

## BATTLE MODE = BRAWL STARS x CLASH OF CLANS x MINI-MAP HYBRID (on the defender's real base, real-time adaptive)
- THE hybrid (operator's exact tag): Brawl Stars FEEL (zoomed-in top-down real-time action) + Clash of Clans ATTACK STRUCTURE (drop + structure your cards/troops onto the DEFENDER'S actual base layout) + the MINI-MAP tying perimeter and positioning together. The defender's built base IS the battlefield -- never a generic arena. This is the deepest engine evolution and gets its OWN research+design pass before building (reuse engine.js, never fork).
- When a fight happens, the battle map IS whoever is getting attacked -- the DEFENDER'S actual base layout. Not a generic arena.
- Everyone goes in, the camera ZOOMS IN (Brawl Stars feel); the mini-map is the Clash of Clans attack view (structure troops, drop cards around the perimeter).
- In MAIN BATTLE MODE it zooms OUT a touch so you see the perimeter + how to attack.
- Co-op: you drop your cards/troops structured AROUND your teammates' positions on the defender's map (squad defense/attack).
- HARD CONSEQUENCE: the battle maps must be FLEXIBLE + adapt in REAL-TIME to each individual's base/territory layout. The defender's built map = the battlefield.

## CLANS + TERRITORY (sum-of-radii)
- Every CLAN has a TERRITORY. Every territory has clan MEMBERS. Every member has a RADIUS around their base; the union of all member radii = the total clan area.
- If ONE member is attacked, the CLAN responds (come help -- the socially-radioactive hook). If the whole VILLAGE is attacked (night horde), everyone defends together.
- The world map = a grid of personal islands, grouped into clan territories.

## WORLD + ENCOUNTERS (on top of the base layer)
- Walk the districts (multi-map, DONE in Build 1). Random ENCOUNTERS like Pokemon -- wild DOG BREEDS (not generic monsters) -- win random loot/cards.
- NIGHT: go outside the zone / on the city perimeter and mutant/zombie dog packs attack (Whiteout Survival / Dark War Survival DNA). Need your CLAN to help, or the whole village gets swarmed and everyone defends. OR a rival clan raids.
- Layers stacked on top: cards, skill points, handlers (6 commanders), Lieutenants, skins, mini-maps, "go in here / go in there" exploration.

## GAMEPLAY MODES (all from one base)
- MACRO: clan wars, world map, territory, village defense.
- MICRO: the single battle (Brawl-Stars-feel on a base).
- MINI: mini-games, random encounters, gather nodes.
- PERSONAL STRATEGY: your base layout + collection + loadout + skins.
All equate from the same foundation -- one game, many lenses.

## HOW IT MAPS TO THE BUILD ORDER (research-first before each new piece, per operator rule)
- Build 1 (DONE): multi-map districts -- the walkable world the base/clan/battle layers sit in.
- Build 2 (NEXT): night-raids + movement fix -- the PvE night-horde + clan-defense on-ramp; also the random wild-dog encounters. Production buildings + gold economy start feeding here.
- Build 3: world-map + bases -- becomes "personal islands you BUILD + arrange, grouped into clan territories, raided async." Bot bases = snapshot real layouts.
- NET-NEW pieces this vision adds (each gets a research pass before building, like the V2 workflow):
  - CR card-collection ECONOMY + Town-Hall gating (cards -> gold -> upgrades -> TH level) -> M02 BUILDING + M06 ECONOMY + M07 PROGRESSION.
  - PERSONAL BASE BUILDER/EDITOR (position your own ~9-tile island; same resources, unique layout) -> new M02 sub-system.
  - BRAWL-STARS-FEEL BATTLE ON THE DEFENDER'S ADAPTIVE BASE MAP (zoom, drop cards around teammates, real-time per-layout) -> the big engine.js/battle evolution; reuse engine.js, do NOT fork; likely the deepest research+build of all.
  - CLAN TERRITORY = union of member radii -> M04 CREW + M11 + the world map.
- CRYPTO guardrail still hard: all of the above economy is SOFT currency (gold/gems/bones); $BCARDD/ALK stays cosmetic + geo-gated.

## SYSTEMS + METRICS THE DEEP-DIVE MUST NAIL (operator 2026-06-19, "the best hybrid game of all time")
Fusing the keen-edge elements of: Pokemon + Golden Sun (overworld wild encounters, djinn/genie superpowers) + Duel Masters + Gods Unchained + Clash Royale + Clash of Clans + Sunflower Land + GTA + Dragon City / Jurassic Park Builder (breeding) -- into ONE 2.5D WebGL world map with micro/mini games + a full economy. Each system needs its real metrics + logic researched, then tailored:
- CARD-DEPLOYMENT METRICS x TOWN HALL: HOW MANY cards can you drop, and what gates it? (Clash Royale elixir curve + Clash of Clans army-camp capacity + Town Hall level). Everyone has the SAME cards/buildings/ecosystem -- the differentiation is how you UPGRADE cards, MANAGE economy, and lay out your BASE. A level-2 card vs a level-10 card (striking, range, HP) plays totally differently. Deployment cap, card cost, draw, and stat curves all scale off Town Hall + upgrades.
- CARD COMBOS EVERYWHERE: combo/bonus rules already exist on the battler/main-tower map. They must extend across the ENTIRE world map / Clash-of-Clans / Dark-War layer (faction + role + breed combos in base defense, raids, encounters), not just the 1v1 battler.
- WILD ENCOUNTERS (Pokemon / Golden Sun): walking the world -> run into WILD CREATURES (dog breeds) -> fight (and maybe capture). Add a Golden-Sun djinn/genie superpower layer -- collectible powers that modify your loadout.
- BREEDING / HYBRID CARDS (Dragon City + Jurassic Park Builder): players BREED two opposite breeds -> EGG -> germinate/incubate -> a HYBRID dog card. Make different breeds, make labs. Major retention + collection driver. CRYPTO/LEGAL HARD GATE: breeding stays SOFT-currency + fun only (the Axie breeding-for-profit collapse + securities exposure is the cautionary tale) -- hybrids NOT minted-for-sale / not pay-to-breed-for-profit in v1; cosmetic/collection value only; Theo GC sign-off before any tradeable hybrid.
- UNIFIED ECONOMY: gems (endgame/premium) + scraps + gold + cards-to-upgrade-towers -- one coherent faucet/sink web across build/upgrade/breed/raid/encounter. Soft currency only; $BCARDD/ALK cosmetic + geo-gated.
- SENSOR PACKAGES FOR EVERYTHING (operator 2026-06-19): every system AND every entity (card/unit/building/enemy/gather-node) ships a defined SENSOR PACKAGE = (1) GAMEPLAY sensors -- detection radius, aggro/trigger range, striking range, vision, line-of-sight, encounter-trigger radius; AND (2) INSTRUMENTATION -- the telemetry events + metrics tracked for balancing, analytics, anti-cheat, and perf. If it exists, it is measured and it has defined ranges. Observability + tunable metrics are a default, not an afterthought.
- GAMEPLAY LENSES from one base: macro (clan war / world / territory) | micro (the Brawl-Stars x CoC x mini-map battle) | mini (encounters, mini-games, gather) | personal strategy (collection + layout + loadout + breeds).
- NESTED STRATEGY LAYERS (operator's organizing principle): MICRO strategies (the per-encounter move -- collide/avert/jump-out -- and the in-battle card drops) are EMBEDDED in MINI strategies (winning a battle / mission / encounter), which are EMBEDDED in the MACRO (clan war, world, territory, your base/city, the long game). Every granular choice rolls UP: win the micro -> win the mini -> win the macro. The whole game is this fractal -- small decisions compounding into the meta. Design + balance + the SENSOR PACKAGES must respect the nesting (a micro stat feeds a mini outcome feeds a macro standing).
All reuses the existing engine.js / cards / handlers / economy + the 2.5D Canvas2D stack -- never a rebuild, Three.js stays V3.

## MONETIZATION + WORLD-COMBAT + SKILL TREES + DECK-AS-WORKERS + FORTRESS (operator 2026-06-19, "take the best, most unique elements of each game")
Central game = the PRINCESS-TOWER battle (Clash Royale). Everything else is the wrapper. Research each game's MARKET/selling-pitch and fold the products in (soft-currency / cosmetic / convenience ONLY -- never pay-to-win-power, never $BCARDD-gated; CoC/Pokemon ethical-F2P model):
- MONETIZATION PRODUCTS (the "design selling pitch" of each game): SHIELD (CoC -- buy 8h/24h/weekend protection so you don't get looted + Town Hall degraded while away); REPEL (Pokemon -- avoid wild encounters while traveling); SKINS (Brawl Stars / Fortnite -- pure cosmetic vibe, the whole hook); REVERT/HEAL POTIONS (undo degradation, heal troops). Each is a shop item. Price + market like the source game. Crypto-safe: convenience+cosmetic, not power.
- WORLD-MAP REAL-TIME COMBAT MODE (Mobile Legends vibe): when WALKING the world map it is a real-time RPG/MOBA -- you have spells/magic, attack things, with friends, using the SAME cards but a DIFFERENT mode. Upper TASKBAR shows Mana / energy / elixir / health bars. Solo or with a pack.
- WILD ENCOUNTERS -> TOWER BATTLE: step too far / off the path -> "a wild dog appeared" -> a random 1v1 or 2v2 (you + partner) that plays like the princess-tower battle (use your cards) -> win money/loot. Your clan may move on -> catch up. (This is exactly why REPEL is a product.)
- SKILL TREES (Skyrim + Shadow of Mordor -- operator loves these): deep skill trees + upgrading for cards/handlers/commanders. (handlers_data.js already has Bones skill trees -- extend the pattern.)
- DECK-AS-WORKERS (the key dual-purpose): your TOWER deck is ALWAYS 11 cards. But those same cards ALSO are your CITY WORKERS / managers / farmers / occupations, assigned to buildings BY FACTION (cards have factions + skill sets + handlers). Your TOWN HALL (dog-pound/doghouse, keep it themed) caps how many workers you have AND caps your max card level (loot degrades the Town Hall -> degrades your cards). Level up army/barricades/kitchen/etc. in the CoC/Dark-War layer.
- FORTRESS + NIGHT DEFENSE + NEW LOOT LOOP: gather elixir/energy/WOOD/STONE -> craft materials -> build walls/fences around your base + place your Town Halls/castles strategically (CoC base-building). At NIGHT a wild dog pack (or a rival player) attacks; your fence buys your crew time; your crew defends. If troops die -> heal at the infirmary or recruit new (costs wood/stone). The new world map = a whole NEW loot economy (wood/stone/materials) layered on the card economy. Dog/Alley-Kingz themed throughout.
- BUILD OUT EVERY "COMING SOON": every building/section currently marked 'soon' (Card Lab/Collection, Trophy Hall, Arcade, production interiors, etc.) gets RESEARCHED, designed to be the best version, and given BRAND-NEW ARTWORK with defined prompts (Leonardo / CF Workers AI / Seedance), art tier possibly scaling by RARITY. Nothing stays a placeholder.

## BATTLE/GAME MODES + MODE-SPECIFIC CAMERAS (operator 2026-06-19): "graphics and angle change according to the concept"
The game is MULTI-MODE, and EACH mode has its OWN camera angle + render style (the camera + graphics swap per concept). One roster of cards/dogs, many lenses:
- TOWER BATTLE (the core): Clash-Royale princess-tower, top-down lane card battle. (engine.js -- exists.)
- WORLD MAP (overworld): 2.5D top-down walk + drive. Dogs PILOT RIGS/CARS (Twisted-Metal canon) across the world; the avatar can be in-rig or on-foot.
- WORLD REAL-TIME COMBAT (Mobile Legends): overhead real-time spell/ability combat while roaming.
- WILD ENCOUNTER (Pokemon): step off the path -> "a wild dog appeared" -> resolves as a tower-style card battle.
- NEW -- GULAG / DOOMSDAY SHOOTER (CoD Mobile / Warzone Gulag): JUMP OUT of your car and engage a 1v1 or 2v2 SHOOTOUT -> the mode converts into a doom/shooter micro-game (a mini-game inside the mini-game). Tighter, lower camera angle, shooter graphics/perspective -- a hard visual + camera shift from the top-down world. Win/lose feeds the same economy.
- ENCOUNTER RESOLUTION = THE PLAYER'S MOVE DECIDES THE MODE (operator: "it depends on their move") -- the signature unifying mechanic: when two dogs/cars meet on the world map, what they DO picks the battle. Cars COLLIDE head-on -> TOWER battle (Clash-Royale cards). AVERT / swerve past -> Brawl Stars / Mobile Legends real-time battle. JUMP OUT -> Gulag/Doomsday shooter (1v1/2v2). One encounter, branches into different game modes by player intent -- emergent + skill-expressive. The HUD/controls read the move (collide vs swerve vs dismount) and route the camera + mode accordingly. ALSO ELECTIVE: a player can just go to the TOWN HALL (or directly challenge / pick a fight) to battle on demand -- battle is available both emergently (encounters) and electively (player choice), never forced.
- ART: every mode + system here needs BRAND-NEW art (mode backdrops, the Gulag-shooter set, car/rig sprites, the walk-cycle sheet, per-coming-soon sections, rarity-tiered). Tracked via each research track's art list + the coming-soon art list; generated in the gold/gritty dog house style on the secured CF/Leonardo key as each piece is built. Art never gates a launch (glyph/procedural fallbacks hold).
PRINCIPLE: the engine routes to a mode; each mode owns its camera + art treatment. Reuse the existing battler for card modes; the Gulag-shooter is a distinct net-new micro-mode (research+design its own pass before building -- it is NOT the battler). Cars/rigs + jump-out is a world-avatar upgrade (pairs with the walk-cycle sprite-sheet art). All dog/Alley-Kingz themed, crypto-safe soft-currency rewards.

## ARCHITECTURE RULE -- ONE CONSISTENT SYSTEM, PER-MODE CUSTOMIZABLE MENUS (operator 2026-06-19)
Every shared mechanic (SKILL TREE, upgrade menu, inventory, loadout, economy) is ONE consistent core system -- one data model + one ruleset -- but each GAME MODE renders its OWN customizable MENU/skin on top. The skill tree shows up in EVERY mode, but it LOOKS different per mode: Doom/shooter = gritty weapon/perk tree; breeding = lab/genome tree; tower-defense = strategic grid; Town Hall = building-blueprint tree. SAME underlying data + logic, different presentation. A skill point / level / upgrade / currency means the SAME thing everywhere -- only the view changes.
This is the modular EventBus/adapter pattern (ALLEY_KINGZ_CORE) extended to the UI: build the core ONCE, theme per mode. Benefits = consistent mechanics + far faster builds (one system, many skins) + the per-mode "vibe" the operator wants. Precedent: the existing handler "Bones" skill trees (handlers_data.js); theming via the vantaris design tokens. HARD RULE: never fork a MECHANIC per mode -- fork only the VIEW/skin. Each mode = {shared core systems} + {its own menu skin + camera + art treatment}.

## OPERATOR INTENT (verbatim flavor)
"You have to build your card collection, manage it, upgrade it... get gold like Clash Royale... once the collection is leveled enough you level up your Town Hall. Everybody has the same resources -- what makes it unique is the player decides which skins, how their map is set up, their card levels. When it's time to fight it's like Brawl Stars, but the map is whoever's getting attacked -- everyone zooms in, mini-map like the Clash of Clans attack, structure troops, drop cards around your teammates' map. Battle maps adapt in real-time to each individual's territory. Every clan has a territory, every territory has members, every member has a radius, the union is the clan area. One person attacked -> the clan helps. Wild Pokemon a.k.a. dog breeds; outside the zone at night like Whiteout/Dark War, zombie mutant dogs attack, need your clan. Macro, micro, mini, personal strategy -- all from the base of this game."
