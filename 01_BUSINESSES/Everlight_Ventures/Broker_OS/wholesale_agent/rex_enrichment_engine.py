"""
Rex Enrichment Engine -- Deep property enrichment + hyper-personalized pitch generation.

Takes a lead with basic info (address, owner name, city/state) and:
1. Pulls expanded data from ATTOM API (years owned, sqft, beds, baths, value gaps, mortgage)
2. Uses Perplexity to find distress signals (code violations, probate, divorce, liens, expired listings)
3. Calculates equity position and carrying cost estimates
4. Detects the PRIMARY distress type
5. Generates a hyper-personalized pitch that reads like a handwritten note from someone who
   did their homework -- not a form letter

Every email references specific property details. Every pitch addresses the seller's
actual situation. No generic "I buy houses" spam.

Uses:
  ATTOM_API_KEY       -- property data enrichment
  PERPLEXITY_API_KEY  -- distress signal research
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
    format="[Rex Enrichment %(asctime)s] %(message)s",
    datefmt="%H:%M",
)
log = logging.getLogger("rex_enrichment")

AGENT_DIR = Path(__file__).parent

ATTOM_API_KEY = os.environ.get("ATTOM_API_KEY", "")
PERPLEXITY_API_KEY = os.environ.get("PERPLEXITY_API_KEY", "")
ATTOM_BASE = "https://api.gateway.attomdata.com"

CURRENT_YEAR = datetime.now(timezone.utc).year


# ---------------------------------------------------------------------------
# ATTOM API HELPERS
# ---------------------------------------------------------------------------

def _attom_headers() -> dict:
    return {
        "Accept": "application/json",
        "apikey": ATTOM_API_KEY,
    }


def enrich_from_attom(lead: dict) -> dict:
    """
    Pull expanded property data from ATTOM API.

    Returns enrichment dict with: years_owned, year_built, sqft, beds, baths,
    assessed_value, market_value, value_gap, last_sale_price, last_sale_date,
    mortgage_balance, is_absentee, lot_size_sqft.
    """
    if not ATTOM_API_KEY:
        log.warning("No ATTOM_API_KEY -- skipping ATTOM enrichment")
        return {}

    address = lead.get("address", "").strip()
    city = lead.get("city", "").strip()
    state = lead.get("state", "").strip()

    if not address or not city or not state:
        return {}

    params = {
        "address1": address.upper(),
        "address2": f"{city}, {state}",
    }

    enrichment = {}

    # --- Basic profile (building, assessment) ---
    try:
        resp = requests.get(
            f"{ATTOM_BASE}/propertyapi/v1.0.0/property/basicprofile",
            headers=_attom_headers(),
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
                summary = building.get("summary", {})
                address_info = prop.get("address", {})

                market_value = assessment.get("market", {}).get("mktTtlValue", 0) or 0
                assessed_value = assessment.get("assessed", {}).get("assdTtlValue", 0) or 0
                year_built = summary.get("yearbuilt", 0) or 0

                enrichment.update({
                    "year_built": year_built,
                    "sqft": size.get("livingsize", 0) or 0,
                    "lot_size_sqft": size.get("lotsize", 0) or 0,
                    "beds": rooms.get("beds", 0) or 0,
                    "baths": rooms.get("bathsfull", 0) or 0,
                    "assessed_value": assessed_value,
                    "market_value": market_value,
                    "estimated_arv": market_value or assessed_value,
                    "value_gap": market_value - assessed_value if market_value and assessed_value else 0,
                })

                # Absentee owner detection
                mailing = address_info.get("matchCode", "")
                owner_mailing = prop.get("assessment", {}).get("owner", {}).get("mailingaddressoneline", "")
                property_addr = address.upper()
                if owner_mailing and property_addr:
                    # If mailing address doesn't contain the property street number, likely absentee
                    street_num = property_addr.split()[0] if property_addr.split() else ""
                    if street_num and street_num not in owner_mailing.upper():
                        enrichment["is_absentee"] = True
                    else:
                        enrichment["is_absentee"] = False

        elif resp.status_code == 429:
            log.warning("ATTOM rate limited on basicprofile -- waiting 60s")
            time.sleep(60)
        else:
            log.debug(f"ATTOM basicprofile returned {resp.status_code} for {address}")

    except requests.RequestException as e:
        log.debug(f"ATTOM basicprofile failed for {address}: {e}")

    time.sleep(0.5)

    # --- Sale history (last sale price/date, years owned) ---
    try:
        resp = requests.get(
            f"{ATTOM_BASE}/propertyapi/v1.0.0/saleshistory/basichistory",
            headers=_attom_headers(),
            params=params,
            timeout=20,
        )

        if resp.status_code == 200:
            data = resp.json()
            props = data.get("property", [])
            if props:
                sales = props[0].get("saleHistory", [])
                if sales:
                    # Most recent sale
                    latest = sales[0]
                    sale_amount = latest.get("amount", {})
                    sale_date_str = latest.get("saleTransDate", "") or ""

                    last_price = sale_amount.get("saleAmt", 0) or 0
                    enrichment["last_sale_price"] = last_price
                    enrichment["last_sale_date"] = sale_date_str

                    # Calculate years owned
                    if sale_date_str:
                        try:
                            sale_year = int(sale_date_str[:4])
                            enrichment["years_owned"] = CURRENT_YEAR - sale_year
                            enrichment["purchase_year"] = sale_year
                        except (ValueError, IndexError):
                            pass

        elif resp.status_code == 429:
            log.warning("ATTOM rate limited on saleshistory -- waiting 60s")
            time.sleep(60)

    except requests.RequestException as e:
        log.debug(f"ATTOM saleshistory failed for {address}: {e}")

    time.sleep(0.5)

    # --- Mortgage data ---
    try:
        resp = requests.get(
            f"{ATTOM_BASE}/propertyapi/v1.0.0/property/detailmortgage",
            headers=_attom_headers(),
            params=params,
            timeout=20,
        )

        if resp.status_code == 200:
            data = resp.json()
            props = data.get("property", [])
            if props:
                mortgage = props[0].get("mortgage", {})
                if mortgage:
                    first = mortgage.get("first", {})
                    amount = first.get("amount", 0) or 0
                    enrichment["mortgage_balance"] = amount
                    enrichment["mortgage_date"] = first.get("date", "") or ""

        elif resp.status_code == 429:
            log.warning("ATTOM rate limited on mortgage -- waiting 60s")
            time.sleep(60)

    except requests.RequestException as e:
        log.debug(f"ATTOM mortgage failed for {address}: {e}")

    log.info(f"  ATTOM enrichment for {address}: {len(enrichment)} fields")
    return enrichment


# ---------------------------------------------------------------------------
# PERPLEXITY DISTRESS RESEARCH
# ---------------------------------------------------------------------------

def _perplexity_search(query: str, system_prompt: str = "", max_tokens: int = 1500) -> str:
    """Query Perplexity API and return response text."""
    if not PERPLEXITY_API_KEY:
        log.warning("No PERPLEXITY_API_KEY -- skipping search")
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


def enrich_from_perplexity(lead: dict) -> dict:
    """
    Use Perplexity to research distress signals for a property.

    Searches for: listing history, code violations, obituary/probate,
    divorce filings, liens/judgments, and other distress indicators.

    Returns dict with distress findings.
    """
    if not PERPLEXITY_API_KEY:
        return {}

    address = lead.get("address", "").strip()
    owner_name = lead.get("owner_name", "").strip()
    city = lead.get("city", "").strip()
    state = lead.get("state", "").strip()
    county = lead.get("county", "").strip()

    if not address:
        return {}

    findings = {
        "listing_history": None,
        "code_violations": None,
        "probate_indicator": None,
        "divorce_indicator": None,
        "liens_judgments": None,
        "vacancy_indicator": None,
        "distress_signals": [],
    }

    system_prompt = (
        "You are a real estate research assistant analyzing public records. "
        "Return a JSON object with these keys: found (boolean), details (string with "
        "specifics), severity (string: high/medium/low/none). "
        "Return ONLY the JSON object, no other text."
    )

    # --- Search 1: Listing history (Zillow, Realtor, Redfin) ---
    query_listing = (
        f"Has the property at {address}, {city}, {state} been listed for sale recently? "
        f"Check Zillow, Realtor.com, Redfin. Was it listed and removed? Any price drops? "
        f"How many days was it on market? What was the listing price?"
    )
    listing_raw = _perplexity_search(query_listing, system_prompt, max_tokens=500)
    listing_data = _parse_json_response(listing_raw)
    if listing_data.get("found"):
        findings["listing_history"] = listing_data.get("details", "")
        findings["distress_signals"].append("expired_listing")
    time.sleep(2)

    # --- Search 2: Code violations ---
    query_violations = (
        f"Are there any open code violations, building code issues, or city citations "
        f"for {address}, {city}, {state}? Check municipal code enforcement records."
    )
    violations_raw = _perplexity_search(query_violations, system_prompt, max_tokens=500)
    violations_data = _parse_json_response(violations_raw)
    if violations_data.get("found"):
        findings["code_violations"] = violations_data.get("details", "")
        findings["distress_signals"].append("code_violation")
    time.sleep(2)

    # --- Search 3: Obituary / Probate (only if we have owner name) ---
    if owner_name and len(owner_name) > 3:
        query_probate = (
            f"Has {owner_name} from {city}, {state} passed away? "
            f"Check obituary records, probate court filings, estate records "
            f"for {county or city} county."
        )
        probate_raw = _perplexity_search(query_probate, system_prompt, max_tokens=500)
        probate_data = _parse_json_response(probate_raw)
        if probate_data.get("found"):
            findings["probate_indicator"] = probate_data.get("details", "")
            findings["distress_signals"].append("probate")
        time.sleep(2)

        # --- Search 4: Divorce filings ---
        query_divorce = (
            f"Are there any divorce filings or family court records for {owner_name} "
            f"in {county or city}, {state}? Check court records."
        )
        divorce_raw = _perplexity_search(query_divorce, system_prompt, max_tokens=500)
        divorce_data = _parse_json_response(divorce_raw)
        if divorce_data.get("found"):
            findings["divorce_indicator"] = divorce_data.get("details", "")
            findings["distress_signals"].append("divorce")
        time.sleep(2)

    # --- Search 5: Liens and judgments ---
    query_liens = (
        f"Are there any liens, tax liens, mechanic's liens, or judgment filings "
        f"against {address}, {city}, {state}? Check county recorder records."
    )
    liens_raw = _perplexity_search(query_liens, system_prompt, max_tokens=500)
    liens_data = _parse_json_response(liens_raw)
    if liens_data.get("found"):
        findings["liens_judgments"] = liens_data.get("details", "")
        findings["distress_signals"].append("liens")
    time.sleep(2)

    signal_count = len(findings["distress_signals"])
    log.info(f"  Perplexity enrichment for {address}: {signal_count} distress signals found")
    return findings


def _parse_json_response(text: str) -> dict:
    """Parse a JSON object from Perplexity response text."""
    if not text:
        return {}
    try:
        json_match = re.search(r"\{[\s\S]*?\}", text)
        if json_match:
            parsed = json.loads(json_match.group())
            return parsed
    except (json.JSONDecodeError, AttributeError):
        pass
    # Fallback: check for keywords indicating a positive finding
    lower = text.lower()
    if any(kw in lower for kw in ["found", "yes", "violation", "deceased", "divorce", "lien", "expired"]):
        return {"found": True, "details": text[:300], "severity": "medium"}
    return {"found": False, "details": "", "severity": "none"}


# ---------------------------------------------------------------------------
# EQUITY & FINANCIAL ANALYSIS
# ---------------------------------------------------------------------------

def calculate_equity_position(lead: dict) -> dict:
    """
    Calculate equity position and carrying costs from ATTOM enrichment data.

    Returns dict with: estimated_equity, equity_percent, years_owned,
    monthly_carrying_cost, annual_tax_estimate.
    """
    market_value = lead.get("market_value", 0) or lead.get("estimated_arv", 0) or 0
    mortgage_balance = lead.get("mortgage_balance", 0) or 0
    assessed_value = lead.get("assessed_value", 0) or 0

    result = {}

    # Equity calculation
    if market_value > 0:
        if mortgage_balance > 0:
            result["estimated_equity"] = market_value - mortgage_balance
            result["equity_percent"] = round(
                (market_value - mortgage_balance) / market_value * 100, 1
            )
        else:
            # No known mortgage -- likely free and clear or data unavailable
            result["estimated_equity"] = market_value
            result["equity_percent"] = 100.0

    # Years of ownership
    purchase_year = lead.get("purchase_year", 0)
    if purchase_year and purchase_year > 1900:
        result["years_owned"] = CURRENT_YEAR - purchase_year

    # Carrying cost estimates (rough)
    if assessed_value > 0:
        # Average property tax rate ~1.1% nationally
        annual_tax = assessed_value * 0.011
        # Insurance ~0.5% of value
        annual_insurance = market_value * 0.005 if market_value else assessed_value * 0.005
        # Maintenance ~1% of value
        annual_maintenance = market_value * 0.01 if market_value else assessed_value * 0.01

        result["annual_tax_estimate"] = round(annual_tax)
        result["monthly_carrying_cost"] = round(
            (annual_tax + annual_insurance + annual_maintenance) / 12
        )

    return result


# ---------------------------------------------------------------------------
# DISTRESS TYPE DETECTION
# ---------------------------------------------------------------------------

def detect_distress_type(lead: dict) -> str:
    """
    Analyze all enrichment data and return the PRIMARY distress type.

    Priority order (most motivated seller first):
    1. pre_foreclosure
    2. tax_delinquent
    3. code_violation
    4. probate
    5. divorce
    6. expired_listing
    7. absentee
    8. long_hold (15+ years)
    9. vacant
    10. high_equity (default fallback)
    """
    distress_signals = lead.get("distress_signals", [])
    lead_type = lead.get("lead_type", "")

    # Check Perplexity findings
    if "pre_foreclosure" in distress_signals or lead_type == "pre_foreclosure":
        return "pre_foreclosure"

    # Tax delinquency
    tax_years = lead.get("tax_years_delinquent", 0) or 0
    if tax_years >= 2 or lead_type == "tax_lien" or "tax_delinquent" in distress_signals:
        return "tax_delinquent"

    if "code_violation" in distress_signals or lead_type == "code_violation":
        return "code_violation"

    if "probate" in distress_signals or lead_type == "probate":
        return "probate"

    if "divorce" in distress_signals or lead_type == "divorce":
        return "divorce"

    if "expired_listing" in distress_signals or lead_type == "expired_listing":
        return "expired_listing"

    # Absentee owner
    if lead.get("is_absentee") or lead_type == "absentee":
        return "absentee"

    # Long-hold owner (15+ years)
    years_owned = lead.get("years_owned", 0) or 0
    if years_owned >= 15:
        return "long_hold"

    if "vacant" in distress_signals or lead_type == "vacant":
        return "vacant"

    return "high_equity"


# ---------------------------------------------------------------------------
# HYPER-PERSONALIZED PITCH GENERATOR
# ---------------------------------------------------------------------------

# Pitch templates keyed by distress type
_PITCH_TEMPLATES = {
    "high_equity": {
        "subject": "Your property on {street}",
        "body": (
            "Hey {first_name} -- I noticed you've owned the property on {street} "
            "{years_clause}. {value_clause}\n\n"
            "I'm a private buyer acquiring in {city} this quarter. If you've ever "
            "considered unlocking that equity without the hassle of listing, I can "
            "make you a cash offer and close in 7 days.\n\n"
            "No agents, no repairs, no showings. Just a check.\n\n"
            "Worth a conversation?\n\n"
            "-- Piper\n"
            "Everlight Ventures | Private Acquisitions\n"
            "piper@everlightventures.io\n\n"
            "Reply STOP to opt out."
        ),
    },
    "tax_delinquent": {
        "subject": "Can I help with {street}?",
        "body": (
            "Hey {first_name} -- I came across your property on {street}. "
            "{tax_clause}\n\n"
            "I specialize in buying properties in exactly this situation. I handle "
            "the back taxes at closing{violation_addon}, and you walk away with cash. "
            "No cleanup, no repairs, no stress.\n\n"
            "Would it help to hear what I can offer?\n\n"
            "-- Piper\n"
            "Everlight Ventures | Private Acquisitions\n"
            "piper@everlightventures.io\n\n"
            "Reply STOP to opt out."
        ),
    },
    "code_violation": {
        "subject": "Quick question about {street}",
        "body": (
            "Hey {first_name} -- I came across your property on {street}. "
            "I know dealing with the city on code issues {tax_addon}is a nightmare. "
            "The fines don't stop and the county doesn't wait.\n\n"
            "I specialize in buying properties in exactly this situation. I handle "
            "everything at closing -- the violations go away the day we close, "
            "and you walk away with cash. No cleanup, no repairs, no stress.\n\n"
            "Would it help to hear what I can offer?\n\n"
            "-- Piper\n"
            "Everlight Ventures | Private Acquisitions\n"
            "piper@everlightventures.io\n\n"
            "Reply STOP to opt out."
        ),
    },
    "probate": {
        "subject": "Thinking of you -- {street}",
        "body": (
            "Hey {first_name} -- I understand you may have recently inherited or "
            "taken responsibility for the property on {street}. I know this can "
            "be an overwhelming time, and dealing with a property on top of "
            "everything else is the last thing you need.\n\n"
            "I'm a private buyer and I work with families in this exact situation. "
            "I buy as-is -- no repairs, no cleanout, no agent fees. I handle the "
            "paperwork and can close on your timeline.\n\n"
            "If it would help to have one less thing to worry about, I'm happy to "
            "share what I can offer. No pressure.\n\n"
            "-- Piper\n"
            "Everlight Ventures | Private Acquisitions\n"
            "piper@everlightventures.io\n\n"
            "Reply STOP to opt out."
        ),
    },
    "divorce": {
        "subject": "Quick thought on {street}",
        "body": (
            "Hey {first_name} -- I know transitions like this can be stressful, "
            "especially when there's a property in the mix. If you and your family "
            "need to sell the property on {street} quickly and cleanly, I might "
            "be able to help.\n\n"
            "I'm a private cash buyer. I close fast, buy as-is, and make the "
            "process as simple as possible -- no agents, no showings, no drawn-out "
            "negotiations. {value_clause}\n\n"
            "If a clean break on the property would be useful, just reply and "
            "I'll send a number.\n\n"
            "-- Piper\n"
            "Everlight Ventures | Private Acquisitions\n"
            "piper@everlightventures.io\n\n"
            "Reply STOP to opt out."
        ),
    },
    "expired_listing": {
        "subject": "Saw your listing on {street}",
        "body": (
            "Hey {first_name} -- I saw your property on {street} was on the market "
            "recently{listing_clause}. I know it's frustrating when the market "
            "doesn't deliver, especially after months of showings.\n\n"
            "I'm a different kind of buyer. No contingencies, no inspections, no "
            "waiting for financing. Cash, close in 7 days, and I buy as-is.\n\n"
            "I think I can get close to where you need to be. Want to hear a number?\n\n"
            "-- Piper\n"
            "Everlight Ventures | Private Acquisitions\n"
            "piper@everlightventures.io\n\n"
            "Reply STOP to opt out."
        ),
    },
    "absentee": {
        "subject": "Your property on {street}",
        "body": (
            "Hey {first_name} -- I noticed you own the property on {street} in {city} "
            "but live elsewhere. Managing a property from a distance is never easy -- "
            "maintenance, tenants, taxes, it all adds up. {property_clause}\n\n"
            "If you've ever thought about cashing out, I'm a private buyer making "
            "offers in {city} this quarter. All cash, close in 7 days, completely "
            "as-is. No repairs, no agents, no hassle.\n\n"
            "Interested in hearing a number?\n\n"
            "-- Piper\n"
            "Everlight Ventures | Private Acquisitions\n"
            "piper@everlightventures.io\n\n"
            "Reply STOP to opt out."
        ),
    },
    "long_hold": {
        "subject": "Your property on {street}",
        "body": (
            "Hey {first_name} -- I noticed you've owned the property on {street} "
            "{years_clause}. That's a lot of equity built up{value_clause_inline}.\n\n"
            "If you've ever considered unlocking that equity without the hassle of "
            "listing -- no agents, no repairs, no months of showings -- I can make "
            "you a cash offer and close in 7 days.\n\n"
            "A lot of owners in your position are surprised at what their property "
            "is worth in a private cash sale. Worth a quick conversation?\n\n"
            "-- Piper\n"
            "Everlight Ventures | Private Acquisitions\n"
            "piper@everlightventures.io\n\n"
            "Reply STOP to opt out."
        ),
    },
    "vacant": {
        "subject": "The property on {street}",
        "body": (
            "Hey {first_name} -- I noticed the property on {street} in {city} "
            "appears to be sitting vacant. A vacant property can become a real "
            "liability -- vandalism, code fines, insurance costs, and the value "
            "doesn't go up while it sits.\n\n"
            "I'm a private cash buyer and I can take it off your hands fast. "
            "As-is condition, I cover closing costs, and we can close in 7 days.\n\n"
            "Would it help to hear an offer?\n\n"
            "-- Piper\n"
            "Everlight Ventures | Private Acquisitions\n"
            "piper@everlightventures.io\n\n"
            "Reply STOP to opt out."
        ),
    },
    "pre_foreclosure": {
        "subject": "Can I help with {street}?",
        "body": (
            "Hey {first_name} -- I came across your property on {street} and "
            "wanted to reach out. I know the bank's timeline doesn't wait, and "
            "the stress of that situation is real.\n\n"
            "I'm a private cash buyer. I can close before the bank does -- "
            "often in 7-10 days. You walk away with your equity instead of "
            "losing it to foreclosure, and your credit takes a much smaller hit.\n\n"
            "It costs nothing to hear a number. Want me to send one over?\n\n"
            "-- Piper\n"
            "Everlight Ventures | Private Acquisitions\n"
            "piper@everlightventures.io\n\n"
            "Reply STOP to opt out."
        ),
    },
}


def _get_street_name(address: str) -> str:
    """Extract just the street name from a full address for shorter references."""
    if not address:
        return "your property"
    # Remove city/state/zip if comma-separated
    parts = address.split(",")
    street = parts[0].strip()
    # Trim to something readable
    if len(street) > 40:
        street = street[:40].rsplit(" ", 1)[0]
    return street.title() if street == street.upper() else street


def _format_value(value: int) -> str:
    """Format dollar value like $280k or $1.2M."""
    if not value:
        return ""
    if value >= 1_000_000:
        return f"${value / 1_000_000:.1f}M"
    elif value >= 1_000:
        return f"${value // 1_000}k"
    return f"${value:,}"


def generate_personalized_pitch(lead: dict) -> dict:
    """
    Generate a hyper-personalized email pitch based on ALL enrichment data.

    Returns dict with 'subject' and 'body' keys.
    Also returns 'sms_body' for SMS touches.
    """
    distress_type = detect_distress_type(lead)
    template = _PITCH_TEMPLATES.get(distress_type, _PITCH_TEMPLATES["high_equity"])

    # Build replacement values
    owner = lead.get("owner_name", "")
    first_name = owner.split()[0].title() if owner else "there"
    street = _get_street_name(lead.get("address", ""))
    city = lead.get("city", "").title() if lead.get("city", "") == lead.get("city", "").upper() else lead.get("city", "")
    state = lead.get("state", "")

    years_owned = lead.get("years_owned", 0) or 0
    market_value = lead.get("market_value", 0) or lead.get("estimated_arv", 0) or 0
    year_built = lead.get("year_built", 0) or 0
    sqft = lead.get("sqft", 0) or 0
    beds = lead.get("beds", 0) or 0
    baths = lead.get("baths", 0) or 0

    # Build dynamic clauses
    years_clause = ""
    if years_owned > 0:
        years_clause = f"since {CURRENT_YEAR - years_owned}"
        if years_owned >= 5:
            years_clause += f" -- that's over {years_owned} years of equity"
    else:
        years_clause = "and it caught my eye"

    value_clause = ""
    if market_value:
        value_clause = f"In a neighborhood where values have climbed to {_format_value(market_value)}+, that's significant."
    elif sqft and year_built:
        value_clause = f"A {sqft} sqft home built in {year_built} has a lot of potential."

    value_clause_inline = ""
    if market_value:
        value_clause_inline = f" in an area where values have hit {_format_value(market_value)}+"

    tax_clause = ""
    tax_years = lead.get("tax_years_delinquent", 0) or 0
    tax_amount = lead.get("tax_amount_owed", 0) or 0
    if tax_years and tax_amount:
        tax_clause = (
            f"I know dealing with {tax_years} years of back taxes "
            f"({_format_value(int(tax_amount))}+) while the county threatens "
            f"auction is a nightmare"
        )
    elif tax_years:
        tax_clause = (
            f"I know dealing with {tax_years} years of unpaid taxes while the "
            f"county threatens auction is a nightmare"
        )
    else:
        tax_clause = (
            "I know dealing with back taxes while the county threatens "
            "auction is a nightmare"
        )

    tax_addon = ""
    if tax_years >= 2:
        tax_addon = "while taxes stack up "

    violation_addon = ""
    code_violations = lead.get("code_violations")
    if code_violations:
        violation_addon = ", the code violations go away the day we close"

    listing_clause = ""
    listing_history = lead.get("listing_history", "")
    if listing_history and isinstance(listing_history, str):
        # Try to extract price from listing history
        price_match = re.search(r"\$[\d,]+k?", listing_history)
        if price_match:
            listing_clause = f" at {price_match.group(0)}"

    property_clause = ""
    property_details = []
    if year_built:
        property_details.append(f"built in {year_built}")
    if sqft:
        property_details.append(f"{sqft:,} sqft")
    if beds and baths:
        property_details.append(f"{beds}bd/{baths}ba")
    if property_details:
        property_clause = f"A {', '.join(property_details)} property like yours has real value."

    # Format the template
    replacements = {
        "first_name": first_name,
        "street": street,
        "city": city,
        "state": state,
        "years_clause": years_clause,
        "value_clause": value_clause,
        "value_clause_inline": value_clause_inline,
        "tax_clause": tax_clause,
        "tax_addon": tax_addon,
        "violation_addon": violation_addon,
        "listing_clause": listing_clause,
        "property_clause": property_clause,
    }

    try:
        subject = template["subject"].format(**replacements)
        body = template["body"].format(**replacements)
    except KeyError as e:
        log.warning(f"Template formatting error for {distress_type}: {e}")
        # Fall back to high_equity template
        fallback = _PITCH_TEMPLATES["high_equity"]
        subject = fallback["subject"].format(**replacements)
        body = fallback["body"].format(**replacements)

    # Generate SMS version (under 160 chars)
    sms_body = _generate_sms(first_name, street, city, distress_type, years_owned, market_value)

    return {
        "subject": subject,
        "body": body,
        "sms_body": sms_body,
        "distress_type": distress_type,
    }


def _generate_sms(first_name, street, city, distress_type, years_owned, market_value):
    """Generate a short SMS pitch under 160 chars referencing specific details."""
    # Build the most relevant detail snippet
    detail = ""
    if distress_type == "tax_delinquent":
        detail = "I handle back taxes at closing"
    elif distress_type == "code_violation":
        detail = "I handle code issues at closing"
    elif distress_type == "probate":
        detail = "I work with families in this situation"
    elif distress_type == "expired_listing":
        detail = "Cash, no contingencies, 7 days"
    elif distress_type == "pre_foreclosure":
        detail = "I can close before the bank does"
    elif years_owned and years_owned >= 10:
        detail = f"{years_owned}+ yrs of equity there"
    elif market_value:
        detail = f"Values at {_format_value(market_value)}+ in {city}"
    else:
        detail = f"Buying in {city} this month"

    base = f"Hey {first_name} -- saw {street}. {detail}. Cash offer, 7 days, as-is. Worth a chat? -Rich"

    # Trim if over 160
    if len(base) > 155:
        base = f"Hey {first_name} -- saw {street}. {detail}. Cash, 7 days. Worth a chat? -Rich"
    if len(base) > 160:
        base = f"{first_name} -- {street}. {detail}. Cash offer? -Rich"

    return base[:160]


# ---------------------------------------------------------------------------
# FULL ENRICHMENT PIPELINE
# ---------------------------------------------------------------------------

def enrich_lead(lead: dict) -> dict:
    """
    Run the full enrichment pipeline on a single lead.

    1. ATTOM enrichment (property data, sales history, mortgage)
    2. Perplexity research (distress signals)
    3. Equity calculation
    4. Distress type detection

    Mutates the lead dict in place and returns it.
    Sets lead["enriched"] = True when complete.
    """
    if lead.get("enriched"):
        log.debug(f"  Lead already enriched: {lead.get('address', 'unknown')}")
        return lead

    log.info(f"Enriching lead: {lead.get('address', 'unknown')}")

    # Step 1: ATTOM data
    attom_data = enrich_from_attom(lead)
    if attom_data:
        lead.update(attom_data)
    time.sleep(1)

    # Step 2: Perplexity distress research
    perplexity_data = enrich_from_perplexity(lead)
    if perplexity_data:
        lead["listing_history"] = perplexity_data.get("listing_history")
        lead["code_violations"] = perplexity_data.get("code_violations")
        lead["probate_indicator"] = perplexity_data.get("probate_indicator")
        lead["divorce_indicator"] = perplexity_data.get("divorce_indicator")
        lead["liens_judgments"] = perplexity_data.get("liens_judgments")
        lead["vacancy_indicator"] = perplexity_data.get("vacancy_indicator")
        lead["distress_signals"] = perplexity_data.get("distress_signals", [])

    # Step 3: Equity position
    equity_data = calculate_equity_position(lead)
    if equity_data:
        lead.update(equity_data)

    # Step 4: Distress type
    lead["detected_distress"] = detect_distress_type(lead)

    # Mark as enriched so we don't re-fetch
    lead["enriched"] = True
    lead["enriched_at"] = datetime.now(timezone.utc).isoformat()

    log.info(
        f"  Enrichment complete: distress={lead['detected_distress']}, "
        f"equity={lead.get('estimated_equity', 'unknown')}, "
        f"signals={lead.get('distress_signals', [])}"
    )

    return lead


if __name__ == "__main__":
    # Test with a sample lead
    test_lead = {
        "address": "123 MAIN ST, ATLANTA, GA 30301",
        "city": "ATLANTA",
        "state": "GA",
        "owner_name": "JOHN SMITH",
        "lead_type": "high_equity",
    }
    enriched = enrich_lead(test_lead)
    pitch = generate_personalized_pitch(enriched)
    print(f"\nDistress type: {enriched.get('detected_distress')}")
    print(f"\nSubject: {pitch['subject']}")
    print(f"\nBody:\n{pitch['body']}")
    print(f"\nSMS: {pitch['sms_body']}")


# ---------------------------------------------------------------------------
# OPPORTUNITY ZONE ENRICHMENT
# ---------------------------------------------------------------------------

def check_opportunity_zone(lead: dict) -> bool:
    """Check if a property is in a Qualified Opportunity Zone."""
    oz_file = Path(__file__).parent / "opportunity_zones.json"
    if not oz_file.exists():
        return False

    import json as jmod
    oz_data = jmod.loads(oz_file.read_text())
    all_oz_zips = set()
    for zips in oz_data.values():
        all_oz_zips.update(zips)

    return lead.get("zip_code", "") in all_oz_zips


def generate_oz_buyer_pitch(lead: dict) -> str:
    """Generate OZ-specific pitch for buyers -- this is the profit multiplier."""
    addr = lead.get("address", "the property")
    city = lead.get("city", "")
    zc = lead.get("zip_code", "")
    arv = lead.get("arv", lead.get("estimated_arv", 0)) or 0

    return f"""OPPORTUNITY ZONE PROPERTY -- TAX-FREE APPRECIATION

This property at {addr} is located in a Qualified Opportunity Zone (zip {zc}).

What this means for you as a buyer:

  - DEFER capital gains by investing through a Qualified Opportunity Fund (QOF)
  - 5-year hold: 10% of your deferred gain is EXCLUDED from taxes
  - 7-year hold: 15% exclusion
  - 10-year hold: ALL appreciation on this investment is 100% TAX-FREE

Example on this deal:
  Purchase at contract price, rehab, rent or sell.
  If property appreciates from ${arv:,} to ${int(arv * 1.5):,} over 10 years,
  that ${int(arv * 0.5):,} gain is COMPLETELY TAX-FREE.

  No other investment vehicle offers this.

OZ 1.0 designations sunset Dec 31, 2026 -- invest before the window closes.
New OZ 2.0 designations take effect Jan 1, 2027.

This property qualifies NOW. First buyer to wire EMD locks it in.
"""


def generate_oz_seller_pitch(lead: dict) -> str:
    """Tell sellers their property is in an OZ -- it's worth MORE to investors."""
    first = lead.get("owner_name", "").split()[0].title() if lead.get("owner_name") else "there"
    addr = lead.get("address", "your property")
    city = lead.get("city", "")

    return (
        f"Hey {first} -- one more thing about {addr}. Your property is in a "
        f"federally designated Opportunity Zone. That means investors get major "
        f"tax breaks when they buy in your area, which makes properties like yours "
        f"highly sought after right now. The current OZ window closes Dec 2026, "
        f"so there's strong buyer demand. That's partly why I'm reaching out -- "
        f"I have investors specifically looking for OZ properties in {city}."
    )
