from __future__ import annotations

# OpenFEMA disaster declarations (free, no key). Recent federally-declared
# disasters for the operator's state (fires, floods, storms, etc.).
FEMA = "https://www.fema.gov/api/open/v2/DisasterDeclarationsSummaries"


def parse(payload: dict) -> list[dict]:
    out: list[dict] = []
    seen = set()
    for d in payload.get("DisasterDeclarationsSummaries", []):
        num = d.get("disasterNumber")
        key = (num, d.get("designatedArea"))
        if key in seen:
            continue
        seen.add(key)
        out.append(
            {
                "disaster": num,
                "title": d.get("declarationTitle"),
                "type": d.get("incidentType"),
                "state": d.get("state"),
                "county": d.get("designatedArea"),
                "begin": d.get("incidentBeginDate"),
                "end": d.get("incidentEndDate"),
            }
        )
    return out


def _fetch(state: str, since: str) -> dict:
    import httpx

    params = {
        "$filter": f"state eq '{state}' and incidentBeginDate gt '{since}'",
        "$orderby": "incidentBeginDate desc",
        "$top": 50,
    }
    r = httpx.get(FEMA, params=params, headers={"User-Agent": "solano-live-desk/0.1"}, timeout=20)
    r.raise_for_status()
    return r.json()


def fetch(state: str = "CA", since: str = "2026-01-01", fetch_fn=None) -> list[dict]:
    fetch_fn = fetch_fn or _fetch
    try:
        return parse(fetch_fn(state, since))
    except Exception:  # noqa: BLE001
        return []
