"""
Ace's Pitch Engine -- generates custom investment pitches per property.

Every deal gets 3 outputs:
1. Deal one-pager (HTML, can be converted to PDF)
2. Email pitch (3 paragraphs: pain, numbers, urgency)
3. SMS pitch (2 sentences)

Uses Claude for custom copy when available, falls back to templates.
"""

import json
import logging
import os
import random
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="[Ace %(asctime)s] %(message)s", datefmt="%H:%M")
log = logging.getLogger("ace")

AGENT_DIR = Path(__file__).parent
PITCH_DIR = AGENT_DIR / "pitches"
PITCH_DIR.mkdir(parents=True, exist_ok=True)

TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# PAIN POINTS -- the hook that makes buyers act fast
# ---------------------------------------------------------------------------

PAIN_POINTS = {
    "code_violation": {
        "hook": "The city is fining the owner daily. Every day they hold this property costs them money.",
        "detail": "Active code violations mean the seller is bleeding cash. They need this gone -- not next month, now.",
        "urgency": "Fines compound. The longer this sits, the more desperate the seller gets -- and the less competition you have.",
    },
    "pre_foreclosure": {
        "hook": "Foreclosure auction is approaching. The seller loses everything if they don't act.",
        "detail": "A lis pendens has been filed. The clock is ticking toward auction. The seller's credit, equity, and home are all at risk.",
        "urgency": "Once the auction date passes, this deal disappears. The seller is motivated to close before the bank takes it.",
    },
    "tax_lien": {
        "hook": "Back taxes are piling up. The county will seize this property if the owner doesn't sell.",
        "detail": "Delinquent property taxes put the owner at risk of losing the property entirely. They often owe more in penalties than the original tax bill.",
        "urgency": "Tax lien sales happen on a fixed schedule. The seller knows the deadline and wants out.",
    },
    "probate": {
        "hook": "Inherited property. The heirs live far away and want cash, not a house to manage.",
        "detail": "Probate properties sit in limbo while heirs figure out what to do. Most just want the money -- they have no emotional attachment to the property.",
        "urgency": "Heirs are splitting the proceeds. The faster they sell, the faster everyone gets paid. They are not going to hold out for top dollar.",
    },
    "vacant": {
        "hook": "This property has been sitting empty. The owner is paying insurance, taxes, and liability on a house nobody uses.",
        "detail": "Vacant properties are dead weight -- they cost money every month with zero return. The owner is subsidizing an empty building.",
        "urgency": "Every month vacant costs the owner $500-2,000 in carrying costs. They are financially incentivized to sell fast.",
    },
    "absentee": {
        "hook": "Out-of-state owner managing this property from far away. Tired of tenant calls and repair bills.",
        "detail": "Remote landlords eventually hit a breaking point -- one more midnight maintenance call, one more eviction, one more repair bill. That is when they sell.",
        "urgency": "The owner already checked out mentally. They just need someone to make it easy. That is you.",
    },
    "divorce": {
        "hook": "Court-ordered sale. Both parties want this done fast so they can move on.",
        "detail": "Divorce sales have two motivated sellers instead of one. Neither wants to negotiate -- they want it over.",
        "urgency": "The court has ordered this sale. Price is secondary to speed. Both sides just want their check.",
    },
    "expired_listing": {
        "hook": "This property sat on the MLS with no takers. The market already said no at list price.",
        "detail": "After months on market with no offers, the seller is demoralized. The agent relationship is strained. They are ready for a different approach.",
        "urgency": "The seller has already mentally adjusted their expectations down. Your below-market offer is not insulting -- it is realistic.",
    },
}

DEFAULT_PAIN = {
    "hook": "Motivated seller looking to move quickly on this property.",
    "detail": "The seller has indicated willingness to accept a below-market cash offer for speed and certainty.",
    "urgency": "Cash buyers who move fast get the best deals. This one is available now.",
}


# ---------------------------------------------------------------------------
# PROFIT CALCULATIONS
# ---------------------------------------------------------------------------

def calculate_flip_profit(purchase: float, repairs: float, arv: float) -> dict:
    closing_sell = arv * 0.08  # 6% agent + 2% closing
    holding_costs = arv * 0.03  # 3-6 months of carrying
    total_cost = purchase + repairs + closing_sell + holding_costs
    profit = arv - total_cost
    roi = (profit / (purchase + repairs) * 100) if (purchase + repairs) > 0 else 0
    return {
        "strategy": "Fix and Flip",
        "purchase": purchase,
        "repairs": repairs,
        "arv": arv,
        "closing_costs": round(closing_sell),
        "holding_costs": round(holding_costs),
        "total_invested": round(purchase + repairs),
        "profit": round(profit),
        "roi_pct": round(roi, 1),
        "timeline": "6-9 months",
    }


def calculate_rental_profit(purchase: float, repairs: float, monthly_rent: float) -> dict:
    annual_rent = monthly_rent * 12
    expenses = annual_rent * 0.40  # 40% for taxes, insurance, maintenance, vacancy
    noi = annual_rent - expenses
    cap_rate = (noi / (purchase + repairs) * 100) if (purchase + repairs) > 0 else 0
    return {
        "strategy": "Buy and Hold Rental",
        "purchase": purchase,
        "repairs": repairs,
        "monthly_rent": monthly_rent,
        "annual_rent": round(annual_rent),
        "annual_expenses": round(expenses),
        "noi": round(noi),
        "cap_rate": round(cap_rate, 1),
        "cash_on_cash": round(cap_rate, 1),  # simplified, assumes all cash
        "timeline": "Year 1 cash flow",
    }


def calculate_build_profit(land_cost: float, construction: float, sale_price: float) -> dict:
    closing = sale_price * 0.08
    profit = sale_price - land_cost - construction - closing
    roi = (profit / (land_cost + construction) * 100) if (land_cost + construction) > 0 else 0
    return {
        "strategy": "Ground-Up Build",
        "land_cost": land_cost,
        "construction": round(construction),
        "sale_price": sale_price,
        "closing_costs": round(closing),
        "profit": round(profit),
        "roi_pct": round(roi, 1),
        "timeline": "12-18 months",
    }


def estimate_monthly_rent(arv: float, market: str = "") -> float:
    """Rough rent estimate: 0.8-1.0% of ARV per month."""
    return round(arv * 0.009, -1)  # 0.9% rule, rounded to nearest 10


# ---------------------------------------------------------------------------
# PITCH GENERATION
# ---------------------------------------------------------------------------

def generate_pitch(deal: dict) -> dict:
    """
    Generate a complete marketing pitch for a deal.

    Input: dict with keys like address, city, state, asking_price, arv,
           repair_estimate, lead_type, assignment_fee, owner_name, etc.

    Returns: dict with email_pitch, sms_pitch, one_pager_html
    """
    address = deal.get("address", "Property")
    city = deal.get("city", "")
    state = deal.get("state", "")
    asking = deal.get("asking_price", 0) or deal.get("our_offer", 0)
    arv = deal.get("arv", 0) or deal.get("estimated_arv", 0) or deal.get("zestimate", 0)
    repairs = deal.get("repair_estimate", 0) or deal.get("estimated_repair", 0)
    assignment_fee = deal.get("assignment_fee", 10000)
    lead_type = deal.get("lead_type", "")
    buyer_price = asking + assignment_fee
    sqft = deal.get("sqft", 0)
    beds = deal.get("beds", 0)
    baths = deal.get("baths", 0)
    year_built = deal.get("year_built", 0)
    property_type = deal.get("property_type", "sfr")

    # Get pain point
    pain = PAIN_POINTS.get(lead_type, DEFAULT_PAIN)

    # Calculate profit scenarios
    flip = calculate_flip_profit(buyer_price, repairs, arv) if arv else None
    rent = calculate_rental_profit(buyer_price, repairs, estimate_monthly_rent(arv)) if arv else None

    # Build email pitch
    email_pitch = _build_email_pitch(deal, pain, flip, rent, buyer_price)
    sms_pitch = _build_sms_pitch(deal, pain, flip, buyer_price)
    one_pager = _build_one_pager(deal, pain, flip, rent, buyer_price)

    result = {
        "address": address,
        "email_pitch": email_pitch,
        "sms_pitch": sms_pitch,
        "one_pager_html": one_pager,
        "pain_point": pain,
        "flip_numbers": flip,
        "rental_numbers": rent,
        "buyer_price": buyer_price,
        "generated_at": TODAY,
    }

    # Save pitch
    import re
    safe = re.sub(r'[^\w\s-]', '', address).strip().replace(' ', '_')[:40]
    pitch_path = PITCH_DIR / f"{TODAY}_{safe}.json"
    with open(pitch_path, "w") as f:
        json.dump(result, f, indent=2, default=str)

    return result


def _build_email_pitch(deal, pain, flip, rent, buyer_price) -> str:
    address = deal.get("address", "Property")
    city = deal.get("city", "")
    state = deal.get("state", "")
    arv = deal.get("arv", 0) or deal.get("estimated_arv", 0) or deal.get("zestimate", 0)
    repairs = deal.get("repair_estimate", 0) or deal.get("estimated_repair", 0)

    # Paragraph 1: The pain (hook)
    para1 = f"{pain['hook']}\n\n{pain['detail']}"

    # Paragraph 2: The numbers
    if flip and flip["profit"] > 0:
        para2 = (
            f"The numbers on {address}, {city} {state}:\n"
            f"- Acquisition: ${buyer_price:,.0f}\n"
            f"- Estimated repairs: ${repairs:,.0f}\n"
            f"- After-repair value: ${arv:,.0f}\n"
            f"- Projected profit (flip): ${flip['profit']:,.0f} ({flip['roi_pct']}% ROI)\n"
        )
        if rent and rent["cap_rate"] > 5:
            para2 += f"- Or rent at ${rent['monthly_rent']:,.0f}/mo ({rent['cap_rate']}% cap rate)\n"
    else:
        para2 = (
            f"Property: {address}, {city} {state}\n"
            f"- Price: ${buyer_price:,.0f}\n"
            f"- Estimated value: ${arv:,.0f}\n"
            f"- Spread: ${arv - buyer_price:,.0f}\n"
        )

    # Paragraph 3: The urgency
    para3 = (
        f"{pain['urgency']}\n\n"
        f"Cash only. 7-14 day close. Assignment structure -- clean title through a licensed title company.\n\n"
        f"Reply 'SEND DETAILS' for the full property package.\n"
        f"First qualified buyer locks it.\n\n"
        f"Everlight Ventures -- Acquisitions\n"
        f"support@everlightventures.io"
    )

    return f"{para1}\n\n{para2}\n{para3}"


def _build_sms_pitch(deal, pain, flip, buyer_price) -> str:
    address = deal.get("address", "Property")
    city = deal.get("city", "")
    profit_str = f"${flip['profit']:,.0f} profit potential" if flip and flip["profit"] > 0 else f"${deal.get('arv', 0) - buyer_price:,.0f} spread"
    return f"Off-market deal: {address}, {city}. ${buyer_price:,.0f} cash, {profit_str}. Reply for details. - Everlight Ventures"


def _build_one_pager(deal, pain, flip, rent, buyer_price) -> str:
    address = deal.get("address", "Property")
    city = deal.get("city", "")
    state = deal.get("state", "")
    arv = deal.get("arv", 0) or deal.get("estimated_arv", 0) or deal.get("zestimate", 0)
    repairs = deal.get("repair_estimate", 0) or deal.get("estimated_repair", 0)
    sqft = deal.get("sqft", 0)
    beds = deal.get("beds", 0)
    baths = deal.get("baths", 0)
    year = deal.get("year_built", 0)
    lead_type = deal.get("lead_type", "distressed")

    flip_section = ""
    if flip and flip["profit"] > 0:
        flip_section = f"""
        <div style="background:#1a1a2e;border:1px solid #c9a84c33;border-radius:8px;padding:20px;margin:16px 0;">
            <h3 style="color:#c9a84c;margin:0 0 12px;">Flip Scenario</h3>
            <table style="width:100%;color:#ccc;font-size:14px;">
                <tr><td>Acquisition</td><td style="text-align:right">${buyer_price:,.0f}</td></tr>
                <tr><td>Repairs</td><td style="text-align:right">${repairs:,.0f}</td></tr>
                <tr><td>Total invested</td><td style="text-align:right">${buyer_price + repairs:,.0f}</td></tr>
                <tr><td>Sell at (ARV)</td><td style="text-align:right">${arv:,.0f}</td></tr>
                <tr><td>Less closing (8%)</td><td style="text-align:right">-${flip['closing_costs']:,.0f}</td></tr>
                <tr style="color:#c9a84c;font-weight:bold;font-size:16px;">
                    <td>Net profit</td><td style="text-align:right">${flip['profit']:,.0f}</td></tr>
                <tr><td>ROI</td><td style="text-align:right">{flip['roi_pct']}%</td></tr>
            </table>
        </div>"""

    rental_section = ""
    if rent and rent["cap_rate"] > 4:
        rental_section = f"""
        <div style="background:#1a1a2e;border:1px solid #c9a84c33;border-radius:8px;padding:20px;margin:16px 0;">
            <h3 style="color:#c9a84c;margin:0 0 12px;">Rental Scenario</h3>
            <table style="width:100%;color:#ccc;font-size:14px;">
                <tr><td>Monthly rent</td><td style="text-align:right">${rent['monthly_rent']:,.0f}</td></tr>
                <tr><td>Annual gross</td><td style="text-align:right">${rent['annual_rent']:,.0f}</td></tr>
                <tr><td>Annual expenses (40%)</td><td style="text-align:right">-${rent['annual_expenses']:,.0f}</td></tr>
                <tr style="color:#c9a84c;font-weight:bold;">
                    <td>NOI</td><td style="text-align:right">${rent['noi']:,.0f}</td></tr>
                <tr><td>Cap rate</td><td style="text-align:right">{rent['cap_rate']}%</td></tr>
            </table>
        </div>"""

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Deal: {address}</title></head>
<body style="background:#0a0a0f;color:#fff;font-family:'Inter',sans-serif;margin:0;padding:40px;">
<div style="max-width:600px;margin:0 auto;">

    <div style="text-align:center;margin-bottom:32px;">
        <h1 style="font-family:'Cinzel',serif;color:#c9a84c;font-size:20px;letter-spacing:3px;margin:0;">
            EVERLIGHT VENTURES</h1>
        <p style="color:#666;font-size:11px;letter-spacing:2px;margin:4px 0 0;">
            ACQUISITIONS -- PRIVATE DEAL ALERT</p>
    </div>

    <div style="background:#111;border:1px solid #c9a84c55;border-radius:12px;padding:24px;margin-bottom:24px;">
        <h2 style="color:#fff;margin:0 0 4px;font-size:18px;">{address}</h2>
        <p style="color:#999;margin:0 0 16px;font-size:14px;">{city}, {state} | {beds}bd/{baths}ba | {sqft:,} sqft | Built {year}</p>

        <div style="background:#c9a84c22;border-radius:8px;padding:16px;margin-bottom:16px;">
            <p style="color:#c9a84c;font-weight:bold;margin:0 0 4px;font-size:12px;text-transform:uppercase;">
                Why This Deal Exists</p>
            <p style="color:#ddd;margin:0;font-size:14px;">{pain['hook']}</p>
        </div>

        <div style="display:flex;gap:16px;margin-bottom:16px;">
            <div style="flex:1;background:#1a1a2e;border-radius:8px;padding:16px;text-align:center;">
                <p style="color:#999;font-size:11px;margin:0;">PRICE</p>
                <p style="color:#c9a84c;font-size:24px;font-weight:bold;margin:4px 0;">${buyer_price:,.0f}</p>
            </div>
            <div style="flex:1;background:#1a1a2e;border-radius:8px;padding:16px;text-align:center;">
                <p style="color:#999;font-size:11px;margin:0;">ARV</p>
                <p style="color:#fff;font-size:24px;font-weight:bold;margin:4px 0;">${arv:,.0f}</p>
            </div>
            <div style="flex:1;background:#1a1a2e;border-radius:8px;padding:16px;text-align:center;">
                <p style="color:#999;font-size:11px;margin:0;">SPREAD</p>
                <p style="color:#4ade80;font-size:24px;font-weight:bold;margin:4px 0;">${arv - buyer_price:,.0f}</p>
            </div>
        </div>

        {flip_section}
        {rental_section}
    </div>

    <div style="text-align:center;padding:24px;background:#c9a84c;border-radius:8px;">
        <p style="color:#000;font-weight:bold;font-size:16px;margin:0 0 4px;">
            Cash only. 7-14 day close. First buyer locks it.</p>
        <p style="color:#000;font-size:14px;margin:0;">
            Reply to this email or contact support@everlightventures.io</p>
    </div>

    <p style="text-align:center;color:#444;font-size:11px;margin-top:24px;">
        Everlight Ventures -- Acquisitions | everlightventures.io/wholesale<br>
        This is a private deal alert for qualified buyers only.</p>
</div>
</body>
</html>"""


# ---------------------------------------------------------------------------
# AI-ENHANCED PITCH (uses Claude for custom copy)
# ---------------------------------------------------------------------------

def generate_ai_pitch(deal: dict) -> str:
    """Use Claude to write a custom pitch. Falls back to templates."""
    try:
        import requests
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            return ""

        arv = deal.get("arv", 0) or deal.get("estimated_arv", 0) or deal.get("zestimate", 0)
        repairs = deal.get("repair_estimate", 0)
        buyer_price = (deal.get("asking_price", 0) or deal.get("our_offer", 0)) + deal.get("assignment_fee", 10000)

        prompt = f"""Write a 3-paragraph investment pitch email for this property deal.

Property: {deal.get('address', '?')}, {deal.get('city', '?')}, {deal.get('state', '?')}
Type: {deal.get('property_type', 'SFR')} | {deal.get('beds', '?')}bd/{deal.get('baths', '?')}ba | {deal.get('sqft', '?')} sqft
Lead type: {deal.get('lead_type', 'distressed')}
Price: ${buyer_price:,.0f}
ARV: ${arv:,.0f}
Repairs: ${repairs:,.0f}
Spread: ${arv - buyer_price:,.0f}

Paragraph 1: The pain point -- why this seller is motivated. Be specific to the lead type.
Paragraph 2: The numbers -- purchase price, repairs, ARV, projected profit, ROI.
Paragraph 3: The urgency -- why a buyer should act now. Cash only, 7-14 day close.

Tone: professional, direct, numbers-first. Sound like a private equity acquisitions desk, not a wholesaler. Do not use the word wholesale anywhere.
Sign as: Rich, Everlight Ventures -- Acquisitions"""

        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": "claude-sonnet-4-20250514", "max_tokens": 600,
                  "system": "You write concise investment pitch emails for a real estate acquisitions firm. No buzzwords. Numbers first. 3 paragraphs max.",
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=30)

        if resp.status_code == 200:
            return resp.json()["content"][0]["text"]
    except Exception as e:
        log.debug(f"AI pitch failed: {e}")
    return ""


# ---------------------------------------------------------------------------
# MAIN: Generate pitch for a deal
# ---------------------------------------------------------------------------

def pitch_deal(deal: dict) -> dict:
    """
    Main entry point. Takes a deal dict, returns full pitch package.
    Tries AI first, falls back to templates.
    """
    log.info(f"Generating pitch for {deal.get('address', '?')}")

    # Try AI pitch first
    ai_email = generate_ai_pitch(deal)
    template_pitch = generate_pitch(deal)

    if ai_email:
        template_pitch["email_pitch"] = ai_email
        log.info("  Used AI-generated email pitch")
    else:
        log.info("  Used template email pitch")

    return template_pitch


if __name__ == "__main__":
    # Test with a sample deal
    sample = {
        "address": "1847 Peachtree Rd",
        "city": "Atlanta",
        "state": "GA",
        "zip_code": "30310",
        "asking_price": 150000,
        "arv": 245000,
        "estimated_arv": 245000,
        "repair_estimate": 22000,
        "assignment_fee": 15000,
        "lead_type": "code_violation",
        "property_type": "sfr",
        "beds": 3,
        "baths": 2,
        "sqft": 1450,
        "year_built": 1962,
    }
    result = pitch_deal(sample)
    print("\n=== EMAIL PITCH ===")
    print(result["email_pitch"])
    print("\n=== SMS PITCH ===")
    print(result["sms_pitch"])
    print(f"\n=== ONE-PAGER saved to pitches/ ===")
