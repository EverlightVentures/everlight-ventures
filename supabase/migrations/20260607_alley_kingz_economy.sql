-- ============================================================================
-- ALLEY KINGZ -- Player Progression + Shop Economy (Track 2, M1+M2 foundation)
-- ============================================================================
-- Author: Amara Osei (Iron Stack / SaaS Factory). Date: 2026-06-07.
-- Pairs with: alley-kingz-shop edge function + game/shop UI.
-- Source of truth for design: SHOP_MARKETPLACE_MASTER_PLAN.md, GAME_SHOP_MIRROR.md,
--   ALLEY_KINGZ_MASTER_STRATEGY.md sec 3 / 3.2a, MONETIZATION_LEGAL_LANES.md.
--
-- LEGAL POSTURE (Lane A only -- baked into the schema, not just the UI):
--   * Every currency here flows IN only. There is NO cash-out column, NO redeemable
--     balance, NO "sweeps" coin. Gems/Coins/Scrap are in-game value with NO cash value.
--     (The cashable B-CARDD BET sweeps product lives on Lane B in the casino_* tables;
--     it is a SEPARATE product and is intentionally not referenced here.)
--   * Random/odds-based chests carry an is_random flag. The edge function REFUSES to
--     open them (GACHA_GATED) until PACK_RIP A/B/C is signed + Legal Gate 3 clears.
--   * No-pay-to-win is structural: card/tower levels cap at 10 and the stat curve
--     1 + 0.10*(L-1) lives in the GAME engine, not here. This schema only sinks
--     copies+coins; it can never grant a stat a free player cannot reach.
--
-- WRITE MODEL (server-authoritative, non-spoofable):
--   Only the alley-kingz-shop edge function (service-role key, bypasses RLS) WRITES
--   the player-state tables. The browser may only SELECT its own rows. A
--   browser-writable economy is an economy anyone can mint, so there are NO anon
--   INSERT/UPDATE policies on player-state tables.
--
-- IDEMPOTENCY: every statement is CREATE ... IF NOT EXISTS / ADD COLUMN IF NOT EXISTS
--   / DROP POLICY IF EXISTS so this migration HEALS a partially-built DB and is a
--   no-op on a complete one. Reverse with 20260607_alley_kingz_economy_down.sql.
--
-- player_id TYPE NOTE: player_id is TEXT (no FK) to match the live, un-migrated
--   game_currencies / player_accounts tables (their PK type is not under our control
--   and a hard FK that fails on apply would block the whole migration). player_id
--   mirrors player_accounts.player_id by convention; integrity is enforced in the
--   edge function, not by an FK that could break against live data.
-- ============================================================================

create extension if not exists "pgcrypto";  -- gen_random_uuid()

-- ============================================================================
-- 0. SHARED LIVE TABLES -- HEAL ONLY (we do NOT own these; do NOT drop on down)
-- ============================================================================
-- game_currencies is referenced live by verify-arcade-purchase / verify-gem-purchase
-- but was never migrated (same gap the blackjack_leaderboard migration documents).
-- We create-if-not-exists with the EXACT columns the live edge functions already use
-- so the schema becomes reproducible. If it already exists, this is a no-op.
create table if not exists public.game_currencies (
  id            uuid primary key default gen_random_uuid(),
  player_id     text not null,
  game_id       text not null,            -- canonical AK value = 'alley-kingz' (hyphen)
  currency_name text not null,            -- gems | coins | scrap_common|rare|epic|legendary|mythic | nos
  balance       bigint not null default 0,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now(),
  unique (player_id, game_id, currency_name)
);
alter table public.game_currencies add column if not exists created_at timestamptz not null default now();
alter table public.game_currencies add column if not exists updated_at timestamptz not null default now();
create index if not exists idx_game_currencies_player on public.game_currencies (player_id, game_id);

-- player_accounts is the shared arcade account row. HEAL only -- create a minimal
-- shape if entirely absent so dev DBs work; never clobber the live columns.
create table if not exists public.player_accounts (
  player_id    text primary key,
  display_name text default 'Player',
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now()
);

-- ============================================================================
-- 1. AK CARD / SPELL CATALOG  (reference data -- public read, drives the Card Shop)
-- ============================================================================
create table if not exists public.ak_card_catalog (
  card_id         text primary key,         -- canonical cardNumber, e.g. '0001' (spells 'S001')
  name            text not null,
  rarity          text not null check (rarity in ('Common','Rare','Epic','Legendary','Mythic')),
  faction_id      text,
  is_spell        boolean not null default false,
  cost            integer,                  -- energy cost in-match (display only)
  role            text,
  domain          text,                     -- ground | air | both (display)
  scrap_value     integer not null default 1,   -- rarity card-value unit (Common 1 ... Mythic 1000)
  card_shop_price integer not null default 1,    -- matching-rarity scrap tokens to buy 1 copy (TUNABLE)
  description     text,
  max_level       integer not null default 10,
  active          boolean not null default true,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);
create index if not exists idx_ak_catalog_rarity on public.ak_card_catalog (rarity) where active;

-- ============================================================================
-- 2. AK LEVEL COSTS  (reference -- copies+coins to go from_level -> from_level+1)
-- ============================================================================
-- entity_type 'card' uses rarity; entity_type 'tower' uses rarity = NULL.
-- A copies_required of 0 = a coins-only "blank band" (legendary/mythic dupe drip).
-- Scrap tokens of the matching rarity substitute missing copies 1:1 (enforced in
-- the edge function, not here). Numbers are the committed FIRST DRAFT and TUNABLE.
create table if not exists public.ak_level_costs (
  entity_type     text not null check (entity_type in ('card','tower')),
  rarity          text check (rarity in ('Common','Rare','Epic','Legendary','Mythic')),
  from_level      integer not null check (from_level between 1 and 9),
  copies_required integer not null default 0,
  coins_required  bigint  not null default 0,
  -- towers have NULL rarity; NULLS NOT DISTINCT keeps ON CONFLICT dedupe working
  constraint ak_level_costs_uniq unique nulls not distinct (entity_type, rarity, from_level)
);

-- ============================================================================
-- 3. AK SHOP PRODUCTS  (reference -- gems, chests, consumables, passes, cosmetics)
-- ============================================================================
create table if not exists public.ak_shop_products (
  sku           text primary key,
  kind          text not null check (kind in ('gems','chest','consumable','cosmetic','pass','bundle')),
  title         text not null,
  description   text,
  price_usd     numeric(8,2),              -- set for fiat SKUs (gems/passes/bundles)
  price_gems    integer,                   -- set for gem-priced SKUs (chests/consumables)
  price_scrap   integer,                   -- set for scrap-priced SKUs
  scrap_rarity  text check (scrap_rarity in ('Common','Rare','Epic','Legendary','Mythic')),
  checkout_slug text,                      -- maps to create-checkout PRICE_MAP slug (fiat SKUs)
  grants        jsonb not null default '{}'::jsonb,   -- {coins, gems, scrap_common, card_copies:{card_id:n}, ...}
  odds          jsonb,                     -- DISCLOSED drop odds (random chests only) -- store policy + legal
  is_random     boolean not null default false,       -- true = gacha/loot-box -> edge fn GATES it
  active        boolean not null default true,
  sort_order    integer not null default 100,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);
create index if not exists idx_ak_products_kind on public.ak_shop_products (kind) where active;

-- ============================================================================
-- 4. AK CARD INVENTORY  (player state -- owned copies + level per card)
-- ============================================================================
create table if not exists public.ak_card_inventory (
  player_id  text not null,
  card_id    text not null,
  copies     integer not null default 0 check (copies >= 0),   -- spendable duplicates
  level      integer not null default 1 check (level between 1 and 10),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (player_id, card_id)
);
create index if not exists idx_ak_inv_player on public.ak_card_inventory (player_id);

-- ============================================================================
-- 5. AK TOWER LEVELS  (player state -- the 3 garrison/king towers, levels 1-10)
-- ============================================================================
create table if not exists public.ak_tower_levels (
  player_id  text not null,
  tower_id   text not null,        -- 'crown' | 'left_garrison' | 'right_garrison'
  copies     integer not null default 0 check (copies >= 0),
  level      integer not null default 1 check (level between 1 and 10),
  updated_at timestamptz not null default now(),
  primary key (player_id, tower_id)
);
create index if not exists idx_ak_tower_player on public.ak_tower_levels (player_id);

-- ============================================================================
-- 6. AK CHEST INVENTORY  (player state -- unopened chests owned)
-- ============================================================================
create table if not exists public.ak_chest_inventory (
  player_id  text not null,
  chest_id   text not null references public.ak_shop_products(sku),
  qty        integer not null default 0 check (qty >= 0),
  updated_at timestamptz not null default now(),
  primary key (player_id, chest_id)
);
create index if not exists idx_ak_chest_player on public.ak_chest_inventory (player_id);

-- ============================================================================
-- 7. AK TRANSACTIONS  (audit + anti-cheat + Stripe idempotency)
-- ============================================================================
create table if not exists public.ak_transactions (
  id                uuid primary key default gen_random_uuid(),
  player_id         text not null,
  action            text not null,        -- buy-card | open-chest | level-up-card | level-up-tower | confirm-gems | grant
  sku               text,
  currency_deltas   jsonb not null default '{}'::jsonb,   -- {coins:-500, scrap_rare:-2}
  card_deltas       jsonb not null default '{}'::jsonb,   -- {"0007":+1}
  stripe_session_id text,
  stripe_event_id   text,                 -- UNIQUE -> dedupes webhook/confirm re-fires
  source            text not null default 'alley-kingz-shop',
  created_at        timestamptz not null default now()
);
-- Partial unique: many NULLs allowed, but a real stripe_event_id can credit only once.
create unique index if not exists uq_ak_tx_stripe_event
  on public.ak_transactions (stripe_event_id) where stripe_event_id is not null;
create index if not exists idx_ak_tx_player on public.ak_transactions (player_id, created_at desc);

-- ============================================================================
-- 8. updated_at TOUCH TRIGGER (shared)
-- ============================================================================
create or replace function public.ak_touch_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at := now();
  return new;
end;
$$;

do $$
declare t text;
begin
  foreach t in array array[
    'game_currencies','ak_card_catalog','ak_shop_products',
    'ak_card_inventory','ak_tower_levels','ak_chest_inventory'
  ] loop
    execute format('drop trigger if exists trg_%s_touch on public.%s', t, t);
    execute format(
      'create trigger trg_%s_touch before update on public.%s for each row execute function public.ak_touch_updated_at()',
      t, t);
  end loop;
end$$;

-- ============================================================================
-- 9. ROW LEVEL SECURITY
-- ============================================================================
-- Reference tables: public READ, service-role WRITE.
-- Player-state tables: a player reads ONLY its own rows; all writes are service-role.
-- player_id is TEXT, so own-row policies compare against auth.uid()::text.
-- ----------------------------------------------------------------------------

-- Reference: public read --------------------------------------------------
alter table public.ak_card_catalog  enable row level security;
alter table public.ak_level_costs   enable row level security;
alter table public.ak_shop_products enable row level security;

drop policy if exists ak_catalog_read  on public.ak_card_catalog;
drop policy if exists ak_costs_read     on public.ak_level_costs;
drop policy if exists ak_products_read  on public.ak_shop_products;
create policy ak_catalog_read  on public.ak_card_catalog  for select using (true);
create policy ak_costs_read    on public.ak_level_costs   for select using (true);
create policy ak_products_read on public.ak_shop_products for select using (true);

-- Player state: own-row read + service-role full ---------------------------
alter table public.game_currencies    enable row level security;
alter table public.ak_card_inventory  enable row level security;
alter table public.ak_tower_levels    enable row level security;
alter table public.ak_chest_inventory enable row level security;
alter table public.ak_transactions    enable row level security;

drop policy if exists ak_gc_own    on public.game_currencies;
drop policy if exists ak_inv_own   on public.ak_card_inventory;
drop policy if exists ak_tower_own on public.ak_tower_levels;
drop policy if exists ak_chest_own on public.ak_chest_inventory;
drop policy if exists ak_tx_own    on public.ak_transactions;
create policy ak_gc_own    on public.game_currencies    for select using (player_id::text = auth.uid()::text);
create policy ak_inv_own   on public.ak_card_inventory  for select using (player_id::text = auth.uid()::text);
create policy ak_tower_own on public.ak_tower_levels    for select using (player_id::text = auth.uid()::text);
create policy ak_chest_own on public.ak_chest_inventory for select using (player_id::text = auth.uid()::text);
create policy ak_tx_own    on public.ak_transactions    for select using (player_id::text = auth.uid()::text);

-- Service-role bypass (the edge function is the only writer) ----------------
do $$
declare t text;
begin
  foreach t in array array[
    'game_currencies','ak_card_catalog','ak_level_costs','ak_shop_products',
    'ak_card_inventory','ak_tower_levels','ak_chest_inventory','ak_transactions'
  ] loop
    execute format('drop policy if exists ak_%s_service on public.%s', t, t);
    execute format(
      'create policy ak_%s_service on public.%s for all using (auth.role() = ''service_role'')',
      t, t);
  end loop;
end$$;

-- ============================================================================
-- END. Seed reference data with 20260607_alley_kingz_economy_seed.sql.
-- ============================================================================
