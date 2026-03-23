-- Agent Performance Tracking (Meta performance review pattern)
-- Tracks per-agent task metrics for dashboard leaderboards and weekly reports

CREATE TABLE IF NOT EXISTS agent_performance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_name TEXT NOT NULL,
    department TEXT NOT NULL,
    session_id TEXT NOT NULL,
    task_type TEXT DEFAULT '',
    started_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ DEFAULT now(),
    success BOOLEAN DEFAULT false,
    duration_s REAL DEFAULT 0,
    findings_count INT DEFAULT 0,
    recommendations_count INT DEFAULT 0,
    user_rating INT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_agent_perf_name ON agent_performance(agent_name);
CREATE INDEX IF NOT EXISTS idx_agent_perf_session ON agent_performance(session_id);
CREATE INDEX IF NOT EXISTS idx_agent_perf_created ON agent_performance(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_perf_dept ON agent_performance(department);

-- RLS: allow anon inserts and reads for now (internal tool)
ALTER TABLE agent_performance ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow anon read agent_performance"
    ON agent_performance FOR SELECT
    USING (true);

CREATE POLICY "Allow anon insert agent_performance"
    ON agent_performance FOR INSERT
    WITH CHECK (true);
