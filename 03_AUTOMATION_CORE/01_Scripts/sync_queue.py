"""sync_queue.py -- the offline-first write queue primitive.

Per HARD LAW feedback_offline_first_bidirectional_sync: every state mutation
on phone or cloud needs to PROPAGATE to the other side eventually. When the
other side is unreachable, writes append to a local queue and ship later.

This module is the queue primitive used by:
  * memory_writer.py (Blinko notes, agentmemory edits)
  * audit_appender.py (audit-log entries)
  * generic sync_to_mother / sync_from_mother flows
  * future: deal-pipeline state, workspace mutations, etc.

Queue format: JSONL (one JSON object per line, append-only).
Schema:
  {
    "id": "uuid",
    "ts": "2026-05-15T10:00:00-07:00",
    "type": "blinko_note" | "agentmemory_entity" | "audit_log" | "file_replace",
    "origin": "phone" | "mother" | "pc",
    "target": "mother" | "phone" | "pc" | "*",  # * means broadcast to all peers
    "payload": {...},      # the actual content to ship
    "payload_hash": "sha256...",
    "status": "pending" | "shipped" | "failed" | "conflict",
    "attempts": 0,
    "last_attempt": "...",
    "shipped_to": []       # which targets confirmed delivery
  }

Usage:
  from sync_queue import enqueue, drain, queue_depth

  enqueue(type="blinko_note", target="mother", payload={"content": "...", "tags": [...]})
  drain()  # ships everything pending to reachable targets
  depth = queue_depth()  # how many pending writes
"""
from __future__ import annotations

import hashlib
import json
import os
import socket
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

WORKSPACE = Path("/mnt/sdcard/AA_MY_DRIVE")
QUEUE_PATH = WORKSPACE / "_state" / "sync_queue.jsonl"
ORIGIN = os.environ.get("SYNC_ORIGIN", socket.gethostname())  # phone hostname
PEERS = {
    "mother": {
        "tailnet": "100.125.115.95",
        "user": "ubuntu",
        "ssh_key": "/root/.ssh/github_deploy",
    },
    "pc": {
        "tailnet": "100.93.253.49",
        "user": "richgee",
        "ssh_key": "/root/.ssh/phone_to_arch",
    },
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def _ensure_queue() -> None:
    QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not QUEUE_PATH.exists():
        QUEUE_PATH.touch()


def enqueue(
    type: str,
    target: str,
    payload: dict[str, Any],
    origin: str = ORIGIN,
) -> str:
    """Append an entry to the queue; returns the entry id."""
    _ensure_queue()
    entry_id = str(uuid.uuid4())
    entry = {
        "id": entry_id,
        "ts": _now(),
        "type": type,
        "origin": origin,
        "target": target,
        "payload": payload,
        "payload_hash": _hash(payload),
        "status": "pending",
        "attempts": 0,
        "last_attempt": None,
        "shipped_to": [],
    }
    with open(QUEUE_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")
    return entry_id


def _read_queue() -> list[dict]:
    _ensure_queue()
    out = []
    with open(QUEUE_PATH) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def _write_queue(entries: list[dict]) -> None:
    """Atomic rewrite of the queue."""
    tmp = QUEUE_PATH.with_suffix(".jsonl.tmp")
    with open(tmp, "w") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")
    tmp.replace(QUEUE_PATH)


def queue_depth() -> int:
    """Count pending entries."""
    return sum(1 for e in _read_queue() if e.get("status") == "pending")


def _is_reachable(target: str) -> bool:
    """Check if a peer is reachable on the tailnet (quick ping + ssh test)."""
    if target not in PEERS:
        return False
    p = PEERS[target]
    # Fast TCP probe
    try:
        with socket.create_connection((p["tailnet"], 22), timeout=3):
            return True
    except (OSError, socket.timeout):
        return False


# Per-type ship handlers ------------------------------------------------------


def _ship_blinko_note(entry: dict, peer: dict) -> bool:
    """Push a Blinko note to a peer's Blinko endpoint via the upsert API."""
    payload = entry["payload"]
    url = f"http://{peer['tailnet']}:1111/api/v1/note/upsert"
    body = {
        "content": payload["content"],
        "type": payload.get("note_type", 1),
        "external_id": f"sync_{entry['id']}",
    }
    cmd = [
        "curl", "-sS", "-X", "POST", url,
        "-H", "Content-Type: application/json",
        "-d", json.dumps(body),
        "--max-time", "10",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return result.returncode == 0 and "error" not in result.stdout.lower()
    except subprocess.TimeoutExpired:
        return False


def _ship_agentmemory_entity(entry: dict, peer: dict) -> bool:
    """Push an agentmemory knowledge graph entity update to peer's MCP."""
    # The agentmemory MCP doesn't expose REST directly -- the proxy serves SSE.
    # For now, ship by writing to the graph file via SSH (operator-trusted).
    payload = entry["payload"]
    graph_path = "/home/ubuntu/e5_data/agentmemory_graph.json" if peer["user"] == "ubuntu" else "/home/richgee/AA_MY_DRIVE/_state/agentmemory_graph.json"
    cmd = [
        "ssh", "-i", peer["ssh_key"], "-o", "StrictHostKeyChecking=accept-new",
        f"{peer['user']}@{peer['tailnet']}",
        # Append-merge style: caller is responsible for the operation already
        # being a delta. For now we just touch the file -- proper merge needs the
        # knowledge-graph library (next iteration).
        f"echo '{json.dumps(payload).replace(chr(39), chr(34))}' >> /tmp/agentmemory_inbox.jsonl",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        return False


def _ship_file_replace(entry: dict, peer: dict) -> bool:
    """Rsync a file from local to peer's path."""
    payload = entry["payload"]
    src = payload["src"]
    dst = payload["dst"]
    cmd = [
        "rsync", "-az", "--update",
        "-e", f"ssh -i {peer['ssh_key']} -o StrictHostKeyChecking=accept-new",
        src, f"{peer['user']}@{peer['tailnet']}:{dst}",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        return False


SHIP_HANDLERS: dict[str, Callable] = {
    "blinko_note": _ship_blinko_note,
    "agentmemory_entity": _ship_agentmemory_entity,
    "file_replace": _ship_file_replace,
    # "audit_log": _ship_audit_log,  # next iteration
}


def drain(max_attempts: int = 5, verbose: bool = False) -> dict:
    """Drain pending queue entries to their targets.

    Returns a summary dict: {pending_before, shipped, failed, conflicts}.
    """
    entries = _read_queue()
    pending = [e for e in entries if e.get("status") == "pending"]
    summary = {
        "pending_before": len(pending),
        "shipped": 0,
        "failed": 0,
        "conflicts": 0,
        "skipped_unreachable": 0,
    }

    for entry in entries:
        if entry.get("status") != "pending":
            continue
        if entry.get("attempts", 0) >= max_attempts:
            entry["status"] = "failed"
            summary["failed"] += 1
            continue

        target = entry["target"]
        targets = list(PEERS.keys()) if target == "*" else [target]

        all_shipped = True
        for t in targets:
            if t in entry.get("shipped_to", []):
                continue
            if not _is_reachable(t):
                if verbose:
                    print(f"  skip {entry['id'][:8]} -> {t} (unreachable)")
                summary["skipped_unreachable"] += 1
                all_shipped = False
                continue

            handler = SHIP_HANDLERS.get(entry["type"])
            if not handler:
                if verbose:
                    print(f"  skip {entry['id'][:8]} -> {t} (no handler for {entry['type']})")
                all_shipped = False
                continue

            ok = handler(entry, PEERS[t])
            entry["attempts"] = entry.get("attempts", 0) + 1
            entry["last_attempt"] = _now()

            if ok:
                entry.setdefault("shipped_to", []).append(t)
                if verbose:
                    print(f"  ✓ shipped {entry['id'][:8]} -> {t}")
            else:
                all_shipped = False
                if verbose:
                    print(f"  ✗ failed {entry['id'][:8]} -> {t}")

        if all_shipped:
            entry["status"] = "shipped"
            summary["shipped"] += 1

    # Write back the updated queue
    _write_queue(entries)
    return summary


def gc(older_than_days: int = 30) -> int:
    """Garbage-collect successfully-shipped entries older than N days."""
    entries = _read_queue()
    cutoff = time.time() - older_than_days * 86400
    kept = []
    removed = 0
    for e in entries:
        if e.get("status") == "shipped":
            try:
                ts = datetime.fromisoformat(e["ts"]).timestamp()
                if ts < cutoff:
                    removed += 1
                    continue
            except (ValueError, KeyError):
                pass
        kept.append(e)
    _write_queue(kept)
    return removed


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("drain", help="ship pending entries")
    sub.add_parser("depth", help="show queue depth")
    sub.add_parser("show", help="show all pending entries")
    gc_p = sub.add_parser("gc", help="garbage-collect old shipped entries")
    gc_p.add_argument("--days", type=int, default=30)
    args = ap.parse_args()

    if args.cmd == "drain":
        summary = drain(verbose=True)
        print(json.dumps(summary, indent=2))
    elif args.cmd == "depth":
        print(queue_depth())
    elif args.cmd == "show":
        pending = [e for e in _read_queue() if e.get("status") == "pending"]
        print(json.dumps(pending, indent=2))
    elif args.cmd == "gc":
        n = gc(older_than_days=args.days)
        print(f"removed {n} shipped entries older than {args.days}d")
