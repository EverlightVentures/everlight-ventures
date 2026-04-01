"""Divergence Detection -- RSI price/indicator divergence scanner.

Detects bullish and bearish divergences between price and RSI:
- Bullish: price makes lower low, RSI makes higher low (reversal up)
- Bearish: price makes higher high, RSI makes lower high (reversal down)

Used as confirmation boost (+10 score) for fib_retrace, wick_rejection,
and volume_climax_reversal entries. NOT a standalone entry signal.

Based on trading knowledge: "we got our bullish divergences on market cipher
so we stayed in the trade"
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from indicators.rsi import rsi as compute_rsi


def _find_swing_lows(values: np.ndarray, window: int = 3) -> list[tuple[int, float]]:
    """Find local minima (swing lows) in a series."""
    lows = []
    for i in range(window, len(values) - window):
        if all(values[i] <= values[i - j] for j in range(1, window + 1)) and \
           all(values[i] <= values[i + j] for j in range(1, window + 1)):
            lows.append((i, float(values[i])))
    return lows


def _find_swing_highs(values: np.ndarray, window: int = 3) -> list[tuple[int, float]]:
    """Find local maxima (swing highs) in a series."""
    highs = []
    for i in range(window, len(values) - window):
        if all(values[i] >= values[i - j] for j in range(1, window + 1)) and \
           all(values[i] >= values[i + j] for j in range(1, window + 1)):
            highs.append((i, float(values[i])))
    return highs


def detect_divergence(
    df: pd.DataFrame,
    direction: str = "bullish",
    rsi_period: int = 14,
    lookback: int = 25,
    swing_window: int = 3,
) -> dict:
    """Detect RSI divergence on a DataFrame with OHLCV data.

    Args:
        df: DataFrame with at least 'close', 'low', 'high' columns
        direction: "bullish" (look for bullish divergence) or "bearish"
        rsi_period: RSI calculation period
        lookback: how many bars to look back for swing points
        swing_window: window size for swing detection (smaller = more sensitive)

    Returns:
        detected: bool
        strength: float (0-1, how strong the divergence is)
        type: str ("bullish_divergence" | "bearish_divergence" | "none")
        detail: str (human-readable description)
        price_swing_1: float
        price_swing_2: float
        rsi_swing_1: float
        rsi_swing_2: float
    """
    result = {
        "detected": False,
        "strength": 0.0,
        "type": "none",
        "detail": "",
        "price_swing_1": 0.0,
        "price_swing_2": 0.0,
        "rsi_swing_1": 0.0,
        "rsi_swing_2": 0.0,
    }

    if df is None or len(df) < lookback + rsi_period:
        return result

    window = df.tail(lookback + rsi_period)
    closes = window["close"].values

    rsi_series = compute_rsi(window["close"], rsi_period)
    if rsi_series.empty or len(rsi_series) < lookback:
        return result

    rsi_values = rsi_series.values[-lookback:]
    price_slice = closes[-lookback:]

    if direction == "bullish":
        # Bullish divergence: price lower low + RSI higher low
        lows_price = window["low"].values[-lookback:]
        price_lows = _find_swing_lows(lows_price, swing_window)
        rsi_lows = _find_swing_lows(rsi_values, swing_window)

        if len(price_lows) >= 2 and len(rsi_lows) >= 2:
            # Compare the two most recent swing lows
            p1_idx, p1_val = price_lows[-2]
            p2_idx, p2_val = price_lows[-1]
            r1_idx, r1_val = rsi_lows[-2]
            r2_idx, r2_val = rsi_lows[-1]

            # Price made lower low
            price_lower = p2_val < p1_val
            # RSI made higher low
            rsi_higher = r2_val > r1_val

            if price_lower and rsi_higher:
                # Calculate strength based on divergence magnitude
                price_diff = abs(p2_val - p1_val) / max(p1_val, 1e-9)
                rsi_diff = abs(r2_val - r1_val)
                strength = min(1.0, (price_diff * 100 + rsi_diff / 10) / 2)

                result["detected"] = True
                result["strength"] = round(strength, 3)
                result["type"] = "bullish_divergence"
                result["price_swing_1"] = p1_val
                result["price_swing_2"] = p2_val
                result["rsi_swing_1"] = r1_val
                result["rsi_swing_2"] = r2_val
                result["detail"] = (
                    f"Bullish divergence: price {p1_val:.5f}->{p2_val:.5f} (lower low), "
                    f"RSI {r1_val:.1f}->{r2_val:.1f} (higher low). Strength: {strength:.2f}"
                )

    elif direction == "bearish":
        # Bearish divergence: price higher high + RSI lower high
        highs_price = window["high"].values[-lookback:]
        price_highs = _find_swing_highs(highs_price, swing_window)
        rsi_highs = _find_swing_highs(rsi_values, swing_window)

        if len(price_highs) >= 2 and len(rsi_highs) >= 2:
            p1_idx, p1_val = price_highs[-2]
            p2_idx, p2_val = price_highs[-1]
            r1_idx, r1_val = rsi_highs[-2]
            r2_idx, r2_val = rsi_highs[-1]

            price_higher = p2_val > p1_val
            rsi_lower = r2_val < r1_val

            if price_higher and rsi_lower:
                price_diff = abs(p2_val - p1_val) / max(p1_val, 1e-9)
                rsi_diff = abs(r1_val - r2_val)
                strength = min(1.0, (price_diff * 100 + rsi_diff / 10) / 2)

                result["detected"] = True
                result["strength"] = round(strength, 3)
                result["type"] = "bearish_divergence"
                result["price_swing_1"] = p1_val
                result["price_swing_2"] = p2_val
                result["rsi_swing_1"] = r1_val
                result["rsi_swing_2"] = r2_val
                result["detail"] = (
                    f"Bearish divergence: price {p1_val:.5f}->{p2_val:.5f} (higher high), "
                    f"RSI {r1_val:.1f}->{r2_val:.1f} (lower high). Strength: {strength:.2f}"
                )

    return result
