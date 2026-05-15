#!/usr/bin/env python3
"""session_export_to_mailbox.py -- append a session summary to AGENT_MAILBOX.md.

The fail-safe sync layer per HARD LAW feedback_exit_exports_session_to_mailbox.
Triggered when Rich types `exit` -- Claude composes the summary, this script
formats + appends with atomic write.

Format of each appended entry:
    ## [YYYY-MM-DD HH:MM PT] Session: <auto title from first H1 or first 60 chars>
    <summary markdown body>
    ---

The mailbox file is append-only at the entry level (we never rewrite existing
entries) and atomic at the file level (tmp + rename) so concurrent writes
don't truncate.

Usage:
    # via stdin (Claude pipes the markdown)
    echo "## What I did\\n- thing 1\\n- thing 2" | session_export_to_mailbox.py

    # via file
    session_export_to_mailbox.py --file /tmp/session.md

    # with explicit title
    session_export_to_mailbox.py --title "Sync gaps closed" --file /tmp/session.md

    # dry-run
    session_export_to_mailbox.py --file /tmp/session.md --dry-run
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

WORKSPACE = Path("/mnt/sdcard/AA_MY_DRIVE")
MAILBOX = WORKSPACE / "_state" / "AGENT_MAILBOX.md"
PT_OFFSET = timedelta(hours=-7)  # PDT; switches to -8 in winter -- accept the drift


def _pt_now() -> datetime:
    return datetime.now(timezone.utc) + PT_OFFSET


def _ts_human() -> str:
    return _pt_now().strftime("%Y-%m-%d %H:%M PT")


def _ts_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _derive_title(body: str, fallback: str = "Session checkpoint") -> str:
    """Extract a title from the body's first H1 or first non-empty meaningful line."""
    for line in body.splitlines():
        line = line.strip()
        if not line:
            continue
        # First H1
        if line.startswith("# "):
            return line[2:].strip()[:80]
        # First H2 if no H1
        if line.startswith("## "):
            return line[3:].strip()[:80]
        # First non-heading line
        if not line.startswith("#") and len(line) > 10:
            return line[:60].rstrip(".:") + ("..." if len(line) > 60 else "")
    return fallback


def _ensure_mailbox() -> None:
    """Create the mailbox with a header if it doesn't exist."""
    if MAILBOX.exists():
        return
    MAILBOX.parent.mkdir(parents=True, exist_ok=True)
    MAILBOX.write_text(
        "# AGENT MAILBOX\n\n"
        "Chronological session diary -- the fail-safe sync layer.\n"
        "Per HARD LAW feedback-exit-exports-session-to-mailbox: every chat\n"
        "session ends with an entry here. If Blinko/agentmemory/queue all\n"
        "break, this is how agents on any device catch up.\n\n"
        "Format: append-only. Newest entries at the bottom. Each entry has\n"
        "a timestamp, derived title, and the session's work narrative.\n\n"
        "---\n\n"
    )


def _atomic_append(content: str) -> None:
    """Append to MAILBOX atomically. Read existing, concat, tmp + rename."""
    _ensure_mailbox()
    existing = MAILBOX.read_text()
    new_content = existing.rstrip() + "\n\n" + content.rstrip() + "\n\n---\n"
    tmp = MAILBOX.with_suffix(".md.tmp")
    tmp.write_text(new_content)
    tmp.replace(MAILBOX)


def append_session(
    body: str,
    title: str | None = None,
    dry_run: bool = False,
) -> dict:
    """Append a session entry to the mailbox. Returns metadata."""
    body = body.rstrip()
    if not body:
        return {"ok": False, "error": "empty body, nothing to append"}

    derived_title = title or _derive_title(body)
    ts_human = _ts_human()
    ts_iso = _ts_iso()

    # Compose the entry
    header = f"## [{ts_human}] Session: {derived_title}\n\n"
    # Add a small metadata line for grep-ability
    meta = f"<!-- session_iso={ts_iso} | size={len(body)}b -->\n\n"
    entry = header + meta + body

    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "title": derived_title,
            "ts": ts_iso,
            "size_bytes": len(entry),
            "would_write_to": str(MAILBOX),
            "preview_first_400": entry[:400],
        }

    _atomic_append(entry)

    return {
        "ok": True,
        "title": derived_title,
        "ts": ts_iso,
        "ts_human": ts_human,
        "appended_bytes": len(entry),
        "mailbox_path": str(MAILBOX),
        "mailbox_total_size": MAILBOX.stat().st_size,
    }


def queue_for_sync() -> dict:
    """If sync_queue is available, queue a file_replace for the mailbox so
    peers get the updated copy promptly (rather than waiting for the next
    full sync_to_mother run).
    """
    try:
        sys.path.insert(0, str(WORKSPACE / "03_AUTOMATION_CORE" / "01_Scripts"))
        import sync_queue
        entry_id = sync_queue.enqueue(
            type="file_replace",
            target="*",
            payload={
                "src": str(MAILBOX),
                "dst": "/home/ubuntu/AA_MY_DRIVE/_state/AGENT_MAILBOX.md",
            },
        )
        return {"queued": True, "entry_id": entry_id}
    except Exception as e:
        return {"queued": False, "error": str(e)[:100]}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file", help="read body from file instead of stdin")
    ap.add_argument("--title", help="explicit title override (default: derived from body)")
    ap.add_argument("--dry-run", action="store_true", help="show what would be written, don't write")
    ap.add_argument("--no-queue", action="store_true", help="skip queueing for sync (default: queue)")
    args = ap.parse_args()

    if args.file:
        body = Path(args.file).read_text()
    else:
        body = sys.stdin.read()

    if not body.strip():
        print(json.dumps({"ok": False, "error": "no body provided (empty stdin or empty file)"}))
        return 1

    result = append_session(body, title=args.title, dry_run=args.dry_run)

    if not args.dry_run and result.get("ok") and not args.no_queue:
        result["sync"] = queue_for_sync()

    print(json.dumps(result, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
