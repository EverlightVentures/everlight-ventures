"""RSI Gap / Spread indicator.

Measures how far RSI has stretched from its own smoothing line.
When the gap is wide and starts closing, price is likely to mean-revert.

RSI_GAP = RSI(14) - SMA(RSI, 9)
- Wide positive gap (>15) → overbought stretch, likely to snap back down
- Wide negative gap (<-15) → oversold stretch, likely to snap back up
- Gap closing (shrinking 2 bars in a row) → mean reversion in progress
"""
from __future__ import annotations

import pandas as pd

from indicators.rsi import rsi


def rsi_gap(df: pd.DataFrame, rsi_period: int = 14, ma_period: int = 9) -> dict:
    """Compute RSI gap metrics.

    Returns dict with:
        rsi_now: current RSI value
        rsi_ma: smoothed RSI (SMA of RSI)
        gap: RSI - RSI_MA (positive = overbought stretch, negative = oversold)
        gap_abs: absolute gap
        gap_wide: True if |gap| >= 15
        gap_closing: True if |gap| has decreased for 2 consecutive bars
        gap_direction: "bullish" (negative gap = oversold) or "bearish" (positive gap)
    """
    result = {
        "rsi_now": None,
        "rsi_ma": None,
        "gap": 0.0,
        "gap_abs": 0.0,
        "gap_wide": False,
        "gap_closing": False,
        "gap_direction": "neutral",
    }

    if df is None or df.empty or len(df) < rsi_period + ma_period + 3:
        return result

    rsi_series = rsi(df["close"], rsi_period)
    if rsi_series.isna().tail(ma_period + 3).sum() > ma_period // 2:
        return result

    rsi_ma = rsi_series.rolling(ma_period).mean()

    rsi_now = float(rsi_series.iloc[-1])
    ma_now = float(rsi_ma.iloc[-1])

    if pd.isna(rsi_now) or pd.isna(ma_now):
        return result

    gap = rsi_now - ma_now
    gap_abs = abs(gap)

    # Check if gap is closing (shrinking for 2 bars)
    gap_closing = False
    if len(rsi_series) >= 3 and len(rsi_ma) >= 3:
        gaps = []
        for i in range(-3, 0):
            r = rsi_series.iloc[i]
            m = rsi_ma.iloc[i]
            if not pd.isna(r) and not pd.isna(m):
                gaps.append(abs(float(r) - float(m)))
        if len(gaps) == 3:
            gap_closing = gaps[2] < gaps[1] < gaps[0]

    result["rsi_now"] = round(rsi_now, 2)
    result["rsi_ma"] = round(ma_now, 2)
    result["gap"] = round(gap, 2)
    result["gap_abs"] = round(gap_abs, 2)
    result["gap_wide"] = gap_abs >= 15.0
    result["gap_closing"] = gap_closing

    if gap < -5:
        result["gap_direction"] = "bullish"   # oversold stretch → expect bounce
    elif gap > 5:
        result["gap_direction"] = "bearish"   # overbought stretch → expect pullback
    else:
        result["gap_direction"] = "neutral"

    return result


def rsi_gap_signal(df: pd.DataFrame, direction: str, rsi_period: int = 14, ma_period: int = 9) -> bool:
    """Return True if RSI gap supports a mean-reversion entry in the given direction.

    Bullish (long): gap was wide negative AND is now closing (oversold snapping back)
    Bearish (short): gap was wide positive AND is now closing (overbought snapping back)
    """
    g = rsi_gap(df, rsi_period, ma_period)
    if not g["gap_wide"] or not g["gap_closing"]:
        return False
    if direction == "long":
        return g["gap_direction"] == "bullish"  # negative gap closing
    else:
        return g["gap_direction"] == "bearish"  # positive gap closing
