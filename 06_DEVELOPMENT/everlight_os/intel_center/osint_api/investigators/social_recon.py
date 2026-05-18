"""Sherlock-style username sweep across 25+ social platforms."""
from urllib.parse import quote
from ._common import fetch, head, now_ms
import re

NAME = "Social Recon"
DOMAINS = [
    "github.com", "twitter.com", "x.com", "instagram.com", "reddit.com",
    "linkedin.com", "youtube.com", "tiktok.com", "medium.com", "stackoverflow.com",
    "pinterest.com", "facebook.com", "vimeo.com", "soundcloud.com", "twitch.tv",
    "behance.net", "dribbble.com", "producthunt.com", "kickstarter.com",
    "patreon.com", "flickr.com", "deviantart.com", "keybase.io", "about.me",
    "gravatar.com",
]
WHEN = ["person", "*"]


async def run(target: str, http) -> dict:
    t0 = now_ms()
    findings = []
    raw = {}
    # Derive a username candidate from target
    handle = target.strip().lower().replace(" ", "")
    handle = re.sub(r"[^a-z0-9_-]", "", handle)
    if not handle:
        return {"ok": False, "findings": [], "raw": {}, "elapsed_ms": 0,
                "investigator": NAME, "investigator_id": "social_recon"}

    PROBES = [
        ("GitHub", f"https://github.com/{handle}"),
        ("Twitter/X", f"https://twitter.com/{handle}"),
        ("Instagram", f"https://www.instagram.com/{handle}/"),
        ("Reddit", f"https://www.reddit.com/user/{handle}"),
        ("LinkedIn", f"https://www.linkedin.com/in/{handle}"),
        ("YouTube", f"https://www.youtube.com/@{handle}"),
        ("TikTok", f"https://www.tiktok.com/@{handle}"),
        ("Medium", f"https://medium.com/@{handle}"),
        ("StackOverflow", f"https://stackoverflow.com/users/{handle}"),
        ("Pinterest", f"https://www.pinterest.com/{handle}/"),
        ("ProductHunt", f"https://www.producthunt.com/@{handle}"),
        ("Patreon", f"https://www.patreon.com/{handle}"),
        ("Behance", f"https://www.behance.net/{handle}"),
        ("Dribbble", f"https://dribbble.com/{handle}"),
        ("Keybase", f"https://keybase.io/{handle}"),
        ("Gravatar", f"https://gravatar.com/{handle}"),
        ("About.me", f"https://about.me/{handle}"),
        ("DeviantArt", f"https://www.deviantart.com/{handle}"),
        ("SoundCloud", f"https://soundcloud.com/{handle}"),
        ("Twitch", f"https://www.twitch.tv/{handle}"),
        ("Vimeo", f"https://vimeo.com/{handle}"),
        ("Flickr", f"https://www.flickr.com/people/{handle}/"),
    ]
    import asyncio
    sem = asyncio.Semaphore(8)

    async def probe(label, url):
        async with sem:
            status = await head(http, url, timeout=5)
            raw[label] = status
            if status and 200 <= status < 400:
                return {"label": f"✓ {label}", "value": "found", "url": url}
            return None

    coros = [probe(l, u) for l, u in PROBES]
    results = await asyncio.gather(*coros, return_exceptions=True)
    for r in results:
        if isinstance(r, dict):
            findings.append(r)

    summary = f"{len(findings)} of {len(PROBES)} platforms returned a profile page for '{handle}'"
    findings.insert(0, {"label": "Sweep summary", "value": summary})

    return {"ok": True, "findings": findings, "raw": raw,
            "elapsed_ms": now_ms() - t0,
            "investigator": NAME, "investigator_id": "social_recon"}
