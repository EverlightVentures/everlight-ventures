"""
live_log -- single source of truth for "this domain was actually fetched and returned data"
Replaces the grep-based audit's blind spot: a domain is live_active when it has been
HTTP-called and returned 2xx/3xx within the freshness window (default 30 days).

Schema:
  live_pulls(domain PK, first_success, last_success, success_count, last_error,
             last_status_code, last_bytes, last_method)
"""
from __future__ import annotations

import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path("/mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/intel_center/cache/live_log.sqlite")


def _con():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS live_pulls (
            domain TEXT PRIMARY KEY,
            first_success TEXT,
            last_success TEXT,
            success_count INTEGER DEFAULT 0,
            last_error TEXT,
            last_status_code INTEGER,
            last_bytes INTEGER,
            last_method TEXT,
            last_attempt TEXT
        )
    """)
    # Idempotent attribution column
    try:
        con.execute("ALTER TABLE live_pulls ADD COLUMN last_triggered_by TEXT")
    except sqlite3.OperationalError:
        pass
    con.execute("CREATE INDEX IF NOT EXISTS idx_lp_last_success ON live_pulls(last_success)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_lp_triggered ON live_pulls(last_triggered_by)")
    return con


def record(domain: str, *, status_code: int, bytes_received: int = 0,
           method: str = "GET", error: str | None = None,
           triggered_by: str = "unknown") -> None:
    """Log a fetch attempt. status_code 200-399 counts as success."""
    if not domain:
        return
    domain = domain.strip().lower()
    now = datetime.now().isoformat()
    is_success = 200 <= status_code < 400
    con = _con()
    row = con.execute(
        "SELECT first_success, success_count FROM live_pulls WHERE domain=?", (domain,)
    ).fetchone()
    first = row[0] if row and row[0] else (now if is_success else None)
    cnt = (row[1] or 0) + (1 if is_success else 0) if row else (1 if is_success else 0)
    con.execute("""
        INSERT INTO live_pulls (domain, first_success, last_success, success_count,
                                last_error, last_status_code, last_bytes, last_method,
                                last_attempt, last_triggered_by)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(domain) DO UPDATE SET
            first_success = COALESCE(first_success, excluded.first_success),
            last_success = CASE WHEN excluded.last_status_code BETWEEN 200 AND 399
                                THEN excluded.last_success ELSE last_success END,
            success_count = success_count + CASE WHEN excluded.last_status_code BETWEEN 200 AND 399 THEN 1 ELSE 0 END,
            last_error = excluded.last_error,
            last_status_code = excluded.last_status_code,
            last_bytes = excluded.last_bytes,
            last_method = excluded.last_method,
            last_attempt = excluded.last_attempt,
            last_triggered_by = excluded.last_triggered_by
    """, (domain, first, now if is_success else None, cnt,
          error, status_code, bytes_received, method, now, triggered_by))
    con.commit()
    con.close()


def live_active_domains(window_days: int = 30) -> list[str]:
    """Domains successfully fetched within window_days."""
    cutoff = (datetime.now() - timedelta(days=window_days)).isoformat()
    con = _con()
    rows = con.execute(
        "SELECT domain FROM live_pulls WHERE last_success >= ? ORDER BY last_success DESC",
        (cutoff,)
    ).fetchall()
    con.close()
    return [r[0] for r in rows]


def stats(window_days: int = 30) -> dict:
    cutoff = (datetime.now() - timedelta(days=window_days)).isoformat()
    con = _con()
    total = con.execute("SELECT COUNT(*) FROM live_pulls").fetchone()[0]
    active = con.execute(
        "SELECT COUNT(*) FROM live_pulls WHERE last_success >= ?", (cutoff,)
    ).fetchone()[0]
    by_status = con.execute(
        "SELECT last_status_code, COUNT(*) FROM live_pulls GROUP BY last_status_code"
    ).fetchall()
    recent = con.execute(
        "SELECT domain, last_status_code, last_bytes, last_success FROM live_pulls "
        "WHERE last_success IS NOT NULL ORDER BY last_success DESC LIMIT 20"
    ).fetchall()
    con.close()
    return {
        "total_attempted": total,
        "live_active": active,
        "window_days": window_days,
        "by_status": dict(by_status),
        "recent_success": [
            {"domain": d, "status": s, "bytes": b, "at": ts}
            for d, s, b, ts in recent
        ],
    }


def all_records() -> list[dict]:
    con = _con()
    rows = con.execute("""
        SELECT domain, first_success, last_success, success_count,
               last_status_code, last_bytes, last_error
        FROM live_pulls
    """).fetchall()
    con.close()
    return [
        {"domain": d, "first_success": fs, "last_success": ls,
         "success_count": sc, "last_status_code": st,
         "last_bytes": b, "last_error": e}
        for d, fs, ls, sc, st, b, e in rows
    ]
