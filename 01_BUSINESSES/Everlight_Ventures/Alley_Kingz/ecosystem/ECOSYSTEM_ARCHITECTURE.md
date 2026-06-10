# ALLEY KINGZ x $BCARDD -- Ecosystem Architecture
**Date:** 2026-06-02 | **Author:** Ecosystem Economist (Hive fork) | **Status:** Design spec for operator review
**Pairs with:** `MASTER_ECOSYSTEM_PLAN_2026-06-02.md`, `BCARDI_SOLANA_RELAUNCH_SPEC_2026-06-02.md`, `MONETIZATION_UX_REWRITE.md`, `PACK_RIP_OUTCOME_MODEL.md`

> **One sentence:** One dog ($BCARDD), one currency ($BCARDD on Solana), one aesthetic (gold on vanta-black), one arcade (Everlight Arcade on vantaris) -- five pillars wired into a single closed-loop economy where the coin is the chip, the NFT is the playable card, and every sink either burns supply or funds the next player.

---

## 0. THE FIVE PILLARS AT A GLANCE

```
                        $BCARDD (Solana / pump.fun)
                    the currency AND the mascot dog
                                |
   +------------+--------------+--------------+--------------+
   |            |              |              |              |
 PILLAR 1     PILLAR 2       PILLAR 3       PILLAR 4       PILLAR 5
 THE COIN     THE GAME       THE NFTs       THE ARCADE     METAVERSE
 $BCARDD      Alley Kingz    50 dog cards   vantaris hub   (option layer)
 chip+fuel    dog crews +    = playable     blackjack +    avatars + rigs
 buyback-burn TM war rigs    on-chain stat  AK + 6 games   3D, LATER
                                            one wallet
```

The pieces already rhyme. $BCARDD is **coin mascot + card #0001 Mythic + blackjack dealer** -- the through-line. This doc specifies the *plumbing* that turns the rhyme into one economy.

**Chain assumption (Decision A, recommended in master plan): Solana-native.** The coin is Solana/pump.fun. NFTs go Metaplex Core / compressed NFTs on Solana so it is one Phantom wallet for coin + cards + chips. The EVM `.sol` contracts (`AlleyKingzCards.sol`, `AlleyKingzMarketplace.sol`, ticker `$BCRDI`) become **reference logic only** -- their 2.5%-burn + 2.5%-royalty fee model and the `CardMeta{rarity, elixirCost, breed, maxSupply}` struct port directly to a Solana program. Note the ticker fix: old EVM artifacts say `$BCRDI`; the live coin is `$BCARDD`. Canon is `$BCARDD`.

---

## 1. CORE PRINCIPLE -- TWO-LAYER MONEY (do not collapse them)

The single most important design decision: **$BCARDD never sits directly inside a casino-style game loop.** It is the *settlement layer*, not the *table-stakes layer*. This keeps the coin clean (utility, not promised return) and keeps the games legal (skill/cosmetic, not a money-out gambling desk).

| Layer | What it is | Where it lives | Cash-out? |
|---|---|---|---|
| **Settlement layer** | `$BCARDD` SPL token | Player's Phantom wallet (on-chain) | Yes -- via DEX, player-controlled, Everlight never operates the desk |
| **Table layer** | Chips (Blackjack), NOS (Alley Kingz), Gems (hard) | Supabase `game_currencies` + `player_accounts` (off-chain) | No -- in-game only, never paid out by Everlight |

A player **bridges** between layers at a one-way-priced on-ramp (buy chips/NOS with $BCARDD) and a rate-limited, fee-bearing off-ramp (redeem in-game value back to $BCARDD). The off-ramp is what makes ownership real; the gating is what keeps it from being a gambling cash-out. This is the **Option A posture from `PACK_RIP_OUTCOME_MODEL.md`** (Splinterlands/Gods Unchained model -- strongest legal footing) implemented as code: Everlight never runs a USD buy-back desk, marketplace is denominated in $BCARDD only, players self-bridge $BCARDD on a DEX.

> **LEGAL REVIEW GATE 1:** The existence of *any* in-game-value -> $BCARDD off-ramp is the line that separates "utility token" from "redeemable chip = gambling/money-transmission." Legal must sign the off-ramp design (rate limits, skill-gating, no operator-funded payout) before it ships. Default until signed: off-ramp DISABLED, on-ramp + marketplace only. See Section 7.

---

## 2. (a) $BCARDD AS THE UNIVERSAL CHIP + CURRENCY

### 2.1 The three roles of one token
$BCARDD plays three roles, all from the same wallet balance:

1. **The chip in Blackjack.** $BCARDD deals. You buy a chip stack with $BCARDD (on-ramp). Chips are off-chain table credits (`game_currencies.game_id='blackjack', currency_name='chips'`). You play skill/luck at the table in chips. Net table winnings can be redeemed back toward $BCARDD through the gated off-ramp (LEGAL GATE 1).
2. **Soft + hard currency in Alley Kingz.** $BCARDD buys NOS (soft, the in-game gold analog) and Gems (hard premium). NOS upgrades cards and enters events; Gems skip timers and buy the Crew Pass / cosmetics. Per `MONETIZATION_UX_REWRITE.md`, Gems remain the premium currency and the **Master Pass ($14.99/mo)** stays fiat-priced via Stripe -- $BCARDD is an *additional* on-ramp, not a replacement for the clean Stripe path.
3. **The buy/sell token for NFT cards.** Every marketplace listing is priced in $BCARDD. Mint, trade, and pack purchases settle in $BCARDD on-chain. This is the only place value moves purely on-chain wallet-to-wallet.

### 2.2 Conversion table (the bridge rates)
One published reference rate, set by treasury, adjusted only on a schedule (never reactively -- reactive repricing reads as manipulation):

```
ON-RAMP (always on):
  $BCARDD -> Chips        (Blackjack table credit)
  $BCARDD -> NOS          (Alley Kingz soft currency)
  $BCARDD -> Gems         (hard currency; ALSO buyable via Stripe fiat -- two doors, same Gem)

OFF-RAMP (LEGAL GATE 1; default OFF):
  Net in-game value -> $BCARDD   (rate-limited, fee-bearing, skill-gated, no operator USD)

FIAT (clean Stripe path, unchanged from MONETIZATION_UX_REWRITE):
  USD -> Gems / Master Pass / Game Pass   (verify-arcade-purchase edge function)
```

Fiat (Stripe) and crypto ($BCARDD) are **parallel doors to the same Gems/NOS/Chips balance.** A player never needs a wallet to enjoy the arcade (Stripe door), and a crypto-native player never needs a card (Phantom door). This is the FREE-FIRST-friendly, mass-market on-ramp: the existing `verify-arcade-purchase` function already mints NOS/chips/passes from Stripe; we add a parallel `verify-bcardi-onramp` function that does the same from a confirmed Solana transfer.

### 2.3 Why two doors, one balance
- Mass market (no crypto) pays USD, plays, never touches a wallet -- protects the casual funnel and the luxury UX.
- Crypto-native pays $BCARDD, creates **buy-pressure** on the token (the flywheel from the launch spec section 7).
- The token's *utility* is the moat the launch spec calls out: "almost no meme coin has a real product behind it; Rich does."

---

## 3. (b) NFT CARD = PLAYABLE CARD WITH ON-CHAIN STATS (TRUE OWNERSHIP)

### 3.1 The binding
The 50-card roster in `cards.json` ($BCARDD #0001 Mythic, HP 2600, "Crownbreaker") IS the NFT collection. The `nft_metadata_template.json` already encodes the gameplay stats as on-chain attributes:

```
attributes: Class, Breed, Name, Rarity, Role, Cost, Tags[], HP, Damage,
            Attack Speed, Move Speed, Range, Ability, Queen Target
```

On Solana (Metaplex Core), these live in the asset's on-chain attribute plugin. **The game reads stats FROM the chain, not from a private DB.** Owning the $BCARDD NFT = owning the playable Mythic card. Stats are immutable on the NFT (so a card you bought cannot be silently nerfed out from under you), but **level/upgrade state is off-chain** (a card you own can be leveled with NOS; the base stat is the floor, the upgrade multiplier sits in `player_accounts`/collection). This split is the EVM `CardMeta` struct ported: immutable base stats on-chain, mutable progression off-chain.

### 3.2 Card identity model (NFT-card vs play-card)
Not every player needs an NFT to play -- that would kill the F2P funnel and the `MONETIZATION_UX_REWRITE` luxury feel.

| Card type | How obtained | Tradeable | On-chain | Playable |
|---|---|---|---|---|
| **Play-card** (default) | Earned via PvE ladder, chests, NOS upgrade | No | No (off-chain `unlockedCardIds`) | Yes |
| **NFT-card** (collector) | Minted, pack-ripped, or bought on marketplace | Yes (in $BCARDD) | Yes (Metaplex Core) | Yes -- same stats, plus OG perks |

A play-card and an NFT-card of the same character (e.g. both are "Balboa") are gameplay-identical at base stats. The NFT adds **ownership, tradeability, scarcity, and cross-perks** (Section 5) -- never raw power. **This is the no-pay-to-win guardrail from PRD section 5.3, preserved.** NFT = flex + ownership + economy access, not a bigger sword.

### 3.3 Genesis scarcity ladder (drives floor + Seedance budget)
From `cards.json` rarity counts (48-card v1.0 roster): 4 Mythic, 1 Legendary, 9 Epic, 20 Rare, 14 Common. The EVM `AlleyKingzCards.sol` already has a **Genesis lock** (`lockGenesis()` -- "can never be minted again after lock"). Port that to Solana as a capped Genesis edition:

| Rarity | Cards | Genesis mint cap (each) | Seedance video priority |
|---|---|---|---|
| Mythic | 4 ($BCARDD, Jagged, Rosco, Crown Foxhound) | 100 | Cinematic hero clips FIRST (~1,200 credits) |
| Legendary | 1 (Stonejaw) | 500 | Hero treatment |
| Epic | 9 | 2,000 | Batch video |
| Rare | 20 | 10,000 | Short batch clips |
| Common | 14 | uncapped (compressed NFT, cents to mint) | Long-tail batch |

Genesis caps create the floor; compressed-NFT commons keep minting near-free (FREE-FIRST). After Genesis lock, new card *characters* can still ship but the Genesis edition number is fixed -- the OG badge is permanent.

---

## 4. (c) TOKEN SINKS & SOURCES -- SUSTAINABLE, NOT INFLATIONARY

The death-spiral risk (`PACK_RIP_OUTCOME_MODEL` Option B, Axie 2022) is **unbounded emission.** We avoid it by making $BCARDD **fixed-supply (1B, pump.fun standard, dev cannot mint more)** -- there is no token emission at all. In-game *soft* currency (NOS) is emitted by play, but NOS is NOT $BCARDD and never freely converts back. So the only way $BCARDD enters circulation is the bonding curve; the only way it leaves is burns. That asymmetry is the sustainability engine.

### 4.1 SOURCES of $BCARDD flowing to the ecosystem/treasury
| Source | Mechanic | Notes |
|---|---|---|
| **Creator fees** (primary) | pump.fun pays creator a slice of every trade in SOL | No sell-pressure on the token; scales with volume. Funds buyback-burn + airdrops + Rich (launch spec section 4) |
| **Treasury bag** | 3% (30M) labeled wallet | Funds airdrops, rewards, tournament prizes |
| **Marketplace fee** | 2.5% of every NFT sale (ported from `AlleyKingzMarketplace.sol` FEE_BPS=250) | Goes to **burn** |
| **Pack sales** | Players spend $BCARDD to rip packs | Spent token routes: portion burned, portion treasury |
| **On-ramp spend** | $BCARDD spent to buy chips/NOS/Gems | Token leaves player wallet -> treasury (NOT burned; backs the off-ramp reserve) |

### 4.2 SINKS that remove or lock $BCARDD
| Sink | Mechanic | Deflationary? |
|---|---|---|
| **Entry fees** | Ranked seasons, tournaments, special events cost $BCARDD to enter | Portion burned |
| **Pack rips** | Buying a pack burns a fixed % of the spend | Yes |
| **Card upgrades** | High-tier upgrades (Mythic/Legendary level-ups) cost $BCARDD on top of NOS | Yes (burned) |
| **Marketplace fee** | 2.5% per sale burned to dead address | Yes (`totalBurned` tracked, like the EVM contract) |
| **Buyback-burn** | Creator-fee SOL buys $BCARDD off-market and burns it | Yes -- the headline deflation loop (launch spec section 7) |
| **Cosmetics / dealer skins / OG badges** | Premium cosmetics priced in $BCARDD | Portion burned |

### 4.3 The closed loop (this is the whole economy in one diagram)
```
   Players trade $BCARDD  ----->  pump.fun creator fees (SOL)
          |                                  |
          | spend on packs/upgrades/         | buyback
          | entry/marketplace                v
          v                          buy $BCARDD off-market
   PARTIAL BURN  <-----------------  BURN  (supply down)
          |                                  ^
          | treasury portion                 |
          v                                  |
   TREASURY  --> airdrops + tournament prizes + reward pools
          |                                  |
          v                                  |
   players get $BCARDD back  -------> they trade/spend again (volume up -> more fees)
```

**Sustainability test:** every player action either (1) burns supply, (2) routes to treasury that funds *the next* reward, or (3) creates trade volume that generates creator fees that fund buyback-burn. No action mints new $BCARDD. NOS (the play-to-earn soft currency) is the *only* freely-earned thing, and it can never round-trip to $BCARDD without passing the rate-limited, fee-bearing, skill-gated off-ramp (LEGAL GATE 1). That single valve is what prevents the Axie spiral.

### 4.4 Numbers (illustrative, to be tuned by treasury)
- Marketplace fee: **2.5% burn + 2.5% royalty-to-treasury** (direct port of the EVM constants FEE_BPS=250, ROYALTY_BPS=250).
- Pack rip: **10% of spend burned, 20% to treasury, 70% to liquidity/reward pool.**
- Tournament entry: **50% to prize pool, 30% to treasury, 20% burned.**
- Buyback-burn cadence: **weekly**, sized to a fixed fraction of accrued creator fees (never promise an amount -- promised buybacks read as a security; see LEGAL GATE 2).

---

## 5. (d) CROSS-PERKS -- THE PILLARS REWARD EACH OTHER

The cross-perks are what make it ONE ecosystem instead of three products sharing a logo. Each pillar grants status in the others. **All perks are utility/fun/access -- never a promised financial return** (LEGAL GATE 2).

### 5.1 The cross-perk matrix
| You hold / do... | You get in... | Perk |
|---|---|---|
| **Coin: $BCARDD holder** (threshold tiers) | NFT pillar | **Whitelist** for Genesis card mints (early access, no extra cost) + airdrop eligibility |
| **Coin: $BCARDD holder** | Arcade | Holder-only Blackjack tables ($BCARDD deals VIP tables) + dealer skins |
| **NFT: card holder** | Game | **In-game perks** -- OG card frame (holo), cosmetic-only aura, profile badge, deck-slot cosmetics; NEVER stat boosts |
| **NFT: Mythic/Genesis holder** | Coin + Arcade | Top whitelist tier, priority airdrops, exclusive tournament bracket |
| **Blackjack: regular player** | Coin + brand | Meets $BCARDD (the dealer = the mascot = the coin); airdrop wave 1 targets early blackjack players (launch spec section 6, step 6) |
| **Arcade: Master Pass member** | All | 2x rewards (existing `MONETIZATION_UX_REWRITE` nudge), $BCARDD airdrop drip as a membership perk |
| **Game: ranked finisher** | Coin | Season prize pool paid from treasury in $BCARDD (skill-gated -- NOT time-gated, avoids Howey) |

### 5.2 The conversion funnel the cross-perks create
```
  Casual hits the Arcade (Stripe, no wallet)
        -> plays Blackjack, meets $BCARDD the dealer
        -> curious about the dog, finds $BCARDD (airdrop wave targets blackjack players)
        -> becomes a holder, gets NFT whitelist
        -> mints/buys a card, plays Alley Kingz with an owned card
        -> wins ranked, earns $BCARDD prize, trades on marketplace (fees burn supply)
        -> deeper holder, buys Master Pass, gets 2x + airdrop drip
        -> the whole loop tightens; each pillar feeds the next
```
This is the macro/holding-company logic: **3 surfaces (casino, card game, token) feed one compounding median** of engaged, invested users. One acquisition (a blackjack casual) is monetized across all five pillars over its lifetime.

### 5.3 Skill-gating is the legal load-bearing wall
Per `PACK_RIP_OUTCOME_MODEL` Hive pre-vote (theo_briggs: Option A; everlight_trading_risk: A first): rewards must be **skill-gated, not time-gated.** Ranked prizes reward winning, not holding-and-waiting. Staking-for-yield is OUT (that is the Howey trip-wire). "Hold to qualify for a whitelist" is access, not yield -- that is fine. "Hold to earn passive $BCARDD" is a security risk -- banned.

---

## 6. (e) HOW ALLEY KINGZ MOUNTS INSIDE EVERLIGHT ARCADE (ONE WALLET, ONE IDENTITY)

### 6.1 What exists today (do NOT rebuild)
- `vantaris/src/app/arcade/page.tsx` -- the hub. 6 live casino games (Blackjack, Crash, Dice, Mines, Plinko, Roulette) + ventures grid. Alley Kingz is listed as a venture linking to `/alley-kingz`.
- `vantaris/src/app/alley-kingz/page.tsx` -- currently a **marketing/waitlist page** (EmailCapture, "JOIN WAITLIST"). This becomes the game mount point.
- `supabase/functions/verify-arcade-purchase/index.ts` -- the Stripe verification + currency-grant engine. Already routes `nos-*` -> Alley Kingz `game_currencies`, `chips-*` -> Blackjack, `ak-game-pass`/`master-pass` -> `game_passes`. **This is the shared economy backbone.**
- Supabase tables: `player_accounts` (identity, `lives_balance`, `season_pass`, `chip_balance`), `game_currencies` (per-game per-currency balances), `game_passes`, `arcade_purchases`, `arcade_sessions`.

### 6.2 The mount -- shared identity + shared wallet
```
                 EVERLIGHT ARCADE (vantaris, Cloudflare Pages)
                              |
        +---------------------+---------------------+
        |                     |                     |
   ARCADE HUB           SHARED IDENTITY        SHARED WALLET
   /arcade              player_accounts        Phantom (Solana)
   (page.tsx)           (Supabase)             connected once
        |                     |                     |
   +----+----+----+----+      |          +----------+----------+
   |    |    |    |    |      |          |                     |
 BJ  Crash Dice ...  ALLEY KINGZ      $BCARDD balance     NFT card inventory
                     /alley-kingz     (read from chain)   (Metaplex assets)
                     (game mount)
```

**One identity:** `player_accounts.player_id` is the single account across every game. Alley Kingz reads/writes `game_currencies` (game_id='alley-kingz') and `unlockedCardIds` the same way Blackjack reads chips. No separate Alley Kingz login.

**One wallet:** the player connects ONE Phantom wallet to the arcade (not per-game). That wallet:
- holds $BCARDD (the chip/currency across all games),
- holds the NFT cards (Metaplex Core assets),
- is the on-ramp source (verify-bcardi-onramp confirms a transfer, grants chips/NOS/Gems),
- is the marketplace settlement account.
The wallet link is stored once on `player_accounts` (add column `solana_wallet`). Stripe path users have a null wallet and play fiat-only -- fully supported.

### 6.3 Concrete integration steps
1. **Replace the waitlist page** at `/alley-kingz` with the playable build (best prototype: game_v8 / Unity WebGL or the HTML prototype), or add `/play/alley-kingz` alongside the casino games and keep `/alley-kingz` as the marketing front. Recommend: marketing at `/alley-kingz`, game at `/play/alley-kingz` (matches the `/play/blackjack` pattern already in `arcade/page.tsx`).
2. **Add Alley Kingz to the GAMES grid** in `arcade/page.tsx` (move it out of VENTURES into CASINO/GAMES with status 'BETA' then 'LIVE').
3. **Extend verify-arcade-purchase** with the existing NOS slugs (already present: `nos-50/300/800`) -- no change needed, the backbone already supports Alley Kingz currency.
4. **Add `verify-bcardi-onramp` edge function** (sibling to verify-arcade-purchase): input = Solana tx signature + player_id + product slug; verifies the on-chain $BCARDD transfer to treasury; grants the same NOS/chips/Gems via the same `game_currencies` writes. One backbone, two funding doors.
5. **Add `solana_wallet` to `player_accounts`** + a wallet-connect component (shared across the arcade, not per-game).
6. **NFT-card read path:** Alley Kingz deck builder queries the connected wallet's Metaplex assets, matches `Name` attribute to `cards.json`, marks those as owned NFT-cards (tradeable + OG perks) on top of the off-chain `unlockedCardIds`.

### 6.4 Brand consistency (one aesthetic)
The arcade hub uses gold (#c9a84c) on vanta-void (#050507) with Cinzel serif. Alley Kingz currently uses orange (#ff6b35). **Per master plan + ART_BIBLE, the Everlight gold (#c9a84c / #D4AF37) on vanta-black is canonical** -- Alley Kingz keeps orange as a *faction/energy accent* but the chrome, frames, and premium surfaces use Everlight gold so it reads as one arcade. $BCARDD's war rig is "crowned matte-black, gold trim" (master plan section 5) -- the same gold ties rig -> card -> coin -> dealer.

---

## 7. (f) THE METAVERSE -- OPTION LAYER, NOT DEPENDENCY

The metaverse is the **roof, built last, and only if the foundation pays for it.** Nothing in pillars 1-4 depends on it.

### 7.1 What makes it an option, not a dependency
- The dog crews + their Twisted-Metal rigs are **already 3D-destined** (Unity ArenaAdvance project exists). The same assets that render the Seedance battle videos and the card art become metaverse avatars/vehicles later -- **zero new IP, just a new surface.**
- The $BCARDD wallet + NFT cards are **already the identity + inventory layer** a metaverse would need. A metaverse mount is "render the assets the player already owns in 3D space" -- additive, not foundational.
- If the metaverse never ships, the economy is complete: coin + game + NFT + arcade is a full closed loop.

### 7.2 Phased option ladder
```
NOW:       coin + 4 Mythic Seedance hero videos (teaser/NFT preview)
30-60d:    canon-merge cards.json, Solana NFT Genesis mint, AK playable in arcade w/ NFT binding
60-120d:   full 50-card video set (phased), marketplace live, $BCARDD as chip across BJ + AK
LATER:     Unity mobile release, treasury-funded tournaments
OPTION:    metaverse -- avatars + rigs as 3D assets, same wallet/NFT/$BCARDD identity
```

The metaverse is a Phase-N toggle. Build the startup now; the metaverse is upside, never a prerequisite.

---

## 8. LEGAL GUARDRAILS -- WHERE THE LEGAL TEAM MUST REVIEW

The guardrail from the launch spec is absolute: **market as utility + fun, NEVER as an investment with promised returns.** NFTs + a coin + gameplay utility raise the "is this a security / is this gambling / is this money transmission" question higher than a pure meme coin. Three named gates require legal sign-off before the relevant surface ships:

| Gate | Trigger | Risk | Default until signed |
|---|---|---|---|
| **LEGAL GATE 1 -- the off-ramp** | Any in-game-value -> $BCARDD redemption | Redeemable chip = gambling cash-out + money transmission (state MTLs). This is the `PACK_RIP_OUTCOME_MODEL` Option-C trap. | Off-ramp DISABLED. On-ramp + $BCARDD-only marketplace + skill-gated prizes only (Option A posture). |
| **LEGAL GATE 2 -- promised returns** | Buyback-burn cadence, staking, "hold to earn", any yield language | Howey-test security. Promised buybacks/yield = investment contract. | No promised amounts. Buyback is discretionary treasury action, never a guarantee. No staking-for-yield. Hold-for-whitelist = access (OK), hold-for-yield = banned. |
| **LEGAL GATE 3 -- loot-box / pack rips** | Paid packs with random tradeable-value outcomes | Loot-box gambling rules (state-by-state). | Geofence WA, MN, HI (per `PACK_RIP_OUTCOME_MODEL` section "On execution lock"). Disclose odds. Packs in $BCARDD or fiat for game cards (Option A). KYC trigger over a spend threshold TBD by legal. |

**Additional standing guardrails (already doctrine):**
- Disclaimer on every surface: *"$BCARDD is a community meme coin inspired by $BCARDD the dog. Not affiliated with $BCARDD Limited."* + *"In-game items and tokens are for entertainment and utility, not investments. No promised returns."*
- AI never touches keys or signs on-chain (launch spec section 9). All on-chain actions are Rich's.
- Rewards skill-gated, not time-gated (avoids Howey).
- Everlight never operates a USD cash-out desk (the Option-C money-transmitter trap is permanently off the table).

**Recommended default to ship clean (operator decision):** Launch on **Option A (Pure Utility + Cosmetic)** posture from `PACK_RIP_OUTCOME_MODEL` -- strongest legal footing, ~14 days to clean, no off-ramp desk, marketplace in $BCARDD only. Evolve toward a gated off-ramp in season 2 *only* after legal signs Gate 1 and the token has trade-history depth (matches the everlight_trading_risk pre-vote: "A first, B in season 2").

---

## 9. CANONICAL ECONOMY SCHEMA (the deliverable)

### 9.1 Entities
```
TOKEN
  $BCARDD (SPL, Solana, fixed 1,000,000,000, pump.fun, dev cannot mint more)
    - founder bag 9% (locked/vested 3-6mo)
    - treasury 3% (labeled wallet)
    - creator-fee faucet (SOL, off bonding curve / PumpSwap)

WALLET (one per player, optional)
  Phantom (Solana)
    - holds $BCARDD
    - holds NFT cards (Metaplex Core assets)
    - linked to player_accounts.solana_wallet (nullable -- fiat users have none)

NFT CARD (Metaplex Core asset)
  on-chain immutable: { name, breed, class, rarity, role, cost, tags[],
                        hp, damage, attack_speed, move_speed, range,
                        ability{name,desc,cooldown}, queen_target,
                        genesis_edition_number }
  off-chain mutable (player_accounts/collection): { level, upgrade_multiplier, xp }
  binds 1:1 by `name` to cards.json roster ($BCARDD #0001 ... 48-card v1.0)

OFF-CHAIN BALANCES (Supabase)
  player_accounts { player_id, display_name, auth_provider, solana_wallet (NEW),
                    lives_balance, chip_balance, season_pass, nos? ... }
  game_currencies { player_id, game_id, currency_name, balance, updated_at }
    - (alley-kingz, 'nos')   soft currency
    - (alley-kingz, 'gems')  hard currency (also Stripe)
    - (blackjack,   'chips') table credit
  game_passes { player_id, pass_type, game_id, stripe_subscription_id, active }
  arcade_purchases { session_id, player_id, slug, product_type, amount_total, currency }
```

### 9.2 Value flows (directed edges)
```
FIAT door:    USD --Stripe--> verify-arcade-purchase --> game_currencies (NOS/chips/gems) | game_passes
CRYPTO door:  $BCARDD --on-chain transfer--> verify-bcardi-onramp --> game_currencies (same writes)
MARKETPLACE:  $BCARDD --listing/sale--> 2.5% burn + 2.5% treasury + 95% seller  (on-chain)
PACK RIP:     $BCARDD --pack--> 10% burn + 20% treasury + 70% pool --> random NFT card (on-chain mint)
UPGRADE:      NOS (+ $BCARDD for high tiers) --> card level up (off-chain progression; $BCARDD portion burned)
ENTRY:        $BCARDD --tournament/ranked entry--> 50% prize pool + 30% treasury + 20% burn
PRIZE:        treasury --skill-gated win--> $BCARDD to player wallet  (NOT time-gated)
BUYBACK-BURN: creator fees (SOL) --weekly discretionary--> buy $BCARDD off-market --> burn
OFF-RAMP:     [LEGAL GATE 1 -- DEFAULT OFF] net in-game value --rate-limited, fee, skill-gated--> $BCARDD
```

### 9.3 Sink/source balance sheet (sustainability proof)
```
SOURCES (into ecosystem):  creator fees (SOL, no token sell-pressure)
                           treasury bag (fixed 3%, no new mint)
                           player on-ramp spend (token to treasury, backs reserve)
SINKS (out of supply):     marketplace burn, pack-rip burn, upgrade burn,
                           entry burn, weekly buyback-burn
EMISSION (new $BCARDD):    NONE (fixed supply -- the anti-spiral)
FREE-EARNED (soft only):   NOS via play  ->  cannot round-trip without LEGAL GATE 1 valve
NET:                       supply trends DOWN (burns) ; treasury funds rewards ;
                           volume funds buyback ; no inflation path exists
```

### 9.4 Pillar -> economy mapping (one-line each)
```
PILLAR 1 COIN     : $BCARDD = settlement layer + mascot. Fixed supply. Creator fees fund buyback-burn + treasury.
PILLAR 2 GAME     : Alley Kingz. Skill loop. NOS soft / Gems hard. NFT-cards optional, cosmetic-perk only (no P2W).
PILLAR 3 NFT      : 50 dog cards, Metaplex, on-chain stats = playable card. Genesis caps = scarcity. 2.5% burn marketplace.
PILLAR 4 ARCADE   : vantaris hub. One identity (player_accounts), one wallet (Phantom). Two funding doors (Stripe + $BCARDD).
PILLAR 5 METAVERSE: option layer. Same assets/wallet/NFT/identity rendered in 3D. Built last, never a dependency.
```

---

## 10. OPERATOR DECISIONS SURFACED (with recommended defaults)

1. **Legal posture (gates Sections 1, 8):** Ship Option A (Pure Utility/Cosmetic, no off-ramp desk, $BCARDD-only marketplace). **RECOMMEND: A.** Evolve to gated off-ramp in season 2 only after Legal Gate 1 sign-off + token trade-history depth.
2. **Chain (gates everything):** Solana-native NFTs (Metaplex Core / compressed). **RECOMMEND: Solana** -- one wallet for coin + cards + chips; EVM `.sol` files kept as reference logic only. (Decision A in master plan.)
3. **Off-ramp:** Default OFF until Legal Gate 1. **RECOMMEND: keep OFF for launch.**
4. **NFT requirement to play:** NFT optional; play-cards remain F2P-earnable. **RECOMMEND: optional** (protects funnel + luxury UX + no-P2W).
5. **AK mount path:** `/play/alley-kingz` game + `/alley-kingz` marketing. **RECOMMEND: split** (matches existing `/play/blackjack` pattern).
6. **Buyback-burn cadence:** Weekly, discretionary, never a promised amount (Legal Gate 2). **RECOMMEND: weekly discretionary.**

---

## 11. FREE-FIRST NOTES

- **Reuse, do not rebuild:** verify-arcade-purchase backbone, `player_accounts`/`game_currencies` schema, the arcade hub, the Stripe catalog, the EVM contract fee logic (port, do not redesign), the Unity/HTML prototypes, the cards.json roster, the Seedance pipeline.
- **Free/cheap rails:** Solana compressed NFTs (cents to mint thousands of commons), Cloudflare Pages (site already there), e5-mother/AceMagician for heavy renders (phone proot cannot build Unity or render video).
- **Only real spend:** Seedance credits (phase Mythic-first per master plan) + the $BCARDD dev-buy (already planned). Everything else uses existing infra. The new build is one edge function (`verify-bcardi-onramp`), one DB column (`solana_wallet`), and the Solana NFT program (port of the `.sol` logic) -- all on infra that already exists.

---

*Compiled 2026-06-02 from the live Alley Kingz specs (PRD_V2, 05_DATA_MODEL, PACK_RIP_OUTCOME_MODEL, MONETIZATION_UX_REWRITE), the vantaris arcade + verify-arcade-purchase backbone, the EVM contracts (AlleyKingzCards/Marketplace), the nft_metadata_template, the cards.json roster ($BCARDD #0001), and the $BCARDD Solana relaunch spec. Pairs with MASTER_ECOSYSTEM_PLAN_2026-06-02.md. Next: operator resolves Section 10 decisions, then the Phase 1-9 Hive workflow builds it.*
