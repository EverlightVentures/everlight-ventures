"""Dispersed Egress: smart multi-route escape routing.

Ranks OSRM alternative routes to a safe destination by REAL free-flow time --
speed limits (via OSRM's own per-road-class duration) PLUS a time penalty for
every traffic light and stop sign on the route -- and drops any route that runs
through an incident-blocked road. The operator gets the genuinely clearest way
out, not just the obvious artery everyone else piles onto (the one-road jam that
kills people in real evacuations). Free public data only (OSRM + OpenStreetMap).

This is the single-user version. The coordinated version (assign DIFFERENT users
DIFFERENT routes to load-balance the whole evacuation) rides on the multi-user
data plane later; the scoring here is the shared core.
"""
from __future__ import annotations

from . import evac, routing
from .geo_county import bearing, distance_mi

_OVERPASS = "https://overpass-api.de/api/interpreter"

# Average delay each control adds. Rough absolute numbers; what matters is the
# RELATIVE cost, so a light-heavy artery loses to a clear back road. Tunable.
SIGNAL_PENALTY_S = 18
STOP_PENALTY_S = 7
NEAR_LINE_MI = 0.025    # a control counts as "on" the route within ~40 m of it
BLOCK_RADIUS_MI = 0.05  # a route "hits" a blocker within ~80 m of it
BLOCK_PENALTY_S = 3600  # blocked = last resort (still offered, ranked last)


def _line_latlon(geometry: dict) -> list[tuple[float, float]]:
    """OSRM geojson LineString ([lon,lat] pairs) -> [(lat, lon), ...]."""
    return [
        (c[1], c[0])
        for c in (geometry or {}).get("coordinates", [])
        if isinstance(c, list) and len(c) >= 2
    ]


def _near_line(pt: tuple[float, float], line: list[tuple[float, float]], within_mi: float) -> bool:
    """True if pt is within within_mi of any vertex of the polyline. OSRM
    overview=full is dense, so vertex proximity approximates the segment."""
    return any(distance_mi(pt, v) <= within_mi for v in line)


def _angle(a: float, b: float) -> float:
    """Smallest absolute difference between two compass bearings (0..180)."""
    d = abs(a - b) % 360
    return 360 - d if d > 180 else d


def score_route(geometry: dict, base_duration_s: float, controls, blockers) -> dict:
    """Adjusted travel time = OSRM duration + light/stop penalties + block penalty.
    controls: iterable of (lat, lon, kind) where kind in traffic_signals|stop.
    blockers: iterable of (lat, lon, label) incident/fire points to route around."""
    line = _line_latlon(geometry)
    signals = sum(1 for c in controls if c[2] == "traffic_signals" and _near_line((c[0], c[1]), line, NEAR_LINE_MI))
    stops = sum(1 for c in controls if c[2] == "stop" and _near_line((c[0], c[1]), line, NEAR_LINE_MI))
    hits = [b for b in blockers if _near_line((b[0], b[1]), line, BLOCK_RADIUS_MI)]
    adj = base_duration_s + signals * SIGNAL_PENALTY_S + stops * STOP_PENALTY_S + (BLOCK_PENALTY_S if hits else 0)
    return {
        "signals": signals,
        "stops": stops,
        "blocked": bool(hits),
        "avoids": [h[2] for h in hits][:3],
        "adj_s": round(adj),
    }


def _reason(s: dict, recommended: bool) -> str:
    lc = f"{s['signals']} light{'s' if s['signals'] != 1 else ''}"
    sc = f"{s['stops']} stop{'s' if s['stops'] != 1 else ''}"
    if s["blocked"]:
        lead, tail = "last resort", "crosses a blocked road"
    elif recommended:
        lead, tail = "clearest way out", f"{lc}, {sc}"
    else:
        lead, tail = "alternate", f"{lc}, {sc}"
    return f"{lead}: {tail}"


def _pick_dest(pts: list[dict], user: tuple[float, float], hazard: dict | None) -> dict | None:
    """Nearest safe point that is NOT toward the hazard (do not flee into the fire)."""
    if not pts:
        return None
    if hazard and hazard.get("lat") is not None:
        hb = bearing(user, (hazard["lat"], hazard["lon"]))
        away = [p for p in pts if _angle(bearing(user, (p["lat"], p["lon"])), hb) > 90]
        if away:
            return away[0]  # pts arrive sorted nearest-first
    return pts[0]


def _bbox(user: tuple[float, float], dest: dict, pad: float = 0.02):
    lats, lons = [user[0], dest["lat"]], [user[1], dest["lon"]]
    return (min(lats) - pad, min(lons) - pad, max(lats) + pad, max(lons) + pad)


def _fetch_controls(bbox) -> list[tuple]:
    """Traffic lights + stop signs inside the route bounding box (one Overpass call)."""
    import httpx

    s, w, n, e = bbox
    q = (
        f"[out:json][timeout:20];("
        f'node["highway"="traffic_signals"]({s},{w},{n},{e});'
        f'node["highway"="stop"]({s},{w},{n},{e});'
        f");out;"
    )
    r = httpx.post(_OVERPASS, data={"data": q}, headers={"User-Agent": "solano-live-desk/0.1"}, timeout=25)
    r.raise_for_status()
    out = []
    for el in r.json().get("elements", []):
        if el.get("lat") is not None:
            out.append((el["lat"], el["lon"], (el.get("tags", {}) or {}).get("highway")))
    return out


def _blockers(base: str) -> list[tuple]:
    """Incident / fire points to route around, as (lat, lon, label). Points only
    (evac-order polygons are handled by the destination pick, not per-edge here)."""
    out = []
    for f in routing.danger_features(base).get("features", []):
        g = f.get("geometry") or {}
        if g.get("type") == "Point":
            coords = g.get("coordinates") or [None, None]
            lon, lat = coords[0], coords[1]
            if lat is not None:
                out.append((lat, lon, (f.get("properties", {}) or {}).get("type") or "hazard"))
    return out


def plan_escape(
    lat: float,
    lon: float,
    base: str,
    hazard: dict | None = None,
    osrm_fn=None,
    controls_fn=None,
    blockers=None,
    safe_fn=None,
) -> dict:
    """Return {dest, routes[], headline}. routes are ranked clearest-first; each
    carries geometry, distance_mi, base_eta_min, eta_min (adjusted), signals,
    stops, blocked, recommended, reason. Every fetch is injectable for testing."""
    safe_fn = safe_fn or (lambda la, lo: evac.fetch_safe_points(la, lo, 12000))
    pts = safe_fn(lat, lon)
    if not pts:
        return {"error": "no safe destination nearby"}
    dest = _pick_dest(pts, (lat, lon), hazard)

    osrm_fn = osrm_fn or routing._osrm
    try:
        data = osrm_fn(lat, lon, dest["lat"], dest["lon"])
    except Exception as e:  # noqa: BLE001
        return {"error": f"routing unavailable: {e}", "dest": dest}
    routes = data.get("routes", [])
    if not routes:
        return {"error": "no route found", "dest": dest}

    controls_fn = controls_fn or _fetch_controls
    try:
        controls = controls_fn(_bbox((lat, lon), dest))
    except Exception:  # noqa: BLE001
        controls = []
    blk = blockers if blockers is not None else _blockers(base)

    scored: list[dict] = []
    for r in routes[:4]:
        s = score_route(r["geometry"], r.get("duration", 0), controls, blk)
        scored.append({
            "geometry": r["geometry"],
            "distance_mi": round(r.get("distance", 0) / 1609.34, 1),
            "base_eta_min": round(r.get("duration", 0) / 60),
            "eta_min": max(1, round(s["adj_s"] / 60)),
            **s,
        })
    scored.sort(key=lambda x: x["adj_s"])
    for i, x in enumerate(scored):
        x["recommended"] = i == 0
        x["reason"] = _reason(x, i == 0)

    best = scored[0]
    headline = (
        f"Head to {dest.get('name', 'safety')} ({dest.get('distance_mi', best['distance_mi'])} mi). "
        f"{best['reason'][0].upper()}{best['reason'][1:]}."
    )
    return {"dest": dest, "routes": scored, "headline": headline}
