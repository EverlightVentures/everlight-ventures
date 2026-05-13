"""
pitch_tailor.py -- digest OSINT signals into personalized pitch hooks.

Takes a profile (from profile_synthesizer) or a raw seller_intel dict, extracts
the strongest 1-2 PUBLIC-RECORD signals about the recipient, and returns a
tailored opener line + value-prop sentence that slots INSIDE the existing pitch
template (without replacing the brand voice).

Examples of digested signals:
  * "7-year hold + multi-deed history" -> investor pattern -> "investor-to-investor"
  * "out-of-state mailing in CA" -> absentee burden -> "managing from a distance"
  * "21-year ownership + estate executor on file" -> estate burden -> "executor-friendly close"
  * "founded LLC at this address" -> business owner -> "free the equity for the next move"
  * "MMA gym membership inferred from social" -> personal interest -> "could fund a year of training"

The output is a dict the pitch builder interpolates:
  { "hook_line": "...", "value_line": "...", "trail": [...] }
"""
from __future__ import annotations

from typing import Any


def _money(n: float) -> str:
    return f"${n:,.0f}"


def tailor_for_seller(intel: dict, lead: dict, offer: dict | None = None) -> dict:
    """
    intel: parcel-level intel dict (e.g. seller_intel/<parcel>/intel.json content)
    lead:  the lead row (address/owner/state/etc.)
    offer: optional pre-computed offer dict (purchase_price_usd, etc.)
    Returns: dict with hook_line + value_line + trail (signals used).
    """
    signals = (intel.get("signals_detected") or {}) if isinstance(intel.get("signals_detected"), dict) else {}
    hooks_avail = intel.get("pitch_hooks") or []
    sales = intel.get("sales_history") or []
    owner_state = (intel.get("owner_mailing_state") or "").upper()
    prop_state = (lead.get("state") or "").upper()
    appraisal = intel.get("total_appraisal_usd") or 0
    yrs_owned = signals.get("ownership_years") or 0
    tax_delinq = signals.get("tax_delinquent_years") or ""
    multi_sales = bool(signals.get("multiple_sales_in_history"))
    absentee = bool(intel.get("absentee_owner"))
    in_state_absentee = (owner_state == prop_state) and (
        intel.get("owner_mailing_zip", "")[:3] != lead.get("zip_code", "")[:3]
    )

    trail: list[str] = []
    hook_line = ""
    value_line = ""

    # SIGNAL A: investor pattern (multi-deed + zero-dollar QCs = active wholesaler/investor)
    qc_count = sum(1 for s in sales if s.get("type_code") == "QC" and (s.get("price_usd") or 0) == 0)
    if multi_sales or qc_count >= 2:
        trail.append(f"investor pattern: {qc_count} zero-dollar QCs in deed history; total {len(sales)} sales")
        hook_line = (
            "Investor to investor here, no fluff. Pulled the deed history on the parcel and "
            f"the pattern reads like portfolio activity ({qc_count} zero-dollar QC entries"
            f"{', plus ' + str(len(sales) - qc_count) + ' priced sales' if len(sales) > qc_count else ''})."
        )
        if offer and offer.get("purchase_price_usd"):
            value_line = (
                f"Clean cash close on this one frees roughly {_money(offer['purchase_price_usd'])} "
                "for the next pickup, and you stop paying the back-tax meter on a parcel that's "
                "been sitting."
            )
        else:
            value_line = (
                "Clean cash close frees the capital for the next pickup, and you stop "
                "paying the back-tax meter on a parcel that's been sitting."
            )
        return {"hook_line": hook_line, "value_line": value_line, "trail": trail}

    # SIGNAL B: out-of-state absentee
    if absentee and owner_state and owner_state != prop_state:
        city = (intel.get("owner_mailing_city") or "").title()
        trail.append(f"absentee owner: mailing {city}, {owner_state}; property in {prop_state}")
        hook_line = (
            f"Managing a {prop_state} parcel from {city} {owner_state} is its own kind of work, "
            "tax notices, code letters, weed cuttings, all by mail. We handle the close-out "
            "by mail and wire. You don't fly in."
        )
        if offer:
            value_line = (
                f"Cash {_money(offer['purchase_price_usd'])} at closing, back tax handled at the "
                "title firm, and the file closes itself."
            )
        else:
            value_line = (
                "Cash at closing, back tax handled at the title firm, no out-of-pocket on your end."
            )
        return {"hook_line": hook_line, "value_line": value_line, "trail": trail}

    # SIGNAL C: long ownership (20+ years)
    if isinstance(yrs_owned, (int, float)) and yrs_owned >= 20:
        trail.append(f"long-term ownership: {yrs_owned} years")
        hook_line = (
            f"You've held this property for {int(yrs_owned)} years. Memphis values have shifted, "
            "carrying costs haven't. This is a clean way to free the equity without listing or "
            "showings."
        )
        value_line = (
            "Cash close, your timeline, paperwork by email. We do this every week with long-hold "
            "owners who are ready to move on."
        )
        return {"hook_line": hook_line, "value_line": value_line, "trail": trail}

    # SIGNAL D: heavy tax delinquency burden
    if tax_delinq and "+" in str(tax_delinq):
        trail.append(f"tax delinquency: {tax_delinq} years")
        hook_line = (
            f"The parcel's been on the back-tax list for {tax_delinq} years now. "
            "Most of the calls we get from owners in that situation start with the same "
            "sentence: \"how do I make this stop without writing a check?\""
        )
        value_line = (
            "We pay every dollar of back tax + penalty at the title firm, out of OUR side, "
            "not yours. You walk clean."
        )
        return {"hook_line": hook_line, "value_line": value_line, "trail": trail}

    # SIGNAL E: fallback (use one of the pre-built pitch hooks)
    if hooks_avail:
        h = hooks_avail[0]
        if isinstance(h, dict):
            trail.append(f"fallback hook: {h.get('id', 'unnamed')}")
            hook_line = h.get("opener", "Quick note about the property.")
            value_line = h.get("value_prop", "Cash close, your timeline, no surprises.")
            return {"hook_line": hook_line, "value_line": value_line, "trail": trail}

    # SIGNAL F: nothing personalized -- generic but honest
    trail.append("no personalized signals available; generic fallback")
    return {
        "hook_line": "Quick note about the property before reaching out by phone.",
        "value_line": "Cash close, your timeline, paperwork by email. No agents, no fees on your side.",
        "trail": trail,
    }


def tailor_for_buyer(buyer_profile: dict, deal: dict) -> dict:
    """Stub for buyer-side (Chris) tailoring. Future expansion."""
    return {
        "hook_line": (
            f"{deal.get('city', 'Memphis')} parcel matching your buy-box, ready for assignment."
        ),
        "value_line": (
            f"ARV-ready entry at {_money(deal.get('chris_pay_usd', 0))}, your standard 14-day flow."
        ),
        "trail": ["buy-box match"],
    }
