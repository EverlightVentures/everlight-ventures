#!/usr/bin/env python3
"""
Blinko offline-first queue drainer.

Per [[feedback_offline_first_bidirectional_sync]]: writes queue locally when
e5-mother is unreachable and drain on reconnect -- no single-source state.

- Session notes are dropped as timestamped `.md` files into
  `_logs/blinko_log_queue/` (by any caller, e.g. `enqueue()` below).
- This drainer POSTs each queued note to Blinko on e5-mother. Successes move
  to `processed/`; failures stay queued for the next run (idempotent).
- Safe when mother is down: it logs and leaves the queue intact.

Replaces the stale `blinko_log_ingest.sh` (which targeted the dead mother at
129.159.38.250 and pulled FROM Oracle rather than pushing the local queue).

Usage:
  python3 blinko_queue_drain.py                 # drain the queue
  python3 blinko_queue_drain.py --enqueue FILE  # queue a markdown file, then drain
  echo "# note" | python3 blinko_queue_drain.py --enqueue -
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path("/mnt/sdcard/AA_MY_DRIVE")
QUEUE = WORKSPACE / "_logs" / "blinko_log_queue"
PROCESSED = QUEUE / "processed"
LOG = WORKSPACE / "_logs" / "blinko_queue_drain.log"
TIMEOUT = float(os.environ.get("BLINKO_TIMEOUT", "5"))

# Blinko lives on e5-mother (tailnet). We try a candidate list rather than a
# single address so the drainer survives name-resolution gaps and relocation.
# NOTE: a stale shell BLINKO_URL=http://163.192.19.196:1111 points at Oracle
# Micro (the xlm-bot host, NO Blinko) -- we deliberately do NOT trust it.
_BAD_HOSTS = ("163.192.19.196", "129.159.38.250")  # xlm-bot host + dead old mother


def _candidate_urls() -> list[str]:
    urls = []
    env = (os.environ.get("BLINKO_URL") or "").strip().rstrip("/")
    if env and not any(b in env for b in _BAD_HOSTS):
        urls.append(env)
    urls += [
        "http://e5-mother:1111",        # tailnet hostname (when MagicDNS resolves)
        "http://100.125.115.95:1111",   # e5-mother tailnet IP (when tailscale up)
        "http://127.0.0.1:1111",        # local tunnel/mirror, if present
    ]
    # de-dup preserving order
    seen, out = set(), []
    for u in urls:
        if u not in seen:
            seen.add(u); out.append(u)
    return out


def _log(msg: str) -> None:
    line = f"[{datetime.now(timezone.utc).isoformat()}] {msg}"
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a") as fh:
        fh.write(line + "\n")
    # Console echo only when interactive. The */17 cron redirects stdout back
    # into LOG (`>> blinko_queue_drain.log`); an unconditional print() would
    # write every line twice. The final JSON summary in _main() stays printed
    # (it is the intended cron-captured run report and is not also file-logged).
    if sys.stdout.isatty():
        print(line)


def enqueue(text: str) -> Path:
    """Drop a markdown note into the queue. Returns its path."""
    QUEUE.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    path = QUEUE / f"note_{stamp}.md"
    path.write_text(text)
    return path


def _post_note_to(url: str, content: str) -> bool:
    payload = json.dumps({"content": content, "type": 1}).encode()
    req = urllib.request.Request(
        f"{url}/api/v1/note/upsert",
        data=payload, method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            body = r.read().decode()
            return r.status in (200, 201) and ('"id"' in body or '"success"' in body)
    except Exception:
        return False


def _health_ok(url: str) -> bool:
    """Reachability check via GET /health -- does NOT write a note."""
    try:
        req = urllib.request.Request(f"{url}/health", method="GET")
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status == 200
    except Exception:
        return False


def _reachable_blinko() -> str | None:
    """First candidate URL that is reachable. None if all are down.

    Prefer GET /health (no side effect). The old implementation proved
    reachability by POSTing a throwaway '#hive/probe' note to /upsert on EVERY
    drain -- ~85 junk notes/day on the */17 cron, polluting RAG search. We only
    fall back to the POST probe if a target does not serve /health, so any
    Blinko variant still works while blinko_lite stops littering the brain.
    """
    for url in _candidate_urls():
        if _health_ok(url):
            return url
    probe = f"# blinko reachability probe {datetime.now(timezone.utc).isoformat()}\n#hive/probe"
    for url in _candidate_urls():
        if _post_note_to(url, probe):
            return url
    return None


def drain() -> dict:
    QUEUE.mkdir(parents=True, exist_ok=True)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    pending = sorted(p for p in QUEUE.glob("*.md") if p.is_file())
    if not pending:
        return {"queued": 0, "ingested": 0, "remaining": 0}
    target = _reachable_blinko()
    if not target:
        _log(f"drain skipped: no reachable Blinko ({', '.join(_candidate_urls())}); {len(pending)} note(s) stay queued")
        return {"queued": len(pending), "ingested": 0, "remaining": len(pending)}
    ingested = 0
    for f in pending:
        if _post_note_to(target, f.read_text()):
            f.rename(PROCESSED / f.name)
            ingested += 1
        else:
            _log(f"drain halted mid-run: {target} stopped accepting; {len(pending) - ingested} note(s) stay queued")
            break
    remaining = len(list(QUEUE.glob("*.md")))
    if ingested:
        _log(f"ingested {ingested} note(s) into Blinko @ {target}; {remaining} remaining")
    return {"queued": len(pending), "ingested": ingested, "remaining": remaining, "target": target}


def _main(argv) -> int:
    ap = argparse.ArgumentParser(description="Blinko offline-first queue drainer.")
    ap.add_argument("--enqueue", metavar="FILE", help="queue a markdown file ('-' for stdin) then drain")
    args = ap.parse_args(argv)
    if args.enqueue:
        text = sys.stdin.read() if args.enqueue == "-" else Path(args.enqueue).read_text()
        path = enqueue(text)
        _log(f"enqueued {path.name} ({len(text)} bytes)")
    print(json.dumps(drain(), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
