# ALLEY KINGZ -- THE ECONOMY WEB (unified-economy formalization, Part 4 of THE GLUE)
> Operator 2026-06-20. Companion to AK_DEEP_DIVE_SYNTHESIS.md (Part 4) + ALLEY_KINGZ_DEEP_DIVE_SYNTHESIS.md (Part 4 raw) + AK_SYSTEMS_DESIGN.md (System 5). This is the SOURCE->SINK->CONVERT + BURN web, reconciled against the LIVE code (game/economy.js + the 8 AK_SYSTEMS waves in game/systems/). Sunflower-Land doctrine: no currency ships before its sink loop; no dead-ends.

## 0. SCOPE + HARD WALL (read first)
- This is a **wiring + balancing** formalization, **NOT** new currencies. Every LIVE currency below already exists in the `ak_profile` shape (`economy.js ensureShape`). The GLUE = connect the cross-wave conversions + lock the burn rates.
- **CRYPTO HARD WALL (unchanged, all rows):** the economy is **soft-currency only**. Gems are SERVER-ONLY (Stripe), timer-skip / cosmetic / convenience ONLY -- never buy power, never raise a rate/cap/skill-point ceiling (parity invariant). $BCARDD / ALK ($KINGZ) are **cosmetic + geo-gated**, **NEVER** an earn-by-play reward, and Gold has **NO** redemption path to any token. All economy writes go through edge fns on `mfghdobptredxxhbjwyz` (never `jdqqmsmwmbsnlnstyavl`).
- **Legend:** `[LIVE]` = wired + in the profile today. `[DSGN]` = field/loop designed, faucet or sink not yet wired. `[DEFER]` = legal/sequence-gated, code stubbed.

---

## 1. CURRENCY LEDGER -- SOURCE -> SINK -> CONVERT -> BURN

### GOLD / COINS  `p.coins`  -- the soft bottleneck  `[LIVE]`
- **SOURCE:** match payout (`grantMatchRewards`, capped `CAP_COINS=40`/match, Spark=2 coins) · GOLD MINT producer (`production.js` MINT, rate 90/cycle, Banker Bones) · chest payouts (15->500 by tier, `economy.js` CHEST loot) · arcade (daily-capped) · raid loot (`raid.js` `110*tier + rng`) · trading sale leg · mission "front N gold" reads (when positive).
- **SINK:** card upgrades (`UP_COINS` C20/R50/E400/L600/M1000, escalating) · building upgrades (`production.js` `costBase`, scales per level) · raid shield buy (gold tier ladder, `raid.js` `grant('gold', -tier.gold)`) · deterministic Card Shop · mission consume ("front 700 gold", `missions.js`).
- **CONVERT:** -> Scrap (Chop Shop / Trading Post) · <- Spark (`SPARK_COINS:2`).
- **BURN:** **~60%** of income (upgrades scale, building repairs). Anti-inflation lever = the upgrade curve, not destruction.

### SCRAP  `p.scrap{Common..Mythic}`  -- the craft currency  `[LIVE]`
- **SOURCE:** dupe cards (`SCRAP_DUPE` per rarity, `dupeToScrap`) · Chop Shop · chest scrap lines (`silver`+ tiers) · GEM MINE producer (Rare scrap, `production.js` GEM) · raid loot (`scrapR` Rare/Epic at tier>=2) · mission rewards.
- **SINK:** deterministic Card Shop -- buy the EXACT card with matching-rarity scrap (`buyCardWithScrap`, see-what-you-buy, no gambling) · card-tune / forge (design).
- **CONVERT:** -> Cards (Card Shop) · -> Gold (selling crafted/listed via trading) · the Mythic-scrap leg is **blocked** in trading (`trading.js` canList).
- **BURN:** **~70%** target (Card Forge random-outcome design). NOTE: the LIVE Card Shop is **deterministic** -- the "forge can fail" burn is DSGN; today scrap burn = the Card Shop price ladder.

### COPIES  `p.copies{cardName}`  -- per-card upgrade fuel  `[LIVE]`
- **SOURCE:** dupe draws / chest cards / any grant (`addCopies`, `AK-SHOPFIX` heals legacy cards to copies=1).
- **SINK:** card upgrades (spent alongside Gold in the Garage upgrade math).
- **CONVERT:** overflow dupes route to Scrap (`dupeToScrap`).
- **BURN:** consumed per level-up (100% of what an upgrade costs).

### KEYS  `p.keys`  -- convenience / chest opener  `[LIVE]`
- **SOURCE:** THE GENERATOR producer (`production.js` GEN, rate 0.5, Volt) · diamond chest (`keys:1`) · fragment auto-forge (10 frags -> 1 key) · mission ("slide me a key").
- **SINK:** open an owned-tier chest for free / skip its timer (`useKey`).
- **CONVERT:** <- Fragments (10:1).
- **BURN:** **100%** -- consumed on use.

### KEY FRAGMENTS  `p.fragments`  -- key sub-unit  `[LIVE]`
- **SOURCE:** CARD FORGE producer (`production.js` FORGE, rate 4, Sparks) · AK-LOOT2 rare layer.
- **SINK / CONVERT:** auto-forge 10 -> 1 Key (`bankFragments`, returns `{fragments,forged}`).
- **BURN:** 100% at forge (rolls into Keys).

### BONES  `p.bones`  -- soulbound skill currency  `[LIVE]`
- **SOURCE:** post-match · arcade (`grantReward`, `DAILY_BONES_CAP`) · quests/missions · high-karma escort encounters (`karma.js` resource rewards) · Pup-escort mission.
- **SINK:** skill trees -- the 6 handler Bones trees (`handlers_data.js`, key is `bones`) + per-card Collar Constellations · breeding costs (Kennel, DSGN) · commander upgrades.
- **CONVERT:** **NONE** -- soulbound, never tradeable / never sellable / never gem-buyable (`trading.js` has no bones leg; arcade `grant('gems')` is a no-op).
- **BURN:** **100%** -- skill nodes are permanent + irreversible.

### SKILL POINTS  `p.sp` / `p.spEarned` / `p.skills`  -- research track  `[LIVE field / DSGN faucet]`
- **SOURCE:** RESEARCH LAB producer (Doc Wattson) -- field exists, the sp faucet is DSGN (`production.js` wires GEM/MINT/FORGE/GEN today, not the Lab).
- **SINK:** `p.skills{}` skill-tree nodes (Collar Constellations visible-attribute-sheet first).
- **PARITY:** Research Lab feeds combat power -> gems may ONLY skip its TIMER, never raise the sp rate/ceiling.

### CHESTS  `p.chests{wood..diamond}`  -- loot containers (gate, not spend)  `[LIVE]`
- **SOURCE:** match result-tier (`pickChestTier`: loss->wood, sweep->gold, diamond rare) · drops.
- **SINK:** opened by waiting out a timer OR spending a Key. Random chests open ONLY with **earned soft currency** (gambling firewall); gem opens are DETERMINISTIC + odds-published + pity.
- **CONVERT:** contents -> Cards / Coins / Scrap / Keys.

### KARMA  `p.karma{zoneId}`  -- district social standing  `[LIVE]`
- **SOURCE:** friendly encounters · missions · gather nodes (`karma.js addKarma`; 7 tiers Stranger->Legend).
- **SINK:** mission-tier unlocks · shop discounts (0-30%) · building access · NPC dialog · perks (karma-gated content).
- **CONVERT:** -> crew **Reputation** at high tiers (**DSGN** -- Reputation is not yet a profile field).
- **BURN:** **0%** -- accumulates; prestige resets it (tiers get exponentially harder).

### SEASON MARKS  `p.season.marks`  -- cosmetic season currency  `[LIVE]`
- **SOURCE:** daily check-in streak · season XP (`seasons.js`).
- **SINK:** claim cosmetic season-pass rewards (`item.cost` in marks). **Cosmetic-only** -- never buys power.
- **CONVERT:** NONE. Resets per season.

### GEMS  (server-only, NOT in `economy.js`)  -- premium  `[LIVE server]`
- **SOURCE:** IAP (Stripe) · pass · events · rare drops.
- **SINK:** time-skips · cosmetics · convenience · raid gem-shield (server-resolved, `raid.js callAkRaid`).
- **CONVERT:** NONE.  **HARD RULE: never buys power -- timer/cosmetic/convenience only (parity invariant baked into DataValidator/economy).**

### MATERIALS -- WOOD / STONE / METAL  -- base-building  `[DSGN]`
- **SOURCE (planned):** hub gathering nodes · raid salvage · missions (mission table already grants `wood`).
- **SINK (planned):** building upgrades · walls/barricades (wood 200hp / stone 500 / metal 1200 / electric 800) · tool crafting.
- **CONVERT:** -> Gold (sell excess) · -> Scrap (Chop Shop).
- **BURN:** **~50%** -- destroyed in raids. **TODO:** not in `ak_profile` yet -> lands with **World-Map Sprint 2** (`worldmap.js` base-rearrange + `AK_COLLISION.validPlacement`).

### REPUTATION (crew)  `[DSGN]`
- **SOURCE:** crew wars · helping crewmates · Karma conversion at high tiers.
- **SINK:** crew roles · territory expansion · crew shop. **CONVERT:** none (social). **TODO:** wire the karma->rep bridge.

### NOS (city loop) + ALK / $KINGZ  `[DEFER]`
- NOS = the city-loop currency, **deferred until its loop exists** (`AK_SYSTEMS_DESIGN` S5). ALK/$KINGZ = the deferred game token; $BCARDD = the cosmetic meme/mascot coin. **Both cosmetic + geo-gated, never earn-by-play, legal sign-off (Theo GC) before any on-chain tie.** Keep all crypto code stubbed.

### CONSUMABLES (Repel / Potions / Leashes / Extracts)  `[DSGN/partial]`
- **SOURCE:** crafting · Block Market · mission/extraction loot. **SINK:** one-time use in combat/encounters (Repel = encounter opt-out; Leash = capture; Kibble Rush = time-skip; Patch = revert). **CONVERT:** none. Priced in soft currency / fiat -- never token for a gameplay-utility SKU.

---

## 2. THE SYNERGY LOOP -- one action touches 3+ currencies (LIVE today)
The doctrine test (Sunflower-Land): no action moves a single number. Grounded in the wired path:

```
ONE MATCH (the live battler)
  -> COINS  (grantMatchRewards, capped 40)
  -> COPIES (+ dupe cards into your collection)
  -> SCRAP  (overflow dupes -> dupeToScrap, per-rarity)
  -> CHEST  (result-tier: loss->wood ... sweep->gold)
        the CHEST is opened by a KEY (minted by THE GENERATOR producer)
            -> the KEY came from FRAGMENTS (CARD FORGE producer, 10->1)
        opening pays COINS + SCRAP + (rare) more KEYS
  -> SCRAP buys an exact card in the Card Shop (deterministic)
  -> COINS + COPIES upgrade that card (capped by TOWN HALL = anti-whale)
  -> a stronger card wins more matches -> the loop widens (more OPTIONS, not just bigger numbers)

ONE MISSION (FIXER / gather node)
  -> KARMA (district standing, gates the next tier)
  -> COINS (payout)  +  BONES (skill fuel) [+ WOOD once materials land]
  -> BONES spent in a skill tree (handler Bones tree / Collar Constellation)
  -> KARMA tier unlocks better missions + shop discount -> richer payouts
```
Every node above is a wave we already shipped; the **web is the connective tissue** between them.

---

## 3. WAVE-WIRING MATRIX -- where each currency lives in the LIVE waves

| Wave (`game/systems/`) | Sources it faucets | Sinks it drains | Status |
|---|---|---|---|
| `production.js` (5 producers) | GOLD MINT->Gold, GEM MINE->Rare Scrap, CARD FORGE->Fragments(->Keys), GENERATOR->Keys | building-upgrade Gold (`costBase`) | **LIVE** (Research Lab->SP faucet = DSGN) |
| `missions.js` (FIXER) | Gold, Keys, Bones, Karma, [Wood] | Gold consume ("front 700"), Key consume | **LIVE** (`p.missions` cache; server = ak-quests) |
| `karma.js` | Karma (encounters/gather), Bones (escort) | Karma-gated unlocks / discounts / access | **LIVE** (karma->Rep convert = DSGN) |
| `raid.js` | Gold loot (`110*tier`), Scrap loot (tier>=2) | Gold/Gems shield ladder | **LIVE client** (loot via `ak_grants`; `ak-raid` edge fn = TODO/server-pending) |
| `trading.js` | Gold/Scrap/Copies in (barter claim) | Gold/Scrap/Copies out (listing) | **LIVE client** (`TRADE_FN="ak-trading"`; edge fn = TODO/server-pending; no gems, no token) |
| `seasons.js` | Marks (check-in + season XP) | Marks (cosmetic claims) | **LIVE** (cosmetic-only) |
| `arcade.js` | Gold + Bones (daily-capped) | -- (pure faucet, capped) | **LIVE** (`grant('gems')` is a no-op) |
| `economy.js` (core ledger) | match Coins/Copies/Scrap, chest contents | card upgrades, Card Shop, chest opens | **LIVE** (localStorage; server ledger = TODO) |

---

## 4. BURN-RATE TABLE (anti-inflation, locked)

| Currency | Burn mechanism | Rate | Wired? |
|---|---|---|---|
| Gold | Card upgrades (escalating), building repairs/upgrades, shields | ~60% | LIVE |
| Scrap | Card Shop price ladder (Forge random-fail = DSGN) | ~70% | LIVE (deterministic today) |
| Copies | Consumed per level-up | per-upgrade | LIVE |
| Keys | Opening crates / timer skip | 100% | LIVE |
| Fragments | Forge into Keys | 100% | LIVE |
| Bones | Skill-tree nodes (permanent) | 100% | LIVE |
| Wood/Stone/Metal | Building + barricades (destroyed in raids) | ~50% | TODO (Sprint 2) |
| Karma | None (accumulates; prestige resets) | 0% | LIVE |
| Season Marks | Cosmetic claims (resets per season) | 100%/season | LIVE |
| Gems | Timer-skip / cosmetic only | n/a (premium) | LIVE server |

---

## 5. STILL-TODO WIRING (the glue gaps, prioritized)
1. **Materials economy (Wood/Stone/Metal)** -- add the 3 fields to `ak_profile`, faucet from hub gather nodes + raid salvage, sink into walls/buildings. Lands with **World-Map Sprint 2** (`worldmap.js`). *(highest leverage -- unlocks the Fortress + CoC defense loop)*
2. **Karma -> Reputation bridge** -- add the `Reputation` field + the high-tier conversion in `karma.js`; without it Karma has no top-end overflow sink.
3. **Server-authoritative grant ledger** -- economy is `localStorage` today (every client number is an untrusted CLAIM). Move grants behind edge fns on `mfghdobptredxxhbjwyz`; deploy `ak-raid` + `ak-trading` (client done, edge fns spec-only).
4. **Research Lab -> SP faucet** -- wire the 5th producer so `p.sp` has a source (timer-skip-only gem parity).
5. **Card Forge random-outcome burn** -- to hit the ~70% scrap burn target, add the fail/variance layer (today the Card Shop is deterministic, which is the correct gambling-firewall default -- so this is a balance decision, not a bug).
6. **Block Market consumables** -- Repel / Potions / Leashes priced in soft currency/fiat; skins = the ONLY token-eligible lane.
7. **NOS + ALK/$KINGZ** -- DEFERRED; do not faucet either before its loop exists + Theo GC sign-off.

---

## THE WEB, IN ONE LINE
Ten LIVE soft currencies (Gold/Scrap/Copies/Keys/Fragments/Bones/SP/Karma/Marks + server Gems) each have a faucet in a shipped wave and a drain in another; one match or one mission ripples through 3+ of them; the open gaps are the Materials economy, the Karma->Rep bridge, and the server ledger -- and the token lane stays cosmetic, geo-gated, and walled off from every one of these rows.
