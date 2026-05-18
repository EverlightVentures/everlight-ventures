"""
public_records -- the detective-grade public-records mine.

Pulls REAL data (not just links) from:
  - CourtListener.com -- federal + state court records, opinions, dockets
  - Find-A-Grave / Legacy.com -- obituaries + death records
  - OpenCorporates -- business filings + officer history
  - News archives (Google News + Bing News for the target's name)
  - SEC EDGAR for public-company affiliations

Each finding includes the actual extracted text snippet so the operator can
read what we know about the person, not just where to go look.

Legal scope (state-by-state checked by legal_state.py):
  - Court records: PUBLIC under common-law access (Nixon v. Warner)
  - Obituaries / death records: PUBLIC (newspaper archives, vital records)
  - Business filings: PUBLIC (SoS, OpenCorporates)
  - NEVER touched here: DMV (DPPA-protected), credit, medical, FBI ICR
"""
from __future__ import annotations

import re
from urllib.parse import quote

from ._common import fetch, now_ms

NAME = "Public Records (deep mine)"
DOMAINS = [
    "courtlistener.com", "www.courtlistener.com",
    "findagrave.com", "www.findagrave.com",
    "legacy.com", "www.legacy.com",
    "api.opencorporates.com", "opencorporates.com",
    "efts.sec.gov", "sec.gov",
    "news.google.com", "bing.com",
]
WHEN = ["person", "company", "*"]


def _strip_html(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s or "")).strip()


async def _courtlistener(target: str, http) -> list[dict]:
    """CourtListener has a free JSON API. Returns recent dockets + opinions."""
    findings = []
    q = quote(target)
    # Docket search
    url = f"https://www.courtlistener.com/api/rest/v3/search/?q={q}&type=r&order_by=dateFiled+desc"
    status, body, err = await fetch(http, url, timeout=10)
    if status == 200 and body:
        try:
            import json as _json
            data = _json.loads(body)
            for hit in data.get("results", [])[:5]:
                court = hit.get("court", "")
                docket = hit.get("docketNumber", "")
                case_name = hit.get("caseName", "")
                date = hit.get("dateFiled", "")[:10]
                snippet = _strip_html(hit.get("snippet", ""))[:240]
                findings.append({
                    "label": f"Court docket · {court}",
                    "value": f"{case_name} ({docket}, {date}) -- {snippet}".strip(),
                    "url": f"https://www.courtlistener.com{hit.get('absolute_url','')}",
                })
        except (ValueError, AttributeError):
            pass

    # Opinion search (legal authorship / appearances)
    url = f"https://www.courtlistener.com/api/rest/v3/search/?q={q}&type=o&order_by=dateFiled+desc"
    status, body, err = await fetch(http, url, timeout=10)
    if status == 200 and body:
        try:
            import json as _json
            data = _json.loads(body)
            for hit in data.get("results", [])[:3]:
                findings.append({
                    "label": f"Court opinion · {hit.get('court','')}",
                    "value": f"{hit.get('caseName','')} ({hit.get('dateFiled','')[:10]})",
                    "url": f"https://www.courtlistener.com{hit.get('absolute_url','')}",
                })
        except (ValueError, AttributeError):
            pass
    return findings


async def _opencorporates(target: str, http) -> list[dict]:
    """OpenCorporates free-tier API. Real company filings."""
    findings = []
    url = f"https://api.opencorporates.com/v0.4/companies/search?q={quote(target)}&per_page=8"
    status, body, err = await fetch(http, url, timeout=10)
    if status == 200 and body:
        try:
            import json as _json
            data = _json.loads(body)
            for hit in data.get("results", {}).get("companies", [])[:6]:
                co = hit.get("company", {})
                jur = co.get("jurisdiction_code", "?")
                status_str = co.get("current_status") or co.get("company_type", "")
                addr = co.get("registered_address_in_full", "") or ""
                findings.append({
                    "label": f"Business filing · {jur.upper()}",
                    "value": (f"{co.get('name','')} · {status_str} · "
                              f"incorporated {co.get('incorporation_date','?')}"
                              f"{(' · ' + addr[:80]) if addr else ''}"),
                    "url": co.get("opencorporates_url", ""),
                })
        except (ValueError, AttributeError):
            pass

    # Officers search -- if target is a person, find boards/directorships
    url = f"https://api.opencorporates.com/v0.4/officers/search?q={quote(target)}&per_page=6"
    status, body, err = await fetch(http, url, timeout=10)
    if status == 200 and body:
        try:
            import json as _json
            data = _json.loads(body)
            for hit in data.get("results", {}).get("officers", [])[:5]:
                off = hit.get("officer", {})
                findings.append({
                    "label": f"Officer/director role",
                    "value": f"{off.get('name','')} -- {off.get('position','officer')} at "
                             f"{off.get('company',{}).get('name','?')}",
                    "url": off.get("opencorporates_url", ""),
                })
        except (ValueError, AttributeError):
            pass
    return findings


async def _findagrave(target: str, http) -> list[dict]:
    """Find-A-Grave -- public death records. Catches life events for family research."""
    findings = []
    url = f"https://www.findagrave.com/memorial/search?firstname={quote(target.split()[0] if ' ' in target else target)}&lastname={quote(target.split()[-1] if ' ' in target else '')}&birthyear=&deathyear="
    status, body, err = await fetch(http, url, timeout=10)
    if status == 200 and body:
        # Snip the first 3 memorial cards
        for m in re.finditer(
            r'class="memorial-item"[^>]*>.*?<a[^>]+href="([^"]+)"[^>]*>([^<]+)</a>.*?'
            r'<span[^>]+class="birth"[^>]*>([^<]+)</span>.*?<span[^>]+class="death"[^>]*>([^<]+)</span>',
            body, re.S
        ):
            findings.append({
                "label": "Death record (Find-A-Grave)",
                "value": f"{m.group(2).strip()} -- born {m.group(3).strip()}, died {m.group(4).strip()}",
                "url": "https://www.findagrave.com" + m.group(1),
            })
            if len(findings) >= 3:
                break
    return findings


async def _news_archive(target: str, http) -> list[dict]:
    """Google News + Bing News -- 'in the news' mentions. Captures profile + life events."""
    findings = []
    # Google News HTML (rss feed is most reliable)
    rss_url = f"https://news.google.com/rss/search?q={quote(target)}&hl=en-US&gl=US&ceid=US:en"
    status, body, err = await fetch(http, rss_url, timeout=10)
    if status == 200 and body:
        for m in re.finditer(r"<item>\s*<title>([^<]+)</title>\s*<link>([^<]+)</link>", body[:50000])[:5] if False else \
                  list(re.finditer(r"<item>\s*<title>([^<]+)</title>\s*<link>([^<]+)</link>", body[:50000]))[:5]:
            title = m.group(1).strip()
            link = m.group(2).strip()
            findings.append({
                "label": "News mention",
                "value": title[:240],
                "url": link,
            })
    return findings


async def run(target: str, http) -> dict:
    t0 = now_ms()
    findings: list = []
    raw: dict = {}

    # Run all four extractors sequentially (under shared httpx client, parallel within each)
    for fn, key in [(_courtlistener, "courtlistener"),
                     (_opencorporates, "opencorporates"),
                     (_findagrave, "findagrave"),
                     (_news_archive, "news_archive")]:
        try:
            sub = await fn(target, http)
            raw[key] = len(sub)
            findings.extend(sub)
        except Exception as e:
            raw[key] = f"err:{str(e)[:80]}"

    return {
        "ok": len(findings) > 0,
        "findings": findings,
        "raw": raw,
        "elapsed_ms": now_ms() - t0,
        "investigator": NAME,
        "investigator_id": "public_records",
    }
