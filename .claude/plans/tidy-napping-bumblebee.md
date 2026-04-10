# XLM Bot: Structure-First Strategy Upgrade

## Context

Bot has 51 trades, -$172 total ($100 bad trades + $72 fees). Biggest win ~$8. Three root problems: exits kill winners too early, Lane V wick plays never fire, pattern scoring is decorative. Capital ~$627, 1 contract max, realistic target $25-50/day.

The Gemini research recommends 12 intelligence layers. The bot already has 10 of 12 built -- they need tuning/activation, not rebuilding.

### Already exists (tune, don't rebuild):
- Regime engine (expansion.py, regime_state_machine.py) -- COMPRESSION/IGNITION/EXPANSION/PANIC
- BTC-as-boss filter (market/btc_correlation.py) -- btc_trend, btc_score_mod
- Derivatives layer (contract_context.py, liquidation_clusters.py) -- funding, OI, basis, liquidation heatmap
- Macro event filter (market/news_intel.py) -- event calendar, risk blocking
- Volatility throttle (expansion.py) -- regime-based sizing via lane_budgets
- Session engine (session_filter, margin_policy.py) -- session windows, margin hours
- Structure map (v4_engine.py) -- HTF levels, fibs, VWAP, swing H/L
- Execution intelligence (spread gate in regime.py, slippage in v4_engine)

### Missing (build later):
- Relative strength XLM/BTC ratio tracking
- Post-trade regime tagging in trade_reviewer

### Broken/misconfigured (fix now):
- SAFE_MODE bug: `pnl <= -0` triggers on any losing day (line 1510)
- Lane V filters too strict (4-of-6 signals, balanced cluster skip, high wick minimums)
- Exits too tight (3hr time stop, 1.5% early save)
- Pattern scoring too weak (+/-5 pts on 75pt thresholds)
- EV gate too low ($1 min, doesn't cover fees)

---

## Implementation (5 files)

### 1. config.yaml -- Main Tuning

**Exits (let winners run):**

| Setting | Current | New | Why |
|---------|---------|-----|-----|
| time_stop_bars | 12 (3hr) | 24 (6hr) | Winners need time |
| early_save_adverse_pct | 0.015 | 0.025 | XLM swings 2% routinely |
| breakeven_atr_trigger | 2.0 | 1.5 | Arm break-even earlier |
| time_stop_bars_trend | 24 | 36 | 9hr for trend rides |

**Lane V (activate wick plays):**

| Setting | Current | New | Why |
|---------|---------|-----|-----|
| lane_v_skip_balanced_clusters | true | false | Primary reason Lane V returns None |
| lane_v_min_cluster_strength | 30 | 15 | Let moderate setups through |
| lane_v_wick_min_ratio | 0.35 | 0.25 | Catch moderate wicks |
| lane_v_wick_score_min | 55 | 40 | Lower bar, 40 still decent quality |
| lane_v_min_signals | 4 | 3 | 3-of-6 core signals |

**Patterns (make them matter):**

| Setting | Current | New | Why |
|---------|---------|-----|-----|
| bonus_pts | 5 | 12 | 16% of threshold vs 7% |
| penalty_pts | 3 | 8 | Contradictions = real warning |
| level_bonus_pts | new | 8 | Pattern at structure = +20 total |
| level_penalty_extra | new | 5 | Contradiction at level = -13 |

**Fee/EV gate:**

| Setting | Current | New | Why |
|---------|---------|-----|-----|
| min_ev_usd | 1.00 | 2.00 | Must clear $2 after fees |

**Daily target:**

| Setting | Current | New | Why |
|---------|---------|-----|-----|
| daily_profit_target_usd | 5000 | 0 | Disable SAFE_MODE trigger |

### 2. main.py -- SAFE_MODE Kill + Pattern Integration

**Bug fix (line ~1510):** `realized_pnl <= -max_dd` when max_dd=0 is always true.
```python
if max_dd > 0 and realized_pnl <= -max_dd:
```
Same fix at line ~1539.

**Force-clear (near line ~3405):**
```python
state.pop("_safe_mode", None)
state.pop("safe_mode", None)
```

**Remove line ~8188:** `state["_safe_mode"] = True` on daily target hit.

**Pattern integration (line ~7106):** Pass HTF_LEVEL and FIB_ZONE flags into candle pattern detection.

### 3. indicators/candle_patterns.py -- Location-Aware Scoring

Add optional `at_structure_level` and `at_fib_zone` params (backward-compatible).

- Pattern confirms at key level: +8 extra (20 total with base 12)
- Pattern contradicts at level: -5 extra (13 total)
- Doji: never positive modifier, alert only

Research rule enforced: structure > trend > location > pattern > raw candle.

### 4. strategy/entries.py -- Lane V Gate Loosening

**Reversal entry (line ~2676):** Three paths instead of one:
- Strong wick + reclaim/reject (current)
- Very strong wick alone (score >= 70)
- Reclaim/reject + moderate wick (ratio >= 0.20)

**Balanced cluster (line ~2642):** Allow when wick score >= 70.

### 5. strategy/v4_engine.py -- Structure-First Weights

MR weights rebalance:

| Flag | Current | New |
|------|---------|-----|
| HTF_LEVEL | 20 | 25 |
| FIB_ZONE | 15 | 20 |
| RSI_EXTREME | 15 | 12 |
| MACD_DIVERGENCE | 15 | 12 |

### 6. State Reset on Deploy

Clear safe_mode, recovery_mode, cooldowns, consecutive_losses.

---

## Existing Systems Status (Gemini 12 Layers)

| Layer | Implementation | Active? | Action |
|---|---|---|---|
| Regime engine | expansion.py, regime_state_machine.py | Yes | Verify config enabled |
| BTC-as-boss | btc_correlation.py | Yes | Verify data flowing |
| Derivatives | contract_context.py, liquidation_clusters.py | Yes | Lane V tuning activates this |
| Macro calendar | news_intel.py | Yes | Already blocking around events |
| Vol throttle | expansion.py regime_size_mult | Yes | COMPRESSION=0.7x already |
| Session engine | session_filter, margin_policy.py | Yes | Margin windows active |
| Structure map | v4_engine.py | Yes | Upweighting HTF_LEVEL/FIB |
| Execution | spread gate, slippage calc | Yes | Already filtering wide spreads |
| Pattern detection | candle_patterns.py, pattern_engine.py | Yes | Upgrading scoring weight |
| Lane V wicks | wick_score.py, entries.py | Built but dormant | Loosening filters |
| Relative strength | Partial (btc_correlation) | Partial | Future: add XLM/BTC ratio |
| Post-trade regime | trade_reviewer.py | Shadow tracking live | Future: tag regime on exits |

---

## Verification

1. py_compile all 5 files
2. SCP to Oracle, clear state, verify on Oracle
3. Monitor first 10 decisions:
   - lane_v_mode showing non-None
   - candle_pattern_mod > 5 at key levels
   - Time stop not firing at 3hr
   - No SAFE_MODE in state
   - EV gate blocking sub-$2 trades
4. After 5 trades: `python3 trade_reviewer.py summary`
5. After 24hr: compare win rate vs prior 49-trade history
