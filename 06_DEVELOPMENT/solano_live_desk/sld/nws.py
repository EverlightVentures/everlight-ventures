from __future__ import annotations

NWS_URL = "https://api.weather.gov/alerts/active"


def _flatten_coords(coords) -> list:
    pts: list = []

    def rec(x):
        if isinstance(x, (list, tuple)):
            if len(x) == 2 and all(isinstance(v, (int, float)) for v in x):
                pts.append(x)
            else:
                for y in x:
                    rec(y)

    rec(coords)
    return pts


def parse_alerts(payload: dict) -> list[dict]:
    """Normalize an NWS active-alerts GeoJSON payload into event dicts."""
    out: list[dict] = []
    for f in payload.get("features", []):
        p = f.get("properties", {})
        lat = lon = None
        pts = _flatten_coords((f.get("geometry") or {}).get("coordinates"))
        if pts:
            lon = sum(c[0] for c in pts) / len(pts)
            lat = sum(c[1] for c in pts) / len(pts)
        aid = p.get("id") or p.get("@id") or p.get("headline") or ""
        out.append(
            {
                "id": f"nws:{aid}",
                "source": "nws",
                "type": p.get("event"),
                "title": p.get("headline") or p.get("event"),
                "lat": lat,
                "lon": lon,
                "geo_label": p.get("areaDesc"),
                "log_time": p.get("effective"),
                "area": "",
                "body": (p.get("description") or "")[:1000],
                "details": [],
            }
        )
    return out


def _fetch_nws(lat: float, lon: float) -> dict:
    import httpx

    r = httpx.get(
        NWS_URL,
        params={"point": f"{lat},{lon}"},
        headers={
            "User-Agent": "solano-live-desk/0.1 (personal safety)",
            "Accept": "application/geo+json",
        },
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


def fetch_alerts(lat: float, lon: float, fetch_fn=None) -> list[dict]:
    """Active NWS alerts near a point. fetch_fn injectable for tests."""
    fetch_fn = fetch_fn or _fetch_nws
    return parse_alerts(fetch_fn(lat, lon))
