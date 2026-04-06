"""
Rex Comp Validator -- validates ATTOM ARV against real sold comps.

ATTOM assessed values can be 20-40% off. This module:
1. Uses Perplexity API to find 3-5 recent sold comps nearby
2. Calculates a validated ARV from median comp price
3. Scores confidence: HIGH / MEDIUM / LOW
4. Only lets Rex make offers on HIGH or MEDIUM confidence
5. Calculates MAO (Maximum Allowable Offer) using the 65% rule
6. Handles tear-downs with the 10520 rule (20% of new construction)
"""

import json
import logging
import os
import re
import statistics
from typing import Optional

import requests

logging.basicConfig(
    level=logging.INFO,
    format="[Rex Comps %(asctime)s] %(message)s",
    datefmt="%H:%M",
)
log = logging.getLogger("rex_comp_validator")

PERPLEXITY_API_KEY = os.environ.get("PERPLEXITY_API_KEY", "")
PERPLEXITY_URL = "https://api.perplexity.ai/chat/completions"
PERPLEXITY_MODEL = "sonar"


# ---------------------------------------------------------------------------
# PERPLEXITY SEARCH HELPER
# ---------------------------------------------------------------------------

def _query_perplexity(prompt: str, timeout: int = 30) -> str:
    """Send a prompt to Perplexity and return the text response."""
    if not PERPLEXITY_API_KEY:
        log.warning("PERPLEXITY_API_KEY not set -- comp validation disabled")
        return ""

    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": PERPLEXITY_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a real estate data assistant. Return factual data "
                    "about recent home sales. Always include the sale price, "
                    "address, beds, baths, sqft, and sale date when available. "
                    "Format each comp on its own line."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
        "max_tokens": 1500,
    }

    try:
        resp = requests.post(
            PERPLEXITY_URL,
            headers=headers,
            json=payload,
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("choices", [{}])[0].get("message", {}).get("content", "")
    except requests.RequestException as e:
        log.error(f"Perplexity API error: {e}")
        return ""


# ---------------------------------------------------------------------------
# COMP EXTRACTION
# ---------------------------------------------------------------------------

def _extract_prices(text: str) -> list[float]:
    """
    Pull dollar amounts from Perplexity response text.
    Matches patterns like $350,000 or $275000 or $1.2M.
    Filters to plausible home sale prices ($30k - $5M).
    """
    prices = []

    # Match $NNN,NNN or $NNNNNN patterns
    pattern_full = re.findall(r'\$\s*([\d,]+(?:\.\d+)?)\b', text)
    for raw in pattern_full:
        cleaned = raw.replace(",", "")
        try:
            val = float(cleaned)
            if 30_000 <= val <= 5_000_000:
                prices.append(val)
        except ValueError:
            continue

    # Match $N.NM patterns (e.g., $1.2M)
    pattern_m = re.findall(r'\$([\d.]+)\s*[Mm]', text)
    for raw in pattern_m:
        try:
            val = float(raw) * 1_000_000
            if 30_000 <= val <= 5_000_000:
                prices.append(val)
        except ValueError:
            continue

    return prices


def _extract_comp_details(text: str) -> list[dict]:
    """
    Try to parse structured comp data from the Perplexity response.
    Returns list of dicts with address, price, beds, baths, sqft, date.
    Falls back to price-only extraction if parsing fails.
    """
    comps = []
    lines = text.split("\n")

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Look for a price in this line
        price_match = re.search(r'\$([\d,]+(?:\.\d+)?)', line)
        if not price_match:
            continue

        price_str = price_match.group(1).replace(",", "")
        try:
            price = float(price_str)
        except ValueError:
            continue

        if price < 30_000 or price > 5_000_000:
            continue

        comp = {"price": price, "raw_line": line[:200]}

        # Try to extract beds/baths/sqft
        beds_match = re.search(r'(\d+)\s*(?:bed|br|bedroom)', line, re.IGNORECASE)
        if beds_match:
            comp["beds"] = int(beds_match.group(1))

        baths_match = re.search(r'([\d.]+)\s*(?:bath|ba|bathroom)', line, re.IGNORECASE)
        if baths_match:
            comp["baths"] = float(baths_match.group(1))

        sqft_match = re.search(r'([\d,]+)\s*(?:sq\s*ft|sqft|sf)', line, re.IGNORECASE)
        if sqft_match:
            comp["sqft"] = int(sqft_match.group(1).replace(",", ""))

        comps.append(comp)

    return comps


# ---------------------------------------------------------------------------
# ARV VALIDATION
# ---------------------------------------------------------------------------

def validate_arv(
    address: str,
    city: str,
    state: str,
    attom_arv: float,
    beds: int = 3,
    baths: float = 2.0,
    sqft: int = 1500,
) -> dict:
    """
    Validate ATTOM's ARV estimate against real sold comps via Perplexity.

    Returns dict:
        validated_arv: float -- median of comps (or attom_arv if no comps)
        comps: list[dict] -- extracted comp data
        confidence: str -- HIGH / MEDIUM / LOW
        attom_arv: float -- original ATTOM value
        deviation_pct: float -- how far off ATTOM was
        should_proceed: bool -- True if HIGH or MEDIUM
    """
    prompt = (
        f"Find 3-5 recently sold homes near {address}, {city}, {state} "
        f"similar to {beds}BR {baths}BA {sqft} sqft, sold in the last 6 months "
        f"within 0.5 miles. For each comp, list: address, sale price, beds, "
        f"baths, sqft, and sale date."
    )

    response_text = _query_perplexity(prompt)
    comps = _extract_comp_details(response_text)

    # If structured parsing got fewer than 2 comps, fall back to price extraction
    if len(comps) < 2:
        raw_prices = _extract_prices(response_text)
        # Deduplicate and use the ones we don't already have
        existing_prices = {c["price"] for c in comps}
        for p in raw_prices:
            if p not in existing_prices:
                comps.append({"price": p, "raw_line": ""})
                existing_prices.add(p)

    comp_prices = [c["price"] for c in comps]

    # If we still have no comps, fall back to ATTOM value with LOW confidence
    if not comp_prices:
        log.warning(f"No comps found for {address} -- falling back to ATTOM value")
        return {
            "validated_arv": attom_arv,
            "comps": [],
            "confidence": "LOW",
            "attom_arv": attom_arv,
            "deviation_pct": 0.0,
            "should_proceed": False,
            "note": "No comps found -- ATTOM value unvalidated",
        }

    # Filter outliers: remove comps more than 50% from median
    if len(comp_prices) >= 3:
        rough_median = statistics.median(comp_prices)
        filtered = [
            p for p in comp_prices
            if abs(p - rough_median) / rough_median <= 0.50
        ]
        if len(filtered) >= 2:
            comp_prices = filtered

    validated_arv = statistics.median(comp_prices)

    # Calculate deviation from ATTOM value
    if attom_arv > 0:
        deviation_pct = abs(validated_arv - attom_arv) / attom_arv * 100
    else:
        deviation_pct = 100.0

    # Assign confidence
    if deviation_pct <= 10:
        confidence = "HIGH"
    elif deviation_pct <= 20:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    should_proceed = confidence in ("HIGH", "MEDIUM")

    result = {
        "validated_arv": round(validated_arv),
        "comps": comps[:5],
        "comp_count": len(comp_prices),
        "comp_median": round(validated_arv),
        "comp_min": round(min(comp_prices)),
        "comp_max": round(max(comp_prices)),
        "confidence": confidence,
        "attom_arv": attom_arv,
        "deviation_pct": round(deviation_pct, 1),
        "should_proceed": should_proceed,
    }

    if deviation_pct > 15:
        result["flag"] = (
            f"ATTOM value ${attom_arv:,.0f} differs from comp median "
            f"${validated_arv:,.0f} by {deviation_pct:.1f}%"
        )

    log.info(
        f"Comp validation for {address}: "
        f"ATTOM=${attom_arv:,.0f} Validated=${validated_arv:,.0f} "
        f"({confidence}, {deviation_pct:.1f}% off, {len(comp_prices)} comps)"
    )
    return result


# ---------------------------------------------------------------------------
# TEAR-DOWN DETECTION
# ---------------------------------------------------------------------------

def is_tear_down(year_built: int, sqft: int, arv: float) -> bool:
    """
    Determine if a property is a tear-down candidate.

    Criteria:
    - Built before 1960
    - Under 1500 sqft
    - Land value likely exceeds improvement value (rough heuristic:
      if ARV per sqft is under $80, the structure isn't worth much)
    """
    if year_built <= 0 or sqft <= 0:
        return False

    old_enough = year_built < 1960
    small_enough = sqft < 1500
    arv_per_sqft = arv / sqft if sqft > 0 else 0
    low_value_structure = arv_per_sqft < 80

    return old_enough and small_enough and low_value_structure


# ---------------------------------------------------------------------------
# MAO CALCULATOR
# ---------------------------------------------------------------------------

def calculate_mao(
    validated_arv: float,
    condition_score: int,
    property_type: str = "residential",
    repair_estimate: float = 0,
    year_built: int = 2000,
    sqft: int = 1500,
) -> dict:
    """
    Calculate Maximum Allowable Offer.

    Standard: ARV x 0.65 - repairs = MAO
    Tear-down: 20% of new construction sale price (10520 rule)
    Land: comp against similar lot sales, apply $5k discount

    Args:
        validated_arv: comp-validated ARV
        condition_score: 1-10 (1=worst)
        property_type: "residential", "teardown", or "land"
        repair_estimate: itemized repair total (0 = use crude fallback)
        year_built: construction year
        sqft: square footage

    Returns dict with offer, repairs, assignment_fee, buyer_price, buyer_profit
    """
    # Auto-detect tear-down if type is residential
    if property_type == "residential" and is_tear_down(year_built, sqft, validated_arv):
        property_type = "teardown"

    if property_type == "teardown":
        return _calculate_teardown_mao(validated_arv, sqft)

    if property_type == "land":
        return _calculate_land_mao(validated_arv)

    # --- Standard residential MAO ---
    # Use provided repair estimate, or fall back to condition-based guess
    if repair_estimate > 0:
        repairs = repair_estimate
    else:
        if condition_score <= 3:
            repairs = 40_000
        elif condition_score <= 6:
            repairs = 25_000
        else:
            repairs = 10_000

    offer = (validated_arv * 0.65) - repairs
    offer = max(offer, 0)
    offer = round(offer / 500) * 500

    # Assignment fee: 5% of ARV, floor $8k
    assignment_fee = max(8_000, int(validated_arv * 0.05))
    assignment_fee = round(assignment_fee / 500) * 500
    buyer_price = offer + assignment_fee
    buyer_profit = validated_arv - buyer_price - repairs

    return {
        "offer": offer,
        "repairs": round(repairs),
        "assignment_fee": assignment_fee,
        "buyer_price": buyer_price,
        "buyer_profit": round(buyer_profit),
        "arv": round(validated_arv),
        "condition_score": condition_score,
        "property_type": "residential",
        "method": "65_percent_rule",
    }


def _calculate_teardown_mao(arv: float, sqft: int) -> dict:
    """
    10520 rule: offer 20% of new construction sale price in the area.
    ARV here represents what a new build would sell for.
    """
    from rex_repair_estimator import estimate_teardown_cost

    offer = round(arv * 0.20 / 500) * 500
    demo_cost = estimate_teardown_cost(sqft)
    offer = max(0, offer - demo_cost)
    offer = round(offer / 500) * 500

    assignment_fee = max(5_000, int(arv * 0.03))
    assignment_fee = round(assignment_fee / 500) * 500
    buyer_price = offer + assignment_fee

    return {
        "offer": offer,
        "repairs": 0,
        "demolition_cost": demo_cost,
        "assignment_fee": assignment_fee,
        "buyer_price": buyer_price,
        "buyer_profit": round(arv - buyer_price - demo_cost),
        "arv": round(arv),
        "condition_score": 1,
        "property_type": "teardown",
        "method": "10520_rule",
    }


def _calculate_land_mao(land_arv: float) -> dict:
    """
    Land MAO: comp against similar lot sales, apply $5k discount.
    """
    offer = land_arv - 5_000
    offer = max(offer, 0)
    offer = round(offer / 500) * 500

    assignment_fee = max(5_000, int(land_arv * 0.05))
    assignment_fee = round(assignment_fee / 500) * 500
    buyer_price = offer + assignment_fee

    return {
        "offer": offer,
        "repairs": 0,
        "assignment_fee": assignment_fee,
        "buyer_price": buyer_price,
        "buyer_profit": round(land_arv - buyer_price),
        "arv": round(land_arv),
        "condition_score": 0,
        "property_type": "land",
        "method": "land_comp_minus_5k",
    }


# ---------------------------------------------------------------------------
# CLI TEST
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    if len(sys.argv) >= 5:
        addr = sys.argv[1]
        city = sys.argv[2]
        state = sys.argv[3]
        attom = float(sys.argv[4])
        beds = int(sys.argv[5]) if len(sys.argv) > 5 else 3
        baths = float(sys.argv[6]) if len(sys.argv) > 6 else 2.0
        sq = int(sys.argv[7]) if len(sys.argv) > 7 else 1500

        result = validate_arv(addr, city, state, attom, beds, baths, sq)
        print(json.dumps(result, indent=2))

        if result["should_proceed"]:
            mao = calculate_mao(
                result["validated_arv"],
                condition_score=5,
            )
            print("\nMAO Calculation:")
            print(json.dumps(mao, indent=2))
        else:
            print(f"\nWould NOT proceed -- confidence: {result['confidence']}")
    else:
        print("Usage: python rex_comp_validator.py ADDRESS CITY STATE ATTOM_ARV [beds] [baths] [sqft]")
