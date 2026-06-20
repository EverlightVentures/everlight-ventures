# ALLEY KINGZ -- SEASONS / ECONOMY / TRADING / MISSIONS + FULL CONTENT BACKLOG (2026-06-20)
> Operator ask: "include dog-themed seasons and economies per season, trading mechanics and missions like Sunflower Land; list ALL the mini-games, micro-games, all the coming-soons not built yet -- I want to make a plan for you."
> This doc = (1) the new seasons/trading/missions design, (2) the complete backlog with STATUS so you can prioritize. Companion to AK_GAME_VISION (north-star), AK_SYSTEMS_DESIGN (build bible), AK_RAID_DEFENSE_SYSTEM, AK_AI_BOTS_PLAN.
> STATUS legend:  [LIVE] shipped  ·  [DSGN] designed in a doc, not built  ·  [SOON] a building stub (url='soon'), nothing behind it  ·  [NEW] proposed here, no design yet.
> CRYPTO GATE (applies to ALL below): every economy is SOFT-currency / cosmetic; $BCARDD/ALK is cosmetic + geo-gated ONLY; no token in trades/missions/seasons (RMT + securities line). Parity invariant: gems skip TIMERS, never raise a cap.

==================================================================
## PART 1 -- SEASONS, SEASONAL ECONOMY, TRADING, MISSIONS (the new ask)
==================================================================

### A. DOG-THEMED SEASONS (Sunflower-Land "chapters" model)  [NEW]
The world runs in themed multi-week CHAPTERS that re-skin the hub, drop a cosmetic set, rotate missions, and run a seasonal currency + leaderboard. ET-anchored start/end (audience-clock doctrine), ~6-week cadence.
Proposed rotation (dog/street/crypto flavor):
- **Junkyard Dynasty** (launch) -- scrap/industrial theme, oil-drum fires, the Yards lit up.
- **Neon Howl** -- synthwave neon, downtown takes center, glow cosmetics.
- **Dog Days** (summer) -- block-party/heat, kiddie-pool + grill props, bright palette.
- **Blood Moon** (Halloween) -- the zombie-stray night-waves ramp, spooky skins -- ties to FORTRESS night-defense.
- **Frostbite Streets** (winter) -- snow on the asphalt, Whiteout survival vibe, frost cosmetics.
- **Golden Leash** (anniversary) -- crown/gold everything, best rewards, throwback skins.
Each season ships: a re-skin (hub tint + props + a seasonal district background variant), a 30-tier seasonal track (the Alley Pass, already [LIVE] as a building -- re-theme per season), a seasonal cosmetic set (Drip), a story mission chain, and a leaderboard with season-end rewards.

### B. SEASONAL ECONOMY  [NEW]
- **Seasonal currency** = "**Marks**" (or per-season flavor name) -- earned ONLY from that season's missions/events, spent in the **Seasonal Stall** (limited cosmetics + a few QoL), and **RESETS to 0 at season end** (hard sink -> no inflation, drives "earn it now" urgency). Unspent Marks -> auto-convert to a trickle of gold at rollover (anti-feel-bad).
- **Core currencies persist** (gold/gems/scrap/fragments/keys + the Town Hall meta-gate) -- seasons never touch them.
- Crypto-safe: Marks + cosmetics only; never $BCARDD/ALK; never cashable.

### C. TRADING MECHANICS (Sunflower-Land marketplace, de-risked)  [NEW]
A new **TRADING POST** building (the keeper = "Switch the Broker"). Player-to-player exchange of SOFT items only:
- **Barter board:** list a spare CARD or COSMETIC for gold/scrap, or card-for-card. Server-authoritative (a `ak_trades` edge fn + table on Supabase mfghdobptredxxhbjwyz), escrow-style so nobody gets scammed.
- **Gates (anti-abuse / anti-RMT):** min Town Hall level to trade; daily trade cap; trophy-band matching; a tax (gold sink) per trade; NO $BCARDD/ALK ever in a trade (kills the securities/RMT exposure); duplicates/cosmetics only -- never account-bound progression.
- Later: a passive **Auction Stall** (list, walk away, sell offline) -- the deck-as-workers economy feeds it.

### D. MISSIONS (Sunflower-Land Deliveries + Chores) -- ties to the NEW interior keepers  [NEW]
The building **keepers you just got** (Coach Diesel, Prospector Pip, Mama Bones...) become the **mission-givers**:
- **Deliveries:** a keeper asks for items/actions ("Bring me 8 scrap", "Win 2 arena matches", "Breed a Rare pup") -> reward gold/Marks/cosmetic. Rotating, per-keeper, personable (their voice). This is the reason to walk the world + visit buildings.
- **Daily / Weekly board:** extend the **Hit List** (already [LIVE]) -- rotating objectives, streak bonuses.
- **Seasonal story chain:** a multi-step narrative quest per season (the keepers + a seasonal antagonist), big end reward.
- **Crew missions:** co-op goals for your crew (ties to the [DSGN] social layer).
All rewards soft/cosmetic/Marks; mission text later voiced from `ak_flavor_pool` (AK_AI_BOTS_PLAN).

==================================================================
## PART 2 -- COMPLETE BACKLOG (everything not finished)
==================================================================

### COMING-SOON BUILDINGS (url='soon' -- literal stubs, nothing built)
1. **TROPHY HALL** [SOON] -- trophies / profile / achievements / season leaderboard display.
2. **GEM MINE** [SOON] -- production: gems (note: gems are server-only -> may produce a tradeable gem-shard or scrap instead).
3. **GOLD MINT** [SOON] -- production: gold (offline accrual, collect on visit).
4. **CARD FORGE** [SOON] -- production: card fragments; later the crafting/forge UI.
5. **RESEARCH LAB** [SOON] -- production: skill points + the CARD skill-tree UI (Collar Constellations).
6. **THE GENERATOR** [SOON] -- production: power (gates the other producers -- no power = cascade, per AK_RAID_DEFENSE).
7. **THE ARCADE** [SOON] -- the mini-games hub (see PART 3).
> All 7 already have an interior keeper + "coming soon" gate LIVE -- they just need the activity behind the keeper.

### BUILDINGS WITH A LIVE MENU (done, behind the new keeper now)
THE DROP (gem shop) · THE GARAGE (deck builder) · THE WARDROBE (Drip cosmetics) · THE ARCHIVE (Codex) · CREW YARD (crews/chat) · PASS HOUSE (Alley Pass) · THE FIXER (Hit List) · THE KENNEL (handlers) · THE STREET (street mode) · TOWN HALL/ARENA (the battler) -- all [LIVE].

### DESIGNED-BUT-UNBUILT MODES & SYSTEMS (specs exist)
- **Town Hall meta-gate** [LIVE] (card-level cap + upgrade) -- the keystone, done this session.
- **Production loop** [DSGN] -- the 5 producers above (Bitcoin-Miner residual income, offline accrual, AK_RAID_DEFENSE sec.3).
- **RAID + BASE-DEFENSE** [DSGN] -- the Brawl-Stars x CoC battle-hybrid; targeted building damage, crew reinforcement, shields (repriced soft), revenge. THE big greenfield (AK_RAID_DEFENSE + AK_SYSTEMS_DESIGN S6).
- **WILD ENCOUNTERS** [DSGN] -- Pokemon-style visible/avoidable strays on the world map -> battler (?mode=encounter); capture = soft collectible.
- **BREEDING (The Kennel)** [DSGN] -- Dragon-City fixed-roster breeding; bred dog = a cards.json object, stats decoupled from parents, Mythics don't breed, soft-currency sink.
- **CARD SKILL TREES (Collar Constellations)** [DSGN] -- per-card mastery trees (handler "Bones" trees already [LIVE]); via Research Lab.
- **FORTRESS + NIGHT DEFENSE** [DSGN] -- wood/stone loot economy, walls/barricades, night zombie-stray waves, crew defends, infirmary heal/recruit.
- **STREET WAR / WORLD MOBA** [DSGN] -- Mobile-Legends real-time world combat (health/energy/mana taskbar); its own research pass; never fork engine.js.
- **GULAG / DOOMSDAY SHOOTER** [DSGN] -- jump-out 1v1/2v2 CoD-Mobile-style micro-game; new camera/render.
- **ENCOUNTER-RESOLUTION-BY-MOVE** [DSGN] -- collide->tower battle / swerve->MOBA / jump-out->Gulag (the signature router).
- **BOT LIVING-WORLD** [DSGN] -- ak_flavor_pool barks + snapshot-as-bot rival bases (AK_AI_BOTS_PLAN).
- **CARD PERSONALITY + SOUND + FEEDBACK packages** [DSGN] -- per-card {personality, voiceSet, sfxSet, lines, reactionProfile, hapticProfile}, faction-default + rarity-override (the post-systems layer).
- **SEASONS / SEASONAL ECONOMY / TRADING / MISSIONS** [NEW] -- PART 1 above.

==================================================================
## PART 3 -- MINI-GAMES & MICRO-GAMES CATALOG (for THE ARCADE + embedded)  [NEW]
==================================================================
ARCADE (standalone games, soft-currency rewards, daily play limit):
- **Bone Dig** -- grid dig/match for scrap + buried cards.
- **Hydrant Hustle** -- timing/tap rhythm; perfect taps = gold.
- **Scrap Sorter** -- sort falling junk into bins (reaction/puzzle).
- **Alley Dash** -- endless runner, dog on a rig dodging traffic.
- **Whack-a-Stray** -- reaction whack game.
- **Crown Match** -- memory card-flip (theme: the roster).
- **Two-Up / Coin Toss** -- light gamble vs the house, SOFT currency only, capped (no real gambling, no token).
MICRO-GAMES (embedded inside other modes -- the "micro inside mini inside macro" idea):
- **Gulag/Doomsday shooter** -- the jump-out duel (also a mode).
- **Lockpick** -- quick skill-check to crack a chest / breach a raid wall.
- **Mining tap-rhythm** -- inside the Gem Mine, tap the vein on-beat for a bonus.
- **Forge temper** -- timing bar to crit-forge a card fragment.
- **Lab hack** -- a wire/sequence puzzle to unlock a skill node faster.
- **Encounter QTEs** -- dodge/bark quick-time prompts that swing a wild encounter.
- **Kennel mini** -- a "calm the pup" rhythm during breeding for better odds.

==================================================================
## SUGGESTED PRIORITY (my recommendation -- you re-order)
==================================================================
1. PRODUCTION LOOP (the 5 producers) -- fastest visible payoff, the keepers already greet you there; residual income hooks daily play.
2. MISSIONS via keepers (deliveries + extend Hit List) -- reuses what shipped today, gives the world purpose.
3. WILD ENCOUNTERS -- reuses the battler, makes the walk meaningful.
4. RAID + BASE-DEFENSE -- the big hybrid; needs bot-bases first (AK_AI_BOTS_PLAN snapshot-as-bot).
5. SEASONS + seasonal economy -- wraps everything in a live-ops loop once there's enough to do.
6. TRADING POST -- after there's a deep enough item pool to trade.
7. ARCADE mini-games -- parallel, low-risk, art-driven.
8. STREET WAR / GULAG -- the deepest net-new modes; own research passes, last.
> Operator: mark your priority numbers / cuts on this list and I build top-down, research-first, one system at a time.
