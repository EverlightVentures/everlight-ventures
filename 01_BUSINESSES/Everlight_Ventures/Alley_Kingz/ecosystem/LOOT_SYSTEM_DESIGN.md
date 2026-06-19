# LOOT SYSTEM DESIGN -- "THE SHAKEDOWN" (AK-LOOT)
**Wave-6 loot researcher deliverable, 2026-06-12.**
**Contract:** LOOT_SYSTEM_MANDATE.md (operator: DMZ-style looting as a KEY
feature) + WAVE6_RPG_DEPTH_SPEC.md (section 7 radical-personalization test
governs every choice) + TRANSITION_SHOWPIECE_SPEC.md (the district ledger is
the banking beat). Design only -- zero game-code edits in this wave.

Street name for the system: **THE SHAKEDOWN**. When a dog goes down in the
alley, whatever it was carrying hits the pavement. Your crew pockets it as
they fight. The district gate is where you BANK it.

---

## 1. WHAT THE RESEARCH SAYS (verified across 3+ sources each)

1. **Loot is a variable-ratio reinforcement engine.** Diablo-style random
   drops are "a slot machine built into a game mechanic": unpredictable
   rewards drive the strongest dopamine response, and the anticipation cue
   (the drop sound, the colored glow) fires harder than the reward itself
   (Schultz's dopamine research, cited by Psychology of Games / Game
   Developer / PC Gamer). Design consequence: the DROP MOMENT needs its own
   sound + glow language per tier, and rates must stay genuinely random
   inside caps.
2. **Dopamine binds on PICKUP, not on grant.** Diablo III's auction house
   killed the thrill because loot stopped being a discovered, physical thing.
   The act of seeing a token on the field and watching it get scooped is the
   reward event. Design consequence: loot must be PHYSICAL TOKENS on the
   battlefield, never a silent counter increment. This independently confirms
   the operator's miniaturized-real-art rule.
3. **Extraction stakes are why DMZ/Tarkov/ARC Raiders hook.** "Everything you
   collect is only yours if you escape" turns every run into a continuous
   risk-reward calculation, and successfully extracted loot feeding PERMANENT
   progression is the retention spine (run -> extract -> upgrade -> run).
   2026 trend: the genre went mainstream by SOFTENING death punishment (ARC
   Raiders' accessibility push, ~6M weekly actives held since launch).
   Design consequence: AK imports the BANKING tension (unbanked loot at risk
   until the gate) but never confiscates out-of-match property.
4. **Tangible kill tokens beat scoreboard kills.** COD Kill Confirmed: the
   kill only "counts" when you run over the dog tag -- see it drop, hear the
   collect, get the point. Tight feedback loop, punishes passivity, creates
   push-or-bait decisions. Design consequence: kills drop tokens NEAR the
   fight, so board position has loot meaning.
5. **Auto-magnet is the proven one-thumb pattern.** Vampire Survivors /
   Archero / Survivor.io are one-finger games where kills drop gems and a
   MAGNET RADIUS collects them; the mass gem-hoover moment is repeatedly
   described as the single biggest dopamine payoff in the game. Magnet stat
   stacks, radius is upgradeable. Design consequence: auto-collect with a
   visible magnet radius around YOUR units; no tap-to-collect (the thumb is
   busy deploying).
6. **Pacing: bursts about every 5 seconds, structure beats every minute.**
   Reward-pacing literature (Game Developer / Chaotic Stupid / Level Design
   Book): active players should hit small reward bursts roughly every 5s and
   bigger structural payoffs on a minutes cadence; variable-ratio keeps the
   response rate steady, fixed milestones create the "one more gate" pull.
   Design consequence: kill drops (seconds) -> gate pinata + ledger bank
   (per minute) -> match rewards (4 min) -> first-clear vaults (per level)
   -> daily bounties. One curve, five frequencies.
7. **Anti-farm = soft ceilings, not punishment.** Economy-design consensus:
   uncapped kill faucets inflate and destroy item value; the fixes are
   per-session budgets, diminishing returns on repeats, and keeping the FEEL
   while zeroing the value (cosmetic-only drops after cap). Design
   consequence: per-match drop budgets + the existing replay decayMult.

---

## 2. THE LOOP IN ONE PARAGRAPH

Enemy dog goes down -> a miniaturized-art token pops onto the asphalt with a
tier-colored glow -> the nearest friendly unit's magnet radius hoovers it ->
it lands in the match STASH chip (UNBANKED, pulsing) -> clear the district
gate and the DISTRICT LEDGER stamps "SALVAGE BANKED +X" (TRANSITION_SHOWPIECE
step 3 gets one new line) -> banked loot folds into grantMatchRewards at the
end -> shards buy exact cards (deterministic Card Shop), tags level YOUR
hunted card, fragments forge keys -> you pin new bounties on your Shakedown
List and queue the next run. Kill -> scoop -> bank -> build -> hunt.

---

## 3. LOOT TYPES + THE MINIATURIZED-REAL-ART RULE

Operator law: real artwork shrunk into cool field tokens, NEVER generic dots.
Every token is a painted asset at 256x256 transparent PNG, rendered ~28-36 px
on field, with the rarity color/glow language the card frames already use.

| # | Loot type | Field token (the real art it miniaturizes) | Value | Feeds |
|---|-----------|--------------------------------------------|-------|-------|
| 1 | **Coin Spark** | The crowned-B $BCARDD emblem (`game/assets/ui/bcard_emblem.png`) shrunk to a spinning gold chip | 2 coins per spark; big kills drop 2-3 sparks | `profile.coins` (Garage upgrades, Scrap Crates) |
| 2 | **Scrap Shard** | New master art: jagged chrome scrap chunk with exposed wiring, gritty TV-MA house style; ONE painted master, tinted + glowed per rarity color (Common grey / Rare / Epic / Legendary gold / Mythic, exact tokens from the index.html card-frame palette) | 1 scrap of the KILLED unit's rarity (Legendary kill = 2, Mythic kill = 5) | `profile.scrap[rarity]` (deterministic Card Shop: C1 / R5 / E25 / L250 / M1000) |
| 3 | **Key Fragment** | New art: a snapped third of a brass dog-tag key on a broken chain | 1 fragment; 10 fragments auto-forge 1 Key (AK-KEYS) | `profile.keys` (free chest opens) |
| 4 | **Card Tag** | The KILLED card's REAL portrait (`game/assets/cards/<slug>.png`) masked inside a new brass dog-tag frame with chain (transparent center window) -- the token literally shows the dog you took it off | +1 copy of that exact card | `profile.copies[name]` (AK-GARAGE levelUpCard) |
| 5 | **Street Meat** (phase 3, in-match power pickup) | New art: a glowing cyber-bone wrapped in butcher paper | In-match only: +10% dmg for 10s to friendly units in 2.5 tiles when scooped; never persists | match state only (Brawl Stars power-cube analog) |
| 6 | **Dust Puff** (post-cap cosmetic) | Tiny grey reuse of the scrap-shard art at 50% alpha, no glow | 0 -- pure confetti after a budget cap empties | nothing (keeps the feel, kills inflation) |

### art_factory queue entries (ART_AUTOROUTE_DOCTRINE -- no placeholder ships permanent)
```
python3 art/art_factory.py --enqueue --id loot_scrap_shard \
  --prompt "single jagged chrome scrap-metal shard, exposed copper wiring, oil sheen, cyberpunk alley junk, isolated game item icon on transparent background, painted, gritty" \
  --out game/assets/ui/loot_scrap_shard.png
python3 art/art_factory.py --enqueue --id loot_key_fragment \
  --prompt "broken third of an ornate brass dog-tag key on a snapped chain, scratched metal, isolated game item icon on transparent background, painted, gritty" \
  --out game/assets/ui/loot_key_fragment.png
python3 art/art_factory.py --enqueue --id loot_tag_frame \
  --prompt "empty brass military dog-tag frame with ball chain, transparent center window, scratched and street-worn, isolated game UI frame on transparent background" \
  --out game/assets/ui/loot_tag_frame.png
python3 art/art_factory.py --enqueue --id loot_power_bone \
  --prompt "glowing neon cyber-bone wrapped in bloody butcher paper, street-food menace, isolated game pickup icon on transparent background, painted, gritty" \
  --out game/assets/ui/loot_power_bone.png
```
Coin Spark needs NO new art (bcard_emblem.png exists). The gritty house style
suffix is auto-appended by the factory. Until painted, tokens may ship behind
a feature flag but never with generic-dot placeholders visible to players.

---

## 4. DROP RATES -- THE NUMBERS

### 4.1 Per-kill drop chance (player-attributed kills only)
A kill rolls ONE drop check. Chance scales with the energy cost of the KILLED
unit (expensive dogs carry more):

```
P(drop) = clamp(0.20 + 0.04 * cost, 0.20, 0.60)
```

| Killed unit cost | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 |
|---|---|---|---|---|---|---|---|---|---|---|
| P(drop) | 28% | 32% | 36% | 40% | 44% | 48% | 52% | 56% | 60% | 60% |

**Guarantee rule:** Legendary and Mythic kills ALWAYS drop (P=100%) -- the
boss-kill loot moment must never whiff (variable ratio for the grind, fixed
ratio for the spectacle).

### 4.2 What drops (when the check passes)
| Roll | Weight | Detail |
|------|--------|--------|
| Coin Spark | 68% | sparks dropped: cost<=4 -> 1, cost 5-7 -> 2, cost 8+ -> 3 (2 coins each) |
| Scrap Shard | 25% | rarity = killed unit's rarity; value C1/R1/E1/L2/M5 of that rarity's scrap |
| Key Fragment | 5% | 1 fragment |
| Card Tag | 2% | +1 copy of the killed card (doubled to 4% if the card is on your Shakedown List, sec 8) |

Kill-shard rarity mirrors the victim, so kill-loot is the ONLY earnable
trickle of Legendary scrap (Legendary stays out of DROP_W match draws by
design -- this respects that wall: you cannot DRAW a Legendary, but you can
slowly MUG one, 125 Legendary kills per 250-shard card at 2/shard).

### 4.3 Deterministic structure drops (always, no roll)
| Event | Drop |
|-------|------|
| Enemy princess tower down | 3 Coin Sparks (6c) + 1 Common Shard + 10% Key Fragment |
| District gate cleared (mini-boss) | LOOT PINATA: 5 Coin Sparks (10c) + 2 Shards (1 rolled at victim-district rarity floor: districts 0-1 Common, 2 Rare, 3 Epic) + 25% Key Fragment |
| Enemy king down (match win) | nothing extra here -- the win pay lives in grantMatchRewards (no double-dip) |

The gate pinata IS the celebration shower (Diablo/Vampire-Survivors moment)
and lands exactly on the TRANSITION_SHOWPIECE ledger beat.

### 4.4 Expected per-match yield (full 4-district clear, ~20-30 kills)
~9-13 drop events: roughly 18-26 coins from sparks + tower/gate bursts
(~16-20c) = **~30-40 coins**, **3-5 shards** (mostly Common/Rare), **0-2 key
fragments**, **0-1 tags**. Against the current faucet (COIN_WIN 60 + fast-pay
+ chest coins 15-500) this is a +30-50% in-match coin layer on wins and a
meaningful consolation on losses -- exactly the "spread the rewards" order.

---

## 5. BANKING -- THE DMZ STAKE, AK-SIZED

- Scooped loot lands in the match **STASH chip** (HUD, top corner, pulsing
  gold outline) as **UNBANKED**.
- **District gate clear = BANK.** The DISTRICT CLEARED ledger panel
  (TRANSITION_SHOWPIECE step 3) gains one line: `SALVAGE BANKED +Xc +N shards`
  ticking up with the existing coin counter. Banked loot is safe forever.
- **King down (loss) = you keep 50% of UNBANKED loot** (rounded down,
  per loot type), the street takes the rest. Banked loot is untouched.
  Rare-class loot (Epic+ shards, Key Fragments, Card Tags) survives at 100% --
  losses must sting on volume, never on the jackpot piece (rage-quit guard,
  consistent with the 2026 soften-the-punishment trend).
- Match win / timer end = everything banks automatically.
- NOTHING outside the current match is ever at risk. The extraction tension
  lives entirely inside the 4 minutes.

This makes the last 30 seconds before a gate the DMZ moment: fat unbanked
stash, gate in sight, push or protect.

---

## 6. COLLECTION MECHANIC -- ONE-THUMB PORTRAIT RULING

**Recommendation: 100% auto-magnet. No tap-to-collect. Ever.**
The deploy thumb is the only thumb (AK is one-thumb portrait by doctrine);
tap-to-loot would fight card placement on the same surface. Kill Confirmed's
tension survives because the magnet is anchored to YOUR UNITS, not to the
camera: your dogs pocket what they walk past, so board position still has
loot meaning (push the lane where the loot fell).

Numbers:
- **Magnet radius: 2.0 engine tiles** around every friendly unit (and 1.5
  around your towers). Token pull speed 8 tiles/s with ease-in (the
  Vampire-Survivors streak feel), scoop SFX pitched by tier.
- **Drop pop:** token arcs 0.25s from the corpse, lands, glow-pulses on a
  1.2s cycle. Epic+ drops add a 0.4s beacon flare so they read over combat.
- **Token lifetime: 12s** on the pavement, then it fades to a ghost.
- **The Sweep:** at district transition, all uncollected/ghost tokens
  auto-sweep to the stash at **50% value** ("left it on the street, the rats
  got the rest"). Epic+ shards, Key Fragments and Card Tags ALWAYS sweep at
  100% -- no jackpot is ever lost to UX.
- LOW_FX mode: pop + scoop only, no streaks/beacons (AK-VIBES contract).

So the magnet rewards attention without ever punishing a busy thumb: play
well near your loot = full value; ignore it = 50% of the commons, all of the
rares. Skill expression, zero rage.

---

## 7. ANTI-FARM GUARDS -- PER-MATCH DROP BUDGET

| Budget pool | Cap per match | After cap |
|-------------|---------------|-----------|
| Coins from sparks | 40 | Dust Puffs (cosmetic, 0 value) |
| Shards total | 10 (sub-caps: Epic 3, Legendary 2, Mythic 1) | Dust Puffs |
| Key Fragments | 3 | nothing drops in that slot (reroll as spark) |
| Card Tags | 2 | reroll as shard |

Plus:
1. **Player-attributed kills only.** Storm Clock hazards, map events and
   AI-vs-AI deaths drop NOTHING. The AI never loots. AFK-farming a hazard
   district yields zero.
2. **Replay decay rides the existing rail:** on replays of cleared world
   levels, all budget caps multiply by the same `worldChestContext.decayMult`
   (floor 0.15) that already decays coins/xp -- one decay law, no new knob.
3. **Quick Play:** budgets at 75%, Card Tags DISABLED (targeted tag farming
   is a world-map activity; keeps Quick Play byte-light and unfarmable).
4. **Clamp discipline:** `coinMult` (hustle branch) applies ONCE at BANK
   time, never per token; all loot math lives behind the same
   metaPerks-style clamps as AK-SCRAP so a corrupt profile saturates instead
   of printing money.
5. Faucet ceiling check: worst case 40 + 60 + fast-pay + chest is still
   below one silver-chest open; the Card Shop and Garage sinks
   (C1/R5/E25/L250/M1000 scrap, 20-1000c upgrades) absorb it.

---

## 8. RADICAL PERSONALIZATION (the section-7 contract)

Anti-generic test: **would two veteran accounts look and play meaningfully
different?** Yes, on four axes:

1. **THE SHAKEDOWN LIST.** Pin up to 3 cards as bounty targets (any card in
   the dictionary). Pinned-card kills: Card Tag chance 2% -> 4% and +1 bonus
   spark. Your list is YOUR farm: a Boneguard main hunting Mythic tags runs
   different districts, different decks, different risks than a Zoomie main
   stacking Rare shards. The list shows on the profile (MySpace Top-8 energy).
2. **TAGS ON THE RAP SHEET.** Per-card battle record (wave-6 sec 7) gains
   `Tags taken: N`. 100 tags off one card = the **"Marked"** badge cosmetic
   on YOUR card detail; the lore tagline of the victim shows on the badge
   (cards_lore.js voice: take 100 tags off Stonejaw and his "Walls fall
   down. I don't." sits crossed-out on your sheet).
3. **LOOT COSMETICS.** Lifetime milestones skin the TOKENS THEMSELVES:
   1,000 banked sparks = gold-trim coin token; 500 shards = chromed shard
   glint; 25 tags = engraved tag frame. Even the loot falling on a veteran's
   battlefield looks like theirs (cosmetic differentiation mandate).
4. **BUILD HOOKS.** Hustle branch already owns the loot identity (Street
   Cut/Scrapper/Lucky Paw/Crate Cracker). Phase 3 adds one node:
   **"Loot Snout"** (hustle, max 2, req h2): +0.75 magnet radius per rank.
   A loot-spec build plays visibly differently (greedy lane pushes to scoop)
   than a muscle build.

---

## 9. ONE DOPAMINE CURVE (how it stacks, slowest to fastest)

| Cadence | Beat | System |
|---------|------|--------|
| every 2-6s | kill drop pop + magnet scoop tick | AK-LOOT (new) -- the 5s burst layer the pacing research demands |
| ~every 60s | gate LOOT PINATA + ledger SALVAGE BANKED stamp | AK-LOOT + TRANSITION_SHOWPIECE step 3 (existing beat, one new line) |
| every 4 min | match rewards: XP/coins/card drops/chest grant | grantMatchRewards (UNCHANGED -- loot adds, never replaces) |
| per level | first-clear Crew Crates, L10 City Vaults | AK-CHESTRULE (existing) |
| per day | rotating bounties ("bank 15 shards", "take 3 tags off K9 Circuitry") | wave-6 sec 5 sidequest layer (hook only, built there) |

The mandate line "end-of-match is no longer the only payday" is satisfied at
the seconds AND minutes scale while every existing payday stays byte-intact.

---

## 10. PHASED BUILD PLAN

### Phase 1 -- KILL DROPS + AUTO-MAGNET + LEDGER (ship first)
- Engine: loot-spawn event from the unit death block (the existing
  `hp<=0 -> addBurst` site in engine.js, ~line 633) + tower/gate
  deterministic drops; token entities with magnet pull; marker **AK-LOOT**.
- Loot types: Coin Sparks + Scrap Shards only. Budgets (sec 7) live from
  day one. Replay decay wired to decayMult.
- Stash HUD chip; Sweep at transition; `SALVAGE BANKED` line on the
  DISTRICT CLEARED ledger; banked loot folds into the grantMatchRewards
  summary object (one new `loot:{coins,scrap}` field, one grant per match
  preserved).
- Tables exported from `economy.js` (`AK_ECON.LOOT_TABLE`) so index/shop can
  never disagree -- same pattern as CHEST_TABLE.
- Art: enqueue `loot_scrap_shard` (sec 3); Coin Spark reuses bcard_emblem.
- Acceptance: headless harness green (45/90/135 + TRANSITION_DUR contract
  untouched, all DOM/localStorage guarded); protected constants unchanged;
  a full clear banks 25-45 loot-coins; a loss keeps exactly 50% of unbanked
  commons; LOW_FX shows pop+scoop only.

### Phase 2 -- THE RARE LAYER + THE STAKE
- Key Fragments (10 -> 1 key, auto-forge on bank) + Card Tags (+1 copy,
  world-map only) + the 100%-survival rule for rare-class loot.
- Epic+ beacon flare; tier-pitched scoop SFX (AK-AUDIO); tag token masks the
  victim's real card art in the loot_tag_frame.
- Art: enqueue `loot_key_fragment` + `loot_tag_frame`.
- Acceptance: tag copies verifiably feed levelUpCard; fragments cap 3/match;
  Quick Play never drops tags.

### Phase 3 -- IDENTITY + POWER (post balance-audit)
- Shakedown List (3 pins, profile surface, 2x tag rule); Tags-taken rap-sheet
  line + Marked badge; loot cosmetic milestones; "Loot Snout" hustle node;
  optional Street Meat power pickup (gated on the wave-6 sec 2 fairness
  report -- an in-match power faucet must pass the cost-vs-power audit
  before it ships).
- Daily bounty hooks handed to the sidequest layer (wave-6 sec 5).
- Art: enqueue `loot_power_bone`.

---

## 11. SOURCES

- COD DMZ extraction loot + risk-reward psychology: [Call of Duty official DMZ guide](https://www.callofduty.com/guides/mobile/dmz-recon-101-how-to-play), [zleague.gg DMZ extraction guide](https://www.zleague.gg/theportal/cod-mobile-dmz-guide/), [lootbar.com DMZ overview](https://www.lootbar.com/blog/en/call-of-duty-mobile-dmz-mode-info.html), [Destructoid MW4 DMZ dev interview](https://www.destructoid.com/mw4-dmz-interview-infinity-ward/)
- Extraction-genre loop + 2025-2026 retention: [Antihero Studios: What Is an Extraction Shooter](https://antiherostudios.com/blog/what-is-an-extraction-shooter), [GamesAlchemy: genre-blending extraction/looter design](https://gamesalchemy.substack.com/p/31-genre-blending-extraction-shooters), [Alloutemo extraction guide](https://alloutemo.co.uk/extraction-shooter/), [GeekVibesNation: ARC Raiders live-service numbers](https://geekvibesnation.com/arc-raiders-live-service-contender/), [arc-raiders.online 2026 player-count reality check](https://arc-raiders.online/arc-raiders-losing-players-2026/)
- Loot psychology / variable-ratio / dopamine-on-pickup: [Psychology of Games: Dopamine Binds On Pickup (Schultz research)](https://www.psychologyofgames.com/2012/06/the-psychology-of-diablo-iii-loot-part-3-dopamine-binds-on-pickup/), [Game Developer: The psychology of Diablo III loot](https://www.gamedeveloper.com/design/the-psychology-of-i-diablo-iii-i-loot), [PC Gamer: addictive psychology of loot boxes](https://www.pcgamer.com/behind-the-addictive-psychology-and-seductive-art-of-loot-boxes/), [PureDiablo: psychology behind the D2 loot system](https://www.purediablo.com/the-psychology-behind-diablo-ii-loot-system)
- Kill Confirmed tangible-token design: [Call of Duty BO6 Kill Confirmed mode guide](https://www.callofduty.com/guides/blackops6/modes/call-of-duty-guides-black-ops-6-multiplayer-mode-guide-kill-confirmed), [Call of Duty Wiki: Kill Confirmed](https://callofduty.fandom.com/wiki/Kill_Confirmed)
- Auto-magnet / one-thumb pickup UX: [Vampire Survivors Wiki: Magnet](https://vampire.survivors.wiki/w/Magnet), [Vampire Survivors Wiki: Experience Gem](https://vampire.survivors.wiki/w/Experience_Gem), [Twinfinite: hoovering up gems](https://twinfinite.net/features/hoovering-up-gems-in-vampire-survivors-is-my-new-happy-place/), [Kokutech: Vampire Survivors design analysis](https://www.kokutech.com/blog/gamedev/design-patterns/power-fantasy/vampire-survivors), [Naavik: Survivor.io / Archero deep dive](https://naavik.co/deep-dives/survivorio-archeros-footsteps/)
- Reward pacing (5s bursts) + schedules: [Game Developer: Reward Schedules and When to Use Them](https://www.gamedeveloper.com/business/reward-schedules-and-when-to-use-them), [Game Developer: Behavioral Game Design](https://www.gamedeveloper.com/design/behavioral-game-design), [Chaotic Stupid: Reward Schedules](http://www.chaoticstupid.com/reward-schedules/), [Level Design Book: Pacing](https://book.leveldesignbook.com/process/preproduction/pacing)
- Anti-farm / faucet control: [PageOne: Designing Better Game Economies](https://pageone.gg/p/designing-better-game-economies), [PulseGeek: inflation in game economies](https://pulsegeek.com/articles/inflation-in-video-game-economies-causes-and-fixes/), [Adrian Crook: 5 common mobile economy problems](https://adriancrook.com/5-common-mobile-game-economy-problems-solved/), [GameDesignSkills: economy design](https://gamedesignskills.com/game-design/economy-design/)
- In-game grounding (read this wave): `game/index.html` (grantMatchRewards / rollChestTier / DROP_W 70-22-7-1 / XP_WIN 40 / COIN_WIN 60 / CHEST_TABLE), `game/economy.js` (AK_ECON, SCRAP_DUPE, CHEST_TABLE, levelUpCard), `game/engine.js` (death block ~L633, snapshotPerks clamps, AK-FEEL/AK-SYNERGY/AK-ATTRS), `game/shop/cards_catalog.js` (scrap prices C1/R5/E25/L250/M1000), `data/cards.json` (106 cards, costs 2-11), `cards_lore.js`, LOOT_SYSTEM_MANDATE.md, WAVE6_RPG_DEPTH_SPEC.md, TRANSITION_SHOWPIECE_SPEC.md, WORLD_MAP_REWARDS_SPEC behavior via worldChestContext, ART_AUTOROUTE_DOCTRINE.md.
