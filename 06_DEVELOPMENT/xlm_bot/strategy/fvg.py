from __future__ import annotations

from typing import Dict, List, Optional

import pandas as pd


def detect_fvg(df: pd.DataFrame, lookback: int = 20) -> List[Dict]:
    """Find unfilled Fair Value Gaps in recent candles.

    A bullish FVG exists when candle[i+2].low > candle[i].high (gap up).
    A bearish FVG exists when candle[i].low > candle[i+2].high (gap down).

    Returns list of dicts: {type, high, low, age, filled}
    """
    if df.empty or len(df) < 4:
        return []

    fvgs: List[Dict] = []
    n = len(df)
    start = max(0, n - lookback - 2)
    current_price = float(df["close"].iloc[-1])

    for i in range(start, n - 2):
        candle_0_high = float(df["high"].iloc[i])
        candle_0_low = float(df["low"].iloc[i])
        candle_2_high = float(df["high"].iloc[i + 2])
        candle_2_low = float(df["low"].iloc[i + 2])
        age = n - 1 - (i + 1)  # age in bars from the middle candle

        # Bullish FVG: gap between candle[i].high and candle[i+2].low
        gap_bull = candle_2_low - candle_0_high
        if gap_bull > 0:
            fvg_high = candle_2_low
            fvg_low = candle_0_high
            # Check if price has filled the gap (traded into the zone)
            filled = False
            for j in range(i + 3, n):
                if float(df["low"].iloc[j]) <= fvg_high:
                    filled = True
                    break
            fvgs.append({
                "type": "bullish",
                "high": fvg_high,
                "low": fvg_low,
                "age": age,
                "filled": filled,
            })

        # Bearish FVG: gap between candle[i].low and candle[i+2].high
        gap_bear = candle_0_low - candle_2_high
        if gap_bear > 0:
            fvg_high = candle_0_low
            fvg_low = candle_2_high
            filled = False
            for j in range(i + 3, n):
                if float(df["high"].iloc[j]) >= fvg_low:
                    filled = True
                    break
            fvgs.append({
                "type": "bearish",
                "high": fvg_high,
                "low": fvg_low,
                "age": age,
                "filled": filled,
            })

    # Return only unfilled gaps
    return [f for f in fvgs if not f["filled"]]


def nearest_fvg(price: float, fvgs: List[Dict], direction: str) -> Optional[Dict]:
    """Find the nearest unfilled FVG that supports the trade direction.

    For longs: bullish FVG near/below current price (support zone).
    For shorts: bearish FVG near/above current price (resistance zone).
    """
    if not fvgs:
        return None

    candidates = []
    for f in fvgs:
        if direction == "long" and f["type"] == "bullish":
            # Price should be near or at the FVG zone (within 1 ATR-ish)
            dist = abs(price - f["high"]) / price if price > 0 else 999
            if dist < 0.02:  # within 2% of the FVG edge
                candidates.append((dist, f))
        elif direction == "short" and f["type"] == "bearish":
            dist = abs(price - f["low"]) / price if price > 0 else 999
            if dist < 0.02:
                candidates.append((dist, f))

    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0])
    return candidates[0][1]
