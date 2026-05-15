"""memory_writer.py -- the unified write surface for ALL memory mutations.

Per HARD LAW feedback_offline_first_bidirectional_sync: writes commit locally
first, then propagate. If the cloud peer is unreachable, the write queues
in sync_queue.jsonl and ships on the next drain.

This module replaces ad-hoc direct calls to:
  * curl http://e5-mother:1111/api/v1/note/upsert  (Blinko)
  * agentmemory MCP write tools
  * direct edits to _state/agentmemory_graph.json

Callers should route ALL memory mutations through here so the queue stays
authoritative for every change.

Usage:
  from memory_writer import write_blinko_note, write_agentmemory_entity, write_audit_log

  write_blinko_note(content="...", tags=["hive/session"])
  write_agentmemory_entity({"entity": "Rich", "type": "operator", "facts": [...]})
"""
from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

# Import sync_queue from same dir
sys.path.insert(0, str(Path(__file__).parent))
import sync_queue

WORKSPACE = Path("/mnt/sdcard/AA_MY_DRIVE")
PHONE_BLINKO_DB = WORKSPACE / "_state" / "blinko_lite.db"
PHONE_AGENTMEM = WORKSPACE / "_state" / "agentmemory_graph.json"
PHONE_BLINKO_URL = "http://127.0.0.1:1111"
MOTHER_BLINKO_URL = "http://100.125.115.95:1111"


def _try_remote(url: str, body: dict, timeout: float = 5.0) -> tuple[bool, str]:
    """Try a remote POST; return (success, response_text)."""
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return True, r.read().decode()
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e:
        return False, str(e)


def _local_blinko_write(content: str, tags: list[str], external_id: str | None = None) -> bool:
    """Direct write to phone-side blinko_lite.db. Used when remote is unreachable."""
    try:
        con = sqlite3.connect(PHONE_BLINKO_DB)
        try:
            c = con.cursor()
            ts = int(time.time())
            ext = external_id or f"local_{ts}"
            tag_str = ",".join(tags) if tags else ""
            c.execute(
                "INSERT OR REPLACE INTO notes(id, content, created_at, tags) VALUES (?, ?, ?, ?)",
                (ext, content, ts, tag_str),
            )
            con.commit()
            return True
        finally:
            con.close()
    except sqlite3.Error:
        return False


def write_blinko_note(
    content: str,
    tags: list[str] | None = None,
    note_type: int = 1,
) -> dict[str, Any]:
    """Write a Blinko note. Local-first; queue for cloud if unreachable.

    Returns a dict with: {ok, local_committed, cloud_shipped, queue_id}.
    """
    tags = tags or []
    result = {"ok": False, "local_committed": False, "cloud_shipped": False, "queue_id": None}

    # Step 1: local write (phone BlinkoLite)
    local_ok = False
    # Try the local Blinko service first (HTTP)
    local_url = f"{PHONE_BLINKO_URL}/api/v1/note/upsert"
    ok, _ = _try_remote(local_url, {"content": content, "type": note_type}, timeout=2)
    if ok:
        local_ok = True
    else:
        # Fall back to direct SQLite write
        local_ok = _local_blinko_write(content, tags)

    result["local_committed"] = local_ok

    # Step 2: try cloud write
    cloud_url = f"{MOTHER_BLINKO_URL}/api/v1/note/upsert"
    cloud_ok, _ = _try_remote(cloud_url, {"content": content, "type": note_type}, timeout=4)
    result["cloud_shipped"] = cloud_ok

    # Step 3: if cloud failed, queue it
    if not cloud_ok:
        result["queue_id"] = sync_queue.enqueue(
            type="blinko_note",
            target="mother",
            payload={"content": content, "tags": tags, "note_type": note_type},
        )

    result["ok"] = local_ok  # ok if we got AT LEAST local commit
    return result


def write_agentmemory_entity(entity: dict[str, Any]) -> dict[str, Any]:
    """Write/merge an agentmemory knowledge-graph entity.

    Local-first: merge into _state/agentmemory_graph.json.
    Cloud: queued (the MCP doesn't expose write REST yet; queue + drain
    via ssh-append-then-merge handler).
    """
    result = {"ok": False, "local_committed": False, "queue_id": None}

    # Step 1: local merge
    try:
        graph = {}
        if PHONE_AGENTMEM.exists():
            try:
                graph = json.loads(PHONE_AGENTMEM.read_text())
            except json.JSONDecodeError:
                graph = {}
        if not isinstance(graph, dict):
            graph = {}
        entities = graph.setdefault("entities", [])
        # Replace or append by entity name
        name = entity.get("name") or entity.get("entity") or f"unnamed_{int(time.time())}"
        existing_idx = next(
            (i for i, e in enumerate(entities) if e.get("name") == name),
            None,
        )
        if existing_idx is not None:
            entities[existing_idx] = {**entities[existing_idx], **entity, "name": name}
        else:
            entities.append({**entity, "name": name})
        PHONE_AGENTMEM.write_text(json.dumps(graph, indent=2))
        result["local_committed"] = True
    except OSError:
        result["local_committed"] = False

    # Step 2: queue cloud propagation (no direct write API)
    result["queue_id"] = sync_queue.enqueue(
        type="agentmemory_entity",
        target="mother",
        payload=entity,
    )

    result["ok"] = result["local_committed"]
    return result


def write_audit_log(
    entry_id: str,
    title: str,
    body: str,
    category: int = 100,
) -> dict[str, Any]:
    """Append an audit-log entry. Local-first; queue propagation to peers."""
    result = {"ok": False, "local_committed": False, "queue_id": None}

    audit_dir = WORKSPACE / "_state" / "audit_log"
    audit_dir.mkdir(parents=True, exist_ok=True)
    md_path = audit_dir / f"{entry_id}.md"

    try:
        md_path.write_text(body)
        result["local_committed"] = True
    except OSError:
        result["local_committed"] = False

    # Queue file_replace to peers
    result["queue_id"] = sync_queue.enqueue(
        type="file_replace",
        target="*",  # broadcast to all peers
        payload={
            "src": str(md_path),
            "dst": f"/home/ubuntu/AA_MY_DRIVE/_state/audit_log/{entry_id}.md",  # mother
        },
    )

    result["ok"] = result["local_committed"]
    return result


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    bp = sub.add_parser("blinko", help="write a Blinko note")
    bp.add_argument("--content", required=True)
    bp.add_argument("--tags", default="")

    ap_p = sub.add_parser("agentmem", help="write an agentmemory entity (JSON)")
    ap_p.add_argument("--json", required=True, help="JSON entity")

    args = ap.parse_args()

    if args.cmd == "blinko":
        tags = [t.strip() for t in args.tags.split(",") if t.strip()]
        r = write_blinko_note(args.content, tags=tags)
        print(json.dumps(r, indent=2))
    elif args.cmd == "agentmem":
        entity = json.loads(args.json)
        r = write_agentmemory_entity(entity)
        print(json.dumps(r, indent=2))
