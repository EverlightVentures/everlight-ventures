#!/usr/bin/env python3
"""regenerate_index.py - Weekly crawl that rebuilds INDEX.md at the workspace root.

Purpose
-------
Your team cannot find bot-generated data because (a) files land in many places
with inconsistent names and (b) Google Doc URLs from `hive_3format.publish()`
only persist in one-off Slack messages.

This script queries the three authoritative sources and writes one scannable
index file:

  1. Django `HiveSession` (last 50 canonical runs)
  2. Django `HiveArtifact` (recent Google Docs, HTML reports, files)
  3. `_logs/hive.db` `file_index` table (recently-modified workspace files)

Output
------
  /mnt/sdcard/AA_MY_DRIVE/INDEX.md

Run from cron weekly:

  15 3 * * 0 /usr/bin/python3 /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/regenerate_index.py >> /mnt/sdcard/AA_MY_DRIVE/_logs/regenerate_index.log 2>&1

Manual run:

  python3 regenerate_index.py [--dry-run]
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

WORKSPACE = Path("/mnt/sdcard/AA_MY_DRIVE")
if not WORKSPACE.exists():
    WORKSPACE = Path("/home/opc/AA_MY_DRIVE")
if not WORKSPACE.exists():
    WORKSPACE = Path("/home/opc")

INDEX_FILE = WORKSPACE / "INDEX.md"
HIVE_DB = WORKSPACE / "_logs" / "hive.db"
REPORTS_DIR = WORKSPACE / "09_DASHBOARD" / "reports"

DJANGO_PROJECT_DIR = WORKSPACE / "09_DASHBOARD" / "hive_dashboard"


def _bootstrap_django():
    """Load the hive_dashboard Django project in-process.

    Returns (True, (HiveSession, HiveArtifact)) on success, (False, None) if Django
    is unavailable (e.g. running on phone where Django is not installed).
    """
    try:
        if str(DJANGO_PROJECT_DIR) not in sys.path:
            sys.path.insert(0, str(DJANGO_PROJECT_DIR))
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hive_dashboard.settings")
        import django
        django.setup()
        from hive.models import HiveSession, HiveArtifact  # type: ignore
        return True, (HiveSession, HiveArtifact)
    except Exception as exc:
        print(f"[regenerate_index] Django bootstrap failed: {exc}", file=sys.stderr)
        return False, None


def _section_recent_sessions(HiveSession, limit: int = 50) -> list[str]:
    lines = ["## Recent Hive Runs", ""]
    try:
        sessions = HiveSession.objects.order_by("-created_at")[:limit]
        if not sessions:
            lines.append("_(no sessions recorded)_")
            return lines
        lines.append("| When | Agent | Task | Status | Duration | Artifacts |")
        lines.append("|------|-------|------|--------|----------|-----------|")
        for s in sessions:
            when = s.created_at.strftime("%Y-%m-%d %H:%M") if s.created_at else "?"
            agent = s.agent or "-"
            task = (s.task or s.query or "")[:60]
            duration = f"{s.duration_seconds:.1f}s" if s.duration_seconds else "-"
            lines.append(f"| {when} | {agent} | {task} | {s.status} | {duration} | {s.artifacts_count} |")
    except Exception as exc:
        lines.append(f"_(error: {exc})_")
    lines.append("")
    return lines


def _section_artifacts_by_kind(HiveArtifact, days: int = 30) -> list[str]:
    lines = [f"## Artifacts (last {days} days)", ""]
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        qs = HiveArtifact.objects.filter(created_at__gte=cutoff).order_by("-created_at")
        total = qs.count()
        lines.append(f"_Total: {total}_")
        lines.append("")

        by_kind: dict[str, list[Any]] = {}
        for a in qs[:300]:
            by_kind.setdefault(a.kind, []).append(a)

        for kind in sorted(by_kind.keys()):
            items = by_kind[kind]
            lines.append(f"### {kind} ({len(items)})")
            lines.append("")
            for a in items[:40]:
                when = a.created_at.strftime("%Y-%m-%d") if a.created_at else "?"
                title = a.title or a.url or a.path or "(untitled)"
                link = a.url if a.url else a.path
                if a.url:
                    lines.append(f"- [{when}] [{title}]({link}) -- _{a.agent}_")
                else:
                    lines.append(f"- [{when}] {title} `{link}` -- _{a.agent}_")
            lines.append("")
    except Exception as exc:
        lines.append(f"_(error: {exc})_")
    return lines


def _section_top_agents(HiveSession, days: int = 30) -> list[str]:
    lines = [f"## Top Agents by Run Volume (last {days} days)", ""]
    try:
        from django.db.models import Count
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        qs = (
            HiveSession.objects.filter(created_at__gte=cutoff)
            .exclude(agent="")
            .values("agent")
            .annotate(n=Count("id"))
            .order_by("-n")[:20]
        )
        if not qs:
            lines.append("_(no recent sessions with agent set)_")
            return lines
        lines.append("| Agent | Runs |")
        lines.append("|-------|------|")
        for row in qs:
            lines.append(f"| {row['agent']} | {row['n']} |")
    except Exception as exc:
        lines.append(f"_(error: {exc})_")
    lines.append("")
    return lines


def _section_orphan_reports() -> list[str]:
    """Files in 09_DASHBOARD/reports/ that are NOT registered as a HiveArtifact path."""
    lines = ["## Orphan Files in reports/", ""]
    if not REPORTS_DIR.exists():
        lines.append("_(reports dir not found)_")
        return lines
    try:
        recent = sorted(
            [p for p in REPORTS_DIR.rglob("*") if p.is_file()],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )[:30]
        if not recent:
            lines.append("_(no files)_")
            return lines
        lines.append("| Modified | Path |")
        lines.append("|----------|------|")
        for p in recent:
            mtime = datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            rel = p.relative_to(WORKSPACE)
            lines.append(f"| {mtime} | `{rel}` |")
    except Exception as exc:
        lines.append(f"_(error: {exc})_")
    lines.append("")
    return lines


def _section_hive_db_stats() -> list[str]:
    """Summary of the `_logs/hive.db` log store."""
    lines = ["## Log Store (hive.db)", ""]
    if not HIVE_DB.exists():
        lines.append("_(not found)_")
        return lines
    try:
        size_mb = HIVE_DB.stat().st_size / 1024 / 1024
        lines.append(f"Size: **{size_mb:.1f} MB**")
        conn = sqlite3.connect(f"file:{HIVE_DB}?mode=ro", uri=True, timeout=5)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cur.fetchall()]
        lines.append("")
        lines.append("| Table | Rows |")
        lines.append("|-------|------|")
        for t in tables:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {t}")
                lines.append(f"| {t} | {cur.fetchone()[0]:,} |")
            except Exception:
                lines.append(f"| {t} | (err) |")
        conn.close()
    except Exception as exc:
        lines.append(f"_(error: {exc})_")
    lines.append("")
    return lines


def build_index() -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    header = [
        "# Everlight Workspace Index",
        "",
        f"_Generated: {now}_",
        "",
        "This file is regenerated weekly by `regenerate_index.py`. It is the single",
        "place the team can scan to find recent bot activity, artifacts (Google Docs,",
        "HTML reports, files), top agents by volume, and the state of the log store.",
        "",
        "Do not hand-edit. Re-run `regenerate_index.py` to refresh.",
        "",
        "---",
        "",
    ]

    ok, models = _bootstrap_django()

    body: list[str] = []
    if ok:
        HiveSession, HiveArtifact = models
        body += _section_recent_sessions(HiveSession, limit=50)
        body += ["---", ""]
        body += _section_artifacts_by_kind(HiveArtifact, days=30)
        body += ["---", ""]
        body += _section_top_agents(HiveSession, days=30)
        body += ["---", ""]
    else:
        body += [
            "## Django data unavailable",
            "",
            "_Could not bootstrap hive_dashboard. Running phone-local cron? This section_",
            "_will populate when run on Oracle (where Django is installed)._",
            "",
            "---",
            "",
        ]

    body += _section_orphan_reports()
    body += ["---", ""]
    body += _section_hive_db_stats()

    return "\n".join(header + body)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="Print to stdout instead of writing")
    ap.add_argument("--output", default=str(INDEX_FILE))
    args = ap.parse_args()

    content = build_index()

    if args.dry_run:
        print(content)
        return 0

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content, encoding="utf-8")
    print(f"[regenerate_index] wrote {len(content)} bytes to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
