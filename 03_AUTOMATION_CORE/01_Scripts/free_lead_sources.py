"""free_lead_sources -- zero-cost property / owner discovery.

Sources (in order of typical yield):
    1. Zillow FSBO listings -- For Sale By Owner, highest motivation signal
       (contact info usually on the listing page or 1 click away)
    2. Craigslist "real estate by owner" -- regional boards, low volume,
       high motivation

Writes dedupe'd rows into the same leads_db.json format state_property_hunter
uses. Per-state CSVs get rewritten on the same schedule.

Usage:
    python3 free_lead_sources.py                     # all enabled sources + states
    python3 free_lead_sources.py --source zillow     # only Zillow FSBO
    python3 free_lead_sources.py --source craigslist # only Craigslist
    python3 free_lead_sources.py --state GA          # single-state sweep
    python3 free_lead_sources.py --dry-run
    python3 free_lead_sources.py --max-per-source 10 # small run
"""
from __future__ import annotations

import argparse
import json
import logging
import random
import re
import sys
import time
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote_plus, urlparse, urljoin

try:
    import httpx
except ImportError:
    print("ERR: httpx not installed"); sys.exit(1)
try:
    from bs4 import BeautifulSoup
except ImportError:
    print("ERR: beautifulsoup4 not installed"); sys.exit(1)

logging.basicConfig(level=logging.INFO, format="[free-src %(asctime)s] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("free_lead_sources")

ROOT = Path("/mnt/sdcard/AA_MY_DRIVE")
LEADS_DB = ROOT / "01_BUSINESSES" / "Everlight_Ventures" / "Broker_OS" / "wholesale_agent" / "leads_db.json"
PROSP = ROOT / "01_BUSINESSES" / "Everlight_Ventures" / "Wholesale" / "prospecting"

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
]

PHONE_RE = re.compile(r"\(?(\d{3})\)?[\s.\-]?(\d{3})[\s.\-]?(\d{4})")
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
PRICE_RE = re.compile(r"\$\s?([\d,]{4,})")


# ---------------------------------------------------------------------------
# Metro configs -- which cities to scrape per state
# ---------------------------------------------------------------------------

METRO_MAP: dict[str, list[dict]] = {
    "GA": [
        {"city": "Atlanta",   "zillow_slug": "atlanta-ga",   "cl_host": "atlanta"},
        {"city": "Augusta",   "zillow_slug": "augusta-ga",   "cl_host": "augusta"},
        {"city": "Savannah",  "zillow_slug": "savannah-ga",  "cl_host": "savannah"},
    ],
    "MO": [
        {"city": "St. Louis", "zillow_slug": "st-louis-mo",  "cl_host": "stlouis"},
        {"city": "Kansas City","zillow_slug": "kansas-city-mo","cl_host": "kansascity"},
    ],
    "FL": [
        {"city": "Jacksonville", "zillow_slug": "jacksonville-fl", "cl_host": "jacksonville"},
        {"city": "Orlando",      "zillow_slug": "orlando-fl",      "cl_host": "orlando"},
        {"city": "Tampa",        "zillow_slug": "tampa-fl",        "cl_host": "tampa"},
    ],
    "TX": [
        {"city": "Dallas",       "zillow_slug": "dallas-tx",       "cl_host": "dallas"},
        {"city": "Houston",      "zillow_slug": "houston-tx",      "cl_host": "houston"},
        {"city": "San Antonio",  "zillow_slug": "san-antonio-tx",  "cl_host": "sanantonio"},
        {"city": "Fort Worth",   "zillow_slug": "fort-worth-tx",   "cl_host": "fortworth"},
    ],
    "AZ": [
        {"city": "Phoenix",  "zillow_slug": "phoenix-az", "cl_host": "phoenix"},
        {"city": "Tucson",   "zillow_slug": "tucson-az",  "cl_host": "tucson"},
    ],
    "TN": [
        {"city": "Memphis",  "zillow_slug": "memphis-tn", "cl_host": "memphis"},
        {"city": "Nashville","zillow_slug": "nashville-tn","cl_host": "nashville"},
    ],
}


def _get(url: str, timeout: float = 12.0) -> str | None:
    h = {"User-Agent": random.choice(USER_AGENTS), "Accept-Language": "en-US,en;q=0.9"}
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True, headers=h) as c:
            r = c.get(url)
            if r.status_code >= 400:
                log.warning("  HTTP %s for %s", r.status_code, url)
                return None
            return r.text
    except Exception as e:
        log.warning("  fetch err for %s: %s", url, str(e)[:80])
        return None


# ---------------------------------------------------------------------------
# Zillow FSBO
# ---------------------------------------------------------------------------

def scrape_zillow_fsbo(city_slug: str, state: str, city: str, max_leads: int = 20) -> list[dict]:
    url = f"https://www.zillow.com/{city_slug}/fsbo/"
    html = _get(url)
    if not html:
        return []
    # Zillow injects structured JSON in a <script id="__NEXT_DATA__"> tag. Parse that if present.
    leads: list[dict] = []
    try:
        m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(\{.*?\})</script>', html, re.DOTALL)
        if m:
            data = json.loads(m.group(1))
            # Navigate into the search-results payload
            paths_to_try = [
                ("props", "pageProps", "searchPageState", "cat1", "searchResults", "listResults"),
                ("props", "pageProps", "componentProps", "searchResults", "listResults"),
                ("props", "pageProps", "initialData", "searchResults", "listResults"),
            ]
            results = []
            for path in paths_to_try:
                node = data
                try:
                    for p in path: node = node[p]
                    if isinstance(node, list):
                        results = node; break
                except (KeyError, TypeError):
                    continue
            for r in results[:max_leads]:
                addr = r.get("address") or r.get("streetAddress") or ""
                if not addr: continue
                leads.append({
                    "id": f"fsbo_zillow_{uuid.uuid4().hex[:10]}",
                    "address":       addr,
                    "city":          r.get("addressCity") or city,
                    "state":         r.get("addressState") or state,
                    "zip":           r.get("addressZipcode") or "",
                    "owner_name":    r.get("listing_sub_type", {}).get("is_FSBO") and "(FSBO owner)" or "",
                    "email":         "",
                    "phone":         "",
                    "estimated_arv": int(r.get("unformattedPrice") or r.get("price") or 0),
                    "beds":          r.get("beds") or "",
                    "baths":         r.get("baths") or "",
                    "sqft":          r.get("area") or "",
                    "year_built":    "",
                    "lead_type":     "fsbo_zillow",
                    "detected_distress": "fsbo",
                    "source":        f"zillow_fsbo:{city_slug}",
                    "status":        "new",
                    "listing_url":   f"https://www.zillow.com{r.get('detailUrl', '')}" if r.get("detailUrl") else "",
                    "created_at":    datetime.now(timezone.utc).isoformat(),
                })
    except Exception as e:
        log.warning("  zillow parse err: %s", e)
    # Fallback: regex addresses from HTML if JSON path didn't work
    if not leads:
        # Listing cards have the address in an <address> tag.
        for addr_tag in BeautifulSoup(html, "html.parser").find_all("address")[:max_leads]:
            a = addr_tag.get_text(strip=True)
            if not a or "," not in a: continue
            leads.append({
                "id":          f"fsbo_zillow_{uuid.uuid4().hex[:10]}",
                "address":     a.split(",")[0].strip(),
                "city":        city,
                "state":       state,
                "lead_type":   "fsbo_zillow",
                "detected_distress": "fsbo",
                "source":      f"zillow_fsbo:{city_slug}",
                "status":      "new",
                "created_at":  datetime.now(timezone.utc).isoformat(),
            })
    return leads


# ---------------------------------------------------------------------------
# Craigslist real-estate-by-owner
# ---------------------------------------------------------------------------

def scrape_craigslist_reo(cl_host: str, state: str, city: str, max_leads: int = 20) -> list[dict]:
    # Craigslist redirects /search/reo -> /search/rea?purveyor=owner
    url = f"https://{cl_host}.craigslist.org/search/rea?purveyor=owner"
    html = _get(url)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    leads: list[dict] = []
    # Current Craigslist markup uses <li class="cl-static-search-result">
    results = soup.select("li.cl-static-search-result, li.cl-search-result, li.result-row")
    for r in results[:max_leads]:
        title_el = (r.select_one("a.posting-title")
                    or r.select_one("a.cl-app-anchor")
                    or r.select_one("a.result-title")
                    or r.find("a"))
        price_el = (r.select_one(".priceinfo")
                    or r.select_one(".price")
                    or r.select_one(".result-price"))
        meta_el  = (r.select_one(".meta")
                    or r.select_one(".location")
                    or r.select_one(".result-hood"))
        title = title_el.get_text(strip=True) if title_el else ""
        href  = title_el.get("href", "") if title_el else ""
        if not title:
            # Title sometimes nested -- try the row's title attribute or div.title
            t = r.get("title") or (r.find("div", {"class": "title"}) or r.find("span", {"class": "title"}))
            if t:
                title = t.get_text(strip=True) if hasattr(t, "get_text") else t
        price = 0
        if price_el:
            m = PRICE_RE.search(price_el.get_text())
            if m: price = int(m.group(1).replace(",", ""))
        neighborhood = (meta_el.get_text(strip=True) if meta_el else "").strip(" ()")
        if not title:
            continue
        leads.append({
            "id":          f"fsbo_cl_{uuid.uuid4().hex[:10]}",
            "address":     title,
            "city":        neighborhood or city,
            "state":       state,
            "lead_type":   "fsbo_craigslist",
            "detected_distress": "fsbo",
            "estimated_arv": price,
            "source":      f"craigslist_reo:{cl_host}",
            "status":      "new",
            "listing_url": href,
            "created_at":  datetime.now(timezone.utc).isoformat(),
        })
    return leads


# ---------------------------------------------------------------------------
# Core runner
# ---------------------------------------------------------------------------

def _load_db() -> list[dict]:
    if not LEADS_DB.exists():
        return []
    return json.loads(LEADS_DB.read_text())


def _dedupe_key(lead: dict) -> str:
    return (
        (lead.get("address") or "").strip().lower()
        + "|"
        + (lead.get("city") or "").strip().lower()
        + "|"
        + (lead.get("state") or "").strip().upper()
    )


def run(sources: list[str], only_state: str | None,
        max_per_source: int, delay: float, dry_run: bool) -> dict:
    existing = _load_db()
    existing_keys = {_dedupe_key(l) for l in existing}

    per_source = {"zillow_fsbo": 0, "craigslist_reo": 0}
    new_leads: list[dict] = []
    per_state: Counter = Counter()

    states = [only_state.upper()] if only_state else list(METRO_MAP.keys())
    for st in states:
        cities = METRO_MAP.get(st, [])
        for m in cities:
            city, zslug, clhost = m["city"], m["zillow_slug"], m["cl_host"]
            if "zillow" in sources:
                log.info("Zillow FSBO %s / %s", st, city)
                batch = scrape_zillow_fsbo(zslug, st, city, max_leads=max_per_source)
                for l in batch:
                    if _dedupe_key(l) in existing_keys: continue
                    existing_keys.add(_dedupe_key(l))
                    new_leads.append(l)
                    per_source["zillow_fsbo"] += 1
                    per_state[st] += 1
                time.sleep(delay + random.uniform(0, delay * 0.4))
            if "craigslist" in sources:
                log.info("Craigslist REO %s / %s", st, city)
                batch = scrape_craigslist_reo(clhost, st, city, max_leads=max_per_source)
                for l in batch:
                    if _dedupe_key(l) in existing_keys: continue
                    existing_keys.add(_dedupe_key(l))
                    new_leads.append(l)
                    per_source["craigslist_reo"] += 1
                    per_state[st] += 1
                time.sleep(delay + random.uniform(0, delay * 0.4))

    if not dry_run and new_leads:
        existing.extend(new_leads)
        LEADS_DB.write_text(json.dumps(existing, indent=2, default=str))

    return {
        "new_total": len(new_leads),
        "per_source": dict(per_source),
        "per_state":  dict(per_state),
        "db_total":   len(existing) + (0 if dry_run else 0),  # existing already includes
        "dry_run":    dry_run,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=["zillow", "craigslist", "all"], default="all")
    ap.add_argument("--state", help="filter to one state (e.g. GA)")
    ap.add_argument("--max-per-source", type=int, default=20)
    ap.add_argument("--delay", type=float, default=4.0, help="seconds between city requests")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    sources = ["zillow", "craigslist"] if args.source == "all" else [args.source]
    s = run(sources=sources, only_state=args.state,
            max_per_source=args.max_per_source, delay=args.delay, dry_run=args.dry_run)
    print(json.dumps(s, indent=2))


if __name__ == "__main__":
    main()
