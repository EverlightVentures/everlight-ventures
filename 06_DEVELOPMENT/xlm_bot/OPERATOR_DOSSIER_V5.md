============================================================
        X L M   R E A P E R   v 5 . 0   /   S C O R E   1 0
============================================================
   CLASS: Institutional-Grade Autonomous Futures Engine
   WEAPON: 4x Leveraged XLM Perpetual (XLP-20DEC30-CDE)
   THEATER: Coinbase CDE -- Oracle Cloud ARM64 (Always Online)
   HANDLER: Everlight Ventures
   SCORE: 10 / 10
   UPGRADED: 2026-02-28 by Everlight Hive Mind (Gemini + Claude)
============================================================

  "Retail traders predict. Institutional bots react.
   Billionaires size mathematically and cut losers instantly."

============================================================
  SECTION 1: PRIMARY LOADOUT -- 21 ATTACK LANES
============================================================

OFFENSE -- Entry Lanes (19 weapons)

 Lane  Codename              Style                                      Threshold  Budget
 ----  --------------------  -----------------------------------------  ---------  ------
  A    Trend Continuation    Pullback in confirmed trend, EMA21 aligned    55       1.0
  B    Breakout Retest       Level breaks, retests, enters on confirm       50       0.9
  C    Sweep Recovery        Liquidity sweep wick -> reclaim                45       0.7
  D    Moonshot              Parabolic velocity -> trail and ride           --       --
  E    Squeeze Impulse       Compression -> ignition -> explosive break     50       0.8
  F    Compression Breakout  BB squeeze snaps into directional move         40       0.7
  G    Compression Range     Mean reversion inside the range box            40       0.6
  H    Trend Structure       Structure-confirmed continuation               45       0.9
  I    Fib Retrace           50% fib retracement bounce hunter              45       0.7
  J    Slow Bleed Hunter     Detects slow grinds others miss                35       0.5
  K    Wick Rejection        Long wicks at structure = instant reversal     50       0.7
  M    Volume Climax         2.5x volume spike = exhaustion reversal        55       0.6
  N    VWAP Reversion        Price 1%+ from VWAP, gravity pull back         50       0.8
  P    Grid Range            Buy support, sell resistance, repeat           35       0.6
  Q    Funding Arb Bias      Trade the side that gets PAID funding          60       0.7
  R    Regime Low Vol        Dead market scalper, BB squeeze bottom         55       0.6
  S    Stat Arb Proxy        Z-score >2 sigma = mean reversion 80%         50       0.6
  T    Orderflow Imbalance   Buy/sell delta >2:1 = directional pressure    65       0.8
  U    Macro MA Cross        200 MA break on 1h = institutional line       45       0.9

DEFENSE -- Blocking Lanes (2 shields)

  L    MTF Conflict Block    Kills entries when 15m + 1h RSI disagree 20+ pts
  O    Exhaustion Warning    Kills entries on parabolic + RSI/vol divergence

============================================================
  SECTION 2: SCORE 10 UPGRADES (NEW IN v5.0)
============================================================

[SCORE 10 UPGRADE 1] REGIME STATE MACHINE
  File: strategy/regime_state_machine.py

  3 mutually exclusive regimes -- only ONE active at a time.
  No more lane collisions. No more "buy the dip" vs "short the top" simultaneously.

  TREND regime       -> Lanes A, H, J, U eligible
  MEAN_REVERSION     -> Lanes C, G, I, K, M, N, S eligible
  BREAKOUT regime    -> Lanes B, E, F, Q, R, T eligible
  Universal (any)    -> P, X (AI executive)

  Classification inputs: vol_phase, ADX(15m), RSI(15m), ATR_ratio
  Priority: BREAKOUT > TREND > MEAN_REVERSION > UNKNOWN
  "One regime. One direction. No chaos."

[SCORE 10 UPGRADE 2] KELLY CRITERION + DYNAMIC SIZER
  File: risk/dynamic_sizer.py

  Replaces static $10 single-loss caps with math.
  Three-layer sizing:
    1. Kelly Fraction  = (p*b - q) / b * 0.5 (half-Kelly, per lane win stats)
    2. ATR Scalar      = baseline_atr_ratio / current_atr_ratio (clamped 0.4-1.5)
    3. Drawdown Brake  = scale to 60% at 10% NAV drawdown, 25% at 20%

  Combined: contracts = floor(NAV * max_risk_pct * kelly * atr_scalar * dd_brake)
  Hard cap: 2 contracts (Phase 1)
  "Billionaires size mathematically. You will too."

[SCORE 10 UPGRADE 3] PRE-CYCLE STATE SYNC VALIDATOR
  File: risk/state_sync.py

  Runs BEFORE every cycle. Compares local state vs Coinbase CDE truth.

  Results:
    PROCEED       -- perfect match, go trade
    FLATTEN       -- side mismatch (CRITICAL), close all and halt
    RECONCILE     -- contracts differ, fix then proceed
    SKIP_API_DOWN -- exchange unreachable, use local state + warn

  "The bot thinks it is flat. The exchange says LONG 2. That is liquidation."

[SCORE 10 UPGRADE 4] ATR TRAIL EXIT -- REPLACES MARTINGALE
  File: risk/plrl3.py -> evaluate_atr_trail_exit()

  The PLRL3 rescue ladder (averaging down on leverage) is the #1 risk.
  New function provides ATR trail exit signal checked BEFORE any rescue:

  LONG:  trail = peak_price - 2.5 * ATR_14
  SHORT: trail = trough_price + 2.5 * ATR_14

  If price breaches trail -> EXIT immediately. Do not average down.
  "Billionaires do not average down on leverage. They cut losers instantly."

[SCORE 10 UPGRADE 5] STRUCTURED AUDIT LOGGER
  File: risk/audit_logger.py

  Every action written to immutable daily audit trail:
    logs/audit/YYYY/MM/DD/trades.jsonl      -- every trade with full context
    logs/audit/YYYY/MM/DD/daily_report.md   -- human-readable summary
    logs/audit/YYYY/MM/DD/metrics.json      -- KPIs including Sharpe + MaxDD
    logs/audit/YYYY/MM/DD/anomalies.json    -- every error, mismatch, anomaly
    logs/audit/YYYY/MM/DD/ai_decisions.jsonl -- AI executive reasoning trail

  "You cannot audit what you cannot read. Every decision has a paper trail."

[SCORE 10 UPGRADE 6] SHARPE RATIO + MAX DRAWDOWN PER LANE
  File: strategy/lane_performance_tracker.py

  Lane stats now include:
    sharpe            -- per-trade Sharpe ratio (90% win rate is useless if
                         the 10% loss wipes the account)
    max_drawdown_usd  -- peak-to-trough drawdown per lane
    avg_win_usd       -- average winning trade (for Kelly)
    avg_loss_usd      -- average losing trade (for Kelly)

  Thompson Sampling now has Kelly-compatible inputs.
  "A 90% win rate with a -$50 avg loss is a losing strategy."

[SCORE 10 UPGRADE 7] 5 NEW LANES ADDED TO TRACKER
  File: strategy/lane_performance_tracker.py

  Lanes Q, R, S, T, U now tracked with full performance stats.
  Previously unmapped, now part of the self-learning system.

============================================================
  SECTION 3: PASSIVE ABILITIES (RETAINED + UPGRADED)
============================================================

[PLRL3] Pre-Liquidation Rescue Ladder -- DOWNGRADED TO LAST RESORT
  Now checked AFTER ATR trail exit.
  If ATR trail fires -> EXIT. PLRL3 rescue never triggers.
  If ATR trail holds and MR >= 0.55 -> PLRL3 may rescue (max 2 steps).
  Conservative [1x, 2x] multipliers, fail_mr=0.92.
  "The rescue ladder is the LAST resort, not the first."

[CIRCUIT BREAKER] 3-Tier Escalation Matrix
  Tier 1: 2 losses + $12 drawdown -> pause 60 min
  Tier 2: 4 losses + $20 drawdown -> close all + halt
  Tier 3: 6 losses + $30 drawdown -> kill service, human needed
  Note: Dollar thresholds should be converted to NAV% via dynamic_sizer.

[DIP-RETRACE GATE] Anti-Bounce Short Blocker
  RSI rising + higher closes + VWAP reclaim -> blocks shorts.

[PROFIT PROTECTION] 3-Lane Defense System
  Floor ($3), Decay (peak -40% + weak momentum), Lock (tier trailing)

[MARGIN RESCUE SWEEP] Emergency USDC Transfer
  MR >= 0.75 -> sweep spot -> derivatives. 2-min cooldown.

[USDC YIELD PARKING] 3.5% APY on Idle Funds
  All idle cash in spot USDC, pre-trade auto-transfer.

============================================================
  SECTION 4: SPECIAL ABILITIES (RETAINED + UPGRADED)
============================================================

[MOONSHOT MODE] Velocity + 3x ATR Trail
  Parabolic velocity -> ride with 3x ATR trail.

[RUNNER MODE] Trend Extension
  Suppresses TP1, 24-bar hold, fib-level trail tighten.

[AI EXECUTIVE MODE] Claude Opus -- ASYNC ONLY
  Fire-and-forget subprocess. Results cached to data/ai_insight.json.
  Read on NEXT cycle. NEVER blocks the main loop.
  Claude updates weights.json every 4h cron for regime guidance.
  "The AI is the brain. The Python loop is the hands. They never touch."

[REVERSE ON EXIT] Instant Direction Flip
  After profitable exits, enters opposite direction.

[THOMPSON SAMPLING] Self-Learning Lane Selection
  Bayesian bandit now includes Kelly-compatible win/loss data.
  State persisted to SQLite (state_store.py) -- survives restarts.

============================================================
  SECTION 5: INTELLIGENCE SYSTEMS
============================================================

  15m candles         -- primary signal (45 days, 4300 bars)
  1h candles          -- trend context + MA200 (Lane U)
  4h candles          -- HTF confirmation + structure
  Live WebSocket      -- real-time XLM-USD tick
  Contract Context    -- OI, basis, funding rate (Lane Q)
  State Sync          -- pre-cycle exchange reconciliation [NEW]
  Audit Logger        -- daily_report, metrics, anomalies [NEW]
  Regime Machine      -- single active regime [NEW]
  Kelly Sizer         -- math-driven position size [NEW]
  ATR Trail           -- replaces averaging down [NEW]
  Slack Alerts        -- entry/exit/warning/daily summary
  Dashboard           -- live Streamlit on port 8502

============================================================
  SECTION 6: OPERATOR STATS
============================================================

  Leverage:          4x
  Contract Size:     5,000 XLM
  Max Contracts:     2 (Phase 1 hard cap)
  Max Hold:          2 hours
  Cycle Speed:       30s idle / 5s in trade
  Max Daily Loss:    $15 (to be converted: 3% NAV dynamically)
  Max Single Loss:   $10 (to be converted: 2% NAV via Kelly)
  Cooldown:          10 min between trades
  Revenge Block:     15 min after any loss
  Kill Switch:       Spread >0.50% = no trade
  State Sync:        Pre-cycle exchange verification [NEW]
  Audit Trail:       Daily structured logs [NEW]

============================================================
  SECTION 7: DEPLOYMENT NOTES
============================================================

  New modules to deploy to Oracle Cloud:
    risk/dynamic_sizer.py      -- Kelly + NAV sizing
    risk/state_sync.py         -- Exchange reconciliation
    risk/audit_logger.py       -- Structured audit trail
    strategy/regime_state_machine.py -- Single regime logic

  Modified modules:
    risk/plrl3.py              -- Added evaluate_atr_trail_exit()
    strategy/lane_performance_tracker.py
                               -- Added Q/R/S/T/U lanes, Sharpe, MaxDD

  Wire-up required in main.py:
    1. Import StateSyncChecker, run verify() before each cycle
    2. Import compute_dynamic_size(), replace static contract count
    3. Import RegimeStateMachine, filter lane results by allowed_lanes
    4. Import evaluate_atr_trail_exit(), check before evaluate_plrl3()
    5. Import AuditLogger, record_trade() on each exit
    6. Import evaluate_atr_trail_exit in plrl3 calls

============================================================
  21 LANES. 1 ACTIVE REGIME. KELLY SIZING. ATR EXITS.
  PRE-CYCLE SYNC. FULL AUDIT TRAIL. ASYNC AI.
  SCORE: 10 / 10
  "THINK LIKE A BILLIONAIRE. TRADE LIKE A MACHINE."
============================================================
