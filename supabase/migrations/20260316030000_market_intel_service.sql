CREATE TABLE IF NOT EXISTS xlm_market_intel_state (
  state_key TEXT PRIMARY KEY,
  generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  research_kind TEXT NOT NULL,
  source_mode TEXT,
  macro_regime TEXT,
  directional_bias TEXT,
  xlm_bias TEXT,
  confidence DOUBLE PRECISION,
  review_score INTEGER,
  summary TEXT,
  window_label TEXT,
  payload JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS xlm_market_intel_runs (
  run_id TEXT PRIMARY KEY,
  generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  source_timestamp TIMESTAMPTZ,
  research_kind TEXT NOT NULL,
  source_mode TEXT,
  macro_regime TEXT,
  directional_bias TEXT,
  xlm_bias TEXT,
  confidence DOUBLE PRECISION,
  review_score INTEGER,
  summary TEXT,
  window_label TEXT
);

CREATE TABLE IF NOT EXISTS xlm_market_intel_documents (
  document_id TEXT PRIMARY KEY,
  run_id TEXT REFERENCES xlm_market_intel_runs(run_id) ON DELETE CASCADE,
  research_kind TEXT NOT NULL,
  topic TEXT,
  source_name TEXT,
  title TEXT,
  url TEXT,
  published_at TIMESTAMPTZ,
  collected_at TIMESTAMPTZ,
  snippet TEXT,
  source_quality DOUBLE PRECISION
);

CREATE TABLE IF NOT EXISTS xlm_market_intel_claims (
  claim_id TEXT PRIMARY KEY,
  run_id TEXT REFERENCES xlm_market_intel_runs(run_id) ON DELETE CASCADE,
  generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  research_kind TEXT NOT NULL,
  claim_type TEXT,
  asset_scope TEXT,
  horizon TEXT,
  bias TEXT,
  confidence DOUBLE PRECISION,
  claim_text TEXT,
  invalidation TEXT,
  tradable BOOLEAN DEFAULT FALSE,
  review_score INTEGER
);

ALTER TABLE xlm_market_intel_state ENABLE ROW LEVEL SECURITY;
ALTER TABLE xlm_market_intel_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE xlm_market_intel_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE xlm_market_intel_claims ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'xlm_market_intel_state' AND policyname = 'Market intel state public read'
  ) THEN
    CREATE POLICY "Market intel state public read" ON xlm_market_intel_state FOR SELECT USING (true);
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'xlm_market_intel_runs' AND policyname = 'Market intel runs public read'
  ) THEN
    CREATE POLICY "Market intel runs public read" ON xlm_market_intel_runs FOR SELECT USING (true);
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'xlm_market_intel_documents' AND policyname = 'Market intel docs public read'
  ) THEN
    CREATE POLICY "Market intel docs public read" ON xlm_market_intel_documents FOR SELECT USING (true);
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'xlm_market_intel_claims' AND policyname = 'Market intel claims public read'
  ) THEN
    CREATE POLICY "Market intel claims public read" ON xlm_market_intel_claims FOR SELECT USING (true);
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_xlm_market_intel_state_kind ON xlm_market_intel_state (research_kind);
CREATE INDEX IF NOT EXISTS idx_xlm_market_intel_runs_generated_at ON xlm_market_intel_runs (generated_at DESC);
CREATE INDEX IF NOT EXISTS idx_xlm_market_intel_runs_kind ON xlm_market_intel_runs (research_kind, generated_at DESC);
CREATE INDEX IF NOT EXISTS idx_xlm_market_intel_documents_run_id ON xlm_market_intel_documents (run_id);
CREATE INDEX IF NOT EXISTS idx_xlm_market_intel_documents_topic ON xlm_market_intel_documents (topic);
CREATE INDEX IF NOT EXISTS idx_xlm_market_intel_claims_run_id ON xlm_market_intel_claims (run_id);
CREATE INDEX IF NOT EXISTS idx_xlm_market_intel_claims_asset_scope ON xlm_market_intel_claims (asset_scope, generated_at DESC);
