from __future__ import annotations

import pandas as pd


def vwap(df: pd.DataFrame, reset_hour: int = 0) -> pd.Series:
    """Session VWAP with daily reset.

    Expects columns: 'close', 'high', 'low', 'volume', 'time'.
    Returns a Series of VWAP values aligned with the input index.
    """
    if df.empty or len(df) < 2:
        return pd.Series(dtype=float, index=df.index)

    typical = (df["high"] + df["low"] + df["close"]) / 3
    dates = pd.to_datetime(df["time"]).dt.date
    cum_tpv = (typical * df["volume"]).groupby(dates).cumsum()
    cum_vol = df["volume"].groupby(dates).cumsum()
    return cum_tpv / cum_vol.replace(0, float("nan"))
