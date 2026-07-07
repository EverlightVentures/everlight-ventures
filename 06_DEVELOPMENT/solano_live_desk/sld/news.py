from __future__ import annotations

# GDELT DOC 2.0 -- free global news-events database, no key. Surfaces recent
# articles about a place so the operator sees the wider story behind incidents.
GDELT_DOC = "https://api.gdeltproject.org/api/v2/doc/doc"


def parse(payload: dict) -> list[dict]:
    out: list[dict] = []
    for a in payload.get("articles", []):
        out.append(
            {
                "title": a.get("title"),
                "url": a.get("url"),
                "domain": a.get("domain"),
                "time": a.get("seendate"),
                "image": a.get("socialimage"),
            }
        )
    return out


def _fetch(query: str, timespan: str, maxrecords: int) -> dict:
    import httpx

    r = httpx.get(
        GDELT_DOC,
        params={
            "query": query, "mode": "artlist", "format": "json",
            "timespan": timespan, "maxrecords": maxrecords, "sort": "datedesc",
        },
        headers={"User-Agent": "solano-live-desk/0.1"},
        timeout=20,
    )
    # GDELT throttles (429) and occasionally returns empty/non-JSON. Degrade to
    # an empty list rather than raising, so the news panel just shows "no news".
    if r.status_code != 200:
        return {"articles": []}
    try:
        return r.json()
    except Exception:  # noqa: BLE001
        return {"articles": []}


def fetch_news(place: str, timespan: str = "3d", maxrecords: int = 25, fetch_fn=None) -> list[dict]:
    """Recent English news mentioning a place (city or county name)."""
    fetch_fn = fetch_fn or _fetch
    query = f'"{place}" sourcelang:english'
    return parse(fetch_fn(query, timespan, maxrecords))
