#!/usr/bin/env python3
"""session_save.py - Stop hook that preserves session transcript to disk.

Triggered on Claude Code's Stop event. Reads any information Claude Code exposes
on stdin (the hook protocol passes a JSON blob), extracts session id + working
directory + minimal metadata, and writes a session manifest to
`_logs/sessions/YYYY-MM-DD_HH-MM_<session_id>.md`.

This is the first piece of the file-over-AI guarantee for Claude Code sessions.
The transcript text itself requires more plumbing (Claude Code's hook protocol
doesn't currently expose the full message stream to Stop hooks) -- this script
captures what IS exposed and bookmarks a pointer so future work can extend it.

Exit code 0 always (non-blocking, informational).
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    try:
        payload = json.load(sys.stdin) if not sys.stdin.isatty() else {}
    except (json.JSONDecodeError, OSError):
        payload = {}

    now = datetime.now(timezone.utc)
    session_id = str(payload.get("session_id", "unknown"))[:16]
    cwd = payload.get("cwd", "")
    event = payload.get("hook_event_name", "Stop")

    log_dir = Path("/mnt/sdcard/AA_MY_DRIVE/_logs/sessions")
    log_dir.mkdir(parents=True, exist_ok=True)

    ts = now.strftime("%Y-%m-%d_%H-%M")
    path = log_dir / f"{ts}_{session_id}.md"

    header = f"# Claude Code Session {session_id}\n\nOpened: {ts} UTC\n\n---\n\n"
    existing = path.read_text(encoding="utf-8") if path.exists() else header

    entry = (
        f"## {event} at {now.isoformat()}\n\n"
        f"- cwd: `{cwd}`\n"
        f"- payload keys: {sorted(payload.keys())}\n"
    )
    path.write_text(existing + entry, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
