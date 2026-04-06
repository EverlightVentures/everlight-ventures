"""
Rex Distress Finder -- Daily scout for distressed properties across all 5 legal markets.

Unlike generic ATTOM high-equity pulls, this scout actively searches for properties
with REAL distress signals: code violations, pre-foreclosure, tax delinquency,
probate, divorce settlements, expired listings, and vacant/condemned properties.

These leads score HIGH on the lead scorer because they have actual distress signals
and motivated sellers -- not just high equity with no reason to sell.

Target markets (NO North Carolina -- requires broker license):
  - Atlanta, GA (Fulton County)
  - Dallas, TX (Dallas County)
  - Cleveland, OH (Cuyahoga County)
  - St. Louis, MO (St. Louis City)
  - Jacksonville, FL (Duval County)

Pipeline per market:
  1. Run 7 Perplexity queries for different distress types
  2. Parse results for addresses + owner names
  3. Set lead_type based on which query found them
  4. Skip trace owners for email via Perplexity
  5. Import to leads_db.json with enrichment data pre-filled

Cron (5 AM PT = 13:00 UTC):
  0 13 * * * cd /mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Broker_OS/wholesale_agent && python3 rex_distress_finder.py

Uses:
  PERPLEXITY_API_KEY  -- distress research + skip tracing
"""

import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

logging.basicConfig(
    level=logging.INFO,
    format="[Rex DistressFinder %(asctime)s] %(message)s",
    datefmt="%H:%M",
)
log = logging.getLogger("rex_distress_finder")

AGENT_DIR = Path(__file__).parent
LEADS_DB = AGENT_DIR / "leads_db.json"
SCOUT_LOG = AGENT_DIR / "pipeline" / "distress_finder_log.jsonl"
SCOUT_LOG.parent.mkdir(parents=True, exist_ok=True)

PERPLEXITY_API_KEY = os.environ.get("PERPLEXITY_API_KEY", "")

TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")
CURRENT_YEAR = datetime.now(timezone.utc).year


# ---------------------------------------------------------------------------
# TARGET MARKETS -- NO North Carolina
# ---------------------------------------------------------------------------

TARGET_MARKETS = [
    {
        "city": "Atlanta",
        "state": "GA",
        "county": "Fulton County",
        "fips": "13121",
    },
    {
        "city": "Dallas",
        "state": "TX",
        "county": "Dallas County",
        "fips": "48113",
    },
    {
        "city": "Cleveland",
        "state": "OH",
        "county": "Cuyahoga County",
        "fips": "39035",
    },
    {
        "city": "St. Louis",
        "state": "MO",
        "county": "St. Louis City",
        "fips": "29510",
    },
    {
        "city": "Jacksonville",
        "state": "FL",
        "county": "Duval County",
        "fips": "12031",
    },
]


# ---------------------------------------------------------------------------
# DISTRESS QUERY DEFINITIONS
# ---------------------------------------------------------------------------

DISTRESS_QUERIES = [
    {
        "label": "code_violation",
        "lead_type": "code_violation",
        "query_template": (
            "Properties with open code violations in {city} {state} {year_prev} {year_curr}. "
            "Include property address and owner name if available. "
            "Search municipal code enforcement records, building inspections, "
            "condemned properties. Focus on residential properties."
        ),
    },
    {
        "label": "pre_foreclosure",
        "lead_type": "pre_foreclosure",
        "query_template": (
            "Pre-foreclosure properties in {city} {state} with lis pendens filings "
            "{year_prev} {year_curr}. Include property address and owner name. "
            "Search county recorder, court records, foreclosure listings."
        ),
    },
    {
        "label": "tax_delinquent",
        "lead_type": "tax_lien",
        "query_template": (
            "Tax delinquent properties in {county} {state} with 2 or more years "
            "of unpaid property taxes. Include property address and owner name. "
            "Search county tax collector delinquent lists."
        ),
    },
    {
        "label": "probate",
        "lead_type": "probate",
        "query_template": (
            "Probate real estate filings in {county} {state} {year_prev} {year_curr}. "
            "Include property address and estate/heir name if available. "
            "Search probate court records, estate filings with real property."
        ),
    },
    {
        "label": "divorce",
        "lead_type": "divorce",
        "query_template": (
            "Divorce property settlements in {county} {state} {year_prev} {year_curr}. "
            "Include property address and party names if available. "
            "Search family court records, property division filings."
        ),
    },
    {
        "label": "expired_listing",
        "lead_type": "expired_listing",
        "query_template": (
            "Expired real estate listings in {city} {state} that were withdrawn "
            "or delisted in the last 90 days. Include property address, listing "
            "price, and days on market if available. Search Zillow, Realtor.com, Redfin."
        ),
    },
    {
        "label": "vacant",
        "lead_type": "vacant",
        "query_template": (
            "Vacant or abandoned residential properties in {city} {state}. "
            "Include property address and owner name if available. "
            "Search boarded, condemned, and vacant property registries. "
            "Focus on properties that appear unoccupied."
        ),
    },
]


# ---------------------------------------------------------------------------
# PERPLEXITY API
# ---------------------------------------------------------------------------

def perplexity_search(query: str, system_prompt: str = "", max_tokens: int = 1500) -> str:
    """Query Perplexity API and return response text."""
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
            return resp.json().get("choices", [{}])[0].get("message", {}).get("content", "").strip()
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
# RESULT PARSING
# ---------------------------------------------------------------------------

def _safe_float(val) -> float:
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        cleaned = re.sub(r"[^\d.]", "", val)
        try:
            return float(cleaned) if cleaned else 0.0
        except ValueError:
            return 0.0
    return 0.0


def parse_properties_from_response(text: str, market: dict, distress_type: str) -> list:
    """
    Parse property records from Perplexity response.
    Handles JSON arrays and freeform text with addresses.
    Returns list of partial lead dicts.
    """
    if not text:
        return []

    properties = []

    # Attempt 1: Parse as JSON array
    try:
        json_match = re.search(r"\[[\s\S]*?\]", text)
        if json_match:
            parsed = json.loads(json_match.group())
            if isinstance(parsed, list):
                for item in parsed:
                    if isinstance(item, dict) and item.get("address"):
                        properties.append({
                            "address": str(item.get("address", "")).strip().upper(),
                            "owner_name": str(item.get("owner_name", item.get("owner", ""))).strip(),
                            "listing_price": _safe_float(item.get("listing_price", item.get("price", 0))),
                            "days_on_market": int(item.get("days_on_market", 0) or 0),
                            "amount_owed": _safe_float(item.get("amount_owed", 0)),
                        })
                if properties:
                    return properties
    except (json.JSONDecodeError, AttributeError, TypeError, ValueError):
        pass

    # Attempt 2: Parse freeform text with address patterns
    address_pattern = re.compile(
        r"(\d+\s+[A-Za-z0-9\s\.]+(?:St|Ave|Rd|Dr|Blvd|Ln|Way|Ct|Pl|Ter|Cir|Pkwy)\.?)",
        re.IGNORECASE,
    )

    for match in address_pattern.finditer(text):
        addr = match.group(1).strip().upper()
        if addr and len(addr) > 5:
            # Try to find owner name near the address
            context = text[max(0, match.start() - 50):match.end() + 100]
            owner_match = re.search(
                r"(?:owner|owned by|name)[:\s]+([A-Za-z\s\.]+)",
                context,
                re.IGNORECASE,
            )
            owner = owner_match.group(1).strip() if owner_match else ""

            properties.append({
                "address": addr,
                "owner_name": owner,
                "listing_price": 0,
                "days_on_market": 0,
                "amount_owed": 0,
            })

    return properties[:20]  # Cap at 20 per query


# ---------------------------------------------------------------------------
# SKIP TRACING
# ---------------------------------------------------------------------------

def skip_trace_owner(owner_name: str, city: str, state: str) -> dict:
    """Use Perplexity to find email address for a property owner."""
    if not owner_name or len(owner_name) < 3:
        return {}

    query = (
        f"Find the email address for {owner_name} in {city}, {state}. "
        f"Search public records, white pages, people search sites, "
        f"LinkedIn, and business registrations."
    )

    system_prompt = (
        "You are a skip tracing assistant. Find the person's email address "
        "from public records. Return a JSON object with keys: email (string or null), "
        "phone (string or null), confidence (string: high/medium/low). "
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
                "email": parsed.get("email") or "",
                "phone": parsed.get("phone") or "",
                "confidence": parsed.get("confidence", "low"),
            }
    except (json.JSONDecodeError, AttributeError):
        pass

    # Fallback: extract email/phone from text
    email_match = re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", content)
    phone_match = re.search(r"\(?(\d{3})\)?[\s.-]?(\d{3})[\s.-]?(\d{4})", content)

    return {
        "email": email_match.group(0) if email_match else "",
        "phone": (
            f"({phone_match.group(1)}) {phone_match.group(2)}-{phone_match.group(3)}"
            if phone_match else ""
        ),
        "confidence": "low",
    }


# ---------------------------------------------------------------------------
# LEAD DATABASE
# ---------------------------------------------------------------------------

def load_leads() -> list:
    """Load existing leads from the shared database."""
    if LEADS_DB.exists():
        try:
            return json.loads(LEADS_DB.read_text())
        except json.JSONDecodeError:
            log.error("leads_db.json is corrupted -- starting fresh")
            return []
    return []


def save_leads(leads: list):
    """Save leads back to the shared database."""
    LEADS_DB.write_text(json.dumps(leads, indent=2, default=str))


def import_distress_leads(new_leads: list) -> int:
    """Import distressed leads into the shared leads database. Dedup by address."""
    existing = load_leads()
    existing_addrs = {lead.get("address", "").upper() for lead in existing}

    added = 0
    for lead in new_leads:
        addr = lead.get("address", "").upper()
        if addr and addr not in existing_addrs:
            existing.append(lead)
            existing_addrs.add(addr)
            added += 1

    if added > 0:
        save_leads(existing)

    return added


# ---------------------------------------------------------------------------
# SCOUT PIPELINE
# ---------------------------------------------------------------------------

def search_distress_type(market: dict, distress_query: dict) -> list:
    """
    Run a single distress query for a market and return parsed property records.
    """
    query = distress_query["query_template"].format(
        city=market["city"],
        state=market["state"],
        county=market["county"],
        year_prev=CURRENT_YEAR - 1,
        year_curr=CURRENT_YEAR,
    )

    system_prompt = (
        "You are a real estate research assistant finding distressed properties "
        "from public records. For each property found, return a JSON array of "
        "objects with keys: address (string), owner_name (string or empty), "
        "listing_price (number or 0), days_on_market (number or 0), "
        "amount_owed (number or 0). "
        "Only include residential properties. If no specific properties found, "
        "return an empty array []. Return ONLY the JSON array."
    )

    label = distress_query["label"]
    log.info(f"    [{label}] Searching {market['city']}, {market['state']}...")

    content = perplexity_search(query, system_prompt)
    if not content:
        return []

    properties = parse_properties_from_response(content, market, label)
    log.info(f"    [{label}] Found {len(properties)} properties")
    return properties


def scout_market(market: dict) -> list:
    """
    Run the full distress finder pipeline for one market.
    Executes all 7 distress queries, deduplicates, skip traces, and builds leads.
    """
    log.info(f"  Scouting {market['city']}, {market['state']}...")

    all_properties = []
    property_types = {}  # address -> lead_type

    for dq in DISTRESS_QUERIES:
        try:
            properties = search_distress_type(market, dq)
            for prop in properties:
                addr = prop.get("address", "").upper()
                if addr and addr not in property_types:
                    property_types[addr] = dq["lead_type"]
                    prop["_lead_type"] = dq["lead_type"]
                    prop["_label"] = dq["label"]
                    all_properties.append(prop)
                elif addr in property_types:
                    # Property found in multiple distress queries -- bonus signal
                    # Keep the first (higher priority) type
                    pass
        except Exception as e:
            log.error(f"    [{dq['label']}] Failed: {e}")

        # Rate limit between queries -- Perplexity throttles aggressively
        time.sleep(3)

    log.info(f"  Total unique properties found: {len(all_properties)}")

    if not all_properties:
        return []

    # Build lead records
    leads = []
    for prop in all_properties:
        address = prop.get("address", "")
        if not address or len(address) < 5:
            continue

        # Build the full address with city/state
        full_address = address
        if market["city"].upper() not in full_address.upper():
            full_address = f"{address}, {market['city'].upper()}, {market['state']} "

        lead_type = prop.get("_lead_type", "high_equity")

        lead = {
            "address": full_address.strip().upper(),
            "city": market["city"].upper(),
            "state": market["state"].upper(),
            "zip_code": "",
            "county": market["county"],
            "owner_name": prop.get("owner_name", ""),
            "owner_email": "",
            "owner_phone": "",
            "estimated_arv": 0,
            "beds": 0,
            "baths": 0,
            "sqft": 0,
            "year_built": 0,
            "lead_type": lead_type,
            "source": "distress_finder",
            "market": market["city"].lower(),
            "status": "new",
            "outreach_count": 0,
            "sequence_step": 0,
            "last_outreach": "",
            "created_at": TODAY,
            "motivation_score": 0,
            # Pre-fill enrichment flags based on distress type
            "detected_distress": lead_type,
            "distress_signals": [prop.get("_label", "")],
            "enriched": False,  # Full ATTOM enrichment happens in Belfort sequence
        }

        # Store any extra data from the search
        if prop.get("listing_price"):
            lead["listing_price_found"] = prop["listing_price"]
        if prop.get("days_on_market"):
            lead["days_on_market_found"] = prop["days_on_market"]
        if prop.get("amount_owed"):
            lead["tax_amount_owed"] = prop["amount_owed"]

        leads.append(lead)

    # Skip trace owners for contact info
    traced_count = 0
    for lead in leads:
        owner = lead.get("owner_name", "")
        if owner and len(owner) > 3:
            trace_result = skip_trace_owner(owner, market["city"], market["state"])
            if trace_result.get("email"):
                lead["owner_email"] = trace_result["email"]
                traced_count += 1
            if trace_result.get("phone"):
                lead["owner_phone"] = trace_result["phone"]
            time.sleep(2)

    log.info(f"  Skip traced {traced_count}/{len(leads)} owners with email")

    # Calculate motivation scores
    for lead in leads:
        score = _calculate_distress_score(lead)
        lead["motivation_score"] = min(score, 100)
        if score >= 70:
            lead["motivation_tier"] = "HOT"
        elif score >= 40:
            lead["motivation_tier"] = "WARM"
        else:
            lead["motivation_tier"] = "COLD"

    return leads


def _calculate_distress_score(lead: dict) -> int:
    """Calculate motivation score based on distress type and available data."""
    lead_type = lead.get("lead_type", "")

    # Base scores by distress type (higher = more motivated seller)
    type_scores = {
        "pre_foreclosure": 45,
        "probate": 40,
        "code_violation": 35,
        "tax_lien": 30,
        "vacant": 30,
        "divorce": 25,
        "expired_listing": 20,
        "absentee": 15,
    }

    score = 20 + type_scores.get(lead_type, 0)

    # Bonus: has contact info (actionable lead)
    if lead.get("owner_email"):
        score += 10
    if lead.get("owner_phone"):
        score += 5

    # Bonus: has owner name (can personalize)
    if lead.get("owner_name") and len(lead.get("owner_name", "")) > 3:
        score += 5

    # Bonus: tax amount owed is significant
    tax_owed = lead.get("tax_amount_owed", 0)
    if tax_owed and tax_owed >= 10000:
        score += 10
    elif tax_owed and tax_owed >= 5000:
        score += 5

    return score


def log_scout_run(market: str, queries_run: int, properties_found: int,
                  imported: int, traced: int):
    """Append a line to the scout log for tracking."""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "scout_type": "distress_finder",
        "market": market,
        "queries_run": queries_run,
        "properties_found": properties_found,
        "imported_new": imported,
        "skip_traced": traced,
    }
    with open(SCOUT_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def run_distress_finder():
    """Run the full distress finder across all target markets."""
    log.info("=" * 60)
    log.info("Rex Distress Finder -- starting daily run")
    log.info(f"Date: {TODAY}")
    log.info(f"Target markets: {len(TARGET_MARKETS)}")
    log.info(f"Distress queries per market: {len(DISTRESS_QUERIES)}")
    log.info("=" * 60)

    total_found = 0
    total_imported = 0
    total_hot = 0

    for market in TARGET_MARKETS:
        try:
            leads = scout_market(market)
            total_found += len(leads)

            # Import into shared database
            imported = import_distress_leads(leads)
            total_imported += imported

            hot = sum(1 for l in leads if l.get("motivation_tier") == "HOT")
            total_hot += hot

            traced = sum(1 for l in leads if l.get("owner_email"))

            log.info(
                f"  {market['city']}: {len(leads)} found, "
                f"{imported} imported, {hot} HOT, {traced} with email"
            )

            log_scout_run(
                market=f"{market['city']}, {market['state']}",
                queries_run=len(DISTRESS_QUERIES),
                properties_found=len(leads),
                imported=imported,
                traced=traced,
            )

        except Exception as e:
            log.error(f"Failed to scout {market['city']}: {e}")
            continue

        # Rate limit between markets
        time.sleep(5)

    # Summary
    all_leads = load_leads()
    distress_count = sum(
        1 for l in all_leads
        if l.get("source") == "distress_finder"
    )

    log.info("")
    log.info("=" * 60)
    log.info("Rex Distress Finder -- daily run complete")
    log.info(f"  Properties found today: {total_found}")
    log.info(f"  New leads imported: {total_imported}")
    log.info(f"  HOT leads: {total_hot}")
    log.info(f"  Distress finder leads in DB: {distress_count}")
    log.info(f"  Total leads in DB: {len(all_leads)}")
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
                        f"*Rex Distress Finder -- {TODAY}*\n"
                        f"Scouted {len(TARGET_MARKETS)} markets x "
                        f"{len(DISTRESS_QUERIES)} distress types\n"
                        f"Properties found: {total_found}\n"
                        f"New leads imported: {total_imported}\n"
                        f"HOT leads: {total_hot}\n"
                        f"Distress leads in DB: {distress_count}\n"
                        f"Total leads in DB: {len(all_leads)}"
                    ),
                },
                timeout=10,
            )
        except Exception:
            pass

    return total_found


if __name__ == "__main__":
    run_distress_finder()
