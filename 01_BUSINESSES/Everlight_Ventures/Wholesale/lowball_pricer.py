"""lowball_pricer -- we set the price. We do not ask. But we SHOW THE MATH.

The wholesale mentality:
  Find a motivated seller. Run the math. Tell them OUR number AND why it's
  their best move. Sell the assignment to a buyer at our number + assignment
  fee. Buyer rehabs and resells at 2x. Everyone makes money.

Why "show the math" matters:
  A seller hears "$122k for a $280k house" and feels insulted.
  The same seller hears:
    - 'Your situation: vacant property burning $1,200/mo carrying cost'
    - 'Retail path: $230k list - $14k commission - $25k repair credits
       - $7k carrying over 6 months = $184k net IF it sells'
    - 'Our path: $122k cash, no commission, no repairs, no showings,
       14-day close, 7-day walk-away, certain'
    - 'Net difference: $62k more on retail BUT 6 months later,
       and only IF it sells'
  ...and they feel SHOWN, not insulted.

What this module produces:
  An offer pack with FIVE blocks, in this order:
    1. Pain mirror -- their specific situation acknowledged in their words
    2. Market context -- live Zillow / area stats showing we know the comp
    3. Retail comparison -- what they'd actually net selling traditionally
    4. The number -- declarative, in a gold box, with our value props
    5. Trust + walk-away -- why we're not the late-night-call wholesalers

Compute mode: pure math (compute_offer)
Render mode: narrative + math (render_offer_pack)

Usage from a lead:
  from lowball_pricer import build_offer_for_lead
  pack = build_offer_for_lead(lead, assignment_fee=15000)
  send_branded_email(to=lead.owner_email,
                     subject=pack['email_subject'],
                     content_html=pack['email_body'])
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# Allow reuse of pitch_generator's pain identifier + market stats
for p in (
    "/home/opc/wholesale/pitches",
    "/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale/pitches",
):
    if p not in sys.path and Path(p).exists():
        sys.path.insert(0, p)


# Market multiplier overrides -- adjust 70% rule by market vibe
MARKET_MULTIPLIERS = {
    "ATL_URBAN":     0.65,
    "PHX_URBAN":     0.65,
    "TPA_URBAN":     0.65,
    "DEFAULT":       0.70,
    "STL_OUTER":     0.75,
    "MEM_OUTER":     0.75,
    "OH_RURAL":      0.75,
}

DEFAULT_ASSIGNMENT_FEE = 15000.0       # used as floor + as fixed-fee fallback
ASSIGNMENT_FEE_FLOOR = 15000.0          # minimum fee per deal -- forces deal-selection discipline
ASSIGNMENT_FEE_BASE_PCT = 0.075         # 7.5% standard
ASSIGNMENT_FEE_CEILING = 75000.0        # safety cap -- never charge more than this no matter the math
MIN_OFFER_USD = 5000.0

# Retail-path standard deductions (what they'd actually pay listing traditionally)
AGENT_COMMISSION_PCT = 0.06        # 6% buyer + listing agent
SELLER_CONCESSIONS_PCT = 0.02      # ~2% concessions buyers ask for at close
TYPICAL_RETAIL_DOM_MONTHS = 4      # 120 days from list to close in most markets
DEFAULT_CARRY_PER_MONTH = 1200     # mortgage + tax + insurance + utilities
DEFAULT_REPAIR_CREDIT_AT_INSPECTION = 0.10  # 10% of repair budget typically credits


def _compute_assignment_fee(
    arv: float,
    lead_type: str = "",
    motivation_tier: int = 3,
    market_label: str = "",
) -> tuple[float, float, str]:
    """Smart dynamic assignment fee. Returns (fee_dollars, effective_pct, reasoning).

    Formula layers:
      1. Base 7.5% of ARV
      2. Distress adjustment:
           +2.5% foreclosure (urgency = leverage)
           +1.0% vacant / tax_lien / absentee / inherited / probate
           -0.5% expired_listing / fsbo (market-tested seller, harder to lock)
      3. ARV tier:
           +1.0% on >= $500k (big deal = bigger fee tolerance)
           -1.5% on < $150k (cheap deal = thin spread, can't squeeze)
      4. Motivation intelligence (from owner_intel):
           +0.5% on tier 4-5 (high motivation)
           -1.0% on tier 1-2 (low motivation)
      5. Floor enforcement: $15k minimum
      6. Ceiling enforcement: $75k cap

    Why this matters (real examples):
      - $280k pre-foreclosure absentee tier 4    -> 0.075+.025+.01+.005 = 11.5% = $32,200
      - $325k vacant tier 3                       -> 0.075+.01 = 8.5% = $27,625
      - $180k expired-listing owner-occupied tier 2 -> 0.075-.005-.015-.01 = 4.5% = $8,100 -> floor $15k
      - $550k inherited tier 5                    -> 0.075+.01+.01+.005 = 10% = $55,000
      - $750k pre-foreclosure absentee tier 5     -> 0.075+.025+.01+.01+.005 = 12.5% = $93,750 -> ceiling $75k

    The system charges what each specific deal can mathematically bear, not flat $15k everywhere.
    """
    pct = ASSIGNMENT_FEE_BASE_PCT
    notes = ["base 7.5%"]

    lt = (lead_type or "").lower()
    if "foreclosure" in lt:
        pct += 0.025
        notes.append("+2.5% foreclosure leverage")
    elif "vacant" in lt or "tax_lien" in lt:
        pct += 0.01
        notes.append("+1% distressed property")
    elif "absentee" in lt or "inherited" in lt or "probate" in lt:
        pct += 0.01
        notes.append("+1% out-of-touch owner")
    elif "expired_listing" in lt or "fsbo" in lt:
        pct -= 0.005
        notes.append("-0.5% market-tested seller")

    if arv >= 500000:
        pct += 0.01
        notes.append("+1% large-deal bump (>$500k)")
    elif arv < 150000:
        pct -= 0.015
        notes.append("-1.5% small-deal compression (<$150k)")

    if motivation_tier and motivation_tier >= 4:
        pct += 0.005
        notes.append(f"+0.5% high motivation (tier {motivation_tier})")
    elif motivation_tier and motivation_tier <= 2:
        pct -= 0.01
        notes.append(f"-1% low motivation (tier {motivation_tier})")

    raw_fee = arv * pct
    fee = max(ASSIGNMENT_FEE_FLOOR, min(raw_fee, ASSIGNMENT_FEE_CEILING))
    effective_pct = fee / arv if arv else 0

    if fee == ASSIGNMENT_FEE_FLOOR and raw_fee < ASSIGNMENT_FEE_FLOOR:
        notes.append(f"FLOOR enforced (raw ${raw_fee:,.0f} -> ${fee:,.0f})")
    elif fee == ASSIGNMENT_FEE_CEILING and raw_fee > ASSIGNMENT_FEE_CEILING:
        notes.append(f"CEILING enforced (raw ${raw_fee:,.0f} -> ${fee:,.0f})")

    reasoning = "; ".join(notes) + f" | final {pct*100:.1f}% = ${fee:,.0f} (effective {effective_pct*100:.1f}%)"
    return fee, effective_pct, reasoning


@dataclass
class LowballOffer:
    arv: float
    repair: float
    assignment_fee: float
    market_multiplier: float
    seller_offer: float       # THE NUMBER
    buyer_ask: float          # what we tell the buyer
    spread_to_buyer: float    # buyer's equity room after rehab
    rule_70_check: bool
    confidence: str
    reasoning: str


@dataclass
class RetailComparison:
    """What the seller would actually net via traditional listing."""
    list_price_estimate: float
    agent_commission: float
    seller_concessions: float
    repair_credits: float
    carry_cost_total: float
    months_to_close: int
    retail_net_proceeds: float
    cash_offer_today: float
    delta_dollars: float       # retail_net - cash_offer (positive = retail higher)
    delta_per_month_waiting: float
    risk_adjusted_delta: float  # delta minus probability-weighted "what if it doesn't sell"


def _pick_market_multiplier(market_label: str = "") -> tuple[float, str]:
    m = (market_label or "").upper()
    for key, mult in MARKET_MULTIPLIERS.items():
        if key in m:
            return mult, key
    return MARKET_MULTIPLIERS["DEFAULT"], "DEFAULT"


def compute_offer_mortgage_balance(
    mortgage_balance: float,
    arv: float,
    repair: float,
    assignment_fee: float = DEFAULT_ASSIGNMENT_FEE,
) -> LowballOffer:
    """PRE-FORECLOSURE variant. Offer = mortgage payoff amount.

    Seller walks away with $0 cash but no foreclosure on their credit
    (worth $5-15k of credit damage avoided). Best for sellers behind on
    payments where retail won't sell fast enough to beat the auction date.

    Math check: this only works if (ARV * 0.70) >= mortgage_balance + repair + assignment_fee.
    If the spread isn't there, the deal can't be done at this number -- walk.
    """
    seller_offer = mortgage_balance
    buyer_ask = seller_offer + assignment_fee
    spread_to_buyer = arv - buyer_ask - repair
    rule_70_check = (buyer_ask + repair) <= (arv * 0.70)

    if not rule_70_check:
        confidence = "low"
    elif spread_to_buyer >= arv * 0.20:
        confidence = "high"
    elif spread_to_buyer >= arv * 0.10:
        confidence = "medium"
    else:
        confidence = "low"

    reasoning = (
        f"PRE-FORECLOSURE MODE: offer = mortgage payoff {_money(mortgage_balance)}. "
        f"Seller walks with $0 cash but avoids foreclosure on credit. "
        f"Buyer all-in {_money(buyer_ask + repair)} on {_money(arv)} ARV. "
        f"70% rule: {'PASSES' if rule_70_check else 'FAILS -- walk away'}"
    )

    return LowballOffer(
        arv=arv, repair=repair, assignment_fee=assignment_fee,
        market_multiplier=1.0,  # not used in this mode
        seller_offer=round(seller_offer, 2),
        buyer_ask=round(buyer_ask, 2),
        spread_to_buyer=round(spread_to_buyer, 2),
        rule_70_check=rule_70_check,
        confidence=confidence,
        reasoning=reasoning,
    )


def compute_offer_tax_assessed(
    tax_assessed_value: float,
    repair: float,
    assignment_fee: float = DEFAULT_ASSIGNMENT_FEE,
    multiplier: float = 0.80,
) -> LowballOffer:
    """TAX-ASSESSED variant. Offer = tax_assessed_value * 0.80 (default).

    Used when ARV data is sparse (rural, vacant land, weird properties,
    or where Zillow doesn't have good comps). Tax-assessed value is usually
    60-80% of true market value, so 80% of tax-assessed = roughly 50-65% of
    true ARV -- which is an aggressive lowball but defensible because
    tax-assessed is a documented public number.

    Best for: text-blast campaigns to lists where you don't have time to
    look up ARV per-property.
    """
    seller_offer = tax_assessed_value * multiplier
    buyer_ask = seller_offer + assignment_fee
    # Estimate ARV as ~150% of tax_assessed (tax is typically 60-70% of market)
    arv_est = tax_assessed_value * 1.5
    spread_to_buyer = arv_est - buyer_ask - repair
    rule_70_check = (buyer_ask + repair) <= (arv_est * 0.70)

    confidence = "medium" if rule_70_check else "low"

    reasoning = (
        f"TAX-ASSESSED MODE: offer = {multiplier:.2f} * tax_assessed_value "
        f"({_money(tax_assessed_value)}) = {_money(seller_offer)}. "
        f"ARV est at {_money(arv_est)} (1.5x tax-assessed). "
        f"70% rule: {'PASSES' if rule_70_check else 'FAILS'}"
    )

    return LowballOffer(
        arv=arv_est, repair=repair, assignment_fee=assignment_fee,
        market_multiplier=multiplier,
        seller_offer=round(seller_offer, 2),
        buyer_ask=round(buyer_ask, 2),
        spread_to_buyer=round(spread_to_buyer, 2),
        rule_70_check=rule_70_check,
        confidence=confidence,
        reasoning=reasoning,
    )


def compute_offer(
    arv: float,
    repair: float,
    assignment_fee: float = DEFAULT_ASSIGNMENT_FEE,
    market_label: str = "",
    seller_pre_foreclosure: bool = False,
    seller_carry_cost_monthly: float = 0.0,
    seller_months_until_foreclosure: int = 0,
) -> LowballOffer:
    """Compute the ONE number to offer the seller. Pure math."""
    mult, used_market = _pick_market_multiplier(market_label)
    mao_raw = (arv * mult) - repair - assignment_fee

    carry_offset = 0.0
    if seller_pre_foreclosure and seller_months_until_foreclosure > 0:
        carry_offset = seller_carry_cost_monthly * seller_months_until_foreclosure
        mao_raw += carry_offset * 0.5

    seller_offer = max(MIN_OFFER_USD, mao_raw)
    buyer_ask = seller_offer + assignment_fee
    spread_to_buyer = arv - buyer_ask - repair
    rule_70_check = (buyer_ask + repair) <= (arv * 0.70)

    if spread_to_buyer >= arv * 0.20:
        confidence = "high"
    elif spread_to_buyer >= arv * 0.10:
        confidence = "medium"
    else:
        confidence = "low"

    reasoning = (
        f"ARV {arv:,.0f} * {mult:.2f} = {arv*mult:,.0f}; "
        f"-${repair:,.0f} repair -${assignment_fee:,.0f} fee "
        f"{'+' + str(int(carry_offset*0.5)) + ' carry-credit' if carry_offset else ''} "
        f"= seller offer ${seller_offer:,.0f}. Buyer keeps ${spread_to_buyer:,.0f} of equity."
    )

    return LowballOffer(
        arv=arv, repair=repair, assignment_fee=assignment_fee,
        market_multiplier=mult,
        seller_offer=round(seller_offer, 2),
        buyer_ask=round(buyer_ask, 2),
        spread_to_buyer=round(spread_to_buyer, 2),
        rule_70_check=rule_70_check,
        confidence=confidence,
        reasoning=reasoning,
    )


def compute_retail_comparison(
    arv: float,
    repair: float,
    cash_offer: float,
    list_price_pct_of_arv: float = 0.95,
    carry_per_month: float = DEFAULT_CARRY_PER_MONTH,
    months_to_close: int = TYPICAL_RETAIL_DOM_MONTHS,
    sale_probability_pct: float = 75.0,
) -> RetailComparison:
    """What would they ACTUALLY net listing it traditionally?

    This is the persuasion math. We're not lying about the retail path -- we're
    showing the realistic version that includes commission, concessions, repair
    credits, and the carry burn while it sits on market.

    `sale_probability_pct` accounts for "what if it doesn't sell at the list
    price" -- dropping prices, longer DOM, withdrawing the listing entirely.
    Risk-adjusted delta = (retail_net - cash_offer) * sale_probability_pct.
    """
    list_price = arv * list_price_pct_of_arv
    commission = list_price * AGENT_COMMISSION_PCT
    concessions = list_price * SELLER_CONCESSIONS_PCT
    repair_credits = repair * DEFAULT_REPAIR_CREDIT_AT_INSPECTION
    carry_total = carry_per_month * months_to_close

    retail_net = list_price - commission - concessions - repair_credits - carry_total
    delta = retail_net - cash_offer
    risk_adj = delta * (sale_probability_pct / 100.0)
    per_month = delta / max(months_to_close, 1)

    return RetailComparison(
        list_price_estimate=round(list_price, 2),
        agent_commission=round(commission, 2),
        seller_concessions=round(concessions, 2),
        repair_credits=round(repair_credits, 2),
        carry_cost_total=round(carry_total, 2),
        months_to_close=months_to_close,
        retail_net_proceeds=round(retail_net, 2),
        cash_offer_today=round(cash_offer, 2),
        delta_dollars=round(delta, 2),
        delta_per_month_waiting=round(per_month, 2),
        risk_adjusted_delta=round(risk_adj, 2),
    )


# ── Render the FULL offer pack with pain + market + retail + the number + trust ──

def _money(n: float) -> str:
    return f"${n:,.0f}"


def _pain_block_html(pains: list) -> str:
    """Mirror the seller's specific situation in their language. Acknowledges
    their pain so they feel SEEN before they feel sold."""
    if not pains:
        return ""
    items = "".join(f"<li>{p.one_liner}</li>" for p in pains[:3])
    return (
        f"<div style='background:#fafafa;border-left:4px solid #D4A843;padding:14px 18px;margin:18px 0;'>"
        f"<div style='color:#7a5c00;font-weight:600;text-transform:uppercase;letter-spacing:2px;font-size:11px;'>"
        f"Where you're at, near as we can tell</div>"
        f"<ul style='margin:8px 0 0 18px;padding:0;color:#444;font-size:14px;line-height:1.6;'>"
        f"{items}"
        f"</ul>"
        f"<p style='color:#666;font-size:12px;margin:10px 0 0;'>"
        f"If we got this wrong, please tell us. We'd rather know than guess.</p>"
        f"</div>"
    )


def _market_block_html(stats) -> str:
    """Live area stats so they know we did our homework, not throwing darts."""
    if not stats:
        return ""
    return (
        f"<div style='background:#fff;border:1px solid #eee;padding:14px 18px;margin:18px 0;'>"
        f"<div style='color:#D4A843;font-weight:600;letter-spacing:2px;text-transform:uppercase;font-size:11px;'>"
        f"What your market looks like right now</div>"
        f"<table style='width:100%;border-collapse:collapse;font-size:13px;margin-top:8px;'>"
        f"<tr><td style='padding:4px 0;color:#999;'>Median home value</td>"
        f"<td style='padding:4px 0;text-align:right;'><strong>{_money(stats.median_home_value)}</strong></td></tr>"
        f"<tr><td style='padding:4px 0;color:#999;'>Days on market (current)</td>"
        f"<td style='padding:4px 0;text-align:right;'><strong>{stats.median_days_on_market} days</strong></td></tr>"
        f"<tr><td style='padding:4px 0;color:#999;'>Investor share of buys</td>"
        f"<td style='padding:4px 0;text-align:right;'><strong>{stats.investor_purchase_share_pct:.0f}%</strong></td></tr>"
        f"<tr><td style='padding:4px 0;color:#999;'>Median 3BR rent</td>"
        f"<td style='padding:4px 0;text-align:right;'><strong>{_money(stats.median_rent_3br)}/mo</strong></td></tr>"
        f"</table>"
        f"<p style='color:#666;font-size:11px;margin:8px 0 0;'>Source: {stats.source_quarter} Zillow / Redfin / NAR</p>"
        f"</div>"
    )


def _retail_comparison_html(retail: RetailComparison, the_number: float) -> str:
    """Side-by-side: traditional listing vs our cash offer.

    The persuasion math. Retail looks higher on paper, but after commissions,
    concessions, repair credits, and carrying costs, the gap usually shrinks
    to a few months of waiting. This block shows that honestly.
    """
    delta = retail.delta_dollars
    delta_color = "#0F7B3D" if delta < 5000 else "#7a5c00"
    delta_phrase = (
        "About the same money" if abs(delta) < 5000
        else f"{_money(abs(delta))} more on retail" if delta > 0
        else f"{_money(abs(delta))} more in cash today"
    )

    return (
        f"<div style='background:#0A0A0A;color:#E8E8E8;padding:18px 22px;margin:18px 0;border-left:6px solid #D4A843;'>"
        f"<div style='color:#D4A843;font-weight:600;text-transform:uppercase;letter-spacing:2px;font-size:11px;'>"
        f"Honest comparison: retail vs cash today</div>"

        f"<table style='width:100%;border-collapse:collapse;font-size:14px;margin-top:12px;color:#E8E8E8;'>"
        f"<tr style='border-bottom:1px solid #333;'>"
        f"<td style='padding:8px 6px;'><strong>Retail listing path</strong></td>"
        f"<td style='padding:8px 6px;text-align:right;'></td></tr>"
        f"<tr><td style='padding:4px 6px;color:#aaa;'>List price (~95% of ARV)</td>"
        f"<td style='padding:4px 6px;text-align:right;'>{_money(retail.list_price_estimate)}</td></tr>"
        f"<tr><td style='padding:4px 6px;color:#aaa;'>- Agent commission (6%)</td>"
        f"<td style='padding:4px 6px;text-align:right;color:#C77;'>-{_money(retail.agent_commission)}</td></tr>"
        f"<tr><td style='padding:4px 6px;color:#aaa;'>- Buyer concessions (~2%)</td>"
        f"<td style='padding:4px 6px;text-align:right;color:#C77;'>-{_money(retail.seller_concessions)}</td></tr>"
        f"<tr><td style='padding:4px 6px;color:#aaa;'>- Repair credits at inspection</td>"
        f"<td style='padding:4px 6px;text-align:right;color:#C77;'>-{_money(retail.repair_credits)}</td></tr>"
        f"<tr><td style='padding:4px 6px;color:#aaa;'>- Carrying cost ({retail.months_to_close} months while listed)</td>"
        f"<td style='padding:4px 6px;text-align:right;color:#C77;'>-{_money(retail.carry_cost_total)}</td></tr>"
        f"<tr style='border-top:1px solid #555;'>"
        f"<td style='padding:8px 6px;'><strong>Retail net (in {retail.months_to_close} months, IF it sells)</strong></td>"
        f"<td style='padding:8px 6px;text-align:right;'><strong>{_money(retail.retail_net_proceeds)}</strong></td></tr>"

        f"<tr><td colspan='2' style='padding:14px 0 0;'></td></tr>"

        f"<tr style='border-bottom:1px solid #333;background:#1a1a1a;'>"
        f"<td style='padding:8px 6px;'><strong>Our cash path</strong></td>"
        f"<td style='padding:8px 6px;text-align:right;'></td></tr>"
        f"<tr><td style='padding:4px 6px;color:#aaa;'>Cash offer today</td>"
        f"<td style='padding:4px 6px;text-align:right;'><strong style='color:#D4A843;'>{_money(the_number)}</strong></td></tr>"
        f"<tr><td style='padding:4px 6px;color:#aaa;'>- Commission</td>"
        f"<td style='padding:4px 6px;text-align:right;color:#0F7B3D;'>$0</td></tr>"
        f"<tr><td style='padding:4px 6px;color:#aaa;'>- Concessions</td>"
        f"<td style='padding:4px 6px;text-align:right;color:#0F7B3D;'>$0</td></tr>"
        f"<tr><td style='padding:4px 6px;color:#aaa;'>- Repair credits</td>"
        f"<td style='padding:4px 6px;text-align:right;color:#0F7B3D;'>$0</td></tr>"
        f"<tr><td style='padding:4px 6px;color:#aaa;'>- Carrying cost while listed</td>"
        f"<td style='padding:4px 6px;text-align:right;color:#0F7B3D;'>$0</td></tr>"
        f"<tr style='border-top:1px solid #555;'>"
        f"<td style='padding:8px 6px;'><strong>Cash net (in 14 days, certain)</strong></td>"
        f"<td style='padding:8px 6px;text-align:right;'><strong>{_money(the_number)}</strong></td></tr>"
        f"</table>"

        f"<div style='margin-top:14px;padding-top:12px;border-top:2px solid #D4A843;'>"
        f"<div style='color:#D4A843;font-size:13px;'>The honest delta:</div>"
        f"<div style='font-size:18px;color:{delta_color};margin-top:4px;'>"
        f"<strong>{delta_phrase}</strong> -- but that retail number assumes it sells in {retail.months_to_close} months and survives inspection without further credits.</div>"
        f"</div>"
        f"</div>"
    )


def _benefits_block_html(carry_savings_per_month: float = 0.0) -> str:
    """The non-monetary upside they're not factoring in."""
    carry_line = ""
    if carry_savings_per_month > 0:
        carry_line = f"<li>Stop bleeding ~{_money(carry_savings_per_month)}/mo in mortgage + taxes + insurance the day we close</li>"

    return (
        f"<div style='background:#fff;padding:14px 18px;margin:18px 0;border:1px solid #eee;'>"
        f"<div style='color:#D4A843;font-weight:600;text-transform:uppercase;letter-spacing:2px;font-size:11px;'>"
        f"What you also get with cash</div>"
        f"<ul style='margin:8px 0 0 18px;padding:0;color:#444;font-size:14px;line-height:1.7;'>"
        f"<li>14-day close. Done. Cash in your account.</li>"
        f"<li>No showings, no open houses, no strangers walking your property</li>"
        f"<li>No repairs. We buy as-is, every condition.</li>"
        f"<li>No inspection drama. We've already underwritten the property.</li>"
        f"<li>7-day Quality Assurance Review Period -- you can walk away with no penalty in the first 7 days. Right in the contract.</li>"
        f"{carry_line}"
        f"<li>One closing date you set. No 'just one more buyer is coming through.'</li>"
        f"</ul></div>"
    )


def _the_number_block_html(the_number: float, addr_short: str) -> str:
    """The gold box. Declarative. The number. No 'starting at' or 'up to'."""
    return (
        f"<div style='background:#0A0A0A;color:#D4A843;padding:30px;text-align:center;"
        f"margin:24px 0;border:2px solid #D4A843;'>"
        f"<div style='text-transform:uppercase;letter-spacing:3px;font-size:11px;'>OUR CASH OFFER</div>"
        f"<div style='font-family:Playfair Display,Georgia,serif;font-size:48px;margin:8px 0;color:#D4A843;'>"
        f"{_money(the_number)}</div>"
        f"<div style='color:#aaa;font-size:12px;'>{addr_short} -- 14 day close, as-is, zero commission</div>"
        f"</div>"
    )


def _trust_block_html() -> str:
    return (
        f"<div style='background:#fafafa;padding:14px 18px;margin:18px 0;border-radius:4px;'>"
        f"<div style='color:#7a5c00;font-weight:600;text-transform:uppercase;letter-spacing:2px;font-size:11px;'>"
        f"Why us, specifically</div>"
        f"<ul style='margin:8px 0 0 18px;padding:0;color:#555;font-size:13px;line-height:1.7;'>"
        f"<li>We're Atlanta-based. Real phone, real address, real reviews.</li>"
        f"<li>You'll deal with a named human (Piper for acquisitions, Hammer for closing) -- not 'the team'</li>"
        f"<li>Every offer comes with the math we used. We show our work.</li>"
        f"<li>Our PSA includes a 7-day walk-away. You're never stuck.</li>"
        f"<li>We close at title companies you can verify, not in random offices</li>"
        f"</ul></div>"
    )


def build_offer_for_lead(
    lead: Any,
    assignment_fee: Optional[float] = None,
    market_label: Optional[str] = None,
    use_dynamic_fee: bool = True,
) -> dict:
    """Build the full offer pack from a PropertyLead-shaped object.

    Assignment fee:
      - If `assignment_fee` is passed explicitly, that value is used (override).
      - Otherwise, _compute_assignment_fee() runs and dynamically scales the fee
        based on ARV, distress signal, motivation tier, and market label.
      - Set use_dynamic_fee=False to force the $15k flat (legacy behavior).

    Reuses pitch_generator's pain identifier + area_market_data for stats.
    Returns a dict with email_subject, email_body, plain_text, sms_body,
    phone_script, and the underlying offer + retail_comparison + fee_breakdown.
    """
    # Lazy imports so this module doesn't hard-fail without Django/pitch deps
    try:
        from pitch_generator import _identify_seller_pain, _live_stats  # type: ignore
    except Exception:
        _identify_seller_pain = lambda l, s: []
        _live_stats = lambda l: None

    arv = float(getattr(lead, "estimated_arv", 0) or 0)
    repair = float(getattr(lead, "estimated_repair", 0) or 0)
    if repair == 0:
        sqft = int(getattr(lead, "sqft", 0) or 1200)
        repair = sqft * 25  # rough $25/sqft fallback

    # Pull live market data
    stats = None
    try:
        stats = _live_stats(lead)
        if stats and arv == 0:
            from area_market_data import estimate_arv  # type: ignore
            bedrooms = int(getattr(lead, "bedrooms", 0) or 3)
            sqft = int(getattr(lead, "sqft", 0) or 1200)
            arv = float(estimate_arv(stats, bedrooms=bedrooms, sqft=sqft))
    except Exception:
        pass

    if arv == 0:
        # Last fallback: derive from local averages
        arv = 200000

    # Pain points from existing logic
    pains = _identify_seller_pain(lead, stats) if _identify_seller_pain else []

    # Market label inference
    if not market_label:
        city = (getattr(lead, "city", "") or "").upper()
        state = (getattr(lead, "state", "") or "").upper()
        if "ATLANTA" in city or state == "GA":
            market_label = "ATL_URBAN"
        elif "PHOENIX" in city or state == "AZ":
            market_label = "PHX_URBAN"
        elif "TAMPA" in city or state == "FL":
            market_label = "TPA_URBAN"
        elif "ST. LOUIS" in city or "SAINT LOUIS" in city or state == "MO":
            market_label = "STL_OUTER"
        elif "MEMPHIS" in city or state == "TN":
            market_label = "MEM_OUTER"
        elif state == "OH":
            market_label = "OH_RURAL"
        else:
            market_label = "DEFAULT"

    # Estimate carrying cost based on property type
    carry_per_month = DEFAULT_CARRY_PER_MONTH
    if hasattr(lead, "is_absentee") and getattr(lead, "is_absentee", False):
        carry_per_month = 1500  # absentee owners typically have higher carry

    # Pre-foreclosure indicator (boosts our offer math)
    lead_type_str = (getattr(lead, "lead_type", "") or "").lower()
    pf = "foreclosure" in lead_type_str

    # ── Dynamic assignment fee (intelligence layer) ──
    # Pull motivation_tier from owner_intel if available, else default 3
    motivation_tier = 3
    try:
        from owner_intel import build_owner_intel  # type: ignore
        intel = build_owner_intel(lead)
        if intel and getattr(intel, "motivation_tier", None):
            motivation_tier = int(intel.motivation_tier)
    except Exception:
        pass

    if assignment_fee is None and use_dynamic_fee:
        fee_dollars, effective_pct, fee_reasoning = _compute_assignment_fee(
            arv=arv, lead_type=lead_type_str,
            motivation_tier=motivation_tier, market_label=market_label,
        )
        assignment_fee = fee_dollars
    elif assignment_fee is None:
        assignment_fee = DEFAULT_ASSIGNMENT_FEE
        effective_pct = assignment_fee / arv if arv else 0
        fee_reasoning = f"flat ${assignment_fee:,.0f} (dynamic disabled)"
    else:
        effective_pct = assignment_fee / arv if arv else 0
        fee_reasoning = f"caller-override ${assignment_fee:,.0f}"

    offer = compute_offer(
        arv=arv, repair=repair, assignment_fee=assignment_fee,
        market_label=market_label,
        seller_pre_foreclosure=pf,
        seller_carry_cost_monthly=carry_per_month if pf else 0.0,
        seller_months_until_foreclosure=3 if pf else 0,
    )

    retail = compute_retail_comparison(
        arv=arv, repair=repair,
        cash_offer=offer.seller_offer,
        carry_per_month=carry_per_month,
    )

    # Get owner first name (with entity guard)
    try:
        from pitch_generator import _first_name as pg_first_name  # type: ignore
        first_name = pg_first_name(getattr(lead, "owner_name", "") or "")
    except Exception:
        first_name = "there"

    addr = getattr(lead, "address", "") or "your property"
    addr_short = addr.split(",")[0].strip() if "," in addr else addr
    city = getattr(lead, "city", "") or ""

    # ── Render HTML body with all 5 blocks ──
    html_body = (
        f"<p>Hi {first_name},</p>"
        f"<p>Piper at Everlight Ventures here. I want to make this as straightforward as possible -- "
        f"here's the situation as we see it, here's the math, here's our number, and here's the comparison "
        f"to listing it traditionally. You decide.</p>"

        f"{_pain_block_html(pains)}"
        f"{_market_block_html(stats)}"
        f"{_the_number_block_html(offer.seller_offer, addr_short)}"
        f"{_retail_comparison_html(retail, offer.seller_offer)}"
        f"{_benefits_block_html(carry_per_month)}"
        f"{_trust_block_html()}"

        f"<p style='margin-top:18px;'><strong>Yes or no in 24 hours.</strong></p>"
        f"<p>Reply <strong>YES</strong> -- contract goes out today, EMD lands at title within 48 hours.<br>"
        f"Reply <strong>PASS</strong> -- we never bother you again. No hard feelings.</p>"

        f"<p>Piper Reeves<br>"
        f"<em>Acquisitions, Everlight Ventures</em><br>"
        f"<a href='mailto:piper@everlightventures.io' style='color:#D4A843;'>piper@everlightventures.io</a> | "
        f"(404) 800-4380</p>"
    )

    plain_text = (
        f"Hi {first_name}, Piper at Everlight Ventures.\n\n"
        f"Cash offer for {addr_short}: {_money(offer.seller_offer)}\n"
        f"14-day close, as-is, zero commission, 7-day walk-away clause.\n\n"
        f"Honest comparison:\n"
        f"  Retail path (in {retail.months_to_close} months IF it sells):\n"
        f"    List ~{_money(retail.list_price_estimate)} - commission - credits - carrying = {_money(retail.retail_net_proceeds)} net\n"
        f"  Cash path (in 14 days, certain):\n"
        f"    {_money(offer.seller_offer)} cash, $0 deductions\n\n"
        f"Reply YES for contract today. Reply PASS to opt out.\n"
        f"Holds 24 hours.\n\n"
        f"Piper Reeves, Everlight Ventures"
    )

    sms_body = (
        f"Hi {first_name}, Hammer @ Everlight. Cash offer for {addr_short}: {_money(offer.seller_offer)}. "
        f"Retail nets ~{_money(retail.retail_net_proceeds)} in {retail.months_to_close}mo IF it sells. "
        f"Cash today, 14d close, $0 commission. Reply YES for contract. PASS to opt out."
    )

    pain_lines = "\n".join("  - " + p.one_liner for p in pains[:3]) if pains else "  - I know managing this isn't easy."
    phone_script = f"""
PHONE SCRIPT -- {first_name} ({addr_short})
============================================

OPEN:
"Hi {first_name}, Hammer with Everlight Ventures. Got 90 seconds?"

WHERE THEY'RE AT (mirror):
{pain_lines}

THE NUMBER:
"Our cash offer is {_money(offer.seller_offer)}. 14-day close, zero commission, as-is. Firm number."

THE HONEST COMPARISON:
"Listing it retail, you'd net about {_money(retail.retail_net_proceeds)} -- but only IF it sells in 4 months,
and that's after agent commission, repair credits, and carrying costs.
Cash today is certain in 14 days."

THE WALK-AWAY:
"Our PSA has a 7-day Quality Assurance Review Period. You can walk away with no penalty
in the first 7 days. Right in the contract. You're never stuck."

CLOSE:
"YES, the contract goes out today. PASS, we never bother you again. Either way, you tell me right now.
And if you need to think on it, the offer holds 24 hours."

IF THEY COUNTER:
"I appreciate the ask but the math doesn't move. {_money(offer.seller_offer)} is firm.
If it doesn't work I get it -- best of luck with it."
"""

    return {
        "email_subject": f"Cash offer for {addr_short}: {_money(offer.seller_offer)}, 14-day close",
        "email_body": html_body,
        "plain_text": plain_text,
        "sms_body": sms_body,
        "phone_script": phone_script,
        "the_number": offer.seller_offer,
        "buyer_ask": offer.buyer_ask,
        "offer": asdict(offer),
        "retail_comparison": asdict(retail),
        "pains_identified": [p.name for p in pains],
        "market_stats_source": getattr(stats, "source_quarter", None) if stats else None,
        "fee_breakdown": {
            "assignment_fee": assignment_fee,
            "effective_pct": effective_pct,
            "reasoning": fee_reasoning,
            "motivation_tier_used": motivation_tier,
        },
    }


def main():
    """CLI for testing without a Django lead -- raw numbers in, full pack out."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--arv", type=float, required=True)
    ap.add_argument("--repair", type=float, required=True)
    ap.add_argument("--fee", type=float, default=DEFAULT_ASSIGNMENT_FEE)
    ap.add_argument("--market", default="")
    ap.add_argument("--address", default="the property")
    ap.add_argument("--first-name", default="there")
    ap.add_argument("--carry-monthly", type=float, default=DEFAULT_CARRY_PER_MONTH)
    args = ap.parse_args()

    offer = compute_offer(arv=args.arv, repair=args.repair,
                           assignment_fee=args.fee, market_label=args.market)
    retail = compute_retail_comparison(
        arv=args.arv, repair=args.repair,
        cash_offer=offer.seller_offer,
        carry_per_month=args.carry_monthly,
    )

    print(json.dumps({
        "offer": asdict(offer),
        "retail_comparison": asdict(retail),
        "the_number": offer.seller_offer,
        "buyer_ask": offer.buyer_ask,
        "delta_msg": (
            f"Retail nets {_money(retail.retail_net_proceeds)} in {retail.months_to_close}mo IF it sells. "
            f"Cash today {_money(offer.seller_offer)}. Delta: {_money(retail.delta_dollars)}."
        ),
    }, indent=2, default=str))


if __name__ == "__main__":
    main()
