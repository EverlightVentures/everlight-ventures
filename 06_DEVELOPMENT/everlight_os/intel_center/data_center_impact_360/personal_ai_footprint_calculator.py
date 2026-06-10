#!/usr/bin/env python3
"""
PERSONAL AI FOOTPRINT CALCULATOR -- Data Center Impact 360
===========================================================
Plug in your own AI usage and see your daily/yearly energy, water, and CO2,
translated into everyday anchors (phone charges, gas miles, almonds, burgers,
% of your household electricity).

Honest by design: water is reported as a LOW-HIGH range because per-query water
estimates span ~2 orders of magnitude depending on accounting scope. Sources in
SOURCES_PERSONAL.md.

Usage:  python3 personal_ai_footprint_calculator.py     # runs example profiles
        (or import footprint() into your own script)
"""
from __future__ import annotations
from dataclasses import dataclass

# ---- Per-query constants (current flagship models, 2025) -- see SOURCES ------
WH_PER_SHORT_QUERY = 0.30        # Epoch AI / Google / OpenAI converge ~0.24-0.34
WATER_ML_PER_QUERY_LOW = 0.26    # Google, on-site only
WATER_ML_PER_QUERY_HIGH = 18.0   # UC Riverside era, full scope (power-plant + on-site)
CO2_G_PER_QUERY_LOW = 0.03       # market-based (clean PPAs)
CO2_G_PER_QUERY_HIGH = 0.14      # grid-average

# ---- Everyday anchors -- see SOURCES ----------------------------------------
PHONE_CHARGE_WH = 12.0           # one smartphone charge
GAS_MILE_WH = 1350.0             # ~1.35 kWh energy-equiv per mile (25 mpg)
HOUSEHOLD_DAY_KWH = 29.0         # US household daily electricity
ALMOND_WATER_L = 3.8             # ~1 gallon per almond
BURGER_WATER_L = 1703.0          # ~450 gal per quarter-pound burger
BURGER_CO2_G = 9700.0            # ~9.7 kg CO2e per quarter-pound burger
NETFLIX_HR_CO2_G = 36.0          # IEA revised central estimate


@dataclass
class Usage:
    name: str
    queries_per_day: int
    wh_per_query: float = WH_PER_SHORT_QUERY  # bump up for long-context/reasoning work


def footprint(u: Usage) -> dict:
    e_wh = u.queries_per_day * u.wh_per_query
    # Water and CO2 track compute, so both bounds scale with the energy multiplier.
    # The LOW-HIGH gap is accounting SCOPE (on-site cooling only vs. + power plant),
    # which is ~70x and is the honest uncertainty -- not your behavior.
    mult = u.wh_per_query / WH_PER_SHORT_QUERY
    w_lo = u.queries_per_day * WATER_ML_PER_QUERY_LOW * mult
    w_hi = u.queries_per_day * WATER_ML_PER_QUERY_HIGH * mult
    c_lo = u.queries_per_day * CO2_G_PER_QUERY_LOW * mult
    c_hi = u.queries_per_day * CO2_G_PER_QUERY_HIGH * mult
    return {
        "energy_wh_day": e_wh,
        "energy_kwh_year": e_wh * 365 / 1000,
        "water_ml_day_low": w_lo,
        "water_ml_day_high": w_hi,
        "co2_g_day_low": c_lo,
        "co2_g_day_high": c_hi,
    }


def anchors(f: dict) -> dict:
    e = f["energy_wh_day"]
    return {
        "phone_charges": e / PHONE_CHARGE_WH,
        "gas_miles": e / GAS_MILE_WH,
        "pct_household": 100 * (e / 1000) / HOUSEHOLD_DAY_KWH,
        "almonds_water_high": f["water_ml_day_high"] / 1000 / ALMOND_WATER_L,
        "burger_fraction_water_high": f["water_ml_day_high"] / 1000 / BURGER_WATER_L,
    }


def report(u: Usage) -> str:
    f = footprint(u); a = anchors(u and f)
    L = [
        f"=== {u.name} ===",
        f"  Assumes {u.queries_per_day} prompts/day at {u.wh_per_query} Wh each "
        f"({'short' if u.wh_per_query <= 0.5 else 'long-context/heavy'} regime)",
        f"  ENERGY:  {f['energy_wh_day']:.0f} Wh/day  ({f['energy_kwh_year']:.0f} kWh/year)",
        f"  WATER:   {f['water_ml_day_low']:.0f} mL  to  {f['water_ml_day_high']/1000:.2f} L per day "
        f"(range = accounting scope, not your behavior)",
        f"  CO2:     {f['co2_g_day_low']:.1f} g  to  {f['co2_g_day_high']:.1f} g per day",
        "  In everyday terms:",
        f"    ~ {a['phone_charges']:.0f} phone charges/day",
        f"    ~ {a['gas_miles']:.2f} miles of gas driving/day",
        f"    ~ {a['pct_household']:.2f}% of your household's daily electricity",
        f"    ~ {a['almonds_water_high']:.2f} almonds' worth of water (high estimate)",
        f"    ~ 1/{1/a['burger_fraction_water_high']:.0f} of one burger's water (high estimate)",
    ]
    return "\n".join(L)


if __name__ == "__main__":
    profiles = [
        Usage("Casual user (a few chats)", queries_per_day=20),
        Usage("Daily professional", queries_per_day=100),
        # Rich: $100 Claude Max power user -- long-context + agents + code.
        # Modeled as 120 heavy prompts/day at ~3 Wh (the long-query regime).
        Usage("Rich -- $100 Claude Max power user", queries_per_day=120, wh_per_query=3.0),
    ]
    for p in profiles:
        print(report(p)); print()
    print("Edit the profiles (queries_per_day, wh_per_query) to match YOUR real usage.")
    print("wh_per_query: ~0.3 short chat | ~3 heavy long-context/agent work | ~40 huge-context.")
