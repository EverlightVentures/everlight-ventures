-- Alley Kingz cloud save: one jsonb row per Google-authed player.
-- Mirrors every ak_* localStorage key so progress follows the account
-- (same auth rails as blackjack, separate product surface -- own table only).
-- Idempotent: safe to re-run.

create table if not exists public.ak_player_saves (
  user_id  uuid primary key references auth.users(id) on delete cascade,
  save     jsonb not null default '{}'::jsonb,
  saved_at timestamptz not null default now()
);

alter table public.ak_player_saves enable row level security;

-- owner-only: a player reads/writes exactly their own save
drop policy if exists ak_saves_own on public.ak_player_saves;
create policy ak_saves_own on public.ak_player_saves
  for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);
