"""Chart pattern detection engine for v4 scoring.

Detects multi-bar structural patterns from OHLC data:
  - Flag / Pennant (continuation after impulse)
  - Cup & Handle (rounded bottom + consolidation breakout)
  - Double Bottom / Double Top (W/M reversal)

Pure functions — operate on existing 15m DataFrame.
Returns dicts that plug into v4_engine as scoring flags.

Detection rates target: 1-5% of bars (selective, not noisy).
"""
from __future__ import annotations

import pandas as pd
import numpy as np


# Minimum confidence to report a detection (filters weak matches)
MIN_CONFIDENCE = 65


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _atr_14(df: pd.DataFrame) -> float:
    """Compute 14-period ATR from OHLC DataFrame."""
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - df["close"].shift(1)).abs(),
        (df["low"] - df["close"].shift(1)).abs(),
    ], axis=1).max(axis=1)
    val = tr.rolling(14).mean().iloc[-1]
    return float(val) if not pd.isna(val) and val > 0 else 0.0


# ---------------------------------------------------------------------------
# 1. Flag / Pennant (Continuation)
# ---------------------------------------------------------------------------

def detect_flag(
    df: pd.DataFrame,
    direction: str,
    pole_bars: int = 8,
    flag_bars: int = 12,
    min_pole_move_atr: float = 2.0,
) -> dict:
    """Detect bull/bear flag pattern.

    A flag is a sharp impulse move (pole) followed by a tight consolidation
    (flag) that slopes against the impulse direction. Continuation signal.

    Tightened: pole must be ≥2.0 ATR, flag range < 40% of pole,
    retrace < 38.2% of pole, and pole must be directional (>60% body).
    """
    result = {
        "detected": False,
        "direction": "neutral",
        "pole_size_atr": 0.0,
        "flag_bars_count": 0,
        "flag_range_pct": 0.0,
        "confidence": 0,
    }

    need = pole_bars + flag_bars + 20
    if df is None or df.empty or len(df) < need:
        return result

    atr_14 = _atr_14(df)
    if atr_14 <= 0:
        return result

    for flag_len in range(4, flag_bars + 1):
        pole_end = len(df) - flag_len
        pole_start = max(0, pole_end - pole_bars)

        if pole_start >= pole_end:
            continue

        pole_slice = df.iloc[pole_start:pole_end + 1]
        flag_slice = df.iloc[pole_end:len(df)]

        if len(pole_slice) < 3 or len(flag_slice) < 3:
            continue

        pole_high = float(pole_slice["high"].max())
        pole_low = float(pole_slice["low"].min())
        pole_move = pole_high - pole_low
        pole_close_start = float(pole_slice.iloc[0]["close"])
        pole_close_end = float(pole_slice.iloc[-1]["close"])
        pole_direction = pole_close_end - pole_close_start

        # Pole must be ≥2 ATR
        if pole_move < min_pole_move_atr * atr_14:
            continue

        # Pole must be directional (net close change > 60% of range)
        if abs(pole_direction) < pole_move * 0.60:
            continue

        flag_high = float(flag_slice["high"].max())
        flag_low = float(flag_slice["low"].min())
        flag_range = flag_high - flag_low
        flag_mid = (flag_high + flag_low) / 2

        # Flag must be tight (< 40% of pole)
        if flag_range > pole_move * 0.40:
            continue

        # Flag must retrace less than 38.2% of pole (Fibonacci)
        if direction == "long":
            if pole_direction <= 0:
                continue
            retrace = pole_high - flag_low
            if retrace > pole_move * 0.382:
                continue
            cur_close = float(df.iloc[-1]["close"])
            if cur_close < flag_mid:
                continue
            result["direction"] = "bullish"
        else:
            if pole_direction >= 0:
                continue
            retrace = flag_high - pole_low
            if retrace > pole_move * 0.382:
                continue
            cur_close = float(df.iloc[-1]["close"])
            if cur_close > flag_mid:
                continue
            result["direction"] = "bearish"

        tightness = 1.0 - (flag_range / pole_move)
        pole_strength = min(pole_move / (atr_14 * min_pole_move_atr), 3.0) / 3.0
        conf = int(min(100, (tightness * 50 + pole_strength * 50)))

        if conf < MIN_CONFIDENCE:
            continue

        result["detected"] = True
        result["pole_size_atr"] = round(pole_move / atr_14, 2)
        result["flag_bars_count"] = flag_len
        result["flag_range_pct"] = round(flag_range / float(df.iloc[-1]["close"]) * 100, 3)
        result["confidence"] = conf
        return result

    return result


# ---------------------------------------------------------------------------
# 2. Cup & Handle
# ---------------------------------------------------------------------------

def detect_cup_handle(
    df: pd.DataFrame,
    direction: str,
    cup_min_bars: int = 60,
    cup_max_bars: int = 140,
    handle_max_bars: int = 12,
) -> dict:
    """Detect cup & handle pattern (bullish) or inverted cup & handle (bearish).

    Tightened: min 30 bars (~7.5h on 15m), cup depth 3-12%, rim symmetry ≤1.5%,
    handle within 1.5% of rim, and U-shape roundness check.
    """
    result = {
        "detected": False,
        "direction": "neutral",
        "cup_depth_pct": 0.0,
        "cup_bars": 0,
        "handle_bars": 0,
        "rim_price": 0.0,
        "confidence": 0,
    }

    if df is None or df.empty or len(df) < cup_min_bars + 10:
        return result

    if direction == "long":
        return _detect_cup_handle_bullish(df, cup_min_bars, cup_max_bars, handle_max_bars, result)
    else:
        return _detect_cup_handle_bearish(df, cup_min_bars, cup_max_bars, handle_max_bars, result)


def _detect_cup_handle_bullish(df, cup_min, cup_max, handle_max, result):
    """Bullish cup & handle: U-shaped bottom → handle pullback → breakout."""
    cur_close = float(df.iloc[-1]["close"])

    for total_len in range(cup_min + 5, min(cup_max + handle_max, len(df) - 5) + 1, 4):
        start_idx = len(df) - total_len
        if start_idx < 0:
            continue

        segment = df.iloc[start_idx:]
        seg_len = len(segment)

        # Left rim: high in first 20% of pattern
        left_slice = segment.iloc[:max(3, seg_len // 5)]
        left_rim = float(left_slice["high"].max())

        # Cup bottom: low in the middle 60%
        mid_start = seg_len // 5
        mid_end = 4 * seg_len // 5
        mid_section = segment.iloc[mid_start:mid_end]
        if len(mid_section) < 5:
            continue
        cup_bottom = float(mid_section["low"].min())

        # Right rim: high in last 20%
        right_slice = segment.iloc[4 * seg_len // 5:]
        right_rim = float(right_slice["high"].max())

        # Rim symmetry: must be within 1.5%
        rim_avg = (left_rim + right_rim) / 2
        if rim_avg <= 0:
            continue
        rim_diff_pct = abs(left_rim - right_rim) / rim_avg * 100
        if rim_diff_pct > 0.8:
            continue

        # Cup depth: 5% to 10%
        cup_depth_pct = (rim_avg - cup_bottom) / rim_avg * 100
        if cup_depth_pct < 5.0 or cup_depth_pct > 10.0:
            continue

        # U-shape roundness: the bottom should be in the middle third, not at edges
        bottom_idx = mid_section["low"].idxmin()
        if hasattr(bottom_idx, '__index__'):
            # Convert to position relative to mid_section
            bottom_pos = mid_section.index.get_loc(bottom_idx)
        else:
            bottom_pos = len(mid_section) // 2  # fallback
        mid_third_start = len(mid_section) // 3
        mid_third_end = 2 * len(mid_section) // 3
        if bottom_pos < mid_third_start or bottom_pos > mid_third_end:
            continue  # V-shape or skewed, not a cup

        # Handle: current price within 1.0% of right rim
        handle_depth = (right_rim - cur_close) / right_rim * 100
        if handle_depth > 1.0:
            continue
        if cur_close < cup_bottom:
            continue

        symmetry_score = max(0, 40 - rim_diff_pct * 20)
        depth_score = min(30, cup_depth_pct * 4)
        breakout_score = 30 if cur_close >= right_rim * 0.995 else 10
        conf = int(min(100, symmetry_score + depth_score + breakout_score))

        if conf < MIN_CONFIDENCE:
            continue

        result["detected"] = True
        result["direction"] = "bullish"
        result["cup_depth_pct"] = round(cup_depth_pct, 2)
        result["cup_bars"] = total_len
        result["rim_price"] = round(rim_avg, 6)
        result["confidence"] = conf
        return result

    return result


def _detect_cup_handle_bearish(df, cup_min, cup_max, handle_max, result):
    """Inverted cup & handle: inverted U-shape top → handle rally → breakdown."""
    cur_close = float(df.iloc[-1]["close"])

    for total_len in range(cup_min + 5, min(cup_max + handle_max, len(df) - 5) + 1, 4):
        start_idx = len(df) - total_len
        if start_idx < 0:
            continue

        segment = df.iloc[start_idx:]
        seg_len = len(segment)

        left_slice = segment.iloc[:max(3, seg_len // 5)]
        left_rim = float(left_slice["low"].min())

        mid_start = seg_len // 5
        mid_end = 4 * seg_len // 5
        mid_section = segment.iloc[mid_start:mid_end]
        if len(mid_section) < 5:
            continue
        cup_top = float(mid_section["high"].max())

        right_slice = segment.iloc[4 * seg_len // 5:]
        right_rim = float(right_slice["low"].min())

        rim_avg = (left_rim + right_rim) / 2
        if rim_avg <= 0:
            continue
        rim_diff_pct = abs(left_rim - right_rim) / rim_avg * 100
        if rim_diff_pct > 1.5:
            continue

        cup_depth_pct = (cup_top - rim_avg) / rim_avg * 100
        if cup_depth_pct < 3.0 or cup_depth_pct > 12.0:
            continue

        # Roundness check
        top_idx = mid_section["high"].idxmax()
        if hasattr(top_idx, '__index__'):
            top_pos = mid_section.index.get_loc(top_idx)
        else:
            top_pos = len(mid_section) // 2
        mid_third_start = len(mid_section) // 3
        mid_third_end = 2 * len(mid_section) // 3
        if top_pos < mid_third_start or top_pos > mid_third_end:
            continue

        handle_depth = (cur_close - right_rim) / right_rim * 100
        if handle_depth > 1.0:
            continue
        if cur_close > cup_top:
            continue

        symmetry_score = max(0, 40 - rim_diff_pct * 20)
        depth_score = min(30, cup_depth_pct * 4)
        breakdown_score = 30 if cur_close <= right_rim * 1.005 else 10
        conf = int(min(100, symmetry_score + depth_score + breakdown_score))

        if conf < MIN_CONFIDENCE:
            continue

        result["detected"] = True
        result["direction"] = "bearish"
        result["cup_depth_pct"] = round(cup_depth_pct, 2)
        result["cup_bars"] = total_len
        result["rim_price"] = round(rim_avg, 6)
        result["confidence"] = conf
        return result

    return result


# ---------------------------------------------------------------------------
# 3. Double Bottom / Double Top
# ---------------------------------------------------------------------------

def detect_double_pattern(
    df: pd.DataFrame,
    direction: str,
    lookback: int = 160,
    tolerance_pct: float = 0.25,
    min_valley_gap: int = 40,
) -> dict:
    """Detect double bottom (bullish) or double top (bearish).

    Tightened: tolerance 0.5%, min gap 16 bars (4h on 15m), lookback 80 bars,
    neckline must be ≥1.5% above/below the level, and recency gate (second touch
    within last 40% of window).
    """
    result = {
        "detected": False,
        "direction": "neutral",
        "level_price": 0.0,
        "touches": 0,
        "neckline_price": 0.0,
        "gap_bars": 0,
        "confidence": 0,
    }

    if df is None or df.empty or len(df) < lookback:
        return result

    window = df.tail(lookback)
    cur_close = float(df.iloc[-1]["close"])

    if direction == "long":
        return _detect_double_bottom(window, cur_close, tolerance_pct, min_valley_gap, result)
    else:
        return _detect_double_top(window, cur_close, tolerance_pct, min_valley_gap, result)


def _detect_double_bottom(window, cur_close, tol_pct, min_gap, result):
    """Double bottom (W pattern): two lows at similar price → bullish."""
    lows = window["low"].values.astype(float)
    highs = window["high"].values.astype(float)
    n = len(lows)

    # Find swing lows (local minima with order=4 for stronger pivots)
    swing_lows = []
    for i in range(4, n - 4):
        if (lows[i] <= lows[i-1] and lows[i] <= lows[i-2] and
                lows[i] <= lows[i-3] and lows[i] <= lows[i-4] and
                lows[i] <= lows[i+1] and lows[i] <= lows[i+2] and
                lows[i] <= lows[i+3] and lows[i] <= lows[i+4]):
            swing_lows.append((i, lows[i]))

    if len(swing_lows) < 2:
        return result

    best_conf = 0
    for i in range(len(swing_lows)):
        for j in range(i + 1, len(swing_lows)):
            idx1, low1 = swing_lows[i]
            idx2, low2 = swing_lows[j]

            gap = idx2 - idx1
            if gap < min_gap:
                continue

            avg_low = (low1 + low2) / 2
            if avg_low <= 0:
                continue
            diff_pct = abs(low1 - low2) / avg_low * 100
            if diff_pct > tol_pct:
                continue

            # Neckline: highest point between the two lows
            between = highs[idx1:idx2 + 1]
            neckline = float(between.max())

            # Neckline must be meaningful: ≥1.5% above the level
            neck_height_pct = (neckline - avg_low) / avg_low * 100
            if neck_height_pct < 3.0:
                continue

            # Current price near neckline (within 1.5%)
            neck_dist_pct = (neckline - cur_close) / neckline * 100
            if neck_dist_pct > 1.5:
                continue

            # Recency: second low must be in last 40% of window
            if idx2 < n * 0.6:
                continue

            level_score = max(0, 40 - diff_pct * 40)
            gap_score = min(30, gap * 1.0)
            breakout_score = 30 if cur_close >= neckline * 0.99 else 10
            conf = int(min(100, level_score + gap_score + breakout_score))

            if conf < MIN_CONFIDENCE:
                continue

            if conf > best_conf:
                best_conf = conf
                result["detected"] = True
                result["direction"] = "bullish"
                result["level_price"] = round(avg_low, 6)
                result["touches"] = 2
                result["neckline_price"] = round(neckline, 6)
                result["gap_bars"] = gap
                result["confidence"] = conf

    return result


def _detect_double_top(window, cur_close, tol_pct, min_gap, result):
    """Double top (M pattern): two highs at similar price → bearish."""
    highs = window["high"].values.astype(float)
    lows = window["low"].values.astype(float)
    n = len(highs)

    swing_highs = []
    for i in range(4, n - 4):
        if (highs[i] >= highs[i-1] and highs[i] >= highs[i-2] and
                highs[i] >= highs[i-3] and highs[i] >= highs[i-4] and
                highs[i] >= highs[i+1] and highs[i] >= highs[i+2] and
                highs[i] >= highs[i+3] and highs[i] >= highs[i+4]):
            swing_highs.append((i, highs[i]))

    if len(swing_highs) < 2:
        return result

    best_conf = 0
    for i in range(len(swing_highs)):
        for j in range(i + 1, len(swing_highs)):
            idx1, high1 = swing_highs[i]
            idx2, high2 = swing_highs[j]

            gap = idx2 - idx1
            if gap < min_gap:
                continue

            avg_high = (high1 + high2) / 2
            if avg_high <= 0:
                continue
            diff_pct = abs(high1 - high2) / avg_high * 100
            if diff_pct > tol_pct:
                continue

            between = lows[idx1:idx2 + 1]
            neckline = float(between.min())

            # Neckline depth must be meaningful: ≥1.5% below the level
            neck_depth_pct = (avg_high - neckline) / avg_high * 100
            if neck_depth_pct < 3.0:
                continue

            neck_dist_pct = (cur_close - neckline) / neckline * 100
            if neck_dist_pct > 1.5:
                continue

            if idx2 < n * 0.6:
                continue

            level_score = max(0, 40 - diff_pct * 40)
            gap_score = min(30, gap * 1.0)
            breakdown_score = 30 if cur_close <= neckline * 1.01 else 10
            conf = int(min(100, level_score + gap_score + breakdown_score))

            if conf < MIN_CONFIDENCE:
                continue

            if conf > best_conf:
                best_conf = conf
                result["detected"] = True
                result["direction"] = "bearish"
                result["level_price"] = round(avg_high, 6)
                result["touches"] = 2
                result["neckline_price"] = round(neckline, 6)
                result["gap_bars"] = gap
                result["confidence"] = conf

    return result


# ---------------------------------------------------------------------------
# Unified interface
# ---------------------------------------------------------------------------

def detect_patterns(df: pd.DataFrame, direction: str) -> dict:
    """Run all pattern detectors and return unified result.

    Returns:
        dict with flag, cup_handle, double_pattern sub-dicts,
        plus any_detected, best_pattern, best_confidence.
    """
    flag = detect_flag(df, direction)
    cup = detect_cup_handle(df, direction)
    double = detect_double_pattern(df, direction)

    patterns = {
        "flag": flag,
        "cup_handle": cup,
        "double_pattern": double,
    }

    best_name = None
    best_conf = 0
    for name, p in patterns.items():
        if p["detected"] and p["confidence"] > best_conf:
            best_name = name
            best_conf = p["confidence"]

    patterns["any_detected"] = best_name is not None
    patterns["best_pattern"] = best_name
    patterns["best_confidence"] = best_conf

    return patterns
