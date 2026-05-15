---
id: 2026-05-15-002-memory-awareness-service
title: Memory awareness service shipped (blinko_status.py + activity_feed.py)
date: 2026-05-15T08:00:00-07:00
agent: phone-claude
phase: post-migration
category: 230
thread: memory-resilience
session: s-003-may15-tooling
status: completed
tags: memory, observability, tools, hive
summary: Built two stdlib-Python tools that let any agent honestly report its memory state and pull a unified activity timeline. Agents can now say "I have my memory back and here's what I remember" or "I'm operating without persistent memory right now" — instead of pretending.
---

## What was done

Built two complementary tools that any agent (or human) can call:

1. **`blinko_status.py`** — probes the Blinko service in priority order
   (tailnet hostname → tailnet IP → public IP → local SQLite fallback).
   Reports state as CONNECTED / DEGRADED / OFFLINE with note counts and
   last-sync timestamps. Output modes for humans, JSON for scripts, banners
   for agent startup announcements.

2. **`activity_feed.py`** — unified view across the distributed Hive log
   (Blinko notes, AGENT_MAILBOX entries, JSONL files, Supabase events).
   Doesn't centralize the data — gives a single command to *see* it.

Both are stdlib-only, fast, and degrade gracefully when sources are
unreachable.

## Why

Operator's directive: "I need some sort of system that identifies when
Blinko is connected and my bots have actual memory, and when Blinko is not
connected they don't have memory — like, they need to be able to tell me
'hey, this is the amount of memory we're missing right now.'"

That's the missing observability layer. The Hive's persistent memory
(Blinko on e5-mother :1111) is a single point of failure for "what do the
agents remember?" Without a way to *announce state truthfully*, agents
might silently operate without memory — losing fidelity, missing context,
duplicating work. The operator can't trust outputs if he doesn't know
whether the agent was speaking from memory or speaking blind.

Operator Truth Doctrine demands honest reporting. This is the toolchain.

## Before

- No way for an agent to know whether Blinko was reachable
- No way for the operator to verify "my agents have their memory" without
  manually `curl`ing e5-mother
- "Activity log" was distributed across 5+ formats (Blinko, mailbox, JSONL,
  Supabase, Slack) — no single command to view chronological events
- Risk of agents confidently making statements without flagging "I'm
  operating from a stale local copy from April 24"

## After

### `blinko_status.py` — usage examples

```bash
# Human-readable, one line
$ python3 03_AUTOMATION_CORE/01_Scripts/blinko_status.py
Memory: DEGRADED -- Blinko unreachable, using local fallback
(3711 notes from 2026-04-27T12:59:05.729409+00:00,
 path: /mnt/sdcard/AA_MY_DRIVE/_state/blinko_lite.db)

# JSON for scripts
$ python3 .../blinko_status.py -m json
{"state": "DEGRADED", "source_path": "...", "notes_count": 3711, ...}

# Short status line
$ python3 .../blinko_status.py -m short
degraded 3711 (local)

# Banner for agent startup
$ python3 .../blinko_status.py -m banner --agent "Marcus Cole"
[Marcus Cole] -- memory check --
  STATE   : DEGRADED -- local fallback
  source  : /mnt/sdcard/AA_MY_DRIVE/_state/blinko_lite.db
  notes   : 3711 (last sync 2026-04-27T12:59:05.729409+00:00)
  Blinko on e5-mother is unreachable. I'm reading from a local
  copy -- anything written AFTER 2026-04-27T12:59:05.729409+00:00 is
  not in my memory. Heads up.
```

Exit codes: `0=connected`, `1=degraded`, `2=offline`, `3=error`. Scripts
can branch on these.

### `activity_feed.py` — unified view

```bash
$ python3 03_AUTOMATION_CORE/01_Scripts/activity_feed.py -n 10
=== Hive activity (10 events) ===

  2026-05-15 07:30:00  [mailbox:phone]  === SESSION 2 UPDATE ===
  2026-05-14 17:50:00  [mailbox:phone]  LAST ORPHAN PASS -- partial success.
  ...
```

Filters: `--hours 24`, `--source blinko`, `--grep wholesale`.

## How (the design choices)

**Probe order for Blinko**: tailnet hostname → tailnet IP → public IP.
Public is last because tailnet should be the default path; falling through
to public means tailscale is unhappy on the calling node.

**Local fallback chain**: looks in 5 likely paths (phone canonical, phone
legacy, e5-mother itself, PC canonical, user override). First readable DB
wins. The phone got its `blinko_lite.db` synced from e5-mother as part of
the same work, so the fallback is always 3,711 notes (not the stale 614).

**Stdlib only**: `urllib.request`, `sqlite3`, `argparse`, `json`. No
`requests`, no Flask, no extra installs. Runs on Termux+proot without
friction.

**Activity feed is a VIEW not a DATABASE**: each source stays in its
native format (Blinko stays in SQLite, mailbox stays in Markdown, JSONL
stays in JSONL). The script reads them all and prints a chronological view.
"Centralized view, decentralized data."

## Verification

```bash
$ python3 blinko_status.py
Memory: DEGRADED -- Blinko unreachable, using local fallback (3711 notes...)
# Exit code: 1 (degraded as expected -- phone tailscale stale)

$ python3 activity_feed.py -n 10
=== Hive activity (10 events) ===
[shows real events from mailbox]
```

## Audit trail

- Both scripts are stdlib-only — no `pip install`, no network deps to
  audit.
- Read-only on local files; only network calls are GETs/POSTs to Blinko's
  documented API.
- No secrets handled by these tools.

## What this enables

- Agents can call `blinko_status.py -m banner` on startup and announce
  their memory state in their first reply.
- Hive dispatch can branch on exit code: skip persistent-memory writes if
  DEGRADED (no point writing to a stale fallback).
- The Moltbook dashboard's "Memory" pane pulls from `blinko_status.py -m json`.
- The Moltbook dashboard's "Recent Activity" pane pulls from `activity_feed.py`.

## Links

- See entry `2026-05-14-005-blinko-restored.md` for the service this tool
  observes.
- See entry `2026-05-15-003-moltbook-v1.md` for the dashboard that
  consumes both.
- Cheat sheet: §9 (Memory awareness service).
