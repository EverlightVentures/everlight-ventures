-- ============================================================================
-- blackjack_leaderboard  --  the "Hall of Legends" rollup table
-- ============================================================================
-- WHY THIS MIGRATION EXISTS:
--   The frontend (vantaris/src/lib/supabase.ts :: getLeaderboard) and the
--   server-authoritative edge function (functions/blackjack-api :: record-hand,
--   get-leaderboard) BOTH read/write public.blackjack_leaderboard, but no
--   migration ever created it -- it only existed (if at all) as a hand-made
--   dashboard table. That made the schema un-reproducible and, when missing,
--   silently dropped every leaderboard write so the UI fell back to FAKE players.
--
--   This migration makes the table real + reproducible. It is fully idempotent:
--   CREATE TABLE IF NOT EXISTS + ADD COLUMN IF NOT EXISTS, so it safely HEALS a
--   pre-existing hand-made table (e.g. one missing the jackpots_won column) and
--   is a no-op on a DB that already has the full shape.
--
-- WRITE MODEL (server-authoritative, non-spoofable):
--   Only the blackjack-api edge function (service-role key, bypasses RLS) writes
--   here. The browser may only SELECT (public read for the Hall of Legends).
--   This is why there is NO anon INSERT/UPDATE policy -- a browser-writable
--   leaderboard is a leaderboard anyone can cheat.
--
-- BALANCE DECOUPLING:
--   These are competitive STATS only (hands, winnings, jackpots). They are
--   deliberately separate from any wallet/chip_balance so the public board can
--   never drive a real-money payout and can never drift a player's balance.
-- ============================================================================

create table if not exists public.blackjack_leaderboard (
  player_id       uuid primary key,
  display_name    text not null default 'Player',
  hands_played    bigint not null default 0,
  hands_won       bigint not null default 0,
  total_winnings  bigint not null default 0,
  biggest_win     bigint not null default 0,
  jackpots_won    bigint not null default 0,   -- B-CARDD BET hits (the marquee stat)
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);

-- Heal an older/hand-made table that predates one of these columns.
alter table public.blackjack_leaderboard add column if not exists display_name   text not null default 'Player';
alter table public.blackjack_leaderboard add column if not exists hands_played   bigint not null default 0;
alter table public.blackjack_leaderboard add column if not exists hands_won      bigint not null default 0;
alter table public.blackjack_leaderboard add column if not exists total_winnings bigint not null default 0;
alter table public.blackjack_leaderboard add column if not exists biggest_win    bigint not null default 0;
alter table public.blackjack_leaderboard add column if not exists jackpots_won   bigint not null default 0;
alter table public.blackjack_leaderboard add column if not exists created_at     timestamptz not null default now();
alter table public.blackjack_leaderboard add column if not exists updated_at     timestamptz not null default now();

-- The board is always ordered by total_winnings desc, limit 50.
create index if not exists idx_bj_leaderboard_winnings
  on public.blackjack_leaderboard (total_winnings desc);

-- ---- Row Level Security -------------------------------------------------
-- Public can READ the board. Writes happen only via the service-role edge
-- function (service role bypasses RLS), so there is intentionally no public
-- write policy.
alter table public.blackjack_leaderboard enable row level security;

drop policy if exists "blackjack_leaderboard public read" on public.blackjack_leaderboard;
create policy "blackjack_leaderboard public read"
  on public.blackjack_leaderboard
  for select
  using (true);

-- keep updated_at honest on every write
create or replace function public.touch_blackjack_leaderboard_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at := now();
  return new;
end;
$$;

drop trigger if exists trg_bj_leaderboard_touch on public.blackjack_leaderboard;
create trigger trg_bj_leaderboard_touch
  before update on public.blackjack_leaderboard
  for each row execute function public.touch_blackjack_leaderboard_updated_at();
