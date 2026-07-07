from __future__ import annotations

from .geo_county import distance_mi

# CA Evacuation Aggregation Layer (Cal OES). This is a "view" that only holds
# zones currently under an active order/warning; it is empty in blue-sky.
EVAC_URL = (
    "https://services.arcgis.com/BLN4oKB0N1YSgvY8/arcgis/rest/services/"
    "CA_EVACUATIONS_CalOESHosted_view/FeatureServer/0/query"
)
_OVERPASS = "https://overpass-api.de/api/interpreter"

# STATUS string -> map color (order = flee now, warning = get ready).
STATUS_COLORS = {
    "Evacuation Order": "#ff2d2d",
    "Evacuation Warning": "#ff8c1a",
    "Shelter in Place": "#7fd1ff",
    "Advisory": "#ffd21a",
}


def summarize(geojson: dict) -> list[dict]:
    """Flatten active-evac GeoJSON to a list (for alerts + a zone list view)."""
    out: list[dict] = []
    for f in geojson.get("features", []):
        p = f.get("properties", {}) or {}
        out.append(
            {
                "zone_id": p.get("ZONE_ID"),
                "name": p.get("ZONE_NAME"),
                "status": p.get("STATUS"),
                "county": p.get("COUNTY"),
                "event": p.get("EVENT_TYPE"),
                "info": p.get("CRITICAL_INFO"),
            }
        )
    return out


def _fetch_evac() -> dict:
    import httpx

    r = httpx.get(
        EVAC_URL,
        params={
            "where": "1=1",
            "outFields": "STATUS,ZONE_NAME,ZONE_ID,COUNTY,EVENT_TYPE,CRITICAL_INFO",
            "f": "geojson",
        },
        headers={"User-Agent": "solano-live-desk/0.1"},
        timeout=25,
    )
    r.raise_for_status()
    return r.json()


def fetch_active_zones(fetch_fn=None) -> dict:
    """GeoJSON FeatureCollection of active CA evacuation zones (empty if none)."""
    fetch_fn = fetch_fn or _fetch_evac
    gj = fetch_fn()
    if "features" not in gj:
        gj = {"type": "FeatureCollection", "features": []}
    return gj


def parse_safe_points(overpass: dict, lat: float, lon: float, limit: int = 12) -> list[dict]:
    """Nearest shelters / hospitals / police / fire stations to a point."""
    out: list[dict] = []
    for el in (overpass or {}).get("elements", []):
        tags = el.get("tags", {}) or {}
        p = el.get("center") or {"lat": el.get("lat"), "lon": el.get("lon")}
        if p.get("lat") is None or p.get("lon") is None:
            continue
        kind = tags.get("amenity") or tags.get("emergency") or "safe"
        out.append(
            {
                "name": tags.get("name") or kind.replace("_", " ").title(),
                "kind": kind,
                "lat": p["lat"],
                "lon": p["lon"],
                "distance_mi": round(distance_mi((lat, lon), (p["lat"], p["lon"])), 1),
            }
        )
    out.sort(key=lambda x: x["distance_mi"])
    return out[:limit]


def _fetch_safe(lat: float, lon: float, radius_m: int) -> dict:
    import httpx

    q = (
        f"[out:json][timeout:20];("
        f'node["amenity"~"hospital|police|fire_station|shelter"](around:{radius_m},{lat},{lon});'
        f'node["emergency"="assembly_point"](around:{radius_m},{lat},{lon});'
        f'way["amenity"~"hospital|police|fire_station|shelter"](around:{radius_m},{lat},{lon});'
        f");out center 40;"
    )
    r = httpx.post(_OVERPASS, data={"data": q},
                   headers={"User-Agent": "solano-live-desk/0.1"}, timeout=25)
    r.raise_for_status()
    return r.json()


def fetch_safe_points(lat: float, lon: float, radius_m: int = 8000, fetch_fn=None) -> list[dict]:
    """Nearby safe destinations (hospitals, police, fire, shelters)."""
    fetch_fn = fetch_fn or _fetch_safe
    try:
        return parse_safe_points(fetch_fn(lat, lon, radius_m), lat, lon)
    except Exception:  # noqa: BLE001
        return []
