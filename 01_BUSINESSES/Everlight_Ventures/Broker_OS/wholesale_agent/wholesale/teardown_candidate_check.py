"""Teardown-candidate gate.

Used by L1/L2/L5 lanes to auto-switch a property to the teardown_80pct offer
strategy when the buy-box matches. Also used by L6 scout to filter its own
pipeline.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TeardownDecision:
    is_candidate: bool
    reasons: list  # one string per check that passed or failed
    market_code: str = "DEFAULT"


# Keywords in a listing description that strongly signal teardown status.
TEARDOWN_KEYWORDS = (
    "teardown", "tear-down", "tear down",
    "land value", "land-value",
    "needs demo", "ready to demo",
    "estate sale",
    "as-is", "as is",
    "investor special",
    "build your dream",
)

# Starter markets where we have builder segment buyers.
SUPPORTED_MARKET_CODES = {
    ("phoenix", "AZ"): "PHX",
    ("scottsdale", "AZ"): "PHX",
    ("dallas", "TX"): "DAL",
    ("plano", "TX"): "DAL",
    ("atlanta", "GA"): "ATL",
    ("decatur", "GA"): "ATL",
    ("nashville", "TN"): "NASH",
}


def is_teardown_candidate(prop: dict) -> TeardownDecision:
    """Run the teardown buy-box checks against a property dict.

    Expected keys: lot_sqft, structure_sqft, year_built, assessed_value,
    city, state, description (optional), historic_district (optional).
    """
    reasons = []

    lot_sqft = _f(prop.get("lot_sqft"))
    if lot_sqft < 6000:
        reasons.append(f"FAIL: lot_sqft {lot_sqft} below 6000")
    else:
        reasons.append(f"pass: lot_sqft {lot_sqft}")

    structure_sqft = _f(prop.get("structure_sqft") or prop.get("sqft"))
    if structure_sqft == 0 or structure_sqft > 1500:
        reasons.append(f"FAIL: structure_sqft {structure_sqft} above 1500")
    else:
        reasons.append(f"pass: structure_sqft {structure_sqft}")

    year_built = int(prop.get("year_built") or 0)
    desc = (prop.get("description") or "").lower()
    keyword_match = any(kw in desc for kw in TEARDOWN_KEYWORDS)
    if year_built and year_built < 1980:
        reasons.append(f"pass: year_built {year_built}")
    elif keyword_match:
        reasons.append("pass: teardown keyword in description")
    else:
        reasons.append(f"FAIL: year_built {year_built} not < 1980 and no teardown keyword")

    assessed = _f(prop.get("assessed_value"))
    if assessed <= 0:
        reasons.append("FAIL: no assessed_value on record")
    else:
        reasons.append(f"pass: assessed_value ${assessed:,.0f}")

    city = (prop.get("city") or "").strip().lower()
    state = (prop.get("state") or "").strip().upper()
    market_code = SUPPORTED_MARKET_CODES.get((city, state), "")
    if not market_code:
        reasons.append(f"FAIL: {city}, {state} not in supported builder markets")
        market_code = "DEFAULT"
    else:
        reasons.append(f"pass: market {market_code}")

    if prop.get("historic_district"):
        reasons.append("FAIL: historic_district flag set")

    is_candidate = all(not r.startswith("FAIL") for r in reasons)
    return TeardownDecision(is_candidate=is_candidate, reasons=reasons, market_code=market_code)


def _f(val) -> float:
    if val is None:
        return 0.0
    try:
        if isinstance(val, str):
            val = val.replace("$", "").replace(",", "").strip()
        return float(val)
    except (ValueError, TypeError):
        return 0.0
