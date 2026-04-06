"""
Rex Probate Scout -- Finds probate/inherited property leads in 6 target counties.

Pipeline:
  1. Query ATTOM API for properties with estate/trust/probate ownership
  2. Cross-reference with Perplexity API for heir/obituary info
  3. Skip-trace heirs for contact info
  4. Import leads into leads_db.json with lead_type="probate"
  5. Rex SDR picks them up for pain-aware outreach

Runs daily at 8:30 AM PT (16:30 UTC) via cron:
  30 16 * * * cd /path/to/wholesale_agent && python3 rex_probate_scout.py

Uses:
  ATTOM_API_KEY  -- property data
  PERPLEXITY_API_KEY  -- heir/obituary research
"""

import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

logging.basicConfig(
    level=logging.INFO,
    format="[Rex Probate %(asctime)s] %(message)s",
    datefmt="%H:%M",
)
log = logging.getLogger("rex_probate_scout")

AGENT_DIR = Path(__file__).parent
LEADS_DB = AGENT_DIR / "leads_db.json"
SCOUT_LOG = AGENT_DIR / "pipeline" / "probate_scout_log.jsonl"
SCOUT_LOG.parent.mkdir(parents=True, exist_ok=True)

ATTOM_API_KEY = os.environ.get("ATTOM_API_KEY", "8b8f49842c214289928801e9bc67ecc7")
PERPLEXITY_API_KEY = os.environ.get("PERPLEXITY_API_KEY", "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")
ATTOM_BASE = "https://api.gateway.attomdata.com"

TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")

# ---------------------------------------------------------------------------
# TARGET COUNTIES -- probate court search URLs for reference + ATTOM FIPS
# ---------------------------------------------------------------------------

TARGET_COUNTIES = [
    {
        "county": "Fulton County",
        "state": "GA",
        "fips": "13121",
        "court_url": "https://publicrecordsaccess.fultoncountyga.gov/Portal/Home/Dashboard/29",
        "city_filter": "Atlanta",
    },
    {
        "county": "Dallas County",
        "state": "TX",
        "fips": "48113",
        "court_url": "https://www.dallascounty.org/department/probate-courts/",
        "city_filter": "Dallas",
    },
    {
        "county": "Cuyahoga County",
        "state": "OH",
        "fips": "39035",
        "court_url": "https://probate.cuyahogacounty.us/pa/CaseSearch.aspx",
        "city_filter": "Cleveland",
    },
    {
        "county": "Mecklenburg County",
        "state": "NC",
        "fips": "37119",
        "court_url": "https://www.mecklenburgcountync.gov/courts-services/clerk-of-superior-court/estates/",
        "city_filter": "Charlotte",
    },
    {
        "county": "St. Louis County",
        "state": "MO",
        "fips": "29189",
        "court_url": "https://www.stlouisco.com/Government/Courts/Probate-Court",
        "city_filter": "St. Louis",
    },
    {
        "county": "Duval County",
        "state": "FL",
        "fips": "12031",
        "court_url": "https://www.duvalclerk.com/probate",
        "city_filter": "Jacksonville",
    },
]


# ---------------------------------------------------------------------------
# ATTOM API -- Find estate/trust/probate properties
# ---------------------------------------------------------------------------

def attom_headers():
    return {
        "Accept": "application/json",
        "apikey": ATTOM_API_KEY,
    }


def fetch_probate_properties(county: dict, page: int = 1, page_size: int = 50) -> list[dict]:
    """
    Query ATTOM property/basicprofile for properties in a county where
    the owner type suggests estate, trust, or probate ownership.

    ATTOM filters:
      - ownertype=2 (corporate/entity -- catches trusts/estates)
      - saletype=11 (probate/estate sale)

    We try both approaches and merge results.
    """
    results = []

    # Approach 1: Owner type = entity (catches "Estate of..." and trusts)
    try:
        resp = requests.get(
            f"{ATTOM_BASE}/propertyapi/v1.0.0/property/basicprofile",
            headers=attom_headers(),
            params={
                "countyfips": county["fips"],
                "ownertype": "2",
                "page": page,
                "pagesize": page_size,
                "orderby": "SaleSearchDate desc",
            },
            timeout=30,
        )
        if resp.status_code == 200:
            data = resp.json()
            properties = data.get("property", [])
            results.extend(properties)
            log.info(
                f"  ATTOM ownertype query: {len(properties)} properties "
                f"in {county['county']}, {county['state']}"
            )
        elif resp.status_code == 429:
            log.warning("  ATTOM rate limited -- waiting 60s")
            time.sleep(60)
        else:
            log.warning(f"  ATTOM ownertype query returned {resp.status_code}: {resp.text[:200]}")
    except requests.RequestException as e:
        log.error(f"  ATTOM ownertype query failed: {e}")

    time.sleep(2)  # rate limit buffer

    # Approach 2: Recent sales with probate/estate sale type
    try:
        resp = requests.get(
            f"{ATTOM_BASE}/propertyapi/v1.0.0/sale/basicprofile",
            headers=attom_headers(),
            params={
                "countyfips": county["fips"],
                "saletype": "Probate",
                "page": page,
                "pagesize": page_size,
                "orderby": "SaleSearchDate desc",
            },
            timeout=30,
        )
        if resp.status_code == 200:
            data = resp.json()
            sales = data.get("property", [])
            results.extend(sales)
            log.info(
                f"  ATTOM sale/probate query: {len(sales)} properties "
                f"in {county['county']}, {county['state']}"
            )
        elif resp.status_code == 429:
            log.warning("  ATTOM rate limited -- waiting 60s")
            time.sleep(60)
        else:
            log.warning(f"  ATTOM sale query returned {resp.status_code}: {resp.text[:200]}")
    except requests.RequestException as e:
        log.error(f"  ATTOM sale query failed: {e}")

    return results


def is_probate_property(prop: dict) -> bool:
    """Check if an ATTOM property record indicates probate/estate/trust ownership."""
    # Check owner name for estate/trust indicators
    owner1 = (
        prop.get("assessment", {}).get("owner", {}).get("owner1", {}).get("fullname", "")
        or ""
    ).upper()
    owner_indicators = ["ESTATE OF", "ESTATE", "TRUST", "TRUSTEE", "HEIR", "DECEASED", "PROBATE"]
    if any(ind in owner1 for ind in owner_indicators):
        return True

    # Check owner type
    owner_type = prop.get("assessment", {}).get("owner", {}).get("corporateindicator", "")
    if str(owner_type).upper() in ("Y", "YES", "TRUE", "1"):
        # Corporate indicator + estate-like name
        if any(ind in owner1 for ind in ["ESTATE", "TRUST"]):
            return True

    # Check sale type for probate
    sale_type = (
        prop.get("sale", {}).get("saleTransType", "")
        or ""
    ).upper()
    if any(t in sale_type for t in ["PROBATE", "ESTATE", "INHERITANCE"]):
        return True

    return False


def extract_lead_from_attom(prop: dict, county: dict) -> dict | None:
    """Extract a lead record from an ATTOM property object."""
    address_info = prop.get("address", {})
    assessment = prop.get("assessment", {})
    owner_info = assessment.get("owner", {})

    address_line = address_info.get("oneLine", "") or address_info.get("line1", "")
    city = address_info.get("locality", "") or county.get("city_filter", "")
    state = address_info.get("countrySubd", "") or county.get("state", "")
    zipcode = address_info.get("postal1", "")

    owner_name = (
        owner_info.get("owner1", {}).get("fullname", "")
        or owner_info.get("absenteeOwnerStatus", "")
        or ""
    )

    if not address_line or not owner_name:
        return None

    # Get property value for ARV estimate
    market_value = assessment.get("market", {}).get("mktTtlValue", 0)
    assessed_value = assessment.get("assessed", {}).get("assdTtlValue", 0)
    arv = market_value or assessed_value or 0

    # Get mailing address (for absentee detection)
    mail_address = (
        owner_info.get("mailingAddressOneLine", "")
        or owner_info.get("owner1", {}).get("mailingAddressOneLine", "")
        or ""
    )
    is_absentee = mail_address.lower() != address_line.lower() if mail_address else False

    return {
        "address": address_line.upper(),
        "city": city.upper(),
        "state": state.upper(),
        "zip_code": zipcode,
        "county": county["county"],
        "owner_name": owner_name,
        "owner_email": "",  # filled by skip trace
        "owner_phone": "",  # filled by skip trace
        "mail_address": mail_address,
        "arv": arv,
        "is_absentee": is_absentee,
        "lead_type": "probate",
        "source": "attom_probate",
        "court_url": county["court_url"],
        "status": "new",
        "outreach_count": 0,
        "last_outreach": "",
        "sequence_step": 0,
        "created_at": TODAY,
        "dead_since": "",
        "heir_info": {},
    }


# ---------------------------------------------------------------------------
# PERPLEXITY API -- Find heirs via obituary search
# ---------------------------------------------------------------------------

def search_heirs(deceased_name: str, city: str, state: str) -> dict:
    """
    Use Perplexity API to find obituary info and extract heir names.

    Returns dict with:
      - obituary_found: bool
      - heir_names: list of strings
      - raw_summary: str
    """
    if not PERPLEXITY_API_KEY or PERPLEXITY_API_KEY.startswith("pplx-FAKE"):
        return {"obituary_found": False, "heir_names": [], "raw_summary": ""}

    query = f"{deceased_name} obituary {city} {state} children family survivors"

    try:
        resp = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers={
                "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "sonar",
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a research assistant. Find obituary information for "
                            "the named person. Extract: (1) names of surviving family members "
                            "(children, spouse, siblings), (2) city/state of family members if "
                            "mentioned. Return a JSON object with keys: obituary_found (bool), "
                            "heir_names (list of full name strings), relationship (list matching "
                            "heir_names with relationship like 'son', 'daughter', 'spouse'). "
                            "If no obituary found, return obituary_found: false."
                        ),
                    },
                    {"role": "user", "content": query},
                ],
                "max_tokens": 500,
                "temperature": 0.1,
            },
            timeout=30,
        )

        if resp.status_code == 200:
            content = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
            # Try to parse structured response
            try:
                # Look for JSON in the response
                import re
                json_match = re.search(r"\{[\s\S]*\}", content)
                if json_match:
                    parsed = json.loads(json_match.group())
                    return {
                        "obituary_found": parsed.get("obituary_found", False),
                        "heir_names": parsed.get("heir_names", []),
                        "relationships": parsed.get("relationship", []),
                        "raw_summary": content[:500],
                    }
            except (json.JSONDecodeError, AttributeError):
                pass

            # Fallback: return raw text
            return {
                "obituary_found": bool(content.strip()),
                "heir_names": [],
                "raw_summary": content[:500],
            }

        elif resp.status_code == 429:
            log.warning("  Perplexity rate limited -- skipping heir search")
            time.sleep(10)
        else:
            log.warning(f"  Perplexity returned {resp.status_code}")

    except requests.RequestException as e:
        log.error(f"  Perplexity search failed: {e}")

    return {"obituary_found": False, "heir_names": [], "raw_summary": ""}


# ---------------------------------------------------------------------------
# LEAD DATABASE -- import into shared leads_db.json
# ---------------------------------------------------------------------------

def load_leads() -> list[dict]:
    if LEADS_DB.exists():
        try:
            return json.loads(LEADS_DB.read_text())
        except json.JSONDecodeError:
            log.error("leads_db.json is corrupted -- starting fresh")
            return []
    return []


def save_leads(leads: list[dict]):
    LEADS_DB.write_text(json.dumps(leads, indent=2, default=str))


def import_probate_leads(new_leads: list[dict]) -> int:
    """Import probate leads into the shared leads database. Dedup by address."""
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


def log_scout_run(county: str, raw_count: int, filtered_count: int, imported: int, heirs_found: int):
    """Append a line to the scout log for tracking."""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "county": county,
        "raw_properties": raw_count,
        "filtered_probate": filtered_count,
        "imported_new": imported,
        "heirs_researched": heirs_found,
    }
    with open(SCOUT_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")


# ---------------------------------------------------------------------------
# MAIN SCOUT PIPELINE
# ---------------------------------------------------------------------------

def scout_county(county: dict) -> list[dict]:
    """Run the full probate scout pipeline for one county."""
    log.info(f"Scouting {county['county']}, {county['state']}...")

    # Step 1: Fetch properties from ATTOM
    raw_properties = fetch_probate_properties(county)
    log.info(f"  Raw properties from ATTOM: {len(raw_properties)}")

    # Step 2: Filter to probate/estate only
    probate_leads = []
    for prop in raw_properties:
        if is_probate_property(prop):
            lead = extract_lead_from_attom(prop, county)
            if lead:
                probate_leads.append(lead)

    log.info(f"  Filtered probate leads: {len(probate_leads)}")

    # Step 3: Research heirs for each lead (rate-limited)
    heirs_found = 0
    for lead in probate_leads:
        owner = lead.get("owner_name", "")
        # Strip "ESTATE OF" prefix for obituary search
        search_name = owner
        for prefix in ["ESTATE OF ", "ESTATE OF", "THE ESTATE OF "]:
            if search_name.upper().startswith(prefix):
                search_name = search_name[len(prefix):].strip()
                break

        if search_name and len(search_name) > 3:
            heir_info = search_heirs(
                search_name,
                lead.get("city", ""),
                lead.get("state", ""),
            )
            lead["heir_info"] = heir_info
            if heir_info.get("heir_names"):
                heirs_found += 1
                log.info(
                    f"  Found heirs for {search_name}: "
                    f"{', '.join(heir_info['heir_names'][:3])}"
                )
            # Rate limit: 2 seconds between Perplexity calls
            time.sleep(2)

    # Step 4: Import into leads database
    imported = import_probate_leads(probate_leads)
    log.info(f"  Imported {imported} new leads (skipped {len(probate_leads) - imported} duplicates)")

    # Step 5: Log the run
    log_scout_run(
        county=f"{county['county']}, {county['state']}",
        raw_count=len(raw_properties),
        filtered_count=len(probate_leads),
        imported=imported,
        heirs_found=heirs_found,
    )

    return probate_leads


def run_probate_scout():
    """Run the full probate scout across all target counties."""
    log.info("=" * 60)
    log.info("Rex Probate Scout -- starting daily run")
    log.info(f"Date: {TODAY}")
    log.info(f"Target counties: {len(TARGET_COUNTIES)}")
    log.info("=" * 60)

    total_raw = 0
    total_filtered = 0
    total_imported = 0
    total_heirs = 0

    for county in TARGET_COUNTIES:
        try:
            leads = scout_county(county)
            total_raw += len(leads)
            total_filtered += len([l for l in leads if l.get("lead_type") == "probate"])
            # Count imported from the log
        except Exception as e:
            log.error(f"Failed to scout {county['county']}: {e}")
            continue

        # Rate limit between counties
        time.sleep(3)

    # Summary
    all_leads = load_leads()
    probate_count = sum(1 for l in all_leads if l.get("lead_type") == "probate")
    total_count = len(all_leads)

    log.info("")
    log.info("=" * 60)
    log.info("Rex Probate Scout -- daily run complete")
    log.info(f"  Probate leads in database: {probate_count}")
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
                        f"*Rex Probate Scout -- {TODAY}*\n"
                        f"Scouted {len(TARGET_COUNTIES)} counties\n"
                        f"Probate leads in DB: {probate_count}\n"
                        f"Total leads in DB: {total_count}"
                    ),
                },
                timeout=10,
            )
        except Exception:
            pass

    return probate_count


if __name__ == "__main__":
    run_probate_scout()
