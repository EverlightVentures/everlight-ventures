#!/usr/bin/env python3
"""Workspace root drift audit -- local mirror of cloud routine ev-workspace-drift-audit.

Walks workspace root, diffs against the whitelist, posts to Slack #hive-alerts via
branded_slack.post_branded_alert(). Designed to run as a daily cron at 9 AM PT.

The whitelist MUST stay in sync with .claude/hooks/pre_tool_guard.py
WORKSPACE_ROOT_WHITELIST -- edit both when changing rules.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path("/mnt/sdcard/AA_MY_DRIVE")
LOG_PATH = WORKSPACE / "_logs" / "workspace_root_audit.jsonl"

WHITELIST = frozenset({
    "01_BUSINESSES", "02_CONTENT_FACTORY", "03_AUTOMATION_CORE", "04_MEDIA_LIBRARY",
    "05_PERSONAL", "06_DEVELOPMENT", "07_STAGING", "08_BACKUPS", "09_DASHBOARD",
    "_state", "_logs", "supabase",
    "CLAUDE.md", "CODEX.md", "GEMINI.md", "AGENTS.md",
    "HIVE_CONSTITUTION.md", "HIVE_MIND.md", "EVERLIGHT_COMMANDMENTS.md",
    "LIVING_PUNCHLIST.md", "WORKSPACE_MANIFEST.md", "MEMORY.md",
})


def _audit() -> dict:
    drift = []
    for entry in sorted(WORKSPACE.iterdir()):
        name = entry.name
        if name.startswith("."):
            continue
        if name in WHITELIST:
            continue
        kind = "dir" if entry.is_dir() else "file"
        try:
            stat = entry.stat()
            size_bytes = stat.st_size if kind == "file" else _dir_size(entry)
            mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
        except Exception as e:
            size_bytes, mtime = 0, str(e)
        drift.append({"name": name, "kind": kind, "size_bytes": size_bytes, "last_modified_utc": mtime})
    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "drift_count": len(drift),
        "drift_items": drift,
    }


def _dir_size(p: Path) -> int:
    total = 0
    try:
        for sub in p.rglob("*"):
            try:
                total += sub.stat().st_size
            except Exception:
                pass
    except Exception:
        pass
    return total


def _human_size(n: int) -> str:
    for unit in ("B", "K", "M", "G"):
        if n < 1024 or unit == "G":
            return f"{n:.0f}{unit}"
        n /= 1024
    return f"{n:.0f}T"


def _format_slack(report: dict) -> str:
    if report["drift_count"] == 0:
        return f"✓ Workspace root clean as of {report['timestamp_utc'][:19]}Z -- 9 numbered + 3 hot-state + 10 doctrine + dotfiles only."
    lines = [f"🟡 Workspace Root Drift Detected -- {report['drift_count']} items"]
    lines.append("```")
    lines.append(f"{'name':<50} {'kind':<5} {'size':>8} mtime")
    for item in report["drift_items"]:
        lines.append(f"{item['name'][:50]:<50} {item['kind']:<5} {_human_size(item['size_bytes']):>8} {item['last_modified_utc'][:10]}")
    lines.append("```")
    lines.append(f"_See WORKSPACE_MANIFEST.md File Save Rules to route each into 01-09._")
    return "\n".join(lines)


def _post_slack(message: str, severity: str) -> bool:
    try:
        sys.path.insert(0, str(WORKSPACE / "03_AUTOMATION_CORE" / "01_Scripts"))
        from content_tools.branded_slack import post_branded_alert  # type: ignore
        post_branded_alert(
            channel="#hive-alerts",
            title="Workspace Root Drift Audit",
            message=message,
            severity=severity,
        )
        return True
    except Exception as e:
        print(f"slack post failed: {e}", file=sys.stderr)
        return False


def _log(report: dict) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(report, ensure_ascii=True) + "\n")


def main() -> int:
    report = _audit()
    _log(report)
    if "--quiet" not in sys.argv:
        print(_format_slack(report))
    if "--post" in sys.argv:
        severity = "warning" if report["drift_count"] > 0 else "info"
        _post_slack(_format_slack(report), severity)
    return 0 if report["drift_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
