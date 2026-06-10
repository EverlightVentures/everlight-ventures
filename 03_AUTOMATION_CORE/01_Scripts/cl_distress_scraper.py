"""
cl_distress_scraper.py -- Craigslist distressed-seller scraper.

Per Rex Blackwell's lead-supply recommendation: ATL + DFW housing-by-owner with
8 distressed keywords. Phone-side residential IP (CL 403's datacenter IPs).

Captures from listing body text:
- Direct email addresses (FSBO posters often paste despite CL policy)
- Phone numbers (very common)
- Address (when present)
- Asking price (when present)
- Lead-type tag (derived from matching keyword)

Writes to wholesale_agent/leads_db.json with status='new'. Filter scoring runs
on the fresh batch before next rex_sdr fire.

Run from phone: ~16 search queries * 5-15 listings each = 80-240 listings/cycle.
At Rex's optimistic 60-70% capture, that's 50-170 emails. Realistic capture
(no relay-email scraping) is closer to 5-15% direct emails + 30-50% phones.

Compliance:
- Justine's auto-block applies post-scrape (LLC/agent/business filtering)
- merge_field_gate fires at outreach time
- DNC ledger checked at outreach time
- This script just collects; it doesn't send.
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from bs4 import BeautifulSoup


KEYWORDS = [
    "must sell", "estate sale", "as-is", "cash only",
    "behind on payments", "tax sale", "motivated seller",
    "divorce", "must move", "vacant", "fire damage",
    "handyman special", "estate", "probate", "fixer",
]

METROS = [
    ("atlanta",   "GA"),
    ("dallas",    "TX"),
    ("fortworth", "TX"),
    ("memphis",   "TN"),  # Added 2026-04-28 -- Chris @ Mid South Homebuyers buy-box scout
]

# Per-buyer zip filters. If a buyer is targeted, leads outside their zip list
# are deprioritized at scrape time. Memphis only matters if zip in Chris's list.
CHRIS_MSH_MEMPHIS_ZIPS = {
    "38127","38128","38134","38117","38111","38141","38115","38118",
    "38116","38109","38104","38122","38107","38114","38106",
}

CL_SEARCH_URL = "https://{metro}.craigslist.org/search/reo?query={q}&srchType=A"

USER_AGENT = "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36"

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_RE = re.compile(r"\(?\b([2-9][0-9]{2})\)?[\s\-.]+([2-9][0-9]{2})[\s\-.]+([0-9]{4})\b")
PRICE_RE = re.compile(r"\$\s?(\d{1,3}(?:[,\.]\d{3})+|\d{4,})")
ADDRESS_RE = re.compile(r"\b(\d{1,6}\s+[A-Za-z0-9 .'-]+(?:Rd|Road|St|Street|Ave|Avenue|Blvd|Boulevard|Dr|Drive|Ct|Court|Ln|Lane|Way|Pl|Place|Pkwy|Parkway|Cir|Circle|Trail|Trl))\b", re.IGNORECASE)

LEAD_TYPE_BY_KEYWORD = {
    "must sell": "motivated_seller",
    "estate sale": "probate",
    "as-is": "distressed",
    "cash only": "distressed",
    "behind on payments": "pre_foreclosure",
    "tax sale": "tax_lien",
    "motivated seller": "motivated_seller",
    "divorce": "divorce",
    "must move": "motivated_seller",
    "vacant": "vacant",
    "fire damage": "distressed",
    "handyman special": "distressed",
    "estate": "probate",
    "probate": "probate",
    "fixer": "distressed",
}

# Skip listings that are obviously commercial / agent / wholesaler-competitor
SKIP_TITLE_SIGNALS = (
    "investor opportunity",  # competitor
    "real estate license",
    "broker",
    "we buy",  # wholesaler competitor
    "i buy",
    "off market properties",  # competitor
    "off-market",
    "wholesale",
    "seeking buyer",
    "seeking investor",
    "find your dream",
    "fha approved",
    "for rent",
    "rent to own",
    "lease purchase",
)

OUT_DIR = Path("/mnt/sdcard/AA_MY_DRIVE/_logs/cl_scrape")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def fetch(url: str, timeout: int = 15) -> str:
    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  fetch error {url}: {e}", file=sys.stderr)
        return ""


def parse_search(html: str, metro: str) -> list[dict]:
    """Returns list of {title, url, price?, location?}."""
    soup = BeautifulSoup(html, "lxml")
    listings = soup.find_all("li", class_="cl-static-search-result")
    out = []
    for li in listings:
        title_el = li.find("div", class_="title")
        link_el = li.find("a", href=True)
        if not (title_el and link_el):
            continue
        title = title_el.get_text(strip=True)
        url = link_el.get("href")
        if not url.startswith("http"):
            url = f"https://{metro}.craigslist.org{url}"
        price_el = li.find("div", class_="price")
        price = price_el.get_text(strip=True) if price_el else ""
        loc_el = li.find("div", class_="location")
        loc = loc_el.get_text(strip=True) if loc_el else ""
        out.append({"title": title, "url": url, "price": price, "location": loc})
    return out


def parse_listing(html: str) -> dict:
    """Returns extracted contact + property fields from a listing detail page."""
    soup = BeautifulSoup(html, "lxml")
    # Posting body
    body_el = soup.find("section", id="postingbody")
    body = body_el.get_text("\n", strip=True) if body_el else ""

    # Title
    title_el = soup.find("span", id="titletextonly")
    if not title_el:
        title_el = soup.find("h1", class_="postingtitle")
    title = title_el.get_text(strip=True) if title_el else ""

    # Map address from postingmaps if present
    map_el = soup.find("div", id="map")
    map_addr = ""
    if map_el and map_el.get("data-latitude") and map_el.get("data-longitude"):
        # CL doesn't expose street address from map; just lat/lon
        pass

    # Posting infos (postID, posted timestamp)
    info_el = soup.find("div", class_="postinginfos")
    info_text = info_el.get_text("|", strip=True) if info_el else ""

    # Extract emails from body
    emails = list(set(EMAIL_RE.findall(body)))
    # Filter obvious noise (CL system emails, plus invalid)
    emails = [e for e in emails if not e.endswith("@craigslist.org")]

    # Extract phones (deduped)
    phones_raw = PHONE_RE.findall(body)
    phones = list(set(f"({a}) {b}-{c}" for (a, b, c) in phones_raw))

    # Try to extract address from body
    addresses = ADDRESS_RE.findall(body)
    address = addresses[0] if addresses else ""

    # Asking price
    price_match = PRICE_RE.search(body)
    asking_price_raw = price_match.group(0) if price_match else ""

    return {
        "title": title,
        "body_excerpt": body[:600],
        "emails": emails,
        "phones": phones,
        "address": address,
        "asking_price_raw": asking_price_raw,
        "info": info_text,
    }


def looks_like_business_or_competitor(title: str, body: str) -> bool:
    t = (title or "").lower()
    b = (body or "").lower()[:1500]
    return any(s in t or s in b for s in SKIP_TITLE_SIGNALS)


def parse_price(raw: str) -> float:
    if not raw:
        return 0.0
    digits = re.sub(r"[^\d]", "", raw)
    try:
        return float(digits)
    except ValueError:
        return 0.0


def scrape_metro(metro: str, state: str, keywords: list[str], max_listings_per_kw: int = 6) -> list[dict]:
    """Walk N keywords for one metro, fetch listing details, return new leads."""
    all_listings: dict[str, dict] = {}  # url -> listing dict
    for kw in keywords:
        url = CL_SEARCH_URL.format(metro=metro, q=urllib.parse.quote_plus(kw))
        print(f"  [{metro}] keyword '{kw}' ...")
        html = fetch(url)
        if not html:
            continue
        results = parse_search(html, metro)
        print(f"    found {len(results)} search results")
        for r in results[:max_listings_per_kw]:
            if r["url"] in all_listings:
                continue
            r["matched_keyword"] = kw
            r["lead_type"] = LEAD_TYPE_BY_KEYWORD.get(kw.lower(), "distressed")
            all_listings[r["url"]] = r
        time.sleep(1.5)  # courtesy delay between keyword searches

    print(f"  [{metro}] {len(all_listings)} unique listings to fetch detail for")

    detailed = []
    for url, l in all_listings.items():
        html = fetch(url)
        if not html:
            continue
        parsed = parse_listing(html)
        # Skip business/competitor listings
        if looks_like_business_or_competitor(parsed["title"] or l["title"], parsed["body_excerpt"]):
            continue
        # Build canonical lead row
        lead = {
            "address": parsed["address"] or l.get("location", ""),
            "city": "",  # to extract from address later if possible
            "state": state,
            "lead_type": l["lead_type"],
            "source": f"cl_{l['matched_keyword']}",
            "source_url": url,
            "status": "new",
            "outreach_count": 0,
            "sequence_step": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "title": parsed["title"] or l["title"],
            "body_excerpt": parsed["body_excerpt"],
            "owner_email": parsed["emails"][0] if parsed["emails"] else "",
            "owner_phone": parsed["phones"][0] if parsed["phones"] else "",
            "asking_price": parse_price(parsed["asking_price_raw"] or l.get("price", "")),
            "days_on_market": 0,  # CL doesn't expose; would need posting-date math
            "owner_name": "",  # CL doesn't expose owner name on listings
            "captured_emails_count": len(parsed["emails"]),
            "captured_phones_count": len(parsed["phones"]),
        }
        detailed.append(lead)
        time.sleep(1.0)  # courtesy delay between detail fetches

    print(f"  [{metro}] {len(detailed)} listings parsed (after skip filter)")
    return detailed


def merge_into_leads_db(new_leads: list[dict]) -> dict:
    """Append new_leads to leads_db.json, dedupe by url + by address."""
    db_path = Path("/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Broker_OS/wholesale_agent/leads_db.json")
    existing = json.loads(db_path.read_text()) if db_path.exists() else []
    existing_urls = {l.get("source_url") for l in existing if l.get("source_url")}
    existing_addrs = {(l.get("address") or "").upper() for l in existing if l.get("address")}
    existing_emails = {(l.get("owner_email") or "").lower() for l in existing if l.get("owner_email")}
    existing_phones = {re.sub(r"\D", "", l.get("owner_phone") or "") for l in existing if l.get("owner_phone")}

    added = 0
    skipped = 0
    for lead in new_leads:
        if lead.get("source_url") and lead["source_url"] in existing_urls:
            skipped += 1
            continue
        if lead.get("address") and lead["address"].upper() in existing_addrs:
            skipped += 1
            continue
        if lead.get("owner_email") and lead["owner_email"].lower() in existing_emails:
            skipped += 1
            continue
        ph_digits = re.sub(r"\D", "", lead.get("owner_phone") or "")
        if ph_digits and ph_digits in existing_phones:
            skipped += 1
            continue
        existing.append(lead)
        existing_urls.add(lead.get("source_url"))
        if lead.get("address"):
            existing_addrs.add(lead["address"].upper())
        if lead.get("owner_email"):
            existing_emails.add(lead["owner_email"].lower())
        if ph_digits:
            existing_phones.add(ph_digits)
        added += 1

    db_path.write_text(json.dumps(existing, indent=2, default=str))
    return {"added": added, "skipped": skipped, "total_now": len(existing)}


def write_audit(metro_results: dict, merge_stats: dict) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    audit_path = OUT_DIR / f"cl_scrape_{ts}.json"
    payload = {
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "metros": {m: len(leads) for m, leads in metro_results.items()},
        "merge_stats": merge_stats,
        "lead_summary": {
            m: {
                "with_email": sum(1 for l in leads if l.get("owner_email")),
                "with_phone": sum(1 for l in leads if l.get("owner_phone")),
                "with_neither": sum(1 for l in leads if not l.get("owner_email") and not l.get("owner_phone")),
                "by_lead_type": {},
            }
            for m, leads in metro_results.items()
        },
    }
    for m, leads in metro_results.items():
        bt = {}
        for l in leads:
            lt = l.get("lead_type", "?")
            bt[lt] = bt.get(lt, 0) + 1
        payload["lead_summary"][m]["by_lead_type"] = bt
    audit_path.write_text(json.dumps(payload, indent=2))
    return audit_path


def main():
    """Run the full scrape: ATL + DFW (atlanta + dallas + fortworth) x N keywords."""
    print(f"=== CL distress scraper -- {datetime.now().isoformat()} ===")
    print(f"Metros: {[m for m, _ in METROS]}")
    print(f"Keywords ({len(KEYWORDS)}): {KEYWORDS}")
    print()

    metro_results = {}
    for metro, state in METROS:
        print(f"== {metro.upper()} ({state}) ==")
        leads = scrape_metro(metro, state, KEYWORDS, max_listings_per_kw=4)
        metro_results[metro] = leads
        print()

    # Flatten + merge
    all_leads = [l for leads in metro_results.values() for l in leads]
    merge_stats = merge_into_leads_db(all_leads)

    audit_path = write_audit(metro_results, merge_stats)

    print("=== SUMMARY ===")
    for metro, leads in metro_results.items():
        with_em = sum(1 for l in leads if l.get("owner_email"))
        with_ph = sum(1 for l in leads if l.get("owner_phone"))
        print(f"  {metro:12} {len(leads):3} leads parsed | {with_em:3} with email | {with_ph:3} with phone")
    print(f"  Total parsed: {sum(len(v) for v in metro_results.values())}")
    print(f"  Merged into leads_db: {merge_stats['added']} added, {merge_stats['skipped']} skipped (dedup)")
    print(f"  leads_db total now: {merge_stats['total_now']}")
    print(f"  Audit: {audit_path}")


if __name__ == "__main__":
    main()
