"""
Rex Tax Delinquency Scout -- finds properties with 2+ years unpaid taxes.

Tax delinquency lists are the #1 free lead source for wholesaling.
Properties with multi-year unpaid taxes = motivated sellers facing
tax foreclosure auctions. These owners will take pennies on the dollar
to avoid losing the property entirely.

Target markets (NO North Carolina -- requires broker license):
  - Fulton County GA (Atlanta)
  - Dallas County TX
  - Cuyahoga County OH (Cleveland)
  - St. Louis City MO
  - Duval County FL (Jacksonville)

Pipeline:
  1. Query Perplexity for current tax delinquency data per county
  2. Parse addresses and owner names from results
  3. Cross-reference with ATTOM API for property details
  4. Skip trace owners via Perplexity for email addresses
  5. Import leads into leads_db.json with lead_type="tax_lien"

Cron (6 AM PT = 14:00 UTC):
  0 14 * * * cd /mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Broker_OS/wholesale_agent && python3 rex_tax_delinquency_scout.py

Uses:
  ATTOM_API_KEY       -- property data enrichment
  PERPLEXITY_API_KEY  -- tax delinquency research + skip tracing
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
    format="[Rex TaxScout %(asctime)s] %(message)s",
    datefmt="%H:%M",
)
log = logging.getLogger("rex_tax_delinquency_scout")

AGENT_DIR = Path(__file__).parent
LEADS_DB = AGENT_DIR / "leads_db.json"
SCOUT_LOG = AGENT_DIR / "pipeline" / "tax_delinquency_log.jsonl"
SCOUT_LOG.parent.mkdir(parents=True, exist_ok=True)

ATTOM_API_KEY = os.environ.get("ATTOM_API_KEY", "")
PERPLEXITY_API_KEY = os.environ.get("PERPLEXITY_API_KEY", "")
ATTOM_BASE = "https://api.gateway.attomdata.com"

TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")

# ---------------------------------------------------------------------------
# TARGET COUNTIES -- tax delinquency portals for reference
# NO North Carolina (NC requires broker license for wholesaling)
# ---------------------------------------------------------------------------

TARGET_COUNTIES = [
    {
        "county": "Fulton County",
        "state": "GA",
        "fips": "13121",
        "city": "Atlanta",
        "tax_portal": "Fulton County Tax Commissioner delinquent property tax list",
        "search_hint": "fulton county georgia delinquent tax list 2024 2025",
    },
    {
        "county": "Dallas County",
        "state": "TX",
        "fips": "48113",
        "city": "Dallas",
        "tax_portal": "Dallas County Tax Office delinquent property taxes",
        "search_hint": "dallas county texas delinquent property tax list 2024 2025",
    },
    {
        "county": "Cuyahoga County",
        "state": "OH",
        "fips": "39035",
        "city": "Cleveland",
        "tax_portal": "Cuyahoga County Treasurer delinquent tax list",
        "search_hint": "cuyahoga county ohio delinquent tax list 2024 2025",
    },
    {
        "county": "St. Louis City",
        "state": "MO",
        "fips": "29510",
        "city": "St. Louis",
        "tax_portal": "St. Louis City Collector delinquent real estate taxes",
        "search_hint": "st louis city missouri delinquent real estate tax list 2024 2025",
    },
    {
        "county": "Duval County",
        "state": "FL",
        "fips": "12031",
        "city": "Jacksonville",
        "tax_portal": "Duval County Tax Collector delinquent property tax list",
        "search_hint": "duval county florida delinquent tax list 2024 2025",
    },
]


# ---------------------------------------------------------------------------
# PERPLEXITY API -- search for tax delinquency data
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


def search_tax_delinquent_properties(county: dict) -> list[dict]:
    """
    Use Perplexity to find tax delinquent properties in a county.
    Returns a list of parsed property dicts.
    """
    query = (
        f"List properties with delinquent taxes in {county['county']} {county['state']} "
        f"2024 2025. Include property address, owner name, amount owed, and years "
        f"delinquent. Focus on residential properties with 2 or more years of unpaid "
        f"taxes. Search: {county['search_hint']}"
    )

    system_prompt = (
        "You are a real estate research assistant. Find tax delinquent properties "
        "from public county records. For each property, extract and return a JSON "
        "array of objects with these keys: address (string), owner_name (string), "
        "amount_owed (number), years_delinquent (number). Only include residential "
        "properties. If you cannot find specific properties, return an empty array []. "
        "Return ONLY the JSON array, no other text."
    )

    log.info(f"  Searching tax delinquency data for {county['county']}, {county['state']}...")
    content = perplexity_search(query, system_prompt)

    if not content:
        return []

    # Try to parse JSON from the response
    properties = _parse_properties_from_text(content, county)
    return properties


def _parse_properties_from_text(text: str, county: dict) -> list[dict]:
    """
    Parse property records from Perplexity response text.
    Handles both JSON arrays and freeform text.
    """
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
                            "owner_name": str(item.get("owner_name", "")).strip(),
                            "amount_owed": _safe_float(item.get("amount_owed", 0)),
                            "years_delinquent": _safe_int(item.get("years_delinquent", 0)),
                        })
                if properties:
                    return properties
    except (json.JSONDecodeError, AttributeError, TypeError):
        pass

    # Attempt 2: Parse freeform text with address patterns
    # Look for patterns like "123 Main St" followed by owner info
    address_pattern = re.compile(
        r"(\d+\s+[A-Za-z0-9\s\.]+(?:St|Ave|Rd|Dr|Blvd|Ln|Way|Ct|Pl|Ter|Cir|Pkwy)\.?)"
        r"[,\s]+([A-Za-z\s\.]+)?"  # city (optional)
        r".*?(?:owner|owned by|name)[:\s]+([A-Za-z\s\.]+)",
        re.IGNORECASE,
    )

    for match in address_pattern.finditer(text):
        address = match.group(1).strip().upper()
        owner = match.group(3).strip() if match.group(3) else ""
        if address and len(address) > 5:
            properties.append({
                "address": address,
                "owner_name": owner,
                "amount_owed": 0,
                "years_delinquent": 2,
            })

    # Attempt 3: Look for any addresses in the text
    if not properties:
        addr_simple = re.findall(
            r"(\d{1,5}\s+[A-Za-z0-9\s\.]{3,30}(?:St|Ave|Rd|Dr|Blvd|Ln|Way|Ct|Pl)\.?)",
            text,
            re.IGNORECASE,
        )
        for addr in addr_simple[:20]:  # cap at 20
            properties.append({
                "address": addr.strip().upper(),
                "owner_name": "",
                "amount_owed": 0,
                "years_delinquent": 2,
            })

    return properties


def _safe_float(val) -> float:
    """Safely convert a value to float."""
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        cleaned = re.sub(r"[^\d.]", "", val)
        try:
            return float(cleaned) if cleaned else 0.0
        except ValueError:
            return 0.0
    return 0.0


def _safe_int(val) -> int:
    """Safely convert a value to int."""
    if isinstance(val, int):
        return val
    if isinstance(val, float):
        return int(val)
    if isinstance(val, str):
        cleaned = re.sub(r"[^\d]", "", val)
        try:
            return int(cleaned) if cleaned else 0
        except ValueError:
            return 0
    return 0


# ---------------------------------------------------------------------------
# ATTOM API -- enrich properties with detail data
# ---------------------------------------------------------------------------

def attom_headers() -> dict:
    return {
        "Accept": "application/json",
        "apikey": ATTOM_API_KEY,
    }


def enrich_property_attom(address: str, city: str, state: str) -> dict:
    """
    Look up a property in ATTOM by address to get value, beds, baths, sqft.
    Returns enrichment dict or empty dict on failure.
    """
    if not ATTOM_API_KEY:
        return {}

    # Normalize address for ATTOM lookup
    clean_address = address.strip().upper()
    params = {
        "address1": clean_address,
        "address2": f"{city}, {state}",
    }

    try:
        resp = requests.get(
            f"{ATTOM_BASE}/propertyapi/v1.0.0/property/basicprofile",
            headers=attom_headers(),
            params=params,
            timeout=20,
        )

        if resp.status_code == 200:
            data = resp.json()
            props = data.get("property", [])
            if props:
                prop = props[0]
                building = prop.get("building", {})
                assessment = prop.get("assessment", {})
                size = building.get("size", {})
                rooms = building.get("rooms", {})

                market_value = assessment.get("market", {}).get("mktTtlValue", 0)
                assessed_value = assessment.get("assessed", {}).get("assdTtlValue", 0)

                return {
                    "estimated_arv": market_value or assessed_value or 0,
                    "beds": rooms.get("beds", 0) or 0,
                    "baths": rooms.get("bathsfull", 0) or 0,
                    "sqft": size.get("livingsize", 0) or 0,
                    "year_built": building.get("summary", {}).get("yearbuilt", 0) or 0,
                    "lot_size_sqft": size.get("lotsize", 0) or 0,
                }
        elif resp.status_code == 429:
            log.warning("  ATTOM rate limited -- waiting 60s")
            time.sleep(60)
        else:
            log.debug(f"  ATTOM lookup returned {resp.status_code} for {clean_address}")

    except requests.RequestException as e:
        log.debug(f"  ATTOM lookup failed for {clean_address}: {e}")

    return {}


# ---------------------------------------------------------------------------
# SKIP TRACE -- find owner contact info via Perplexity
# ---------------------------------------------------------------------------

def skip_trace_owner(owner_name: str, city: str, state: str) -> dict:
    """
    Use Perplexity to find contact information for a property owner.
    Returns dict with email and phone if found.
    """
    if not owner_name or len(owner_name) < 3:
        return {}

    query = (
        f"Find contact information for {owner_name} in {city}, {state}. "
        f"I need their email address and phone number. "
        f"Search public records, white pages, and people search sites."
    )

    system_prompt = (
        "You are a skip tracing assistant. Find the person's contact info from "
        "public records. Return a JSON object with keys: email (string or null), "
        "phone (string or null), confidence (string: high/medium/low). "
        "Return ONLY the JSON object."
    )

    content = perplexity_search(query, system_prompt, max_tokens=300)
    if not content:
        return {}

    # Parse response
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
        "phone": f"({phone_match.group(1)}) {phone_match.group(2)}-{phone_match.group(3)}" if phone_match else "",
        "confidence": "low",
    }


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


def import_tax_leads(new_leads: list[dict]) -> int:
    """Import tax delinquency leads into the shared leads database. Dedup by address."""
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


def log_scout_run(county: str, searched: int, enriched: int, imported: int, traced: int):
    """Append a line to the scout log for tracking."""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "scout_type": "tax_delinquency",
        "county": county,
        "properties_found": searched,
        "attom_enriched": enriched,
        "imported_new": imported,
        "skip_traced": traced,
    }
    with open(SCOUT_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")


# ---------------------------------------------------------------------------
# MAIN SCOUT PIPELINE
# ---------------------------------------------------------------------------

def scout_county(county: dict) -> list[dict]:
    """Run the full tax delinquency scout pipeline for one county."""
    log.info(f"Scouting {county['county']}, {county['state']}...")

    # Step 1: Search for tax delinquent properties via Perplexity
    raw_properties = search_tax_delinquent_properties(county)
    log.info(f"  Found {len(raw_properties)} potential tax delinquent properties")

    if not raw_properties:
        log_scout_run(f"{county['county']}, {county['state']}", 0, 0, 0, 0)
        return []

    time.sleep(2)  # rate limit buffer

    # Step 2: Build lead records with enrichment from ATTOM
    leads = []
    enriched_count = 0
    for prop in raw_properties:
        address = prop.get("address", "")
        if not address or len(address) < 5:
            continue

        # Build base lead
        lead = {
            "address": address.upper(),
            "city": county["city"].upper(),
            "state": county["state"].upper(),
            "zip_code": "",
            "county": county["county"],
            "owner_name": prop.get("owner_name", ""),
            "owner_email": "",
            "owner_phone": "",
            "estimated_arv": 0,
            "beds": 0,
            "baths": 0,
            "sqft": 0,
            "year_built": 0,
            "lead_type": "tax_lien",
            "source": "tax_delinquency_scout",
            "status": "new",
            "outreach_count": 0,
            "last_outreach": "",
            "sequence_step": 0,
            "created_at": TODAY,
            "tax_amount_owed": prop.get("amount_owed", 0),
            "tax_years_delinquent": prop.get("years_delinquent", 0),
            "motivation_score": 0,
        }

        # Enrich via ATTOM if we have the key
        if ATTOM_API_KEY:
            enrichment = enrich_property_attom(address, county["city"], county["state"])
            if enrichment:
                lead.update({
                    "estimated_arv": enrichment.get("estimated_arv", 0),
                    "beds": enrichment.get("beds", 0),
                    "baths": enrichment.get("baths", 0),
                    "sqft": enrichment.get("sqft", 0),
                    "year_built": enrichment.get("year_built", 0),
                })
                enriched_count += 1
                time.sleep(1)  # ATTOM rate limit

        leads.append(lead)

    log.info(f"  ATTOM enriched {enriched_count}/{len(leads)} properties")

    # Step 3: Skip trace owners for contact info
    traced_count = 0
    for lead in leads:
        owner = lead.get("owner_name", "")
        if owner and len(owner) > 3:
            trace_result = skip_trace_owner(owner, county["city"], county["state"])
            if trace_result.get("email"):
                lead["owner_email"] = trace_result["email"]
                traced_count += 1
            if trace_result.get("phone"):
                lead["owner_phone"] = trace_result["phone"]
            time.sleep(2)  # Perplexity rate limit

    log.info(f"  Skip traced {traced_count}/{len(leads)} owners")

    # Step 4: Calculate motivation scores
    for lead in leads:
        score = 25  # base tax_lien score
        years = lead.get("tax_years_delinquent", 0)
        amount = lead.get("tax_amount_owed", 0)

        if years >= 3:
            score += 25  # serious delinquency
        elif years >= 2:
            score += 15

        if amount >= 10000:
            score += 15  # large debt = more pressure
        elif amount >= 5000:
            score += 10

        arv = lead.get("estimated_arv", 0)
        if arv >= 150000:
            score += 10  # higher ARV = bigger assignment fee

        if lead.get("owner_email"):
            score += 5  # contactable = actionable

        lead["motivation_score"] = min(score, 100)

        # Set motivation tier
        if score >= 70:
            lead["motivation_tier"] = "HOT"
        elif score >= 40:
            lead["motivation_tier"] = "WARM"
        else:
            lead["motivation_tier"] = "COLD"

    # Step 5: Import into leads database
    imported = import_tax_leads(leads)
    log.info(f"  Imported {imported} new leads (skipped {len(leads) - imported} duplicates)")

    # Step 6: Log the run
    log_scout_run(
        county=f"{county['county']}, {county['state']}",
        searched=len(raw_properties),
        enriched=enriched_count,
        imported=imported,
        traced=traced_count,
    )

    return leads


def run_tax_delinquency_scout():
    """Run the full tax delinquency scout across all target counties."""
    log.info("=" * 60)
    log.info("Rex Tax Delinquency Scout -- starting daily run")
    log.info(f"Date: {TODAY}")
    log.info(f"Target counties: {len(TARGET_COUNTIES)}")
    log.info("=" * 60)

    total_found = 0
    total_imported = 0
    all_county_leads = []

    for county in TARGET_COUNTIES:
        try:
            leads = scout_county(county)
            total_found += len(leads)
            all_county_leads.extend(leads)
        except Exception as e:
            log.error(f"Failed to scout {county['county']}: {e}")
            continue

        # Rate limit between counties
        time.sleep(3)

    # Count imported (new leads only)
    all_leads = load_leads()
    tax_count = sum(1 for l in all_leads if l.get("lead_type") == "tax_lien")
    total_count = len(all_leads)
    hot_count = sum(
        1 for l in all_county_leads
        if l.get("motivation_tier") == "HOT"
    )

    log.info("")
    log.info("=" * 60)
    log.info("Rex Tax Delinquency Scout -- daily run complete")
    log.info(f"  Properties found today: {total_found}")
    log.info(f"  HOT leads: {hot_count}")
    log.info(f"  Tax lien leads in database: {tax_count}")
    log.info(f"  Total leads in database: {total_count}")
    log.info("=" * 60)

    # Post summary to Slack if configured
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
                        f"*Rex Tax Delinquency Scout -- {TODAY}*\n"
                        f"Scouted {len(TARGET_COUNTIES)} counties\n"
                        f"Properties found: {total_found}\n"
                        f"HOT leads: {hot_count}\n"
                        f"Tax lien leads in DB: {tax_count}\n"
                        f"Total leads in DB: {total_count}"
                    ),
                },
                timeout=10,
            )
        except Exception:
            pass

    return total_found


if __name__ == "__main__":
    run_tax_delinquency_scout()
