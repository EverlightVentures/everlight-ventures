# ALLEY KINGZ -- PROGRESSION + SKILL-POINTS SPEC (M07)
> Companion to PROGRESSION_DESIGN.md (the live single-player loop), META_GAME_BUILD_PLAN.md (System 1
> card levels), AK_MASTER_BLUEPRINT.md (prestige + 7 sinks), AK_WORLD_BIBLE.md (Crew Ascension, 6 tiers),
> and the LIVE code: game/index.html (XP/level, Street Code skill tree, AK-SPEC, AK-VIS/AK-GARAGE card
> levels, AK-ATTRS card tune), game/economy.js (cardLvls/copies/sp/skills shape + levelUpCard),
> game/pass.js (season XP), game/handlers_data.js (Bones skill trees).
> This is M07 PROGRESSION. Law: REUSE the live progression code; ADD prestige on top; never rewrite the
> battler. Build-plan slot: W4.1 -- "activate cardLvls + prestige burn + milestones + match XP."

## 0. GROUND TRUTH -- M07 IS MOSTLY ALREADY LIVE (the build plan predates the ship)
The build plan calls cardLvls "unused [GAP M07]." That gap is now CLOSED in the live build. What ships
today:
- **Account XP + Level 1-21** (index.html `xpToNext(lv)=80+40*(lv-1)`, `LEVEL_CAP=21`), match rewards in
  `grantMatchRewards` (WIN 40 XP / LOSS 15 / +10 per convoy gate).
- **Skill Points (SP):** `ak_profile.sp` / `spEarned`. Earned +1/level-up, +2/city first-clear,
  + quest SP, + City Vault bonus. Spent on skill-tree nodes (1 SP) + per-card tune (1 SP/pt).
- **Street Code skill tree:** 3 branches (Muscle/Hustle/Tech), 18 base nodes + 18 specialization nodes,
  folded into `computePerks()` -> `AK.PERKS` (engine clamps).
- **Specializations (AK-SPEC):** unlock at level 10, one path per branch, switch costs 2000 coins +
  refunds SP.
- **Per-card tune (AK-ATTRS):** `skills.cards[name]={hp,dmg,def,spdef,agi,aspd}`, +/-5%/pt, cap 8/card.
- **Card levels (AK-VIS / AK-GARAGE):** `cardLvls[name]` 1-10 + `copies[name]`, `levelUpCard()` in
  economy.js (copies + coins per rarity), folded as `cardLevels` in computePerks, engine clamps the mult.
- **Handler Bones trees:** `handlers.{selected,bones,unlocked}` + handlers_data.js per-handler skill_tree.
- **Season pass XP:** pass.js (30 tiers, 100 XP/tier, free + premium lanes) -- a SEPARATE XP track.

**So M07's remaining net-new work is small and specific: PRESTIGE / CREW ASCENSION + MILESTONES + the
EventBus bridge.** Everything else is formalizing what ships and wiring it to the bus.

## 1. THE PROGRESSION LAYER CAKE (six tracks, each with a distinct fantasy + sink)
| Track | Currency | LIVE field | Caps | Spent on | Status |
|---|---|---|---|---|---|
| Account level | XP | `xp` / `level` | level 21 | unlocks deck slots [1,3,6,9,12,15,18,21] + SP faucet | LIVE |
| Skill Points | SP | `sp` / `spEarned` | none (faucet-limited) | Street Code nodes + per-card tune | LIVE |
| Specialization | -- | `spec{muscle,hustle,tech}` | 1 path/branch | unlocks exclusive top-tier nodes | LIVE (unlock Lv10) |
| Card level | copies + coins | `cardLvls` / `copies` | level 10/card | +HP/+DMG stat bump (clamped, no-P2W) | LIVE |
| Card tune | SP | `skills.cards[name]` | 8 pts/card | per-card HP/DMG/DEF/SPDEF/AGI/ASPD overlay | LIVE |
| Commander | Bones | `handlers.{bones,unlocked}` | per tree | handler special/passive upgrades | LIVE |
| Season pass | pass XP / Gems | pass.js server | 30 tiers | free + premium reward track | LIVE |
| **Prestige** | **ALK (burn)** | `ascend{tier,count}` (NEW) | 6 tiers | reset level -> permanent multiplier + emblem | **NEW (M07)** |

Each track answers a different "why log in": level = unlock slots; SP = tailor your perks; card level =
make your favorite card hit harder; Bones = master your commander; pass = the season chase; prestige =
the endgame flex + the SP re-faucet.

## 2. ACCOUNT XP + LEVEL (LIVE -- formalized)
- Curve: `xpToNext(lv) = 80 + 40*(lv-1)`. Total 1->21 = 9,600 XP, ~160 matches at a winning pace.
- Match XP (in `grantMatchRewards`): WIN/Clean Sweep 40, LOSS/DRAW 15, +10 per convoy gate cleared.
  `xpMult` perk (Hustle "Fast Learner" + Kingpin/Empire spec) scales it; engine-clamped 1.0-1.25.
- Level-up grants **+1 SP** (the `spGain++` loop in grantMatchRewards). Deck slots unlock on the
  `SLOT_UNLOCK=[1,3,6,9,12,15,18,21]` table -- zero extra code.
- Live-fill XP bar on the result screen paints along the REAL curve (`renderRewards` / AK-XPBAR).

## 3. SKILL POINTS -- EARN + SPEND (LIVE -- formalized, the one canonical table)
### Earn (SP faucets)
| Source | SP | Where |
|---|---|---|
| Account level-up | +1 / level | grantMatchRewards `spGain++` |
| City first-clear (10 cities) | +2 / city | world clear hook (index.html ~7669) |
| City Vault bonus | +1 (conditional) | `vaultSp` in grantMatchRewards |
| Sidequests (UNION CREW / CARD COUNTER) | quest-defined | `quests.sp` fold |
Lifetime SP from a single climb: ~20 (levels) + 20 (10 cities x2) + quests. Prestige RE-OPENS the level
faucet (sec 7) -- that is the endgame SP engine.

### Spend (SP sinks)
1. **Street Code node** = 1 SP/rank (sec 4).
2. **Per-card tune** = 1 SP/point, max 8 pts/card across 6 attributes (sec 5).
- **Respec:** `respecSkills()` wipes all nodes + all card tune, refunds SP to `spEarned`, costs
  `RESPEC_COST=1000` coins.
- **Spec switch:** `chooseSpec()` first pick free at Lv10, switching a branch path costs
  `SPEC_RESPEC_COST=2000` coins + refunds that path's node SP.

## 4. STREET CODE SKILL TREE (LIVE -- reference, do not rebuild)
Three branches in `SKILL_TREE` (index.html ~6488), folded by `computePerks()` into the clamped
`AK.PERKS` snapshot the engine reads at `startMatch`. Never touches the engine directly.
- **Muscle (Combat):** Thick Hide (towerHp), Big Dog (unitDmg), Pack Stamina (startEnergy), Iron Collar,
  Alpha Surge (energyRegen), Junkyard King capstone.
- **Hustle (Economy):** Street Cut (coinMult), Scrapper (scrapMult), Fast Learner (xpMult), Lucky Paw
  (dropLuck), Crate Cracker (chestLuck), Kingpin Cut capstone.
- **Tech (Utility):** Cold Start (checkpointDiscount), Quick Rig (spellCD), Jump Charge (startEnergy),
  Overdrive (energyRegen), Salvage Rig (scrapMult), Ghost Protocol capstone.
- **Specializations (Lv10, one path/branch):** Muscle = Enforcer/Bulwark/Warlord; Hustle =
  Kingpin/Fence/Gambler; Tech = Hacker/Engineer/Saboteur. Each path opens 2 exclusive top-tier nodes
  gated on the branch capstone (m6/h6/t6). An off-path node never folds into perks (computePerks guards
  corrupt saves) -- power can never leak.
- **Clamp safety:** `metaPerks()` (economy.js) clamps every perk (coinMult 1-1.5, scrapMult 1-1.75,
  xpMult 1-1.25, dropLuck 0-8, chestLuck 0-0.15). An over-stacked tree saturates, never breaks.

## 5. PER-CARD TUNE (AK-ATTRS, LIVE -- reference)
`skills.cards[name] = {hp,dmg,def,spdef,agi,aspd}` point counts. `TUNE_STEP=0.05`, `TUNE_CAP=8` pts/card.
Boosts (hp/dmg/agi/aspd) = +5%/pt (5 useful pts each, engine clamps mult at 1.25); guards (def/spdef) =
-5%/pt taken (4 useful pts each, clamp 0.80). `cardTunePts()` greedy-clamps to the 8-pt cap in attr
order. Folds into `computePerks().cardTune` -> engine re-clamps at build time. Lives next to the card in
the Deck Lab collection detail (the dropdown picker was retired 2026-06-11).

## 6. CARD LEVELS (AK-VIS / AK-GARAGE, LIVE -- reference; closes the M07 cardLvls gap)
The cardLvls field the build plan called "unused" is LIVE. ONE source of truth shared by the Deck Lab
collection (index.html) and the Chop Shop Garage (economy.js `levelUpCard`): both ride
`ak_profile.cardLvls` + `.copies` + `.coins`.
- Per-level cost: `UP_COPIES[rarity]*lv` copies + `UP_COINS[rarity]*lv` coins. Common 4/20c ...
  Mythic 1/1000c at L1, scaled by current level, cap `CARD_LV_CAP=10`.
- Scaling: `levelMult(L)=1+0.10*(L-1)` (L10 = 1.90x), HP+DMG only, LINEAR (no compounding power cliff =
  no-P2W). Folded as `computePerks().cardLevels`; the engine turns it into its own clamped build-time
  mult. Copies come from dupes (drops/chests/draws/scrap-buy all bank a `copies[name]++`); scrap of the
  matching rarity can substitute missing dupes 1:1 (master-plan sec 3).
- **Card Gear (sec 2.2 of AK_SHOP_INTEGRATION.md) stacks ON TOP of card level** via a third perk map
  (`cardGear`) resolved with the handlers_data.js mods pattern -- M11 work, same clamp discipline.

## 7. PRESTIGE / CREW ASCENSION (NEW -- the M07 net-new deliverable)
The blueprint defines prestige as Crew Ascension: reset buildings to L1 but KEEP collection, gear,
emblem, permanent reputation multipliers; **6 visual tiers Bronze -> Silver -> Gold -> Platinum ->
Diamond -> Crown**; burns **500 ALK** (sink 1). Spec it at TWO honest levels that share the tier math +
the one burn sink:

### 7.1 Account Prestige (M07, single-player-friendly, ships first)
- **Trigger:** available at `LEVEL_CAP` (21). The player chooses to "Ascend."
- **Reset:** `level -> 1`, `xp -> 0`. Deck-slot unlocks stay unlocked (do NOT re-lock slots -- punishing).
- **Keep (never reset):** `owned`, `cardLvls`, `copies`, `gear`, `skills` (nodes + tune), `spec`,
  cosmetics/identity, handlers/bones, coins/scrap/gems.
- **Gain:** `ascend.tier++` (cap 6 = Crown) + a permanent, clamped multiplier and an emblem frame:
  - Per-tier permanent buff (RECOMMEND, tune in playtest): +1% coinMult, +1% scrapMult, +1% xpMult per
    tier (Crown = +6% each). Folds into the SAME `metaPerks` clamp so it can never break the budget.
  - Visual: the 6-tier emblem/frame on the profile + lobby chip + (later) crew HQ building skin.
- **Cost:** **burns 500 ALK** through the `economy.sink.request {sinkId:'prestige'}` -> `SINK_CONFIRMED`
  -> `ALK_BURNED` chain (TokenSink, 100% burn). Until ALK ships (M06), gate the Ascend button on
  `config.ready` and accept the prestige tier without the burn in a pre-M06 "preview" mode OFF by
  default.
- **The SP re-faucet (the retention hook):** re-leveling 1->21 grants the full +20 level SP again.
  Prestige is the reason the skill tree + card tune stay a live spend long after the first climb. This is
  the single-player endgame loop: max -> ascend -> re-earn SP -> deepen the build -> ascend higher.

### 7.2 Crew Ascension (M11, the blueprint's crew-leader version)
- **Trigger:** crew LEADER action in the hub once the crew HQ (MainTower, M02 subclass) hits its cap.
- **Reset:** crew buildings to L1 (M11/M02 own the building reset).
- **Keep:** card collection, gear, emblem, **permanent reputation multipliers** (the crew-wide buff).
- **Same 6 tiers, same 500 ALK burn** (sink 1), same emblem art scope (6 tiers per building/frame/emblem
  -- the massive ART scope flagged in the world bible).
- M07 owns the tier math + the burn; M11 owns the building reset + the crew-rep multiplier. They share
  the `progression.prestige` event so the social-urgency layer can broadcast "CREW ASCENDED TO GOLD."

### 7.3 Storage (NEW field, backfilled never-rewrites)
`ak_profile.ascend = { tier: 0, count: 0, lastAt: null }`. Add to `ensureShape()` (economy.js) and
`loadProfile()` (index.html) with the same backfill pattern every other field uses. `tier` 0-6 (0 =
un-ascended, 6 = Crown). The permanent multiplier is derived from `tier`, never stored separately.

## 8. MILESTONES (NEW -- light, reuses the pass/quest rails)
Account-level achievement track distinct from the season pass (which resets each season). One-time
rewards on lifetime thresholds, paid through the existing `AKSocial.claimGrants()` rail (the same rail
the pass + donations use). Examples: first card to L10, all 4 factions owned, first city cleared, first
Ascension, 100 wins. Store claimed ids in `ak_profile.identity.badges` (already exists, AK-PERSONA).
Cheap: it is a threshold check in grantMatchRewards + a grant queue. No new infra.

## 9. EVENTBUS CONTRACT (M07 produces / consumes -- no direct imports)
Per AK_BUILD_PLAN W4.1: M07 consumes `match.win` (from the engine adapter) + `economy.burn`; produces
`progression.levelup` + `progression.prestige`.
- **Consumes:**
  - `match.win` / `match.lose` (engine adapter bridge) -- the XP + SP faucet trigger. Today
    grantMatchRewards reads `AK.game` directly; the bus bridge is the read-only publish of the same facts.
  - `SINK_CONFIRMED {sinkId:'prestige'}` -- confirms the 500 ALK burn landed before applying the tier.
- **Produces:**
  - `progression.levelup {playerId, level, spGained, slotUnlocked?}` -- M05 social-urgency + the lobby
    chip listen.
  - `progression.prestige {playerId, tier, scope:'account'|'crew'}` -- M05 broadcasts the flex; M11
    consumes the crew-scope version to re-skin the HQ emblem.
  - `economy.sink.request {sinkId:'prestige', meta}` -- the burn intent into CurrencyManager.

## 10. BUILD DELTA (what is net-new vs what ships)
- **LIVE (no build):** account XP/level, SP earn+spend, Street Code tree, AK-SPEC, per-card tune, card
  levels (cardLvls/copies/levelUpCard), handler Bones trees, season pass XP. Formalize in this doc; do
  not touch.
- **NEW (M07):**
  1. `ak_profile.ascend{tier,count,lastAt}` field + backfill (economy.js ensureShape + index.html
     loadProfile).
  2. Account Prestige UI: an "Ascend" affordance at Lv21 (lobby + Collection), the 500 ALK burn intent,
     the tier-derived permanent multiplier folded through metaPerks, the 6-tier emblem art.
  3. Milestones threshold-check + grant via AKSocial.claimGrants.
  4. The EventBus bridge (sec 9): publish progression.levelup / progression.prestige; consume match.* +
     SINK_CONFIRMED. Read-only adapter, never rewrites grantMatchRewards' local-first behavior.
- **DEPENDS ON:** M06 ALK ledger (CurrencyManager + TokenSink) for the 500 ALK burn. Ship account
  prestige's UI + tier math first; gate the burn on `config.ready`.
- **M11 (separate):** Crew Ascension building reset + crew-rep multiplier (shares the tier math + burn).

## 11. OPERATOR DECISIONS NEEDED
1. **Prestige multiplier size** (sec 7.1): +1%/tier coin/scrap/xp (recommended, clamped) vs a different
   curve. Playtest-tune.
2. **Re-lock deck slots on prestige?** Recommend NO (keep slots, only reset level/xp) -- relocking is
   punishing. Confirm.
3. **Account prestige vs crew-only prestige:** ship account prestige first (single-player retention) vs
   wait for the crew layer (M11). Recommend account-first.
4. **6-tier emblem art** (Bronze->Crown) is a real art scope (per building/frame/emblem in the crew
   version) -- confirm Leonardo/Seedance budget before the crew-scope tiers (account-scope needs only the
   profile emblem first).
5. **ALK gating:** accept a pre-M06 "preview" prestige (tier without the 500 burn, OFF by default) or
   hard-block prestige until M06 ships? Recommend hard-block (keeps the sink honest).

---
*Authored for the lucrex-os-engine branch session. Grounded in a line-level read of game/index.html
(xpToNext/LEVEL_CAP, SKILL_TREE/SPEC_PATHS/computePerks, AK-VIS/AK-GARAGE cardLvls, AK-ATTRS tune,
grantMatchRewards SP faucet, city-clear SP), game/economy.js (ensureShape/levelUpCard/metaPerks),
game/pass.js (season XP), game/handlers_data.js (Bones trees). No code modified -- spec only. Pairs with
AK_SHOP_INTEGRATION.md (the shop / currency / burn-sink half of the meta loop).*
