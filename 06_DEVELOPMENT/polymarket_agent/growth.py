"""Compound-growth ladder -- operator's bankroll-tiered sizing + harvest plan.

Operator directive (2026-05-29): scale max bet with the bankroll, compound
everything until $30k, then passively pay $100/day and let the rest keep
compounding. We are at $250 building to $1k; the % cap (5%) is the binding
constraint early, the absolute tier ceilings bind only much later.

Final per-bet size = MIN of three caps (most conservative wins):
  1. quarter-Kelly (risk_manager)         -- the edge-based size
  2. max_bet_pct x bankroll (5%)          -- the % risk cap
  3. tier absolute ceiling (this ladder)  -- the operator's $ ceiling per band

This module owns #3 + the harvest schedule.
"""
from decimal import Decimal

# Bankroll band -> absolute max bet ceiling (USD). Operator's ladder.
DEFAULT_TIERS = [
    (Decimal("0"),     Decimal("1000")),   # < $10k bankroll: ceiling $1,000
    (Decimal("10000"), Decimal("2000")),   # $10k-20k:        ceiling $2,000
    (Decimal("20000"), Decimal("4000")),   # $20k-30k:        ceiling $4,000
    (Decimal("30000"), Decimal("5000")),   # >= $30k:         ceiling $5,000
]
COMPOUND_UNTIL = Decimal("30000")  # below this: 100% compounds (no withdrawal)
PAYOUT_PER_DAY = Decimal("100")    # at/above compound_until: passive daily pay


def _tiers_from_cfg(cfg: dict):
    g = (cfg or {}).get("growth_ladder") or {}
    raw = g.get("tiers")
    if not raw:
        return DEFAULT_TIERS
    return [(Decimal(str(t["min_bankroll"])), Decimal(str(t["max_bet_usd"]))) for t in raw]


def max_bet_for(bankroll, cfg: dict = None) -> Decimal:
    """Absolute max-bet ceiling (USD) for the current bankroll band."""
    bk = Decimal(str(bankroll))
    ceiling = DEFAULT_TIERS[0][1]
    for min_bk, cap in _tiers_from_cfg(cfg or {}):
        if bk >= min_bk:
            ceiling = cap
    return ceiling


def compound_until(cfg: dict = None) -> Decimal:
    return Decimal(str(((cfg or {}).get("growth_ladder") or {}).get("compound_until_usd", COMPOUND_UNTIL)))


def payout_per_day(cfg: dict = None) -> Decimal:
    return Decimal(str(((cfg or {}).get("growth_ladder") or {}).get("payout_per_day_usd", PAYOUT_PER_DAY)))


def harvest_plan(bankroll, cfg: dict = None) -> dict:
    """What to do with profit at the current bankroll.

    < compound_until : compound everything, withdraw $0 (pure growth phase).
    >= compound_until: keep compound_until working, pay up to payout_per_day/day,
                       and sweep any excess above the working line to the operator.
    """
    bk = Decimal(str(bankroll))
    until = compound_until(cfg)
    if bk < until:
        return {"phase": "compound", "withdraw_today": Decimal("0"),
                "working_capital": bk, "reason": f"compounding until ${until}"}
    pay = payout_per_day(cfg)
    excess = bk - until
    # Pay the daily amount; if there's extra growth above the working line, it is
    # available to pocket too (operator's "rest gets pocketed"). Keep `until` working.
    withdraw = min(excess, pay) if excess > 0 else Decimal("0")
    return {"phase": "harvest", "withdraw_today": withdraw,
            "working_capital": until,
            "reason": f"keep ${until} working, pay ${pay}/day, compound the rest"}
