-- ============================================================================
-- ALLEY KINGZ -- RAID: REAL-PLAYER BASES  (snapshot-as-bot, but the bot IS a
-- real player's published base). Builds on 20260620010000_ak_raid.sql.
-- Target: AK's OWN Supabase project  mfghdobptredxxhbjwyz  (NEVER the casino project).
--
-- WHY: today ak-raid {action:'targets'} serves only the 3 procedural bot bases.
-- This migration adds the table the edge fn needs to ALSO serve REAL players'
-- published base snapshots (their producer-building levels + trophies + crew),
-- so raids hit live rivals -- with bots kept as the degrade fallback. Loot stays
-- server-authoritative (ak_grants), shielded victims are skipped, and a raid on a
-- real base pushes a 24h revenge row to that player.
--
-- SECURITY MODEL (mirrors ak_raid + social_layer):
--   * RLS FORCED. A player may SELECT only their OWN published base. The ak-raid
--     edge fn (service role) is the SOLE reader-for-others + SOLE writer; there is
--     NO insert/update/delete policy, so every direct client write is denied.
--   * The public name is a CANON crew gang name (chosen server-side from the
--     player's crew faction or a deterministic uid seed) -- never free-text PII.
--
-- CRYPTO GATE (HARD LAW): loot is soft-currency ONLY (gold + scrap). The CHECK
--   below + the edge-fn FORBID regex reject any $BCARDD/ALK token on a loot line.
--   Mythic is NEVER fielded as a defender (roster is built from the tier ladder,
--   which caps at Legendary). No gems/cards in raid loot.
--
-- Idempotent: safe to re-run.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. PLAYER BASES (one published snapshot per player; upserted on publish-base)
--    user_id IS the key + the served base id (resolve() looks it up by user_id
--    when a base_id is not a bot uuid). Stored fields mirror ak_bot_bases so the
--    war map renders a player base byte-identically to a bot.
-- ----------------------------------------------------------------------------
create table if not exists public.ak_player_bases (
  user_id      uuid primary key references auth.users(id) on delete cascade,
  name         text   not null,                       -- canon gang name (no PII)
  faction      text   not null,                       -- boneguard_crew | zoomie_syndicate | leashbreak_tactix | k9_circuitry
  cls          text   not null,                       -- display class label
  accent       text   not null,                       -- hex accent for the war-map card
  tier         int    not null default 1,             -- 1..3 difficulty stars
  trophies     int    not null default 0,
  roster       jsonb  not null default '[]'::jsonb,    -- ["Tank Pug",...] REAL names, Mythic NEVER fielded
  buildings    jsonb  not null default '[]'::jsonb,    -- [{id,name,lvl},...] the player's 5 producer levels
  loot         jsonb  not null default '{}'::jsonb,    -- {gold,scrap,scrapR}  soft-currency ONLY (server-computed)
  city         int    not null default 1,
  level        int    not null default 2,
  diff_offset  int    not null default 0,
  seed         bigint not null default 0,
  updated_at   timestamptz not null default now(),
  created_at   timestamptz not null default now(),
  constraint ak_pb_faction_chk check (faction in
    ('boneguard_crew','zoomie_syndicate','leashbreak_tactix','k9_circuitry')),
  constraint ak_pb_tier_chk check (tier between 1 and 3),
  -- HARD LAW: a player base can never field $BCARDD/ALK as loot.
  constraint ak_pb_loot_token_chk check ((loot->>'scrapR') is null or (loot->>'scrapR') !~* '\$|bcardd|alk')
);
create index if not exists ak_player_bases_updated_idx on public.ak_player_bases (updated_at desc);

alter table public.ak_player_bases enable row level security;
alter table public.ak_player_bases force  row level security;

drop policy if exists ak_player_bases_sel on public.ak_player_bases;
-- Own-row only. The edge fn (service role) serves OTHER players' bases as raid
-- targets; clients never read a peer's base directly (it carries their layout).
create policy ak_player_bases_sel on public.ak_player_bases
  for select to authenticated using (user_id = auth.uid());
-- NOTE: no INSERT/UPDATE/DELETE policy by design -> all writes go through ak-raid.

-- ----------------------------------------------------------------------------
-- 2. RELAX ak_raid_log so it can ledger raids on BOTH bot bases AND player bases.
--    * Drop the FK to ak_bot_bases: a player-base raid logs base_id = victim uid,
--      which is not a row in ak_bot_bases.
--    * Swap the once-ever unique (raider_id, base_id) for a once-per-WINDOW unique
--      (raider_id, base_id, window_id). Bot base uuids only exist in one window, so
--      bot behavior is unchanged; player bases (stable id) become re-raidable in a
--      later rotation window -- the Boom-Beach async cadence.
-- ----------------------------------------------------------------------------
do $$ begin
  alter table public.ak_raid_log drop constraint if exists ak_raid_log_base_id_fkey;
exception when others then null; end $$;

do $$ begin
  alter table public.ak_raid_log drop constraint if exists ak_raid_log_raider_id_base_id_key;
exception when others then null; end $$;

do $$ begin
  alter table public.ak_raid_log add constraint ak_raid_log_once_per_window
    unique (raider_id, base_id, window_id);
exception when duplicate_object then null; when duplicate_table then null; when others then null; end $$;

-- ----------------------------------------------------------------------------
-- 3. HOUSEKEEPING: drop player bases that have gone stale (no publish in ~7 days)
--    so the war map only serves recently-active rivals. no-op without pg_cron.
-- ----------------------------------------------------------------------------
do $$
begin
  if exists (select 1 from pg_extension where extname = 'pg_cron') then
    perform cron.schedule('ak_player_base_prune', '25 9 * * *', $cron$
      delete from public.ak_player_bases where updated_at < now() - interval '7 days';
    $cron$);
  end if;
exception when others then null;
end $$;

-- END Alley Kingz raid -- real-player bases.
