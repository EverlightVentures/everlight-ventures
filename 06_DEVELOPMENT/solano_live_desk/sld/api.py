from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from . import dvr, store, threat
from .geo_county import county_for

WEB_DIR = Path(__file__).resolve().parent.parent / "web"

# Alarm-queue ordering: most dangerous, then closest, first.
_LEVEL_RANK = {"EXTREME": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "LOG": 0}

app = FastAPI(title="Solano Live Desk")


def _store_dir() -> str:
    return os.environ.get("SLD_STORE", "store")


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/api/days")
def days():
    return {"days": store.list_days(_store_dir())}


@app.get("/api/events")
def events(date: str | None = None, lat: float | None = None, lon: float | None = None):
    """Events for a day, threat-scored against the caller's live GPS if given."""
    base = _store_dir()
    day = date or store.today_pt()
    if not store.day_db_path(base, day).exists():
        return {"date": day, "events": []}
    conn = store.connect(base, day)
    try:
        rows = store.get_events(conn)
    finally:
        conn.close()
    user = (lat, lon) if lat is not None and lon is not None else None
    scored = [threat.classify(r, user) for r in rows]
    scored.sort(
        key=lambda e: (
            _LEVEL_RANK.get(e["threat_level"], 0),
            -(e["distance_mi"] if e["distance_mi"] is not None else 9999),
        ),
        reverse=True,
    )
    return {"date": day, "user": user, "events": scored}


@app.get("/api/county")
def county(lat: float, lon: float):
    """Resolve the caller's GPS to a US county (the follow-me re-key trigger)."""
    try:
        return county_for(lat, lon)
    except Exception as e:  # noqa: BLE001
        return {"error": str(e), "fips": None, "county": None, "state": None}


@app.post("/api/location")
def set_location(lat: float, lon: float):
    """Phone posts its live GPS so server-side alerting scores against it."""
    p = Path(_store_dir())
    p.mkdir(parents=True, exist_ok=True)
    (p / "last_location.json").write_text(json.dumps({"lat": lat, "lon": lon}))
    return {"ok": True, "lat": lat, "lon": lon}


@app.get("/api/incidents")
def incidents(limit: int = 200):
    """The DVR / case log: cross-day recorded incidents, newest first."""
    conn = dvr.connect(_store_dir())
    try:
        return {"incidents": dvr.recent(conn, limit)}
    finally:
        conn.close()


# Serve the static web page at "/" (index.html). Mounted last so /api and
# /healthz win. Guard so the app imports even before web/ exists.
if WEB_DIR.exists():
    app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web")
