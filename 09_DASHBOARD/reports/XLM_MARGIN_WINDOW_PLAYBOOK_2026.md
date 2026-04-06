# XLM Margin Window Playbook

This playbook is wired into the live bot so position sizing and entry timing align with Coinbase CDE margin behavior.

## Windows

- `INTRADAY_ATTACK`
  - Lower-margin session.
  - Press the best setups.
  - Multi-contract entries can open only when readiness passes and setup quality is at least `FULL`.
  - Default cap: `2` contracts.
  - Objective: close before the cutoff instead of drifting into overnight margin.

- `PRE_CUTOFF_DEFENSE`
  - Final minutes before the overnight transition.
  - No new entries.
  - Manage existing exposure and prefer being flat before the higher-margin window.

- `OVERNIGHT_DEFENSE`
  - Higher-margin session.
  - Trade only if overnight safety is real.
  - Default bias is single-contract only.
  - Multi-contract overnight entries are disabled by default.

## Operating Principle

- Attack during the cheaper intraday window.
- Stop opening fresh risk near the cutoff.
- Treat overnight as defense unless the account is clearly strong enough.
- Margin window, setup quality, and account stage must all agree before size increases.
