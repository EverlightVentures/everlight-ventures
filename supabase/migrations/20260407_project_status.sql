-- Project Status: Central state tracking across CLI sessions
-- Every session reads this first to know what's already built, deployed, and healthy.
-- Prevents duplicate work across conversations.

CREATE TABLE IF NOT EXISTS project_status (
    id              BIGSERIAL PRIMARY KEY,
    system_name     TEXT NOT NULL UNIQUE,           -- e.g. "flip_os", "xlm_bot", "broker_os"
    status          TEXT DEFAULT 'active',           -- active, paused, broken, planned, deprecated
    description     TEXT,                            -- one-line what this system does
    last_deployed   TIMESTAMPTZ,                     -- when code was last pushed to Oracle
    last_verified   TIMESTAMPTZ,                     -- when a health check confirmed it works
    health          TEXT DEFAULT 'unknown',           -- healthy, degraded, down, unknown
    deploy_command  TEXT,                             -- e.g. "deploy_to_oracle.sh django"
    cron_schedule   TEXT,                             -- e.g. "5 AM PT daily"
    oracle_service  TEXT,                             -- systemd service name if applicable
    oracle_path     TEXT,                             -- path on Oracle server
    supabase_tables TEXT[],                           -- which Supabase tables this system uses
    slack_channel   TEXT,                             -- where it posts
    files_phone     TEXT[],                           -- key files on the phone
    files_oracle    TEXT[],                           -- key files on Oracle
    notes           TEXT,                             -- freeform notes, known issues, resume keywords
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- RLS
ALTER TABLE project_status ENABLE ROW LEVEL SECURITY;
CREATE POLICY "anon_project_status" ON project_status FOR ALL TO anon USING (true) WITH CHECK (true);

-- Index
CREATE INDEX IF NOT EXISTS idx_project_status_name ON project_status(system_name);
CREATE INDEX IF NOT EXISTS idx_project_status_health ON project_status(health);
