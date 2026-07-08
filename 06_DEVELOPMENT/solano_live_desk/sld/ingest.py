from __future__ import annotations

import asyncio
import json
import math
import os
from datetime import datetime
from pathlib import Path

from . import config, store
from . import threat
from .chp_parser import DEFAULT_CENTER, parse_incidents
from .firms import fetch as fetch_firms
from .nws import fetch_alerts
from .quakes import fetch_quakes
from .roads import fetch as fetch_roads
from .geo_county import distance_mi

config.load_env()

CHP_URL = "http://media.chp.ca.gov/sa_xml/sa.xml"
# Bubble radius (miles) around the operator's live GPS. 45mi covers Solano +
# Napa/Yolo + eastern Contra Costa + the near East Bay, and drops SF, San Jose,
# Santa Rosa, Stockton, Sacramento -- less area = less CPU. Override SLD_RADIUS_MI.
RADIUS_MI = float(os.environ.get("SLD_RADIUS_MI", "45"))


def bubble_center(base: str) -> tuple[float, float]:
    """The live GPS the phone last posted, or the Fairfield default."""
    p = Path(base) / "last_location.json"
    if p.exists():
        try:
            d = json.loads(p.read_text())
            return (float(d["lat"]), float(d["lon"]))
        except Exception:  # noqa: BLE001
            pass
    return DEFAULT_CENTER


def _store_all(events: list[dict], base, day: str, now_iso: str) -> int:
    conn = store.connect(base, day)
    try:
        for ev in events:
            # Sources may pre-set severity (e.g. quakes by magnitude); else derive it.
            ev["severity"] = ev.get("severity") or threat.severity(
                " ".join(str(v) for v in (ev.get("type"), ev.get("title"), ev.get("body")) if v)
            )
            store.upsert_event(conn, ev, now_iso)
    finally:
        conn.close()
    return len(events)


def run_once(
    fetch_fn, base, day: str | None = None, now_iso: str | None = None,
    center: tuple[float, float] | None = None,
) -> int:
    """Fetch, parse, and upsert one CHP cycle for the current bubble."""
    day = day or store.today_pt()
    now_iso = now_iso or datetime.now(store.PT).isoformat()
    events = parse_incidents(fetch_fn(), center=center or bubble_center(base), radius_mi=RADIUS_MI)
    return _store_all(events, base, day, now_iso)


def run_once_nws(
    base, lat: float | None = None, lon: float | None = None,
    day: str | None = None, now_iso: str | None = None, fetch_fn=None,
) -> int:
    """Pull active NWS alerts near the bubble center and upsert them."""
    day = day or store.today_pt()
    now_iso = now_iso or datetime.now(store.PT).isoformat()
    c = (lat, lon) if lat is not None and lon is not None else bubble_center(base)
    events = fetch_alerts(c[0], c[1], fetch_fn=fetch_fn)
    return _store_all(events, base, day, now_iso)


def run_once_quakes(
    base, day: str | None = None, now_iso: str | None = None, fetch_fn=None,
) -> int:
    """Pull recent earthquakes within the bubble and upsert them."""
    day = day or store.today_pt()
    now_iso = now_iso or datetime.now(store.PT).isoformat()
    c = bubble_center(base)
    events = fetch_quakes(c[0], c[1], radius_km=RADIUS_MI * 1.60934, fetch_fn=fetch_fn)
    return _store_all(events, base, day, now_iso)


def _bbox(lat: float, lon: float, radius_mi: float) -> tuple[float, float, float, float]:
    dlat = radius_mi / 69.0
    dlon = radius_mi / (69.0 * max(0.1, math.cos(math.radians(lat))))
    return (lon - dlon, lat - dlat, lon + dlon, lat + dlat)  # w, s, e, n


def run_once_firms(
    base, day: str | None = None, now_iso: str | None = None, fetch_fn=None,
) -> int:
    """Pull satellite wildfire hotspots within the bubble and upsert them."""
    day = day or store.today_pt()
    now_iso = now_iso or datetime.now(store.PT).isoformat()
    c = bubble_center(base)
    w, s, e, n = _bbox(c[0], c[1], RADIUS_MI)
    events = fetch_firms(w, s, e, n, fetch_fn=fetch_fn)
    return _store_all(events, base, day, now_iso)


def run_once_roads(
    base, day: str | None = None, now_iso: str | None = None, fetch_fn=None,
) -> int:
    """Pull 511 road incidents/closures within the bubble and upsert them."""
    day = day or store.today_pt()
    now_iso = now_iso or datetime.now(store.PT).isoformat()
    c = bubble_center(base)
    events = [
        ev for ev in fetch_roads(fetch_fn=fetch_fn)
        if distance_mi(c, (ev["lat"], ev["lon"])) <= RADIUS_MI
    ]
    return _store_all(events, base, day, now_iso)


def fetch_chp(timeout: float = 20.0) -> str:
    """GET the CHP statewide XML with retries (old IIS host is flaky)."""
    import httpx

    headers = {"User-Agent": "solano-live-desk/0.1 (personal)"}
    last: Exception | None = None
    for _ in range(3):
        try:
            r = httpx.get(CHP_URL, headers=headers, timeout=timeout)
            r.raise_for_status()
            return r.text
        except Exception as e:  # noqa: BLE001 - retry any transport error
            last = e
    raise RuntimeError(f"CHP fetch failed after 3 tries: {last}")


async def poll_loop(base: str, interval: int = 60) -> None:
    ticks = 0
    while True:
        try:
            n = run_once(fetch_chp, base)
            print(f"[ingest] {store.today_pt()} upserted {n} CHP events", flush=True)
        except Exception as e:  # noqa: BLE001 - keep the loop alive
            print(f"[ingest] chp error: {e}", flush=True)
        # NWS alerts + earthquakes change slowly; pull every ~5 minutes.
        if ticks % 5 == 0:
            try:
                nn = run_once_nws(base)
                print(f"[ingest] upserted {nn} NWS alerts", flush=True)
            except Exception as e:  # noqa: BLE001
                print(f"[ingest] nws error: {e}", flush=True)
            try:
                nq = run_once_quakes(base)
                print(f"[ingest] upserted {nq} earthquakes", flush=True)
            except Exception as e:  # noqa: BLE001
                print(f"[ingest] quake error: {e}", flush=True)
            try:
                nf = run_once_firms(base)
                if nf:
                    print(f"[ingest] upserted {nf} wildfire hotspots", flush=True)
            except Exception as e:  # noqa: BLE001
                print(f"[ingest] firms error: {e}", flush=True)
            try:
                nr = run_once_roads(base)
                if nr:
                    print(f"[ingest] upserted {nr} road events", flush=True)
            except Exception as e:  # noqa: BLE001
                print(f"[ingest] roads error: {e}", flush=True)
        # Score today's events vs the phone's last-known GPS and fire alerts.
        try:
            from .alert_worker import run_alerts

            fired = run_alerts(base)
            if fired:
                print(f"[alert] fired {len(fired)}: "
                      + ", ".join(f"{f['threat_level']} {f['type']}" for f in fired), flush=True)
        except Exception as e:  # noqa: BLE001
            print(f"[alert] error: {e}", flush=True)
        # Camera DVR: snapshot the cameras nearest the operator into the ring
        # buffer so an incident can replay the 5-min-before/after window.
        try:
            from . import camera_dvr

            clat, clon = bubble_center(base)
            camera_dvr.snapshot_once(base, clat, clon)
            if ticks % 5 == 0:
                camera_dvr.rotate(base)
        except Exception as e:  # noqa: BLE001
            print(f"[camdvr] error: {e}", flush=True)
        # Social recon: fetch + geo-tag local safety chatter into hotspots ~10min.
        if ticks % 10 == 0:
            try:
                from . import social

                data = social.collect(base)
                if data.get("hotspots"):
                    print(f"[social] {len(data['posts'])} posts, hotspots: "
                          + ", ".join(f"{h['city']}({h['count']})" for h in data["hotspots"][:4]), flush=True)
            except Exception as e:  # noqa: BLE001
                print(f"[social] error: {e}", flush=True)
        ticks += 1
        await asyncio.sleep(interval)
