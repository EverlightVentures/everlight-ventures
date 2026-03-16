from __future__ import annotations

from typing import Dict, Optional, Tuple

import pandas as pd

from indicators.atr import atr


def find_last_swing(df_1h: pd.DataFrame, direction: str, lookback: int = 20) -> float:
    if df_1h.empty:
        return 0.0
    window = df_1h.tail(lookback)
    if direction == "long":
        return float(window["low"].min())
    return float(window["high"].max())


def stop_loss_price(price: float, df_1h: pd.DataFrame, direction: str,
                    df_15m: pd.DataFrame | None = None,
                    buffer_atr_mult: float = 0.5) -> float:
    swing = find_last_swing(df_1h, direction)
    if swing <= 0:
        return 0.0
    # Add ATR wick buffer so normal volatility doesn't clip the stop
    if df_15m is not None and len(df_15m) >= 14:
        atr_series = atr(df_15m, 14)
        if not atr_series.empty and not pd.isna(atr_series.iloc[-1]):
            atr_val = float(atr_series.iloc[-1])
            buffer = buffer_atr_mult * atr_val
            if direction == "long":
                swing -= buffer
            else:
                swing += buffer
    return swing


def sl_distance_ok(price: float, stop_price: float, max_pct: float) -> bool:
    if price <= 0 or stop_price <= 0:
        return False
    dist = abs(price - stop_price) / price
    return dist <= max_pct


def structure_stop_loss_price(
    price: float,
    entry_result: dict,
    direction: str,
    df_15m: pd.DataFrame,
    buffer_atr_mult: float = 0.3,
) -> float:
    """Structure-based stop for trend_continuation entries.

    Short → stop above the most recent lower-high + ATR buffer.
    Long  → stop below the most recent higher-low − ATR buffer.

    Often tighter than the default 20-bar swing stop, giving better R:R.
    """
    structure_stop = entry_result.get("structure_stop")
    if not structure_stop or structure_stop <= 0:
        return 0.0

    buffer = 0.0
    if df_15m is not None and len(df_15m) >= 14:
        atr_series = atr(df_15m, 14)
        if not atr_series.empty and not pd.isna(atr_series.iloc[-1]):
            buffer = buffer_atr_mult * float(atr_series.iloc[-1])

    if direction == "short":
        return structure_stop + buffer
    return structure_stop - buffer
