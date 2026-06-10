#!/usr/bin/env python3
"""
RESOURCE PARITY CALCULATOR -- Data Center Impact 360
=====================================================
Turns Rich's thesis -- "technology shouldn't consume more resources than the
humans it shares a commons with" -- into a usable test.

Plug in a proposed/real data center's water + power draw and the local supply,
and it answers three questions in plain English:
  1. How many humans' worth of WATER does this consume?
  2. How many humans' worth of ELECTRICITY does this consume?
  3. Does it breach the parity cap (its share of the LOCAL supply)?

Usage:
  python3 resource_parity_calculator.py            # runs the built-in examples
  (or import facility_footprint / evaluate_parity into another script)

All baselines are cited in SOURCES.md. Change them in HUMAN_BASELINES if you
have better local numbers.
"""
from __future__ import annotations
from dataclasses import dataclass

# ---- Human baselines (per person) -- see SOURCES.md -------------------------
HUMAN_BASELINES = {
    "water_gal_per_person_per_day": 100.0,     # US home use, 82-100 gal/day
    "power_kwh_per_person_per_year": 4300.0,   # ~10,800 kWh/home/yr / ~2.5 people
    "people_per_home": 2.5,
}


@dataclass
class DataCenter:
    name: str
    water_gal_per_day: float          # on-site cooling water
    power_mw: float                   # average power draw (megawatts)
    local_water_supply_gal_per_day: float | None = None   # the community's daily supply
    local_power_supply_mw: float | None = None            # the community's power supply
    pays_scarcity_price: bool = False  # does it pay the same/higher per-unit rate as residents?
    funds_own_grid: bool = False       # does it pay for its own grid/water upgrades?


def facility_footprint(dc: DataCenter) -> dict:
    """Translate a facility's draw into 'equivalent number of humans'."""
    water_people = dc.water_gal_per_day / HUMAN_BASELINES["water_gal_per_person_per_day"]
    # power: MW -> kWh/year -> homes -> people
    kwh_per_year = dc.power_mw * 1000 * 24 * 365
    homes = kwh_per_year / HUMAN_BASELINES["power_kwh_per_person_per_year"] / HUMAN_BASELINES["people_per_home"]
    power_people = homes * HUMAN_BASELINES["people_per_home"]
    out = {
        "water_people_equiv": round(water_people),
        "power_homes_equiv": round(homes),
        "power_people_equiv": round(power_people),
    }
    if dc.local_water_supply_gal_per_day:
        out["pct_local_water"] = round(100 * dc.water_gal_per_day / dc.local_water_supply_gal_per_day, 1)
    if dc.local_power_supply_mw:
        out["pct_local_power"] = round(100 * dc.power_mw / dc.local_power_supply_mw, 1)
    return out


# =============================================================================
# YOUR DECISION, RICH -- define what "passing the parity test" means.
# =============================================================================
# This is the heart of the tool, and it is deliberately left for YOU, because
# it is a VALUES call, not a math call. The math above is settled; the THRESHOLD
# is a judgment about how much of a shared, finite commons one machine may claim.
#
# Consider the trade-offs:
#   - A strict cap (e.g. "no facility may take >5% of local water OR power, AND
#     must pay scarcity price AND fund its own grid") protects the community hard
#     but may push every project away -- including efficient, well-run ones.
#   - A loose cap (e.g. "20% is fine as long as it pays its own way") invites
#     investment but risks the Newton County GA outcome (a center at ~10% of a
#     county's water while residents' wells ran dry).
#   - You might weight it: a center that pays scarcity prices AND funds its own
#     grid earns a higher allowed share than a subsidized one.
#
# Reference points from the research:
#   - Meta / Newton County GA: ~10% of county water  -> wells failed, rates +33%
#   - Santa Clara CA: data centers = 60% of city POWER -> grid maxed, centers idle
#   - Mesa AZ: Google paid 44% LESS per gallon than residents (NOT scarcity price)
#
# TODO(Rich): implement the verdict. Return a dict like:
#   {"verdict": "PASS" | "CONDITIONAL" | "FAIL", "reasons": [list of plain-English strings]}
# You have ~5-15 lines of real judgment to encode here. Make it yours.
def evaluate_parity(dc: DataCenter, footprint: dict) -> dict:
    """
    Decide whether this facility passes the parity principle.

    Inputs:
      dc        -- the DataCenter (incl. pays_scarcity_price, funds_own_grid)
      footprint -- output of facility_footprint() (incl. pct_local_water,
                   pct_local_power, *_people_equiv)

    Return:
      {"verdict": str, "reasons": list[str]}
    """
    # ----------------------------------------------------------------------
    # TODO(Rich): your cap + your logic goes here. A reasonable starting shape:
    #
    #   reasons = []
    #   verdict = "PASS"
    #   water_share = footprint.get("pct_local_water")
    #   power_share = footprint.get("pct_local_power")
    #   # 1. how much of the local commons may one machine claim?
    #   # 2. does it have to pay scarcity price to claim it?
    #   # 3. does it have to fund its own grid/water?
    #   # ...set verdict to FAIL/CONDITIONAL and append reasons accordingly...
    #   return {"verdict": verdict, "reasons": reasons}
    #
    # Until you fill this in, we return UNDEFINED so nothing fakes a judgment.
    return {
        "verdict": "UNDEFINED",
        "reasons": ["Parity threshold not yet defined -- see TODO(Rich) in evaluate_parity()."],
    }


def report(dc: DataCenter) -> str:
    f = facility_footprint(dc)
    p = evaluate_parity(dc, f)
    lines = [
        f"=== {dc.name} ===",
        f"  Water: {dc.water_gal_per_day:,.0f} gal/day  =  {f['water_people_equiv']:,} people",
        f"  Power: {dc.power_mw:,.0f} MW  =  {f['power_homes_equiv']:,} homes "
        f"(~{f['power_people_equiv']:,} people)",
    ]
    if "pct_local_water" in f:
        lines.append(f"  Local water share: {f['pct_local_water']}%")
    if "pct_local_power" in f:
        lines.append(f"  Local power share: {f['pct_local_power']}%")
    lines.append(f"  Pays scarcity price: {dc.pays_scarcity_price} | Funds own grid: {dc.funds_own_grid}")
    lines.append(f"  PARITY VERDICT: {p['verdict']}")
    for r in p["reasons"]:
        lines.append(f"    - {r}")
    return "\n".join(lines)


if __name__ == "__main__":
    # Example A: a large/hyperscale center at peak (the Master Brief headline case)
    big = DataCenter(
        name="Generic hyperscale center (peak)",
        water_gal_per_day=5_000_000,
        power_mw=300,
        pays_scarcity_price=False,
        funds_own_grid=False,
    )
    # Example B: Meta-style center vs a small county (Newton County GA shape)
    county = DataCenter(
        name="Meta-style center vs a small county",
        water_gal_per_day=500_000,
        power_mw=150,
        local_water_supply_gal_per_day=5_000_000,   # ~10% of county (the GA cautionary tale)
        pays_scarcity_price=False,
        funds_own_grid=False,
    )
    print(report(big))
    print()
    print(report(county))
    print()
    print("Note: PARITY VERDICT reads UNDEFINED until evaluate_parity() is implemented.")
    print("That function is intentionally left for Rich -- the cap is a values call.")
