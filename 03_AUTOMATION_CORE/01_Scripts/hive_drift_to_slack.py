#!/usr/bin/env python3
"""
Hive Drift -> Slack -- posts the latest parity report to #hive-alerts.

Runs nightly via cron. Uses content_tools.branded_slack if available so the
post lands gold-branded; falls back to raw chat.postMessage if the branded
module isn't importable. Only posts when there's actual drift (no spam on
all-green nights -- per the "service-active is never proof" doctrine, we
also post a one-line "OK" once per week so silence doesn't mean dead).
"""
from __future__ import annotations

import datetime as dt
import os
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path("/mnt/sdcard/AA_MY_DRIVE")
sys.path.insert(0, str(ROOT))

REPORT = ROOT / "_logs/hive_parity_report.md"
CHANNEL = os.environ.get("HIVE_ALERTS_CHANNEL", "#hive-alerts")
HEARTBEAT_DAY = 0  # Monday -- one mandatory all-green post per week

PT = ZoneInfo("America/Los_Angeles")


def is_green(report_text: str) -> bool:
    return "## Failures" not in report_text


def should_post(report_text: str) -> bool:
    if not is_green(report_text):
        return True
    return dt.datetime.now(PT).weekday() == HEARTBEAT_DAY


def post(report_text: str) -> int:
    title = "Hive Parity Drift" if not is_green(report_text) else "Hive Parity Heartbeat -- all green"
    category = "alert" if not is_green(report_text) else "system"

    try:
        from content_tools.branded_slack import post_branded_slack  # type: ignore
    except Exception:
        try:
            from content_tools.branded_slack import post_branded_slack  # noqa: F401
        except Exception:
            print(f"[drift] branded_slack unavailable; would post to {CHANNEL}: {title}")
            print(report_text[:500])
            return 1

    post_branded_slack(
        channel=CHANNEL,
        title=title,
        body=report_text[:2500],
        category=category,
        agent="parity-check",
    )
    return 0


def main() -> int:
    if not REPORT.exists():
        print(f"[drift] no parity report at {REPORT}; run hive_parity_check.py first")
        return 2
    text = REPORT.read_text(encoding="utf-8")
    if not should_post(text):
        print("[drift] green and not heartbeat day; skipping Slack post")
        return 0
    return post(text)


if __name__ == "__main__":
    sys.exit(main())
