-- ============================================================================
-- ALLEY KINGZ -- FORTNITE LAYER, PHASE 1c: THE DROP + DRIP (cosmetics)
-- Cosmetic OWNERSHIP is server-side (persists, can't be lost). The catalog (ids,
-- names, CSS-filter recipes) + EQUIP state live client-side (drip.js / localStorage)
-- -- equipping is a visual pref and the engine applies the filter at draw time.
-- Purchases deduct in-game Gold client-side (cosmetic = no pay-to-win, low stakes);
-- the server just records what you own. Idempotent / additive. AK project only.
-- ============================================================================
create table if not exists public.ak_owned_cosmetics (
  user_id     uuid not null,
  cosmetic_id text not null,
  source      text default 'shop',
  acquired_at timestamptz not null default now(),
  primary key (user_id, cosmetic_id)
);

alter table public.ak_owned_cosmetics enable row level security;
alter table public.ak_owned_cosmetics force row level security;
drop policy if exists ak_cos_sel on public.ak_owned_cosmetics;
create policy ak_cos_sel on public.ak_owned_cosmetics for select to authenticated using (user_id = auth.uid());

-- END cosmetics.
