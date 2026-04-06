"""
Rex Teardown Finder -- identifies tear-down houses for highest-profit deals.

Teardowns are the holy grail of wholesaling: $20-50k assignment fees.
The strategy: find old, small houses in neighborhoods with active new
construction. The land is worth more than the house. Builders will pay
a premium to knock it down and build new.

Pipeline:
  1. Use ATTOM API to find properties built before 1960 and under 1,500 sqft
  2. Use Perplexity to verify active new construction in the area
  3. Calculate value using the 10520 rule:
     - Find new construction sale prices nearby
     - Land value = 20% of new construction price
     - Offer = land value - demolition cost ($10-15k)
  4. Import into leads_db.json with lead_type="teardown" and PRIORITY flag

Target markets (NO North Carolina -- requires broker license):
  - Fulton County GA (Atlanta)
  - Dallas County TX
  - Cuyahoga County OH (Cleveland)
  - St. Louis City MO
  - Duval County FL (Jacksonville)

Cron (7 AM PT = 15:00 UTC):
  0 15 * * * cd /mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Broker_OS/wholesale_agent && python3 rex_teardown_finder.py

Uses:
  ATTOM_API_KEY       -- property data (year built, sqft, zoning, sales)
  PERPLEXITY_API_KEY  -- new construction verification
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
    format="[Rex Teardown %(asctime)s] %(message)s",
    datefmt="%H:%M",
)
log = logging.getLogger("rex_teardown_finder")

AGENT_DIR = Path(__file__).parent
LEADS_DB = AGENT_DIR / "leads_db.json"
SCOUT_LOG = AGENT_DIR / "pipeline" / "teardown_finder_log.jsonl"
SCOUT_LOG.parent.mkdir(parents=True, exist_ok=True)

ATTOM_API_KEY = os.environ.get("ATTOM_API_KEY", "")
PERPLEXITY_API_KEY = os.environ.get("PERPLEXITY_API_KEY", "")
ATTOM_BASE = "https://api.gateway.attomdata.com"

TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")

# Demolition cost estimate range
DEMO_COST_LOW = 10000
DEMO_COST_HIGH = 15000
DEMO_COST_MID = 12500

# ---------------------------------------------------------------------------
# TARGET MARKETS -- zip codes with known new construction activity
# NO North Carolina (NC requires broker license for wholesaling)
# ---------------------------------------------------------------------------

TARGET_MARKETS = [
    {
        "city": "Atlanta",
        "state": "GA",
        "fips": "13121",
        "market_key": "atlanta",
        # Intown Atlanta zips with active infill development
        "zips": ["30310", "30311", "30314", "30315", "30316", "30318", "30317"],
        "new_construction_avg": 350000,  # avg new build sale price
    },
    {
        "city": "Dallas",
        "state": "TX",
        "fips": "48113",
        "market_key": "dallas",
        # East Dallas and Oak Cliff -- heavy teardown/rebuild activity
        "zips": ["75203", "75215", "75216", "75217", "75227", "75210"],
        "new_construction_avg": 320000,
    },
    {
        "city": "Cleveland",
        "state": "OH",
        "fips": "39035",
        "market_key": "cleveland",
        # Tremont, Ohio City, Detroit Shoreway -- gentrifying
        "zips": ["44102", "44103", "44104", "44105", "44108", "44109"],
        "new_construction_avg": 250000,
    },
    {
        "city": "St. Louis",
        "state": "MO",
        "fips": "29510",
        "market_key": "st_louis",
        # North city + south city revitalization zones
        "zips": ["63106", "63107", "63111", "63112", "63115", "63116"],
        "new_construction_avg": 220000,
    },
    {
        "city": "Jacksonville",
        "state": "FL",
        "fips": "12031",
        "market_key": "jacksonville",
        # Springfield, Riverside, Murray Hill -- infill activity
        "zips": ["32202", "32204", "32205", "32206", "32208", "32209"],
        "new_construction_avg": 300000,
    },
]


# ---------------------------------------------------------------------------
# ATTOM API HELPERS
# ---------------------------------------------------------------------------

def attom_headers() -> dict:
    return {
        "Accept": "application/json",
        "apikey": ATTOM_API_KEY,
    }


def fetch_old_small_properties(zip_code: str, page: int = 1, page_size: int = 25) -> list[dict]:
    """
    Query ATTOM for residential properties in a zip code that are:
      - Built before 1960
      - Under 1,500 sqft living area
    These are teardown candidates if the neighborhood has new construction.
    """
    if not ATTOM_API_KEY:
        log.warning("No ATTOM_API_KEY -- cannot fetch properties")
        return []

    try:
        resp = requests.get(
            f"{ATTOM_BASE}/propertyapi/v1.0.0/property/basicprofile",
            headers=attom_headers(),
            params={
                "postalcode": zip_code,
                "propertytype": "SFR",
                "maxyearbuilt": "1960",
                "maxuniversalsize": "1500",
                "page": page,
                "pagesize": page_size,
                "orderby": "yearbuilt asc",
            },
            timeout=30,
        )

        if resp.status_code == 200:
            data = resp.json()
            properties = data.get("property", [])
            log.info(f"    ATTOM: {len(properties)} old/small properties in {zip_code}")
            return properties
        elif resp.status_code == 429:
            log.warning("    ATTOM rate limited -- waiting 60s")
            time.sleep(60)
            return []
        elif resp.status_code == 404:
            log.debug(f"    ATTOM: no results for {zip_code}")
            return []
        else:
            log.warning(f"    ATTOM returned {resp.status_code} for {zip_code}: {resp.text[:200]}")
            return []

    except requests.RequestException as e:
        log.error(f"    ATTOM request failed for {zip_code}: {e}")
        return []


def fetch_new_construction_sales(zip_code: str) -> list[dict]:
    """
    Query ATTOM for recent new construction sales in a zip code.
    Used to determine land value and verify builder activity.
    """
    if not ATTOM_API_KEY:
        return []

    try:
        resp = requests.get(
            f"{ATTOM_BASE}/propertyapi/v1.0.0/sale/basicprofile",
            headers=attom_headers(),
            params={
                "postalcode": zip_code,
                "minyearbuilt": "2020",
                "pagesize": "10",
                "orderby": "SaleSearchDate desc",
            },
            timeout=30,
        )

        if resp.status_code == 200:
            data = resp.json()
            sales = data.get("property", [])
            return sales
        elif resp.status_code == 429:
            log.warning("    ATTOM rate limited -- waiting 60s")
            time.sleep(60)
        else:
            log.debug(f"    ATTOM new construction query returned {resp.status_code} for {zip_code}")

    except requests.RequestException as e:
        log.debug(f"    ATTOM new construction query failed for {zip_code}: {e}")

    return []


def extract_property_data(prop: dict) -> dict:
    """Extract relevant fields from an ATTOM property record."""
    address_info = prop.get("address", {})
    building = prop.get("building", {})
    assessment = prop.get("assessment", {})
    size = building.get("size", {})
    rooms = building.get("rooms", {})
    summary = building.get("summary", {})
    owner_info = assessment.get("owner", {})

    address_line = address_info.get("oneLine", "") or address_info.get("line1", "")
    city = address_info.get("locality", "")
    state = address_info.get("countrySubd", "")
    zipcode = address_info.get("postal1", "")

    owner_name = (
        owner_info.get("owner1", {}).get("fullname", "")
        or ""
    )

    market_value = assessment.get("market", {}).get("mktTtlValue", 0) or 0
    assessed_value = assessment.get("assessed", {}).get("assdTtlValue", 0) or 0

    year_built = summary.get("yearbuilt", 0) or 0
    sqft = size.get("livingsize", 0) or 0
    lot_sqft = size.get("lotsize", 0) or 0
    beds = rooms.get("beds", 0) or 0
    baths = rooms.get("bathsfull", 0) or 0

    return {
        "address": address_line.upper() if address_line else "",
        "city": city.upper() if city else "",
        "state": state.upper() if state else "",
        "zip_code": zipcode,
        "owner_name": owner_name,
        "year_built": year_built,
        "sqft": sqft,
        "lot_size_sqft": lot_sqft,
        "beds": beds,
        "baths": baths,
        "current_value": market_value or assessed_value,
    }


# ---------------------------------------------------------------------------
# PERPLEXITY -- verify new construction activity
# ---------------------------------------------------------------------------

def perplexity_search(query: str, system_prompt: str = "", max_tokens: int = 800) -> str:
    """Query Perplexity API. Returns text content or empty string."""
    if not PERPLEXITY_API_KEY:
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
        else:
            log.warning(f"Perplexity returned {resp.status_code}")

    except requests.RequestException as e:
        log.error(f"Perplexity request failed: {e}")

    return ""


def verify_new_construction(address: str, city: str, state: str) -> dict:
    """
    Use Perplexity to check if there is active new construction near a property.
    Returns dict with is_active (bool), avg_new_price (int), and notes.
    """
    query = (
        f"Are there new houses built after 2020 near {address} {city} {state}? "
        f"Are builders actively constructing in this neighborhood? "
        f"What is the average price of new construction homes in this area?"
    )

    system_prompt = (
        "You are a real estate market analyst. Determine if there is active new "
        "construction near the given address. Return a JSON object with keys: "
        "is_active (boolean -- true if builders are actively building nearby), "
        "avg_new_price (number -- average sale price of new construction homes, "
        "or 0 if unknown), notes (string -- brief description of construction "
        "activity). Return ONLY the JSON object."
    )

    content = perplexity_search(query, system_prompt)
    if not content:
        return {"is_active": False, "avg_new_price": 0, "notes": ""}

    try:
        json_match = re.search(r"\{[\s\S]*?\}", content)
        if json_match:
            parsed = json.loads(json_match.group())
            return {
                "is_active": bool(parsed.get("is_active", False)),
                "avg_new_price": int(parsed.get("avg_new_price", 0) or 0),
                "notes": str(parsed.get("notes", ""))[:300],
            }
    except (json.JSONDecodeError, AttributeError, TypeError, ValueError):
        pass

    # Fallback: scan text for positive signals
    content_lower = content.lower()
    positive_signals = ["new construction", "new build", "being built", "under construction",
                        "recently built", "new homes", "builder", "development"]
    is_active = any(signal in content_lower for signal in positive_signals)

    # Try to extract price
    price_match = re.search(r"\$\s*([\d,]+)", content)
    avg_price = 0
    if price_match:
        cleaned = re.sub(r"[^\d]", "", price_match.group(1))
        avg_price = int(cleaned) if cleaned else 0

    return {
        "is_active": is_active,
        "avg_new_price": avg_price,
        "notes": content[:300],
    }


# ---------------------------------------------------------------------------
# TEARDOWN VALUE CALCULATION -- the 10520 rule
# ---------------------------------------------------------------------------

def calculate_teardown_value(
    new_construction_price: int,
    current_value: int = 0,
    demolition_cost: int = DEMO_COST_MID,
) -> dict:
    """
    Calculate teardown deal economics using the 10520 rule.

    The 10520 rule:
      - Land value = roughly 20% of new construction sale price
      - Offer to owner = land value - demolition cost
      - Assignment fee = what the builder pays you minus your offer

    Returns dict with all calculated values.
    """
    if new_construction_price <= 0:
        return {
            "land_value_estimate": 0,
            "max_offer": 0,
            "assignment_fee_estimate": 0,
            "builder_price": 0,
            "is_viable": False,
            "notes": "Cannot calculate -- no new construction price data",
        }

    # Step 1: Estimate land value (20% of new construction price)
    land_value = int(new_construction_price * 0.20)

    # Step 2: Max offer to owner = land value minus demo cost
    max_offer = max(land_value - demolition_cost, 0)

    # Step 3: What a builder would pay = land value (they factor in demo)
    # Our assignment fee = builder pays us the land value, we assigned at our offer
    assignment_fee = land_value - max_offer  # this equals demo cost basically
    # But realistically builders pay a bit more -- they want the lot
    builder_premium = int(land_value * 0.15)  # 15% premium for a good lot
    realistic_fee = assignment_fee + builder_premium

    # Viability check
    is_viable = (
        land_value > 30000  # land must be worth something
        and max_offer > 0
        and (current_value == 0 or max_offer <= current_value * 1.1)  # don't overpay
    )

    return {
        "land_value_estimate": land_value,
        "max_offer": max_offer,
        "assignment_fee_estimate": realistic_fee,
        "builder_price": land_value + builder_premium,
        "demolition_cost": demolition_cost,
        "is_viable": is_viable,
        "notes": (
            f"Land value: ${land_value:,} (20% of ${new_construction_price:,} new construction). "
            f"Offer: ${max_offer:,}. Builder pays: ${land_value + builder_premium:,}. "
            f"Assignment fee: ${realistic_fee:,}."
        ),
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


def import_teardown_leads(new_leads: list[dict]) -> int:
    """Import teardown leads into the shared leads database. Dedup by address."""
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


def log_scout_run(market: str, searched: int, candidates: int, viable: int, imported: int):
    """Append a line to the scout log for tracking."""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "scout_type": "teardown_finder",
        "market": market,
        "properties_searched": searched,
        "teardown_candidates": candidates,
        "viable_deals": viable,
        "imported_new": imported,
    }
    with open(SCOUT_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")


# ---------------------------------------------------------------------------
# MAIN SCOUT PIPELINE
# ---------------------------------------------------------------------------

def scout_market(market: dict) -> list[dict]:
    """Run the full teardown finder pipeline for one market."""
    city = market["city"]
    state = market["state"]
    log.info(f"Scouting teardowns in {city}, {state}...")

    all_candidates = []
    total_searched = 0

    for zip_code in market["zips"]:
        # Step 1: Find old, small properties via ATTOM
        raw_props = fetch_old_small_properties(zip_code)
        total_searched += len(raw_props)

        for prop in raw_props:
            prop_data = extract_property_data(prop)
            if prop_data.get("address"):
                prop_data["zip_code"] = zip_code
                prop_data["market_key"] = market["market_key"]
                all_candidates.append(prop_data)

        time.sleep(2)  # ATTOM rate limit

    log.info(f"  Found {len(all_candidates)} old/small properties across {len(market['zips'])} zips")

    if not all_candidates:
        log_scout_run(f"{city}, {state}", total_searched, 0, 0, 0)
        return []

    # Step 2: Check for new construction activity
    # We check a sample of addresses to confirm the area, not every property
    # (saves Perplexity API calls)
    new_construction_verified = {}
    zips_to_check = list(set(c.get("zip_code", "") for c in all_candidates))

    for zip_code in zips_to_check[:5]:  # limit to 5 zip checks
        # First try ATTOM for new construction sales data
        new_sales = fetch_new_construction_sales(zip_code)
        time.sleep(2)

        if new_sales:
            # Calculate average new construction price from ATTOM data
            prices = []
            for sale in new_sales:
                sale_amt = (
                    sale.get("sale", {}).get("saleAmountData", {}).get("saleAmt", 0)
                    or 0
                )
                if sale_amt > 100000:
                    prices.append(sale_amt)

            if prices:
                avg_price = int(sum(prices) / len(prices))
                new_construction_verified[zip_code] = {
                    "is_active": True,
                    "avg_new_price": avg_price,
                    "notes": f"ATTOM: {len(prices)} new construction sales, avg ${avg_price:,}",
                    "source": "attom",
                }
                log.info(f"    {zip_code}: ATTOM confirms new construction -- avg ${avg_price:,}")
                continue

        # Fallback to Perplexity verification
        sample_candidate = next(
            (c for c in all_candidates if c.get("zip_code") == zip_code),
            None,
        )
        if sample_candidate:
            nc_result = verify_new_construction(
                sample_candidate["address"],
                city,
                state,
            )
            nc_result["source"] = "perplexity"
            new_construction_verified[zip_code] = nc_result

            if nc_result["is_active"]:
                log.info(
                    f"    {zip_code}: New construction confirmed"
                    f" -- avg ${nc_result['avg_new_price']:,}" if nc_result['avg_new_price'] else ""
                )
            time.sleep(3)

    # Step 3: Calculate teardown value for candidates in verified zips
    viable_leads = []
    for candidate in all_candidates:
        zip_code = candidate.get("zip_code", "")
        nc_info = new_construction_verified.get(zip_code, {})

        if not nc_info.get("is_active"):
            continue  # skip zips without confirmed new construction

        # Determine new construction price
        new_price = nc_info.get("avg_new_price", 0) or market.get("new_construction_avg", 0)

        if new_price <= 0:
            continue

        # Calculate teardown economics
        deal = calculate_teardown_value(
            new_construction_price=new_price,
            current_value=candidate.get("current_value", 0),
        )

        if not deal["is_viable"]:
            continue

        # Build the lead record -- these get PRIORITY in Belfort sequence
        lead = {
            "address": candidate["address"],
            "city": candidate.get("city", city.upper()),
            "state": candidate.get("state", state.upper()),
            "zip_code": zip_code,
            "owner_name": candidate.get("owner_name", ""),
            "owner_email": "",
            "owner_phone": "",
            "estimated_arv": deal["builder_price"],
            "beds": candidate.get("beds", 0),
            "baths": candidate.get("baths", 0),
            "sqft": candidate.get("sqft", 0),
            "year_built": candidate.get("year_built", 0),
            "lot_size_sqft": candidate.get("lot_size_sqft", 0),
            "lead_type": "teardown",
            "source": "teardown_finder",
            "market": market["market_key"],
            "status": "new",
            "outreach_count": 0,
            "last_outreach": "",
            "sequence_step": 0,
            "created_at": TODAY,
            # Teardown-specific fields
            "current_value": candidate.get("current_value", 0),
            "land_value_estimate": deal["land_value_estimate"],
            "max_offer": deal["max_offer"],
            "assignment_fee_estimate": deal["assignment_fee_estimate"],
            "builder_price": deal["builder_price"],
            "demolition_cost": deal["demolition_cost"],
            "new_construction_avg": new_price,
            "new_construction_source": nc_info.get("source", ""),
            "deal_notes": deal["notes"],
            "is_priority": True,  # teardowns get priority in Belfort sequence
            # Motivation scoring -- teardowns start high
            "motivation_score": 0,
            "motivation_tier": "",
        }

        # Score the teardown lead
        score = 40  # base teardown score
        fee = deal["assignment_fee_estimate"]
        if fee >= 40000:
            score += 30
        elif fee >= 25000:
            score += 20
        elif fee >= 15000:
            score += 10

        if candidate.get("year_built", 9999) < 1950:
            score += 10  # older = more likely actual teardown

        if candidate.get("lot_size_sqft", 0) > 5000:
            score += 5  # bigger lot = more valuable to builder

        if nc_info.get("source") == "attom":
            score += 5  # ATTOM-verified new construction = higher confidence

        lead["motivation_score"] = min(score, 100)
        if score >= 70:
            lead["motivation_tier"] = "HOT"
        elif score >= 40:
            lead["motivation_tier"] = "WARM"
        else:
            lead["motivation_tier"] = "COLD"

        viable_leads.append(lead)

    log.info(f"  Viable teardown deals: {len(viable_leads)}")

    # Sort by assignment fee descending -- biggest money first
    viable_leads.sort(key=lambda x: x.get("assignment_fee_estimate", 0), reverse=True)

    # Log top deals
    for lead in viable_leads[:3]:
        log.info(
            f"    TOP: {lead['address']} -- "
            f"fee ${lead['assignment_fee_estimate']:,} | "
            f"offer ${lead['max_offer']:,} | "
            f"built {lead['year_built']} | "
            f"{lead['sqft']} sqft"
        )

    # Import into leads database
    imported = import_teardown_leads(viable_leads)
    log.info(f"  Imported {imported} new teardown leads (skipped {len(viable_leads) - imported} duplicates)")

    # Log the run
    log_scout_run(
        market=f"{city}, {state}",
        searched=total_searched,
        candidates=len(all_candidates),
        viable=len(viable_leads),
        imported=imported,
    )

    return viable_leads


def run_teardown_finder():
    """Run the full teardown finder across all target markets."""
    log.info("=" * 60)
    log.info("Rex Teardown Finder -- starting daily run")
    log.info(f"Date: {TODAY}")
    log.info(f"Target markets: {len(TARGET_MARKETS)}")
    log.info(f"Strategy: Find pre-1960 houses <1500sqft near new construction")
    log.info(f"Demo cost estimate: ${DEMO_COST_LOW:,}-${DEMO_COST_HIGH:,}")
    log.info("=" * 60)

    total_viable = 0
    total_fee_potential = 0
    all_teardown_leads = []

    for market in TARGET_MARKETS:
        try:
            leads = scout_market(market)
            total_viable += len(leads)
            total_fee_potential += sum(l.get("assignment_fee_estimate", 0) for l in leads)
            all_teardown_leads.extend(leads)
        except Exception as e:
            log.error(f"Failed to scout {market['city']}: {e}")
            continue

        # Rate limit between markets
        time.sleep(5)

    # Summary stats
    all_leads = load_leads()
    teardown_count = sum(1 for l in all_leads if l.get("lead_type") == "teardown")
    total_count = len(all_leads)
    hot_count = sum(1 for l in all_teardown_leads if l.get("motivation_tier") == "HOT")

    log.info("")
    log.info("=" * 60)
    log.info("Rex Teardown Finder -- daily run complete")
    log.info(f"  Viable teardown deals found: {total_viable}")
    log.info(f"  HOT teardown leads: {hot_count}")
    log.info(f"  Total fee potential: ${total_fee_potential:,}")
    log.info(f"  Teardown leads in database: {teardown_count}")
    log.info(f"  Total leads in database: {total_count}")
    log.info("=" * 60)

    # Post summary to Slack
    slack_token = os.environ.get("SLACK_BOT_TOKEN", "")
    if slack_token:
        try:
            top_deal = ""
            if all_teardown_leads:
                best = all_teardown_leads[0]
                top_deal = (
                    f"\n*Top deal:* {best['address']} -- "
                    f"${best.get('assignment_fee_estimate', 0):,} fee potential"
                )

            requests.post(
                "https://slack.com/api/chat.postMessage",
                headers={
                    "Authorization": f"Bearer {slack_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "channel": "C0ANLLV8JAC",
                    "text": (
                        f"*Rex Teardown Finder -- {TODAY}*\n"
                        f"Scouted {len(TARGET_MARKETS)} markets\n"
                        f"Viable teardown deals: {total_viable}\n"
                        f"HOT leads: {hot_count}\n"
                        f"Total fee potential: ${total_fee_potential:,}\n"
                        f"Teardown leads in DB: {teardown_count}\n"
                        f"Total leads in DB: {total_count}"
                        f"{top_deal}"
                    ),
                },
                timeout=10,
            )
        except Exception:
            pass

    return total_viable


if __name__ == "__main__":
    run_teardown_finder()
