"""Shelter-in-place vs Evacuate decision engine (ATAK-style 'so what / what do I
do' layer). Fuses already-classified incidents + active evacuation zones into ONE
clear recommendation. Free-data only; derived, advisory, never authoritative."""
from __future__ import annotations

import re

_AIRBORNE = re.compile(r"hazmat|gas leak|chemical|smoke|toxic|chlorine|ammonia|fumes|spill|hazardous material", re.I)
_FIRE = re.compile(r"\bfire\b|wildfire|brush fire|structure fire|vegetation fire|grass fire", re.I)
_VIOLENCE = re.compile(r"shots? fired|active shooter|shooting|gunman|barricad|pursuit|armed subject|hostage|11-?99", re.I)
_RING_RANK = {"IMMEDIATE": 0, "NEAR": 1, "AREA": 2, "REGIONAL": 3, "UNKNOWN": 4}


def _rings(geom: dict):
    """Coordinate rings from a Polygon / MultiPolygon geometry."""
    t, c = geom.get("type"), geom.get("coordinates") or []
    if t == "Polygon":
        return c
    if t == "MultiPolygon":
        return [ring for poly in c for ring in poly]
    return []


def _point_in_ring(x: float, y: float, ring) -> bool:
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi):
            inside = not inside
        j = i
    return inside


def enrich_zones(geojson: dict, lat: float, lon: float) -> list[dict]:
    """Attach distance_mi + inside to each active evac zone, relative to the operator."""
    from .geo_county import distance_mi

    out = []
    for f in (geojson or {}).get("features", []):
        p = f.get("properties", {}) or {}
        mind, inside = 9999.0, False
        for ring in _rings(f.get("geometry") or {}):
            if _point_in_ring(lon, lat, ring):
                inside = True
            for pt in ring:
                if len(pt) >= 2:
                    d = distance_mi((lat, lon), (pt[1], pt[0]))
                    if d < mind:
                        mind = d
        out.append({"status": p.get("STATUS"), "name": p.get("ZONE_NAME"),
                    "distance_mi": round(mind, 1) if mind < 9999 else None, "inside": inside})
    return out


def decide(incidents: list[dict], evac_zones: list[dict], has_gps: bool = True) -> dict:
    """Return {action, reason, hazard, confidence, factors}.
    action: EVACUATE (red GO) | SHELTER (blue STAY) | CLEAR (green)."""
    if not has_gps:
        return {"action": "CLEAR", "reason": "no GPS fix yet", "hazard": None, "confidence": 0.0, "factors": []}

    # 1) Active EVACUATION ORDER you are inside or within 3 mi -> leave.
    for z in evac_zones or []:
        st = (z.get("status") or "").lower()
        if "order" in st or "mandatory" in st:
            d = z.get("distance_mi")
            if z.get("inside") or (d is not None and d <= 3):
                where = "you are inside it" if z.get("inside") else f"{d} mi away"
                return {"action": "EVACUATE", "reason": f"evacuation ORDER, {where}",
                        "hazard": z.get("name") or "evacuation order", "confidence": 0.9,
                        "factors": [f"EVAC ORDER: {z.get('name', 'zone')} ({where})"]}

    # 2) Nearest hazardous incidents by ring + type.
    fire = airborne = violence = None
    for e in incidents:
        if (e.get("type") or "").startswith("Scanner log"):  # block-log dumps match everything
            continue
        rank = _RING_RANK.get(e.get("ring") or "UNKNOWN", 4)
        text = f"{e.get('type', '')} {e.get('body', '')}"
        if rank <= 1:  # IMMEDIATE or NEAR
            if not fire and _FIRE.search(text):
                fire = e
            if not airborne and _AIRBORNE.search(text):
                airborne = e
        if rank == 0 and not violence and _VIOLENCE.search(text):
            violence = e

    if fire:
        d = fire.get("distance_mi")
        return {"action": "EVACUATE", "reason": f"fire {d} mi away in your {(fire.get('ring') or '').lower()} ring, leave early",
                "hazard": fire.get("type"), "confidence": 0.75,
                "factors": [f"FIRE: {fire.get('type')} ({d} mi, {fire.get('ring')})"]}
    if airborne:
        d = airborne.get("distance_mi")
        return {"action": "SHELTER", "reason": f"airborne hazard {d} mi away, close windows and stay inside",
                "hazard": airborne.get("type"), "confidence": 0.7,
                "factors": [f"AIRBORNE: {airborne.get('type')} ({d} mi)"]}
    if violence:
        d = violence.get("distance_mi")
        return {"action": "SHELTER", "reason": f"active violence {d} mi away, lock down and stay off the street",
                "hazard": violence.get("type"), "confidence": 0.75,
                "factors": [f"VIOLENCE: {violence.get('type')} ({d} mi)"]}

    return {"action": "CLEAR", "reason": "no immediate threat in your rings", "hazard": None, "confidence": 0.6, "factors": []}
