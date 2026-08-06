#!/usr/bin/env python3
"""
activity_feed -- unified "who did what when" view across the Hive's logs.

The action history is intentionally distributed (each format serves a purpose):
  - Blinko notes tagged #hive/session   -> the searchable narrative log
  - JSONL files from hive_logger        -> the structured machine log
  - Django HiveArtifact rows            -> the dashboard view
  - Slack channels                       -> the real-time human log
  - AGENT_MAILBOX.md                     -> Claude-session coordination
  - Memory files                         -> the decision/learning log

This script unifies the VIEW (not the data). It queries the available sources
and prints a chronological feed of recent activity.

Usage:
  activity_feed.py                       # last 20 events
  activity_feed.py -n 50                 # last 50
  activity_feed.py --hours 24            # last 24 hours
  activity_feed.py --source blinko       # only Blinko notes
  activity_feed.py --grep wholesale      # filter by keyword

Sources tried (degrades gracefully if any unreachable):
  1. Blinko at e5-mother:1111 (preferred) -> falls back to local .db
  2. _state/AGENT_MAILBOX.md (always present)
  3. hive_logger JSONL files in _logs/ (if present)
  4. Supabase hive_systemevent (if env has SUPABASE_URL + key)
"""
from __future__ import annotations
import argparse
import json
import os
import re
import sqlite3
import sys
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path

BLINKO_URLS = [
    "http://e5-mother:1111",
    "http://100.125.115.95:1111",
]
LOCAL_DBS = [
    "/mnt/sdcard/AA_MY_DRIVE/_state/blinko_lite.db",
    "/home/ubuntu/e5_data/blinko_lite.db",
    "/AA_MY_DRIVE/_state/blinko_lite.db",
    "/home/richgee/AA_MY_DRIVE/_state/blinko_lite.db",
]
MAILBOX = "/mnt/sdcard/AA_MY_DRIVE/_state/AGENT_MAILBOX.md"
LOGS_DIR = "/mnt/sdcard/AA_MY_DRIVE/_logs"


def _http_post(url: str, data: dict, timeout: float = 4.0) -> dict | None:
    try:
        body = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(url, data=body, method="POST",
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:
        return None


def from_blinko_remote(limit: int, grep: str | None) -> list[dict]:
    """Search Blinko for recent #hive/session notes."""
    payload = {"query": grep or "#hive", "limit": limit}
    for url in BLINKO_URLS:
        data = _http_post(f"{url}/api/v1/note/list", payload, timeout=4)
        if data and "items" in data:
            return [
                {
                    "ts": n.get("updated_at") or n.get("created_at", ""),
                    "src": "blinko",
                    "summary": (n.get("content", "")[:120]
                                .replace("\n", " ").strip()),
                }
                for n in data["items"]
            ]
    return []


def from_blinko_local(limit: int, grep: str | None) -> list[dict]:
    """Fallback: query local .db directly."""
    for p in LOCAL_DBS:
        if not os.path.isfile(p):
            continue
        try:
            conn = sqlite3.connect(f"file:{p}?mode=ro", uri=True, timeout=2)
            q = "select created_at, content from notes"
            params: list = []
            if grep:
                q += " where content like ?"
                params.append(f"%{grep}%")
            q += " order by created_at desc limit ?"
            params.append(limit)
            rows = conn.execute(q, params).fetchall()
            conn.close()
            return [
                {"ts": ts, "src": "blinko-local",
                 "summary": c[:120].replace("\n", " ").strip()}
                for ts, c in rows
            ]
        except sqlite3.DatabaseError:
            continue
    return []


def from_mailbox(limit: int, grep: str | None) -> list[dict]:
    """Parse [timestamp] FROM:node | message entries."""
    if not os.path.isfile(MAILBOX):
        return []
    pattern = re.compile(r"^\[(\d{4}-\d{2}-\d{2}[^\]]+)\]\s+FROM:(\S+)\s*\|\s*(.+)")
    items: list[dict] = []
    with open(MAILBOX) as f:
        for line in f:
            m = pattern.match(line)
            if m:
                ts, who, msg = m.group(1), m.group(2), m.group(3).strip()
                if grep and grep.lower() not in msg.lower():
                    continue
                items.append({"ts": ts, "src": f"mailbox:{who}",
                              "summary": msg[:160]})
    return items[-limit:]


def from_jsonl(limit: int, grep: str | None) -> list[dict]:
    """Read recent hive_logger JSONL events if any."""
    if not os.path.isdir(LOGS_DIR):
        return []
    items: list[dict] = []
    for p in Path(LOGS_DIR).glob("**/*.jsonl"):
        try:
            with open(p) as f:
                for line in f:
                    try:
                        e = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    ts = e.get("ts") or e.get("timestamp") or e.get("created_at", "")
                    msg = e.get("message") or e.get("summary") or e.get("event", "")
                    if grep and grep.lower() not in str(msg).lower():
                        continue
                    items.append({"ts": str(ts), "src": f"jsonl:{p.name}",
                                  "summary": str(msg)[:160]})
        except OSError:
            continue
    items.sort(key=lambda x: x["ts"], reverse=True)
    return items[:limit]


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", "--limit", type=int, default=20)
    ap.add_argument("--hours", type=int, default=0,
                    help="restrict to last N hours (0 = no limit)")
    ap.add_argument("--source", choices=["all", "blinko", "mailbox", "jsonl"],
                    default="all")
    ap.add_argument("--grep", default=None, help="filter by substring")
    args = ap.parse_args(argv[1:])

    all_items: list[dict] = []
    if args.source in ("all", "blinko"):
        items = from_blinko_remote(args.limit, args.grep)
        if not items:
            items = from_blinko_local(args.limit, args.grep)
        all_items.extend(items)
    if args.source in ("all", "mailbox"):
        all_items.extend(from_mailbox(args.limit, args.grep))
    if args.source in ("all", "jsonl"):
        all_items.extend(from_jsonl(args.limit, args.grep))

    # Sort by timestamp descending, dedupe by ts+summary
    seen = set()
    deduped = []
    for it in sorted(all_items, key=lambda x: x.get("ts", ""), reverse=True):
        key = (it["ts"][:19], it["summary"][:80])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(it)

    # Apply --hours filter if set
    if args.hours > 0:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=args.hours)
        filt = []
        for it in deduped:
            try:
                ts_str = it["ts"][:19].replace("T", " ").replace("Z", "")
                ts = datetime.fromisoformat(ts_str).replace(tzinfo=timezone.utc)
                if ts >= cutoff:
                    filt.append(it)
            except (ValueError, TypeError):
                filt.append(it)  # keep if unparseable rather than drop
        deduped = filt

    deduped = deduped[:args.limit]
    if not deduped:
        print("(no activity found)")
        return 1

    print(f"=== Hive activity ({len(deduped)} events) ===\n")
    for it in deduped:
        ts = it["ts"][:19].replace("T", " ")
        print(f"  {ts}  [{it['src']:20}]  {it['summary']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
