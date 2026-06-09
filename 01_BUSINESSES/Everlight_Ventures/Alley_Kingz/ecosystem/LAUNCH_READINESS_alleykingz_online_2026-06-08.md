# Alley Kingz -- Launch Readiness (alleykingz.online)
**Date:** 2026-06-08  **Domain bought:** www.alleykingz.online (.online, ~$0.98 yr1)
**Decision:** games separate from everlightventures.io (house-of-brands). Build stays in the everlight-ventures monorepo; deploys to its own Pages project + own domain.

## What's ALREADY built (verified in code)
- **Front-end <-> backend wired:** `ecosystem/game/shop/shop.js` fetches `/functions/v1/alley-kingz-shop` on the real Supabase (`jdqqmsmwmbsnlnstyavl`). engine.js/canon.js/shop.js all reference the backend.
- **Backend:** 9 tables + 17 RLS policies (`supabase/migrations/20260607_alley_kingz_economy.sql`). Data-safe by row-level security.
- **Shop edge functions (6):** `alley-kingz-shop`, `stripe-webhook`, `verify-arcade-purchase`, `verify-gem-purchase`, `send-purchase-email`. Server-authoritative ("the browser is hostile; may NOT self-grant").
- **Stripe = TEST MODE, fail-closed:** buy-gems/confirm-gems refuse to run against a LIVE key while `AK_SHOP_TEST_MODE` is on. Loot-box (`open-draw`) uses DISCLOSED odds. B-CARDD sweeps explicitly separated.
- **Art:** The Crown daemon paints daily -> alley-kingz.pages.dev. 34/106 cards real (rest fill in as painted).

## Gap to LIVE (not engineering -- access + decisions)
1. **Domain DNS** -- alleykingz.online is NOT yet on Cloudflare (0 zones). The Pages API token can't create zones. NEEDS: add the site in the Cloudflare dashboard (free), change nameservers at the registrar, then add it as a Pages custom domain.
2. **Stripe go-live** -- currently TEST. Flipping to live needs: live keys as Supabase secrets, products/prices, `AK_SHOP_TEST_MODE` off. Per legal, do AFTER the P0 list.
3. **Supabase deploy check** -- confirm the migrations/functions are applied to the live project (code exists locally; SUPABASE_ACCESS_TOKEN is in .env for verification).

## Legal P0 -- BEFORE public + charging (Imani Calder)
1. Gaming LLC holds the IP/domain/Stripe (entity separation).
2. ToS/EULA + Privacy Policy (CCPA/GDPR) + refund terms, linked.
3. COPPA-compliant age gate.
4. Footer: "Alley Kingz is not affiliated with, endorsed by, or sponsored by Supercell Oy or Clash Royale."
5. Trade-dress scrub: card frame, resource bar, arena layout, HUD all confirmed DIFFERENTIATED from Clash Royale (mechanics are fair game; look-and-feel is the risk).
6. Asset provenance log -- every art file original + dated.
7. Confirm zero redeemable-coin/cash-out anywhere (pay-to-play + cosmetics = clean, not gambling).
P1: USPTO "Alley Kingz" filing (privileged clearance first), DMCA agent, outside IP clearance opinion, loot-box odds-disclosure policy.

## Monetization starter stack (Aisha Bello)
- **Launch SKUs (keep simple):** Founder packs ($9.99/$24.99/$49.99), Rewarded video (gems for a watch), Cosmetics, Daily-login streak + trophy ladder (the retention spine).
- **Day Pass ($1.99/24h):** unlocks Arcade Mode (unlimited fast runs, 2x coins, rotating modifiers) + ad-free day + a cosmetic chest. 7-day $9.99 anchor.
- **AdSense reality:** runs on CONTENT pages (home/blog/patch-notes/leaderboard), NOT in-gameplay (flag risk). RPM ~$2-8; ~1M pageviews ~= $2-8k. Rewarded video ($10-40 RPM) beats AdSense once there's a game loop. IAP carries launch; ads are a scale play.
- **Math:** $1k = ~3k signups x 3% pay x ~$11. $10k = ~25-30k MAU. $100k = ~250k MAU / paid-UA machine. Get payer% ~4% + D1 ~35% BEFORE pouring UA money.
- **First UA test:** $300-500 across 3-5 "dopamine-moment" hook creatives -> measure CPI vs ARPU.

## Recommended sequence
1. Domain live (Cloudflare add-site + NS) -> game public on www.alleykingz.online, FREE/test mode.
2. Legal P0 in place (LLC, ToS, privacy, age-gate, disclaimer, trade-dress scrub).
3. Flip Stripe live + ship Founder packs + Day Pass + rewarded video.
4. First UA creative test. Then scale.

*Contributors: Imani Calder (legal), Aisha Bello (growth), infra audit (Lucrex). Advisory, not formal legal advice.*
