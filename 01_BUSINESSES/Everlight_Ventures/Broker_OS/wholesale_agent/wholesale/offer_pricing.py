"""Offer pricing engine.

One function: `max_offer(strategy, ...)`. Dispatch by strategy name to the
appropriate formula. Every lane playbook references a strategy here.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

STRATEGIES = (
    "teardown_80pct",
    "balance_assignment",
    "seventy_rule",
    "subject_to",
)

# Local land-premium multipliers for the teardown_80pct strategy.
# Source: observed new-home-builder markups by market in starter list.
# Tune quarterly as we capture more closed comps.
LAND_PREMIUM_MULTIPLIERS = {
    "PHX": 1.8,  # Phoenix
    "DAL": 1.4,  # Dallas
    "ATL": 1.5,  # Atlanta
    "NASH": 1.6,  # Nashville
    "DEFAULT": 1.4,
}


@dataclass
class Offer:
    strategy: str
    offer_to_seller: float
    assignment_fee: float
    buyer_pays: float
    margin_ok: bool
    notes: str = ""


def max_offer(
    strategy: str,
    *,
    assessed: Optional[float] = None,
    arv: Optional[float] = None,
    rehab: Optional[float] = None,
    mortgage_balance: Optional[float] = None,
    market_code: str = "DEFAULT",
    target_fee: float = 10_000,
) -> Offer:
    """Compute the max offer for a given strategy.

    Callers pass only the inputs their strategy needs. Unknown strategies raise
    ValueError rather than silently defaulting, so routing bugs surface early.
    """
    if strategy == "teardown_80pct":
        if assessed is None:
            raise ValueError("teardown_80pct requires assessed")
        offer_to_seller = round(0.80 * assessed, 2)
        fee = max(target_fee, 30_000)  # teardowns carry higher fees
        buyer_pays = offer_to_seller + fee
        premium = LAND_PREMIUM_MULTIPLIERS.get(market_code.upper(), LAND_PREMIUM_MULTIPLIERS["DEFAULT"])
        implied_land_value = assessed * premium
        margin_ok = buyer_pays <= 0.85 * implied_land_value
        return Offer(
            strategy=strategy,
            offer_to_seller=offer_to_seller,
            assignment_fee=fee,
            buyer_pays=buyer_pays,
            margin_ok=margin_ok,
            notes=f"land_premium={premium}x, implied_land_value=${implied_land_value:,.0f}",
        )

    if strategy == "balance_assignment":
        if mortgage_balance is None or arv is None:
            raise ValueError("balance_assignment requires mortgage_balance and arv")
        closing_cushion = 2_000
        offer_to_seller = mortgage_balance + closing_cushion
        fee = target_fee
        buyer_pays = offer_to_seller + fee
        margin_ok = buyer_pays <= 0.75 * arv
        return Offer(
            strategy=strategy,
            offer_to_seller=offer_to_seller,
            assignment_fee=fee,
            buyer_pays=buyer_pays,
            margin_ok=margin_ok,
            notes=f"buyer_pays_pct_of_arv={buyer_pays/arv:.1%}" if arv else "",
        )

    if strategy == "seventy_rule":
        if arv is None or rehab is None:
            raise ValueError("seventy_rule requires arv and rehab")
        buyer_pays = 0.70 * arv - rehab
        fee = target_fee
        offer_to_seller = buyer_pays - fee
        margin_ok = offer_to_seller > 0
        return Offer(
            strategy=strategy,
            offer_to_seller=max(0.0, offer_to_seller),
            assignment_fee=fee,
            buyer_pays=buyer_pays,
            margin_ok=margin_ok,
        )

    if strategy == "subject_to":
        if mortgage_balance is None:
            raise ValueError("subject_to requires mortgage_balance")
        offer_to_seller = mortgage_balance
        fee = target_fee
        buyer_pays = offer_to_seller + fee
        margin_ok = True
        return Offer(
            strategy=strategy,
            offer_to_seller=offer_to_seller,
            assignment_fee=fee,
            buyer_pays=buyer_pays,
            margin_ok=margin_ok,
            notes="existing mortgage stays in place; buyer takes over payments",
        )

    raise ValueError(f"unknown strategy: {strategy!r}. Known: {STRATEGIES}")
