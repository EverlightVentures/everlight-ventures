# Intel Center · Master End-to-End Audit
**Date:** 2026-05-12 · **Operator:** Rich Gee (CEO) · **AI CEO:** Lucrex

---

## What works (verified live this session)

| Layer | Status | Evidence |
|---|---|---|
| OSINT investigation (15 investigators) | ✓ | `intel investigate` returns in 25-40s with structured findings |
| Agent voice extraction | ✓ | Marquise's "Hey Rich, hope y'all are doing well" pulled from his `.md` firmware |
| Pipeline (5 stages) | ✓ | Profile → Resonance → Strategy → Narrative → Routing all chained |
| State-specific routing | ✓ | TN routed to `marquise_reed_acquisitions`, CA to Piper, OH/AZ to Rex |
| `phrase_scrub` compliance gate | ✓ | Caught "listing" + "MLS" + "no agents" three times before allowing send |
| Branded HTML report | ✓ | TLDR + Profile Depth + Pitch Package + per-state legal panel |
| `branded_mailer` Resend send | ✓ | Email sent, message_id `85c590b5-4166-4a99-9c32-0cf4d56d1ad9` |
| Branded Slack notification | ✓ | Posted to #war-room ts `1778619178.994449` |
| Google Doc preview | ✓ | HTML rendered at `http://127.0.0.1:2200/reports/outreach_preview_*.html` |

## Gaps still on the board (prioritized)

### P0 — Pipeline-blocking
- **MCP servers not running on phone.** Voice/Marcus/Cipher/Justine etc. are all firmware files that the orchestrator reads SYNCHRONOUSLY, but the *long-running* MCP servers (broker-os, blinko-memory, market-intel, Slack, Gmail, Calendar) only run on Oracle. When Oracle is down, the agents lose their tool layer. **Fix: see MCP failover doctrine below.**

### P1 — Per-agent voice still partial
- **Only `marquise_reed_acquisitions` and `31_outreach_agent` have rich `**Speech style:**` blocks** that voice_extractor can parse. The other 90+ agent firmware files have personality but in a different format. The voice_extractor falls back to default_voice() for them.
  - **Fix:** standardize the firmware schema across all agents, OR make voice_extractor parse 2-3 alternate formats (`## Voice + Personality` section, free-text personality block).

### P2 — n8n is dead but referenced
- `publish_gdoc` first tries 4 n8n webhooks (all `unreachable`) before falling back to direct Google Docs. Each attempt is a 3-5s timeout — so every send has a ~15s delay before the GDoc renders.
  - **Fix:** set `GDOCS_DISABLE_N8N=1` permanently (already done on Oracle, but not exported in the phone shell). Will save 12-15s per send.

### P3 — Pitch templates have hidden phrase_scrub mines
- I caught and patched 3 today. Likely 5-10 more lurking in `marketing_pipeline.POSITIONING_ANGLES` and `pitch_narrative.BODY_TEMPLATES`.
  - **Fix:** lint the templates against `pre_send_phrase_scrub._DEFAULT_BASELINE` at module load time. Refuse to start the API if any template has a forbidden phrase.

### P4 — Profile depth still bare for the operator
- Rich's profile shows 11/100. Not enough public-source coverage to generate a *truly* personalized pitch. The send today was generic-Memphis voice with no Rich-specific signals.
  - **Fix:** more lead-context inputs (phone, past addresses, business name, LinkedIn URL). Even one specific signal lifts depth dramatically.

## MCP failover doctrine (NEW)

**Problem:** Phone is the SOT but offline-prone. AceMagician is heavy but cron-friendly. Dell PC is intermittent. Oracle Micro hosts only the XLM bot. We need the MCP servers running SOMEWHERE always.

**Election order** (per Rich's guidance):
1. **Phone (Termux + proot)** — preferred when on, lowest latency to operator
2. **AceMagician** (Arch Linux, tailnet `100.93.253.49`) — fallback when phone is off
3. **Dell PC** — last resort

**Mechanism (to deploy on each node):**
- A `mcp_elect.sh` cron job runs every 2 min on each node
- Each node checks (via tailnet ping) if the higher-priority node is reachable
- If yes → ensure local MCP servers are STOPPED
- If no → ensure local MCP servers are RUNNING (start the 7-server fleet from `mcp_servers/start_all.sh`)
- All 3 nodes also write a heartbeat to `/var/lib/mcp_election/<node>.ts` synced via Tailscale

**Failover ports** (same on every node):
- 3101: broker-os MCP
- 3102: blinko-memory MCP
- 3103: market-intel MCP
- 3104: Slack MCP
- 3105: Gmail MCP
- 3106: Calendar MCP
- 3107: hive-orchestrator MCP

**Operator deploys:** `bash 03_AUTOMATION_CORE/01_Scripts/mcp_failover/install.sh` on each node (phone Termux, AceMagician via SSH, Dell when next online).

## Live test (just executed -- this turn)

- **Investigation:** `rich_gee_1778619173`
- **Recipient:** Rich Gee (`1m.rich.gee@gmail.com`)
- **Sender voice:** Marquise Reed (loaded from `marquise_reed_acquisitions.md`)
- **Lead:** 942 S Melrose, Memphis TN — Mid South Homebuyers / Chris Ulander match
- **Send:** ok, Resend `85c590b5-4166-4a99-9c32-0cf4d56d1ad9`
- **Slack:** posted to `#war-room` ts `1778619178.994449`
- **GDoc:** `http://127.0.0.1:2200/reports/outreach_preview_*.html`
- **Report:** http://127.0.0.1:2301/report/rich_gee_1778619173

## Next 5 things, in order

1. Standardize all 90+ agent firmware files to have `**Speech style:**` blocks so voice_extractor pulls from every agent
2. Build `mcp_elect.sh` + deploy on phone + AceMagician
3. Lint phrase_scrub against templates at startup
4. Set `GDOCS_DISABLE_N8N=1` in phone `.bashrc` (saves 15s/send)
5. Add lead-context inputs (phone, business, LinkedIn) to depth-boost the pipeline
