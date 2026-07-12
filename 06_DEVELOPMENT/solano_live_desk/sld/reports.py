"""Community reports + gig-driver presence -- user-generated map markers.

Two kinds:
  * REPORTS  -- one-shot, time-decaying hazard reports (reckless driver on the
    shoulder, weaving, wrong-way, object on road). Warn other drivers, not the
    police. Reckless markers decay fast (drivers move); static hazards linger.
  * PRESENCE -- a gig driver marking themselves "on delivery" while they work, so
    anyone watching the map reads a vehicle idling on their street as a delivery,
    not a prowler. One row per driver, refreshed while active, auto-expires when
    they stop.

Stored in its own SQLite (store/reports.db), separate from the scanner/feed event
store so user data never mixes with dispatch data. Advisory, free-data only.
"""
from __future__ import annotations

import sqlite3
import time
import uuid
from pathlib import Path

# kind -> (label, severity, time-to-live seconds).
KINDS = {
    "reckless_shoulder":   ("Reckless: shoulder driving", "HIGH", 900),
    "reckless_weaving":    ("Reckless: weaving / swerving", "HIGH", 900),
    "reckless_wrongway":   ("Reckless: wrong-way driver", "CRITICAL", 900),
    "reckless_tailgating": ("Reckless: aggressive tailgating", "MEDIUM", 900),
    "reckless_racing":     ("Reckless: street racing", "HIGH", 900),
    "hazard_object":       ("Hazard: object on road", "MEDIUM", 3600),
    "hazard_pothole":      ("Hazard: pothole", "LOW", 86400),
    "hazard_flood":        ("Hazard: flooded road", "HIGH", 7200),
    "presence_delivery":   ("Delivery driver on shift", "LOG", 300),
}
_DEFAULT = ("Driver-reported hazard", "MEDIUM", 1800)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS reports (
    id TEXT PRIMARY KEY,
    kind TEXT, label TEXT, severity TEXT,
    lat REAL, lon REAL, detail TEXT, heading REAL,
    created REAL, expires REAL, client TEXT
);
"""


def _db(base: str | Path) -> sqlite3.Connection:
    Path(base).mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(Path(base) / "reports.db")
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    return conn


def add_report(base, kind, lat, lon, detail="", heading=None, now=None) -> dict:
    """One-shot hazard / reckless-driver report. Unknown kind -> generic hazard."""
    now = now if now is not None else time.time()
    label, sev, ttl = KINDS.get(kind, _DEFAULT)
    rid = f"report:{uuid.uuid4().hex[:12]}"
    conn = _db(base)
    try:
        conn.execute(
            "INSERT INTO reports (id,kind,label,severity,lat,lon,detail,heading,created,expires,client) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (rid, kind, label, sev, lat, lon, detail, heading, now, now + ttl, None),
        )
        conn.commit()
    finally:
        conn.close()
    return {"id": rid, "kind": kind, "label": label, "severity": sev, "expires": now + ttl}


def mark_presence(base, client, lat, lon, kind="presence_delivery", now=None) -> dict:
    """Upsert a gig driver's live 'on delivery' marker (one row per client, refreshed)."""
    now = now if now is not None else time.time()
    label, sev, ttl = KINDS.get(kind, KINDS["presence_delivery"])
    conn = _db(base)
    try:
        conn.execute("DELETE FROM reports WHERE client=? AND kind LIKE 'presence%'", (client,))
        conn.execute(
            "INSERT INTO reports (id,kind,label,severity,lat,lon,detail,heading,created,expires,client) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (f"presence:{client}", kind, label, sev, lat, lon, "", None, now, now + ttl, client),
        )
        conn.commit()
    finally:
        conn.close()
    return {"ok": True, "expires": now + ttl}


def clear_presence(base, client) -> dict:
    conn = _db(base)
    try:
        conn.execute("DELETE FROM reports WHERE client=? AND kind LIKE 'presence%'", (client,))
        conn.commit()
    finally:
        conn.close()
    return {"ok": True}


_SEV_ORDER = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]


def _escalate(sev: str, count: int) -> tuple[str, bool]:
    """Two or more reports of the same thing nearby = corroborated: bump severity
    and mark verified (the handoff doc's '2+ reports = verified' model)."""
    if count < 2 or sev not in _SEV_ORDER:
        return sev, count >= 2
    bump = 2 if count >= 3 else 1
    return _SEV_ORDER[min(len(_SEV_ORDER) - 1, _SEV_ORDER.index(sev) + bump)], True


def active(base, now=None) -> list[dict]:
    """Non-expired markers. Presences pass through one-per-driver; one-shot reports
    of the same kind within ~150 m collapse to a single marker whose count drives
    severity escalation + a 'verified' flag, so one incident is not five pins."""
    now = now if now is not None else time.time()
    conn = _db(base)
    try:
        conn.execute("DELETE FROM reports WHERE expires < ?", (now,))  # opportunistic cleanup
        conn.commit()
        rows = conn.execute("SELECT * FROM reports WHERE expires >= ? ORDER BY created", (now,)).fetchall()
    finally:
        conn.close()

    presences: list[dict] = []
    groups: dict[tuple, list[dict]] = {}
    for r in rows:
        d = dict(r)
        d["age_s"] = int(now - d["created"])
        d["ttl_s"] = int(d["expires"] - now)
        d["is_presence"] = str(d["kind"]).startswith("presence")
        if d["is_presence"]:
            d["count"], d["verified"] = 1, False
            presences.append(d)
        else:  # 3-decimal lat/lon grid ~= 150 m clustering per kind
            key = (d["kind"],
                   round(d["lat"], 3) if d["lat"] is not None else None,
                   round(d["lon"], 3) if d["lon"] is not None else None)
            groups.setdefault(key, []).append(d)

    out = list(presences)
    for g in groups.values():
        g.sort(key=lambda x: x["created"])
        marker = dict(g[-1])  # freshest position wins as the marker
        marker["count"] = len(g)
        marker["severity"], marker["verified"] = _escalate(marker["severity"], len(g))
        out.append(marker)
    return out
