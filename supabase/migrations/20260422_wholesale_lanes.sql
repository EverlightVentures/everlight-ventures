-- Wholesale lane routing schema.
-- Adds lane classification to every deal/lead record and seeds the routing rules
-- table so the pipeline can look up which playbook applies to a property.

-- 1. Add lane column to deal tracking.
ALTER TABLE IF EXISTS wholesale_client_files
    ADD COLUMN IF NOT EXISTS lane TEXT
    CHECK (lane IN ('L1', 'L2', 'L3', 'L4', 'L5', 'L6'));

COMMENT ON COLUMN wholesale_client_files.lane IS
    'Distress lane: L1 code violations, L2 pre-foreclosure, L3 probate, L4 tax delinquency, L5 vacant/absentee, L6 teardown hunt.';

CREATE INDEX IF NOT EXISTS idx_wholesale_client_files_lane
    ON wholesale_client_files(lane);

-- 2. Lane routing rules table.
-- One row per lane with the offer strategy, scout function, and fire-team assignments.
CREATE TABLE IF NOT EXISTS lane_routing_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lane TEXT UNIQUE NOT NULL CHECK (lane IN ('L1', 'L2', 'L3', 'L4', 'L5', 'L6')),
    name TEXT NOT NULL,
    playbook_path TEXT NOT NULL,
    default_offer_strategy TEXT NOT NULL,
    scout_module TEXT NOT NULL,
    buyer_segment TEXT NOT NULL,
    fire_team JSONB NOT NULL DEFAULT '{}'::jsonb,
    active BOOLEAN NOT NULL DEFAULT FALSE,
    launched_at TIMESTAMPTZ,
    success_metric TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE lane_routing_rules IS
    'Single source of truth for which lane gets which scout, offer strategy, and buyer segment. Rex pipeline reads this on every morning cycle.';

-- 3. Seed the rules. L2 ships first (active=true when deployed),
-- others stay inactive until we unlock them per plan.
INSERT INTO lane_routing_rules (lane, name, playbook_path, default_offer_strategy, scout_module, buyer_segment, fire_team, success_metric, notes)
VALUES
    (
        'L1', 'Code violations / tired landlords',
        '01_BUSINESSES/Everlight_Ventures/Wholesale/offers/L1_code_violation.md',
        'seventy_rule',
        'rex_distress_finder',
        'cash_buyer_flipper',
        '{"scout":"rex_blackwell","qualifier":"filter_banks","outreach":"piper_reeves","closer":"harrison_cole","compliance":"justine_park"}'::jsonb,
        '1 closed deal / 30 days',
        'Unlock after L2 ships first contract.'
    ),
    (
        'L2', 'Pre-foreclosure assignment',
        '01_BUSINESSES/Everlight_Ventures/Wholesale/offers/L2_preforeclosure_assignment.md',
        'balance_assignment',
        'rex_zillow_keyword_scraper',
        'cash_buyer_flipper',
        '{"scout":"rex_blackwell","qualifier":"filter_banks","profit":"penny_prescott","matcher":"cupid_hayes","outreach":"piper_reeves","closer":"harrison_cole","compliance":"justine_park"}'::jsonb,
        '1 closed deal / 60 days at $10K fee',
        'Proof-of-concept lane. Ship first.'
    ),
    (
        'L3', 'Probate',
        '01_BUSINESSES/Everlight_Ventures/Wholesale/offers/L3_probate.md',
        'seventy_rule',
        'rex_probate_scout',
        'cash_buyer_flipper',
        '{"scout":"rex_blackwell","qualifier":"filter_banks","outreach":"piper_reeves","closer":"harrison_cole"}'::jsonb,
        '1 closed deal / 60 days',
        'Waiting on county probate filings feed.'
    ),
    (
        'L4', 'Tax delinquency',
        '01_BUSINESSES/Everlight_Ventures/Wholesale/offers/L4_tax_delinquency.md',
        'seventy_rule',
        'rex_tax_delinquency_scout',
        'cash_buyer_flipper',
        '{"scout":"rex_blackwell","qualifier":"filter_banks","outreach":"piper_reeves","closer":"harrison_cole"}'::jsonb,
        '1 closed deal / 60 days',
        'Waiting on county tax lien feed.'
    ),
    (
        'L5', 'Vacant / absentee owner',
        '01_BUSINESSES/Everlight_Ventures/Wholesale/offers/L5_vacant_absentee.md',
        'balance_assignment',
        'rex_zillow_keyword_scraper',
        'cash_buyer_flipper',
        '{"scout":"rex_blackwell","qualifier":"filter_banks","outreach":"piper_reeves","closer":"harrison_cole"}'::jsonb,
        '1 closed deal / 45 days',
        'Unlock with L1 + L6 after L2 ships.'
    ),
    (
        'L6', 'Teardown hunt (new-home builders)',
        '01_BUSINESSES/Everlight_Ventures/Wholesale/offers/L6_teardown_hunt.md',
        'teardown_80pct',
        'rex_teardown_finder',
        'builder_new_home',
        '{"scout":"rex_blackwell","qualifier":"filter_banks","profit":"penny_prescott","matcher":"cupid_hayes","marketer":"ace_morgan","outreach":"piper_reeves","closer":"harrison_cole","compliance":"justine_park"}'::jsonb,
        '1 closed deal / 30 days / market at $30K fee',
        'Teardown offer also overlays L1/L2/L5 when buy-box matches.'
    )
ON CONFLICT (lane) DO UPDATE SET
    name = EXCLUDED.name,
    playbook_path = EXCLUDED.playbook_path,
    default_offer_strategy = EXCLUDED.default_offer_strategy,
    scout_module = EXCLUDED.scout_module,
    buyer_segment = EXCLUDED.buyer_segment,
    fire_team = EXCLUDED.fire_team,
    success_metric = EXCLUDED.success_metric,
    notes = EXCLUDED.notes,
    updated_at = NOW();

-- 4. Row-level security: only service role writes, anon can read (read-only visibility into lane status on the dashboard).
ALTER TABLE lane_routing_rules ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS lane_rules_read ON lane_routing_rules;
CREATE POLICY lane_rules_read ON lane_routing_rules
    FOR SELECT USING (true);

DROP POLICY IF EXISTS lane_rules_write ON lane_routing_rules;
CREATE POLICY lane_rules_write ON lane_routing_rules
    FOR ALL USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');
