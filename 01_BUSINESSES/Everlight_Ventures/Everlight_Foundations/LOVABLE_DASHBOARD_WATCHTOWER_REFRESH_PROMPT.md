# Lovable Prompt: Everlight `/dashboard` Watchtower Refresh

Paste this into Lovable to replace the current placeholder `/dashboard` route with a real public watchtower page.

Do not use mock numbers. Do not hardcode XLM price. Do not fall back to generic homepage content. This page must read live data from Supabase and say plainly when the feed is stale.

## Build goal

Create a public `/dashboard` page for Everlight Ventures that shows:

- live XLM watchtower status
- current XLM price
- whether the feed is healthy or stale
- whether the bot is waiting, in a trade, or blocked
- one plain-English explanation of what the machine is doing
- a small recent performance section

This is a public proof page, not an operator console. Keep private balances, controls, and detailed strategy internals out of it.

## Data source

Use the existing Supabase connection already configured in the site.

Primary tables:

- `xlm_bot_metrics` -> single live row where `id = 1`
- `xlm_bot_timeseries` -> equity / pnl trend
- `xlm_bot_trade_labels` -> most recent reviewed trade

## Field priority

For text labels, prefer these human-ready fields from `xlm_bot_metrics` first:

- `public_system_state`
- `public_setup_state`
- `public_market_climate`
- `public_tick_status`
- `public_data_status`
- `public_decision_label`
- `public_pressure_note`
- `public_status_blurb`
- `public_decision_age_label`
- `public_brief_age_label`
- `public_price_age_label`

If one of those is missing, then fall back to the raw field and format it gently.

Key raw fields still needed:

- `contract_mark_price`
- `generated_at`
- `data_quality_status`
- `stream_status`
- `bot_state`
- `entry_signal`
- `pulse_regime`
- `tick_health`
- `goal_progress_pct`
- `pnl_today_usd`
- `equity_usd`
- `win_rate_pct`

## Page structure

1. Hero

- Eyebrow: `Public Trading Watchtower`
- Headline: `Live system status for the XLM machine`
- Short copy:
  This page shows whether the live feed is current, whether the machine is waiting or active, and what the latest public telemetry says. If the data is stale, say that directly.

2. Four primary cards

- `Live Price`
  - value: `contract_mark_price`
  - sublabel: `public_price_age_label`
- `System State`
  - value: `public_system_state`
  - sublabel: `public_data_status`
- `Trade Setup`
  - value: `public_setup_state`
  - sublabel: `public_decision_age_label`
- `Market Climate`
  - value: `public_market_climate`
  - sublabel: `public_brief_age_label`

3. Status strip

- show pills for:
  - `data_quality_status`
  - `stream_status`
- one sentence using `public_status_blurb`
- one sentence using `public_decision_label`
- one sentence using `public_pressure_note`

4. Performance block

- daily pnl
- equity
- win rate
- daily goal progress bar
- simple line chart from `xlm_bot_timeseries`

5. Recent trade block

- pull latest row from `xlm_bot_trade_labels` ordered by `ts desc`
- show:
  - status
  - side
  - result
  - pnl
  - hold minutes
  - exit reason

## Tone and wording

Use plain English first, then the trading term in parentheses when helpful.

Examples:

- `Price feed is lagging (stale tick)`
- `Risk is elevated (danger regime)`
- `Sellers are getting forced out (short liquidations / squeeze pressure)`
- `No clean trade setup yet`

Avoid jargon-only labels like:

- `entry_blocked_no_signal`
- `tick stale`
- `pulse danger`
- `liquidation bias`

Translate those into human wording on screen.

## UX rules

- If `data_quality_status` is `degraded`, show an amber or red warning banner.
- If the Supabase query fails, show `Live data temporarily unavailable` instead of blank cards.
- Do not show mock data.
- Do not show private operator controls.
- Keep the page visually aligned with the Everlight brand already on the live site.

## Important routing fix

The current `/dashboard` route is effectively falling back to the generic site shell. Create a dedicated route/page component so `/dashboard` renders this watchtower page directly.
