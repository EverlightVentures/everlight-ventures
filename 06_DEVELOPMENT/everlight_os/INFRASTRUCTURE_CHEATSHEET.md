# EVERLIGHT VENTURES — INFRASTRUCTURE CHEAT SHEET

> **The fail-proof reference.** If any device or instance goes down, everything
> needed to rebuild or reconnect is here. Lives in the git repo → on GitHub.
> Last rebuilt: 2026-05-14 (the .250 → e5-mother migration).

---

## 1. THE FAMILY — 4 devices, one system

| Member | Role | Tailnet IP | Public / Other | Status |
|--------|------|-----------|----------------|--------|
| **e5-mother** | Oracle hub — always-on, 24/7, runs the stack | `100.125.115.95` | `163.192.60.35` (public) | ONLINE — new, 2026-05-14 |
| **acemagician-pc** | Powerful #2 — heavy compute, can't run 24/7 (power) | `100.93.253.49` | — | ONLINE |
| **richards-z-fold7** | Phone — workstation, where edits originate | `100.112.180.29` | — | tailscaled stale, needs kick |
| **mgn-latitude-e7240** | Dell laptop — spare/thin client | `100.120.23.23` | — | OFFLINE (last seen 9d) |

**Priority order (hosting role):** e5-mother #1 → acemagician-pc #2 → phone #3.
**Sync flow:** phone edit → GitHub → Oracle (e5-mother) → PC. GitHub is the bus.
**Connectivity:** Tailscale mesh. Goal: every service tailnet-only, public surface = SSH only.

---

## 2. ORACLE CLOUD — the e5-mother instance

| Item | Value |
|------|-------|
| Instance name | `e5-mother` |
| Instance OCID | `ocid1.instance.oc1.us-sanjose-1.anzwuljrwtpnzgacztxdo45gi6hupzd67gumuqy7g33uycc5fad7al3wy6ra` |
| Shape | VM.Standard.A1.Flex — 4 OCPU / 24 GB RAM (the **Always Free** allotment — $0) |
| OS | Ubuntu 22.04.5 LTS, aarch64 |
| Boot disk | 50 GB (49 GB usable, 43 GB free) |
| Public IP | `163.192.60.35` |
| Tailnet IP | `100.125.115.95` |
| SSH | `ssh -i /root/.ssh/github_deploy -p 22 ubuntu@163.192.60.35` (port 22 for now; hardening to 2222 later) |
| Region / AD | `us-sanjose-1` / `kNfe:US-SANJOSE-1-AD-1` |
| Compartment | `ev-box` (`ocid1.compartment.oc1..aaaaaaaalhtovyf6lyn3xppwmdfjkfssf7vf56zahmp2xdc5hv4gay3vtv2a`) |
| VCN subnet | `ocid1.subnet.oc1.us-sanjose-1.aaaaaaaa7gg2a526yyx3iqdgr7wyfth7w2e675qmyeixiavm6rcmkttq26xq` |
| Ubuntu image | `ocid1.image.oc1.us-sanjose-1.aaaaaaaae5nqxnx7734mvbzkt3pctumjdb525h2mpzxqxyh3pfmw2iqdsqqq` |

### Other Oracle resources
| Item | Value | Notes |
|------|-------|-------|
| Oracle Micro (xlm-bot host) | public `163.192.19.196`, hostname `xlm-bot` | E2.1.Micro, runs xlm-bot only |
| Dead E5 ".250" | was `129.159.38.250` | TERMINATED 2026-04-30 (was paid shape) |
| **Orphan boot volume** | `ocid1.bootvolume.oc1.us-sanjose-1.abzwuljrzmlkhudjg2iauamz6zr4mhrygp6kmxurur4d7wrh73qrfvlmg3oq` | `xlm-bot-core-e5-2c16g`, 47 GB, AVAILABLE — **the cold backup of all E5 data**. Do not delete. |
| OCI CLI auth | `/root/.oci/config` on phone | user/tenancy/fingerprint + `oci_api_key.pem` |
| Account | Pay-As-You-Go (card on file 2026-05-14) — but 4/24 A1 stays $0 (Always Free tier) |

---

## 3. EXTERNAL SERVICES — every key, what it's for

> Keys live in the recovered `.env` — on **e5-mother: `/home/ubuntu/e5_data/.env`**
> (83 lines, all production keys). Also in the PC canonical tree under
> `_oracle_e5_recovery/`. **Rotate anything that may have been exposed.**

| Service | Env var(s) | Purpose |
|---------|-----------|---------|
| Anthropic (Claude) | `ANTHROPIC_API_KEY` | Hive Mind, all Claude calls |
| OpenAI | `OPENAI_API_KEY` | Codex / GPT cross-checks |
| Google Gemini | `GEMINI_API_KEY` | alternate-perspective checks |
| Resend | `RESEND_API_KEY`, `SMTP_PASS` | all outbound email (branded_mailer) |
| Stripe | `STRIPE_SECRET_KEY` | payments — Onyx POS, Broker OS fees |
| Supabase | `SUPABASE_ACCESS_TOKEN` | deal pipeline DB — `https://jdqqmsmwmbsnlnstyavl.supabase.co` |
| Slack | `SLACK_BOT_TOKEN`, `SLACK_ALERTS_CH` | Hive comms, `#hive-alerts` |
| Langfuse | `LANGFUSE_HOST/PUBLIC_KEY/SECRET_KEY` | LLM observability (runs on PC) |
| Google Maps | `GOOGLE_MAPS_API_KEY` | property geo / wholesale |
| Google Docs/Drive | `google_tokens.json` in e5_data | 3-format report publishing |
| Twilio | **NOT in recovered .env** — operator mentioned it; locate or confirm retired | voice / SMS |
| Cloudflare | via `cloudflared.service` | tunnel + `everlightventures.io` Pages |

---

## 4. SERVICE MAP — what runs (113 systemd units recovered from old E5)

### Wholesale pipeline (the revenue engine — "where we left off")
`broker-orch-full/match/outreach/scout` (+timers) · `wholesale-day` · `wholesale-outreach` · `wholesale-pipeline` · `buybox-reply-router` · `cuyahoga-scrape` (Cleveland county) · `deal-closeout-tracker` · `sync-deals` · `inbound-watch` · `rex-belfort` · `rex-negotiator` · `rex-recycler`

### Hive core
`hive-action-engine` · `hive-dashboard` · `hive-directory` · `hive-django` · `hive-health` · `hive-reports` · `hive-self-healer` · `hive-slack-agent` · `hive-sync` · `hive-task-runner` · `hive-voice` · `claude-chat-bridge`

### MCP fleet (the 24/7 target)
`mcp-blinko-proxy` · `mcp-dispatcher-relay` · `mcp-market-intel-proxy` · `mcp-n8n-proxy` · `mcp-resend-proxy` · `mcp-stripe-proxy` · `mcp-supabase-proxy`

### Knowledge / RAG
`blinko` · `langfuse` · `ollama`

### Briefs & pulse
`ceo-brief` · `morning-brief` · `hourly-pulse`

### XLM trading (stays on Oracle Micro, not e5-mother)
`xlm-bot` · `xlm-ws` · `xlm-dash-react` · `xlm-liqfeed` · `xlm-watchtower`

### Other business units
`onyx-pos` + `onyx-pos-ui` (POS SaaS) · `polymarket` · `stark-ai` · `vantaris` · `wealth-intel` · `triple-threat`

### Infra / glue
`cloudflared` · `n8n` (parked) · `nextcloud` · `nightly-backup` · `gmail-organizer` · `port80-forward` · `computer-use`

> Full unit files preserved: `e5-mother:/home/ubuntu/e5_data/_systemd_units/`
> Source code preserved: `e5-mother:/home/ubuntu/e5_data/` (3.8 GB — content_tools,
> hive_*, broker_*, wholesale_*, all of it)

---

## 5. IF DISASTER STRIKES — recovery pointers

| If you lose... | Recover from... |
|----------------|-----------------|
| e5-mother instance | Orphan boot volume `xlm-bot-core-e5-2c16g` (attach to new instance, mount, rsync). Or `_oracle_e5_recovery/` in the workspace. |
| The phone | PC canonical tree `/AA_MY_DRIVE` + GitHub. Phone is workstation, not sole-source. |
| The PC | Phone workspace + GitHub + e5-mother. |
| All API keys | `/home/ubuntu/e5_data/.env` on e5-mother, mirrored in `_oracle_e5_recovery/` |
| Workspace history | GitHub repo (`git@github.com:EverlightVentures/...`) |
| Context / decisions | `/root/.claude/projects/.../memory/` (181 memory files) + `_state/AGENT_MAILBOX.md` |

### Key scripts
- `03_AUTOMATION_CORE/01_Scripts/e5_mother/` — provisioning kit
- `03_AUTOMATION_CORE/01_Scripts/claude_sync_acemagician.sh` — phone↔PC sync
- `03_AUTOMATION_CORE/01_Scripts/network_sync/sync_on_reconnect.sh` — multi-peer sync
- `08_BACKUPS/recovery_log.md` — full recovery history
- `_state/AGENT_MAILBOX.md` — live coordination between Claude sessions

---

## 6. STILL TO DO (post-migration verification)

- [ ] Provision the hive stack on e5-mother from `/home/ubuntu/e5_data/` + systemd units
- [ ] MCP fleet running 24/7 on e5-mother (the 7 mcp-*-proxy services)
- [ ] Smoke-test wholesale pipeline (TN + all) — Resend, broker-orch, cuyahoga-scrape
- [ ] Verify Supabase / Tailscale / Twilio / Stripe / Slack connectivity end-to-end
- [ ] VCN lockdown — close public ports, SSH-only (PC session's lane)
- [ ] Mirror credentials to PC, confirm 3-way sync
- [ ] Kick phone tailscaled (showing offline despite being active)
- [ ] Commit this + everything to GitHub

---

## 7. WHAT GOES WHERE — the architecture clarity (added 2026-05-15)

### Why each node exists (in one sentence each)

- **Oracle e5-mother** — for things that MUST run 24/7 when phone + PC are off:
  webhook endpoints for customer purchases, scheduled wholesale jobs, the
  persistent memory layer (Blinko), the agent dispatch brain.
- **AceMagician PC** — heavy local compute + dashboards YOU look at + hot
  backup of Oracle's state. Not 24/7 (power cost). Powerful when on.
- **Phone** — workstation. Where you EDIT, where Claude Code runs interactively,
  source of truth for the workspace files.
- **Dell laptop** — spare / thin client. Almost everything pulls from the others.

### Public vs Private surface (the security model)

**Customer-facing / external (PUBLIC):**
- `everlightventures.io` — Cloudflare Pages (static site, always-on, free)
- Stripe webhook → reaches e5-mother (purchases get processed)
- Twilio webhook → reaches e5-mother (SMS/voice replies)
- Resend inbound → reaches e5-mother (email replies)
- GitHub webhook → triggers deploys
- SSH:22 on e5-mother — operator break-glass

**Everything else is PRIVATE (tailnet-only):**
- Blinko (1111) — only your bots query it. Tailnet-only by Ubuntu iptables default.
- All hive dashboards (8504, 8080, etc.) — operator-only, tailnet-only.
- All MCP proxies (3101-3107) — agent-only, tailnet-only.
- Langfuse, n8n, BlinkoLite UI — tailnet-only.

### Where data lives (source of truth per data type)

| Data | SOT lives on | Why |
|------|--------------|-----|
| Workspace files (code, scripts, docs) | Phone sdcard | You edit there |
| Memory / RAG (Blinko notes) | e5-mother | Always-on, queried by agents |
| Deal pipeline (broker_ops, leads) | Supabase cloud | Always available, eventually-consistent |
| XLM bot state | Oracle Micro | Already there, stable |
| Customer payments | Stripe + Supabase | Stripe = source, Supabase = record |
| Agent firmware / Claude memory | `.claude/projects/*/memory/` | synced across phone/PC |

### "What can stay local" answer

**Stays LOCAL (no Oracle copy needed):**
- Your Claude Code sessions, your terminal, your editor
- Langfuse (PC) — you use it to debug, no agents need it 24/7
- Homarr (PC) — your personal dashboard
- Ollama on PC — if you run local LLMs
- Fight Camp OS — personal stuff
- 04_MEDIA_LIBRARY, A_Rich, 05_PERSONAL — your files

**MUST be on Oracle (24/7):**
- Blinko (memory)
- The wholesale orchestrators (broker-orch-*, cuyahoga-scrape, wholesale-*)
- Stripe webhook handler (customer purchases)
- Resend inbound handler (email replies)
- The MCP fleet (so agents can call them anytime)
- hive-self-healer, hive-health (keep the box honest)
- ceo-brief, morning-brief, hourly-pulse (scheduled jobs)

**Cloud (already always-on, no work needed):**
- everlightventures.io (Cloudflare Pages)
- Supabase (deal pipeline DB)
- GitHub (code, immortal layer)

---

## 8. SUBSCRIPTIONS — what you're paying for (best inventory 2026-05-15)

> Based on what's in the recovered `.env` + what we know is wired up. Operator should
> spot-check billing dashboards for each — I can see API keys, not payment status.

### Pay-as-you-go (per-request, no monthly minimum)
| Service | What it does | Typical cost |
|---------|--------------|--------------|
| Anthropic (Claude) | The Hive's primary brain | $3–15 per million tokens |
| OpenAI | Cross-check / GPT alternates | $1.50–15 per million tokens |
| Google Gemini | Alternate perspectives | free tier 60 RPM, then per-token |
| Stripe | Payment processing | 2.9% + $0.30 per transaction |
| Twilio | SMS / voice (NOT in recovered .env — verify) | per-message ($0.0075 SMS US) |
| Google Maps | Geocoding for wholesale | free tier 28k/mo, then $5/1k |

### Free tier (no card needed)
| Service | Free limit | Currently using |
|---------|------------|-----------------|
| Resend (email) | 3,000/mo, 100/day | Yes — branded_mailer + resend_budget gate |
| Supabase | 500MB DB, 50k MAU | Yes — deal pipeline |
| Cloudflare Pages | Unlimited static | Yes — everlightventures.io |
| Cloudflare Tunnel | Free | Set up, unclear if active |
| GitHub (public) | Free | Yes — EverlightVentures org |
| Oracle Cloud Free Tier | 4 OCPU + 24GB A1.Flex | Yes — e5-mother (this is HUGE value) |
| ImprovMX | 42 email addresses | Yes — @everlightventures.io aliases |
| Slack | Workspace free tier | Yes — 13 channels |

### Self-hosted (free, runs on YOUR boxes)
| Service | Runs on | Replaces what |
|---------|---------|---------------|
| BlinkoLite | e5-mother :1111 | Notion / cloud RAG |
| Langfuse | PC :3100 | LangSmith / Phoenix paid tiers |
| n8n | e5-mother (parked) | Zapier / Make.com |
| Ollama | PC | OpenAI for low-stakes calls |
| Local Postgres (potential) | PC or e5-mother | Supabase for dev |

### Things to verify in your billing (not from API keys)
- [ ] Anthropic — pay-as-you-go balance / credit remaining
- [ ] OpenAI — same
- [ ] Stripe — payouts, fees, currently in test or live mode
- [ ] Twilio — credit balance, phone numbers rented (monthly $1/number)
- [ ] Google Cloud — billing alerts set?
- [ ] Oracle Cloud — now PAYG on file, but 4/24 A1 stays free

### What you're NOT paying for (worth knowing)
- No SaaS like Notion / Airtable / Linear / monday — built into the Hive
- No paid analytics — Langfuse is self-hosted free
- No paid CDN beyond Cloudflare's free tier
- No paid CI/CD — GitHub Actions free tier

### What could replace paid subs with self-host
| Today | Self-host alternative | Trade-off |
|-------|----------------------|-----------|
| Anthropic API (low-stakes calls) | Ollama on PC (llama 3.x) | Worse quality, no cost |
| Supabase | Self-hosted Postgres + Studio | More ops work; lose cloud uptime |
| Resend | Postfix on Oracle | Reliability hit, IP reputation work |
| Slack | Matrix / Element | Lose Slack ecosystem |
| Stripe | NOT replaceable for payments |

---

## 9. THE MEMORY AWARENESS SERVICE (added 2026-05-15)

`03_AUTOMATION_CORE/01_Scripts/blinko_status.py` — any agent or script can call
this to know its memory state in 3 seconds.

**States it reports:**
- `CONNECTED` — Blinko reachable on e5-mother, full live memory
- `DEGRADED` — fallback to local `blinko_lite.db` (still has 3,711 notes,
  marked with last-sync timestamp so agents know what they're missing)
- `OFFLINE` — no remote AND no local copy, agents announce no persistent memory

**Local fallback DB locations (in priority order):**
1. `/mnt/sdcard/AA_MY_DRIVE/_state/blinko_lite.db` — phone canonical (synced from e5-mother)
2. `/mnt/sdcard/AA_MY_DRIVE/_logs/blinko_lite.db` — legacy phone copy
3. `/home/ubuntu/e5_data/blinko_lite.db` — on e5-mother itself
4. `/home/richgee/AA_MY_DRIVE/_state/blinko_lite.db` — PC

**Usage:**
```bash
python3 blinko_status.py                       # human-readable
python3 blinko_status.py -m banner --agent X   # agent startup announcement
python3 blinko_status.py -m json               # for scripts
python3 blinko_status.py -m short              # for status lines
```

**Exit codes:** 0=connected, 1=degraded, 2=offline, 3=error. Agents can branch
on these.

**Resilience model:**
- Primary: Blinko on e5-mother (always-on)
- Hot backup: `blinko_lite.db` synced to phone (~8MB, just copied 2026-05-15)
- Cold backup: same .db on PC (synced when PC comes online)
- Immortal: commit the .db to GitHub for true offline recovery
