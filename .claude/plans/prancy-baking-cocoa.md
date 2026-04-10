# XLM Bot Self-Learning Evolution System

## Context

The bot has 171 trades with a 21% win rate and -$119 net PnL. Lane A (pullbacks) fired 47 times at 0% win rate. Fees ate $71. The bot has no memory between sessions -- it can't learn from its own mistakes. The adaptive threshold system exists but is disabled. Claude sees past trades but never gets told whether its own calls were right or wrong. The 9 entry lanes miss several common market conditions (wick rejections, volume climax reversals, VWAP reversion, and have no protection against MTF conflicts or trend exhaustion).

This plan adds self-learning capabilities, 5 new lanes, a full evolution engine, and live inter-agent communication so the AI agents can debate, challenge each other, and reach consensus in real-time during trades.

---

## Phase 0: Live Agent Communication (Critical Gap)

### Problem
Right now the 3 AI agents (Claude, Gemini, Codex) fire independently as detached subprocesses. They write results to the same cache file but never see each other's live output. Claude gets Gemini's previous cycle's stale result as "peer_intel." There is no real-time debate, challenge, or consensus mechanism. Each agent operates in isolation.

### Solution: New file `ai/agent_comms.py` (~250 lines)

A lightweight real-time communication layer using a shared JSON message board (`data/agent_comms.json`). Each cycle runs a 3-step protocol:

**Step 1: Independent Assessment (parallel, non-blocking)**
- All 3 agents fire simultaneously with the same market context (already happens)
- Each writes their assessment to `agent_comms.json` under their key
- Format: `{"action": "ENTER_SHORT", "confidence": 0.72, "reasoning": "...", "concerns": ["..."]}`

**Step 2: Challenge Round (sequential, fast)**
- Once all 3 assessments land, fire a second call to Claude with ALL peer assessments visible
- Prompt: "Here is what you said, here is what Gemini said, here is what Codex reported. Do you still agree? Any concerns raised by peers you want to address?"
- Gemini gets the same -- sees Claude's and Codex's assessments, can revise or hold firm
- This is the "debate" -- each agent sees the others' reasoning and can change their mind

**Step 3: Executive Consensus (Claude decides)**
- Claude sees the final positions of all agents after the challenge round
- Makes the executive call with full awareness of agreements and disagreements
- Logs: `{"consensus": true/false, "dissenter": "gemini", "dissent_reason": "...", "final_action": "ENTER_SHORT"}`
- If all 3 agree: high confidence, full size
- If 2 of 3 agree: moderate confidence, standard size
- If all disagree: FLAT (stay out)

**During-trade communication (exit monitoring):**
- Every cycle while in a trade, all 3 agents assess the position
- If any agent says EXIT with confidence > 0.70, it triggers an emergency review
- Claude sees the exit request + reasoning from the requesting agent
- Must actively OVERRIDE the exit request to stay in (not just ignore it)
- Logged as: `{"exit_challenge_by": "gemini", "claude_override": true/false, "reason": "..."}`

### Functions:
- `post_assessment(agent_name, assessment)` -- write to message board
- `get_all_assessments()` -- read all agents' current positions
- `build_challenge_prompt(agent_name, own_assessment, peer_assessments)` -- creates debate prompt
- `build_consensus_prompt(all_final_assessments)` -- creates final decision prompt
- `log_consensus(result)` -- append to `logs/agent_debates.jsonl`
- `check_exit_challenge(agent_name, exit_request)` -- during-trade exit debate

### Config additions (config.yaml):
```yaml
ai:
  agent_comms:
    enabled: true
    challenge_round: true
    consensus_required: false
    exit_challenge_threshold: 0.70
    max_debate_time_sec: 30
    log_debates: true
```

### main.py integration (~20 lines):
- After initial agent assessments fire (line 6538-6539): wait up to 30s for all to land
- Fire challenge round prompts
- Read final consensus before entry/exit decision
- During trade: check for exit challenges each cycle

### Timing impact:
- Step 1 already happens (parallel fire, ~10-15s)
- Step 2 adds ~15-20s (one more API call per agent)
- Step 3 adds ~10s (Claude final call)
- Total: ~30-45s per decision vs current ~15s
- Acceptable for 15m candle timeframe (cycle every 900s)
- Config `challenge_round: false` skips Step 2 for faster execution

**Output:** `logs/agent_debates.jsonl` -- full debate history, `data/agent_comms.json` -- live message board

---

## Phase 1: Stop the Bleeding

### 1A. Enable adaptive thresholds
- **File:** `config.yaml` line 440 -- flip `enabled: false` to `enabled: true`
- Already wired in `main.py` line 4929 and `strategy/adaptive.py` -- just needs the flag

### 1B. New file: `strategy/lane_performance_tracker.py` (~180 lines)
Computes per-lane win rate, avg PnL, trade count from `logs/trades.csv` after every trade close.

Functions:
- `compute_lane_stats(trades_csv, lookback=50)` -- returns dict of per-lane stats
- `update_lane_performance(trades_csv, output_path)` -- writes to `logs/lane_performance.json`
- `get_lane_overrides(stats, min_trades=15, min_win_rate=0.15)` -- returns disable/raise_threshold directives for bad lanes

### 1C. Hook into main.py
- After `log_trade()` (~line 1924): call `update_lane_performance()`
- In lane scoring (~line 2640): read `lane_performance.json`, disable or raise thresholds for bad lanes
- All wrapped in try/except -- never blocks trading

**Output:** `logs/lane_performance.json` -- per-lane stats updated after every trade

---

## Phase 2: Agent Memory & Feedback Loop

### 2A. New file: `ai/decision_linker.py` (~150 lines)
Links decisions from `decisions.jsonl` to trade outcomes in `trades.csv`.

Functions:
- `link_decisions(decisions_path, trades_path, output_path)` -- matches decisions to outcomes
- Uses watermark file (`data/.linker_watermark`) to avoid re-reading the 110MB file
- Called after each trade close alongside lane tracker

### 2B. Enhance `ai/prompts.py`
- Add `_fmt_lane_performance(lane_perf_path)` -- formats lane stats table for Claude
- Modify `master_directive_prompt()` -- add `lane_perf_path` param, inject lane performance after trade history
- Add `lane_adjustments` to Claude's response schema: `{"lane_A_threshold": 70, "lane_B_enabled": false}`

### 2C. Modify `ai/claude_advisor.py`
- Add `lane_perf_path` param to `request_directive()`, pass through to prompt builder

### 2D. Apply Claude's lane adjustments in `main.py`
- After directive is read (~line 5537): parse `lane_adjustments`, store in state as `_ai_lane_overrides`
- In lane scoring (~line 2640): apply AI overrides (disable lanes, raise thresholds)
- Claude can now say "Lane A is garbage, raise threshold to 80" and the bot obeys

**Output:** `logs/decision_outcomes.jsonl` -- each trade linked to the decision that created it

---

## Phase 3: Five New Lanes

All detection functions added to `strategy/entries.py`. Lane routing added to `strategy/lane_scoring.py`. Config added to `config.yaml`.

### Lane K: Wick Rejection (ENTRY)
- Detects: large wick at S/R level, body closes away, volume confirms
- Requirements: within 1.5% of structure level, wick >= 60% of range, volume >= 1.0x avg
- Threshold: 50, rescore as reversal_impulse, ATR+distance bypass
- Lane budget: 0.7

### Lane L: MTF Conflict Block (BLOCKER)
- Returns True to BLOCK entries when 15m contradicts 1h/4h
- Checks: EMA slope conflict, RSI gap > 20 between timeframes, structure bias mismatch
- Not an entry lane -- prevents bad entries from other lanes
- Applied after entry detection, before scoring

### Lane M: Volume Climax Reversal (ENTRY)
- Detects: extreme volume (>= 2.5x avg) with against-momentum close (capitulation)
- Requirements: RSI was in extreme zone within 3 bars, body in reversal direction
- Threshold: 55, rescore as reversal_impulse
- Lane budget: 0.6

### Lane N: VWAP Reversion (ENTRY)
- Detects: price snapping back to VWAP after >1% deviation
- Requirements: reversion started, RSI supports, volume declining from peak
- Threshold: 50
- Lane budget: 0.8

### Lane O: Exhaustion Warning (BLOCKER)
- Returns True to BLOCK late entries into dying trends
- Checks: 3+ expanding-body candles, RSI deep extreme (>75/<25), volume divergence, ATR shock
- Applied after entry detection, before scoring

### main.py changes (~30 lines)
- Add imports for 5 new functions
- Add K/M/N to entry signal chain (lines 2519-2536)
- Add L/O as blocking gates after entry detection (before scoring)

### config.yaml additions
- Lane thresholds: K=50, M=55, N=50
- Lane enables: K/L/M/N/O all true
- Lane weights for K/M/N (flag profiles for v4 scoring)
- Lane budgets: K=0.7, M=0.6, N=0.8

---

## Phase 4: Evolution Engine

### New file: `strategy/evolution.py` (~350 lines)

`EvolutionEngine` class with three components:

**1. Thompson Sampling Bandit**
- Each lane = arm with (alpha=wins+1, beta=losses+1)
- Sample from Beta(alpha, beta) to prioritize lanes
- Naturally explores undersampled lanes, exploits proven ones
- `sample_lane_priority(available_lanes)` -- returns lanes sorted by probability
- `update_bandit(lane, won)` -- update after trade

**2. Weight Adjuster**
- Tracks which v4 flags predict wins vs losses per lane
- Every 25 trades per lane: flags with >55% win rate get +5 weight, <35% get -5 (capped +/-15)
- `get_weight_adjustments(lane)` -- returns flag deltas
- `update_weights(lane, flags_fired, won)` -- track per trade

**3. Threshold Optimizer**
- Rolling 50-trade windows per lane
- Tests candidate thresholds (base-10 to base+20, step 5)
- Picks threshold maximizing: win_rate * avg_win - (1-win_rate) * avg_loss
- `get_optimal_threshold(lane, base)` -- returns evolved threshold
- `update_threshold_data(lane, score, threshold, pnl, won)` -- record data

### Public API
- `post_trade_update(lane, won, pnl, score, threshold, flags)` -- called after every trade
- `get_lane_config(lane, base_threshold)` -- returns evolved threshold + weight adjustments + bandit priority
- `get_dashboard_metrics()` -- for dashboard visualization

### State: `data/evolution_state.json`
- Bandit arm counts per lane
- Flag win/loss counters per lane
- Threshold optimization windows per lane
- Generation counter (increments every 25 trades)

### main.py hooks (~30 lines)
- Initialize `EvolutionEngine` at startup
- Post-trade: call `post_trade_update()` in `log_trade()`
- Pre-entry: call `get_lane_config()` to apply evolved thresholds + weight adjustments
- All wrapped in try/except -- evolution failure never blocks trading

### Dashboard additions (~80 lines in `dashboard.py`)
- Lane bandit priorities bar chart
- Weight adjustment table per lane
- Threshold evolution history
- Win rate by lane with color coding

---

## File Summary

### New files (4)
| File | Lines | Purpose |
|------|-------|---------|
| `ai/agent_comms.py` | ~250 | Live inter-agent communication, debate, consensus |
| `strategy/lane_performance_tracker.py` | ~180 | Per-lane stats tracking |
| `ai/decision_linker.py` | ~150 | Link decisions to outcomes |
| `strategy/evolution.py` | ~350 | Thompson Sampling + Weight Adjuster + Threshold Optimizer |

### Modified files (8)
| File | Changes |
|------|---------|
| `config.yaml` | Enable adaptive threshold, add lane configs, add agent_comms config |
| `strategy/entries.py` | Add 5 new detection functions (~250 lines) |
| `strategy/lane_scoring.py` | Add K/M/N lane routing in select_lane() (~30 lines) |
| `ai/prompts.py` | Add `_fmt_lane_performance()`, `lane_adjustments` schema, challenge/consensus prompts (~80 lines) |
| `ai/claude_advisor.py` | Add `lane_perf_path` param, integrate agent_comms calls (~15 lines) |
| `ai/gemini_advisor.py` | Integrate agent_comms challenge round (~10 lines) |
| `main.py` | Imports, entry chains, blocking gates, evolution hooks, agent comms orchestration (~80 lines) |
| `dashboard.py` | Evolution tab + agent debate log viewer (~100 lines) |

---

## Build Order

0. **Phase 0 first** -- agent_comms.py + prompts for debate. Makes agents talk to each other live.
1. **Phase 1 next** -- config flip + lane tracker. Immediate impact, stops worst lanes.
2. **Phase 2** -- decision linker + prompt changes. Gives Claude lane awareness.
3. **Phase 3: blocking lanes first** (L, O) -- pure risk reduction, no new entries.
4. **Phase 3: entry lanes** (K, M, N) -- one at a time.
5. **Phase 4 last** -- needs 50+ trades of Phase 0-3 data to be meaningful.

## Verification

- Phase 1: Check `lane_performance.json` appears after next trade. Verify adaptive threshold shows in decision logs.
- Phase 2: Verify Claude's directive includes `lane_adjustments`. Check `decision_outcomes.jsonl` gets populated.
- Phase 3: Run with `paper=true` for 24h per new lane. Check blocking lanes actually prevent entries.
- Phase 4: After 50+ trades, verify `evolution_state.json` has non-trivial bandit/weight/threshold data.

## Rollback

Each phase independently reversible:
- Phase 0: `agent_comms.enabled: false` -- agents revert to independent fire-and-forget
- Phase 1: `adaptive_threshold.enabled: false`, delete `lane_performance.json`
- Phase 2: Remove `lane_perf_path` from directive payload
- Phase 3: `lane_X_enabled: false` in config for any lane
- Phase 4: Delete `evolution_state.json` -- engine resets to fresh state
- Nuclear: Revert main.py -- all new modules are standalone and do nothing unless imported
