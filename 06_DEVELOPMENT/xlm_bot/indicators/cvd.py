"""Cumulative Volume Delta (CVD) indicator.

Approximates buy/sell pressure from OHLCV candle data using close position
within the bar range. No tick data required -- works on standard candles.

Functions:
  compute_cvd     -- raw CVD series (cumulative delta)
  cvd_divergence  -- price vs CVD divergence detection
  cvd_momentum    -- fast/slow EMA crossover on CVD
  cvd_absorption  -- high volume + minimal price movement detection
"""
from __future__ import annotations

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Core CVD computation
# ---------------------------------------------------------------------------

def compute_cvd(df: pd.DataFrame) -> pd.Series:
    """Compute Cumulative Volume Delta from OHLCV data.

    Delta per candle is approximated by where close sits within the bar range:
      delta_pct  = (close - low) / (high - low)   [0.5 if flat bar]
      buy_vol    = volume * delta_pct
      sell_vol   = volume * (1 - delta_pct)
      delta      = buy_vol - sell_vol

    Returns the cumulative sum of delta as a Series (same index as input).
    """
    if df.empty or len(df) < 1:
        return pd.Series(dtype=float, index=df.index)

    high = df["high"].values
    low = df["low"].values
    close = df["close"].values
    volume = df["volume"].values

    bar_range = high - low
    # Where high == low (doji / flat bar), assume neutral 0.5
    flat_mask = bar_range == 0
    safe_range = np.where(flat_mask, 1.0, bar_range)

    delta_pct = np.where(flat_mask, 0.5, (close - low) / safe_range)
    delta_pct = np.clip(delta_pct, 0.0, 1.0)

    delta = volume * (2.0 * delta_pct - 1.0)  # buy - sell simplified
    cvd = np.cumsum(delta)

    return pd.Series(cvd, index=df.index, name="cvd")


# ---------------------------------------------------------------------------
# Divergence detection
# ---------------------------------------------------------------------------

def _trend_direction(series: np.ndarray) -> str:
    """Simple linear regression slope to classify trend."""
    n = len(series)
    if n < 3:
        return "flat"
    x = np.arange(n, dtype=float)
    x_mean = x.mean()
    s_mean = series.mean()
    denom = np.sum((x - x_mean) ** 2)
    if denom == 0:
        return "flat"
    slope = np.sum((x - x_mean) * (series - s_mean)) / denom
    # Normalize slope relative to series range for threshold
    s_range = series.max() - series.min()
    if s_range == 0:
        return "flat"
    norm_slope = slope * n / s_range
    if norm_slope > 0.3:
        return "up"
    elif norm_slope < -0.3:
        return "down"
    return "flat"


def _find_peaks(arr: np.ndarray) -> list[int]:
    """Find local maxima indices (simple 3-point comparison)."""
    peaks = []
    for i in range(1, len(arr) - 1):
        if arr[i] > arr[i - 1] and arr[i] > arr[i + 1]:
            peaks.append(i)
    return peaks


def _find_troughs(arr: np.ndarray) -> list[int]:
    """Find local minima indices (simple 3-point comparison)."""
    troughs = []
    for i in range(1, len(arr) - 1):
        if arr[i] < arr[i - 1] and arr[i] < arr[i + 1]:
            troughs.append(i)
    return troughs


def cvd_divergence(df: pd.DataFrame, lookback: int = 20) -> dict:
    """Detect divergence between price and CVD.

    Bearish divergence: price higher highs, CVD lower highs.
    Bullish divergence: price lower lows, CVD higher lows.

    Returns dict with divergence type, strength, trends, and score adjustments.
    """
    result = {
        "divergence": "none",
        "strength": 0.0,
        "price_trend": "flat",
        "cvd_trend": "flat",
        "score_adj_long": 0,
        "score_adj_short": 0,
    }

    if df.empty or len(df) < lookback + 2:
        return result

    cvd_series = compute_cvd(df)
    window = df.tail(lookback)
    cvd_window = cvd_series.tail(lookback)

    price_arr = window["close"].values.astype(float)
    cvd_arr = cvd_window.values.astype(float)

    result["price_trend"] = _trend_direction(price_arr)
    result["cvd_trend"] = _trend_direction(cvd_arr)

    # Check bearish divergence: price higher highs + CVD lower highs
    price_peaks = _find_peaks(price_arr)
    cvd_peaks = _find_peaks(cvd_arr)

    if len(price_peaks) >= 2 and len(cvd_peaks) >= 2:
        p1, p2 = price_arr[price_peaks[-2]], price_arr[price_peaks[-1]]
        c1, c2 = cvd_arr[cvd_peaks[-2]], cvd_arr[cvd_peaks[-1]]
        if p2 > p1 and c2 < c1:
            # Strength based on how much CVD declined relative to price rise
            p_change = abs(p2 - p1) / max(abs(p1), 1e-10)
            c_change = abs(c1 - c2) / max(abs(c1), 1e-10)
            strength = min((p_change + c_change) / 2.0, 1.0)
            result["divergence"] = "bearish"
            result["strength"] = round(strength, 3)
            result["score_adj_long"] = -8
            result["score_adj_short"] = 5
            return result

    # Check bullish divergence: price lower lows + CVD higher lows
    price_troughs = _find_troughs(price_arr)
    cvd_troughs = _find_troughs(cvd_arr)

    if len(price_troughs) >= 2 and len(cvd_troughs) >= 2:
        p1, p2 = price_arr[price_troughs[-2]], price_arr[price_troughs[-1]]
        c1, c2 = cvd_arr[cvd_troughs[-2]], cvd_arr[cvd_troughs[-1]]
        if p2 < p1 and c2 > c1:
            p_change = abs(p1 - p2) / max(abs(p1), 1e-10)
            c_change = abs(c2 - c1) / max(abs(c1), 1e-10)
            strength = min((p_change + c_change) / 2.0, 1.0)
            result["divergence"] = "bullish"
            result["strength"] = round(strength, 3)
            result["score_adj_long"] = 5
            result["score_adj_short"] = -8
            return result

    return result


# ---------------------------------------------------------------------------
# CVD Momentum (EMA crossover)
# ---------------------------------------------------------------------------

def cvd_momentum(df: pd.DataFrame, fast: int = 5, slow: int = 20) -> dict:
    """Compute CVD momentum via fast/slow EMA crossover.

    Returns dict with current EMA values, crossover state, and momentum label.
    """
    result = {
        "cvd_fast": 0.0,
        "cvd_slow": 0.0,
        "crossover": "none",
        "momentum": "neutral",
    }

    if df.empty or len(df) < slow + 2:
        return result

    cvd_series = compute_cvd(df)
    ema_fast = cvd_series.ewm(span=fast, adjust=False).mean()
    ema_slow = cvd_series.ewm(span=slow, adjust=False).mean()

    result["cvd_fast"] = round(float(ema_fast.iloc[-1]), 4)
    result["cvd_slow"] = round(float(ema_slow.iloc[-1]), 4)

    # Crossover detection: compare last two bars
    prev_diff = ema_fast.iloc[-2] - ema_slow.iloc[-2]
    curr_diff = ema_fast.iloc[-1] - ema_slow.iloc[-1]

    if prev_diff <= 0 and curr_diff > 0:
        result["crossover"] = "bullish"
    elif prev_diff >= 0 and curr_diff < 0:
        result["crossover"] = "bearish"

    # Momentum classification based on EMA spread
    spread = curr_diff
    avg_vol = df["volume"].tail(slow).mean()
    if avg_vol == 0:
        return result

    # Normalize spread by average volume for comparable thresholds
    norm_spread = spread / avg_vol

    if norm_spread > 0.5:
        result["momentum"] = "strong_buy"
    elif norm_spread > 0.1:
        result["momentum"] = "buy"
    elif norm_spread < -0.5:
        result["momentum"] = "strong_sell"
    elif norm_spread < -0.1:
        result["momentum"] = "sell"
    else:
        result["momentum"] = "neutral"

    return result


# ---------------------------------------------------------------------------
# CVD Absorption detection
# ---------------------------------------------------------------------------

def cvd_absorption(df: pd.DataFrame, window: int = 5) -> dict:
    """Detect volume absorption -- high volume with minimal price movement.

    Absorption signals that one side is absorbing the other's pressure without
    letting price move. Often precedes reversals.

    Criteria: volume > 2x average AND price range < 0.5x average range.

    Returns dict with detection flag, type, and score adjustment.
    """
    result = {
        "detected": False,
        "type": "none",
        "score_adj": 0,
    }

    if df.empty or len(df) < window + 1:
        return result

    recent = df.tail(window + 1)
    lookback = recent.iloc[:-1]  # previous N bars for averages
    current = recent.iloc[-1]

    avg_volume = lookback["volume"].mean()
    avg_range = (lookback["high"] - lookback["low"]).mean()

    if avg_volume == 0 or avg_range == 0:
        return result

    current_range = current["high"] - current["low"]
    current_volume = current["volume"]

    vol_ratio = current_volume / avg_volume
    range_ratio = current_range / avg_range

    # Absorption: high volume (>2x) but small range (<0.5x)
    if vol_ratio > 2.0 and range_ratio < 0.5:
        result["detected"] = True

        # Classify: buying absorption holds price up, selling absorption holds it down
        delta_pct = (current["close"] - current["low"]) / max(current_range, 1e-10) if current_range > 0 else 0.5

        if delta_pct >= 0.5:
            # Close near high despite huge volume -- buyers absorbing sell pressure
            result["type"] = "buying_absorption"
            result["score_adj"] = 6  # bullish
        else:
            # Close near low despite huge volume -- sellers absorbing buy pressure
            result["type"] = "selling_absorption"
            result["score_adj"] = -6  # bearish (negative = favors short)

    return result
