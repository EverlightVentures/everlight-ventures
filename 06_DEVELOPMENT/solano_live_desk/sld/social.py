from __future__ import annotations

import re
import xml.etree.ElementTree as ET

# Legal, free social recon: Reddit's public RSS (the .json API 403s from cloud
# IPs, but RSS is open). Monitor local subs for safety/hotspot chatter.

_ATOM = {"a": "http://www.w3.org/2005/Atom"}
LOCAL_SUBS = ["bayarea", "Sacramento", "Solano", "Fairfield", "vacaville", "Napa", "Vallejo"]
_SAFETY = re.compile(
    r"shoot|shots?\s*fired|\bfire\b|wildfire|crash|collision|accident|police|sheriff|swat|"
    r"robber|stabb?|assault|evac|protest|riot|danger|avoid|active\s*shooter|pursuit|missing|"
    r"amber\s*alert|homicide|burglar|arson|explos|hazmat|lockdown|standoff|gunman|looting|"
    r"power\s*outage|flood|road\s*closed|shelter",
    re.I,
)


def _parse_atom(xml: str) -> list[dict]:
    out: list[dict] = []
    try:
        root = ET.fromstring(xml)
    except Exception:  # noqa: BLE001
        return out
    for e in root.findall("a:entry", _ATOM):
        title = (e.findtext("a:title", "", _ATOM) or "").strip()
        le = e.find("a:link", _ATOM)
        out.append({
            "title": title,
            "url": le.get("href", "") if le is not None else "",
            "author": e.findtext("a:author/a:name", "", _ATOM),
            "updated": e.findtext("a:updated", "", _ATOM),
        })
    return out


def fetch_reddit_rss(subs: list[str], query: str | None = None, limit: int = 25) -> list[dict]:
    import httpx

    out: list[dict] = []
    for sub in subs:
        try:
            if query:
                url = f"https://www.reddit.com/r/{sub}/search.rss"
                params = {"q": query, "restrict_sr": 1, "sort": "new", "limit": limit, "t": "week"}
            else:
                url = f"https://www.reddit.com/r/{sub}/new.rss"
                params = {"limit": limit}
            r = httpx.get(url, params=params, headers={"User-Agent": "Mozilla/5.0 solano-safety-monitor"},
                          timeout=15, follow_redirects=True)
            if r.status_code == 200:
                for p in _parse_atom(r.text):
                    p["source"] = "reddit"
                    p["sub"] = sub
                    out.append(p)
        except Exception:  # noqa: BLE001
            pass
    return out


def safety_posts(place: str = "Solano County") -> list[dict]:
    """Recent local safety/hotspot chatter: Reddit posts that hit a safety keyword
    or name the operator's city, newest first, deduped."""
    city = place.split(",")[0].strip()
    posts = fetch_reddit_rss(LOCAL_SUBS)
    rel = [p for p in posts if _SAFETY.search(p["title"]) or (city and city.lower() in p["title"].lower())]
    seen, out = set(), []
    for p in sorted(rel, key=lambda x: x.get("updated", ""), reverse=True):
        if p["url"] in seen:
            continue
        seen.add(p["url"])
        out.append(p)
    return out[:25]
