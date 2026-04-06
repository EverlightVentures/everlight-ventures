"""
Rex Buyer Segmenter -- segment the buyers list so the right deals
go to the right buyers instead of blasting everyone identically.

Reads buyers_db.json, infers segment fields from existing data
(company name, market, buy_criteria), and provides match/rank
functions for deal targeting.

Usage:
    from rex_buyer_segmenter import segment_buyers, match_buyers_to_deal, get_priority_buyers

    # One-time: enrich buyers_db.json with segment fields
    segment_buyers()

    # Per deal: get ranked matches
    deal = {"city": "Atlanta", "state": "GA", "contract_price": 85000, ...}
    matched = match_buyers_to_deal(deal)
    top10 = get_priority_buyers(deal, top_n=10)
"""

import json
import logging
import re
from pathlib import Path
from typing import Optional

logging.basicConfig(level=logging.INFO, format="[Segmenter %(asctime)s] %(message)s", datefmt="%H:%M")
log = logging.getLogger("rex_buyer_segmenter")

AGENT_DIR = Path(__file__).parent
BUYERS_DB = AGENT_DIR / "buyers_db.json"


# ---------------------------------------------------------------------------
# KEYWORD MAPS for inference
# ---------------------------------------------------------------------------

_PROPERTY_TYPE_KEYWORDS = {
    "sfr": ["sfr", "single family", "house", "home", "residential", "single-family"],
    "multifamily": ["multifamily", "multi-family", "duplex", "triplex", "fourplex", "apartment", "multi"],
    "land": ["land", "lot", "vacant", "acreage"],
    "teardown": ["teardown", "tear-down", "demo", "tear down", "knockdown"],
}

_REHAB_KEYWORDS = {
    "heavy": ["any condition", "as-is", "as is", "distressed", "fire damage", "heavy rehab", "gut"],
    "light": ["light rehab", "cosmetic", "turnkey", "move-in", "light"],
}

_SPEED_KEYWORDS = {
    "7_days": ["7 day", "quick close", "fast close", "immediate", "cash close"],
    "14_days": ["14 day", "two week", "2 week"],
    "30_days": ["30 day", "standard", "flexible"],
}

# Market city normalization
_MARKET_ALIASES = {
    "atl": "Atlanta",
    "atlanta": "Atlanta",
    "atlanta metro": "Atlanta",
    "dallas": "Dallas",
    "dfw": "Dallas",
    "dallas-fort worth": "Dallas",
    "dallas fort worth": "Dallas",
    "cleveland": "Cleveland",
    "cle": "Cleveland",
    "charlotte": "Charlotte",
    "clt": "Charlotte",
    "st. louis": "St. Louis",
    "st louis": "St. Louis",
    "stl": "St. Louis",
    "saint louis": "St. Louis",
    "jacksonville": "Jacksonville",
    "jax": "Jacksonville",
}


# ---------------------------------------------------------------------------
# LOADING / SAVING
# ---------------------------------------------------------------------------

def _load_buyers() -> list:
    """Load the buyers database."""
    if not BUYERS_DB.exists():
        log.error("buyers_db.json not found at %s", BUYERS_DB)
        return []
    with open(BUYERS_DB, "r") as f:
        return json.load(f)


def _save_buyers(buyers: list) -> None:
    """Write buyers back to disk."""
    with open(BUYERS_DB, "w") as f:
        json.dump(buyers, f, indent=2)
    log.info("Saved %d buyers to %s", len(buyers), BUYERS_DB)


# ---------------------------------------------------------------------------
# INFERENCE ENGINE
# ---------------------------------------------------------------------------

def _infer_markets(buyer: dict) -> list:
    """Infer preferred markets from market field, city, and buy_criteria."""
    markets = set()
    raw_texts = [
        buyer.get("market", ""),
        buyer.get("city", ""),
        buyer.get("buy_criteria", ""),
        buyer.get("company", ""),
    ]
    combined = " ".join(str(t) for t in raw_texts).lower()

    for alias, canonical in _MARKET_ALIASES.items():
        if alias in combined:
            markets.add(canonical)

    # Fallback: use the market field directly if we got nothing
    if not markets and buyer.get("market"):
        markets.add(buyer["market"])

    return sorted(markets)


def _infer_property_types(buyer: dict) -> list:
    """Infer property types from buy_criteria and company name."""
    criteria = " ".join([
        str(buyer.get("buy_criteria", "")),
        str(buyer.get("company", "")),
    ]).lower()

    types = set()
    for ptype, keywords in _PROPERTY_TYPE_KEYWORDS.items():
        for kw in keywords:
            if kw in criteria:
                types.add(ptype)
                break

    # Default to SFR if nothing detected (most wholesale buyers want SFR)
    if not types:
        types.add("sfr")

    return sorted(types)


def _infer_rehab_tolerance(buyer: dict) -> str:
    """Infer rehab tolerance from buy_criteria."""
    criteria = str(buyer.get("buy_criteria", "")).lower()

    for level, keywords in _REHAB_KEYWORDS.items():
        for kw in keywords:
            if kw in criteria:
                return level

    # Default: any (most cash buyers can handle rehab)
    return "any"


def _infer_close_speed(buyer: dict) -> str:
    """Infer close speed from buy_criteria and company name."""
    combined = " ".join([
        str(buyer.get("buy_criteria", "")),
        str(buyer.get("company", "")),
    ]).lower()

    for speed, keywords in _SPEED_KEYWORDS.items():
        for kw in keywords:
            if kw in combined:
                return speed

    # Most cash buyers can close in 14 days
    return "14_days"


def _infer_price_range(buyer: dict) -> tuple:
    """
    Infer price range from buy_criteria text.
    Returns (min, max) as integers.
    """
    criteria = str(buyer.get("buy_criteria", "")).lower()

    # Look for dollar amounts in the text
    amounts = re.findall(r'\$?([\d,]+)k?', criteria)
    parsed = []
    for amt in amounts:
        cleaned = amt.replace(",", "")
        try:
            val = int(cleaned)
            # If it ends with 'k' or is suspiciously small, multiply
            if val < 1000:
                val *= 1000
            parsed.append(val)
        except ValueError:
            continue

    if len(parsed) >= 2:
        return (min(parsed), max(parsed))
    elif len(parsed) == 1:
        # Single number -- assume +/- 30%
        val = parsed[0]
        return (int(val * 0.7), int(val * 1.3))

    # Default ranges by market tier
    market = str(buyer.get("market", "")).lower()
    if market in ("atlanta", "dallas", "charlotte", "jacksonville"):
        return (50000, 300000)
    elif market in ("cleveland", "st. louis"):
        return (20000, 200000)

    return (30000, 250000)


# ---------------------------------------------------------------------------
# SEGMENTATION
# ---------------------------------------------------------------------------

def segment_buyers() -> list:
    """
    Analyze all buyers and add segmentation fields.
    Writes the enriched data back to buyers_db.json.
    Returns the enriched buyer list.
    """
    buyers = _load_buyers()
    if not buyers:
        return []

    enriched = 0
    for buyer in buyers:
        buyer["preferred_markets"] = _infer_markets(buyer)
        buyer["property_types"] = _infer_property_types(buyer)
        buyer["rehab_tolerance"] = _infer_rehab_tolerance(buyer)
        buyer["close_speed"] = _infer_close_speed(buyer)

        price_min, price_max = _infer_price_range(buyer)
        buyer["price_range_min"] = price_min
        buyer["price_range_max"] = price_max

        enriched += 1

    _save_buyers(buyers)
    log.info("Segmented %d buyers", enriched)
    return buyers


# ---------------------------------------------------------------------------
# MATCHING
# ---------------------------------------------------------------------------

def _score_buyer(buyer: dict, deal: dict) -> float:
    """
    Score a buyer against a deal. Higher = better match.
    Returns 0 if the buyer is disqualified.
    """
    score = 0.0
    deal_city = deal.get("city", "").strip()
    deal_state = deal.get("state", "").strip()
    contract_price = int(deal.get("contract_price", 0))
    assignment_fee = int(deal.get("assignment_fee", 0))
    buyer_price = contract_price + assignment_fee

    # -- Market match (critical) --
    preferred = buyer.get("preferred_markets", [])
    if preferred:
        # Normalize deal city
        deal_market = _MARKET_ALIASES.get(deal_city.lower(), deal_city)
        if deal_market in preferred:
            score += 40  # Strong market match
        else:
            # Not in their market -- still send but low priority
            score += 5
    else:
        score += 15  # No preference = open buyer

    # -- Price range match --
    price_min = buyer.get("price_range_min", 0)
    price_max = buyer.get("price_range_max", 999999999)
    if price_min <= buyer_price <= price_max:
        score += 25
    elif buyer_price < price_min * 0.8 or buyer_price > price_max * 1.2:
        score += 0  # Way outside range
    else:
        score += 10  # Close enough

    # -- Property type match --
    deal_type = deal.get("property_type", "sfr").lower()
    buyer_types = buyer.get("property_types", ["sfr"])
    if deal_type in buyer_types:
        score += 15
    else:
        score += 3

    # -- Rehab tolerance --
    deal_rehab = deal.get("rehab_level", "heavy").lower()
    buyer_rehab = buyer.get("rehab_tolerance", "any")
    if buyer_rehab == "any":
        score += 10
    elif buyer_rehab == deal_rehab:
        score += 10
    elif buyer_rehab == "heavy":
        score += 8  # Heavy tolerance covers light too
    else:
        score += 2  # Light buyer + heavy deal = unlikely

    # -- Close speed bonus --
    speed = buyer.get("close_speed", "14_days")
    if speed == "7_days":
        score += 5  # Fast closers get a bonus

    # -- Track record bonus --
    deals_closed = buyer.get("deals_closed", 0)
    if deals_closed >= 3:
        score += 10
    elif deals_closed >= 1:
        score += 5

    # -- Responsiveness bonus --
    if buyer.get("responded"):
        score += 5

    # -- Penalize inactive --
    if buyer.get("status") == "dead":
        score = 0

    return score


def match_buyers_to_deal(deal: dict) -> list:
    """
    Return all buyers ranked by match score for a given deal.
    Each entry: {**buyer_fields, "_match_score": float}
    """
    buyers = _load_buyers()
    if not buyers:
        return []

    scored = []
    for buyer in buyers:
        s = _score_buyer(buyer, deal)
        if s > 0:
            entry = dict(buyer)
            entry["_match_score"] = s
            scored.append(entry)

    scored.sort(key=lambda x: x["_match_score"], reverse=True)
    return scored


def get_priority_buyers(deal: dict, top_n: int = 10) -> list:
    """
    Return the top N buyers most likely to close this deal.
    These buyers get a 2-hour head start before the blast goes to everyone.
    """
    all_matched = match_buyers_to_deal(deal)
    return all_matched[:top_n]


def get_blast_schedule(deal: dict, priority_window_hours: int = 2, top_n: int = 10) -> dict:
    """
    Return a blast schedule with priority and general tiers.

    Returns:
        {
            "priority": [list of top_n buyers -- send immediately],
            "general": [remaining buyers -- send after priority_window_hours],
            "priority_window_hours": int,
            "total_recipients": int,
        }
    """
    all_matched = match_buyers_to_deal(deal)
    priority = all_matched[:top_n]
    general = all_matched[top_n:]

    priority_emails = {b["email"] for b in priority}
    # Deduplicate general against priority
    general = [b for b in general if b["email"] not in priority_emails]

    return {
        "priority": priority,
        "general": general,
        "priority_window_hours": priority_window_hours,
        "total_recipients": len(priority) + len(general),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "segment":
        buyers = segment_buyers()
        print(f"Segmented {len(buyers)} buyers.")
        # Show a sample
        if buyers:
            b = buyers[0]
            print(f"\nSample -- {b['name']}:")
            print(f"  Markets:    {b.get('preferred_markets')}")
            print(f"  Types:      {b.get('property_types')}")
            print(f"  Rehab:      {b.get('rehab_tolerance')}")
            print(f"  Speed:      {b.get('close_speed')}")
            print(f"  Price:      {b.get('price_range_min')} - {b.get('price_range_max')}")
    else:
        # Demo matching
        print("Running segmentation first...")
        segment_buyers()

        demo_deal = {
            "address": "1234 Elm St",
            "city": "Atlanta",
            "state": "GA",
            "contract_price": 85000,
            "assignment_fee": 10000,
            "property_type": "sfr",
            "rehab_level": "heavy",
        }
        print(f"\nMatching deal: {demo_deal['address']}, {demo_deal['city']}")
        print(f"Buyer price: ${demo_deal['contract_price'] + demo_deal['assignment_fee']:,}")
        print("-" * 50)

        schedule = get_blast_schedule(demo_deal)
        print(f"\nTotal recipients: {schedule['total_recipients']}")
        print(f"Priority tier ({len(schedule['priority'])} buyers -- send NOW):")
        for b in schedule["priority"]:
            print(f"  {b['name']:35s}  score={b['_match_score']:.0f}  market={b.get('market','?')}")

        print(f"\nGeneral tier ({len(schedule['general'])} buyers -- send after {schedule['priority_window_hours']}h):")
        for b in schedule["general"][:5]:
            print(f"  {b['name']:35s}  score={b['_match_score']:.0f}  market={b.get('market','?')}")
        if len(schedule["general"]) > 5:
            print(f"  ... and {len(schedule['general']) - 5} more")
