"""
reverse_whois -- find other domains registered by the same name/email.

High-signal for LLC-owned wholesale targets: if an LLC owner registered
20 commercial domains over 10 years, that owner is a sophisticated
operator and pitch language shifts to investor-to-investor.

Free path: ViewDNS reverse-WHOIS scrape (limited, ToS-grey but
public-record-adjacent), Whoisology snippets. Per network-first doctrine,
we attempt the live API and fall back to URL generation if rate-limited.

Paid path: WHOXY API (~$0.005/lookup) -- if WHOXY_API_KEY in env, prefer
this; cleaner data, no scrape.

Legal scope:
  - WHOIS data is PUBLIC (court precedent + ICANN policy)
  - Reverse-WHOIS aggregators republish the same public records
  - No login walls, no breach data
  - In-scope per legal_scope.IN_SCOPE["court_records"] adjacency
"""
from __future__ import annotations

import os
import re
from urllib.parse import quote

from ._common import fetch, now_ms

NAME = "Reverse WHOIS"
DOMAINS = ["api.whoxy.com", "viewdns.info", "www.viewdns.info", "whoisology.com"]
WHEN = ["person", "company", "email"]


async def _whoxy_api(target: str, http) -> list[dict]:
    """Paid path: WHOXY reverse WHOIS API. Clean JSON, ~5k results per query."""
    key = os.environ.get("WHOXY_API_KEY", "")
    if not key:
        return []
    # WHOXY supports name + email + company; auto-detect
    if "@" in target:
        url = f"https://api.whoxy.com/?key={key}&reverse=whois&email={quote(target)}"
    else:
        url = f"https://api.whoxy.com/?key={key}&reverse=whois&name={quote(target)}"
    status, body, _ = await fetch(http, url, timeout=12)
    if status != 200 or not body:
        return []
    try:
        import json as _json
        data = _json.loads(body)
        out: list[dict] = []
        for d in data.get("search_result", [])[:20]:
            out.append({
                "domain": d.get("domain_name", ""),
                "registered": d.get("create_date", ""),
                "expires": d.get("expiry_date", ""),
                "registrar": d.get("domain_registrar", {}).get("registrar_name", "")
                              if isinstance(d.get("domain_registrar"), dict)
                              else d.get("domain_registrar", ""),
            })
        return out
    except (ValueError, KeyError):
        return []


async def _viewdns_scrape(target: str, http) -> list[dict]:
    """Free path: ViewDNS reverse-WHOIS scrape. Limited rows per query but
    no key required. ToS-grey -- they expect humans, not bots, but the data
    is public record. Set polite UA."""
    # ViewDNS supports name lookups; use full target string
    url = f"https://viewdns.info/reversewhois/?q={quote(target)}"
    status, body, _ = await fetch(http, url, timeout=12)
    if status != 200 or not body:
        return []

    # Scrape the result table: rows are <td>domain</td><td>created</td><td>registrar</td>
    rows = re.findall(
        r"<tr><td>([a-zA-Z0-9.\-]+)</td><td>(\d{4}-\d{2}-\d{2})</td><td>([^<]+)</td></tr>",
        body
    )
    return [
        {"domain": d, "registered": dt, "expires": "", "registrar": reg.strip()[:60]}
        for d, dt, reg in rows[:20]
    ]


async def run(target: str, http) -> dict:
    t0 = now_ms()
    findings: list = []
    raw: dict = {"source": None, "domains_found": 0}

    target = (target or "").strip()
    if not target:
        return {"ok": False, "findings": [], "raw": raw,
                "elapsed_ms": now_ms() - t0,
                "investigator": NAME, "investigator_id": "reverse_whois"}

    # Try paid API first if key present
    results = await _whoxy_api(target, http)
    if results:
        raw["source"] = "whoxy_api"
    else:
        # Fall back to free scrape
        results = await _viewdns_scrape(target, http)
        raw["source"] = "viewdns_scrape" if results else "no_results"

    raw["domains_found"] = len(results)

    if not results:
        # Even on zero results, return the search URL so an operator can browse
        findings.append({
            "label": "Reverse WHOIS search (no automated hits)",
            "value": f"open browser to check '{target}'",
            "url": f"https://viewdns.info/reversewhois/?q={quote(target)}",
        })
        return {"ok": False, "findings": findings, "raw": raw,
                "elapsed_ms": now_ms() - t0,
                "investigator": NAME, "investigator_id": "reverse_whois"}

    for r in results[:15]:
        bits = [r["domain"]]
        if r.get("registered"):
            bits.append(f"reg {r['registered']}")
        if r.get("registrar"):
            bits.append(r["registrar"][:30])
        findings.append({
            "label": "Domain registered",
            "value": " · ".join(bits),
            "url": f"https://www.whois.com/whois/{r['domain']}",
        })

    return {
        "ok": True,
        "findings": findings,
        "raw": raw,
        "elapsed_ms": now_ms() - t0,
        "investigator": NAME,
        "investigator_id": "reverse_whois",
    }
