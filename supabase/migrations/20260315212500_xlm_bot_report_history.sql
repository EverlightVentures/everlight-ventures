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
