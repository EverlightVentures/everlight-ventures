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


def _bearing(user, e) -> str | None:
    """Compass direction (N/NE/.../NW) from the operator to a hazard."""
    import math

    if not user or e.get("lat") is None or e.get("lon") is None:
        return None
    lat1, lon1 = math.radians(user[0]), math.radians(user[1])
    lat2, lon2 = math.radians(e["lat"]), math.radians(e["lon"])
    dl = lon2 - lon1
    y = math.sin(dl) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dl)
    deg = (math.degrees(math.atan2(y, x)) + 360) % 360
    return ["N", "NE", "E", "SE", "S", "SW", "W", "NW"][round(deg / 45) % 8]


def decide(incidents: list[dict], evac_zones: list[dict], user=None) -> dict:
    """Return {action, reason, hazard, hazard_lat/lon/dist/bearing, confidence, factors}.
    action: EVACUATE (red GO) | SHELTER (blue STAY) | CLEAR (green). user = (lat, lon)."""
    if not user:
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

    def _haz(e: dict) -> dict:  # so the console can fly to + highlight the exact hazard
        return {"hazard_id": e.get("id"), "hazard_lat": e.get("lat"), "hazard_lon": e.get("lon"),
                "hazard_dist": e.get("distance_mi"), "hazard_bearing": _bearing(user, e)}

    if fire:
        d, b = fire.get("distance_mi"), _bearing(user, fire)
        return {"action": "EVACUATE", "reason": f"fire {d} mi to your {b}, head the other way",
                "hazard": fire.get("type"), "confidence": 0.75, **_haz(fire),
                "factors": [f"FIRE: {fire.get('type')} ({d} mi {b}, {fire.get('ring')})"]}
    if airborne:
        d, b = airborne.get("distance_mi"), _bearing(user, airborne)
        return {"action": "SHELTER", "reason": f"airborne hazard {d} mi to your {b}, close windows and stay inside",
                "hazard": airborne.get("type"), "confidence": 0.7, **_haz(airborne),
                "factors": [f"AIRBORNE: {airborne.get('type')} ({d} mi {b})"]}
    if violence:
        d, b = violence.get("distance_mi"), _bearing(user, violence)
        return {"action": "SHELTER", "reason": f"active violence {d} mi to your {b}, lock down and stay off the street",
                "hazard": violence.get("type"), "confidence": 0.75, **_haz(violence),
                "factors": [f"VIOLENCE: {violence.get('type')} ({d} mi {b})"]}

    return {"action": "CLEAR", "reason": "no immediate threat in your rings", "hazard": None, "confidence": 0.6, "factors": []}
