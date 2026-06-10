-- ============================================================================
-- DOWN migration for 20260607_alley_kingz_economy.sql
-- ============================================================================
-- Author: Amara Osei. Reverses ONLY the tables this migration OWNS (the ak_* set).
--
-- INTENTIONALLY NOT REVERSED -- shared infra we only HEALED, never owned:
--   * public.game_currencies   (live: NOS bottles, blackjack gems/chips)
--   * public.player_accounts   (live: arcade accounts, lives, passes)
-- Dropping those would break the blackjack + arcade products that already write
-- them. A heal is not reversible without data loss, so we leave them in place.
-- (We also do NOT drop the shared ak_touch_updated_at function if other objects
-- still reference it -- DROP ... cascade is deliberately avoided.)
--
-- Order matters: ak_chest_inventory FKs ak_shop_products, so drop it first.
-- ============================================================================

-- 1. Player-state tables ----------------------------------------------------
drop table if exists public.ak_transactions;
drop table if exists public.ak_chest_inventory;   -- FK -> ak_shop_products (drop before it)
drop table if exists public.ak_tower_levels;
drop table if exists public.ak_card_inventory;

-- 2. Reference tables -------------------------------------------------------
drop table if exists public.ak_shop_products;
drop table if exists public.ak_level_costs;
drop table if exists public.ak_card_catalog;

-- 3. Triggers we added to the SHARED game_currencies (leave the table itself) -
drop trigger if exists trg_game_currencies_touch on public.game_currencies;

-- 4. Drop the touch helper ONLY if nothing else uses it. We guard it: if any
--    trigger still depends on it, the drop is skipped (no cascade).
do $$
begin
  if not exists (
    select 1 from pg_trigger tg
    join pg_proc p on p.oid = tg.tgfoid
    where p.proname = 'ak_touch_updated_at' and not tg.tgisinternal
  ) then
    drop function if exists public.ak_touch_updated_at();
  end if;
end$$;

-- Note: RLS policies on game_currencies (ak_gc_own / ak_game_currencies_service)
-- are left in place -- they are harmless and the live edge functions use the
-- service role which bypasses RLS regardless.
