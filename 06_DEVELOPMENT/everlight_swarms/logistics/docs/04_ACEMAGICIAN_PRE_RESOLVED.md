# PRE-RESOLVED UNKNOWNS -- AceMagician Environment Audit

**Probed by:** phone-side Claude via SSH over Tailscale, 2026-05-07 PT
**Purpose:** flip the seven unknowns in HANDOFF_TO_ACEMAGICIAN.md to greens BEFORE you (AceMagician Claude CLI) start the checklist

---

## Result: 6 of 7 unknowns flipped GREEN. AceMagician is more built-out than expected.

| # | Question | Answer | Source |
|---|----------|--------|--------|
| 1 | Does `content_tools/` exist on AceMagician? | **YES** -- 17 modules, fuller than E5 had | `ls /AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/content_tools/` |
| 2 | Is there a `hive_reports/` dir? | **YES** at `/AA_MY_DRIVE/_logs/hive_reports/` (slight path variant from E5) | `find /AA_MY_DRIVE -name hive_reports` |
| 3 | Is Blinko running locally? | **YES** -- port 1111 listening | `ss -ltn` |
| 4 | What's in `docker ps`? | n8n, langfuse stack (6 containers), jellyfin, mdtv-pc, homarr | `docker ps` |
| 5 | Django/MCP dashboard equivalent? | **MCP FLEET 3101-3107 ALL LISTENING** on 127.0.0.1, n8n 5678 active. No 8504 yet. | `ss -ltn` |
| 6 | Resend key live? | **PROBE FAILED** -- `/home/richgee/.env` does not exist. Keys may be at `/AA_MY_DRIVE/.env` (saw `.env`, `.env.bak`, `.env.bak2` there). Verify yourself. | `ls /AA_MY_DRIVE/.env*` |
| 7 | Sync direction? | **TWO-WAY (auto)** -- `hive-sync-watch.service` is loaded+active+running, "Hive Mind sync watcher (auto-fire on phone connect)" | `systemctl --user list-units` |

---

## content_tools/ inventory on AceMagician (full)

```
HIVE_LOGGER_API.md       hive_logger.py        report_template.py
__pycache__              hive_tags.py          resend_budget.py
branded_calendar.py      log_to_canvas.py      resend_guard.py
branded_mailer.py        n8n_replacements.py   resend_manager.py
branded_slack.py         pre_send_phrase_scrub.py   slack_canvas_bridge.py
branded_sms.py           dnc_gate.py
gdocs_bridge.py          gdrive_setup.py
```

**Branded comms chokepoint is fully present.** No prerequisite blocker on this front.

---

## Live Docker stack on AceMagician

```
mdtv-pc-gateway       -> 0.0.0.0:8800
mdtv-pc-jellyfin      -> 0.0.0.0:8096
mdtv-pc-threadfin     -> 0.0.0.0:34400
mdtv-pc-postgres      -> 5432/tcp
mdtv-pc-redis         -> 6379/tcp
langfuse              -> 0.0.0.0:3100->3000/tcp
langfuse-worker       -> 127.0.0.1:3030
langfuse-clickhouse   -> 127.0.0.1:8123, 9000
langfuse-postgres     -> 127.0.0.1:5432
langfuse-minio        -> 127.0.0.1:9090, 9091
langfuse-redis        -> 127.0.0.1:6379
homarr                -> 0.0.0.0:7575
n8n                   -> 0.0.0.0:5678
```

**Notable additions vs E5:** Langfuse full stack (LLM observability). This is *gold* for the swarm -- wire OpenSwarm's LLM client through Langfuse and you get per-agent token traces, cost tracking, and prompt-versioning out of the box. Strongly recommend.

---

## Listening ports

```
0.0.0.0:5678        n8n
0.0.0.0:1111        blinko
127.0.0.1:3101      MCP server 1
127.0.0.1:3102      MCP server 2
127.0.0.1:3103      MCP server 3
127.0.0.1:3104      MCP server 4 (broker-os, per phone-side memory)
127.0.0.1:3105      MCP server 5
127.0.0.1:3106      MCP server 6
127.0.0.1:3107      MCP server 7
```

**Free ports for swarm services:**
- `:3120` (proposed for swarm internal API, tailnet-only)
- `:8504` (free -- if you want to stand up a Django artifact dashboard equivalent)
- `:8200` (E5 had voice handler here; check if reused)

---

## Implications for the checklist

The original handoff section 4 checklist now simplifies significantly:

- **Step 2** (verify content_tools): SKIP, confirmed present.
- **Step 3** (verify keys): change target to `/AA_MY_DRIVE/.env`, NOT `~/.env`.
- **Step 4** (clone upstream): proceed as written.
- **Step 5** (sandbox model verify): still required, no shortcut.
- **Step 6** (build missing pieces): still required:
  - `content_tools/swarm_budget.py` (NEW module)
  - The 6 missing `agents/*/instructions.md` files
  - systemd unit + timer
- **Step 7** (mock RFP): proceed as written.
- **NEW step 8** (Langfuse wire-up): patch the swarm's LLM client to send traces to Langfuse at `http://localhost:3100`. This wasn't in the original plan because E5 didn't have it.

---

## Architectural decision to surface to Marquise

The original plan called for the swarm to publish to a Django dashboard at `:8504`. AceMagician doesn't have that yet. Three options:

1. **Stand up Django on AceMagician** (faithful to E5 architecture)
2. **Use Homarr as the dashboard surface** (already running on `:7575`, Homarr can render service dashboards)
3. **Use Langfuse as the observability layer** (already running, more LLM-native than Django)

Recommend option 3 for swarm runs (Langfuse handles agent traces) plus option 2 for at-a-glance status (Homarr widget pointing at Langfuse). Skip Django Step 1 unless we have a reason.

---

## What's still YOUR job (AceMagician CLI)

1. Verify keys at `/AA_MY_DRIVE/.env` (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `RESEND_API_KEY`).
2. Clone OpenSwarm upstream + verify sandbox model isn't paid e2b.
3. Build `swarm_budget.py` mirroring `resend_budget.py` shape.
4. Write the 6 missing `agents/*/instructions.md` files (orchestrator, intake, research, docs, slides, onboarding) -- you've got Penny's pricing prompt as the template.
5. Decide on Langfuse wire-up vs Django dashboard.
6. systemd unit + timer for the queue poller.
7. First mock RFP run.
8. Drop status note at `04_ACEMAGICIAN_DEPLOY_STATUS.md` (separate from this file).

---

**Phone-side Claude signing off.** Sync watcher should mirror your status note back to me next session. Lucrex directive applies. Operator Truth Doctrine applies. Free-path-first applies.
