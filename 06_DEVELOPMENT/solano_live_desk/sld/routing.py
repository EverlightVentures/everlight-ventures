from __future__ import annotations

from . import evac, store

# Free public OSRM (driving). No avoid-polygon (that needs self-hosted Valhalla,
# staged separately); we overlay the danger set so the operator can see hazards.
OSRM = "https://router.project-osrm.org/route/v1/driving/{coords}"


def danger_features(base: str) -> dict:
    """One GeoJSON of everything to avoid: active evac ORDER zones + fire hotspots
    + CRITICAL/HIGH incidents. Shared by the map overlay (and future avoid-routing)."""
    feats: list[dict] = []
    try:
        for f in evac.fetch_active_zones().get("features", []):
            status = ((f.get("properties", {}) or {}).get("STATUS", "") or "").upper()
            if "ORDER" in status:
                feats.append(f)
    except Exception:  # noqa: BLE001
        pass
    try:
        conn = store.connect(base, store.today_pt())
        try:
            rows = store.get_events(conn)
        finally:
            conn.close()
    except Exception:  # noqa: BLE001
        rows = []
    for r in rows:
        if r.get("lat") is None:
            continue
        if r.get("source") == "firms" or r.get("severity") in ("CRITICAL", "HIGH"):
            feats.append({
                "type": "Feature",
                "properties": {"type": r.get("type"), "src": r.get("source")},
                "geometry": {"type": "Point", "coordinates": [r["lon"], r["lat"]]},
            })
    return {"type": "FeatureCollection", "features": feats}


def _osrm(lat, lon, dlat, dlon) -> dict:
    import httpx

    r = httpx.get(
        OSRM.format(coords=f"{lon},{lat};{dlon},{dlat}"),
        params={"overview": "full", "geometries": "geojson", "alternatives": "true"},
        headers={"User-Agent": "solano-live-desk/0.1"},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


def route_to_safety(lat: float, lon: float, fetch_fn=None) -> dict:
    """Route to the nearest safe destination (hospital/police/fire/shelter)."""
    pts = evac.fetch_safe_points(lat, lon, 12000)
    if not pts:
        return {"error": "no safe destination nearby"}
    dest = pts[0]
    fetch_fn = fetch_fn or _osrm
    try:
        d = fetch_fn(lat, lon, dest["lat"], dest["lon"])
    except Exception as e:  # noqa: BLE001
        return {"error": f"routing unavailable: {e}", "dest": dest}
    routes = d.get("routes", [])
    if not routes:
        return {"error": "no route found", "dest": dest}
    r0 = routes[0]
    return {
        "dest": dest,
        "route": r0["geometry"],
        "distance_mi": round(r0["distance"] / 1609.34, 1),
        "eta_min": round(r0["duration"] / 60),
        "alternates": [x["geometry"] for x in routes[1:3]],
    }
