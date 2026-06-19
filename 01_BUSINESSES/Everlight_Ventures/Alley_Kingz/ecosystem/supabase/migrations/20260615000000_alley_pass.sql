-- ============================================================================
-- ALLEY KINGZ -- FORTNITE LAYER, PHASE 1a: THE ALLEY PASS (battle pass)
-- Player progress only. The reward TRACK (per-tier free/premium rewards) is a
-- constant in the ak-pass edge function (easy to tune; no seed migration). Pass
-- rewards are paid through the existing ak_grants inbox -> client claimGrants().
-- Season reset (Phase 2) will add ak_seasons + pg_cron. Idempotent / additive.
-- Targets AK's OWN project mfghdobptredxxhbjwyz (never the casino).
-- ============================================================================
create table if not exists public.ak_pass_progress (
  user_id      uuid primary key,
  season       int  not null default 1,
  xp           int  not null default 0,        -- xp within the current season
  tier         int  not null default 0,        -- derived = floor(xp / xp_per_tier), capped
  premium      boolean not null default false, -- unlocked the premium lane (Gems, via shop)
  claimed_free int[] not null default '{}',    -- free tiers already claimed
  claimed_prem int[] not null default '{}',    -- premium tiers already claimed
  daily_xp     int  not null default 0,        -- anti-grind: xp earned today
  daily_day    date,
  updated_at   timestamptz not null default now()
);

alter table public.ak_pass_progress enable row level security;
alter table public.ak_pass_progress force row level security;

drop policy if exists ak_pass_sel on public.ak_pass_progress;
-- a player reads ONLY their own pass progress; all writes are service-role (ak-pass edge fn).
create policy ak_pass_sel on public.ak_pass_progress
  for select to authenticated using (user_id = auth.uid());

-- END Alley Pass progress.
