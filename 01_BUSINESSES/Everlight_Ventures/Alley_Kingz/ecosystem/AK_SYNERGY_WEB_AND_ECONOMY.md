# Alley Kingz -- THE SYNERGY WEB + ECONOMY BALANCE
*How story/chapter mode + every system flow into ONE non-linear web (no compartments), with the story's themes trickling down into all gameplay + a lifecycle-balanced economy (generous early, aggressive endgame, always rewards engagement). The architecture behind "everything flows into each other."*
2026-06-25. Sits on top of AK_STORY_MODE_DESIGN.md (Crown Bloodline) + AK_MASTER_BUILD_PLAN.md (Crown Climb spine).

## 1. THE PRINCIPLE -- web, not ladder
The story (Crown Bloodline) is the SPINE, but progress is NON-LINEAR: there are multiple PARALLEL AVENUES, and every avenue's OUTPUT is another avenue's FUEL. No dead ends. The player picks their own path; it all channels back to the MAIN (rise to King + hold the block). "Chapter mode" = the story gates that the avenues unlock -- you advance the chapter by playing ANY avenue that meets the gate, not by a forced line.

## 2. THE AVENUES (parallel progression lanes)
1. **STORY / CHAPTERS** -- the spine (Crown Bloodline, 7 stages -> Gen II/III). Theme delivery + the gate that the other avenues feed.
2. **RANK / ARENA** -- PvP: 1v1 ladder + 2v2 pack hunts (tower battle). Competitive proving.
3. **TURF / BASE** -- district building, production, guarding/defense (Clash-of-Clans economy side).
4. **BLOODLINE / COLLECTION** -- cards, leveling, killstreak evolution, breeding heirs (Pokemon collection + the torch-pass).
5. **MARKET / TRADE** -- player marketplace + resource exchange (Sunflower-Land economy valve).
6. **CREW / SOCIAL** -- clan, co-op missions, clan wars, shared rewards.
7. **MINI-GAMES** -- arcade = crew TRAINING that feeds the others (never a standalone toy).

## 3. THE INTERSECTION MAP (the synergy -- each output is another's input)
- STORY chapters UNLOCK by hitting gates met through ANY avenue (rank tier OR turf control OR crew karma OR a season milestone) -- non-linear.
- RANK wins -> trophies -> division -> unlocks story chapters + better MARKET access + CREW standing.
- TURF production -> resources -> fuels BLOODLINE upgrades + MARKET trades + DEFENSE (guarding).
- BLOODLINE (stronger dogs) -> wins RANK + raids + STORY battles + makes better builders/guards/traders.
- MARKET trades -> resources for TURF/BLOODLINE; the economy's source/sink valve.
- CREW/SOCIAL -> co-op missions (STORY duties) + clan wars (TURF) + split rewards.
- MINI-GAMES -> training XP + resources feeding BLOODLINE + a STORY beat.
Result: the dog you raise (BLOODLINE) is the one you climb with (RANK) is the one that guards your turf (TURF) is the heir of your saga (STORY). One progression, many doors.

## 4. SUBLIMINALS TRICKLE-DOWN (themes -> mechanics + sensory, everywhere)
The Crown Bloodline themes are expressed as MECHANICS + a SENSORY payoff in every system, so the feeling is everywhere, not siloed in a chapter screen:
- **Rise from nothing** -> every system has a visible low->high climb (rank divisions, building levels, dog evolution/killstreak tiers, karma tiers, story stages), each with ESCALATING sensory payoff (glows, effects, fuller music). The killstreak DOG-GOD aura + the rank-up + the building-level-up all sing the same "you are rising" note.
- **Loyalty / clan** -> faction identity (color, banner, district music, crests) + crew bonuses + clan wars.
- **Turf / territory** -> the map, district control, guarding, seasons-as-eras.
- **Legacy / bloodline** -> collection, breeding heirs, the torch-pass, the Old Pack ancestors.
SENSORY PACKAGE = the de-emojify custom art (every surface), killstreak effects, per-district music, season visuals, the dream-vision delivery. This IS the subliminal layer -- it makes the theme FELT, not read.

## 5. THE ECONOMY -- 3 currencies + the trade valve
- **SOFT** (gold / wood / stone / metal / scrap / produce / seeds-crops) -- earned EVERYWHERE; the main flow. Sources: production, harvest, battles, missions, mini-games. Sinks: upgrades, seeds, transit fare, guarding, market fees.
- **HARD** (gems = Stripe) -- COSMETIC / SKIP / CONVENIENCE ONLY. NEVER power or loot (hard doctrine -- no pay-to-win). Sources: Stripe + sparse earn. Sinks: skins, killstreak effect-skins, time-skips, premium cosmetics, marketplace convenience, extra builder/loadout slots (convenience, not power).
- **MARKET** (player-to-player trade) -- resources + cosmetics exchanged; the balancing valve + a social/economic endgame.

## 6. THE BALANCE CURVE (the core ask: generous early, aggressive endgame, always rewards engagement)
Principle: **SOURCES reward ENGAGEMENT** (play any avenue -> earn); **SINKS scale with PROGRESSION** (the higher you climb, the more the next rung costs). A fun treadmill, not a paywall.
- **EARLY (Stray -> Warrior):** GENEROUS. Fast payouts, low sinks, quick wins on every avenue. Hook + teach the web. Build momentum.
- **MID (Warrior -> Right Paw):** SYNERGY. Avenues start feeding each other; soft flows but bigger sinks appear (higher upgrades, guarding upkeep). The player learns to specialize + trade.
- **ENDGAME (King + prestige):** AGGRESSIVE SINKS. Top-tier upgrades, throne defense, prestige/bloodline costs scale HARD -- the economy + trading TIGHTEN so there is always a chase. BUT defending, investing (build/market), and social (co-op/clan) are REWARDED richly -- the squeeze rewards the engaged player, it does not punish them. Trading becomes aggressive (the endgame meta) while defending + social pay.
- Anti-frustration rails: a daily/season floor of soft income; the market lets you trade out of a bottleneck; cosmetics (not power) are the gem sink so a non-payer can still reach the top via play.

## 7. SCALABILITY -- personalization + timelines
- **PERSONALIZATION:** the web supports archetypes, each a viable path to the crown -- the Fighter (rank), the Builder (turf), the Trader (market), the Diplomat (crew), the Collector (bloodline). The story adapts to how you actually play (the chapter gates accept any avenue). Loadouts/skins personalize the dog.
- **TIMELINES:** seasons (6-week eras) + generations (bloodline torch-pass) layer time. Each season is a faction's ERA + a soft economy refresh/prestige so the endgame stays fresh + the curve re-runs. Scalable: new avenues/mini-games plug into the intersection map without breaking the main loop.

## 8. BUILD IMPLICATIONS (how this guides the remaining work)
- The held/failed items each become an AVENUE node, wired into the intersection map (not standalone): farming/marketplace = the MARKET + TURF economy valve; guarding = TURF defense; co-op = CREW; mini-game crew-training = the MINI-GAME -> BLOODLINE feed.
- The loop gates: rank wins / turf control / crew karma / season milestones all report into window.AKStory.check() so playing ANY avenue advances the chapter (the non-linear unlock).
- Economy tuning lives in AK_ECON (one source of truth) -- a single balance table (sources + sinks per tier) so the curve is adjustable, not hardcoded per system.

## 9. LOCKED economy + monetization (operator decided 2026-06-25)
1. **Endgame squeeze = AGGRESSIVE + SELF-BALANCING ("tainting cycle"), with a SEASONAL recovery path.** Lean aggressive (hard sinks, trade-reliant chase) BUT the economy is a CLOSED LOOP that "contributes to the environment" -- nothing vanishes, it recirculates:
   - Sinks recirculate: market fees/upkeep pool into district/season reward pots; a raided player's lost resources become the raider's LOOT (player-to-player flow, not deleted); spent gold partly seeds bounty/season pools.
   - Faded standing -> PRESTIGE: when a season resets, your peak converts to a permanent prestige/legacy currency instead of evaporating.
   - RECOVERY ADVANTAGE: after a seasonal partial-reset, players get a comeback path -- a head-start scaled to their prior peak + a "reclaim" quest to win back a portion of what they lost. The reset keeps it fresh; the recovery keeps it fair. The aggressive cycle self-balances (sources reward engagement, sinks recirculate) so the world economy stays alive, not deflationary.
2. **Monetization = COSMETICS + CONVENIENCE + SEASONAL BATTLE PASS (free + premium), strictly non-power, CALIFORNIA-COMPLIANT + proactively legally protected.** Gems/Stripe sell skins, killstreak effect-skins, time-skips, extra builder/loadout slots (convenience), and a seasonal pass with a free track + premium track (rewards play, never power/loot for cash). See section 10 -- compliance is a HARD gate before any real-money launch.
3. **Personalization = FULL ARCHETYPE PATHS in V1.** Fighter (rank), Builder (turf), Trader (market), Diplomat (crew), Collector (bloodline) -- each a viable climb to the crown; the story chapter gates accept progress from any avenue; loadouts/skins personalize the dog.

## 10. CALIFORNIA / LEGAL COMPLIANCE (HARD GATE before real-money launch -- proactive protection)
Operator directive: "whatever makes it compliant in California, proactive, protect us legally." Bake these in BY DESIGN (full researched memo pending from the legal agent):
- **No pay-to-win (strongest shield):** gems = cosmetic/convenience/pass ONLY; a non-payer can reach the crown by play. This is both the doctrine and the best legal + app-store + optics protection.
- **Randomized purchases (chests/gacha): DISCLOSE ODDS** (probability disclosure -- Apple/Google require it; CA + federal scrutiny rising). Always offer a DIRECT-buy alternative. No real-money wagering mechanics. Treat loot-box-style items carefully, especially for minors.
- **Minors (the game attracts under-18): CA Age-Appropriate Design Code (AADC) + COPPA + CCPA/CPRA** -- privacy-by-default for minors, no behavioral ads to kids, data minimization, parental controls, age gating/estimation, no sale of minors' data.
- **Auto-renewal (CA ARL):** SAFER to make the battle pass a ONE-TIME seasonal purchase (NOT auto-renewing) to avoid CA Automatic Renewal Law complexity; if it ever auto-renews -> clear disclosure + affirmative consent + one-click cancel + renewal reminders.
- **No dark patterns (CPRA bans them):** clear pricing, honest timers, easy cancel, no manipulative funnels.
- **Virtual currency terms:** gems have no cash value, non-transferable, non-refundable (per ToS); clear EULA/ToS + privacy policy.
- **Refunds/consumer protection:** honor app-store refund policies; clear disclosures.
- ACTION: a legal-compliance memo is being produced; a full legal review by counsel is required before charging real money. Entity/payment posture per [[reference_everlight_entity_structure]].
