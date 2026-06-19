# WAVE 7 BUILD CONTRACT -- ONE SYNERGISTIC DYNAMIC
**Synthesis editor, 2026-06-12.** This is the single build-ready implementation
contract for wave 7. It merges: TAXONOMY_DESIGN.md, BALANCE_AUDIT_REPORT.md,
STORYLINE_CANON.md, LOOT_SYSTEM_DESIGN.md, TRANSITION_SHOWPIECE_SPEC.md,
WAVE6_RPG_DEPTH_SPEC.md (sections 2-7; section 1 attribute sheets ship in the
micro-pass and are an assumed-present surface here), LOOT_SYSTEM_MANDATE.md,
and ALL 15 items of WAVE7_ADDENDUM_OPERATOR_NIGHT_NOTES.md.

Governing principle (spec section 7): RADICAL PERSONALIZATION. Every lane was
gated on "would two veteran accounts look and play meaningfully different?"
Standing order 15: everything BLENDS -- the loot magnet feeds the ledger, the
ledger is the showpiece beat, kills feed the rap sheet, the rap sheet feeds
badges, losses feed the nemesis, the nemesis feeds a synergy combo and the
opponent ladder, the class table feeds quests and the codex. One dynamic.

NO em-dash characters anywhere in code, strings, or docs. Use -- in source and
plain punctuation in UI strings.

---

## 0. BUILD ORDER (dependency-locked)

| # | Lane | Blocks | Blocked by |
|---|------|--------|------------|
| L0 | BUGS (addendum 1-3) | everything (trust floor) | nothing -- FIRST |
| L1 | COMBAT RULES + VARIANT TUNING (addendum 4, 5, 9 + audit corrections) | L2 counter web re-check | L0; tuning numbers gated on operator sign-off (see OPERATOR_ONE_PAGER) |
| L2 | TAXONOMY / CLASSES + STRUCTURES + g.stats (addendum 6) | L4, L5, L6, L7, L8 | L0, L1 |
| L3 | TRANSITIONS SHOWPIECE (addendum 8, 10) | L4 (ledger line), L8 (step-4 slot) | L0 |
| L4 | LOOT DROPS PHASE 1 (addendum 14) | -- | L2 (kill attribution), L3 (ledger panel) |
| L5 | SIDEQUESTS + JOURNAL | L7 (cosmetic token grants) | L2 (counters + class table) |
| L6 | NEMESIS (addendum 13) | L8 (taunt display slots) | L2 (lastHitBy plumbing) |
| L7 | PERSONALIZATION + PROFILE (addendum 7) | -- | L2 (g.stats), L5 (token grants; can ship rendering first) |
| L8 | STORYLINE INTEGRATION (addendum 11, 12) | -- | L2 (codex data), L3 (ride slot), L6 (taunts) |

L3 can run in parallel with L1/L2 (no shared seams). L5/L6 can run in
parallel with each other after L2. Nothing in L4-L8 starts before L0 is green.

---

## L0. BUGS LANE -- FIX FIRST (addendum items 1-3)
Marker: **AK-FIX7**. These are trust bugs: visible broken numbers and broken
input poison every feature downstream. No feature work until all three pass.

1. **UPGRADE STATS MUST MECHANICALLY APPLY.** Verify the full chain:
   DBPROFILE.cardLvls (index.html ~3767/~4259) -> perks.cardLevels export
   (~4483-4490) -> snapshotPerks clamp (engine.js ~704-722) -> akLevelMult
   (~658) applied at deployUnit (~1345-1348) -> computeBulk AFTER the mult
   (~1377). The plumbing EXISTS -- the bug is display and/or a break in the
   chain. Fix: (a) prove with a harness probe that a Lv5 card deploys with
   akLevelMult(5) stats; (b) card detail + attribute sheet (AK-SHEET,
   index.html ~4045-4056) must re-render on levelUpCard and on skill-point
   spend, showing base -> current with the level AND tune deltas. If any link
   is dead, that is the critical fix of the wave.
2. **ENEMY KING TOWER HP VISIBLE.** Princess towers show HP; the enemy king
   does not. Render an HP bar/strip for BOTH kings in ALL four districts
   (the near-edge king strip comment at index.html ~1649 is the prior art;
   the staircase king bulk at engine.js ~836 must read correctly on the bar).
3. **DRAG-RETURN CANCEL.** Dragging a card from the tray and releasing it
   back over the tray cancels the deploy: no field drop, no energy spend,
   card returns to hand. Seam: the pointerup/touchend disambiguation block
   (index.html ~3014-3157) -- add a tray-bounds check before deploy commit.

File scope: index.html (tray input, card detail, HUD bars), engine.js
(verification probe only -- no stat logic changes), tests/ (new probe:
level_apply_probe.js). Acceptance: harness green; a Lv5 vs Lv1 deploy of the
same card differs by exactly akLevelMult; king bars visible in a headless DOM
snapshot; drag-return leaves energy unchanged.

---

## L1. COMBAT RULES LANE (addendum items 4, 5, 9 + balance corrections)
Markers: **AK-RESPAWN** (refined), **AK-FEEL B1** (range), **AK-HAPTIC** (new).

### 1A. Phase carry -- TOWERS ONLY (addendum 4)
ONLY towers persist across district transitions. Surviving towers carry their
current HP and state into the new phase (no heal, no restat -- see conflict
C3). ALL units leave on BOTH sides at section 1->2 and 2->3 (today only the
player side wipes: resetPlayerBoard ~859 vs repositionEnemyUnitsToBack ~862).
EXCEPTION: entering the finale (section 4) keeps the existing both-side
survivor respawn (AK-RESPAWN keepSurvivors seam, engine.js ~893-963).
Seam: the transition block engine.js ~852-991.

### 1B. Princess tower range supremacy (addendum 5, Clash model)
Towers must out-range nearly every card. TOWER_STATS (engine.js ~292):
princess range 6, king 6.5 -- UNCHANGED. The card side moves:
- rangeBand (engine.js ~317): Structure band 6.5 -> **5.75**; Blaster stays
  5.5; OVERRIDE map trims to exactly TWO sanctioned outrangers:
  **Laser Beagle 6.5** (beam siege) and **Rail Terrier 6.25** (rail sniper).
  Byte Beagle 6.0 -> 5.5; Rosco stays 5.0.
- Audit hook: a one-shot console table (band per card) confirms no third card
  reaches >= 6.0. Re-check the SIEGE row of the counter web
  (BALANCE_AUDIT_REPORT section F assumed 5.5-6.5) after the change.

### 1C. Variant tuning pass (BALANCE_AUDIT_REPORT corrections -- operator-gated)
Apply in data/, regenerate canon.js via data/_build_canon.py. Numbers ship
ONLY after operator sign-off (the one question in OPERATOR_ONE_PAGER):
- Street: no -1 cost when parent cost <= 4; dmg mult 1.25 -> 1.15 on Common
  landings (hits Nitro, Spike, Switchblade, Carrier, Hotwire, Knuckles,
  Flatline per the audit top-5).
- Heavy: enforce the 2850 HP clamp on variants (Tombstone 3648 -> 2850,
  Anvil/Slab 3392 -> 2850). Structures only: Heavy dmg mult 0.85 -> 0.95.
- Re-examine AIR domain on the 5 Street melee flyers (Nitro, Spike, Hotwire,
  Roadblock, Crashcage) -- over-budget + unanswerable is the toxic combo; the
  budget fix above is the primary remedy, air stays pending playtest.
- Fix data/_balance_pass.py: drop the 48-card assert, make it 106-aware by
  applying variant multipliers on top of the formula; re-run as the proof.
- Update data/BALANCE_NOTES.md ("no strictly better card" claim) after.
- Spells: NO stat changes. Reword Jolt/Strike codex text to match reality
  (chip + stun / token-killer); the execute-threshold idea is wave 8.

### 1D. Haptics (addendum 9)
navigator.vibrate patterns per hit, varying by attack style (melee thud /
cannon boom / beam buzz / tower crack), small and tasteful. Settings toggle
`ak_haptics` (default on). Fully guarded (no-op when API absent, headless
safe). Seams: the hit/knockback sites that already gate sfxThump (engine.js
~1786) and sfxCard -- ride the existing AK-AUDIO call sites, never new timing.

File scope: engine.js (transition block, rangeBand, OVERRIDE map, haptic
calls), data/_build_canon.py, data/_balance_pass.py, data/cards.json,
canon.js (regenerated only), data/BALANCE_NOTES.md, index.html (settings
toggle row). Acceptance: harness green incl. 45/90/135 + TRANSITION_DUR;
phase-carry probe shows zero units cross 1->2 while damaged towers carry HP;
band audit prints exactly 2 cards >= 6.0; tuned canon passes the rebuilt
_balance_pass.py.

---

## L2. TAXONOMY / CLASSES + STRUCTURES LANE (TAXONOMY_DESIGN 1-3 + addendum 6)
Markers: **AK-CLASS** (class layer), **AK-STATS** (match counters).
This lane is the shared foundation -- it ships the data and counters that
L4/L5/L6/L7/L8 all consume. Build ONCE here, never re-derive downstream.

1. **combatClass field, all 106 cards** (TAXONOMY_DESIGN 1.2): added to
   cards.json by data/_build_canon.py per the ability-family table; interim
   CLASS_BY_FAMILY constant in engine.js mapCanonToEngine (~340) until the
   merge runs. Census contract: BRUISER 30 / ASSASSIN 21 / CASTER 22 /
   MARKSMAN 10 / SUPPORT 14 / SUMMONER 6 / STRUCTURE family 12 (9 native +
   reclassed 0045/0046/0048).
2. **Five structure archetypes** (TAXONOMY_DESIGN 1.3): RAMPING DAMAGE
   (per-target ramp reset on retarget), STATIC TURRET (timed burst window in
   maybeFireAbility ~2088, off the ramp code path), LOCKDOWN (snare beam holds
   one unit + keeps the 35% slow field), SPAWNER NEST (0045/0048 reclassed
   static via STATIC_OVERRIDE, repeating spawn, 4-token cap), AURA PYLON
   (0046 reclassed static, +15% atkSpd to allied structures in 3.5 tiles via
   the ns* per-tick layer, computeSynergy ~1522/1555). Reclass trio gets +10%
   hp in _build_canon.py, CLAMPED at 2850 (conflict C1).
3. **CC subtypes** (TAXONOMY_DESIGN 2): CC_SUBTYPE map next to ABILITY_KIND
   (engine.js ~300) -- LOCK / SLOW / KNOCK / SILENCE riding existing timers
   (stunTimer/snareTimer/frozenTimer, slowTimer+slowMag, kbVx/kbVy, silenceT).
   BLIND/REVEAL classified as DENIAL, excluded from CC-counting payoffs.
   Card detail gains the one-line "CONTROL:" row.
4. **10 new named synergy combos + GRUDGE MATCH** (TAXONOMY_DESIGN 3): append
   to NAMED_SYNERGY (~255), apply in computeSynergy (~1545-1578). New layers:
   nsCd mult, lock_and_key conditional in doAttack, wrecking_crew conditional
   at the tower-hit path. All under MOVE_CAP/DMG_CAP, symmetric for the AI.
   full_battery supersedes turret_net (take max, never stack). GRUDGE MATCH
   activates only when the L6 nemesis is fielded (+5% nsDmg).
5. **g.stats counters** (TAXONOMY_DESIGN 4.0 -- the shared spine):
   killsByCard, deploysByCard, spellsCast, towersLost, kingDamageTaken,
   ccApplied{lock,slow,knock,silence}, ccTaken mirror, hazard damage tally
   (~1204), and **Tower.takeDamage(d, attacker)** -> t.lastHitBy (engine.js
   ~518-527, call sites ~2067/2075 + projectile impact). Kill attribution
   (which side/unit landed the killing blow) lives here -- L4 loot and L6
   nemesis both read it.
6. **Per-card BASE attributes** (addendum 6): dexterity/speed, special
   attack, special defense assigned PER CARD in cards.json by the taxonomy
   table (derive defaults from role + speedTier + ability kind; CASTER kits
   get spatk-weighted, BRUISER spdef-weighted, ASSASSIN dex-weighted).
   Engine consumes them as base values under the EXISTING AK-ATTRS clamp
   contract (tune mults stack on top, clamps unchanged: agi/aspd <= 1.25,
   def/spdef >= 0.80). The attribute sheet (micro-pass) displays base ->
   tuned for all of them. Balance gate: base-attr spreads must keep every
   card within the audited power proxy +/- 5% (re-run _balance_pass.py).

File scope: data/cards.json, data/_build_canon.py, canon.js (regenerated),
engine.js (mapCanonToEngine, ABILITY_KIND area, NAMED_SYNERGY, computeSynergy,
maybeFireAbility, doAttack, Tower.takeDamage, unit death block), index.html
(Deck Lab card detail rows ~3754). Acceptance: census numbers exact; harness
green; a Pylon deck measurably buffs structures and never exceeds DMG_CAP;
g.stats populated in a full headless match; lastHitBy set on king kills.

---

## L3. TRANSITIONS SHOWPIECE LANE (TRANSITION_SHOWPIECE_SPEC + addendum 8, 10)
Marker: **AK-SHOW**. The signature moment: suspense in, celebration out.

1. **The five-step choreography** exactly per TRANSITION_SHOWPIECE_SPEC.md:
   WARNING (T-10 clock flash, T-3 countdown; timer-path only) -> BREAK
   (hit-stop frame + white flash + bass sting; LOW_FX = flash + sting only)
   -> LEDGER ("DISTRICT CLEARED" panel, live coin tick, stars slam, NEW
   district-clear bonus per tower standing + time remaining, surviving-card
   tagline via AK-SPEAK, 3-crown crown stamp + "CLEARED EARLY +X") -> RIDE
   (existing convoy path + destination name + act flavor line slot + nemesis
   taunt slot -- slots ship EMPTY here, L8/L6 fill them) -> DROP ("ENTERING
   <DISTRICT>" banner, edge flare, visible energy refill).
   Earned = gold/major timbre; timer = red/minor. Added wall time <= ~3s
   (ledger overlaps the ride). NOT skippable. TRANSITION_DUR = 5.0 and the
   45/90/135 harness contract stay green (the showpiece dresses the existing
   window, never stretches the sim).
2. **The ledger panel exposes a line API** (`ledgerAddLine(label, value)`)
   so L4 can stamp `SALVAGE BANKED +Xc +N shards` without touching this lane
   again. This is the blend joint between showpiece and loot.
3. **Live XP bar at match end** (addendum 8): result screen XP bar fills in
   real time with numbers (current/needed from the existing per-level curve),
   level-up moment celebrated with the same gold timbre family. Surface the
   curve, never change it.
4. **Border everywhere** (addendum 10): the arena's glowing edge frame
   renders on EVERY screen (lobby, collection/garage, chop shop, world map,
   profile) as a static/breathing gold guide frame. Beat-reactivity stays
   arena-only (AK-VIBES contract). One CSS component, themed by the L7
   accent token when it lands (blend joint with personalization).

File scope: engine.js (transition timing hooks only -- read, not retimed),
index.html (overlay DOM, ledger panel, result screen, global frame CSS),
AK-AUDIO sting assets via existing sfx layer. Acceptance: harness green incl.
TRANSITION_DUR; LOW_FX path verified; total transition wall time measured
<= today + 3s; XP bar numbers match the stored curve exactly.

---

## L4. LOOT DROPS PHASE 1 LANE -- "THE SHAKEDOWN" (LOOT_SYSTEM_DESIGN phase 1)
Marker: **AK-LOOT**. DMZ-style kill loot is the operator's KEY feature
(addendum 14: phase 1 ships in wave 7). Scope is EXACTLY phase 1.

1. **Kill drops**: player-attributed kills only (reads L2 kill attribution).
   P(drop) = clamp(0.20 + 0.04 * cost, 0.20, 0.60); Legendary/Mythic kills
   always drop. Phase-1 table: Coin Spark 68% (1-3 sparks by cost, 2c each) /
   Scrap Shard 25% (victim's rarity; L=2, M=5) / the Key Fragment + Card Tag
   slots REROLL as spark/shard until phase 2 (weights preserved so phase 2
   is a flag flip, not a retune).
2. **Deterministic structure drops**: princess tower down = 3 sparks + 1
   Common shard + 10% fragment-slot reroll; district gate clear = LOOT PINATA
   (5 sparks + 2 shards, district rarity floor). King down adds nothing
   (the win pay lives in grantMatchRewards -- no double-dip).
3. **Auto-magnet collection, 100%, no tap-to-collect ever** (one-thumb law):
   2.0-tile magnet around friendly units, 1.5 around towers, pull 8 tiles/s
   ease-in, tier-pitched scoop SFX, 12s token lifetime then ghost; Sweep at
   transition banks ghosts at 50% (Epic+ shards always 100%). LOW_FX: pop +
   scoop only.
4. **Banking**: STASH chip HUD (unbanked, pulsing) -> gate clear stamps
   `SALVAGE BANKED` on the L3 ledger -> loss keeps 50% of unbanked commons,
   100% of Epic+ (rage-quit guard) -> win/timer banks all. Nothing outside
   the match is ever at risk.
5. **Anti-farm budgets live from day one**: 40 spark-coins / 10 shards
   (Epic 3, Legendary 2, Mythic 1) per match, Dust Puffs after cap; replay
   caps multiply by the existing worldChestContext.decayMult (floor 0.15);
   Quick Play budgets 75%; hazard/AI-vs-AI kills drop nothing; coinMult
   applies ONCE at bank time behind the AK-SCRAP-style clamps.
6. **Tokens are miniaturized REAL art, never dots** (operator law): Coin
   Spark reuses game/assets/ui/bcard_emblem.png; enqueue `loot_scrap_shard`
   per the LOOT_SYSTEM_DESIGN art_factory commands. NOTE Leonardo API is
   dead (2026-06-10) -- queue anyway (idempotent), ship phase 1 behind a
   feature flag until the shard master is painted; never show a generic dot.
7. **Tables in economy.js** (`AK_ECON.LOOT_TABLE`, CHEST_TABLE pattern) so
   index/shop can never disagree. Banked loot folds into grantMatchRewards
   as one new `loot:{coins,scrap}` field -- one grant per match preserved.

File scope: engine.js (death block ~633, token entities + magnet in the unit
update loop, transition sweep), economy.js (LOOT_TABLE), index.html (stash
HUD, ledger line via L3 API, grantMatchRewards fold), art/ queue entries.
Acceptance: per LOOT_SYSTEM_DESIGN phase 1 -- harness green, full clear banks
~25-45 loot-coins, loss keeps exactly 50% of unbanked commons, caps hold,
LOW_FX minimal, protected constants byte-identical.

---

## L5. SIDEQUESTS + JOURNAL LANE (TAXONOMY_DESIGN 4)
Marker: **AK-QUEST**.

1. **State**: `w.quests = {done, daily, counters}` in ak_world (cloud-mirrored
   ak_* key, loadWorld backfill like checkpoint).
2. **All 30 city sidequests** exactly as cataloged in TAXONOMY_DESIGN 4.1
   (3 per city, The Lot through Crown Citadel), evaluated in ONE place:
   grantMatchRewards (index.html ~4394) reading g.stats + deck checks.
   Rewards pay through existing verbs only: coins, scrap, keys, chests, sp,
   plus COSMETIC TOKENS granted into p.identity.cosmetics (L7 renders them).
3. **6 rotating daily bounty templates** (4.2): date-seeded PRNG, 2 active
   per day, rewards below sidequest rates. Loot-flavored bounty templates
   are wave 8 (after loot phase 2 gives them targets).
4. **Quest Journal** (WAVE6 section 5): panel on the world-map screen
   (wmScreen DOM ~4730) listing act progress (w.prog), the open city's
   sidequests with act-flavor lines in STORYLINE_CANON voice, daily timers.
   This is the player's "what next" surface.
5. Quest display copy uses the act titles/voice from STORYLINE_CANON.md
   (blend joint with L8).

File scope: index.html only (ak_world shape, grantMatchRewards checks,
journal panel, dateSeed helper). Engine counters were built in L2 -- this
lane adds ZERO engine code. Acceptance: a scripted headless run completes
STRAY'S OATH and NO HELP COMING; daily roll deterministic per date; rewards
land once (idempotent done-flags); cloud mirror round-trips w.quests.

---

## L6. NEMESIS LANE (TAXONOMY_DESIGN 5 + addendum 13)
Marker: **AK-NEMESIS**. The Shadow of Mordor layer: grudges nobody else has.

1. **State**: w.nemesis per TAXONOMY_DESIGN 5.1 -- max 4 named rivals per
   city, each {card, name, title, deed, tier 1-3, wins/losses, lastLevel,
   tauntSeed}. Single write point: recordWorldResult (index.html ~4126).
2. **Name generator**: breed-group x district x deed tables verbatim from
   5.2 (Scarjaw / Hairpin / Wiretap / Halfpint pools; Warden/Kingtaker/
   Butcher titles; DISTRICT_NOUN per city).
3. **Promotion/demotion** per 5.3: king-killer identified via t.lastHitBy
   (built in L2); top-damage fallback; tier up on your losses, tier down on
   your wins, removal at tier 0 pays the bounty (chest tier +1 inside
   grantMatchRewards, AK-CHESTRULE seam ~4419, + 20 scrap of the rival's
   rarity + "Grudges Settled" credit).
4. **Fielding**: startMatch opts.nemesis; rival card inserted at the world
   garrison deck seam (engine.js ~947), hp/dmg x 1.12/1.22/1.35 by tier on
   the AK-AICURVE mult seam (~1329) BEFORE computeBulk; u.nemesisName renders
   as the name tag; 60% appearance, haunts lastLevel +/- 2.
5. **Taunt lines** from the 5.4 template tables (tauntSeed-stable voice):
   rematch intro fills the L3 RIDE slot; promotion lines on the loss screen;
   demotion lines on the win screen.
6. **Opponent names ladder** (addendum 13): every phase shows a generated
   opponent name climbing a chain of command across the level/city, drawn
   from the SAME name tables (no second generator), capping at the named
   STORYLINE_CANON city boss at level 10. Nemesis rivals, when fielded,
   replace the generated name for their phase -- one namespace, fully blended.
7. **GRUDGE MATCH synergy** (L2 table) lights up when the rival is on the
   enemy field: all your units +5% nsDmg. Two accounts can never share it.

File scope: index.html (w.nemesis, recordWorldResult, loss/win screens,
opponent name strip), engine.js (startMatch opts, garrison seam, deploy mult,
name tag render). Acceptance: scripted loss promotes the king-killer; win
demotes and pays the bumped chest exactly once; rival stat mult verified at
deploy; ladder names render every phase; harness green.

---

## L7. PERSONALIZATION + PROFILE LANE (TAXONOMY_DESIGN 6 + addendum 7)
Marker: **AK-IDENT**. The MySpace layer -- the governing principle made flesh.

1. **State**: p.cardMeta (nick, rec, badges, cosmetic flags) + p.identity
   (accent, banner, frame, deployLine, motto, status, top8, cosmetics) via
   the loadProfile backfill pattern (index.html ~3727; never rewrites).
2. **Card nicknames** (6.1): rename owned cards (max 14 chars, filtered);
   nickname renders FIRST on every player-facing surface (deck lab, hand,
   unit name tag, kill feed), canon name subtitles. Engine stays
   nickname-blind (display only).
3. **Rap sheet** (6.2): grantMatchRewards merges g.stats into
   p.cardMeta[n].rec {k,d,tw,w,ab}; police-blotter block on card detail;
   profile aggregates (total kills, favorite weapon, Grudges Settled).
4. **Badges** (6.3): the 10-badge table verbatim (certified, crowned,
   wrecker, ride_or_die, trigger_finger, untouchable, grudge_keeper,
   block_historian, first_of_name, alley_king), checked after the rec merge,
   append-only, stamped on the card art frame.
5. **Theme tokens** (6.4): accent (one CSS var at boot -- also tints the L3
   global border), banner (reuses owned map/card art, zero new art), frame,
   deployLine (arena deploy-zone tint, same draw call recolored). EARNED
   only (L5 quests, badges, vaults, nemesis bounties); shop sells none of
   the quest tokens. Motto + status free-text (filtered). Top-8 showcase
   with nicknames + badges + headline stats ("Rep your eight").
6. **Deck archetype detection** (6.5): rush/siege/control/swarm/wall/
   cutthroat scores at deck save from class + cost + speedTier; argmax with
   0.15 lead else HYBRID; stored p.decks[i].arch; deck header speaks it
   ("You run a RUSH deck. 71% aggression.").
7. **Upgrade preview** (addendum 7): before confirming ANY level-up or
   skill-point spend, show current -> next side by side (uses the same
   AK-SHEET math L0 bug 1 fixed -- numbers must be the LIVE chain, never a
   re-derivation). Per-rarity/per-card pace curves surfaced on the panel.

File scope: index.html only (profile shapes, deck lab UI, card detail,
profile screen, deploy-zone tint table, boot CSS var). Acceptance: rename
round-trips the cloud mirror; badges fire once; two seeded test profiles
produce visibly different deck-lab/profile/arena snapshots (the anti-generic
test, automated); upgrade preview matches post-upgrade reality exactly.

---

## L8. STORYLINE INTEGRATION LANE (STORYLINE_CANON + addendum 11, 12)
Markers: **AK-STORY**, **AK-CODEX**, **AK-TUT**.

1. **Act surfaces**: 10 act intros shown on world-map city entry; clearing
   lines on city completion; the 4 in-match district hook lines fill the L3
   RIDE destination slot (STORYLINE_CANON 11, engine SECTIONS order). City
   boss flavor (name/title/intro) dresses every level-10 fight; nemesis
   promotions layer UNDER the boss, never replace it. Citadel victory screen
   reads back THEIR run: named cards, buried nemeses, archetype readout
   (personalization law, STORYLINE_CANON act X).
2. **Dealer law is HARD**: $BCARDD-the-dealer is teased only (crown mark,
   white paw, face-down card, gold door). Never shown, named, or confirmed
   on any surface this lane builds. Casino Strip assets respect it.
3. **THE CODEX** (addendum 11): browsable encyclopedia page -- every card
   (stats, class, elevation, CC subtype, combos, lore, storyline ties), each
   faction, divisions, elevation rules, synergy reference. ONE source of
   truth: renders from canon.js + cards_lore.js + the L2 class/CC tables +
   STORYLINE_CANON strings; zero hand-copied stats. Spell texts use the L1C
   reworded reality (Jolt/Strike). New file game/codex.js + an index.html
   surface, loaded lazily.
4. **New-player tutorial** (addendum 12): first launch on a fresh account =
   guided real-time teach (drag-and-drop, the objective, card types, energy,
   towers), framed as the Act I prologue in The Lot voice ("Born in the
   Dirt"). Skippable; never again (`ak_tut_done`). Drag teaching must match
   the L0 bug-3 corrected input rules (including drag-return cancel).
5. Boss portrait art: enqueue via art factory only (ART_AUTOROUTE law); text
   surfaces ship first, portraits land when the art lane revives.

File scope: index.html (world map entry/clear hooks, L10 boss dressing,
victory screen, tutorial overlay), game/codex.js (new), cards_lore.js
(read-only), assets via art queue. Acceptance: every act string renders from
canon files (grep proves no duplicated stat literals); fresh-profile boot
enters the tutorial, ak_tut_done suppresses it; no em-dash characters in any
shipped string; dealer never named.

---

## CONFLICTS RESOLVED (noted per mandate)

- **C1. Reclass +10% HP vs the 2850 clamp.** TAXONOMY 1.3 grants the static
  reclass trio (0045/0046/0048) +10% hp; the AUDIT demands one clamp law
  everywhere. Resolution: +10% applies, clamped at 2850 (all three are small
  cards -- no practical clash), and the rebuilt _balance_pass.py asserts it.
- **C2. Tower range supremacy vs existing bands.** Addendum 5 vs rangeBand
  Structure 6.5 / three name overrides >= 6.0 vs the audit's counter web
  (siege kites at 5.5-6.5). Resolution: towers unchanged; exactly two
  sanctioned outrangers (Laser Beagle 6.5, Rail Terrier 6.25); Byte Beagle
  and the structure band pulled under 6. The audit's SIEGE matrix row is
  re-verified after the change (L1B acceptance).
- **C3. Towers-only phase carry vs the king staircase bulk.** engine.js ~836
  re-stats king maxHp per section ("staircase"); the operator rule says
  surviving towers "stay as they are". Resolution: operator rule wins for
  CARRIED towers -- a surviving tower keeps its current hp/maxHp untouched;
  the staircase applies only where a tower is (re)created fresh. The visible
  king HP bar (L0 bug 2) must read the carried values.
- **C4. Audit corrections vs "analysis only".** The audit applied nothing;
  WAVE6 sequence says the operator reviews the fairness report before the
  build. Resolution: tuning is IN wave 7 (L1C) but gated on the single
  operator sign-off in OPERATOR_ONE_PAGER. Everything else in L1 proceeds.
- **C5. Spell damage flag.** Audit offers reword vs execute-threshold.
  Resolution: reword now (free, honest), execute-threshold deferred to the
  wave-8 balance pass with playtest data.
- **C6. Two daily systems.** TAXONOMY dailies vs LOOT daily bounties.
  Resolution: ONE daily system owned by L5; loot-flavored templates join in
  wave 8 when loot phase 2 gives them targets.
- **C7. Rival roster size.** Spec said 3-5, taxonomy locked 4. Resolution: 4.
- **C8. Mythic premium.** Audit shows Mythics mid-pack on stats with utility
  as the real premium, currently violated by Tombstone/Knuckles. Resolution:
  rarity stays stat-inverted BY DESIGN; the premium contract is protected by
  the L1C clamps and Street nerf, not by buffing Mythics.
- **C9. Loot art vs dead Leonardo API.** Operator law: never generic dots;
  the art pipeline is down pending CF_AI_TOKEN. Resolution: phase 1 builds
  complete behind a feature flag; Coin Spark (existing emblem art) can ship
  alone; shard tokens unflag when the painted master lands.

---

## EXCLUDED UNTIL WAVE 8 (scope fence)

- LOOT phases 2 + 3: Key Fragments, Card Tags, the 100%-survival rare rule,
  Shakedown List, tags-on-rap-sheet + Marked badge, loot cosmetic milestones,
  Loot Snout hustle node, Street Meat power pickup (gated on fairness),
  loot daily-bounty templates.
- SPECIALIZATIONS (WAVE6 section 5, DA:I branch commitment + respec): NO
  design doc landed for it this wave -- it needs its own design pass before
  build. Do not improvise it.
- Spell execute-threshold rebalance (C5) and any AIR-domain change on Street
  flyers beyond the L1C budget fix (playtest first).
- Per-level 1-line blurbs (STORYLINE 12 -- derive later from act + taunts).
- Public/social profile layer (versus splash mottos, public pages),
  matchmaking flavor from archetype labels.
- Boss portrait art, loot token paintings beyond the queue entries (art
  pipeline down -- queue now, paint when it revives).
- Burrow elevation, marketplace/NFT anything, Phase-2 camera tilt.

---

## PROTECTED LIST (byte-identical unless a lane explicitly amends above)

- TRANSITION_DUR = 5.0 and the headless harness contracts (tests/: 45/90/135
  timing checks, ak_match_harness.js, full_match_test.js, probes) -- every
  lane's acceptance includes "harness green".
- AK-FEEL B2/B3/B4 combat-feel constants (COMBAT_FEEL_SPEC verbatim);
  ENERGY_SECTION_MULT; energyCost() formula.
- AK-ATTRS clamps: agi/aspd [1.0, 1.25], def/spdef [0.80, 1.0].
- AK-SYNERGY caps MOVE_CAP / DMG_CAP and the symmetric-for-AI rule.
- Balance clamps: HP [450, 2850], dmg [35, 230] -- now ONE law for originals
  AND variants (L1C enforces, nothing may newly exceed).
- Economy faucets: XP_WIN 40, COIN_WIN 60, DROP_W 70-22-7-1, CHEST_TABLE,
  scrap prices C1/R5/E25/L250/M1000, one grantMatchRewards grant per match,
  worldChestContext.decayMult as the only replay-decay law.
- ak_* localStorage cloud-mirror key rule; loadProfile/loadWorld backfill
  pattern (never rewrite existing values); all DOM/localStorage access
  headless-guarded.
- TOWER_STATS hp/dmg/atkSpd (range handled per L1B: tower ranges unchanged).
- Dealer tease-only law (HARD). TV-MA voice, no profanity past damn/hell,
  no real brands. NO em-dash characters anywhere. No generic art ever stays
  (ART_AUTOROUTE). One-thumb portrait doctrine (no tap-to-collect).
- LOW_FX (AK-VIBES) degradation path for every new visual.

---

## ACCEPTANCE, WAVE LEVEL

1. tests/ harness fully green after EVERY lane (run per lane, not once).
2. Protected list verified by diff (constants byte-identical).
3. The anti-generic test, automated: two seeded veteran profiles produce
   visibly different deck lab, profile, arena, journal, and nemesis surfaces.
4. The blend test (standing order 15): one full world clear exercises kill
   drop -> magnet -> stash -> gate ledger -> banked grant -> rap sheet ->
   badge -> quest tick -> nemesis update -> journal entry without a seam.
5. Operator sign-off received on the L1C tuning numbers before canon.js
   regenerates (the one question in OPERATOR_ONE_PAGER.md).
