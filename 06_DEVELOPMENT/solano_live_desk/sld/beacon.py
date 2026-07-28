"""EPIRB-style distress beacon.

NOT a certified 406 MHz EPIRB: it cannot reach Coast Guard / SARSAT. It is the
free software analog. When activated it broadcasts the operator's position + SOS
on every channel we have (ntfy push now; Meshtastic mesh for off-grid), REPEATS on
a timer until cancelled or rescued (a real EPIRB keeps transmitting on its own),
and stays readable so anyone watching sees an active distress. For open water or
true wilderness, carry a real EPIRB or PLB.

One active beacon per client, stored in its own SQLite (store/beacon.db).
"""
from __future__ import annotations

import sqlite3
import time
from pathlib import Path

REPEAT_S = 300  # re-broadcast every 5 min while active, like an EPIRB pulse

_SCHEMA = """
CREATE TABLE IF NOT EXISTS beacons (
    client TEXT PRIMARY KEY,
    lat REAL, lon REAL, note TEXT,
    activated REAL, last_bcast REAL
);
"""


def _db(base: str | Path) -> sqlite3.Connection:
    Path(base).mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(Path(base) / "beacon.db")
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    return conn


def _row(r: sqlite3.Row, now: float) -> dict:
    d = dict(r)
    d["elapsed_s"] = int(now - d["activated"])
    d["active"] = True
    return d


def activate(base, client, lat, lon, note="", now=None) -> dict:
    """Start (or refresh the position of) a distress beacon for one client."""
    now = now if now is not None else time.time()
    conn = _db(base)
    try:
        existing = conn.execute("SELECT activated FROM beacons WHERE client=?", (client,)).fetchone()
        activated = existing["activated"] if existing else now  # keep original start time on refresh
        conn.execute("DELETE FROM beacons WHERE client=?", (client,))
        conn.execute(
            "INSERT INTO beacons (client,lat,lon,note,activated,last_bcast) VALUES (?,?,?,?,?,?)",
            (client, lat, lon, note, activated, 0.0),  # last_bcast=0 -> due immediately
        )
        conn.commit()
    finally:
        conn.close()
    return get(base, client, now)


def cancel(base, client) -> dict:
    conn = _db(base)
    try:
        conn.execute("DELETE FROM beacons WHERE client=?", (client,))
        conn.commit()
    finally:
        conn.close()
    return {"active": False}


def get(base, client=None, now=None):
    """One client's beacon (dict, {active:False} if none) or the list of all active."""
    now = now if now is not None else time.time()
    conn = _db(base)
    try:
        if client is not None:
            r = conn.execute("SELECT * FROM beacons WHERE client=?", (client,)).fetchone()
            return _row(r, now) if r else {"active": False}
        rows = conn.execute("SELECT * FROM beacons ORDER BY activated").fetchall()
    finally:
        conn.close()
    return [_row(r, now) for r in rows]


def due_for_broadcast(base, now=None) -> list[dict]:
    """Active beacons whose repeat interval has elapsed (for the server repeater)."""
    now = now if now is not None else time.time()
    conn = _db(base)
    try:
        rows = conn.execute("SELECT * FROM beacons WHERE ? - last_bcast >= ?", (now, REPEAT_S)).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


def mark_broadcast(base, client, now=None) -> None:
    now = now if now is not None else time.time()
    conn = _db(base)
    try:
        conn.execute("UPDATE beacons SET last_bcast=? WHERE client=?", (now, client))
        conn.commit()
    finally:
        conn.close()
