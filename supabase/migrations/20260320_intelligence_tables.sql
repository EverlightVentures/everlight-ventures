-- Everlight Intelligence -- Lis Pendens Data Product Tables
-- Migration: 20260320_intelligence_tables.sql

-- Subscribers table
create table if not exists intelligence_subscribers (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  email text not null,
  company text,
  tier text default 'basic' check (tier in ('basic', 'pro', 'enterprise')),
  markets text[] default '{}',
  stripe_customer_id text,
  stripe_subscription_id text,
  status text default 'active' check (status in ('active', 'paused', 'cancelled', 'past_due')),
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- Indexes for subscriber lookups
create index if not exists idx_intel_subs_email on intelligence_subscribers(email);
create index if not exists idx_intel_subs_status on intelligence_subscribers(status);
create index if not exists idx_intel_subs_stripe on intelligence_subscribers(stripe_subscription_id);

alter table intelligence_subscribers enable row level security;

-- Service role can do everything
create policy "Service manages subscribers"
  on intelligence_subscribers for all
  using (true);

-- Allow inserts from anon (checkout flow creates subscriber record)
create policy "Anon can insert subscribers"
  on intelligence_subscribers for insert
  with check (true);


-- Lis pendens records table
create table if not exists lis_pendens_records (
  id uuid primary key default gen_random_uuid(),
  address text not null,
  city text not null,
  state text not null,
  zip_code text,
  county text,
  filing_date date,
  case_number text,
  amount_owed numeric,
  property_type text default 'sfr',
  estimated_arv numeric,
  equity_pct numeric,
  owner_name text,
  motivation_score integer default 0,
  enrichment_data jsonb default '{}',
  created_at timestamptz default now()
);

-- Indexes for record queries
create index if not exists idx_lp_county on lis_pendens_records(county);
create index if not exists idx_lp_state on lis_pendens_records(state);
create index if not exists idx_lp_filing_date on lis_pendens_records(filing_date);
create index if not exists idx_lp_score on lis_pendens_records(motivation_score desc);
create index if not exists idx_lp_case on lis_pendens_records(case_number);

alter table lis_pendens_records enable row level security;

-- Service role can do everything
create policy "Service manages records"
  on lis_pendens_records for all
  using (true);
