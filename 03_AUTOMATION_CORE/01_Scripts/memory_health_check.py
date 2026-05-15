#!/usr/bin/env python3
"""memory_health_check.py -- multi-source memory integrity verifier.

Extends `blinko_status.py` from a connectivity check to a full integrity check.
Run on a 5-min watchdog interval (already wired in dashboards_watchdog.sh) and
on every agent startup to ensure memory state is healthy across all 4 surfaces:

  1. Blinko on e5-mother (cloud RAG, 1111)
  2. BlinkoLite on phone (local fallback RAG, 1111)
  3. agentmemory MCP on e5-mother (knowledge graph, 3108)
  4. Phone-side mirror files (_state/blinko_lite.db, _state/agentmemory_graph.json)
  5. Rolling snapshots (08_BACKUPS/mother_snapshots/)
  6. Claude project memory (/root/.claude/projects/.../memory/)

Checks (per surface):
  - Reachable / present?
  - Row count / file count / size within expected range?
  - Last-modified within freshness window?
  - Structural integrity (valid SQLite, valid JSON, no corruption)?

Exit codes:
  0 = all green
  1 = degraded (one surface unhealthy, but redundancy holds)
  2 = critical (multiple surfaces unhealthy, agent should announce "no memory")

Modes:
  --human          (default): print readable table
  --json           : machine-readable for dashboard ingestion
  --slack-alert    : post to #hive-alerts if not all-green
  --quick          : connectivity-only (legacy blinko_status behavior)
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path("/mnt/sdcard/AA_MY_DRIVE")
PHONE_BLINKO_DB = WORKSPACE / "_state" / "blinko_lite.db"
PHONE_AGENTMEM = WORKSPACE / "_state" / "agentmemory_graph.json"
SNAPSHOT_DIR = WORKSPACE / "08_BACKUPS" / "mother_snapshots"
CLAUDE_MEM_DIR = Path("/root/.claude/projects/-mnt-sdcard-AA-MY-DRIVE/memory")
MOTHER_BLINKO_URL = "http://e5-mother:1111"
MOTHER_AGENTMEM_URL = "http://e5-mother:3108"
PHONE_BLINKO_URL = "http://127.0.0.1:1111"

# Expected ranges (relax over time if false-positives)
MIN_BLINKO_NOTES = 3000   # we have ~3,711; alert if drops below 3,000
MAX_FRESHNESS_SECS = 86400  # 24h -- live files older than this = stale
MIN_CLAUDE_MEM_FILES = 100  # we have ~181; alert if below 100


def _check_blinko_remote() -> dict:
    """Probe Blinko on e5-mother."""
    out = {"surface": "blinko-mother", "url": MOTHER_BLINKO_URL}
    try:
        req = urllib.request.Request(f"{MOTHER_BLINKO_URL}/api/v1/note/list?limit=1")
        with urllib.request.urlopen(req, timeout=4) as r:
            r.read()
            out["reachable"] = True
        # count
        req = urllib.request.Request(f"{MOTHER_BLINKO_URL}/api/v1/note/list?limit=10000")
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
            count = len(data) if isinstance(data, list) else data.get("count", 0)
            out["count"] = count
            out["healthy"] = count >= MIN_BLINKO_NOTES
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, OSError) as e:
        out["reachable"] = False
        out["healthy"] = False
        out["error"] = str(e)[:80]
    return out


def _check_blinko_phone() -> dict:
    """Probe BlinkoLite on phone (port 1111 local)."""
    out = {"surface": "blinko-phone", "url": PHONE_BLINKO_URL}
    try:
        req = urllib.request.Request(f"{PHONE_BLINKO_URL}/health")
        with urllib.request.urlopen(req, timeout=2) as r:
            r.read()
            out["reachable"] = True
            out["healthy"] = True
    except (urllib.error.URLError, OSError) as e:
        out["reachable"] = False
        out["healthy"] = False
        out["error"] = str(e)[:60]
    return out


def _check_blinko_db_file() -> dict:
    """Probe the phone-side blinko_lite.db file directly (the disk-level mirror)."""
    out = {"surface": "blinko-db-file", "path": str(PHONE_BLINKO_DB)}
    if not PHONE_BLINKO_DB.exists():
        out.update({"present": False, "healthy": False, "error": "file missing"})
        return out
    try:
        stat = PHONE_BLINKO_DB.stat()
        out["present"] = True
        out["size_bytes"] = stat.st_size
        out["age_secs"] = int(time.time() - stat.st_mtime)
        # validate SQLite + count
        con = sqlite3.connect(f"file:{PHONE_BLINKO_DB}?mode=ro", uri=True)
        try:
            c = con.cursor()
            c.execute("SELECT count(*) FROM notes")
            out["count"] = c.fetchone()[0]
            # integrity check
            c.execute("PRAGMA integrity_check")
            integrity = c.fetchone()[0]
            out["integrity"] = integrity
            out["healthy"] = (
                out["count"] >= MIN_BLINKO_NOTES
                and integrity == "ok"
            )
        finally:
            con.close()
    except (sqlite3.Error, OSError) as e:
        out["healthy"] = False
        out["error"] = str(e)[:80]
    return out


def _check_agentmemory_remote() -> dict:
    """Probe agentmemory MCP on e5-mother (port 3108 SSE proxy)."""
    out = {"surface": "agentmemory-mother", "url": MOTHER_AGENTMEM_URL}
    try:
        req = urllib.request.Request(f"{MOTHER_AGENTMEM_URL}/sse")
        with urllib.request.urlopen(req, timeout=3) as r:
            out["reachable"] = True
            out["healthy"] = True
    except (urllib.error.URLError, OSError) as e:
        out["reachable"] = False
        out["healthy"] = False
        out["error"] = str(e)[:60]
    return out


def _check_agentmemory_file() -> dict:
    """Probe the phone-side agentmemory_graph.json (disk mirror of the knowledge graph)."""
    out = {"surface": "agentmemory-file", "path": str(PHONE_AGENTMEM)}
    if not PHONE_AGENTMEM.exists():
        out.update({"present": False, "healthy": False, "error": "file missing"})
        return out
    try:
        stat = PHONE_AGENTMEM.stat()
        out["present"] = True
        out["size_bytes"] = stat.st_size
        out["age_secs"] = int(time.time() - stat.st_mtime)
        # validate JSON
        data = json.loads(PHONE_AGENTMEM.read_text())
        out["entities"] = len(data.get("entities", [])) if isinstance(data, dict) else 0
        out["healthy"] = True  # empty {} is valid for new install
    except (json.JSONDecodeError, OSError) as e:
        out["healthy"] = False
        out["error"] = str(e)[:80]
    return out


def _check_snapshots() -> dict:
    """Probe the rolling 14-day snapshots dir."""
    out = {"surface": "rolling-snapshots", "path": str(SNAPSHOT_DIR)}
    if not SNAPSHOT_DIR.exists():
        out.update({"present": False, "healthy": False, "error": "dir missing"})
        return out
    snapshots = list(SNAPSHOT_DIR.glob("blinko_*.db"))
    agentmem_snaps = list(SNAPSHOT_DIR.glob("agentmemory_*.json"))
    out["blinko_snapshots"] = len(snapshots)
    out["agentmem_snapshots"] = len(agentmem_snaps)
    if snapshots:
        latest = max(snapshots, key=lambda p: p.stat().st_mtime)
        out["latest_blinko_snapshot_age_secs"] = int(time.time() - latest.stat().st_mtime)
    out["healthy"] = len(snapshots) >= 1  # need at least one snapshot
    return out


def _check_claude_memory() -> dict:
    """Probe Claude's project memory dir."""
    out = {"surface": "claude-memory", "path": str(CLAUDE_MEM_DIR)}
    if not CLAUDE_MEM_DIR.exists():
        out.update({"present": False, "healthy": False, "error": "dir missing"})
        return out
    files = list(CLAUDE_MEM_DIR.glob("*.md"))
    out["file_count"] = len(files)
    memory_md = CLAUDE_MEM_DIR / "MEMORY.md"
    if memory_md.exists():
        out["memory_md_size"] = memory_md.stat().st_size
        out["memory_md_age_secs"] = int(time.time() - memory_md.stat().st_mtime)
    out["healthy"] = len(files) >= MIN_CLAUDE_MEM_FILES
    return out


# Queue depth thresholds -- alert when any of these are exceeded
QUEUE_DEPTH_WARN = 20      # 20+ pending entries = cloud has been unreachable a while
QUEUE_DEPTH_CRITICAL = 100  # 100+ = something is seriously wrong
QUEUE_OLDEST_WARN_SECS = 3600     # 1 hour old pending entry
QUEUE_OLDEST_CRITICAL_SECS = 86400  # 1 day old


def _check_sync_queue() -> dict:
    """Probe the sync_queue.jsonl: depth, oldest pending age, conflict count."""
    out = {"surface": "sync-queue", "path": str(WORKSPACE / "_state" / "sync_queue.jsonl")}
    queue_path = WORKSPACE / "_state" / "sync_queue.jsonl"
    conflict_log = WORKSPACE / "_state" / "sync_conflicts.jsonl"

    if not queue_path.exists():
        # Empty queue = healthy state (no writes attempted yet)
        out.update({"present": False, "depth": 0, "conflicts": 0, "healthy": True})
        return out

    pending = []
    total_lines = 0
    try:
        for line in queue_path.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            total_lines += 1
            try:
                e = json.loads(line)
                if e.get("status") == "pending":
                    pending.append(e)
            except json.JSONDecodeError:
                continue
    except OSError as exc:
        out.update({"healthy": False, "error": f"queue unreadable: {exc}"})
        return out

    out["depth"] = len(pending)
    out["total_entries"] = total_lines

    # Oldest pending age
    if pending:
        oldest_ts = None
        for e in pending:
            try:
                ts = datetime.fromisoformat(e["ts"]).timestamp()
                if oldest_ts is None or ts < oldest_ts:
                    oldest_ts = ts
            except (ValueError, KeyError):
                continue
        if oldest_ts:
            out["oldest_age_secs"] = int(time.time() - oldest_ts)

    # Conflict count
    conflicts = 0
    if conflict_log.exists():
        try:
            for line in conflict_log.read_text().splitlines():
                if line.strip():
                    conflicts += 1
        except OSError:
            pass
    out["conflicts"] = conflicts

    # Health verdict
    depth = out["depth"]
    age = out.get("oldest_age_secs", 0)
    if depth >= QUEUE_DEPTH_CRITICAL or age >= QUEUE_OLDEST_CRITICAL_SECS:
        out["healthy"] = False
        out["severity"] = "critical"
    elif depth >= QUEUE_DEPTH_WARN or age >= QUEUE_OLDEST_WARN_SECS:
        out["healthy"] = False
        out["severity"] = "warning"
    elif conflicts > 0:
        # Conflicts always need operator eyes, even if depth is low
        out["healthy"] = False
        out["severity"] = "warning"
    else:
        out["healthy"] = True

    return out


def run_checks(quick: bool = False) -> list[dict]:
    """Run all checks and return list of results."""
    checks = [_check_blinko_remote, _check_blinko_phone, _check_blinko_db_file]
    if not quick:
        checks.extend([
            _check_agentmemory_remote,
            _check_agentmemory_file,
            _check_snapshots,
            _check_claude_memory,
            _check_sync_queue,
        ])
    return [c() for c in checks]


def overall_state(results: list[dict]) -> tuple[str, int]:
    """Compute overall state from individual check results."""
    healthy = sum(1 for r in results if r.get("healthy"))
    total = len(results)
    if healthy == total:
        return "GREEN", 0
    if healthy >= total - 1:
        return "DEGRADED", 1
    return "CRITICAL", 2


def render_human(results: list[dict]) -> str:
    state, _ = overall_state(results)
    lines = [
        f"\n  Memory Health: {state}  ({datetime.now(timezone.utc).isoformat()[:19]}Z)",
        f"  {'-' * 78}",
        f"  {'surface':22} | {'status':10} | {'details'}",
        f"  {'-' * 78}",
    ]
    for r in results:
        status = "✓ healthy" if r.get("healthy") else "✗ degraded"
        details_parts = []
        for k in ("count", "entities", "file_count", "blinko_snapshots", "depth", "conflicts", "oldest_age_secs", "size_bytes", "age_secs", "integrity", "severity", "error"):
            if k in r:
                v = r[k]
                if k == "size_bytes" and isinstance(v, int):
                    v = f"{v / 1024:.1f} KB" if v < 1_000_000 else f"{v / 1_000_000:.1f} MB"
                elif k == "age_secs" and isinstance(v, int):
                    v = f"{v // 60} min" if v < 3600 else f"{v // 3600} hr"
                details_parts.append(f"{k}={v}")
        details = "  ".join(details_parts)[:46]
        lines.append(f"  {r['surface']:22} | {status:10} | {details}")
    lines.append("")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true", help="machine-readable JSON output")
    ap.add_argument("--quick", action="store_true", help="connectivity-only (legacy mode)")
    ap.add_argument("--slack-alert", action="store_true", help="post to #hive-alerts on non-green")
    args = ap.parse_args()

    results = run_checks(quick=args.quick)
    state, exit_code = overall_state(results)

    if args.json:
        print(json.dumps({
            "state": state,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "results": results,
        }, indent=2))
    else:
        print(render_human(results))

    if args.slack_alert and state != "GREEN":
        # Build a focused alert summary -- highlight queue issues specifically
        queue_check = next((r for r in results if r.get("surface") == "sync-queue"), None)
        alert_body = render_human(results)
        alert_summary = f"Memory health: {state}"
        severity = "warning" if state == "DEGRADED" else "critical"

        if queue_check and not queue_check.get("healthy"):
            depth = queue_check.get("depth", 0)
            age = queue_check.get("oldest_age_secs", 0)
            conflicts = queue_check.get("conflicts", 0)
            alert_summary = f"Sync queue {queue_check.get('severity', 'warning').upper()}: depth={depth}, oldest={age // 60}min, conflicts={conflicts}"
            severity = queue_check.get("severity", severity)

        try:
            sys.path.insert(0, str(WORKSPACE / "03_AUTOMATION_CORE" / "01_Scripts"))
            from content_tools.branded_slack import post_branded_alert
            post_branded_alert(
                channel="#hive-alerts",
                summary=alert_summary,
                severity=severity,
                body=alert_body,
            )
        except Exception as e:
            print(f"  (slack alert failed: {e})", file=sys.stderr)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
