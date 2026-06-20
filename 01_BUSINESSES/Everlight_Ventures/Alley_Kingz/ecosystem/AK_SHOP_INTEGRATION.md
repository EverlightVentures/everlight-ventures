# ALLEY KINGZ -- SHOP INTEGRATION SPEC (master-plan items -> live shop -> ALK economy -> 7 burn sinks)
> Companion to SHOP_MARKETPLACE_MASTER_PLAN.md (the WHAT), AK_MASTER_BLUEPRINT.md (token economy + 7 sinks),
> AK_WORLD_BIBLE.md (currencies canon), META_GAME_BUILD_PLAN.md (System 1-3), and the LIVE code:
> game/shop/shop.js + game/economy.js + game/drip.js + game/pass.js + game/handlers_data.js +
> ALLEY_KINGZ_CORE/MODULE_06_ECONOMY/{CurrencyManager,TokenSink}.js.
> This doc is the HOW: where every master-plan SKU lands in the shop that already ships, what currency it
> moves, and which of the 7 burn sinks (if any) it fires. Law: WRAP the live shop, never rewrite it.

## 0. GROUND TRUTH (what is already LIVE -- do not relitigate)
The Chop Shop (`game/shop/shop.js`, ~2600 lines) is a separate SURFACE. It never imports engine.js,
never touches window.AK, posts INTENTS to the `alley-kingz-shop` Supabase edge fn (project
mfghdobptredxxhbjwyz); the SERVER decides every gem grant + every draw outcome. Offline it renders
local DEMO data clearly labelled "Local Mode".

Live shop tabs (the `tabsBar()` list in shop.js): `deck` Deck Lab | `gems` Gems | `cards` Card Shop |
`draw` Lucky Draw | `chests` Crates | `upgrade` Collection | `codex2` Codex | `handlers` Handlers |
`drip2` Drip | `crew2` Crew | `pass2` Alley Pass | `hit2` Hit List | `street` Street Code.

So most master-plan categories ALREADY have a home tab. The net-new surfaces are CARD GEAR and the
NFT MARKETPLACE. Everything else is a wiring + currency job, not a new screen.

Live wallet = `localStorage.ak_profile` via `game/economy.js` (window.AK_ECON), local-first for
coins/scrap/keys/chests; gems are SERVER-ONLY (signed-out = 0 gems by definition). `walletView()` in
shop.js already merges "server gems + local everything else" into one header wallet.

## 1. THE CURRENCY LAYER CAKE (reconciled across blueprint, world bible, master plan, and live code)
The plans use four different names for overlapping things. This is the single reconciled model.

| Layer | Canonical name | LIVE ak_profile field | Earned from | Buyable for $ | Burns? |
|---|---|---|---|---|---|
| Hard IAP | **Gems** | `gems` (server-only, alley-kingz-shop) | Stripe checkout / $BCARDD on-ramp (later) | YES | No -- converts INTO items, in-game value only |
| Soft street | **Coins** (the "Fuel" of the old plans) | `coins` | match wins, loot Sparks (2c each), chests, dailies | No (anti-P2W) | spent on card upgrades + soft offers |
| Meta token | **ALK** | NOT in ak_profile yet -- M06 Supabase-ledger-mocked | daily login, raid loot, task board, crew chest, staking, events | No (earned-only, anti-P2W) | YES -- the 7 burn sinks |
| Season | **Gears** | pass premium lane (pass.js) | pass tiers, events | via pass only | No |
| Craft | **Scrap** (per rarity) | `scrap{Common..Mythic}` | dupes (SCRAP_DUPE), chests, Chop Shop | indirectly (gems->chests) | consumed on Card Shop buy + upgrade dupe-sub |
| Convenience | **Keys / Fragments** | `keys`, `fragments` (10 frags forge 1 key) | match loot, diamond crate | No | consumed opening an owned crate free |
| Commander meta | **Bones** | `handlers.bones` | post-match grant | No | consumed unlocking handler skill nodes |
| Account meta | **Skill Points (SP)** | `sp` / `spEarned` | level-up (+1), city first-clear (+2), quests, City Vault | No | consumed on skill nodes + per-card tune |

**The naming fork the operator must rule on (flagged, not assumed):** the blueprint's deflationary
"ALK" is the OVERWORLD/CREW token (its inflows are login/raid/crew-chest/staking, NOT match coins).
The live battler already runs on `coins`. Two clean options:
- **(A) RECOMMENDED -- keep them distinct.** `coins` stays the battler/PvE soft currency the Chop Shop
  already spends; **ALK is a NEW overworld/crew currency** introduced at M06, the only thing the 7 burn
  sinks touch. The shop SURFACES the ALK balance and sells the 4 shop-relevant sink actions; it never
  lets gems buy ALK (preserves anti-P2W).
- **(B) Rebrand `coins` -> ALK.** One soft currency, deflationary, with the 7 sinks. Cleaner UX, but it
  turns today's freely-earned coins into a scarce token and forces a balance re-tune of every drop table.
This doc is written for **option A** (lowest blast radius, no re-tune). Switching to B later is a rename
+ a ledger swap behind M06's adapter, not a shop rewrite.

## 2. MASTER-PLAN ITEM -> LIVE SHOP HOME (the core mapping)
For each master-plan category: the home tab, the currency, the edge fn, the burn sink (if any), and the
build status. "LIVE" = shipping today; "WIRE" = code exists, needs hookup; "NEW" = net-new surface.

### 2.1 Skins / card alt-art / emotes / paint / board themes
- **Home:** `drip2` (Drip / "THE DROP") tab -- **LIVE** (game/drip.js, ak-cosmetics edge fn).
- **Currency:** Coins (soft) for the common tier; **Gems** for premium/seasonal drip. Ownership is
  server-side (ak-cosmetics); equipping is a LOCAL pref (`ak_skins` / `ak_drip`). drip.js already exposes
  `cardFilter(card)` + `boardFilter()` engine hooks and `equippedEmotes()`.
- **In-match cosmetic = a card alt-art swap (2D)** per the Fortnite-layer memory -- it rides drip.js
  `cardFilter`, no engine change.
- **Burn sink:** `cosmetic reroll = 50 ALK` (sink 5) -- a "reroll this cosmetic's color/variant" button in
  the Drip locker. ALK-priced (earned-only), so it is anti-P2W. Until ALK ships (M06) the reroll button is
  hidden behind a `config.ready` flag.
- **Action:** add a Gems price lane to the premium Drip rows (Drip currently reads only `gold()`/coins);
  add the ALK reroll button gated on M06.

### 2.2 Card Gear (4 slots -- the Whiteout "hero gear") -- **NEW tab**
- **Home:** a NEW `gear` tab, OR fold into the `upgrade` (Collection) card-detail. Recommend a `gear`
  sub-panel on the Collection card-detail so gear sits next to the card it modifies.
- **The 4 slots (AK_MASTER_BLUEPRINT whiteout-integration):** Frame (atk+hp), Ability Gem (spell power),
  Aura (def+hp), Finisher (crit). Two tiers: Tower Battles gear L1-5, World Raids gear L6+.
- **Currency:** Scrap (craft gear) + Coins (level gear) -- NEVER gems for raw power (anti-P2W wall,
  master-plan non-negotiable #1). Cosmetic gear *appearance* may be gem/drip.
- **Engine wiring (no combat rewrite):** gear is a stat overlay folded into the SAME perk snapshot the
  per-card tune already uses. `computePerks()` (index.html ~6634) already emits `cardTune` and
  `cardLevels` maps the engine clamps at build time. Gear adds a third map, `cardGear`, resolved with the
  **handlers_data.js `mods` pattern** (absolute/multiplier patches folded onto the card object before
  `newMatch()`). The engine clamps keep it inside the no-P2W power budget exactly like tune does.
- **Storage:** `ak_profile.gear[cardName] = {frame,gem,aura,finisher:{lvl}}`. Backfill in `ensureShape()`
  (economy.js) and `loadProfile()` (index.html) with the same never-rewrites pattern.
- **Burn sink:** none directly. Gear reroll could route the `reroll` sink later; ship without it first.
- **Status:** NEW. This is M11 (Card Gear subsystem) surfaced in the shop. Build AFTER M11's gear model.

### 2.3 Gem packs (the hard-currency choke point)
- **Home:** `gems` tab -- **LIVE** (5 packs $4.99-$99.99, Stripe via alley-kingz-shop `get-shop` +
  `verify-arcade-purchase`). Real gem-pack art auto-routes through the art-factory queue
  (assets/shop/<sku>.png) with a diamond-glyph fallback.
- **Currency:** real money in, Gems out. Everything paid routes through Gems = one refund surface, one
  auditable currency (master-plan sec 6 + legal sec 8).
- **Burn sink:** none (gems never burn).
- **Action:** none for fiat. ADD the `$BCARDD on-ramp` (`verify-bcardi-onramp` edge fn) as a parallel
  buy-gems path LATER -- legal-gated (Gate 1).

### 2.4 Building skins (hub cosmetics)
- **Home:** EXTEND the Drip tab with a "Block" sub-section, OR a Hub-side locker. Buildings live in
  M02 (BuildingBase + SpellShop/DeckLab/MainTower), so building skins are a hub-layer cosmetic.
- **Currency:** Gems / Coins (cosmetic only). The 6 Crew-Ascension visual tiers (Bronze->Crown) are
  PROGRESSION-earned, not bought (see AK_PROGRESSION_SKILLPOINTS.md) -- do not sell the ascension look.
- **Burn sink:** `building relocation = 150 ALK` (sink 4) is a HUB action, not a shop SKU, but the shop
  shows the ALK balance so the player knows they can afford to relocate.
- **Status:** NEW, gated on M02/M11 hub being walkable + having visible buildings. Reuse the drip.js
  ownership+equip rail (server owns, local equips).

### 2.5 NFT cosmetics / tradable NFT cards -- **NEW marketplace surface, legal-gated**
- **Home:** a NEW `market` surface that LINKS OUT to Tensor / Magic Eden (aggregators first, no custom
  escrow -- MASTER_BUILD_PLAN Phase 5). Owned NFTs are detected by reading the connected Phantom wallet's
  Metaplex assets and matching `Name` to canon, then marking the card `is_nft=true`.
- **Currency:** $BCARDD on-chain (Solana). In-game gems/coins/scrap NEVER buy NFTs.
- **Burn sinks (TWO fire here):**
  - `marketplace fee = 5%` (sink 6) = 2.5% burn + 2.5% to stakers. Routed by TokenSink `marketplace`
    split (the ONLY sink that splits; SINK_SPLIT marketplace = 5000bps burn / 5000bps staker).
  - `creator mint = 25 ALK` (sink 7) when a UGC card/cosmetic is minted (M09 Creator Economy, 70/25/5).
- **Legal:** Gate 1 (off-ramp), Gate 2 (no promised returns), Gate 3 (loot-box) must each be legal-signed
  BEFORE this surface ships. The Lucky Draw NEVER outputs a tradable NFT (enforced server-side, shop.js
  legal block lane "A"). Keep the loot-box lane (in-game value only) and the NFT lane strictly separate.
- **Status:** NEW + LATER. Last to ship. Build behind all three gates.

### 2.6 VIP / Passes
- **Home:** `pass2` (Alley Pass) tab -- **LIVE** (game/pass.js, ak-pass edge fn). 30 tiers, 100 XP/tier,
  free + premium lanes; premium unlock = 800 gems; tier rewards queue to ak_grants and apply via the
  shared `AKSocial.claimGrants()` rail.
- **The pass-model conflict (still OPEN, operator must lock):** PRD says Crew Pass $9.99/35d;
  MONETIZATION_UX_REWRITE says arcade-wide Master Pass $14.99/mo. RECOMMEND ship BOTH: Master Pass
  $14.99/mo (arcade-wide, the recurring-revenue backbone) + a cheap AK-only Crew Pass $4.99/season for
  AK-only players. **LOCK before any pass SKU/banner ships.**
- **Currency:** real money (Stripe sub) for the pass; 800 gems for the in-app premium unlock; **Gears**
  flow on the premium lane.
- **VIP gating** (Pixels-style) = a flag on `player_accounts.season_pass`; VIP perks = 2x gem/coin earn,
  exclusive seasonal card track, cosmetic, +1 chest slot. VIP buffs turn OFF during DvD Siege (M11).
- **Burn sink:** none.
- **Status:** LIVE (Alley Pass) + partial (Master Pass SKU needs the conflict locked + the Stripe sub).

### 2.7 Garage consumables (the distinct PvE-only lane)
- **Home:** a NEW `garage` consumables row (master plan 4.4) OR fold into the Crates tab. PvE-ONLY (never
  ranked) = not P2W. Nitro Cans (+1 start energy pre-PvE), one-shot Spells (lane EMP/repair/rage),
  XP/coin potions, decals (cosmetic, everywhere).
- **Currency:** Gems / Coins; cosmetic decals via Drip.
- **Burn sink:** none.
- **Status:** NEW, optional, low priority vs gear + pass.

## 3. THE 7 BURN SINKS -- which the SHOP touches + the event contract
Locked numbers (AK_MASTER_BLUEPRINT + MODULE_06_ECONOMY/TokenSink.js SINK_COST):

| # | Sink | ALK cost | Fires from | Shop's role |
|---|---|---|---|---|
| 1 | prestige reset | 500 | Progression / Crew Ascension | shows ALK balance (see progression spec) |
| 2 | war declaration | 200 / member | Crew layer (M04) | shows ALK balance |
| 3 | emergency shield | 100 | Raid layer (M03) | a convenience BUY surfaced in shop, fires the shield |
| 4 | building relocation | 150 | Hub layer (M02) | shows ALK balance |
| 5 | **cosmetic reroll** | 50 | **Drip tab (shop)** | shop triggers it |
| 6 | **marketplace fee** | 5% (2.5 burn + 2.5 stakers) | **NFT market (shop)** | shop triggers it |
| 7 | **creator mint** | 25 | **Creator/mint (shop, M09)** | shop triggers it |

So the SHOP directly fires sinks **5, 6, 7** and surfaces a convenience buy for **3**. Sinks 1, 2, 4 fire
from Progression/Crew/Hub but the shop is where the player tops up understanding of their ALK.

**Event contract (EventBus pub/sub, no direct imports -- the M06 law):**
- Shop emits a SINK INTENT, never debits ALK itself: `bus.emit('economy.sink.request', {sinkId, meta})`
  where meta = `{memberCount}` for war or `{saleAmount}` for marketplace.
- `CurrencyManager` validates the balance, debits ALK, emits `SINK_CONFIRMED {sinkId, amount, meta}`.
- `TokenSink.onSinkConfirmed` reads SINK_SPLIT, computes burn/staker/treasury (last portion = remainder
  to avoid rounding loss), updates totals, emits `ALK_BURNED` + (marketplace only) `STAKER_POOL_CREDITED`.
- Shop listens for `SINK_CONFIRMED` to update its header wallet + toast the outcome.
- ALK grants (login/raid/crew-chest/staking/events) emit `economy.grant {playerId, amount, source}`;
  the shop never grants ALK, it only reflects the balance from `config.ready` + CurrencyManager state.

Mock the token behind the Supabase-ledger adapter (M06) so the real ALK contract is a later swap.

## 4. ANTI-P2W + LEGAL GATE CHECKLIST (per category, enforced at review)
- **Cards & gear power:** NEVER gem-priced for raw stat power. Cards earnable free; gear crafted with
  scrap/coins. A SKU that grants a ranked stat edge is REJECTED at review (master-plan non-negotiable #1).
- **Cosmetics / drip / building skins / decals:** safe revenue, any currency.
- **Lucky Draw:** disclose exact odds on the buy screen (already in shop.js `dropRates`), in-game value
  only, NEVER outputs a tradable NFT, lane "A" enforced server-side. Geofence paid random packs where
  required; honor the still-BLANK PACK_RIP A/B/C decision before shipping paid random chests.
- **Marketplace / NFT:** Gates 1-3 legal-signed first. No cash-out, no real-money item trading for fiat.
- **Gems = the single hard choke point:** every paid thing routes through gems (one refund surface).

## 5. BUILD ORDER (smallest valuable wrap first; everything reuses live rails)
1. **Now (LIVE):** Gems, Card Shop (scrap), Lucky Draw, Crates, Collection, Alley Pass, Drip, Handlers,
   Street Code tabs already ship. No build.
2. **Step 1 -- Drip premium + Gems lane:** add a gem price lane to premium Drip rows. (Days.)
3. **Step 2 -- Master Pass SKU:** lock the pass-model conflict, add the $14.99/mo Stripe sub + $4.99
   AK Crew Pass; wire to `game_passes`. (Legal-light, pass conflict is the blocker.)
4. **Step 3 -- M06 ALK ledger (CurrencyManager + TokenSink):** finish the two stubs; emit `config.ready`
   with the cost table; wire the `economy.sink.request` -> `SINK_CONFIRMED` -> `ALK_BURNED` chain.
   Surface the ALK balance in the shop header.
5. **Step 4 -- Cosmetic reroll (sink 5) + emergency-shield convenience buy (sink 3).** (Needs Step 3.)
6. **Step 5 -- Card Gear tab:** after M11 gear model lands; fold into Collection card-detail via the
   handlers_data.js mods-resolver pattern + the `cardGear` perk map.
7. **Step 6 -- Garage consumables** (optional, PvE-only).
8. **LATER (legal-gated):** $BCARDD on-ramp (Gate 1) -> NFT marketplace + creator mint (Gates 1-3,
   sinks 6+7). Last to ship.

## 6. OPERATOR DECISIONS NEEDED
1. **Currency naming fork (sec 1):** option A (coins distinct from ALK, RECOMMENDED) vs option B
   (rebrand coins -> ALK). Everything downstream depends on this.
2. **Pass model (sec 2.6):** Master Pass $14.99/mo + AK Crew Pass $4.99/season (recommended) vs one only.
3. **PACK_RIP A/B/C:** sign the loot-box outcome model, or ship the deterministic Scrap Card Shop ONLY
   and defer paid random chests.
4. **Card gear home:** dedicated `gear` tab vs a sub-panel on the Collection card-detail (recommended).
5. **Legal counsel** engaged before live $BCARDD on-ramp + NFT marketplace (Gates 1-3).

---
*Authored for the lucrex-os-engine branch session. Grounded in a line-level read of game/shop/shop.js,
game/economy.js, game/drip.js, game/pass.js, game/handlers_data.js, and
ALLEY_KINGZ_CORE/MODULE_06_ECONOMY/TokenSink.js. No code modified -- spec only. Pairs with
AK_PROGRESSION_SKILLPOINTS.md (the SP / card-level / prestige half of the meta loop).*
