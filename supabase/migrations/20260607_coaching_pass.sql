-- ============================================================================
-- Pro Coaching -- the premium AI-dealer feature (Gold-funded, compliant).
-- ----------------------------------------------------------------------------
-- Adds the day-pass expiry to player_accounts. The premium conversational AI
-- dealer is paid for in GOLD COINS (chip_balance) -- NEVER Sweeps Coins -- so the
-- sweepstakes safe harbor (SC = free + redeemable-only) is preserved. While
-- coaching_pass_until is in the future, the player gets unlimited AI coaching with
-- no per-message Gold charge; otherwise each AI reply costs Gold = 3x token cost
-- (floored). All metering is server-side in functions/blackjack-api (dealer-ai +
-- buy-coaching-pass actions) so it cannot be spoofed from the browser.
--
-- Idempotent: safe to run against the existing prod player_accounts table.
-- ============================================================================
alter table public.player_accounts
  add column if not exists coaching_pass_until timestamptz;

comment on column public.player_accounts.coaching_pass_until is
  'Pro Coaching day-pass expiry. NULL/past = pay-per-message in Gold; future = unlimited AI coaching. Set by blackjack-api buy-coaching-pass.';
