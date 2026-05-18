"""
social_bio_scraper -- the deep social fetch.

Stops at HEAD checks (current social_recon). This module actually GETs found
social profile pages and extracts:
  - bio / about / description text
  - location text
  - job title / company
  - follower / follow count (if shown)
  - interests / hashtags from public posts
  - profile photo URL

These signals feed personality_synth + pitch_hooks. The "Google knows you
like classic cars" effect comes from THIS data, not the existence of the
profile URL.

Per Operator Truth: never scrape what's not publicly served. We only fetch
the public-facing profile page (no login, no auth). If a site blocks us
(401/403), we record that and move on.
"""
from __future__ import annotations

import asyncio
import re
from urllib.parse import quote

from ._common import fetch, now_ms

NAME = "Deep Social Mine"
DOMAINS = [
    "github.com", "instagram.com", "twitter.com", "x.com", "reddit.com",
    "linkedin.com", "youtube.com", "medium.com", "pinterest.com",
    "behance.net", "dribbble.com", "patreon.com", "about.me",
    "keybase.io", "gravatar.com", "producthunt.com",
]
WHEN = ["person", "*"]


_META_RE = re.compile(
    r'<meta\s+[^>]*(?:name|property)=["\']([^"\']+)["\'][^>]*content=["\']([^"\']{2,300})["\']',
    re.I,
)
_TITLE_RE = re.compile(r"<title[^>]*>([^<]{2,200})</title>", re.I)
_BIO_RE = re.compile(
    r'(?:bio|about|description|profile)["\']?\s*[:=]\s*["\']([^"\']{20,400})["\']',
    re.I,
)
_LOC_RE = re.compile(r'(?:location|locale|place)["\']?\s*[:=]\s*["\']([A-Z][^"\']{3,60})["\']', re.I)
_HASHTAG_RE = re.compile(r"(?<![\w])#([a-zA-Z][a-zA-Z0-9_]{2,30})")


def _parse_bio(html: str, url: str) -> dict:
    """Extract bio/location/title-ish text from any social profile HTML."""
    out: dict = {"url": url, "raw_size": len(html)}

    # 1. OG tags + meta description (most reliable across platforms)
    for m in _META_RE.finditer(html[:60000]):
        prop = (m.group(1) or "").lower()
        val = m.group(2).strip()
        if prop in ("og:description", "description", "twitter:description"):
            if not out.get("bio"):
                out["bio"] = val[:300]
        elif prop in ("og:title", "twitter:title"):
            out["page_title"] = val[:160]
        elif prop in ("og:site_name",):
            out["platform"] = val[:60]
        elif prop in ("og:image", "twitter:image"):
            out["avatar_url"] = val
        elif prop in ("profile:first_name", "profile:last_name"):
            out.setdefault("name_hints", []).append(val)

    # 2. <title> as fallback
    if not out.get("page_title"):
        m = _TITLE_RE.search(html[:6000])
        if m:
            out["page_title"] = m.group(1).strip()[:160]

    # 3. JSON-LD blocks (LinkedIn, some Twitter etc embed structured data)
    for m in re.finditer(r'<script[^>]+application/ld\+json[^>]*>(.+?)</script>',
                          html[:80000], re.I | re.S):
        try:
            import json as _json
            data = _json.loads(m.group(1))
            if isinstance(data, dict):
                if data.get("description") and not out.get("bio"):
                    out["bio"] = str(data["description"])[:300]
                if data.get("jobTitle"):
                    out["job_title"] = str(data["jobTitle"])[:120]
                if data.get("worksFor", {}).get("name"):
                    out["employer"] = str(data["worksFor"]["name"])[:120]
                addr = data.get("address") or {}
                if isinstance(addr, dict):
                    parts = [addr.get(k) for k in ("addressLocality", "addressRegion", "addressCountry") if addr.get(k)]
                    if parts:
                        out["location"] = ", ".join(parts)[:120]
        except (ValueError, AttributeError):
            pass

    # 4. Bio-ish regex fallback
    if not out.get("bio"):
        m = _BIO_RE.search(html[:30000])
        if m:
            out["bio"] = m.group(1).strip()[:300]

    # 5. Hashtags from page text (Instagram/Twitter clusters of interests)
    text_strip = re.sub(r"<[^>]+>", " ", html[:50000])
    tags = _HASHTAG_RE.findall(text_strip)[:30]
    if tags:
        # dedupe + take top 12
        seen = set(); uniq = []
        for t in tags:
            tl = t.lower()
            if tl not in seen:
                seen.add(tl); uniq.append(t)
        out["hashtags"] = uniq[:12]

    return out


async def run(target: str, http) -> dict:
    """For each social profile probably belonging to target, fetch + parse."""
    t0 = now_ms()
    findings = []
    raw: dict = {}

    handle = re.sub(r"[^a-z0-9_-]", "", target.lower().replace(" ", ""))
    if not handle or len(handle) < 3:
        return {"ok": False, "findings": [],
                "raw": {"reason": "no_handle_derivable"},
                "elapsed_ms": now_ms() - t0,
                "investigator": NAME, "investigator_id": "social_bio_scraper"}

    # Same probe set as social_recon, but full GET
    PROFILES = [
        ("GitHub",    f"https://github.com/{handle}"),
        ("Twitter/X", f"https://twitter.com/{handle}"),
        ("Reddit",    f"https://www.reddit.com/user/{handle}/about.json"),
        ("Medium",    f"https://medium.com/@{handle}/about"),
        ("ProductHunt", f"https://www.producthunt.com/@{handle}"),
        ("About.me", f"https://about.me/{handle}"),
        ("Keybase",  f"https://keybase.io/{handle}"),
        ("Pinterest", f"https://www.pinterest.com/{handle}/"),
        ("Behance", f"https://www.behance.net/{handle}"),
        ("Dribbble", f"https://dribbble.com/{handle}"),
    ]

    sem = asyncio.Semaphore(6)

    async def probe(label: str, url: str):
        async with sem:
            status, body, err = await fetch(http, url, timeout=10)
            raw[label] = {"status": status, "len": len(body or "")}
            if not body or len(body) < 500 or status >= 400:
                return None
            parsed = _parse_bio(body, url)
            if not (parsed.get("bio") or parsed.get("page_title") or
                     parsed.get("hashtags") or parsed.get("location")):
                return None
            return label, parsed

    coros = [probe(l, u) for l, u in PROFILES]
    for result in await asyncio.gather(*coros, return_exceptions=True):
        if isinstance(result, tuple):
            label, parsed = result
            # Bio finding
            if parsed.get("bio"):
                findings.append({
                    "label": f"{label} bio",
                    "value": parsed["bio"],
                    "url": parsed["url"],
                })
            # Location finding (a strong identity-verifier signal)
            if parsed.get("location"):
                findings.append({
                    "label": f"{label} location",
                    "value": parsed["location"],
                    "url": parsed["url"],
                })
            # Job title
            if parsed.get("job_title"):
                v = parsed["job_title"]
                if parsed.get("employer"):
                    v += f" @ {parsed['employer']}"
                findings.append({
                    "label": f"{label} role",
                    "value": v,
                    "url": parsed["url"],
                })
            # Hashtags / interests (the pitch-hook gold)
            if parsed.get("hashtags"):
                findings.append({
                    "label": f"{label} interests",
                    "value": "#" + ", #".join(parsed["hashtags"]),
                    "url": parsed["url"],
                })

    return {
        "ok": len(findings) > 0,
        "findings": findings,
        "raw": raw,
        "elapsed_ms": now_ms() - t0,
        "investigator": NAME,
        "investigator_id": "social_bio_scraper",
    }
