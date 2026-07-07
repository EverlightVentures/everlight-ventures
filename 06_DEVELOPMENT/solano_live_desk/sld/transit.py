from __future__ import annotations

import os

from .geo_county import distance_mi

# 511 Bay Area GTFS-Realtime vehicle positions (free token). agency=RG is the
# consolidated 9-county regional feed (one call covers the whole bubble).
URL = "https://api.511.org/transit/vehiclepositions"


def parse(pb_bytes: bytes) -> list[dict]:
    """Parse a GTFS-Realtime protobuf feed into vehicle (bus/rail) dicts."""
    from google.transit import gtfs_realtime_pb2

    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(pb_bytes)
    out: list[dict] = []
    for ent in feed.entity:
        if not ent.HasField("vehicle"):
            continue
        v = ent.vehicle
        pos = v.position
        if not pos.latitude or not pos.longitude:
            continue
        out.append(
            {
                "id": (v.vehicle.id or ent.id),
                "route": v.trip.route_id or "",
                "lat": pos.latitude,
                "lon": pos.longitude,
                "bearing": pos.bearing or 0,
                "speed": pos.speed or 0,
                "label": v.vehicle.label or "",
            }
        )
    return out


def near(vehicles: list[dict], lat: float, lon: float, radius_mi: float = 30) -> list[dict]:
    scored = [
        {**t, "distance_mi": round(distance_mi((lat, lon), (t["lat"], t["lon"])), 1)}
        for t in vehicles
    ]
    return sorted([t for t in scored if t["distance_mi"] <= radius_mi], key=lambda t: t["distance_mi"])


def _fetch(agency: str, key: str) -> bytes:
    import httpx

    r = httpx.get(URL, params={"api_key": key, "agency": agency},
                  headers={"User-Agent": "solano-live-desk/0.1"}, timeout=15)
    r.raise_for_status()
    return r.content


def fetch(agency: str = "RG", key: str | None = None, fetch_fn=None) -> list[dict]:
    """Live transit vehicle positions. No token -> []."""
    key = key or os.environ.get("SLD_511_TOKEN")
    if not key:
        return []
    fetch_fn = fetch_fn or _fetch
    return parse(fetch_fn(agency, key))
