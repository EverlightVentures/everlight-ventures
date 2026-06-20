-- ============================================================================
-- ALLEY KINGZ -- RAID / BASE DEFENSE  (Boom-Beach snapshot-as-bot war map + shields)
-- Target: AK's OWN Supabase project  mfghdobptredxxhbjwyz  (NEVER the casino project).
-- Source spec: ecosystem/game/systems/raid.js + specs/WAVE_INTEGRATION.md E2 +
--              AK_RAID_DEFENSE_SYSTEM.md.
--
-- SECURITY MODEL (mirrors social_layer + grants_donations + ak_trading):
--   * RLS FORCED on every table.
--   * anon / authenticated may SELECT only what they are entitled to
--     (bot bases are public bot data -> readable; raid state + revenge are
--     OWN-rows-only). NO insert/update/delete policy exists -> every direct
--     client write is denied. The ak-raid edge fn (service role) is the ONLY
--     writer and re-enforces every rule.
--   * Loot delivery rides the EXISTING public.ak_grants rail (grants_donations):
--     the server only ever GRANTS soft currency (gold / scrap); it never grants
--     gems, cards, or any $BCARDD/ALK line.
--
-- CRYPTO GATE (HARD LAW, the load-bearing fix 2 verifiers caught):
--   * Loot is soft-currency ONLY (gold + scrap). A CHECK + the edge-fn FORBID
--     reject any $BCARDD/ALK token on loot or roster-as-loot.
--   * Shields purchased on the SERVER are GEM-TIER ONLY (Fortress Dome 80 /
--     Panic 160). Gold tiers settle client-side. No ALK/$BCARDD shield pricing.
--   * Gems are server-only -> spent via the existing public.ak_spend_gems RPC.
--   * PARITY INVARIANT: a gem shield only buys a TIMER (hours of peace), never a
--     rate/cap/ceiling.
--
-- Idempotent: safe to re-run (IF NOT EXISTS / drop-then-create policies).
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. BOT BASES (snapshot-as-bot rival crews; Boom-Beach async targets)
--    Deterministic per ~12-min rotation window (window_id). The edge fn
--    generates + upserts the window's 3 bases (faction / tier / roster of REAL
--    card names / per-building levels / loot / seed). snap_user_id is the hook
--    for a future real-player snapshot job (null = pure-bot, the MVP path).
-- ----------------------------------------------------------------------------
create table if not exists public.ak_bot_bases (
  id           uuid primary key default gen_random_uuid(),
  window_id    bigint not null,                       -- floor(epoch_ms / 720000)  (~12 min)
  slot         int    not null,                       -- 0..2 within the window
  name         text   not null,                       -- gang name (e.g. "The Boneyard Mob")
  faction      text   not null,                       -- boneguard_crew | zoomie_syndicate | leashbreak_tactix | k9_circuitry
  cls          text   not null,                       -- display class label
  accent       text   not null,                       -- hex accent for the war-map card
  tier         int    not null,                       -- 1..3 difficulty stars
  trophies     int    not null default 0,
  roster       jsonb  not null default '[]'::jsonb,    -- ["Tank Pug","Granite Saint",...] REAL names, Mythic NEVER fielded
  buildings    jsonb  not null default '[]'::jsonb,    -- [{id,name,lvl},...] 5 producer buildings, independent levels
  loot         jsonb  not null default '{}'::jsonb,    -- {gold,scrap,scrapR}  soft-currency ONLY
  city         int    not null default 1,             -- battler launch: map city index
  level        int    not null default 2,             -- battler launch: difficulty level
  diff_offset  int    not null default 0,             -- battler launch: AI curve offset
  seed         bigint not null default 0,             -- deterministic mulberry32 seed
  snap_user_id uuid,                                  -- real-player snapshot origin (null = bot)
  created_at   timestamptz not null default now(),
  unique (window_id, slot),
  constraint ak_bot_faction_chk check (faction in
    ('boneguard_crew','zoomie_syndicate','leashbreak_tactix','k9_circuitry')),
  constraint ak_bot_tier_chk check (tier between 1 and 3),
  -- HARD LAW: a bot base can never field $BCARDD/ALK as loot (roster is flavor; loot
  -- text is guarded here as defense-in-depth behind the edge-fn FORBID).
  constraint ak_bot_loot_token_chk check ((loot->>'scrapR') is null or (loot->>'scrapR') !~* '\$|bcardd|alk')
);
create index if not exists ak_bot_bases_window_idx on public.ak_bot_bases (window_id, slot);

-- ----------------------------------------------------------------------------
-- 2. RAID STATE (per-player shield + anti-chain + reinforce cooldown)
--    Server-authoritative for GEM shields (gems are server-only). Gold shields
--    stay client-side. shield_until lets a future snapshot job skip shielded
--    players when picking real-base targets.
-- ----------------------------------------------------------------------------
create table if not exists public.ak_raid_state (
  user_id          uuid primary key references auth.users(id) on delete cascade,
  shield_until     timestamptz not null default 'epoch',
  last_raid_at     timestamptz,
  last_reinforce_at timestamptz,
  updated_at       timestamptz not null default now()
);

-- ----------------------------------------------------------------------------
-- 3. RAID LOG (anti-farm ledger: one loot payout per base per raider)
--    Replays still play for fun; loot pays once (mirrors the night-defense
--    once-per-cycle cap in raid.js endDefense()).
-- ----------------------------------------------------------------------------
create table if not exists public.ak_raid_log (
  id          uuid primary key default gen_random_uuid(),
  raider_id   uuid not null,
  base_id     uuid not null references public.ak_bot_bases(id) on delete cascade,
  window_id   bigint not null,
  is_revenge  boolean not null default false,
  loot_gold   int not null default 0,
  loot_scrap  int not null default 0,
  loot_scrapr text,
  created_at  timestamptz not null default now(),
  unique (raider_id, base_id)                         -- HARD anti-farm: loot a base once
);
create index if not exists ak_raid_log_raider_idx on public.ak_raid_log (raider_id, created_at desc);

-- ----------------------------------------------------------------------------
-- 4. REVENGE INBOX (server pushes a 24h revenge row when a player is raided
--    offline). The victim reads it via ak-raid {action:'revenge'} and merges it
--    into local p.raid.revenge (shape {name,faction,tier,at}). Only fires when a
--    base is a REAL-player snapshot (snap_user_id set); pure bots take no revenge.
-- ----------------------------------------------------------------------------
create table if not exists public.ak_raid_revenge (
  id               uuid primary key default gen_random_uuid(),
  victim_id        uuid not null,                     -- the player who was raided offline
  attacker_name    text not null default 'Rival Crew',
  attacker_faction text,
  tier             int  not null default 2,
  claimed          boolean not null default false,
  created_at       timestamptz not null default now(),
  expires_at       timestamptz not null default (now() + interval '24 hours'),
  constraint ak_revenge_faction_chk check (attacker_faction is null or attacker_faction in
    ('boneguard_crew','zoomie_syndicate','leashbreak_tactix','k9_circuitry'))
);
create index if not exists ak_raid_revenge_victim_idx on public.ak_raid_revenge (victim_id, claimed, expires_at);

-- ============================================================================
-- ROW-LEVEL SECURITY  (anon read-only + own-rows; all writes service-role)
-- ============================================================================
alter table public.ak_bot_bases    enable row level security;
alter table public.ak_raid_state   enable row level security;
alter table public.ak_raid_log     enable row level security;
alter table public.ak_raid_revenge enable row level security;

alter table public.ak_bot_bases    force row level security;
alter table public.ak_raid_state   force row level security;
alter table public.ak_raid_log     force row level security;
alter table public.ak_raid_revenge force row level security;

drop policy if exists ak_bot_bases_sel    on public.ak_bot_bases;
drop policy if exists ak_raid_state_sel   on public.ak_raid_state;
drop policy if exists ak_raid_log_sel     on public.ak_raid_log;
drop policy if exists ak_raid_revenge_sel on public.ak_raid_revenge;

-- Bot bases are public bot data (no PII) -> readable by anyone signed in (the war
-- map can fall back to a direct read; the fn is the normal path).
create policy ak_bot_bases_sel on public.ak_bot_bases
  for select to anon, authenticated using (true);

-- Raid state / log / revenge are OWN-rows-only.
create policy ak_raid_state_sel on public.ak_raid_state
  for select to authenticated using (user_id = auth.uid());
create policy ak_raid_log_sel on public.ak_raid_log
  for select to authenticated using (raider_id = auth.uid());
create policy ak_raid_revenge_sel on public.ak_raid_revenge
  for select to authenticated using (victim_id = auth.uid() and expires_at > now());

-- NOTE: no INSERT/UPDATE/DELETE policies exist for anon/authenticated by design.
-- With RLS forced and no write policy, every direct client write is denied; the
-- service-role ak-raid edge function is the only writer.

-- ============================================================================
-- REALTIME: publish revenge so the war-map REVENGE tab can light up live.
-- ============================================================================
do $$
begin
  if exists (select 1 from pg_publication where pubname = 'supabase_realtime') then
    execute 'alter publication supabase_realtime add table public.ak_raid_revenge';
  end if;
exception when duplicate_object then null;  -- already in publication on re-run
end $$;

-- ============================================================================
-- HOUSEKEEPING (pg_cron; no-op if pg_cron is not enabled)
--   - prune bot bases older than ~2h (a few rotation windows back)
--   - expire revenge rows past their 24h window
-- ============================================================================
do $$
begin
  if exists (select 1 from pg_extension where extname = 'pg_cron') then
    perform cron.schedule('ak_raid_prune', '20 9 * * *', $cron$
      delete from public.ak_bot_bases where created_at < now() - interval '2 hours';
      delete from public.ak_raid_revenge where expires_at < now() - interval '1 hour';
    $cron$);
  end if;
exception when others then null;  -- pg_cron absent / insufficient priv -> wire later
end $$;

-- END Alley Kingz raid / base-defense.
