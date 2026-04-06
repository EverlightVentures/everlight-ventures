"""
Rex's Land Deal Analyzer -- evaluates vacant land wholesale opportunities.

Implements the playbook from the $45k Dallas land deal:
1. Find undervalued land in good neighborhoods
2. Check zoning (duplex vs SFR changes the math completely)
3. Calculate land value as % of new construction value
4. Estimate builder profit to validate buyer interest
5. Generate deal packets for buyer disposition

Usage:
    from land_analyzer import analyze_land_deal, LandDeal
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ZoningInfo:
    """Zoning classification for a lot."""
    allows_sfr: bool = True
    allows_duplex: bool = False
    allows_multi: bool = False       # 3-4 units
    allows_commercial: bool = False
    max_units: int = 1
    setback_ft: float = 5.0
    lot_width_ft: float = 50.0
    buildable_width_ft: float = 0.0  # lot_width - (2 * setback)
    zoning_code: str = ""
    notes: str = ""

    def __post_init__(self):
        if not self.buildable_width_ft:
            self.buildable_width_ft = max(0, self.lot_width_ft - (2 * self.setback_ft))


@dataclass
class ConstructionEstimate:
    """Builder cost and profit estimate."""
    sqft: int = 2500
    cost_per_sqft: float = 175.0
    total_construction: float = 0.0
    expected_sale_price: float = 0.0
    closing_costs_pct: float = 0.10   # realtor fees + closing = ~10%
    net_after_fees: float = 0.0
    land_cost: float = 0.0
    total_all_in: float = 0.0
    builder_profit: float = 0.0
    builder_roi_pct: float = 0.0

    def calculate(self):
        self.total_construction = self.sqft * self.cost_per_sqft
        self.net_after_fees = self.expected_sale_price * (1 - self.closing_costs_pct)
        self.total_all_in = self.land_cost + self.total_construction
        self.builder_profit = self.net_after_fees - self.total_all_in
        if self.total_all_in > 0:
            self.builder_roi_pct = round(self.builder_profit / self.total_all_in * 100, 1)
        return self


@dataclass
class LandDeal:
    """Complete land wholesale deal analysis."""
    address: str = ""
    city: str = ""
    state: str = ""
    zip_code: str = ""
    lot_sqft: int = 0
    lot_acres: float = 0.0

    # Pricing
    list_price: float = 0.0
    negotiated_price: float = 0.0
    assignment_fee: float = 10000.0

    # Comps
    comparable_land_low: float = 0.0
    comparable_land_high: float = 0.0
    comparable_homes_low: float = 0.0
    comparable_homes_high: float = 0.0

    # Zoning
    zoning: ZoningInfo = field(default_factory=ZoningInfo)

    # Construction estimates per unit
    sfr_estimate: Optional[ConstructionEstimate] = None
    duplex_estimate: Optional[ConstructionEstimate] = None

    # Deal outcome
    estimated_land_value: float = 0.0
    buyer_offer: float = 0.0
    our_profit: float = 0.0
    deal_status: str = "analyzing"  # analyzing, locked, assigned, closed, dead


def estimate_land_value(home_value: float, units: int = 1) -> float:
    """
    Land typically sells for ~20% of new construction value.
    For duplexes, the total build value doubles.

    From the playbook:
    - SFR at $750k -> land worth ~$150k (20%)
    - Duplex 2x $600k = $1.2M -> land worth ~$240k (20%)
    """
    total_build_value = home_value * units
    return total_build_value * 0.20


def analyze_land_deal(deal: LandDeal) -> dict:
    """
    Full deal analysis following Rex's playbook.

    Returns a dict with:
    - land_value_sfr: estimated value if zoned for single family
    - land_value_duplex: estimated value if zoned for duplex
    - sfr_builder_profit: what a builder would make on SFR
    - duplex_builder_profit: what a builder would make on duplex
    - max_offer: our maximum price to pay
    - spread: profit potential at negotiated price
    - recommendation: buy / negotiate_lower / pass
    """
    avg_home_value = (deal.comparable_homes_low + deal.comparable_homes_high) / 2 if deal.comparable_homes_high else 0

    # Land value estimates
    land_value_sfr = estimate_land_value(avg_home_value, units=1)
    land_value_duplex = estimate_land_value(avg_home_value, units=2) if deal.zoning.allows_duplex else 0

    # Use the higher value based on zoning
    if deal.zoning.allows_duplex:
        deal.estimated_land_value = land_value_duplex
    else:
        deal.estimated_land_value = land_value_sfr

    # SFR construction estimate
    deal.sfr_estimate = ConstructionEstimate(
        sqft=2500,
        cost_per_sqft=175.0,
        expected_sale_price=avg_home_value,
        land_cost=deal.negotiated_price or deal.list_price,
    ).calculate()

    # Duplex estimate (if zoned)
    if deal.zoning.allows_duplex:
        per_unit_value = avg_home_value * 0.85  # duplex units typically 85% of SFR value
        deal.duplex_estimate = ConstructionEstimate(
            sqft=3500,  # total for both units
            cost_per_sqft=165.0,  # slightly cheaper per sqft for duplex
            expected_sale_price=per_unit_value * 2,
            land_cost=deal.negotiated_price or deal.list_price,
        ).calculate()

    # Our deal math
    purchase_price = deal.negotiated_price or deal.list_price
    max_we_should_pay = deal.estimated_land_value - deal.assignment_fee
    spread = deal.estimated_land_value - purchase_price
    our_profit = spread - deal.assignment_fee if spread > deal.assignment_fee else spread * 0.5

    # Recommendation
    if spread >= deal.assignment_fee * 2:
        recommendation = "STRONG BUY -- spread covers 2x+ assignment fee"
    elif spread >= deal.assignment_fee:
        recommendation = "BUY -- solid spread, worth locking up"
    elif spread >= deal.assignment_fee * 0.5:
        recommendation = "NEGOTIATE LOWER -- thin margin, need price reduction"
    else:
        recommendation = "PASS -- numbers don't work at this price"

    return {
        "address": deal.address,
        "city": deal.city,
        "state": deal.state,
        "list_price": deal.list_price,
        "negotiated_price": deal.negotiated_price,
        "land_value_sfr": round(land_value_sfr),
        "land_value_duplex": round(land_value_duplex),
        "best_land_value": round(deal.estimated_land_value),
        "zoning_allows_duplex": deal.zoning.allows_duplex,
        "max_units": deal.zoning.max_units,
        "sfr_builder_profit": round(deal.sfr_estimate.builder_profit) if deal.sfr_estimate else 0,
        "sfr_builder_roi": deal.sfr_estimate.builder_roi_pct if deal.sfr_estimate else 0,
        "duplex_builder_profit": round(deal.duplex_estimate.builder_profit) if deal.duplex_estimate else 0,
        "duplex_builder_roi": deal.duplex_estimate.builder_roi_pct if deal.duplex_estimate else 0,
        "max_offer": round(max_we_should_pay),
        "assignment_fee": deal.assignment_fee,
        "spread": round(spread),
        "our_profit": round(our_profit),
        "recommendation": recommendation,
    }


def generate_deal_packet(deal: LandDeal, analysis: dict) -> str:
    """
    Generate a deal packet for buyer disposition.
    This is what Rex's sales team sends to investors.
    """
    zoning_line = "Duplex-zoned" if analysis["zoning_allows_duplex"] else "Single-family only"
    duplex_section = ""
    if analysis["zoning_allows_duplex"] and analysis["duplex_builder_profit"]:
        duplex_section = f"""
## Duplex Build Scenario
- Total build value: ${analysis['land_value_duplex'] * 5:,.0f} (2 units)
- Builder profit estimate: ${analysis['duplex_builder_profit']:,}
- Builder ROI: {analysis['duplex_builder_roi']}%
"""

    packet = f"""# WHOLESALE DEAL PACKET
## {deal.address}, {deal.city}, {deal.state} {deal.zip_code}

**Property Type:** Vacant Land ({deal.lot_acres:.2f} acres / {deal.lot_sqft:,} sqft)
**Zoning:** {zoning_line} (max {deal.zoning.max_units} units)
**Asking Price:** ${analysis['negotiated_price'] or analysis['list_price']:,.0f}

## Comparable Sales
- Land comps: ${deal.comparable_land_low:,.0f} - ${deal.comparable_land_high:,.0f}
- New home sales: ${deal.comparable_homes_low:,.0f} - ${deal.comparable_homes_high:,.0f}

## Estimated Land Value
- As SFR lot: ${analysis['land_value_sfr']:,}
- As duplex lot: ${analysis['land_value_duplex']:,} (if zoned)
- Best estimate: ${analysis['best_land_value']:,}

## SFR Build Scenario
- 2,500 sqft home at $175/sqft = ${deal.sfr_estimate.total_construction:,.0f} construction
- Expected sale: ${deal.sfr_estimate.expected_sale_price:,.0f}
- Net after fees: ${deal.sfr_estimate.net_after_fees:,.0f}
- Builder profit estimate: ${analysis['sfr_builder_profit']:,}
- Builder ROI: {analysis['sfr_builder_roi']}%
{duplex_section}
## Deal Terms
- **Assignment fee:** ${analysis['assignment_fee']:,}
- **Cash only, close in 14-21 days**
- Non-refundable EMD required

## Contact
Everlight Ventures -- Real Estate Division
Email: support@everlightventures.io
"""
    return packet


def generate_renegotiation_script(
    original_price: float,
    new_issue: str,
    desired_price: float,
) -> str:
    """
    Generate a renegotiation script when deal terms change.

    From the playbook: when the city killed duplex zoning, Max asked
    the realtor to come back with a number rather than naming one himself.
    """
    reduction = original_price - desired_price
    reduction_pct = round(reduction / original_price * 100, 1)

    return f"""RENEGOTIATION SCRIPT

Situation: {new_issue}

Opening:
"Hey [realtor name], I appreciate you working with us on this. As you know,
[brief description of the issue]. This changes the numbers significantly
on our end."

Key points to hit:
- Acknowledge the realtor's work and commission expectations
- Explain how the issue affects your numbers specifically
- Show your math (construction costs, expected sale, profit margin)
- Make it clear you'll walk if the numbers don't pencil
- Ask THEM to come back with a number (don't name your price first)

Closing:
"I still want to close this -- we have ${reduction:,.0f} on the line in
earnest money. But if the numbers don't work, I'd rather take the loss
than force a bad deal. Can you check with your seller and see what
flexibility there is?"

Target: ${desired_price:,.0f} (${reduction_pct}% reduction from ${original_price:,.0f})

Fallback: If they counter above your target, calculate whether
the builder profit still clears $100k+ spread. If yes, take it.
If no, walk.
"""
