"""BB Width Percentile + TTM Squeeze indicators.

BB Width Percentile: measures current BB width as percentile of recent history.
< 10th percentile = extreme squeeze = breakout imminent.

TTM Squeeze: Bollinger Bands inside Keltner Channels = compression.
When squeeze fires (BB exits KC), expect explosive move.
"""
from __future__ import annotations

import pandas as pd
import numpy as np

from indicators.atr import atr as calc_atr


def bb_width_percentile(df: pd.DataFrame, period: int = 20, lookback: int = 100) -> pd.Series:
    """Bollinger Band Width as percentile of last N periods.
    Returns 0-100 percentile. < 10 = extreme squeeze."""
    if df is None or df.empty or len(df) < period + 1:
        return pd.Series(dtype=float, index=df.index if df is not None else [])
    close = pd.to_numeric(df["close"], errors="coerce")
    std = close.rolling(period).std(ddof=0)
    mean = close.rolling(period).mean()
    bb_width = (std * 2) / mean.replace(0, np.nan)
    rank = bb_width.rolling(lookback, min_periods=max(10, lookback // 4)).apply(
        lambda x: (x.iloc[-1] > x[:-1]).sum() / max(1, len(x) - 1) * 100
        if len(x) > 1 else 50.0,
        raw=False,
    )
    return rank.fillna(50.0)


def ttm_squeeze(
    df: pd.DataFrame,
    bb_period: int = 20,
    bb_mult: float = 2.0,
    kc_period: int = 20,
    kc_mult: float = 1.5,
) -> pd.Series:
    """TTM Squeeze: True when BB is inside Keltner Channel (squeeze ON).
    False when BB exits KC (squeeze OFF = breakout firing)."""
    if df is None or df.empty or len(df) < max(bb_period, kc_period) + 1:
        return pd.Series(False, index=df.index if df is not None else [])
    close = pd.to_numeric(df["close"], errors="coerce")
    mid = close.rolling(bb_period).mean()
    std = close.rolling(bb_period).std(ddof=0)
    bb_upper = mid + bb_mult * std
    bb_lower = mid - bb_mult * std

    atr_vals = calc_atr(df, kc_period)
    kc_upper = mid + kc_mult * atr_vals
    kc_lower = mid - kc_mult * atr_vals

    squeeze_on = (bb_lower > kc_lower) & (bb_upper < kc_upper)
    return squeeze_on.fillna(False)


def squeeze_fire(df: pd.DataFrame, **kwargs) -> pd.Series:
    """Detect squeeze-to-fire transitions (squeeze ON -> OFF).
    Returns True on the bar where squeeze fires."""
    sq = ttm_squeeze(df, **kwargs)
    return sq.shift(1).fillna(False) & ~sq
