"""
Everlight OS — Append-only JSONL logger.
All runs are logged to _logs/everlight_runs.jsonl
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

BASE = Path("/mnt/sdcard/AA_MY_DRIVE/everlight_os")
LOG_DIR = BASE / "_logs"
LOG_FILE = LOG_DIR / "everlight_runs.jsonl"


def _ensure_log_dir():
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def append_run(entry: dict):
    """Append a run log entry (dict or RunLogEntry.to_dict())."""
    _ensure_log_dir()
    if "timestamp" not in entry:
        entry["timestamp"] = datetime.now(timezone.utc).isoformat()
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")


def append_event(event_type: str, data: dict):
    """Append a generic event to the log."""
    _ensure_log_dir()
    line = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event_type,
        **data,
    }
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(line) + "\n")


def read_recent_runs(n: int = 20) -> list:
    """Read last N run entries from the log."""
    if not LOG_FILE.exists():
        return []
    lines = []
    with open(LOG_FILE) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    lines.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return lines[-n:]


def count_runs_today() -> int:
    """Count how many runs happened today (UTC)."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    count = 0
    if not LOG_FILE.exists():
        return 0
    with open(LOG_FILE) as f:
        for line in f:
            if today in line[:30]:
                count += 1
    return count
