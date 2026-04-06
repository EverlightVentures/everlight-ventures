"""
Rex Zillow Keyword Scraper -- finds distressed property listings via Perplexity.

Searches for Zillow listings with motivated-seller keywords:
  as-is, fixer upper, handyman special, investor special, TLC, cash only,
  needs work, must sell, estate sale, motivated seller, price reduced.

Also targets:
  - FSBO (For Sale By Owner) -- no agent = more flexible on price
  - Properties with multiple price reductions
  - Listings mentioning "investor", "wholesale", "ARV"

Target markets (NO North Carolina -- requires broker license):
  - Atlanta, GA (Fulton County)
  - Dallas, TX (Dallas County)
  - Cleveland, OH (Cuyahoga County)
  - St. Louis, MO (St. Louis City)
  - Jacksonville, FL (Duval County)

Pipeline:
  1. Search Perplexity for distressed Zillow listings per market
  2. Parse addresses, prices, and description keywords
  3. Assign lead_type based on keyword match
  4. Skip trace owners via Perplexity
  5. Import leads into leads_db.json

Cron (6:30 AM PT = 14:30 UTC):
  30 14 * * * cd /mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Broker_OS/wholesale_agent && python3 rex_zillow_keyword_scraper.py

Uses:
  PERPLEXITY_API_KEY  -- listing search + skip tracing
"""

import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

logging.basicConfig(
    level=logging.INFO,
    format="[Rex ZillowScraper %(asctime)s] %(message)s",
    datefmt="%H:%M",
)
log = logging.getLogger("rex_zillow_keyword_scraper")

AGENT_DIR = Path(__file__).parent
LEADS_DB = AGENT_DIR / "leads_db.json"
SCOUT_LOG = AGENT_DIR / "pipeline" / "zillow_keyword_log.jsonl"
SCOUT_LOG.parent.mkdir(parents=True, exist_ok=True)

PERPLEXITY_API_KEY = os.environ.get("PERPLEXITY_API_KEY", "")

TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# TARGET MARKETS -- NO North Carolina
# ---------------------------------------------------------------------------

TARGET_MARKETS = [
    {"city": "Atlanta", "state": "GA", "market_key": "atlanta"},
    {"city": "Dallas", "state": "TX", "market_key": "dallas"},
    {"city": "Cleveland", "state": "OH", "market_key": "cleveland"},
    {"city": "St. Louis", "state": "MO", "market_key": "st_louis"},
    {"city": "Jacksonville", "state": "FL", "market_key": "jacksonville"},
]

# Keywords that indicate motivated sellers
DISTRESS_KEYWORDS = [
    "as-is", "fixer upper", "handyman special", "investor special",
    "TLC", "cash only", "needs work", "must sell", "estate sale",
    "motivated seller", "price reduced",
]

# FSBO and investor-specific keywords
INVESTOR_KEYWORDS = [
    "FSBO", "for sale by owner", "investor", "wholesale", "ARV",
    "below market", "price drop", "multiple price reductions",
]

# Keyword -> lead_type mapping
KEYWORD_TO_LEAD_TYPE = {
    "as-is": "fixer",
    "fixer upper": "fixer",
    "fixer": "fixer",
    "handyman special": "fixer",
    "needs work": "fixer",
    "TLC": "fixer",
    "investor special": "fixer",
    "cash only": "distressed",
    "must sell": "distressed",
    "motivated seller": "distressed",
    "price reduced": "price_reduced",
    "price drop": "price_reduced",
    "multiple price reductions": "price_reduced",
    "estate sale": "estate_sale",
    "FSBO": "fsbo",
    "for sale by owner": "fsbo",
    "investor": "investor_target",
    "wholesale": "investor_target",
    "ARV": "investor_target",
    "below market": "below_market",
    "code violation": "code_violation",
}


# ---------------------------------------------------------------------------
# PERPLEXITY API -- search helper
# ---------------------------------------------------------------------------

def perplexity_search(query: str, system_prompt: str = "", max_tokens: int = 1500) -> str:
    """
    Query Perplexity API and return the text content of the response.
    Returns empty string on failure.
    """
    if not PERPLEXITY_API_KEY:
        log.warning("No PERPLEXITY_API_KEY set -- cannot search")
        return ""

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": query})

    try:
        resp = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers={
                "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "sonar",
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": 0.1,
            },
            timeout=45,
        )

        if resp.status_code == 200:
            content = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
            return content.strip()
        elif resp.status_code == 429:
            log.warning("Perplexity rate limited -- waiting 15s")
            time.sleep(15)
            return ""
        else:
            log.warning(f"Perplexity returned {resp.status_code}: {resp.text[:200]}")
            return ""

    except requests.RequestException as e:
        log.error(f"Perplexity request failed: {e}")
        return ""


# ---------------------------------------------------------------------------
# LISTING SEARCH -- find distressed listings via Perplexity
# ---------------------------------------------------------------------------

def search_distressed_listings(market: dict) -> list[dict]:
    """
    Search Perplexity for Zillow listings with distressed keywords in a market.
    Returns a list of parsed listing dicts.
    """
    city = market["city"]
    state = market["state"]

    keywords_str = ", ".join(DISTRESS_KEYWORDS)
    query = (
        f"Find Zillow listings in {city} {state} with these keywords in the "
        f"description: {keywords_str}. Include property address, price, and "
        f"listing description snippet. Focus on single family homes. "
        f"Search zillow.com for current active listings."
    )

    system_prompt = (
        "You are a real estate listing researcher. Search Zillow for distressed "
        "property listings. For each listing found, return a JSON array of objects "
        "with keys: address (string), price (number), description (string -- "
        "include the relevant keyword phrases from the listing), keywords_matched "
        "(list of strings -- which distress keywords appear in the listing). "
        "Return ONLY the JSON array. If no listings found, return []."
    )

    log.info(f"  Searching distressed listings in {city}, {state}...")
    content = perplexity_search(query, system_prompt)

    listings = _parse_listings(content, market)
    return listings


def search_fsbo_listings(market: dict) -> list[dict]:
    """
    Search for FSBO and investor-targeted listings.
    Returns a list of parsed listing dicts.
    """
    city = market["city"]
    state = market["state"]

    query = (
        f"Find For Sale By Owner (FSBO) listings in {city} {state} on Zillow "
        f"and FSBO.com. Also find listings mentioning 'investor', 'wholesale', "
        f"or 'ARV'. Include property address, price, and listing description. "
        f"Also find properties with multiple price reductions in the last 60 days."
    )

    system_prompt = (
        "You are a real estate listing researcher. Find FSBO and investor-targeted "
        "listings. For each listing, return a JSON array of objects with keys: "
        "address (string), price (number), description (string), keywords_matched "
        "(list of strings), is_fsbo (boolean). Return ONLY the JSON array. "
        "If no listings found, return []."
    )

    log.info(f"  Searching FSBO/investor listings in {city}, {state}...")
    content = perplexity_search(query, system_prompt)

    listings = _parse_listings(content, market)
    # Tag FSBO listings
    for listing in listings:
        if listing.get("is_fsbo") or "fsbo" in str(listing.get("keywords_matched", [])).lower():
            listing["lead_type"] = "fsbo"
    return listings


def search_price_reduced_listings(market: dict) -> list[dict]:
    """
    Search for properties with significant price reductions.
    Returns a list of parsed listing dicts.
    """
    city = market["city"]
    state = market["state"]

    query = (
        f"Find Zillow listings in {city} {state} with significant price reductions "
        f"or multiple price drops in the last 90 days. Focus on single family homes "
        f"where the price has been reduced by 10% or more from original listing. "
        f"Include address, current price, original price, and percent reduced."
    )

    system_prompt = (
        "You are a real estate listing researcher. Find properties with major price "
        "reductions. For each listing, return a JSON array of objects with keys: "
        "address (string), price (number), original_price (number), description "
        "(string), percent_reduced (number). Return ONLY the JSON array. "
        "If no listings found, return []."
    )

    log.info(f"  Searching price-reduced listings in {city}, {state}...")
    content = perplexity_search(query, system_prompt)

    listings = _parse_listings(content, market)
    for listing in listings:
        listing["lead_type"] = "price_reduced"
    return listings


def _parse_listings(text: str, market: dict) -> list[dict]:
    """
    Parse listing records from Perplexity response text.
    Handles both JSON arrays and freeform text.
    """
    if not text:
        return []

    listings = []

    # Attempt 1: Parse as JSON array
    try:
        json_match = re.search(r"\[[\s\S]*?\]", text)
        if json_match:
            parsed = json.loads(json_match.group())
            if isinstance(parsed, list):
                for item in parsed:
                    if isinstance(item, dict) and item.get("address"):
                        listing = _normalize_listing(item, market)
                        if listing:
                            listings.append(listing)
                if listings:
                    return listings
    except (json.JSONDecodeError, AttributeError, TypeError):
        pass

    # Attempt 2: Extract addresses and prices from freeform text
    # Pattern: address followed by price
    entries = re.findall(
        r"(\d+\s+[A-Za-z0-9\s\.]+(?:St|Ave|Rd|Dr|Blvd|Ln|Way|Ct|Pl|Ter|Cir)\.?)"
        r"[^$]*?\$\s*([\d,]+)",
        text,
        re.IGNORECASE,
    )
    for addr, price_str in entries:
        clean_price = re.sub(r"[^\d]", "", price_str)
        listing = {
            "address": addr.strip().upper(),
            "city": market["city"].upper(),
            "state": market["state"].upper(),
            "asking_price": int(clean_price) if clean_price else 0,
            "description": "",
            "keywords_matched": [],
            "lead_type": "distressed",
            "source": "zillow_keyword_scraper",
            "market_key": market["market_key"],
        }
        listings.append(listing)

    return listings[:20]  # cap at 20 per search


def _normalize_listing(item: dict, market: dict) -> dict:
    """Normalize a parsed listing into a standard lead format."""
    address = str(item.get("address", "")).strip().upper()
    if not address or len(address) < 5:
        return {}

    # Determine price
    price = 0
    for key in ("price", "asking_price", "list_price"):
        val = item.get(key, 0)
        if val:
            if isinstance(val, str):
                cleaned = re.sub(r"[^\d]", "", val)
                price = int(cleaned) if cleaned else 0
            else:
                price = int(val)
            break

    # Determine lead type from matched keywords
    keywords = item.get("keywords_matched", [])
    if isinstance(keywords, str):
        keywords = [keywords]
    description = str(item.get("description", "")).lower()

    lead_type = "distressed"  # default
    for kw in keywords:
        kw_lower = kw.lower().strip()
        if kw_lower in KEYWORD_TO_LEAD_TYPE:
            lead_type = KEYWORD_TO_LEAD_TYPE[kw_lower]
            break

    # Also scan description for lead type hints
    if lead_type == "distressed":
        for kw, lt in KEYWORD_TO_LEAD_TYPE.items():
            if kw.lower() in description:
                lead_type = lt
                break

    return {
        "address": address,
        "city": market["city"].upper(),
        "state": market["state"].upper(),
        "asking_price": price,
        "description_snippet": str(item.get("description", ""))[:300],
        "keywords_matched": keywords,
        "lead_type": lead_type,
        "source": "zillow_keyword_scraper",
        "market_key": market["market_key"],
        "is_fsbo": bool(item.get("is_fsbo", False)),
        "original_price": int(item.get("original_price", 0) or 0),
        "percent_reduced": float(item.get("percent_reduced", 0) or 0),
    }


# ---------------------------------------------------------------------------
# SKIP TRACE -- find owner contact info via Perplexity
# ---------------------------------------------------------------------------

def skip_trace_owner(address: str, city: str, state: str) -> dict:
    """
    Use Perplexity to find the property owner and their contact info.
    Returns dict with owner_name, email, and phone if found.
    """
    query = (
        f"Who owns the property at {address}, {city}, {state}? "
        f"Find the owner's name, email address, and phone number from "
        f"public property records and people search sites."
    )

    system_prompt = (
        "You are a skip tracing assistant. Find the property owner from "
        "public records. Return a JSON object with keys: owner_name (string), "
        "email (string or null), phone (string or null). "
        "Return ONLY the JSON object."
    )

    content = perplexity_search(query, system_prompt, max_tokens=300)
    if not content:
        return {}

    try:
        json_match = re.search(r"\{[\s\S]*?\}", content)
        if json_match:
            parsed = json.loads(json_match.group())
            return {
                "owner_name": parsed.get("owner_name", "") or "",
                "email": parsed.get("email", "") or "",
                "phone": parsed.get("phone", "") or "",
            }
    except (json.JSONDecodeError, AttributeError):
        pass

    return {}


# ---------------------------------------------------------------------------
# LEAD DATABASE -- import into shared leads_db.json
# ---------------------------------------------------------------------------

def load_leads() -> list[dict]:
    """Load existing leads from the shared database."""
    if LEADS_DB.exists():
        try:
            return json.loads(LEADS_DB.read_text())
        except json.JSONDecodeError:
            log.error("leads_db.json is corrupted -- starting fresh")
            return []
    return []


def save_leads(leads: list[dict]):
    """Save leads back to the shared database."""
    LEADS_DB.write_text(json.dumps(leads, indent=2, default=str))


def import_zillow_leads(new_leads: list[dict]) -> int:
    """Import Zillow keyword leads into the shared leads database. Dedup by address."""
    existing = load_leads()
    existing_addrs = {lead.get("address", "").upper() for lead in existing}

    added = 0
    for lead in new_leads:
        addr = lead.get("address", "").upper()
        if addr and addr not in existing_addrs:
            # Convert to standard lead format
            std_lead = {
                "address": addr,
                "city": lead.get("city", ""),
                "state": lead.get("state", ""),
                "zip_code": lead.get("zip_code", ""),
                "owner_name": lead.get("owner_name", ""),
                "owner_email": lead.get("owner_email", ""),
                "owner_phone": lead.get("owner_phone", ""),
                "estimated_arv": lead.get("asking_price", 0),  # asking as proxy until enriched
                "beds": 0,
                "baths": 0,
                "sqft": 0,
                "year_built": 0,
                "lead_type": lead.get("lead_type", "distressed"),
                "source": "zillow_keyword_scraper",
                "market": lead.get("market_key", ""),
                "status": "new",
                "outreach_count": 0,
                "last_outreach": "",
                "sequence_step": 0,
                "created_at": TODAY,
                "motivation_score": 0,
                "asking_price": lead.get("asking_price", 0),
                "description_snippet": lead.get("description_snippet", ""),
                "keywords_matched": lead.get("keywords_matched", []),
                "is_fsbo": lead.get("is_fsbo", False),
            }
            existing.append(std_lead)
            existing_addrs.add(addr)
            added += 1

    if added > 0:
        save_leads(existing)

    return added


def log_scout_run(market: str, distressed: int, fsbo: int, reduced: int, imported: int):
    """Append a line to the scout log for tracking."""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "scout_type": "zillow_keyword",
        "market": market,
        "distressed_found": distressed,
        "fsbo_found": fsbo,
        "price_reduced_found": reduced,
        "imported_new": imported,
    }
    with open(SCOUT_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")


# ---------------------------------------------------------------------------
# MOTIVATION SCORING
# ---------------------------------------------------------------------------

def score_zillow_lead(lead: dict) -> int:
    """Calculate motivation score for a Zillow keyword lead."""
    score = 20  # base

    lead_type = lead.get("lead_type", "")

    # Lead type scoring
    type_scores = {
        "code_violation": 35,
        "distressed": 30,
        "estate_sale": 30,
        "fixer": 25,
        "fsbo": 20,
        "below_market": 20,
        "price_reduced": 15,
        "investor_target": 15,
    }
    score += type_scores.get(lead_type, 10)

    # FSBO bonus -- no agent means seller is more flexible
    if lead.get("is_fsbo"):
        score += 10

    # Price reduction bonus
    pct_reduced = lead.get("percent_reduced", 0)
    if pct_reduced >= 20:
        score += 15
    elif pct_reduced >= 10:
        score += 10

    # Keyword density -- more distress keywords = more motivated
    keywords = lead.get("keywords_matched", [])
    if len(keywords) >= 3:
        score += 10
    elif len(keywords) >= 2:
        score += 5

    # Contactable bonus
    if lead.get("owner_email"):
        score += 5

    return min(score, 100)


# ---------------------------------------------------------------------------
# MAIN SCOUT PIPELINE
# ---------------------------------------------------------------------------

def scout_market(market: dict) -> list[dict]:
    """Run the full Zillow keyword scout pipeline for one market."""
    city = market["city"]
    state = market["state"]
    log.info(f"Scouting {city}, {state}...")

    all_listings = []

    # Search 1: Distressed keywords
    distressed = search_distressed_listings(market)
    log.info(f"  Distressed listings: {len(distressed)}")
    all_listings.extend(distressed)
    time.sleep(3)

    # Search 2: FSBO and investor listings
    fsbo = search_fsbo_listings(market)
    log.info(f"  FSBO/investor listings: {len(fsbo)}")
    all_listings.extend(fsbo)
    time.sleep(3)

    # Search 3: Price-reduced listings
    reduced = search_price_reduced_listings(market)
    log.info(f"  Price-reduced listings: {len(reduced)}")
    all_listings.extend(reduced)
    time.sleep(2)

    if not all_listings:
        log_scout_run(f"{city}, {state}", 0, 0, 0, 0)
        return []

    # Dedup within this batch by address
    seen_addrs = set()
    unique_listings = []
    for listing in all_listings:
        addr = listing.get("address", "").upper()
        if addr and addr not in seen_addrs:
            seen_addrs.add(addr)
            unique_listings.append(listing)

    log.info(f"  Unique listings after dedup: {len(unique_listings)}")

    # Skip trace owners for contact info (limit to top 10 per market)
    traced = 0
    for listing in unique_listings[:10]:
        if not listing.get("owner_name"):
            trace_result = skip_trace_owner(
                listing.get("address", ""),
                city,
                state,
            )
            if trace_result:
                listing["owner_name"] = trace_result.get("owner_name", "")
                listing["owner_email"] = trace_result.get("email", "")
                listing["owner_phone"] = trace_result.get("phone", "")
                if trace_result.get("email"):
                    traced += 1
            time.sleep(2)  # Perplexity rate limit

    log.info(f"  Skip traced {traced} owners")

    # Score all leads
    for listing in unique_listings:
        listing["motivation_score"] = score_zillow_lead(listing)
        score = listing["motivation_score"]
        if score >= 70:
            listing["motivation_tier"] = "HOT"
        elif score >= 40:
            listing["motivation_tier"] = "WARM"
        else:
            listing["motivation_tier"] = "COLD"

    # Sort by score descending
    unique_listings.sort(key=lambda x: x.get("motivation_score", 0), reverse=True)

    # Import into leads database
    imported = import_zillow_leads(unique_listings)
    log.info(f"  Imported {imported} new leads (skipped {len(unique_listings) - imported} duplicates)")

    # Log the run
    log_scout_run(
        market=f"{city}, {state}",
        distressed=len(distressed),
        fsbo=len(fsbo),
        reduced=len(reduced),
        imported=imported,
    )

    return unique_listings


def run_zillow_keyword_scraper():
    """Run the full Zillow keyword scraper across all target markets."""
    log.info("=" * 60)
    log.info("Rex Zillow Keyword Scraper -- starting daily run")
    log.info(f"Date: {TODAY}")
    log.info(f"Target markets: {len(TARGET_MARKETS)}")
    log.info(f"Distress keywords: {len(DISTRESS_KEYWORDS)}")
    log.info(f"Investor keywords: {len(INVESTOR_KEYWORDS)}")
    log.info("=" * 60)

    total_found = 0
    all_market_leads = []

    for market in TARGET_MARKETS:
        try:
            leads = scout_market(market)
            total_found += len(leads)
            all_market_leads.extend(leads)
        except Exception as e:
            log.error(f"Failed to scout {market['city']}: {e}")
            continue

        # Rate limit between markets
        time.sleep(5)

    # Summary stats
    all_leads = load_leads()
    zillow_count = sum(1 for l in all_leads if l.get("source") == "zillow_keyword_scraper")
    total_count = len(all_leads)
    hot_count = sum(1 for l in all_market_leads if l.get("motivation_tier") == "HOT")
    fsbo_count = sum(1 for l in all_market_leads if l.get("is_fsbo"))

    log.info("")
    log.info("=" * 60)
    log.info("Rex Zillow Keyword Scraper -- daily run complete")
    log.info(f"  Listings found today: {total_found}")
    log.info(f"  HOT leads: {hot_count}")
    log.info(f"  FSBO leads: {fsbo_count}")
    log.info(f"  Zillow keyword leads in database: {zillow_count}")
    log.info(f"  Total leads in database: {total_count}")
    log.info("=" * 60)

    # Post summary to Slack
    slack_token = os.environ.get("SLACK_BOT_TOKEN", "")
    if slack_token:
        try:
            requests.post(
                "https://slack.com/api/chat.postMessage",
                headers={
                    "Authorization": f"Bearer {slack_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "channel": "C0ANLLV8JAC",
                    "text": (
                        f"*Rex Zillow Keyword Scraper -- {TODAY}*\n"
                        f"Scouted {len(TARGET_MARKETS)} markets\n"
                        f"Listings found: {total_found}\n"
                        f"HOT leads: {hot_count}\n"
                        f"FSBO leads: {fsbo_count}\n"
                        f"Zillow keyword leads in DB: {zillow_count}\n"
                        f"Total leads in DB: {total_count}"
                    ),
                },
                timeout=10,
            )
        except Exception:
            pass

    return total_found


if __name__ == "__main__":
    run_zillow_keyword_scraper()
