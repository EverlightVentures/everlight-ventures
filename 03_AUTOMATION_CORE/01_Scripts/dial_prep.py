"""
dial_prep.py -- Print today's dial sheet for Marquise's morning routine.

Referenced by Piper's SOLO_OUTREACH_SOP.md. Reads dial_list_*.csv for the
current day-of-week and prints a numbered, dial-friendly format.

Also supports --summarize mode: counts outcomes in dial_log.csv.
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from datetime import date
from pathlib import Path


DATA_DIR = Path("/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Broker_OS/wholesale_agent/data")


def find_today_dial_list() -> Path | None:
    """Find the dial_list CSV for today. Tuesday=ATL, Wednesday=DFW, fallback combined."""
    today = date.today()
    weekday = today.weekday()  # 0=Mon, 1=Tue, 2=Wed
    candidates = []
    if weekday == 1:  # Tuesday
        candidates.append(DATA_DIR / f"dial_list_ATL_{today.isoformat()}.csv")
    elif weekday == 2:  # Wednesday
        candidates.append(DATA_DIR / f"dial_list_DFW_{today.isoformat()}.csv")
    # Fallbacks
    candidates.append(DATA_DIR / "phone_only_leads.csv")
    for p in candidates:
        if p.exists():
            return p
    return None


def print_dial_sheet(path: Path, limit: int = 32) -> int:
    print(f"# DIAL SHEET -- {path.name}")
    print(f"# Source: {path}")
    print(f"# Use: read each row, dial, log outcome in dial_log.csv")
    print(f"# Outcomes: talked | vm | dnc | wrong# | callback | voicemail_dropped")
    print()
    rows = []
    with open(path, newline="") as f:
        for line in f:
            if line.startswith("#"):
                continue
            break
        reader = csv.DictReader(f) if not f.closed else None
        # Re-open and skip comment lines properly
    with open(path, newline="") as f:
        reader = csv.DictReader(filter(lambda r: not r.startswith("#"), f))
        for r in reader:
            rows.append(r)

    print(f"  {'#':>3}  {'NAME':<26} {'PHONE':<16} {'ADDRESS':<40} {'TYPE':<18} {'SCORE'}")
    print("  " + "-" * 110)
    for i, r in enumerate(rows[:limit], 1):
        name = (r.get("owner_name") or "")[:26]
        phone = (r.get("owner_phone") or "")[:16]
        addr = (r.get("address") or "")[:40]
        lt = (r.get("lead_type") or "")[:18]
        score = r.get("score", "?")
        print(f"  {i:>3}  {name:<26} {phone:<16} {addr:<40} {lt:<18} {score}")

    print()
    print(f"Total rows: {len(rows)}")
    if len(rows) > limit:
        print(f"Showing first {limit}. Hard cap at {limit} dials/day per Piper SOP.")
    return len(rows)


def summarize_dial_log() -> None:
    log = DATA_DIR / "dial_log.csv"
    if not log.exists():
        print("No dial_log.csv found. Start dialing first.")
        return
    outcomes = Counter()
    today_outcomes = Counter()
    today_str = date.today().isoformat()
    rows_total = 0
    with open(log, newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows_total += 1
            o = r.get("outcome", "").strip().lower()
            outcomes[o or "<empty>"] += 1
            ts = r.get("timestamp_pt", "")
            if ts.startswith(today_str):
                today_outcomes[o or "<empty>"] += 1

    print(f"=== Dial log summary ===")
    print(f"Total rows: {rows_total}")
    print()
    print("All-time outcomes:")
    for o, c in outcomes.most_common():
        print(f"  {o:<22} {c}")
    if today_outcomes:
        print()
        print("Today's outcomes:")
        for o, c in today_outcomes.most_common():
            print(f"  {o:<22} {c}")

    # Hot-lead callout (any 'talked' outcome)
    talked_today = today_outcomes.get("talked", 0)
    if talked_today:
        print()
        print(f"!! {talked_today} live conversation(s) today -- tag Hammer in #broker-pipeline !!")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--summarize", action="store_true", help="Summarize dial_log.csv")
    parser.add_argument("--file", help="Specific CSV to print (override today auto-detect)")
    parser.add_argument("--limit", type=int, default=32, help="Max rows to print")
    args = parser.parse_args()

    if args.summarize:
        summarize_dial_log()
        return

    if args.file:
        path = Path(args.file)
        if not path.exists():
            print(f"FATAL: {path} not found", file=sys.stderr)
            sys.exit(1)
    else:
        path = find_today_dial_list()
        if not path:
            print("FATAL: no dial list for today. Run build_phone_dial_list.py first.", file=sys.stderr)
            sys.exit(1)

    print_dial_sheet(path, args.limit)


if __name__ == "__main__":
    main()
