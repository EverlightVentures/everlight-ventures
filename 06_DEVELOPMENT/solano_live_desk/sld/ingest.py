from __future__ import annotations

import asyncio
import os
from datetime import datetime

from . import store
from . import threat
from .chp_parser import parse_incidents
from .nws import fetch_alerts

CHP_URL = "http://media.chp.ca.gov/sa_xml/sa.xml"
# Default region for area-wide feeds (NWS) when the driver's live GPS is unknown.
DEFAULT_LAT = float(os.environ.get("SLD_LAT", "38.25"))
DEFAULT_LON = float(os.environ.get("SLD_LON", "-121.98"))


def scope() -> str:
    """Feed scope: 'corridor' (default, Solano + I-80/I-680 approaches) or 'county'."""
    return os.environ.get("SLD_SCOPE", "corridor")


def _store_all(events: list[dict], base, day: str, now_iso: str) -> int:
    conn = store.connect(base, day)
    try:
        for ev in events:
            ev["severity"] = threat.severity(
                " ".join(str(v) for v in (ev.get("type"), ev.get("title"), ev.get("body")) if v)
            )
            store.upsert_event(conn, ev, now_iso)
    finally:
        conn.close()
    return len(events)


def run_once(
    fetch_fn, base, day: str | None = None, now_iso: str | None = None,
    scope_name: str | None = None,
) -> int:
    """Fetch, parse, and upsert one CHP cycle. fetch_fn is injectable for tests."""
    day = day or store.today_pt()
    now_iso = now_iso or datetime.now(store.PT).isoformat()
    events = parse_incidents(fetch_fn(), scope=scope_name or scope())
    return _store_all(events, base, day, now_iso)


def run_once_nws(
    base, lat: float | None = None, lon: float | None = None,
    day: str | None = None, now_iso: str | None = None, fetch_fn=None,
) -> int:
    """Pull active NWS alerts near a point and upsert them as events."""
    day = day or store.today_pt()
    now_iso = now_iso or datetime.now(store.PT).isoformat()
    events = fetch_alerts(
        lat if lat is not None else DEFAULT_LAT,
        lon if lon is not None else DEFAULT_LON,
        fetch_fn=fetch_fn,
    )
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
        # NWS alerts change slowly; pull every ~5 minutes.
        if ticks % 5 == 0:
            try:
                nn = run_once_nws(base)
                print(f"[ingest] upserted {nn} NWS alerts", flush=True)
            except Exception as e:  # noqa: BLE001
                print(f"[ingest] nws error: {e}", flush=True)
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
