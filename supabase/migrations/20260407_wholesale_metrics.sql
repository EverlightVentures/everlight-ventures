-- Wholesale Pipeline Metrics Table
-- Receives daily rollups from workbook_logger.sync_to_supabase()
-- Used by Django dashboard + React site for pipeline visibility

CREATE TABLE IF NOT EXISTS wholesale_metrics (
    id TEXT PRIMARY KEY,
    date DATE NOT NULL,
    funnel_30d JSONB DEFAULT '{}',
    conversion_rates JSONB DEFAULT '{}',
    revenue JSONB DEFAULT '{}',
    costs JSONB DEFAULT '{}',
    agent_performance JSONB DEFAULT '{}',
    active_deals INTEGER DEFAULT 0,
    total_leads INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for date-range queries
CREATE INDEX IF NOT EXISTS idx_wholesale_metrics_date ON wholesale_metrics(date DESC);

-- Upsert trigger for updated_at
CREATE OR REPLACE FUNCTION update_wholesale_metrics_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_wholesale_metrics_updated ON wholesale_metrics;
CREATE TRIGGER trg_wholesale_metrics_updated
    BEFORE UPDATE ON wholesale_metrics
    FOR EACH ROW
    EXECUTE FUNCTION update_wholesale_metrics_timestamp();

-- RLS: service role can read/write, anon can read
ALTER TABLE wholesale_metrics ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access on wholesale_metrics"
    ON wholesale_metrics FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Anon read wholesale_metrics"
    ON wholesale_metrics FOR SELECT
    USING (true);
