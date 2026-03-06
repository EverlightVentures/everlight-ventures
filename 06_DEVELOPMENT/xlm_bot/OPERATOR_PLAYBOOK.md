# XLM CDE Bot Operator Playbook

## 1) What this system is
- `main.py` is a rules-based futures trader for Coinbase CDE contracts.
- It makes one decision cycle every loop, writes all reasoning to logs, and updates the dashboard snapshot feed.
- It has two strategy regimes:
  - `trend`: breakout/continuation behavior
  - `mean_reversion`: rejection/reversion behavior

## 2) Core files
- Bot logic: `main.py`
- Config (base): `config.yaml`
- Trend profile: `config_trend.yaml`
- Mean reversion profile: `config_mr.yaml`
- Dashboard: `dashboard.py`
- Exchange reconciliation: `risk/reconcile.py`

## 3) Start commands
- Single bot (base config): `bash ./xpb`
- Trend-only bot: `bash ./xpb-trend`
- MR-only bot: `bash ./xpb-mr`
- Base dashboard: `bash ./xdr`
- Trend dashboard (default `8502`): `bash ./xdr-trend`
- MR dashboard (default `8503`): `bash ./xdr-mr`
- Optional history tuning:
  - `XLM_DASH_HISTORY_DAYS` (minimum enforced: 7)
  - `XLM_DASH_HISTORY_MAX_LINES` (default 120000)
  - `XLM_DASH_HISTORY_MAX_MB` (default 24)

## 4) Two-bot capital split
- Base now supports per-bot capital cap with `risk.capital_allocation_pct`.
- Trend profile: `0.125`
- MR profile: `0.125`
- This enforces a maximum initial position size per bot based on required margin per contract.

## 5) Decision order (what the bot is "thinking")
1. Load candles and compute indicators.
2. Reconcile exchange truth vs local state.
3. If open position exists, manage exits/rescue/scale first.
4. If flat, evaluate entries:
   - regime gates (ATR/session/spread/value-distance),
   - v4 confluence score thresholds,
   - EV filter (`expected_value_v4`),
   - margin/risk/cooldown checks,
   - idempotency (duplicate suppression),
   - place order with exchange-native stop and TP1 attachment.

## 6) Exit logic summary
- Can exit on:
  - `profit_lock`
  - `trend_flip`
  - `reversal_signal`
  - `tp1` (plus ATR dynamic TP logic)
  - `time_stop`
  - `early_save`
  - `cutoff_derisk`
  - emergency margin exits
- Reverse re-entry is enabled on `reversal_signal` and `trend_flip` if opposite signal is valid.

## 7) EV formula used
- `EV = P(win)*E(win) - (1-P(win))*E(loss) - fees - slippage - funding`
- `P(win) = clamp(0.30 + 0.004*score, 0.40, 0.65)`
- Trend: `E(win)=1.8*ATR`, `E(loss)=1.0*ATR`
- MR: `E(win)=1.15*ATR`, `E(loss)=1.5*ATR`
- Configurable fee model: `conservative | balanced | maker_bias`

## 8) What to watch live
- `logs/decisions.jsonl` (or profile logs dir): every decision and block reason.
- `logs/trades.csv`: realized trades.
- `logs/incidents.jsonl`: reconciliation and risk incidents.
- `logs/margin_policy.jsonl`: margin tier/actions each cycle.
- `logs/plrl3.jsonl`: rescue ladder status/actions.
- `logs/fills.jsonl`: order/fill audit trail.
- Dashboard now highlights **Major Events** (entry/exit/take-profit/liquidation-risk/reconcile incidents) separately from noisy signal chatter.

## 9) If no trade is placed, check these reasons
- `entry_blocked_preflight`
- `entry_blocked_max_daily_loss`
- `entry_blocked_max_trades`
- `entry_blocked_max_losses`
- `entry_blocked_no_signal`
- `entry_blocked_regime_mode`
- `entry_blocked_allocation`
- `v4_score_block_entry`
- `ev_block_entry`
- `margin_policy_block_entry`

## 10) Expected behavior and limits
- It is intentionally selective; some cycles will do nothing.
- Tight safety can reduce trade frequency but lowers catastrophic risk.
- One or a few trades are not enough to judge edge; evaluate on a larger sample window.

## 11) Codex + Opus team mode
- Architecture:
  Opus remains the trade authority. Codex runs as a parallel peer advisor only.
- Enable in `config.yaml`:
  Set `ai.codex.enabled: true` after confirming `codex` CLI is logged in.
- Safety:
  `ai.codex.sandbox_mode` defaults to `read-only`, so Codex analysis cannot modify files.
- What gets logged:
  `codex_entry_eval`, `codex_exit_eval`, `codex_regime_eval`, and `codex_directive` are cached in `data/ai_insight.json`.
- Decision visibility:
  `main.py` now includes Codex fields in decision payloads, while execution still follows `ai_directive` (Opus).

## 12) Gemini + Opus + Codex team mode
- Architecture:
  Opus remains the Executive (trade authority). Codex and Gemini run as parallel peer advisors.
- Role:
  Gemini provides long-context analysis and a "second opinion" to counter Claude's potential tunnel vision.
- Enable in `config.yaml`:
  Set `ai.gemini.enabled: true`. Defaults to `gemini-1.5-pro-latest`.
- What gets logged:
  `gemini_entry_eval`, `gemini_exit_advice`, `gemini_regime`, and `gemini_directive` are cached in `data/ai_insight.json`.
- Decision visibility:
  `main.py` includes Gemini fields in decision payloads. Currently advisory-only.
