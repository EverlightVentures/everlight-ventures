from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

PT = ZoneInfo("America/Los_Angeles")
DAY_FMT = "%Y_%m_%d"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    source TEXT, type TEXT, title TEXT,
    lat REAL, lon REAL, geo_label TEXT,
    first_seen TEXT, last_seen TEXT,
    body TEXT, entities TEXT, raw TEXT,
    severity TEXT, log_time TEXT
);
"""

# Columns added after the original schema shipped; added to old DBs on connect.
_MIGRATIONS = [("severity", "TEXT"), ("log_time", "TEXT")]


def today_pt() -> str:
    return datetime.now(PT).strftime(DAY_FMT)


def day_db_path(base: str | Path, day: str) -> Path:
    return Path(base) / f"events_{day}.db"


def connect(base: str | Path, day: str) -> sqlite3.Connection:
    Path(base).mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(day_db_path(base, day))
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    have = {r[1] for r in conn.execute("PRAGMA table_info(events)").fetchall()}
    for col, coltype in _MIGRATIONS:
        if col not in have:
            conn.execute(f"ALTER TABLE events ADD COLUMN {col} {coltype}")
    conn.commit()
    return conn


def upsert_event(conn: sqlite3.Connection, ev: dict, now_iso: str) -> None:
    row = conn.execute(
        "SELECT first_seen FROM events WHERE id=?", (ev["id"],)
    ).fetchone()
    entities = json.dumps(ev.get("entities") or {})
    raw = json.dumps(ev.get("details") or [])
    if row is None:
        conn.execute(
            "INSERT INTO events "
            "(id,source,type,title,lat,lon,geo_label,first_seen,last_seen,body,"
            "entities,raw,severity,log_time) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (ev["id"], ev.get("source"), ev.get("type"), ev.get("title"),
             ev.get("lat"), ev.get("lon"), ev.get("geo_label"),
             now_iso, now_iso, ev.get("body"), entities, raw,
             ev.get("severity"), ev.get("log_time")),
        )
    else:
        conn.execute(
            "UPDATE events SET last_seen=?, body=?, "
            "lat=COALESCE(?,lat), lon=COALESCE(?,lon), raw=?, "
            "severity=COALESCE(?,severity) WHERE id=?",
            (now_iso, ev.get("body"), ev.get("lat"), ev.get("lon"), raw,
             ev.get("severity"), ev["id"]),
        )
    conn.commit()


def get_events(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute("SELECT * FROM events ORDER BY last_seen").fetchall()
    return [dict(r) for r in rows]


def list_days(base: str | Path) -> list[str]:
    base = Path(base)
    if not base.exists():
        return []
    found = list(base.glob("events_*.db")) + list((base / "archive").glob("events_*.db"))
    days = {p.stem.replace("events_", "") for p in found}
    return sorted(days)
