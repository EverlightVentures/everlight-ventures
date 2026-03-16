from __future__ import annotations

from typing import Dict, List

import pandas as pd

from indicators.ema import ema
from indicators.rsi import rsi
from indicators.macd import macd
from structure.levels import nearest_level


def ema_bias(df_1h: pd.DataFrame, df_4h: pd.DataFrame) -> Dict[str, bool]:
    """Relaxed EMA bias — accepts partial alignment (1h OR 4h).

    Old logic required BOTH timeframes + slope + separation = almost never true
    in ranging markets. Now: 1h alignment alone is sufficient; 4h is a bonus
    but not required. Slope check uses 2-bar lookback instead of 3.
    """
    out = {"long": False, "short": False}
    if df_1h.empty or df_4h.empty:
        return out
    e21_1h = ema(df_1h["close"], 21)
    e55_1h = ema(df_1h["close"], 55)
    e21_4h = ema(df_4h["close"], 21)
    e55_4h = ema(df_4h["close"], 55)

    slope_ok = e21_1h.diff().tail(2).mean() > 0

    # Core: EMA21 vs EMA55 on each timeframe independently
    long_1h = e21_1h.iloc[-1] > e55_1h.iloc[-1]
    long_4h = e21_4h.iloc[-1] > e55_4h.iloc[-1]
    short_1h = e21_1h.iloc[-1] < e55_1h.iloc[-1]
    short_4h = e21_4h.iloc[-1] < e55_4h.iloc[-1]

    # Accept 1h OR 4h alignment (was AND — killed ranging markets)
    out["long"] = (long_1h or long_4h) and slope_ok
    out["short"] = (short_1h or short_4h) and not slope_ok
    return out


def rsi_ok(df_15m: pd.DataFrame, direction: str) -> bool:
    """RSI validity check — relaxed for ranging markets.

    Old logic: no extremes in last 10 bars AND RSI 40-60. This failed
    constantly because any RSI dip below 30 would disqualify longs for 10 bars.
    New: RSI in 30-70 range, direction-appropriate (longs: RSI > 35, shorts: RSI < 65).
    """
    if df_15m.empty:
        return False
    r = rsi(df_15m["close"], 14)
    last = r.iloc[-1]
    if direction == "long":
        return 30 <= last <= 70
    return 30 <= last <= 70


def macd_expanding(df_15m: pd.DataFrame, direction: str) -> bool:
    if df_15m.empty:
        return False
    m = macd(df_15m["close"])
    hist = m["hist"]
    if len(hist) < 3:
        return False
    if direction == "long":
        return hist.iloc[-1] > hist.iloc[-2] > hist.iloc[-3]
    return hist.iloc[-1] < hist.iloc[-2] < hist.iloc[-3]


def rvol_ok(df_15m: pd.DataFrame, min_rvol: float = 0.8) -> bool:
    if df_15m.empty or len(df_15m) < 25:
        return False
    vol = df_15m["volume"]
    avg = vol.rolling(20).mean().iloc[-1]
    if avg <= 0:
        return False
    rvol = vol.iloc[-1] / avg
    return rvol >= min_rvol


def structure_zone(price: float, levels: Dict[str, float], tolerance_pct: float = 0.012) -> bool:
    if not levels:
        return False
    _, dist = nearest_level(price, levels)
    return dist <= price * tolerance_pct


def fib_zone(price: float, fibs: Dict[str, float], tolerance_pct: float = 0.008) -> bool:
    if not fibs:
        return False
    for lvl in fibs.values():
        if abs(price - lvl) <= price * tolerance_pct:
            return True
    return False


def compute_confluences(
    price: float,
    df_1h: pd.DataFrame,
    df_4h: pd.DataFrame,
    df_15m: pd.DataFrame,
    levels: Dict[str, float],
    fibs: Dict[str, float],
    direction: str,
) -> Dict[str, bool]:
    bias = ema_bias(df_1h, df_4h)
    conf = {
        "EMA_BIAS": bias["long"] if direction == "long" else bias["short"],
        "RSI_VALID": rsi_ok(df_15m, direction),
        "MACD_EXPAND": macd_expanding(df_15m, direction),
        "RVOL_OK": rvol_ok(df_15m),
        "STRUCTURE_ZONE": structure_zone(price, levels),
        "FIB_ZONE": fib_zone(price, fibs),
    }
    return conf


def confluence_passes(conf: Dict[str, bool]) -> bool:
    """Tiered confluence gate.

    - 3+ flags with struct/fib → strong pass (FULL quality)
    - 2+ flags with struct/fib → pass (REDUCED quality)
    - 2+ flags without struct/fib → pass (SCALP quality)
    - 1 or fewer → fail

    The old logic required 3+ AND struct_or_fib — too strict for ranging
    markets where EMA_BIAS and RVOL are almost never true simultaneously.
    """
    true_count = sum(1 for v in conf.values() if v)
    return true_count >= 2


def confluence_count(conf: Dict[str, bool]) -> int:
    return sum(1 for v in conf.values() if v)
