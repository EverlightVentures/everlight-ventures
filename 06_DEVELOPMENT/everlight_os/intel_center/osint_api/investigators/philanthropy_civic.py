"""
philanthropy_civic -- public political + philanthropic signals.

Pulls from:
  - FEC.gov individual contribution search (federal campaign donations -- public by law)
  - OpenSecrets.org (consolidated FEC + state data)
  - ProPublica Nonprofit Explorer (990 filings, board members, donors above threshold)
  - GoFundMe public campaigns (organizer + public donors when shown)
  - USPTO patent assignee search (innovation + technical interests)

Each finding is heavy signal: donors care about causes, board members are
proud of their work, patents reveal technical depth + employer history.
"""
from __future__ import annotations

import asyncio
import re
from urllib.parse import quote

from ._common import fetch, now_ms

NAME = "Civic + Philanthropy (deep mine)"
DOMAINS = [
    "fec.gov", "api.open.fec.gov", "www.opensecrets.org",
    "projects.propublica.org", "www.guidestar.org",
    "www.gofundme.com", "patft.uspto.gov", "patents.google.com",
]
WHEN = ["person", "company", "*"]


async def _fec(target: str, http) -> list[dict]:
    """FEC individual contributor search (no API key needed for basic search)."""
    findings = []
    # FEC OpenAPI without auth has rate limits but returns JSON
    url = (f"https://api.open.fec.gov/v1/schedules/schedule_a/"
           f"?contributor_name={quote(target)}"
           f"&sort=-contribution_receipt_date&per_page=10&api_key=DEMO_KEY")
    status, body, err = await fetch(http, url, timeout=10)
    if status == 200 and body:
        try:
            import json as _json
            data = _json.loads(body)
            for r in data.get("results", [])[:6]:
                committee = r.get("committee", {}).get("name", "")
                amt = r.get("contribution_receipt_amount", 0)
                date = r.get("contribution_receipt_date", "")[:10]
                state = r.get("contributor_state", "")
                findings.append({
                    "label": "FEC contribution",
                    "value": f"${amt:,.0f} to {committee} ({date}{', '+state if state else ''})",
                    "url": f"https://www.fec.gov/data/receipts/?contributor_name={quote(target)}",
                })
        except (ValueError, AttributeError):
            pass
    return findings


async def _propublica_nonprofit(target: str, http) -> list[dict]:
    """ProPublica Nonprofit Explorer -- if target is a company / 501c3."""
    findings = []
    url = f"https://projects.propublica.org/nonprofits/api/v2/search.json?q={quote(target)}"
    status, body, err = await fetch(http, url, timeout=10)
    if status == 200 and body:
        try:
            import json as _json
            data = _json.loads(body)
            for org in data.get("organizations", [])[:4]:
                state = org.get("state", "")
                ein = org.get("ein", "")
                rev = org.get("income_amt", 0)
                findings.append({
                    "label": "Nonprofit 501c3",
                    "value": f"{org.get('name','')} -- {state}, EIN {ein}, revenue ${rev:,}",
                    "url": f"https://projects.propublica.org/nonprofits/organizations/{ein}",
                })
        except (ValueError, AttributeError):
            pass
    return findings


async def _gofundme(target: str, http) -> list[dict]:
    """GoFundMe public campaign search."""
    findings = []
    url = f"https://www.gofundme.com/s?q={quote(target)}"
    status, body, err = await fetch(http, url, timeout=10)
    if status == 200 and body:
        for m in list(re.finditer(
            r'<a[^>]+href="(/f/[^"]+)"[^>]*>\s*<[^>]+>\s*<h\d[^>]*>([^<]+)</h\d>',
            body[:60000]))[:3]:
            findings.append({
                "label": "GoFundMe campaign",
                "value": m.group(2).strip()[:200],
                "url": "https://www.gofundme.com" + m.group(1),
            })
    return findings


async def _patents(target: str, http) -> list[dict]:
    """Google Patents inventor search."""
    findings = []
    url = f"https://patents.google.com/?inventor={quote(target)}&oq={quote(target)}"
    status, body, err = await fetch(http, url, timeout=10)
    if status == 200 and body:
        for m in list(re.finditer(
            r'<state-modifier[^>]+data-result="patent/([A-Z]+\d+[A-Z]?\d*)/[^"]*"[^>]*>\s*<a[^>]*>([^<]{10,200})</a>',
            body[:60000]))[:3]:
            patent_id = m.group(1)
            title = m.group(2).strip()
            findings.append({
                "label": "Patent filing",
                "value": f"{patent_id} -- {title}",
                "url": f"https://patents.google.com/patent/{patent_id}",
            })
    return findings


async def run(target: str, http) -> dict:
    t0 = now_ms()
    findings = []
    raw = {}

    async def run_one(name, fn):
        try:
            return name, await fn(target, http)
        except Exception as e:
            return name, []

    probes = [("fec", _fec), ("nonprofit", _propublica_nonprofit),
               ("gofundme", _gofundme), ("patents", _patents)]
    results = await asyncio.gather(*(run_one(n, f) for n, f in probes), return_exceptions=True)
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
        "investigator_id": "philanthropy_civic",
    }
