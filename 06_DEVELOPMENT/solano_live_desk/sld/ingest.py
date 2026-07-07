from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path

from . import store
from . import threat
from .chp_parser import DEFAULT_CENTER, parse_incidents
from .nws import fetch_alerts
from .quakes import fetch_quakes

CHP_URL = "http://media.chp.ca.gov/sa_xml/sa.xml"
# Bubble radius (miles) around the center. Default 75mi = whole Bay Area +
# Napa + toward Sacramento. Override with SLD_RADIUS_MI as you like.
RADIUS_MI = float(os.environ.get("SLD_RADIUS_MI", "75"))


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
        # Score today's events vs the phone's last-known GPS and fire alerts.
        try:
            from .alert_worker import run_alerts

            fired = run_alerts(base)
            if fired:
                print(f"[alert] fired {len(fired)}: "
                      + ", ".join(f"{f['threat_level']} {f['type']}" for f in fired), flush=True)
        except Exception as e:  # noqa: BLE001
            print(f"[alert] error: {e}", flush=True)
        ticks += 1
        await asyncio.sleep(interval)
