"""magnet_monitor -- tail dispatcher events.jsonl and surface magnet activity.

Shows new magnet_click / magnet_accept / magnet_counter / magnet_call /
magnet_not_interested / wholesale_lead_new / wholesale_reply events in real
time, color-coded.

Usage:
    python3 magnet_monitor.py                # live tail (follow)
    python3 magnet_monitor.py --last 20      # last 20 events then exit
    python3 magnet_monitor.py --only accept  # only accept events
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

EVENTS = Path("/mnt/sdcard/AA_MY_DRIVE/_logs/dispatcher/events.jsonl")

# ANSI colors (graceful fallback if not a TTY)
_USE_COLOR = sys.stdout.isatty() and os.environ.get("NO_COLOR", "") == ""
def _c(code: str, s: str) -> str:
    return f"\033[{code}m{s}\033[0m" if _USE_COLOR else s

EVENT_STYLE = {
    "magnet_click":           ("34", "click"),            # blue
    "magnet_accept":          ("32;1", "ACCEPT"),         # bold green
    "magnet_counter":         ("33", "counter"),          # yellow
    "magnet_call":            ("35;1", "CALL"),           # bold magenta
    "magnet_not_interested":  ("90", "pass"),             # gray
    "wholesale_lead_new":     ("36", "new-lead"),         # cyan
    "wholesale_reply":        ("32", "REPLY"),            # green
    "stripe_charge":          ("33;1", "CHARGE"),         # bold yellow
}


def _fmt(row: dict) -> str:
    t = row.get("type", "?")
    code, label = EVENT_STYLE.get(t, ("0", t))
    ts = row.get("ts", "")[:19].replace("T", " ")
    payload = row.get("payload", {})
    lead_id = payload.get("lead_id") or (payload.get("record", {}) or {}).get("id") or "?"
    magnet  = payload.get("magnet", "")
    addr    = (payload.get("record", {}) or {}).get("address", "")
    extra = ""
    if addr: extra = f" @ {addr[:50]}"
    if magnet and t.startswith("magnet_"): extra = f" [{magnet}]" + extra
    return f"{_c('90', ts)}  {_c(code, label.rjust(10))}  lead=`{lead_id}`{extra}"


def tail(path: Path, follow: bool = True, only: str | None = None, last: int = 0):
    if not path.exists():
        print(f"events.jsonl not found at {path}", file=sys.stderr)
        sys.exit(1)

    # Emit the tail-N first
    if last > 0:
        with path.open("r", encoding="utf-8") as f:
            rows = [ln for ln in f if ln.strip()]
        for ln in rows[-last:]:
            try:
                row = json.loads(ln)
            except Exception:
                continue
            if only and only not in row.get("type", ""):
                continue
            print(_fmt(row))
        if not follow:
            return

    if not follow:
        return

    # Follow new lines
    with path.open("r", encoding="utf-8") as f:
        f.seek(0, 2)
        while True:
            ln = f.readline()
            if not ln:
                time.sleep(0.5)
                continue
            try:
                row = json.loads(ln)
            except Exception:
                continue
            if only and only not in row.get("type", ""):
                continue
            print(_fmt(row), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--last", type=int, default=0, help="show last N events then (by default) follow")
    ap.add_argument("--no-follow", action="store_true", help="exit after --last")
    ap.add_argument("--only", help="substring filter on event type (e.g. 'accept', 'magnet')")
    args = ap.parse_args()

    tail(EVENTS, follow=not args.no_follow, only=args.only, last=args.last)


if __name__ == "__main__":
    main()
