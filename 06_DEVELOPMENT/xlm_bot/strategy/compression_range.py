"""Compression Range Strategy -- Scalp the range during low-vol periods.

Buy near support, sell near resistance. Tiny targets, fast exits.
Target: $5-10/day in compression (vs $0 currently).

This module provides detection + signal generation. The main bot loop
calls these functions when vol_state == COMPRESSION to find micro-trades
within the defined range.
"""
from __future__ import annotations

from typing import Any


def detect_compression_range(
    candles_15m: list[dict],
    atr: float,
    *,
    lookback: int = 20,
    min_width_atr: float = 0.20,
    max_width_atr: float = 1.0,
) -> dict | None:
    """Detect if we're in a tradeable compression range.

    Args:
        candles_15m: List of candle dicts with 'high' and 'low' keys.
        atr: Current ATR value for normalization.
        lookback: Number of candles to scan for range.
        min_width_atr: Minimum range width as multiple of ATR.
        max_width_atr: Maximum range width as multiple of ATR.

    Returns:
        Range dict if tradeable range detected, None otherwise.
    """
    if not candles_15m or len(candles_15m) < lookback:
        return None
    if atr <= 0:
        return None

    recent = candles_15m[-lookback:]
    highs = [float(c["high"]) for c in recent]
    lows = [float(c["low"]) for c in recent]

    range_high = max(highs)
    range_low = min(lows)
    range_width = range_high - range_low

    # Range must be meaningful but not too wide
    if range_width < atr * min_width_atr or range_width > atr * max_width_atr:
        return None

    return {
        "range_high": round(range_high, 8),
        "range_low": round(range_low, 8),
        "range_width": round(range_width, 8),
        "range_mid": round((range_high + range_low) / 2, 8),
        "atr_ratio": round(range_width / atr, 3),
    }


def compression_range_signal(
    price: float,
    range_data: dict | None,
    atr: float,
    *,
    buy_zone_pct: float = 0.25,
    sell_zone_pct: float = 0.25,
    sl_atr_mult: float = 0.10,
) -> dict | None:
    """Generate buy/sell signal within compression range.

    Args:
        price: Current price.
        range_data: Output from detect_compression_range().
        atr: Current ATR for stop placement.
        buy_zone_pct: Bottom fraction of range for buy signals (0.25 = bottom 25%).
        sell_zone_pct: Top fraction of range for sell signals (0.25 = top 25%).
        sl_atr_mult: Stop loss distance as multiple of ATR beyond range edge.

    Returns:
        Signal dict with entry/tp/sl or None if no edge.
    """
    if not range_data or atr <= 0:
        return None

    rw = range_data["range_width"]
    if rw <= 0:
        return None

    proximity_to_low = (price - range_data["range_low"]) / rw
    proximity_to_high = (range_data["range_high"] - price) / rw

    # Buy zone: bottom portion of range
    if proximity_to_low < buy_zone_pct:
        tp = range_data["range_mid"]
        sl = range_data["range_low"] - atr * sl_atr_mult
        reward = tp - price
        risk = price - sl
        rr = (reward / risk) if risk > 0 else 0
        if rr < 1.5:
            return None  # Not enough R:R even for a scalp
        return {
            "signal": "LONG",
            "entry": round(price, 8),
            "tp": round(tp, 8),
            "sl": round(sl, 8),
            "rr_ratio": round(rr, 2),
            "reason": f"Compression range long: price at {proximity_to_low:.0%} of range (near support)",
            "strategy": "compression_range",
        }

    # Sell zone: top portion of range
    if proximity_to_high < sell_zone_pct:
        tp = range_data["range_mid"]
        sl = range_data["range_high"] + atr * sl_atr_mult
        reward = price - tp
        risk = sl - price
        rr = (reward / risk) if risk > 0 else 0
        if rr < 1.5:
            return None
        return {
            "signal": "SHORT",
            "entry": round(price, 8),
            "tp": round(tp, 8),
            "sl": round(sl, 8),
            "rr_ratio": round(rr, 2),
            "reason": f"Compression range short: price at {proximity_to_high:.0%} of range (near resistance)",
            "strategy": "compression_range",
        }

    return None  # In the middle of range -- no edge
