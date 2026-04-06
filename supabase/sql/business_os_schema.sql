-- Everlight Business OS schema
-- Source of truth tables for events, alerts, and revenue streams.
-- Run via Supabase SQL editor or CLI.

create table if not exists business_events (
  id uuid primary key default gen_random_uuid(),
  event_type text not null,
  source text not null,
  entity_type text default '',
  entity_id text default '',
  status text not null default 'info',
  priority text not null default 'medium',
  revenue_impact_usd numeric(12, 2) not null default 0,
  requires_approval boolean not null default false,
  owner_agent text default '',
  summary text not null,
  payload jsonb not null default '{}'::jsonb,
  approved_at timestamptz,
  acknowledged_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists business_events_created_at_idx on business_events (created_at desc);
create index if not exists business_events_source_idx on business_events (source);
create index if not exists business_events_status_idx on business_events (status);
create index if not exists business_events_requires_approval_idx on business_events (requires_approval);

create table if not exists business_alerts (
  id uuid primary key default gen_random_uuid(),
  alert_key text default '',
  severity text not null default 'warning',
  state text not null default 'open',
  source text not null,
  summary text not null,
  detail text default '',
  entity_type text default '',
  entity_id text default '',
  requires_approval boolean not null default false,
  related_event_id uuid references business_events(id) on delete set null,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  resolved_at timestamptz
);

create index if not exists business_alerts_state_idx on business_alerts (state);
create index if not exists business_alerts_severity_idx on business_alerts (severity);
create index if not exists business_alerts_created_at_idx on business_alerts (created_at desc);

create table if not exists revenue_streams (
  id uuid primary key default gen_random_uuid(),
  slug text unique not null,
  name text not null,
  owner_agent text default '',
  category text default '',
  status text not null default 'building',
  monthly_target_usd numeric(12, 2) not null default 0,
  mrr_usd numeric(12, 2) not null default 0,
  cash_today_usd numeric(12, 2) not null default 0,
  cash_30d_usd numeric(12, 2) not null default 0,
  pending_pipeline_usd numeric(12, 2) not null default 0,
  notes text default '',
  metadata jsonb not null default '{}'::jsonb,
  last_event_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists revenue_streams_status_idx on revenue_streams (status);

create or replace function everlight_set_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists business_events_updated_at on business_events;
create trigger business_events_updated_at
before update on business_events
for each row execute function everlight_set_updated_at();

drop trigger if exists revenue_streams_updated_at on revenue_streams;
create trigger revenue_streams_updated_at
before update on revenue_streams
for each row execute function everlight_set_updated_at();

alter table business_events enable row level security;
alter table business_alerts enable row level security;
alter table revenue_streams enable row level security;

drop policy if exists "service role full access business_events" on business_events;
create policy "service role full access business_events"
on business_events
for all
to service_role
using (true)
with check (true);

drop policy if exists "service role full access business_alerts" on business_alerts;
create policy "service role full access business_alerts"
on business_alerts
for all
to service_role
using (true)
with check (true);

drop policy if exists "service role full access revenue_streams" on revenue_streams;
create policy "service role full access revenue_streams"
on revenue_streams
for all
to service_role
using (true)
with check (true);

insert into revenue_streams (slug, name, owner_agent, category, status, monthly_target_usd, notes)
values
  ('hive_mind_saas', 'Hive Mind SaaS', 'saas_growth', 'recurring_saas', 'pilot', 3000, 'Chief-of-staff product and AI operations platform.'),
  ('broker_os', 'Broker OS', '32_deal_closer', 'deal_fees', 'pilot', 2500, 'B2B matchmaking, finder fees, and invoiced commissions.'),
  ('onyx_pos', 'Onyx POS', 'engineering_foreman', 'vertical_saas', 'building', 1500, 'Retail and POS subscriptions.'),
  ('daily_gear_drop', 'Daily Gear Drop', 'distribution_ops', 'affiliate_commerce', 'pilot', 800, 'Affiliate commerce and daily product drops.'),
  ('digital_products', 'Digital Products', 'writer', 'one_time_sales', 'building', 1000, 'Templates, prompts, guides, and downloadable offers.'),
  ('publishing_media', 'Publishing and Media', 'content_director', 'catalog_revenue', 'active', 1200, 'Books, audiobooks, and long-tail catalog assets.'),
  ('ai_services', 'AI Implementation Services', 'chief_operator', 'services', 'building', 4000, 'Setup, advisory, and retainer work.'),
  ('trading_intelligence', 'Trading Intelligence', 'trading_risk', 'data_product', 'pilot', 900, 'Analytics and reporting products, not trade promises.')
on conflict (slug) do update
set
  name = excluded.name,
  owner_agent = excluded.owner_agent,
  category = excluded.category,
  status = excluded.status,
  monthly_target_usd = excluded.monthly_target_usd,
  notes = excluded.notes;
