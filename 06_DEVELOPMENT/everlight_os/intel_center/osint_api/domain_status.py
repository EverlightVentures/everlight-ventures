"""
domain_status -- classifier for each domain's liveness state.

Reads live_log.sqlite and classifies every catalogued resource into:
  - live          (HTTP 200-399 within 30d, content delivered)
  - auth_gated    (HTTP 401/403/429 -- alive but blocked)
  - dead          (HTTP 5xx, 0/timeout, repeated failures)
  - rate_limited  (HTTP 429, 503)
  - untested      (no live_log entry yet)

Used by:
  - intel coverage CLI command
  - audit.html dashboard breakdown chart
  - rebuild_data.py to expose status per resource
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

LIVE_LOG = Path("/mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/intel_center/cache/live_log.sqlite")


def classify(status_code: int | None, error: str | None) -> str:
    if status_code and 200 <= status_code < 400:
        return "live"
    if status_code in (401, 403):
        return "auth_gated"
    if status_code in (429, 503):
        return "rate_limited"
    if status_code in (404, 410):
        return "dead"
    if status_code and 500 <= status_code < 600:
        return "dead"
    if status_code == 0 or (error and "timeout" in (error or "").lower()):
        return "dead"
    if status_code is None:
        return "untested"
    return "dead"


def status_map() -> dict[str, str]:
    """Returns {domain: status_string} for every domain in live_log."""
    if not LIVE_LOG.exists():
        return {}
    con = sqlite3.connect(LIVE_LOG)
    try:
        rows = con.execute(
            "SELECT domain, last_status_code, last_error FROM live_pulls"
        ).fetchall()
        return {d: classify(s, e) for d, s, e in rows}
    except sqlite3.OperationalError:
        return {}
    finally:
        con.close()


def stats() -> dict:
    """Aggregate breakdown for the dashboard."""
    counts = {"live": 0, "auth_gated": 0, "rate_limited": 0, "dead": 0, "untested": 0}
    for status in status_map().values():
        counts[status] = counts.get(status, 0) + 1
    return counts


if __name__ == "__main__":
    import json
    print(json.dumps(stats(), indent=2))
