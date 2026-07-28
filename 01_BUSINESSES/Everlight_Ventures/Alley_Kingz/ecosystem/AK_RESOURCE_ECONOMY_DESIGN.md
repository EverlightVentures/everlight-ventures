# ALLEY KINGZ -- RESOURCE / ECONOMY SYSTEM DESIGN
## AK_RESOURCE_ECONOMY_DESIGN.md
### Punch-list 11-15 (AK_PLAYTEST_FIXES.md) -- DESIGN-FIRST spec. Code does NOT change from this doc; this is the number/ratio/tool/builder/timer law the implementation batch builds to.

> Operator's words: *"thought we had all of that implemented but it's not actually working."* It is half-wired. `worldverbs.js` faucets wood/stone/metal but harvest is **walk-up-and-grab, instant, no tool**. `buildmode.js` places structures **instantly, no builder, no build time**, and the Sunflower bed is a flat +2 gold/min trickle, **not a grow cycle**. `production.js` is the only piece that already scales rate by level. This doc reconciles `AK_2D_3D_CONCEPT.md` sec 2 + sec 5 with the operator's five refinements and gives **real number tables** + **exact module hooks**.

Theme law: gritty gold cyberpunk **dog-gang**, **crew (not clan)**, **soft-currency + cosmetic only**. Gems skip **timers only** + buy cosmetics, never raise a cap, a level, or loot quality (`MODULE_CONTRACT.md` "Crypto gate").

---

## 0. RESEARCH BASIS (what the two reference economies actually do)

### 0.1 Sunflower Land (the gather / plant / trade loop)
- **Core loop:** plant seed -> wait a real timer -> harvest crop -> sell for **SFL/Coins** -> buy more seed + tools. SFL is the constantly-earned currency; **Gems** are reserved for VIP + land expansions (the "premium" lane), **Coins** buy seeds, tools and buildings. (naavik, sfl.world FAQ, docs.sunflower-land farming guide.)
- **Crop ladder (value ~ time):** the published ladder runs **Sunflower 1 min -> Potato 5 min -> Pumpkin 30 min -> Carrot 1 h -> Cabbage 2 h -> Beetroot 4 h -> Cauliflower 8 h -> Parsnip 12 h -> Radish/Wheat 24 h -> Kale 36 h**; fruit tiers run Basic 2-4 h, Medium 6-8 h, Advanced 16-48 h. More valuable = longer wait. (gam3s.gg starter guide; earnfromgaming guide.)
- **Tools gate gathering -- you cannot harvest bare-handed.** Tools are crafted at the **Blacksmith** (axe, pickaxe, shovel, hammer). **Wood needs an Axe; Stone needs a Stone Pickaxe; Iron needs a Stone Pickaxe; Gold needs an Iron Pickaxe** -- a tier ladder where the better node demands the better tool. Each tool has limited uses (durability). (shapes.inc resources; sfl.world harvesting; N1 Guild guide.)
- **Node regen timers:** a **tree regrows in 2 h** (1 h with the Apprentice Beaver skill); stone/iron/gold nodes each carry their own longer cooldown before they can be worked again. Trees yield a set amount of wood, then enter a regeneration phase. (medium/N1 Guild; sfl.world.)

### 0.2 Clash of Clans (the builder / time-gate / gem-skip loop)
- **Builders are the hard throttle.** Home Village = **max 5 Builder's Huts (5 builders) + B.O.B at TH10+**. Extra builders are **gem-only**: 2nd = 250, 3rd = 500, 4th = 1,000, 5th = 2,000, 6th = 2,000 (5,750 gems total). One builder = one concurrent upgrade; more builders = parallel progress. (CoC Wiki: Builder's Hut, Town Hall.)
- **Everything costs resources + TIME + a builder.** Upgrades scale from seconds (early) to **14+ days** (max TH). Resources (Gold/Elixir/Dark Elixir) come from collectors that fill over time, from raids, and from the Treasury. (CoC Wiki: Cumulative Costs; gameboost 2026 resource guide.)
- **Gem time-skip with diminishing returns** (the monetization curve we mirror): cost to finish = **20 + 11*(hours-1)** for jobs under a day, **260 + 123*(days-1)** for jobs over a day. Short skips are expensive per-minute; long skips are cheap per-minute -- the curve pushes you to skip *big* jobs, never trivial ones. A 1-week skip is ~90% cheaper per-minute than a 1-minute skip. (gamedeveloper.com time-monetization breakdown; cocland gem system.)

### 0.3 Reconciliation principle for AK
AK is a **phone session game** (90 s - 8 min sessions), so Sunflower's 2 h tree / 36 h kale and CoC's 14-day upgrades are **scaled down ~5-8x** to keep a faucet alive in a single sit-down, while keeping the *shape* (value ~ time, tools gate tiers, builders throttle parallelism, gems skip with diminishing returns). The operator's anchor -- **"~25 min to mine a node"** -- sets the mid-tier node respawn; small nodes regrow in 8-12 min (mobile faucet), big/rare nodes in 25-90 min.

---

## 1. THE FIVE PILLARS (maps 1:1 to punch-list items 11-15)

| # | Operator refinement | Today | This design |
|---|---|---|---|
| 11 | **Tools required to harvest** (cost gold/gems OR tradable for produce; tier = speed + durability + bonus loot) | none -- instant grab | sec 3 Tool tiers T0-T4, per node-type tool-lock, durability, bonus-loot, gem-repair (parity-safe) |
| 12 | **Time gates** on chop/mine/grow (collecting takes real time) | only a 60-180 s respawn; harvest is instant | sec 4 two clocks: **gather channel** (active seconds, tool-scaled) + **node respawn** (8-90 min) + sec 6 crop grow timers |
| 13 | **Builders = X per TH; each builder IS a dog card; card LVL + TH LVL scale speed/loot/store** | none (instant build); `production.js` scales by building level only | sec 5 builder caps per TH, **assign an owned card to a builder slot**, speed/loot/store multipliers by card level x TH x faction |
| 14 | **Ratio scale** (skill <-> resource <-> time <-> gems <-> currency), NOT random | partial (`MAT_SELL`, `townHallCost`) | sec 7 the RATIO BACKBONE: one anchor, every conversion derived from it; gem-skip ladder; produce<->resource trade |
| 15 | **Aesthetic + patterned node placement to the maps** (per-district patterns) | deterministic but scattered random | sec 8 per-district placement *patterns* (rows / ring / grid / quay-line / cluster) + themed node skins |

---

## 2. RESOURCE TAXONOMY (existing + the 2 new ones)

| Resource | Status | Source | Sink | Notes |
|---|---|---|---|---|
| **Gold** (`coins`) | live | matches, MINT, garden sell, material overflow | TH upgrade, tools, seeds, building upgrades | primary soft currency |
| **Gems** | live (server-only) | purchase / events only | **skip timers + cosmetics ONLY** | `grant('gems')` is a hard no-op; never raises a cap |
| **Wood / Stone / Metal** | live | worldverbs nodes | walls, building upgrades, sell-to-gold | `MAT_CAP=2000`; sell `wood 2 / stone 3 / metal 5` |
| **Scrap** (rarity-keyed) | live | SCRAP nodes, chests, dupes | Card Forge / Garage upgrades | keep as-is |
| **Keys / Fragments** | live | chests, GEN, FORGE | chest opens | 10 frags -> 1 key |
| **Bones** | live | skill systems | commander skill trees | soulbound |
| **Produce** (`produce`) | **NEW** | garden beds (crops) | **trade for tools, materials, gold**; feed/heal | the operator's "vegetation"; the tradable peasant resource |
| **Builder-time** | **NEW** (implicit) | TH builder slots | every build/upgrade/bulk-gather/train job | the CoC throttle; scaled by card LVL x TH |

`Produce` is the only new currency field. Garden crop state rides the existing `p.builds` entry (no new array). Everything else already has a falsy-default in `economy.js ensureShape`, so **zero-state stays byte-identical** (hard rule).

---

## 3. TOOLS (Pillar 11) -- *no tool, no harvest*

A **universal 5-tier ladder** applied per tool *type*. Four tool types map to the four material families:

| Tool type | Harvests | Node families |
|---|---|---|
| **Axe** | wood | Brushwood, Hardwood |
| **Pickaxe** | stone | Rubble, Boulder |
| **Crowbar** | scrap + metal | Scrap heap, Wreck, Coolant pipe |
| **Drill** | rare metal | Rare vein (contested only) |

### 3.1 Tier table (the multiplier ladder -- same shape for every tool type)

| Tier | Name | Buy cost (gold) | OR produce | Durability (uses) | Gather-speed | Time mult | Bonus loot | Rare-drop | Unlock |
|---|---|---|---|---|---|---|---|---|---|
| **T0** | Bare Paws | -- | -- | inf | -- | -- | -- | -- | default -- **can only pick loose produce; cannot work any node** |
| **T1** | Rusty | 60 | 25 | 25 | 1.00x | x1.00 | +0% | 0% | TH1 |
| **T2** | Street | 220 (+30 Common scrap) | 90 | 60 | 1.35x | x0.74 | +15% | 5% | TH3 |
| **T3** | Power | 600 (+40 Rare scrap) | 240 | 120 | 1.80x | x0.56 | +30% | 10% | TH5 |
| **T4** | Chrome | 1,500 (+60 metal) | (craft only) | 240 | 2.50x | x0.40 | +50% | 18% | TH7 -- *T1-class nodes cost 0 durability* |

- **Node tool-lock:** each node sets a **minimum tier**. A Boulder needs Pickaxe >= T2; a Coolant pipe needs Crowbar >= T3; a Rare vein needs Drill T4 (see sec 4). Walking up with a lower tier shows `NEED A BETTER {TOOL}`.
- **Durability:** each completed harvest spends **1 use** (T4 spends 0 on T1-class nodes). At 0 uses the tool breaks -> auto-falls back to the next lower owned tier (never to "unusable"; you always keep T1 once bought).
- **Repair / instant-buy with gems (parity-safe):** gems may **refill durability** or **instant-buy** a tier you have already unlocked (convenience), but **never unlock a tier above your TH gate** and never change its stats. This is the only gem touch on tools.
- **Produce path** (operator's "tradable for vegetation"): every tier <= T3 is buyable with **Produce** instead of gold, at the rate in the table, so a farmer who never fights can still tool up by growing crops.

### 3.2 Faction affinity (flavor + small edge, ties tools to the 4 factions)
The *equipped tool's art skin* + a **+10% bonus loot** when the tool's faction matches the active builder dog's faction: Crowned->gold nodes, Rusted->metal/scrap, Hologhost->tech/keys, Unbound->produce/wood. Cosmetic-driven, capped at +10%, never stacks past T4's +50%.

---

## 4. TIME GATES (Pillar 12) -- two clocks

### 4.1 Clock A -- the **gather channel** ("collecting takes time")
Harvest is no longer instant. Tapping a ripe node starts a **channel**: the dog works for `channel_seconds` (progress ring, alpha-only, no shadowBlur). Channel time is reduced by tool tier and by the working dog's skill:

```
effective_channel = base_channel x toolTimeMult x (1 / builderSpeed)
```
(If a *builder* is auto-working the node, the player is free; if the *player* channels manually, builderSpeed uses the player's lead card. See sec 5.)

### 4.2 Clock B -- the **node respawn** (the "~25 min" node)
On harvest the node depletes and regrows over `respawn_ms`, stepping `growthStage 0->1->2->3` (the depletion art already exists in `worldverbs.drawNode`). Respawn is **fixed** (not tool-scaled): tools speed the *work*, time gates the *supply*.

### 4.3 NODE TABLE (the numbers)

| Node | Material | Tool-lock | Base channel | Base yield | Respawn | Districts (bias) |
|---|---|---|---|---|---|---|
| **Brushwood** | wood | Axe T1 | 6 s | 8 wood | **8 min** | uptown |
| **Hardwood** | wood | Axe T2 | 16 s | 22 wood | **25 min** | uptown |
| **Rubble** | stone | Pickaxe T1 | 8 s | 8 stone | **12 min** | midtown |
| **Boulder** | stone | Pickaxe T2 | 18 s | 24 stone | **35 min** | midtown |
| **Scrap heap** | scrap (Common) | Crowbar T1 | 7 s | 12 scrap | **10 min** | docks |
| **Wreck** | metal+scrap | Crowbar T2 | 16 s | 5 metal + 6 scrap | **30 min** | docks |
| **Coolant pipe** | metal | Crowbar T3 | 14 s | 5 metal | **45 min** | docks |
| **Rare vein** | metal (+rare drop) | Drill T4 | 28 s | 10 metal + jackpot roll | **90 min** | contested / raid zones only |

Mid-tier nodes land on the operator's **~25 min** anchor; small nodes feed the fast faucet, rare nodes throttle the top end (CoC long-skip shape). Today's flat `dur` (90/120/75/180 s) becomes these per-node `respawn` values; today's instant harvest becomes the channel.

### 4.4 Gem-skip the gather/grow (optional, parity-safe)
A channel or grow timer can be **instantly finished with gems** using the sec 7.3 ladder -- convenience only, identical yield, never more loot.

---

## 5. BUILDERS = DOGS (Pillar 13)

### 5.1 Builder caps per Town Hall
`builderCap(TH) = clamp(1 + floor(TH/2), 1, 6)`:

| TH | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| **Builders** | 1 | 1 | 2 | 2 | 3 | 3 | 4 | 4 | 5 | **6** |

Mirrors CoC's 5 (+B.O.B at TH10 -> our 6th "Top Dog" foreman slot). Each builder runs **one concurrent job** (build / upgrade / bulk-gather / train). More TH = more parallel jobs.

### 5.2 A builder IS an owned card (the cards run the city)
Assign any **owned card** to a builder slot at the **Foreman** (Town Hall keeper). The assigned dog's **card level** and your **TH level** set that builder's job speed, loot tier, and what its keeper store stocks:

```
builderSpeed(cardLvl, TH) = (1 + 0.08*(cardLvl - 1)) * (1 + 0.05*(TH - 1))
```

### 5.3 Speed grid (builderSpeed -- the skill<->time lever)

| cardLvl \ TH | TH1 | TH3 | TH5 | TH7 | TH10 |
|---|---|---|---|---|---|
| **Lv1** | 1.00x | 1.10x | 1.20x | 1.30x | 1.45x |
| **Lv3** | 1.16x | 1.28x | 1.39x | 1.51x | 1.68x |
| **Lv5** | 1.32x | 1.45x | 1.58x | 1.72x | 1.91x |
| **Lv7** | 1.48x | 1.63x | 1.78x | 1.92x | 2.15x |
| **Lv10** | 1.72x | 1.89x | 2.06x | 2.23x | **2.49x** |

A maxed dog under a maxed Town Hall works ~2.5x faster than a fresh L1 dog at TH1. This is the operator's **"skill <-> time"** scale, made of real numbers.

### 5.4 Loot tier & store offerings by builder
- **Loot tier:** the builder card's **rarity** sets a bonus-loot floor; **cardLvl >= 7** unlocks the **"high-gear" drop** (one tier better on rare rolls -- e.g. a Boulder can drop a metal bonus, a Wreck can roll a fragment). Realizes "high-gear loot tier."
- **Store offerings:** each producer/keeper store gates its stock by **TH** (rows) AND the **best assigned builder's level** (top SKU). e.g. The Workbench sells T1-T2 at TH3, unlocks T3 at TH5 *and* a Lv5+ builder, T4 at TH7 *and* a Lv7+ builder. Realizes "what the store offers."

### 5.5 Build / upgrade / train as TIMED builder jobs
- **Build a structure** (buildmode): no longer instant. Costs materials **+ a build time** consumed by one builder. `build_time = base_time / builderSpeed`.
- **Upgrade a building / Town Hall:** same -- gold + materials + a builder for `time / builderSpeed`.
- **Bulk-gather:** assign a builder to a node cluster -> it auto-harvests on a loop (no durability cost, like CoC builder vs. player-tool), banking material while you are away (production-style accrual reused).
- **Train (optional, TH-gated):** at TH5+, a card level-up (`levelUpCard`) becomes a **timed** job (CoC lab style) rather than instant, so progression has a parallelism cost. Default OFF until TH5 to keep early game snappy.

### 5.6 Base build times (pre-speed)

| Job | Base time (TH1, Lv1 builder) | Notes |
|---|---|---|
| Wall / barricade | 30 s | trivial, keeps placement fluid |
| Path / planter / garden bed | 10 s | deco/utility |
| Producer building L->L+1 | 4 min -> 90 min (scales with target level) | reuse `production.upCost` curve for *time* too |
| Town Hall L->L+1 | 8 min (TH1->2) -> 6 h (TH9->10) | the keystone gate |
| Garden bulk-plant/harvest (per bed) | 8 s | builder tends beds in batch |

All divided by `builderSpeed`, all gem-skippable (sec 7.3), all one-builder-per-job.

---

## 6. GARDENS (Pillar 12 + the sec 3 produce faucet) -- Sunflower plant->grow->harvest

Replace `buildmode.js`'s flat **+2 gold/min trickle** with a real **plant -> grow-timer -> harvest** cycle on each `GARDEN` ("Sunflower Bed"). Crop state rides the build entry: `b.crop`, `b.plantedAt`; `growthStage = clamp(floor(elapsed/growTime * 4), 0, 3)` (reuse the stage idea already in worldverbs). Ripe bed -> tap **HARVEST** (or a builder bulk-tends) -> yields **Produce**.

### 6.1 CROP TABLE (Sunflower ladder, scaled ~6x for mobile)

| Crop | Seed cost (gold) | Grow time | Yield (produce) | Sell (gold) | Produce/hr* | Unlock |
|---|---|---|---|---|---|---|
| **Catnip** | 5 | 2 min | 3 | 6 | 90 | TH1 |
| **Street Corn** | 20 | 12 min | 9 | 26 | 45 | TH1 |
| **Pumpkin** | 60 | 30 min | 20 | 78 | 40 | TH2 |
| **Beetroot** | 140 | 2 h | 46 | 190 | 23 | TH3 |
| **Kingweed** | 320 | 6 h | 110 | 470 | 18 | TH5 |
| **Goldroot** | 700 | 16 h | 230 | 1,020 | 14 | TH7 |

*Produce/hr falls as grow-time rises (anti-AFK: short crops are higher throughput but demand attention; long crops are set-and-forget but lower rate -- exactly Sunflower's shape). Every crop's gold ROI is **positive but below active match income**, so farming supplements, never replaces, playing.

### 6.2 Produce sinks
Produce -> **buy tools** (sec 3, the no-fight path), **trade for materials** at the Trading Post (sec 7.4), **sell for gold** (table above), or **feed/heal** (future Infirmary tie-in). A builder dog can be assigned to **auto-tend** all beds in a zone (plant + harvest on a loop) at `builderSpeed`.

---

## 7. THE RATIO BACKBONE (Pillar 14) -- one anchor, everything derived

> Nothing is random. Pick **one anchor**, derive every other rate so the web stays balanced when any single number is retuned.

**ANCHOR:** `1 base labor-minute of T1 active gathering ~= 12 gold of value.`
(Brushwood: 8 wood / 6 s channel = 80 wood/min, at sell `wood 2` that is 160 gold/min *raw faucet*, intentionally throttled by the **8-min respawn** so sustained yield ~= 1 wood/min/node ~= the anchor once supply-gated. The respawn is the real regulator, matching CoC collectors.)

### 7.1 Resource -> Gold (sell / overflow) -- *keep existing, add produce*
| Resource | Gold each | Source of truth |
|---|---|---|
| Wood | 2 | `MAT_SELL.wood` (live) |
| Stone | 3 | `MAT_SELL.stone` (live) |
| Metal | 5 | `MAT_SELL.metal` (live) |
| Produce | 1.0 base (crop sell tables apply the real premium) | NEW |

Sell rates stay **below** match/producer income so selling never beats playing (existing AK-MAT doctrine).

### 7.2 Gold -> progression (keep existing curves)
- **Town Hall:** `townHallCost(lv) = 500*lv*lv` -> 500 / 2,000 / 4,500 / 8,000 / 12,500 / 18,000 / 24,500 / 32,000 / **40,500** (TH9->10). (live)
- **Producer upgrade:** `upCost = costBase * 1.5^(lvl-1)` (live).
- **Card level:** `UP_COINS[rarity]*lvl` + `UP_COPIES[rarity]*lvl` copies (live).

### 7.3 Gems -> Time (skip ladder -- CoC diminishing-returns shape, AK-scaled)
| Time remaining | Gem cost | Per-minute |
|---|---|---|
| <= 2 min | **free** (auto-finish) | -- |
| <= 10 min | 2 | high |
| <= 30 min | 5 | -- |
| <= 1 h | 9 | -- |
| <= 4 h | 24 | -- |
| <= 12 h | 60 | -- |
| <= 24 h | 100 | low |

Closed form (matches the table within rounding, mirrors CoC `20+11*(h-1)` / `260+123*(d-1)`):
```
gemSkip(min) = min<=2 ? 0 : min<=60 ? round(2 + 7*(min/60))*k : round(24 + 76*((min-240)/1200))
```
Gems skip **only**: build/upgrade/TH timers, gather channels, crop grow, tool-durability repair. **Never** caps, levels, loot quality (HARD LAW).

### 7.4 Produce <-> Resource <-> Tool (the trade web -- operator's "vegetation <-> resources")
| Trade (at Trading Post / Chop Shop) | Rate |
|---|---|
| Produce -> Wood | 1 produce -> 0.8 wood |
| Produce -> Stone | 1 produce -> 0.55 stone |
| Produce -> Metal | 1 produce -> 0.30 metal |
| Produce -> Gold | 1 produce -> 1.0 gold (crop tables give the premium) |
| Wood/Stone/Metal -> Gold | `MAT_SELL` (2 / 3 / 5) |
| Produce -> Tool (T1-T3) | sec 3.1 produce column (25 / 90 / 240) |

All trades route through `convertMaterial`-style atomic helpers; rates are **lossy** (a small spread) so trading is a convenience, not an arbitrage faucet.

### 7.5 Skill -> everything (the multiplier that ties it together)
`builderSpeed(cardLvl, TH)` (sec 5.2) multiplies **gather channel, build time, upgrade time, bulk-gather rate, crop auto-tend, train time**. One function, applied everywhere -> the "skill <-> resource <-> time" loop is a single coherent lever, not scattered constants.

### 7.6 Worked balance check (sanity)
- **Tool T1 axe (60 gold)** ~= MINT L1 (90 gold/hr) in 40 min, or ~1 match. Reasonable on-ramp.
- **TH1->2 (500 gold)** ~= ~5.5 h of MINT L1 *or* a handful of matches *or* selling ~250 wood. Multiple paths, none trivial.
- **A wood wall (10 wood)** = ~1.25 Brushwood harvests (8 wood each). Matches the live `worldverbs` comment ("a few harvests fund a wall").
- **Maxed builder (2.49x)** turns a 6 h TH9->10 into ~2.4 h -- meaningful but not a skip; gems remain the only true skip.

---

## 8. PATTERNED NODE PLACEMENT (Pillar 15) -- designed *to* each district

Replace `worldverbs.genZone`'s random-within-constraints scatter with a **per-zone placement *pattern***, still seeded deterministically and still honoring door/plaza/corridor/debris clearance (keep all the existing exclusion checks). Pattern + node-type + density are assigned per district so each map *reads* as a place, not noise. The 9 zones (from `index.html ZONES`):

| Zone (id) | Ground | Pattern | Dominant nodes | Density | Aesthetic note |
|---|---|---|---|---|---|
| **HOME_TURF** (THE LOT) | uptown | **Orchard rows** -- 2 tidy rows flanking the plaza | Brushwood, Hardwood | low (safe home base) | groomed, gold-lit, the player's yard |
| **DOWNTOWN** | midtown | **Rubble grid** -- lattice in the lot interior | Rubble, Boulder | med | construction-site teardown |
| **NEON_HEIGHTS** | midtown | **Boulevard cluster** -- clumps along the strip | Rubble, Brushwood | med | broken planters + curb rubble |
| **THE_YARDS** | docks | **Scrap field** -- staggered heaps | Scrap heap, Wreck | high | junkyard rows |
| **FACTORY_ROW** | docks | **Pipe runs** -- straight lines along the wall | Coolant pipe, Wreck | med-high | industrial, cyan coolant glow |
| **THE_STRIP** | docks | **Perimeter ring** -- nodes hug the edges | Scrap heap, Rubble | med | open center for foot traffic |
| **THE_DOCKS** | docks | **Quay line** -- single row along the water edge | Coolant pipe, Wreck, Rare vein* | high | metal-rich, the top faucet |
| THE_OVERLOOK | midtown | *locked (POLICE CHECKPOINT)* | -- | -- | unlocks late |
| THE_UNDERCITY | midtown | *locked (COLLAPSED BRIDGE)* | -- | -- | unlocks late |

*Rare veins (Drill T4) live only in contested/raid zones and the deepest docks -- the top of the supply curve.

**Implementation:** add a `PATTERN` map (zoneId -> `{shape, nodes[], count}`) and pattern generators (`rows`, `grid`, `ring`, `line`, `cluster`) seeded by `mulberry32(hashStr('AKWVP|'+zid))`. Each generator emits candidate points; the **existing** clearance filters (corridors, doors, plaza bubble, debris, min-spacing) still run, so placement stays legal. `GROUND_BIAS` becomes the *fallback* for unlisted zones.

---

## 9. CRYPTO / PARITY GUARDRAILS (re-stated -- HARD LAW)
- Gems skip **timers** + buy **cosmetics** only. Never raise builder caps, TH/card levels, tool tiers above the TH gate, loot quality, or yields.
- Produce, materials, scrap, keys, bones, gold = **100% client-side soft currency**. No `$BCARDD` / `ALK` in any tool, trade, crop, or builder reward.
- `ctx.currency.grant('gems', ...)` stays a hard no-op (gems server-only).
- Tools, builders, crops are **earnable free** (gold or produce); gems are pure convenience. Not pay-to-win.

---

## 10. IMPLEMENTATION HOOKS (exact module -> function changes)

> All additive. **Do NOT edit `engine.js`.** Keep every JS hook/ID. 60 fps: progress rings are alpha/transform only, no per-frame `shadowBlur`. Respect `prefers-reduced-motion`. Verify `node --check` on every `.js`; extract+parse inline `<script>` in any `.html` touched. e5-only deploy.

### 10.1 `economy.js` -- the law tables + helpers (single source of truth)
- **`ensureShape(p)`** add falsy-defaults: `p.produce = 0`; `p.tools = {}` (`{axe:{tier,dur}, pickaxe:{}, crowbar:{}, drill:{}}`); `p.crew = {}` (`{slotIndex:{card, task, target, started, dur}}`). (Garden crop state rides existing `p.builds[i].crop/plantedAt`, no new array.) Zero-state stays byte-identical.
- **New constants:** `TOOL_TIERS` (sec 3.1), `GEM_SKIP`/`gemSkipCost(min)` (sec 7.3), `BUILDER_CAP(th)` (sec 5.1), `builderSpeed(cardLvl, th)` (sec 5.2), `CROPS` (sec 6.1), `TRADE_RATES` (sec 7.4).
- **New helpers** (all atomic via `mutateProfile`): `buyTool(type, tier, payWith)`, `equipTool(type, tier)`, `spendDurability(type, n)`, `toolFor(p, type)`; `assignBuilder(slot, cardName, task, target)`, `builderCapNow(p)` (reads `townHall`); `tradeProduce(toKind, n)` + extend `convertMaterial` to accept `produce`; `gemSkip(jobRef)` (server-gated stub, gems server-only). Export all on `AK_ECON`.
- **Town Hall:** keep `townHallCost`/`upgradeTownHall` (it already deducts -- playtest #7 is a UI surfacing fix, not a logic bug). Add `townHallUnlocks(lv)` -> `{cardLvlCap:lv, builders:BUILDER_CAP(lv), crewSize, grid}` so the #thpanel can *show* what an upgrade provides.

### 10.2 `systems/worldverbs.js` -- tools + channel + node timers + patterns + scaling
- **`NODE_TYPES`** -> the sec 4.3 table: add `tool` (axe/pickaxe/crowbar/drill), `minTier`, `channel` (active seconds), and raise `dur` to the 8-90 min respawns.
- **`harvest()`** -> (1) gate on `AK_ECON.toolFor(p, node.tool).tier >= node.minTier` (else banner `NEED A BETTER {TOOL}`); (2) **start a channel** instead of instant grant -- add `WV.channel = {key, t0, dur}`, advance in `onTick`, complete when `elapsed >= base_channel * toolTimeMult / builderSpeed`; (3) on complete: grant yield * (1 + toolBonus + factionBonus), roll rare-drop, **spend 1 durability** (0 for T4 on T1-class), then deplete + set respawn (`p.nodes[zid][key] = {r: now+respawn, d: respawn}`, same shape, new values).
- **Channel render:** in `onDrawWorld`/`drawNode`, draw a gold progress arc for the channeling node (alpha only).
- **Placement:** add `PATTERN` map + generators (`rows/grid/ring/line/cluster`); `genZone` calls the zone's pattern, keeps all existing clearance filters. `GROUND_BIAS` = fallback.
- **Builder bulk-gather:** if a `p.crew` slot targets this zone with task `gather`, accrue material on a `production`-style timer at `node.yield * builderSpeed` (no durability), bank via `bankMaterial`.

### 10.3 `systems/buildmode.js` -- builders + real gardens
- **Build/upgrade timing:** `place()` no longer instant for HP structures -- enqueue a builder job (`p.crew` slot, `dur = base_time / builderSpeed` from sec 5.6); show a build timer + a gem-skip button; structure renders "under construction" until done. Require a **free builder** (`builderCapNow` minus active jobs > 0) else banner `ALL BUILDERS BUSY`. (Walls' HP for raids = playtest #2, separate.)
- **GARDEN:** delete the flat +gold trickle in `onTick`. On entering/tapping a `GARDEN` build with no crop -> crop picker (TH-gated, sec 6.1), deduct seed gold, set `b.crop/b.plantedAt`. `growthStage` from elapsed/growTime drives the sprite. Ripe -> `HARVEST` grants `produce` (* faction/builder bonus). A `crew` slot with task `tend` auto-plants+harvests beds in the zone.
- **Demolish refund** stays 50%.

### 10.4 Town Hall -- `index.html #thpanel` + `economy.js`
- `#thpanel` reads `AK_ECON.townHallUnlocks(lv)` to **show** the caps an upgrade unlocks (card-level cap, builders, crew size, grid) **and** the exact cost, and confirms the deduction (playtest #7). Logic already atomic in `upgradeTownHall`.
- The **Foreman** (Town Hall keeper, `onEnterBuilding`) is where you **assign owned cards to builder slots** (up to `builderCapNow`) and pick each builder's task (build / gather / tend / train). New small module **`systems/crew.js`** owns this interior (disjoint ownership per MODULE_CONTRACT) and reads/writes `p.crew` via `AK_ECON`.

### 10.5 `systems/production.js` -- reconcile with builders
- Effective rate gains the assigned builder's multiplier: `ratePerHr * (builder ? builderSpeed(builderCardLvl, TH) : 1)`. Keeps the passive producers consistent with active gather (a high-level dog speeds *both*). Building level scaling stays; this multiplies on top.
- Store SKUs (`renderKeeper`) gate by `TH` + best builder level (sec 5.4).

### 10.6 New module -- `systems/crew.js` (Foreman / builder assignment)
- `AK_SYSTEMS.register({ id:'crew', onEnterBuilding(b){ if(b.id!=='TOWNHALL') return false; ... }, ... })`. Renders a `ctx.ui.keeperCard` (or `ctx.overlay.open` for the assignment grid): list builder slots (`builderCapNow`), let the player drop an owned card into each, choose a task + target zone, show each job's timer + gem-skip. All writes atomic via `AK_ECON.assignBuilder`. Headless-safe, falsy-default, no engine edits.

### 10.7 Test gates (per task HARD rules)
`node --check economy.js worldverbs.js buildmode.js production.js crew.js`; parse each touched inline `<script>`; verify zero-state profile is byte-identical (no field written until first tool buy / first plant / first builder assign); confirm `grant('gems')` no-op; 60 fps (no new per-frame `shadowBlur`).

---

## 11. PHASED ROLLOUT (suggested; design-only)
1. **P1 -- Tools + channel + node timers** (`worldverbs` + `economy` tool tables). The harvest loop becomes real. Lowest risk, highest "it works now" payoff.
2. **P2 -- Gardens** (`buildmode` GARDEN grow cycle + `produce` currency + trade rates). The Sunflower layer.
3. **P3 -- Builders** (`crew.js` Foreman + `builderCap` + timed build/upgrade + `builderSpeed` everywhere + production reconcile). The CoC throttle + skill scaling.
4. **P4 -- Patterns + faction affinity + store gating + gem-skip UI** (`worldverbs` PATTERN, sec 5.4 stores, sec 7.3 skip). Polish + monetization-safe convenience.

---

*Document version: 2026-06-20 - Status: SPEC-ONLY (no game code changed) - Companion to AK_2D_3D_CONCEPT.md sec 2 + sec 5, AK_PLAYTEST_FIXES.md items 11-15, specs/MODULE_CONTRACT.md.*

### Sources
- Sunflower Land -- economy & rise: https://naavik.co/digest/sunflower-land/
- Sunflower Land -- FAQ (currencies): https://wiki.sfl.world/en/faq
- Sunflower Land -- farming guide (docs): https://docs.sunflower-land.com/player-guides/farming-guide
- Sunflower Land -- starter tips / crop ladder: https://gam3s.gg/sunflower-land/guides/sunflower-land-guide-starter-tips-before-building-your-first-farm/
- Sunflower Land -- play-to-earn guide (crop tiers): https://www.earnfromgaming.com/ultimate-guide-sunflower-land-play-to-earn/
- Sunflower Land -- resources & tools (axe/pickaxe tiers): https://shapes.inc/fandom/sunflower-land/resources
- Sunflower Land -- tree regen (beginner guide): https://medium.com/@n1guildofficial/beginners-guide-in-sunflower-land-85bcf6dcf4d7
- Clash of Clans -- Town Hall / builders: https://clashofclans.fandom.com/wiki/Town_Hall
- Clash of Clans -- Builder's Hut (gem costs): https://clashofclansconception.fandom.com/wiki/Builder's_Hut
- Clash of Clans -- cumulative costs / times: https://clashofclans.fandom.com/wiki/Cumulative_Costs
- Clash of Clans -- 2026 resource guide: https://gameboost.com/blog/all-resources-in-clash-of-clans
- Clash of Clans -- gem time-skip formula: https://www.gamedeveloper.com/business/clash-of-clans-time-monetization-formulas-demistifyed
- Clash of Clans -- gem system: https://cocland.com/miscellaneous/how-the-gem-system-works
