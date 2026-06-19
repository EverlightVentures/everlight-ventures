-- ============================================================================
-- ALLEY KINGZ -- SOCIAL LAYER, PHASE 1  (Crews + Chat + Donations + Crew-War shell)
-- Target: AK's OWN Supabase project  mfghdobptredxxhbjwyz  (NEVER the casino project).
-- Source map: ecosystem/SOCIAL_LAYER_ARCHITECTURE.md
--
-- SECURITY MODEL (read before editing):
--   * Every table has RLS FORCED on.
--   * anon (the public game key) may SELECT only rows it is entitled to
--     (its own crew, world chat, open crews for browsing). It may NOT
--     insert/update/delete ANYTHING directly.
--   * ALL writes go through edge functions (ak-crew, ak-chat) running with the
--     SERVICE ROLE, which bypasses RLS and enforces the real rules (gold cost,
--     50-member cap, role gates, rate-limit, profanity, ban-check). This mirrors
--     the proven alley-kingz-shop pattern: the server is the only source of truth.
--   * "one crew per player" is a hard DB constraint (unique on user_id), not app logic.
--
-- Idempotent: safe to re-run (IF NOT EXISTS / drop-then-create policies).
-- No money rail -- donations + rewards are in-game value only (brand-safe).
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. CREWS (player clans, each aligned to one of the 4 lore factions)
-- ----------------------------------------------------------------------------
create table if not exists public.ak_crews (
  id             uuid primary key default gen_random_uuid(),
  name           text not null unique,
  tag            text not null,                          -- 2-4 char crew tag e.g. "BONE"
  faction        text not null,                          -- boneguard_crew | zoomie_syndicate | leashbreak_tactix | k9_circuitry
  crest          text not null default 'default',        -- faction base + accent id
  description    text not null default '',
  region         text not null default '',
  privacy        text not null default 'open',           -- open | request | closed
  req_trophies   int  not null default 0,
  trophies       int  not null default 0,                -- aggregate of member ladder
  member_count   int  not null default 1,
  donations_week int  not null default 0,
  war_wins       int  not null default 0,
  created_by     uuid not null,                          -- auth.uid of founder
  created_at     timestamptz not null default now(),
  constraint ak_crews_faction_chk check (faction in
    ('boneguard_crew','zoomie_syndicate','leashbreak_tactix','k9_circuitry')),
  constraint ak_crews_privacy_chk check (privacy in ('open','request','closed')),
  constraint ak_crews_tag_len_chk check (char_length(tag) between 2 and 4)
);

create table if not exists public.ak_crew_members (
  crew_id       uuid not null references public.ak_crews(id) on delete cascade,
  user_id       uuid not null,                           -- auth.uid
  role          text not null default 'member',          -- leader | co | elder | member
  donated_week  int  not null default 0,
  received_week int  not null default 0,
  fame_week     int  not null default 0,                 -- crew-war contribution this season
  joined_at     timestamptz not null default now(),
  last_seen     timestamptz not null default now(),
  primary key (crew_id, user_id),
  unique (user_id),                                      -- HARD: one crew per player
  constraint ak_crew_role_chk check (role in ('leader','co','elder','member'))
);
create index if not exists ak_crew_members_user_idx on public.ak_crew_members(user_id);

create table if not exists public.ak_crew_requests (        -- request-to-join queue (privacy='request')
  id         uuid primary key default gen_random_uuid(),
  crew_id    uuid not null references public.ak_crews(id) on delete cascade,
  user_id    uuid not null,
  status     text not null default 'pending',             -- pending | accepted | rejected
  created_at timestamptz not null default now(),
  unique (crew_id, user_id),
  constraint ak_crew_req_status_chk check (status in ('pending','accepted','rejected'))
);

-- ----------------------------------------------------------------------------
-- 2. DONATIONS ("carry your weight" reciprocal loop -- top retention hook)
-- ----------------------------------------------------------------------------
create table if not exists public.ak_donation_requests (
  id         uuid primary key default gen_random_uuid(),
  crew_id    uuid not null references public.ak_crews(id) on delete cascade,
  user_id    uuid not null,                               -- requester
  card_id    text not null,
  qty_req    int  not null,
  qty_filled int  not null default 0,
  expires_at timestamptz not null,                        -- ~3-8h appointment window
  created_at timestamptz not null default now()
);
create index if not exists ak_donation_req_crew_idx on public.ak_donation_requests(crew_id, created_at desc);

create table if not exists public.ak_donations (
  id           uuid primary key default gen_random_uuid(),
  crew_id      uuid not null,
  request_id   uuid references public.ak_donation_requests(id) on delete set null,
  donor_id     uuid not null,
  recipient_id uuid not null,
  card_id      text not null,
  qty          int  not null,
  created_at   timestamptz not null default now()
);

-- ----------------------------------------------------------------------------
-- 3. CREW WARS (recurring shared win-condition + per-member quota)
--    Until Phase 2 ghost resolver lands, a war = tally of normal ladder wins.
-- ----------------------------------------------------------------------------
create table if not exists public.ak_crew_wars (
  id          uuid primary key default gen_random_uuid(),
  crew_id     uuid not null references public.ak_crews(id) on delete cascade,
  opp_crew_id uuid,
  season      int  not null,
  state       text not null default 'prep',               -- prep | battle | ended
  score       int  not null default 0,
  opp_score   int  not null default 0,
  tickets     int  not null default 4,                    -- per-member match allotment
  starts_at   timestamptz,
  ends_at     timestamptz,
  constraint ak_war_state_chk check (state in ('prep','battle','ended'))
);

create table if not exists public.ak_war_battles (
  war_id     uuid not null references public.ak_crew_wars(id) on delete cascade,
  user_id    uuid not null,
  result     text not null,                               -- win | loss
  fame       int  not null,
  created_at timestamptz not null default now(),
  constraint ak_war_result_chk check (result in ('win','loss'))
);

-- ----------------------------------------------------------------------------
-- 4. CHAT (world + crew) -- send via edge fn, receive via Realtime Postgres Changes
-- ----------------------------------------------------------------------------
create table if not exists public.ak_chat_messages (
  id         bigint generated always as identity primary key,
  scope      text not null,                               -- world | crew
  crew_id    uuid,                                        -- null for world scope
  user_id    uuid not null,
  name       text not null,
  faction    text,
  body       text not null,
  created_at timestamptz not null default now(),
  constraint ak_chat_scope_chk check (scope in ('world','crew')),
  constraint ak_chat_body_len_chk check (char_length(body) between 1 and 200)
);
create index if not exists ak_chat_msg_feed_idx on public.ak_chat_messages(scope, crew_id, created_at desc);

create table if not exists public.ak_chat_bans (
  user_id    uuid primary key,
  until      timestamptz,
  reason     text,
  created_at timestamptz not null default now()
);

create table if not exists public.ak_chat_reports (
  id          bigint generated always as identity primary key,
  message_id  bigint,
  reporter_id uuid,
  reason      text,
  created_at  timestamptz not null default now()
);

-- ============================================================================
-- ROW-LEVEL SECURITY
-- anon = read-only, entitlement-scoped. All writes are service-role (edge fns).
-- ============================================================================
alter table public.ak_crews            enable row level security;
alter table public.ak_crew_members     enable row level security;
alter table public.ak_crew_requests    enable row level security;
alter table public.ak_donation_requests enable row level security;
alter table public.ak_donations        enable row level security;
alter table public.ak_crew_wars        enable row level security;
alter table public.ak_war_battles      enable row level security;
alter table public.ak_chat_messages    enable row level security;
alter table public.ak_chat_bans        enable row level security;
alter table public.ak_chat_reports     enable row level security;

alter table public.ak_crews            force row level security;
alter table public.ak_crew_members     force row level security;
alter table public.ak_crew_requests    force row level security;
alter table public.ak_donation_requests force row level security;
alter table public.ak_donations        force row level security;
alter table public.ak_crew_wars        force row level security;
alter table public.ak_war_battles      force row level security;
alter table public.ak_chat_messages    force row level security;
alter table public.ak_chat_bans        force row level security;
alter table public.ak_chat_reports     force row level security;

-- helper: is the calling user a member of crew :cid ?
create or replace function public.ak_is_crew_member(cid uuid)
returns boolean language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.ak_crew_members m
                 where m.crew_id = cid and m.user_id = auth.uid());
$$;

-- ---- SELECT policies (drop-then-create so re-runs are clean) ----
drop policy if exists ak_crews_sel        on public.ak_crews;
drop policy if exists ak_members_sel      on public.ak_crew_members;
drop policy if exists ak_requests_sel     on public.ak_crew_requests;
drop policy if exists ak_donreq_sel       on public.ak_donation_requests;
drop policy if exists ak_don_sel          on public.ak_donations;
drop policy if exists ak_wars_sel         on public.ak_crew_wars;
drop policy if exists ak_warbattles_sel   on public.ak_war_battles;
drop policy if exists ak_chat_sel         on public.ak_chat_messages;

-- Crews: anyone signed in can browse the crew directory (for join/search).
create policy ak_crews_sel on public.ak_crews
  for select to authenticated using (true);

-- Members roster: visible to fellow crew members only.
create policy ak_members_sel on public.ak_crew_members
  for select to authenticated using (public.ak_is_crew_member(crew_id));

-- Join requests: requester sees their own; crew members see their crew's queue.
create policy ak_requests_sel on public.ak_crew_requests
  for select to authenticated
  using (user_id = auth.uid() or public.ak_is_crew_member(crew_id));

-- Donations + wars: crew-scoped.
create policy ak_donreq_sel on public.ak_donation_requests
  for select to authenticated using (public.ak_is_crew_member(crew_id));
create policy ak_don_sel on public.ak_donations
  for select to authenticated using (public.ak_is_crew_member(crew_id));
create policy ak_wars_sel on public.ak_crew_wars
  for select to authenticated using (public.ak_is_crew_member(crew_id));
create policy ak_warbattles_sel on public.ak_war_battles
  for select to authenticated
  using (exists (select 1 from public.ak_crew_wars w
                 where w.id = war_id and public.ak_is_crew_member(w.crew_id)));

-- Chat: world is readable by all signed-in; crew chat by crew members only.
create policy ak_chat_sel on public.ak_chat_messages
  for select to authenticated
  using (scope = 'world' or (scope = 'crew' and public.ak_is_crew_member(crew_id)));

-- NOTE: no INSERT/UPDATE/DELETE policies exist for anon/authenticated by design.
-- With RLS forced and no write policy, every direct client write is denied;
-- the service-role edge functions (ak-crew, ak-chat) are the only writers.

-- ============================================================================
-- REALTIME: publish chat (+ crew tables for live roster/donation updates)
-- ============================================================================
do $$
begin
  if exists (select 1 from pg_publication where pubname = 'supabase_realtime') then
    execute 'alter publication supabase_realtime add table public.ak_chat_messages';
    execute 'alter publication supabase_realtime add table public.ak_crew_members';
    execute 'alter publication supabase_realtime add table public.ak_donation_requests';
  end if;
exception when duplicate_object then null;  -- already in publication on re-run
end $$;

-- ============================================================================
-- WEEKLY RESET + CHAT PRUNE  (pg_cron; no-op if pg_cron is not enabled)
--   - Mon 00:00 PT (08:00 UTC): zero out donated/received/fame_week + crew donations_week
--   - nightly: prune world chat >7d, crew chat >30d (Comms Doctrine: archive flagged first)
-- ============================================================================
do $$
begin
  if exists (select 1 from pg_extension where extname = 'pg_cron') then
    perform cron.schedule('ak_social_weekly_reset', '0 8 * * 1', $cron$
      update public.ak_crew_members set donated_week=0, received_week=0, fame_week=0;
      update public.ak_crews set donations_week=0;
    $cron$);
    perform cron.schedule('ak_chat_prune', '30 9 * * *', $cron$
      delete from public.ak_chat_messages
       where (scope='world' and created_at < now() - interval '7 days')
          or (scope='crew'  and created_at < now() - interval '30 days');
    $cron$);
  end if;
exception when others then null;  -- pg_cron absent / insufficient priv -> wire later
end $$;

-- END Phase 1 social layer.
