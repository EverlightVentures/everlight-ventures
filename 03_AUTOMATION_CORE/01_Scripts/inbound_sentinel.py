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
_SEEN_MAX = 5000   # prune trigger
_SEEN_KEEP = 3000  # survivors after prune (NEWEST by insertion order)


def _load_seen() -> list[str]:
    """Return the seen Message-IDs as an ordered list (oldest first)."""
    try:
        data = json.loads(SEEN.read_text())
        return [str(x) for x in data] if isinstance(data, list) else []
    except Exception:
        return []


def _save_seen(ids: list[str]) -> None:
    SEEN.parent.mkdir(parents=True, exist_ok=True)
    SEEN.write_text(json.dumps(ids))


def process_one(msg: dict, *, dry_run: bool = True) -> dict | None:
    keep, reason = triage_keep(msg)
    if not keep:
        return None
    classification = classify(msg)
    return route(msg, classification, dry_run=dry_run)


def scan_once(*, dry_run: bool = True, days: int = 1) -> dict:
    seen_list = _load_seen()
    seen = set(seen_list)
    kept = 0
    actions: dict[str, int] = {}
    new_ids: list[str] = []
    for msg in fetch_recent(days=days):
        mid = msg.get("message_id", "")
        if mid and mid in seen:
            continue
        result = process_one(msg, dry_run=dry_run)
        if result:
            kept += 1
            actions[result["action"]] = actions.get(result["action"], 0) + 1
        if mid:
            seen.add(mid)        # within-run dedup
            new_ids.append(mid)  # ordered, newest appended last
    if new_ids:
        merged = seen_list + new_ids
        if len(merged) > _SEEN_MAX:
            merged = merged[-_SEEN_KEEP:]  # keep the NEWEST by insertion order
        _save_seen(merged)       # one write per scan, not per message
    return {"kept": kept, "actions": actions, "dry_run": dry_run}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--daemon", action="store_true",
                    help="run forever, scan every 5 min (process-manager only; use --once for cron)")
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
