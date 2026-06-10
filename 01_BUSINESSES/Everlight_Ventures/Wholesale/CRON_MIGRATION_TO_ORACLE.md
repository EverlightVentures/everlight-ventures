# Phone -> Oracle Cron Migration Plan

**Filed:** 2026-04-25
**Owner:** Lucrex
**Trigger:** Phone cron died at 00:36 PT, 18+ hours of silence. We fix this once and forever by moving every job that does not require phone-local resources to Oracle E5.

---

## Current Phone Crontab (audited 2026-04-25)

The phone crontab has 24 active lines. Each is one of:

| Category | Migrate to Oracle? | Reason |
|---|---|---|
| **A. Pure Python/Bash automation against shared paths** | YES | The "phone" reference is a historical artifact, the script could run anywhere. |
| **B. SSH tunnel maintenance** | NO | Phone-local SSH state. Tunnels live on the side that needs them. |
| **C. Phone-local file operations** | NO | Termux home, ~/.termux/boot, Android-specific behavior. |
| **D. Already runs on Oracle in parallel** | DELETE phone copy | Avoid duplicate sends. |

---

## Detailed Per-Line Plan

### MIGRATE TO ORACLE (Category A)

These run from the workspace at /mnt/sdcard/AA_MY_DRIVE/. On Oracle the equivalent path is /home/opc/AA_MY_DRIVE/ (already rsync'd nightly via deploy_to_oracle.sh).

| Phone cron | Oracle systemd timer | Cadence |
|---|---|---|
| `broker_daily_orchestrator.py full` (12:00 PT) | `broker-orch-full.timer` | Daily 12:00 PT |
| `broker_daily_orchestrator.py outreach` (19:00 PT) | `broker-orch-outreach.timer` | Daily 19:00 PT |
| `broker_daily_orchestrator.py scout` (01:00 PT) | `broker-orch-scout.timer` | Daily 01:00 PT |
| `broker_daily_orchestrator.py match` (05:00 PT) | `broker-orch-match.timer` | Daily 05:00 PT |
| `reddit_monitor.py scan` (every 30 min, 8-23 + 0-3 PT) | `reddit-monitor.timer` | Every 30 min |
| `daily_drop_orchestrator.py full` (01:05 PT) | `gear-drops.timer` | Daily 01:05 PT |
| `wholesale_hive_pipeline.py --stage scout qualify match pitch` (15:00 PT) | `wholesale-pipeline-day.timer` | Daily 15:00 PT |
| `wholesale_hive_pipeline.py --stage outreach` (20:00 PT) | `wholesale-outreach.timer` | Daily 20:00 PT |
| `wholesale_hive_pipeline.py --stage followup report` (00:00 PT) | `wholesale-followup.timer` | Daily 00:00 PT |
| `rex_negotiator.py` (every 2 min) | `rex-negotiator.timer` | Every 2 min |
| `rex_belfort_sequence.py` (every hour) | `rex-belfort.timer` | Hourly |
| `rex_lead_recycler.py` (Sun 16:00 PT) | `rex-recycler.timer` | Weekly Sun 16:00 |
| `ceo_daily_brief.py` (15:00 PT) | `ceo-brief.timer` | Daily 15:00 PT |
| `hourly_status_pulse.py` | **Already on Oracle** -- delete phone copy | Hourly |
| `hive_health_monitor.py --fix --quiet` (every 5 min) | `hive-health.timer` | Every 5 min |
| `blinko_log_ingest.sh` (11:30 PT) | `blinko-ingest.timer` | Daily 11:30 PT |
| `auto_sort_transcripts.sh` (hourly) | `transcript-sort.timer` | Hourly |
| `hive_master_sync.py --quick` (every 10 min) | `hive-sync.timer` | Every 10 min |

### KEEP ON PHONE (Category B + C)

| Phone cron | Why phone-only |
|---|---|
| `claude_bridge_guardian.sh` (every 1 min) | Termux-specific health watchdog for Claude bridge socket |
| `mcp_tunnel.sh` (every 5 min) | SSH tunnel to Oracle MCPs, lives on the requesting side |
| `mcp_broker_os_local.sh` (every 5 min) | Phone-local MCP server, by design |
| n8n SSH tunnel reverse-bind (every 2 min) | Tunnel is from phone perspective |
| Resend secrets sourced from Termux env | Migrate to /home/opc/.env on Oracle (already done) |
| `~/.termux/boot/start_hive.sh` | Boot-time only |

### DELETE FROM PHONE (Category D)

| Phone cron | Oracle equivalent already running |
|---|---|
| `hourly_status_pulse.py` | Yes, on Oracle E5 already |

---

## Migration Order (least risk first)

**Stage 1 -- safe, atomic:**
1. `hive-health.timer` (every 5 min health monitor)
2. `hive-sync.timer` (every 10 min)
3. `wholesale-followup.timer` (daily 00:00)
4. `ceo-brief.timer` (daily 15:00)

**Stage 2 -- outreach jobs (after Stage 1 verified):**
5. `wholesale-pipeline-day.timer`
6. `wholesale-outreach.timer`
7. `rex-belfort.timer`
8. `rex-negotiator.timer`

**Stage 3 -- broker orchestrator (last, highest impact):**
9. `broker-orch-full.timer`
10. `broker-orch-outreach.timer`
11. `broker-orch-scout.timer`
12. `broker-orch-match.timer`

**Each migration step:**
- a. Write the systemd unit + timer (template at `Wealth_OS/03_Engines/oracle_systemd/wealth-intel.service`).
- b. Deploy with INSTALL.sh-style script (chmod 644 + chown root:root + restorecon, the SELinux trap).
- c. Enable + start.
- d. Verify it fired by tailing `/home/opc/_logs/<job>.log`.
- e. **Delete the phone crontab line** (this prevents duplicate sends).
- f. Phone-side, leave a stub note in the crontab as a comment so we remember why the line is gone.

---

## Watchdog (the "just in case" layer)

`/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/phone_cron_watchdog.sh` watches the phone cron heartbeat and fires Slack `#hive-alerts` if silence exceeds 30 minutes. Once Stage 3 of the migration is done, this watchdog effectively only watches Categories B+C, which is cheap insurance and worth keeping.

To install on phone:
```
crontab -l | grep -v "phone_cron_watchdog" > /tmp/cron.tmp
echo "*/15 * * * * bash /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/phone_cron_watchdog.sh >/dev/null 2>&1" >> /tmp/cron.tmp
crontab /tmp/cron.tmp
```

---

## Why this matters more than it looks

A cron that "ran every 2 min for the last 30 days" gives you **21,600 fire windows** of attempted work. Phone cron dying for one night = 720 missed fires. Across 12 months that adds up to ~8,750 missed fires assuming 30% phone-cron uptime. **That is most of your year.**

Moving to Oracle makes this an Oracle uptime problem, and Oracle has been up 42 days straight as of this writing. The blast radius of one downtime event drops from "every job dies" to "one specific timer is paused while the service restarts."

---

**Filed by:** Lucrex.
