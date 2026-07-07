from __future__ import annotations

import asyncio
from datetime import datetime

from . import store
from .chp_parser import parse_incidents

CHP_URL = "http://media.chp.ca.gov/sa_xml/sa.xml"


def run_once(fetch_fn, base, day: str | None = None, now_iso: str | None = None) -> int:
    """Fetch, parse, and upsert one cycle. fetch_fn is injectable for tests."""
    day = day or store.today_pt()
    now_iso = now_iso or datetime.now(store.PT).isoformat()
    events = parse_incidents(fetch_fn())
    conn = store.connect(base, day)
    try:
        for ev in events:
            store.upsert_event(conn, ev, now_iso)
    finally:
        conn.close()
    return len(events)


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
    while True:
        try:
            n = run_once(fetch_chp, base)
            print(f"[ingest] {store.today_pt()} upserted {n} Solano events", flush=True)
        except Exception as e:  # noqa: BLE001 - keep the loop alive
            print(f"[ingest] error: {e}", flush=True)
        await asyncio.sleep(interval)
