# Service Tiers — Live Truth Log

> Source of truth for which service runs where, what tier of availability it's expected at, and how to verify it's actually running. **Run the health-check column when claiming "X is up" — never assume from memory.** Aligned with Operator Truth Doctrine (`feedback_operator_truth_doctrine.md`).

<details>
<summary><b>Last full health sweep</b> &mdash; 2026-05-11 PT &middot; post recover-and-replace audit</summary>

```
Phone (Termux+proot)          : LIVE     (this session)
Oracle Micro (xlm-bot)        : LIVE     (5d 11h uptime, xlm-bot + xlm-ws active)
e5-mother (NEW Ampere ARM)    : NOT PROVISIONED  (cloud_init + provision.sh ready)
ev-box   (planned Ampere ARM) : NOT PROVISIONED  (scripts ready)
AceMagician PC (Arch)         : OFFLINE  (powered off or tailnet suspended)
```

Run `bash /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/network_sync/sync_on_reconnect.sh --dry-run` for a current reachability scan.

</details>

---

## Tier definitions

- **T0 — 24/7 Mandatory.** Must always run. If down, business stops.
- **T1 — Available When Up.** Useful when running, recoverable when down.
- **T2 — Device-Specific.** Tied to physical hardware. Cannot move.

## Source-of-truth rules

| Data | SOT lives on | Sync direction |
|---|---|---|
| Workspace files (skills, agents, commands, content) | Phone sdcard | Phone → peers on reconnect |
| `.claude` memory | Phone (canonical) but bidirectional with PC | rsync `--update` (mtime wins) |
| Blinko notes | e5-mother (once up) | Phone read via tailnet |
| Deal pipeline / Supabase | Supabase cloud | No local sync; clients write directly |
| broker_ops + hive sessions | `hive_dashboard/db.sqlite3` on phone (until Phase 7) | n/a — frozen until Django decision |

---

## Service registry

| Service | Host | Tier | Health check | Status |
|---|---|---|---|---|
| `xlm-bot.service` | Oracle Micro | T0 | `ssh oracle-e5 systemctl is-active xlm-bot` | LIVE |
| `xlm-ws.service` | Oracle Micro | T0 | `ssh oracle-e5 systemctl is-active xlm-ws` | LIVE |
| `blinko` (Docker, PG-backed) | e5-mother | T0 | `ssh e5-mother 'curl -s -o /dev/null -w "%{http_code}" -m 5 http://127.0.0.1:1111/'` | NOT DEPLOYED |
| `blinko-db` (postgres:14-alpine) | e5-mother | T0 | `ssh e5-mother 'sudo docker exec everlight-blinko-db pg_isready -U blinko'` | NOT DEPLOYED |
| `agentmemory.service` (MCP :3108) | e5-mother | T0 | `ssh e5-mother 'curl -s -o /dev/null -w "%{http_code}" -m 5 http://127.0.0.1:3108/'` | NOT DEPLOYED |
| `openwebui` (Docker) | e5-mother | T1 | `ssh e5-mother 'curl -s -o /dev/null -w "%{http_code}" -m 5 http://127.0.0.1:8080/'` | NOT DEPLOYED |
| `hive-voice.service` (:8200) | e5-mother | T1 | `ssh e5-mother systemctl is-active hive-voice` | NOT DEPLOYED |
| `nginx` (tailnet reverse proxy) | e5-mother | T1 | `ssh e5-mother systemctl is-active nginx` | NOT DEPLOYED |
| `blinko_mirror.sh` (nightly 03:15) | e5-mother cron | T0 | `ssh e5-mother 'crontab -l | grep blinko_mirror'` | NOT DEPLOYED |
| `tailscaled` | e5-mother + ev-box + phone + PC | T0 | `tailscale status` | partial (phone+PC; Micro install attempted, unverified) |
| `hive-django` (:8000 ops dash) | e5-mother | T1 (DEFERRED) | `ssh e5-mother systemctl is-active hive-django` | DEFERRED (Phase 7) |
| `n8n` (workflow runner) | e5-mother | — | n/a — parked | PARKED |
| MCP fleet bridge (3101-3107) | SSH tunnel from phone | T1 | `for p in 3101 3102 3103 3104 3105 3106 3107; do curl -s -o /dev/null -w "$p:%{http_code} " -m 2 http://127.0.0.1:$p/mcp; done; echo` | tunnel down + upstream not yet deployed |
| Camera / Termux APIs | Phone | T2 | n/a (physical) | LIVE |
| Public webhooks (Cloudflare → e5-mother) | Cloudflare Pages → e5-mother nginx | T1 | `curl -s https://everlightventures.io/.well-known/health` (after wiring) | not yet wired |
| Workspace SOT (sdcard) | Phone | T2 | `ls /mnt/sdcard/AA_MY_DRIVE/CLAUDE.md` | LIVE |
| AceMagician sync (claude_sync_acemagician.sh) | Phone + PC | T1 | `bash /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/claude_sync_acemagician.sh --status` | LIVE (script intact) |
| PC-side hourly pull cron | AceMagician PC | T1 | `ssh pc 'crontab -l | grep claude_sync'` | TEMPLATE READY (install when PC returns) |

---

## Reconnect protocol

When a peer comes back online, this is what fires:

1. **Phone boot:** `/root/.termux/boot/start_hive.sh` runs `claude_sync_acemagician.sh --full` (non-blocking).
2. **Manual or planned trigger:** `bash 03_AUTOMATION_CORE/01_Scripts/network_sync/sync_on_reconnect.sh` — auto-detects peers, delegates PC to `claude_sync_acemagician.sh`, runs inline rsync for mother/ev-box/Micro.
3. **PC-side hourly:** PC's `~/bin/claude_sync_pull.sh` (from template) SSHes to phone at 17 past every hour, runs `--push` on phone side.
4. **e5-mother cron:** `blinko_mirror.sh` nightly at 03:15 to keep `08_BACKUPS/blinko_mirror/` current.

## Verification checklist (paste-runnable)

```bash
# 1. Phone workspace SOT alive
ls /mnt/sdcard/AA_MY_DRIVE/CLAUDE.md && echo "phone workspace ok"

# 2. Oracle Micro xlm-bot alive
ssh oracle-e5 'systemctl is-active xlm-bot xlm-ws' 2>&1 | head -5

# 3. e5-mother (after provision)
ssh e5-mother 'systemctl is-active blinko-db tailscaled; docker ps --format "{{.Names}} {{.Status}}"' 2>&1 | head -10

# 4. Blinko health (after restore)
ssh e5-mother 'curl -s -m 5 http://127.0.0.1:1111/api/v1/note/list?limit=1' | head -c 200

# 5. Sync orchestrator dry-run
bash /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/network_sync/sync_on_reconnect.sh --dry-run | tail -20
```

## How to keep this file honest

- Update the `Status` column whenever a service flips state. One row per change, dated.
- Re-run the live health sweep at the top of any session that claims "everything's up."
- Failures lead any update. Greens follow. No "should be" — only "is."
- Reference `08_BACKUPS/recovery_log.md` for the data-side history (what was restored vs lost).
