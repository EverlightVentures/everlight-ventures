#!/usr/bin/env python3
"""Hive Mind scheduled agent runner.

Reads agent_schedules.yaml, computes which schedule entries are due (within
the current minute, America/Los_Angeles time), and dispatches each one.

Modes:
  chat     -- calls the hive_directory /api/team/<slug>/chat endpoint on
              localhost:8503. Fast, returns the agent's reply.
  dispatch -- calls hive_mind.dispatcher.dispatch() in-process. Full war-room.

Outputs:
  Each run is logged to /home/opc/hive_schedule/runs.jsonl as one JSON line.
  A compact status is also written to /home/opc/hive_schedule/last_run.json
  so the directory /api/team/<slug>/activity endpoint can surface it.

Intended to be invoked every minute via systemd timer or cron:
  * * * * * /usr/bin/python3 /home/opc/06_DEVELOPMENT/everlight_os/hive_mind/run_scheduled_agents.py

Idempotency: each (slug, cron, minute) tuple is marked in a lock file so a
schedule fires at most once per minute even if the runner is invoked twice.

No em-dash or en-dash characters appear in this file.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

ROOT = Path(__file__).resolve().parent
SCHEDULES_FILE = ROOT / "agent_schedules.yaml"

LOG_DIR = Path(os.environ.get("HIVE_SCHEDULE_DIR", "/home/opc/hive_schedule"))
LOG_DIR.mkdir(parents=True, exist_ok=True)
RUNS_FILE = LOG_DIR / "runs.jsonl"
LOCK_DIR = LOG_DIR / ".fired"
LOCK_DIR.mkdir(parents=True, exist_ok=True)
LAST_RUN_FILE = LOG_DIR / "last_run.json"

HIVE_DIRECTORY_BASE = os.environ.get(
    "HIVE_DIRECTORY_BASE", "http://127.0.0.1:8503"
)
PT = ZoneInfo("America/Los_Angeles")


def _cron_field_matches(spec: str, val: int) -> bool:
    """Match a single cron field (minute, hour, dom, month, dow) against
    a value. Supports: *, N, N,M,..., A-B, */N. No named months or dows."""
    spec = spec.strip()
    if spec == "*":
        return True
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        step = 1
        if "/" in part:
            base, step_str = part.split("/", 1)
            step = int(step_str)
            part = base
        if part in ("", "*"):
            if val % step == 0:
                return True
            continue
        if "-" in part:
            lo, hi = part.split("-", 1)
            lo_i, hi_i = int(lo), int(hi)
            if lo_i <= val <= hi_i and (val - lo_i) % step == 0:
                return True
            continue
        if int(part) == val:
            return True
    return False


def _matches_cron(cron: str, now: datetime) -> bool:
    parts = cron.split()
    if len(parts) != 5:
        return False
    minute, hour, dom, month, dow = parts
    return (
        _cron_field_matches(minute, now.minute)
        and _cron_field_matches(hour, now.hour)
        and _cron_field_matches(dom, now.day)
        and _cron_field_matches(month, now.month)
        and _cron_field_matches(dow, now.isoweekday() % 7)  # Sunday = 0
    )


def _already_fired(slug: str, cron: str, now: datetime) -> bool:
    """Idempotency: mark (slug, cron, YYYY-mm-dd-HHMM) once per minute."""
    stamp = now.strftime("%Y%m%d_%H%M")
    safe_cron = cron.replace(" ", "_").replace("/", "x").replace("*", "A")
    marker = LOCK_DIR / f"{slug}__{safe_cron}__{stamp}.lock"
    if marker.exists():
        return True
    marker.write_text("")
    # Prune marker files older than 2 days
    cutoff = time.time() - 2 * 86400
    for old in LOCK_DIR.glob("*.lock"):
        try:
            if old.stat().st_mtime < cutoff:
                old.unlink()
        except Exception:
            pass
    return False


def _log_run(record: dict) -> None:
    record["logged_at"] = datetime.now(timezone.utc).isoformat()
    with RUNS_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    # Maintain last-run map keyed by slug
    try:
        current = {}
        if LAST_RUN_FILE.exists():
            current = json.loads(LAST_RUN_FILE.read_text(encoding="utf-8"))
        current[record["slug"]] = {
            "name": record.get("name"),
            "task_name": record.get("task_name"),
            "mode": record.get("mode"),
            "ok": record.get("ok"),
            "reply_preview": (record.get("reply", "") or "")[:280],
            "logged_at": record["logged_at"],
        }
        LAST_RUN_FILE.write_text(
            json.dumps(current, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    except Exception:
        pass


def _fire_chat(slug: str, task: str, timeout: int = 60) -> dict:
    """Hit the hive_directory chat endpoint in-process on this VM."""
    url = f"{HIVE_DIRECTORY_BASE}/api/team/{slug}/chat"
    data = json.dumps({"message": task, "max_tokens": 600}).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read().decode("utf-8")
            j = json.loads(body)
            return j
    except urllib.error.HTTPError as e:
        return {"ok": False, "error": f"HTTP {e.code}", "reply": ""}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}", "reply": ""}


def _fire_dispatch(slug: str, task: str) -> dict:
    """Dispatch via the hive_directory endpoint so progress is tracked the
    same way as manual Launch Agent clicks."""
    url = f"{HIVE_DIRECTORY_BASE}/api/team/{slug}/dispatch"
    data = json.dumps({"task": task}).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            j = json.loads(r.read().decode("utf-8"))
            return j
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def main() -> int:
    if not SCHEDULES_FILE.exists():
        print(f"no schedules file at {SCHEDULES_FILE}", file=sys.stderr)
        return 1

    cfg = yaml.safe_load(SCHEDULES_FILE.read_text(encoding="utf-8")) or {}
    schedules = cfg.get("schedules") or []
    now = datetime.now(PT).replace(second=0, microsecond=0)

    fired = 0
    skipped = 0
    for entry in schedules:
        if not entry.get("enabled", True):
            continue
        slug = entry.get("slug", "").strip()
        cron = entry.get("cron", "").strip()
        if not slug or not cron:
            continue
        if not _matches_cron(cron, now):
            continue
        if _already_fired(slug, cron, now):
            skipped += 1
            continue

        mode = (entry.get("mode") or "chat").lower()
        task = (entry.get("task") or "").strip()
        task_name = entry.get("name", "")
        started_at = time.time()

        if mode == "dispatch":
            result = _fire_dispatch(slug, task)
        else:
            result = _fire_chat(slug, task)

        took = time.time() - started_at
        record = {
            "slug": slug,
            "task_name": task_name,
            "mode": mode,
            "cron": cron,
            "fired_at_pt": now.isoformat(),
            "duration_sec": round(took, 2),
            "ok": bool(result.get("ok")),
            "name": result.get("name"),
            "reply": result.get("reply", ""),
            "error": result.get("error"),
            "session_id": result.get("session_id"),
        }
        _log_run(record)
        fired += 1
        print(
            f"[fired] slug={slug} mode={mode} task={task_name!r} "
            f"ok={record['ok']} dur={took:.1f}s"
        )

    print(f"[done] fired={fired} skipped={skipped} at {now.isoformat()} PT")
    return 0


if __name__ == "__main__":
    sys.exit(main())
