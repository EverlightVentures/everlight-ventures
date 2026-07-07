from __future__ import annotations

import math

from .geo_county import bearing

_COMPASS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]


def _compass(deg: float) -> str:
    return _COMPASS[int((deg + 22.5) % 360 // 45)]


def describe(reverse: dict, landmarks: list[dict]) -> str:
    """Human location string, e.g. 'near Wells Fargo (~120m NE), on Texas St, Fairfield'."""
    addr = (reverse or {}).get("address", {}) or {}
    road = addr.get("road")
    city = addr.get("city") or addr.get("town") or addr.get("village") or addr.get("neighbourhood")
    parts: list[str] = []
    if landmarks:
        lm = landmarks[0]
        parts.append(f"near {lm['name']} (~{lm['dist_m']}m {lm['dir']})")
    if road:
        parts.append(f"on {road}")
    if city:
        parts.append(city)
    return ", ".join(parts) or "location unavailable"


def parse_landmarks(overpass: dict, lat: float, lon: float, limit: int = 3) -> list[dict]:
    """Named POIs near a point, distance + compass direction from the incident."""
    out: list[dict] = []
    for el in (overpass or {}).get("elements", []):
        tags = el.get("tags", {}) or {}
        name = tags.get("name")
        if not name:
            continue
        p = el.get("center") or {"lat": el.get("lat"), "lon": el.get("lon")}
        if p.get("lat") is None or p.get("lon") is None:
            continue
        dm = _haversine_m(lat, lon, p["lat"], p["lon"])
        out.append(
            {
                "name": name,
                "kind": tags.get("amenity") or tags.get("shop") or "place",
                "dist_m": int(dm),
                "dir": _compass(bearing((lat, lon), (p["lat"], p["lon"]))),
            }
        )
    out.sort(key=lambda x: x["dist_m"])
    return out[:limit]


def _haversine_m(lat1, lon1, lat2, lon2) -> float:
    r = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


_OVERPASS = "https://overpass-api.de/api/interpreter"


def _fetch_reverse(lat: float, lon: float) -> dict:
    import httpx

    r = httpx.get(
        "https://nominatim.openstreetmap.org/reverse",
        params={"format": "jsonv2", "lat": lat, "lon": lon, "zoom": 18, "addressdetails": 1},
        headers={"User-Agent": "solano-live-desk/0.1 (1m.rich.gee@gmail.com)"},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


def _fetch_landmarks(lat: float, lon: float) -> dict:
    import httpx

    q = (
        f"[out:json][timeout:20];("
        f'node["amenity"~"bank|hospital|school|police|fire_station|pharmacy|fuel|place_of_worship"](around:300,{lat},{lon});'
        f'node["shop"]["name"](around:200,{lat},{lon});'
        f'way["amenity"~"bank|hospital|school"](around:300,{lat},{lon});'
        f");out center 25;"
    )
    r = httpx.post(_OVERPASS, data={"data": q},
                   headers={"User-Agent": "solano-live-desk/0.1"}, timeout=25)
    r.raise_for_status()
    return r.json()


def where(lat: float, lon: float, reverse_fn=None, landmarks_fn=None) -> dict:
    """Assemble a wayfinding description for a point (graceful on any failure)."""
    reverse_fn = reverse_fn or _fetch_reverse
    landmarks_fn = landmarks_fn or _fetch_landmarks
    try:
        rev = reverse_fn(lat, lon)
    except Exception:  # noqa: BLE001
        rev = {}
    try:
        lms = parse_landmarks(landmarks_fn(lat, lon), lat, lon)
    except Exception:  # noqa: BLE001
        lms = []
    return {"text": describe(rev, lms), "landmarks": lms}
