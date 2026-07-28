# Alley Kingz -- CORE LOOP CANON (operator's authoritative ruleset, from playtest 2026-06-25)
*This is the SOURCE OF TRUTH for how the game works. Every system must obey it; the TUTORIAL teaches it. Captured verbatim-intent from the operator's own play session. Queued for build AFTER the current roadmap waves -- but the TRANSITIONS fix + TUTORIAL are near-term (player is actively confused).*

## THE LOOP (canonical)
1. **TOWN HALL = the master.** It controls the BUILDINGS, the BUILDERS, and the DECK CARD-LEVEL MAX. Upgrading Town Hall raises all three. Your deck can only be as strong as your Town Hall allows.
2. **The CITY is run by the 11-CARD DECK.** You ASSIGN your 11 cards to buildings according to their TRAITS + FACTIONS. (Building-card assignment by trait/faction -- ALREADY BUILT, this confirms it as canon.)
3. **RAID STAKES (the missing spine):** if your district/buildings get RAIDED by another clan, your Town Hall / buildings take damage -> your deck is NO LONGER max level (card-max drops with the Town Hall). Raids have a REAL, painful consequence -- this is what makes defense matter.
4. **TWO DISTINCT COMBAT MODES (do not conflate):**
   - **TOWER LANE BATTLE** = the Clash-lane-style arena (the FROZEN engine.js). Lane combat.
   - **WORLD-MAP RAID = RPG-STYLE, NOT lane.** When you are attacked on the WORLD MAP (not the tower), your default 11-card deck defends RPG-style. Different system from the lane battle.
5. **DEATH -> INFIRMARY:** any card killed (in a raid / RPG combat) must be HEALED in the INFIRMARY building before it can be used again. Cards are not disposable.
6. **ECONOMY + FORTIFICATION:**
   - **CROPS** -> tradeable for in-game currency + used in MISSIONS.
   - **TREES (wood) + STONE** -> used to FORTIFY districts against raids (the defensive sink).
7. **CARD ACQUISITION (exactly 3 paths):**
   - **WILD ENCOUNTERS** -> win the mini-battle -> get a COPY of that card. (BUILT.)
   - **TOWN HALL upgrade** -> unlocks more card slots/cards.
   - **SHOP** -> buy cards. (BUILT.)

## BUILT vs GAP (against this canon)
- Town Hall controls builders + buildings: BUILT (builder-cap). Card-level-MAX gated by Town Hall: PARTIAL (townHallPerks maxToolTier exists; the DECK card-level cap tied to TH needs explicit build + the raid-de-level link). GAP.
- 11-deck assigned to buildings by trait/faction: BUILT (greeter/assignment).
- RAID -> Town Hall down -> deck de-levels: GAP (NEW -- the stakes spine).
- World-map raid = RPG-style 11-deck defense (not lane): PARTIAL (modes.js raid has kill-scaling but must be the canonical RPG 11-deck defense, clearly separate from the lane). ALIGN/BUILD.
- Death -> INFIRMARY heal: GAP (NEW -- infirmary building + heal-over-time / pay-to-heal, soft currency).
- Crops -> currency + missions: PARTIAL (farming held; wire crops to the Fence + mission rewards).
- Trees/stone -> FORTIFY districts: GAP (NEW -- fortification consumes wood/stone, raises raid defense).
- Card unlock via encounter / Town Hall / shop: encounter BUILT, shop BUILT, Town-Hall-unlock PARTIAL (confirm TH gates card unlocks).

## NEAR-TERM player-pain fixes (do NOT wait for the full queue)
- **TRANSITIONS interrupt play.** The operator: "I dont understand the transitions, they interrupt the game Im already playing." LIKELY the cinematic chapter cards (shipped 2026-06-25, pause ~3.5s) and/or zone-dive transitions. FIX: make chapter cards smaller/faster/rarer (only true chapter breaks, never mid-stride), instant tap-through, and never block input the player already initiated. Audit ALL transitions (zone dive, interior open, battle launch) for "interrupts flow" feel. HIGH priority -- it is actively hurting the session.
- **TUTORIAL.** "I have no idea what Im doing." Build a guided onboarding that teaches THIS loop in order: move (hjkl/tap) -> Town Hall -> assign your 11 deck to buildings by trait/faction -> harvest/crops -> fortify -> wild encounter (get a card) -> a raid (defend RPG-style) -> heal in infirmary -> climb rank/story. First-run, skippable, gritty-voiced (the Old Pack / the Fixer teaches you the streets). This is the #1 retention fix per the auteur/research work.

## GRAPHICS
Operator: "I cant stand how it looks yet." Ongoing overhaul -- the de-emojify passes + custom art + interior videos + sensory layer all feed this. Treat visual polish as a standing track, not a one-off.

## SEQUENCE
Per operator: address this AFTER the current roadmap work. EXCEPTION: the TRANSITIONS softening is near-term (it is a regression-feel from this session's chapter cards). Build order when we get here: (1) the RAID->DE-LEVEL stakes spine (makes everything matter), (2) INFIRMARY, (3) FORTIFY (trees/stone), (4) world-map RPG-raid alignment, (5) crops->currency/missions wiring, (6) Town-Hall card-max + unlock confirm, (7) the TUTORIAL teaching all of it. Then graphics polish continuous.
