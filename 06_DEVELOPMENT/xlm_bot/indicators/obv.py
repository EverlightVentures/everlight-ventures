"""On Balance Volume (OBV) indicator.

Cumulative volume: add volume on up-close bars, subtract on down-close.
OBV divergence (price flat/down but OBV rising) signals accumulation.
"""
from __future__ import annotations

import pandas as pd


def obv(df: pd.DataFrame) -> pd.Series:
    """Compute OBV from DataFrame with 'close' and 'volume' columns."""
    if df.empty or len(df) < 2:
        return pd.Series(dtype=float, index=df.index)
    direction = df["close"].diff().apply(lambda x: 1 if x > 0 else (-1 if x < 0 else 0))
    return (df["volume"] * direction).cumsum()


def obv_divergence(df: pd.DataFrame, direction: str, lookback: int = 14) -> bool:
    """Detect OBV divergence.

    Bullish: price lower low + OBV higher low (accumulation).
    Bearish: price higher high + OBV lower high (distribution).
    """
    if df.empty or len(df) < lookback + 2:
        return False
    obv_series = obv(df)
    if obv_series.isna().tail(lookback).any():
        return False
    window = df.tail(lookback)
    obv_window = obv_series.tail(lookback)
    half = lookback // 2
    if direction == "long":
        recent_price_low = float(window["low"].iloc[-3:].min())
        earlier_price_low = float(window["low"].iloc[:half].min())
        recent_obv_low = float(obv_window.iloc[-3:].min())
        earlier_obv_low = float(obv_window.iloc[:half].min())
        return recent_price_low < earlier_price_low and recent_obv_low > earlier_obv_low
    else:
        recent_price_high = float(window["high"].iloc[-3:].max())
        earlier_price_high = float(window["high"].iloc[:half].max())
        recent_obv_high = float(obv_window.iloc[-3:].max())
        earlier_obv_high = float(obv_window.iloc[:half].max())
        return recent_price_high > earlier_price_high and recent_obv_high < earlier_obv_high
