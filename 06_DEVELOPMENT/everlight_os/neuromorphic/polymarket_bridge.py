"""
Polymarket Bridge -- connects prediction agent to brain policy.

Instead of the Polymarket agent running empty cycles (0 bets placed),
this bridge feeds brain policy confidence scores into its decision logic.

The Polymarket container runs paper trading mode with $100 virtual bankroll.
"""
from __future__ import annotations

import json
import logging
import os
import urllib.request
from typing import Any

log = logging.getLogger(__name__)

POLYMARKET_URL = os.environ.get("POLYMARKET_URL", "http://localhost:9100")


def get_market_opportunities(limit: int = 5) -> list[dict]:
    """Get current prediction market opportunities."""
    try:
        req = urllib.request.Request(f"{POLYMARKET_URL}/api/markets?limit={limit}")
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception as e:
        log.debug(f"Polymarket markets fetch failed: {e}")
        return []


def should_bet(market: dict, brain_policy: dict) -> dict:
    """Use brain policy to decide if a bet should be placed.

    Factors:
    - decisive_score: high = more willing to bet
    - logical_score: high = better analysis
    - self_healing_score: low after losses = more cautious
    - plasticity_score: high = adapting to new info
    """
    decisive = float(brain_policy.get("decisive_score", 0.5))
    logical = float(brain_policy.get("logical_score", 0.5))
    self_healing = float(brain_policy.get("self_healing_score", 0.5))
    plasticity = float(brain_policy.get("plasticity_score", 0.5))

    # Market confidence (from Polymarket agent's own analysis)
    market_confidence = float(market.get("confidence", 0))
    edge = float(market.get("edge", 0))

    # Brain-adjusted confidence
    brain_boost = (decisive * 0.3) + (logical * 0.3) + (plasticity * 0.2) + (self_healing * 0.2)
    adjusted_confidence = market_confidence * brain_boost

    # Decision thresholds
    min_confidence = 0.6 if decisive > 0.7 else 0.75
    min_edge = 0.05

    should_place = adjusted_confidence >= min_confidence and edge >= min_edge

    # Position sizing based on confidence
    if should_place:
        base_size = 5.0  # $5 base on $100 bankroll
        size = base_size * min(adjusted_confidence, 1.0)
    else:
        size = 0

    return {
        "should_bet": should_place,
        "original_confidence": market_confidence,
        "brain_adjusted_confidence": round(adjusted_confidence, 3),
        "brain_boost": round(brain_boost, 3),
        "position_size_usd": round(size, 2),
        "reasoning": {
            "decisive": decisive,
            "logical": logical,
            "min_confidence_threshold": min_confidence,
            "edge": edge,
        },
    }


def get_status() -> dict:
    """Check Polymarket agent status."""
    try:
        req = urllib.request.Request(f"{POLYMARKET_URL}/api/status")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return {"available": True, **json.loads(resp.read())}
    except Exception:
        return {"available": False, "url": POLYMARKET_URL}
