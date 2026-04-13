-- ============================================================
-- ONYX PLATFORM -- Consumer-Side Operating System
-- "Not a POS. A protocol layer for neighborhood commerce."
--
-- THIS IS THE CONSUMER SIDE. Previous migrations built the
-- merchant side (POS, scanner, lottery, pricing, wages, network,
-- marketplace). This migration builds everything the CUSTOMER
-- touches: profiles, wallets, social, sports, fashion, voice.
--
-- 12 new tables across 7 feature domains.
-- ============================================================

-- ============================================================
-- 1. CUSTOMER PROFILES + LOYALTY WALLET
-- The consumer identity layer. One profile across all Onyx merchants.
-- ============================================================
create table if not exists public.onyx_customers (
    id uuid primary key default uuid_generate_v4(),
    -- Identity (minimal PII, privacy-first)
    phone_hash text unique,               -- hashed phone number (lookup key)
    display_name text,                     -- chosen display name
    avatar_url text,
    -- Wallet
    loyalty_points integer default 0,      -- universal Onyx points
    lifetime_points integer default 0,     -- total ever earned
    tier text default 'bronze' check (tier in ('bronze', 'silver', 'gold', 'platinum', 'obsidian')),
    -- Preferences (for predictive commerce)
    favorite_merchants uuid[],             -- ordered list of most-visited
    purchase_tags text[],                  -- ["coffee", "pastries", "flowers"]
    preferred_time text,                   -- "morning", "afternoon", "evening"
    -- Social
    social_handle text,                    -- @username for leaderboards
    social_score integer default 0,        -- clout points from sharing
    referral_code text unique,             -- ONYX-XXXX for inviting friends
    referred_by uuid references public.onyx_customers(id),
    -- Wallet pass
    apple_pass_serial text,
    google_pass_id text,
    -- Streaks
    current_streak integer default 0,      -- consecutive days visiting any Onyx merchant
    longest_streak integer default 0,
    last_visit_date date,
    -- Stats
    total_visits integer default 0,
    total_spent numeric(12,2) default 0.00,
    merchants_visited integer default 0,
    lottery_wins integer default 0,
    -- Metadata
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

create index if not exists idx_onyx_customers_phone on public.onyx_customers(phone_hash);
create index if not exists idx_onyx_customers_referral on public.onyx_customers(referral_code);
create index if not exists idx_onyx_customers_tier on public.onyx_customers(tier, loyalty_points desc);

-- Customer visits per merchant (for predictive commerce)
create table if not exists public.onyx_customer_visits (
    id uuid primary key default uuid_generate_v4(),
    customer_id uuid not null references public.onyx_customers(id),
    tenant_id uuid not null references public.onyx_tenants(id),
    transaction_id uuid references public.onyx_transactions(id),
    -- What they bought (for predictions)
    items_purchased jsonb default '[]',   -- [{name, qty, price}]
    total_spent numeric(10,2),
    -- Context (for pattern matching)
    visit_day text,                       -- "Monday"
    visit_hour integer,                   -- 0-23
    weather text,                         -- "sunny", "rainy", "cold" (from API)
    -- Metadata
    created_at timestamptz default now()
);

create index if not exists idx_onyx_visits_customer
    on public.onyx_customer_visits(customer_id, created_at desc);
create index if not exists idx_onyx_visits_tenant
    on public.onyx_customer_visits(tenant_id, customer_id);

-- Points ledger (every earn/spend is tracked)
create table if not exists public.onyx_points_ledger (
    id uuid primary key default uuid_generate_v4(),
    customer_id uuid not null references public.onyx_customers(id),
    tenant_id uuid references public.onyx_tenants(id),
    -- Transaction
    points integer not null,              -- positive = earn, negative = spend
    balance_after integer not null,
    reason text not null,                 -- "purchase", "referral", "streak_bonus", "prediction_win", "social_share"
    reference_id uuid,                    -- transaction, prediction, social post, etc.
    created_at timestamptz default now()
);

create index if not exists idx_onyx_points_customer
    on public.onyx_points_ledger(customer_id, created_at desc);

-- ============================================================
-- 2. QR RECEIPTS (physical-digital bridge)
-- Every receipt is a QR code containing: lottery, promo, social share link
-- ============================================================
create table if not exists public.onyx_qr_receipts (
    id uuid primary key default uuid_generate_v4(),
    tenant_id uuid not null references public.onyx_tenants(id),
    transaction_id uuid not null references public.onyx_transactions(id),
    customer_id uuid references public.onyx_customers(id),
    -- QR payload
    qr_code_data text not null,            -- JSON payload encoded in QR
    qr_image_url text,                     -- hosted QR image
    short_url text,                        -- onyx.link/XXXX for scanning
    -- Embedded content
    lottery_code_id uuid references public.onyx_lottery_codes(id),
    cross_promo_id uuid references public.onyx_cross_promos(id),
    -- Engagement tracking
    times_scanned integer default 0,
    last_scanned_at timestamptz,
    shared_to text[],                      -- ["instagram", "tiktok"]
    -- Metadata
    created_at timestamptz default now()
);

create index if not exists idx_onyx_qr_receipts_tx
    on public.onyx_qr_receipts(transaction_id);

-- ============================================================
-- 3. SOCIAL CLOUT SYSTEM
-- Sharing, streaks, leaderboards, influencer tiers
-- ============================================================
create table if not exists public.onyx_social_posts (
    id uuid primary key default uuid_generate_v4(),
    customer_id uuid not null references public.onyx_customers(id),
    tenant_id uuid references public.onyx_tenants(id),
    -- Content
    post_type text not null check (post_type in (
        'purchase_share', 'lottery_win', 'streak_milestone',
        'level_up', 'review', 'photo', 'drop_cop', 'prediction_win'
    )),
    content_text text,
    image_url text,
    -- Social card (auto-generated branded image for IG/TikTok)
    social_card_url text,                  -- branded share image
    social_card_template text,             -- which template was used
    -- Platform targeting
    platforms text[] default '{}',         -- ["instagram", "tiktok", "twitter"]
    -- Engagement
    clout_points_earned integer default 0,
    external_link text,                    -- link to the actual social post
    verified boolean default false,        -- did they actually post it?
    -- Metadata
    reference_id uuid,                     -- transaction, lottery code, etc.
    created_at timestamptz default now()
);

create index if not exists idx_onyx_social_customer
    on public.onyx_social_posts(customer_id, created_at desc);

-- Leaderboards (per merchant + global)
create table if not exists public.onyx_leaderboards (
    id uuid primary key default uuid_generate_v4(),
    tenant_id uuid references public.onyx_tenants(id), -- null = global leaderboard
    -- Period
    period text not null check (period in ('weekly', 'monthly', 'all_time')),
    period_start date,
    period_end date,
    -- Rankings (stored as JSONB array for fast reads)
    rankings jsonb not null default '[]',  -- [{customer_id, display_name, score, rank}]
    board_type text default 'spending' check (board_type in (
        'spending', 'visits', 'streak', 'clout', 'predictions', 'referrals'
    )),
    -- Metadata
    computed_at timestamptz default now(),
    created_at timestamptz default now()
);

create index if not exists idx_onyx_leaderboards_tenant
    on public.onyx_leaderboards(tenant_id, board_type, period);

-- ============================================================
-- 4. SPORTS PREDICTION MARKET (loyalty points, not cash = legal)
-- ============================================================
create table if not exists public.onyx_prediction_events (
    id uuid primary key default uuid_generate_v4(),
    tenant_id uuid references public.onyx_tenants(id), -- null = platform-wide
    -- Event details
    title text not null,                   -- "Lakers vs Warriors - Tonight 7PM"
    description text,
    category text not null check (category in (
        'sports', 'local', 'weather', 'pop_culture', 'merchant', 'crypto'
    )),
    -- Options
    options jsonb not null,                -- [{id, label, odds}] e.g. [{id: "a", label: "Lakers", odds: 1.8}]
    -- Resolution
    status text default 'open' check (status in ('open', 'locked', 'resolved', 'canceled')),
    correct_option_id text,                -- which option won
    resolved_at timestamptz,
    -- Timing
    locks_at timestamptz not null,         -- when betting closes
    event_time timestamptz,                -- when the event happens
    -- Stakes
    total_points_wagered integer default 0,
    -- Metadata
    image_url text,
    source_url text,                       -- link to game/event info
    created_at timestamptz default now()
);

create index if not exists idx_onyx_predictions_status
    on public.onyx_prediction_events(status, locks_at);

create table if not exists public.onyx_prediction_bets (
    id uuid primary key default uuid_generate_v4(),
    event_id uuid not null references public.onyx_prediction_events(id),
    customer_id uuid not null references public.onyx_customers(id),
    -- Bet details
    option_id text not null,               -- which option they picked
    points_wagered integer not null,       -- loyalty points bet
    odds_at_time numeric(6,2) not null,    -- odds when they placed the bet
    -- Outcome
    won boolean,
    points_won integer default 0,          -- payout
    -- Metadata
    created_at timestamptz default now()
);

create index if not exists idx_onyx_bets_event
    on public.onyx_prediction_bets(event_id);
create index if not exists idx_onyx_bets_customer
    on public.onyx_prediction_bets(customer_id, created_at desc);

-- ============================================================
-- 5. FASHION / DROP CULTURE ENGINE
-- Limited releases, waitlists, hype notifications, collab drops
-- ============================================================
create table if not exists public.onyx_drops (
    id uuid primary key default uuid_generate_v4(),
    tenant_id uuid not null references public.onyx_tenants(id),
    -- Drop details
    title text not null,                   -- "Summer Collection Drop"
    description text,
    -- Products in this drop
    products jsonb not null default '[]',  -- [{product_id, name, price, quantity, image_url}]
    -- Scheduling
    announce_at timestamptz,               -- when to tease
    drop_time timestamptz not null,        -- when it goes live
    end_time timestamptz,                  -- when it closes (null = until sold out)
    -- Mechanics
    drop_type text default 'fcfs' check (drop_type in (
        'fcfs',           -- first come first served
        'raffle',         -- random selection from waitlist
        'auction',        -- highest bid wins (in points)
        'invite_only'     -- VIP/obsidian tier only
    )),
    max_per_customer integer default 1,    -- limit purchases
    -- Status
    status text default 'upcoming' check (status in (
        'upcoming', 'teased', 'live', 'sold_out', 'ended', 'canceled'
    )),
    total_inventory integer not null,
    remaining_inventory integer not null,
    -- Hype metrics
    waitlist_count integer default 0,
    views integer default 0,
    shares integer default 0,
    -- Collab (joint drop between merchants)
    collab_tenant_id uuid references public.onyx_tenants(id),
    -- Metadata
    cover_image_url text,
    created_at timestamptz default now()
);

create index if not exists idx_onyx_drops_tenant
    on public.onyx_drops(tenant_id, status, drop_time desc);
create index if not exists idx_onyx_drops_upcoming
    on public.onyx_drops(status, drop_time) where status in ('upcoming', 'teased', 'live');

-- Waitlist / RSVP
create table if not exists public.onyx_drop_waitlist (
    id uuid primary key default uuid_generate_v4(),
    drop_id uuid not null references public.onyx_drops(id) on delete cascade,
    customer_id uuid not null references public.onyx_customers(id),
    -- Status
    status text default 'waiting' check (status in (
        'waiting', 'notified', 'purchased', 'expired', 'won_raffle'
    )),
    position integer,                      -- queue position for FCFS
    notified_at timestamptz,
    -- For raffles
    raffle_entries integer default 1,      -- more entries = higher chance (earned by clout)
    -- For auctions
    bid_amount integer,                    -- in loyalty points
    -- Metadata
    created_at timestamptz default now(),
    unique(drop_id, customer_id)
);

create index if not exists idx_onyx_waitlist_drop
    on public.onyx_drop_waitlist(drop_id, status, position);

-- ============================================================
-- 6. VOICE COMMERCE / AI AGENT ORDERING
-- Conversational ordering from any Onyx merchant
-- ============================================================
create table if not exists public.onyx_voice_orders (
    id uuid primary key default uuid_generate_v4(),
    customer_id uuid references public.onyx_customers(id),
    tenant_id uuid references public.onyx_tenants(id),
    -- Order details
    channel text not null check (channel in ('sms', 'voice', 'web_chat', 'whatsapp', 'instagram_dm')),
    -- Conversation
    conversation jsonb not null default '[]',  -- [{role, content, timestamp}]
    -- Extracted order
    parsed_items jsonb default '[]',           -- [{product_name, quantity, price}]
    estimated_total numeric(10,2),
    -- Status
    status text default 'pending' check (status in (
        'pending', 'confirmed', 'preparing', 'ready', 'picked_up',
        'delivered', 'canceled', 'failed'
    )),
    -- Fulfillment
    confirmed_at timestamptz,
    ready_at timestamptz,
    pickup_time timestamptz,                   -- estimated or actual
    delivery_address text,
    -- AI agent metadata
    ai_model text default 'claude-haiku-4-5',
    tokens_used integer default 0,
    confidence numeric(3,2),
    -- Metadata
    created_at timestamptz default now()
);

create index if not exists idx_onyx_voice_orders_customer
    on public.onyx_voice_orders(customer_id, created_at desc);
create index if not exists idx_onyx_voice_orders_tenant
    on public.onyx_voice_orders(tenant_id, status);

-- ============================================================
-- 7. PREDICTIVE COMMERCE (customer anticipation)
-- "Your usual?" -- pre-staged based on patterns
-- ============================================================
create table if not exists public.onyx_customer_predictions (
    id uuid primary key default uuid_generate_v4(),
    customer_id uuid not null references public.onyx_customers(id),
    tenant_id uuid not null references public.onyx_tenants(id),
    -- Prediction
    predicted_items jsonb not null,        -- [{product_name, probability, avg_qty}]
    predicted_total numeric(10,2),
    prediction_confidence numeric(3,2),
    -- Context that triggered prediction
    trigger_type text check (trigger_type in (
        'time_pattern', 'day_pattern', 'weather', 'event',
        'streak', 'proximity', 'seasonal'
    )),
    trigger_data jsonb default '{}',       -- {day: "Monday", hour: 8, weather: "cold"}
    -- Outcome
    was_accurate boolean,                  -- did they actually buy this?
    actual_transaction_id uuid references public.onyx_transactions(id),
    -- Metadata
    valid_for_date date,
    created_at timestamptz default now()
);

create index if not exists idx_onyx_predictions_customer
    on public.onyx_customer_predictions(customer_id, tenant_id, valid_for_date);

-- ============================================================
-- RLS FOR ALL NEW TABLES
-- ============================================================
alter table public.onyx_customers enable row level security;
alter table public.onyx_customer_visits enable row level security;
alter table public.onyx_points_ledger enable row level security;
alter table public.onyx_qr_receipts enable row level security;
alter table public.onyx_social_posts enable row level security;
alter table public.onyx_leaderboards enable row level security;
alter table public.onyx_prediction_events enable row level security;
alter table public.onyx_prediction_bets enable row level security;
alter table public.onyx_drops enable row level security;
alter table public.onyx_drop_waitlist enable row level security;
alter table public.onyx_voice_orders enable row level security;
alter table public.onyx_customer_predictions enable row level security;

-- Customer data: customers see their own data
create policy "customer_own_data" on public.onyx_customers
    for all using (true); -- managed via API auth, not RLS user matching
create policy "customer_visits_own" on public.onyx_customer_visits
    for all using (true);
create policy "points_own" on public.onyx_points_ledger
    for all using (true);

-- QR receipts: tenant isolation
create policy "tenant_isolation" on public.onyx_qr_receipts
    for all using (tenant_id in (select id from public.onyx_tenants where owner_user_id = auth.uid()));

-- Social posts: public reads, own writes
create policy "social_public_read" on public.onyx_social_posts
    for select using (true);

-- Leaderboards: public
create policy "leaderboards_public" on public.onyx_leaderboards
    for select using (true);

-- Predictions: public events, own bets
create policy "events_public" on public.onyx_prediction_events
    for select using (true);
create policy "bets_own" on public.onyx_prediction_bets
    for all using (true);

-- Drops: public browse
create policy "drops_public" on public.onyx_drops
    for select using (true);
create policy "drops_tenant_manage" on public.onyx_drops
    for all using (tenant_id in (select id from public.onyx_tenants where owner_user_id = auth.uid()));
create policy "waitlist_own" on public.onyx_drop_waitlist
    for all using (true);

-- Voice orders: customer + tenant access
create policy "voice_orders_access" on public.onyx_voice_orders
    for all using (true);

-- Predictions: tenant + customer access
create policy "predictions_access" on public.onyx_customer_predictions
    for all using (true);

-- Service role bypass for ALL tables
create policy "service_role_bypass" on public.onyx_customers for all using (auth.role() = 'service_role');
create policy "service_role_bypass" on public.onyx_customer_visits for all using (auth.role() = 'service_role');
create policy "service_role_bypass" on public.onyx_points_ledger for all using (auth.role() = 'service_role');
create policy "service_role_bypass" on public.onyx_qr_receipts for all using (auth.role() = 'service_role');
create policy "service_role_bypass" on public.onyx_social_posts for all using (auth.role() = 'service_role');
create policy "service_role_bypass" on public.onyx_leaderboards for all using (auth.role() = 'service_role');
create policy "service_role_bypass" on public.onyx_prediction_events for all using (auth.role() = 'service_role');
create policy "service_role_bypass" on public.onyx_prediction_bets for all using (auth.role() = 'service_role');
create policy "service_role_bypass" on public.onyx_drops for all using (auth.role() = 'service_role');
create policy "service_role_bypass" on public.onyx_drop_waitlist for all using (auth.role() = 'service_role');
create policy "service_role_bypass" on public.onyx_voice_orders for all using (auth.role() = 'service_role');
create policy "service_role_bypass" on public.onyx_customer_predictions for all using (auth.role() = 'service_role');

-- ============================================================
-- TIER THRESHOLDS (for auto-promotion)
-- Bronze: 0pts | Silver: 500pts | Gold: 2000pts | Platinum: 10000pts | Obsidian: 50000pts
-- ============================================================
comment on column public.onyx_customers.tier is
    'Bronze: 0pts, Silver: 500pts, Gold: 2000pts, Platinum: 10000pts, Obsidian: 50000pts. '
    'Obsidian = VIP access to invite-only drops, 2x prediction odds, custom social cards.';
