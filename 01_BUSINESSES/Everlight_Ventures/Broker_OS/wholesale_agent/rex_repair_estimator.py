"""
Rex Repair Estimator -- itemized repair cost analysis via Perplexity AI.

Replaces the crude 3-tier guess ($10k/$25k/$40k) with:
1. AI-powered itemized repair breakdown by category
2. Per-sqft sanity checks ($15-50/sqft depending on condition)
3. Tear-down demolition cost estimation
"""

import json
import logging
import os
import re
from typing import Optional

import requests

logging.basicConfig(
    level=logging.INFO,
    format="[Rex Repairs %(asctime)s] %(message)s",
    datefmt="%H:%M",
)
log = logging.getLogger("rex_repair_estimator")

PERPLEXITY_API_KEY = os.environ.get("PERPLEXITY_API_KEY", "")
PERPLEXITY_URL = "https://api.perplexity.ai/chat/completions"
PERPLEXITY_MODEL = "sonar"

# Per-sqft sanity bounds by condition score
# condition 1-2: heavy rehab ($40-50/sqft)
# condition 3-4: major rehab ($30-40/sqft)
# condition 5-6: moderate rehab ($20-30/sqft)
# condition 7-8: light rehab ($15-20/sqft)
# condition 9-10: cosmetic only ($5-15/sqft)
PER_SQFT_RANGES = {
    1: (40, 55),
    2: (35, 50),
    3: (30, 45),
    4: (25, 40),
    5: (20, 35),
    6: (18, 30),
    7: (15, 25),
    8: (12, 20),
    9: (8, 15),
    10: (5, 12),
}

# Default repair categories with typical cost ranges
REPAIR_CATEGORIES = [
    "roof",
    "hvac",
    "foundation",
    "kitchen",
    "bathrooms",
    "flooring",
    "paint_interior",
    "paint_exterior",
    "electrical",
    "plumbing",
    "windows",
    "siding_exterior",
]


# ---------------------------------------------------------------------------
# PERPLEXITY REPAIR QUERY
# ---------------------------------------------------------------------------

def _query_perplexity_repairs(
    address: str,
    city: str,
    state: str,
    sqft: int,
    year_built: int,
    condition: int,
) -> str:
    """Ask Perplexity for an itemized repair estimate."""
    if not PERPLEXITY_API_KEY:
        log.warning("PERPLEXITY_API_KEY not set -- using fallback estimates")
        return ""

    prompt = (
        f"Estimate repair costs for a {sqft} sqft house built in {year_built} "
        f"in {city}, {state}, condition {condition}/10. "
        f"The property is at {address}. "
        f"Itemize costs for each category: "
        f"roof, HVAC, foundation, kitchen remodel, bathroom remodel, "
        f"flooring, interior paint, exterior paint, electrical, plumbing, "
        f"windows, siding/exterior. "
        f"Give a dollar amount for each item. "
        f"If a system is likely fine for the condition rating, say $0. "
        f"Use typical contractor rates for {city}, {state}."
    )

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
                    "You are a construction cost estimator. Provide realistic "
                    "repair cost estimates for residential properties. "
                    "Always give a specific dollar amount for each category. "
                    "Format: Category: $AMOUNT"
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
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("choices", [{}])[0].get("message", {}).get("content", "")
    except requests.RequestException as e:
        log.error(f"Perplexity repair query failed: {e}")
        return ""


# ---------------------------------------------------------------------------
# REPAIR PARSING
# ---------------------------------------------------------------------------

def _parse_repair_items(text: str) -> dict[str, float]:
    """
    Extract itemized repair costs from Perplexity response.
    Looks for patterns like "Roof: $8,500" or "HVAC -- $4,000".
    """
    items = {}

    # Category name mappings (normalize various phrasings)
    category_map = {
        "roof": "roof",
        "roofing": "roof",
        "hvac": "hvac",
        "heating": "hvac",
        "air conditioning": "hvac",
        "ac": "hvac",
        "foundation": "foundation",
        "structural": "foundation",
        "kitchen": "kitchen",
        "bath": "bathrooms",
        "bathroom": "bathrooms",
        "bathrooms": "bathrooms",
        "floor": "flooring",
        "flooring": "flooring",
        "paint": "paint_interior",
        "interior paint": "paint_interior",
        "exterior paint": "paint_exterior",
        "exterior painting": "paint_exterior",
        "electrical": "electrical",
        "electric": "electrical",
        "wiring": "electrical",
        "plumbing": "plumbing",
        "pipes": "plumbing",
        "window": "windows",
        "windows": "windows",
        "siding": "siding_exterior",
        "exterior": "siding_exterior",
    }

    lines = text.split("\n")
    for line in lines:
        line_lower = line.lower().strip()
        if not line_lower:
            continue

        # Find a dollar amount in this line
        price_match = re.search(r'\$([\d,]+(?:\.\d+)?)', line)
        if not price_match:
            continue

        price_str = price_match.group(1).replace(",", "")
        try:
            price = float(price_str)
        except ValueError:
            continue

        # Match the line to a category
        matched_category = None
        for keyword, cat in category_map.items():
            if keyword in line_lower:
                matched_category = cat
                break

        if matched_category and price >= 0:
            # If we already have this category, take the higher value
            # (sometimes Perplexity lists sub-items)
            if matched_category in items:
                items[matched_category] = max(items[matched_category], price)
            else:
                items[matched_category] = price

    return items


def _fallback_estimate(sqft: int, condition: int) -> dict[str, float]:
    """
    Generate a fallback repair estimate when Perplexity is unavailable.
    Uses per-sqft rates and condition-based category allocation.
    """
    lo, hi = PER_SQFT_RANGES.get(condition, (20, 35))
    mid_rate = (lo + hi) / 2
    total_budget = sqft * mid_rate

    # Allocate budget by category (typical % breakdown)
    allocations = {
        "roof": 0.15,
        "hvac": 0.10,
        "foundation": 0.05,
        "kitchen": 0.20,
        "bathrooms": 0.15,
        "flooring": 0.10,
        "paint_interior": 0.05,
        "paint_exterior": 0.05,
        "electrical": 0.05,
        "plumbing": 0.05,
        "windows": 0.03,
        "siding_exterior": 0.02,
    }

    items = {}
    for cat, pct in allocations.items():
        cost = total_budget * pct
        # Zero out categories that likely don't need work at higher conditions
        if condition >= 8 and cat in ("roof", "hvac", "foundation", "electrical", "plumbing"):
            cost = 0
        elif condition >= 6 and cat in ("foundation", "electrical"):
            cost = 0
        items[cat] = round(cost / 100) * 100  # round to nearest $100

    return items


# ---------------------------------------------------------------------------
# SANITY CHECK
# ---------------------------------------------------------------------------

def _apply_sanity_check(
    items: dict[str, float],
    sqft: int,
    condition: int,
) -> tuple[dict[str, float], float, str]:
    """
    Validate total repair estimate against per-sqft bounds.
    Returns (adjusted_items, total, note).
    """
    total = sum(items.values())
    per_sqft = total / sqft if sqft > 0 else 0

    lo, hi = PER_SQFT_RANGES.get(condition, (20, 35))
    note = ""

    if per_sqft < lo:
        # Estimate seems too low -- scale up to minimum
        if total > 0:
            scale = (lo * sqft) / total
            items = {k: round(v * scale / 100) * 100 for k, v in items.items()}
            total = sum(items.values())
            note = f"Scaled up from ${per_sqft:.0f}/sqft to ${lo}/sqft minimum"
        else:
            # All zeros but condition says work is needed
            items = _fallback_estimate(sqft, condition)
            total = sum(items.values())
            note = "AI returned $0 but condition requires repairs -- using fallback"
    elif per_sqft > hi:
        # Estimate seems too high -- cap it
        scale = (hi * sqft) / total
        items = {k: round(v * scale / 100) * 100 for k, v in items.items()}
        total = sum(items.values())
        note = f"Capped from ${per_sqft:.0f}/sqft to ${hi}/sqft maximum"

    return items, total, note


# ---------------------------------------------------------------------------
# PUBLIC API
# ---------------------------------------------------------------------------

def estimate_repairs(
    address: str,
    city: str,
    state: str,
    sqft: int,
    year_built: int,
    condition: int,
) -> dict:
    """
    Estimate itemized repair costs for a property.

    Args:
        address: property street address
        city: city name
        state: state abbreviation
        sqft: square footage
        year_built: construction year
        condition: 1-10 score (1=worst, 10=move-in ready)

    Returns dict:
        items: dict of category -> cost
        total: float total repair cost
        per_sqft: float cost per sqft
        condition: int input condition
        sanity_note: str any adjustments made
        method: str "perplexity" or "fallback"
    """
    condition = max(1, min(10, condition))
    sqft = max(100, sqft)  # floor at 100 sqft to avoid division issues

    # Try Perplexity first
    response_text = _query_perplexity_repairs(
        address, city, state, sqft, year_built, condition
    )

    if response_text:
        items = _parse_repair_items(response_text)
        method = "perplexity"
    else:
        items = {}
        method = "fallback"

    # If Perplexity returned fewer than 3 categories, use fallback
    if len(items) < 3:
        items = _fallback_estimate(sqft, condition)
        method = "fallback"

    # Apply sanity check
    items, total, sanity_note = _apply_sanity_check(items, sqft, condition)

    per_sqft_actual = total / sqft if sqft > 0 else 0

    result = {
        "items": items,
        "total": round(total),
        "per_sqft": round(per_sqft_actual, 2),
        "sqft": sqft,
        "year_built": year_built,
        "condition": condition,
        "method": method,
    }
    if sanity_note:
        result["sanity_note"] = sanity_note

    log.info(
        f"Repair estimate for {address}: "
        f"${total:,.0f} total (${per_sqft_actual:.0f}/sqft), "
        f"condition {condition}/10, method={method}"
    )
    return result


def estimate_teardown_cost(sqft: int) -> int:
    """
    Estimate demolition + site prep cost.

    Demolition: $5-15k depending on sqft
    Site prep: $2-5k
    """
    if sqft <= 0:
        return 10_000  # default

    # Demolition scales with sqft
    if sqft <= 1000:
        demo = 5_000
    elif sqft <= 1500:
        demo = 8_000
    elif sqft <= 2000:
        demo = 10_000
    elif sqft <= 3000:
        demo = 12_000
    else:
        demo = 15_000

    # Site prep scales slightly with lot size (proxy: house sqft)
    if sqft <= 1000:
        site_prep = 2_000
    elif sqft <= 2000:
        site_prep = 3_000
    else:
        site_prep = 5_000

    total = demo + site_prep
    return total


# ---------------------------------------------------------------------------
# CLI TEST
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    if len(sys.argv) >= 6:
        addr = sys.argv[1]
        city = sys.argv[2]
        state = sys.argv[3]
        sq = int(sys.argv[4])
        yr = int(sys.argv[5])
        cond = int(sys.argv[6]) if len(sys.argv) > 6 else 5

        result = estimate_repairs(addr, city, state, sq, yr, cond)
        print(json.dumps(result, indent=2))
        print(f"\nTear-down cost for {sq} sqft: ${estimate_teardown_cost(sq):,}")
    else:
        print("Usage: python rex_repair_estimator.py ADDRESS CITY STATE SQFT YEAR_BUILT [CONDITION]")
