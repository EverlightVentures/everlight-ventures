# AGENT MAILBOX — the family coordination board

The Everlight system is **one family, four members**. This file is how the
Claude sessions running on different members coordinate, and the running
history of what's been done. We can't talk in real time (separate processes),
but we all read/write this file and it syncs across the family.

**Protocol:** append a timestamped entry · state your lane · check others'
entries before touching shared resources · conflicts → keep both, flag for Rich.
Entry format: `[YYYY-MM-DD HH:MM PT] FROM:<member> | <message>`

---

## THE FAMILY — 4 members

| Member | Tailnet IP | Role | Status |
|--------|-----------|------|--------|
| **e5-mother** | `100.125.115.95` | Oracle hub, always-on 24/7, runs the stack. Priority #1. | ONLINE (joined 2026-05-14) |
| **acemagician-pc** | `100.93.253.49` | Powerful #2, heavy compute, not 24/7 (power). | ONLINE |
| **richards-z-fold7** (phone) | `100.112.180.29` | Workstation #3 — where edits originate. | tailscaled stale — needs kick |
| **mgn-latitude-e7240** (Dell) | `100.120.23.23` | Spare / thin client. | OFFLINE (last seen 9d) |

Full infra reference: `06_DEVELOPMENT/everlight_os/INFRASTRUCTURE_CHEATSHEET.md`

## LANE ASSIGNMENTS

- **PHONE session**: e5-mother — instance launch ✓, E5 data restore ✓, Tailscale ✓.
  NEXT: provision hive stack from `/home/ubuntu/e5_data/` + systemd units.
- **PC session**: PC-side tailnet, the VCN port-lockdown / port-map plan,
  PC↔Oracle sync wiring. (PC session: confirm by appending.)

## RELATED PLAN DOCS (poured in for history)

- `08_BACKUPS/recovery_log.md` — full .250→e5-mother recovery history
- `09_DASHBOARD/reports/oracle_paid_restore_plan_20260512.html` — the restore plan
- `09_DASHBOARD/reports/workspace_sprawl_reconciliation_20260514.html` — 5-tree merge
- `09_DASHBOARD/reports/network_ai_upgrade_audit_20260510.html` — network audit
- `reference_oci_capacity_plan.md` (memory) — capacity hunt + sequenced plan
- `project_sync_architecture_v3.md` (memory) — Oracle-hub / GitHub-bus / priority order
- `/root/.claude/plans/yeah-its-a-r3c9ver-polymorphic-crystal.md` — recover-and-replace plan

---

## LOG

[2026-04-30] | Oracle E5 ".250" (`xlm-bot-core-e5-2c16g`, 2c/16GB, paid shape)
TERMINATED — wasn't free-tier eligible. Boot volume retained as orphan.

[2026-05-04 → 05-07] FROM:pc | Recovery jumpbox `everlight-recovery-clean`
launched; orphan boot volume mounted; full 4.4 GB E5 tree rsync'd to PC at
`/AA_MY_DRIVE/_oracle_e5_recovery/`. Capacity hammer built.

[2026-05-10 → 05-13] FROM:phone | Network audit, e5_mother provisioning kit
built, capacity hunters built, workspace sprawl mapped.

[2026-05-14 ~11:00 PT] FROM:phone | Memory layer reconciled — phone 156 +
PC 26 files → 181 both sides (was forked). Workspace sprawl: 5 trees → 1
canonical (`/AA_MY_DRIVE` on PC, 125 GB), conflict-preserving, 0 deleted.

[2026-05-14 ~11:50 PT] FROM:phone | Rich added card + initiated Pay-As-You-Go
upgrade. Quota walls cleared. `hunt_and_provision_e5.sh` launched on phone.

[2026-05-14 ~13:06 PT] FROM:phone | Hunter caught capacity, landed an instance
(192.18.137.52) + rsync'd E5 data. BUT cloud-init had a ufw bug that barricaded
SSH — instance unreachable.

[2026-05-14 ~15:54 PT] FROM:phone | Terminated barricaded instance. Relaunched
CLEAN (no cloud-init) at **163.192.60.35**. SSH port 22 works.

[2026-05-14 ~16:00 PT] FROM:phone | E5 data restored: orphan boot volume
`xlm-bot-core-e5-2c16g` mounted (VG `ocivolume`), rsync'd to
`/home/ubuntu/e5_data` on e5-mother — 3.8 GB, `.env` + 113 systemd units.
Orphan detached + intact as cold backup.

[2026-05-14 ~16:10 PT] FROM:phone | Tailscale installed on e5-mother. Rich
clicked the auth URL. **e5-mother joined the tailnet: `100.125.115.95`.**

[2026-05-14 ~16:20 PT] FROM:phone | Built `INFRASTRUCTURE_CHEATSHEET.md` —
complete service/IP/recovery reference. Expanded this mailbox into the family
registry. NEXT (phone lane): provision the hive stack on e5-mother.

[2026-05-14 ~16:20 PT] FROM:phone | PC session — OPEN ITEMS for you:
  1. Verify recovered `.env` exists in PC canonical tree under `_oracle_e5_recovery/`
     — Rich wants creds mirrored on PC for disaster-proofing.
  2. The VCN lockdown is your lane. SEQUENCING: e5-mother is now ON the tailnet
     (100.125.115.95) — verify you can reach it tailnet-side, THEN close the
     public ports down to SSH-only. Don't close before verified.
  3. Append your status here so the phone session knows what you've done.

<!-- members: append entries below this line -->

[2026-05-14 ~16:45 PT] FROM:phone | PROVISIONING STARTED on e5-mother.
Base layer installed + verified: docker 29.5, node 20, pip3, nginx, redis,
postgresql-client, jq.
BATCH 1 DONE: BlinkoLite live on e5-mother:1111 -- active+enabled, 3711 notes
queryable (recovered E5 db, not the 614-note phone copy). Systemd unit
translated opc->ubuntu paths, fixed env var (BLINKO_DB not BLINKO_DB_PATH).

[2026-05-14 ~16:45 PT] FROM:phone | NEXT BATCHES need the shared env files
reconstructed first: units reference /etc/default/rex-negotiator and
/etc/mcp/hive_relay.env -- those were NOT in the orphan rsync (only
/etc/systemd/system/ was captured). Options: re-attach orphan volume to grab
/etc/default + /etc/mcp, OR reconstruct from /home/ubuntu/e5_data/.env.
PC session: if you have these env files in the canonical tree, flag it here.

[2026-05-14 ~17:30 PT] FROM:phone | === SESSION-END HANDOFF ===
Rich heading out, PC powered off. Recap of state for next session:

## VERIFIED WORKING ON e5-mother
- Base layer: docker 29.5, node 20, pip3, nginx, redis, postgresql-client, jq -- installed + verified
- BlinkoLite: live on :1111, active+enabled, 3711 notes queryable
  - /health, /api/v1/note/stats (GET), /api/v1/note/list (POST), /api/v1/note/ai-query (POST)
- Tailscale: e5-mother joined tailnet as 100.125.115.95, --ssh advertised
- SSH: github_deploy key in authorized_keys, port 22 listening on all interfaces

## RECOVERED FROM ORPHAN (now on e5-mother)
- /home/ubuntu/e5_data/ -- 3.8 GB E5 production tree (.env, hive_*, broker_*, wholesale_*, content_tools, hive_django, blinko_lite.py + .db)
- /home/ubuntu/e5_data/_systemd_units/ -- 113 unit files
- /home/ubuntu/e5_data/_etc_config/ -- /etc/default/rex-negotiator, /etc/mcp/{hive_relay,dispatcher_relay}.env, cloudflared/, nginx/

## INSTALLED ENV FILES ON e5-mother
- /etc/default/rex-negotiator (PATCHED: opc->ubuntu/e5_data, .250->100.125.115.95)
- /etc/mcp/hive_relay.env
- /etc/mcp/dispatcher_relay.env
- /home/ubuntu/.env (copy of /home/ubuntu/e5_data/.env)
All chmod 600, owned by ubuntu.

## OUTSTANDING / NEXT SESSION
1. **Tailscale ACL** -- Rich needs to paste this in login.tailscale.com/admin/acls
   so PC can `tailscale ssh` to e5-mother keyless:
   ```json
   "ssh": [{
     "action": "accept",
     "src":    ["autogroup:member"],
     "dst":    ["autogroup:member"],
     "users":  ["autogroup:nonroot", "root"]
   }]
   ```
2. **Phone tailscaled stale** -- showing offline despite being active. Needs
   `tailscale down && tailscale up` on Termux side (outside proot).
3. **MCP servers source code** -- /opt/mcp_servers/ NOT yet on e5-mother.
   Orphan re-attach + mount failed this round (VG didn't auto-activate fast
   enough). RETRY next session: oci attach orphan, wait 30s, vgscan --mknodes,
   vgchange -ay ocivolume, mount ro /dev/ocivolume/root /mnt/orphan_e5, rsync
   /mnt/orphan_e5/opt -> /home/ubuntu/e5_opt, unmount, detach.
4. **Batch 2 (MCP fleet)** -- blocked on #3. Once /opt is on-box, install
   mcp-proxy (pip), translate the 7 mcp-*-proxy.service files (opc->ubuntu,
   /opt/mcp_servers -> /home/ubuntu/e5_opt/mcp_servers), enable each.
5. **Batch 3 (hive core)** -- hive-action-engine, hive-django, hive-self-healer,
   hive-task-runner. These need Python deps installed via pip from
   requirements.txt files in the recovered tree.
6. **Batch 4 (wholesale pipeline)** -- broker-orch-*, cuyahoga-scrape, etc.
   Smoke test Resend + Supabase + Slack + Stripe end-to-end.
7. **VCN port lockdown** -- PC session's lane. e5-mother is on tailnet ✓ now,
   so the public ports (1111, 5678, 8080, 8200, 8502, 8503, 8504) can be closed
   down to just SSH:22 + tailscale0.
8. **Twilio credentials** -- not in recovered .env. Locate or confirm retired.
9. **Commit cheat sheet + everything to GitHub.**

## TASK STATE (for new session)
- #13 DONE: e5-mother launched + recovered + tailscale joined
- #14 PENDING: PC sprawl reconciliation (memory done, snapshots archived, workspace
  merged, but compare-contrast verification + 3-way sync still open)
- #15 IN PROGRESS: Provision hive stack -- Batch 1 done, Batch 2-4 queued

## QUICK REFS
- e5-mother SSH: `ssh -i /root/.ssh/github_deploy -p 22 ubuntu@163.192.60.35` (public)
  or `ubuntu@100.125.115.95` (tailnet, once phone TS reconnects)
- Blinko UI: http://163.192.60.35:1111  (or http://100.125.115.95:1111)
- Cheat sheet: 06_DEVELOPMENT/everlight_os/INFRASTRUCTURE_CHEATSHEET.md
- State files: _state/e5_new_ip.txt, _state/e5_new_ocid.txt

[2026-05-14 ~17:50 PT] FROM:phone | LAST ORPHAN PASS -- partial success.
  - SUCCESS earlier this session: /home/opc -> e5_data (3.8G), /etc/{default,mcp,nginx,cloudflared} -> e5_data/_etc_config
  - FAILED this round: /opt + /usr/local + /root + crontabs grab
    Mount error: "EXT4-fs (dm-0): unable to read superblock", "Buffer I/O error"
    The LV /dev/ocivolume/root is probably XFS not EXT4 -- kernel guessed wrong.
    Volume itself is FINE (first mounts worked, data integrity verified by rsync).
  - NEXT SESSION RETRY: oci attach orphan, wait 30s, vgchange -ay ocivolume,
    try BOTH: `mount -t xfs -o ro /dev/ocivolume/root /mnt/orphan_e5` AND
    `sudo partprobe /dev/sdc; sudo udevadm settle; mount -o ro ...`
    Need to grab: /opt/mcp_servers (CRITICAL for MCP fleet), /usr/local/bin,
    /root (config + keys), /var/spool/cron (crontabs).
  - Orphan volume AVAILABLE in OCI as cold backup -- not lost, just needs the
    right mount incantation next time.

[2026-05-14 ~17:50 PT] FROM:phone | === FINAL STATE THIS SESSION ===
e5-mother (163.192.60.35 public, 100.125.115.95 tailnet):
  - Base layer installed
  - BlinkoLite live + verified (3711 notes)
  - All recovered env files placed and path-translated
  - Tailscale joined, --ssh advertised
  - Ready for Batch 2 next session
Phone tailscaled still stale (needs Termux-side kick).
PC powered off (Rich did this).
Rich heading out. Next session: ACL paste, orphan retry for /opt, MCP fleet,
hive core, wholesale smoke test, GitHub commit.

[2026-05-15 ~07:30 PT] FROM:phone | === SESSION 2 UPDATE ===
- ORPHAN GRAB SUCCEEDED (third try): partprobe + explicit fstype detection.
  LV was XFS not EXT4 -- kernel was guessing wrong. /opt/mcp_servers,
  /usr/local, /root config, etc. all now at /home/ubuntu/e5_recovered/ on
  e5-mother (9.1 GB recovered this round).
  → /opt/mcp_servers has: blinko_memory, dispatcher_relay, market_intel, n8n_mcp
  Batch 2 is now UNBLOCKED.
- MEMORY AWARENESS SERVICE built: blinko_status.py at
  03_AUTOMATION_CORE/01_Scripts/. Probes remote → falls back to local SQLite.
  Reports CONNECTED / DEGRADED / OFFLINE in human/json/banner/short modes.
  Exit codes 0/1/2/3 for scripts. Agents can announce memory state honestly.
- BLINKO .db BACKED UP to phone: 8.2 MB at _state/blinko_lite.db (3711 notes).
  Phone now has hot fallback when remote unreachable. PC copy next session.
- BLINKO TAILNET-ONLY CONFIRMED: Ubuntu's default iptables blocks 1111 from
  public (allows only SSH:22 public + tailnet via ts-input chain). Security
  model is correctly in place by default -- no extra hardening needed.
- ARCHITECTURE CLARITY added to INFRASTRUCTURE_CHEATSHEET.md sections 7-9:
  "what goes where", subscriptions inventory, memory awareness docs. Cheat
  sheet now 299 lines, fully covers Rich's "I don't know what's what" question.

[2026-05-15 ~07:35 PT] FROM:phone | NEXT-SESSION queue still:
  1. Rich pastes the Tailscale ACL `ssh` block (login.tailscale.com/admin/acls)
  2. Kick phone tailscaled (Termux side, outside proot)
  3. Batch 2 MCP fleet -- /opt/mcp_servers code is on e5-mother now,
     install mcp-proxy via pip, translate the 7 mcp-*-proxy units (opc->ubuntu,
     /opt/mcp_servers -> /home/ubuntu/e5_recovered/opt/mcp_servers), enable each.
  4. Batch 3 hive core (hive-action-engine, hive-django, hive-self-healer etc.)
  5. Batch 4 wholesale pipeline smoke (Resend, broker-orch, cuyahoga-scrape)
  6. PC sync when PC online: copy blinko_lite.db to PC, run sync_on_reconnect.sh
  7. Commit everything to GitHub

---

## ACTIVITY INDEX -- where to find "who did what when"

The Hive's action log is intentionally distributed across formats, each serving
a purpose. **DON'T dump everything into this mailbox** -- it'd break it as a
coordination board. Instead, this index points to where each kind of history
lives, and `activity_feed.py` gives you a unified VIEW on demand.

| Looking for...                          | Look at...                                          |
|-----------------------------------------|-----------------------------------------------------|
| Claude-session coordination + decisions | **THIS FILE** (AGENT_MAILBOX.md) -- keep lean       |
| Searchable narrative of Hive sessions   | **Blinko** (tag `#hive/session`, on e5-mother:1111) |
| Structured machine log of agent runs    | `_logs/**/*.jsonl` from `hive_logger`               |
| Dashboard view (sessions, agents, runs) | Django `hive_hivesession` / `hive_agentresponse`    |
| Real-time human log of events           | Slack `#deploy-log`, `#war-room`, `#hive-alerts`    |
| Doctrine, feedback rules, references    | `.claude/projects/.../memory/` (181 files, synced)  |
| Recovery + .250 -> e5-mother history    | `08_BACKUPS/recovery_log.md`                        |
| Architectural decisions / plans         | `/root/.claude/plans/*.md`                          |
| Subscriptions + service map             | `06_DEVELOPMENT/everlight_os/INFRASTRUCTURE_CHEATSHEET.md` |

### Unified view (one command, all sources):

```bash
python3 03_AUTOMATION_CORE/01_Scripts/activity_feed.py
python3 .../activity_feed.py -n 50              # last 50 events
python3 .../activity_feed.py --hours 24         # last 24h only
python3 .../activity_feed.py --grep wholesale   # filter
python3 .../activity_feed.py --source blinko    # one source only
```

### Memory model (RAG explained)

- **Blinko = your FTS5 (text-matching) RAG.** Fast keyword + full-text search
  over 3,711 notes. Pure SQLite, stdlib Python. Lives on e5-mother :1111
  (tailnet-only), hot fallback on phone, cold on PC. Use `/api/v1/note/list`
  (text search) and `/api/v1/note/ai-query` (formatted response).
- **Supabase pgvector = your potential SEMANTIC RAG layer.** Not wired up yet.
  Would do vector embedding search (semantic similarity, not just text match).
  Build this later if Blinko's text search proves insufficient. Not worth the
  ops cost yet.
- **Memory awareness service**: `blinko_status.py` tells any agent its current
  memory state (CONNECTED / DEGRADED / OFFLINE) so they announce honestly.

[2026-05-15 ~08:30 PT] FROM:phone | PHASE 8 DONE -- Moltbook is LIVE.
  http://127.0.0.1:1112 (local, port 1112; flip MOLTBOOK_BIND=0.0.0.0 to expose
  on tailnet).
  All 7 API endpoints verified HTTP 200: /api/health /api/config /api/memory
  /api/family /api/activity /api/mailbox /api/notes.
  /api/memory currently DEGRADED (3711 notes from local fallback) because the
  phone's tailscaled is still stale -- the moment phone re-joins tailnet, it
  flips to CONNECTED automatically.
  Files at 09_DASHBOARD/moltbook/. Launcher: bash start.sh (nohup'd).
  Vanilla JS, DOM-safe rendering (no innerHTML), proven Termux pattern.
  Also saved a new HARD-LAW memory: feedback_oracle_always_free.md -- Oracle
  resources stay in Always Free tier unless Rich explicitly directs spending.
  Card on file is for verification, not authorization.

[2026-05-15 ~09:00 PT] FROM:phone | MOLTBOOK v2 + AUDIT LOG SYSTEM live.
  - Built _state/audit_log/ with 8 bootstrap entries (the major recover-and-
    replace milestones) + a Dewey-Decimal-style codebook (_classification.json,
    29 codes, 6 threads, 3 sessions).
  - Each audit entry is a markdown file with YAML frontmatter (id, title, date,
    category, thread, session, status, tags, summary) + structured body
    (what / why / before / after / how / verification / audit trail / links).
    Auditable. Defensible.
  - Moltbook v2 at http://127.0.0.1:1112 -- audit pane groups by date, shows
    classification badges, click any card -> modal opens with full markdown
    rendered. Operator's "if we got audited" requirement met.
  - New endpoints: /api/audit, /api/audit/classification, /api/audit/<id>.
  - Phase 9 deferred for now -- the e5-mother sync boot hook needs the phone's
    tailscaled to be live so e5-mother can SSH into the phone for rsync pulls.
    Phone tailscaled is still stale (shows offline-4h-ago). Building the
    systemd unit would just create a service that perpetually fails. Better to
    wait until the phone-tailscale-kick is done by the operator.
  - Phases 10 + 11 also still pending. Phase 10 is multi-hour, Phase 11
    requires careful .gitignore review before pushing secrets-adjacent files.

[2026-05-15 ~09:45 PT] FROM:phone | PHASE 9 + doctrine compliance shipped.
- Phone tailscale RECONNECTED (operator did the Termux-side kick).
- sync_to_mother.sh built -- phone-side rsync push to e5-mother. Wired into
  /root/.termux/boot/start_hive.sh so every phone boot auto-pushes workspace
  + memory deltas to mother. Reachability-gated, conflict-preserving, one-way.
- Tailscale-SSH ACL trap diagnosed + fixed: `tailscale set --ssh=false` on
  e5-mother. Regular sshd now handles tailnet:22 normally. HTTP/1111 always
  worked; the trap only affected port 22.
- First 35GB seed sync ACTIVELY RUNNING over tailnet now (PID 18663+). Will
  finish in the background; future boots only push deltas.
- MOLTBOOK migrated to port band scheme: was on 1112, now on 2401 (2400
  band = "Apps" per feedback_port_band_scheme memory). Added to
  dashboards_watchdog.sh SERVICES array -- watchdog --status confirms UP.
- Audit log: 10 entries now (added moltbook-v2/audit-system + phone-to-mother-sync).
  Browse at http://127.0.0.1:2401.
- HONEST OPEN ITEMS: Phase 10 (Batch 2/3/4 MCP fleet + hive core + wholesale
  smoke) still pending, multi-hour. Phase 11 (GitHub commit) still pending,
  needs careful .gitignore review. Operator can resume those in a focused
  next session.
