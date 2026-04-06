"""Simple Exit Logic -- hold until TP, stop, or trend flip.

No Position IQ. No profit manager. No decay system.
Three reasons to exit:
1. Stop loss hit
2. Take profit hit
3. 1H EMA 21 slope flipped against us (trend changed)

That's it.
"""
from __future__ import annotations

import pandas as pd
from indicators.ema import ema


_CS = 5000.0


def _ema_slope(series: pd.Series, period: int = 21, lookback: int = 5) -> float:
    e = ema(series, period)
    if len(e) < lookback + 1:
        return 0.0
    return float(e.diff().tail(lookback).mean())


def should_exit_simple(
    *,
    direction: str,
    entry_price: float,
    current_price: float,
    stop_price: float,
    tp1: float,
    tp2: float,
    tp3: float,
    df_1h: pd.DataFrame,
) -> str | None:
    """Check if the simple trade should exit.

    Returns exit reason string or None (hold).
    """
    if not direction or entry_price <= 0 or current_price <= 0:
        return None

    # 1. STOP LOSS HIT
    if direction == "long" and current_price <= stop_price:
        return "simple_stop_loss"
    if direction == "short" and current_price >= stop_price:
        return "simple_stop_loss"

    # 2. TAKE PROFIT HIT (check TP1 for now -- single contract)
    if direction == "long" and current_price >= tp1:
        return "simple_tp1_hit"
    if direction == "short" and current_price <= tp1:
        return "simple_tp1_hit"

    # 3. TREND FLIP -- 1H EMA 21 slope reversed
    if df_1h is not None and len(df_1h) >= 30:
        slope = _ema_slope(df_1h["close"], 21, 5)
        if direction == "long" and slope < 0:
            # Was long, 1H trend flipped bearish -- get out
            pnl = (current_price - entry_price) * _CS
            if pnl > 0:
                return "simple_trend_flip_profit"
            else:
                return "simple_trend_flip_cut"
        if direction == "short" and slope > 0:
            pnl = (entry_price - current_price) * _CS
            if pnl > 0:
                return "simple_trend_flip_profit"
            else:
                return "simple_trend_flip_cut"

    # Hold. Trade is between stop and TP, trend intact.
    return None
