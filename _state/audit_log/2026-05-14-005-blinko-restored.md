---
id: 2026-05-14-005-blinko-restored
title: BlinkoLite restored on e5-mother (3,711 notes, tailnet-only by default)
date: 2026-05-14T16:45:00-07:00
agent: phone-claude
phase: migration
category: 210
thread: memory-resilience
session: s-002-may14-migration
status: completed
tags: blinko, rag, memory, services
summary: Brought up the BlinkoLite knowledge base on e5-mother:1111 with the recovered .db (3711 notes). Translated the Oracle Linux systemd unit to Ubuntu paths, fixed an env-var name bug, verified all read endpoints.
---

## What was done

Started BlinkoLite — the operator's RAG/knowledge layer — on the new e5-mother
using the recovered SQLite database. The original systemd unit from the dead
.250 referenced `User=opc` and `/home/opc/...` paths (Oracle Linux convention);
translated it to `User=ubuntu` and `/home/ubuntu/e5_data/...` for the Ubuntu
runtime. Caught and fixed an env-var bug in the original unit
(`BLINKO_DB_PATH` — the script actually reads `BLINKO_DB`, which only "worked"
on the old box by coincidence because the default path matched).

## Why

Blinko is the persistent memory of the Hive. Every agent session, every
significant decision, every wholesale lead summary is logged here. Without
Blinko running, the agents have no long-term recall — they'd "forget" the
moment a session ends. Getting it back online unblocks the entire memory-
awareness model, the Hive's auto-logging discipline, and the Moltbook's
"Recent Notes" pane.

The recovered `.db` has **3,711 notes** — much more than the 614 we'd feared
from the phone's local-only `blinko_lite.db`. The phone's copy was the
lite/local buffer; the E5's was the full canonical store.

## Before

- BlinkoLite not running anywhere except a stale phone-side copy with 614 notes
- The `.250` original was unreachable (instance terminated)
- The full `.db` (3,711 notes) was on the orphan boot volume, copied to
  `/home/ubuntu/e5_data/blinko_lite.db` on e5-mother via the data restore

## After

- `blinko.service` active + enabled on e5-mother (survives reboot)
- Listening on `0.0.0.0:1111` — *but Ubuntu's default iptables blocks 1111
  from public*, so it's effectively **tailnet-only by default**. Tailnet
  peers (PC, phone-when-tailscale-up, e5-mother itself) reach it; nobody
  else.
- All read endpoints verified working:
  - `GET /health` → `{"status": "ok", "service": "blinko-lite", "pid": ...}`
  - `GET /api/v1/note/stats` → `{"total_notes": 3711, "db_size_mb": 8.14, ...}`
  - `POST /api/v1/note/list` → returns real note content
- Note count: 3,711 (date range 2026-03-11 → 2026-04-27)

## How

```bash
# 1. Write translated systemd unit
sudo tee /etc/systemd/system/blinko.service > /dev/null <<UNIT
[Unit]
Description=BlinkoLite Knowledge Base
After=network.target
[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/e5_data
Environment=BLINKO_DB=/home/ubuntu/e5_data/blinko_lite.db
Environment=BLINKO_LOG=/home/ubuntu/e5_data/blinko_lite.log
Environment=BLINKO_PORT=1111
ExecStart=/usr/bin/python3 /home/ubuntu/e5_data/blinko_lite.py
Restart=always
RestartSec=5
[Install]
WantedBy=multi-user.target
UNIT

# 2. Enable + start
sudo systemctl daemon-reload
sudo systemctl enable --now blinko.service

# 3. Verify
curl -s localhost:1111/health
curl -s localhost:1111/api/v1/note/stats
```

## Verification

- `systemctl is-active blinko.service` → `active`
- `systemctl is-enabled blinko.service` → `enabled`
- `curl -s -m 5 http://127.0.0.1:1111/health` → 200 OK
- `curl -s http://127.0.0.1:1111/api/v1/note/stats` → 3,711 notes
- POST search returns content correctly (sampled)

## Bug fixed in the process

The original `blinko.service` from the dead .250 had
`Environment=BLINKO_DB_PATH=/home/opc/blinko_lite.db`. But the script
(`blinko_lite.py`) reads `BLINKO_DB` (no `_PATH` suffix) — see line 35:
```python
DB_PATH = Path(os.environ.get("BLINKO_DB", "/home/opc/blinko_lite.db"))
```
So on the old box, `BLINKO_DB_PATH` was ignored and the script fell through
to the **default** `/home/opc/blinko_lite.db`. That default happened to be
correct on Oracle Linux, so nobody noticed. On Ubuntu with `/home/opc` not
existing, it failed immediately. Fixed by using the correct var name in
the translated unit.

## Audit trail

- Source code unchanged — pure stdlib Python, no dependency install needed.
- Note data preserved bit-for-bit (the `.db` was rsync'd from the orphan
  volume without modification).
- Service auto-restarts on failure (`Restart=always`, `RestartSec=5`).

## Resilience model (after this restore)

- **Primary**: Blinko on e5-mother :1111 (always-on)
- **Hot backup**: `blinko_lite.db` on phone at `_state/blinko_lite.db` (8.2 MB)
  — `scp`'d immediately after restore
- **Cold backup**: same `.db` on PC (synced when PC online)
- **Immortal**: should be committed to GitHub for true offline rebuild
- **Memory-aware client**: `blinko_status.py` (built same session) reports
  CONNECTED / DEGRADED / OFFLINE so agents announce their memory state
  honestly

## Links

- See entry `2026-05-15-002-memory-awareness-service.md` for the awareness
  layer that consumes this service.
- Cheat sheet: §3 (Blinko in external services), §4 (Blinko in service map).
