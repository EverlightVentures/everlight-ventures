# ALLEY KINGZ -- SHOP & MARKETPLACE MASTER PLAN
**Date:** 2026-06-03 | **Author:** Lucrex (Hive fork) | **Status:** Plan + research. No code/payments built.
**Pairs with:** `META_GAME_BUILD_PLAN.md` (System 1 levels + System 3 economy -- this doc DEEPENS the shop layer), `spec/PRD_V2.md` (4 ladder, 5 economy), `MONETIZATION_UX_REWRITE.md`, `spec/PACK_RIP_OUTCOME_MODEL.md`, `ECOSYSTEM_ARCHITECTURE.md` (sec 6 infra, sec 8 legal gates).
**Card spread (cards.json):** Mythic 4 / Legendary 1 / Epic 9 / Rare 20 / Common 14 = 48. Max level = **10** (operator-set, not Clash's 16).

> The combat prototype is live (alley-kingz.pages.dev). This is the layer that makes money: people play -> want stronger cards -> upgrade -> need cards -> the SHOP. Goal = a Supercell-grade pay-to-play money machine that is legally CLEAN (no Supercell lawsuit, no gambling exposure) and a DIFFERENT vibe (cyberpunk dogs + Twisted-Metal rigs), with cheap competitive pricing to seed early adoption.

---

## 0. THE FIVE NON-NEGOTIABLES (every shop decision obeys these)
1. **No pay-to-win in ranked.** Money buys cosmetics, convenience (chest skips, dupes faster), the pass track, and PvE-only consumables. Every card is earnable free (PRD 5.3). A SKU that grants a raw stat edge in ranked is rejected at review.
2. **Legally distinct from Supercell.** We model their FORMAT, never their assets/names/trade-dress. Our terms (NOS Bottles, Crew/Master Pass, Chop Shop, Scrap Tokens), our art, our copy. See section 8.
3. **No real-money cash-out.** Gems/cards/tokens flow IN only. The moment value flows OUT for cash it becomes gambling/money-transmission (ECOSYSTEM gate 1, DEFAULT OFF). The $BCARDD/NFT door is a separate legal track (gates 1-3).
4. **Reveal value, do not hard-sell** (MONETIZATION_UX_REWRITE): the shop seduces through experience, not FOMO timers and bullet lists. Premium = quiet gold accents, not flashing "BUY NOW."
5. **Cheap to seed, raise later.** Launch pricing undercuts Clash to convert first-payers; LiveOps tunes upward once the base + retention prove out.

---

## 1. HOW WE DIFFER FROM CLASH (the "different pay-to-play")
| Clash Royale | Alley Kingz (distinct) |
|---|---|
| Wild Cards substitute dupes | **Scrap Tokens** (per-rarity) -- earned from the Chop Shop + duplicates of MAXED cards, spendable to buy ANY same-rarity card. Transparent: you always know the exchange rate. |
| Chests = the only card source, opaque | Chests PLUS a **direct Card Shop** (spend Scrap Tokens on the exact card you want -- less gacha-rage, friendlier, fewer loot-box-law headaches). |
| No consumables | **Garage consumables** -- pre-match PvE-only **Nitro (buff), Spells, Potions, Decals** (cosmetic). A new spend lane Clash does not have, kept OUT of ranked so it is not P2W. |
| Trophies only | NOS Bottles + a **$BCARDD crypto on-ramp** (parallel, optional) + tradable NFT cards (later). |
| Generic fantasy | **Cyberpunk dog crews + Twisted-Metal war-rigs.** The whole shop is a neon back-alley chop-shop. |

The dog/Twisted-Metal "chop shop" framing is the brand wrapper around a proven Supercell economy.

---

## 2. CURRENCIES + THE SCRAP TOKEN SYSTEM
| Currency | Type | Earn | Spend | Buyable for $? |
|---|---|---|---|---|
| **Fuel** | soft | wins, dailies, chests, ladder | card upgrades, shop soft offers | no (anti-P2W) |
| **Gears** | mid/season | pass track, events | premium/seasonal cards, skins | via pass only |
| **Gems** | hard | Stripe $ OR $BCARDD on-ramp OR slow free drip | chests, chest skips, the pass, consumables, Scrap Tokens | YES |
| **Scrap Tokens** (per rarity: Common/Rare/Epic/Leg/Mythic) | crafting | Chop Shop, dupes of maxed cards, chests, pass | buy ANY card of that rarity, or sub for missing dupes on upgrade | indirectly (via gems->chests) |

**Card-value unit (for token math):** Common 1 / Rare 5 / Epic 25 / Legendary 250 / Mythic 1000 "scrap-value" (mirrors Clash's rarity value ladder, our numbers). A Mythic Scrap Token = 1000 common-equivalents -- a deliberate long grind that protects the NFT-floor scarcity story for $BCARDD etc.

---

## 3. CARD LEVELING ECONOMY (FINAL per-rarity tables, levels 1-10)
Stat scaling stays **`levelMult(L)=1+0.10*(L-1)`** (META System 1: L10 = 1.90x, linear, no-P2W). This table is the COST side -- dupes + Fuel to go L->L+1. Scrap Tokens of the matching rarity can substitute missing dupes 1:1.

**Common** (14 cards, flood-and-cap): 2,4,6,10,20,40,80,150,300 dupes | Fuel 5,20,50,100,250,500,1k,2k,4k. Total to L10: ~612 dupes / ~7.9k Fuel.
**Rare** (20 cards): 1,2,4,8,16,30,60,120,250 | Fuel 50,150,400,1k,2k,4k,8k,15k,30k. Total: ~491 / ~60k.
**Epic** (9): 1,1,2,4,8,16,30,60,120 | Fuel 0.4k,0.8k,2k,4k,8k,15k,30k,60k,120k. Total: ~242 / ~240k.
**Legendary** (1 -- Stonejaw): 1,-,1,-,2,-,4,-,8 (dupe drip slow, blank bands cost Fuel only) | Fuel up to 150k/band. Total: ~16 / ~250k.
**Mythic** (4 -- $BCARDD/Jagged/Rosco/Crown Foxhound): 1,-,-,1,-,-,1,-,1 | Fuel up to 250k/band. Total: ~4 / ~430k.

Reading it: a Common maxes in days, a Mythic in months -- the spend curve that drives chest/pass purchases. Tune in `game/UPGRADE_SPEC.md` after playtest; numbers above are the committed first draft.

---

## 4. THE SHOP (surfaces)
### 4.1 The Daily Lot (free, the retention hook)
- **Free Daily Crate** every 24h (Fuel + a few random Common/Rare cards). The "log in" magnet.
- **Free ad-watch crate** (optional later -- rewarded video, +Fuel/Scrap).
- **Daily Deals row** -- 6 rotating offers (cards for Fuel/Scrap, small gem bundles, a cosmetic). Refreshes daily; a free first slot.

### 4.2 Chests (gem-bought + earned)
Earned from wins (unlock timer like Clash) OR gem-skip the timer. Buyable directly with gems.
| Chest | Gem price | Contents (ODDS DISCLOSED) |
|---|---|---|
| Scrap Crate | 40 | commons + Fuel |
| Crew Chest | 150 | rares + a chance at epic |
| Chop-Shop Chest | 400 | epic-guaranteed + rare + scrap tokens |
| Kingpin Chest | 900 | legendary chance + epic + tokens |
| **Mythic Vault** (event-only) | 2000 | mythic chance (low, posted %) + guaranteed legendary tokens |
Every chest shows exact drop odds on the buy screen (store-policy + legal requirement, sec 8).

### 4.3 Card Shop / Scrap Token Exchange
Spend matching-rarity Scrap Tokens to buy the EXACT card you want (no gacha). This is our friendlier, lower-legal-risk alternative to pure loot boxes -- and a strong retention lever.

### 4.4 The Garage (consumables -- the distinct lane, PvE-only)
NOT usable in ranked (keeps no-P2W). Cosmetic ones usable everywhere.
- **Nitro Cans** (pre-PvE-match buff: +1 starting energy) -- gems/Fuel.
- **Spells** (one-shot PvE: lane EMP, repair, rage) -- gems.
- **Potions** (XP/Fuel boost timers) -- gems.
- **Decals / paint / emotes / dealer skins** (cosmetic, everywhere) -- gems.

### 4.5 Cosmetics shop
Rig skins, arena themes, victory emotes, $BCARDD dealer skins. Pure cosmetic = the safest revenue. Rotating + seasonal.

### 4.6 Passes (RESOLVE THE CONFLICT)
PRD says Crew Pass $9.99/35d; MONETIZATION_UX_REWRITE says arcade-wide Master Pass $14.99/mo. **RECOMMEND: ship the Master Pass ($14.99/mo, covers every Everlight Arcade game incl AK) + a cheap AK-only Crew Pass ($4.99/season) for players who only want Alley Kingz.** Master Pass perks: 2x gem/Fuel earn, exclusive seasonal card track, cosmetic, chest-slot. OPERATOR MUST LOCK THIS before any pass SKU/banner ships.

### 4.7 Bundles (the conversion drivers)
- **Starter Garage** $2.99 one-time (gems + Fuel + a Chop-Shop chest) -- the cheap first-purchase converter.
- **Revival Pack** $1.99 -- fires on a 5-loss streak (highest-uplift offer per industry data).
- **Seasonal/themed bundles** -- a dog/faction-themed gem+skin+card pack each season.

---

## 5. PRODUCT CATALOG + PRICING (competitive-cheap, Stripe SKUs)
| SKU | Price (USD) | Grants |
|---|---|---|
| gems-80 | $0.99 | 80 gems |
| gems-500 | $4.99 | 500 gems (+10%) |
| gems-1100 | $9.99 | 1,100 gems (+15%) |
| gems-2500 | $19.99 | 2,500 gems (+25%) |
| gems-6500 | $49.99 | 6,500 gems (+30%) |
| gems-14000 | $99.99 | 14,000 gems (+40%, whale tier) |
| pass-master | $14.99/mo | arcade-wide Master Pass |
| pass-crew-ak | $4.99/season | AK-only season track |
| bundle-starter | $2.99 once | starter garage |
| bundle-revival | $1.99 | revival pack (streak-triggered) |
Pricing is intentionally a notch under Clash to convert first payers; LiveOps raises/adds tiers after retention proves out. All real-money goes Stripe; gems are the single hard-currency choke point (everything paid routes through gems for clean accounting + one refund surface).

---

## 6. DATA + PAYMENTS (Supabase + Stripe, reuse the live backbone)
Reuses `verify-arcade-purchase` edge fn + `game_currencies`/`game_passes`/`arcade_purchases` (ECOSYSTEM 6.1). New schema:
- **`shop_products`**: sku, kind (gems|pass|bundle|chest|consumable|cosmetic), price_usd OR price_gems, grants (jsonb), active, geo_restrict (jsonb), odds (jsonb for chests).
- **`player_currencies`**: player_id, fuel, gears, gems, scrap_common/rare/epic/leg/mythic (extend `game_currencies`).
- **`player_inventory`**: player_id, item_sku, qty (consumables/cosmetics owned).
- **`transactions`** (audit + anti-cheat): player_id, kind, sku, currency_delta (jsonb), stripe_event_id (idempotency), source, created_at.
**Crediting flow (fiat):** Stripe Checkout -> webhook -> `verify-arcade-purchase` verifies the event (idempotent on `stripe_event_id`) -> writes the grant to `player_currencies`/`player_inventory`/`game_passes` under a Supabase RLS-guarded, SERVER-side write. Client never self-grants. **Crediting flow (crypto, later):** `verify-bcardi-onramp` confirms a Solana $BCARDD transfer -> grants the same gems. Receipts + a re-grant-on-failure retry are mandatory (a paid player who did not get credited = a chargeback + a 1-star review).

---

## 7. LEONARDO AI VISUAL PROMPTS (marketplace + every product)
**Style bible anchor (prepend to all):** "premium mobile-game shop UI art, Everlight palette gold #D4AF37 / #c9a84c on vanta-black #050507, cyberpunk neon back-alley chop-shop vibe, Twisted-Metal dog-crew energy, hyper-real PBR, clean readable at icon size, centered, no text, no watermark, no UI chrome."
- **Shop screen backdrop:** "a neon cyberpunk underground chop-shop / black-market garage, gold-trimmed stalls, hanging rig parts and graffiti, a Dogo Argentino shopkeeper silhouette, warm gold key light on vanta-black, wide background plate."
- **Chests (5 tiers):** "a [rusted scrap crate | chrome crew chest | gold-trimmed chop-shop chest | crowned kingpin vault | glowing mythic vault with a gold dog-crown sigil] war-loot chest, closed, sitting in a neon garage, premium game chest icon, square." (escalate materials per tier)
- **Gem stacks (per pack):** "a stack of glowing faceted neon-cyan power-gems, gold flecks, small to overflowing pile for the [80..14000] tier, premium IAP currency icon, square, dark backdrop."
- **Scrap Tokens (5 rarity icons):** "a circular war-rig scrap-token coin, [grey steel | blue | violet | gold | crowned black-gold] rim matching the card rarity, a dog-paw + gear emblem stamped, game currency token icon."
- **Garage consumables:** "Nitro Can (a chrome NOS canister, gold-cyan), Spell vial (neon energy potion in a war-flask), XP Potion (glowing amber bottle), each a premium game consumable icon, square."
- **Pass banners:** "a wide premium battle-pass banner, gold MASTER PASS / AK CREW PASS crest with a crowned cyberpunk war-dog and a rig, gold-on-vanta, cinematic, banner aspect, no text."
- **Bundle hero art:** "a bundle hero shot -- a war-dog crew chest spilling gems + scrap tokens + a card, neon garage, premium store bundle art, square."
Generate via the existing `generate_icons.py` Leonardo pipeline (add a SHOP section), 512px PNG, into `game/assets/shop/`.

---

## 8. LEGAL & COMPLIANCE (do NOT skip -- this is how we make money WITHOUT a lawsuit)
- **Anti-Supercell (trademark/trade-dress):** copy the ECONOMIC FORMAT (chests, passes, dupe-upgrades, daily deals) -- this is not protectable. NEVER copy: their card names, art, exact UI layout, their trademarked terms (use our NOS Bottles/Crew Pass/Chop Shop/Scrap Tokens), or any asset. All art is our Leonardo/Seedance originals. Keep the brand unmistakably "cyberpunk dogs," not Clash clones.
- **Loot boxes / chests:** **disclose exact drop odds** on every paid random pack (Apple/Google store policy + a growing list of jurisdictions). Offer the **direct Card Shop (Scrap Tokens)** as the deterministic alternative. **Geofence** paid random packs where required (Belgium, Netherlands historically; flag WA/MN/HI/US-minors). Honor `PACK_RIP_OUTCOME_MODEL` -- its A/B/C decision is STILL BLANK; do not ship paid random packs until the operator signs it.
- **No gambling / money transmission:** no cash-out, no real-money trading of in-game items for fiat (ECOSYSTEM gate 1, default OFF). The NFT/$BCARDD marketplace is a SEPARATE legal track (gates 1-3) and ships only after legal sign-off.
- **Stripe + consumer:** clear pricing, a refund policy, "all sales final on virtual goods" where lawful, parental-gate for under-13 (COPPA) if the audience skews young, and a Terms/Privacy page. Route everything through Gems so there is one auditable currency + one refund surface.
- **The 3 gates (ECOSYSTEM sec 8)** must each be legal-signed before their surface: Gate 1 off-ramp, Gate 2 promised-returns (no "hold to earn"), Gate 3 loot-box. **Loop the legal team in BEFORE live payments.**

---

## 9. MARKETING + REVENUE STRATEGY (grab a slice of the pie)
**The benchmark (sources below):** Clash Royale did **$452M in 2025** ($3.06B lifetime) off ~10M MAU / 4.4M DAU; Supercell ~$1.12B in 2025. Mobile F2P norms: **~2-5% of players ever pay**; **~50% of revenue comes from the top ~1% (whales)**; healthy strategy/card ARPDAU lands roughly $0.05-0.20. We are not chasing $452M; capturing even **0.1% of that lane (~$450k/yr)** is a life-changing indie outcome and a realistic 12-24mo target IF retention holds.
**The funnel (what actually makes money):**
1. **Free combat beta (live now)** -> top of funnel, viral clip-able. Acquisition = organic social (TikTok/Reels of dog-rig battles), the $BCARDD community cross-promo, Everlight Arcade cross-traffic.
2. **Retention spine (META plan, this week)** -- accounts + levels + ladder. Monetization is meaningless without D1/D7 retention; build this BEFORE the shop.
3. **First-purchase converter:** the $2.99 Starter Garage + the daily free crate habit. Cheap-first beats the conversion wall.
4. **The pass** ($14.99 Master) = the recurring-revenue backbone (subscriptions smooth the whale-tail volatility -- the lesson of Supercell's 2025 comeback was deeper passes + LiveOps, not more loot boxes).
5. **LiveOps / seasons** -- a new dog faction or arena + themed bundle each season = the live-service revenue engine. This is where Clash 5.7x'd its revenue.
6. **The whale tail** -- the $99 gem tier + Mythic Vault + cosmetics for the ~1% who fund ~half the revenue. Ethical: cosmetics + speed, never ranked power.
**Pricing strategy:** launch cheap (undercut Clash) to win first-payers + reviews, then LiveOps-tune upward + add tiers. Track ARPDAU, D1/D7/D30, payer-conversion, and pass-attach from day one (PostHog/Supabase analytics).

---

## 10. BUILD SEQUENCE (what ships when -- gated)
1. **NOW:** free beta is live (done). Generate the shop VISUALS (section 7, Leonardo) so the UI can be mocked.
2. **THIS WEEK (gated on META accounts):** the shop is meaningless without accounts + currencies + levels (META Systems 1-2). Build those first.
3. **THEN (legal-gated):** Stripe SKUs (section 5) + the shop UI + crediting flow (section 6) + cosmetics/chests with odds. **Blocked on:** the pass-conflict lock + legal sign-off on live payments + the PACK_RIP A/B/C decision.
4. **LATER:** $BCARDD on-ramp + NFT marketplace (gates 1-3 + the mint).

## 11. OPERATOR DECISIONS NEEDED
1. **Pass model:** Master Pass $14.99/mo (recommended) vs Crew Pass $9.99/35d vs both. LOCK before any pass SKU/art.
2. **PACK_RIP A/B/C:** sign the loot-box outcome model, or ship the deterministic Scrap-Token Card Shop ONLY (lower legal risk) and defer paid random chests.
3. **Launch gem prices:** confirm the section-5 table (cheap-to-seed) vs match-Clash.
4. **Legal counsel** engaged before live Stripe payments (gates 1-3).

---
## ADDENDUM: Gacha / Lucky-Draw model (COD Mobile / PUBG) -- ADDED 2026-06-03
Apply the **loot-box / gacha** monetization the COD-Mobile / PUBG way. Full legal framework:
`01_BUSINESSES/Everlight_Ventures/Everlight_Gaming/MONETIZATION_LEGAL_LANES.md`.
- **Sell the draws directly** (no free-entry needed) -- LEGAL because the reward is **IN-GAME value only,
  not cashable for real money** (why COD/PUBG sell crates and have never been successfully sued).
- **Escalating mythic draw:** each pull shifts pool/price so a Mythic is guaranteed at ~$X total (COD's is
  ~$300/mythic by design). High-margin, proven, legal. Build the draw with **disclosed odds**, always give
  the player SOMETHING per pull.
- **THE WRINKLE (Alley Kingz cards are $BCARDD NFTs):** if draw-pulled cards have **real resale value**, a
  paid draw edges toward gambling. SAFE PLAYS: (1) keep draw cards **in-game value only** = clean loot box
  like COD, OR (2) if tradeable NFTs, run the draw past the attorney + disclose odds + never market resale.
- **NEVER** sell a paid draw whose prize cashes out for real money (= gambling). Loot box = sell draw,
  in-game prize. Sweeps (B Card Blackjack) = free entry, cashable prize. Keep the two lanes separate.

---
*Sources: Clash Royale revenue [Business of Apps](https://www.businessofapps.com/data/clash-royale-statistics/), [Udonis](https://www.blog.udonis.co/mobile-marketing/mobile-games/clash-royale-player-count), [Statista](https://www.statista.com/statistics/557510/clash-of-clans-and-clash-royale-sales-revenue/); card-upgrade/Wild-Card model [Clash Royale Wiki](https://clashroyale.fandom.com/wiki/Cards), [RoyaleAPI economy](https://royaleapi.com/blog/level-16-and-economy-changes-2025-q4); gacha/loot-box legality in MONETIZATION_LEGAL_LANES. Grounded in META_GAME_BUILD_PLAN, PRD_V2, MONETIZATION_UX_REWRITE, PACK_RIP_OUTCOME_MODEL, ECOSYSTEM_ARCHITECTURE. No payments/code built; plan + visuals-spec only.*
