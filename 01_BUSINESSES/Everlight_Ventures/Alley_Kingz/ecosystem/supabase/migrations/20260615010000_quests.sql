-- ============================================================================
-- ALLEY KINGZ -- FORTNITE LAYER, PHASE 1b: THE HIT LIST (daily/weekly quests)
-- Raw-counter model: per-period counters (daily key = date, weekly key = ISO
-- week) bumped as the player plays/donates/chats; quest definitions (constant in
-- the ak-quests edge fn) are thresholds against those counters. Claims tracked in
-- a ledger. Rewards pay through ak_grants (or directly bump ak_pass_progress for
-- pass-XP rewards). Idempotent / additive. AK project only.
-- ============================================================================
create table if not exists public.ak_period_stats (
  user_id    uuid not null,
  period_key text not null,                 -- 'YYYY-MM-DD' (daily) or 'YYYY-Www' (weekly)
  matches    int  not null default 0,
  wins       int  not null default 0,
  gates      int  not null default 0,
  donates    int  not null default 0,
  chats      int  not null default 0,
  updated_at timestamptz not null default now(),
  primary key (user_id, period_key)
);

create table if not exists public.ak_quest_claims (
  user_id    uuid not null,
  quest_id   text not null,
  period_key text not null,
  claimed_at timestamptz not null default now(),
  primary key (user_id, quest_id, period_key)
);

alter table public.ak_period_stats enable row level security;
alter table public.ak_period_stats force row level security;
alter table public.ak_quest_claims enable row level security;
alter table public.ak_quest_claims force row level security;

drop policy if exists ak_pstats_sel on public.ak_period_stats;
drop policy if exists ak_qclaims_sel on public.ak_quest_claims;
-- players read only their own counters / claims; all writes are service-role.
create policy ak_pstats_sel  on public.ak_period_stats for select to authenticated using (user_id = auth.uid());
create policy ak_qclaims_sel on public.ak_quest_claims for select to authenticated using (user_id = auth.uid());

-- END Hit List.
