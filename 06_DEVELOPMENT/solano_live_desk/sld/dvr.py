from __future__ import annotations

import sqlite3
from pathlib import Path

DB_NAME = "secops.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS incidents (
    id TEXT PRIMARY KEY,
    source TEXT, type TEXT, title TEXT,
    lat REAL, lon REAL, geo_label TEXT,
    severity TEXT, threat_level TEXT, distance_mi REAL, ring TEXT,
    body TEXT, first_seen TEXT, last_seen TEXT,
    cleared INTEGER DEFAULT 0, notes TEXT
);
"""


def connect(base: str | Path) -> sqlite3.Connection:
    """The cross-day master security store (the DVR / case log)."""
    Path(base).mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(Path(base) / DB_NAME)
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    return conn


def record(conn: sqlite3.Connection, ev: dict, now_iso: str) -> bool:
    """Insert a new incident or refresh an existing one. Returns True if NEW."""
    row = conn.execute("SELECT id FROM incidents WHERE id=?", (ev["id"],)).fetchone()
    if row is None:
        conn.execute(
            "INSERT INTO incidents "
            "(id,source,type,title,lat,lon,geo_label,severity,threat_level,"
            "distance_mi,ring,body,first_seen,last_seen) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (ev["id"], ev.get("source"), ev.get("type"), ev.get("title"),
             ev.get("lat"), ev.get("lon"), ev.get("geo_label"), ev.get("severity"),
             ev.get("threat_level"), ev.get("distance_mi"), ev.get("ring"),
             ev.get("body"), now_iso, now_iso),
        )
        conn.commit()
        return True
    conn.execute(
        "UPDATE incidents SET last_seen=?, threat_level=?, distance_mi=?, ring=? WHERE id=?",
        (now_iso, ev.get("threat_level"), ev.get("distance_mi"), ev.get("ring"), ev["id"]),
    )
    conn.commit()
    return False


def recent(conn: sqlite3.Connection, limit: int = 200) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM incidents WHERE cleared=0 ORDER BY last_seen DESC LIMIT ?", (limit,)
    ).fetchall()
    return [dict(r) for r in rows]
