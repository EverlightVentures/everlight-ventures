#!/usr/bin/env python3
"""
cron_catchup.py -- anacron-for-the-Hive. Makes the wholesale team WORK even when the phone
dozes through exact-minute cron slots.

The problem (proven 2026-05-26): daily jobs (scout, tn_deal_engine, daily_lead_pipeline) are
scheduled at exact minutes. A battery-managed phone sleeps through those minutes, the slot is
skipped, and the job just never runs (last ran 5/24 -> 2 days dark). Exact-minute scheduling
assumes an always-awake host.

The fix: schedule by STALENESS, not by minute. This runs frequently (every ~20 min, firing
whenever the phone is awake at all) and, for each daily job, checks its last-run heartbeat. If
it is older than the job's interval, it runs it NOW and stamps a fresh heartbeat. So a daily
job runs at least once per day as long as the phone is awake for ANY 20-min window that day.

Reuses hive_cron_redundancy heartbeats (shared/synced phone<->e5, so the two never double-run
hard). Acquires termux-wake-lock to reduce doze. Complement: install the same crontab on e5 so
its copy fires when the phone is fully down (active-passive, already supported).

  python3 cron_catchup.py            # one catch-up cycle
  python3 cron_catchup.py --status   # show staleness of each job, run nothing
"""
from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/mnt/sdcard/AA_MY_DRIVE")
sys.path.insert(0, str(ROOT / "03_AUTOMATION_CORE" / "01_Scripts"))
LOG = ROOT / "_logs" / "cron_catchup.log"

# (job_name, interval_hours, timeout_sec, command). VALUE-FIRST order + per-job timeout so one
# slow job can never starve the rest. The Perplexity scout is DROPPED -- it 401s/returns 0 and
# hung the cycle (2026-05-26); re-add only when its source is rebuilt (hermes/assessor).
JOBS = [
    ("catchup_conductor", 4, 120, ["python3", "01_BUSINESSES/Everlight_Ventures/Wholesale/scripts/pipeline_phase_manager.py", "--state"]),
    ("catchup_daily_lead", 24, 240, ["python3", "01_BUSINESSES/Everlight_Ventures/Wholesale/scripts/daily_lead_pipeline.py"]),
    ("catchup_tn_deal_engine", 24, 420, ["bash", "03_AUTOMATION_CORE/01_Scripts/tn_deal_engine.sh"]),
]
_LOCK = ROOT / "_state" / "cron_catchup.lock"


def _log(m: str) -> None:
    line = f"[{datetime.now(timezone.utc).isoformat()}] {m}"
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a") as f:
        f.write(line + "\n")
    print(line)


def _wake_lock() -> bool:
    """Best-effort: hold a partial wake-lock so the phone keeps firing crons (reduce doze)."""
    for p in ("termux-wake-lock", "/data/data/com.termux/files/usr/bin/termux-wake-lock"):
        try:
            subprocess.run([p], timeout=5, capture_output=True)
            return True
        except Exception:
            continue
    return False


def staleness(job: str, hours: int):
    """Return (is_stale, human_reason) from the freshest heartbeat across all hosts."""
    try:
        import hive_cron_redundancy as h
        hb = h.freshest_heartbeat(job)
        if not hb:
            return True, "never run (no heartbeat)"
        ts = datetime.fromisoformat(hb["ts_utc"].replace("Z", "+00:00"))
        age = (datetime.now(timezone.utc) - ts).total_seconds() / 3600
        return age >= hours, f"{age:.1f}h since last run (interval {hours}h)"
    except Exception as e:
        return True, f"heartbeat unreadable ({type(e).__name__}) -> treat as stale"


def _locked() -> bool:
    """True if a cycle is already running (lock < 25 min old) -- prevents */20 overlap stacking."""
    try:
        if _LOCK.exists() and (datetime.now(timezone.utc).timestamp() - _LOCK.stat().st_mtime) < 25 * 60:
            return True
    except Exception:
        pass
    return False


def run_cycle(status_only: bool = False) -> dict:
    if not status_only:
        if _locked():
            _log("another catch-up cycle is running (lock fresh) -- skip")
            return {"ran": [], "skipped": ["locked"], "at": datetime.now(timezone.utc).isoformat()}
        _LOCK.parent.mkdir(parents=True, exist_ok=True)
        _LOCK.write_text(datetime.now(timezone.utc).isoformat())
        _log(f"wake-lock acquired: {_wake_lock()}")
    ran, skipped = [], []
    try:
        for job, hours, tmo, cmd in JOBS:
            stale, why = staleness(job, hours)
            if not stale:
                skipped.append(job)
                _log(f"FRESH  {job} -- {why} -- skip")
                continue
            if status_only:
                _log(f"STALE  {job} -- {why} -- WOULD run")
                continue
            _log(f"CATCH-UP {job} -- {why} -- running now (timeout {tmo}s)")
            try:
                r = subprocess.run(cmd, cwd=str(ROOT), timeout=tmo, capture_output=True, text=True)
                import hive_cron_redundancy as h
                h.heartbeat(job, status="ok" if r.returncode == 0 else f"rc{r.returncode}")
                ran.append(job)
                _log(f"  {job} done rc={r.returncode}")
            except subprocess.TimeoutExpired:
                _log(f"  {job} TIMEOUT after {tmo}s -- moved on (cycle not starved)")
            except Exception as e:
                _log(f"  {job} ERROR {type(e).__name__}: {e}")
    finally:
        if not status_only:
            try:
                _LOCK.unlink()
            except Exception:
                pass
    summary = {"ran": ran, "skipped": skipped, "at": datetime.now(timezone.utc).isoformat()}
    _log(f"cycle done: ran {len(ran)} {ran}")
    return summary


if __name__ == "__main__":
    import json
    print(json.dumps(run_cycle(status_only="--status" in sys.argv), indent=2))
