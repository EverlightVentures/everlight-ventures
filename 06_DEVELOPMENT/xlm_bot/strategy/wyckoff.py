"""Wyckoff accumulation/distribution phase detector.

Identifies the current Wyckoff market phase from price action and
volume patterns over a configurable lookback window.  Also detects
springs (false breakdowns) and upthrusts (false breakouts) which
are high-conviction reversal signals.

Phases:
    ACCUMULATION -- smart money buying at range lows, declining volume
                    on drops, rising volume on rallies
    DISTRIBUTION -- smart money selling at range highs, declining volume
                    on rallies, rising volume on drops
    MARKUP       -- trending up with expanding volume, higher lows
    MARKDOWN     -- trending down with expanding volume, lower highs
    RANGING      -- sideways but no clear accumulation/distribution signal

Score adjustments plug directly into the lane scoring system.
"""
from __future__ import annotations

from typing import Dict

import numpy as np
import pandas as pd


_PHASES = ("ACCUMULATION", "DISTRIBUTION", "MARKUP", "MARKDOWN", "RANGING")


def detect_wyckoff_phase(
    df: pd.DataFrame,
    lookback: int = 96,
) -> Dict:
    """Analyze recent price/volume action for Wyckoff phase.

    Parameters
    ----------
    df : pd.DataFrame
        OHLCV dataframe with columns: open, high, low, close, volume.
    lookback : int
        Number of bars to analyze.  96 x 15min = 24 hours.

    Returns
    -------
    dict with keys:
        phase          -- one of ACCUMULATION, DISTRIBUTION, MARKUP,
                          MARKDOWN, RANGING
        confidence     -- float 0-1 indicating signal strength
        bias           -- "long", "short", or "neutral"
        score_adj_long -- int score adjustment for long setups
        score_adj_short -- int score adjustment for short setups
        details        -- dict with sub-metrics used in detection
    """
    default = {
        "phase": "RANGING",
        "confidence": 0.0,
        "bias": "neutral",
        "score_adj_long": 0,
        "score_adj_short": 0,
        "details": {},
    }

    required = {"open", "high", "low", "close", "volume"}
    if df.empty or len(df) < max(lookback, 20) or not required.issubset(df.columns):
        return default

    window = df.iloc[-lookback:].copy()
    closes = window["close"].values.astype(float)
    highs = window["high"].values.astype(float)
    lows = window["low"].values.astype(float)
    volumes = window["volume"].values.astype(float)

    # --- Range detection ---
    price_range_high = float(np.max(highs))
    price_range_low = float(np.min(lows))
    price_span = price_range_high - price_range_low
    mid_price = (price_range_high + price_range_low) / 2.0

    if mid_price <= 0:
        return default

    range_pct = price_span / mid_price

    # --- Trend detection ---
    half = lookback // 2
    first_half_mean = float(np.mean(closes[:half]))
    second_half_mean = float(np.mean(closes[half:]))
    trend_delta = (second_half_mean - first_half_mean) / max(first_half_mean, 1e-12)

    # --- Higher lows / lower highs ---
    quarter = max(lookback // 4, 2)
    q_lows = [float(np.min(lows[i * quarter:(i + 1) * quarter]))
              for i in range(4) if (i + 1) * quarter <= lookback]
    q_highs = [float(np.max(highs[i * quarter:(i + 1) * quarter]))
               for i in range(4) if (i + 1) * quarter <= lookback]

    higher_lows = all(q_lows[i] < q_lows[i + 1] for i in range(len(q_lows) - 1)) if len(q_lows) >= 2 else False
    lower_highs = all(q_highs[i] > q_highs[i + 1] for i in range(len(q_highs) - 1)) if len(q_highs) >= 2 else False

    # --- Volume analysis ---
    up_bars = closes[1:] > closes[:-1]
    down_bars = closes[1:] < closes[:-1]
    vol_trail = volumes[1:]  # align with up_bars/down_bars

    avg_vol_up = float(np.mean(vol_trail[up_bars])) if np.any(up_bars) else 0.0
    avg_vol_down = float(np.mean(vol_trail[down_bars])) if np.any(down_bars) else 0.0

    # Volume trend -- compare first half vs second half
    vol_first = float(np.mean(volumes[:half])) if half > 0 else 0.0
    vol_second = float(np.mean(volumes[half:])) if half > 0 else 0.0
    vol_expanding = vol_second > vol_first * 1.1

    # Volume bias: positive = more volume on up bars, negative = more on down bars
    total_vol = avg_vol_up + avg_vol_down
    vol_bias = (avg_vol_up - avg_vol_down) / max(total_vol, 1e-12)

    # --- Spring / upthrust quick check ---
    recent = df.iloc[-5:]
    recent_low = float(recent["low"].min())
    recent_high = float(recent["high"].max())
    recent_close = float(recent["close"].iloc[-1])
    has_spring = recent_low < price_range_low and recent_close > price_range_low
    has_upthrust = recent_high > price_range_high and recent_close < price_range_high

    details = {
        "range_pct": round(range_pct, 4),
        "trend_delta": round(trend_delta, 4),
        "vol_bias": round(vol_bias, 4),
        "vol_expanding": vol_expanding,
        "higher_lows": higher_lows,
        "lower_highs": lower_highs,
        "has_spring": has_spring,
        "has_upthrust": has_upthrust,
        "avg_vol_up": round(avg_vol_up, 2),
        "avg_vol_down": round(avg_vol_down, 2),
    }

    # --- Phase classification ---
    is_ranging = range_pct < 0.06  # less than 6% range = consolidation
    is_trending = abs(trend_delta) > 0.015  # more than 1.5% shift between halves

    # MARKUP: trending up + expanding volume + higher lows
    if trend_delta > 0.015 and (vol_expanding or higher_lows):
        confidence = min(1.0, abs(trend_delta) * 20 + (0.2 if vol_expanding else 0))
        return {
            "phase": "MARKUP",
            "confidence": round(confidence, 3),
            "bias": "long",
            "score_adj_long": 5,
            "score_adj_short": -3,
            "details": details,
        }

    # MARKDOWN: trending down + expanding volume + lower highs
    if trend_delta < -0.015 and (vol_expanding or lower_highs):
        confidence = min(1.0, abs(trend_delta) * 20 + (0.2 if vol_expanding else 0))
        return {
            "phase": "MARKDOWN",
            "confidence": round(confidence, 3),
            "bias": "short",
            "score_adj_long": -3,
            "score_adj_short": 5,
            "details": details,
        }

    # ACCUMULATION: ranging, volume favors up bars, possible spring
    if is_ranging and vol_bias > 0.05:
        confidence = min(1.0, vol_bias * 2 + (0.3 if has_spring else 0))
        return {
            "phase": "ACCUMULATION",
            "confidence": round(confidence, 3),
            "bias": "long",
            "score_adj_long": 8,
            "score_adj_short": -6,
            "details": details,
        }

    # DISTRIBUTION: ranging, volume favors down bars, possible upthrust
    if is_ranging and vol_bias < -0.05:
        confidence = min(1.0, abs(vol_bias) * 2 + (0.3 if has_upthrust else 0))
        return {
            "phase": "DISTRIBUTION",
            "confidence": round(confidence, 3),
            "bias": "short",
            "score_adj_long": -6,
            "score_adj_short": 8,
            "details": details,
        }

    # RANGING: in range but no clear volume signature
    confidence = 0.3 if is_ranging else 0.1
    return {
        "phase": "RANGING",
        "confidence": round(confidence, 3),
        "bias": "neutral",
        "score_adj_long": 0,
        "score_adj_short": 0,
        "details": details,
    }


def detect_spring_upthrust(
    df: pd.DataFrame,
    support: float,
    resistance: float,
    atr: float,
) -> Dict:
    """Detect Wyckoff spring or upthrust on the most recent candle.

    A spring is a false breakdown below support that closes back above
    it -- a high-conviction bullish reversal.  An upthrust is the mirror:
    a false breakout above resistance that closes back below.

    Parameters
    ----------
    df : pd.DataFrame
        OHLCV dataframe. Uses the last candle.
    support : float
        Key support level (e.g. range low, equal lows).
    resistance : float
        Key resistance level (e.g. range high, equal highs).
    atr : float
        Current ATR for depth validation.

    Returns
    -------
    dict with keys:
        signal    -- "spring", "upthrust", or "none"
        level     -- the support/resistance level that was tested
        score_adj -- int score adjustment (+12 for confirmed signals)
    """
    no_signal = {"signal": "none", "level": 0.0, "score_adj": 0}

    if df.empty or len(df) < 2 or atr <= 0:
        return no_signal

    last = df.iloc[-1]
    candle_low = float(last["low"])
    candle_high = float(last["high"])
    candle_close = float(last["close"])

    # Spring: wick below support, close reclaimed above support
    if candle_low < support and candle_close > support:
        penetration = support - candle_low
        if 0 < penetration <= 1.0 * atr:
            return {
                "signal": "spring",
                "level": round(support, 6),
                "score_adj": 12,
            }

    # Upthrust: wick above resistance, close reclaimed below resistance
    if candle_high > resistance and candle_close < resistance:
        penetration = candle_high - resistance
        if 0 < penetration <= 1.0 * atr:
            return {
                "signal": "upthrust",
                "level": round(resistance, 6),
                "score_adj": 12,
            }

    return no_signal
