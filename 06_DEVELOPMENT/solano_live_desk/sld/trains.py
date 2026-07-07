from __future__ import annotations

from .geo_county import distance_mi

AMTRAKER_URL = "https://api.amtraker.com/v3/trains"


def parse(payload: dict) -> list[dict]:
    """Normalize the Amtraker v3 national trains feed into train dicts.

    Shape is {trainNum: [train, ...]}. Freight is not present (not public).
    """
    out: list[dict] = []
    if not isinstance(payload, dict):
        return out
    for arr in payload.values():
        for t in arr or []:
            lat, lon = t.get("lat"), t.get("lon")
            if lat is None or lon is None:
                continue
            out.append(
                {
                    "id": t.get("trainID") or f"{t.get('trainNum')}",
                    "num": t.get("trainNum"),
                    "route": t.get("routeName"),
                    "lat": lat,
                    "lon": lon,
                    "heading": t.get("heading"),   # compass string e.g. "N", "SW"
                    "speed": t.get("velocity"),
                    "state": t.get("trainState"),
                }
            )
    return out


def near(trains: list[dict], lat: float, lon: float, radius_mi: float = 60) -> list[dict]:
    """Trains within radius_mi of a point, annotated + sorted by distance."""
    scored = [
        {**t, "distance_mi": round(distance_mi((lat, lon), (t["lat"], t["lon"])), 1)}
        for t in trains
    ]
    return sorted([t for t in scored if t["distance_mi"] <= radius_mi], key=lambda t: t["distance_mi"])


def _fetch() -> dict:
    import httpx

    r = httpx.get(AMTRAKER_URL, headers={"User-Agent": "solano-live-desk/0.1"}, timeout=20)
    r.raise_for_status()
    return r.json()


def fetch(fetch_fn=None) -> list[dict]:
    fetch_fn = fetch_fn or _fetch
    return parse(fetch_fn())
