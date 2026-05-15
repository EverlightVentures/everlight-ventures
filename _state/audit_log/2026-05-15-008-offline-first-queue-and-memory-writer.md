---
id: 2026-05-15-008-offline-first-queue-and-memory-writer
title: Offline-first sync queue + memory writer + drain timer wired (the foundation primitive)
date: 2026-05-15T10:45:00-07:00
agent: phone-claude
phase: post-migration
category: 230
thread: sync-architecture
session: s-003-may15-tooling
status: completed
tags: offline-first, queue, memory-writer, drain, sync, taildrive
summary: Built sync_queue.py + memory_writer.py + sync-drain.timer (on e5-mother) + phone-boot drain hook. The offline-first bidirectional sync doctrine now has executable primitives. Every memory write (Blinko notes, agentmemory entities, audit log appends) routes through the writer, commits locally first, attempts cloud propagation, and queues on failure. Drain runs every 5 min on mother + on every phone boot. Taildrive integration plan documented but deferred -- rsync over tailnet is the current transport.
---

## What was done

Built the executable foundation for the
`feedback_offline_first_bidirectional_sync` doctrine.

**New files:**
- `03_AUTOMATION_CORE/01_Scripts/sync_queue.py` (10 KB, 280 lines):
  the queue primitive. Append-only JSONL. Per-type ship handlers
  (blinko_note, agentmemory_entity, file_replace). Reachability-gated
  drain. Atomic queue rewrites. CLI: `drain`, `depth`, `show`, `gc`.

- `03_AUTOMATION_CORE/01_Scripts/memory_writer.py` (7.3 KB, 210 lines):
  the unified write surface. All memory mutations route through
  here. Functions:
    - `write_blinko_note(content, tags)` -- local commit (SQLite or HTTP)
      first, then cloud HTTP POST; queue on failure.
    - `write_agentmemory_entity(entity)` -- merge into local graph file
      first, queue for cloud propagation always (cloud MCP has no write
      REST yet).
    - `write_audit_log(id, title, body)` -- file write + queue
      file_replace to broadcast.

**New systemd unit on e5-mother:**
- `/etc/systemd/system/sync-drain.service` (oneshot, runs the drain).
- `/etc/systemd/system/sync-drain.timer` (every 5 min, OnBootSec=2min).

**Phone boot hook updated:**
- `/root/.termux/boot/start_hive.sh` now fires
  `sync_queue.py drain` after the sync_to_mother call.

## Why

Rich's directive: "the offline-first bidirectional sync doctrine applies
to everything we're doing as far as data sinking goes between all the
devices, all the devices on tail scale and tail drive."

The need: phone could write a Blinko note while mother is unreachable;
that note would only live on phone until the next manual sync. If the
phone died first, the note was lost. The queue+drain primitive
eliminates that gap -- any write commits locally THEN propagates
eventually, with retries on failure.

The same primitive is the foundation for:
- workspace mutations (file edits)
- agentmemory knowledge-graph deltas
- audit log appends
- deal-pipeline state changes
- service config changes
- any future state mutation

One queue, every category. Pluggable ship handlers per type.

## Before

- Memory writes were direct calls (curl to Blinko HTTP, MCP tool to
  agentmemory) with no retry, no queue. If the cloud was down, the
  write happened locally but the remote sync only ran on the next
  rsync push (which only covers files, not Blinko DB rows).
- No primitive for "this write needs to reach peer X."
- `sync_to_mother.sh` push-up was one-way for workspace; no
  symmetric primitive for memory.

## After

- Every memory write commits locally instantly.
- Cloud propagation attempted immediately if reachable; queued otherwise.
- Drain runs on mother (5 min systemd timer) + on phone boot.
- Queue depth visible via `sync_queue.py depth` (currently 0 in healthy
  state; would grow during cloud outage).
- Queue entries have full provenance: id, ts, type, origin, target,
  payload, content hash, status, attempts, last_attempt, shipped_to.

## How

```python
# Local write first (fast, sync, never blocked by network)
write_blinko_note("test", tags=["hive/session"])
# returns: {"ok": true, "local_committed": true, "cloud_shipped": true, "queue_id": null}

# If cloud is down:
# returns: {"ok": true, "local_committed": true, "cloud_shipped": false, "queue_id": "abc-123"}

# Drain runs automatically:
#   e5-mother: every 5 min via sync-drain.timer
#   phone:     on boot via start_hive.sh

# Manual drain on demand:
python3 sync_queue.py drain
# returns: {"pending_before": 1, "shipped": 1, "failed": 0, "conflicts": 0}
```

## Verification

```bash
# 1. Scripts exist + executable
test -x /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/sync_queue.py
test -x /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/memory_writer.py

# 2. Smoke: happy path
python3 /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/memory_writer.py blinko \
  --content "smoke test" --tags "hive/test"
# Expect: {"ok": true, "local_committed": true, "cloud_shipped": true, ...}

# 3. Queue depth
python3 /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/sync_queue.py depth
# Expect: 0 (healthy)

# 4. Drain timer on e5-mother
ssh ubuntu@100.125.115.95 'systemctl is-active sync-drain.timer'
# Expect: active

# 5. Phone boot hook present
grep -c sync_queue /root/.termux/boot/start_hive.sh
# Expect: >= 1
```

## Audit trail

- Queue is append-only JSONL -- every write event is preserved with
  timestamp + content hash even after drain (status changes from
  pending to shipped).
- `sync_queue.py gc --days 30` cleans up old shipped entries.
- Drain failures retry up to 5 attempts before marking as
  permanently failed (operator-visible via `sync_queue.py show`).
- Conflict resolution path exists in schema (`status: conflict`) but
  no auto-merge implementation yet -- next iteration.

## Taildrive integration (deferred)

Tailscale released **Taildrive** in 2024 -- WebDAV-style file shares
between tailnet machines. It would let us mount e5-mother's workspace
directly on phone/PC as if local. Pairs naturally with the queue:
queue+drain handles WRITES; Taildrive handles "see remote view"
READS without rsync.

**Why deferred:**
- Requires Tailscale 1.64+ on all devices (verify first).
- Linux mount setup needs `davfs2`.
- Android (Termux) doesn't have native Taildrive mount yet --
  workaround needed.
- Current rsync-over-tailnet works fine and is well-proven.

**When to revisit:** after Deal 1, when we want the "feels native"
UX upgrade. The queue primitive doesn't need to change -- transport
is pluggable.

## Honest limitations

- **agentmemory write to peer is stub-quality.** The ship handler
  appends JSON to `/tmp/agentmemory_inbox.jsonl` on peer; doesn't
  actually merge into the live MCP graph. Next iteration: write
  a proper merger on the peer side or use the official Tailscale
  agentmemory write API once it exists.
- **No conflict resolution yet.** Schema supports it (`status:
  conflict`) but the drain just marks any failure as "failed" not
  "conflict." Need timestamp + hash compare logic.
- **Phone-side drain timing.** Phone is not a cron host per doctrine.
  Drain runs on boot + on every sync_to_mother. For mid-session
  drains, the operator runs `sync_queue.py drain` manually OR a
  watchdog cycle picks it up (next iteration: add to
  dashboards_watchdog).
- **No queue depth alerting yet.** If queue grows beyond N entries,
  Slack alert. Wire next.

## What this enables

- The amnesia-defense doctrine has its execution layer.
- Every future state class (deals, leads, contracts, content) gets
  offline-first for free by routing through the queue.
- When operator writes happen during cloud outage, they survive.

## Links

- HARD LAW: [[feedback-offline-first-bidirectional-sync]]
- HARD LAW: [[feedback-cloud-state-mirrors-local-always]]
- Script: `03_AUTOMATION_CORE/01_Scripts/sync_queue.py`
- Script: `03_AUTOMATION_CORE/01_Scripts/memory_writer.py`
- Unit: e5-mother `/etc/systemd/system/sync-drain.timer`
- Boot hook: `/root/.termux/boot/start_hive.sh` (sync_queue drain on boot)
