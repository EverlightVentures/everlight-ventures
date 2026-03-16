# Everlight AI Hive Mind Protocol
> The central collaboration doctrine for Claude, Gemini, Codex, and Perplexity operating in `AA_MY_DRIVE`.

## The Quad Architecture
Four AI systems act as a unified brain, each playing to their strengths.

1.  **Claude (Chief Operator / Strategist)**
    - Role: High-level planning, deep architectural review, complex synthesis, risk assessment
    - Domain: `.claude/`
    - 8 employees: chief_operator, architect, content_director, qa_gate, trading_risk, reviewer, content_strategy, editor_qa

2.  **Gemini (Logistics Commander / Executor)**
    - Role: Rapid implementation, multi-tool orchestration, workflow automation, distribution
    - Domain: `.gemini/`
    - 8 employees: logistics_commander, ops_deputy, workflow_builder, automation_architect, sync_coordinator, distribution_ops, analytics_auditor, packager

3.  **Codex (Engineering Foreman / Profit Maximizer)**
    - Role: Code generation, ROI analysis, SaaS building, funnel architecture
    - Domain: `.codex/`
    - 8 employees: engineering_foreman, profit_maximizer, saas_builder, saas_pm, saas_growth, funnel_architect, seo_mapper, writer

4.  **Perplexity (Intelligence Anchor / News Desk)**
    - Role: Real-time research, unbiased news, market data, sourced findings
    - ALWAYS runs first as intel scout before other managers engage
    - 8 research beats: Crypto/DeFi, Finance/Markets, World News, Tech/AI, Business/Startups, Science/Health, Legal/Regulatory, Personal/Local

## How to Use the Hive

### Headless (smart dispatch)
```bash
hive "Should I scale xlm_bot to $2000?"     # Smart routing picks best managers
hive --lite "What's XLM doing today?"        # Claude + Perplexity only (fast/cheap)
hive --all "Full Q2 strategy review"         # Force all 4 managers
hive -v "Source a product for April"          # Verbose: see each manager's progress
```

### Visual War Room (tmux)
```bash
ws                                            # Open 4-pane War Room
ws "analyze my bot performance"               # Open + broadcast to all 4
```

### Web Dashboard
```bash
# Hive dashboard at localhost:8503
cd 09_DASHBOARD/hive_dashboard && python manage.py runserver 0.0.0.0:8503
```
Features: session browser, agent stats, analytics charts, live console (dispatch queries from browser), per-agent copy buttons, markdown export, date/sort filters, 7-day activity chart, query history chips.

### In the War Room
- Tap a pane to focus it (keyboard pops up)
- Ctrl-b + arrow keys to switch panes
- Ctrl-b m to toggle mouse mode (for scrolling)
- Ctrl-b d to detach (session keeps running)
- Run `ws` again to reattach

## Smart Routing
The router classifies your prompt and picks only the managers needed:

| Prompt type | Managers engaged |
|---|---|
| Trading/bot/crypto | Claude + Codex + Perplexity |
| Content/writing/publishing | Claude + Gemini + Perplexity |
| Engineering/code/deploy | Codex + Perplexity |
| Business/SaaS/ecommerce | Claude + Codex + Perplexity |
| Research/news/market | Perplexity + Claude |
| Operations/automation | Gemini + Claude + Perplexity |
| Ambiguous/complex | All 4 |

## Execution Flow
1. **Perplexity runs first** - grabs real-time intel personalized to you
2. **Router classifies** - picks the best managers for this specific prompt
3. **Managers run in parallel** - each with Perplexity intel + their team's expertise
4. **Claude executes** - actionable items auto-implemented when possible
5. **Results converge** - combined summary on screen, full reports in War Room

## XLM Bot Intelligence Layer
The Hive Mind feeds directly into the XLM trading bot's decision engine:

### HTF Trend Bias Filter
Classifies market state from 1h data: `bearish_crash / bearish_trend / neutral / bullish_trend / bullish_expansion`.
- **bearish_crash**: blocks all longs except capitulation reversals (reversal_impulse, wick_rejection, volume_climax_reversal, fib_retrace)
- **bullish_expansion**: blocks all shorts except those same reversal types
- Asymmetric sizing: crash longs get 0.4x, crash shorts get 1.2x (and vice versa for expansion)

### Sentiment Gate (Fear & Greed Index)
- F&G < 10: blocks ALL entries (catastrophic panic)
- F&G < 20: blocks longs specifically (extreme fear, shorts only)
- F&G < 30: reduces position size by 50%

### Circuit Breaker & Escalation Matrix
- **Single trade max loss**: $15 (any trade bleeding more is force-exited)
- **Max hold time**: 4 hours (any position open longer is force-exited)
- **Hard daily drawdown cap**: $35 (non-overrideable, blocks AI executive too)
- **Tier 1**: 4 losses / $20 drawdown -> pause 30 min, auto-recover
- **Tier 2**: 6 losses / $35 drawdown -> close all + halt
- **Tier 3**: 8 losses / $50 drawdown -> stop service, manual restart only

### AI Executive Mode
Claude Opus acts as executive decision-maker, with Codex and Gemini as peer advisors. 3-agent consensus available (challenge rounds, debate logging). All 3 run in parallel for entry/exit/hold/flat decisions.

### Stale Data Guards
- Candle staleness: blocks entries if most recent 15m candle > 45 min old
- Price sanity: aborts cycle if candle price diverges > 10% from contract mark price
- Candle cache: merges instead of overwriting, preventing partial API data from corrupting history

## War Room Communication
- Location: `_logs/ai_war_room/`
- Each session creates: `hive_{id}_{timestamp}/`
- Contains: individual manager reports + combined summary + session.json
- Execution reports: `05_claude_execution_report.md` (when Claude implements changes)
- Sessions logged to: `_logs/hive_sessions.jsonl`
- Slack: posted to `#xlm-bot` (trades) and `#hive-war-room` (deliberations)

## Deployment
- **XLM Bot**: Oracle Cloud VM (Ampere A1 ARM64 free tier), Docker, always-on
- **Dashboard**: `http://ORACLE_VM_IP:8502` (bot), `localhost:8503` (hive)
- **War Room**: local Termux tmux sessions
- **Slack**: dual webhooks (trade alerts + war room deliberations)

## Execution Rules
1. **Never duplicate work** - Router ensures only the right managers engage
2. **Perplexity first** - Always get fresh intel before deliberating
3. **Synergy, not replacement** - Claude plans, Gemini builds, Codex engineers, Perplexity researches
4. **Profit first** - All business operations checked against Profit Maximizer principles
5. **Save tokens** - Lite mode for quick questions, full mode for big decisions
6. **Zero toxic losses** - Bot guardrails (circuit breaker, sentiment gate, HTF filter) are non-negotiable

## SaaS Roadmap
The Hive Mind is being evaluated for SaaS productization:
- **Phase 0 (current)**: Local-first, single-user, prove the workflow
- **Phase 1**: Multi-tenant auth, API-first backend, managed dashboard
- **Phase 2**: AI workflows, mindmaps, automated sales/support
- **Phase 3**: Full office suite, subscriptions, premium UI

## Workspace Map & Semantic Mind Map
Before suggesting profitable moves, manipulating data, or trying to find files, ALL agents MUST read `WORKSPACE_MANIFEST.md` for the absolute source of truth on the 01-09 directory structure.

## Configuration
- Team rosters: `everlight_os/hive_mind/roster.yaml`
- Routing rules: same file under `routing_rules:`
- User context: same file under `user_context:`
- Slack: `everlight_os/configs/everlight.yaml` under `slack:`
- Hive dashboard: `09_DASHBOARD/hive_dashboard/`
- Bot config: `xlm_bot/config.yaml`
