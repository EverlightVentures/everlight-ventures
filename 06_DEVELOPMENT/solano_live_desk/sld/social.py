from __future__ import annotations

import re
import xml.etree.ElementTree as ET

# Legal, free social recon: Reddit's public RSS (the .json API 403s from cloud
# IPs, but RSS is open). Monitor local subs for safety/hotspot chatter.

_ATOM = {"a": "http://www.w3.org/2005/Atom"}
# The big regional subs stay reliable (200); the tiny local ones 429 + are quiet.
# We geo-tag posts to cities anyway, so regional coverage still lands on Solano.
LOCAL_SUBS = ["bayarea", "Sacramento", "napa"]
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
    import time

    import httpx

    out: list[dict] = []
    for i, sub in enumerate(subs):
        if i:
            time.sleep(3)  # avoid Reddit's per-window 429 from the cloud IP
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


# Bubble cities -> centroid. Posts name cities, not addresses, so we geo-tag to
# the city and cluster there (city-level heat is the honest granularity).
CITY_COORDS = {
    "fairfield": (38.2494, -122.0400), "vacaville": (38.3566, -121.9877),
    "vallejo": (38.1041, -122.2566), "suisun": (38.2382, -122.0405),
    "napa": (38.2975, -122.2869), "benicia": (38.0494, -122.1586),
    "dixon": (38.4455, -121.8233), "rio vista": (38.1557, -121.6913),
    "davis": (38.5449, -121.7405), "woodland": (38.6785, -121.7733),
    "concord": (37.9780, -122.0311), "walnut creek": (37.9101, -122.0652),
    "antioch": (38.0049, -121.8058), "pittsburg": (38.0280, -121.8847),
    "oakland": (37.8044, -122.2712), "berkeley": (37.8715, -122.2730),
    "richmond": (37.9358, -122.3477), "san leandro": (37.7249, -122.1561),
    "hayward": (37.6688, -122.0808), "fremont": (37.5485, -121.9886),
    "livermore": (37.6819, -121.7680), "pleasanton": (37.6624, -121.8747),
    "sacramento": (38.5816, -121.4944), "vacaville": (38.3566, -121.9877),
}


def tag_city(text: str):
    low = (text or "").lower()
    for city, coord in CITY_COORDS.items():
        if city in low:
            return city, coord
    return None, None


def hotspots(posts: list[dict]) -> list[dict]:
    """City-level heat: safety posts grouped by geo-tagged city, hottest first."""
    from collections import defaultdict

    g: dict[str, list] = defaultdict(list)
    for p in posts:
        if p.get("city"):
            g[p["city"]].append(p)
    out = []
    for city, ps in g.items():
        c = CITY_COORDS.get(city)
        if not c:
            continue
        out.append({"city": city.title(), "lat": c[0], "lon": c[1], "count": len(ps), "posts": ps[:5]})
    out.sort(key=lambda x: x["count"], reverse=True)
    return out


def collect(base: str, place: str = "Solano County") -> dict:
    """Fetch safety chatter, geo-tag it to cities, compute hotspots, write
    store/social.json. Run periodically (from the ingest loop)."""
    import json
    import os
    import time

    posts = safety_posts(place)
    for p in posts:
        city, coord = tag_city(p.get("title", ""))
        if city:
            p["city"] = city
            p["lat"], p["lon"] = coord
    data = {"posts": posts, "hotspots": hotspots(posts), "updated": int(time.time())}
    try:
        json.dump(data, open(os.path.join(base, "social.json"), "w"))
    except Exception:  # noqa: BLE001
        pass
    return data


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
