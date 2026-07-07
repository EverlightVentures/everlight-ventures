from __future__ import annotations

USGS_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"


def _severity_for(mag) -> str:
    try:
        m = float(mag)
    except (TypeError, ValueError):
        return "LOW"
    if m >= 5.0:
        return "CRITICAL"
    if m >= 4.0:
        return "HIGH"
    if m >= 3.0:
        return "MEDIUM"
    return "LOW"


def parse(payload: dict) -> list[dict]:
    """Normalize a USGS FDSN GeoJSON response into earthquake event dicts."""
    out: list[dict] = []
    for f in payload.get("features", []):
        p = f.get("properties", {}) or {}
        coords = (f.get("geometry", {}) or {}).get("coordinates") or [None, None]
        mag = p.get("mag")
        out.append(
            {
                "id": f"usgs:{f.get('id')}",
                "source": "usgs",
                "type": f"Earthquake M{mag}" if mag is not None else "Earthquake",
                "title": p.get("title"),
                "lat": coords[1],
                "lon": coords[0],
                "geo_label": p.get("place"),
                "log_time": p.get("time"),
                "body": f"{p.get('place') or ''}\nMagnitude {mag}",
                "details": [],
                "severity": _severity_for(mag),
                "mag": mag,
            }
        )
    return out


def _fetch(lat: float, lon: float, radius_km: float, min_mag: float, hours: int) -> dict:
    import httpx

    r = httpx.get(
        USGS_URL,
        params={
            "format": "geojson",
            "latitude": lat,
            "longitude": lon,
            "maxradiuskm": round(radius_km, 1),
            "minmagnitude": min_mag,
            "orderby": "time",
            "limit": 50,
        },
        headers={"User-Agent": "solano-live-desk/0.1"},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


def fetch_quakes(
    lat: float, lon: float, radius_km: float = 120.0,
    min_mag: float = 2.5, hours: int = 24, fetch_fn=None,
) -> list[dict]:
    """Recent earthquakes within radius_km of a point (magnitude >= min_mag)."""
    fetch_fn = fetch_fn or (lambda la, lo, r=radius_km, mm=min_mag, h=hours: _fetch(la, lo, r, mm, h))
    return parse(fetch_fn(lat, lon))
