"""
username_enrichment -- username-across-platforms sweep.

Replaces the HEAD-only social_recon.py with a real username sweep.
Source: WhatsMyName project (500+ platform URL templates, MIT licensed,
maintained by WebBreacher). Per feedback_network_first_not_clone_first:
we fetch the JSON catalog at runtime from the GitHub raw URL on first
call and cache it for the lifetime of the process. Offline fallback is
a 30-platform hardcoded list.

For each platform URL template, substitute the candidate username, HEAD
probe the URL, treat 200 (or platform-specific "exists" status) as a
positive hit. Returns the list of platforms where the username appears.

Legal scope:
  - PUBLIC profiles only (covered by hiQ v. LinkedIn, 9th Cir.)
  - No authentication / cookies / session reuse
  - No deep-scraping; HEAD probe + status interpretation
  - Signal stays internal as personality_synth fuel or buyer vetting,
    NEVER quoted in outbound copy per the Google-version doctrine

Target conventions:
  "JOHN HOWARD"          -> candidate handles: johnhoward, jhoward, jhh, etc.
  "rich_gee"             -> exact handle, single sweep
  "user@example.com"     -> derive handle from local-part
"""
from __future__ import annotations

import re
from urllib.parse import quote
from typing import Any

from ._common import head, fetch, now_ms


NAME = "Username Enrichment"
DOMAINS = [
    "raw.githubusercontent.com",
    # Major platforms HEAD-probed at runtime; live_log records each
    "github.com", "twitter.com", "x.com", "instagram.com", "reddit.com",
    "tiktok.com", "linkedin.com", "medium.com", "pinterest.com",
    "patreon.com", "behance.net", "dribbble.com", "spotify.com",
    "soundcloud.com", "youtube.com", "vimeo.com", "twitch.tv",
    "keybase.io", "about.me", "gravatar.com", "flickr.com",
]
WHEN = ["person", "email", "username"]

# Network-first source: live WhatsMyName JSON catalog (500+ platforms)
WMN_URL = "https://raw.githubusercontent.com/WebBreacher/WhatsMyName/main/wmn-data.json"

# Offline fallback: top-30 hand-curated platform templates
FALLBACK_PLATFORMS = [
    {"name": "GitHub", "uri_check": "https://github.com/{account}", "e_code": 200, "m_code": 404},
    {"name": "Twitter/X", "uri_check": "https://twitter.com/{account}", "e_code": 200, "m_code": 404},
    {"name": "Reddit", "uri_check": "https://www.reddit.com/user/{account}", "e_code": 200, "m_code": 404},
    {"name": "Instagram", "uri_check": "https://www.instagram.com/{account}/", "e_code": 200, "m_code": 404},
    {"name": "TikTok", "uri_check": "https://www.tiktok.com/@{account}", "e_code": 200, "m_code": 404},
    {"name": "LinkedIn", "uri_check": "https://www.linkedin.com/in/{account}/", "e_code": 200, "m_code": 404},
    {"name": "Medium", "uri_check": "https://medium.com/@{account}", "e_code": 200, "m_code": 404},
    {"name": "Pinterest", "uri_check": "https://www.pinterest.com/{account}/", "e_code": 200, "m_code": 404},
    {"name": "Patreon", "uri_check": "https://www.patreon.com/{account}", "e_code": 200, "m_code": 404},
    {"name": "Behance", "uri_check": "https://www.behance.net/{account}", "e_code": 200, "m_code": 404},
    {"name": "Dribbble", "uri_check": "https://dribbble.com/{account}", "e_code": 200, "m_code": 404},
    {"name": "SoundCloud", "uri_check": "https://soundcloud.com/{account}", "e_code": 200, "m_code": 404},
    {"name": "YouTube", "uri_check": "https://www.youtube.com/@{account}", "e_code": 200, "m_code": 404},
    {"name": "Vimeo", "uri_check": "https://vimeo.com/{account}", "e_code": 200, "m_code": 404},
    {"name": "Twitch", "uri_check": "https://www.twitch.tv/{account}", "e_code": 200, "m_code": 404},
    {"name": "Keybase", "uri_check": "https://keybase.io/{account}", "e_code": 200, "m_code": 404},
    {"name": "About.me", "uri_check": "https://about.me/{account}", "e_code": 200, "m_code": 404},
    {"name": "Gravatar", "uri_check": "https://en.gravatar.com/{account}", "e_code": 200, "m_code": 404},
    {"name": "Flickr", "uri_check": "https://www.flickr.com/people/{account}/", "e_code": 200, "m_code": 404},
    {"name": "Goodreads", "uri_check": "https://www.goodreads.com/{account}", "e_code": 200, "m_code": 404},
    {"name": "Letterboxd", "uri_check": "https://letterboxd.com/{account}/", "e_code": 200, "m_code": 404},
    {"name": "Untappd", "uri_check": "https://untappd.com/user/{account}", "e_code": 200, "m_code": 404},
    {"name": "Strava", "uri_check": "https://www.strava.com/athletes/{account}", "e_code": 200, "m_code": 404},
    {"name": "DeviantArt", "uri_check": "https://www.deviantart.com/{account}", "e_code": 200, "m_code": 404},
    {"name": "Bandcamp", "uri_check": "https://bandcamp.com/{account}", "e_code": 200, "m_code": 404},
    {"name": "Last.fm", "uri_check": "https://www.last.fm/user/{account}", "e_code": 200, "m_code": 404},
    {"name": "ProductHunt", "uri_check": "https://www.producthunt.com/@{account}", "e_code": 200, "m_code": 404},
    {"name": "HackerNews", "uri_check": "https://news.ycombinator.com/user?id={account}", "e_code": 200, "m_code": 404},
    {"name": "StackOverflow", "uri_check": "https://stackoverflow.com/users/{account}", "e_code": 200, "m_code": 404},
    {"name": "DevTo", "uri_check": "https://dev.to/{account}", "e_code": 200, "m_code": 404},
]

# Module-level cache of the WMN catalog (lazy-loaded on first call)
_WMN_CACHE: dict[str, Any] = {"platforms": None, "source": None}


async def _load_platform_catalog(http) -> tuple[list[dict], str]:
    """Network-first per feedback_network_first_not_clone_first.
    Returns (platforms, source_label). Source is 'whatsmyname_live' or 'hardcoded_fallback'."""
    if _WMN_CACHE["platforms"] is not None:
        return _WMN_CACHE["platforms"], _WMN_CACHE["source"]

    status, body, err = await fetch(http, WMN_URL, timeout=10)
    if status == 200 and body:
        try:
            import json as _json
            data = _json.loads(body)
            sites = data.get("sites", [])
            # Filter to known-good entries with HEAD-probable URL templates
            usable = [
                s for s in sites
                if s.get("uri_check") and "{account}" in s["uri_check"]
                and s.get("e_code") and s.get("m_code")
            ]
            if len(usable) >= 50:  # sanity check
                _WMN_CACHE["platforms"] = usable
                _WMN_CACHE["source"] = "whatsmyname_live"
                return usable, "whatsmyname_live"
        except (ValueError, KeyError):
            pass

    # Offline fallback
    _WMN_CACHE["platforms"] = FALLBACK_PLATFORMS
    _WMN_CACHE["source"] = "hardcoded_fallback"
    return FALLBACK_PLATFORMS, "hardcoded_fallback"


def _candidate_handles(target: str) -> list[str]:
    """Turn a name/email/raw-handle into candidate username strings."""
    t = target.strip()
    # If looks like email, derive handle from local-part
    if "@" in t and "." in t.split("@", 1)[-1]:
        local = t.split("@", 1)[0]
        return [local.lower(), local.lower().replace(".", "")]
    # If single token, treat as exact handle
    if " " not in t and "@" not in t:
        return [t.lower()]
    # Multi-word name -> standard handle permutations
    parts = [p for p in re.split(r"\s+", t.lower()) if p and p.replace("-", "").isalpha()]
    if len(parts) < 2:
        return [t.lower().replace(" ", "")]
    first, last = parts[0], parts[-1]
    return [
        f"{first}{last}",       # johnhoward
        f"{first[0]}{last}",    # jhoward
        f"{first}.{last}",      # john.howard (some platforms accept dots)
        f"{first}_{last}",      # john_howard
        last,                   # howard (rare-name path)
    ]


async def run(target: str, http) -> dict:
    t0 = now_ms()
    findings: list = []
    raw: dict = {"candidates": [], "platform_source": None, "platforms_probed": 0,
                 "hits": 0}

    platforms, source = await _load_platform_catalog(http)
    raw["platform_source"] = source
    raw["platforms_probed"] = len(platforms)

    handles = _candidate_handles(target)
    raw["candidates"] = handles

    if not handles:
        return {"ok": False, "findings": [], "raw": raw,
                "elapsed_ms": now_ms() - t0,
                "investigator": NAME, "investigator_id": "username_enrichment"}

    # Limit scan: top 50 platforms x first handle candidate. Other handles
    # tested only on top 15 platforms to keep latency manageable.
    primary_handle = handles[0]
    other_handles = handles[1:5]  # cap at 4 alt handles

    seen: set[tuple[str, str]] = set()  # (platform_name, handle) dedup
    probe_count = 0
    PROBE_BUDGET = 70  # roughly 30-40 seconds total

    for plat in platforms[:50]:
        if probe_count >= PROBE_BUDGET:
            break
        url = plat["uri_check"].replace("{account}", quote(primary_handle, safe=""))
        e_code = plat.get("e_code")
        try:
            status = await head(http, url, timeout=5)
            probe_count += 1
            if status == e_code:
                key = (plat["name"], primary_handle)
                if key not in seen:
                    seen.add(key)
                    findings.append({
                        "label": f"{plat['name']}",
                        "value": f"@{primary_handle} present (HTTP {status})",
                        "url": url,
                    })
        except Exception:
            pass

    # Run top-15 only for alternative handles (broader sweep gets too long)
    for alt_handle in other_handles:
        for plat in platforms[:15]:
            if probe_count >= PROBE_BUDGET:
                break
            url = plat["uri_check"].replace("{account}", quote(alt_handle, safe=""))
            try:
                status = await head(http, url, timeout=5)
                probe_count += 1
                if status == plat.get("e_code"):
                    key = (plat["name"], alt_handle)
                    if key not in seen:
                        seen.add(key)
                        findings.append({
                            "label": f"{plat['name']} (alt)",
                            "value": f"@{alt_handle} present (HTTP {status})",
                            "url": url,
                        })
            except Exception:
                pass

    raw["hits"] = len(findings)
    raw["probes_used"] = probe_count

    return {
        "ok": len(findings) > 0,
        "findings": findings,
        "raw": raw,
        "elapsed_ms": now_ms() - t0,
        "investigator": NAME,
        "investigator_id": "username_enrichment",
    }
