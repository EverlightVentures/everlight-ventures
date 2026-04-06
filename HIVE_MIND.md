# Everlight AI Hive Mind Protocol
> The central collaboration doctrine for Claude, Gemini, Codex, and Perplexity operating in `AA_MY_DRIVE`.

## The Quad Architecture
Four AI departments, 42 named employees, operating as one team. **No solo missions** -- every task activates 3+ employees across 2+ departments. Perplexity Intel always runs first.

> **Full Employee Directory:** `06_DEVELOPMENT/everlight_os/hive_mind/EMPLOYEE_DIRECTORY.md`
> **Team Roster Config:** `06_DEVELOPMENT/everlight_os/hive_mind/roster.yaml`

### 1. Claude Corp -- Strategy & Quality (10 employees)
- **Dept Head:** Marcus Cole, Chief Operator (marcus@everlightventures.io)
- **Domain:** `.claude/` | **Slack:** #claude-corp
- **Team:** Marcus Cole (Chief), Atlas Vega (Architect), Vera Lux (Content Director), Quinn Sharp (QA), Rex Thornton (Trading Risk), Sage Holloway (Reviewer), Nora Blaine (Content Strategy), Edith Cross (Editor), Cash Moreno (Commission Auditor), Justine Park (Compliance)
- **Owns:** Strategy, quality gates, risk, compliance, brand voice, legal review

### 2. Gemini Ops -- Execution & Distribution (13 employees)
- **Dept Head:** Major Dex, Logistics Commander (major@everlightventures.io)
- **Domain:** `.gemini/` | **Slack:** #gemini-ops
- **Team:** Major Dex (Commander), Mack Rivera (Deputy), Gears Tanaka (Workflows), Aria Chen (Automation), Link Masters (Sync), Dash Monroe (Distribution), Metric Webb (Analytics), Bo Crate (Packager), Scout Navarro (Deal Scout), Piper Reeves (Outreach), Chart Dawson (Broker Analytics), Rex Blackwell (Wholesale Scout), Ace Morgan (Deal Marketer)
- **Owns:** Execution, automation, pipelines, distribution, deal sourcing, outreach

### 3. Codex Labs -- Engineering & Profit (11 employees)
- **Dept Head:** Forge Steele, Engineering Foreman (forge@everlightventures.io)
- **Domain:** `.codex/` | **Slack:** #codex-labs
- **Team:** Forge Steele (Engineer Lead), Penny Vance (Profit Maximizer), Stack Torres (SaaS Builder), Road Harper (PM), Rocket Kim (Growth), Flow Jordan (Funnels), Spider Locke (SEO), Ink Castellano (Writer), Filter Banks (Lead Qualifier), Cupid Osei (Match Maker), Hammer Knox (Deal Closer)
- **Owns:** Code, SaaS products, ROI, funnels, SEO, deal lifecycle (qualify to match to close)

### 4. Perplexity Intel -- Research & Intelligence (8 beat reporters)
- **Dept Head:** The Desk (collective newsroom) (intel@everlightventures.io)
- **Domain:** `.perplexity/` | **Slack:** #perplexity-intel
- **Beats:** Cipher Wolfe (Crypto), Bull Archer (Markets), Wire Santos (World), Nova Ling (Tech/AI), Pitch Adler (Business), Helix Patel (Science), Brief Calloway (Legal), Pulse Diaz (Personal)
- **Owns:** Real-time sourced intelligence. ALWAYS runs first before any department moves

### Collaboration Rules
- **Min 3 agents per task, across 2+ departments** -- no exceptions
- **Perplexity first** -- fresh intel before anyone deliberates
- **Cross-dept Slack threads** are the norm for every deliverable
- **War Room** for big decisions -- all 4 dept heads weigh in

### Cross-Department Workflow: Dashboard Ops

All dashboards (bot, broker, hive, public) are maintained by a 7-person cross-department team:

| # | Employee | Dept | Responsibility |
|---|----------|------|----------------|
| 1 | Link Masters | Gemini/Sync | Data sync integrity across Supabase, Django, Lovable |
| 2 | Metric Webb | Gemini/Analytics | KPI accuracy + anomaly detection |
| 3 | Chart Dawson | Gemini/Broker Analytics | Broker pipeline dashboard accuracy |
| 4 | Rex Thornton | Claude/Risk | XLM bot dashboard (P&L, drawdowns, margin, circuit breaker) |
| 5 | Penny Vance | Codex/Profit | Profit relevance audit -- every widget must earn its screen space |
| 6 | Quinn Sharp | Claude/QA | Dashboard QA (broken charts, stale data, slow loads, wrong dates) |
| 7 | Major Dex | Gemini/Ops | Daily 5:30 AM health check coordination ("are all dashboards green?") |

### Cross-Department Workflow: Wholesale Pipeline

12-person crew handles every wholesale deal from scout to close:

| # | Employee | Dept | Role in Pipeline |
|---|----------|------|------------------|
| 1 | Rex Blackwell | Gemini/Scout | Finds distressed properties, Zillow keywords, initial scoring |
| 2 | Filter Banks | Codex/Qualifier | Property qualification (ARV, equity, motivation score) |
| 3 | Penny Vance | Codex/Profit | Money math (MAO, repair costs, assignment fee calc) |
| 4 | Cupid Osei | Codex/Matcher | Matches properties to cash buyers from investor list |
| 5 | Ace Morgan | Gemini/Marketing | Custom investment pitches per property |
| 6 | Piper Reeves | Gemini/Outreach | Seller outreach (SMS, email, direct mail) |
| 7 | Hammer Knox | Codex/Closer | Contract to close, earnest money, deadlines |
| 8 | Justine Park | Claude/Compliance | CA wholesaling rules, contract review |
| 9 | Cash Moreno | Claude/Auditor | Assignment fee tracking, payment reconciliation |
| 10 | Chart Dawson | Gemini/Analytics | Pipeline analytics, conversion tracking |
| 11 | Brief Calloway | Perplexity/Legal | Wholesale regulation monitoring (CA AB 1850) |
| 12 | Pitch Adler | Perplexity/Intel | Market intel on target cities, investor trends |

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
# Hive dashboard at localhost:8504
cd 09_DASHBOARD/hive_dashboard && ./start.sh
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
- **Dashboard**: `http://ORACLE_VM_IP:8502` (bot), `localhost:8504` (hive)
- **War Room**: local Termux tmux sessions
- **Slack**: dual webhooks (trade alerts + war room deliberations)

## Execution Rules
1. **Never duplicate work** - Router ensures only the right managers engage
2. **Perplexity first** - Always get fresh intel before deliberating
3. **Synergy, not replacement** - Claude plans, Gemini builds, Codex engineers, Perplexity researches
4. **Profit first** - All business operations checked against Profit Maximizer principles
5. **Save tokens** - Lite mode for quick questions, full mode for big decisions
6. **Zero toxic losses** - Bot guardrails (circuit breaker, sentiment gate, HTF filter) are non-negotiable

## Data Flow Architecture (3-Lane Model)

All production data flows through Supabase. Local dashboards are ops/dev tools.

| Lane | Purpose | Stack | Data Flow |
|------|---------|-------|-----------|
| LOCAL OPS | Private internal dashboard, dev/test | Django 8504 | Reads/writes Supabase |
| SUPABASE | Source of truth for all production data | PostgreSQL + Edge Functions | Both lanes read/write |
| LOVABLE | Public customer-facing site | React on everlightventures.io | Reads from Supabase only |

### Agent Data Rules
- Production state MUST be written to Supabase, not local-only files
- Django apps read/write Supabase via `hive_dashboard/supabase_client.py`
- Lovable reads Supabase only -- never writes to local
- After modifying game/business/broker state, ALWAYS push to Supabase
- Supabase migrations go in `supabase/migrations/` with timestamp prefixes
- Edge functions go in `supabase/functions/`
- NEVER hardcode Supabase URLs -- use env vars or the shared client module

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
