"""
Creative Finance Engine -- Generates Subject-To, Owner Finance, and Lease-Option
offers for any property in the wholesale pipeline.

Part of the Everlight Ventures wholesale pipeline.
Agent: Penny Voss (underwriting) + Rex Blackwell (deal structure).

Usage:
    from creative_finance_engine import underwrite_property, batch_underwrite
    offers = underwrite_property("123 Main St", assessed_value=200000, arv=280000, rental_estimate=1800)
    batch_underwrite("data/apify_leads.json")
"""

import json
import math
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Any

log = logging.getLogger("creative_finance")

OUTPUT_DIR = Path(__file__).parent / "data"


# ---------------------------------------------------------------------------
# Financial helpers
# ---------------------------------------------------------------------------

def monthly_payment(principal: float, annual_rate: float, years: int) -> float:
    """Standard amortization monthly payment calculation (PITI approximation).

    Returns 0.0 if principal <= 0 or rate <= 0.
    """
    if principal <= 0 or annual_rate <= 0 or years <= 0:
        return 0.0
    r = annual_rate / 12.0
    n = years * 12
    try:
        payment = principal * (r * (1 + r) ** n) / ((1 + r) ** n - 1)
    except (OverflowError, ZeroDivisionError):
        return 0.0
    return round(payment, 2)


def estimate_existing_mortgage(assessed_value: float, ltv: float = 0.70) -> float:
    """Rough estimate of remaining mortgage balance from assessed value."""
    return round(assessed_value * ltv, 2)


def estimate_monthly_piti(mortgage_balance: float, rate_factor: float = 0.006) -> float:
    """Rough PITI estimate. Rate factor 0.006 covers P+I+T+I at ~7% 30yr."""
    return round(mortgage_balance * rate_factor, 2)


# ---------------------------------------------------------------------------
# Offer generators
# ---------------------------------------------------------------------------

def subject_to_offer(assessed_value: float, arv: float, rental_estimate: float) -> dict:
    """Generate a Subject-To (take over existing mortgage) offer.

    Strategy: Take over seller's existing mortgage payments. Seller walks away
    from a property they can't afford or don't want. Buyer gets below-market
    financing already in place.
    """
    mortgage_balance = estimate_existing_mortgage(assessed_value)
    monthly_piti = estimate_monthly_piti(mortgage_balance)

    # Cash to seller (earnest / moving money)
    cash_to_seller = min(5000, assessed_value * 0.02)

    # Buyer's total acquisition cost
    acquisition_cost = mortgage_balance + cash_to_seller

    # Equity captured on day one
    equity_captured = arv - acquisition_cost

    # Cash flow if rented
    monthly_cashflow = rental_estimate - monthly_piti

    return {
        "offer_type": "subject_to",
        "label": "Subject-To (Take Over Payments)",
        "terms": {
            "estimated_mortgage_balance": mortgage_balance,
            "monthly_payment_estimate": monthly_piti,
            "cash_to_seller": round(cash_to_seller, 2),
            "total_acquisition_cost": round(acquisition_cost, 2),
        },
        "projections": {
            "arv": arv,
            "equity_captured": round(equity_captured, 2),
            "monthly_rental_income": rental_estimate,
            "monthly_cashflow": round(monthly_cashflow, 2),
            "annual_cashflow": round(monthly_cashflow * 12, 2),
            "cash_on_cash_return": round((monthly_cashflow * 12) / max(cash_to_seller, 1) * 100, 1),
        },
        "pitch": (
            f"We take over your existing mortgage payments of ~${monthly_piti:,.0f}/mo. "
            f"You walk away clean with ${cash_to_seller:,.0f} cash at closing. "
            f"No repairs needed, no realtor fees, we handle everything."
        ),
    }


def owner_finance_offer(assessed_value: float, arv: float, rental_estimate: float) -> dict:
    """Generate an Owner Financing (seller carries the note) offer.

    Strategy: Seller becomes the bank. Buyer pays monthly to seller instead
    of a traditional lender. Good for sellers who want passive income.
    """
    offer_price = round(arv * 0.80, 2)  # 80% of ARV
    interest_rate = 0.06  # 6% -- attractive to seller, below hard money
    amort_years = 30
    balloon_years = 5
    down_payment_pct = 0.15
    down_payment = round(offer_price * down_payment_pct, 2)
    financed_amount = offer_price - down_payment

    monthly_pmt = monthly_payment(financed_amount, interest_rate, amort_years)

    # Balloon: remaining balance after 5 years of payments
    r = interest_rate / 12
    n_paid = balloon_years * 12
    n_total = amort_years * 12
    if r > 0 and n_total > 0:
        balloon_balance = financed_amount * ((1 + r) ** n_total - (1 + r) ** n_paid) / ((1 + r) ** n_total - 1)
    else:
        balloon_balance = financed_amount
    balloon_balance = round(balloon_balance, 2)

    # Cash flow projection for buyer (if rented out)
    monthly_cashflow = rental_estimate - monthly_pmt

    return {
        "offer_type": "owner_finance",
        "label": "Owner Financing (Seller Carries Note)",
        "terms": {
            "offer_price": offer_price,
            "down_payment": down_payment,
            "down_payment_pct": f"{down_payment_pct * 100:.0f}%",
            "financed_amount": financed_amount,
            "interest_rate": f"{interest_rate * 100:.1f}%",
            "amortization": f"{amort_years} years",
            "balloon": f"{balloon_years} years",
            "monthly_payment": monthly_pmt,
            "balloon_balance": balloon_balance,
        },
        "projections": {
            "arv": arv,
            "discount_from_arv": round(arv - offer_price, 2),
            "monthly_rental_income": rental_estimate,
            "monthly_cashflow": round(monthly_cashflow, 2),
            "annual_cashflow": round(monthly_cashflow * 12, 2),
            "total_paid_before_balloon": round(down_payment + monthly_pmt * n_paid, 2),
        },
        "pitch": (
            f"We offer ${offer_price:,.0f} with ${down_payment:,.0f} down. "
            f"You receive ${monthly_pmt:,.0f}/mo for {balloon_years} years at {interest_rate*100:.1f}% interest. "
            f"No bank involved, no appraisal delays. Steady income for you, "
            f"balloon payoff in {balloon_years} years."
        ),
    }


def lease_option_offer(assessed_value: float, arv: float, rental_estimate: float) -> dict:
    """Generate a Lease-Option (lease with option to purchase) offer.

    Strategy: Lease the property with the right (not obligation) to buy at a
    locked price within 2-3 years. Option consideration is non-refundable but
    applied to purchase price.
    """
    option_price = arv  # Lock at current ARV
    lease_term_years = 3
    option_consideration_pct = 0.04  # 4% of option price
    option_consideration = round(option_price * option_consideration_pct, 2)
    monthly_lease = rental_estimate  # Market rent

    # Buyer's upside: if ARV appreciates 3-5%/yr over lease term
    appreciation_rate = 0.04  # Conservative 4%/yr
    future_value = round(arv * (1 + appreciation_rate) ** lease_term_years, 2)
    equity_at_exercise = round(future_value - option_price, 2)

    # Net cost to exercise
    net_purchase_price = option_price - option_consideration  # Option $ applied

    return {
        "offer_type": "lease_option",
        "label": "Lease-Option (Rent-to-Own)",
        "terms": {
            "monthly_lease": monthly_lease,
            "lease_term": f"{lease_term_years} years",
            "option_price": option_price,
            "option_consideration": option_consideration,
            "option_consideration_pct": f"{option_consideration_pct * 100:.0f}%",
            "option_consideration_note": "Non-refundable, applied to purchase price",
            "net_purchase_price_at_exercise": round(net_purchase_price, 2),
        },
        "projections": {
            "arv_today": arv,
            "projected_value_at_exercise": future_value,
            "equity_at_exercise": equity_at_exercise,
            "total_lease_payments": round(monthly_lease * lease_term_years * 12, 2),
            "total_invested_before_exercise": round(
                option_consideration + monthly_lease * lease_term_years * 12, 2
            ),
        },
        "pitch": (
            f"We lease your property at ${monthly_lease:,.0f}/mo for {lease_term_years} years "
            f"with an option to buy at ${option_price:,.0f}. You receive ${option_consideration:,.0f} "
            f"upfront as non-refundable option consideration. Guaranteed income, no vacancy risk, "
            f"and if we exercise, you get your full price."
        ),
    }


# ---------------------------------------------------------------------------
# Offer letter generation
# ---------------------------------------------------------------------------

def generate_offer_letter(offer_type: str, property_data: dict, terms: dict) -> str:
    """Generate a professional offer letter for any creative finance offer type.

    Args:
        offer_type: One of 'subject_to', 'owner_finance', 'lease_option'
        property_data: Dict with address, city, state, etc.
        terms: The 'terms' dict from the corresponding offer function
    """
    address = property_data.get("address", "the property")
    city = property_data.get("city", "")
    state = property_data.get("state", "")
    full_address = f"{address}, {city}, {state}".strip(", ")
    today = datetime.now(timezone.utc).strftime("%B %d, %Y")

    header = f"""LETTER OF INTENT
Everlight Ventures -- Real Estate Acquisitions
Date: {today}
Re: {full_address}

Dear Property Owner,

Thank you for considering our offer on your property at {full_address}.
We are a professional real estate investment company and we buy properties
in any condition. Below is our offer for your review.

"""

    if offer_type == "subject_to":
        body = f"""OFFER TYPE: Subject-To (Assumption of Existing Financing)

We propose to take over your existing mortgage payments, estimated at
${terms['monthly_payment_estimate']:,.0f} per month, on the remaining
balance of approximately ${terms['estimated_mortgage_balance']:,.0f}.

Additionally, we will provide ${terms['cash_to_seller']:,.0f} in cash
to you at closing for moving expenses.

Benefits to you:
- Immediate relief from mortgage payments
- No repairs or cleaning required
- Cash at closing
- Quick close (7-14 days)
- No realtor commissions or fees

"""

    elif offer_type == "owner_finance":
        body = f"""OFFER TYPE: Owner Financing (Seller-Carried Note)

Purchase Price: ${terms['offer_price']:,.0f}
Down Payment: ${terms['down_payment']:,.0f} ({terms['down_payment_pct']})
Financed Amount: ${terms['financed_amount']:,.0f}
Interest Rate: {terms['interest_rate']}
Monthly Payment: ${terms['monthly_payment']:,.0f}
Amortization: {terms['amortization']}
Balloon Payment: {terms['balloon']} (${terms['balloon_balance']:,.0f})

Benefits to you:
- Above-market interest rate on your equity
- Steady monthly income for {terms['balloon']}
- Tax advantages (installment sale treatment)
- No bank involvement or delays
- Balloon payoff guarantees your full return

"""

    elif offer_type == "lease_option":
        body = f"""OFFER TYPE: Lease with Option to Purchase

Monthly Lease Payment: ${terms['monthly_lease']:,.0f}
Lease Term: {terms['lease_term']}
Option Price: ${terms['option_price']:,.0f}
Option Consideration: ${terms['option_consideration']:,.0f} ({terms['option_consideration_pct']})
Note: Option consideration is non-refundable and applied to purchase price.

Benefits to you:
- Guaranteed monthly income with no vacancy risk
- Non-refundable upfront payment
- Property maintained by tenant-buyer
- Full asking price if option is exercised
- You retain ownership until exercise

"""

    else:
        body = "[Offer type not recognized]\n\n"

    footer = """This is a non-binding Letter of Intent. A formal purchase agreement
will follow upon acceptance. We can close on your timeline.

We look forward to working with you.

Sincerely,
Everlight Ventures
Real Estate Acquisitions Division
acquisitions@everlightventures.io
"""

    return header + body + footer


# ---------------------------------------------------------------------------
# Property underwriting
# ---------------------------------------------------------------------------

def underwrite_property(
    address: str,
    assessed_value: float,
    arv: float,
    rental_estimate: float,
    city: str = "",
    state: str = "",
) -> dict:
    """Run full underwriting on a property -- generates all 3 offer types.

    Args:
        address: Property street address
        assessed_value: County assessed value or estimated current value
        arv: After-repair value (what it's worth fixed up)
        rental_estimate: Monthly rental value from comps
        city: City name (for offer letters)
        state: State abbreviation (for offer letters)

    Returns:
        Dict with property_data, all 3 offers, and generated letters.
    """
    if assessed_value <= 0 or arv <= 0:
        log.warning("Invalid values for %s: assessed=%s, arv=%s", address, assessed_value, arv)
        return {"error": "assessed_value and arv must be positive", "address": address}

    if rental_estimate <= 0:
        # Rough estimate: 0.8% of ARV per month
        rental_estimate = round(arv * 0.008, 2)
        log.info("No rental estimate for %s, using rough calc: $%s/mo", address, rental_estimate)

    property_data = {
        "address": address,
        "city": city,
        "state": state,
        "assessed_value": assessed_value,
        "arv": arv,
        "rental_estimate": rental_estimate,
    }

    # Generate all 3 offer types
    sub_to = subject_to_offer(assessed_value, arv, rental_estimate)
    owner_fin = owner_finance_offer(assessed_value, arv, rental_estimate)
    lease_opt = lease_option_offer(assessed_value, arv, rental_estimate)

    # Generate letters
    sub_to["letter"] = generate_offer_letter("subject_to", property_data, sub_to["terms"])
    owner_fin["letter"] = generate_offer_letter("owner_finance", property_data, owner_fin["terms"])
    lease_opt["letter"] = generate_offer_letter("lease_option", property_data, lease_opt["terms"])

    return {
        "property": property_data,
        "offers": {
            "subject_to": sub_to,
            "owner_finance": owner_fin,
            "lease_option": lease_opt,
        },
        "underwritten_at": datetime.now(timezone.utc).isoformat(),
        "best_offer": _pick_best_offer(sub_to, owner_fin, lease_opt),
    }


def _pick_best_offer(sub_to: dict, owner_fin: dict, lease_opt: dict) -> str:
    """Heuristic to pick best offer type based on cash flow."""
    scores = {
        "subject_to": sub_to["projections"].get("monthly_cashflow", 0),
        "owner_finance": owner_fin["projections"].get("monthly_cashflow", 0),
        "lease_option": lease_opt["projections"].get("equity_at_exercise", 0) / 36,  # Amortize over 3yr
    }
    return max(scores, key=scores.get)


# ---------------------------------------------------------------------------
# Batch underwriting
# ---------------------------------------------------------------------------

def batch_underwrite(leads_file: str | Path, output_file: str | Path | None = None) -> list[dict]:
    """Read a JSON file of leads, underwrite each, output results.

    Expects leads_file to have structure: {"leads": [...]} where each lead has
    at minimum: address, price (used as assessed_value). ARV defaults to 1.3x price
    if not provided.
    """
    leads_path = Path(leads_file)
    if not leads_path.exists():
        log.error("Leads file not found: %s", leads_path)
        return []

    with open(leads_path) as f:
        data = json.load(f)

    leads = data.get("leads", data if isinstance(data, list) else [])
    log.info("Underwriting %d leads from %s", len(leads), leads_path)

    results = []
    for i, lead in enumerate(leads):
        address = lead.get("address", f"Property #{i+1}")
        price = lead.get("price", 0)
        if not price or price <= 0:
            log.warning("Skipping %s -- no price data", address)
            continue

        arv = lead.get("arv", round(price * 1.30, 2))  # Default: 30% above list
        rental = lead.get("rental_estimate", 0)

        result = underwrite_property(
            address=address,
            assessed_value=price,
            arv=arv,
            rental_estimate=rental,
            city=lead.get("city", ""),
            state=lead.get("state", ""),
        )
        results.append(result)

    # Save results
    if output_file is None:
        output_file = OUTPUT_DIR / "underwritten_deals.json"
    else:
        output_file = Path(output_file)

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w") as f:
        json.dump({
            "deals": results,
            "count": len(results),
            "source_file": str(leads_path),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }, f, indent=2, default=str)

    log.info("Underwritten %d deals -> %s", len(results), output_file)
    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

    # Demo: underwrite a single property
    result = underwrite_property(
        address="1234 Maple Ave",
        assessed_value=180000,
        arv=250000,
        rental_estimate=1600,
        city="Cleveland",
        state="OH",
    )

    print("\n=== UNDERWRITING REPORT ===")
    print(f"Property: {result['property']['address']}")
    print(f"Best offer type: {result['best_offer']}")
    for name, offer in result["offers"].items():
        print(f"\n--- {offer['label']} ---")
        print(offer["pitch"])
        cf = offer.get("projections", {}).get("monthly_cashflow")
        if cf is not None:
            print(f"  Monthly cash flow: ${cf:,.0f}")
