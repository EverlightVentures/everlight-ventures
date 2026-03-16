# EVERLIGHT VENTURES - MASTER DISASTER RECOVERY DOCUMENT

**Generated:** 2026-03-11 (PT)
**System:** Ubuntu 25.10 (aarch64) | Python 3.13.7 | Node v20.19.4
**Workspace Root:** `/mnt/sdcard/AA_MY_DRIVE` (33GB used / 460GB total)
**Git Remote:** `https://github.com/EverlightVentures/everlight-ventures.git`

---

## LIVE SYSTEMS (What Must Be Running)

| Service | Location | Port | Auto-Start |
|---------|----------|------|------------|
| XLM Trading Bot | Oracle Cloud (163.192.19.196) | 8502 (tunneled) | Docker restart:always |
| Bot Dashboard | Oracle Cloud (tunneled) | 8502 | Docker restart:always |
| BlinkoLite Knowledge Base | Local (PRoot) | 1111 | Cron + watchdog (15s) |
| Hive Dashboard (Django) | Local | 8503/8504 | Manual (`hdx` alias) |
| Oracle SSH Tunnel | Local | 8502 | Cron (2min check) |

---

## CREDENTIALS & SECRETS (Not in Git)

All secrets live in `/mnt/sdcard/AA_MY_DRIVE/.env` -- regenerate from provider dashboards if lost:

| Provider | Dashboard URL | What to Regenerate |
|----------|--------------|-------------------|
| Coinbase | coinbase.com/settings/api | API key + secret |
| Stripe | dashboard.stripe.com/apikeys | Secret key, webhook secret, publishable key |
| Supabase | supabase.com/dashboard | Anon key, service key |
| Anthropic | console.anthropic.com | API key |
| ElevenLabs | elevenlabs.io/settings | API key + voice IDs |
| OpenAI | platform.openai.com/api-keys | API key |
| Google Cloud | console.cloud.google.com | Credentials JSON |
| GitHub | github.com/settings/tokens | PAT token |

### Supabase (From Memory - Always Available)
```
Ref ID: jdqqmsmwmbsnlnstyavl
Region: East US (North Virginia)
Access Token: sbp_48538dbc9cdfd7dd49f9bb8e14a336f60790afcd
```

### Oracle Cloud Instance
```
IP: 163.192.19.196
Region: us-sanjose-1
User: opc
SSH key: /root/.ssh/oracle_key.pem
Architecture: ARM64 free tier
```

---

## DIRECTORY STRUCTURE

```
AA_MY_DRIVE/
|-- 01_BUSINESSES/Everlight_Ventures/    Parent brand + all sub-businesses
|   |-- 00_Core/                         Brand guidelines, SOPs
|   |-- 02_Operations/                   Finance, payroll, Slack
|   |-- 03_Content/                      Drafts, published, avatar assets
|   |-- Alley_Kingz/                     PvP mobile game (HTML5 + Unity)
|   |-- Everlight_Crypto/                BCARDI token, Zilliqa
|   |-- Everlight_Foundations/            Logos, brand docs, site copy
|   |-- Everlight_Literature/             Sam & Robo, Beyond the Veil, TSW
|   |-- Everlight_Logistics/              Shipping & fulfillment
|   |-- Last_Light_Protocol/              Gaming clan
|   |-- Personal_Training/                Fitness coaching
|   +-- trading/                          Strategies & research
|
|-- 02_CONTENT_FACTORY/                  Content pipeline
|   |-- 00_Inbox/ -> 01_Queue/ -> 02_Published/
|   |-- 03_Assets/                       Brand kits, templates
|   +-- AI_Workteams/                    Session outputs
|
|-- 03_AUTOMATION_CORE/                  Scripts & automation
|   |-- 01_Scripts/ai_workers/           Hive dispatch, bridge, delegates
|   |-- 02_Config/                       YAML configs
|   +-- 03_Credentials/                  GPG vault
|
|-- 06_DEVELOPMENT/                      Active projects
|   |-- everlight_os/                    OS core + hive_mind + blinko
|   |-- xlm_bot/                         Trading bot (LIVE on Oracle)
|   +-- hivemind_saas/                   Hive Mind SaaS product
|
|-- 08_BACKUPS/                          Archives, dumps, Takeout
|-- 09_DASHBOARD/                        Django + Streamlit + FastAPI
|   |-- hive_dashboard/                  War room browser + task mgmt
|   +-- aa_dashboard/                    File browser
|
|-- _logs/                               System logs
|   |-- ai_war_room/                     94+ war room session reports
|   |-- hive.db                          475 MB session database
|   |-- blinko_lite.db                   Knowledge base (RAG)
|   +-- hive_sessions.jsonl              Event log
|
|-- .claude/                             Claude agent configs
|   |-- agents/ (38 agents)
|   |-- modes/ (plan, execute, review)
|   |-- hooks/ (pre_tool_guard, log_tool_use)
|   +-- skills/ (3 skills)
+-- .gemini/                             Gemini agent configs
```

---

## HIVE MIND ARCHITECTURE (4 AI Managers, 32+ Employees)

### The Quad
| Manager | Role | Timeout | Employees |
|---------|------|---------|-----------|
| **Claude** | Chief Operator / Strategist | Orchestrator | 8 (chief_operator, architect, qa_gate, etc.) |
| **Gemini** | Logistics Commander / Executor | 300s | 8 (ops_deputy, workflow_builder, etc.) |
| **Codex** | Engineering Foreman / Profit Maximizer | 240s | 8 (saas_builder, funnel_architect, etc.) |
| **Perplexity** | Intelligence Anchor / News Desk | 90s | 8 research beats |

### Execution Flow
```
User Prompt
    |
Phase 0: BlinkoLite RAG query (prior knowledge)
    |
Phase 1: Perplexity intel scout (real-time news)
    |
Phase 2: Router classifies -> picks managers
    |
Phase 3: Gemini + Codex run in parallel
    |
Phase 4: Convergence -> war room reports
    |
Phase 5: Auto-ingest to BlinkoLite
    |
Claude reads, synthesizes, executes
```

### Routing Rules
| Category | Managers | Keywords |
|----------|----------|----------|
| Trading | Gemini, Codex, Perplexity | trade, xlm, bot, scalp, pnl |
| Content | Gemini, Codex, Perplexity | write, blog, post, publish |
| Engineering | Gemini, Codex, Perplexity | fix, bug, code, deploy |
| Business | Gemini, Codex, Perplexity | saas, revenue, launch |
| Research | Perplexity, Gemini | news, price, market |
| Operations | Gemini, Perplexity | sync, automate, workflow |

### Key Files
```
Dispatcher:    06_DEVELOPMENT/everlight_os/hive_mind/dispatcher.py (342 lines)
Convergence:   06_DEVELOPMENT/everlight_os/hive_mind/convergence.py (362 lines)
Roster:        06_DEVELOPMENT/everlight_os/hive_mind/roster.yaml (119 lines)
Config:        06_DEVELOPMENT/everlight_os/configs/everlight.yaml (204 lines)
CLI:           03_AUTOMATION_CORE/01_Scripts/ai_workers/hive_cmd.py
```

---

## XLM BOT ARCHITECTURE (LIVE ON ORACLE)

### Core Config
```yaml
symbol: XLM-PERP
product_id: XLP-20DEC30-CDE
leverage: 4
paper: false
data_product_id: XLM-USD
timezone: America/Los_Angeles
```

### Margin Hours (CRITICAL)
```
Intraday:  5AM-1PM PT (8AM-4PM ET) = 8h lower margin
Overnight: 1PM-5PM PT (4PM-8AM ET) = 16h higher margin
Internal: UTC. Display: PT. Margin calc: ET.
NEVER use hardcoded timedelta(hours=-8)
```

### Circuit Breakers
```
Single trade max loss: $15
Max hold time: 4 hours
Hard daily drawdown cap: $35 (non-overrideable)
Tier 1: 4 losses / $20 DD -> pause 30 min
Tier 2: 6 losses / $35 DD -> close all + halt
Tier 3: 8 losses / $50 DD -> stop, manual restart only
```

### AI Executive Mode
- claude_advisor.py + prompts.py
- Opus as decision engine (ENTER_LONG, ENTER_SHORT, EXIT, HOLD, FLAT)
- Fire-and-forget: bot never blocks waiting for Claude
- Results cached in data/ai_insight.json (read on next cycle)
- Trade decisions auto-ingested to BlinkoLite for permanent memory

### Process Architecture
```
xon starts: xpb (bot), xdr (dashboard), xws (WS feed)
xpb-guardian keeps xpb-fg alive (12s checks)
Bot is NOT long-running: each main.py = one 3-5s cycle
```

---

## BLINKO KNOWLEDGE BASE

### Architecture
- BlinkoLite: Python-native RAG server (SQLite FTS5)
- Port: 1111
- DB: _logs/blinko_lite.db
- Watchdog: 15s health checks, auto-restart, max 10 restarts/hr

### Control
```bash
bk start        # Start server + watchdog
bk stop          # Kill everything
bk restart       # Stop + start
bk status        # Health check
bk logs          # Tail logs
bk stats         # Note count, DB size, uptime
bk query "text"  # RAG search
bk ingest        # Backfill war room + memory files
bk watch         # Auto-ingest daemon (60s)
```

### Integration Points (Automatic)
1. convergence.py auto-ingests war room sessions after every hive dispatch
2. claude_advisor.py auto-logs trade decisions after every closed trade
3. dispatcher.py auto-queries BlinkoLite for prior knowledge before routing (Phase 0)

### Key Files
```
Server:    06_DEVELOPMENT/everlight_os/blinko/blinko_lite.py
Watchdog:  06_DEVELOPMENT/everlight_os/blinko/blinko_watchdog.sh
Control:   06_DEVELOPMENT/everlight_os/blinko/bk
Bridge:    03_AUTOMATION_CORE/01_Scripts/ai_workers/blinko_bridge.py
Context:   03_AUTOMATION_CORE/01_Scripts/ai_workers/blinko_context.py
```

---

## ORACLE CLOUD SELF-HEALING

### Watchdog FSM
```
State 1: RUNNING + SSH OK -> healthy, do nothing
State 2: RUNNING + SSH fail x3 -> SOFTRESET (3 min)
State 3: Still failing -> HARD RESET (5 min)
State 4: Still failing -> Slack alert + stop
State 5: STOPPING stuck -> HARD RESET immediately
State 6: STOPPED -> START immediately
Max 3 hard resets per 6-hour window
```

### SSH Config
```
Host oracle
  HostName 163.192.19.196
  User opc
  IdentityFile /root/.ssh/oracle_key.pem
  GSSAPIAuthentication no
  AddressFamily inet
  PreferredAuthentications publickey
  KexAlgorithms curve25519-sha256
  Ciphers aes128-ctr
```

---

## REVENUE STREAMS (Target: $10k/mo)

| Product | Model | Price |
|---------|-------|-------|
| Onyx POS | SaaS | $49/mo |
| Hive Mind | Tiered SaaS | $29-149/mo |
| Publishing | KDP + direct | Per book |
| Alley Kingz | IAP + VIP | $4.99/mo VIP |
| HIM Loadout | Affiliate | Commission |
| Everlight Logistics | Service | Per contract |
| XLM Bot | Future SaaS | TBD |

### Stripe Integration
```
Django app: payments/ (Customer, Subscription, Order models)
Webhook: processes charge.succeeded, subscription events, invoices
Notifications: Slack via signals
```

---

## PUBLIC SITE

- **Domain:** everlightventures.io (Namecheap -> Lovable)
- **7 tabs:** / (brand), /him-loadout, /logistics, /publishing, /alley-kingz, /onyx, /hivemind
- **Affiliate app:** him-gear-drop.lovable.app
- **Supabase tables:** ebook_purchases, download_tokens, arcade_*, stripe_events, player_accounts
- **Edge functions:** create-checkout, verify purchases, stripe-webhook, send-purchase-email

---

## ESSENTIAL ALIASES (Add to .zshrc on new device)

```bash
# Navigation
export EL_HOME=/mnt/sdcard/AA_MY_DRIVE
alias cdw='cd $EL_HOME'
alias ev='cd $EL_HOME/01_BUSINESSES/Everlight_Ventures'
alias dev='cd $EL_HOME/06_DEVELOPMENT'

# Hive Mind
alias hive='python3 $EL_HOME/03_AUTOMATION_CORE/01_Scripts/ai_workers/hive_cmd.py'
alias hdx='cd $EL_HOME/09_DASHBOARD/hive_dashboard && pkill -f "manage.py runserver.*8504" 2>/dev/null; sleep 0.5; python3 manage.py import_sessions 2>&1 && python3 manage.py runserver 0.0.0.0:8504'

# BlinkoLite
alias bk='$EL_HOME/06_DEVELOPMENT/everlight_os/blinko/bk'

# XLM Bot
alias rdx="bash $EL_HOME/xlm_bot/rdx.sh"
alias rxl="bash $EL_HOME/xlm_bot/rxl.sh"

# AI Workers
alias ai='python3 $EL_HOME/03_AUTOMATION_CORE/01_Scripts/ai_workers/ai_terminal.py'
alias ppx='python3 $EL_HOME/03_AUTOMATION_CORE/01_Scripts/ai_workers/ppx_terminal.py'
alias ask='python3 $EL_HOME/03_AUTOMATION_CORE/01_Scripts/ai_workers/ask_router.py'

# Proton Drive backup
alias sync-proton='rclone sync $EL_HOME protondrive:AA_MY_DRIVE --progress --exclude ".claude/**" --exclude "_logs/**"'
```

---

## CRONTAB (Restore on New Device)

```
@reboot cd /mnt/sdcard/AA_MY_DRIVE/xlm_bot && /bin/bash ./xpb-shortbias >> logs/xpb_boot.log 2>&1
@reboot cd /mnt/sdcard/AA_MY_DRIVE/xlm_bot && /bin/bash ./xdr >> logs/xdr_boot.log 2>&1
@reboot nohup bash /mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/blinko/blinko_watchdog.sh >> _logs/blinko_watchdog.log 2>&1 &
```

---

## SYSTEM DEPENDENCIES (Install on Fresh Ubuntu)

```bash
# Python 3.13+
apt install python3 python3-pip

# Key Python packages
pip install django django-extensions django-htmx
pip install aiohttp httpx pandas
pip install cryptography bcrypt
pip install beautifulsoup4 lxml
pip install gitpython pyyaml

# Node.js 20+
apt install nodejs npm
npm install -g @anthropic-ai/claude-code prettier

# System tools
apt install postgresql-client sqlite3 git tmux rclone
```

---

## DATABASES

| Database | Path | Size | Purpose |
|----------|------|------|---------|
| hive.db | _logs/hive.db | 475 MB | All hive sessions + agent responses |
| blinko_lite.db | _logs/blinko_lite.db | 4.8 MB | BlinkoLite RAG knowledge base (439 notes) |
| django.sqlite3 | 09_DASHBOARD/hive_dashboard/db.sqlite3 | ~10 MB | Django ORM (agents, tasks, payments) |
| bot_state.db | xlm_bot/data/bot_state.db | ~1 MB | XLM bot position state |
| Supabase (cloud) | jdqqmsmwmbsnlnstyavl | Cloud | Ebook/arcade purchases, Stripe events |

---

## RECOVERY CHECKLIST

```
[ ] 1. Clone repo: git clone https://github.com/EverlightVentures/everlight-ventures.git
[ ] 2. Restore .env from provider dashboards (Coinbase, Stripe, Supabase, etc.)
[ ] 3. Restore SSH key: /root/.ssh/oracle_key.pem (from backup)
[ ] 4. Install system dependencies (see above)
[ ] 5. Restore crontab entries (see above)
[ ] 6. Copy .zshrc aliases (see above)
[ ] 7. Verify Oracle Cloud VM is running: ssh oracle "docker ps"
[ ] 8. Start BlinkoLite: bk start
[ ] 9. Backfill BlinkoLite: bk ingest
[ ] 10. Start Hive Dashboard: hdx
[ ] 11. Test hive dispatch: hive "test query"
[ ] 12. Verify Proton Drive sync: proton-test
[ ] 13. Check disk space: df -h /mnt/sdcard
```

---

**5 years of development. 40+ AI agents. 6 revenue streams. One workspace.**
**Keep this file safe. Email it. Print it. Back it up everywhere.**
