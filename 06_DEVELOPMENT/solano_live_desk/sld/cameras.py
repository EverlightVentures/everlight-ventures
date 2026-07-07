from __future__ import annotations

from .geo_county import distance_mi

D4_URL = "https://cwwp2.dot.ca.gov/data/d4/cctv/cctvStatusD04.json"


def _first(*vals):
    for v in vals:
        if v:
            return v
    return None


def parse_cameras(payload: dict) -> list[dict]:
    """Normalize the Caltrans D4 CCTV status JSON into camera dicts.

    Tolerant to the two shapes the feed has used: image URLs either directly
    on imageData or nested under imageData.static / imageData.streamingVideo.
    """
    out: list[dict] = []
    for item in payload.get("data", []):
        c = item.get("cctv", item) or {}
        loc = c.get("location", {}) or {}
        img = c.get("imageData", {}) or {}
        try:
            lat = float(loc.get("latitude"))
            lon = float(loc.get("longitude"))
        except (TypeError, ValueError):
            continue
        if lat == 0 and lon == 0:
            continue
        static = img.get("static", {}) or {}
        stream = img.get("streamingVideo", {}) or {}
        out.append(
            {
                "id": str(c.get("index") or loc.get("locationName") or f"{lat},{lon}"),
                "name": _first(loc.get("locationName"), loc.get("nearbyPlace"), "camera"),
                "lat": lat,
                "lon": lon,
                "route": loc.get("route"),
                "county": loc.get("county"),
                "direction": loc.get("direction"),
                "image_url": _first(img.get("currentImageURL"), static.get("currentImageURL")),
                "stream_url": _first(img.get("streamingVideoURL"), stream.get("streamingVideoURL")),
            }
        )
    return out


def nearest(cams: list[dict], lat: float, lon: float, n: int = 3) -> list[dict]:
    """The n cameras closest to a point, each annotated with distance_mi."""
    scored = [{**c, "distance_mi": round(distance_mi((lat, lon), (c["lat"], c["lon"])), 2)} for c in cams]
    scored.sort(key=lambda c: c["distance_mi"])
    return scored[:n]


def _fetch_d4() -> dict:
    import httpx

    r = httpx.get(D4_URL, headers={"User-Agent": "solano-live-desk/0.1"}, timeout=20)
    r.raise_for_status()
    return r.json()


def fetch_cameras(fetch_fn=None) -> list[dict]:
    fetch_fn = fetch_fn or _fetch_d4
    return parse_cameras(fetch_fn())
