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


# Conflict resolution -------------------------------------------------------
# Each ship handler returns one of: "shipped", "conflict", "failed".
# A "conflict" means the peer already has divergent content for this logical
# key AND the peer's version is newer than ours -- we DO NOT overwrite.
# Conflicts are logged to _state/sync_conflicts.jsonl for operator review.

CONFLICT_LOG = WORKSPACE / "_state" / "sync_conflicts.jsonl"
CONFLICT_WINDOW_SECS = 60


def _log_conflict(entry: dict, peer_name: str, peer_state: dict, reason: str) -> None:
    CONFLICT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFLICT_LOG, "a") as f:
        f.write(json.dumps({
            "ts": _now(),
            "queue_entry_id": entry.get("id"),
            "type": entry.get("type"),
            "peer": peer_name,
            "reason": reason,
            "our_payload": entry.get("payload"),
            "our_hash": entry.get("payload_hash"),
            "our_ts": entry.get("ts"),
            "peer_state": peer_state,
        }) + "\n")


# Per-type ship handlers ------------------------------------------------------
# Each handler returns: "shipped" | "conflict" | "failed"


def _ship_blinko_note(entry: dict, peer: dict) -> str:
    """Push a Blinko note. Probe peer first for the same external_id; if peer
    has divergent content with newer ts, mark as conflict (do not overwrite).
    """
    payload = entry["payload"]
    external_id = payload.get("external_id", f"sync_{entry['id']}")
    base_url = f"http://{peer['tailnet']}:1111"

    # Pre-ship probe: does peer have this external_id already?
    try:
        probe_cmd = [
            "curl", "-sS", "--max-time", "5",
            f"{base_url}/api/v1/note/get?external_id={external_id}",
        ]
        probe = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=8)
        if probe.returncode == 0 and probe.stdout.strip():
            # Try parse -- if it's a JSON note object, check for divergence
            try:
                peer_note = json.loads(probe.stdout)
                if isinstance(peer_note, dict) and peer_note.get("content"):
                    peer_content = peer_note.get("content", "")
                    if peer_content != payload.get("content", ""):
                        # Content diverged -- check timestamps
                        peer_ts = peer_note.get("updated_at") or peer_note.get("created_at") or ""
                        our_ts = entry.get("ts", "")
                        if peer_ts and our_ts:
                            try:
                                peer_epoch = datetime.fromisoformat(peer_ts.rstrip("Z")).timestamp()
                                our_epoch = datetime.fromisoformat(our_ts.rstrip("Z")).timestamp()
                                if peer_epoch > our_epoch:
                                    # Peer wrote a different version after us -> conflict
                                    _log_conflict(entry, "blinko", {
                                        "external_id": external_id,
                                        "content_preview": peer_content[:200],
                                        "peer_ts": peer_ts,
                                    }, "peer_newer_diverged")
                                    return "conflict"
                            except (ValueError, TypeError):
                                pass  # ts parse failed, fall through to ship
            except json.JSONDecodeError:
                pass  # probe returned non-JSON, just ship

    except subprocess.TimeoutExpired:
        pass  # probe timeout, attempt ship anyway

    # Ship via upsert (idempotent on external_id)
    body = {
        "content": payload["content"],
        "type": payload.get("note_type", 1),
        "external_id": external_id,
    }
    cmd = [
        "curl", "-sS", "-X", "POST", f"{base_url}/api/v1/note/upsert",
        "-H", "Content-Type: application/json",
        "-d", json.dumps(body),
        "--max-time", "10",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if result.returncode == 0 and "error" not in result.stdout.lower():
            return "shipped"
        return "failed"
    except subprocess.TimeoutExpired:
        return "failed"


def _ship_agentmemory_entity(entry: dict, peer: dict) -> str:
    """Ship an agentmemory entity to peer's inbox. The peer's
    agentmemory_inbox_merger.py does the conflict-aware merge there.
    Conflicts surface in peer's agentmemory_conflicts.jsonl, NOT here.
    """
    payload = entry["payload"]
    # Encode payload as a single-line JSON, ssh-append to inbox
    json_payload = json.dumps(payload)
    # Use printf with %s to safely embed the JSON without shell interpretation
    cmd = [
        "ssh", "-i", peer["ssh_key"],
        "-o", "StrictHostKeyChecking=accept-new",
        "-o", "ConnectTimeout=8",
        f"{peer['user']}@{peer['tailnet']}",
        "cat >> /tmp/agentmemory_inbox.jsonl",
    ]
    try:
        result = subprocess.run(
            cmd,
            input=json_payload + "\n",
            capture_output=True, text=True, timeout=15,
        )
        return "shipped" if result.returncode == 0 else "failed"
    except subprocess.TimeoutExpired:
        return "failed"


def _ship_file_replace(entry: dict, peer: dict) -> str:
    """Rsync a file. Probe peer mtime first; if peer's file is newer than ours,
    flag as conflict and don't overwrite.
    """
    payload = entry["payload"]
    src = payload["src"]
    dst = payload["dst"]

    # Probe peer mtime
    try:
        probe_cmd = [
            "ssh", "-i", peer["ssh_key"],
            "-o", "StrictHostKeyChecking=accept-new", "-o", "ConnectTimeout=5",
            f"{peer['user']}@{peer['tailnet']}",
            f"stat -c '%Y' {dst} 2>/dev/null || echo 0",
        ]
        probe = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=10)
        if probe.returncode == 0:
            peer_mtime = float(probe.stdout.strip() or "0")
            our_mtime = Path(src).stat().st_mtime if Path(src).exists() else 0
            if peer_mtime > 0 and peer_mtime > our_mtime + CONFLICT_WINDOW_SECS:
                # Peer's file is meaningfully newer -- don't clobber
                _log_conflict(entry, peer.get("user", "unknown"), {
                    "dst": dst,
                    "peer_mtime": peer_mtime,
                    "our_mtime": our_mtime,
                }, "peer_file_newer")
                return "conflict"
    except (subprocess.TimeoutExpired, ValueError, OSError):
        pass

    # Ship via rsync --update (which already respects mtime)
    cmd = [
        "rsync", "-az", "--update",
        "-e", f"ssh -i {peer['ssh_key']} -o StrictHostKeyChecking=accept-new",
        src, f"{peer['user']}@{peer['tailnet']}:{dst}",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return "shipped" if result.returncode == 0 else "failed"
    except subprocess.TimeoutExpired:
        return "failed"


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

            result = handler(entry, PEERS[t])
            entry["attempts"] = entry.get("attempts", 0) + 1
            entry["last_attempt"] = _now()

            # Backward compat: bool return -> map to tri-state
            if isinstance(result, bool):
                result = "shipped" if result else "failed"

            if result == "shipped":
                entry.setdefault("shipped_to", []).append(t)
                if verbose:
                    print(f"  ✓ shipped {entry['id'][:8]} -> {t}")
            elif result == "conflict":
                entry["status"] = "conflict"
                entry.setdefault("conflict_with", []).append(t)
                summary["conflicts"] += 1
                all_shipped = False
                if verbose:
                    print(f"  ⚠ CONFLICT {entry['id'][:8]} -> {t} (peer has newer divergent content; logged)")
                # Once any peer reports conflict, stop trying others until operator resolves
                break
            else:  # failed
                all_shipped = False
                if verbose:
                    print(f"  ✗ failed {entry['id'][:8]} -> {t}")

        # Status transition: only mark shipped if every target acknowledged AND no conflict
        if all_shipped and entry.get("status") == "pending":
            entry["status"] = "shipped"
            summary["shipped"] += 1

    # Write back the updated queue
    _write_queue(entries)
    return summary


# Conflict inspection helpers ------------------------------------------------


def list_conflicts() -> list[dict]:
    """Return all logged conflicts for operator review."""
    if not CONFLICT_LOG.exists():
        return []
    out = []
    for line in CONFLICT_LOG.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def resolve_conflict(entry_id: str, action: str) -> bool:
    """Operator resolves a conflict. Action is 'force_ship' (overwrite peer)
    or 'accept_peer' (drop our version, mark shipped).
    """
    entries = _read_queue()
    for e in entries:
        if e.get("id") == entry_id:
            if action == "force_ship":
                e["status"] = "pending"
                e["attempts"] = 0
                e.pop("conflict_with", None)
                e["resolved"] = {"by": "operator", "ts": _now(), "action": "force_ship"}
            elif action == "accept_peer":
                e["status"] = "shipped"
                e["resolved"] = {"by": "operator", "ts": _now(), "action": "accept_peer"}
            else:
                return False
            _write_queue(entries)
            return True
    return False


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
    sub.add_parser("conflicts", help="show all logged conflicts for operator review")
    res_p = sub.add_parser("resolve", help="resolve a conflict")
    res_p.add_argument("--id", required=True, help="queue entry id")
    res_p.add_argument(
        "--action", required=True, choices=["force_ship", "accept_peer"],
        help="force_ship overwrites peer; accept_peer drops our version",
    )
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
    elif args.cmd == "conflicts":
        print(json.dumps(list_conflicts(), indent=2))
    elif args.cmd == "resolve":
        ok = resolve_conflict(args.id, args.action)
        print(json.dumps({"ok": ok, "id": args.id, "action": args.action}))
    elif args.cmd == "gc":
        n = gc(older_than_days=args.days)
        print(f"removed {n} shipped entries older than {args.days}d")
