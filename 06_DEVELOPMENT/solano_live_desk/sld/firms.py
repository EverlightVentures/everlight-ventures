from __future__ import annotations

import os

# NASA FIRMS active-fire hotspots (satellite). Free MAP_KEY.
FIRMS_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv/{key}/{src}/{bbox}/{days}"


def parse_csv(text: str) -> list[dict]:
    """Parse the FIRMS area CSV into wildfire-hotspot event dicts."""
    lines = (text or "").strip().splitlines()
    if len(lines) < 2 or "," not in lines[0]:
        return []
    ix = {h.strip(): i for i, h in enumerate(lines[0].split(","))}
    if "latitude" not in ix or "longitude" not in ix:
        return []

    def cell(cols, name):
        i = ix.get(name)
        return cols[i] if i is not None and i < len(cols) else ""

    out: list[dict] = []
    for ln in lines[1:]:
        c = ln.split(",")
        try:
            lat = float(cell(c, "latitude"))
            lon = float(cell(c, "longitude"))
        except ValueError:
            continue
        frp = cell(c, "frp")
        conf = cell(c, "confidence")
        ad, at = cell(c, "acq_date"), cell(c, "acq_time")
        out.append(
            {
                "id": f"firms:{lat:.4f},{lon:.4f},{ad}{at}",
                "source": "firms",
                "type": "Wildfire hotspot",
                "title": "Satellite fire detection",
                "lat": lat,
                "lon": lon,
                "geo_label": f"FRP {frp}, confidence {conf}",
                "log_time": f"{ad} {at}".strip(),
                "body": f"Satellite-detected fire. Radiative power {frp}, confidence {conf}.",
                "details": [],
                "severity": "MEDIUM",  # detection, not confirmed fire; proximity elevates it
            }
        )
    return out


def _fetch(bbox: str, key: str, src: str, days: int) -> str:
    import httpx

    r = httpx.get(
        FIRMS_URL.format(key=key, src=src, bbox=bbox, days=days),
        headers={"User-Agent": "solano-live-desk/0.1"},
        timeout=20,
    )
    r.raise_for_status()
    return r.text


def fetch(
    w: float, s: float, e: float, n: float,
    key: str | None = None, src: str = "VIIRS_SNPP_NRT", days: int = 1, fetch_fn=None,
) -> list[dict]:
    """Wildfire hotspots in a bbox (west,south,east,north). No key -> []."""
    key = key or os.environ.get("SLD_FIRMS_KEY")
    if not key:
        return []
    fetch_fn = fetch_fn or _fetch
    return parse_csv(fetch_fn(f"{w},{s},{e},{n}", key, src, days))
