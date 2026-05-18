"""DuckDuckGo + Bing site-search dorks (no API key needed)."""
from urllib.parse import quote
from ._common import fetch, now_ms
import re

NAME = "Search Dorks"
DOMAINS = ["html.duckduckgo.com", "duckduckgo.com", "bing.com"]
WHEN = ["*"]

DORKS = [
    '"{q}"',
    '{q} site:linkedin.com',
    '{q} site:github.com',
    '{q} site:reddit.com',
    '{q} filetype:pdf',
    '{q} contact email',
]


async def run(target: str, http) -> dict:
    t0 = now_ms()
    findings = []
    raw = {}

    for dork in DORKS:
        q = dork.format(q=target)
        url = f"https://html.duckduckgo.com/html/?q={quote(q)}"
        status, text, err = await fetch(http, url, timeout=8)
        raw[dork] = {"status": status, "len": len(text)}
        if status == 200 and text:
            matches = list(re.finditer(
                r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>([^<]+)</a>',
                text[:60000]))[:2]
            for m in matches:
                href, title = m.group(1), m.group(2).strip()
                # DDG wraps URLs in /l/?uddg=
                if "uddg=" in href:
                    from urllib.parse import unquote, parse_qs, urlparse
                    qs = parse_qs(urlparse(href).query)
                    href = unquote(qs.get("uddg", [""])[0])
                findings.append({
                    "label": dork.replace("{q}", "·")[:35],
                    "value": title[:120],
                    "url": href,
                })

    return {"ok": len(findings) > 0,
            "findings": findings[:18], "raw": raw,
            "elapsed_ms": now_ms() - t0,
            "investigator": NAME, "investigator_id": "google_dorks"}
