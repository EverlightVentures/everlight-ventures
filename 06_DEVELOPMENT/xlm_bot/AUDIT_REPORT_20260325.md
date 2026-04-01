# XLM Bot Full Configuration Audit -- 2026-03-25

**Context**: Bot sat flat during an 11% XLM breakout ($0.156 -> $0.177) on 2026-03-25.
Multiple kill-switches and over-conservative gates blocked all entries.

**Already fixed today** (not re-listed):
1. `compression_gate: false` (was true)
2. `regime_mode: adaptive` (was mr_only)
3. `overnight_trading_ok: yes` (was no)
4. `rolling_expectancy: enabled: false` (was true)

---

## ISSUE 1: AI Advisor Hardcoded Compression Block (STILL ACTIVE)

**Severity: CRITICAL**

`claude_advisor.py` line 449 has a HARDCODED compression block that is **independent of config.yaml**:

```python
if vol_state == "COMPRESSION" and not is_compression_range:
    flat_result = {
        "action": "FLAT",
        "verdict": "skip",
        "confidence": 0.95,
        "score_adjustment": -20,
        "reasoning": "COMPRESSION regime -- blocking entry...",
    }
```

Even with `compression_gate: false` in config.yaml, the AI advisor **still blocks every non-compression-range entry during COMPRESSION**. This is a second compression gate that was NOT fixed today.

With `executive_mode: true`, this AI FLAT directive can override the strategy engine.

**Fix**: Edit `ai/claude_advisor.py` line 446-460. Either:
- Remove the hardcoded block entirely, OR
- Gate it behind `config.get("regime", {}).get("compression_gate", False)`

```yaml
# No config change needed -- fix is in Python code
# File: ai/claude_advisor.py, lines 446-460
```

---

## ISSUE 2: Config Still Shows `compression_gate: true` and `regime_mode: mr_only`

**Severity: CRITICAL (if live config not updated)**

The config snapshot at line 243 still reads:
```yaml
regime:
  compression_gate: true       # Line 243
```
And at line 376:
```yaml
v4:
  regime_mode: mr_only         # Line 376
```
And `rolling_expectancy` at line 1301:
```yaml
rolling_expectancy:
  enabled: true                # Line 1301
```

User says these are fixed on live -- **verify the live Oracle config matches**. If the deploy script hasn't pushed, these are still active.

**Fix**: Confirm live config on Oracle at `/home/opc/xlm-bot/config.yaml`

---

## ISSUE 3: EXHAUSTION Phase Still Blocked

**Severity: HIGH**

Config lines 247-249:
```yaml
regime:
  blocked_phases:
    - COMPRESSION
    - EXHAUSTION
```

EXHAUSTION is the phase AFTER a breakout move when volume starts to fade but the trend is still intact. This is exactly when mean-reversion setups appear (the bread and butter). Blocking EXHAUSTION means:
- After a breakout run, the bot cannot enter the pullback trade
- It misses the best risk/reward MR setups (retracement after expansion)

Note: The `blocked_phases` key is NOT directly consumed by Python code in the strategy engine -- it appears to be read only by the AI advisor via the config context. But with `executive_mode: true`, the AI uses this as a reason to block trades.

Additionally, `regime_manager.py` line 62 treats EXHAUSTION as compression:
```python
is_compression_phase = vol_phase.upper() in ("COMPRESSION", "EXHAUSTION")
```

This means EXHAUSTION gets compression-level sizing (potentially reduced), compression-level TP targets, and compression treatment -- even though exhaustion follows expansion and often has more directional opportunity.

**Fix**:
```yaml
# config.yaml line 247-249
blocked_phases:
  # Remove EXHAUSTION, keep empty or remove section entirely
  []
```
Also fix `strategy/regime_manager.py` line 62:
```python
# Change from:
is_compression_phase = vol_phase.upper() in ("COMPRESSION", "EXHAUSTION")
# To:
is_compression_phase = vol_phase.upper() == "COMPRESSION"
```

---

## ISSUE 4: max_trades_per_day=2 and max_losses_per_day=1 -- Ultra-Restrictive

**Severity: HIGH**

Config lines 33-34:
```yaml
risk:
  max_trades_per_day: 2
  max_losses_per_day: 1
```

The bot cycles every ~30 seconds (2,880 cycles/day). It can only fire 2 trades. One loss and it's done for the entire day. During today's 11% breakout, if the bot had taken a losing trade earlier, it would have been locked out of the biggest move of the month.

Combined with:
- `cooldown_minutes: 60` (line 35) -- 1 hour between trades
- `revenge_cooldown_minutes: 120` (line 37) -- 2 hours after a loss

Timeline: If Trade 1 fires at 9 AM and loses, the bot cannot trade again until 11 AM (revenge cooldown), and then has only 1 trade left for the rest of the day.

**Fix**:
```yaml
risk:
  max_trades_per_day: 5         # was 2 -- allow more shots
  max_losses_per_day: 2         # was 1 -- one loss shouldn't end the day
  cooldown_minutes: 20          # was 60 -- 20 min is enough to avoid chasing
  revenge_cooldown_minutes: 45  # was 120 -- 45 min, not 2 hours
```

---

## ISSUE 5: Circuit Breaker Trips at 1 Loss

**Severity: HIGH**

Config lines 660-666:
```yaml
circuit_breaker:
  combo_loss_count: 1           # trips at 1 loss + drawdown
  combo_drawdown_pct: 0.04      # 4% of equity (~$18)
  single_trade_max_loss_usd: 5  # $5 max loss per trade
  single_trade_max_loss_pct: 0.01  # 1% max loss per trade
```

Escalation matrix (lines 672-678):
```yaml
tier1_soft_halt:
  trigger_losses: 1             # 1 loss = soft halt
  trigger_drawdown_usd: 5.0     # $5 drawdown = soft halt
  recover_after_minutes: 120    # 2 hours to recover from soft halt
```

A single $5 loss triggers: max_losses_per_day block + circuit breaker combo + tier1 soft halt + 2-hour cooldown. The bot is effectively dead for most of the day after one normal loss.

**Fix**:
```yaml
circuit_breaker:
  combo_loss_count: 2           # was 1 -- need 2 losses + drawdown to trip
  single_trade_max_loss_usd: 8  # was 5 -- slightly more room
  single_trade_max_loss_pct: 0.02  # was 0.01 -- 2% is reasonable

# Escalation
tier1_soft_halt:
  trigger_losses: 2             # was 1 -- 2 losses before soft halt
  trigger_drawdown_usd: 10.0    # was 5 -- $10 before halt
  recover_after_minutes: 45     # was 120 -- 45 min recovery
```

---

## ISSUE 6: Quality Tier Gaps Make REDUCED/SCALP Nearly Impossible

**Severity: HIGH**

Config lines 380-381:
```yaml
quality_tiers:
  reduced_gap: 3               # score must be within 3 of threshold
  scalp_gap: 8                 # score must be within 8 of threshold
  monster_above: 25            # score must be 25+ above threshold
```

With lane thresholds raised to 55-70 range (SNIPER MODE), a signal scoring 52 against a 55 threshold = gap of 3 = REDUCED. Score of 47 = gap 8 = SCALP boundary. Score of 46 = NO_TRADE.

The `reduced_gap: 3` is absurdly tight. Most legitimate signals will score within 5-10 points of threshold during transitions. Combined with `regime_mode: mr_only` (now adaptive), many signals that would have been FULL tier in mean_reversion regime get blocked when regime shifts to neutral.

**Fix**:
```yaml
quality_tiers:
  reduced_gap: 8               # was 3 -- allow scores within 8 of threshold
  scalp_gap: 15                # was 8 -- allow scores within 15 of threshold
  monster_above: 20            # was 25 -- more trades qualify as MONSTER
```

---

## ISSUE 7: TP Targets Are Unrealistically Wide for Compression/Scalp Scenarios

**Severity: HIGH**

Config lines 219-221:
```yaml
exits:
  tp1_move: 0.40               # 0.40% move
  tp2_move: 0.70               # 0.70% move
  tp3_move: 1.20               # 1.20% move
```

At XLM $0.165 with 1 contract ($3,140 notional per contract):
- TP1 = 0.40% = $0.00066 move = $12.56 profit
- TP2 = 0.70% = $0.00116 move = $21.98 profit
- TP3 = 1.20% = $0.00198 move = $37.68 profit

These look reasonable for swing trades. BUT the compression override (lines 224-228) applies multipliers:
```yaml
compression_override:
  tp1_mult: 0.15          # 0.40 * 0.15 = 0.06% = $1.88
  tp2_mult: 0.30          # 0.70 * 0.30 = 0.21% = $6.59
  tp3_mult: 0.50          # 1.20 * 0.50 = 0.60% = $18.84
```

Then the regime TP scaling at line 9670-9671:
```python
if _vol_regime == "compression":
    _vol_tp_mult = 0.60   # multiply TP by 0.60
```

Combined: compression TP1 = 0.40 * 0.15 * 0.60 = **0.036% = $1.13**. After fees (~$2.90 round trip), this is a net LOSS even on a winning trade.

Additionally, `min_tp_pct: 0.005` (line 232) should floor this at 0.5%, but the compression override `tp1_mult: 0.15` is applied as a separate channel (exit profiles), not always caught by the floor.

**Fix**:
```yaml
# config.yaml exits section
compression_override:
  tp1_mult: 0.50          # was 0.15 -- 0.40 * 0.50 = 0.20% = $6.28
  tp2_mult: 0.65          # was 0.30 -- decent mid target
  tp3_mult: 0.80          # was 0.50 -- reasonable full target
```
And remove the double-scaling in `main.py` line 9670-9671, or set `_vol_tp_mult = 1.0` for compression since the override already handles it.

---

## ISSUE 8: Sniper Mode Config Section is Dead Code

**Severity: MEDIUM**

Config lines 1362-1392 (`sniper_mode:` section) with entry_filters (RSI < 25, RSI > 75, BB squeeze percentile 20, range proximity 0.5%) is **never read by any Python code**. Grep across the entire codebase returns zero hits for `sniper_mode`, `rsi_oversold_max`, `rsi_overbought_min`, or `bb_squeeze_percentile`.

This means the "SNIPER MODE" strategy is implemented only through scattered config changes (raised thresholds, widened TPs, etc.) but NOT through the explicit entry filters documented in the config. The RSI 25/75 filter that was supposed to restrict entries to extreme levels is NOT enforced.

This is a double-edged sword: the filters aren't blocking anything (good -- they would have blocked the breakout), but they're also not providing the selectivity the strategy describes.

**Action**: Either implement the `sniper_mode.entry_filters` in the strategy engine, or remove the dead config section to avoid confusion.

---

## ISSUE 9: Three AI Advisors Running in Parallel (Latency + Conflict)

**Severity: MEDIUM**

Config lines 1120-1171:
```yaml
ai:
  enabled: true
  executive_mode: true
  codex:
    enabled: true
    executive_mode: true
  gemini:
    enabled: true
    executive_mode: true
```

Plus Perplexity (line 1181) and agent_comms with challenge rounds (line 1173).

Three AI advisors all producing executive directives, all with `executive_mode: true`. The `agent_comms.challenge_round: true` adds a 30-second debate timeout (line 1178). On a 30-second bot cycle, this means:
- AI debate can consume the entire cycle
- Conflicting ENTER/FLAT/EXIT directives from Claude/Codex/Gemini
- Claude's hardcoded compression block (Issue 1) can override even when Gemini says ENTER

**Fix**:
```yaml
ai:
  executive_mode: true          # Claude stays boss
  codex:
    executive_mode: false       # advisory only, no override
  gemini:
    executive_mode: false       # advisory only, no override
  agent_comms:
    max_debate_time_sec: 10     # was 30 -- faster debate
```

---

## ISSUE 10: Regime Manager Treats EXHAUSTION Like COMPRESSION

**Severity: MEDIUM**

`strategy/regime_manager.py` line 62:
```python
is_compression_phase = vol_phase.upper() in ("COMPRESSION", "EXHAUSTION")
```

EXHAUSTION follows EXPANSION. It's the wind-down of a trend, not a range-bound chop. Treating it as compression means:
- Size multiplier drops to compression level (1.0x, but could be lower via other multipliers)
- TP targets get compression scaling (0.60x from line 9671)
- Missed MR opportunities at the end of a move

Combined with Issue 3 (blocked_phases includes EXHAUSTION), the bot completely ignores the exhaustion phase.

**Fix**: See Issue 3 fix for `regime_manager.py`.

---

## ISSUE 11: min_rr_ratio Set Too High Across All Tiers

**Severity: MEDIUM**

Config lines 48-52:
```yaml
min_rr_ratio:
  MONSTER: 2.5
  SCALP: 3.5
  REDUCED: 3.0
  FULL: 3.0
  default: 3.0
```

3:1 R:R minimum means the bot needs a TP target 3x the stop distance. With `max_risk_pct_per_trade: 0.05` (5%) and typical ATR-based stops, many legitimate setups fail the R:R check because the TP target would need to be unrealistically wide.

For a $459 account:
- 5% risk = $22.95 max risk per trade
- 3:1 R:R = need $68.85 target
- At $0.165 XLM with 1 contract ($3,140): need a 2.2% move for TP
- Average XLM daily range is ~3-4%, so a 2.2% TP is reachable but not for every setup

SCALP at 3.5:1 is especially punishing -- scalps by definition target small moves.

**Fix**:
```yaml
min_rr_ratio:
  MONSTER: 2.0               # was 2.5
  SCALP: 2.0                 # was 3.5 -- scalps need lower bar
  REDUCED: 2.5               # was 3.0
  FULL: 2.5                  # was 3.0
  default: 2.5               # was 3.0
```

---

## ISSUE 12: Position Sizing Walkthrough at $459 Equity

**Severity: INFO (documenting actual behavior)**

At $459 equity, here's the sizing math:

1. **Growth ladder**: BUILD_A (max_equity 750), so:
   - `max_contracts: 1`
   - `base_risk_pct: 0.025` (2.5%)
   - `per_trade_risk_usd: $10`

2. **Account tier**: $459 < $500, so `risk_mult: 1.3` (aggressive)

3. **Position sizing math**:
   - Base risk: $459 * 0.025 = $11.48
   - Account tier mult: $11.48 * 1.3 = $14.92
   - Lane budget (e.g., Lane G = 0.6): $14.92 * 0.6 = $8.95
   - Quality tier mult (FULL = 1.25): $8.95 * 1.25 = $11.19
   - Streak (0 streak = 1.0x): $11.19

4. **But max_contracts_hard_cap = 2** and growth_ladder BUILD_A says max_contracts = 1
   - So always 1 contract

5. **Margin check**: At $0.165 XLM, 1 contract = $3,140 notional
   - Intraday margin ~10% = $314 required
   - $459 equity covers this with ~31% buffer
   - Overnight margin ~14% = $440 required
   - $459 / $440 = 1.04x -- below the 1.20x `min_equity_ratio` for overnight trading

6. **Compression override**: `max_contracts: 1`, `size_multiplier: 0.5`
   - During compression: size cut in half
   - Risk becomes: $11.19 * 0.5 = $5.60

**Key finding**: The bot can only trade 1 contract. Overnight trading is borderline blocked (equity ratio 1.04 < required 1.20). In compression, risk is cut to ~$5.60 per trade.

---

## ISSUE 13: Overnight Trading Blocked by Equity Ratio

**Severity: HIGH**

Config line 318:
```yaml
overnight_trading:
  min_equity_ratio: 1.20       # need equity >= 1.2x overnight margin
```

At $459 equity and ~$440 overnight margin for 1 contract:
- Ratio = $459 / $440 = 1.04x
- Required: 1.20x = $528

Today's breakout started and continued through overnight hours (1 PM PT onward = overnight margin). The bot would be blocked from entering even with all other fixes applied.

**Fix**:
```yaml
overnight_trading:
  min_equity_ratio: 1.05       # was 1.20 -- just need to cover margin + small buffer
```

---

## ISSUE 14: Pre-Cutoff Block Prevents Intraday Entries

**Severity: MEDIUM**

Config lines 340-344:
```yaml
pre_cutoff:
  block_new_entries: true
  force_exit_before_cutoff: true
```

Pre-cutoff starts 15 minutes before 1 PM PT (12:45 PM PT). Combined with `force_exit_before_cutoff: true`, the bot exits any position AND blocks new entries during the last 15 minutes of intraday session.

If a breakout starts at 12:30 PM PT, the bot has only 15 minutes before it's forced to exit. This is appropriate for risk management but contributes to missed moves.

**Fix**: Consider reducing `pre_cutoff_minutes` from 15 to 5:
```yaml
pre_cutoff_minutes: 5          # was 15
```

---

## ISSUE 15: Friday Break Locks Out Trading for 1+ Hour

**Severity: LOW**

Config lines 320-329:
```yaml
friday_break:
  enabled: true
  pre_break_new_entry_lock_minutes: 60
  force_flat_minutes_before_break: 20
```

Every Friday, the bot locks out new entries for 60 minutes before the break and force-flattens 20 minutes before. This is a 1-hour trading blackout every Friday.

**Action**: Acceptable for risk management. No change recommended unless Friday moves are being missed.

---

## ISSUE 16: Lane Threshold Inflation (SNIPER MODE)

**Severity: MEDIUM**

All lane thresholds were raised 10-15 points for "SNIPER MODE":
- Lane A: 65 (was 55)
- Lane B: 60 (was 50)
- Lane M: 65 (was 55)
- Lane T: 70 (was 65)

With quality tier `reduced_gap: 3` (Issue 6), a signal needs to score within 3 points of these inflated thresholds to even qualify as REDUCED. The combination creates an effective minimum score of 57-67 depending on lane, which most signals won't reach during transitions or low-vol periods.

**Fix**: Roll back thresholds 5-10 points closer to originals:
```yaml
lane_scoring:
  lane_a_threshold: 58         # was 65
  lane_b_threshold: 55         # was 60
  lane_c_threshold: 50         # was 55
  lane_e_threshold: 55         # was 60
  lane_g_threshold: 48         # was 55
  lane_m_threshold: 58         # was 65
  lane_n_threshold: 55         # was 60
  lane_t_threshold: 62         # was 70
```

---

## ISSUE 17: Freshness Gate Can Block During Data Lag

**Severity: MEDIUM**

Config lines 1323-1330:
```yaml
freshness_gates:
  enabled: true
  max_live_tick_age_sec: 60
  block_on_dead_tick: true
  block_on_stale_market_brief: true
  block_on_pulse_danger: true
```

If the WebSocket feed drops for >60 seconds, the freshness gate blocks ALL entries. Combined with `market_pulse.danger_block_entries: true` (line 1318), a temporary data issue can prevent the bot from trading during a real breakout.

**Fix**: Increase tick staleness tolerance:
```yaml
freshness_gates:
  max_live_tick_age_sec: 120    # was 60 -- WS reconnects can take 30-60s
```

---

## ISSUE 18: Sentiment Gate Can Block Longs in Fear

**Severity: LOW**

Config lines 1101-1103:
```yaml
sentiment_gate:
  block_longs_below: 20        # extreme fear = no longs
  reduce_size_below: 30        # fear = half size
```

During the March crypto pullback, Fear & Greed was in the 20s. This would block long entries or halve their size exactly when buy-the-dip setups are strongest.

**Action**: Consider lowering `block_longs_below` to 10 (same as `block_all_below`).

---

## ISSUE 19: EV Minimum of $3 May Be Too High

**Severity: MEDIUM**

Config line 600:
```yaml
ev:
  min_ev_usd: 3.00             # require $3+ expected value after fees
```

With 1 contract at $0.165 XLM:
- Fees round trip: ~$2.90 (maker $2.67 + taker $2.83 avg)
- To get $3 EV: need raw expected gain of ~$5.90
- At 50% win rate: need avg win of $11.80
- At $3,140 notional: need 0.38% avg winning move

This is achievable but filters out many legitimate small-edge setups.

**Fix**:
```yaml
ev:
  min_ev_usd: 2.00             # was 3.00 -- $2 EV after fees is still profitable
```

---

## ISSUE 20: Contradictions Summary

**Severity: VARIES**

| Contradiction | Severity |
|---|---|
| `compression_gate: false` (config) vs hardcoded FLAT in `claude_advisor.py` | CRITICAL |
| `regime_mode: adaptive` but AI advisor ignores regime_mode and uses its own compression check | CRITICAL |
| `blocked_phases: [EXHAUSTION]` but `regime_manager.py` also treats EXHAUSTION as compression | HIGH |
| `max_risk_pct_per_trade: 0.05` (5%) but `single_trade_max_loss_pct: 0.01` (1%) -- the 1% cap overrides the 5% | MEDIUM |
| `max_contracts_hard_cap: 2` but growth_ladder BUILD_A says `max_contracts: 1` -- BUILD_A wins | LOW (correct) |
| `compression_override.size_multiplier: 0.5` AND `regime_manager.compression.size_multiplier: 1.0` -- double application possible | MEDIUM |
| `min_tp_pct: 0.005` floor vs compression TP overrides that go below 0.005 -- floor may not catch all paths | MEDIUM |

---

## GATE CASCADE ANALYSIS: Signal -> Order Path

A signal must pass through ALL of these gates (in order) before an order is placed:

1. **Vol Phase Gate** -- expansion.py determines COMPRESSION/IGNITION/EXPANSION/EXHAUSTION
2. **AI Advisor Compression Block** -- hardcoded FLAT if COMPRESSION (Issue 1)
3. **Regime Mode Gate** -- mr_only/trend_only/adaptive filters regime classification
4. **Lane Scoring** -- signal must exceed lane-specific threshold (55-70 range)
5. **Quality Tier** -- score must be within `reduced_gap` (3 points!) of threshold
6. **Regime Gates** -- ATR regime, distance from value, spread, session
7. **Route Tier** -- full/reduced/blocked based on gate failures
8. **Dip Retrace Gate** -- blocks shorts during bounces
9. **Support Proximity Gate** -- blocks shorts near support
10. **Short Confirmation Gate** -- extra confirmation for reversal shorts
11. **Pattern Gates** -- block entries fighting chart patterns
12. **Preflight Block** -- gate_blocked OR cooldown OR product unavailable OR fail_safe
13. **Max Trades Per Day** -- hard cap at 2
14. **Max Losses Per Day** -- hard cap at 1
15. **Daily Profit Target** -- blocks if already hit
16. **Revenge Cooldown** -- 120 minutes after any loss
17. **Rolling Expectancy Gate** -- blocks if win rate < 25% (disabled)
18. **Sentiment Gate** -- blocks in extreme fear
19. **Circuit Breaker** -- trips at 1 loss + 4% drawdown
20. **Margin Policy** -- checks margin ratio < 85%
21. **Overnight Trading** -- checks equity ratio >= 1.20x
22. **Playbook** -- pre-cutoff blocks new entries
23. **EV Gate** -- expected value must be >= $3.00
24. **R:R Gate** -- risk/reward must be >= 3.0:1
25. **Score Gate** -- v4 score must pass lane threshold
26. **AI Executive Decision** -- Claude can override ENTER to FLAT
27. **Entry Preflight** -- bracket geometry, spread, margin check
28. **Freshness Gate** -- live tick must be < 60 seconds old
29. **Market Pulse** -- danger regime blocks entries

**That is 29 gates.** A signal has to pass EVERY SINGLE ONE. The probability of a legitimate signal passing all 29 gates simultaneously is very low, which is why the bot almost never trades.

---

## PRIORITY FIXES (Ordered by Impact)

### Immediate (Do Now)
1. **Fix claude_advisor.py compression block** (Issue 1) -- CRITICAL
2. **Verify live config has the 4 fixes applied** (Issue 2) -- CRITICAL
3. **Lower overnight equity ratio to 1.05** (Issue 13) -- HIGH
4. **Remove EXHAUSTION from blocked_phases** (Issue 3) -- HIGH
5. **Fix regime_manager.py EXHAUSTION treatment** (Issue 10) -- MEDIUM

### Today
6. **Raise max_trades_per_day to 5, max_losses to 2** (Issue 4) -- HIGH
7. **Raise circuit breaker combo_loss_count to 2** (Issue 5) -- HIGH
8. **Widen quality tier gaps** (Issue 6) -- HIGH
9. **Fix compression TP double-scaling** (Issue 7) -- HIGH

### This Week
10. **Lower min_rr_ratio across tiers** (Issue 11) -- MEDIUM
11. **Roll back lane thresholds 5-10 points** (Issue 16) -- MEDIUM
12. **Disable executive_mode on Codex/Gemini** (Issue 9) -- MEDIUM
13. **Lower EV minimum to $2** (Issue 19) -- MEDIUM
14. **Increase freshness tick tolerance** (Issue 17) -- MEDIUM

---

*Report generated 2026-03-25 by Lucrex audit system*
*Config snapshot from live Oracle + local dev codebase analysis*
