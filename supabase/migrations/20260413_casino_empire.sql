-- ============================================================
-- VANTARIS -- Empire Schema
-- International crypto casino + US sweepstakes platform
--
-- Brand hierarchy:
--   Everlight Ventures (parent)
--   └── Vantaris (the casino empire)
--       ├── .casino (international, crypto, Anjouan license)
--       ├── .us (sweepstakes, US market)
--       └── Onyx (POS/commerce layer, feeds player acquisition)
--
-- Tables:
--   casino_players: extended player profiles with region/KYC
--   casino_wallets: multi-currency wallet (GC, SC, BTC, ETH, XLM, USDT)
--   casino_game_rounds: universal game history (all games)
--   casino_pf_seeds: provably fair seed pairs
--   casino_cashouts: withdrawal requests + processing
--   casino_sweeps_log: SC distribution audit trail (legal compliance)
--   casino_deposits: crypto deposit tracking
--   casino_jackpots: progressive jackpot pools
-- ============================================================

-- Enable UUID
create extension if not exists "uuid-ossp";

-- ============================================================
-- 1. CASINO PLAYERS (extended from auth.users)
-- ============================================================
create table if not exists public.casino_players (
    id uuid primary key default uuid_generate_v4(),
    user_id uuid unique references auth.users(id),
    -- Identity
    display_name text default 'Player',
    avatar_url text,
    -- Region & compliance
    country_code text default 'XX',
    state_code text,
    region_mode text default 'unknown' check (region_mode in ('sweepstakes', 'crypto', 'blocked', 'unknown')),
    ip_address text,
    -- KYC
    kyc_status text default 'none' check (kyc_status in ('none', 'pending', 'verified', 'rejected')),
    kyc_verified_at timestamptz,
    kyc_document_type text,  -- passport, drivers_license, national_id
    -- Currencies (multi-wallet)
    gold_coins bigint default 1000,        -- play money (sweepstakes) / entertainment chips
    sweeps_coins numeric(12,2) default 0,  -- redeemable for cash (US only)
    crypto_usd numeric(12,2) default 0,    -- crypto balance in USD equivalent (international)
    -- Stats
    total_wagered numeric(14,2) default 0,
    total_won numeric(14,2) default 0,
    total_deposited numeric(14,2) default 0,
    total_withdrawn numeric(14,2) default 0,
    games_played integer default 0,
    -- Rank / progression
    xp integer default 0,
    rank text default 'Ember' check (rank in ('Ember','Shadow','Eclipse','Supernova','Vanta Black')),
    vip_level integer default 0,
    -- Referral
    referral_code text unique,
    referred_by uuid references public.casino_players(id),
    referral_earnings numeric(10,2) default 0,
    -- Responsible gambling
    daily_deposit_limit numeric(10,2),
    weekly_deposit_limit numeric(10,2),
    session_time_limit integer,  -- minutes
    self_excluded boolean default false,
    self_excluded_until timestamptz,
    cooling_off boolean default false,
    cooling_off_until timestamptz,
    -- Metadata
    last_login timestamptz,
    last_game_played timestamptz,
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

create index if not exists idx_casino_players_user on public.casino_players(user_id);
create index if not exists idx_casino_players_referral on public.casino_players(referral_code);
create index if not exists idx_casino_players_rank on public.casino_players(rank, xp desc);

-- ============================================================
-- 2. MULTI-CURRENCY WALLETS
-- ============================================================
create table if not exists public.casino_wallets (
    id uuid primary key default uuid_generate_v4(),
    player_id uuid not null references public.casino_players(id) on delete cascade,
    currency text not null,  -- gc, sc, btc, eth, xlm, usdt, ltc, doge
    balance numeric(18,8) default 0,
    deposit_address text,    -- for crypto currencies
    total_deposited numeric(18,8) default 0,
    total_withdrawn numeric(18,8) default 0,
    created_at timestamptz default now(),
    updated_at timestamptz default now(),
    unique(player_id, currency)
);

create index if not exists idx_casino_wallets_player on public.casino_wallets(player_id);

-- ============================================================
-- 3. GAME ROUNDS (universal, all games)
-- ============================================================
create table if not exists public.casino_game_rounds (
    id uuid primary key default uuid_generate_v4(),
    player_id uuid not null references public.casino_players(id),
    game text not null check (game in ('blackjack','roulette','crash','dice','plinko','mines','slots')),
    currency text not null,  -- gc, sc, btc, eth, etc.
    -- Bet + outcome
    bet_amount numeric(14,4) not null,
    win_amount numeric(14,4) default 0,
    net numeric(14,4) default 0,
    multiplier numeric(10,4) default 0,
    -- Provably fair
    seed_id uuid references public.casino_pf_seeds(id),
    nonce_used integer,
    -- Game data (full result JSON)
    game_data jsonb default '{}',
    -- XP
    xp_earned integer default 0,
    -- Metadata
    played_at timestamptz default now()
);

create index if not exists idx_casino_rounds_player on public.casino_game_rounds(player_id, played_at desc);
create index if not exists idx_casino_rounds_game on public.casino_game_rounds(game, played_at desc);

-- ============================================================
-- 4. PROVABLY FAIR SEEDS
-- ============================================================
create table if not exists public.casino_pf_seeds (
    id uuid primary key default uuid_generate_v4(),
    player_id uuid not null references public.casino_players(id),
    server_seed text not null,         -- HIDDEN until rotated
    server_seed_hash text not null,    -- shown to player as commitment
    client_seed text not null,
    nonce integer default 0,
    is_active boolean default true,
    revealed boolean default false,
    games_played integer default 0,
    created_at timestamptz default now(),
    revealed_at timestamptz
);

create index if not exists idx_casino_pf_active on public.casino_pf_seeds(player_id, is_active) where is_active = true;

-- ============================================================
-- 5. CRYPTO DEPOSITS
-- ============================================================
create table if not exists public.casino_deposits (
    id uuid primary key default uuid_generate_v4(),
    player_id uuid not null references public.casino_players(id),
    currency text not null,
    amount numeric(18,8) not null,
    usd_value numeric(12,2),
    tx_hash text,              -- blockchain transaction hash
    deposit_address text,
    status text default 'pending' check (status in ('pending','confirmed','credited','failed')),
    confirmations integer default 0,
    required_confirmations integer default 3,
    coinspaid_id text,         -- CoinsPaid transaction ID
    created_at timestamptz default now(),
    confirmed_at timestamptz
);

create index if not exists idx_casino_deposits_player on public.casino_deposits(player_id, created_at desc);

-- ============================================================
-- 6. CASHOUT REQUESTS
-- ============================================================
create table if not exists public.casino_cashouts (
    id uuid primary key default uuid_generate_v4(),
    player_id uuid not null references public.casino_players(id),
    currency text not null,  -- sc, btc, eth, xlm, usdt
    amount numeric(14,4) not null,
    usd_value numeric(12,2),
    method text not null check (method in ('paypal','bank','crypto','skrill')),
    destination text not null,  -- email, address, wallet
    status text default 'pending' check (status in ('pending','kyc_required','approved','processing','completed','denied')),
    reviewed_by text,
    denial_reason text,
    external_tx_id text,
    created_at timestamptz default now(),
    reviewed_at timestamptz,
    completed_at timestamptz
);

create index if not exists idx_casino_cashouts_player on public.casino_cashouts(player_id, created_at desc);
create index if not exists idx_casino_cashouts_status on public.casino_cashouts(status);

-- ============================================================
-- 7. SWEEPS COIN AUDIT LOG (legal compliance)
-- ============================================================
create table if not exists public.casino_sweeps_log (
    id uuid primary key default uuid_generate_v4(),
    player_id uuid not null references public.casino_players(id),
    promo_type text not null check (promo_type in (
        'daily_login','mail_in','social_media','purchase_bonus','referral','event','game_win'
    )),
    sc_amount numeric(10,2) not null,
    gc_purchased numeric(10,2) default 0,  -- if bundled with GC purchase
    amoe_reference text,  -- mail tracking for mail-in entries
    round_id uuid,        -- if from game win
    created_at timestamptz default now()
);

create index if not exists idx_casino_sweeps_player on public.casino_sweeps_log(player_id, created_at desc);

-- ============================================================
-- 8. PROGRESSIVE JACKPOTS
-- ============================================================
create table if not exists public.casino_jackpots (
    id uuid primary key default uuid_generate_v4(),
    name text not null,              -- "Obsidian Jackpot", "Daily Mini"
    game text,                        -- null = all games contribute
    currency text default 'gc',
    current_amount numeric(14,2) default 0,
    seed_amount numeric(14,2) default 1000,  -- resets to this after win
    contribution_pct numeric(5,4) default 0.01,  -- 1% of each bet feeds jackpot
    last_won_at timestamptz,
    last_won_by uuid references public.casino_players(id),
    last_won_amount numeric(14,2),
    times_won integer default 0,
    is_active boolean default true,
    created_at timestamptz default now()
);

-- ============================================================
-- RLS
-- ============================================================
alter table public.casino_players enable row level security;
alter table public.casino_wallets enable row level security;
alter table public.casino_game_rounds enable row level security;
alter table public.casino_pf_seeds enable row level security;
alter table public.casino_deposits enable row level security;
alter table public.casino_cashouts enable row level security;
alter table public.casino_sweeps_log enable row level security;
alter table public.casino_jackpots enable row level security;

-- Players see own data
create policy "own_data" on public.casino_players
    for all using (user_id = auth.uid());
create policy "own_data" on public.casino_wallets
    for all using (player_id in (select id from public.casino_players where user_id = auth.uid()));
create policy "own_data" on public.casino_game_rounds
    for all using (player_id in (select id from public.casino_players where user_id = auth.uid()));
create policy "own_data" on public.casino_pf_seeds
    for all using (player_id in (select id from public.casino_players where user_id = auth.uid()));
create policy "own_data" on public.casino_deposits
    for all using (player_id in (select id from public.casino_players where user_id = auth.uid()));
create policy "own_data" on public.casino_cashouts
    for all using (player_id in (select id from public.casino_players where user_id = auth.uid()));
create policy "own_data" on public.casino_sweeps_log
    for all using (player_id in (select id from public.casino_players where user_id = auth.uid()));

-- Jackpots are public (everyone sees the pool)
create policy "public_read" on public.casino_jackpots for select using (true);

-- Service role bypass
create policy "service_role" on public.casino_players for all using (auth.role() = 'service_role');
create policy "service_role" on public.casino_wallets for all using (auth.role() = 'service_role');
create policy "service_role" on public.casino_game_rounds for all using (auth.role() = 'service_role');
create policy "service_role" on public.casino_pf_seeds for all using (auth.role() = 'service_role');
create policy "service_role" on public.casino_deposits for all using (auth.role() = 'service_role');
create policy "service_role" on public.casino_cashouts for all using (auth.role() = 'service_role');
create policy "service_role" on public.casino_sweeps_log for all using (auth.role() = 'service_role');
create policy "service_role" on public.casino_jackpots for all using (auth.role() = 'service_role');

-- ============================================================
-- SEED: Initial jackpots
-- ============================================================
insert into public.casino_jackpots (name, game, currency, seed_amount, current_amount, contribution_pct) values
    ('Vantaris Jackpot', null, 'gc', 100000, 100000, 0.01),
    ('Daily Mini', null, 'gc', 1000, 1000, 0.005),
    ('Vantaris Crypto', null, 'btc', 0.01, 0.01, 0.005);
