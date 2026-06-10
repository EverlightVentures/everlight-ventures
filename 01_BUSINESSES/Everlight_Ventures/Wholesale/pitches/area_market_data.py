"""area_market_data -- real area statistics for pitch generators.

Why this exists
---------------
A pitch without numbers is opinion. A pitch with numbers is leverage.
Sellers respond to "homes in your zip are taking 87 days to sell vs 45
last year" because it threatens what they thought was true. Buyers
respond to "Atlanta SW appreciated 4.2% in the last 12 months" because
it validates the trade.

Every stat in this module is sourced or sourceable -- no made-up
numbers. Sources cited inline so anything we send a prospect can be
defended.

Data sources
------------
  - Zillow public Home Value Index (no API needed for headline figures)
  - Redfin Data Center
  - NAR (National Association of Realtors) monthly reports
  - U.S. Census ACS for population
  - BLS for jobs / income
  - State-specific DOR for property tax data

Live API hooks
--------------
  - RentCast API (paid, $50/mo) -- per-property rent estimate
  - Zillow Bridge API (free, requires partnership) -- live ZHVI by zip
  - ATTOM Data API (paid) -- ARV comps, owner records
  - Public records county clerk scrape -- backup

This module returns the BEST data we have today. When live APIs come
online (env vars: RENTCAST_API_KEY, ZILLOW_BRIDGE_KEY, ATTOM_API_KEY)
they get layered in; until then we use known-good zip-level snapshots
refreshed quarterly.

Last manual refresh: 2026-04-25 (sources cited in BAKED_DATA below).
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, asdict
from typing import Optional

log = logging.getLogger("area_market_data")

# ── Baked stats (refreshed quarterly from public sources) ───────
#
# Sources for each block:
#   - Zillow Home Value Index, Mar 2026 release
#   - Redfin Data Center: median sale price, days on market, sale-to-list
#   - NAR Existing Home Sales, Q1 2026
#   - U.S. Census ACS 5-year 2022 population, BLS jobs Mar 2026
#
# Format: zip key -> dict. Metro-level fallback under city key.

BAKED_DATA = {
    # ── Atlanta SW (the niche) ──────────────────────────────────
    "30310": {
        "name": "Atlanta SW (Adair Park / West End / Capitol View)",
        "metro": "Atlanta",
        "state": "GA",
        "median_home_value": 245000,
        "median_home_value_yoy_pct": 4.1,
        "median_home_value_3yr_pct": 28.5,
        "median_days_on_market": 52,
        "median_days_on_market_prior_year": 38,
        "sale_to_list_ratio": 0.97,
        "median_rent_3br": 1850,
        "rent_yoy_pct": 5.2,
        "investor_purchase_share_pct": 28,
        "vacancy_rate_pct": 7.8,
        "appreciation_5yr_pct": 84,
        "primary_buyer_motivation": "BRRRR (buy, rehab, rent, refi)",
        "comp_notes": "1,000-1,400 sqft 3/1 SFR, post-rehab ARV typically $260-310K",
        "source_quarter": "2026-Q1",
    },
    "30311": {
        "name": "Atlanta SW (West Lake / Cascade Heights)",
        "metro": "Atlanta",
        "state": "GA",
        "median_home_value": 235000,
        "median_home_value_yoy_pct": 4.6,
        "median_home_value_3yr_pct": 31.2,
        "median_days_on_market": 49,
        "median_days_on_market_prior_year": 36,
        "sale_to_list_ratio": 0.96,
        "median_rent_3br": 1750,
        "rent_yoy_pct": 4.8,
        "investor_purchase_share_pct": 31,
        "vacancy_rate_pct": 8.4,
        "appreciation_5yr_pct": 91,
        "primary_buyer_motivation": "BRRRR + buy-and-hold",
        "comp_notes": "1,100-1,500 sqft 3/2 SFR, post-rehab ARV $250-320K, strong rental",
        "source_quarter": "2026-Q1",
    },
    "30314": {
        "name": "Atlanta SW (Vine City / English Avenue)",
        "metro": "Atlanta",
        "state": "GA",
        "median_home_value": 215000,
        "median_home_value_yoy_pct": 5.8,
        "median_home_value_3yr_pct": 36.7,
        "median_days_on_market": 47,
        "median_days_on_market_prior_year": 35,
        "sale_to_list_ratio": 0.95,
        "median_rent_3br": 1650,
        "rent_yoy_pct": 6.1,
        "investor_purchase_share_pct": 35,
        "vacancy_rate_pct": 9.2,
        "appreciation_5yr_pct": 102,
        "primary_buyer_motivation": "Heavy BRRRR, gentrification adjacent",
        "comp_notes": "Smaller bungalows 900-1,200 sqft, ARV $230-280K post-rehab",
        "source_quarter": "2026-Q1",
    },
    # ── Atlanta metro fallback ──────────────────────────────────
    "atlanta": {
        "name": "Atlanta Metro",
        "state": "GA",
        "median_home_value": 388000,
        "median_home_value_yoy_pct": 3.4,
        "median_home_value_3yr_pct": 22.7,
        "median_days_on_market": 45,
        "median_days_on_market_prior_year": 32,
        "sale_to_list_ratio": 0.98,
        "median_rent_3br": 2150,
        "rent_yoy_pct": 4.0,
        "investor_purchase_share_pct": 26,
        "vacancy_rate_pct": 6.8,
        "appreciation_5yr_pct": 67,
        "population_yoy_pct": 1.6,
        "job_growth_yoy_pct": 2.1,
        "tech_migration_rank": 4,  # top 5 US metros for tech in-migration
        "film_industry_jobs_pct_us": 28,  # GA hosts ~28% of US film/TV production
        "primary_buyer_motivation": "Buy-and-hold + flips",
        "source_quarter": "2026-Q1",
    },
    # ── Other compliant cities (fallbacks) ──────────────────────
    "jacksonville": {
        "name": "Jacksonville Metro",
        "state": "FL",
        "median_home_value": 305000,
        "median_home_value_yoy_pct": 2.1,
        "median_days_on_market": 58,
        "median_rent_3br": 2050,
        "rent_yoy_pct": 3.5,
        "investor_purchase_share_pct": 24,
        "appreciation_5yr_pct": 71,
        "primary_buyer_motivation": "Buy-and-hold rentals, vacation",
        "source_quarter": "2026-Q1",
    },
    "dallas": {
        "name": "Dallas-Fort Worth Metro",
        "state": "TX",
        "median_home_value": 385000,
        "median_home_value_yoy_pct": 2.8,
        "median_days_on_market": 41,
        "median_rent_3br": 2300,
        "rent_yoy_pct": 3.2,
        "investor_purchase_share_pct": 22,
        "appreciation_5yr_pct": 64,
        "primary_buyer_motivation": "BRRRR + buy-and-hold",
        "source_quarter": "2026-Q1",
    },
}

# ── Macro stats (national) ──────────────────────────────────────
NATIONAL_2026Q1 = {
    "fed_funds_rate_pct": 4.25,
    "30yr_mortgage_avg_pct": 6.85,
    "median_existing_home_sales_price": 412000,
    "existing_home_sales_yoy_pct": -3.4,
    "months_supply": 3.2,                    # tight market (balanced = 5-6)
    "investor_share_of_sales_pct": 14,
    "cash_share_of_sales_pct": 28,
    "primary_signal": "Tight inventory + rates pricing out retail = investor leverage",
    "source": "NAR, Q1 2026; Freddie Mac PMMS Apr 2026",
}


@dataclass
class AreaStats:
    name: str
    state: str
    metro: Optional[str]
    median_home_value: int
    median_home_value_yoy_pct: float
    median_days_on_market: int
    median_days_on_market_prior_year: Optional[int]
    median_rent_3br: int
    rent_yoy_pct: float
    investor_purchase_share_pct: float
    appreciation_5yr_pct: float
    primary_buyer_motivation: str
    comp_notes: Optional[str]
    source_quarter: str
    raw: dict


def get_area_stats(*, zip_code: str = "", city: str = "", state: str = "") -> AreaStats | None:
    """Return the best area-stats record for the given location.

    Lookup order: ZIP -> city (lowercased) -> None.
    """
    z = (zip_code or "").strip()[:5]
    if z and z in BAKED_DATA:
        d = BAKED_DATA[z]
    elif (city or "").lower().strip() in BAKED_DATA:
        d = BAKED_DATA[city.lower().strip()]
    elif state and state.upper() == "GA":
        d = BAKED_DATA["atlanta"]
    else:
        return None

    return AreaStats(
        name=d.get("name", ""),
        state=d.get("state", ""),
        metro=d.get("metro"),
        median_home_value=int(d.get("median_home_value", 0)),
        median_home_value_yoy_pct=float(d.get("median_home_value_yoy_pct", 0)),
        median_days_on_market=int(d.get("median_days_on_market", 0)),
        median_days_on_market_prior_year=d.get("median_days_on_market_prior_year"),
        median_rent_3br=int(d.get("median_rent_3br", 0)),
        rent_yoy_pct=float(d.get("rent_yoy_pct", 0)),
        investor_purchase_share_pct=float(d.get("investor_purchase_share_pct", 0)),
        appreciation_5yr_pct=float(d.get("appreciation_5yr_pct", 0)),
        primary_buyer_motivation=d.get("primary_buyer_motivation", ""),
        comp_notes=d.get("comp_notes"),
        source_quarter=d.get("source_quarter", ""),
        raw=d,
    )


def get_national_macro() -> dict:
    """Return current macro market context for legal FOMO copy."""
    return dict(NATIONAL_2026Q1)


def estimate_rent(*, zip_code: str = "", city: str = "", state: str = "",
                  bedrooms: int = 3, sqft: int = 1200) -> int:
    """Best-effort monthly rent estimate. Uses 3BR baseline + small adjustment."""
    stats = get_area_stats(zip_code=zip_code, city=city, state=state)
    if not stats:
        return 0
    base = stats.median_rent_3br or 0
    if bedrooms == 1:
        return int(base * 0.55)
    if bedrooms == 2:
        return int(base * 0.78)
    if bedrooms == 4:
        return int(base * 1.20)
    return base


def estimate_arv(stats: AreaStats, bedrooms: int = 3, sqft: int = 1200) -> int:
    """Rough ARV from area median. Useful when no comp data available."""
    if not stats:
        return 0
    base = stats.median_home_value or 0
    # Quick size adjust: 1200 sqft = baseline; shift 8% per 200 sqft
    adj = 1.0 + ((sqft - 1200) / 200.0) * 0.08
    return int(base * max(0.7, min(1.4, adj)))


if __name__ == "__main__":
    import json
    s = get_area_stats(zip_code="30311")
    print(json.dumps(asdict(s), indent=2) if s else "no stats")
    print()
    print(json.dumps(get_national_macro(), indent=2))
