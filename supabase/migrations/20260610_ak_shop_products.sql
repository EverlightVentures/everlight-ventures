-- ============================================================================
-- ALLEY KINGZ -- Shop Product Catalog seed + Stripe wiring columns (Track 2, M3)
-- ============================================================================
-- Date: 2026-06-10. Pairs with: alley-kingz-shop edge function,
--   20260607_alley_kingz_economy.sql (table definitions),
--   03_AUTOMATION_CORE/01_Scripts/ak_stripe_seed_products.py (Stripe TEST seeder).
--
-- WHAT THIS DOES:
--   1. Heals public.ak_shop_products if absent (exact shape from the 20260607
--      economy migration, so this file is standalone-safe on a fresh DB).
--   2. Adds art_path (shop tile art, assets/shop/<sku>.png) and the optional
--      stripe_product_id / stripe_price_id columns (filled later from the
--      seeder's _state/ak_stripe_products.json output -- TEST IDs only).
--   3. Upserts the FULL canonical product catalog (5 gem packs, 5 chests,
--      2 consumables, 2 passes) idempotently. Values match the 20260607 seed
--      and game/shop/shop.js (the canonical SKUs).
--
-- LEGAL POSTURE (Lane A): every product grants in-game value ONLY. No cash-out.
--   Random chests stay is_random=true and the edge function GATES them.
--   Stripe stays TEST MODE: the edge function's liveBlocked() refuses sk_live
--   while AK_SHOP_TEST_MODE is on. This migration changes none of that.
--
-- IDEMPOTENT: CREATE IF NOT EXISTS / ADD COLUMN IF NOT EXISTS /
--   ON CONFLICT DO UPDATE. Safe to re-run.
-- ============================================================================

create extension if not exists "pgcrypto";

-- ----------------------------------------------------------------------------
-- 1. HEAL: ak_shop_products (no-op when 20260607_alley_kingz_economy ran first)
-- ----------------------------------------------------------------------------
create table if not exists public.ak_shop_products (
  sku           text primary key,
  kind          text not null check (kind in ('gems','chest','consumable','cosmetic','pass','bundle')),
  title         text not null,
  description   text,
  price_usd     numeric(8,2),
  price_gems    integer,
  price_scrap   integer,
  scrap_rarity  text check (scrap_rarity in ('Common','Rare','Epic','Legendary','Mythic')),
  checkout_slug text,
  grants        jsonb not null default '{}'::jsonb,
  odds          jsonb,
  is_random     boolean not null default false,
  active        boolean not null default true,
  sort_order    integer not null default 100,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);
create index if not exists idx_ak_products_kind on public.ak_shop_products (kind) where active;

-- ----------------------------------------------------------------------------
-- 2. NEW COLUMNS: shop tile art + Stripe TEST id homes
-- ----------------------------------------------------------------------------
-- art_path: relative to the game root. Placeholder until the art_factory queue
-- delivers Leonardo art per the ART_AUTOROUTE doctrine (no generic art stays).
alter table public.ak_shop_products add column if not exists art_path text;

-- Stripe ids written back from _state/ak_stripe_products.json after the seeder
-- runs (TEST MODE keys only). NULL until then. The live checkout path still
-- resolves via checkout_slug -> create-checkout PRICE_MAP; these columns make
-- the catalog self-describing for baskets/receipts/audits.
alter table public.ak_shop_products add column if not exists stripe_product_id text;
alter table public.ak_shop_products add column if not exists stripe_price_id   text;

comment on column public.ak_shop_products.art_path is
  'Shop tile art, game-root relative: assets/shop/<sku>.png. Auto-routed to Leonardo via art_factory queue.';
comment on column public.ak_shop_products.stripe_product_id is
  'Stripe Product id (TEST mode until operator/legal go-live). Written by ak_stripe_seed_products.py output.';
comment on column public.ak_shop_products.stripe_price_id is
  'Stripe Price id (TEST mode until operator/legal go-live). Written by ak_stripe_seed_products.py output.';

-- ----------------------------------------------------------------------------
-- 3. RLS heal (same policy names as 20260607 so re-runs are clean no-ops)
-- ----------------------------------------------------------------------------
alter table public.ak_shop_products enable row level security;
drop policy if exists ak_products_read on public.ak_shop_products;
create policy ak_products_read on public.ak_shop_products for select using (true);
drop policy if exists ak_ak_shop_products_service on public.ak_shop_products;
create policy ak_ak_shop_products_service on public.ak_shop_products
  for all using (auth.role() = 'service_role');

-- ----------------------------------------------------------------------------
-- 4. CATALOG UPSERT (canonical SKUs -- matches game/shop/shop.js + 20260607 seed)
-- ----------------------------------------------------------------------------
-- Gem packs: fiat (price_usd) + checkout_slug routed through create-checkout.
-- Deterministic chests (is_random=false): fixed disclosed contents, open-able.
-- Random chests (is_random=true): odds disclosed, edge fn gates open (Lucky Draw
--   is the live odds surface; see open-chest USE_LUCKY_DRAW steer).
insert into public.ak_shop_products
  (sku, kind, title, description, price_usd, price_gems, checkout_slug, grants, odds, is_random, sort_order, art_path)
values
  ('ak-gems-rookie',     'gems',  'Rookie Stash',      '500 Gems. In-game value only, no cash value.',                              4.99, NULL, 'ak-gems-rookie',     '{"gems":500}'::jsonb,   NULL, false, 10, 'assets/shop/ak-gems-rookie.png'),
  ('ak-gems-player',     'gems',  'Player Pack',       '1,100 Gems (+10%).',                                                        9.99, NULL, 'ak-gems-player',     '{"gems":1100}'::jsonb,  NULL, false, 11, 'assets/shop/ak-gems-player.png'),
  ('ak-gems-baller',     'gems',  'Baller Bag',        '2,500 Gems (+25%).',                                                       19.99, NULL, 'ak-gems-baller',     '{"gems":2500}'::jsonb,  NULL, false, 12, 'assets/shop/ak-gems-baller.png'),
  ('ak-gems-highroller', 'gems',  'High Roller Crate', '6,500 Gems (+30%).',                                                       49.99, NULL, 'ak-gems-highroller', '{"gems":6500}'::jsonb,  NULL, false, 13, 'assets/shop/ak-gems-highroller.png'),
  ('ak-gems-kingpin',    'gems',  'Kingpin Vault',     '14,000 Gems (+40%).',                                                      99.99, NULL, 'ak-gems-kingpin',    '{"gems":14000}'::jsonb, NULL, false, 14, 'assets/shop/ak-gems-kingpin.png'),
  ('chest_scrap_crate',  'chest', 'Scrap Crate',       'Fixed contents: 200 Coins + 5 Common Scrap. No random draw.',               NULL,   40, NULL, '{"coins":200,"scrap_Common":5}'::jsonb,                 NULL, false, 20, 'assets/shop/chest_scrap_crate.png'),
  ('chest_crew',         'chest', 'Crew Chest',        'Fixed contents: 500 Coins + 10 Common Scrap + 3 Rare Scrap. No random draw.', NULL, 150, NULL, '{"coins":500,"scrap_Common":10,"scrap_Rare":3}'::jsonb, NULL, false, 21, 'assets/shop/chest_crew.png'),
  ('chest_chop_shop',    'chest', 'Chop-Shop Chest',   'Random: epic-guaranteed + rare + scrap. GATED until legal Gate 3.',         NULL,  400, NULL, '{}'::jsonb, '{"Epic":1.0,"Rare":2.0,"scrap_Epic":[3,8]}'::jsonb,          true,  22, 'assets/shop/chest_chop_shop.png'),
  ('chest_kingpin',      'chest', 'Kingpin Chest',     'Random: legendary chance + epic + tokens. GATED until legal Gate 3.',       NULL,  900, NULL, '{}'::jsonb, '{"Legendary":0.15,"Epic":1.0,"scrap_Legendary":[1,3]}'::jsonb, true, 23, 'assets/shop/chest_kingpin.png'),
  ('chest_mythic_vault', 'chest', 'Mythic Vault',      'Event-only random: mythic chance + guaranteed legendary tokens. GATED.',    NULL, 2000, NULL, '{}'::jsonb, '{"Mythic":0.02,"scrap_Legendary":[5,5]}'::jsonb,             true,  24, 'assets/shop/chest_mythic_vault.png'),
  ('nitro_can',          'consumable', 'Nitro Can',    'Pre-PvE-match: +1 starting energy. PvE-only (never ranked).',               NULL,   50, NULL, '{"pve_only":true,"effect":"+1_start_energy"}'::jsonb,   NULL, false, 30, 'assets/shop/nitro_can.png'),
  ('spell_emp',          'consumable', 'Lane EMP',     'One-shot PvE lane EMP. PvE-only (never ranked).',                           NULL,   80, NULL, '{"pve_only":true,"effect":"lane_emp"}'::jsonb,          NULL, false, 31, 'assets/shop/spell_emp.png'),
  ('pass-master',        'pass',  'Master Pass',       'Arcade-wide: 2x earn, seasonal card track, +chest slot. $14.99/mo.',       14.99, NULL, 'master-pass',     '{"perk":"arcade_master_pass"}'::jsonb, NULL, false, 40, 'assets/shop/pass-master.png'),
  ('pass-crew-ak',       'pass',  'AK Crew Pass',      'Alley Kingz only season track. $4.99/season.',                              4.99, NULL, 'ak-season-pass',  '{"perk":"ak_crew_pass"}'::jsonb,       NULL, false, 41, 'assets/shop/pass-crew-ak.png')
on conflict (sku) do update set
  kind=excluded.kind, title=excluded.title, description=excluded.description,
  price_usd=excluded.price_usd, price_gems=excluded.price_gems,
  checkout_slug=excluded.checkout_slug, grants=excluded.grants, odds=excluded.odds,
  is_random=excluded.is_random, sort_order=excluded.sort_order,
  art_path=excluded.art_path, updated_at=now();

-- NOTE: stripe_product_id / stripe_price_id are intentionally NOT set here.
-- They come from the TEST-mode seeder output (_state/ak_stripe_products.json)
-- and are applied by the operator once reviewed. Example backfill:
--   update public.ak_shop_products
--     set stripe_product_id='prod_xxx', stripe_price_id='price_xxx'
--   where sku='ak-gems-rookie';

-- 5 gem packs + 5 chests + 2 consumables + 2 passes = 14 products.
-- END.
