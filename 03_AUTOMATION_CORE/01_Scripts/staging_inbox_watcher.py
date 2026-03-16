#!/usr/bin/env python3
"""
staging_inbox_watcher.py - Everlight Staging Inbox Auto-Router
Owner: 26_logistics_commander

Watches 07_STAGING/Inbox/ for new files and routes them to
Processing/ or Review/ based on file type, logging every move.

Usage:
  python3 staging_inbox_watcher.py          # Watch continuously (use with cron or tmux)
  python3 staging_inbox_watcher.py --once   # Process inbox once and exit
  python3 staging_inbox_watcher.py --dry-run  # Preview moves, no actual changes

Requires: pip install watchdog (for continuous mode)
Fallback: poll mode if watchdog not available
"""

import os
import sys
import json
import shutil
import argparse
import time
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

BASE = Path(__file__).resolve().parents[2]  # AA_MY_DRIVE root
INBOX = BASE / "07_STAGING" / "Inbox"
PROCESSING = BASE / "07_STAGING" / "Processing"
REVIEW = BASE / "07_STAGING" / "Review"
LOG_DIR = BASE / "_logs" / "sync"
LOG_FILE = LOG_DIR / "inbox_moves.jsonl"

PT = ZoneInfo("America/Los_Angeles")

# File type -> destination + tag
ROUTING_TABLE = {
    # Content / writing -> Processing for agent review
    ".md":   {"dest": PROCESSING, "tag": "content",     "notify": "agent-content-strategy"},
    ".txt":  {"dest": PROCESSING, "tag": "content",     "notify": "agent-content-strategy"},
    ".docx": {"dest": PROCESSING, "tag": "content",     "notify": "agent-content-strategy"},
    ".pdf":  {"dest": PROCESSING, "tag": "content",     "notify": "agent-content-strategy"},
    # Data files -> Processing for analytics
    ".csv":  {"dest": PROCESSING, "tag": "data",        "notify": "agent-analytics-auditor"},
    ".json": {"dest": PROCESSING, "tag": "data",        "notify": "agent-analytics-auditor"},
    ".xlsx": {"dest": PROCESSING, "tag": "data",        "notify": "agent-analytics-auditor"},
    # Code -> Review for QA gate before use
    ".py":   {"dest": REVIEW,     "tag": "code",        "notify": "agent-ops-logs"},
    ".sh":   {"dest": REVIEW,     "tag": "code",        "notify": "agent-ops-logs"},
    ".js":   {"dest": REVIEW,     "tag": "code",        "notify": "agent-ops-logs"},
    ".ts":   {"dest": REVIEW,     "tag": "code",        "notify": "agent-ops-logs"},
    # Media -> Processing for creative pipeline
    ".jpg":  {"dest": PROCESSING, "tag": "media",       "notify": "agent-creative-prompts"},
    ".jpeg": {"dest": PROCESSING, "tag": "media",       "notify": "agent-creative-prompts"},
    ".png":  {"dest": PROCESSING, "tag": "media",       "notify": "agent-creative-prompts"},
    ".webp": {"dest": PROCESSING, "tag": "media",       "notify": "agent-creative-prompts"},
    ".gif":  {"dest": PROCESSING, "tag": "media",       "notify": "agent-creative-prompts"},
    ".mp4":  {"dest": PROCESSING, "tag": "media",       "notify": "agent-creative-prompts"},
    # Config/yaml -> Review for safety check
    ".yaml": {"dest": REVIEW,     "tag": "config",      "notify": "agent-approvals"},
    ".yml":  {"dest": REVIEW,     "tag": "config",      "notify": "agent-approvals"},
    ".toml": {"dest": REVIEW,     "tag": "config",      "notify": "agent-approvals"},
    ".env":  {"dest": REVIEW,     "tag": "config",      "notify": "agent-approvals"},
}

DEFAULT_ROUTE = {"dest": PROCESSING, "tag": "unknown", "notify": "ai-war-room"}


def now_pt_str():
    return datetime.now(PT).strftime("%Y-%m-%d %H:%M:%S PT")


def log_move(src: Path, dest: Path, tag: str, dry_run: bool = False):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": now_pt_str(),
        "file": src.name,
        "from": str(src.parent.relative_to(BASE)),
        "to": str(dest.parent.relative_to(BASE)),
        "tag": tag,
        "dry_run": dry_run,
    }
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")


def route_file(filepath: Path, dry_run: bool = False) -> bool:
    """Move one file from inbox to its destination. Returns True if moved."""
    if not filepath.is_file():
        return False
    if filepath.name.startswith("."):
        return False  # skip hidden files

    ext = filepath.suffix.lower()
    rule = ROUTING_TABLE.get(ext, DEFAULT_ROUTE)
    dest_dir = rule["dest"]
    tag = rule["tag"]

    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / filepath.name

    # Avoid overwrite: add suffix if name collision
    if dest_path.exists():
        stem = filepath.stem
        suf = filepath.suffix
        ts = datetime.now(PT).strftime("%Y%m%d_%H%M%S")
        dest_path = dest_dir / f"{stem}_{ts}{suf}"

    if dry_run:
        print(f"  [DRY-RUN] {filepath.name} ({ext}) -> {dest_dir.name}/ [{tag}]")
    else:
        shutil.move(str(filepath), str(dest_path))
        print(f"  [MOVED] {filepath.name} -> {dest_dir.name}/{dest_path.name} [{tag}]")

    log_move(filepath, dest_path, tag, dry_run=dry_run)
    return True


def process_inbox(dry_run: bool = False) -> int:
    """Route all files currently in inbox. Returns count moved."""
    if not INBOX.exists():
        print(f"[!] Inbox not found: {INBOX}")
        return 0

    files = [f for f in INBOX.iterdir() if f.is_file() and not f.name.startswith(".")]
    if not files:
        return 0

    print(f"\n[{now_pt_str()}] Processing {len(files)} file(s) in inbox...")
    count = 0
    for f in files:
        if route_file(f, dry_run=dry_run):
            count += 1
    print(f"  Done. Routed {count} file(s).")
    return count


def watch_continuous(poll_interval: int = 10, dry_run: bool = False):
    """Poll inbox every N seconds. Falls back if watchdog unavailable."""
    print(f"Watching {INBOX} every {poll_interval}s... (Ctrl+C to stop)")
    try:
        while True:
            process_inbox(dry_run=dry_run)
            time.sleep(poll_interval)
    except KeyboardInterrupt:
        print("\nWatcher stopped.")


def main():
    parser = argparse.ArgumentParser(description="Everlight Staging Inbox Watcher")
    parser.add_argument("--once", action="store_true",
                        help="Process inbox once and exit")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview moves without actually moving files")
    parser.add_argument("--interval", type=int, default=10,
                        help="Poll interval in seconds (default: 10)")
    args = parser.parse_args()

    if args.dry_run:
        print("[DRY-RUN MODE] No files will be moved.\n")

    if args.once:
        n = process_inbox(dry_run=args.dry_run)
        print(f"Processed {n} file(s). Exiting.")
    else:
        watch_continuous(poll_interval=args.interval, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
