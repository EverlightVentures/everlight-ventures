#!/usr/bin/env python3
"""
mailbox_readstate.py -- per-device read watermark for _state/AGENT_MAILBOX.md

WHY THIS EXISTS
---------------
The mailbox is the family coordination board. Every agent on every device is
supposed to read it AND write to it, so the phone and the AceMagician can both
see what the other changed. That only works if a device knows WHERE IT LEFT OFF.

Without a watermark an agent either re-reads 450 KB every session (it won't) or
skips it entirely (it did). Both fail the same way: one machine claims work is
synced, the other has no record of it, and nobody can tell which is true.

This tracks, per device: the last mailbox entry that device actually read, plus
a hash of that entry. The hash matters -- if the mailbox is ever rewritten
rather than appended, the index alone would silently point at the wrong place.

USAGE
-----
  mailbox_readstate.py --status              how far behind is this device
  mailbox_readstate.py --unread              print entries not yet read
  mailbox_readstate.py --unread --limit 5    print the 5 oldest unread
  mailbox_readstate.py --catch-up            print unread, then mark read
  mailbox_readstate.py --mark-read           mark current tip as read
  mailbox_readstate.py --all-devices         who is behind, across the fleet

  --device NAME   override auto-detected device id
  --json          machine-readable output

EXIT CODES
  0  up to date (or action completed)
  2  unread entries exist  (so a shell hook can branch on it)
"""

import argparse
import hashlib
import json
import os
import re
import socket
import sys
from datetime import datetime, timezone

WORKSPACE_CANDIDATES = [
    "/mnt/sdcard/AA_MY_DRIVE",   # phone (source of truth)
    "/AA_MY_DRIVE",              # AceMagician canonical (consolidated 2026-08-06)
    "/home/richgee/AA_MY_DRIVE", # AceMagician legacy, retired
    "/home/ubuntu/AA_MY_DRIVE",  # e5-mother
]

# The fleet, for the --all-devices accountability view. Listed explicitly so a
# device that has never once read the mailbox still shows up as behind rather
# than being invisible.
KNOWN_DEVICES = ["phone", "acemagician", "e5-mother"]

# Mailbox entries are delimited by a dated H2. Both the session exporter and
# hand-written entries use this shape, and session_brief.py parses it too, so
# it is the de-facto record separator. Keep these in agreement.
ENTRY_RE = re.compile(r"^## \[(\d{4}-\d{2}-\d{2})[^\]]*\]\s*(.*)$")


def find_workspace():
    env = os.environ.get("EL_HOME")
    if env and os.path.isdir(env):
        return env
    for c in WORKSPACE_CANDIDATES:
        if os.path.isdir(c):
            return c
    sys.exit("ERROR: could not locate the workspace. Set EL_HOME.")


def device_id():
    """Stable, human-readable device name.

    Hostname alone is unreliable here: the AceMagician still reports the Garuda
    default 'rich-defaultstring', and the phone's proot hostname is generic.
    Anchor on the workspace path first, which IS distinctive per device.
    """
    ws = find_workspace()
    if ws.startswith("/mnt/sdcard"):
        return "phone"
    if ws == "/AA_MY_DRIVE" or ws.startswith("/home/richgee"):
        return "acemagician"
    if ws.startswith("/home/ubuntu"):
        return "e5-mother"
    return socket.gethostname() or "unknown"


def parse_entries(path):
    """Split the mailbox into entries. Returns [{index,date,title,body,hash}]."""
    if not os.path.isfile(path):
        sys.exit(f"ERROR: mailbox not found at {path}")
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        lines = fh.readlines()

    entries, cur = [], None
    for line in lines:
        m = ENTRY_RE.match(line.rstrip("\n"))
        if m:
            if cur:
                entries.append(cur)
            cur = {"date": m.group(1), "title": m.group(2).strip(), "lines": [line]}
        elif cur:
            cur["lines"].append(line)
    if cur:
        entries.append(cur)

    for i, e in enumerate(entries):
        e["index"] = i
        e["body"] = "".join(e["lines"])
        e["hash"] = hashlib.sha256(e["body"].encode("utf-8")).hexdigest()[:16]
        del e["lines"]
    return entries


def state_path(ws):
    return os.path.join(ws, "_state", "mailbox_readstate.json")


def load_state(ws):
    p = state_path(ws)
    if not os.path.isfile(p):
        return {}
    try:
        with open(p, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (json.JSONDecodeError, OSError):
        # A corrupt watermark must not block reading the mailbox. Worst case
        # the device re-reads from the top, which is safe; silently trusting a
        # broken file and skipping entries is not.
        print("WARN: read-state file unreadable, treating device as unread",
              file=sys.stderr)
        return {}


def save_state(ws, state):
    p = state_path(ws)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=2, sort_keys=True)
        fh.write("\n")
    os.replace(tmp, p)   # atomic; a torn write here would lose the watermark


def resolve_position(entries, rec):
    """Where does this device actually stand?

    Returns (first_unread_index, drift_note). Uses the stored hash to detect a
    rewritten mailbox: if the recorded entry no longer hashes the same, the
    index is meaningless and we fall back to re-reading everything.
    """
    if not rec:
        return 0, None
    idx = rec.get("last_entry_index")
    hsh = rec.get("last_entry_hash")
    if idx is None or idx < 0:
        return 0, None
    if idx >= len(entries):
        return 0, (f"watermark points at entry {idx} but the mailbox only has "
                   f"{len(entries)}. It was truncated or replaced. Re-reading all.")
    if hsh and entries[idx]["hash"] != hsh:
        return 0, (f"entry {idx} no longer matches its recorded hash. The mailbox "
                   f"was edited in place, not appended. Re-reading all.")
    return idx + 1, None


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--status", action="store_true", help="how far behind (default)")
    g.add_argument("--unread", action="store_true", help="print unread entries")
    g.add_argument("--catch-up", action="store_true", help="print unread, then mark read")
    g.add_argument("--mark-read", action="store_true", help="mark tip as read")
    g.add_argument("--all-devices", action="store_true", help="fleet-wide view")
    ap.add_argument("--device", help="override device id")
    ap.add_argument("--limit", type=int, help="cap entries printed")
    ap.add_argument("--json", action="store_true", help="machine-readable")
    args = ap.parse_args()

    ws = find_workspace()
    mailbox = os.path.join(ws, "_state", "AGENT_MAILBOX.md")
    entries = parse_entries(mailbox)
    total = len(entries)
    dev = args.device or device_id()
    state = load_state(ws)

    if args.all_devices:
        rows = []
        for d, rec in sorted(state.items()):
            start, _ = resolve_position(entries, rec)
            rows.append({"device": d, "read_through": rec.get("last_entry_index"),
                         "unread": total - start,
                         "last_read": rec.get("last_read_iso")})
        # Always list the whole fleet, including devices that have NEVER checked
        # in. A device missing from the table reads as "fine"; a device showing
        # 'never' reads as "this one is behind". The second is the honest signal
        # and is the entire point of the accountability view.
        for d in KNOWN_DEVICES + [dev]:
            if d not in state and not any(r["device"] == d for r in rows):
                rows.append({"device": d, "read_through": None,
                             "unread": total, "last_read": None})
        if args.json:
            print(json.dumps({"total_entries": total, "devices": rows}, indent=2))
        else:
            print(f"Mailbox: {total} entries at {mailbox}\n")
            print(f"  {'device':<14} {'read thru':>10} {'unread':>8}   last read")
            for r in rows:
                rt = r["read_through"]
                print(f"  {r['device']:<14} {str(rt) if rt is not None else '-':>10} "
                      f"{r['unread']:>8}   {r['last_read'] or 'never'}")
        return 0

    rec = state.get(dev)
    start, drift = resolve_position(entries, rec)
    unread = entries[start:]
    if args.limit:
        unread = unread[:args.limit]

    if args.mark_read:
        if total == 0:
            print("mailbox is empty, nothing to mark")
            return 0
        tip = entries[-1]
        state[dev] = {"last_entry_index": tip["index"],
                      "last_entry_hash": tip["hash"],
                      "last_entry_title": tip["title"][:120],
                      "last_read_iso": datetime.now(timezone.utc).isoformat()}
        save_state(ws, state)
        print(f"{dev}: marked read through entry {tip['index']} of {total - 1} "
              f"({tip['date']} {tip['title'][:60]})")
        return 0

    if args.unread or args.catch_up:
        if drift:
            print(f"!! {drift}\n", file=sys.stderr)
        if not unread:
            print(f"{dev}: up to date, {total} entries read.")
            return 0
        print(f"===== {dev}: {len(entries) - start} unread of {total} "
              f"(showing {len(unread)}) =====\n")
        for e in unread:
            print(e["body"].rstrip() + "\n")
        if args.catch_up:
            tip = entries[-1]
            state[dev] = {"last_entry_index": tip["index"],
                          "last_entry_hash": tip["hash"],
                          "last_entry_title": tip["title"][:120],
                          "last_read_iso": datetime.now(timezone.utc).isoformat()}
            save_state(ws, state)
            print(f"----- {dev}: marked read through entry {tip['index']} -----")
            return 0
        return 2

    # default: --status
    n_unread = total - start
    payload = {"device": dev, "total_entries": total,
               "read_through": rec.get("last_entry_index") if rec else None,
               "unread": n_unread, "mailbox": mailbox,
               "last_read": rec.get("last_read_iso") if rec else None,
               "drift": drift}
    if args.json:
        print(json.dumps(payload, indent=2))
    elif n_unread == 0:
        print(f"{dev}: up to date ({total} entries).")
    else:
        rt = rec.get("last_entry_index") if rec else None
        was = f"entry {rt}" if rt is not None else "never read"
        print(f"{dev}: {n_unread} UNREAD of {total} (last read: {was}).")
        if drift:
            print(f"  !! {drift}")
        print(f"  catch up:  python3 {os.path.relpath(__file__, ws)} --catch-up")
    return 2 if n_unread else 0


if __name__ == "__main__":
    sys.exit(main())
