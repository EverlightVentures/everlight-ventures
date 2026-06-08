# B-CARDD BET -- HANDOFF for the main Blackjack chat
**Date:** 2026-06-04 (built) | **Updated:** 2026-06-07 (table polish shipped to prod) | Paste/reference this in the blackjack conversation so it knows exactly what was built here.

> **2026-06-07 UPDATE (main blackjack chat):** The cosmetic dealer-video gap in Open TODO #3 is **CLOSED** and three table fixes shipped to **production** (`everlightventures.io`, not just the preview). See the "2026-06-07 table polish" section below before reading the rest.

> **2026-06-08 UPDATE -- BACKEND DEPLOYED, FEATURES IN OWNER-GATED TEST.** Rich supplied a valid Supabase token (account "EverlightVentures's Project"). Ran `deploy_blackjack_backend.sh`: both migrations applied + `blackjack-api` edge deployed (dealer-ai, buy-coaching-pass, jackpots_won, stats_only). Smoke-tested `dealer-ai` live -> real AI reply, 0 Gold for the owner (dev-free). Frontend activated: `LEADERBOARD_SP_FEED=true` (global), Pro Coaching live but `COACHING_PUBLIC=false` (owner `1m.rich.gee@gmail.com` only). B-Card still beta (every 12 cards, owner-only). NEXT: Rich tests -> approve -> flip `COACHING_PUBLIC=true` + `BCARD_BETA_MODE=false` for public launch.

## TL;DR
We designed + built **Phase 1** of "the B-CARDD BET": $BCARDD's signature card as a 1-in-a-million jackpot
on the EXISTING VIP (Spanish 21) blackjack table. It is BUILT, VERIFIED (no-throw + logic tests), and
DEPLOYED to a PREVIEW. Production `main` is untouched. Real-money cash-out is Phase 2 (gated on legal).

## The mechanic (locked design)
- **The B-Card** = $BCARDD's crowned-B card, shuffled into the VIP table's shoe. Plays mechanically as an
  **8** (B = 8). Odds **1 in 1,854,799 cards** ("$BCARDD" in digits: $1 B8 C5 A4 R7 D9 D9).
- **On a hit, the player CHOOSES (optional jackpot):**
  - **TAKE IT** = auto-win the hand at **100x** their average bet (house-staked, risks nothing).
  - **RIDE IT** = the B-Card stays as the 8, play continues at the normal bet; the NEXT hand is a "Golden
    Hand" worth **200x** -- but ONLY if they BEAT THE DEALER (push/lose = jackpot gone).
- **Average bet** = real **Quarter-To-Date (QTD)** per-player average, reset each quarter, like a casino
  reward-points/player rating. Sub-20-hands fallback = table minimum. Drives Tier 1/2/3 brackets.
- **Payout cap = 888** (lucky-8, hard cap any tier). Replaces the old 777 / IS the progressive, tailored per player.

## Economy (why it makes money + is self-funding)
- **Dual currency (sweeps model):** sell **Gold Coins** (for-fun, NOT redeemable); **Sweeps Coins (SC)** are
  the redeemable prize coin, given FREE (bonus + daily + a real no-purchase mail-in AMOE). NEVER sell SC.
- Revenue = Gold sales. Cost = SC redemptions (small: house edge grinds SC + playthrough + non-redemption).
- **Self-sufficient loop (Rich's model):** jackpot DRAWS players -> they buy Gold -> Gold = profit; payout
  is a multiple of their OWN avg bet that the house edge already profited from. Math: B-Card fires ~1/370k
  hands, house edge banks ~18,500x avg_bet around each hit vs <=888 payout = ~90x cushion. Self-funding.
- **Reserve:** = your payout cap x ~1.5. At an 888 cap that is ~$1,332. At scale it is ~1-2 weeks of expected
  payout (a small % of Gold revenue; the ratio is constant at any volume).
- **DO NOT gate the prize on Gold purchases (illegal).** The spend-link happens implicitly: free SC is tiny,
  so only buyers build an SC average big enough to approach 888. Economics gate it, not a rule.
- **Packages (starting point):** Rookie $4.99/5k GC+5SC, Player $9.99/12k+10, Baller $19.99/25k+20,
  High Roller $49.99/70k+55, Kingpin $99.99/150k+120. 3 tuning dials: free-SC size / house-edge ~5% / playthrough+min.

## Legal (kosher)
- It is a legal SWEEPSTAKES (not gambling) IFF: SC always obtainable FREE + never required to buy, the free
  path is genuine, banned states (WA/MI/ID/NV + 2024-25 list) are geo-blocked. The B-Card is just the prize.
- **Phase 1 = for-fun chips, NO cash-out = NOT gambling = zero legal gate (already shippable).**
- **Phase 2 = real cash-out:** needs LLC (not sole prop), sweeps-friendly payment processor (Stripe bans it),
  KYC/AML, NPN disclosures, + a gaming/sweepstakes attorney sign-off. Rich is using the in-house legal team
  now and deferring an external attorney until revenue justifies it (sound -- Phase 1 needs no attorney).

## What was BUILT (Phase 1, for-fun chips) -- code is LIVE on the preview
Files (in `06_DEVELOPMENT/vantaris/`):
- `src/lib/blackjack-engine.ts` -- the B-Card core: `isBCard` field, `BCARD_ODDS/CAP(888)/TAKE(100)/RIDE(200)`,
  `shouldDealBCard` (beta = every-50 owner-only / prod RNG), `makeBCard` (rank 8), `bcardPayout` (cap + ride-lose=0).
  16/16 node unit tests pass.
- `src/lib/blackjack-store.ts` -- QTD avg (quarterly reset + sub-20 fallback, 8/8 tests), VIP-gated draw
  intercept (`drawPlayerCard`/`isVip`, gated to `tableType==='vip'`), `bcardTake`/`bcardRide`, Golden Hand
  settlement, `BCARD_BETA_MODE` flag (currently TRUE for beta, owner-gated).
- `src/components/blackjack/BCardOverlay.tsx` (NEW) -- Take/Ride choice UI + GoldenHandBanner.
- `src/app/play/blackjack/page.tsx` + `src/app/vantaris/blackjack/page.tsx` -- render overlay, feed email,
  log via `record-hand` side_bets, lobby sets `config.tableType`.

## 2026-06-07 table polish (shipped to PRODUCTION) -- commit `e06577c` on `origin/bj-finish`
Three fixes from a live-table screenshot review, all verified on the live edge (`everlightventures.io`):
1. **Dealer placement.** The dealer was anchored to the top "window" panel -- small, high, read as "a picture on
   the wall." Pulled the dealer group OUT of the window down to table center (`top-[88px] md:top-[104px]`),
   scaled UP to the focal point (`DealerStage size={128}`), name/title stacked, spoken line as a clamped
   caption. Dealer cards dropped onto the felt (`top: 36%`, `scale(1.12)`). Chip tray + bet spots stay
   un-occluded. Files: `src/app/play/blackjack/page.tsx`.
2. **Canonical deal order.** ONE source-of-truth constant drives both the dealing animation AND hand
   resolution: `SEAT_DEAL_ORDER = [4, 3, 2, 1, 0]` (first base on the RIGHT, clockwise, dealer last) +
   `orderActive()` helper + `HOME_SEAT = 2` (the human, never reordered). To flip to "Seat 1 on the left"
   it is a literal one-line change to `[0,1,2,3,4]`. File: `src/lib/blackjack-store.ts`.
3. **Multi-hand lock KILLED.** Betting 2 hands one round used to FORCE 2 hands next round (active-hand count
   persisted across rounds). Now every new round resets to the single `HOME_SEAT`; active hands are derived
   from seats staked THIS round; CLEAR (`resetToHomeSeat()`) drops back to one hand during betting. No
   carryover, no lock. Files: `src/lib/blackjack-store.ts` (`newRound`, `toggleSeat`, `resetToHomeSeat`),
   `src/app/play/blackjack/page.tsx` (CLEAR wiring).
4. **Dealer video = `official_bdl.mp4`** (the new official B-CARDD dealer footage). Wired in
   `src/components/blackjack/DealerStage.tsx` (`DEALER_VIDEOS.bcardd -> '/dealers/official_bdl.mp4'`), asset
   force-added past gitignore at `public/dealers/official_bdl.mp4` (2,768,590 bytes). **This closes the
   Open TODO #3 dealer-video-404 gap below.** Live: `https://everlightventures.io/dealers/official_bdl.mp4` -> 200.

## 2026-06-07 SESSION 2 -- cinematic + leaderboard reality + the one blocker
Rich asked to do, in order: (1) B-Card reveal cinematic, (2) leaderboard/high scores,
(3) Phase-2 cash-out prep, (4) hold for his visual polish call.

**(1) B-CARD REVEAL CINEMATIC -- DONE + LIVE on prod.** Commit `1982df8`. Rewrote
`BCardOverlay.tsx`: the 1-in-a-million hit now plays a real 3D card flip (rotateY,
crowned-B face that plays as an 8) + gold ray burst + flash + `playBlackjack()`
sting, then "THE B-CARDD BET" slams in and the TAKE/RIDE panel rises. Pure local
presentation (no new store phase). ALSO fixed a live bug: the overlay still pointed
at the dead `bcardd_live.mp4` (404) -> now `official_bdl.mp4`. Built green on e5,
deployed (run 27107844007, success).

**(2) LEADERBOARD -- IT WAS ALREADY LIVE WITH REAL DATA.** Key finding: the
`blackjack_leaderboard` table EXISTS in prod, is populated with real players
(XX_ACE_OF_DIAMONDS_X 8.88M/318 hands, OpusV2, Melina Tapiz, AuditBot, SmokeTest),
has the full column set incl `jackpots_won`, and is anon-readable (RLS already
public-read). So `getLeaderboard()` already returns real data -- the "fake DarkStar
fallback" only shows when the live query is empty, which it isn't. The component +
read path were never broken.
  - The ONE real gap: `jackpots_won` is 0 for everyone because NOTHING ever
    increments it. Built the fix (commit `fed2704`): edge `record-hand` now takes a
    `jackpot` flag (+`jackpots_won`++) and a `stats_only` mode that feeds stats/board
    WITHOUT mutating chip_balance (so single-player's local wallet can't drift the
    server balance -- the XLM-bot reconciliation trap). Added a fail-safe frontend
    `recordLeaderboardHand()` + a single-player feed.
  - The migration `supabase/migrations/20260607_blackjack_leaderboard.sql` is now a
    REPRODUCIBILITY artifact only (idempotent; the prod table already matches). Do
    NOT need to apply it -- the table exists.
  - SP feed is GATED OFF (`LEADERBOARD_SP_FEED=false`, commit `851f769`) until the
    edge is redeployed, else the OLD edge (no stats_only) would drift signed-in
    players' balances.

**THE ONE BLOCKER (token):** activating jackpots_won + the SP feed needs the updated
`blackjack-api` edge function DEPLOYED. Every Supabase access token in the workspace
(.env, e5 .env, creds, proton_pass_import.json) returns 401 even via the official
`supabase` CLI -- they're for a different account/org than project
`jdqqmsmwmbsnlnstyavl` (NOT expired -- wrong account). The valid Management token is
in Rich's Proton Pass vault. Deploy command (Rich, ~30s):
  `SUPABASE_ACCESS_TOKEN=<valid> supabase functions deploy blackjack-api --project-ref jdqqmsmwmbsnlnstyavl --no-verify-jwt`
Then flip `LEADERBOARD_SP_FEED=true` in `play/blackjack/page.tsx` + redeploy frontend.

**(3) PHASE-2 CASH-OUT PREP -- groundwork already largely EXISTS; the rest is
LEGAL-GATED (do not blind-build).** Inventory:
  - `redeem_requests` table (migration `20260602000100`): SC redemption + KYC store,
    status enum pending/review/approved/paid/rejected, RLS insert-own/select-own. GAP:
    the `/redeem` page collects KYC then THROWS IT AWAY on an alert() -> needs wiring
    to this table. (Safe to wire; no legal gate to STORE a request.)
  - `game_currencies` (casino_empire + blackjack-api): per-currency balances via
    `currency_name` -- the dual-currency (Gold/Sweeps) substrate already exists.
  - Stripe purchase + webhook + verify-* functions exist (Gold sales = revenue).
  - STILL OPEN (server-auth slice 1 = the record-hand stats_only above): `bcard-resolve`
    server-authoritative B-Card RNG+payout (TODO #1), AMOE free-entry, formal SC
    currency + redemption + KYC/AML + sweeps-friendly processor. These are gated on
    LLC + attorney per the Legal section -- scope, don't ship.

## 2026-06-08 -- PRO COACHING (premium AI dealer, Gold-funded) -- commit `26a662a`
Rich wants the AI dealer that teaches blackjack to be a PREMIUM, self-funding feature
(its cost covers the AI subscription at a 3x markup). Built it COMPLIANT:
  - **Two tiers.** FREE = the existing instant static strategy hints (`dealer-chat`
    action, $0, no tokens) -- stays free for everyone so no player is EVER required to
    pay for help (compliance anchor). PREMIUM = a conversational AI tutor (Perplexity
    `sonar`) that answers anything + explains why.
  - **Paid in GOLD COINS, never SC.** Rich said "SC" but that would break the
    sweepstakes safe harbor (SC must stay free + redeemable-only). Switched to Gold
    (chip_balance) -- the purchasable for-fun currency -- per the compliance fork.
    Decision confirmed with Rich (GC, recommended).
  - **Pricing (Rich chose BOTH):** pay-per-message = Gold `max(15, ceil(3x token cost))`
    (~17 GC/msg at sonar rates), AND a Coaching Pass = 250 Gold for 24h unlimited.
    Config constants top of `blackjack-api` (GC_PER_USD, COST_MULTIPLIER=3, etc.).
  - **Server-authoritative + unspoofable:** balance check + Gold deduction + the LLM
    call ALL happen in the edge fn (`dealer-ai` + `buy-coaching-pass` actions). The
    browser can't force a free reply or fake a deduction. Dev/owner email coaches free.
  - **Files:** `supabase/functions/blackjack-api/index.ts` (2 new actions + helpers),
    `supabase/migrations/20260607_coaching_pass.sql` (coaching_pass_until column),
    `src/components/blackjack/DealerChat.tsx` (PRO toggle + pass UI + Gold cost,
    gated behind `PRO_COACHING_ENABLED=false`). Frontend builds + deploys but the
    premium UI is HIDDEN until the edge is deployed (free chat unchanged, zero regression).
  - **Activation (same one blocker -- the Supabase token):** deploy `blackjack-api`,
    apply the coaching_pass migration, set `PRO_COACHING_ENABLED=true`, ensure
    `PERPLEXITY_API_KEY` is set on the function. Then it's live.

## DEPLOY status
- Built on **e5-mother** (phone proot SIGSEGVs on npm build). The `bj-finish` branch now auto-deploys to
  **PRODUCTION** via GitHub Action `.github/workflows/deploy-vantaris.yml` (triggers on push to
  `[main, everlightventures.io, bj-finish]`, path-filtered to `06_DEVELOPMENT/vantaris/**`, builds on the
  ubuntu runner, ships to CF Pages production).
- **LIVE on production:** https://everlightventures.io/play/blackjack  (B-CARDD Phase 1 + the 2026-06-07
  table polish are both live here).
- Original Phase-1 preview (still valid): https://bj-finish-preview.everlightventures.pages.dev
- Commits on `origin/bj-finish`: `9d0ef72` (B-CARDD Phase 1, 6 files) + `e06577c` (2026-06-07 table polish).
  Deploy recipe in memory `reference_cf_pages_deploy_from_proot` (vantaris section).
- Flip `BCARD_BETA_MODE=false` for true prod odds (still TRUE / owner-gated for beta).

## Open TODOs / Phase 2 (for the main blackjack chat to finish)
1. **Server-authoritative** (REQUIRED before real money): move the B-Card RNG + avg-bet + payout to the
   `blackjack-api` edge function (a `bcard-resolve` action). Today it is client-side (fine for for-fun, spoofable).
2. **Gold/Sweeps real cash-out:** add the dual-currency ledger, the AMOE free-entry, redemption + KYC. (The
   frontend already has a `gameMode:'sc'` + `sweepsCoins` notion to build on.)
3. **Dealer video asset -- DONE (2026-06-07).** ~~`bcardd_live.mp4` 404s on the preview~~ -> replaced by
   `official_bdl.mp4`, committed to `public/dealers/`, live (200) on prod. STILL OPEN: give the B-Card a
   dedicated REVEAL animation using the buff $BCARDD dealer (the video plays dealing-motion in sync now, but
   the 1-in-a-million B-Card hit has no special cinematic yet).
4. **Roll the B-Card into the other card games** with the same odds + handler.
5. Confirm/tune the Tier 1/2/3 thresholds (defaults: <=100 / <=1,000 / above).

## Spec docs (full detail)
`Everlight_Gaming/Blackjack/BCARDD_BET_SPEC.md` (mechanic+economy+legal+phasing),
`BCARDD_PACKAGES_AND_MATH.md` (products + the money math), `Everlight_Gaming/MONETIZATION_LEGAL_LANES.md`
(loot-box vs sweeps), `Alley_Kingz/ecosystem/LEGAL_TRADEMARK_DEFENSE.md` ($BCARDD name defense).
