from __future__ import annotations

from typing import Dict, Tuple

import pandas as pd

FIB_LEVELS = [0.382, 0.5, 0.618, 0.786, 1.272, 1.618]


def find_swing(df: pd.DataFrame, lookback: int = 50) -> Tuple[float, float]:
    if df.empty:
        return 0.0, 0.0
    window = df.tail(lookback)
    swing_high = float(window["high"].max())
    swing_low = float(window["low"].min())
    return swing_high, swing_low


def fib_levels(swing_high: float, swing_low: float) -> Dict[str, float]:
    if swing_high == 0 or swing_low == 0:
        return {}
    levels = {}
    diff = swing_high - swing_low
    for lvl in FIB_LEVELS:
        if lvl <= 1:
            price = swing_low + diff * lvl
            levels[f"fib_{lvl}"] = price
        else:
            price = swing_high + diff * (lvl - 1)
            levels[f"fib_{lvl}"] = price
    return levels
