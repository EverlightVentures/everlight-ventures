"""voice_packs -- regional and persona-aware language for the pitch.

Same data, different language. A pitch to an Atlanta retiree reads
differently than a pitch to a Phoenix flipper. This module provides
ready-to-paste copy fragments selected by:

  - Region (state/metro): TX drawl, ATL professional, FL laid-back, AZ
    direct, CA nuanced, NC neighborly, etc.
  - Register (formal, neighborly, urgent, professional): selected upstream
    by owner_intel based on age cohort + motivation tier.
  - Side (seller vs buyer)

Returns dict of fragment slots -- the pitch_generator interpolates them
into the body. Fragments are short, defensible, and avoid Fair Housing
land mines (no marital, family, religious, or age-protected language).
"""
from __future__ import annotations

from typing import Optional


# ── Regional voice characteristics (operational language only) ──

REGIONAL_VOICE = {
    "TX": {
        "name": "Texas",
        "salutation_neighborly": "Hey",
        "salutation_formal": "Good morning",
        "closer": "Appreciate your time.",
        "operational_phrasing": [
            "We close fast in DFW and Houston when sellers want a clean exit.",
            "Texas-licensed title company on every deal. Earnest money up front.",
        ],
        "regional_anchor": "DFW and Houston metros are seeing investor share around 22% of all sales.",
    },
    "GA": {
        "name": "Georgia",
        "salutation_neighborly": "Hey",
        "salutation_formal": "Good morning",
        "closer": "Thanks for the read.",
        "operational_phrasing": [
            "Closings handled by a Georgia attorney (state requires it). No surprise fees.",
            "Atlanta absentee carry is brutal -- 3-4 months of bleeding adds up fast.",
        ],
        "regional_anchor": "Atlanta is a top-3 metro for investor purchases and a magnet for relocators from the northeast.",
    },
    "FL": {
        "name": "Florida",
        "salutation_neighborly": "Hi",
        "salutation_formal": "Good morning",
        "closer": "Sun's still out, life's still good.",
        "operational_phrasing": [
            "Florida title and we cover the doc stamps. No surprises at close.",
            "Insurance + tax + HOA can run higher than mortgage in FL -- carry costs add up.",
        ],
        "regional_anchor": "Florida insurance and tax shifts have changed the math for a lot of out-of-state owners. Lots of folks rebalancing.",
    },
    "AZ": {
        "name": "Arizona",
        "salutation_neighborly": "Hi",
        "salutation_formal": "Hello",
        "closer": "Straight talk only.",
        "operational_phrasing": [
            "Phoenix metro investor share is high; the deal moves fast.",
            "No license required for wholesale assignment in AZ.",
        ],
        "regional_anchor": "Phoenix continues to attract job-driven in-migration. Tight inventory still.",
    },
    "CA": {
        "name": "California",
        "salutation_neighborly": "Hi",
        "salutation_formal": "Good afternoon",
        "closer": "Be well.",
        "operational_phrasing": [
            "California requires extra disclosures. We handle them. Title at one of the licensed escrow companies we use.",
            "CC 2945 (foreclosure consultant law) limits what we can do in pre-foreclosure -- email outreach only.",
        ],
        "regional_anchor": "California carrying costs are the highest in the country. A clean cash close is real money saved.",
    },
    "NC": {
        "name": "North Carolina",
        "salutation_neighborly": "Hey",
        "salutation_formal": "Good morning",
        "closer": "Take care.",
        "operational_phrasing": [
            "Note: NC HB 797 limits how often we can repeat-assign. We default to a direct purchase or a single assignment.",
            "Charlotte and Raleigh-Durham markets continue to absorb new investor capital.",
        ],
        "regional_anchor": "Charlotte and Raleigh investor purchase share is climbing. Strong rent growth.",
    },
    "TN": {
        "name": "Tennessee",
        "salutation_neighborly": "Hey",
        "salutation_formal": "Good morning",
        "closer": "Appreciate it.",
        "operational_phrasing": [
            "Memphis and Nashville operate differently. Memphis is mostly rentals; Nashville is mostly flips.",
            "We close at a Tennessee title company within 14 days.",
        ],
        "regional_anchor": "Memphis remains the country's most rent-favorable major market for new buy-and-hold investors.",
    },
    "MO": {
        "name": "Missouri",
        "salutation_neighborly": "Hi",
        "salutation_formal": "Good morning",
        "closer": "Thanks for reading.",
        "operational_phrasing": [
            "Kansas City and St. Louis are reliable cash-flow markets. Numbers are tight but real.",
            "We close at a local Missouri title company. No long-distance hassle.",
        ],
        "regional_anchor": "KC and STL are well below national median price -- yields stay strong for buy-and-hold.",
    },
}


# ── Register variants (tone) ────────────────────────────────────

# Each register adjusts the same phrase. Keys: opener, ask, close.
REGISTER_VARIANTS = {
    "formal": {
        "opener": "I hope this finds you well.",
        "ask": "If a clean cash sale is something you would consider, I would welcome a brief conversation at your convenience.",
        "close": "I respect your time and will not press if the answer is no.",
    },
    "neighborly": {
        "opener": "Quick note about your property.",
        "ask": "If selling has crossed your mind, even just out of curiosity, give me a shout.",
        "close": "Either way, hope your week is going well.",
    },
    "urgent": {
        "opener": "I will get straight to the point.",
        "ask": "There is a window here where a cash close still helps. After that the leverage shifts.",
        "close": "If I can help, reach out today. If not, I understand.",
    },
    "professional": {
        "opener": "Reaching out about an asset in our pipeline.",
        "ask": "If a 14-day cash close fits your portfolio strategy, let's talk numbers.",
        "close": "Happy to send the offer in writing once we have specs confirmed.",
    },
}


def voice_pack(state: Optional[str], register: str = "neighborly") -> dict[str, str]:
    """Return a dict of language fragments for the pitch templates.

    Slots: salutation, opener, regional_phrase, regional_anchor,
           operational_phrasing, ask, close, closer
    """
    region = REGIONAL_VOICE.get((state or "").upper(), REGIONAL_VOICE["GA"])
    register_pack = REGISTER_VARIANTS.get(register, REGISTER_VARIANTS["neighborly"])

    sal_key = "salutation_formal" if register == "formal" else "salutation_neighborly"
    op_phrase = (region.get("operational_phrasing") or [""])[0]

    return {
        "region_name": region.get("name", ""),
        "salutation": region.get(sal_key, "Hi"),
        "opener": register_pack["opener"],
        "regional_anchor": region.get("regional_anchor", ""),
        "operational_phrasing": op_phrase,
        "ask": register_pack["ask"],
        "close": register_pack["close"],
        "closer": region.get("closer", "Take care."),
    }


# ── Buyer-profile language packs ────────────────────────────────

BUYER_STRATEGY_PACKS = {
    "brrrr": {
        "headline": "BRRRR-ready spread",
        "lead_metric_label": "BRRRR refi pulled out",
        "secondary_label": "Cap rate post-stabilization",
        "value_prop": "Cash-out refi at 75% LTV pulls most or all of your capital back. Stabilized rental cash-flows from day one.",
    },
    "flip": {
        "headline": "Cosmetic-flip equity capture",
        "lead_metric_label": "Equity after rehab",
        "secondary_label": "Time-to-resale (typical)",
        "value_prop": "List on MLS post-rehab. 90-120 day cycle. Equity captured at retail sale.",
    },
    "hold": {
        "headline": "Buy-and-hold rental",
        "lead_metric_label": "Monthly rent",
        "secondary_label": "Cap rate at your cost",
        "value_prop": "Long-term cash flow. Tenant-ready post-rehab. Steady appreciation in this metro.",
    },
    "land": {
        "headline": "Buildable lot opportunity",
        "lead_metric_label": "Lot size",
        "secondary_label": "Comparable build-out value",
        "value_prop": "Tear-down or new-build buildable. Comparable build-outs in the area trade at strong premiums.",
    },
}


def buyer_strategy_pack(strategy_hint: str = "brrrr") -> dict[str, str]:
    """Return language pack for the buyer's likely strategy."""
    s = (strategy_hint or "brrrr").lower()
    return BUYER_STRATEGY_PACKS.get(s, BUYER_STRATEGY_PACKS["brrrr"])


def _cli() -> int:
    import argparse, json
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", default="GA")
    ap.add_argument("--register", default="neighborly")
    ap.add_argument("--strategy", default="brrrr")
    args = ap.parse_args()
    print(json.dumps({
        "voice": voice_pack(args.state, args.register),
        "buyer_strategy": buyer_strategy_pack(args.strategy),
    }, indent=2))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_cli())
