# Everlight Ventures / Vantaris -- Unified Analytics & Data-Capture Architecture

**Version:** v1 (2026-06-02) · **Status:** canonical synthesis of 5 design lanes · **Project:** `jdqqmsmwmbsnlnstyavl`
**Mandate (operator, verbatim):** "fully utilize Supabase for the entire website. Any data we receive or should receive must be logged and documented. Mirror Google Analytics. Track everything. High scores for the games, the wholesaling area, the whole site."

This document is the single source of truth. The migration SQL, the event taxonomy, and the `analytics.ts` `track()` calls are **one contract** -- same event names, same property keys. Provenance is cited per section: `[L1]` inventory, `[L2]` schema, `[L3]` taxonomy, `[L4]` instrumentation, `[L5]` privacy.

---

## 0. The two-collector decision (already made, not re-litigated) `[L3][L5]`

| Layer | Collector | Owns | Cost |
|---|---|---|---|
| Edge pageview / perf / Web Vitals | **Cloudflare Web Analytics** (cookieless, no banner) | raw traffic, Core Web Vitals, bot filtering | free |
| Product analytics + high scores + leads + funnel | **First-party Supabase event store** | every event, every join to `casino_players` / `web_leads` | free (own infra) |

`page_view` is intentionally captured in **both** `[L3]`: Cloudflare for traffic/perf, Supabase for funnel/cohort joins. They are complementary, not redundant. No paid vendor, no ad/martech pixel (free-first law).

---

## 1. SURFACES -- what produces loggable data, and its state today `[L1]`

The full 25-surface inventory `[L1]` collapses into five capture lanes. **Persists today (the short list):** lead forms -> legacy `public.leads`; Supabase Auth users; **Dice rounds only** -> `casino_game_rounds` + `casino_players.gold_coins`. **Everything else is LOST.**

| Lane | Surfaces | State today `[L1]` | After this build |
|---|---|---|---|
| **Engagement** | page views, clicks, sessions, scroll, search, game opens, outbound clicks (surfaces 20-25) | **0 tracking** -- no script in `layout.tsx`, grep for gtag/plausible/posthog/beacon = 0 hits | `page_view` + `click` + `scroll_depth` + `search` + `session_start` -> `analytics_events`/`page_views`/`sessions` |
| **Auth** | signup/login/Google/guest (surface 4) | only `auth.users` row; display_name + guest id in localStorage | `sign_up` / `login` events + `identify()` stitch |
| **Games** | blackjack, crash, dice, mines, plinko, roulette + multiplayer (surfaces 9-15) | **only Dice** persists; blackjack posts to a DEFERRED/unreachable Django endpoint; crash/mines/plinko/roulette import nothing; multiplayer chat/presence ephemeral | every round -> `casino_game_rounds` (via `persistRound`) + `game_round` event + `high_score_set` |
| **Commerce** | Stripe checkout, wallet, daily SC bonus (surfaces 16-18) | checkout funnel lost client-side; SC/gems/non-dice GC deltas localStorage-only; no ledger | `checkout_started` (client) + `checkout_completed` (server webhook truth) + `lead_captured` |
| **Wholesale** | off-site `leads_db.json` (~3,475 records) | lives entirely outside the site | site form -> `web_leads`; pipeline mirror -> `wholesale_events` |

**Compliance gap flagged `[L1][L5]`:** the `redeem` page captures full legal name, DOB, address, ZIP, payout method then throws it away on an `alert()`. That is an AML/KYC record that must be stored in its OWN table (NOT analytics) -- see Open Conflicts; out of scope for this migration but called out so it is not forgotten.

---

## 2. TABLES -- the schema `[L2]`

One idempotent migration (`supabase/migrations/20260602000000_track_everything_analytics.sql`). Eight objects. **Every table here is written by an instrumented code path `[L4]` -- no orphan tables.**

| # | Object | Type | Written by `[L4]` | Read by |
|---|---|---|---|---|
| 1 | `sessions` | table | `ensureSession()` insert + `last_seen` update | `site_traffic_daily`, own-row auth read |
| 2 | `analytics_events` | table | `track()` / `trackPageView()` batched flush | own-row auth read; dashboard via service_role |
| 3 | `page_views` | table | `trackPageView()` (narrow mirror of `page_view`) | `site_traffic_daily` |
| 4 | `high_scores` | table | `submitHighScore()` on `high_score_set` | **public read** (boards render for everyone) |
| 5 | `web_leads` | table | `notify-lead` edge fn (server) on `lead_captured` | own-row auth read |
| 6 | `wholesale_events` | table | Broker_OS -> Supabase sync job (service_role) | service_role only (pipeline internal) |
| 7 | `casino_leaderboard` | view | (derived from `casino_game_rounds`) | **public** (anon + auth GRANT) |
| 8 | `site_traffic_daily` | view | (derived from `page_views`) | authenticated only (internal report) |

**Design decisions kept from L2:**
- `analytics_events.props jsonb` + **GIN index** so `props->>'game'` / `props->>'source'` queries are fast. This is why we do NOT need a wide column per event type.
- `high_scores.score numeric` holds both multipliers and integer scores; `(game, period, score DESC)` index for board reads.
- `wholesale_events.lead_id` is **`text`** -- verified against the real file: keys are `lead_ad8eec735f` / `leg_*` style, NOT uuid. `[L1][L2]` cross-checked against `leads_db.json` (3,475 records).
- `web_leads.email` is **nullable** -- list-tool submissions may omit it `[L2]`.
- Legacy `public.leads` is left untouched for back-compat; `web_leads` is the forward path `[L2]`.
- `casino_leaderboard` uses `CROSS JOIN LATERAL VALUES` for daily/weekly/monthly/all_time in one view + `RANK() OVER (PARTITION BY game, period)` `[L2]`.

**Conflict resolved (table count):** L4 sketched a thin `analytics_events` column set (`path`, `ts`, `inserted_at`); L2's table uses `page`, `created_at`. **L2's schema wins** (it is the migration). `analytics.ts` `[L4]` is rewritten so the inserted object keys (`event_name`, `page`, `referrer`, `props`, `anon_id`, `session_id`, `user_id`, `created_at`) match L2's columns exactly -- see §4.

---

## 3. EVENTS -- the taxonomy (the contract) `[L3]`

**Naming law `[L3]`:** `snake_case`, max 40 chars, names are STABLE (new behavior = new event, never a rename). Adding a property = safe; renaming/removing a required prop = breaking change needing a new versioned name.

**Auto-attached to every event by `analytics.ts` (do not redeclare per-event) `[L3][L4]`:** `event_name`, `anon_id`, `session_id`, `user_id` (null if anon), `page`, `referrer`, `created_at` (client ISO; server stamps its own `created_at` default too). Money: integer cents for `USD`, native integer units for `GC`/`SC`, never floats.

### Conflict resolved -- event names `[L3] vs [L4]`

L3 (taxonomy) and L4 (instrumentation sketch) used **different names** for the same events. The taxonomy is the contract authority, so **L3 names win** and `analytics.ts` track() calls are rewritten to match. Final canonical set:

| Canonical (L3 wins) | L4 had sketched | Verdict |
|---|---|---|
| `lead_captured` | `lead_submit` | L3 -- GA4 `generate_lead` parity |
| `checkout_started` | `checkout_start` | L3 -- GA4 `begin_checkout` parity |
| `checkout_completed` | `purchase` | L3 -- server-confirmed only |
| `game_round` | `game_round` | agree |
| `game_started` | `game_bet` | L3 |
| `game_cashout` | `game_cashout` | agree |
| `high_score_set` | `high_score` | L3 |
| `sign_up` / `login` | `signup` / `login` | L3 |
| `search` | `tool_search` | L3 (`search_scope` distinguishes tools/site/wholesale) |
| `outbound_click` | `outbound_click` | agree |

### Domain: Engagement
| Event | When | Required props | Optional |
|---|---|---|---|
| `page_view` | every route commit | `page_path`, `page_title` | `page_query`, `load_ms` |
| `session_start` | first event of a session (30-min idle rolls new id) | `session_id`, `is_first_session` | `landing_path`, `utm_source/medium/campaign/content/term`, `referrer_domain` |
| `click` | tracked CTA/nav/button click | `target` | `target_text`, `section` |
| `scroll_depth` | crosses a depth threshold | `percent` (25/50/75/90/100) | `max_percent` |
| `search` | find-tools / site / wholesale search | `search_term`, `search_scope` | `results_count`, `filters` |
| `outbound_click` | link leaving origin | `outbound_url`, `outbound_domain` | `target` |

### Domain: Auth
| Event | When | Required | Optional |
|---|---|---|---|
| `sign_up` | auth user committed | `method` (email/google/magic_link) | `referral_source` |
| `login` | existing user authenticates | `method` | `days_since_last_login` |

> On first auth event, `identify(userId)` stitches `anon_id -> user_id` for the rest of the session (GA4 user-id stitching). `[L3][L4]` A **single** `identity_link` row is also written so pre-login funnel joins to the account; historical anon rows are NOT retro-stamped (keeps deletion clean) `[L5]`.

### Domain: Commerce
| Event | When | Required | Optional |
|---|---|---|---|
| `lead_captured` | lead form submit success (the notify-lead path) | `source` (wholesale/onyx/hivemind/alley-kingz/logistics/consulting/list-tool) | `page_path`, `utm_source`, `utm_campaign`, `message_len` -- **NO raw email/phone/name in props** `[L5]` |
| `checkout_started` | Stripe session created / redirect | `value` (cents), `currency` (USD), `product` | `plan_interval`, `quantity`, `checkout_session_id` |
| `checkout_completed` | Stripe `checkout.session.completed` (server webhook ONLY) | `value` (cents), `currency`, `product`, `transaction_id` (dedupe key) | `is_first_purchase`, `coupon` |

> `checkout_completed` is the **only revenue-truth event** and is fired **server-side from the Stripe webhook**, never the client `[L3]`. `transaction_id` is the idempotency key so webhook replays do not double-count.

### Domain: Games  (`game ∈ blackjack | crash | dice | mines | plinko | roulette`)
| Event | When | Required | Optional |
|---|---|---|---|
| `game_started` | round/hand initiated or bet placed | `game`, `currency` (GC/SC) | `bet_intent`, `table_id`, `entry_balance` |
| `game_round` | round resolves (1:1 with a `casino_game_rounds` row) | `game`, `currency`, `bet`, `win`, `net`, `multiplier`, `round_id` | `xp_earned`, `balance_after`, `is_win` |
| `game_cashout` | mid-round cashout (crash/mines) | `game`, `currency`, `cashout_multiplier`, `payout` | `round_id` |
| `high_score_set` | new personal/global best | `game`, `score`, `score_type` (max_win/max_multiplier/win_streak/net_session), `scope` (personal/global) | `currency`, `previous_best`, `round_id` |
| `level_up` | XP threshold crossed | `new_level`, `xp_total` | `rank_name`, `trigger_game` |

> **Wiring reality `[L1]`:** only Dice calls `persistRound()` today. `game_round` rides **alongside** the `saveGameRound()` insert inside `persistRound()` (the one chokepoint), so wiring crash/mines/plinko/roulette/blackjack to `persistRound` simultaneously fixes the LOST DB rows AND emits the analytics event from one place `[L1][L4]`. `high_score_set` is a **derived** event -- fire it in addition to, not instead of, `game_round` when a best is beaten, and it triggers `submitHighScore()` -> `high_scores` table.

### Domain: Wholesale
| Event | When | Required | Optional |
|---|---|---|---|
| `wholesale_lead_created` | wholesale lead record created (site form or pipeline mirror) | `lead_id`, `source` (site_form/distress/probate/tax_delinquency/teardown/zillow/skiptrace) | `state`, `city`, `property_type`, `est_value` |
| `wholesale_status_changed` | pipeline stage transition | `lead_id`, `from_status`, `to_status` | `changed_by`, `reason` |

> These map to the `wholesale_events` table (server-side sync, service_role). `state` is logged for reporting; the TN-only autonomous-outreach gate is a **pipeline** concern, not analytics `[L3]`. Property-owner PII stays firewalled in Broker_OS -- **never** in `wholesale_events.props` or any site analytics path (Streubel eradication law) `[L5]`.

**GA4 parity mapping (for any future BigQuery export) `[L3]`:** `lead_captured`->`generate_lead`, `checkout_started`->`begin_checkout`, `checkout_completed`->`purchase`; `session_start`/`page_view`/`sign_up`/`login`/`search` keep GA4 names 1:1.

---

## 4. INSTRUMENTATION -- how it ships `[L4]`

Three new/edited files + the CF beacon.

- **`src/lib/analytics.ts`** (new) -- SSR-safe, never-throws, fire-and-forget batched flush into `analytics_events`. Public API: `track(name, props?)`, `trackPageView(path)`, `trackPageViewRow(path, title, durationMs)` (writes the narrow `page_views` row), `ensureSession(utm?)` (upserts `sessions`), `submitHighScore(...)` (writes `high_scores`), `identify(userId)`, `getAnonId()`, `getSessionId()`. **The inserted object keys match L2's columns exactly:** `{ event_name, page, referrer, props, anon_id, session_id, user_id, created_at }`. `anon_id` = random UUID in `localStorage` (NOT a cookie -- keeps out of strict cookie-consent regimes) `[L5]`. 30-min idle session window. Max queue 500, batch 25, 4s flush, flush on `visibilitychange`/`pagehide`.
- **`src/components/shared/AnalyticsProvider.tsx`** (new) -- `'use client'`. Auto-fires `page_view` on every App Router nav (`usePathname` + `useSearchParams`, wrapped in `Suspense`), calls `ensureSession()` once on mount, and syncs `identify()` with `supabase.auth.onAuthStateChange`. Renders nothing. Mounted inside `ClientLayout` just under `AuthProvider`.
- **`src/app/layout.tsx`** (edit) -- add the Cloudflare beacon via `next/script strategy="afterInteractive"` as the last child of `<body>`. CF token from dashboard -> Web Analytics -> `everlightventures.io`. CF does NOT see SPA route changes well, which is exactly why first-party `trackPageView` is the source of truth for product pageview counts `[L4]`.
- **`src/lib/casino-engine.ts` `persistRound()`** (edit) -- add `track('game_round', {...})` right after `saveGameRound()` so all six games (once they call `persistRound`) emit the event from one chokepoint.

**track() placement (canonical names from §3) `[L4]` corrected to match taxonomy:**
- Lead forms (sell/wholesale/onyx/hivemind/alley-kingz/logistics/consulting/list-tool) -> `track('lead_captured', { source, page_path })` on submit success. The actual lead row + email go through the `notify-lead` edge fn -> `web_leads` (server holds the PII) `[L5]`.
- `find-tools` -> `track('search', { search_term, search_scope: 'tools', results_count })`.
- `persistRound` chokepoint -> `track('game_round', {...})`; bet placed -> `track('game_started', {...})`; crash/mines cashout -> `track('game_cashout', {...})`; new best -> `track('high_score_set', {...})` + `submitHighScore(...)`.
- Checkout: button -> `track('checkout_started', { value, currency:'USD', product })`; **`checkout_completed` fires server-side in the Stripe webhook, NOT here** `[L3]`.
- Auth success branches -> `track('sign_up'|'login', { method })` then `identify(userId)`.

---

## 5. PRIVACY -- the guardrails `[L5]`

**The one direct conflict, resolved: "track everything" vs the law `[L5]`.** Rule: **track every *event* (100% behavioral breadth -- Google-level coverage), but put zero raw PII *value* in the event stream.** You still answer "who did what" by joining `analytics_events.user_id -> casino_players`, and "which leads converted" by joining to `web_leads.id`. PII lives once, in its system-of-record, behind RLS; analytics references it by key.

**RLS model (enforced in migration) `[L2][L5]`:** anon + authenticated may INSERT into all ingest tables; authenticated read **only their own** rows (`user_id = auth.uid()`); `high_scores` + `casino_leaderboard` are **public read** (boards render for everyone); `web_leads`/`page_views`/`analytics_events` are NOT anon-readable (no exfil); `wholesale_events` has no anon/auth SELECT (service_role only). `sessions` allows anon UPDATE for `last_seen`.

**Green list (log freely) `[L5]`:** event_name, route (query-stripped), referrer_host, anon_id, user_id, session_id, game/currency/bet/win/net/multiplier/xp, funnel step + source (NOT contents), coarse device class (bucketed, not raw UA), coarse geo (country/region; city wholesale-only), Web Vitals.

**Hard DO-NOT-LOG list (deny-by-default `sanitizeEventProps()` allow-list at ingest) `[L5]`:** passwords/tokens/JWTs/API keys; full PAN/expiry/CVV (Stripe holds card data -- events get only `checkout_completed` + Stripe `transaction_id`); raw email/phone/full names in props; gov IDs (SSN/DL/passport); precise geo (lat/long, street address); bank/routing/crypto keys; raw IP (use derived geo or 7-day daily-salted hash); free-text message bodies (store in the lead row, not analytics). **Wholesale property-owner PII is categorically excluded from the site events store and Cloudflare** -- stays in Broker_OS behind the eradication gate.

**Retention `[L5]`:** raw `analytics_events` 90 days (nightly cron `DELETE WHERE created_at < now()-90d`, roll up to aggregates first); aggregates 25 months (GA4 parity + YoY); game rounds / high scores retained (product record, no contact PII); `web_leads` active + 24mo then archive per memory-pipeline no-delete-without-archive law; salted IP hash 7 days max.

**Posture `[L5]`:** cookieless CF + first-party localStorage `anon_id` = lightweight notice + "Privacy & Cookies" link is sufficient; **no blocking consent wall required** because there is no ad-tech/profiling/cross-site sharing. State explicitly: "We do not sell or share your personal information." The moment any ad pixel is added, this posture is void. One-paragraph privacy-policy delta goes into `src/app/privacy/page.tsx`.

---

## 6. Provenance summary

| Section | Primary lane | Cross-checked against |
|---|---|---|
| §1 Surfaces | L1 | L4 (chokepoint reality), real file (`leads_db.json` 3,475 rows) |
| §2 Tables | L2 | L1 (no orphan tables), L4 (column-key match), real file (lead_id text) |
| §3 Events | L3 | L4 (name conflicts -> L3 wins), L5 (PII props stripped) |
| §4 Instrumentation | L4 | L2 (column keys), L3 (canonical names), verified `supabase.ts`/`casino-engine.ts` exports |
| §5 Privacy | L5 | L2 (RLS), L1 (redeem KYC gap) |

**Dropped recommendations (with reason):** L4's thin `analytics_events` column sketch (superseded by L2's actual table). L4's event names `lead_submit`/`checkout_start`/`purchase`/`signup`/`tool_search`/`high_score` (renamed to L3 canonical for GA4 parity). L4's raw `address`/`name`/`email`/`phone_present` props on lead events (stripped per L5 -- only `source`/`page_path` survive in the event; PII goes to `web_leads` server-side).
