#!/usr/bin/env python3
"""
Broker OS -- ATTOM Real Estate API Enrichment

Enriches wholesale property leads with real estate data:
  - Assessed value, market value
  - Last sale price + date
  - Owner name
  - Property type, sq ft, year built, bedrooms, bathrooms
  - Lot size

API Docs: https://api.gateway.attomdata.com/propertyapi/v1.0.0/

Rate limits: 30-day free trial. Cancel by April 16 if no deal closed.
Key from: 03_Credentials/.env -> ATTOM_API_KEY

Usage:
    from broker.attom_enrichment import enrich_property
    data = enrich_property("123 Main St", "Cleveland", "OH", "44101")
"""
import json
import logging
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional

log = logging.getLogger("broker.attom")

# Load API key from env (broker_daily_orchestrator loads .env before importing)
ATTOM_API_KEY = os.environ.get("ATTOM_API_KEY", "8b8f49842c214289928801e9bc67ecc7")
ATTOM_BASE = "https://api.gateway.attomdata.com/propertyapi/v1.0.0"

# Rate limit: ATTOM free tier is ~500 calls/month
_request_log: list[float] = []
RATE_LIMIT_PER_MINUTE = 10
RATE_LIMIT_PER_DAY = 50

_daily_count = {"date": "", "count": 0}


def _check_rate_limit() -> bool:
    """Return True if we're within rate limits."""
    now = time.time()
    today = time.strftime("%Y-%m-%d")

    # Daily limit
    if _daily_count["date"] != today:
        _daily_count["date"] = today
        _daily_count["count"] = 0
    if _daily_count["count"] >= RATE_LIMIT_PER_DAY:
        log.warning("ATTOM daily rate limit hit")
        return False

    # Per-minute limit
    _request_log[:] = [t for t in _request_log if now - t < 60]
    if len(_request_log) >= RATE_LIMIT_PER_MINUTE:
        log.warning("ATTOM per-minute rate limit hit, waiting...")
        time.sleep(6)

    return True


def _attom_request(endpoint: str, params: dict) -> Optional[dict]:
    """Make authenticated GET request to ATTOM API."""
    if not ATTOM_API_KEY:
        log.error("ATTOM_API_KEY not set")
        return None

    if not _check_rate_limit():
        return None

    qs = urllib.parse.urlencode(params)
    url = f"{ATTOM_BASE}/{endpoint}?{qs}"

    req = urllib.request.Request(url, headers={
        "Accept": "application/json",
        "apikey": ATTOM_API_KEY,
    })

    try:
        _request_log.append(time.time())
        _daily_count["count"] += 1

        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode()[:200]
        except Exception:
            pass
        log.error(f"ATTOM HTTP {e.code}: {body}")
        return None
    except Exception as e:
        log.error(f"ATTOM request error: {e}")
        return None


def enrich_property(
    address: str,
    city: str = "",
    state: str = "",
    zipcode: str = "",
) -> Dict[str, Any]:
    """
    Enrich a property address with ATTOM data.

    Returns dict with:
        success: bool
        assessed_value: int or None
        market_value: int or None
        last_sale_price: int or None
        last_sale_date: str or None
        owner_name: str or None
        property_type: str or None
        sqft: int or None
        year_built: int or None
        bedrooms: int or None
        bathrooms: int or None
        lot_size_sqft: int or None
        raw: dict (full ATTOM response for debugging)
    """
    result = {
        "success": False,
        "address": address,
        "assessed_value": None,
        "market_value": None,
        "last_sale_price": None,
        "last_sale_date": None,
        "owner_name": None,
        "property_type": None,
        "sqft": None,
        "year_built": None,
        "bedrooms": None,
        "bathrooms": None,
        "lot_size_sqft": None,
        "raw": {},
    }

    # Build address params
    params = {"address1": address}
    if city:
        params["address2"] = f"{city}, {state} {zipcode}".strip()
    elif zipcode:
        params["address2"] = zipcode

    # Try property detail endpoint first
    data = _attom_request("property/detail", params)
    if not data:
        # Fallback: try expanded profile
        data = _attom_request("property/expandedprofile", params)

    if not data:
        return result

    # Parse response -- ATTOM nests data under property[0]
    properties = data.get("property", [])
    if not properties:
        log.warning(f"ATTOM: no property found for {address}")
        result["raw"] = data
        return result

    prop = properties[0] if isinstance(properties, list) else properties
    result["raw"] = prop

    # Assessment
    assessment = prop.get("assessment", {})
    assessed = assessment.get("assessed", {})
    market = assessment.get("market", {})
    result["assessed_value"] = _safe_int(assessed.get("assdTtlValue"))
    result["market_value"] = _safe_int(market.get("mktTtlValue"))

    # Last sale
    sale = prop.get("sale", prop.get("saleHistory", {}))
    if isinstance(sale, dict):
        amount = sale.get("amount", sale.get("saleAmountData", {}))
        if isinstance(amount, dict):
            result["last_sale_price"] = _safe_int(
                amount.get("saleAmt") or amount.get("salerecamt")
            )
        result["last_sale_date"] = sale.get("saleTransDate") or sale.get("saledate")

    # Owner
    result["owner_name"] = _extract_owner(prop)

    # Building info
    building = prop.get("building", {})
    size_info = building.get("size", {})
    rooms = building.get("rooms", {})
    result["sqft"] = _safe_int(
        size_info.get("livingSize") or size_info.get("bldgSize") or size_info.get("universalSize")
    )
    result["year_built"] = _safe_int(
        building.get("summary", {}).get("yearBuilt") or prop.get("summary", {}).get("yearBuilt")
    )
    result["bedrooms"] = _safe_int(rooms.get("beds") or rooms.get("bathstotal"))
    result["bathrooms"] = _safe_int(rooms.get("bathsTotal") or rooms.get("bathsFull"))

    # Property type
    summary = prop.get("summary", {})
    result["property_type"] = summary.get("propType") or summary.get("propSubType")

    # Lot
    lot = prop.get("lot", {})
    result["lot_size_sqft"] = _safe_int(lot.get("lotSize2") or lot.get("lotSize1"))

    result["success"] = True
    log.info(f"ATTOM enriched: {address} -> assessed=${result['assessed_value']}, sold=${result['last_sale_price']}")
    return result


def _safe_int(val) -> Optional[int]:
    """Safely convert a value to int."""
    if val is None:
        return None
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return None


def _extract_owner(prop: dict) -> Optional[str]:
    """Extract owner name from various ATTOM response formats."""
    # Try direct owner fields
    for key in ("owner", "ownerName"):
        if key in prop and isinstance(prop[key], dict):
            name_parts = []
            for nk in ("owner1", "absenteeOwnerName", "owner1Last", "ownerName"):
                if prop[key].get(nk):
                    return str(prop[key][nk])
            first = prop[key].get("owner1First", "")
            last = prop[key].get("owner1Last", "")
            if first or last:
                return f"{first} {last}".strip()
    return None


def format_enrichment_summary(data: dict) -> str:
    """Format enrichment data for display in broker pipeline."""
    if not data.get("success"):
        return f"ATTOM: No data for {data.get('address', '?')}"

    lines = [f"Property: {data['address']}"]
    if data["assessed_value"]:
        lines.append(f"  Assessed: ${data['assessed_value']:,}")
    if data["market_value"]:
        lines.append(f"  Market Value: ${data['market_value']:,}")
    if data["last_sale_price"]:
        lines.append(f"  Last Sale: ${data['last_sale_price']:,} ({data['last_sale_date'] or '?'})")
    if data["owner_name"]:
        lines.append(f"  Owner: {data['owner_name']}")
    if data["property_type"]:
        lines.append(f"  Type: {data['property_type']}")
    if data["sqft"]:
        lines.append(f"  SqFt: {data['sqft']:,}")
    if data["year_built"]:
        lines.append(f"  Built: {data['year_built']}")
    if data["bedrooms"] or data["bathrooms"]:
        lines.append(f"  Beds/Baths: {data['bedrooms'] or '?'}/{data['bathrooms'] or '?'}")

    return "\n".join(lines)


# CLI test
if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    if len(sys.argv) < 2:
        print("Usage: python attom_enrichment.py '123 Main St' [city] [state] [zip]")
        sys.exit(1)
    addr = sys.argv[1]
    city = sys.argv[2] if len(sys.argv) > 2 else ""
    state = sys.argv[3] if len(sys.argv) > 3 else ""
    zipcode = sys.argv[4] if len(sys.argv) > 4 else ""
    result = enrich_property(addr, city, state, zipcode)
    print(format_enrichment_summary(result))
    if result.get("raw"):
        print("\nRaw ATTOM data:")
        print(json.dumps(result["raw"], indent=2)[:2000])
