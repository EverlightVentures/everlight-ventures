-- XLM Bot Supabase Schema
-- Run in Supabase SQL editor: https://supabase.com/dashboard/project/jdqqmsmwmbsnlnstyavl/sql

-- Live metrics (single row, upserted every minute)
CREATE TABLE IF NOT EXISTS xlm_bot_metrics (
  id                    INT PRIMARY KEY DEFAULT 1,
  generated_at          TIMESTAMPTZ,
  heartbeat_age_s       FLOAT,
  bot_alive             BOOLEAN,
  session_id            TEXT,
  day                   TEXT,
  equity_usd            FLOAT,
  pnl_today_usd         FLOAT,
  net_pnl_today_usd     FLOAT,
  trades_today          INT,
  wins                  INT,
  losses                INT,
  win_rate_pct          FLOAT,
  total_fees_usd        FLOAT,
  vol_state             TEXT,
  recovery_mode         TEXT,
  open_position         BOOLEAN,
  position_side         TEXT,
  safe_mode             BOOLEAN,
  consecutive_losses    INT,
  consecutive_wins      INT,
  spot_usdc             FLOAT,
  daily_target_usd      FLOAT DEFAULT 100,
  daily_floor_usd       FLOAT DEFAULT 25,
  floor_hit             BOOLEAN DEFAULT FALSE,
  target_hit            BOOLEAN DEFAULT FALSE,
  goal_progress_pct     FLOAT DEFAULT 0,
  sentiment_score       INT,
  sentiment_label       TEXT
);

ALTER TABLE xlm_bot_metrics ADD COLUMN IF NOT EXISTS bot_state TEXT;
ALTER TABLE xlm_bot_metrics ADD COLUMN IF NOT EXISTS quality_tier TEXT;
ALTER TABLE xlm_bot_metrics ADD COLUMN IF NOT EXISTS route_tier TEXT;
ALTER TABLE xlm_bot_metrics ADD COLUMN IF NOT EXISTS entry_signal TEXT;
ALTER TABLE xlm_bot_metrics ADD COLUMN IF NOT EXISTS latest_decision_reason TEXT;
ALTER TABLE xlm_bot_metrics ADD COLUMN IF NOT EXISTS signal_product_id TEXT;
ALTER TABLE xlm_bot_metrics ADD COLUMN IF NOT EXISTS spot_reference_product_id TEXT;
ALTER TABLE xlm_bot_metrics ADD COLUMN IF NOT EXISTS contract_mark_price FLOAT;
ALTER TABLE xlm_bot_metrics ADD COLUMN IF NOT EXISTS contract_price_change_24h_pct FLOAT;
ALTER TABLE xlm_bot_metrics ADD COLUMN IF NOT EXISTS orderbook_depth_bias TEXT;
ALTER TABLE xlm_bot_metrics ADD COLUMN IF NOT EXISTS orderbook_imbalance FLOAT;
ALTER TABLE xlm_bot_metrics ADD COLUMN IF NOT EXISTS orderbook_spread_bps FLOAT;
ALTER TABLE xlm_bot_metrics ADD COLUMN IF NOT EXISTS liquidation_signal_source TEXT;
ALTER TABLE xlm_bot_metrics ADD COLUMN IF NOT EXISTS liquidation_feed_live BOOLEAN;
ALTER TABLE xlm_bot_metrics ADD COLUMN IF NOT EXISTS liquidation_bias TEXT;
ALTER TABLE xlm_bot_metrics ADD COLUMN IF NOT EXISTS liquidation_events_5m INT;
ALTER TABLE xlm_bot_metrics ADD COLUMN IF NOT EXISTS liquidation_notional_5m_usd FLOAT;
ALTER TABLE xlm_bot_metrics ADD COLUMN IF NOT EXISTS futures_relativity_bias TEXT;
ALTER TABLE xlm_bot_metrics ADD COLUMN IF NOT EXISTS futures_relativity_confidence FLOAT;
ALTER TABLE xlm_bot_metrics ADD COLUMN IF NOT EXISTS cross_venue_oi_change_pct FLOAT;
ALTER TABLE xlm_bot_metrics ADD COLUMN IF NOT EXISTS cross_venue_funding_bias TEXT;
ALTER TABLE xlm_bot_metrics ADD COLUMN IF NOT EXISTS pulse_regime TEXT;
ALTER TABLE xlm_bot_metrics ADD COLUMN IF NOT EXISTS pulse_health INT;
ALTER TABLE xlm_bot_metrics ADD COLUMN IF NOT EXISTS tick_health TEXT;
ALTER TABLE xlm_bot_metrics ADD COLUMN IF NOT EXISTS tick_age_sec FLOAT;
ALTER TABLE xlm_bot_metrics ADD COLUMN IF NOT EXISTS brief_age_min FLOAT;
ALTER TABLE xlm_bot_metrics ADD COLUMN IF NOT EXISTS news_risk TEXT;
ALTER TABLE xlm_bot_metrics ADD COLUMN IF NOT EXISTS ai_action TEXT;
ALTER TABLE xlm_bot_metrics ADD COLUMN IF NOT EXISTS ai_confidence FLOAT;
ALTER TABLE xlm_bot_metrics ADD COLUMN IF NOT EXISTS data_quality_status TEXT;
ALTER TABLE xlm_bot_metrics ADD COLUMN IF NOT EXISTS public_system_state TEXT;
ALTER TABLE xlm_bot_metrics ADD COLUMN IF NOT EXISTS public_setup_state TEXT;
ALTER TABLE xlm_bot_metrics ADD COLUMN IF NOT EXISTS public_market_climate TEXT;
ALTER TABLE xlm_bot_metrics ADD COLUMN IF NOT EXISTS public_tick_status TEXT;
ALTER TABLE xlm_bot_metrics ADD COLUMN IF NOT EXISTS public_data_status TEXT;
ALTER TABLE xlm_bot_metrics ADD COLUMN IF NOT EXISTS public_decision_label TEXT;
ALTER TABLE xlm_bot_metrics ADD COLUMN IF NOT EXISTS public_pressure_note TEXT;
ALTER TABLE xlm_bot_metrics ADD COLUMN IF NOT EXISTS public_status_blurb TEXT;
ALTER TABLE xlm_bot_metrics ADD COLUMN IF NOT EXISTS public_decision_age_label TEXT;
ALTER TABLE xlm_bot_metrics ADD COLUMN IF NOT EXISTS public_brief_age_label TEXT;
ALTER TABLE xlm_bot_metrics ADD COLUMN IF NOT EXISTS public_price_age_label TEXT;

-- Enable Row Level Security (read-only for anon = public dashboard)
ALTER TABLE xlm_bot_metrics ENABLE ROW LEVEL SECURITY;
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_policies
    WHERE schemaname = 'public'
      AND tablename = 'xlm_bot_metrics'
      AND policyname = 'Public read'
  ) THEN
    CREATE POLICY "Public read" ON xlm_bot_metrics FOR SELECT USING (true);
  END IF;
END $$;

-- Timeseries for equity curve chart
CREATE TABLE IF NOT EXISTS xlm_bot_timeseries (
  id              BIGSERIAL PRIMARY KEY,
  ts              TIMESTAMPTZ DEFAULT NOW(),
  pnl_today_usd   FLOAT,
  equity_usd      FLOAT,
  trades_today    INT,
  win_rate_pct    FLOAT,
  sentiment_score INT
);

ALTER TABLE xlm_bot_timeseries ENABLE ROW LEVEL SECURITY;
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_policies
    WHERE schemaname = 'public'
      AND tablename = 'xlm_bot_timeseries'
      AND policyname = 'Public read'
  ) THEN
    CREATE POLICY "Public read" ON xlm_bot_timeseries FOR SELECT USING (true);
  END IF;
END $$;

-- Index for equity curve queries (last 30 days)
CREATE INDEX IF NOT EXISTS idx_xlm_timeseries_ts ON xlm_bot_timeseries (ts DESC);

CREATE TABLE IF NOT EXISTS xlm_bot_feature_snapshots (
  id                      BIGSERIAL PRIMARY KEY,
  feature_id              TEXT UNIQUE,
  ts                      TIMESTAMPTZ DEFAULT NOW(),
  event_type              TEXT,
  reason                  TEXT,
  session_id              TEXT,
  product_id              TEXT,
  price                   FLOAT,
  direction               TEXT,
  entry_signal            TEXT,
  quality_tier            TEXT,
  route_tier              TEXT,
  gates_pass              BOOLEAN,
  confluence_score        FLOAT,
  ev_usd                  FLOAT,
  v4_regime               TEXT,
  vol_phase               TEXT,
  recovery_mode           TEXT,
  exchange_pnl_today_usd  FLOAT,
  trades_today            INT,
  losses_today            INT,
  pulse_regime            TEXT,
  pulse_health            INT,
  tick_health             TEXT,
  tick_age_sec            FLOAT,
  brief_age_min           FLOAT,
  news_risk               TEXT,
  news_confidence         FLOAT,
  sentiment_score         INT,
  sentiment_stale         BOOLEAN,
  price_source            TEXT,
  bot_state               TEXT,
  ai_action               TEXT,
  ai_confidence           FLOAT,
  ai_initiated            BOOLEAN,
  block_reasons           JSONB,
  live_tick_price         FLOAT
);

ALTER TABLE xlm_bot_feature_snapshots ENABLE ROW LEVEL SECURITY;
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_policies
    WHERE schemaname = 'public'
      AND tablename = 'xlm_bot_feature_snapshots'
      AND policyname = 'Feature snapshots public read'
  ) THEN
    CREATE POLICY "Feature snapshots public read" ON xlm_bot_feature_snapshots FOR SELECT USING (true);
  END IF;
END $$;

ALTER TABLE xlm_bot_feature_snapshots ADD COLUMN IF NOT EXISTS signal_product_id TEXT;
ALTER TABLE xlm_bot_feature_snapshots ADD COLUMN IF NOT EXISTS spot_reference_product_id TEXT;
ALTER TABLE xlm_bot_feature_snapshots ADD COLUMN IF NOT EXISTS contract_mark_price FLOAT;
ALTER TABLE xlm_bot_feature_snapshots ADD COLUMN IF NOT EXISTS contract_price_change_24h_pct FLOAT;
ALTER TABLE xlm_bot_feature_snapshots ADD COLUMN IF NOT EXISTS orderbook_depth_bias TEXT;
ALTER TABLE xlm_bot_feature_snapshots ADD COLUMN IF NOT EXISTS orderbook_imbalance FLOAT;
ALTER TABLE xlm_bot_feature_snapshots ADD COLUMN IF NOT EXISTS orderbook_spread_bps FLOAT;
ALTER TABLE xlm_bot_feature_snapshots ADD COLUMN IF NOT EXISTS liquidation_signal_source TEXT;
ALTER TABLE xlm_bot_feature_snapshots ADD COLUMN IF NOT EXISTS liquidation_feed_live BOOLEAN;
ALTER TABLE xlm_bot_feature_snapshots ADD COLUMN IF NOT EXISTS liquidation_bias TEXT;
ALTER TABLE xlm_bot_feature_snapshots ADD COLUMN IF NOT EXISTS liquidation_events_5m INT;
ALTER TABLE xlm_bot_feature_snapshots ADD COLUMN IF NOT EXISTS liquidation_notional_5m_usd FLOAT;
ALTER TABLE xlm_bot_feature_snapshots ADD COLUMN IF NOT EXISTS futures_relativity_bias TEXT;
ALTER TABLE xlm_bot_feature_snapshots ADD COLUMN IF NOT EXISTS futures_relativity_confidence FLOAT;
ALTER TABLE xlm_bot_feature_snapshots ADD COLUMN IF NOT EXISTS cross_venue_oi_change_pct FLOAT;
ALTER TABLE xlm_bot_feature_snapshots ADD COLUMN IF NOT EXISTS cross_venue_funding_bias TEXT;

CREATE INDEX IF NOT EXISTS idx_xlm_feature_snapshots_ts ON xlm_bot_feature_snapshots (ts DESC);
CREATE INDEX IF NOT EXISTS idx_xlm_feature_snapshots_reason ON xlm_bot_feature_snapshots (reason);

CREATE TABLE IF NOT EXISTS xlm_bot_trade_labels (
  id              BIGSERIAL PRIMARY KEY,
  label_id        TEXT UNIQUE,
  ts              TIMESTAMPTZ DEFAULT NOW(),
  status          TEXT,
  session_id      TEXT,
  order_id        TEXT,
  product_id      TEXT,
  side            TEXT,
  entry_type      TEXT,
  strategy_regime TEXT,
  size            INT,
  entry_price     FLOAT,
  exit_price      FLOAT,
  pnl_usd         FLOAT,
  result          TEXT,
  exit_reason     TEXT,
  hold_minutes    FLOAT,
  fill_verified   BOOLEAN
);

ALTER TABLE xlm_bot_trade_labels ENABLE ROW LEVEL SECURITY;
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_policies
    WHERE schemaname = 'public'
      AND tablename = 'xlm_bot_trade_labels'
      AND policyname = 'Trade labels public read'
  ) THEN
    CREATE POLICY "Trade labels public read" ON xlm_bot_trade_labels FOR SELECT USING (true);
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_xlm_trade_labels_ts ON xlm_bot_trade_labels (ts DESC);
CREATE INDEX IF NOT EXISTS idx_xlm_trade_labels_status ON xlm_bot_trade_labels (status);

CREATE TABLE IF NOT EXISTS xlm_bot_report_history (
  id            BIGSERIAL PRIMARY KEY,
  report_id     TEXT UNIQUE,
  created_at    TIMESTAMPTZ DEFAULT NOW(),
  app           TEXT,
  report_kind   TEXT,
  title         TEXT,
  summary       TEXT,
  status        TEXT,
  folder_path   TEXT,
  doc_link      TEXT,
  history_link  TEXT,
  stored_path   TEXT,
  preview       TEXT,
  metadata      JSONB
);

ALTER TABLE xlm_bot_report_history ENABLE ROW LEVEL SECURITY;
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_policies
    WHERE schemaname = 'public'
      AND tablename = 'xlm_bot_report_history'
      AND policyname = 'Report history public read'
  ) THEN
    CREATE POLICY "Report history public read" ON xlm_bot_report_history FOR SELECT USING (true);
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_xlm_report_history_created_at ON xlm_bot_report_history (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_xlm_report_history_kind ON xlm_bot_report_history (report_kind);
