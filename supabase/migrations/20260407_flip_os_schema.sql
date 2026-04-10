-- Flip OS: Retail Arbitrage Intelligence System
-- Tables for penny item tracking, inventory management, and daily briefings

-- ============================================================================
-- FLIP INTEL: Items discovered via scraping/community (not yet purchased)
-- ============================================================================
CREATE TABLE IF NOT EXISTS flip_intel (
    id              BIGSERIAL PRIMARY KEY,
    source          TEXT NOT NULL DEFAULT 'manual',        -- pennycentral, reddit, facebook, manual
    store           TEXT,                                   -- e.g. "HD Vacaville #1043", "HD Fairfield #0637"
    item_name       TEXT NOT NULL,
    item_sku        TEXT,
    original_price  NUMERIC(10,2),
    clearance_price NUMERIC(10,2),
    penny_confirmed BOOLEAN DEFAULT FALSE,
    tag_code        TEXT,                                   -- e.g. ".02", ".03", ".04"
    aisle           TEXT,
    category        TEXT,                                   -- lighting, tools, garden, seasonal, etc.
    est_resale      NUMERIC(10,2),                         -- estimated resale value
    demand_score    INTEGER DEFAULT 0,                     -- 0-100
    margin_pct      NUMERIC(5,2),                          -- (resale - cost) / resale * 100
    platforms       TEXT[],                                 -- where it sells: ebay, fbmp, offerup, amazon
    source_url      TEXT,
    notes           TEXT,
    acted_on        BOOLEAN DEFAULT FALSE,                 -- did we go get it?
    found_date      TIMESTAMPTZ DEFAULT NOW(),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- FLIP INVENTORY: Items we own (in storage, listed, or sold)
-- ============================================================================
CREATE TABLE IF NOT EXISTS flip_inventory (
    id              BIGSERIAL PRIMARY KEY,
    intel_id        BIGINT REFERENCES flip_intel(id),      -- link back to intel if sourced from scraper
    item_name       TEXT NOT NULL,
    item_sku        TEXT,
    category        TEXT,
    condition       TEXT DEFAULT 'new',                     -- new, like_new, good, fair
    buy_price       NUMERIC(10,2) NOT NULL DEFAULT 0.01,
    buy_source      TEXT DEFAULT 'home_depot',              -- home_depot, walmart, target, thrift, fb_marketplace
    buy_date        DATE DEFAULT CURRENT_DATE,
    storage_location TEXT DEFAULT 'unit_a',                 -- unit_a, home, listed, shipped
    est_sell_price  NUMERIC(10,2),
    listed_price    NUMERIC(10,2),
    listed_on       TEXT[],                                 -- fb_marketplace, ebay, offerup, amazon
    listed_date     DATE,
    sold_price      NUMERIC(10,2),
    sold_date       DATE,
    sold_platform   TEXT,
    shipping_cost   NUMERIC(10,2) DEFAULT 0,
    fees            NUMERIC(10,2) DEFAULT 0,               -- platform fees
    net_profit      NUMERIC(10,2) GENERATED ALWAYS AS (
        COALESCE(sold_price, 0) - buy_price - COALESCE(shipping_cost, 0) - COALESCE(fees, 0)
    ) STORED,
    status          TEXT DEFAULT 'in_storage',              -- in_storage, listed, sold, returned, donated
    photos_url      TEXT,
    listing_title   TEXT,
    listing_desc    TEXT,
    notes           TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- FLIP DAILY BRIEF: Generated each morning
-- ============================================================================
CREATE TABLE IF NOT EXISTS flip_daily_brief (
    id              BIGSERIAL PRIMARY KEY,
    brief_date      DATE NOT NULL UNIQUE,
    hunt_items      JSONB DEFAULT '[]'::JSONB,             -- penny items to look for today
    list_items      JSONB DEFAULT '[]'::JSONB,             -- inventory items ready to list
    inventory_summary JSONB DEFAULT '{}'::JSONB,           -- total value, count, avg days held
    monthly_pnl     JSONB DEFAULT '{}'::JSONB,             -- revenue, costs, net, vs rent
    alerts          JSONB DEFAULT '[]'::JSONB,             -- price drops, demand spikes
    brief_text      TEXT,                                   -- plain-text summary for Slack
    posted_to_slack BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- FLIP MONTHLY STATS: Rolled-up monthly performance
-- ============================================================================
CREATE TABLE IF NOT EXISTS flip_monthly_stats (
    id              BIGSERIAL PRIMARY KEY,
    month           DATE NOT NULL UNIQUE,                   -- first of month
    items_bought    INTEGER DEFAULT 0,
    items_sold      INTEGER DEFAULT 0,
    total_cost      NUMERIC(10,2) DEFAULT 0,
    total_revenue   NUMERIC(10,2) DEFAULT 0,
    total_fees      NUMERIC(10,2) DEFAULT 0,
    storage_rent    NUMERIC(10,2) DEFAULT 60.00,
    net_profit      NUMERIC(10,2) DEFAULT 0,
    best_flip       TEXT,                                   -- item name of highest-margin flip
    best_flip_roi   NUMERIC(8,2),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- INDEXES
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_flip_intel_store ON flip_intel(store);
CREATE INDEX IF NOT EXISTS idx_flip_intel_found ON flip_intel(found_date DESC);
CREATE INDEX IF NOT EXISTS idx_flip_intel_demand ON flip_intel(demand_score DESC);
CREATE INDEX IF NOT EXISTS idx_flip_inventory_status ON flip_inventory(status);
CREATE INDEX IF NOT EXISTS idx_flip_inventory_buy_date ON flip_inventory(buy_date DESC);
CREATE INDEX IF NOT EXISTS idx_flip_daily_brief_date ON flip_daily_brief(brief_date DESC);

-- ============================================================================
-- RLS POLICIES (anon can read/write for now, tighten later)
-- ============================================================================
ALTER TABLE flip_intel ENABLE ROW LEVEL SECURITY;
ALTER TABLE flip_inventory ENABLE ROW LEVEL SECURITY;
ALTER TABLE flip_daily_brief ENABLE ROW LEVEL SECURITY;
ALTER TABLE flip_monthly_stats ENABLE ROW LEVEL SECURITY;

CREATE POLICY "anon_flip_intel" ON flip_intel FOR ALL TO anon USING (true) WITH CHECK (true);
CREATE POLICY "anon_flip_inventory" ON flip_inventory FOR ALL TO anon USING (true) WITH CHECK (true);
CREATE POLICY "anon_flip_daily_brief" ON flip_daily_brief FOR ALL TO anon USING (true) WITH CHECK (true);
CREATE POLICY "anon_flip_monthly_stats" ON flip_monthly_stats FOR ALL TO anon USING (true) WITH CHECK (true);
