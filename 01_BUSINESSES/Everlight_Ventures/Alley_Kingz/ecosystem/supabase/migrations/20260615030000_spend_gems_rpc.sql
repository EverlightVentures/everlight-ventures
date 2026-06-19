-- ============================================================================
-- ALLEY KINGZ -- ATOMIC GEM SPEND (shared-currency safe)
-- Gems live in game_currencies (player_id, game_id='alley-kingz', currency_name=
-- 'gems', balance) and are ALSO written by the shop edge fn. To charge gems from
-- ak-pass (premium unlock) without a lost-update race, spend through this single
-- atomic UPDATE guarded by balance >= amount. Returns the NEW balance, or -1 if
-- insufficient / no wallet row. SECURITY DEFINER so the service role can call it.
-- ============================================================================
create or replace function public.ak_spend_gems(p_player text, p_amount bigint)
returns bigint
language plpgsql
security definer
set search_path = public
as $$
declare new_bal bigint;
begin
  if p_amount is null or p_amount <= 0 then return -1; end if;
  update public.game_currencies
     set balance = balance - p_amount, updated_at = now()
   where player_id = p_player
     and game_id = 'alley-kingz'
     and currency_name = 'gems'
     and balance >= p_amount
  returning balance into new_bal;
  if new_bal is null then return -1; end if;   -- insufficient funds or no wallet
  return new_bal;
end $$;

revoke all on function public.ak_spend_gems(text, bigint) from public, anon, authenticated;
-- service role (edge functions) calls it; never the client directly.

-- END atomic gem spend.
