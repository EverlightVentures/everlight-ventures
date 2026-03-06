# XLM Bot Daily Report -- Feb 26, 2026

**Generated:** 2026-02-26 (11:44 AM PT)
**Account equity at session start:** $138.32 (derivatives) + ~$274 USDC spot = ~$412 total
**Current state:** IN_TRADE (long pullback, entry 0.16102, entered 11:42 AM PT)

---

## Period Summary: Feb 17-26

| Date | Net PnL | Notable Event |
|------|---------|---------------|
| Feb 17 | -$4 | Early bugs: phantom exit loop, emergency exits firing repeatedly |
| Feb 18 | +$31 | Profitable short run, 522-min hold +$10.45 (lucky, not controlled) |
| Feb 19 | -$1 | Lots of churn, tiny wins, 90-min hold -$6.56 time-stop |
| Feb 22-23 | +$2 | Recovered modestly, phantom trade loop incident on Feb 23 |
| Feb 24 | -$27 | Long held 462 min, -$12.25. Multiple loss cascade. |
| Feb 25 | -$64.90 | CATASTROPHIC: Short held 905 min (15 hours), -8.5% on notional |
| Feb 26 | ~flat | Recovery attempt, fib_retrace +$2.23, 1 open trade |

**10-Day Net: approximately -$60 to -$65 real loss**
**loss_debt_usd in state.json confirms: $64.97 in unrecovered debt tracked by bot**

---

## Critical Incident: Feb 25 -- The 905-Minute Short

**What happened:** Bot entered short at 0.15316 (4:28 AM PT, Feb 25). XLM then rallied hard. Position held for 15 hours, exiting at 0.16614. That is an 8.47% adverse move at 4x leverage = -$64.90.

**What should have stopped it:**
- circuit_breaker single_trade_max_loss_usd: 30 -- DID NOT FIRE
- max_hold_hours: 6 -- DID NOT FIRE
- time_stop_bars: 4 (in config = 1 hour at 15m bars) -- DID NOT FIRE
- The overnight margin guard should have blocked the entry or forced closure

**Why circuit breakers failed -- diagnosis:**

1. The config shows time_stop_bars: 4 in the exits section. At 15m candles that is 1 hour. The trade lasted 905 minutes (60+ bars). This means the time stop check either had a bug, was bypassed by a recovery/rescue state, or the bot process restarted and lost hold-time context on Oracle Cloud.

2. No circuit_breaker key exists in config.yaml at all. The single_trade_max_loss_usd: 30 setting referenced does not appear in the deployed config. It may have been removed or was never pushed to Oracle Cloud.

3. The Feb 24 long (462 min, -$12.25) also breached the 4-bar (1h) time stop. Two catastrophic time-stop failures in 2 days is a systemic bug, not a one-off.

4. The reconcile drift count today is 11. High drift count suggests the bot and exchange have been disagreeing about position state, which can suppress exit checks.

**Critical observation:** The exit reason for the Feb 25 trade is exchange_side_close -- meaning Coinbase closed the position, NOT the bot. Same for the Feb 24 loss. The bot did not exit on its own logic on either occasion. The exchange did the cleanup after 7-15 hours of exposure.

---

## Second Incident: Feb 24 -- 462-Minute Long

Bot entered long at 0.15243 (5:34 PM PT, Feb 23). Exited 7:17 AM PT Feb 24 -- 462 min later -- at 0.14998, -$12.25. Exit reason: exchange_side_close. Same pattern as Feb 25.

---

## Today (Feb 26)

- 3 trades, 1 loss, PnL -$0.07 (near flat)
- 1 open long: entry 0.16102, entered 11:42 AM PT
- Margin tier: SAFE (MR intraday 0.785, overnight 1.261)
- Overnight trading: blocked (insufficient equity for overnight margin)
- Reconcile drift count: 11 today -- elevated, watch this
- Wait since last exit: 867 minutes (14+ hours idle before this trade)
- EV estimate on open trade: -$2.84 (negative expected value -- caution)

---

## Bot Health

- Last cycle: 11:43 AM PT (recent, healthy on Oracle Cloud)
- Safe mode: OFF
- Recovery mode: NORMAL
- Loss debt: $64.97 tracked
- Max trades today: 8 (config hard cap, Phase 1 mode)
- Today trade count: 3 of 8 used

---

## Gate and Signal State (as of last snapshot)

- atr_regime: PASS, session: PASS, spread: PASS, distance_from_value: PASS
- Long score: 40 (below 55 threshold -- blocked for new entries)
- Short score: 75 (no structure -- blocked)
- Open trade (pullback, confluence 46) entered under a relaxed overnight REDUCED window threshold
- Vol phase: COMPRESSION -- market is coiling, not trending

---

## Open Position Risk

The current long entered at 0.16102, SL at 0.15815. That is a $1,435 notional stop buffer. With 4x leverage on $808 notional the max bot-managed loss on stop hit is roughly $14. The EV snapshot shows -$2.84 expected value meaning statistically this trade is underwater before fees at current probabilities. This is REDUCED quality tier -- expect small win or small loss, not a large move.

Watch: if price does not move toward TP1 (0.16907) within the next 1-2 hours, the bot should time-stop this trade. Given the recent history of time stops NOT firing, monitor manually.

---

DISCLAIMER: This content is for informational and educational purposes only and does not constitute financial, investment, or trading advice. Cryptocurrency and derivatives trading involves substantial risk of loss. Always do your own research (DYOR) and consult a qualified financial advisor before making any investment decisions.
