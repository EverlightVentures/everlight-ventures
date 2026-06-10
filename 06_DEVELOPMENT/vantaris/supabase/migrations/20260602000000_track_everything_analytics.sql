-- ============================================================================
-- Everlight Ventures / Vantaris -- "Track Everything" first-party analytics
-- Migration: 20260602000000_track_everything_analytics.sql
-- ----------------------------------------------------------------------------
-- Operator mandate: "fully utilize Supabase for the entire website. Any data we
-- receive or should receive must be logged and documented. Mirror Google
-- Analytics. Track everything. High scores for the games, the wholesaling
-- area, the whole site."
--
-- Strategy (decided, do not re-litigate):
--   * Cloudflare Web Analytics (free, cookieless) -> pageview/perf at the edge.
--   * THIS migration -> first-party GA4-style product analytics + high scores
--     + unified leads + wholesale pipeline mirror, all in Supabase.
--   * No paid analytics vendor (free-first law).
--
-- CONTRACT NOTE: column keys here MUST match the object inserted by
-- src/lib/analytics.ts and the event taxonomy in the architecture doc. The
-- canonical event_name values written into analytics_events.event_name are:
--   page_view, session_start, click, scroll_depth, search, outbound_click,
--   sign_up, login, lead_captured, checkout_started, checkout_completed,
--   game_started, game_round, game_cashout, high_score_set, level_up,
--   wholesale_lead_created, wholesale_status_changed.
--
-- Idempotent: CREATE TABLE/INDEX IF NOT EXISTS, CREATE OR REPLACE VIEW,
-- DROP POLICY IF EXISTS before CREATE POLICY. Safe to run repeatedly.
--
-- Existing objects this leans on (already in project jdqqmsmwmbsnlnstyavl):
--   public.casino_players      (id uuid pk, user_id, display_name, gold_coins,
--                               sweeps_coins, xp, rank)
--   public.casino_game_rounds  (id, player_id, game, currency, bet_amount,
--                               win_amount, net, multiplier, game_data jsonb,
--                               xp_earned, played_at)
--   public.leads               (legacy unified leads, kept for back-compat;
--                               web_leads below is the canonical superset)
-- ============================================================================

-- Required for gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS pgcrypto;


-- ============================================================================
-- 1. sessions -- one row per visit/session (GA4 "session" scope)
--    anon_id = first-party cookieless client id (localStorage UUID).
--    user_id = supabase auth user once known (nullable -> anonymous traffic).
--    Written by analytics.ts ensureSession(); last_seen patched on activity.
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.sessions (
  session_id   uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  anon_id      text        NOT NULL,
  user_id      uuid        REFERENCES auth.users(id) ON DELETE SET NULL,
  started_at   timestamptz NOT NULL DEFAULT now(),
  last_seen    timestamptz NOT NULL DEFAULT now(),
  -- acquisition / UTM
  landing_page text,
  referrer     text,
  utm_source   text,
  utm_medium   text,
  utm_campaign text,
  utm_term     text,
  utm_content  text,
  -- device / environment (parsed client-side from UA, coarse, no PII)
  device_type  text,          -- mobile | tablet | desktop
  os           text,
  browser      text,
  screen_w     integer,
  screen_h     integer,
  language     text,
  country      text,          -- coarse, from CF-IPCountry header if available
  -- rollups maintained client-side / by triggers later
  page_view_count integer NOT NULL DEFAULT 0,
  event_count     integer NOT NULL DEFAULT 0,
  is_bounce       boolean
);

CREATE INDEX IF NOT EXISTS idx_sessions_anon       ON public.sessions(anon_id);
CREATE INDEX IF NOT EXISTS idx_sessions_user       ON public.sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_started    ON public.sessions(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_utm_source ON public.sessions(utm_source);
CREATE INDEX IF NOT EXISTS idx_sessions_last_seen  ON public.sessions(last_seen DESC);


-- ============================================================================
-- 2. analytics_events -- GA4-style event stream (the firehose).
--    Every interaction: page_view, click, game_started, game_round,
--    game_cashout, lead_captured, checkout_started, checkout_completed,
--    scroll_depth, search, etc. -> event_name + props jsonb.
--    Written by analytics.ts track() / trackPageView() (batched insert).
--    Column keys here are the contract: event_name, user_id, anon_id,
--    session_id, page, referrer, props, created_at.
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.analytics_events (
  id          bigint      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  event_name  text        NOT NULL,
  user_id     uuid        REFERENCES auth.users(id) ON DELETE SET NULL,
  anon_id     text        NOT NULL,
  session_id  uuid        REFERENCES public.sessions(session_id) ON DELETE SET NULL,
  page        text,                 -- pathname the event fired on
  referrer    text,
  props       jsonb       NOT NULL DEFAULT '{}'::jsonb,
  created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_events_name        ON public.analytics_events(event_name);
CREATE INDEX IF NOT EXISTS idx_events_created     ON public.analytics_events(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_session     ON public.analytics_events(session_id);
CREATE INDEX IF NOT EXISTS idx_events_user        ON public.analytics_events(user_id);
CREATE INDEX IF NOT EXISTS idx_events_anon        ON public.analytics_events(anon_id);
CREATE INDEX IF NOT EXISTS idx_events_page        ON public.analytics_events(page);
CREATE INDEX IF NOT EXISTS idx_events_name_created ON public.analytics_events(event_name, created_at DESC);
-- jsonb prop lookups (e.g. props->>'game', props->>'source', props->>'product')
CREATE INDEX IF NOT EXISTS idx_events_props_gin   ON public.analytics_events USING gin (props);


-- ============================================================================
-- 3. page_views -- denormalized, query-friendly slice of page_view events.
--    Kept separate from analytics_events so the high-volume "what pages get
--    hit" GA report is a narrow, cheap table (mirrors GA "Pages and screens").
--    Written by analytics.ts trackPageViewRow().
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.page_views (
  id            bigint      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  session_id    uuid        REFERENCES public.sessions(session_id) ON DELETE SET NULL,
  anon_id       text        NOT NULL,
  user_id       uuid        REFERENCES auth.users(id) ON DELETE SET NULL,
  page          text        NOT NULL,   -- pathname, e.g. /play/blackjack
  page_title    text,
  referrer      text,
  query_string  text,
  duration_ms   integer,                -- time-on-page (sent on unload/route change)
  created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_pv_page    ON public.page_views(page);
CREATE INDEX IF NOT EXISTS idx_pv_created ON public.page_views(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_pv_session ON public.page_views(session_id);
CREATE INDEX IF NOT EXISTS idx_pv_anon    ON public.page_views(anon_id);
CREATE INDEX IF NOT EXISTS idx_pv_user    ON public.page_views(user_id);
CREATE INDEX IF NOT EXISTS idx_pv_page_created ON public.page_views(page, created_at DESC);


-- ============================================================================
-- 4. high_scores -- explicit best-score-per-game leaderboard.
--    Distinct from the net-winnings VIEW below: this holds skill/score-style
--    bests (crash multiplier survived, mines tiles cleared, plinko top hit,
--    blackjack longest streak, dice biggest win, etc.). period buckets the
--    score so we can run daily / weekly / monthly / all-time boards off one
--    table. Written by analytics.ts submitHighScore() on a high_score_set event.
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.high_scores (
  id           bigint      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  game         text        NOT NULL,   -- blackjack | crash | dice | mines | plinko | roulette
  player_id    uuid        REFERENCES public.casino_players(id) ON DELETE CASCADE,
  user_id      uuid        REFERENCES auth.users(id) ON DELETE SET NULL,
  display_name text,                   -- denormalized snapshot for public boards
  score        numeric     NOT NULL,   -- numeric so it holds multipliers + integer scores
  metric       text        NOT NULL DEFAULT 'score',     -- max_win | max_multiplier | win_streak | net_session | tiles | points
  period       text        NOT NULL DEFAULT 'all_time',  -- daily | weekly | monthly | all_time
  props        jsonb       NOT NULL DEFAULT '{}'::jsonb,
  created_at   timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_hs_game_period_score ON public.high_scores(game, period, score DESC);
CREATE INDEX IF NOT EXISTS idx_hs_player            ON public.high_scores(player_id);
CREATE INDEX IF NOT EXISTS idx_hs_user              ON public.high_scores(user_id);
CREATE INDEX IF NOT EXISTS idx_hs_created           ON public.high_scores(created_at DESC);


-- ============================================================================
-- 5. web_leads -- canonical replacement for the email-only notify-lead path.
--    Superset of the legacy public.leads table; notify-lead edge fn should now
--    INSERT here (then still fire the Resend email). Sources align with
--    notify-lead's SOURCE_LABELS: wholesale, onyx, hivemind, alley-kingz,
--    logistics, consulting, list-tool (+ any future form). PII (name/email/
--    phone/message) lives HERE only, never in analytics_events.props.
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.web_leads (
  id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  source      text        NOT NULL,   -- wholesale | onyx | hivemind | alley-kingz | logistics | consulting | list-tool | ...
  name        text,
  email       text,                   -- nullable: some forms (list-tool) may omit
  phone       text,
  message     text,
  -- attribution: tie the lead back to the analytics session that produced it
  anon_id     text,
  session_id  uuid        REFERENCES public.sessions(session_id) ON DELETE SET NULL,
  user_id     uuid        REFERENCES auth.users(id) ON DELETE SET NULL,
  page        text,                   -- route the form was submitted from
  utm_source  text,
  utm_medium  text,
  utm_campaign text,
  status      text        NOT NULL DEFAULT 'new', -- new | contacted | qualified | won | lost
  metadata    jsonb       NOT NULL DEFAULT '{}'::jsonb,
  created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_web_leads_source  ON public.web_leads(source);
CREATE INDEX IF NOT EXISTS idx_web_leads_created ON public.web_leads(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_web_leads_email   ON public.web_leads(email);
CREATE INDEX IF NOT EXISTS idx_web_leads_status  ON public.web_leads(status);
CREATE INDEX IF NOT EXISTS idx_web_leads_session ON public.web_leads(session_id);


-- ============================================================================
-- 6. wholesale_events -- mirror of the off-site Broker_OS wholesale pipeline.
--    lead_id is TEXT (verified against leads_db.json keys like 'lead_ad8eec735f'
--    / 'leg_03b60821a2', NOT a uuid; 3,475 records). A sync job pushes pipeline
--    activity here so the site/dashboard can report on the wholesaling area
--    without reaching into the flat JSON file. Written by a server-side
--    Broker_OS -> Supabase sync (service_role). Canonical events:
--    wholesale_lead_created | wholesale_status_changed (+ scouted | scored |
--    outreach_sent | reply | offer_made | contract_sent | under_contract |
--    closed | dead). Property-owner PII is NEVER stored here (firewalled in
--    Broker_OS behind the eradication gate).
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.wholesale_events (
  id          bigint      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  lead_id     text        NOT NULL,   -- Broker_OS lead key, e.g. lead_ad8eec735f
  event       text        NOT NULL,
  props       jsonb       NOT NULL DEFAULT '{}'::jsonb,
  created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_wevents_lead    ON public.wholesale_events(lead_id);
CREATE INDEX IF NOT EXISTS idx_wevents_event   ON public.wholesale_events(event);
CREATE INDEX IF NOT EXISTS idx_wevents_created ON public.wholesale_events(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_wevents_props   ON public.wholesale_events USING gin (props);


-- ============================================================================
-- 7. VIEW: casino_leaderboard -- net winnings per player, per game, per period.
--    Aggregates the existing casino_game_rounds. Period buckets materialized
--    via CROSS JOIN LATERAL VALUES so the app can filter `WHERE period =
--    'weekly'`. Public read (granted below). SECURITY INVOKER so it honors
--    caller RLS on the base tables.
-- ============================================================================
CREATE OR REPLACE VIEW public.casino_leaderboard
WITH (security_invoker = true) AS
WITH ranked AS (
  SELECT
    r.player_id,
    p.display_name,
    p.rank                                       AS player_rank,
    r.game,
    b.period,
    SUM(r.net)                                   AS net_winnings,
    SUM(r.win_amount)                            AS total_won,
    SUM(r.bet_amount)                            AS total_wagered,
    COUNT(*)                                     AS rounds_played,
    MAX(r.multiplier)                            AS best_multiplier,
    MAX(r.played_at)                             AS last_played
  FROM public.casino_game_rounds r
  JOIN public.casino_players p ON p.id = r.player_id
  CROSS JOIN LATERAL (
    VALUES
      ('daily',    now() - interval '1 day'),
      ('weekly',   now() - interval '7 days'),
      ('monthly',  now() - interval '30 days'),
      ('all_time', timestamptz '1970-01-01')
  ) AS b(period, since)
  WHERE r.played_at >= b.since
  GROUP BY r.player_id, p.display_name, p.rank, r.game, b.period
)
SELECT
  ranked.*,
  RANK() OVER (
    PARTITION BY game, period
    ORDER BY net_winnings DESC
  ) AS position
FROM ranked;


-- ============================================================================
-- 8. VIEW: site_traffic_daily -- GA-style "Reports > Engagement" rollup.
--    Daily users / sessions / pageviews so the ops dashboard mirrors GA
--    without a paid vendor. Authenticated read (internal in-app analytics page).
-- ============================================================================
CREATE OR REPLACE VIEW public.site_traffic_daily
WITH (security_invoker = true) AS
SELECT
  date_trunc('day', pv.created_at)              AS day,
  COUNT(*)                                      AS page_views,
  COUNT(DISTINCT pv.session_id)                 AS sessions,
  COUNT(DISTINCT pv.anon_id)                    AS visitors,
  COUNT(DISTINCT pv.user_id)                    AS logged_in_users
FROM public.page_views pv
GROUP BY 1
ORDER BY 1 DESC;


-- ============================================================================
-- RLS -- Row Level Security
-- ----------------------------------------------------------------------------
-- Policy model:
--   * anon (cookieless visitors) may INSERT into the ingest tables:
--       analytics_events, page_views, sessions, web_leads, high_scores,
--       wholesale_events. They may NOT read them back (no data exfil).
--   * authenticated users may read ONLY their own rows (user_id = auth.uid()).
--   * sessions: anon may also UPDATE its open session (last_seen, rollups)
--     keyed by the session_id uuid the client already holds.
--   * high_scores are PUBLIC READ (anon + authenticated) so boards render.
--   * web_leads / page_views / analytics_events are NOT anon-readable.
--   * wholesale_events: no anon/auth SELECT -> service_role only (internal).
--   * service_role bypasses RLS entirely (server-side sync jobs, dashboards).
--   * Views (security_invoker) inherit base-table RLS; we additionally GRANT
--     SELECT on the views below.
-- ============================================================================

-- ---- Enable RLS -------------------------------------------------------------
ALTER TABLE public.sessions          ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.analytics_events  ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.page_views        ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.high_scores       ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.web_leads         ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.wholesale_events  ENABLE ROW LEVEL SECURITY;

-- ---- sessions ---------------------------------------------------------------
DROP POLICY IF EXISTS "sessions_insert_anon"       ON public.sessions;
CREATE POLICY "sessions_insert_anon" ON public.sessions
  FOR INSERT TO anon, authenticated WITH CHECK (true);

DROP POLICY IF EXISTS "sessions_update_open"       ON public.sessions;
CREATE POLICY "sessions_update_open" ON public.sessions
  FOR UPDATE TO anon, authenticated
  USING (true)
  WITH CHECK (true);

DROP POLICY IF EXISTS "sessions_select_own"        ON public.sessions;
CREATE POLICY "sessions_select_own" ON public.sessions
  FOR SELECT TO authenticated
  USING (user_id = auth.uid());

-- ---- analytics_events -------------------------------------------------------
DROP POLICY IF EXISTS "events_insert_anon"         ON public.analytics_events;
CREATE POLICY "events_insert_anon" ON public.analytics_events
  FOR INSERT TO anon, authenticated WITH CHECK (true);

DROP POLICY IF EXISTS "events_select_own"          ON public.analytics_events;
CREATE POLICY "events_select_own" ON public.analytics_events
  FOR SELECT TO authenticated
  USING (user_id = auth.uid());

-- ---- page_views -------------------------------------------------------------
DROP POLICY IF EXISTS "pv_insert_anon"             ON public.page_views;
CREATE POLICY "pv_insert_anon" ON public.page_views
  FOR INSERT TO anon, authenticated WITH CHECK (true);

DROP POLICY IF EXISTS "pv_select_own"              ON public.page_views;
CREATE POLICY "pv_select_own" ON public.page_views
  FOR SELECT TO authenticated
  USING (user_id = auth.uid());

-- ---- high_scores ------------------------------------------------------------
-- Anyone may submit a score; EVERYONE may read (public leaderboard).
DROP POLICY IF EXISTS "hs_insert_anyone"           ON public.high_scores;
CREATE POLICY "hs_insert_anyone" ON public.high_scores
  FOR INSERT TO anon, authenticated WITH CHECK (true);

DROP POLICY IF EXISTS "hs_select_public"           ON public.high_scores;
CREATE POLICY "hs_select_public" ON public.high_scores
  FOR SELECT TO anon, authenticated USING (true);

-- ---- web_leads --------------------------------------------------------------
-- Anyone may submit a lead; only the owning user may read their own back.
DROP POLICY IF EXISTS "web_leads_insert_anyone"    ON public.web_leads;
CREATE POLICY "web_leads_insert_anyone" ON public.web_leads
  FOR INSERT TO anon, authenticated WITH CHECK (true);

DROP POLICY IF EXISTS "web_leads_select_own"       ON public.web_leads;
CREATE POLICY "web_leads_select_own" ON public.web_leads
  FOR SELECT TO authenticated
  USING (user_id = auth.uid());

-- ---- wholesale_events -------------------------------------------------------
-- Pipeline mirror is written by the server-side sync (service_role bypasses
-- RLS). Anon insert allowed so a future client-side hook can log too, but
-- NO public read (pipeline data stays internal -> service_role only).
DROP POLICY IF EXISTS "wevents_insert_anon"        ON public.wholesale_events;
CREATE POLICY "wevents_insert_anon" ON public.wholesale_events
  FOR INSERT TO anon, authenticated WITH CHECK (true);
-- (intentionally no SELECT policy for anon/authenticated -> service_role only)


-- ============================================================================
-- GRANTS -- expose the public-read views to the anon + authenticated roles.
-- (RLS governs base tables; views need explicit GRANT to be queryable.)
-- ============================================================================
GRANT SELECT ON public.casino_leaderboard TO anon, authenticated;
GRANT SELECT ON public.site_traffic_daily TO authenticated;  -- internal report


-- ============================================================================
-- END migration. Re-runnable.
-- Next steps (out of scope for this migration, tracked in the checklist):
--   * Point notify-lead edge fn to INSERT into web_leads before emailing.
--   * Add client analytics helpers in src/lib/analytics.ts
--     (track, trackPageView, trackPageViewRow, ensureSession, submitHighScore).
--   * Stripe webhook edge fn writes checkout_completed (server revenue truth).
--   * Broker_OS -> wholesale_events sync job.
--   * SEPARATE migration: redeem_requests table for KYC/cash-out (NOT analytics;
--     see open_conflicts).
-- ============================================================================
