-- ============================================================
-- VANTARIS -- Multiplayer Blackjack Schema
-- Real-time multiplayer tables for 2-5 players.
-- Server-side game engine (edge function) is the single source
-- of truth. Clients subscribe to Realtime broadcast events.
-- ============================================================

-- ============================================================
-- 1. GAME TABLES
-- ============================================================
create table if not exists public.game_tables (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    variant text default 'classic' check (variant in ('classic','lightning','speed','switch','highroller')),
    min_bet integer default 100,
    max_bet integer default 100000,
    max_seats integer default 5 check (max_seats between 2 and 7),
    status text default 'waiting' check (status in ('waiting','active','settling')),
    -- Shoe: encrypted server-side only. Never sent to clients.
    shoe jsonb default '[]',
    -- Round state
    phase text default 'betting' check (phase in ('betting','dealing','player_turn','dealer_turn','settled')),
    current_seat integer default 0,
    dealer_hand jsonb default '[]',
    dealer_total integer default 0,
    round_number integer default 0,
    -- Config
    deck_count integer default 6,
    blackjack_pays text default '3:2',
    dealer_hits_soft17 boolean default true,
    double_after_split boolean default true,
    surrender_allowed boolean default true,
    six_card_charlie boolean default true,
    side_bets_enabled boolean default true,
    -- Display
    felt_color text default '#0d5c2e',
    dealer_name text default 'Aria Sinclair',
    dealer_avatar text default 'aria',
    -- Timestamps
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

create index if not exists idx_game_tables_status on public.game_tables(status);
create index if not exists idx_game_tables_variant on public.game_tables(variant);

-- ============================================================
-- 2. GAME SEATS
-- ============================================================
create table if not exists public.game_seats (
    id uuid primary key default gen_random_uuid(),
    table_id uuid not null references public.game_tables(id) on delete cascade,
    seat_index integer not null check (seat_index between 0 and 6),
    -- Player
    user_id uuid references auth.users(id),
    player_id text,  -- references casino_players when that table exists
    display_name text,
    avatar_url text,
    is_vip boolean default false,
    -- Game state
    chips integer default 0,
    bet integer default 0,
    side_bets jsonb default '{}',
    cards jsonb default '[]',
    split_cards jsonb,
    hand_total integer default 0,
    split_total integer,
    is_split boolean default false,
    doubled boolean default false,
    insured boolean default false,
    insurance_bet integer default 0,
    -- Status
    status text default 'empty' check (status in ('empty','waiting','betting','acting','standing','busted','blackjack','settled')),
    outcome text check (outcome is null or outcome in ('win','loss','push','blackjack','bust','surrender','charlie')),
    payout integer default 0,
    -- Turn tracking
    turn_started_at timestamptz,
    afk_count integer default 0,
    -- Timestamps
    joined_at timestamptz default now(),
    -- One seat per position per table
    unique(table_id, seat_index)
);

create index if not exists idx_game_seats_table on public.game_seats(table_id);
create index if not exists idx_game_seats_user on public.game_seats(user_id);

-- ============================================================
-- 3. GAME HANDS (history / audit log)
-- ============================================================
create table if not exists public.game_hands (
    id uuid primary key default gen_random_uuid(),
    table_id uuid references public.game_tables(id),
    hand_number integer,
    seats_snapshot jsonb,
    dealer_hand jsonb,
    dealer_total integer,
    settled_at timestamptz default now()
);

create index if not exists idx_game_hands_table on public.game_hands(table_id);
create index if not exists idx_game_hands_settled on public.game_hands(settled_at desc);

-- ============================================================
-- 4. SEED DEFAULT TABLES
-- ============================================================
insert into public.game_tables (name, variant, min_bet, max_bet, max_seats, felt_color, dealer_name, dealer_avatar, deck_count) values
    ('The Floor',         'classic',    10,    5000,  5, '#0d5c2e', 'Aria Sinclair',     'aria',    6),
    ('The Parlor',        'classic',    25,   10000,  5, '#0d5c2e', 'Aria Sinclair',     'aria',    6),
    ('Lightning Lounge',  'lightning',  50,   25000,  5, '#1a0a2e', 'Marcus Vega',       'marcus',  8),
    ('Velocity',          'speed',      25,   10000,  5, '#0a1520', 'Kanisha Thompson',  'kanisha', 6),
    ('The Switch',        'switch',    100,   25000,  5, '#150a20', 'Aria Sinclair',     'aria',    6),
    ('Vanta Black',       'highroller', 500,  50000,  5, '#050507', 'Bacardi Ice',       'bacardi', 8)
on conflict do nothing;

-- Pre-create empty seats for each table
do $$
declare
    t record;
    s integer;
begin
    for t in select id, max_seats from public.game_tables loop
        for s in 0..(t.max_seats - 1) loop
            insert into public.game_seats (table_id, seat_index, status)
            values (t.id, s, 'empty')
            on conflict (table_id, seat_index) do nothing;
        end loop;
    end loop;
end $$;

-- ============================================================
-- 5. RLS POLICIES
-- ============================================================

-- Tables: anyone can read, only service role can write
alter table public.game_tables enable row level security;

create policy "Anyone can read tables"
    on public.game_tables for select
    using (true);

create policy "Service role manages tables"
    on public.game_tables for all
    using (auth.role() = 'service_role');

-- Seats: anyone can read, only service role can write
alter table public.game_seats enable row level security;

create policy "Anyone can read seats"
    on public.game_seats for select
    using (true);

create policy "Service role manages seats"
    on public.game_seats for all
    using (auth.role() = 'service_role');

-- Hands: anyone can read history
alter table public.game_hands enable row level security;

create policy "Anyone can read hand history"
    on public.game_hands for select
    using (true);

create policy "Service role writes hands"
    on public.game_hands for insert
    using (auth.role() = 'service_role');

-- ============================================================
-- 6. REALTIME: Enable for seats and tables
-- ============================================================
alter publication supabase_realtime add table public.game_tables;
alter publication supabase_realtime add table public.game_seats;
