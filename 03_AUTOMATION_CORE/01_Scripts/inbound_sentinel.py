"""Inbound Sentinel -- surface strangers who email us about Everlight.

  python3 inbound_sentinel.py --once            # one scan (dry-run default)
  python3 inbound_sentinel.py --once --live      # perform sends/drafts/alerts
  python3 inbound_sentinel.py --daemon --live    # loop every 5 min

Pipeline: fetch -> filter -> classify -> route. Dedup by Message-ID.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from content_tools.imap_fetch import fetch_recent
from inbound.sentinel_filter import triage_keep
from inbound.sentinel_classifier import classify
from inbound.sentinel_router import route

SEEN = Path("/mnt/sdcard/AA_MY_DRIVE/_logs/inbound/sentinel_seen.json")


def _seen() -> set[str]:
    try:
        return set(json.loads(SEEN.read_text()))
    except Exception:
        return set()


def _mark(seen: set[str], mid: str) -> None:
    seen.add(mid)
    if len(seen) > 5000:
        seen = set(list(seen)[-3000:])
    SEEN.parent.mkdir(parents=True, exist_ok=True)
    SEEN.write_text(json.dumps(list(seen)))


def process_one(msg: dict, *, dry_run: bool = True) -> dict | None:
    keep, reason = triage_keep(msg)
    if not keep:
        return None
    classification = classify(msg)
    return route(msg, classification, dry_run=dry_run)


def scan_once(*, dry_run: bool = True, days: int = 1) -> dict:
    seen = _seen()
    kept = 0
    actions: dict[str, int] = {}
    for msg in fetch_recent(days=days):
        mid = msg.get("message_id", "")
        if mid and mid in seen:
            continue
        result = process_one(msg, dry_run=dry_run)
        if result:
            kept += 1
            actions[result["action"]] = actions.get(result["action"], 0) + 1
        if mid:
            _mark(seen, mid)
    return {"kept": kept, "actions": actions, "dry_run": dry_run}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--daemon", action="store_true")
    ap.add_argument("--live", action="store_true", help="perform sends/drafts (default is dry-run)")
    ap.add_argument("--days", type=int, default=1)
    args = ap.parse_args()
    dry = not args.live
    if args.daemon:
        while True:
            print(json.dumps(scan_once(dry_run=dry, days=args.days)))
            time.sleep(300)
    else:
        print(json.dumps(scan_once(dry_run=dry, days=args.days), indent=2))


if __name__ == "__main__":
    main()
