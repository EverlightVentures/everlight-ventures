#!/usr/bin/env python3
"""
blinko_sync.py -- bidirectional, additive, content-deduped sync between the
phone canonical brain (_state/blinko_lite.db) and the e5 primary
(/home/ubuntu/e5_data/blinko_lite.db).

Keeps both brains in constant sync without losing anything:
  - dedupe key = sha256(content.strip()); a note already present (by content)
    on a side is never re-added.
  - PUSH: notes the phone has that e5 lacks -> inserted on e5.
  - PULL: notes e5 has that the phone lacks -> inserted locally.
  - NEVER deletes. (Dedupe/merge of history is blinko_merge.py's job.)

Transport is SSH (the e5 :1111 API only binds locally/tailnet, and the phone
proot cannot route the tailnet -- the public-IP `ssh e5` host is the one path
that works). Only content-hashes + the delta rows cross the wire, and this same
file self-ships to e5 and runs there via the `hashes`/`export`/`import`
subcommands, so there is no second script to keep in sync.

Usage (phone):
  python3 blinko_sync.py                 # run a full two-way sync
Remote subcommands (invoked over SSH on e5, operate on the given db):
  python3 blinko_sync.py hashes  <db>    # print every note's content-hash
  python3 blinko_sync.py export  <db>    # stdin=hashes -> stdout=JSON rows
  python3 blinko_sync.py import  <db>    # stdin=JSON rows -> insert new-by-hash
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path("/mnt/sdcard/AA_MY_DRIVE")
LOCAL_DB = WORKSPACE / "_state" / "blinko_lite.db"
LOG = WORKSPACE / "_logs" / "blinko_sync.log"
REMOTE_HOST = "e5"                                   # ssh config: public-IP host
REMOTE_DB = "/home/ubuntu/e5_data/blinko_lite.db"
REMOTE_SELF = "/tmp/blinko_sync.py"
SSH = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=12"]
SCP = ["scp", "-o", "BatchMode=yes", "-o", "ConnectTimeout=12"]

import sqlite3


def _hash(content: str) -> str:
    return hashlib.sha256(content.strip().encode("utf-8", "replace")).hexdigest()


def _log(msg: str) -> None:
    line = f"[{datetime.now(timezone.utc).isoformat()}] {msg}"
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a") as f:
            f.write(line + "\n")
    except Exception:
        pass
    if sys.stdout.isatty():
        print(line)


# -- db helpers (run on whichever side) ---------------------------------------

def _read_rows(db: str) -> dict[str, dict]:
    con = sqlite3.connect(db, timeout=10)
    con.row_factory = sqlite3.Row
    out: dict[str, dict] = {}
    for r in con.execute("SELECT id,content,type,tags,created_at,updated_at FROM notes"):
        if not r["content"] or not str(r["content"]).strip():
            continue
        out[_hash(r["content"])] = dict(r)
    con.close()
    return out


def _insert_missing(db: str, rows: list[dict]) -> int:
    con = sqlite3.connect(db, timeout=15)
    con.execute("PRAGMA busy_timeout=10000")
    have = {h for h in _read_rows(db)}
    used = {r[0] for r in con.execute("SELECT id FROM notes")}
    n = 0
    for row in rows:
        h = _hash(row["content"])
        if h in have:
            continue
        have.add(h)
        nid = row.get("id") or h[:12]
        if nid in used:
            nid = f"{nid}_{h[:6]}"
        used.add(nid)
        con.execute(
            "INSERT INTO notes(id,content,type,tags,created_at,updated_at) VALUES (?,?,?,?,?,?)",
            (nid, row["content"], row.get("type", 1), row.get("tags", ""),
             str(row.get("created_at") or ""), str(row.get("updated_at") or row.get("created_at") or "")),
        )
        n += 1
    con.commit()
    con.close()
    return n


# -- remote subcommands (run on e5 over SSH) ----------------------------------

def _cmd_hashes(db: str) -> int:
    for h in _read_rows(db):
        print(h)
    return 0


def _cmd_export(db: str) -> int:
    want = {ln.strip() for ln in sys.stdin if ln.strip()}
    rows = _read_rows(db)
    print(json.dumps([rows[h] for h in want if h in rows]))
    return 0


def _cmd_import(db: str) -> int:
    rows = json.loads(sys.stdin.read() or "[]")
    print(_insert_missing(db, rows))
    return 0


# -- orchestrator (run on phone) ----------------------------------------------

def sync() -> dict:
    if not LOCAL_DB.exists():
        _log(f"sync aborted: local db missing {LOCAL_DB}")
        return {"ok": False, "reason": "local db missing"}
    # 0. self-ship to e5
    if subprocess.run(SCP + [str(Path(__file__).resolve()), f"{REMOTE_HOST}:{REMOTE_SELF}"]).returncode != 0:
        _log("sync aborted: cannot reach e5 (scp failed)")
        return {"ok": False, "reason": "e5 unreachable"}

    # 1. hash sets
    r = subprocess.run(SSH + [REMOTE_HOST, f"python3 {REMOTE_SELF} hashes {REMOTE_DB}"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        _log(f"sync aborted: remote hashes failed: {r.stderr.strip()[:200]}")
        return {"ok": False, "reason": "remote hashes failed"}
    e5_hashes = {h for h in r.stdout.split() if h}
    local = _read_rows(str(LOCAL_DB))
    local_hashes = set(local)

    # 2. PUSH phone-only notes to e5
    push_rows = [local[h] for h in (local_hashes - e5_hashes)]
    pushed = 0
    if push_rows:
        r = subprocess.run(SSH + [REMOTE_HOST, f"python3 {REMOTE_SELF} import {REMOTE_DB}"],
                           input=json.dumps(push_rows), capture_output=True, text=True)
        pushed = int(r.stdout.strip() or 0) if r.returncode == 0 else 0

    # 3. PULL e5-only notes to phone
    pull_hashes = e5_hashes - local_hashes
    pulled = 0
    if pull_hashes:
        r = subprocess.run(SSH + [REMOTE_HOST, f"python3 {REMOTE_SELF} export {REMOTE_DB}"],
                           input="\n".join(pull_hashes), capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.strip():
            pulled = _insert_missing(str(LOCAL_DB), json.loads(r.stdout))

    res = {"ok": True, "pushed_to_e5": pushed, "pulled_to_phone": pulled,
           "local_total": len(local) + pulled, "e5_total": len(e5_hashes) + pushed}
    _log(f"sync ok: +{pushed} -> e5, +{pulled} -> phone "
         f"(phone~{res['local_total']}, e5~{res['e5_total']})")
    return res


def main(argv: list[str]) -> int:
    if argv and argv[0] in ("hashes", "export", "import"):
        db = argv[1] if len(argv) > 1 else str(LOCAL_DB)
        return {"hashes": _cmd_hashes, "export": _cmd_export, "import": _cmd_import}[argv[0]](db)
    print(json.dumps(sync(), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
