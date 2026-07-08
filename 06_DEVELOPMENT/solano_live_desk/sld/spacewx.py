from __future__ import annotations

# NOAA SWPC planetary K-index (free, no key). A geomagnetic storm degrades the
# GPS this whole system leans on -- knowing GPS is unreliable is survival info.
SWPC_KP = "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json"


def parse_kp(payload) -> float | None:
    """Latest Kp. SWPC returns a list of {time_tag, Kp, ...} dicts (older mirrors
    used [[header],[row],...] arrays) -- handle both."""
    if not isinstance(payload, list) or not payload:
        return None
    last = payload[-1]
    try:
        return float(last["Kp"] if isinstance(last, dict) else last[1])
    except (ValueError, TypeError, IndexError, KeyError):
        return None


def status_for(kp: float | None) -> dict:
    if kp is None:
        return {"kp": None, "level": "unknown", "gps": "GPS status unknown", "alert": False}
    if kp >= 7:
        return {"kp": kp, "level": "severe storm", "gps": "GPS + HF radio badly degraded", "alert": True}
    if kp >= 5:
        return {"kp": kp, "level": "geomagnetic storm", "gps": "GPS may drift, radio noisy", "alert": True}
    if kp >= 4:
        return {"kp": kp, "level": "unsettled", "gps": "minor GPS noise possible", "alert": False}
    return {"kp": kp, "level": "quiet", "gps": "GPS nominal", "alert": False}


def _fetch() -> list:
    import httpx

    r = httpx.get(SWPC_KP, headers={"User-Agent": "solano-live-desk/0.1"}, timeout=15)
    r.raise_for_status()
    return r.json()


def fetch(fetch_fn=None) -> dict:
    fetch_fn = fetch_fn or _fetch
    try:
        return status_for(parse_kp(fetch_fn()))
    except Exception:  # noqa: BLE001
        return status_for(None)
