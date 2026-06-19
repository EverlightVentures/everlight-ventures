-- ============================================================================
-- ALLEY KINGZ -- GRANTS INBOX (the server -> client economy rail)
-- Phase-1 social polish (donations) AND the foundation Fortnite pass/quest
-- rewards will reuse. The economy lives in the client (ak_profile localStorage,
-- economy.js), so the server can NOT write a player's cards/gold directly without
-- racing the newest-wins cloud save. Instead the server QUEUES a grant here; the
-- client claims unclaimed grants on load and applies them via AK_ECON
-- (addCopy / mutateProfile coins / addScrap / grantChest / addKeys), then the
-- server marks them claimed. Idempotent; additive.
-- ============================================================================
create table if not exists public.ak_grants (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid not null,
  kind       text not null,                 -- card | gold | scrap | chest | keys
  card_id    text,                          -- card name (kind=card)
  rarity     text,                          -- scrap rarity (kind=scrap)
  amount     int  not null default 1,
  source     text,                          -- donation | pass | quest | ...
  note       text,                          -- short human label for the claim toast
  claimed    boolean not null default false,
  created_at timestamptz not null default now(),
  constraint ak_grants_kind_chk check (kind in ('card','gold','scrap','chest','keys'))
);
create index if not exists ak_grants_inbox_idx on public.ak_grants(user_id, claimed, created_at);

alter table public.ak_grants enable row level security;
alter table public.ak_grants force row level security;

drop policy if exists ak_grants_sel on public.ak_grants;
-- a player may READ their own grants (to claim them); writes are service-role only.
create policy ak_grants_sel on public.ak_grants
  for select to authenticated using (user_id = auth.uid());

-- donation requests gain a denormalized requester name for the board UI
alter table public.ak_donation_requests add column if not exists requester_name text;

-- publish grants + donation requests to Realtime so the board + claim toast are live
do $$
begin
  if exists (select 1 from pg_publication where pubname = 'supabase_realtime') then
    execute 'alter publication supabase_realtime add table public.ak_grants';
  end if;
exception when duplicate_object then null;
end $$;

-- END grants inbox.
