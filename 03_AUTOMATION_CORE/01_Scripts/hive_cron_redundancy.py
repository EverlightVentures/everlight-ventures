"""
Hive Cron Redundancy -- active-passive failover for the wholesale cron without
needing a distributed lock service.

Doctrine (Rich, 2026-05-15):
    "if the phone cron goes down, Oracle cron should be the backup and there
     should be watch services for both. this needs to be a system wide sync."

Architecture (active-passive via heartbeat polling):

    Phone cron (primary)  -- fires hourly, writes heartbeat, runs the job
    Oracle cron (secondary) -- fires hourly, checks for primary heartbeat:
                                 - heartbeat fresh (< 65 min)? skip the run
                                 - heartbeat stale or missing?  run the job +
                                                                 alert Slack
    Watchdog (both sides)  -- every 5 min, reads all heartbeats:
                                 - all stale > 30 min? alert "wholesale silent
                                                              on EVERY host"
                                 - one stale, one fresh? log info

State location: _state/heartbeats/wholesale-{hostname}.json (synced via git +
Syncthing). Stale-detection threshold matches one cron tick (65 min cushion
for the hourly schedule). Watchdog window is 30 min (3x the every-15-min tick
of more-frequent jobs).

CLI usage:

    # called by the cron wrapper to decide if this host should run
    python3 hive_cron_redundancy.py should-run wholesale_hourly
    # exit 0 = yes run; exit 1 = no skip (another host is primary)

    # called at the end of a successful job
    python3 hive_cron_redundancy.py heartbeat wholesale_hourly

    # watchdog tick (every 5 min by cron)
    python3 hive_cron_redundancy.py watchdog

    # status snapshot
    python3 hive_cron_redundancy.py status
"""

from __future__ import annotations

import json
import os
import socket
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

WS = Path(os.environ.get("HIVE_LOCAL_WS", "/mnt/sdcard/AA_MY_DRIVE"))
HEARTBEAT_DIR = WS / "_state" / "heartbeats"
HEARTBEAT_DIR.mkdir(parents=True, exist_ok=True)

# Stale thresholds (in minutes)
STALE_PRIMARY_MIN = 65   # one hourly tick + 5 min cushion
STALE_WATCHDOG_MIN = 30  # raise alert when no host heartbeat in this window

# Active-passive role hint. Set on the secondary host (Oracle) to opt into
# defer-to-primary behavior. Phone leaves this unset (defaults to primary).
ROLE = os.environ.get("WHOLESALE_REDUNDANCY_ROLE", "primary").lower()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _host() -> str:
    return socket.gethostname() or os.environ.get("HOSTNAME", "unknown")


def _hb_path(job: str, host: Optional[str] = None) -> Path:
    h = host or _host()
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in h)
    return HEARTBEAT_DIR / f"{job}-{safe}.json"


def heartbeat(job: str, status: str = "ok", extra: Optional[dict] = None) -> Path:
    """Write a heartbeat for this host + job. Called at end of every cron run."""
    payload = {
        "ts_utc": _now().isoformat(),
        "host": _host(),
        "role": ROLE,
        "job": job,
        "status": status,
        "extra": extra or {},
    }
    p = _hb_path(job)
    p.write_text(json.dumps(payload, indent=2))
    return p


def read_all_heartbeats(job: str) -> list[dict]:
    """Read every host's heartbeat for this job."""
    out = []
    for p in HEARTBEAT_DIR.glob(f"{job}-*.json"):
        try:
            out.append(json.loads(p.read_text()))
        except Exception:
            continue
    return out


def freshest_heartbeat(job: str, exclude_host: Optional[str] = None) -> Optional[dict]:
    """Return the most-recent heartbeat across all hosts (optionally excluding self)."""
    beats = read_all_heartbeats(job)
    if exclude_host:
        beats = [b for b in beats if b.get("host") != exclude_host]
    if not beats:
        return None
    return max(beats, key=lambda b: b.get("ts_utc", ""))


def should_run(job: str) -> tuple[bool, str]:
    """
    Decide whether THIS host should run the job on this tick.

    Logic:
        - role=primary: always run (phone is the canonical runner).
        - role=secondary: run only if NO other host has a recent heartbeat.
                          "recent" = within STALE_PRIMARY_MIN minutes.

    Returns (should_run, reason).
    """
    if ROLE == "primary":
        return True, "role=primary always runs"

    other = freshest_heartbeat(job, exclude_host=_host())
    if not other:
        return True, "no peer heartbeat yet -- secondary takes over"

    try:
        peer_ts = datetime.fromisoformat(other["ts_utc"])
    except Exception:
        return True, "peer heartbeat unparseable -- secondary takes over"

    age = _now() - peer_ts
    if age < timedelta(minutes=STALE_PRIMARY_MIN):
        return False, (
            f"peer {other.get('host')} heartbeat is "
            f"{int(age.total_seconds() // 60)}m old -- skip"
        )
    return True, (
        f"peer {other.get('host')} heartbeat is "
        f"{int(age.total_seconds() // 60)}m old (stale) -- secondary taking over"
    )


def watchdog(job: str = "wholesale_hourly") -> dict:
    """
    Inspect all heartbeats. Return a summary dict. Caller decides whether to
    post to Slack (CLI mode does post on critical state).
    """
    beats = read_all_heartbeats(job)
    now = _now()
    fresh = []
    stale = []
    for b in beats:
        try:
            ts = datetime.fromisoformat(b["ts_utc"])
            age_min = int((now - ts).total_seconds() / 60)
        except Exception:
            continue
        entry = {**b, "age_min": age_min}
        if age_min <= STALE_WATCHDOG_MIN:
            fresh.append(entry)
        else:
            stale.append(entry)

    summary = {
        "job": job,
        "ts_utc": now.isoformat(),
        "fresh_hosts": [h["host"] for h in fresh],
        "stale_hosts": [h["host"] for h in stale],
        "total_known_hosts": len({b.get("host") for b in beats}),
        "critical": len(beats) > 0 and len(fresh) == 0,
        "raw": fresh + stale,
    }
    return summary


def _post_slack(text: str) -> bool:
    """Best-effort Slack post via env-configured webhook or bot token."""
    webhook = os.environ.get("SLACK_HIVE_ALERTS_WEBHOOK", "")
    if not webhook:
        return False
    try:
        from urllib.request import Request, urlopen
        body = json.dumps({"text": text}).encode()
        req = Request(webhook, data=body, headers={"Content-Type": "application/json"})
        urlopen(req, timeout=5)
        return True
    except Exception:
        return False


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    cmd = argv[1]
    job = argv[2] if len(argv) > 2 else "wholesale_hourly"

    if cmd == "should-run":
        ok, why = should_run(job)
        print(f"{'RUN' if ok else 'SKIP'}: {why}")
        return 0 if ok else 1

    if cmd == "heartbeat":
        p = heartbeat(job)
        print(f"wrote heartbeat: {p}")
        return 0

    if cmd == "watchdog":
        summary = watchdog(job)
        print(json.dumps(summary, indent=2))
        if summary["critical"]:
            text = (
                f":rotating_light: WHOLESALE CRON SILENT on every host. "
                f"Last {len(summary['raw'])} heartbeats all > {STALE_WATCHDOG_MIN}m old. "
                f"Hosts: {[h['host'] for h in summary['raw']]}. "
                f"Job: {job}."
            )
            posted = _post_slack(text)
            print(f"alert {'posted to Slack' if posted else 'NOT posted (no webhook)'}")
            return 2 if not posted else 0
        return 0

    if cmd == "status":
        summary = watchdog(job)
        print(json.dumps(summary, indent=2))
        return 0

    print(f"unknown command: {cmd}")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
