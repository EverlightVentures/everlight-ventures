# ALLEY KINGZ -- FORTNITE-ELEMENTS ARCHITECTURE (Build-Ready)
**Status: BUILD-READY MAP. Grounded on the live stack, cheapest-path-first.**
Date: 2026-06-14 | Author: AK product architect

This maps the proven Fortnite live-service playbook (battle pass, seasons, rotating
FOMO shop, quests, cosmetics, live events, crossovers) onto the ACTUAL Alley Kingz
stack -- not a clean-room redesign. Every pick reuses `economy.js`, the
`alley-kingz-shop` server-authoritative edge-fn pattern, the social layer
(`SOCIAL_LAYER_ARCHITECTURE.md`), and the 10-city storyline (`STORYLINE_CANON.md`).

LANE-A LAW (non-negotiable, inherited from `GAME_SHOP_MIRROR.md` + the retention
ethics guardrail): everything here sells TIME and STYLE, never POWER. No pay-to-win
on stats. Cards are level-normalized in ranked. All pass/shop rewards are in-game
value only -- never cashable, never a tradeable NFT. $BCARDD is marketed as fun and
culture, NEVER as an investment.

================================================================
## GROUND TRUTH (verified against the live code, not assumed)
================================================================
- Client: vanilla-JS static site on Cloudflare Pages (`alleykingz.online`). No bundler (phone-proot safe).
- Auth + DB: Supabase project **`mfghdobptredxxhbjwyz`** (AK's OWN; never the casino). OAuth redirect glob `https://alleykingz.online/**`.
- Save layer: `public.ak_player_saves` -- one jsonb row per user, RLS owner-scoped, newest-wins (`game/ak_account.js`).
- **Server-authoritative pattern (COPY THIS for every money/reward mutation):** `game/shop/shop.js` POSTs INTENTS to edge fn `/functions/v1/alley-kingz-shop` with `{action, player_id, ...}` + `apikey`/`Bearer` anon headers. The function is the truth; the client never mints currency.
- Economy (`economy.js` -> `AK_ECON`): **Gems** (premium, SERVER-ONLY -- bought via Stripe), **Gold/Coins** (local `ak_profile`), **Scrap** (per-rarity, local), **Keys** + **Fragments** (local), **Chests** (wood/bronze/silver/gold/diamond, local `grantChest`), card **copies** (drive Garage upgrades). Card upgrade math = `upgradeNeed` / `levelUpCard`.
- The ONE reward faucet: `index.html grantMatchRewards(g)` -- every match pays XP + Gold + drops + a chest here, once per match. **The Alley Pass hooks THIS.**
- Stripe rail PROVEN: `buy-gems` -> returns Checkout `url`; `confirm-gems` is idempotent (unique lock on `ak_transactions`). We reuse this rail for the pass and the cosmetic shop.
- Server-grant -> local-copy bridge PROVEN: `shop.js profileSync()` / `grantServerCards()` merge server grants into `ak_profile` so the Deck Lab + Garage see them instantly. **Every pass/shop grant reuses this bridge.**
- Social layer LIVE (Phase 1): crews, world/crew chat, donations, crew-war shell on Supabase. Weekly reset via `pg_cron`. **The pass plugs straight into this -- donations + wars become weekly quests; do NOT duplicate.**
- Retention levers already live: `ak_streak` daily drop, Lucky Draw (variable-ratio + pity), chests, XP/levels, world-map road. The pass + quests are the missing escalating-progression + deadline layer.
- Art: every new asset routes through the art-factory cron (`ART_AUTOROUTE_DOCTRINE.md`) -- NO generic art ships.

================================================================
## THE PICKS -- what we build and why it fits
================================================================
| Fortnite element | AK name | Fit | Phase |
|---|---|---|---|
| Two-track battle pass (free + premium) | **The Alley Pass** | strong | 1 |
| Buy-the-pass-earn-it-back (V-Bucks flywheel) | **Gem-Back Flywheel** (pass priced in Gems) | strong | 1-2 |
| Daily/weekly/milestone quests = XP engine | **The Hit List** (jobs) | strong | 1 |
| Pass XP curve separate from account level | **Street Rep ladder** (`pass_xp`) | strong | 1 |
| Seasonal cadence + reset + FOMO exclusivity | **Seasons** (6-8 wk) + auto-reset | strong | 2 |
| Rotating item shop w/ FOMO countdown | **The Drop** (rotating cosmetic shop) | strong | 1 |
| Cosmetics: card skins, board/arena skins, emotes, dog cosmetics | **Drip** (cosmetics layer) | strong | 1 |
| "Choose your reward" pages + pacing | reward pacing now, claim-order v2 | medium | 2 |
| Subscription (Fortnite Crew) | **Kingpin Club** ($14.99/mo) | medium | 3 |
| Tier skips + battle bundle | **Skip SKUs** (Gems) | medium | 2 |
| Chapter/map/theme/narrative refresh | **Chapters** (story beats + meta) | medium | 4 |
| Bonus track / OG styles / supercharged catch-up XP | **Overtime + Hot Streak** | medium | 3 |
| Live in-game events (concerts/map moments) | **Crown Heists** (timed $BCARDD/city events) | medium | 4 |
| Crossovers | in-house brand crossovers (Onyx/Everlight) only | medium | 4 |

================================================================
## 1. THE ALLEY PASS (two-track battle pass) -- Phase 1 keystone
================================================================
One seasonal pass, two parallel reward lines fed by ONE XP bar.
- **Free track**: a thin reward line everyone earns just by playing (Gold, Scrap, a chest, the occasional Gem driblet). This is the conversion funnel -- free players grind, accrue sunk cost, and stare at the greyed premium tier sitting right next to the free one they just claimed.
- **Premium track** (the Alley Pass, priced in **Gems**): lights up the full ladder -- the season's exclusive **card skins / board skin / emote / crew crest**, the bulk of the Gems, and the headline cosmetic. Buying does NOT skip the grind; it unlocks the rewards you already leveled past.

### 1.1 Data model (Supabase, `ak_` namespace, RLS owner-scoped)
```sql
-- Season definition (one active at a time). Reward track is data, not code.
create table public.ak_seasons (
  id            int primary key,                 -- season number, monotonic
  name          text not null,                   -- "Season 1: Boneyard Reign"
  theme         text not null default '',
  faction_focus text,                            -- boneguard_crew | zoomie_syndicate | ...
  headline_card text,                            -- featured card #, e.g. '0001' ($BCARDD)
  track         jsonb not null,                  -- [{level, free:{...grant}, premium:{...grant}, headline:bool}]
  pass_price_gems int not null default 950,      -- Gem-Back Flywheel anchor
  starts_at     timestamptz not null,
  ends_at       timestamptz not null,
  active        boolean not null default false
);

-- Per-player pass progress for the CURRENT season. Resets each season.
create table public.ak_pass_progress (
  user_id       uuid not null,                   -- auth.uid
  season_id     int  not null references public.ak_seasons(id),
  pass_xp       int  not null default 0,
  pass_level    int  not null default 1,
  bonus_level   int  not null default 0,         -- Overtime track past max (Phase 3)
  owns_premium  boolean not null default false,  -- flipped by buy-pass / sub
  claimed_free  int[] not null default '{}',     -- claimed free-track levels
  claimed_prem  int[] not null default '{}',     -- claimed premium-track levels
  xp_today      int  not null default 0,         -- anti-injection daily XP cap
  xp_day        date,                            -- the day xp_today counts for
  updated_at    timestamptz not null default now(),
  primary key (user_id, season_id)
);
```
RLS: a player reads/writes only their own `ak_pass_progress` row; `ak_seasons` is world-readable, service-role-writable.

### 1.2 Edge function `ak-pass` (copies the `alley-kingz-shop` intent pattern EXACTLY)
Actions (server is truth; client never grants itself XP/rewards):
- `get` -> returns active season + the player's `pass_xp`/`pass_level`/`owns_premium`/claimed sets + the rendered track (free tier vs greyed premium tier).
- `report-match {result, gates, won, mode}` -> server applies BOUNDED, CAPPED XP (see 1.4) to `pass_xp` + account hook, advances quest counters, returns the new level. **This is the only XP write.**
- `claim-tier {level, track}` -> validates the level is unlocked + (for premium) `owns_premium`, not already claimed; grants the reward server-side; returns the grant payload for the local bridge.
- `buy-pass` -> checks Gem balance >= `pass_price_gems`, deducts Gems, sets `owns_premium=true`. (Gems come from Stripe gem packs -- the cash on-ramp already exists.)
- `buy-tier {n}` / `buy-bundle` -> tier skips (Phase 2, sec 6).

### 1.3 Reuse of `economy.js` + the existing shop
- Reward atoms are EXISTING verbs: `grantChest(tier)`, `addScrap(r,n)`, `addKeys`, `addCopy(name)`, coins, plus Gems (server) and cosmetics (new table). No new currency.
- Claimed grants flow back to the client through the PROVEN bridge: `profileSync(names, coins, scrap, chests)` + `grantServerCards(cards)` (already in `shop.js`), so the Deck Lab + Garage see pass rewards immediately, identical to how `open-chest` grants land today.
- Gems are SERVER-ONLY per `economy.js` -- the pass NEVER grants Gems client-side; only `ak-pass claim-tier` (service role) credits them.

### 1.4 Pass XP curve (separate from account level)
- Account level curve is UNTOUCHED (`80 + 40*(N-1)`, cap 21, `PROGRESSION_DESIGN.md`). The pass is purely ADDITIVE.
- Same `grantMatchRewards(g)` call that pays account XP also fires `ak-pass report-match`. A match advances BOTH: account level (permanent) and pass level (resets seasonally).
- Size: ~50-75 pass levels for a 6-8 week season at the live ~60 XP/win pace; most XP comes from quests (sec 3), not raw play.
- **Anti-injection (cheapest honest trust):** the server bounds each `report-match` (max XP/match), enforces a **daily XP cap** via `xp_today`/`xp_day`, and rate-limits. Full referee-grade trust waits for the deterministic-sim Phase 3 of the social layer; until then we use the SAME "sanity-bound the client report" stance `ak-pvp` uses. Documented, not hidden.

### 1.5 Ties to social layer + storyline
- Headline reward is an **exclusive crew crest / banner** that plugs into `ak_crews.crest` (social layer) -- status you fly in chat and on the ladder.
- Season `faction_focus` + `headline_card` anchor to a lore house; Season 1 = `boneguard_crew` / $BCARDD card #0001 as the recurring through-line.

================================================================
## 2. THE GEM-BACK FLYWHEEL (buy-the-pass-earn-it-back) -- Phase 1-2
================================================================
The genius hook, and LEGALLY SAFE for AK because Gems are non-cashable.
- Pass priced in **Gems** (`pass_price_gems`, anchor 950). The premium track seeds Gems across its tiers so a COMPLETER earns back ~**110%** of the price -- enough to buy NEXT season's pass, **never enough to cash out and never enough to skip the grind**.
- First-time players buy Gems with cash (existing Stripe packs) to afford pass #1. Completers self-fund forever; the loop converts a one-time ~$5-8 buyer into a permanent grinder.
- **The recapture loop:** earned Gems flow into **The Drop** (sec 5, the rotating cosmetic shop) on impulse buys. Pass seeds Gems -> player completes -> spends the surplus on cosmetics -> stays engaged. This is the whole flywheel, Lane-A clean.
- Tuning lives in `ak_seasons.track` (data), so we retune payback per season without a code change. Target net: pass costs N Gems, completer earns ~1.1N back, spends the float in The Drop.

================================================================
## 3. THE HIT LIST (daily / weekly / milestone quests) -- Phase 1
================================================================
Most pass XP comes from QUESTS, not raw play -- the habit driver.
- **Daily jobs** (refresh 00:00 PT, small XP): win 1 match, play a Boneguard card, clear 3 gates, open a crate. The habit loop (open -> reward -> repeat; retention doc: +68% 6-mo for daily-reward engagers).
- **Weekly jobs** (expire weekly, big XP -- loss-aversion "don't waste this week"): win 10, **donate 5 cards via the crew donation loop**, **log 3 crew-war battles**, beat a city. *(Donations + wars are the EXISTING social-layer loops -- the quest engine just reads their counters. Align, do not duplicate.)*
- **Milestone/story jobs**: beat city N, reach pass level 25, hit a 7-day streak.

### 3.1 Data model
```sql
create table public.ak_quests (                  -- definitions (service-role authored per season)
  id          text primary key,                  -- 'd_win1', 'w_donate5', 'm_city3'
  season_id   int  references public.ak_seasons(id),
  scope       text not null,                     -- daily | weekly | milestone | story
  label       text not null,
  target      int  not null,
  reward_xp   int  not null,
  reward      jsonb default '{}',                -- optional bonus grant (gold/scrap/chest)
  active      boolean not null default true
);
create table public.ak_quest_progress (
  user_id     uuid not null,
  quest_id    text not null references public.ak_quests(id),
  progress    int  not null default 0,
  completed_at timestamptz,
  claimed     boolean not null default false,
  period_key  text not null,                     -- 'YYYY-MM-DD' daily / 'YYYY-Www' weekly
  primary key (user_id, quest_id, period_key)
);
```
RLS owner-scoped on `ak_quest_progress`; `ak_quests` world-readable.

### 3.2 Reuse + flow
- `ak-pass report-match` (or a thin `ak-quests progress` action) increments quest counters server-side from the same match report -- no client trust on completion.
- Crew donations/wars already write rows (`ak_donations`, `ak_war_battles`); the quest engine counts those rows for the period -- zero new client work.
- **Claim-all** button on the lobby (already flagged P1 in `RETENTION_PSYCHOLOGY_STRATEGY.md`): one tap grants all completed quests' XP via `ak-pass`.
- Daily/weekly refresh = `pg_cron` (reuses the social-layer weekly-reset job) bumping `period_key`.

================================================================
## 4. SEASONS -- cadence + reset + FOMO exclusivity -- Phase 2
================================================================
- Run **6-8 week** AK seasons (shorter than Fortnite -- smaller audience, faster dopamine; ~6-8 seasons/yr).
- At season end: pass EXPIRES (unclaimed tiers gone), the season's exclusive cosmetics are **vaulted forever** (status for OG players), and `pass_level` resets to 1.
- **Auto-roll = `pg_cron`** (same scheduler powering the social-layer reset): archive old `ak_pass_progress`, flip `ak_seasons.active`, reset `pass_level`, swap the reward track + theme.
- A live **season countdown** sits on the lobby all season (appointment + deadline mechanic from the retention doc).

### 4.1 CRITICAL GUARDRAIL (retention ethics)
Reset the **PASS ONLY**. NEVER reset the account level, the card collection, card levels, Gold, or Scrap. Resetting those would be the exploitative dark pattern the retention doc forbids. The ladder is re-runnable; your stuff is permanent.

================================================================
## 5. THE DROP -- rotating cosmetic shop with FOMO -- Phase 1
================================================================
The recapture surface where earned + bought Gems get spent. Built INTO the existing
`alley-kingz-shop` get-shop payload + the dynamic-promos engine in `shop.js` -- a new
**Drip** tab, not a new surface.
- Server-driven daily/weekly **featured rotation** of cosmetics with a live **"resets in HH:MM"** countdown (the deterministic daily deal in `shop.js dailyCard()` proves the pattern; we move rotation to the server for FOMO control + exclusivity).
- Limited-time bundles (a card skin + matching board skin + emote) at a discount, surfaced through the existing promo banner (`promoBanner()` already renders `state.active_promos`).

### 5.1 Data model
```sql
create table public.ak_shop_rotation (
  id           uuid primary key default gen_random_uuid(),
  slot         text not null,                    -- 'featured' | 'daily' | 'bundle'
  cosmetic_id  text references public.ak_cosmetics(id),
  bundle       jsonb,                            -- [cosmetic_id...] for bundle slots
  price_gems   int not null,
  discount_pct int not null default 0,
  featured_from timestamptz not null,
  featured_until timestamptz not null
);
```
`get-shop` (existing fn) reads the active rotation rows and returns them in the
payload; the client renders the Drip tab + countdown. Purchases post `buy-cosmetic`
to the same fn (deduct Gems server-side, write `ak_player_cosmetics`).

================================================================
## 6. DRIP -- the cosmetics layer (card/board skins, emotes, dog cosmetics) -- Phase 1
================================================================
Pure style, zero stats. The thing players actually pay for.
- **Card skins** = alt art for an owned card (the live shop already loads `cards/<slug>.png` variant art -- a skin is just another art row).
- **Board/arena skins** = themed battle backgrounds (seasonal reskins per `STORYLINE_CANON.md` cities).
- **Emotes** = taunts/celebrations in-match (cosmetic, no gameplay effect).
- **Dog cosmetics** = collars / hats / auras / pilot-rig paint on the dog itself.
- **Crew crests + banners** = social-layer identity (`ak_crews.crest`).

### 6.1 Data model
```sql
create table public.ak_cosmetics (
  id          text primary key,                  -- 'skin_0001_gold', 'board_thelot_neon', 'emote_crownflex'
  type        text not null,                     -- card_skin | board_skin | emote | dog_cosmetic | crew_crest | banner
  name        text not null,
  rarity      text not null default 'Rare',
  applies_to  text,                              -- card_id for card_skin/dog_cosmetic; null otherwise
  art_path    text,                              -- assets/cosmetics/<id>.png (art-factory autoroute)
  source      text not null default 'shop',      -- pass | shop | event
  season_id   int references public.ak_seasons(id),
  price_gems  int,                               -- null if pass/event-only (not directly buyable)
  vaulted     boolean not null default false     -- true after its season ends (FOMO)
);
create table public.ak_player_cosmetics (
  user_id     uuid not null,
  cosmetic_id text not null references public.ak_cosmetics(id),
  acquired_at timestamptz not null default now(),
  acquired_via text,                             -- pass | drop | event
  primary key (user_id, cosmetic_id)
);
```
RLS owner-scoped on ownership; `ak_cosmetics` world-readable.
- **Equipped state** lives in `ak_player_saves` jsonb (`saves.cosmetics = {board, emotes:[], card_skins:{card_id:skin_id}, dog:{...}, crest}`) -- no new write path, the save layer already syncs.
- **Art:** every cosmetic enqueues to the art-factory cron (`ART_AUTOROUTE_DOCTRINE.md`); the rarity-framed fallback in `shop.js artBox()` covers any unpainted asset until the cron lands it. NO generic art ships.

================================================================
## 7. REWARD PACING + "CHOOSE YOUR REWARD" -- Phase 2
================================================================
Adopt the PACING, simplify the SYSTEM.
- Grant something small nearly EVERY pass level (Gold / Scrap / a chest) with HEADLINE rewards (an exclusive card skin, a Mythic chest, a Gem drip) every ~5 levels. Always end the track on a forward pull ("2 levels to the season skin").
- Reuse the existing reward-screen renderer (`renderRewards` in `index.html`) + chest tiers (`economy.js CHEST_TABLE`) as the reward atoms.
- v1 = FIXED track (cheapest). v2 = "choose your reward" (a spendable Crown Star token to claim tiers in any order) -- nice-to-have, not blocking.

================================================================
## 8. SKIP SKUs -- tier skips + battle bundle -- Phase 2
================================================================
Sell TIME, never POWER (clean Lane-A fit).
- A **"Skip a Tier"** Gem SKU + a **"Alley Pass + 10 tiers"** bundle, added to The Drop / dynamic-promos engine (`shop.js` + `alley-kingz-shop`), server-granting the levels via `ak-pass buy-tier` / `buy-bundle`.
- Guardrail: skipping delivers cosmetic/currency/copy rewards FASTER but no stat advantage (cards are level-normalized in ranked). Captures whales + rescues lapsed players from an un-finishable season (cuts end-of-season churn). Small build on existing rails.

================================================================
## 9. KINGPIN CLUB -- subscription layer -- Phase 3
================================================================
Per-season purchase -> recurring MRR (already scoped in `GAME_SHOP_MIRROR.md` /
`ALLEY_KINGZ_CARD_EXPANSION.md`: Master Pass $14.99/mo + Crew Pass $4.99/season).
- A sub auto-grants the Alley Pass each season + a **monthly Gem stipend** + an **exclusive monthly cosmetic** + a **2x earn** modifier (rides the `metaPerks.xpMult` clamp `<=1.25` -- season-scoped variant, still no stat advantage).
- The "Crew" framing ties literally to social-layer crews: a subbed crew gets a banner/crest perk (cosmetic only).
- Heavier: needs **Stripe SUBSCRIPTIONS** (recurring billing, renewals, cancels, dunning) in the edge layer + a clear cancel path (consumer-law) -- a real lift vs today's one-shot Checkout. **Build AFTER the one-season pass proves conversion.**

### 9.1 Data model
```sql
create table public.ak_subscriptions (
  user_id            uuid primary key,
  stripe_customer_id text,
  stripe_sub_id      text,
  status             text not null,              -- active | past_due | canceled
  current_period_end timestamptz,
  last_stipend_at    timestamptz,
  created_at         timestamptz not null default now()
);
```
Stripe webhooks (a new `ak-billing` edge fn) keep `status` truthful; the monthly
stipend grant is idempotent (same unique-lock discipline as `ak_transactions`).

================================================================
## 10. OVERTIME + HOT STREAK -- bonus track + catch-up XP -- Phase 3
================================================================
Two cheap config-level adds on the pass-XP grant.
- **Overtime track**: past max pass level, extra card-skin recolors / crew-crest variants / Gem driblets (`bonus_level` column already in `ak_pass_progress`) so finishers keep earning -- pure cosmetic, autoroute the art. Kills the engagement cliff at completion.
- **Hot Streak (supercharged catch-up)**: if a player misses days, their next few matches grant bonus pass XP -- rides the existing `metaPerks.xpMult` clamp (`<=1.25`), season-scoped, fighting the #1 churn trigger (feeling hopelessly behind). Reads as generosity (the retention doc's surprise-and-delight lever); pairs with the live `ak_streak` drop.

================================================================
## 11. CROWN HEISTS -- live events tied to $BCARDD / city unlocks -- Phase 4
================================================================
AK can't run a real-time Fortnite concert (no realtime infra until social Phase 3),
so an AK "live event" = a **timed limited content beat with a countdown + an exclusive
reward**, anchored to the storyline.
- A weekend **Crown Heist**: a timed limited mode / boss city unlock with a clock + an exclusive cosmetic, themed to `boneguard_crew` / $BCARDD card #0001.
- **City unlocks**: an event opens a featured city early or a special arena reskin (painted via art-factory).
- Marketed as fun + culture; $BCARDD framing stays "fun, never investment" per the hard rule.

### 11.1 Data model
```sql
create table public.ak_events (
  id          text primary key,                  -- 'heist_crown_s1'
  name        text not null,
  type        text not null,                     -- story_beat | crown_heist | city_unlock | crossover
  season_id   int references public.ak_seasons(id),
  payload     jsonb not null,                    -- { rewards, city_unlock, mode, exclusive_cosmetic }
  starts_at   timestamptz not null,
  ends_at     timestamptz not null,
  active      boolean not null default false
);
```
`ak-pass get` (or a small `ak-events get`) returns the active event so the lobby shows
the banner + countdown; rewards grant through the same `claim` discipline.

================================================================
## 12. CHAPTERS + CROSSOVERS -- narrative refresh -- Phase 4
================================================================
- **Chapters** = bigger arcs (quarterly, not every season): a faction-war story beat, a new featured city with a seasonal painted map skin, and a **rotating balance meta** (seasonal card buffs/nerfs = "the new meta") so veterans re-learn. Anchor the narrative to `boneguard_crew` / $BCARDD as the through-line. Art-bound -- pace quarterly. Route all art through the autoroute.
- **Crossovers**: IN-HOUSE brand crossovers ONLY (Onyx POS, Everlight, $BCARDD lore) -- themed cosmetic sets. No external licensed IP unless a real license exists. **IP-discretion law: never feed Rich's unreleased concepts into third-party services; build privately, gate exposure at launch.**

================================================================
## PHASED PLAN (effort + cost)
================================================================
| Phase | What | Infra | Effort | Cost |
|---|---|---|---|---|
| **1** | **The Alley Pass (free+premium, one XP bar) + The Hit List (daily/weekly quests) + The Drop (rotating cosmetic shop w/ FOMO countdown) + Drip (card/board skins, emotes, dog cosmetics)** | Existing Supabase + `ak-pass` + extend `alley-kingz-shop` | ~1-2 weeks | **$0** (Stripe per-txn only; art via existing cron) |
| **2** | **Seasons auto-reset (pg_cron) + headline exclusive (vaulted) cosmetics + Gem-Back Flywheel tuning + Skip SKUs + reward pacing** | Existing stack + pg_cron | ~1 week | **$0** |
| **3** | **Kingpin Club subscription (Stripe subscriptions + `ak-billing` webhooks) + Overtime bonus track + Hot Streak catch-up XP** | Stripe Billing + edge fn | ~1-2 weeks | **$0 fixed** (Stripe fees) |
| **4** | **Crown Heists (timed $BCARDD/city events) + Chapters (story beats + rotating meta) + in-house crossovers** | Existing stack + art-factory | ~2-3 weeks (art-bound) | **$0** |

### Build artifacts per phase
- **Phase 1**: migration `supabase/migrations/20260615_alley_pass.sql` (`ak_seasons`, `ak_pass_progress`, `ak_quests`, `ak_quest_progress`, `ak_cosmetics`, `ak_player_cosmetics`, `ak_shop_rotation` + RLS + the pg_cron daily/weekly refresh); edge fn **`ak-pass`** (`get`, `report-match`, `claim-tier`, `buy-pass`); extend **`alley-kingz-shop`** (`get-shop` returns rotation + cosmetics catalog; `buy-cosmetic`); `index.html` -- fire `ak-pass report-match` from inside `grantMatchRewards(g)`; UI -- **Alley Pass tab** (two tracks, greyed premium beside claimed free), **Hit List panel** w/ claim-all on the lobby, **Drip tab** in the shop, **season countdown** on the lobby; seed Season 1 (`boneguard_crew` / $BCARDD) into `ak_seasons.track`.
- **Phase 2**: migration adds the season-roll pg_cron + `vaulted` flips; `ak-pass buy-tier`/`buy-bundle`; tune `track` Gem payback to ~110%; UI -- vault badge on OG cosmetics, Skip SKUs in The Drop.
- **Phase 3**: migration `ak_subscriptions`; edge fn **`ak-billing`** (Stripe subscription create + webhook handler, idempotent stipend); `ak-pass` reads sub status for auto-grant + 2x earn; UI -- Kingpin Club card + cancel path; Overtime + Hot Streak as config on the XP grant.
- **Phase 4**: migration `ak_events`; `ak-events get` (or fold into `ak-pass get`); UI -- event banner + countdown, limited-mode tile; seasonal city/arena reskins via art-factory; in-house crossover cosmetic sets.

================================================================
## SECURITY / BRAND-SAFETY NOTES
================================================================
- **Server-authoritative everywhere**: every XP/reward/Gem/cosmetic mutation goes through an edge fn (`ak-pass`, extended `alley-kingz-shop`, `ak-billing`) -- the same auth + logging boundary the shop already enforces. The client NEVER mints currency, XP, or cosmetics.
- **Match-XP trust**: bounded + capped client report (max XP/match + daily `xp_today` cap + rate-limit), mirroring `ak-pvp`'s sanity-bound stance. Referee-grade trust arrives with the social-layer deterministic-sim Phase 3. Documented, not hidden.
- **RLS**: every per-player table (`ak_pass_progress`, `ak_quest_progress`, `ak_player_cosmetics`, `ak_subscriptions`) is owner-scoped; definition tables (`ak_seasons`, `ak_quests`, `ak_cosmetics`, `ak_shop_rotation`, `ak_events`) are world-readable, service-role-writable.
- **Auth separation**: AK project + AK OAuth only; redirect glob `https://alleykingz.online/**`. Never touch the casino project.
- **Lane-A law**: pass + shop + events sell TIME and STYLE, never POWER. Cards level-normalized in ranked; the Garage curve stays HP/DMG-only (a maxed Common never beats a base Mythic). All rewards in-game value only -- never cashable, never a tradeable NFT (enforced server-side).
- **Gem-Back is non-cashable**: completers earn ~110% Gems back to buy the next pass + spend in The Drop -- never a withdrawal path.
- **$BCARDD**: marketed as fun + culture, NEVER as an investment, across every pass/event surface.
- **Stripe idempotency**: pass purchase + sub stipend reuse the `ak_transactions` unique-lock discipline (`confirm-gems` is already idempotent) so refresh/retry never double-grants.
- **Consumer-law**: the subscription ships with a clear, frictionless cancel path.
- **Art-factory autoroute**: every cosmetic/season/event asset enqueues to the cron -- NO generic art ships; rarity-framed fallback covers the gap.
- **IP discretion**: crossovers stay in-house; never feed unreleased concepts into third-party services.

================================================================
## THE ONE OPERATOR DECISION
================================================================
**Approve Phase 1 -- The Alley Pass (free + premium) + The Hit List (daily/weekly
quests) + The Drop (rotating cosmetic shop with FOMO) + Drip cosmetics -- to ship on
the existing Supabase free tier, ~1-2 weeks, $0 fixed cost?**

GO = the proven live-service retention engine (a seasonal goal ladder with a deadline,
the quest habit loop, and a cosmetic recapture shop) lands on infra we already pay
for, hooking the ONE reward faucet (`grantMatchRewards`) and the PROVEN shop edge-fn
pattern. The Gem-Back Flywheel turns a one-time ~$5-8 buyer into a permanent grinder,
Lane-A clean. Everything below (seasons auto-reset, subscription, live events,
chapters) branches from this yes.

## THE SINGLE CLEAREST FIRST BUILD STEP
Write + apply `supabase/migrations/20260615_alley_pass.sql` for `ak_seasons` +
`ak_pass_progress` (RLS owner-scoped), deploy edge fn **`ak-pass`** with `get` +
`report-match` + `claim-tier`, and fire `ak-pass report-match` from inside
`grantMatchRewards(g)`. That vertical slice = a player earns pass XP from a real match,
levels the pass, and claims a free-track reward end-to-end. The quests, the premium
track, and The Drop all hang off these two tables.
