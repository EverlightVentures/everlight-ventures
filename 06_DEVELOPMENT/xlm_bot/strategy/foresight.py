"""Foresight Engine -- the bot's anticipation system.

Every cycle, computes:
1. What scenarios are most likely in the next 1-4 hours
2. Where are the key levels to watch
3. What trades should fire at each level
4. How much profit is available in each scenario

This feeds into the unified scorer as a confidence boost when the
current setup matches an anticipated scenario.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd
from indicators.ema import ema
from indicators.rsi import rsi
from indicators.atr import atr

_CS = 5000.0


@dataclass
class ForesightResult:
    # Current read
    bias: str = "neutral"  # bullish / bearish / neutral
    rsi_state: str = "neutral"  # oversold / overbought / neutral
    volatility: str = "normal"  # squeezing / expanding / normal

    # Anticipated scenarios (ordered by probability)
    scenarios: list[dict[str, Any]] = field(default_factory=list)

    # Key price levels the bot should watch
    watch_levels: list[dict[str, Any]] = field(default_factory=list)

    # Score modifier: how much should the unified scorer trust the current setup?
    # Positive if setup matches a high-probability scenario
    confidence_boost: int = 0
    confidence_reason: str = ""

    # Projected daily profit range
    projected_trades: int = 0
    projected_profit_conservative: float = 0.0
    projected_profit_best: float = 0.0

    def to_dict(self) -> dict:
        return {
            "bias": self.bias,
            "rsi_state": self.rsi_state,
            "volatility": self.volatility,
            "scenarios": self.scenarios,
            "watch_levels": self.watch_levels,
            "confidence_boost": self.confidence_boost,
            "confidence_reason": self.confidence_reason,
            "projected_trades": self.projected_trades,
            "projected_profit_conservative": self.projected_profit_conservative,
            "projected_profit_best": self.projected_profit_best,
        }


def compute_foresight(
    *,
    df_15m: pd.DataFrame,
    df_1h: pd.DataFrame,
    df_4h: pd.DataFrame | None = None,
    price: float,
    direction: str = "",
    entry_type: str = "",
) -> ForesightResult:
    """Compute market foresight and return anticipated scenarios."""
    result = ForesightResult()

    if df_1h is None or df_1h.empty or len(df_1h) < 30:
        return result

    # Current indicators
    e21_1h = float(ema(df_1h["close"], 21).iloc[-1])
    slope_1h = float(ema(df_1h["close"], 21).diff().tail(5).mean())
    rsi_1h = float(rsi(df_1h["close"], 14).iloc[-1])
    atr_1h = float(atr(df_1h, 14).iloc[-1])

    rsi_4h = 50.0
    if df_4h is not None and not df_4h.empty and len(df_4h) >= 14:
        rsi_4h = float(rsi(df_4h["close"], 14).iloc[-1])

    # Bias
    if slope_1h < 0 and price < e21_1h:
        result.bias = "bearish"
    elif slope_1h > 0 and price > e21_1h:
        result.bias = "bullish"

    # RSI state
    if rsi_4h < 20 or rsi_1h < 25:
        result.rsi_state = "oversold"
    elif rsi_4h > 80 or rsi_1h > 75:
        result.rsi_state = "overbought"

    # Key levels
    high_48h = float(df_1h["high"].tail(48).max())
    low_48h = float(df_1h["low"].tail(48).min())
    high_24h = float(df_1h["high"].tail(24).max())
    low_24h = float(df_1h["low"].tail(24).min())

    result.watch_levels = [
        {"name": "EMA21 1H", "price": round(e21_1h, 6), "type": "dynamic", "action": "short_rejection" if result.bias == "bearish" else "long_support"},
        {"name": "48h high", "price": round(high_48h, 6), "type": "resistance", "action": "short_at_level"},
        {"name": "48h low", "price": round(low_48h, 6), "type": "support", "action": "long_at_level"},
        {"name": "24h high", "price": round(high_24h, 6), "type": "resistance", "action": "short_at_level"},
        {"name": "24h low", "price": round(low_24h, 6), "type": "support", "action": "long_at_level"},
    ]

    # Scenarios
    scenarios = []
    projected_trades = 0
    projected_profit = 0.0

    # Scenario: Oversold bounce
    if result.rsi_state == "oversold":
        bounce_profit = (e21_1h - price) * _CS
        if bounce_profit > 2:
            scenarios.append({
                "name": "oversold_bounce",
                "probability": "high",
                "direction": "long",
                "entry_zone": round(price, 6),
                "target": round(e21_1h, 6),
                "profit_usd": round(bounce_profit, 2),
                "trigger": "RSI < 20 on 4H, bounce to EMA21",
            })
            projected_trades += 2
            projected_profit += bounce_profit * 0.3 * 2

    # Scenario: Overbought rejection
    if result.rsi_state == "overbought":
        reject_profit = (price - e21_1h) * _CS
        if reject_profit > 2:
            scenarios.append({
                "name": "overbought_rejection",
                "probability": "high",
                "direction": "short",
                "entry_zone": round(price, 6),
                "target": round(e21_1h, 6),
                "profit_usd": round(reject_profit, 2),
                "trigger": "RSI > 80 on 4H, reject to EMA21",
            })
            projected_trades += 2
            projected_profit += reject_profit * 0.3 * 2

    # Scenario: Trend continuation (short rallies in downtrend, buy dips in uptrend)
    if result.bias == "bearish":
        rally_profit = (e21_1h - low_48h) * _CS * 0.5
        scenarios.append({
            "name": "bearish_continuation",
            "probability": "medium",
            "direction": "short",
            "entry_zone": round(e21_1h, 6),
            "target": round(low_48h, 6),
            "profit_usd": round((price - low_48h) * _CS, 2),
            "trigger": "Rally to EMA21 or fib 0.382, then reject",
        })
        projected_trades += 2
        projected_profit += 5.0 * 2
    elif result.bias == "bullish":
        dip_profit = (high_48h - e21_1h) * _CS * 0.5
        scenarios.append({
            "name": "bullish_continuation",
            "probability": "medium",
            "direction": "long",
            "entry_zone": round(e21_1h, 6),
            "target": round(high_48h, 6),
            "profit_usd": round((high_48h - price) * _CS, 2),
            "trigger": "Dip to EMA21 or fib 0.382, then bounce",
        })
        projected_trades += 2
        projected_profit += 5.0 * 2

    # Scenario: Range scalp (if range is wide enough)
    range_usd = (high_24h - low_24h) * _CS
    if range_usd > 8:
        scenarios.append({
            "name": "range_scalp",
            "probability": "medium",
            "direction": "both",
            "entry_zone": "support/resistance",
            "target": "opposite side",
            "profit_usd": round(range_usd / 2, 2),
            "trigger": "Long at 24h low, short at 24h high",
        })
        projected_trades += 3
        projected_profit += (range_usd / 2) * 0.3 * 3

    result.scenarios = scenarios
    result.projected_trades = projected_trades
    result.projected_profit_conservative = round(projected_profit, 2)
    result.projected_profit_best = round(projected_profit * 1.5, 2)

    # Confidence boost: does the current trade match an anticipated scenario?
    if direction and entry_type:
        for sc in scenarios:
            sc_dir = sc.get("direction", "")
            if sc_dir == direction or sc_dir == "both":
                if sc.get("probability") == "high":
                    result.confidence_boost = 8
                    result.confidence_reason = "matches high-prob scenario: %s ($%.2f target)" % (sc["name"], sc["profit_usd"])
                elif sc.get("probability") == "medium":
                    result.confidence_boost = 4
                    result.confidence_reason = "matches scenario: %s" % sc["name"]
                break

    return result
