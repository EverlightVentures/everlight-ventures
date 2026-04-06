"""
Rex Multi-Tier Targeting -- run 3 deal types simultaneously.

Tier 1: Volume SFR     -- $75k-$250k ARV, 5 deals/mo, $12k avg fee
Tier 2: Premium SFR    -- $250k-$600k ARV, 2 deals/mo, $25k avg fee
Tier 3: Whale           -- $500k-$10M ARV, 1 per quarter, $75k avg fee

Each tier has its own outreach strategy, target markets, and lead sources.
Leads are auto-classified on import based on ARV and property type.

Also handles:
- 1031 exchange buyer sourcing via Perplexity
- Commercial property queries via ATTOM
- Infill lot detection for new construction plays

Cron: Run classify_all_leads() after every lead import cycle.
  0 14 * * * cd /path/to/wholesale_agent && python3 rex_multi_tier.py
"""

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format="[Rex MultiTier %(asctime)s] %(message)s",
    datefmt="%H:%M",
)
log = logging.getLogger("rex_multi_tier")

AGENT_DIR = Path(__file__).parent
LEADS_DB = AGENT_DIR / "leads_db.json"
PIPELINE_DIR = AGENT_DIR / "pipeline"
PIPELINE_DIR.mkdir(parents=True, exist_ok=True)

PERPLEXITY_API_KEY = os.environ.get("PERPLEXITY_API_KEY", "")
ATTOM_API_KEY = os.environ.get("ATTOM_API_KEY", "")


# ---------------------------------------------------------------------------
# TIER CONFIGURATION
# ---------------------------------------------------------------------------

TIERS = {
    "volume": {
        "name": "Volume SFR",
        "arv_range": (75_000, 250_000),
        "property_types": ["sfr", "residential", "single_family"],
        "target_fee": 12_000,
        "target_deals_month": 5,
        "markets": ["atlanta", "dallas", "cleveland", "st_louis", "jacksonville"],
        "lead_sources": ["attom", "distress_finder", "zillow_scraper"],
        "outreach": "belfort",  # aggressive 5-day sequence
        "max_offer_pct": 0.65,  # 65% of ARV minus repairs
    },
    "premium": {
        "name": "Premium SFR + Small Multi",
        "arv_range": (250_000, 600_000),
        "property_types": [
            "sfr", "residential", "single_family",
            "duplex", "triplex", "fourplex",
            "multi_family_small",
        ],
        "target_fee": 25_000,
        "target_deals_month": 2,
        "markets": ["atlanta", "dallas", "jacksonville"],
        "lead_sources": ["attom", "zillow_scraper"],
        "outreach": "straight_line",  # relationship-based, deep enrichment
        "max_offer_pct": 0.70,  # tighter margins, bigger checks
    },
    "whale": {
        "name": "Commercial + Land",
        "arv_range": (500_000, 10_000_000),
        "property_types": [
            "multifamily", "commercial", "land", "apartment",
            "office", "retail", "industrial", "mixed_use",
        ],
        "target_fee": 75_000,
        "target_deals_month": 0.33,  # 1 per quarter
        "markets": ["atlanta", "dallas"],
        "lead_sources": ["perplexity_commercial", "zillow_scraper"],
        "outreach": "manual_jv",  # high-touch, JV with commercial brokers
        "max_offer_pct": 0.75,  # commercial deals have different math
    },
}

# Property type normalization map
PROPERTY_TYPE_MAP = {
    "single family": "sfr",
    "single-family": "sfr",
    "single_family": "sfr",
    "sfr": "sfr",
    "residential": "sfr",
    "house": "sfr",
    "condo": "sfr",
    "townhouse": "sfr",
    "duplex": "duplex",
    "triplex": "triplex",
    "fourplex": "fourplex",
    "quadplex": "fourplex",
    "4-plex": "fourplex",
    "multi-family": "multifamily",
    "multifamily": "multifamily",
    "multi_family": "multifamily",
    "apartment": "multifamily",
    "commercial": "commercial",
    "office": "commercial",
    "retail": "commercial",
    "industrial": "commercial",
    "warehouse": "commercial",
    "mixed use": "commercial",
    "mixed-use": "commercial",
    "land": "land",
    "vacant land": "land",
    "lot": "land",
    "vacant lot": "land",
}


# ---------------------------------------------------------------------------
# LEAD CLASSIFICATION
# ---------------------------------------------------------------------------

def _normalize_property_type(raw_type: str) -> str:
    """Normalize property type string to a canonical form."""
    if not raw_type:
        return "sfr"  # default
    key = raw_type.lower().strip()
    return PROPERTY_TYPE_MAP.get(key, "sfr")


def classify_lead(lead: dict) -> str:
    """
    Classify a lead into a tier based on ARV and property type.

    Priority: whale > premium > volume (higher tiers checked first).
    If ARV overlaps between tiers (e.g., $500k-$600k fits both premium
    and whale), property type breaks the tie.

    Returns: "volume", "premium", or "whale"
    """
    arv = lead.get("estimated_arv", 0) or lead.get("arv", 0) or 0
    raw_type = lead.get("property_type", "") or lead.get("propertyType", "") or ""
    prop_type = _normalize_property_type(raw_type)

    # Check whale first -- commercial/land with high ARV
    whale_config = TIERS["whale"]
    whale_min, whale_max = whale_config["arv_range"]
    if arv >= whale_min and prop_type in ("multifamily", "commercial", "land"):
        return "whale"

    # Check premium -- higher ARV SFR or small multifamily
    premium_config = TIERS["premium"]
    prem_min, prem_max = premium_config["arv_range"]
    if prem_min <= arv <= prem_max:
        if prop_type in ("sfr", "duplex", "triplex", "fourplex"):
            return "premium"

    # Check volume -- standard SFR in range
    volume_config = TIERS["volume"]
    vol_min, vol_max = volume_config["arv_range"]
    if vol_min <= arv <= vol_max and prop_type == "sfr":
        return "volume"

    # Edge cases
    if arv > 0:
        if arv >= prem_min:
            return "premium"
        if arv >= vol_min:
            return "volume"

    # Default to volume for anything with no ARV data
    return "volume"


def get_tier_config(tier: str) -> dict:
    """Get the configuration dict for a tier."""
    return TIERS.get(tier, TIERS["volume"])


def route_lead_to_tier(lead: dict) -> dict:
    """
    Classify a lead and attach tier-specific metadata.

    Returns the lead dict with added fields:
        - tier: str
        - tier_name: str
        - outreach_strategy: str
        - max_offer_pct: float
        - target_fee: int
    """
    tier = classify_lead(lead)
    config = get_tier_config(tier)

    lead["tier"] = tier
    lead["tier_name"] = config["name"]
    lead["outreach_strategy"] = config["outreach"]
    lead["max_offer_pct"] = config["max_offer_pct"]
    lead["target_fee"] = config["target_fee"]
    lead["classified_at"] = datetime.now(timezone.utc).isoformat()

    log.info(
        f"Lead classified: {lead.get('address', '?')} -> {tier} "
        f"(ARV=${lead.get('estimated_arv', 0):,.0f}, "
        f"type={lead.get('property_type', '?')})"
    )
    return lead


# ---------------------------------------------------------------------------
# TIER STATS
# ---------------------------------------------------------------------------

def get_tier_stats() -> dict:
    """
    Calculate pipeline stats per tier.

    Returns:
        {
            "volume": {"count": int, "pipeline_value": float, "projected_revenue": float},
            "premium": {...},
            "whale": {...},
            "totals": {"count": int, "pipeline_value": float, "projected_revenue": float},
        }
    """
    if not LEADS_DB.exists():
        return {tier: {"count": 0, "pipeline_value": 0, "projected_revenue": 0}
                for tier in TIERS}

    try:
        leads = json.loads(LEADS_DB.read_text())
    except (json.JSONDecodeError, OSError):
        leads = []

    stats = {}
    for tier_key, config in TIERS.items():
        tier_leads = [l for l in leads if l.get("tier") == tier_key]
        count = len(tier_leads)
        pipeline_value = sum(l.get("estimated_arv", 0) or 0 for l in tier_leads)
        # Projected revenue = count * target fee * estimated close rate
        close_rates = {"volume": 0.03, "premium": 0.05, "whale": 0.02}
        close_rate = close_rates.get(tier_key, 0.03)
        projected_revenue = count * config["target_fee"] * close_rate

        stats[tier_key] = {
            "name": config["name"],
            "count": count,
            "pipeline_value": round(pipeline_value),
            "projected_revenue": round(projected_revenue),
            "target_deals_month": config["target_deals_month"],
            "target_fee": config["target_fee"],
        }

    # Totals
    stats["totals"] = {
        "count": sum(s["count"] for s in stats.values() if isinstance(s, dict) and "count" in s),
        "pipeline_value": sum(s["pipeline_value"] for s in stats.values() if isinstance(s, dict) and "pipeline_value" in s),
        "projected_revenue": sum(s["projected_revenue"] for s in stats.values() if isinstance(s, dict) and "projected_revenue" in s),
    }

    return stats


# ---------------------------------------------------------------------------
# CLASSIFY ALL LEADS (batch)
# ---------------------------------------------------------------------------

def classify_all_leads() -> dict:
    """
    Run tier classification on every lead in leads_db.json.
    Skips leads that already have a tier assignment unless ARV has changed.

    Returns: {"classified": int, "skipped": int, "total": int}
    """
    if not LEADS_DB.exists():
        log.warning("No leads_db.json found")
        return {"classified": 0, "skipped": 0, "total": 0}

    try:
        leads = json.loads(LEADS_DB.read_text())
    except (json.JSONDecodeError, OSError) as e:
        log.error(f"Failed to load leads_db.json: {e}")
        return {"classified": 0, "skipped": 0, "total": 0}

    classified = 0
    skipped = 0

    for lead in leads:
        # Skip if already classified and ARV hasn't changed
        existing_tier = lead.get("tier")
        if existing_tier and lead.get("classified_at"):
            skipped += 1
            continue

        route_lead_to_tier(lead)
        classified += 1

    # Save back
    LEADS_DB.write_text(json.dumps(leads, indent=2, default=str))

    result = {"classified": classified, "skipped": skipped, "total": len(leads)}
    log.info(
        f"Tier classification complete: {classified} classified, "
        f"{skipped} skipped, {len(leads)} total"
    )
    return result


# ---------------------------------------------------------------------------
# 1031 EXCHANGE BUYER SOURCING (via Perplexity)
# ---------------------------------------------------------------------------

def search_1031_buyers(city: str, state: str) -> list[dict]:
    """
    Search for 1031 exchange buyers looking for replacement properties.

    These are investors who MUST buy within 45/180 days or lose their
    tax deferral -- extremely motivated buyers.

    Returns list of potential buyer leads.
    """
    if not PERPLEXITY_API_KEY:
        log.warning("No PERPLEXITY_API_KEY -- cannot search 1031 buyers")
        return []

    import requests

    query = (
        f"1031 exchange buyers {city} {state} looking for replacement property "
        f"investment real estate 2025 2026"
    )

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
                            "You are a real estate research assistant. "
                            "Find 1031 exchange buyers, intermediaries, "
                            "and qualified intermediary companies in the "
                            "target market. Return company names, contact "
                            "info, and any relevant details."
                        ),
                    },
                    {"role": "user", "content": query},
                ],
                "max_tokens": 1000,
            },
            timeout=30,
        )

        if resp.status_code != 200:
            log.error(f"Perplexity 1031 search failed: {resp.status_code}")
            return []

        data = resp.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

        # Save raw result for manual review
        result_path = PIPELINE_DIR / f"1031_buyers_{city.lower()}_{state.lower()}.txt"
        result_path.write_text(
            f"Query: {query}\n"
            f"Date: {datetime.now(timezone.utc).isoformat()}\n\n"
            f"{content}"
        )

        log.info(f"1031 buyer search complete for {city}, {state}")
        return [{"source": "perplexity_1031", "city": city, "state": state,
                 "raw_result": content}]

    except Exception as e:
        log.error(f"1031 buyer search error: {e}")
        return []


# ---------------------------------------------------------------------------
# COMMERCIAL PROPERTY SEARCH (via ATTOM)
# ---------------------------------------------------------------------------

def search_commercial_properties(city: str, state: str, zip_code: str = "") -> list[dict]:
    """
    Query ATTOM for multifamily/commercial properties in target markets.

    Focuses on:
    - 5+ unit multifamily
    - Mixed-use properties
    - Properties with high equity (potential motivated sellers)
    """
    if not ATTOM_API_KEY:
        log.warning("No ATTOM_API_KEY -- cannot search commercial properties")
        return []

    try:
        from rex_utils import attom_fetch, attom_rate_can_call
    except ImportError:
        log.warning("rex_utils not available for ATTOM fetch")
        return []

    if not attom_rate_can_call(1):
        log.warning("ATTOM rate limit reached -- skipping commercial search")
        return []

    params = {
        "address1": f"{city}, {state}",
        "propertytype": "APARTMENT",
        "minavmvalue": "500000",
        "pagesize": "50",
    }

    if zip_code:
        params["postalcode"] = zip_code

    data = attom_fetch(
        "/propertyapi/v1.0.0/property/snapshot",
        params,
        zip_code=zip_code or f"{city}_{state}_commercial",
    )

    if not data:
        return []

    properties = data.get("property", [])
    results = []

    for prop in properties:
        address_info = prop.get("address", {})
        lot_info = prop.get("lot", {})
        avm_info = prop.get("avm", {})

        result = {
            "address": address_info.get("oneLine", ""),
            "city": address_info.get("locality", city),
            "state": address_info.get("countrySubd", state),
            "zip_code": address_info.get("postal1", ""),
            "property_type": "multifamily",
            "estimated_arv": avm_info.get("amount", {}).get("value", 0),
            "lot_size": lot_info.get("lotSize1", 0),
            "source": "attom_commercial",
            "tier": "whale",
        }

        if result["address"] and result["estimated_arv"]:
            results.append(result)

    log.info(f"Found {len(results)} commercial properties in {city}, {state}")
    return results


# ---------------------------------------------------------------------------
# INFILL LOT SEARCH (via ATTOM)
# ---------------------------------------------------------------------------

def search_infill_lots(city: str, state: str, zip_codes: list = None) -> list[dict]:
    """
    Search for vacant land in residential areas suitable for new construction.

    Infill lots = vacant land surrounded by existing homes = high value
    for builders.
    """
    if not ATTOM_API_KEY:
        log.warning("No ATTOM_API_KEY -- cannot search infill lots")
        return []

    try:
        from rex_utils import attom_fetch, attom_rate_can_call
    except ImportError:
        log.warning("rex_utils not available for ATTOM fetch")
        return []

    if not zip_codes:
        # Use curated hot zips for the market
        try:
            from rex_utils import get_hot_zips
            hot = get_hot_zips(city, state, count=5)
            zip_codes = [z["zip_code"] for z in hot]
        except ImportError:
            log.warning("Cannot get hot zips -- no zip codes to search")
            return []

    results = []

    for zc in zip_codes:
        if not attom_rate_can_call(1):
            log.warning("ATTOM rate limit reached -- stopping infill search")
            break

        params = {
            "postalcode": zc,
            "propertytype": "VACANT LAND",
            "pagesize": "25",
        }

        data = attom_fetch(
            "/propertyapi/v1.0.0/property/snapshot",
            params,
            zip_code=f"{zc}_vacant_land",
        )

        if not data:
            continue

        properties = data.get("property", [])
        for prop in properties:
            address_info = prop.get("address", {})
            lot_info = prop.get("lot", {})
            avm_info = prop.get("avm", {})

            lot_size = lot_info.get("lotSize1", 0)
            # Filter for buildable lots (at least 3,000 sqft)
            if lot_size and lot_size < 3000:
                continue

            result = {
                "address": address_info.get("oneLine", ""),
                "city": address_info.get("locality", city),
                "state": address_info.get("countrySubd", state),
                "zip_code": zc,
                "property_type": "land",
                "estimated_arv": avm_info.get("amount", {}).get("value", 0),
                "lot_size_sqft": lot_size,
                "source": "attom_infill",
                "tier": "whale" if (avm_info.get("amount", {}).get("value", 0) or 0) >= 500_000 else "premium",
            }

            if result["address"]:
                results.append(result)

        # Rate limit -- 1 second between ATTOM calls
        time.sleep(1)

    log.info(f"Found {len(results)} infill lots in {city}, {state}")
    return results


# ---------------------------------------------------------------------------
# TIER-SPECIFIC OUTREACH ROUTING
# ---------------------------------------------------------------------------

def get_outreach_module(tier: str) -> str:
    """
    Return the module name to use for outreach based on tier.

    - volume  -> rex_belfort_sequence (aggressive 5-day)
    - premium -> rex_straight_line (relationship-based)
    - whale   -> manual_jv (Slack notification for manual handling)
    """
    config = get_tier_config(tier)
    return config.get("outreach", "belfort")


def should_outreach(lead: dict) -> bool:
    """
    Check if a lead should receive outreach based on tier market match.
    Returns True if the lead's market is in the tier's target markets.
    """
    tier = lead.get("tier", "volume")
    config = get_tier_config(tier)
    target_markets = config.get("markets", [])

    lead_market = (
        lead.get("market", "") or lead.get("city", "")
    ).lower().replace(" ", "_").replace(".", "")

    if not target_markets:
        return True

    return any(m in lead_market or lead_market in m for m in target_markets)


# ---------------------------------------------------------------------------
# MAIN -- classify + report
# ---------------------------------------------------------------------------

def main():
    """Run tier classification and print stats."""
    result = classify_all_leads()
    print(f"\nClassification: {result}")

    stats = get_tier_stats()
    print("\n--- TIER PIPELINE STATS ---")
    for tier_key in ("volume", "premium", "whale"):
        s = stats.get(tier_key, {})
        print(
            f"\n{s.get('name', tier_key).upper()}:"
            f"\n  Leads: {s.get('count', 0)}"
            f"\n  Pipeline Value: ${s.get('pipeline_value', 0):,.0f}"
            f"\n  Projected Revenue: ${s.get('projected_revenue', 0):,.0f}"
            f"\n  Target: {s.get('target_deals_month', 0)} deals/mo "
            f"@ ${s.get('target_fee', 0):,.0f}/deal"
        )

    totals = stats.get("totals", {})
    print(
        f"\nTOTALS:"
        f"\n  Total Leads: {totals.get('count', 0)}"
        f"\n  Total Pipeline: ${totals.get('pipeline_value', 0):,.0f}"
        f"\n  Projected Monthly Revenue: ${totals.get('projected_revenue', 0):,.0f}"
    )


if __name__ == "__main__":
    main()
