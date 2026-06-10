"""dnc_writer -- maintains /AA_MY_DRIVE/Wholesale/dnc_list.csv as the
authoritative do-not-contact list. Auto-add on opt-out. Idempotent.

Streubel + anyone else flagged as permaban is seeded manually. Future opt-outs
get auto-added by the triage_daemon.

Per halt-policy v2 (2026-05-07): the DNC list IS the new safety net. The global
WHOLESALE_OUTBOUND_HALT goes away; the DNC list takes over.
"""
from __future__ import annotations

import csv
import fcntl
import time
from pathlib import Path

DNC_PATH = Path("/AA_MY_DRIVE/Wholesale/dnc_list.csv")
HEADERS = ["email", "name", "reason", "added_by", "added_at", "source_thread_id"]


def _ensure_file() -> None:
    DNC_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not DNC_PATH.exists():
        with DNC_PATH.open("w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(HEADERS)


def _normalize(email: str) -> str:
    return (email or "").strip().lower()


def is_dnc(email: str) -> bool:
    """Return True if this email is on the list."""
    _ensure_file()
    target = _normalize(email)
    if not target:
        return False
    with DNC_PATH.open("r", newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            if _normalize(row.get("email", "")) == target:
                return True
    return False


def add_dnc(email: str, name: str = "", reason: str = "opt_out_reply",
            added_by: str = "triage_daemon", source_thread_id: str = "") -> dict:
    """Idempotent add. Returns {added: bool, was_already_present: bool, ...}."""
    _ensure_file()
    e = _normalize(email)
    if not e:
        return {"added": False, "error": "empty email"}

    if is_dnc(e):
        return {"added": False, "was_already_present": True, "email": e}

    row = {
        "email": e,
        "name": name.strip(),
        "reason": reason,
        "added_by": added_by,
        "added_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "source_thread_id": source_thread_id,
    }
    with DNC_PATH.open("a", newline="", encoding="utf-8") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            csv.DictWriter(f, fieldnames=HEADERS).writerow(row)
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
    return {"added": True, "was_already_present": False, **row}


def list_dnc() -> list[dict]:
    _ensure_file()
    with DNC_PATH.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        for r in list_dnc():
            print(f"  {r['email']:40} | {r['reason']:30} | {r['added_at']}")
        print(f"\ntotal: {len(list_dnc())}")
        sys.exit(0)
    cmd = sys.argv[1]
    if cmd == "add" and len(sys.argv) >= 3:
        result = add_dnc(sys.argv[2],
                         name=sys.argv[3] if len(sys.argv) > 3 else "",
                         reason=sys.argv[4] if len(sys.argv) > 4 else "opt_out_reply")
        print(result)
    elif cmd == "check" and len(sys.argv) >= 3:
        print(f"is_dnc({sys.argv[2]!r}) = {is_dnc(sys.argv[2])}")
    else:
        print("usage: dnc_writer.py [add <email> [name] [reason] | check <email>]")
