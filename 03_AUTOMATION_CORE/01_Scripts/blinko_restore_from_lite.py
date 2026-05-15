#!/usr/bin/env python3
"""
blinko_restore_from_lite.py -- restore 614 Blinko notes from local BlinkoLite SQLite
into the freshly-provisioned Blinko on e5-mother.

Source: /mnt/sdcard/AA_MY_DRIVE/_logs/blinko_lite.db  (5.1 MB, 614 rows in `notes`)
Target: http://e5-mother:1111/api/v1/note/upsert  (override via BLINKO_URL env)

Idempotent: tracks success per source id in
/mnt/sdcard/AA_MY_DRIVE/_logs/blinko_restore_progress.json
so re-runs skip already-ingested notes.

Run from phone:
    python3 blinko_restore_from_lite.py
    python3 blinko_restore_from_lite.py --dry-run         # show plan
    python3 blinko_restore_from_lite.py --limit=10        # ingest first 10 only
    BLINKO_URL=http://127.0.0.1:1111 python3 ... --tunnel # via SSH tunnel
"""

from __future__ import annotations
import argparse
import json
import os
import sqlite3
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

DB_PATH = Path("/mnt/sdcard/AA_MY_DRIVE/_logs/blinko_lite.db")
PROGRESS = Path("/mnt/sdcard/AA_MY_DRIVE/_logs/blinko_restore_progress.json")
RECOVERY_LOG = Path("/mnt/sdcard/AA_MY_DRIVE/08_BACKUPS/recovery_log.md")
BLINKO_URL = os.environ.get("BLINKO_URL", "http://e5-mother:1111").rstrip("/")
UPSERT_PATH = "/api/v1/note/upsert"
LIST_PATH = "/api/v1/note/list?limit=1"

# Tunables
PER_NOTE_DELAY_SEC = 0.10
HEALTH_TIMEOUT_SEC = 8
UPSERT_TIMEOUT_SEC = 15


def health_check() -> bool:
    """Quick GET to confirm Blinko is reachable. Returns True if any HTTP response, even 401/404."""
    url = f"{BLINKO_URL}{LIST_PATH}"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=HEALTH_TIMEOUT_SEC) as r:
            return 200 <= r.status < 600
    except urllib.error.HTTPError as e:
        # Auth-protected endpoints return 401, that still proves reachability
        return 400 <= e.code < 600
    except Exception as e:
        print(f"health check FAILED: {e}", file=sys.stderr)
        return False


def load_progress() -> dict:
    if not PROGRESS.exists():
        return {"completed_ids": [], "started_at": None, "last_run": None}
    try:
        return json.loads(PROGRESS.read_text())
    except Exception:
        return {"completed_ids": [], "started_at": None, "last_run": None}


def save_progress(state: dict) -> None:
    PROGRESS.parent.mkdir(parents=True, exist_ok=True)
    PROGRESS.write_text(json.dumps(state, indent=2))


def upsert(note: dict) -> tuple[bool, str]:
    """POST a single note to Blinko. Returns (ok, body_snippet)."""
    payload = {
        "content": note["content"],
        "type": note.get("type", 1) or 1,
    }
    # Some Blinko builds accept an `id` for client-side dedup; harmless if ignored.
    if note.get("id"):
        payload["id"] = f"lite_{note['id']}"
    # Tags handling: BlinkoLite stores comma-separated; main Blinko derives from content.
    # We append a footer tag so we can audit restored notes later.
    payload["content"] = payload["content"].rstrip() + "\n\n#restored-from-blinko-lite #2026-05-11"

    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{BLINKO_URL}{UPSERT_PATH}",
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=UPSERT_TIMEOUT_SEC) as r:
            snippet = r.read(200).decode("utf-8", errors="replace")
            ok = 200 <= r.status < 300 and ('"id"' in snippet or '"success"' in snippet or r.status == 200)
            return ok, snippet[:160]
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}: {e.reason}"
    except Exception as e:
        return False, f"err: {e}"


def append_recovery_log(line: str) -> None:
    """Append a single line to recovery_log.md (auto-creates parent dir)."""
    RECOVERY_LOG.parent.mkdir(parents=True, exist_ok=True)
    with RECOVERY_LOG.open("a") as f:
        f.write(line + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=0, help="0 = all")
    parser.add_argument("--reset-progress", action="store_true")
    args = parser.parse_args(argv)

    if not DB_PATH.exists():
        print(f"FATAL: {DB_PATH} does not exist", file=sys.stderr)
        return 2

    if args.reset_progress and PROGRESS.exists():
        PROGRESS.unlink()
        print("progress file reset")

    print(f"target: {BLINKO_URL}{UPSERT_PATH}")
    if not args.dry_run:
        print("health checking target...")
        if not health_check():
            print("FATAL: Blinko unreachable. Provision e5-mother first.", file=sys.stderr)
            print("  See /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/e5_mother/README.md", file=sys.stderr)
            return 3
        print("  ok")

    state = load_progress()
    completed = set(state.get("completed_ids", []))
    if state["started_at"] is None:
        state["started_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    total = cur.execute("select count(*) from notes").fetchone()[0]
    print(f"source: {DB_PATH}  ({total} notes total, {len(completed)} already done)")

    cur.execute("select id, content, type, tags, created_at, updated_at from notes order by created_at")

    ok_count = 0
    fail_count = 0
    skipped = 0
    processed = 0

    for row in cur:
        if args.limit and processed >= args.limit:
            break
        nid, content, ntype, tags, created_at, updated_at = row

        if nid in completed:
            skipped += 1
            continue

        note = {"id": nid, "content": content, "type": ntype, "tags": tags,
                "created_at": created_at, "updated_at": updated_at}

        if args.dry_run:
            print(f"  [dry] would POST  id={nid}  len={len(content)}  created={created_at}")
            processed += 1
            continue

        ok, msg = upsert(note)
        processed += 1
        if ok:
            ok_count += 1
            completed.add(nid)
            print(f"  ok    id={nid}")
        else:
            fail_count += 1
            print(f"  FAIL  id={nid}  {msg}")

        if processed % 25 == 0:
            state["completed_ids"] = sorted(completed)
            state["last_run"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
            save_progress(state)

        time.sleep(PER_NOTE_DELAY_SEC)

    state["completed_ids"] = sorted(completed)
    state["last_run"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    save_progress(state)

    conn.close()

    summary = (
        f"\n## {time.strftime('%Y-%m-%d %H:%M PT')} -- Blinko restore run\n"
        f"- target: {BLINKO_URL}\n"
        f"- processed this run: {processed}\n"
        f"- success: {ok_count}\n"
        f"- failed: {fail_count}\n"
        f"- already-done skipped: {skipped}\n"
        f"- total notes in source: {total}\n"
        f"- total completed (cumulative): {len(completed)}\n"
    )
    print(summary)
    if not args.dry_run:
        append_recovery_log(summary)

    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
