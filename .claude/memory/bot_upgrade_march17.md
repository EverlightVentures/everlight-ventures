---
name: XLM Bot Major Upgrade March 17 2026
description: Comprehensive bot overhaul - candle fixes, pattern engine, Lane V, exits, personality, learning system
type: project
---

## Completed March 17 2026

### Critical Fixes
- Fixed stale candle data (fetching from perp instead of spot, 3 weeks stale)
- Fixed SAFE_MODE bug (pnl <= -0 triggered on any loss day)
- Fixed balance reconciler drift loop (DERIVATIVES_EXCESS sweep removed)
- Fixed equity calculation (fallback to spot+derivatives balance)
- Distance gate now breakout-aware (5x ATR mult when 1h ATR expanding)

### Exit Strategy (User Mirror Strategy)
- All mechanical exits DISABLED (tp1, profit_lock, break_even, early_save, time_stop)
- Mirror drawdown: down $X = wait for up $X, chart-aware (holds if trend healthy)
- No hard stops. Near liquidation = add margin from spot, never panic sell
- Only exits: trend_flip, reversal_signal, AI executive, margin cutoff

### Patterns
- Candle: 9 -> 27 (deployed)
- Chart: 9 -> 9 (18 more researched, build pending)
- Location-aware scoring: +20 pts at key structure level

### Personality
- Wolf of Wall Street / Belfort persona in ai/prompts.py and alerts/slack.py

### Learning
- trade_reviewer.py: shadow tracking + lessons, 49 trades seeded

### Still TODO
- 18 more chart pattern detectors (research in task a98852b8d801d1125)
- 42 new strategy lanes (research in task a7fd39c4721b3d86a)
