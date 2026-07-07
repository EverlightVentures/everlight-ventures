from __future__ import annotations

import math

FCC_URL = "https://geo.fcc.gov/api/census/block/find"


def distance_mi(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Great-circle miles between (lat, lon) points a and b (Haversine)."""
    r = 3958.7613
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(h)))


def bearing(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Initial compass bearing in degrees from a to b (0=N, 90=E)."""
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    dlon = lon2 - lon1
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


def parse_county(payload: dict) -> dict:
    """Normalize an FCC block/find response into {fips, county, state}."""
    c = payload.get("County") or {}
    s = payload.get("State") or {}
    return {
        "fips": c.get("FIPS"),
        "county": c.get("name"),
        "state": s.get("code") or s.get("name"),
    }


def _fetch_fcc(lat: float, lon: float) -> dict:
    import httpx

    r = httpx.get(
        FCC_URL,
        params={"latitude": lat, "longitude": lon, "format": "json"},
        headers={"User-Agent": "solano-live-desk/0.1 (personal)"},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


def county_for(lat: float, lon: float, fetch_fn=None) -> dict:
    """Resolve a GPS point to its US county. fetch_fn injectable for tests."""
    fetch_fn = fetch_fn or _fetch_fcc
    return parse_county(fetch_fn(lat, lon))
