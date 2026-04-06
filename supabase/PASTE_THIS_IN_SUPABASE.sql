-- ============================================================
-- EVERLIGHT SUPABASE FIX-ALL -- Paste this ONCE in SQL Editor
-- https://supabase.com/dashboard/project/jdqqmsmwmbsnlnstyavl/sql/new
-- ============================================================
-- This does 3 things:
--   1. Creates gear_catalog + daily_drops tables
--   2. Seeds 8 starter products
--   3. Fixes XLM bot write policies (currently ALL FAILING)
-- ============================================================


-- ============================================
-- PART 1: GEAR ENGINE TABLES
-- ============================================

-- Table: gear_catalog (source inventory for orchestrator)
create table if not exists gear_catalog (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  description text,
  image_url text,
  url text not null,
  seller text,
  rating numeric(3,2) default 4.5,
  sales_velocity integer default 100,
  commission_pct numeric(4,2) default 4.0,
  stock integer default 100,
  active boolean default true,
  category text,
  source text default 'manual',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);
alter table gear_catalog enable row level security;
do $$ begin
  create policy "Public read gear_catalog" on gear_catalog for select using (active = true);
exception when duplicate_object then null;
end $$;
do $$ begin
  create policy "Service write gear_catalog" on gear_catalog for all using (true) with check (true);
exception when duplicate_object then null;
end $$;

-- Table: daily_drops (Lovable frontend reads this)
create table if not exists daily_drops (
  id text primary key,
  drop_date date not null,
  product_id text,
  title text not null,
  description text,
  image_url text,
  affiliate_url text not null,
  seller text,
  rating numeric(3,2),
  gear_score numeric(5,2),
  commission_pct numeric(4,2),
  drop_time_pt timestamptz,
  published boolean default true,
  source text default 'supabase',
  created_at timestamptz default now()
);
alter table daily_drops enable row level security;
do $$ begin
  create policy "Public read daily_drops" on daily_drops for select using (true);
exception when duplicate_object then null;
end $$;
do $$ begin
  create policy "Service write daily_drops" on daily_drops for all using (true) with check (true);
exception when duplicate_object then null;
end $$;
create index if not exists idx_daily_drops_date on daily_drops (drop_date desc, published);


-- ============================================
-- PART 2: SEED 8 STARTER PRODUCTS
-- ============================================

insert into gear_catalog (title, description, image_url, url, seller, rating, sales_velocity, commission_pct, stock, category)
values
  ('TRX HOME2 Suspension Trainer System',
   'The gold standard for bodyweight training. 300+ exercises, anchor anywhere, compact and travel-ready. Trusted by military and elite athletes.',
   'https://m.media-amazon.com/images/I/71o0VBB7VRL._AC_SL1500_.jpg',
   'https://www.amazon.com/dp/B00H5N7QOK?tag=everlightv-20',
   'TRX Training', 4.7, 420, 4.5, 100, 'fitness'),
  ('Garmin Forerunner 255 GPS Running Watch',
   'Advanced running dynamics, HRV status tracking, race predictor, and up to 14-day battery.',
   'https://m.media-amazon.com/images/I/71l3vy5cPeL._AC_SL1500_.jpg',
   'https://www.amazon.com/dp/B0B3DRDLJF?tag=everlightv-20',
   'Garmin', 4.8, 380, 5.0, 100, 'wearables'),
  ('WHOOP 4.0 Performance Tracker',
   '24/7 strain, recovery, and sleep coaching. No screen, no distractions -- just data.',
   'https://m.media-amazon.com/images/I/61-ydCH2ZkL._AC_SL1500_.jpg',
   'https://www.amazon.com/dp/B09NKP52TM?tag=everlightv-20',
   'WHOOP', 4.5, 520, 6.0, 100, 'wearables'),
  ('Hydrow Wave Rowing Machine',
   'Live and on-demand rowing classes on a 16-inch screen. 86 lb compact build.',
   'https://m.media-amazon.com/images/I/71AZfqS9oNL._AC_SL1500_.jpg',
   'https://www.amazon.com/dp/B09XY4K5QQ?tag=everlightv-20',
   'Hydrow', 4.6, 150, 8.0, 25, 'cardio'),
  ('Theragun Pro Plus Percussive Massage Device',
   'Professional-grade recovery. 6 attachments, heated head, cooling vibration, 300-minute battery.',
   'https://m.media-amazon.com/images/I/61VLUDgXJhL._AC_SL1500_.jpg',
   'https://www.amazon.com/dp/B0C5QVMNTM?tag=everlightv-20',
   'Therabody', 4.7, 310, 5.5, 100, 'recovery'),
  ('Lululemon Surge Jogger 29"',
   'Four-way stretch, sweat-wicking, anti-stink tech. The best-rated performance jogger.',
   'https://images.lululemon.com/is/image/lululemon/LM5BM2S_0001_1',
   'https://www.amazon.com/s?k=lululemon+surge+jogger&tag=everlightv-20',
   'Lululemon', 4.6, 280, 3.5, 100, 'apparel'),
  ('Momentous Essential Grass-Fed Whey Protein',
   'NSF Certified for Sport. Clean label whey, 25g protein, no artificial junk.',
   'https://m.media-amazon.com/images/I/71f3pzYDXnL._AC_SL1500_.jpg',
   'https://www.amazon.com/dp/B08Y6DLPB5?tag=everlightv-20',
   'Momentous', 4.7, 450, 7.0, 100, 'nutrition'),
  ('Bowflex SelectTech 552 Adjustable Dumbbells',
   'Replaces 15 sets of weights. 5-52.5 lb range, dial-a-weight in seconds.',
   'https://m.media-amazon.com/images/I/71EkBBpCYnL._AC_SL1500_.jpg',
   'https://www.amazon.com/dp/B001ARYU58?tag=everlightv-20',
   'Bowflex', 4.8, 600, 5.0, 50, 'strength')
on conflict do nothing;


-- ============================================
-- PART 3: FIX XLM BOT WRITE POLICIES
-- (currently ALL pushes failing with 42501)
-- ============================================

do $$ begin create policy "Service write xlm_bot_metrics" on xlm_bot_metrics for all using (true) with check (true); exception when duplicate_object then null; end $$;
do $$ begin create policy "Service write xlm_bot_timeseries" on xlm_bot_timeseries for all using (true) with check (true); exception when duplicate_object then null; end $$;
do $$ begin create policy "Service write xlm_bot_feature_snapshots" on xlm_bot_feature_snapshots for all using (true) with check (true); exception when duplicate_object then null; end $$;
do $$ begin create policy "Service write xlm_bot_trade_labels" on xlm_bot_trade_labels for all using (true) with check (true); exception when duplicate_object then null; end $$;
do $$ begin create policy "Service write xlm_bot_report_history" on xlm_bot_report_history for all using (true) with check (true); exception when duplicate_object then null; end $$;
do $$ begin create policy "Service write xlm_market_intel_state" on xlm_market_intel_state for all using (true) with check (true); exception when duplicate_object then null; end $$;
do $$ begin create policy "Service write xlm_market_intel_runs" on xlm_market_intel_runs for all using (true) with check (true); exception when duplicate_object then null; end $$;
do $$ begin create policy "Service write xlm_market_intel_documents" on xlm_market_intel_documents for all using (true) with check (true); exception when duplicate_object then null; end $$;
do $$ begin create policy "Service write xlm_market_intel_claims" on xlm_market_intel_claims for all using (true) with check (true); exception when duplicate_object then null; end $$;

-- ============================================
-- DONE -- Tables created, data seeded, XLM fixed
-- ============================================
