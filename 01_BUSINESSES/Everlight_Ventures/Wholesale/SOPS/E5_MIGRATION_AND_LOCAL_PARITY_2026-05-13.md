# E5 Instance Migration + Local Parity Plan
**Date:** 2026-05-13
**Operator:** Rich Gee
**Status:** PLAN-OF-RECORD. Local self-healing watchdog SHIPPED. MCP/RAG migration QUEUED for next session.

---

## Background

The Oracle E5 instance (`129.159.38.250`) was a paid Always-Free OCI VM that hosted:
- Blinko RAG (port 1111) — knowledge base + memory store
- Hive Django dashboard (port 8504) — ops console
- Hive Voice handler (port 8200) — Twilio webhook
- MCP fleet (ports 3101-3107) — Claude Code MCP servers
- n8n (port 5678) — automation workflows (parked since 2026-04-24)
- Various crons + reports server (port 8504/reports)

The instance got terminated when it slipped off the free tier. Per `memory/oracle_cloud.md`,
the canonical replacement (e5-mother on a tailnet-only Ampere VM) was provisioned in
docs but never fully restored.

**Result**: phone is now the sole host for everything. This memo is the parity plan.

---

## Current local parity (what's already running)

These ports are LIVE on the phone right now, watched by `dashboards_watchdog.sh`:

| Port | Service | Replaces (E5 equivalent) |
|---|---|---|
| 2000 | Master Hub | new — was no E5 equivalent |
| 2200 | Reports Hub | E5:8504/reports/ |
| 2300 | Intel Center static | new |
| 2301 | Intel Center FastAPI | new |
| 2302 | E-Sign + Wire + Audit | new |
| 2400 | Apps (Alley Kingz) | local-only, never E5 |
| 2500 | MMA Fight Camp | local-only, never E5 |

**Self-healing**: dashboards_watchdog.sh runs every 1 min via cron, kills stale processes
on port-in-use errors, restarts cleanly. Wired into Termux boot + Ubuntu shell login.

---

## Missing local parity (queued for next session)

### Priority 1 — Blinko RAG (memory store)

**E5 state**: ran on `:1111`, served the Hive memory layer. Already had a fallback
`blinko_lite.py` that runs on the phone (per existing crontab line:
`*/5 * * * * curl localhost:1111/health || nohup python3 blinko_lite.py`).

**Local restoration plan**:
1. Verify `blinko_lite.py` is healthy + responding on `:1111`
2. If not running → integrate into `dashboards_watchdog.sh` as an 8th service
3. Reassign port from 1111 → **2600** (per the band scheme; reserve 2600 band for memory + RAG)
4. Migrate any Blinko notes data from `_logs/blinko_lite.db` (already on disk)

**Estimated effort**: 30 min (mostly verify + cron integration)

### Priority 2 — MCP Fleet (3101-3107)

**E5 state**: 7 MCP servers (broker-os, blinko-memory, market-intel, slack, gmail, calendar, hive-orchestrator) running on Oracle E5.

**Local restoration plan**:
1. Existing scripts at `06_DEVELOPMENT/mcp_servers/{broker_os,blinko_memory,market_intel}/server.py` — verify they run locally
2. Build `start_all.sh` (already done!) + `stop_all.sh` (already done!) at `06_DEVELOPMENT/mcp_servers/`
3. The MCP failover doctrine at `03_AUTOMATION_CORE/01_Scripts/mcp_failover/mcp_elect.sh` already exists for this exact case
4. Reassign ports from 31xx → **2700 band** (memory/RAG/MCP):
   - 2700 Blinko RAG
   - 2701 broker-os MCP
   - 2702 blinko-memory MCP
   - 2703 market-intel MCP
   - 2704 hive-orchestrator MCP
   - 2705 slack MCP (when set up)
   - 2706 gmail MCP (when set up)
   - 2707 calendar MCP (when set up)
5. Add to `dashboards_watchdog.sh` so they self-heal
6. Update `.mcp.json` to point Claude Code at local URLs

**Estimated effort**: 2-3 hours (need to test each MCP server starts cleanly on phone)

### Priority 3 — Hive Django dashboard (deferred per CLAUDE.md)

**E5 state**: ran on `:8504`, full Django app with 14 views (taskboard, blackjack, broker, etc.)

**Local restoration plan**: per memory `aios_audit_may8_findings.md` and CLAUDE.md, this is
**deferred to Phase 7** after Open WebUI + Supabase prove sufficient. The Django source is
intact at `09_DASHBOARD/hive_dashboard/` with real data in `db.sqlite3`. Don't rebuild.

### Priority 4 — Supabase status check

**Unknown**: per Rich, "I don't know what's going on with Supabase." Per CLAUDE.md, we
have a Supabase project at `https://jdqqmsmwmbsnlnstyavl.supabase.co` for deal pipeline.

**Action item**: 5-min check next session — `curl -s https://.../rest/v1/?apikey=...` to
verify the project is alive and not paused for inactivity. If paused, restore. If alive,
audit which tables are still in active use (broker_ops likely; everything else may be stale).

### Priority 5 — Hive Voice handler

**E5 state**: ran on `:8200`, Twilio inbound voice webhook for Marcus Cole.

**Local plan**: requires public-facing URL (Twilio webhooks need an HTTPS callback). When
Cloudflare Tunnel is set up for esign (per `PUBLIC_URL_VIA_CLOUDFLARE_TUNNEL.md`), add a
second tunnel hostname `voice.everlightventures.io` → phone:2800. Defer until Twilio is
re-needed for live deals.

---

## Migration path: when free Oracle instance comes back

When OCI free-tier capacity opens (per `memory/reference_oci_capacity_plan.md`, the hunter
script polls indefinitely):

### Steps
1. Provision new Ampere ARM 4 OCPU / 24 GB instance via OCI CLI
2. Run `03_AUTOMATION_CORE/01_Scripts/e5_mother/` provisioning scripts (already exist per `memory/reference_ev_box.md`)
3. **Do NOT abandon local services.** Keep phone-side services as the default; Oracle becomes the **secondary** with `mcp_elect.sh` failover doctrine
4. Migrate the data:
   - `deal_execution.sqlite` (audit log) → rsync to Oracle
   - `09_DASHBOARD/reports/deals/*` (signed contracts) → rsync to Oracle
   - `Wholesale/owner_downloads/parsed/*.json` (lead data) → rsync to Oracle
   - `_logs/blinko_lite.db` (memory) → restore to Blinko Postgres
5. Set up Cloudflare Tunnels with Oracle as primary, phone as backup
6. Cross-device tailnet sync: `claude_sync_acemagician.sh` already does this

### Tailnet topology after restoration
```
Phone (2100-2700 bands, primary host)
   ├── Tailscale → AceMagician PC (mirror via claude_sync_acemagician.sh)
   ├── Tailscale → ev-box VM (mirror via claude_sync_ev_box.sh)
   └── Tailscale → new Oracle e5-mother (primary host post-restoration)

Cloudflare Tunnel public hostnames:
   ├── esign.everlightventures.io → phone:2302 (or Oracle:2302 when up)
   ├── voice.everlightventures.io → Oracle:2800 (when Twilio re-needed)
   └── reports.everlightventures.io → Oracle:2200 (cached static reports)
```

---

## Self-healing watchdog (SHIPPED 2026-05-13)

`03_AUTOMATION_CORE/01_Scripts/dashboards_watchdog.sh`:
- Watches all 7 dashboard ports (2000/2200/2300/2301/2302/2400/2500)
- Pattern: `curl health → if down: pkill stale on port + restart launcher`
- Idempotent (safe to run from cron, boot, or shell login)
- Runs every 1 minute via cron
- Runs ONCE on phone boot (start_hive.sh calls it after settling)
- Runs ONCE on first interactive Ubuntu shell login (everlight_shell.zsh fires it)
- Logs to `_logs/dashboards_watchdog.log`

`fastfetch banner now shows live ● / ○ pills per port` so Rich sees health on every shell open.

---

## When to add new ports to the watchdog

Edit `dashboards_watchdog.sh` `SERVICES=` array. Format:
```bash
"<port>|<healthpath>|<launch command>|<human name>"
```
The watchdog will pick up new entries on the next cron tick. No restart needed.

---

## Failure modes + escalation

| Failure | Auto-recovery? | Escalation |
|---|---|---|
| Service crashes mid-day | YES (cron next minute) | log only |
| Port stuck (proc didn't release) | YES (pkill before restart) | log only |
| Phone reboots | YES (start_hive.sh + cron resume) | log only |
| Watchdog itself broken | NO | manual: `bash dashboards_watchdog.sh --status` |
| Phone offline (no network) | NA — services still local | NA |
| sdcard unmounted | NO | requires phone restart |

---

## Verification commands

```bash
# Live status
bash /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/dashboards_watchdog.sh --status

# Force a heal cycle now
bash /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/dashboards_watchdog.sh

# Recent watchdog log
tail -30 /mnt/sdcard/AA_MY_DRIVE/_logs/dashboards_watchdog.log

# Cron entry verification
crontab -l | grep dashboards_watchdog
```
