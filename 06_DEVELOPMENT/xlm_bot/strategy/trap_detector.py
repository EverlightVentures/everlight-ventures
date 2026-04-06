"""Trap Detector -- identifies liquidity traps and squeeze setups.

Wraps the existing liquidation_clusters, orderbook_context, and
contract_context modules into a single analysis that tells the bot:

1. Are we near a liquidation cluster? (trap zone)
2. Which side would get squeezed? (shorts or longs)
3. Should we AVOID entering here? (we'd get trapped)
4. Should we WAIT for the trap to trigger then ride the squeeze?
5. What's the squeeze target and profit potential?

This feeds into the unified scorer as a modifier:
  - Positive: setup aligns with the squeeze direction (ride the whales)
  - Negative: setup walks into a trap (we'd be the victim)
  - Zero: no significant liquidation zones nearby
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd


_CS = 5000.0


@dataclass
class TrapAnalysis:
    # Is there a trap zone nearby?
    trap_detected: bool = False
    trap_side: str = ""          # "longs_trapped" or "shorts_trapped"
    trap_price: float = 0.0      # where the trap would trigger
    trap_distance_usd: float = 0.0  # how far from current price

    # Squeeze potential
    squeeze_direction: str = ""  # "long" (short squeeze) or "short" (long squeeze)
    squeeze_target: float = 0.0  # where price would go after the squeeze
    squeeze_profit_usd: float = 0.0  # profit potential from riding the squeeze

    # Should we enter or wait?
    action: str = "neutral"      # "avoid" / "wait_for_trigger" / "ride_squeeze" / "neutral"

    # Score modifier for unified scorer
    score_modifier: int = 0
    reason: str = ""

    # Raw data for dashboard
    clusters: list[dict] = field(default_factory=list)
    orderbook_imbalance: float = 0.0  # positive = more bids, negative = more asks
    funding_bias: str = ""

    def to_dict(self) -> dict:
        return {
            "trap_detected": self.trap_detected,
            "trap_side": self.trap_side,
            "trap_price": self.trap_price,
            "trap_distance_usd": self.trap_distance_usd,
            "squeeze_direction": self.squeeze_direction,
            "squeeze_target": self.squeeze_target,
            "squeeze_profit_usd": self.squeeze_profit_usd,
            "action": self.action,
            "score_modifier": self.score_modifier,
            "reason": self.reason,
            "clusters": self.clusters[:5],
            "orderbook_imbalance": self.orderbook_imbalance,
            "funding_bias": self.funding_bias,
        }


def analyze_traps(
    *,
    price: float,
    direction: str,
    df_15m: pd.DataFrame,
    liquidation_ctx: dict | None = None,
    orderbook_ctx: dict | None = None,
    contract_ctx: dict | None = None,
    atr_value: float = 0,
) -> TrapAnalysis:
    """Analyze liquidation zones and order book for trap/squeeze setups.

    Uses whatever data is available -- gracefully handles missing feeds.
    """
    result = TrapAnalysis()

    if price <= 0 or not direction:
        return result

    # Extract data from existing contexts
    clusters = []
    if liquidation_ctx and isinstance(liquidation_ctx, dict):
        clusters = liquidation_ctx.get("clusters") or []
        result.funding_bias = str(liquidation_ctx.get("bias") or "")

    if orderbook_ctx and isinstance(orderbook_ctx, dict):
        result.orderbook_imbalance = float(orderbook_ctx.get("imbalance") or 0)

    if contract_ctx and isinstance(contract_ctx, dict):
        if not result.funding_bias:
            result.funding_bias = str(contract_ctx.get("funding_bias") or "")

    # Estimate liquidation zones from recent price action (works without feed data)
    # Leveraged longs have stops below recent lows, shorts above recent highs
    if df_15m is not None and len(df_15m) >= 20:
        recent = df_15m.tail(20)
        recent_high = float(recent["high"].max())
        recent_low = float(recent["low"].min())

        # Shorts have stops above recent highs (1-2% above)
        short_stop_zone = recent_high * 1.005
        # Longs have stops below recent lows (1-2% below)
        long_stop_zone = recent_low * 0.995

        # Build estimated clusters
        if not clusters:
            clusters = [
                {"price": round(short_stop_zone, 6), "side": "short_stops", "strength": 50,
                 "note": "estimated short liquidation zone above recent highs"},
                {"price": round(long_stop_zone, 6), "side": "long_stops", "strength": 50,
                 "note": "estimated long liquidation zone below recent lows"},
            ]

        result.clusters = clusters

        # Find nearest cluster to current price
        dist_to_short_stops = (short_stop_zone - price) * _CS
        dist_to_long_stops = (price - long_stop_zone) * _CS

        # Trap detection: are we walking into a stop zone?
        trap_threshold_usd = 3.0  # within $3 of a liquidation zone = danger

        if direction == "long" and dist_to_short_stops < trap_threshold_usd and dist_to_short_stops > 0:
            # We're going long near where short stops cluster
            # This is actually GOOD -- a short squeeze could accelerate our long
            result.trap_detected = True
            result.trap_side = "shorts_trapped"
            result.trap_price = short_stop_zone
            result.trap_distance_usd = dist_to_short_stops
            result.squeeze_direction = "long"
            result.squeeze_target = short_stop_zone + atr_value * 2 if atr_value > 0 else short_stop_zone * 1.005
            result.squeeze_profit_usd = round((result.squeeze_target - price) * _CS, 2)
            result.action = "ride_squeeze"
            result.score_modifier = 8
            result.reason = "short squeeze zone $%.2f away -- longs benefit from stop cascade" % dist_to_short_stops

        elif direction == "short" and dist_to_short_stops < trap_threshold_usd and dist_to_short_stops > 0:
            # We're going SHORT near where short stops are -- we'd get squeezed too
            result.trap_detected = True
            result.trap_side = "shorts_trapped"
            result.trap_price = short_stop_zone
            result.trap_distance_usd = dist_to_short_stops
            result.action = "avoid"
            result.score_modifier = -10
            result.reason = "SHORT TRAP: short stops cluster $%.2f above. Squeeze would kill our short." % dist_to_short_stops

        elif direction == "short" and dist_to_long_stops < trap_threshold_usd and dist_to_long_stops > 0:
            # We're going short near where long stops cluster
            # Good -- a long squeeze would accelerate our short
            result.trap_detected = True
            result.trap_side = "longs_trapped"
            result.trap_price = long_stop_zone
            result.trap_distance_usd = dist_to_long_stops
            result.squeeze_direction = "short"
            result.squeeze_target = long_stop_zone - atr_value * 2 if atr_value > 0 else long_stop_zone * 0.995
            result.squeeze_profit_usd = round((price - result.squeeze_target) * _CS, 2)
            result.action = "ride_squeeze"
            result.score_modifier = 8
            result.reason = "long squeeze zone $%.2f away -- shorts benefit from stop cascade" % dist_to_long_stops

        elif direction == "long" and dist_to_long_stops < trap_threshold_usd and dist_to_long_stops > 0:
            # We're going LONG near where long stops are -- we'd get squeezed
            result.trap_detected = True
            result.trap_side = "longs_trapped"
            result.trap_price = long_stop_zone
            result.trap_distance_usd = dist_to_long_stops
            result.action = "avoid"
            result.score_modifier = -10
            result.reason = "LONG TRAP: long stops cluster $%.2f below. Squeeze would kill our long." % dist_to_long_stops

        # Orderbook imbalance signal
        if result.orderbook_imbalance > 0.3 and direction == "long":
            result.score_modifier += 3
            result.reason += " + orderbook favors longs (%.0f%% bid heavy)" % (result.orderbook_imbalance * 100)
        elif result.orderbook_imbalance < -0.3 and direction == "short":
            result.score_modifier += 3
            result.reason += " + orderbook favors shorts (%.0f%% ask heavy)" % (abs(result.orderbook_imbalance) * 100)
        elif result.orderbook_imbalance > 0.3 and direction == "short":
            result.score_modifier -= 3
            result.reason += " + orderbook against shorts (bid heavy)"
        elif result.orderbook_imbalance < -0.3 and direction == "long":
            result.score_modifier -= 3
            result.reason += " + orderbook against longs (ask heavy)"

    return result
