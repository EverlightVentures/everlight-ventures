from __future__ import annotations

import pandas as pd


def _ema(series: pd.Series, length: int) -> pd.Series:
    return series.ewm(span=length, adjust=False).mean()


def _atr(df: pd.DataFrame, length: int = 14) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close = df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    return tr.rolling(length).mean()


def _rsi(series: pd.Series, length: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(length).mean()
    avg_loss = loss.rolling(length).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def _atr_expansion(df: pd.DataFrame, mult: float = 1.2) -> bool:
    if df.empty or len(df) < 40:
        return False
    a = _atr(df, 14)
    recent = a.iloc[-1]
    mean20 = a.rolling(20).mean().iloc[-1]
    if pd.isna(recent) or pd.isna(mean20):
        return False
    return recent > mult * mean20


def _rvol(df: pd.DataFrame) -> float:
    if df.empty or len(df) < 25:
        return 0.0
    vol = df["volume"]
    base = vol.rolling(20).mean().iloc[-1]
    if base == 0 or pd.isna(base):
        return 0.0
    return float(vol.iloc[-1] / base)


def _rsi_slope(df: pd.DataFrame) -> float:
    if df.empty or len(df) < 10:
        return 0.0
    r = _rsi(df["close"], 14)
    recent = r.tail(3)
    if recent.isna().any():
        return 0.0
    return float(recent.iloc[-1] - recent.iloc[0])


def _ema_strength(df: pd.DataFrame) -> bool:
    if df.empty or len(df) < 210:
        return False
    e21 = _ema(df["close"], 21)
    e55 = _ema(df["close"], 55)
    e200 = _ema(df["close"], 200)
    return e21.iloc[-1] > e55.iloc[-1] > e200.iloc[-1] or e21.iloc[-1] < e55.iloc[-1] < e200.iloc[-1]


def dominant_timeframe(df_4h: pd.DataFrame, df_1h: pd.DataFrame, df_30m: pd.DataFrame) -> str:
    if _ema_strength(df_4h) and _atr_expansion(df_4h, 1.15):
        return "4h"
    if _ema_strength(df_1h) and _atr_expansion(df_1h, 1.15):
        return "1h"
    return "30m"


def classify_breakout(df: pd.DataFrame, direction: str) -> str:
    atr_exp = _atr_expansion(df, 1.2)
    rvol = _rvol(df)
    slope = _rsi_slope(df)
    slope_ok = slope > 2.5 if direction == "buy" else slope < -2.5

    if atr_exp and rvol >= 2.0 and slope_ok:
        return "exponential"
    if atr_exp or rvol >= 1.5:
        return "trend"
    return "neutral"
