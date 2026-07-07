from __future__ import annotations

ADSB_URL = "https://api.adsb.lol/v2/lat/{lat}/lon/{lon}/dist/{dist}"
MIL_PREFIXES = {"RCH", "CNV", "EVAC", "NAVY", "POLICE", "GRZLY", "SPAR", "DOOM", "REACH"}
EMERGENCY_SQUAWKS = {"7500", "7600", "7700"}  # hijack / radio-fail / general emergency


def classify(a: dict) -> str:
    """military | commercial | ga (general aviation / private)."""
    if (a.get("dbFlags") or 0) & 1:
        return "military"
    cs = (a.get("flight") or "").strip().upper()
    reg = (a.get("r") or "").upper()
    if any(cs.startswith(p) for p in MIL_PREFIXES):
        return "military"
    if not cs or cs == reg or cs.startswith("N"):
        return "ga"
    return "commercial"


def parse(payload: dict) -> list[dict]:
    """Normalize an adsb.lol response into aircraft dicts."""
    out: list[dict] = []
    for a in payload.get("ac") or payload.get("aircraft") or []:
        lat, lon = a.get("lat"), a.get("lon")
        if lat is None or lon is None:
            continue
        squawk = str(a.get("squawk") or "")
        out.append(
            {
                "id": a.get("hex"),
                "flight": (a.get("flight") or "").strip() or a.get("r") or a.get("hex"),
                "lat": lat,
                "lon": lon,
                "alt": a.get("alt_baro"),
                "speed": a.get("gs"),
                "track": a.get("track") if a.get("track") is not None else (a.get("true_heading") or 0),
                "type": a.get("t"),
                "reg": a.get("r"),
                "kind": classify(a),
                "squawk": squawk,
                "emergency": squawk in EMERGENCY_SQUAWKS,
            }
        )
    return out


def _fetch(lat: float, lon: float, dist_nm: int) -> dict:
    import httpx

    r = httpx.get(
        ADSB_URL.format(lat=lat, lon=lon, dist=dist_nm),
        headers={"User-Agent": "solano-live-desk/0.1 (personal safety)"},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


def fetch(lat: float, lon: float, dist_nm: int = 100, fetch_fn=None) -> list[dict]:
    """Aircraft within dist_nm nautical miles of a point (commercial + military)."""
    fetch_fn = fetch_fn or _fetch
    return parse(fetch_fn(lat, lon, dist_nm))
