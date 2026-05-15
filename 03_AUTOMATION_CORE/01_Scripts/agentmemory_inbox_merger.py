#!/usr/bin/env python3
"""agentmemory_inbox_merger.py -- drain /tmp/agentmemory_inbox.jsonl into the live graph.

Companion to sync_queue.py's _ship_agentmemory_entity handler. The ship
handler writes one entity-update JSON per line to /tmp/agentmemory_inbox.jsonl
on the peer. This merger drains the inbox into the live agentmemory_graph.json
with entity-keyed last-write-wins merge.

Run on:
  * e5-mother every 5 min via agentmemory-merge.timer
  * phone every dashboards_watchdog cycle (1 min)

Merge semantics:
  * Each entity has a `name` (unique key) per @modelcontextprotocol/server-memory schema.
  * Incoming entity replaces existing if `last_updated` is newer.
  * If timestamps are within 60s AND content hashes differ -> CONFLICT.
    Conflict entries land in agentmemory_conflicts.jsonl + Slack alert.
  * After successful merge, inbox is truncated (atomic via rename).

Schema of the live graph (matches MCP server-memory format):
  {
    "entities": [
      {"name": "Rich", "type": "operator", "facts": [...], "last_updated": "..."},
      ...
    ],
    "relations": [
      {"from": "Rich", "to": "Everlight Ventures", "kind": "ceo_of"},
      ...
    ]
  }

Schema of inbox entries (one per line):
  {"name": "Rich", "type": "operator", "facts": [...], "last_updated": "..."}
  -- OR --
  {"relation": {"from": "...", "to": "...", "kind": "..."}}
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Defaults differ per host (mother vs phone)
DEFAULT_GRAPH_PATH = Path(os.environ.get(
    "AGENTMEMORY_GRAPH",
    "/home/ubuntu/e5_data/agentmemory_graph.json"
    if Path("/home/ubuntu/e5_data").exists()
    else "/mnt/sdcard/AA_MY_DRIVE/_state/agentmemory_graph.json"
))
DEFAULT_INBOX_PATH = Path(os.environ.get(
    "AGENTMEMORY_INBOX",
    "/tmp/agentmemory_inbox.jsonl"
))
CONFLICT_LOG = Path(os.environ.get(
    "AGENTMEMORY_CONFLICTS",
    str(DEFAULT_GRAPH_PATH.parent / "agentmemory_conflicts.jsonl")
))
MERGE_AUDIT_LOG = Path(os.environ.get(
    "AGENTMEMORY_MERGE_LOG",
    str(DEFAULT_GRAPH_PATH.parent / "agentmemory_merge.log")
))

CONFLICT_WINDOW_SECS = 60  # if timestamps within 60s and hashes differ -> conflict


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash_entity(e: dict) -> str:
    """Stable hash of an entity's content (excluding last_updated metadata)."""
    body = {k: v for k, v in e.items() if k != "last_updated"}
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()


def _parse_ts(s: str | None) -> float:
    """Parse ISO timestamp into epoch seconds. Returns 0 on failure."""
    if not s:
        return 0.0
    try:
        return datetime.fromisoformat(s).timestamp()
    except (ValueError, TypeError):
        return 0.0


def _load_graph(path: Path) -> dict:
    if not path.exists():
        return {"entities": [], "relations": []}
    try:
        d = json.loads(path.read_text())
        if not isinstance(d, dict):
            return {"entities": [], "relations": []}
        d.setdefault("entities", [])
        d.setdefault("relations", [])
        return d
    except json.JSONDecodeError:
        return {"entities": [], "relations": []}


def _atomic_write(path: Path, data: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(json.dumps(data, indent=2))
    tmp.replace(path)


def _read_inbox(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def _archive_inbox(path: Path, archive_root: Path | None = None) -> None:
    """Move the drained inbox to a timestamped archive so we never lose merge history.

    Archive lands NEXT TO THE GRAPH (persistent storage), NOT next to the inbox
    which is typically /tmp (wiped on reboot). Per feedback_no_trash_until_deal1
    we never delete; we archive.
    """
    if not path.exists() or path.stat().st_size == 0:
        return
    if archive_root is None:
        archive_root = DEFAULT_GRAPH_PATH.parent
    archive_dir = archive_root / "agentmemory_inbox_archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive_path = archive_dir / f"inbox_{int(time.time())}.jsonl"
    shutil.move(str(path), str(archive_path))


def _log_conflict(incoming: dict, existing: dict, reason: str) -> None:
    """Append conflict to conflicts log for operator review."""
    CONFLICT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFLICT_LOG, "a") as f:
        f.write(json.dumps({
            "ts": _now(),
            "reason": reason,
            "incoming": incoming,
            "existing": existing,
        }) + "\n")


def _log_merge_audit(line: str) -> None:
    MERGE_AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(MERGE_AUDIT_LOG, "a") as f:
        f.write(f"[{_now()}] {line}\n")


def merge_entity(graph: dict, incoming: dict) -> tuple[str, dict | None]:
    """Merge a single incoming entity into the graph.

    Returns: (action, conflict_record_or_none)
    Where action is one of: "added", "updated", "skipped_older", "skipped_same", "conflict".
    """
    name = incoming.get("name")
    if not name:
        return ("skipped_invalid", None)

    entities = graph["entities"]
    existing_idx = next(
        (i for i, e in enumerate(entities) if e.get("name") == name),
        None,
    )

    incoming = dict(incoming)
    incoming.setdefault("last_updated", _now())

    if existing_idx is None:
        # New entity -- just add
        entities.append(incoming)
        return ("added", None)

    existing = entities[existing_idx]
    inc_hash = _hash_entity(incoming)
    exi_hash = _hash_entity(existing)

    if inc_hash == exi_hash:
        # Same content, no-op
        return ("skipped_same", None)

    inc_ts = _parse_ts(incoming.get("last_updated"))
    exi_ts = _parse_ts(existing.get("last_updated"))

    if inc_ts == 0 and exi_ts == 0:
        # No timestamps anywhere -- treat as last-write-wins, incoming wins
        entities[existing_idx] = incoming
        return ("updated", None)

    if abs(inc_ts - exi_ts) <= CONFLICT_WINDOW_SECS:
        # Concurrent writes with diverged content -> conflict
        _log_conflict(incoming, existing, "concurrent_diverged")
        return ("conflict", {"incoming": incoming, "existing": existing})

    if inc_ts > exi_ts:
        entities[existing_idx] = incoming
        return ("updated", None)
    else:
        # Incoming is older than existing -- drop
        return ("skipped_older", None)


def merge_relation(graph: dict, relation: dict) -> str:
    """Merge a relation. Relations are tuples (from, to, kind) -- dedupe on those."""
    rels = graph["relations"]
    key = (relation.get("from"), relation.get("to"), relation.get("kind"))
    for r in rels:
        if (r.get("from"), r.get("to"), r.get("kind")) == key:
            return "skipped_same"
    rels.append(relation)
    return "added"


def drain(
    inbox_path: Path = DEFAULT_INBOX_PATH,
    graph_path: Path = DEFAULT_GRAPH_PATH,
    verbose: bool = False,
) -> dict:
    """Drain the inbox into the graph. Returns summary."""
    inbox = _read_inbox(inbox_path)
    if not inbox:
        return {"processed": 0, "added": 0, "updated": 0, "conflicts": 0, "skipped": 0}

    graph = _load_graph(graph_path)
    summary = {
        "processed": len(inbox),
        "added": 0,
        "updated": 0,
        "conflicts": 0,
        "skipped_older": 0,
        "skipped_same": 0,
        "skipped_invalid": 0,
        "relations_added": 0,
    }

    for item in inbox:
        # Distinguish entity from relation
        if "relation" in item and isinstance(item["relation"], dict):
            action = merge_relation(graph, item["relation"])
            if action == "added":
                summary["relations_added"] += 1
            if verbose:
                rel = item["relation"]
                print(f"  relation {action}: {rel.get('from')} --{rel.get('kind')}--> {rel.get('to')}")
            continue

        # Otherwise treat as entity
        action, _ = merge_entity(graph, item)
        if action == "added":
            summary["added"] += 1
        elif action == "updated":
            summary["updated"] += 1
        elif action == "conflict":
            summary["conflicts"] += 1
        elif action == "skipped_older":
            summary["skipped_older"] += 1
        elif action == "skipped_same":
            summary["skipped_same"] += 1
        else:
            summary["skipped_invalid"] += 1

        if verbose:
            print(f"  entity {action}: {item.get('name', '<unnamed>')}")

    _atomic_write(graph_path, graph)
    _archive_inbox(inbox_path, archive_root=graph_path.parent)
    _log_merge_audit(
        f"drained {summary['processed']} items: "
        f"+{summary['added']} new, ~{summary['updated']} updated, "
        f"!{summary['conflicts']} conflicts, -{summary['skipped_older']+summary['skipped_same']} skipped, "
        f"{summary['relations_added']} new relations"
    )

    return summary


def status(graph_path: Path = DEFAULT_GRAPH_PATH, inbox_path: Path = DEFAULT_INBOX_PATH) -> dict:
    graph = _load_graph(graph_path)
    inbox = _read_inbox(inbox_path)
    return {
        "graph_path": str(graph_path),
        "graph_entities": len(graph.get("entities", [])),
        "graph_relations": len(graph.get("relations", [])),
        "inbox_path": str(inbox_path),
        "inbox_pending": len(inbox),
        "conflict_log": str(CONFLICT_LOG),
        "conflict_log_exists": CONFLICT_LOG.exists(),
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("drain", help="merge inbox into graph")
    d.add_argument("--verbose", "-v", action="store_true")
    d.add_argument("--inbox", default=str(DEFAULT_INBOX_PATH))
    d.add_argument("--graph", default=str(DEFAULT_GRAPH_PATH))
    sub.add_parser("status", help="show graph + inbox state")

    args = ap.parse_args()
    if args.cmd == "drain":
        r = drain(Path(args.inbox), Path(args.graph), verbose=args.verbose)
        print(json.dumps(r, indent=2))
    elif args.cmd == "status":
        print(json.dumps(status(), indent=2))
