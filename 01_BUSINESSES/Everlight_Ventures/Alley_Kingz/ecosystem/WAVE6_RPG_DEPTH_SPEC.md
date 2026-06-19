# WAVE 6 SPEC -- RPG DEPTH (operator, 2026-06-12 ~2:40 AM)
"Mobile Legends / WoW / Diablo / Skyrim type depth and logic and skill set and
skill tree and storyline, Alley Kingz version."

## 1. ATTRIBUTES MUST BE DEFINED AND VISIBLE (quick win, ship first)
- Skill-point UI today says "+5%" without naming the stat or showing totals.
- Every card gets a visible ATTRIBUTE SHEET: base value -> tuned value with the
  delta ("DMG 180 -> 189 (+5%)", "SPD 0.55 -> 0.58"). Card detail shows all six
  tunable attributes with real numbers pre/post points, plus derived stats
  (range band, attack style, elevation).

## 2. BALANCE AUDIT BY TYPE + RANK (analysis pass, not vibes)
- Re-run/extend art/_balance_pass.py style auditing: cost-vs-power fairness per
  role, per rarity, per faction; strengths/weaknesses matrix (who counters who);
  flag outliers; operator gets a one-page fairness report before any rebalance.

## 3. CLASS TAXONOMY EXPANSION (the big design)
Layers, each card classified on EVERY axis:
- ELEVATION: ground / air / (future: burrow?)
- ROLE (exists, 11): the combat job.
- CLASS (new): mage-type casters, structures/buildings family with DISTINCT
  behaviors (scaling damage ramps, static turret damage, lockdown/CC that holds
  a unit, spawner nests, aura pylons), bruisers, assassins, supports...
- ATTACK TYPE: melee/bullet/cannon/beam (exists) + new CC subtypes (lock, slow,
  knock, silence).
- SKILL-SET TYPE: active ability families (exists per card) classified.
- SYNERGY TAGS (exists, 10): expand to interact with the new classes.
- RANK/rarity: fairness curve per Section 2.
Structures get a family pass: multiple structure archetypes with different
ability logic (ramping beam, fixed turret, snare trap, spawner, buff pylon).

## 4. STORYLINE (campaign narrative)
- The 10 cities ARE the campaign acts. Each city gets: an act title, a 2-3
  sentence act intro (shown entering the city on the world map), a city boss
  flavor beat at level 10, and a 1-line level blurb cadence where cheap.
- Tone: the established gritty TV-MA street-dog canon (cards_lore.js voice).
  The arc: a stray rises from The Lot to take the Crown Citadel. $BCARDD canon
  woven in as the alley king mythology, dealer kept tease-only.

## 5. DRAGON AGE: INQUISITION LAYER (operator add, 2026-06-12)
- SIDEQUESTS: optional objectives layered on the world map, DA:I style. Per
  city: 2-4 side missions off the main level ladder (e.g. "win a level using
  only Zoomie Syndicate", "3-crown any level in under 90s", "clear a level
  without losing a tower") paying unique rewards (scrap caches, keys, a
  cosmetic, an sp). Daily/weekly rotating bounties on top for retention.
- SPECIALIZATIONS: DA:I-style branch commitment -- at a milestone (e.g. player
  level 10) choose a specialization path (one of 3 per branch archetype) that
  unlocks exclusive high-tier skill nodes; respec allows changing it at a
  premium. Makes builds identity-defining, per the skill-tree research law
  (impactful, committing choices).
- QUEST JOURNAL: a simple journal surface listing active side missions, bounty
  timers, and story-act progress so players always have a "what next".

## 6. SHADOW OF MORDOR LAYER (operator add, 2026-06-12): THE NEMESIS SYSTEM
- Street-gang nemesis mechanics, AK version: named RIVAL DOGS in the enemy
  ranks persist across world-map runs. Lose a level and the AI unit that landed
  the killing blow on your king gets PROMOTED: it earns a generated street name
  + title ("Scarjaw, Warden of the Docks"), a power bump, and a taunt line
  (cards_lore voice) shown when you re-enter that level.
- Your nemesis REMEMBERS: rematch intro calls back the last fight ("Back for
  another beating, stray?"). Beat your nemesis -> bonus chest tier + the rival
  is demoted or replaced; it survives -> it climbs the city hierarchy.
- Per-city rival roster (small: 3-5 named rivals max, persisted in ak_world),
  procedural names from breed + district + deed. Cheap to build on existing AI
  decks: a nemesis = a buffed featured unit in the AI deck with its name shown.
- This is the retention hook: players chase personal grudges, not just levels.

## 7. THE GOVERNING PRINCIPLE: RADICAL PERSONALIZATION (operator, 2026-06-12)
"The cards and the dictionary are the same, but individualize how players
personalize their cards, their decks, their attributes." The game must tailor
itself to each player the way a fully user-shaped system does -- same parts,
infinitely personal builds -- with a 90s-kid MySpace/Mafia-Wars identity vibe.
NO two players' $BCARDD should ever feel the same.

Design mandates for every wave-6 system:
- PER-CARD IDENTITY: card NICKNAMES (rename your Bacardi), per-card attribute
  builds (live), per-card battle record (fights won, towers cracked, kill
  count -- displayed on the card like a rap sheet), earned per-card badges
  ("100 kills: Certified", "won a city boss: Crowned").
- DECK IDENTITY: named decks (exists, deepen), deck archetype detection that
  TELLS the player their style ("you run a Rush deck, 71% aggression"),
  playstyle stats on the profile.
- PROFILE AS A MYSPACE PAGE: customizable profile surface -- theme/accent
  color, a TOP-8 style favorite-cards showcase, status line, crew motto,
  banner from owned art. Public-facing later (social layer), personal now.
- COSMETIC DIFFERENTIATION: shape outline tints, token frames, deploy-line
  colors as unlockable/earnable cosmetics so even the battlefield look is
  yours.
- SYSTEMS REINFORCE IT: nemesis grudges (yours alone), specializations
  (commitment = identity), sidequest choices, skill builds -- every layer
  should make a player's account UNMISTAKABLY theirs.
- ANTI-GENERIC TEST for every feature: "would two veteran accounts look and
  play meaningfully different?" If no, redesign.

## SEQUENCE
1. Quick win (#1) ships with the post-wave-5 micro-pass (with spoken taglines).
2. Design workflow: taxonomy architect + balance auditor + storyline writer
   produce specs/reports (no code).
3. Operator reviews the taxonomy + fairness report (5-min read), then the
   implementation wave builds it.
