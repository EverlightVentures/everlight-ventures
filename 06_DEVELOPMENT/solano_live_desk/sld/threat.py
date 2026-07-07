from __future__ import annotations

import re

from .geo_county import distance_mi

# Severity keyword tiers. Checked CRITICAL -> HIGH -> MEDIUM, first match wins.
_CRITICAL = re.compile(
    r"\b(shots?\s*fired|11-?99|shooting|stabbing|245|adw|armed|weapon|gun|"
    r"207|kidnap|211|robbery|in\s*pursuit|pursuit|10-?80|wrong[\s-]?way|"
    r"active\s*shooter|explosion|fully\s*involved|structure\s*fire|hostage|"
    r"11-?44|fatal|barricad)\b",
    re.I,
)
_HIGH = re.compile(
    r"\b(injury|injuries|1180|1181|11-?80|11-?81|vehicle\s*fire|hazmat|"
    r"gas\s*leak|wires?\s*down|arcing|rescue|rollover|overturn|major|"
    r"with\s*inj)\b",
    re.I,
)
_MEDIUM = re.compile(
    r"\b(collision|crash|medical|alarm|person\s*down|fire|smoke|assault|"
    r"fight|trespass|prowler|reckless)\b",
    re.I,
)
_NO_INJURY = re.compile(r"no\s*inj", re.I)

_SEV_ONLY = {"CRITICAL": "HIGH", "HIGH": "MEDIUM", "MEDIUM": "LOW", "LOW": "LOG"}

# matrix[severity][ring] -> threat level
_MATRIX = {
    "CRITICAL": {"IMMEDIATE": "EXTREME", "NEAR": "EXTREME", "AREA": "HIGH", "REGIONAL": "MEDIUM"},
    "HIGH": {"IMMEDIATE": "EXTREME", "NEAR": "HIGH", "AREA": "MEDIUM", "REGIONAL": "LOW"},
    "MEDIUM": {"IMMEDIATE": "HIGH", "NEAR": "MEDIUM", "AREA": "LOW", "REGIONAL": "LOW"},
    "LOW": {"IMMEDIATE": "MEDIUM", "NEAR": "LOW", "AREA": "LOW", "REGIONAL": "LOG"},
}
_BUMP = ["LOG", "LOW", "MEDIUM", "HIGH", "EXTREME"]


def severity(text: str) -> str:
    t = text or ""
    if _CRITICAL.search(t):
        return "CRITICAL"
    if _HIGH.search(t):
        return "HIGH"
    if _MEDIUM.search(t):
        return "LOW" if _NO_INJURY.search(t) else "MEDIUM"
    return "LOW"


def proximity_ring(dist_mi: float | None) -> str:
    if dist_mi is None:
        return "UNKNOWN"
    if dist_mi < 0.5:
        return "IMMEDIATE"
    if dist_mi < 2:
        return "NEAR"
    if dist_mi < 5:
        return "AREA"
    return "REGIONAL"


def threat_level(sev: str, ring: str, heading_toward: bool = False) -> str:
    base = _SEV_ONLY[sev] if ring == "UNKNOWN" else _MATRIX[sev][ring]
    if heading_toward:
        base = _BUMP[min(len(_BUMP) - 1, _BUMP.index(base) + 1)]
    return base


def classify(event: dict, user_latlon: tuple[float, float] | None) -> dict:
    """Attach severity, distance, ring, and threat_level to an event dict."""
    text = " ".join(
        str(v) for v in (event.get("type"), event.get("title"), event.get("body")) if v
    )
    sev = severity(text)
    dist = None
    if user_latlon and event.get("lat") is not None and event.get("lon") is not None:
        dist = distance_mi(user_latlon, (event["lat"], event["lon"]))
    ring = proximity_ring(dist)
    return {
        **event,
        "severity": sev,
        "distance_mi": round(dist, 2) if dist is not None else None,
        "ring": ring,
        "threat_level": threat_level(sev, ring),
    }
