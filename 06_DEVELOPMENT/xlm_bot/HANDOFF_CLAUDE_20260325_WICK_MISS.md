# Claude Handoff -- 2026-03-25 Wick Miss

## Context
- User reviewed Coinbase screenshot: `/mnt/sdcard/DCIM/Screenshots/Screenshot_20260325_043454_Coinbase.jpg`
- Instrument: `XLM PERP`
- Chart timeframe in screenshot: `5m`
- Screenshot time: `2026-03-25 04:34 AM PT`
- Complaint: bot was flat during a sharp downside wick and reclaim that appears to have offered an easy long. User wants to know why we were not in a trade and wants the system changed so this type of move is not missed again.

## Chart Read
- The screenshot shows a sharp downside liquidity flush around the `03:00` area, followed by immediate reclaim and mean reversion back toward `0.17926`.
- This is a classic stop-hunt / liquidation wick followed by reclaim.
- By `04:34`, the high-RR part of the move had already happened. The obvious trade was the reclaim after the wick, not a fresh chase at screenshot time.

## Estimated Missed Move
- Approx wick low to screenshot close area: `0.1752 -> 0.17926`
- Approx move: `0.00406`
- Approx point move: `406 points`
- Approx percent move: `2.3%`
- Coinbase XLM perp contract size in this repo is `5000`
- Gross PnL estimate:
  - `1` contract: `0.00406 x 5000 = about $20.30`
  - `2` contracts: `about $40.60`

This matches the user's rough claim that the wick play was about `400 points`.

## Likely Reasons The Bot Stayed Flat

### 1. Overnight entry lock was likely active
- Config has overnight defense enabled.
- Relevant config and logic:
  - `config.yaml`
  - `main.py` around overnight trading auto-detection and playbook handling
- Current local state snapshot showed:
  - `_overnight_trading_ok: "no"`
- Screenshot time `04:34 AM PT` is still in the bot's overnight window. The repo logic blocks new overnight entries when overnight margin is not safe.

Relevant files:
- `config.yaml`
- `main.py`
- `data/state.json`

### 2. Wick/sweep detection is blind to fast 5m reclaim moves
- Current sweep and wick logic is driven off `df_15m` and `df_1h`, not `5m`.
- The screenshot setup is visible on `5m`. If the stop-hunt and reclaim happened within one `15m` candle, the current logic can easily miss it.

Relevant code:
- `strategy/lane_scoring.py`
  - `detect_sweep(...)` uses `df_15m` and `df_1h`
- `strategy/entries.py`
  - `wick_rejection(...)` uses `df_15m`
  - `liquidity_sweep(...)` uses `df_15m` and liquidation intel
- `main.py`
  - entry selection and lane routing only feed those higher timeframes into the setup detectors

### 3. News/analytics layer appears stale, so context quality was degraded
- Local cache files were not fresh for March 25.
- `data/market_brief.json` timestamp was `2026-03-15`
- `data/market_pulse.json` showed stale/dead feed conditions
- There were no local decision logs available for `2026-03-25` in the workspace snapshot I checked

That means I can explain the structural miss, but not prove the exact live decision from a same-day decision record.

## What Needs To Change

### Primary request
Implement a path so fast `5m` wick sweeps can be acted on without waiting for a clean `15m` pattern that may never print.

### Concrete implementation direction
1. Add a `5m` micro-sweep detector.
2. Feed that detector into the existing wick / liquidity sweep lane logic as a promotion signal.
3. Allow a `5m` wick sweep to qualify when:
   - wick is large relative to candle range and ATR
   - reclaim happens immediately
   - reclaim closes back above the swept level for longs, or below for shorts
   - volume is at least adequate relative to recent `5m` bars
   - higher-timeframe context is not directly hostile
4. Do not blindly chase after the reclaim. Entry should still require:
   - reclaim confirmation
   - distance-to-entry cap
   - fail-fast invalidation
5. Preserve overnight safety, but do not let the overnight policy suppress high-quality `1` contract wick reclaim trades if account margin is actually safe.

## Specific Code Areas To Review
- `main.py`
  - where `df_15m` / `df_1h` signals are assembled
  - where `sweep_long`, `sweep_short`, `wick_rejection`, and `liquidity_sweep` are called
  - overnight trading lock / playbook handling
- `strategy/lane_scoring.py`
  - `detect_sweep(...)`
- `strategy/entries.py`
  - `wick_rejection(...)`
  - `liquidity_sweep(...)`
- `indicators/wick_score.py`
  - reusable wick quality scoring already exists and should probably be reused for a `5m` lane or pre-lane qualifier

## Suggested Fix Shape
- Keep `15m` / `1h` structure for macro bias.
- Add `5m` event detection for:
  - wick sweep
  - immediate reclaim
  - follow-through
- Promote a `5m` event into a valid entry candidate when it aligns with:
  - HTF support / sweep zone
  - non-hostile trend context
  - safe overnight margin state

In short:
- `5m` detects the event
- `15m` / `1h` validate the context
- entry fires on reclaim instead of after the move is over

## Tests Requested
- Add unit tests for a `5m` downside sweep + reclaim producing a long candidate.
- Add a negative test where the wick happens but reclaim fails.
- Add a test where the move exists on `5m` but collapses into a noisy `15m`; the new logic should still catch the valid reclaim if the `5m` signal is strong enough.
- Add a test proving overnight gating does not block the setup when margin is actually safe.
- Add a test proving overnight gating still blocks the setup when margin is unsafe.

## Important Constraints
- Do not turn this into blind scalping.
- We want to catch true liquidation-style wick reclaims, not every noisy `5m` tail.
- Keep size conservative for this class of trade. `1` contract default is fine unless quality is exceptional and margin is clearly safe.

## Bottom Line
The miss was likely a combination of:
- overnight entry lock
- `5m` event not visible to a `15m`-driven wick/sweep system
- stale analytics/news context

The system should be upgraded so a fast `5m` liquidation wick can be promoted into an actionable reclaim trade when higher-timeframe context is supportive and overnight margin is safe.
