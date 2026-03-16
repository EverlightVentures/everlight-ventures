from __future__ import annotations

import numpy as np
import pandas as pd


def adx(df: pd.DataFrame, length: int = 14) -> pd.Series:
    if df.empty:
        return pd.Series(dtype="float64")

    high = pd.to_numeric(df["high"], errors="coerce")
    low = pd.to_numeric(df["low"], errors="coerce")
    close = pd.to_numeric(df["close"], errors="coerce")

    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)

    tr = pd.concat(
        [
            (high - low),
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs(),
        ],
        axis=1,
    ).max(axis=1)

    atr = tr.ewm(alpha=1 / length, adjust=False).mean()
    atr = atr.replace(0, np.nan)
    plus_di = 100.0 * (plus_dm.ewm(alpha=1 / length, adjust=False).mean() / atr)
    minus_di = 100.0 * (minus_dm.ewm(alpha=1 / length, adjust=False).mean() / atr)

    denom = (plus_di + minus_di).replace(0, np.nan)
    dx = 100.0 * (plus_di - minus_di).abs() / denom
    return dx.astype("float64").ewm(alpha=1 / length, adjust=False).mean()
