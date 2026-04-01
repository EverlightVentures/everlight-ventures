"""Anchored VWAP from swing points.

Standard VWAP resets daily. Anchored VWAP starts from a specific swing
high or low, giving a cleaner view of whether a move is still valid.
When price crosses below anchored VWAP from a swing low = move is over.
"""
from __future__ import annotations

import pandas as pd
import numpy as np


def anchored_vwap(df: pd.DataFrame, anchor_idx: int) -> pd.Series:
    """VWAP anchored from a specific candle index (swing high/low).
    Returns Series with NaN before anchor and VWAP values from anchor onward."""
    if df is None or df.empty or anchor_idx < 0 or anchor_idx >= len(df):
        return pd.Series(np.nan, index=df.index if df is not None else [])
    subset = df.iloc[anchor_idx:]
    tp = (subset["high"] + subset["low"] + subset["close"]) / 3
    vol = subset["volume"].replace(0, np.nan)
    cumvol = vol.cumsum()
    cumtpvol = (tp * vol).cumsum()
    avwap = cumtpvol / cumvol
    result = pd.Series(np.nan, index=df.index)
    result.iloc[anchor_idx:] = avwap.values
    return result


def find_swing_anchor(df: pd.DataFrame, lookback: int = 50) -> tuple:
    """Find the most recent swing high and swing low indices within lookback.
    Returns (swing_high_iloc, swing_low_iloc) as integer positions."""
    if df is None or df.empty or len(df) < 5:
        return (0, 0)
    window = df.iloc[-min(lookback, len(df)):]
    swing_high_iloc = len(df) - min(lookback, len(df)) + int(window["high"].values.argmax())
    swing_low_iloc = len(df) - min(lookback, len(df)) + int(window["low"].values.argmin())
    return (swing_high_iloc, swing_low_iloc)


def anchored_vwap_bias(df: pd.DataFrame, lookback: int = 50) -> dict:
    """Compute anchored VWAPs from both swing high and swing low.
    Returns dict with avwap values and whether price is above/below each."""
    if df is None or df.empty or len(df) < 10:
        return {"swing_high_avwap": None, "swing_low_avwap": None,
                "above_low_avwap": False, "below_high_avwap": False}
    hi_idx, lo_idx = find_swing_anchor(df, lookback)
    price = float(df["close"].iloc[-1])

    avwap_from_high = anchored_vwap(df, hi_idx)
    avwap_from_low = anchored_vwap(df, lo_idx)

    hi_val = float(avwap_from_high.iloc[-1]) if not pd.isna(avwap_from_high.iloc[-1]) else None
    lo_val = float(avwap_from_low.iloc[-1]) if not pd.isna(avwap_from_low.iloc[-1]) else None

    return {
        "swing_high_avwap": hi_val,
        "swing_low_avwap": lo_val,
        "above_low_avwap": price > lo_val if lo_val is not None else False,
        "below_high_avwap": price < hi_val if hi_val is not None else False,
    }
