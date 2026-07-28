# Alley Kingz -- CAPTIVATION PLAN (research-backed, 2026-06-27)
*"Immersive yes, but not captivating." The fix: AK has the WORLD but no perishable, escalating, loss-anchored reason to return on a clock. Researched against Clash Royale, Marvel Snap, Genshin, Hay Day, Merge Tactics, EVE/Albion/RuneScape, GTA/RDR2/Rust, Hades/Diablo. Every item maps to OUR existing code + canon. Pairs with AK_COMBAT_DIRECTION.md (real-time MOBA map combat) + AK_CORE_LOOP_CANON.md.*

## THE DAILY HOOK (the #1 fix -- a perishable reason to log in)
1. **BLOCK TRIBUTE LADDER** (game.html ~7296-7338): the login streak ALREADY counts days + resets on a miss, but pays nothing except a Day-7 key. Attach an escalating soft ladder via AK_ECON (Day1 gold -> Day2 scrap -> Day3 bones -> ... -> Day7 key, then loop bigger), and IGNITE the #dc-streak chip on fire at 3+ days (Clash Royale's burning profile). Loss aversion (~2x gain) makes breaking the chain feel like losing -- the highest-leverage move, already half-built.
2. **ONE FRONT DOOR**: unify the game.html lobby claim with seasons.js doCheckIn() so one tap pays soft reward + Marks + advances both streaks (today they are fragmented = weak).
3. **RAID STAMINA "BONES TO RUN"**: an 8h time-regen cap (copy production.js CAP_HOURS=8, deterministic) on reward-raids. Optimal to spend before it caps (Genshin resin) = the literal "achieve something on a deadline." Refill by TIME or BONES only, NEVER gems. Story/free-roam/Watch stay unmetered (GTA feel survives).
4. **DAILY HIT LIST + COUNTDOWN + 3 CLAN DUTIES**: add "RESETS IN 4h" to the Fixer + shop; 3 faction-scoped duties (win a tower match / run a raid / stand a Watch shift) feeding Alley Pass XP via the live ak-quests -> AKSocial.claimGrants rail (Marvel Snap's daily->pass pipe).

## TWO CLOCKS, DELIBERATELY SEPARATED (Brawl Stars split)
- **COMPETITIVE (monthly reset + seasonal exclusive -- the Merge Tactics loop the operator loves):** BLOCK REP, a PvP-only trophy that drives the canon ladder (Stray->...->King of the Block). Tower-lane win +Rep / loss -Rep, with Apex demotion protection. MONTHLY soft reset on the 1st. A seasonal EXCLUSIVE dog card earned via Rep -- but COSMETIC/shard/free-track, NEVER raw power (parity law). Rep buys NOTHING at the Fence -- ladder only.
- **ECONOMY (permanent, never resets):** the Fence + bartering + farming progression carries across seasons. Internal economy SEASONS (winter/summer) change crop yields + Fence prices + scarcity, but your WEALTH is not wiped. Competitive churn kept hard-apart from the permanent economy.

## THE EMERGENT LAYER (three deterministic clocks -- never the same twice, all parity-safe, no client RNG)
1. **DAY/NIGHT** (new daynight.js, copy seasons.js skeleton, anchor to LOCAL PT): different NPCs/prices/events by phase; a night market that closes, a dawn bonus (appointment mechanics).
2. **WEATHER as a world signal** (promote the existing weather): affects farming yield + raid odds + encounter spawns; legible variable state (Pokemon GO boost ring).
3. **AI CHAOS / emergent stories**: the 29 population dogs act on their own offline -- turf flips, random raids/deals/betrayals; a "HIT OF THE DAY" named dog surfaces in a district for 24h (Genshin LTE); a Nemesis that remembers how it beat you + a block that can flip while you sleep (Rust curiosity gap). Structure = Crown Bloodline; chaos = the streets between (the GTA feel).

## REAL-TIME MAP COMBAT (per AK_COMBAT_DIRECTION.md -- the combat half of captivation)
Enhance AK_MODES.openWorldMoba (raids already route here) into a real-time Mobile-Legends/Twisted-Metal action battle: move + aim/fire lasers (arsenal) in real-time, cards cast their REAL abilities with real stats, MOBA HUD (skill icons/cooldowns/HP). Mini-games stay as subsets. engine.js (tower lane) frozen, Arena-only.

## PRIORITIZED BUILD ORDER (highest dopamine-per-effort first; each = its effectiveness)
- P1 Block Tribute ladder + burning chip + one front door -- loss aversion, half-built already
- P2 Daily Hit List countdown + 3 Clan Duties -> Alley Pass -- perishable value + duty->pass pipe
- P3 Always-on GOAL BEACON HUD (next rung + progress bar + an Old Pack stake-line) -- goal-gradient pull
- P4 Raid Stamina "Bones to Run" (8h cap) -- the deadline on the core RPG loop
- P5 Street Talk LIVE event feed + intervene/ignore street events -- offline curiosity gap
- P6 Floating Fence prices (ticker) -- the EVE/RuneScape "second game"
- P7 Day/Night + weather as a world signal -- appointment mechanics + novelty
- P8 Per-chapter bounded economy modifiers + raid-fed Fence buy-order sink -- the self-feeding loop
- P9 Variable-ratio Scrap Crate reveal + rank-promotion cinematic -- the dopamine spike
- P10 Competitive LADDER (Block Rep, monthly reset, seasonal exclusive) -- 5 stacked retention levers + pulls LAPSED players back
- P11 Real-time MOBA map combat (openWorldMoba enhance) + emergent Nemesis persistence -- mastery + player-authored revenge

## PARITY HARD-LAW (non-negotiable)
Genshin resin + Snap pass cards are monetized -- OURS CANNOT be. Stamina refills by TIME/bones only, never gems. Scrap Crate rares + the seasonal exclusive dog = cosmetic/shard/bones/free-track, NEVER raw power. Gems stay cosmetic-only. Sensory package on every piece (it must look + feel good).
