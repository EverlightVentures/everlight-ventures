# XLM Bot Forensic Analysis -- March 22, 2026

## Results: 54 trades, -$93.35 total PnL

| Metric | Value |
|--------|-------|
| Wins | 15 (28%) |
| Losses | 39 (72%) |
| Total PnL | -$93.35 |
| Total Fees | $28.89 |
| Avg Win | +$3.21 |
| Avg Loss | -$3.63 |
| Profit Factor | 0.34 |
| Expectancy | -$1.73/trade |
| Account Start | $640 |
| Account Now | ~$525 |

## Top 3 Problems (Ranked by $ Impact)

### 1. exchange_side_close: -$59.75 (13 trades)
Exchange is closing positions -- not the bot. Likely margin-related or Coinbase CDE order matching issues. The bot never intended to exit these trades.

### 2. reversal_signal exits: -$37.54 (11 trades)
Bot enters, price moves against it slightly, then a reversal signal fires and the bot exits at a loss. It flip-flops instead of holding.

### 3. single_trade_max_loss: -$31.33 (2 trades)
Two catastrophic losses of $15.97 and $15.36. These wiped out multiple winning trades.

## The Only Profitable Pattern
tp1 exits: +$36.83 across 8 trades (avg +$4.60 each). When the bot reaches take-profit, it works. The problem is getting there.

## Root Causes
1. Position sizing too large relative to account -- margin pressure causes exchange closes
2. Reversal signal exits too sensitive -- kills trades before they develop
3. No hard stop-loss -- positions bleed until exchange force-closes them
4. Fees ($28.89) are 30% of gross wins ($48.15) -- eating the edge
5. 72% of trades lose -- entry quality is poor

## Required Fixes (Next Session)
1. Reduce position size to lower margin pressure (stop exchange_side_close)
2. Disable reversal_signal as an EXIT reason (only use for entries)
3. Add hard stop-loss at 1% max to prevent catastrophic losses
4. Increase minimum quality score threshold to only take A+ setups
5. Widen TP targets -- current tp1 is too tight, misses bigger moves
6. Consider pausing the bot until fixes are tested in backtest
