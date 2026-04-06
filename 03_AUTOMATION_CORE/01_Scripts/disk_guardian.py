#!/usr/bin/env python3
"""
Disk Guardian -- Autonomous disk management agent.
Assigned to: Quinn Sharp (QA Gate) + Audit Crane (Compliance Assistant)

Runs every 15 minutes via cron. Does NOT just alert -- it FIXES the problem.
Only alerts the human if it genuinely can't resolve below threshold.

Hierarchy of actions (safest first):
1. Clean caches (.cache, pip, dnf, __pycache__)
2. Trim logs (keep 7 days for .log, 3 days for .jsonl)
3. Clean /tmp (files older than 24h)
4. Vacuum systemd journal (keep 50MB)
5. Remove duplicate/dangling container images
6. Compress old bot logs (gzip anything > 3 days)
7. ALERT only if all above fails and disk > 75%

Posts to #hive-alerts via bot API. Tags Quinn Sharp as the responsible agent.
"""

import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

# Config
DISK_TARGET_PCT = 70       # try to get below this
DISK_WARN_PCT = 75         # alert human only above this AFTER cleanup
DISK_CRITICAL_PCT = 90     # emergency mode
LOG_DIR = Path("/home/opc/xlm-bot/logs")
CACHE_DIRS = [
    Path("/home/opc/.cache"),
    # /root/.cache requires sudo -- handled separately
]
TMP_DIR = Path("/tmp")
BOT_LOG_KEEP_DAYS = 7
JSONL_KEEP_DAYS = 3
TMP_KEEP_HOURS = 24

SLACK_TOKEN = "xoxb-8645963765681-10594020158069-eJRt13YP8qedI6DnQwupuFfy"
SLACK_CHANNEL = "C0ANPRCA4AD"  # #hive-alerts
SLACK_DEPLOY = "C0AN4GSTMT5"   # #deploy-log

LOG_FILE = Path("/tmp/disk_guardian.log")


def _log(msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass


def _run(cmd: str, sudo: bool = False) -> str:
    if sudo:
        cmd = f"sudo {cmd}"
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=30
        )
        return result.stdout.strip()
    except Exception as e:
        return f"ERROR: {e}"


def _disk_pct() -> int:
    out = _run("df / | tail -1 | awk '{print $5}' | tr -d '%'")
    try:
        return int(out)
    except ValueError:
        return 99  # assume bad if can't read


def _freed_mb(before: int, after: int) -> str:
    # Estimate from percentage change on a 30GB disk
    freed = (before - after) * 30000 / 100
    return f"{freed:.0f}MB"


def _slack(msg: str, channel: str = None) -> None:
    ch = channel or SLACK_CHANNEL
    try:
        import urllib.request
        payload = json.dumps({"channel": ch, "text": msg}).encode("utf-8")
        req = urllib.request.Request(
            "https://slack.com/api/chat.postMessage",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {SLACK_TOKEN}",
            },
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception:
        pass


def clean_caches() -> int:
    """Clean pip/dnf/general caches. Returns MB freed estimate."""
    freed = 0
    for cache_dir in CACHE_DIRS:
        if cache_dir.is_dir():
            size_before = _run(f"du -sm {cache_dir} | cut -f1")
            _run(f"rm -rf {cache_dir}/pip {cache_dir}/fontconfig {cache_dir}/thumbnails")
            size_after = _run(f"du -sm {cache_dir} | cut -f1")
            try:
                freed += int(size_before) - int(size_after)
            except ValueError:
                pass

    # Root cache (needs sudo)
    _run("rm -rf /root/.cache/pip /root/.cache/fontconfig 2>/dev/null", sudo=True)
    # DNF cache
    _run("dnf clean all", sudo=True)
    return freed


def trim_logs() -> int:
    """Trim old log and jsonl files. Returns count of files cleaned."""
    count = 0
    if LOG_DIR.is_dir():
        # Delete .log files older than BOT_LOG_KEEP_DAYS
        result = _run(
            f"find {LOG_DIR} -name '*.log' -mtime +{BOT_LOG_KEEP_DAYS} -delete -print"
        )
        count += len(result.strip().splitlines()) if result.strip() else 0

        # Delete .jsonl files older than JSONL_KEEP_DAYS
        result = _run(
            f"find {LOG_DIR} -name '*.jsonl' -mtime +{JSONL_KEEP_DAYS} -delete -print"
        )
        count += len(result.strip().splitlines()) if result.strip() else 0

        # Truncate large active logs to last 5000 lines
        for f in LOG_DIR.glob("*.log"):
            try:
                lines = sum(1 for _ in open(f))
                if lines > 5000:
                    _run(f"tail -5000 {f} > {f}.tmp && mv {f}.tmp {f}")
                    count += 1
            except Exception:
                pass

    # n8n event logs
    for f in Path("/home/opc/.n8n").glob("n8nEventLog*.log"):
        try:
            lines = sum(1 for _ in open(f))
            if lines > 3000:
                _run(f"tail -3000 {f} > {f}.tmp && mv {f}.tmp {f}")
                count += 1
        except Exception:
            pass

    return count


def clean_tmp() -> int:
    """Clean old temp files. Returns count."""
    result = _run(
        f"find {TMP_DIR} -maxdepth 2 -type f -mmin +{TMP_KEEP_HOURS * 60} "
        f"-not -name 'disk_guardian.log' -delete -print 2>/dev/null"
    )
    return len(result.strip().splitlines()) if result.strip() else 0


def vacuum_journal() -> str:
    """Vacuum systemd journal."""
    return _run("journalctl --vacuum-size=50M", sudo=True)


def clean_container_images() -> int:
    """Remove dangling/unused container images."""
    # Remove dangling images
    result = _run("podman image prune -f", sudo=True)
    # Remove duplicate tags (langfuse:latest is same as langfuse:3)
    _run("podman rmi docker.io/langfuse/langfuse:latest 2>/dev/null", sudo=True)
    # Don't remove postgres:17 -- might break langfuse compose
    return 1 if "Reclaimed" in str(result) else 0


def compress_old_logs() -> int:
    """Gzip logs older than 3 days that aren't already compressed."""
    result = _run(
        f"find {LOG_DIR} -name '*.log' -mtime +3 -not -name '*.gz' "
        f"-exec gzip -9 {{}} \\; -print 2>/dev/null"
    )
    return len(result.strip().splitlines()) if result.strip() else 0


def run_guardian():
    """Main guardian loop -- clean and report."""
    before = _disk_pct()
    _log(f"Disk Guardian starting. Current: {before}%")

    if before <= DISK_TARGET_PCT:
        _log(f"Disk at {before}% -- below target {DISK_TARGET_PCT}%. No action needed.")
        return

    actions = []

    # Step 1: Caches
    cache_freed = clean_caches()
    if cache_freed > 0:
        actions.append(f"Cleaned caches ({cache_freed}MB)")
    after = _disk_pct()
    if after <= DISK_TARGET_PCT:
        _log(f"Resolved: {before}% -> {after}% after cache cleanup")
        _slack(
            f"*Quinn Sharp (Disk Guardian):* Disk was {before}%, "
            f"cleaned caches -> {after}%. All clear.",
            SLACK_DEPLOY,
        )
        return

    # Step 2: Trim logs
    log_count = trim_logs()
    if log_count > 0:
        actions.append(f"Trimmed {log_count} log files")
    after = _disk_pct()
    if after <= DISK_TARGET_PCT:
        _log(f"Resolved: {before}% -> {after}% after log trim")
        _slack(
            f"*Quinn Sharp (Disk Guardian):* Disk was {before}%, "
            f"trimmed {log_count} logs -> {after}%. All clear.",
            SLACK_DEPLOY,
        )
        return

    # Step 3: Clean /tmp
    tmp_count = clean_tmp()
    if tmp_count > 0:
        actions.append(f"Cleaned {tmp_count} temp files")

    # Step 4: Vacuum journal
    vacuum_journal()
    actions.append("Vacuumed journal")

    # Step 5: Container image cleanup
    container_cleaned = clean_container_images()
    if container_cleaned:
        actions.append("Pruned container images")

    # Step 6: Compress old logs
    compressed = compress_old_logs()
    if compressed:
        actions.append(f"Compressed {compressed} old logs")

    after = _disk_pct()
    freed = _freed_mb(before, after)

    if after <= DISK_WARN_PCT:
        _log(f"Resolved: {before}% -> {after}% (freed ~{freed})")
        _slack(
            f"*Quinn Sharp (Disk Guardian):* Disk was {before}%, "
            f"ran cleanup -> {after}% (freed ~{freed}). "
            f"Actions: {'; '.join(actions)}",
            SLACK_DEPLOY,
        )
    else:
        # Couldn't get below threshold -- alert the human
        _log(f"ALERT: Disk still at {after}% after all cleanup (was {before}%)")
        _slack(
            f"*Quinn Sharp (Disk Guardian):* :warning: Disk at {after}% "
            f"after full cleanup (was {before}%, freed ~{freed}). "
            f"I've exhausted safe cleanup options. "
            f"Remaining hogs: Langfuse containers (8.6GB), xlm-bot venv (532MB). "
            f"Need human decision: remove Langfuse or expand disk. "
            f"Actions taken: {'; '.join(actions)}",
        )


if __name__ == "__main__":
    run_guardian()
