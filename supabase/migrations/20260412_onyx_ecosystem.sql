-- ============================================================
-- ONYX POS -- Full Ecosystem Expansion
-- The Operating System for Neighborhood Commerce
--
-- 6 new feature tables:
--   1. Vendor Bills (expense-side CV scanning)
--   2. Receipt Lottery (gamification / viral loop)
--   3. Smart Pricing (demand-based suggestions)
--   4. Earned Wage Access (payroll advance)
--   5. Neighborhood Commerce Network (cross-promo)
--   6. Dead Stock Marketplace (B2B wholesale)
-- ============================================================

-- ============================================================
-- 1. VENDOR BILLS (flip receipt scanner for expenses)
-- Scan incoming supplier invoices, auto-categorize, track payables
-- ============================================================
create table if not exists public.onyx_vendor_bills (
    id uuid primary key default uuid_generate_v4(),
    tenant_id uuid not null references public.onyx_tenants(id) on delete cascade,
    -- Vendor info
    vendor_name text,
    vendor_contact text,
    -- Extracted data (from CV pipeline)
    extracted_data jsonb not null default '{}',
    raw_ocr_text text,
    confidence_score numeric(3,2) default 0.00,
    -- Financials
    subtotal numeric(10,2),
    tax_amount numeric(10,2),
    total_amount numeric(10,2),
    -- Categorization
    expense_category text default 'supplies' check (expense_category in (
        'supplies', 'inventory', 'utilities', 'rent', 'services',
        'equipment', 'food_bev', 'marketing', 'payroll', 'other'
    )),
    -- Payment tracking
    due_date date,
    paid boolean default false,
    paid_at timestamptz,
    payment_method text,
    -- Metadata
    raw_image_url text,
    notes text,
    created_at timestamptz default now()
);

create index if not exists idx_onyx_vendor_bills_tenant
    on public.onyx_vendor_bills(tenant_id, created_at desc);
create index if not exists idx_onyx_vendor_bills_unpaid
    on public.onyx_vendor_bills(tenant_id, paid) where paid = false;

-- ============================================================
-- 2. RECEIPT LOTTERY (gamification / viral growth)
-- Every transaction gets a lottery code. Random wins store credit.
-- Funded by 0.1% merchant fee on transactions.
-- ============================================================
create table if not exists public.onyx_lottery_codes (
    id uuid primary key default uuid_generate_v4(),
    tenant_id uuid not null references public.onyx_tenants(id) on delete cascade,
    transaction_id uuid not null references public.onyx_transactions(id),
    -- The code itself (displayed on receipt)
    lottery_code text not null unique,
    -- Win status
    is_winner boolean default false,
    prize_amount numeric(8,2) default 0.00,
    prize_type text default 'store_credit' check (prize_type in ('store_credit', 'discount_pct', 'free_item', 'cashback')),
    -- Redemption
    redeemed boolean default false,
    redeemed_at timestamptz,
    redeemed_transaction_id uuid references public.onyx_transactions(id),
    -- Sharing / viral
    shared_social boolean default false,
    share_platform text, -- instagram, tiktok, twitter, sms
    -- Metadata
    expires_at timestamptz default (now() + interval '30 days'),
    created_at timestamptz default now()
);

create index if not exists idx_onyx_lottery_codes_tenant
    on public.onyx_lottery_codes(tenant_id, created_at desc);
create index if not exists idx_onyx_lottery_codes_code
    on public.onyx_lottery_codes(lottery_code);
create index if not exists idx_onyx_lottery_unredeemed
    on public.onyx_lottery_codes(tenant_id, is_winner, redeemed)
    where is_winner = true and redeemed = false;

-- Lottery config per tenant
alter table public.onyx_tenants
    add column if not exists lottery_enabled boolean default false,
    add column if not exists lottery_fund_pct numeric(5,4) default 0.001,  -- 0.1% of transactions
    add column if not exists lottery_fund_balance numeric(10,2) default 0.00,
    add column if not exists lottery_win_rate numeric(5,4) default 0.05;   -- 5% chance of winning

-- ============================================================
-- 3. SMART PRICING SUGGESTIONS (demand-based dynamic pricing)
-- AI analyzes sales patterns → suggests price changes
-- ============================================================
create table if not exists public.onyx_pricing_suggestions (
    id uuid primary key default uuid_generate_v4(),
    tenant_id uuid not null references public.onyx_tenants(id) on delete cascade,
    product_id uuid references public.onyx_products(id),
    product_name text not null,
    -- Current vs suggested
    current_price numeric(10,2) not null,
    suggested_price numeric(10,2) not null,
    price_change_pct numeric(5,2) not null, -- e.g. +12.5 or -8.0
    -- Reasoning
    reason text not null, -- "Sells 40% more on Saturdays"
    trigger_type text default 'demand' check (trigger_type in (
        'demand', 'time_of_day', 'day_of_week', 'weather',
        'season', 'competitor', 'inventory_low', 'inventory_high'
    )),
    -- Data backing
    data_points jsonb default '{}', -- sales counts, patterns, etc.
    confidence numeric(3,2) default 0.50,
    -- Status
    status text default 'pending' check (status in ('pending', 'accepted', 'rejected', 'expired')),
    accepted_at timestamptz,
    -- Metadata
    valid_from timestamptz default now(),
    valid_until timestamptz default (now() + interval '7 days'),
    created_at timestamptz default now()
);

create index if not exists idx_onyx_pricing_suggestions_tenant
    on public.onyx_pricing_suggestions(tenant_id, status, created_at desc);

-- ============================================================
-- 4. EARNED WAGE ACCESS (payroll advance)
-- Employees access earned wages before payday. $3/advance fee.
-- ============================================================
create table if not exists public.onyx_wage_advances (
    id uuid primary key default uuid_generate_v4(),
    tenant_id uuid not null references public.onyx_tenants(id) on delete cascade,
    employee_id uuid not null references public.onyx_employees(id),
    -- Advance details
    hours_worked numeric(6,2) not null,       -- hours worked this period
    hourly_rate numeric(8,2) not null,         -- employee's rate
    earned_amount numeric(10,2) not null,      -- total earned so far
    advance_amount numeric(10,2) not null,     -- amount requested
    advance_fee numeric(6,2) default 3.00,     -- $3 flat fee
    -- Pay period
    pay_period_start date not null,
    pay_period_end date not null,
    -- Status
    status text default 'pending' check (status in (
        'pending', 'approved', 'disbursed', 'repaid', 'denied'
    )),
    approved_by uuid references public.onyx_employees(id),
    approved_at timestamptz,
    disbursed_at timestamptz,
    repaid_at timestamptz,
    -- Limits
    advance_pct numeric(3,2) default 0.50,     -- max 50% of earned wages
    -- Metadata
    denial_reason text,
    created_at timestamptz default now()
);

create index if not exists idx_onyx_wage_advances_employee
    on public.onyx_wage_advances(tenant_id, employee_id, created_at desc);
create index if not exists idx_onyx_wage_advances_status
    on public.onyx_wage_advances(tenant_id, status);

-- Tenant config for wage access
alter table public.onyx_tenants
    add column if not exists wage_access_enabled boolean default false,
    add column if not exists wage_advance_fee numeric(6,2) default 3.00,
    add column if not exists wage_advance_max_pct numeric(3,2) default 0.50,
    add column if not exists default_pay_period text default 'biweekly'
        check (default_pay_period in ('weekly', 'biweekly', 'monthly'));

-- ============================================================
-- 5. NEIGHBORHOOD COMMERCE NETWORK (cross-promotion)
-- Connect nearby Onyx merchants for mutual customer referrals.
-- ============================================================
create table if not exists public.onyx_merchant_network (
    id uuid primary key default uuid_generate_v4(),
    tenant_id uuid not null references public.onyx_tenants(id) on delete cascade,
    -- Location
    latitude numeric(10,7),
    longitude numeric(10,7),
    neighborhood text,
    city text,
    state text,
    -- Business profile (for cross-promo matching)
    business_type text, -- cafe, florist, salon, grocery, etc.
    business_tags text[], -- ["coffee", "pastries", "wifi"]
    -- Network status
    network_active boolean default true,
    joined_at timestamptz default now(),
    -- Cross-promo preferences
    accepts_cross_promos boolean default true,
    promo_budget_monthly numeric(8,2) default 50.00, -- max discount given via network
    promo_discount_pct numeric(4,2) default 10.00,   -- default: 10% off for referred customers
    created_at timestamptz default now()
);

create index if not exists idx_onyx_merchant_network_location
    on public.onyx_merchant_network using gist (
        point(longitude, latitude)
    );
create index if not exists idx_onyx_merchant_network_tenant
    on public.onyx_merchant_network(tenant_id);

-- Cross-promotion events (when a customer redeems a neighbor's offer)
create table if not exists public.onyx_cross_promos (
    id uuid primary key default uuid_generate_v4(),
    -- Which merchants
    source_tenant_id uuid not null references public.onyx_tenants(id),  -- shop that sent the customer
    target_tenant_id uuid not null references public.onyx_tenants(id),  -- shop that received the customer
    -- Promo details
    promo_code text not null,
    discount_pct numeric(4,2) not null,
    discount_amount numeric(8,2),
    -- Redemption
    redeemed boolean default false,
    redeemed_at timestamptz,
    redeemed_transaction_id uuid references public.onyx_transactions(id),
    -- Customer tracking (anonymous hash)
    customer_hash text, -- hashed identifier, not PII
    -- Metadata
    expires_at timestamptz default (now() + interval '7 days'),
    created_at timestamptz default now()
);

create index if not exists idx_onyx_cross_promos_target
    on public.onyx_cross_promos(target_tenant_id, redeemed, created_at desc);

-- ============================================================
-- 6. DEAD STOCK MARKETPLACE (B2B wholesale between merchants)
-- One shop's dead stock is another shop's opportunity.
-- ============================================================
create table if not exists public.onyx_dead_stock (
    id uuid primary key default uuid_generate_v4(),
    seller_tenant_id uuid not null references public.onyx_tenants(id) on delete cascade,
    -- Product info
    product_id uuid references public.onyx_products(id),
    product_name text not null,
    description text,
    original_price numeric(10,2) not null,
    clearance_price numeric(10,2) not null,
    discount_pct numeric(4,2), -- auto-calculated
    quantity_available integer not null default 1,
    -- Classification
    category text,
    condition text default 'new' check (condition in ('new', 'like_new', 'good', 'fair')),
    -- Listing status
    status text default 'active' check (status in ('active', 'reserved', 'sold', 'expired', 'withdrawn')),
    -- Buyer (when claimed)
    buyer_tenant_id uuid references public.onyx_tenants(id),
    claimed_at timestamptz,
    -- Photos
    image_urls text[],
    -- Metadata
    days_in_stock integer, -- how long this product has been sitting
    expires_at timestamptz default (now() + interval '30 days'),
    created_at timestamptz default now()
);

create index if not exists idx_onyx_dead_stock_active
    on public.onyx_dead_stock(status, created_at desc) where status = 'active';
create index if not exists idx_onyx_dead_stock_seller
    on public.onyx_dead_stock(seller_tenant_id);
create index if not exists idx_onyx_dead_stock_category
    on public.onyx_dead_stock(category, status) where status = 'active';

-- ============================================================
-- RLS FOR ALL NEW TABLES
-- ============================================================
alter table public.onyx_vendor_bills enable row level security;
alter table public.onyx_lottery_codes enable row level security;
alter table public.onyx_pricing_suggestions enable row level security;
alter table public.onyx_wage_advances enable row level security;
alter table public.onyx_merchant_network enable row level security;
alter table public.onyx_cross_promos enable row level security;
alter table public.onyx_dead_stock enable row level security;

-- Tenant isolation policies
create policy "tenant_isolation" on public.onyx_vendor_bills
    for all using (tenant_id in (select id from public.onyx_tenants where owner_user_id = auth.uid()));
create policy "tenant_isolation" on public.onyx_lottery_codes
    for all using (tenant_id in (select id from public.onyx_tenants where owner_user_id = auth.uid()));
create policy "tenant_isolation" on public.onyx_pricing_suggestions
    for all using (tenant_id in (select id from public.onyx_tenants where owner_user_id = auth.uid()));
create policy "tenant_isolation" on public.onyx_wage_advances
    for all using (tenant_id in (select id from public.onyx_tenants where owner_user_id = auth.uid()));
create policy "tenant_isolation" on public.onyx_merchant_network
    for all using (tenant_id in (select id from public.onyx_tenants where owner_user_id = auth.uid()));
create policy "tenant_isolation" on public.onyx_dead_stock
    for all using (seller_tenant_id in (select id from public.onyx_tenants where owner_user_id = auth.uid()));

-- Cross-promos: both source and target tenants can see their promos
create policy "cross_promo_source" on public.onyx_cross_promos
    for all using (source_tenant_id in (select id from public.onyx_tenants where owner_user_id = auth.uid()));
create policy "cross_promo_target" on public.onyx_cross_promos
    for all using (target_tenant_id in (select id from public.onyx_tenants where owner_user_id = auth.uid()));

-- Dead stock marketplace: all active merchants can browse (but only owner modifies)
create policy "dead_stock_browse" on public.onyx_dead_stock
    for select using (status = 'active');

-- Service role bypass for all
create policy "service_role_bypass" on public.onyx_vendor_bills
    for all using (auth.role() = 'service_role');
create policy "service_role_bypass" on public.onyx_lottery_codes
    for all using (auth.role() = 'service_role');
create policy "service_role_bypass" on public.onyx_pricing_suggestions
    for all using (auth.role() = 'service_role');
create policy "service_role_bypass" on public.onyx_wage_advances
    for all using (auth.role() = 'service_role');
create policy "service_role_bypass" on public.onyx_merchant_network
    for all using (auth.role() = 'service_role');
create policy "service_role_bypass" on public.onyx_cross_promos
    for all using (auth.role() = 'service_role');
create policy "service_role_bypass" on public.onyx_dead_stock
    for all using (auth.role() = 'service_role');
