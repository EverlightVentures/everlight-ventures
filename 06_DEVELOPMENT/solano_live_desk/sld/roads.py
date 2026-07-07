from __future__ import annotations

import json
import os

URL = "https://api.511.org/traffic/events"

_SEV = {"SEVERE": "HIGH", "MAJOR": "HIGH", "MODERATE": "MEDIUM", "MINOR": "LOW", "UNKNOWN": "LOW"}


def _point(coords) -> tuple[float | None, float | None]:
    """First (lat, lon) from a GeoJSON Point [lon,lat] or nested LineString."""
    if not coords:
        return (None, None)
    c = coords
    while isinstance(c, list) and c and isinstance(c[0], list):
        c = c[0]
    if isinstance(c, list) and len(c) >= 2 and isinstance(c[0], (int, float)):
        return (c[1], c[0])
    return (None, None)


def parse(payload: dict) -> list[dict]:
    """Normalize 511 traffic events (incidents / closures / work zones)."""
    events = payload.get("events") if isinstance(payload, dict) else payload
    out: list[dict] = []
    for e in events or []:
        lat, lon = _point((e.get("geography") or {}).get("coordinates"))
        if lat is None:
            continue
        etype = e.get("event_type") or "Road event"
        subs = e.get("event_subtypes") or []
        sub = subs[0] if subs else ""
        head = e.get("headline") or ""
        roads = ", ".join(r.get("name", "") for r in (e.get("roads") or []))
        out.append(
            {
                "id": f"511road:{e.get('id')}",
                "source": "511road",
                "type": f"{etype}: {sub}" if sub else etype,
                "title": head,
                "lat": lat,
                "lon": lon,
                "geo_label": (roads or head)[:60],
                "log_time": e.get("updated"),
                "body": head,
                "details": [],
                "severity": _SEV.get((e.get("severity") or "").upper(), "LOW"),
            }
        )
    return out


def _fetch(key: str) -> dict:
    import httpx

    r = httpx.get(URL, params={"api_key": key, "format": "json"},
                  headers={"User-Agent": "solano-live-desk/0.1"}, timeout=20)
    r.raise_for_status()
    return json.loads(r.content.decode("utf-8-sig"))  # 511 responses carry a BOM


def fetch(key: str | None = None, fetch_fn=None) -> list[dict]:
    """511 Bay Area road incidents/closures. No token -> []."""
    key = key or os.environ.get("SLD_511_TOKEN")
    if not key:
        return []
    fetch_fn = fetch_fn or _fetch
    return parse(fetch_fn(key))
