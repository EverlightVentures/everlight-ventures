#!/usr/bin/env python3
"""
blinko_status -- Memory awareness for the Everlight Hive.

Tells any agent (and Rich) the current state of the persistent memory layer:
  - CONNECTED  : Blinko on e5-mother reachable. Bots have full memory.
  - DEGRADED   : Blinko unreachable, falling back to a local SQLite copy.
                 Bots have READ-ONLY memory of what was synced last.
  - OFFLINE    : No remote AND no local fallback. Bots have ZERO persistent
                 memory -- they'll forget anything not in this single session.

Three probe targets, tried in order:
  1. http://e5-mother:1111      (tailnet -- preferred, lowest latency)
  2. http://100.125.115.95:1111 (tailnet IP fallback if magic-dns broken)
  3. http://163.192.60.35:1111  (public IP fallback)

Local fallback locations checked (first found wins):
  - /mnt/sdcard/AA_MY_DRIVE/_state/blinko_lite.db        (phone canonical)
  - /mnt/sdcard/AA_MY_DRIVE/_logs/blinko_lite.db         (phone legacy)
  - /home/ubuntu/e5_data/blinko_lite.db                  (on e5-mother itself)
  - /home/richgee/AA_MY_DRIVE/_state/blinko_lite.db      (PC canonical)
  - $HOME/.blinko_lite.db                                (user override)

Output modes (-m / --mode):
  human  (default)  - One readable line for an agent to announce
  json              - Structured for programmatic use
  short             - 2-3 words for status lines / shell prompts
  banner            - Multi-line announcement for agent startup

Examples:
  blinko_status.py                  # human mode
  blinko_status.py -m json
  blinko_status.py -m banner --agent "Marcus Cole"

Exit codes:
  0 = connected
  1 = degraded (local fallback active)
  2 = offline (no memory available)
  3 = error
"""

from __future__ import annotations
import argparse
import json
import os
import sqlite3
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

REMOTE_URLS = [
    "http://e5-mother:1111",
    "http://100.125.115.95:1111",
    "http://163.192.60.35:1111",
]

LOCAL_DBS = [
    "/mnt/sdcard/AA_MY_DRIVE/_state/blinko_lite.db",
    "/mnt/sdcard/AA_MY_DRIVE/_logs/blinko_lite.db",
    "/home/ubuntu/e5_data/blinko_lite.db",
    "/home/richgee/AA_MY_DRIVE/_state/blinko_lite.db",
    str(Path.home() / ".blinko_lite.db"),
]

REMOTE_TIMEOUT = 3.0  # seconds per probe -- keep snappy


def _http_get_json(url: str, timeout: float = REMOTE_TIMEOUT) -> dict | None:
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            if 200 <= r.status < 300:
                return json.loads(r.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError,
            ConnectionError, OSError, json.JSONDecodeError):
        return None
    return None


def probe_remote() -> dict | None:
    """Returns dict with url + stats on success, None if all remote probes fail."""
    for url in REMOTE_URLS:
        health = _http_get_json(f"{url}/health", timeout=REMOTE_TIMEOUT)
        if not health or health.get("status") != "ok":
            continue
        stats = _http_get_json(f"{url}/api/v1/note/stats", timeout=REMOTE_TIMEOUT)
        if stats:
            return {"url": url, "health": health, **stats}
        return {"url": url, "health": health}
    return None


def probe_local() -> dict | None:
    """First readable local SQLite copy wins. Returns dict with path + count."""
    for p in LOCAL_DBS:
        if not os.path.isfile(p):
            continue
        try:
            conn = sqlite3.connect(f"file:{p}?mode=ro", uri=True, timeout=2)
            cur = conn.execute("select count(*), max(updated_at) from notes")
            count, latest = cur.fetchone()
            size_mb = os.path.getsize(p) / 1024 / 1024
            conn.close()
            return {
                "path": p,
                "notes_count": count,
                "latest_update": latest,
                "db_size_mb": round(size_mb, 2),
            }
        except sqlite3.DatabaseError:
            continue
    return None


def format_human(status: dict) -> str:
    s = status["state"]
    if s == "CONNECTED":
        return (f"Memory: CONNECTED to {status['source_url']} "
                f"({status['notes_count']} notes, latest {status['latest_update']})")
    if s == "DEGRADED":
        return (f"Memory: DEGRADED -- Blinko unreachable, using local fallback "
                f"({status['notes_count']} notes from {status['latest_update']}, "
                f"path: {status['source_path']})")
    if s == "OFFLINE":
        return ("Memory: OFFLINE -- no remote Blinko, no local fallback. "
                "Operating without persistent memory this session.")
    return f"Memory: ERROR -- {status.get('error', 'unknown')}"


def format_short(status: dict) -> str:
    s = status["state"]
    if s == "CONNECTED":
        return f"ok {status['notes_count']}"
    if s == "DEGRADED":
        return f"degraded {status['notes_count']} (local)"
    if s == "OFFLINE":
        return "offline 0"
    return "error"


def format_banner(status: dict, agent: str | None = None) -> str:
    who = f"[{agent}] " if agent else ""
    s = status["state"]
    if s == "CONNECTED":
        return (f"{who}-- memory check --\n"
                f"  STATE   : CONNECTED\n"
                f"  source  : {status['source_url']}\n"
                f"  notes   : {status['notes_count']} (latest {status['latest_update']})\n"
                f"  I have my files back and I remember everything.")
    if s == "DEGRADED":
        return (f"{who}-- memory check --\n"
                f"  STATE   : DEGRADED -- local fallback\n"
                f"  source  : {status['source_path']}\n"
                f"  notes   : {status['notes_count']} (last sync {status['latest_update']})\n"
                f"  Blinko on e5-mother is unreachable. I'm reading from a local\n"
                f"  copy -- anything written AFTER {status['latest_update']} is\n"
                f"  not in my memory. Heads up.")
    return (f"{who}-- memory check --\n"
            f"  STATE   : OFFLINE\n"
            f"  No remote Blinko, no local fallback file found.\n"
            f"  I am operating without persistent memory. Anything we discuss\n"
            f"  this session will be forgotten unless explicitly saved elsewhere.")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("-m", "--mode", default="human",
                    choices=["human", "json", "short", "banner"])
    ap.add_argument("--agent", help="Agent name for banner mode")
    args = ap.parse_args(argv[1:])

    started = time.time()
    remote = probe_remote()
    if remote and remote.get("total_notes") is not None:
        status = {
            "state": "CONNECTED",
            "source_url": remote["url"],
            "notes_count": remote.get("total_notes"),
            "latest_update": remote.get("latest_update"),
            "probe_ms": int((time.time() - started) * 1000),
        }
        rc = 0
    else:
        local = probe_local()
        if local:
            status = {
                "state": "DEGRADED",
                "source_path": local["path"],
                "notes_count": local["notes_count"],
                "latest_update": local["latest_update"],
                "db_size_mb": local["db_size_mb"],
                "probe_ms": int((time.time() - started) * 1000),
            }
            rc = 1
        else:
            status = {"state": "OFFLINE",
                      "probe_ms": int((time.time() - started) * 1000)}
            rc = 2

    if args.mode == "json":
        print(json.dumps(status, indent=2))
    elif args.mode == "short":
        print(format_short(status))
    elif args.mode == "banner":
        print(format_banner(status, args.agent))
    else:
        print(format_human(status))

    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv))
