---
name: Trading philosophy - stop scared exits
description: User is experienced leveraged trader. Bot must trade aggressively with 2:1 R:R minimum, no scared exits. Hold for days if needed.
type: feedback
---

User has made $25k overnight on 5x leverage with $5k down on futures. He knows what he's doing and wants the bot to match his style.

**Why:** Bot was taking $2-8 wins and $3-65 losses. Exiting on noise (reversal_signal, profit_decay, ai_executive_exit) while the trade thesis was still valid. Price returned to entry after exits proving the exits were premature.

**How to apply:**
- Minimum 2:1 risk-to-reward on every trade, no exceptions
- Once in a trade, only exit at STOP LOSS or TAKE PROFIT - no scared middle exits
- Hold for hours or days if the thesis is intact
- Bigger TP targets (5% base, 3 ATR trend, 2 ATR MR)
- Don't lock profits on crumbs ($2-3) - wait for real moves ($5-10+)
- The bot is a green machine - treat it like one
- Reference strategies: 5-min first candle breakout (prev day H/L + session open range), 1-hour continuation candle pattern, FVG entries with 2R fixed target
- Key insight from videos: simplicity wins, mechanical rules, fixed R:R, first 90min of session
