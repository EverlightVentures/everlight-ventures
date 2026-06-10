# Alley Kingz -- META-GAME BUILD PLAN (the Clash-Royale layer on top of the combat prototype)

**Date:** 2026-06-03
**Author:** Lucrex (Hive deep-dive)
**Status:** Planning only. NO game code touched (index.html / engine.js / canon.js left as-is).
**Pairs with:** `spec/PRD_V2.md`, `spec/05_DATA_MODEL.md`, `spec/PACK_RIP_OUTCOME_MODEL.md`,
`MONETIZATION_UX_REWRITE.md`, `ecosystem/ECOSYSTEM_ARCHITECTURE.md`, `ecosystem/MASTER_BUILD_PLAN.md`,
`ecosystem/GAP_AUDIT.md`.

> **What this doc is.** The GAP_AUDIT proved the live build is a single-match combat prototype.
> This doc specifies the META-GAME -- the loop that wraps the fight (PRD_V2 Section 1.0:
> `Login -> Daily Rewards -> Pick Deck -> Battle -> Post-match (NOS +/-) -> Chest -> Upgrade -> Repeat`).
> Six systems. For each: what it is, the data model, which EXISTING infra it reuses, the build
> steps, and an honest day/week/multi-week effort call.

> **What this doc is NOT.** It is not a green-light to rebuild backend. Everything below reuses
> infra the operator already owns: Supabase (`https://jdqqmsmwmbsnlnstyavl.supabase.co` -- accounts,
> cloud save, DB), Stripe (live, the arcade shop), Google OAuth, the $BCARDD Solana coin + the
> Metaplex NFT pipeline, and the vantaris site (Next.js / Cloudflare Pages, has an `/auth` page +
> Supabase edge functions). Per ECOSYSTEM_ARCHITECTURE section 6.1, `player_accounts`,
> `game_currencies`, `game_passes`, `arcade_purchases`, `arcade_sessions` already exist and already
> route `nos-*` to Alley Kingz. We extend, we do not invent.

> **One honesty rule up front.** Accounts + cloud save + card levels + a PvE ladder is a
> THIS-WEEK build done responsibly (it is mostly schema + read/write glue on infra that exists).
> Shop/Stripe and especially real-time ranked PvP are LATER. Real-money payments and NFT/coin
> tie-in cross a compliance line (ECOSYSTEM_ARCHITECTURE section 8, three legal gates) and are NOT
> a same-day build. The fastest responsible path is: ship the free combat toy TODAY with zero
> backend, then add the spine (accounts + levels + ladder) over the week.

---

## 0. THE ENGINE CONTRACT (what the client already gives us to build on)

Two facts from a line-level read of `engine.js` decide most of the design below, so they lead:

1. **The engine reads base stats off the canon card object.** `Unit` constructor (engine.js
   ~line 301-303) sets `this.maxHp = card.hp; this.dmg = card.dmg; this.range = card.range;
   this.atkSpd = card.atkSpd`. The card object is built from `cards.json` (the 48-card canon SoT --
   confirmed dict of `meta` + `cards`, rarities Mythic 4 / Legendary 1 / Epic 9 / Rare 20 /
   Common 14). **This means card levels are a pure multiply-at-build-time: feed the engine
   `card.hp * levelMult(level)` instead of raw `card.hp`. No combat-loop rewrite -- one
   transform on the card object before `newMatch()`.** (See System 1.)
2. **Difficulty is already a 0-9 dial keyed to the ladder.** `engine.js` line 272 declares
   `let DIFFICULTY = 0; // 0=easy (The Lot) ... 9=hardest (Empire State)` and exposes
   `AK.setDifficulty(n)` (line 921, clamps 0-9). The 10 PRD arenas (PRD_V2 4.2) map 1:1 to
   difficulty 0-9. **The PvE ladder is "pick an arena -> call setDifficulty(arenaIndex) -> start a
   match." The hard part (scaling AI) is already in the engine.** (See System 5.)

Everything in this plan sits ABOVE the engine. We never touch the combat loop; we wrap it.

---

## SYSTEM 1 -- CARD LEVELS + UPGRADE ECONOMY (the Clash model)

### What it is
Every owned card has a level 1-10. Leveling needs N duplicate copies of that card PLUS Fuel (the
soft currency, PRD_V2 5.1). Higher level = higher base stats. This is the core retention sink: it
gives daily play a destination (collect dupes, bank Fuel, level up) and it is the reason chests and
the shop matter. It maps directly to PRD_V2 2.2 (`upgradeMultiplier`) and the spec-only
`game/UPGRADE_SPEC.md`.

### The proposed multiplier (the number this doc commits to)
**+10% per level on HP and DMG, applied linearly off the canon base, compounding-free for
predictability.** This matches PRD_V2 2.2 default (`upgradeMultiplier: 1.10`) and 05_DATA_MODEL
(`upgradeMultiplier // Default 1.10 (10% per level)`).

```
levelMult(L) = 1 + 0.10 * (L - 1)        // L1 = 1.00x, L10 = 1.90x
hp(card,L)   = round(card.hp  * levelMult(L))
dmg(card,L)  = round(card.dmg * levelMult(L))
```

- **Why linear, not compounding:** a compounding 1.10^9 = 2.36x makes a maxed common outclass a
  base mythic, which breaks the no-pay-to-win posture (PRD_V2 5.3, ECOSYSTEM_ARCHITECTURE 3.2/5.3).
  Linear caps a level-10 card at 1.90x base -- meaningful progress, not a power cliff.
- **Only HP and DMG scale.** Speed, range, attack-speed, and ability values stay at canon base
  (they are balance-load-bearing and the engine reads them straight). This keeps the level system a
  stat-bump, not a behavior change.
- **Engine integration (no combat rewrite):** in the client, before `newMatch()`, transform each
  deck card: `{...CARDS[name], hp: hp(c,lvl), dmg: dmg(c,lvl)}`. The engine consumes it unchanged
  (per System 0, fact 1). This is the entire wiring.

### Sample cost curve (per rarity)
Cost to go FROM level L to L+1 = `dupesNeeded` copies + `fuelCost` Fuel. Rarer cards need fewer
dupes (you get fewer of them) but more Fuel per dupe. Illustrative, tune in `UPGRADE_SPEC.md`:

| Level-up | Common dupes / Fuel | Rare dupes / Fuel | Epic dupes / Fuel | Legendary dupes / Fuel | Mythic dupes / Fuel |
|---|---|---|---|---|---|
| 1->2 | 2 / 5 | 1 / 50 | 1 / 400 | 1 / 4,000 | 1 / 20,000 |
| 2->3 | 4 / 20 | 2 / 150 | 1 / 800 | -- | -- |
| 3->4 | 10 / 50 | 4 / 400 | 2 / 2,000 | 1 / 8,000 | -- |
| 4->5 | 20 / 150 | 10 / 1,000 | 4 / 4,000 | -- | 1 / 50,000 |
| 5->6 | 50 / 400 | 20 / 2,000 | 10 / 8,000 | 2 / 20,000 | -- |
| 6->7 | 100 / 1,000 | 50 / 4,000 | 20 / 15,000 | -- | -- |
| 7->8 | 200 / 2,000 | 100 / 8,000 | 40 / 30,000 | 4 / 50,000 | 1 / 100,000 |
| 8->9 | 400 / 4,000 | 200 / 15,000 | 80 / 60,000 | -- | -- |
| 9->10 | 800 / 8,000 | 400 / 30,000 | 160 / 120,000 | 8 / 150,000 | 1 / 250,000 |

Reading it: commons flood in and cap cheap; mythics ($BCARDD etc.) are a long grind by design
(scarcity = the NFT floor story, ECOSYSTEM_ARCHITECTURE 3.3). Legendary/Mythic skip some bands
(blank cells) because their dupe drip is slow -- you spend more Fuel per level instead.

### Collection model
A player owns a card the moment they get one copy (it becomes playable at level 1). Extra copies
bank toward the next level. Un-owned cards show as silhouettes. This is the `unlockedCardIds` +
per-card `{level, dupeCount, fuelInvested}` map -- see System 2's `player_cards` table.

### Effort: **THIS WEEK (1-2 days).**
The math is a one-line transform; the engine already reads base stats. The real work is the data
model (System 2) and a minimal collection/upgrade UI. No new infra. The honest risk is balance
tuning (the cost curve above is a first draft, not playtested).

---

## SYSTEM 2 -- ACCOUNTS + CLOUD SAVE (Google OAuth via Supabase Auth)

### What it is
A persistent player identity so the collection, levels, NOS, currencies, and decks survive a
reload and follow the player across devices (PRD_V2 7.1/7.2). Today there is ZERO persistence
(GAP_AUDIT section 4: "state resets every reload"). This is the keystone -- card levels (System 1)
and the ladder (System 5) are meaningless without somewhere to save them.

### Existing infra it reuses (do NOT rebuild)
- **Supabase Auth with the Google provider** -- the vantaris site already has an `/auth` page.
  Alley Kingz reuses the SAME Supabase project and the SAME Google OAuth client. No new auth stack.
- **`player_accounts`** already exists (ECOSYSTEM_ARCHITECTURE 6.1: `player_id`, `display_name`,
  `auth_provider`, `chip_balance`, `season_pass`, plus the planned `solana_wallet` column). One
  identity across every arcade game -- Alley Kingz does NOT get its own login.
- **`game_currencies`** already routes `(game_id='alley-kingz', currency_name='nos')`.

### What persists (the player-state contract, from 05_DATA_MODEL PlayerData)
collection (owned cards), per-card levels + dupe counts, NOS bottles + highest NOS, current
arena/league, the three currencies (Fuel/Gears/Gems), the active deck(s), highest PvE level
completed + district-challenge flags, and settings.

### Supabase tables (extend the existing schema; new tables prefixed for the game)
- **`players`** (or reuse `player_accounts` directly): `player_id` (PK, = Supabase auth uid),
  `display_name`, `auth_provider`, `nos_bottles`, `highest_nos`, `current_arena`, `current_league`,
  `fuel`, `gears`, `gems`, `highest_level_completed`, `ranked_unlocked`, `created_at`, `last_seen`.
  Prefer adding the AK-specific columns to `player_accounts` so it stays one identity.
- **`player_cards`**: `id`, `player_id` (FK), `card_id` (= cards.json `name`/`cardNumber`),
  `level` (1-10, default 1), `dupe_count`, `fuel_invested`, `is_nft` (bool -- true if matched from
  the wallet's Metaplex assets, ECOSYSTEM_ARCHITECTURE 6.3 step 6), `acquired_at`. One row per owned
  card.
- **`decks`**: `id`, `player_id` (FK), `slot` (0-4, or 0-7 with the pass), `name`, `card_ids`
  (jsonb array of 8), `is_selected`. PRD_V2 6.3 (5 slots default, 8 with the pass).
- **`transactions`**: `id`, `player_id` (FK), `kind` (`upgrade` | `chest` | `purchase` | `reward` |
  `match_result`), `delta` (jsonb -- what currencies/cards/NOS changed), `source`, `created_at`.
  This is the audit log AND the anti-cheat trail.

### Anti-cheat note (honest)
For UNRANKED PvE and the local collection, client-authoritative writes are acceptable (a player
cheating their own single-player save hurts no one). For RANKED PvP and anything that touches real
money or NFT value, writes MUST be server-authoritative: a Supabase RLS policy + an edge function
(sibling to `verify-arcade-purchase`) validates the match outcome and the currency delta server-side
before committing. Do NOT let the client POST "I won, give me 30 NOS" unverified once ranked or
payments are live. This is flagged here, built in System 6.

### Effort: **THIS WEEK (2-3 days).**
Auth itself is near-free (Supabase Google provider + existing `/auth`). The work is the schema
migration (`supabase/migrations/`), the load-on-login / save-on-session-end glue, conflict
resolution (PRD_V2 7.2: higher NOS wins), and RLS policies. Honest caveat: **this is the line where
"same-day" stops being responsible.** Account systems touch PII and become the source of truth for
everything else -- they get a migration, RLS, and a tested save/restore path, not a Friday-afternoon
hack.

---

## SYSTEM 3 -- ECONOMY + SHOP + STRIPE

### What it is
The three-currency economy (PRD_V2 5.1) and the store that sells the hard currency and passes for
real money (PRD_V2 5.2), plus the $BCARDD / NFT crypto door (ECOSYSTEM_ARCHITECTURE 2-6).

### The three currencies (PRD_V2 5.1) and what each buys
| Currency | Type | Earned from | Spent on |
|---|---|---|---|
| **Fuel** | soft | wins, dailies, chests | card upgrades (System 1), shop soft offers |
| **Gears** | mid / season | season pass, events | premium cards, exclusive skins |
| **Gems** | hard / IAP | real money (Stripe) OR $BCARDD on-ramp | chest skips, the pass, the cosmetics shop |

### The Stripe products (reuse the live arcade backbone)
ECOSYSTEM_ARCHITECTURE 6.1 confirms `verify-arcade-purchase` (the Stripe verify + currency-grant
edge function) already routes `nos-*` -> Alley Kingz currency and `master-pass` -> `game_passes`.
We add product SKUs, not a new payment system:
- **Gem packs** -- $0.99 / $4.99 / $19.99 / $49.99 / $99.99 (PRD_V2 5.2 #2). Stripe SKU
  `gems-NN` -> webhook -> `verify-arcade-purchase` -> grant Gems to `game_currencies`.
- **Crew Pass** -- PRD_V2 5.2 #1 says **$9.99 / 35 days**; MONETIZATION_UX_REWRITE supersedes that
  with an arcade-wide **Master Pass $14.99/mo** (+ optional Alley Kingz Pass $4.99/mo).
  **CONFLICT -- operator must lock ONE before any pass SKU or banner ships** (also flagged in
  GAP_AUDIT section 3). Recommend the arcade-wide Master Pass so one subscription covers every
  arcade game (matches the one-identity model).
- **Starter Pack** -- $4.99 one-time (PRD_V2 5.2 #4): gems + Fuel + a Legendary chest. Stripe SKU,
  `isOneTimePurchase` flag on `arcade_purchases`.
- **Revival Pack** -- $2.99, fires on a 5-loss streak (PRD_V2 5.2 #3). Triggered by a streak counter
  in `player_accounts`, sold via the same Stripe path.

The webhook flow already exists: **Stripe charge -> `verify-arcade-purchase` edge function ->
grant Gems/Fuel/pass via `game_currencies` / `game_passes` writes.** We register SKUs and wire the
shop UI; we do not build a payment processor.

### F2P cosmetics-only guardrail (PRD_V2 5.3)
All CARDS are earnable via play. Real money buys ONLY cosmetics (rig skins, arena themes, emotes),
convenience (chest skips), and the pass reward track -- never raw power. This is the same no-P2W
wall as the NFT layer (ECOSYSTEM_ARCHITECTURE 3.2). Encode it as a hard rule in the shop: a SKU that
grants a stat advantage is rejected at review.

### $BCARDD + NFT marketplace tie-in (the crypto door)
Per ECOSYSTEM_ARCHITECTURE 2.2/6.2, $BCARDD is a PARALLEL on-ramp to the SAME Gems/Fuel balance:
add a `verify-bcardi-onramp` edge function (sibling to `verify-arcade-purchase`) that confirms a
Solana $BCARDD transfer and grants the same currency. NFT cards are bought/sold on
**Tensor / Magic Eden** in $BCARDD (MASTER_BUILD_PLAN Phase 5: aggregators first, no custom escrow).
A player never NEEDS a wallet (Stripe door fully supports fiat-only play).

### Legal note (non-negotiable, ECOSYSTEM_ARCHITECTURE section 8)
Real money + (later) NFT/coin raises the compliance bar. Three gates need legal sign-off before the
relevant surface ships: **Gate 1** (off-ramp = gambling/money-transmission, DEFAULT OFF),
**Gate 2** (promised returns = Howey security -- no "hold to earn"), **Gate 3** (loot-box/pack-rips
-- geofence WA/MN/HI, disclose odds, PACK_RIP_OUTCOME_MODEL). **Loop legal in BEFORE live payments
and BEFORE the marketplace.** Also note PACK_RIP_OUTCOME_MODEL's A/B/C operator decision is still
BLANK -- do not ship paid random packs until it is signed.

### Effort: **LATER (multi-week, gated by legal).**
The Stripe backbone exists, so the SHOP UI + SKU wiring is ~3-4 days of build. But responsibly it is
multi-week because: (a) the Crew-vs-Master pass conflict must be resolved first, (b) live payments
need legal sign-off + the eradication/compliance posture, (c) the $BCARDD/NFT door is gated behind
all three legal gates. **Payments are explicitly NOT a same-day build.**

---

## SYSTEM 4 -- PLAYER PROFILE + MARKETPLACE

### What it is
The screen that shows who the player is (PRD_V2 -- the meta hub the GAP_AUDIT lists as MISSING) and
the surfaces where they acquire cards/currency.

### Profile screen (reads from System 2 tables)
- **NOS bottle count** + the canister icon (PRD_V2 4.1; the icon is a flagged MISSING asset in
  GAP_AUDIT section 3).
- **League badge** (Bronze Crew -> ... -> Alley King, PRD_V2 4.3 -- 7 badges, MISSING art).
- **Collection grid** -- owned cards with level + dupe progress bars; silhouettes for un-owned.
- **Stats** -- wins/losses, 3-crown count, highest NOS, highest PvE level, favorite card.
- Currency balances (Fuel/Gears/Gems) in the header.

### Where to buy (the acquisition surfaces)
- **Shop packs** (System 3) -- spend Fuel/Gems on chests and card bundles in-game.
- **Currency purchase** -- Gem packs / passes via Stripe (System 3 fiat door) OR $BCARDD on-ramp
  (crypto door).
- **NFT marketplace** -- buy/sell collectible NFT cards on **Tensor / Magic Eden** in $BCARDD
  (MASTER_BUILD_PLAN Phase 5; ECOSYSTEM_ARCHITECTURE 3.2). The profile links out to the listing;
  owned NFTs are detected by querying the connected Phantom wallet's Metaplex assets and matching
  `Name` to cards.json (ECOSYSTEM_ARCHITECTURE 6.3 step 6), then marked `is_nft=true` in
  `player_cards`.

### Effort: **THIS WEEK for the profile read-view (1-2 days); LATER for the marketplace link.**
The profile is a read-only render of System 2 data -- cheap once accounts exist. The marketplace
link is trivial UI but its CONTENT (live NFT cards) depends on the entire Phase 3 mint
(MASTER_BUILD_PLAN) and is gated by Legal Gate 3 -- so it lands in the LATER bucket.

---

## SYSTEM 5 -- PvE ARENA LADDER

### What it is
Progression through the 10 NOS-Bottle arenas (PRD_V2 4.2: The Lot 0 -> Empire State 5000+), where
each arena is a harder AI and better rewards. This is the single-player spine that gives the combat
prototype a REASON to keep playing, and it is the cheapest meta-system to build because the engine
already does the hard part.

### How it wires to the engine (System 0, fact 2)
`engine.js` already exposes `AK.setDifficulty(0-9)` keyed to "The Lot ... Empire State." Map each
arena's NOS threshold to its difficulty index and call it before the match:

| Arena (PRD_V2 4.2) | NOS threshold | `setDifficulty()` |
|---|---|---|
| The Lot | 0 | 0 |
| Strip Run | 400 | 1 |
| Parking Structure | 800 | 2 |
| The Blocks | 1200 | 3 |
| Interchange | 1600 | 4 |
| The Yard | 2000 | 5 |
| Neon District | 2600 | 6 |
| Embassy Row | 3200 | 7 |
| The Penthouse | 4400 | 8 |
| Empire State | 5000+ | 9 |

The player's current arena is derived from their NOS count (System 2). Win -> NOS up -> climb;
lose -> NOS down (floored at the arena threshold, PRD_V2 4.1 "NOS floor"). The board art also swaps
per arena (GAP_AUDIT section 1 -- only `arena_a_neon_night` is wired today; The Lot art does not yet
exist and must be generated).

> **Note on the two ladders.** PRD_V2 has BOTH a 100-level PvE map (Section 3, with its own
> `level_scale` algorithm) AND a 10-arena NOS ladder (Section 4). They are different things: the
> 100-level map is a story/campaign; the NOS ladder is the trophy road. The engine's 0-9 dial maps
> cleanly to the 10 ARENAS. Recommend shipping the 10-arena ladder FIRST (it is the `setDifficulty`
> wiring, near-free) and treating the 100-level campaign map as a LATER expansion.

### Rewards per arena
First-clear of an arena grants a Fuel lump + a chest + (per PRD_V2 3.2 unlock logic) a card unlock.
Repeat wins grant Fuel + NOS. Rewards scale up by arena tier. Stored as `match_result`
transactions (System 2).

### Effort: **THIS WEEK (1-2 days), minus art.**
The difficulty scaling is DONE in the engine. The build is: derive arena from NOS, a level-select /
ladder UI, wire `setDifficulty(arenaIndex)`, apply NOS delta on result (GAP_AUDIT already lists the
cosmetic NOS delta as a 1-day Bucket-A item), and grant rewards. The honest blocker is ART, not
code: The Lot arena + several arena boards + 7 league badges + the NOS icon are all MISSING
(GAP_AUDIT sections 1, 3) and need the Leonardo pipeline.

---

## SYSTEM 6 -- RANKED PvP (the heaviest piece, last)

### What it is
Real-time human-vs-human matches where you only face players inside your own NOS/league bracket
(the trophy road), with the outcome validated server-side so trophies and (later) prizes can not be
faked. PRD_V2 line 11 lists this in the MVP; GAP_AUDIT section 4 confirms it is entirely MISSING
(today's AI is a scripted single opponent, `engine.js updateAI`).

### What it needs (and why it is hard)
1. **Matchmaking** -- a queue that pairs players within a NOS band (e.g. +/- 200 NOS). Doable on
   Supabase Realtime / a lightweight matchmaking edge function.
2. **Real-time netcode** -- this is the genuinely heavy part. The current engine is a local
   single-client simulation. Real-time PvP needs either (a) lockstep deterministic simulation with
   input sync, or (b) a server-authoritative simulation both clients render. Either is a
   multi-week-to-multi-month engineering effort with its own server, and it is the #1 source of
   cheating risk if done naively. Honest call: **this is a rewrite of how the match runs, not a
   wrapper around it.**
3. **Server-authoritative validation** (System 2 anti-cheat) -- the server, not the client, owns the
   match result and the NOS/currency delta. Required the moment trophies (or money/NFT prizes) ride
   on the outcome. Skill-gated prizes only, never time-gated (ECOSYSTEM_ARCHITECTURE 5.3, Howey).

### Effort: **LATER (multi-week to multi-month). The last phase.**
Honest framing: ranked PvP is heavier than every other system in this doc COMBINED. It needs a
dedicated authoritative game server, netcode the prototype does not have, and the anti-cheat spine.
Ship single-player (the PvE ladder, System 5) first, validate the loop is fun, THEN invest in
netcode. Do not let "ranked is in the PRD" pull it forward -- it is correctly the final phase.

---

## EFFORT SUMMARY (honest, at a glance)

| System | Bucket | Effort | Gating dependency |
|---|---|---|---|
| 1. Card levels + upgrade | THIS WEEK | 1-2 days | needs accounts (System 2) to persist |
| 2. Accounts + cloud save | THIS WEEK | 2-3 days | the keystone; nothing else persists without it |
| 5. PvE arena ladder | THIS WEEK | 1-2 days (code) | needs arena ART (Leonardo, GAP_AUDIT) |
| 4. Player profile | THIS WEEK | 1-2 days | read-view of System 2 |
| 3. Economy + shop + Stripe | LATER | ~3-4 days build, multi-week responsibly | legal gates + pass conflict |
| 4b. NFT marketplace link | LATER | trivial UI | the entire Phase-3 mint + Legal Gate 3 |
| 6. Ranked PvP | LATER (last) | multi-week to multi-month | netcode + authoritative server |

---

## INFRA REUSE MAP (per phase -- nothing is rebuilt)

| Build phase | Reuses (already owned) | Net-new (small) |
|---|---|---|
| Combat prototype to web (TODAY) | static `index.html/engine.js/canon.js`, Cloudflare Pages, vantaris `/play/*` pattern | none |
| Accounts + cloud save | Supabase Auth (Google provider), existing `/auth` page, `player_accounts` | `player_cards`/`decks`/`transactions` migration, RLS, load/save glue |
| Card levels | engine reading `card.hp/dmg` (System 0), `player_cards` | one `levelMult()` transform + upgrade UI |
| PvE ladder | `AK.setDifficulty(0-9)`, the 3 existing arena renders | The Lot art (Leonardo), ladder UI, NOS delta |
| Player profile | System 2 tables | profile screen |
| Shop + Stripe | `verify-arcade-purchase` edge fn, Stripe live, `game_currencies`/`game_passes` | new SKUs, shop UI, `verify-bcardi-onramp` |
| NFT marketplace | $BCARDD coin, Metaplex pipeline, Tensor/Magic Eden | wallet-connect, Metaplex asset read |
| Ranked PvP | Supabase Realtime (matchmaking) | authoritative game server + netcode (the big lift) |

---

## PHASED ROADMAP (honest sequencing)

**PHASE T -- TODAY (ships today).** The free combat prototype, deployed to web. No accounts, no
payments, no save. Mount at `/play/alley-kingz` on vantaris (the `/play/blackjack` pattern already
exists), framed as "early COMBAT PROTOTYPE -- one live match vs AI, no progression/shop/accounts
yet" (GAP_AUDIT section 6). Reuses: static build + Cloudflare Pages. Gap-fill first per GAP_AUDIT
Bucket A (the 2 blank starter icons + The Lot boot arena). **Effort: hours, not days.**

**PHASE W -- THIS WEEK (the spine).** Accounts + cloud save (System 2) -> card levels (System 1) ->
PvE arena ladder (System 5) -> player profile read-view (System 4). This is the smallest set that
turns the combat toy into a GAME with progression you keep. Reuses: Supabase Auth + Google OAuth +
`player_accounts` + the engine's existing stat-read and `setDifficulty` dial. **Effort: ~1 focused
week. NOT a same-day build -- accounts are the source of truth and get a migration + RLS + tested
save/restore.**

**PHASE L1 -- LATER (monetize, legal-gated).** Shop + Stripe SKUs (gem packs, the pass, starter +
revival packs) + cosmetics-only guardrail (System 3). Reuses: the live `verify-arcade-purchase`
backbone + Stripe. **Blocked on: the Crew-vs-Master pass decision + legal sign-off on live
payments. Multi-week responsibly.**

**PHASE L2 -- LATER (the crypto layer).** $BCARDD on-ramp (`verify-bcardi-onramp`) + NFT
marketplace link (Tensor/Magic Eden) + wallet-connect + Metaplex asset read (System 4b). Reuses:
the $BCARDD coin + Metaplex mint pipeline (MASTER_BUILD_PLAN Phases 3, 5). **Blocked on: the full
Phase-3 mint + Legal Gates 1-3.**

**PHASE L3 -- LATER, LAST (ranked).** Ranked PvP: matchmaking + authoritative server + netcode +
server-side match validation (System 6). **The heaviest build; ship only after the single-player
loop is proven fun. Multi-week to multi-month.**

---

## THE FASTEST RESPONSIBLE PATH (the bottom line)

Ship the free combat toy TODAY (zero backend, framed honestly). Spend THIS WEEK building the spine
the engine is already shaped for: Supabase accounts + Google OAuth, card levels as a one-line stat
multiply, and the PvE ladder as the `setDifficulty(0-9)` wiring -- all on infra that already exists.
HOLD payments, the crypto/NFT marketplace, and ranked PvP for LATER: payments need legal sign-off and
a pass decision; the marketplace needs the mint + all three legal gates; ranked needs real netcode.
This sequence gets a real, persistent, single-player game in a week and keeps the legally and
technically heavy pieces where they belong -- behind the gates, not on the critical path.

---

*Authored 2026-06-03. Grounded in PRD_V2 (Sections 1-7), 05_DATA_MODEL (PlayerData / ShopOffer /
LevelConfig schemas), MONETIZATION_UX_REWRITE, PACK_RIP_OUTCOME_MODEL, ECOSYSTEM_ARCHITECTURE
(sections 1-8), MASTER_BUILD_PLAN (Phases 0-6), and a line-level read of engine.js (stat-read at
~301, `DIFFICULTY`/`setDifficulty` at 272/921, `STARTER_DECK_NAMES` at 253) + cards.json (48-card
canon). No game code was modified. Pairs with the updated GAP_AUDIT.*
