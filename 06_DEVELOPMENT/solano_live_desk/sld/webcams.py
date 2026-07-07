from __future__ import annotations

import os

# Windy Webcams API v3 (free key). The legal "look around" public-webcam layer.
WINDY_URL = "https://api.windy.com/webcams/api/v3/webcams"


def parse(payload: dict) -> list[dict]:
    """Normalize a Windy webcams response into webcam dicts with preview images."""
    out: list[dict] = []
    for w in payload.get("webcams", []):
        loc = w.get("location", {}) or {}
        cur = (w.get("images", {}) or {}).get("current", {}) or {}
        lat, lon = loc.get("latitude"), loc.get("longitude")
        if lat is None or lon is None:
            continue
        out.append(
            {
                "id": str(w.get("webcamId") or w.get("id") or f"{lat},{lon}"),
                "name": w.get("title") or "webcam",
                "lat": lat,
                "lon": lon,
                "image": cur.get("preview") or cur.get("thumbnail") or cur.get("icon"),
                "status": w.get("status"),
            }
        )
    return out


def _fetch(lat: float, lon: float, radius_km: int, key: str) -> dict:
    import httpx

    r = httpx.get(
        WINDY_URL,
        params={"nearby": f"{lat},{lon},{radius_km}", "include": "images,location", "limit": 30},
        headers={"x-windy-api-key": key},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


def fetch_near(
    lat: float, lon: float, radius_km: int = 50, key: str | None = None, fetch_fn=None,
) -> list[dict]:
    """Public webcams near a point. No key -> []."""
    key = key or os.environ.get("SLD_WINDY_KEY")
    if not key:
        return []
    fetch_fn = fetch_fn or _fetch
    return parse(fetch_fn(lat, lon, radius_km, key))
