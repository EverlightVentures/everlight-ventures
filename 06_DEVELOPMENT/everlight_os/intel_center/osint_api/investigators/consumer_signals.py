"""
consumer_signals -- the Google-targeting-equivalent for public consumer behavior.

Pulls public-only signals from:
  - Yelp public reviews (restaurants visited, ratings)
  - Goodreads (books read / want to read)
  - Letterboxd (films rated)
  - Strava public profiles (running/cycling routes + clubs)
  - Untappd public check-ins (beer / drinks preferences)
  - Spotify public playlists (music taste)
  - Pinterest boards (aspirational interests)
  - Product Hunt upvotes (app preferences)
  - IMDb public ratings

Each finding feeds personality_synth which extracts interest categories
(Food/Travel, Art/Music, Sports & Fitness, etc.) which become pitch hooks.

Per legal_scope.py: PUBLIC ONLY. We do not authenticate, do not pierce
private playlists/lists, do not scrape from accounts.
"""
from __future__ import annotations

import asyncio
import re
from urllib.parse import quote

from ._common import fetch, now_ms

NAME = "Consumer Signals (deep mine)"
DOMAINS = [
    "yelp.com", "goodreads.com", "letterboxd.com", "strava.com",
    "untappd.com", "open.spotify.com", "pinterest.com", "producthunt.com",
    "imdb.com", "tripadvisor.com",
]
WHEN = ["person", "*"]


_TITLE_RE = re.compile(r"<title[^>]*>([^<]+)</title>", re.I)
_META_DESC = re.compile(
    r'<meta\s+[^>]*(?:name|property)=["\'](?:og:description|description|twitter:description)["\']'
    r'[^>]*content=["\']([^"\']{20,400})["\']',
    re.I,
)


def _meta_desc(html: str) -> str:
    m = _META_DESC.search(html[:30000])
    return m.group(1).strip() if m else ""


def _title(html: str) -> str:
    m = _TITLE_RE.search(html[:6000])
    return m.group(1).strip() if m else ""


async def _yelp(handle: str, http) -> list[dict]:
    """Yelp public reviewer page."""
    findings = []
    url = f"https://www.yelp.com/user_details?find={quote(handle)}"
    status, body, err = await fetch(http, url, timeout=8)
    if status == 200 and body and len(body) > 1000:
        desc = _meta_desc(body)
        title = _title(body)
        if "yelp" in (title + desc).lower() and handle.lower() in (title + desc).lower():
            findings.append({
                "label": "Yelp reviewer profile",
                "value": (title or desc)[:240],
                "url": url,
            })
    return findings


async def _goodreads(handle: str, http) -> list[dict]:
    """Goodreads public profile + 'currently-reading' shelf."""
    findings = []
    # Goodreads doesn't have clean username URLs but the search page does
    search_url = f"https://www.goodreads.com/search?q={quote(handle)}&search_type=people"
    status, body, err = await fetch(http, search_url, timeout=8)
    if status == 200 and body and "userName" in body[:50000]:
        for m in re.finditer(r'<a[^>]+class="userName"[^>]+href="([^"]+)"[^>]*>([^<]+)</a>',
                              body[:40000])[:2] if False else \
                  list(re.finditer(r'<a[^>]+class="userName"[^>]+href="([^"]+)"[^>]*>([^<]+)</a>',
                                    body[:40000]))[:2]:
            findings.append({
                "label": "Goodreads profile",
                "value": m.group(2).strip(),
                "url": "https://www.goodreads.com" + m.group(1),
            })
    return findings


async def _letterboxd(handle: str, http) -> list[dict]:
    """Letterboxd public film ratings."""
    findings = []
    url = f"https://letterboxd.com/{handle}/"
    status, body, err = await fetch(http, url, timeout=8)
    if status == 200 and body and "letterboxd" in body.lower()[:1000]:
        desc = _meta_desc(body)
        if desc:
            findings.append({
                "label": "Letterboxd film profile",
                "value": desc[:240],
                "url": url,
            })
    return findings


async def _strava(handle: str, http) -> list[dict]:
    """Strava public athlete profile."""
    findings = []
    url = f"https://www.strava.com/athletes/{quote(handle)}"
    status, body, err = await fetch(http, url, timeout=8)
    if status == 200 and body and "strava" in body.lower()[:2000]:
        desc = _meta_desc(body)
        title = _title(body)
        if title or desc:
            findings.append({
                "label": "Strava athlete",
                "value": (desc or title)[:240],
                "url": url,
            })
    # also try /athletes/<num> via search-engine probe? Skip -- HEAD ping was enough
    return findings


async def _untappd(handle: str, http) -> list[dict]:
    """Untappd public beer check-in profile."""
    findings = []
    url = f"https://untappd.com/user/{quote(handle)}"
    status, body, err = await fetch(http, url, timeout=8)
    if status == 200 and body:
        desc = _meta_desc(body)
        if desc and ("untappd" in body.lower()[:2000] or "beer" in desc.lower()):
            findings.append({
                "label": "Untappd beer profile",
                "value": desc[:240],
                "url": url,
            })
    return findings


async def _spotify(handle: str, http) -> list[dict]:
    """Spotify public profile."""
    findings = []
    url = f"https://open.spotify.com/user/{quote(handle)}"
    status, body, err = await fetch(http, url, timeout=8)
    if status == 200 and body:
        desc = _meta_desc(body)
        title = _title(body)
        if title and "spotify" in title.lower():
            findings.append({
                "label": "Spotify public playlists",
                "value": (desc or title)[:240],
                "url": url,
            })
    return findings


async def _producthunt(handle: str, http) -> list[dict]:
    """Product Hunt profile -- apps they've upvoted = tech preferences."""
    findings = []
    url = f"https://www.producthunt.com/@{quote(handle)}"
    status, body, err = await fetch(http, url, timeout=8)
    if status == 200 and body:
        desc = _meta_desc(body)
        if desc and len(desc) > 30:
            findings.append({
                "label": "Product Hunt activity",
                "value": desc[:240],
                "url": url,
            })
    return findings


async def _imdb(handle: str, http) -> list[dict]:
    """IMDb username profile."""
    findings = []
    url = f"https://www.imdb.com/user/ur{handle}/" if handle.isdigit() else None
    if not url:
        return findings
    status, body, err = await fetch(http, url, timeout=8)
    if status == 200 and body:
        desc = _meta_desc(body)
        if desc:
            findings.append({
                "label": "IMDb user profile",
                "value": desc[:240],
                "url": url,
            })
    return findings


async def run(target: str, http) -> dict:
    t0 = now_ms()
    findings: list = []
    raw: dict = {}

    handle = re.sub(r"[^a-z0-9_-]", "", target.lower().replace(" ", ""))
    if not handle or len(handle) < 3:
        return {"ok": False, "findings": [], "raw": {"reason": "no_handle"},
                "elapsed_ms": now_ms() - t0, "investigator": NAME,
                "investigator_id": "consumer_signals"}

    probes = [
        ("yelp", _yelp), ("goodreads", _goodreads), ("letterboxd", _letterboxd),
        ("strava", _strava), ("untappd", _untappd), ("spotify", _spotify),
        ("producthunt", _producthunt),
    ]

    async def run_probe(name, fn):
        try:
            return name, await fn(handle, http)
        except Exception as e:
            return name, []

    results = await asyncio.gather(*(run_probe(n, f) for n, f in probes), return_exceptions=True)
    for r in results:
        if isinstance(r, tuple):
            name, hits = r
            raw[name] = len(hits)
            findings.extend(hits)

    return {
        "ok": len(findings) > 0,
        "findings": findings,
        "raw": raw,
        "elapsed_ms": now_ms() - t0,
        "investigator": NAME,
        "investigator_id": "consumer_signals",
    }
