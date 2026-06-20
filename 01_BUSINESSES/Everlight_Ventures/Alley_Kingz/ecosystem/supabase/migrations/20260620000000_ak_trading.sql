-- ============================================================================
-- ALLEY KINGZ -- THE TRADING POST  (player barter board; keeper "Switch the Broker")
-- Target: AK's OWN Supabase project  mfghdobptredxxhbjwyz  (NEVER the casino project).
-- Source spec: ecosystem/game/systems/trading.js (:649-:713) + specs/WAVE_INTEGRATION.md E3.
--
-- SECURITY MODEL (mirrors social_layer + grants_donations):
--   * RLS FORCED on. NO insert/update/delete policy exists for anon/authenticated by
--     design -> every direct client write is denied. The ak-trading edge fn (service
--     role) is the ONLY writer and re-enforces every rule (FORBID gems/Mythic/$BCARDD,
--     DAILY<=5, BAND match, soft-goods-only).
--   * A player may SELECT only OPEN, non-expired listings + their own rows (the board +
--     the MINE tab). Sellers' identities on the board are already denormalized
--     (seller_name) so no cross-user PII leaks.
--   * Delivery rides the EXISTING public.ak_grants rail (grants_donations migration):
--     the server only ever GRANTS soft currency; it never deducts client inventory.
--     Anti-dupe by construction -- client deducts on deposit, a failed call refunds.
--
-- Idempotent: safe to re-run (IF NOT EXISTS / drop-then-create policies).
-- No money rail -- soft-currency + card-copy barter only (brand-safe; HARD LAW).
-- ============================================================================

create table if not exists public.ak_trade_listings (
  id           uuid primary key default gen_random_uuid(),
  seller_id    uuid not null references auth.users(id) on delete cascade,
  seller_name  text not null default 'Stray',
  give_kind    text not null,                  -- 'card' (cosmetic reserved; never gems/$BCARDD)
  give_card_id text,                            -- card name (the only stock is the 106 canon cards)
  give_rarity  text,                            -- Common|Rare|Epic|Legendary  (Mythic FORBIDDEN)
  give_amount  int  not null default 1,
  want_kind    text not null,                   -- 'gold' | 'scrap' | 'card'
  want_card_id text,
  want_rarity  text,                            -- scrap rarity when want_kind='scrap'
  want_amount  int  not null default 0,
  band         int  not null default 0,         -- floor(trophies/400); you trade your own bracket
  status       text not null default 'open',    -- open | filled | cancelled | expired
  filled_by    uuid,                            -- acceptor (auth.uid)
  filled_at    timestamptz,
  created_at   timestamptz not null default now(),
  expires_at   timestamptz not null default (now() + interval '48 hours'),
  -- HARD-LAW DB guards (defense-in-depth behind the edge-fn FORBID):
  constraint ak_trade_give_kind_chk check (give_kind in ('card','cosmetic')),
  constraint ak_trade_want_kind_chk check (want_kind in ('gold','scrap','card')),
  constraint ak_trade_status_chk    check (status in ('open','filled','cancelled','expired')),
  constraint ak_trade_give_rar_chk  check (give_rarity is null or give_rarity <> 'Mythic'),
  constraint ak_trade_want_rar_chk  check (want_rarity is null or want_rarity <> 'Mythic'),
  -- $BCARDD / ALK / any $ token can never appear on either leg (the RMT + securities line).
  constraint ak_trade_give_token_chk check (give_card_id is null or give_card_id !~* '\$|bcardd|alk'),
  constraint ak_trade_want_token_chk check (want_card_id is null or want_card_id !~* '\$|bcardd|alk')
);

create index if not exists ak_trade_board_idx on public.ak_trade_listings (status, band, created_at desc);
create index if not exists ak_trade_seller_idx on public.ak_trade_listings (seller_id, status);

alter table public.ak_trade_listings enable row level security;
alter table public.ak_trade_listings force  row level security;

-- ---- SELECT policy (read-only; writes are service-role only) ----
drop policy if exists ak_trade_sel on public.ak_trade_listings;
-- A signed-in player may read OPEN non-expired offers (the board) + any of their OWN rows
-- (the MINE tab, incl. filled/cancelled history). No write policy => all writes via the fn.
create policy ak_trade_sel on public.ak_trade_listings
  for select to authenticated
  using (seller_id = auth.uid()
         or (status = 'open' and expires_at > now()));

-- ---- publish to Realtime so the board can refresh live (best-effort) ----
do $$
begin
  if exists (select 1 from pg_publication where pubname = 'supabase_realtime') then
    execute 'alter publication supabase_realtime add table public.ak_trade_listings';
  end if;
exception when duplicate_object then null;  -- already in publication on re-run
end $$;

-- ---- expire stale open listings nightly (pg_cron; no-op if not enabled) ----
-- Note: the edge fn also treats expires_at<now() as not-open at accept time, so this is
-- just housekeeping to keep the board clean. The deposited card is NOT auto-refunded on
-- expiry (the client holds the deduction); cancel from the MINE tab refunds it.
do $$
begin
  if exists (select 1 from pg_extension where extname = 'pg_cron') then
    perform cron.schedule('ak_trade_expire', '15 9 * * *', $cron$
      update public.ak_trade_listings set status = 'expired'
       where status = 'open' and expires_at < now();
    $cron$);
  end if;
exception when others then null;  -- pg_cron absent / insufficient priv -> wire later
end $$;

-- END The Trading Post.
