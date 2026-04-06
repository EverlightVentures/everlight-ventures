#!/usr/bin/env python3
"""
Log Rotation & Database Maintenance for Everlight Hive

Keeps hive.db sustainable by:
1. Ingesting new raw logs into the database (--append)
2. Trimming old raw_json blobs from high-volume tables
3. Purging bot_decisions older than 30 days (keeps structured fields)
4. Truncating raw JSONL files after successful ingestion
5. Deleting stale VNC/code-server logs

Run daily via cron or manually:
    python3 rotate_logs.py
    python3 rotate_logs.py --dry-run    # Preview without changes
"""

import os
import sys
import sqlite3
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

DRIVE = Path("/mnt/sdcard/AA_MY_DRIVE")
LOGS = DRIVE / "_logs"
DB_PATH = LOGS / "hive.db"
BUILDER = LOGS / "build_hive_db.py"

# Retention: keep raw_json for this many days, then strip it
RAW_JSON_RETENTION_DAYS = 14
# Retention: delete bot_decisions rows older than this
DECISIONS_RETENTION_DAYS = 30

DRY_RUN = "--dry-run" in sys.argv


def log(msg):
    print(f"  {'[DRY] ' if DRY_RUN else ''}{msg}")


def step_1_ingest():
    """Run build_hive_db.py --append to pull in new log data."""
    log("Step 1: Ingesting new logs into hive.db...")
    if DRY_RUN:
        return
    result = subprocess.run(
        [sys.executable, str(BUILDER), "--append"],
        capture_output=True, text=True, cwd=str(LOGS)
    )
    if result.returncode != 0:
        log(f"  WARNING: Ingest failed: {result.stderr[:200]}")
    else:
        # Print last few lines of output
        lines = result.stdout.strip().split("\n")
        for line in lines[-5:]:
            log(f"  {line}")


def step_2_trim_raw_json():
    """Strip raw_json from old rows in high-volume tables."""
    log("Step 2: Trimming old raw_json blobs...")
    cutoff = (datetime.now(timezone.utc) - timedelta(days=RAW_JSON_RETENTION_DAYS)).isoformat()

    if DRY_RUN:
        conn = sqlite3.connect(str(DB_PATH))
        for table, ts_col in [("bot_decisions", "timestamp"), ("claude_hooks", "timestamp_utc")]:
            cur = conn.execute(
                f"SELECT COUNT(*), SUM(LENGTH(raw_json)) FROM {table} WHERE {ts_col} < ? AND raw_json IS NOT NULL",
                (cutoff,)
            )
            count, size = cur.fetchone()
            log(f"  Would trim {count} rows in {table} ({(size or 0)/1024/1024:.1f} MB)")
        conn.close()
        return

    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    for table, ts_col in [("bot_decisions", "timestamp"), ("claude_hooks", "timestamp_utc")]:
        cur = conn.execute(
            f"UPDATE {table} SET raw_json = NULL WHERE {ts_col} < ? AND raw_json IS NOT NULL",
            (cutoff,)
        )
        log(f"  Trimmed raw_json from {cur.rowcount} rows in {table}")
    conn.commit()
    conn.close()


def step_3_purge_old_decisions():
    """Delete very old bot_decisions to keep table manageable."""
    log("Step 3: Purging old bot_decisions...")
    cutoff = (datetime.now(timezone.utc) - timedelta(days=DECISIONS_RETENTION_DAYS)).isoformat()

    conn = sqlite3.connect(str(DB_PATH))
    if DRY_RUN:
        cur = conn.execute("SELECT COUNT(*) FROM bot_decisions WHERE timestamp < ?", (cutoff,))
        count = cur.fetchone()[0]
        log(f"  Would delete {count} old decisions")
        conn.close()
        return

    cur = conn.execute("DELETE FROM bot_decisions WHERE timestamp < ?", (cutoff,))
    log(f"  Deleted {cur.rowcount} old decisions")
    conn.commit()
    conn.close()


def step_4_truncate_raw_logs():
    """Truncate raw JSONL files that have been ingested."""
    log("Step 4: Truncating ingested raw logs...")
    files_to_truncate = [
        LOGS / "claude_hooks" / "pretool.jsonl",
        LOGS / "claude_hooks" / "posttool.jsonl",
        LOGS / "hive_sessions.jsonl",
        LOGS / "daily_briefs.jsonl",
        LOGS / "task_queue.jsonl",
    ]
    for f in files_to_truncate:
        if f.exists() and f.stat().st_size > 0:
            size = f.stat().st_size
            log(f"  Truncating {f.name} ({size/1024:.1f} KB)")
            if not DRY_RUN:
                f.write_text("")


def step_5_cleanup_stale():
    """Delete stale VNC/code-server logs."""
    log("Step 5: Cleaning stale logs...")

    # VNC logs
    vnc_dir = LOGS / "ubuntu_vnc"
    if vnc_dir.exists():
        for f in vnc_dir.glob("*.log"):
            size = f.stat().st_size
            log(f"  Deleting {f.name} ({size/1024/1024:.1f} MB)")
            if not DRY_RUN:
                f.unlink()

    # Old code-server logs
    for f in LOGS.glob("code-server_*.log"):
        log(f"  Deleting {f.name}")
        if not DRY_RUN:
            f.unlink()


def step_6_vacuum():
    """Compact the database."""
    log("Step 6: Compacting database...")
    if DRY_RUN:
        return

    before = DB_PATH.stat().st_size
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("VACUUM")
    conn.close()
    after = DB_PATH.stat().st_size
    saved = (before - after) / 1024 / 1024
    log(f"  {before/1024/1024:.1f} MB -> {after/1024/1024:.1f} MB (saved {saved:.1f} MB)")


def main():
    log(f"Log rotation started at {datetime.now(timezone.utc).isoformat()}")
    log(f"Database: {DB_PATH}")
    log("")

    step_1_ingest()
    step_2_trim_raw_json()
    step_3_purge_old_decisions()
    step_4_truncate_raw_logs()
    step_5_cleanup_stale()
    step_6_vacuum()

    final_size = DB_PATH.stat().st_size / 1024 / 1024
    log("")
    log(f"Final _logs size: {sum(f.stat().st_size for f in LOGS.rglob('*') if f.is_file()) / 1024 / 1024:.1f} MB")
    log(f"hive.db: {final_size:.1f} MB")
    log("Done.")


if __name__ == "__main__":
    main()
