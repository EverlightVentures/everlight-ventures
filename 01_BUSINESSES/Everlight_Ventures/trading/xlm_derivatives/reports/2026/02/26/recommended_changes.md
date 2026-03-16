# Recommended Config Changes -- Feb 26, 2026

All items below are PROPOSALS ONLY. No changes have been made to any config file.
All items labeled REQUIRES APPROVAL must be reviewed and manually applied by the account owner.

---

## Priority 1: Fix the Time Stop (REQUIRES APPROVAL)

**Problem:** time_stop_bars: 4 (1 hour) is not firing. Two trades held 462 and 905 minutes respectively. Both exited via exchange_side_close, not bot logic.

**Root cause to investigate first:** The time stop may be losing its bar counter when the bot restarts on Oracle Cloud. Each main.py invocation is a fresh 3-5s cycle. If the bot process is killed and restarted, the bar count resets. The entry_time in open_position survives (it is in state.json), but the elapsed-bar counter likely does not. The fix should use wall-clock time, not bar counts.

**Proposed change:**
- Add a `max_hold_minutes` field alongside `time_stop_bars`
- Bot should compute: `elapsed_minutes = (now - entry_time).total_minutes()`
- If `elapsed_minutes > max_hold_minutes`, force exit regardless of bar count
- Suggested value: 120 minutes (2 hours) as absolute wall-clock hard stop

```yaml
exits:
  time_stop_bars: 4          # keep as-is (bar-based soft stop)
  max_hold_minutes: 120      # ADD THIS: wall-clock hard stop, survives restarts
```

This is the single highest-priority fix. One -$64.90 trade erased 3 weeks of expected profit.

---

## Priority 2: Add a Dollar-Loss Circuit Breaker (REQUIRES APPROVAL)

**Problem:** No single-trade max loss limit is enforced in the current config.yaml. The setting referenced (single_trade_max_loss_usd: 30) does not exist in the deployed file.

**Proposed change:**

```yaml
circuit_breaker:
  single_trade_max_loss_usd: 25   # exit immediately if unrealized loss hits -$25
  max_hold_hours: 3               # absolute time limit in hours (wall clock)
  enforce: true
```

At 4x leverage with 5000 XLM, a $25 loss represents about a 3.1% adverse move on notional. That is roughly the level where the position is clearly wrong and the expected value of holding is negative.

Note: This requires code changes in main.py exit logic, not just config. The bot must check unrealized PnL on every cycle and compare against this limit.

---

## Priority 3: Re-enable EV Gate at a Reasonable Floor (REQUIRES APPROVAL)

**Problem:** min_ev_usd: -999 disables the EV gate entirely. Most entries in the log show ev_usd between -1.2 and -3.2. This means the bot is routinely taking trades where fees alone guarantee a loss unless the direction is perfect.

**Proposed change:**

```yaml
v4:
  ev:
    min_ev_usd: -1.50   # was -999; block trades where EV is worse than -$1.50
```

At round-trip fees of ~$1.45, an EV of -1.50 means a trade needs at least a coin-flip win rate AND positive gross PnL to pass. This would have blocked several of the marginal entries on Feb 24 that contributed to the loss cascade.

---

## Priority 4: Hard Cap on Overnight Exposure (REQUIRES APPROVAL)

**Problem:** The Feb 25 trade entered at 4:28 AM PT (overnight window, before 5 AM PT intraday start). The overnight margin is $432 per contract vs $207 intraday. The bot entered an overnight position, it went against, and the exit mechanisms failed -- leaving the position open through the entire next day.

**Proposed change:**

```yaml
margin_policy:
  overnight_trading:
    mode: never    # was: auto -- force off until time-stop bug is confirmed fixed
```

This is a temporary safety measure. Once the wall-clock time stop is verified working over at least 5 days without a runaway trade, this can be set back to auto.

---

## Priority 5: Reduce max_trades_per_day During Loss Debt Period (REQUIRES APPROVAL)

**Problem:** With $64.97 loss debt and recovery mode active, the bot is still allowed 8 trades per day. On Feb 24 this resulted in a cascade of losses as the bot tried to recover aggressively.

**Proposed change (temporary, review after 1 week):**

```yaml
risk:
  max_trades_per_day: 4   # was: 8 -- halve it until loss debt is cleared
  max_losses_per_day: 3   # was: 5 -- stop earlier on bad days
```

---

## Do NOT Change (Advisory Notes)

- Do not increase leverage. At 4x with $400-450 equity, one bad 8% move with no exit = account wipeout.
- Do not remove the reconcile drift guard. 11 drifts today suggests Oracle Cloud network latency or API instability that could cause worse problems without reconciliation.
- Do not change contract_size or capital_allocation_pct until time-stop reliability is confirmed.

---

DISCLAIMER: This content is for informational and educational purposes only and does not constitute financial, investment, or trading advice. Cryptocurrency and derivatives trading involves substantial risk of loss. Always do your own research (DYOR) and consult a qualified financial advisor before making any investment decisions.
