---
name: Trading strategy references from videos
description: Core trading strategies user wants implemented - ORB, hourly continuation, FVG, reactive breakout, 2:1 R:R. All deployed 2026-03-19.
type: feedback
---

User studied and wants these strategies integrated into the XLM bot:

1. **5-min ORB (Opening Range Breakout)** - First candle at NY open (9:30 ET), mark high/low, trade breakout + retest, target prev day high/low. Implemented as Lane W.

2. **Hourly Candle Continuation** - Previous 1h candle sets bias, use 15m for momentum shift entries. Implemented as Lane X.

3. **FVG (Fair Value Gap)** - 3-candle pattern confirmation. Already existed in strategy/fvg.py, now used as confluence in Lanes W and X.

4. **Fixed 2:1 R:R** - Never risk $1 for less than $2. Enforced globally via min_rr_ratio: 2.0.

5. **Reactive trading** - Wait for pattern, breakout, retest. Never predict. Already had breakout_retest lane.

6. **Stop to breakeven at 1.5R** - Mechanical profit protection.

7. **First 90 minutes of session** - Highest volume/volatility. Bot's CDE margin window (5AM-1PM PT) aligns.

**Why:** User is experienced leveraged trader who made $25k overnight. Bot was too scared, taking $2-8 wins and $3-65 losses. These strategies enforce discipline and bigger targets.

**How to apply:** All changes deployed to Oracle 2026-03-19. When tuning bot in future, maintain these principles. Never reduce min_rr below 2.0. Keep exits wide. Let trades breathe.
