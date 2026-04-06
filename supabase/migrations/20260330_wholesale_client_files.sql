-- ============================================================================
-- Wholesale Client Files: A-to-Z deal document lifecycle
-- Created: 2026-03-30
-- ============================================================================

-- Client file (one per deal/property)
CREATE TABLE IF NOT EXISTS wholesale_client_files (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    deal_id         UUID,
    property_lead_id UUID,
    client_name     TEXT NOT NULL,
    property_address TEXT NOT NULL,
    city            TEXT DEFAULT '',
    state           CHAR(2) DEFAULT '',
    status          TEXT NOT NULL DEFAULT 'active'
                    CHECK (status IN ('active','under_contract','closing','closed','dead')),

    -- Deal numbers
    contract_price  NUMERIC(12,2) DEFAULT 0,
    assignment_fee  NUMERIC(12,2) DEFAULT 0,
    buyer_price     NUMERIC(12,2) DEFAULT 0,
    estimated_arv   NUMERIC(12,2) DEFAULT 0,

    -- Buyer / title
    buyer_id        UUID,
    buyer_name      TEXT DEFAULT '',
    title_company   TEXT DEFAULT '',
    title_contact   TEXT DEFAULT '',
    title_email     TEXT DEFAULT '',

    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    closed_at       TIMESTAMPTZ,
    notes           TEXT DEFAULT ''
);

-- Individual documents in the timeline
CREATE TABLE IF NOT EXISTS wholesale_client_documents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_file_id  UUID NOT NULL REFERENCES wholesale_client_files(id) ON DELETE CASCADE,

    doc_type        TEXT NOT NULL
                    CHECK (doc_type IN (
                        'seller_outreach','deal_sheet','assignment_contract',
                        'buyer_pitch','title_engagement','signed_contract',
                        'closing_statement','payment_receipt','addendum','note','other'
                    )),
    title           TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'draft'
                    CHECK (status IN ('draft','sent','signed','final','voided')),

    -- Content
    html_content    TEXT DEFAULT '',
    plain_text      TEXT DEFAULT '',

    -- Email tracking
    to_email        TEXT DEFAULT '',
    sent_at         TIMESTAMPTZ,
    opened_at       TIMESTAMPTZ,

    -- Metadata
    generated_by    TEXT DEFAULT '',
    slack_message_id TEXT DEFAULT '',

    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_wcf_status ON wholesale_client_files(status);
CREATE INDEX IF NOT EXISTS idx_wcf_state ON wholesale_client_files(state);
CREATE INDEX IF NOT EXISTS idx_wcf_updated ON wholesale_client_files(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_wcd_file ON wholesale_client_documents(client_file_id);
CREATE INDEX IF NOT EXISTS idx_wcd_type ON wholesale_client_documents(doc_type);
CREATE INDEX IF NOT EXISTS idx_wcd_created ON wholesale_client_documents(created_at);

-- RLS policies
ALTER TABLE wholesale_client_files ENABLE ROW LEVEL SECURITY;
ALTER TABLE wholesale_client_documents ENABLE ROW LEVEL SECURITY;

-- Service role can do everything
CREATE POLICY "service_all_client_files" ON wholesale_client_files
    FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "service_all_client_docs" ON wholesale_client_documents
    FOR ALL USING (true) WITH CHECK (true);

-- Anon can read (for dashboard)
CREATE POLICY "anon_read_client_files" ON wholesale_client_files
    FOR SELECT USING (true);
CREATE POLICY "anon_read_client_docs" ON wholesale_client_documents
    FOR SELECT USING (true);

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION update_client_file_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_wcf_updated
    BEFORE UPDATE ON wholesale_client_files
    FOR EACH ROW EXECUTE FUNCTION update_client_file_timestamp();

CREATE TRIGGER trg_wcd_updated
    BEFORE UPDATE ON wholesale_client_documents
    FOR EACH ROW EXECUTE FUNCTION update_client_file_timestamp();
