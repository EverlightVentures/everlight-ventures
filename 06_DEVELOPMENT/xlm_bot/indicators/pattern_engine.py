"""Chart pattern detection engine for v4 scoring.

Detects multi-bar structural patterns from OHLC data:
  - Flag / Pennant (continuation after impulse)
  - Cup & Handle (rounded bottom + consolidation breakout)
  - Double Bottom / Double Top (W/M reversal)
  - Triangle (ascending / descending / symmetrical)
  - Wedge (rising / falling)
  - Head & Shoulders / Inverse H&S
  - Triple Top / Triple Bottom
  - Rectangle (range box)
  - Rounded Reversal (rounded top / bottom)
  - Diamond (broadening then narrowing reversal)
  - Island Reversal (gap isolation pattern)
  - Pipe (two adjacent tall candles)
  - Failure Swing (failed new extreme)
  - Pennant (converging triangle after impulse)
  - Measured Move / AB=CD
  - Ascending Scallop (rounded bottoms trending higher)
  - Descending Scallop (rounded tops trending lower)
  - Broadening / Megaphone
  - Bump and Run
  - Order Block (ICT)
  - Fair Value Gap (ICT)
  - Breaker Block (ICT)
  - Market Structure Shift (BOS)
  - Harmonic AB=CD
  - Channel Breakout (regression)
  - Donchian Breakout
  - Keltner Squeeze

Pure functions -- operate on existing 15m DataFrame.
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


def _swing_highs(highs: np.ndarray, order: int = 2) -> list[tuple[int, float]]:
    """Find swing high points.  A swing high at index i means
    high[i] > all neighbours within ``order`` bars on each side."""
    pts = []
    n = len(highs)
    for i in range(order, n - order):
        if all(highs[i] > highs[i - j] for j in range(1, order + 1)) and \
           all(highs[i] > highs[i + j] for j in range(1, order + 1)):
            pts.append((i, float(highs[i])))
    return pts


def _swing_lows(lows: np.ndarray, order: int = 2) -> list[tuple[int, float]]:
    """Find swing low points.  A swing low at index i means
    low[i] < all neighbours within ``order`` bars on each side."""
    pts = []
    n = len(lows)
    for i in range(order, n - order):
        if all(lows[i] < lows[i - j] for j in range(1, order + 1)) and \
           all(lows[i] < lows[i + j] for j in range(1, order + 1)):
            pts.append((i, float(lows[i])))
    return pts


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
# 4. Triangle (Ascending / Descending / Symmetrical)
# ---------------------------------------------------------------------------

def detect_triangle(
    df: pd.DataFrame,
    direction: str,
    lookback: int = 60,
    min_touches: int = 3,
    flat_tol_pct: float = 0.5,
) -> dict:
    """Detect triangle patterns from converging swing highs and lows.

    Ascending: flat resistance + rising support -> bullish.
    Descending: flat support + falling resistance -> bearish.
    Symmetrical: both converging -> neutral.
    Requires at least ``min_touches`` on each trendline side.
    """
    result = {
        "detected": False,
        "direction": "neutral",
        "triangle_type": "none",
        "upper_slope": 0.0,
        "lower_slope": 0.0,
        "touches_upper": 0,
        "touches_lower": 0,
        "confidence": 0,
    }

    if df is None or df.empty or len(df) < lookback:
        return result

    window = df.tail(lookback)
    highs = window["high"].values.astype(float)
    lows = window["low"].values.astype(float)
    n = len(highs)

    sh = _swing_highs(highs, order=2)
    sl = _swing_lows(lows, order=2)

    if len(sh) < min_touches or len(sl) < min_touches:
        return result

    # Linear regression on swing highs and swing lows
    sh_x = np.array([p[0] for p in sh], dtype=float)
    sh_y = np.array([p[1] for p in sh], dtype=float)
    sl_x = np.array([p[0] for p in sl], dtype=float)
    sl_y = np.array([p[1] for p in sl], dtype=float)

    if len(sh_x) < 2 or len(sl_x) < 2:
        return result

    h_slope, h_intercept = np.polyfit(sh_x, sh_y, 1)
    l_slope, l_intercept = np.polyfit(sl_x, sl_y, 1)

    avg_price = float(window["close"].mean())
    if avg_price <= 0:
        return result

    # Normalize slopes to percentage per bar
    h_slope_pct = h_slope / avg_price * 100
    l_slope_pct = l_slope / avg_price * 100

    # Check for convergence: upper slope must be <= lower slope (narrowing)
    if h_slope >= l_slope:
        return result  # diverging or parallel, not a triangle

    # Check flatness using tolerance
    h_flat = abs(h_slope_pct) < flat_tol_pct / n * 10  # scaled tolerance
    l_flat = abs(l_slope_pct) < flat_tol_pct / n * 10

    # Residual check -- swing points should be close to trendlines
    h_residuals = np.abs(sh_y - (h_slope * sh_x + h_intercept))
    l_residuals = np.abs(sl_y - (l_slope * sl_x + l_intercept))
    h_fit = float(np.mean(h_residuals)) / avg_price * 100
    l_fit = float(np.mean(l_residuals)) / avg_price * 100
    if h_fit > 0.5 or l_fit > 0.5:
        return result  # poor fit, not a clean triangle

    # Classify
    tri_type = "none"
    tri_dir = "neutral"
    if h_flat and l_slope > 0:
        tri_type = "ascending"
        tri_dir = "bullish"
    elif l_flat and h_slope < 0:
        tri_type = "descending"
        tri_dir = "bearish"
    elif h_slope < 0 and l_slope > 0:
        tri_type = "symmetrical"
        tri_dir = "neutral"
    else:
        return result

    # Direction filter
    if direction == "long" and tri_dir == "bearish":
        return result
    if direction == "short" and tri_dir == "bullish":
        return result

    # Confidence scoring
    touch_score = min(40, (len(sh) + len(sl) - 2 * min_touches) * 10 + 20)
    fit_score = max(0, 30 - (h_fit + l_fit) * 30)
    convergence = abs(h_slope_pct - l_slope_pct)
    conv_score = min(30, convergence * 100)
    conf = int(min(100, touch_score + fit_score + conv_score))

    if conf < MIN_CONFIDENCE:
        return result

    result["detected"] = True
    result["direction"] = tri_dir
    result["triangle_type"] = tri_type
    result["upper_slope"] = round(h_slope_pct, 4)
    result["lower_slope"] = round(l_slope_pct, 4)
    result["touches_upper"] = len(sh)
    result["touches_lower"] = len(sl)
    result["confidence"] = conf
    return result


# ---------------------------------------------------------------------------
# 5. Wedge (Rising / Falling)
# ---------------------------------------------------------------------------

def detect_wedge(
    df: pd.DataFrame,
    direction: str,
    lookback: int = 60,
) -> dict:
    """Detect rising or falling wedge from converging trendlines.

    Rising wedge: both trendlines slope UP but converge -> bearish.
    Falling wedge: both trendlines slope DOWN but converge -> bullish.
    Uses linear regression on swing highs and swing lows.
    """
    result = {
        "detected": False,
        "direction": "neutral",
        "wedge_type": "none",
        "upper_slope": 0.0,
        "lower_slope": 0.0,
        "convergence_pct": 0.0,
        "confidence": 0,
    }

    if df is None or df.empty or len(df) < lookback:
        return result

    window = df.tail(lookback)
    highs = window["high"].values.astype(float)
    lows = window["low"].values.astype(float)

    sh = _swing_highs(highs, order=2)
    sl = _swing_lows(lows, order=2)

    if len(sh) < 3 or len(sl) < 3:
        return result

    sh_x = np.array([p[0] for p in sh], dtype=float)
    sh_y = np.array([p[1] for p in sh], dtype=float)
    sl_x = np.array([p[0] for p in sl], dtype=float)
    sl_y = np.array([p[1] for p in sl], dtype=float)

    h_slope, h_intercept = np.polyfit(sh_x, sh_y, 1)
    l_slope, l_intercept = np.polyfit(sl_x, sl_y, 1)

    avg_price = float(window["close"].mean())
    if avg_price <= 0:
        return result

    h_slope_pct = h_slope / avg_price * 100
    l_slope_pct = l_slope / avg_price * 100

    # Both slopes must point the same direction
    if h_slope * l_slope <= 0:
        return result  # not a wedge (different slope signs)

    # Must be converging: range at end < range at start
    range_start = (h_intercept) - (l_intercept)
    range_end = (h_slope * (len(window) - 1) + h_intercept) - \
                (l_slope * (len(window) - 1) + l_intercept)
    if range_start <= 0 or range_end <= 0:
        return result
    if range_end >= range_start:
        return result  # not converging

    convergence_pct = (range_start - range_end) / range_start * 100

    # Residual quality check
    h_residuals = np.abs(sh_y - (h_slope * sh_x + h_intercept))
    l_residuals = np.abs(sl_y - (l_slope * sl_x + l_intercept))
    h_fit = float(np.mean(h_residuals)) / avg_price * 100
    l_fit = float(np.mean(l_residuals)) / avg_price * 100
    if h_fit > 0.4 or l_fit > 0.4:
        return result

    # Classify
    if h_slope > 0 and l_slope > 0:
        wedge_type = "rising"
        wedge_dir = "bearish"
    elif h_slope < 0 and l_slope < 0:
        wedge_type = "falling"
        wedge_dir = "bullish"
    else:
        return result

    # Direction filter
    if direction == "long" and wedge_dir == "bearish":
        return result
    if direction == "short" and wedge_dir == "bullish":
        return result

    # Confidence scoring
    touch_score = min(35, (len(sh) + len(sl) - 4) * 8 + 15)
    fit_score = max(0, 30 - (h_fit + l_fit) * 40)
    conv_score = min(35, convergence_pct * 0.7)
    conf = int(min(100, touch_score + fit_score + conv_score))

    if conf < MIN_CONFIDENCE:
        return result

    result["detected"] = True
    result["direction"] = wedge_dir
    result["wedge_type"] = wedge_type
    result["upper_slope"] = round(h_slope_pct, 4)
    result["lower_slope"] = round(l_slope_pct, 4)
    result["convergence_pct"] = round(convergence_pct, 2)
    result["confidence"] = conf
    return result


# ---------------------------------------------------------------------------
# 6. Head & Shoulders / Inverse H&S
# ---------------------------------------------------------------------------

def detect_head_shoulders(
    df: pd.DataFrame,
    direction: str,
    lookback: int = 120,
    shoulder_tol_pct: float = 2.0,
) -> dict:
    """Detect Head & Shoulders (bearish) or Inverse H&S (bullish).

    H&S: three peaks where the centre peak is highest and the two shoulder
    peaks are roughly symmetric.  Inverse H&S mirrors this with troughs.
    Reports neckline_price, head_price, and shoulder_prices.
    """
    result = {
        "detected": False,
        "direction": "neutral",
        "pattern_type": "none",
        "head_price": 0.0,
        "shoulder_prices": [],
        "neckline_price": 0.0,
        "confidence": 0,
    }

    if df is None or df.empty or len(df) < lookback:
        return result

    window = df.tail(lookback)
    highs = window["high"].values.astype(float)
    lows = window["low"].values.astype(float)
    cur_close = float(df.iloc[-1]["close"])

    if direction == "short":
        return _detect_hs_top(highs, lows, cur_close, shoulder_tol_pct, result)
    else:
        return _detect_hs_bottom(highs, lows, cur_close, shoulder_tol_pct, result)


def _detect_hs_top(highs, lows, cur_close, tol_pct, result):
    """Standard H&S top -- bearish reversal."""
    n = len(highs)
    peaks = _swing_highs(highs, order=3)
    if len(peaks) < 3:
        return result

    best_conf = 0
    for i in range(len(peaks) - 2):
        ls_idx, ls_val = peaks[i]
        hd_idx, hd_val = peaks[i + 1]
        rs_idx, rs_val = peaks[i + 2]

        # Head must be highest
        if hd_val <= ls_val or hd_val <= rs_val:
            continue

        # Shoulders roughly symmetric
        avg_shoulder = (ls_val + rs_val) / 2
        if avg_shoulder <= 0:
            continue
        shoulder_diff_pct = abs(ls_val - rs_val) / avg_shoulder * 100
        if shoulder_diff_pct > tol_pct:
            continue

        # Neckline: line connecting the two troughs between peaks
        trough1_slice = lows[ls_idx:hd_idx + 1]
        trough2_slice = lows[hd_idx:rs_idx + 1]
        if len(trough1_slice) < 2 or len(trough2_slice) < 2:
            continue
        neck1 = float(trough1_slice.min())
        neck2 = float(trough2_slice.min())
        neckline = (neck1 + neck2) / 2

        # Head must be meaningfully above neckline (> 1.5%)
        head_height_pct = (hd_val - neckline) / neckline * 100
        if head_height_pct < 1.5:
            continue

        # Recency: right shoulder should be in last 50% of window
        if rs_idx < n * 0.5:
            continue

        # Current price near or below neckline
        neck_dist_pct = (cur_close - neckline) / neckline * 100
        if neck_dist_pct > 2.0:
            continue

        symmetry_score = max(0, 35 - shoulder_diff_pct * 15)
        height_score = min(35, head_height_pct * 7)
        breakout_score = 30 if cur_close <= neckline * 1.005 else 10
        conf = int(min(100, symmetry_score + height_score + breakout_score))

        if conf < MIN_CONFIDENCE and conf <= best_conf:
            continue

        if conf > best_conf:
            best_conf = conf
            result["detected"] = True
            result["direction"] = "bearish"
            result["pattern_type"] = "head_and_shoulders"
            result["head_price"] = round(hd_val, 6)
            result["shoulder_prices"] = [round(ls_val, 6), round(rs_val, 6)]
            result["neckline_price"] = round(neckline, 6)
            result["confidence"] = conf

    return result


def _detect_hs_bottom(highs, lows, cur_close, tol_pct, result):
    """Inverse H&S bottom -- bullish reversal."""
    n = len(lows)
    troughs = _swing_lows(lows, order=3)
    if len(troughs) < 3:
        return result

    best_conf = 0
    for i in range(len(troughs) - 2):
        ls_idx, ls_val = troughs[i]
        hd_idx, hd_val = troughs[i + 1]
        rs_idx, rs_val = troughs[i + 2]

        # Head must be lowest
        if hd_val >= ls_val or hd_val >= rs_val:
            continue

        # Shoulders roughly symmetric
        avg_shoulder = (ls_val + rs_val) / 2
        if avg_shoulder <= 0:
            continue
        shoulder_diff_pct = abs(ls_val - rs_val) / avg_shoulder * 100
        if shoulder_diff_pct > tol_pct:
            continue

        # Neckline: line connecting the two peaks between troughs
        peak1_slice = highs[ls_idx:hd_idx + 1]
        peak2_slice = highs[hd_idx:rs_idx + 1]
        if len(peak1_slice) < 2 or len(peak2_slice) < 2:
            continue
        neck1 = float(peak1_slice.max())
        neck2 = float(peak2_slice.max())
        neckline = (neck1 + neck2) / 2

        # Head must be meaningfully below neckline (> 1.5%)
        head_depth_pct = (neckline - hd_val) / neckline * 100
        if head_depth_pct < 1.5:
            continue

        # Recency: right shoulder in last 50%
        if rs_idx < n * 0.5:
            continue

        # Current price near or above neckline
        neck_dist_pct = (neckline - cur_close) / neckline * 100
        if neck_dist_pct > 2.0:
            continue

        symmetry_score = max(0, 35 - shoulder_diff_pct * 15)
        depth_score = min(35, head_depth_pct * 7)
        breakout_score = 30 if cur_close >= neckline * 0.995 else 10
        conf = int(min(100, symmetry_score + depth_score + breakout_score))

        if conf < MIN_CONFIDENCE and conf <= best_conf:
            continue

        if conf > best_conf:
            best_conf = conf
            result["detected"] = True
            result["direction"] = "bullish"
            result["pattern_type"] = "inverse_head_and_shoulders"
            result["head_price"] = round(hd_val, 6)
            result["shoulder_prices"] = [round(ls_val, 6), round(rs_val, 6)]
            result["neckline_price"] = round(neckline, 6)
            result["confidence"] = conf

    return result


# ---------------------------------------------------------------------------
# 7. Triple Top / Triple Bottom
# ---------------------------------------------------------------------------

def detect_triple_pattern(
    df: pd.DataFrame,
    direction: str,
    lookback: int = 200,
    tolerance_pct: float = 0.3,
    min_touch_gap: int = 20,
) -> dict:
    """Detect triple top (bearish) or triple bottom (bullish).

    Three touches at the same price level within ``tolerance_pct``,
    separated by at least ``min_touch_gap`` bars each.
    """
    result = {
        "detected": False,
        "direction": "neutral",
        "level_price": 0.0,
        "touches": 0,
        "gap_bars_avg": 0,
        "confidence": 0,
    }

    if df is None or df.empty or len(df) < lookback:
        return result

    window = df.tail(lookback)
    highs = window["high"].values.astype(float)
    lows = window["low"].values.astype(float)
    n = len(highs)

    if direction == "short":
        return _detect_triple_top(highs, lows, n, tolerance_pct, min_touch_gap, result)
    else:
        return _detect_triple_bottom(highs, lows, n, tolerance_pct, min_touch_gap, result)


def _detect_triple_top(highs, lows, n, tol_pct, min_gap, result):
    """Triple top: three swing highs at same level -> bearish."""
    peaks = _swing_highs(highs, order=4)
    if len(peaks) < 3:
        return result

    best_conf = 0
    for i in range(len(peaks)):
        for j in range(i + 1, len(peaks)):
            for k in range(j + 1, len(peaks)):
                idx1, v1 = peaks[i]
                idx2, v2 = peaks[j]
                idx3, v3 = peaks[k]

                # Minimum gap between each pair
                if idx2 - idx1 < min_gap or idx3 - idx2 < min_gap:
                    continue

                avg_val = (v1 + v2 + v3) / 3.0
                if avg_val <= 0:
                    continue

                # All three within tolerance of their average
                if (abs(v1 - avg_val) / avg_val * 100 > tol_pct or
                        abs(v2 - avg_val) / avg_val * 100 > tol_pct or
                        abs(v3 - avg_val) / avg_val * 100 > tol_pct):
                    continue

                # Recency: third touch in last 40%
                if idx3 < n * 0.6:
                    continue

                gap_avg = ((idx2 - idx1) + (idx3 - idx2)) / 2.0
                spread = max(abs(v1 - avg_val), abs(v2 - avg_val),
                             abs(v3 - avg_val)) / avg_val * 100
                level_score = max(0, 40 - spread * 100)
                gap_score = min(30, gap_avg * 0.75)
                touch_score = 30  # always 3 touches
                conf = int(min(100, level_score + gap_score + touch_score))

                if conf < MIN_CONFIDENCE:
                    continue
                if conf > best_conf:
                    best_conf = conf
                    result["detected"] = True
                    result["direction"] = "bearish"
                    result["level_price"] = round(avg_val, 6)
                    result["touches"] = 3
                    result["gap_bars_avg"] = int(gap_avg)
                    result["confidence"] = conf

    return result


def _detect_triple_bottom(highs, lows, n, tol_pct, min_gap, result):
    """Triple bottom: three swing lows at same level -> bullish."""
    troughs = _swing_lows(lows, order=4)
    if len(troughs) < 3:
        return result

    best_conf = 0
    for i in range(len(troughs)):
        for j in range(i + 1, len(troughs)):
            for k in range(j + 1, len(troughs)):
                idx1, v1 = troughs[i]
                idx2, v2 = troughs[j]
                idx3, v3 = troughs[k]

                if idx2 - idx1 < min_gap or idx3 - idx2 < min_gap:
                    continue

                avg_val = (v1 + v2 + v3) / 3.0
                if avg_val <= 0:
                    continue

                if (abs(v1 - avg_val) / avg_val * 100 > tol_pct or
                        abs(v2 - avg_val) / avg_val * 100 > tol_pct or
                        abs(v3 - avg_val) / avg_val * 100 > tol_pct):
                    continue

                if idx3 < n * 0.6:
                    continue

                gap_avg = ((idx2 - idx1) + (idx3 - idx2)) / 2.0
                spread = max(abs(v1 - avg_val), abs(v2 - avg_val),
                             abs(v3 - avg_val)) / avg_val * 100
                level_score = max(0, 40 - spread * 100)
                gap_score = min(30, gap_avg * 0.75)
                touch_score = 30
                conf = int(min(100, level_score + gap_score + touch_score))

                if conf < MIN_CONFIDENCE:
                    continue
                if conf > best_conf:
                    best_conf = conf
                    result["detected"] = True
                    result["direction"] = "bullish"
                    result["level_price"] = round(avg_val, 6)
                    result["touches"] = 3
                    result["gap_bars_avg"] = int(gap_avg)
                    result["confidence"] = conf

    return result


# ---------------------------------------------------------------------------
# 8. Rectangle (Range Box)
# ---------------------------------------------------------------------------

def detect_rectangle(
    df: pd.DataFrame,
    direction: str,
    lookback: int = 80,
    flat_tol_pct: float = 0.5,
    min_touches: int = 2,
) -> dict:
    """Detect rectangle / range box pattern.

    Flat support AND flat resistance (both within ``flat_tol_pct``
    tolerance), with at least ``min_touches`` on each side and range
    wider than 1 ATR.  Direction is neutral (trade the breakout).
    """
    result = {
        "detected": False,
        "direction": "neutral",
        "support_price": 0.0,
        "resistance_price": 0.0,
        "range_atr": 0.0,
        "touches_upper": 0,
        "touches_lower": 0,
        "confidence": 0,
    }

    if df is None or df.empty or len(df) < lookback:
        return result

    atr_14 = _atr_14(df)
    if atr_14 <= 0:
        return result

    window = df.tail(lookback)
    highs = window["high"].values.astype(float)
    lows = window["low"].values.astype(float)

    sh = _swing_highs(highs, order=2)
    sl = _swing_lows(lows, order=2)

    if len(sh) < min_touches or len(sl) < min_touches:
        return result

    # Resistance: check if swing highs are clustered (flat)
    sh_vals = np.array([p[1] for p in sh])
    sl_vals = np.array([p[1] for p in sl])

    res_mean = float(np.mean(sh_vals))
    sup_mean = float(np.mean(sl_vals))

    if res_mean <= 0 or sup_mean <= 0:
        return result

    res_spread = float(np.std(sh_vals)) / res_mean * 100
    sup_spread = float(np.std(sl_vals)) / sup_mean * 100

    if res_spread > flat_tol_pct or sup_spread > flat_tol_pct:
        return result

    # Range must be meaningful (> 1 ATR)
    box_range = res_mean - sup_mean
    if box_range <= 0 or box_range < atr_14:
        return result

    # Count touches within tolerance of mean levels
    res_touches = sum(1 for v in sh_vals
                      if abs(v - res_mean) / res_mean * 100 < flat_tol_pct)
    sup_touches = sum(1 for v in sl_vals
                      if abs(v - sup_mean) / sup_mean * 100 < flat_tol_pct)

    if res_touches < min_touches or sup_touches < min_touches:
        return result

    # Confidence scoring
    touch_score = min(40, (res_touches + sup_touches - 2 * min_touches) * 10 + 20)
    flat_score = max(0, 30 - (res_spread + sup_spread) * 30)
    range_score = min(30, box_range / atr_14 * 10)
    conf = int(min(100, touch_score + flat_score + range_score))

    if conf < MIN_CONFIDENCE:
        return result

    result["detected"] = True
    result["direction"] = "neutral"
    result["support_price"] = round(sup_mean, 6)
    result["resistance_price"] = round(res_mean, 6)
    result["range_atr"] = round(box_range / atr_14, 2)
    result["touches_upper"] = res_touches
    result["touches_lower"] = sup_touches
    result["confidence"] = conf
    return result


# ---------------------------------------------------------------------------
# 9. Rounded Reversal (Rounded Top / Bottom)
# ---------------------------------------------------------------------------

def detect_rounded_reversal(
    df: pd.DataFrame,
    direction: str,
    lookback: int = 90,
) -> dict:
    """Detect rounded top (bearish) or rounded bottom (bullish).

    Splits the last ``lookback`` bars into three equal thirds and compares
    their average close prices.  A U-shape (middle < edges) signals a
    rounded bottom; an inverted-U (middle > edges) signals a rounded top.
    """
    result = {
        "detected": False,
        "direction": "neutral",
        "pattern_type": "none",
        "edge_avg": 0.0,
        "middle_avg": 0.0,
        "curvature_pct": 0.0,
        "confidence": 0,
    }

    if df is None or df.empty or len(df) < lookback:
        return result

    window = df.tail(lookback)
    closes = window["close"].values.astype(float)
    n = len(closes)
    third = n // 3
    if third < 5:
        return result

    first_avg = float(np.mean(closes[:third]))
    mid_avg = float(np.mean(closes[third:2 * third]))
    last_avg = float(np.mean(closes[2 * third:]))
    edge_avg = (first_avg + last_avg) / 2.0

    if edge_avg <= 0 or mid_avg <= 0:
        return result

    curvature_pct = (mid_avg - edge_avg) / edge_avg * 100

    atr_14 = _atr_14(df)
    if atr_14 <= 0:
        return result

    # Require curvature to be at least 1 ATR worth (meaningful shape)
    min_curve = atr_14 / edge_avg * 100 * 1.5

    pat_type = "none"
    pat_dir = "neutral"

    if curvature_pct < -min_curve:
        # U-shape: middle lower than edges -> rounded bottom
        pat_type = "rounded_bottom"
        pat_dir = "bullish"
    elif curvature_pct > min_curve:
        # Inverted U: middle higher than edges -> rounded top
        pat_type = "rounded_top"
        pat_dir = "bearish"
    else:
        return result

    # Direction filter
    if direction == "long" and pat_dir == "bearish":
        return result
    if direction == "short" and pat_dir == "bullish":
        return result

    # Additional quality: last third should show reversal momentum
    # For bottom: last_avg > mid_avg; for top: last_avg < mid_avg
    if pat_type == "rounded_bottom" and last_avg <= mid_avg:
        return result
    if pat_type == "rounded_top" and last_avg >= mid_avg:
        return result

    # Symmetry: first and last thirds should be close to each other
    sym_diff_pct = abs(first_avg - last_avg) / edge_avg * 100
    if sym_diff_pct > 3.0:
        return result  # too lopsided

    abs_curve = abs(curvature_pct)
    curve_score = min(40, abs_curve * 10)
    sym_score = max(0, 30 - sym_diff_pct * 10)
    momentum_score = 30  # already passed the momentum check above
    conf = int(min(100, curve_score + sym_score + momentum_score))

    if conf < MIN_CONFIDENCE:
        return result

    result["detected"] = True
    result["direction"] = pat_dir
    result["pattern_type"] = pat_type
    result["edge_avg"] = round(edge_avg, 6)
    result["middle_avg"] = round(mid_avg, 6)
    result["curvature_pct"] = round(curvature_pct, 3)
    result["confidence"] = conf
    return result


# ---------------------------------------------------------------------------
# 10. Diamond Top / Bottom (Reversal)
# ---------------------------------------------------------------------------

def detect_diamond(
    df: pd.DataFrame,
    direction: str,
    lookback: int = 40,
    half: int = 10,
) -> dict:
    """Detect diamond top/bottom -- broadening then narrowing range.

    Split last ``lookback`` bars into two halves.  First half should show
    expanding range (each quarter wider than the prior), second half
    contracting.  The transition from expansion to contraction forms a
    diamond shape.
    """
    result = {"detected": False, "direction": "neutral", "confidence": 0}

    if df is None or df.empty or len(df) < lookback:
        return result

    window = df.tail(lookback)
    n = len(window)
    q = n // 4
    if q < 3:
        return result

    highs = window["high"].values.astype(float)
    lows = window["low"].values.astype(float)

    ranges = []
    for i in range(4):
        seg = slice(i * q, (i + 1) * q)
        ranges.append(float(highs[seg].max() - lows[seg].min()))

    # Broadening: q1 < q2; narrowing: q3 > q4
    if not (ranges[1] > ranges[0] * 1.15 and ranges[3] < ranges[2] * 0.85):
        return result

    # Direction: close below midpoint = bearish diamond top
    mid = (float(highs.max()) + float(lows.min())) / 2
    cur = float(df.iloc[-1]["close"])
    pat_dir = "bearish" if cur < mid else "bullish"

    if direction == "long" and pat_dir == "bearish":
        return result
    if direction == "short" and pat_dir == "bullish":
        return result

    expansion = ranges[1] / max(ranges[0], 1e-12)
    contraction = ranges[2] / max(ranges[3], 1e-12)
    conf = int(min(100, 30 + expansion * 15 + contraction * 15))

    if conf < MIN_CONFIDENCE:
        return result

    result.update({"detected": True, "direction": pat_dir, "confidence": conf})
    return result


# ---------------------------------------------------------------------------
# 11. Island Reversal
# ---------------------------------------------------------------------------

def detect_island_reversal(
    df: pd.DataFrame,
    direction: str,
    lookback: int = 30,
    gap_atr_mult: float = 0.8,
) -> dict:
    """Detect island reversal -- sharp move, flat consolidation, sharp reversal.

    In crypto (no true gaps): a bar with body > gap_atr_mult * ATR, followed
    by 2-5 flat bars, then a bar moving opposite direction > gap_atr_mult * ATR.
    """
    result = {"detected": False, "direction": "neutral", "confidence": 0}

    if df is None or df.empty or len(df) < lookback:
        return result

    atr = _atr_14(df)
    if atr <= 0:
        return result

    window = df.tail(lookback)
    closes = window["close"].values.astype(float)
    opens = window["open"].values.astype(float)

    gap_thresh = gap_atr_mult * atr

    # Scan for impulse-flat-reversal
    for i in range(len(closes) - 6, max(0, len(closes) - 20), -1):
        body1 = closes[i] - opens[i]
        if abs(body1) < gap_thresh:
            continue

        # Check 2-5 flat bars after impulse
        for flat_len in range(2, min(6, len(closes) - i - 1)):
            flat_slice = closes[i + 1:i + 1 + flat_len]
            flat_range = float(flat_slice.max() - flat_slice.min())
            if flat_range > atr * 0.5:
                break

            rev_idx = i + 1 + flat_len
            if rev_idx >= len(closes):
                continue
            body2 = closes[rev_idx] - opens[rev_idx]
            if abs(body2) < gap_thresh:
                continue

            # Opposite direction
            if body1 > 0 and body2 > 0:
                continue
            if body1 < 0 and body2 < 0:
                continue

            pat_dir = "bearish" if body1 > 0 else "bullish"
            if direction == "long" and pat_dir == "bearish":
                continue
            if direction == "short" and pat_dir == "bullish":
                continue

            strength = (abs(body1) + abs(body2)) / (2 * atr)
            conf = int(min(100, 40 + strength * 20 + (1 - flat_range / atr) * 20))
            if conf < MIN_CONFIDENCE:
                continue

            result.update({"detected": True, "direction": pat_dir, "confidence": conf})
            return result

    return result


# ---------------------------------------------------------------------------
# 12. Pipe Top / Bottom
# ---------------------------------------------------------------------------

def detect_pipe(
    df: pd.DataFrame,
    direction: str,
    body_atr_mult: float = 2.0,
) -> dict:
    """Detect pipe pattern -- two adjacent tall candles, first one direction,
    second opposite.  Pipe top: up then down (bearish).  Pipe bottom: down
    then up (bullish)."""
    result = {"detected": False, "direction": "neutral", "confidence": 0}

    if df is None or df.empty or len(df) < 16:
        return result

    atr = _atr_14(df)
    if atr <= 0:
        return result

    thresh = body_atr_mult * atr

    # Check last few bar pairs
    for offset in range(0, min(5, len(df) - 1)):
        idx = len(df) - 2 - offset
        if idx < 0:
            break

        c1 = df.iloc[idx]
        c2 = df.iloc[idx + 1]
        body1 = float(c1["close"] - c1["open"])
        body2 = float(c2["close"] - c2["open"])

        if abs(body1) < thresh or abs(body2) < thresh:
            continue
        if body1 * body2 >= 0:
            continue  # same direction

        if body1 > 0 and body2 < 0:
            pat_dir = "bearish"  # pipe top
        else:
            pat_dir = "bullish"  # pipe bottom

        if direction == "long" and pat_dir == "bearish":
            continue
        if direction == "short" and pat_dir == "bullish":
            continue

        strength = (abs(body1) + abs(body2)) / (2 * atr)
        conf = int(min(100, 40 + strength * 15))
        if conf < MIN_CONFIDENCE:
            continue

        result.update({"detected": True, "direction": pat_dir, "confidence": conf})
        return result

    return result


# ---------------------------------------------------------------------------
# 13. Failure Swing
# ---------------------------------------------------------------------------

def detect_failure_swing(
    df: pd.DataFrame,
    direction: str,
    lookback: int = 60,
) -> dict:
    """Detect failure swing -- new high/low, reversal, then failed second push.

    Bullish failure swing: lower low, rally, higher low (failed to make new low).
    Bearish failure swing: higher high, pullback, lower high (failed new high).
    """
    result = {"detected": False, "direction": "neutral", "confidence": 0}

    if df is None or df.empty or len(df) < lookback:
        return result

    window = df.tail(lookback)
    highs = window["high"].values.astype(float)
    lows = window["low"].values.astype(float)

    sh = _swing_highs(highs, order=3)
    sl = _swing_lows(lows, order=3)

    atr = _atr_14(df)
    if atr <= 0:
        return result

    # Bearish: need >=2 swing highs, second lower than first
    if direction == "short" and len(sh) >= 2:
        h1_idx, h1 = sh[-2]
        h2_idx, h2 = sh[-1]
        if h2 < h1 and h2_idx > h1_idx and (h1 - h2) > atr * 0.3:
            pct_fail = (h1 - h2) / atr
            conf = int(min(100, 45 + pct_fail * 20))
            if conf >= MIN_CONFIDENCE:
                result.update({"detected": True, "direction": "bearish", "confidence": conf})
                return result

    # Bullish: need >=2 swing lows, second higher than first
    if direction == "long" and len(sl) >= 2:
        l1_idx, l1 = sl[-2]
        l2_idx, l2 = sl[-1]
        if l2 > l1 and l2_idx > l1_idx and (l2 - l1) > atr * 0.3:
            pct_fail = (l2 - l1) / atr
            conf = int(min(100, 45 + pct_fail * 20))
            if conf >= MIN_CONFIDENCE:
                result.update({"detected": True, "direction": "bullish", "confidence": conf})
                return result

    return result


# ---------------------------------------------------------------------------
# 14. Pennant (distinct from flag -- converging sides)
# ---------------------------------------------------------------------------

def detect_pennant(
    df: pd.DataFrame,
    direction: str,
    pole_bars: int = 8,
    pennant_bars: int = 12,
    min_pole_atr: float = 2.0,
) -> dict:
    """Detect pennant -- sharp impulse then small symmetrical triangle.

    Unlike flag (parallel channel), pennant has converging trendlines
    (highs descending AND lows ascending within the consolidation).
    """
    result = {"detected": False, "direction": "neutral", "confidence": 0}

    need = pole_bars + pennant_bars + 20
    if df is None or df.empty or len(df) < need:
        return result

    atr = _atr_14(df)
    if atr <= 0:
        return result

    for plen in range(4, pennant_bars + 1):
        pole_end = len(df) - plen
        pole_start = max(0, pole_end - pole_bars)
        if pole_start >= pole_end:
            continue

        pole_slice = df.iloc[pole_start:pole_end + 1]
        pen_slice = df.iloc[pole_end:len(df)]

        if len(pen_slice) < 4:
            continue

        pole_move = float(pole_slice["high"].max() - pole_slice["low"].min())
        pole_dir = float(pole_slice.iloc[-1]["close"] - pole_slice.iloc[0]["close"])
        if pole_move < min_pole_atr * atr or abs(pole_dir) < pole_move * 0.5:
            continue

        pen_highs = pen_slice["high"].values.astype(float)
        pen_lows = pen_slice["low"].values.astype(float)

        # Converging: highs decreasing, lows increasing
        h_slope = np.polyfit(range(len(pen_highs)), pen_highs, 1)[0]
        l_slope = np.polyfit(range(len(pen_lows)), pen_lows, 1)[0]

        if not (h_slope < 0 and l_slope > 0):
            continue  # not converging

        pen_range = float(pen_highs.max() - pen_lows.min())
        if pen_range > pole_move * 0.45:
            continue

        pat_dir = "bullish" if pole_dir > 0 else "bearish"
        if direction == "long" and pat_dir == "bearish":
            continue
        if direction == "short" and pat_dir == "bullish":
            continue

        convergence = abs(h_slope) + abs(l_slope)
        tightness = 1.0 - (pen_range / pole_move)
        conf = int(min(100, tightness * 50 + min(convergence / atr * 200, 50)))
        if conf < MIN_CONFIDENCE:
            continue

        result.update({"detected": True, "direction": pat_dir, "confidence": conf})
        return result

    return result


# ---------------------------------------------------------------------------
# 15. Measured Move / AB=CD
# ---------------------------------------------------------------------------

def detect_measured_move(
    df: pd.DataFrame,
    direction: str,
    lookback: int = 80,
    tolerance: float = 0.20,
) -> dict:
    """Detect measured move -- two equal-length impulse legs with correction.

    AB=CD pattern: leg AB, correction BC, then CD ≈ AB in length (within
    ``tolerance``).  Direction based on whether CD completes up or down.
    """
    result = {"detected": False, "direction": "neutral", "confidence": 0}

    if df is None or df.empty or len(df) < lookback:
        return result

    window = df.tail(lookback)
    highs = window["high"].values.astype(float)
    lows = window["low"].values.astype(float)

    sh = _swing_highs(highs, order=3)
    sl = _swing_lows(lows, order=3)

    # Combine and sort all pivots
    pivots = [(idx, val, "H") for idx, val in sh] + [(idx, val, "L") for idx, val in sl]
    pivots.sort(key=lambda x: x[0])

    if len(pivots) < 4:
        return result

    # Check last 4 alternating pivots for ABCD
    for i in range(len(pivots) - 3):
        a_idx, a_val, a_type = pivots[i]
        b_idx, b_val, b_type = pivots[i + 1]
        c_idx, c_val, c_type = pivots[i + 2]
        d_idx, d_val, d_type = pivots[i + 3]

        if a_type == b_type or b_type == c_type or c_type == d_type:
            continue  # must alternate

        leg_ab = abs(b_val - a_val)
        leg_cd = abs(d_val - c_val)

        if leg_ab <= 0:
            continue

        ratio = leg_cd / leg_ab
        if abs(ratio - 1.0) > tolerance:
            continue

        # D should be recent (within last 30% of window)
        if d_idx < len(highs) * 0.7:
            continue

        # Direction: if D is a low, bullish (expecting up); if high, bearish
        pat_dir = "bullish" if d_type == "L" else "bearish"
        if direction == "long" and pat_dir == "bearish":
            continue
        if direction == "short" and pat_dir == "bullish":
            continue

        symmetry = 1.0 - abs(ratio - 1.0)
        conf = int(min(100, symmetry * 70 + 30))
        if conf < MIN_CONFIDENCE:
            continue

        result.update({"detected": True, "direction": pat_dir, "confidence": conf})
        return result

    return result


# ---------------------------------------------------------------------------
# 16. Ascending Scallop
# ---------------------------------------------------------------------------

def detect_ascending_scallop(
    df: pd.DataFrame,
    direction: str,
    lookback: int = 60,
) -> dict:
    """Detect ascending scallop -- series of rounded bottoms trending higher.

    Each swing low higher than prior, forming scoop-like shapes.
    Bullish continuation pattern.
    """
    result = {"detected": False, "direction": "neutral", "confidence": 0}

    if df is None or df.empty or len(df) < lookback:
        return result

    if direction == "short":
        return result  # ascending scallop is bullish only

    window = df.tail(lookback)
    lows = window["low"].values.astype(float)
    sl = _swing_lows(lows, order=3)

    if len(sl) < 3:
        return result

    # All swing lows must be ascending
    recent = sl[-3:]
    ascending = all(recent[i + 1][1] > recent[i][1] for i in range(len(recent) - 1))
    if not ascending:
        return result

    atr = _atr_14(df)
    if atr <= 0:
        return result

    # Each step should be meaningful (> 0.3 ATR)
    steps = [recent[i + 1][1] - recent[i][1] for i in range(len(recent) - 1)]
    if any(s < atr * 0.3 for s in steps):
        return result

    avg_step = sum(steps) / len(steps)
    regularity = 1.0 - (max(steps) - min(steps)) / max(avg_step, 1e-12)
    conf = int(min(100, 40 + max(regularity, 0) * 30 + len(recent) * 10))
    if conf < MIN_CONFIDENCE:
        return result

    result.update({"detected": True, "direction": "bullish", "confidence": conf})
    return result


# ---------------------------------------------------------------------------
# 17. Descending Scallop
# ---------------------------------------------------------------------------

def detect_descending_scallop(
    df: pd.DataFrame,
    direction: str,
    lookback: int = 60,
) -> dict:
    """Detect descending scallop -- series of rounded tops trending lower.

    Each swing high lower than prior.  Bearish continuation pattern.
    """
    result = {"detected": False, "direction": "neutral", "confidence": 0}

    if df is None or df.empty or len(df) < lookback:
        return result

    if direction == "long":
        return result  # descending scallop is bearish only

    window = df.tail(lookback)
    highs = window["high"].values.astype(float)
    sh = _swing_highs(highs, order=3)

    if len(sh) < 3:
        return result

    recent = sh[-3:]
    descending = all(recent[i + 1][1] < recent[i][1] for i in range(len(recent) - 1))
    if not descending:
        return result

    atr = _atr_14(df)
    if atr <= 0:
        return result

    steps = [recent[i][1] - recent[i + 1][1] for i in range(len(recent) - 1)]
    if any(s < atr * 0.3 for s in steps):
        return result

    avg_step = sum(steps) / len(steps)
    regularity = 1.0 - (max(steps) - min(steps)) / max(avg_step, 1e-12)
    conf = int(min(100, 40 + max(regularity, 0) * 30 + len(recent) * 10))
    if conf < MIN_CONFIDENCE:
        return result

    result.update({"detected": True, "direction": "bearish", "confidence": conf})
    return result


# ---------------------------------------------------------------------------
# 18. Broadening / Megaphone
# ---------------------------------------------------------------------------

def detect_broadening(
    df: pd.DataFrame,
    direction: str,
    lookback: int = 50,
) -> dict:
    """Detect broadening (megaphone) pattern -- expanding range with higher
    highs AND lower lows.  Usually bearish at tops, bullish at bottoms."""
    result = {"detected": False, "direction": "neutral", "confidence": 0}

    if df is None or df.empty or len(df) < lookback:
        return result

    window = df.tail(lookback)
    highs = window["high"].values.astype(float)
    lows = window["low"].values.astype(float)

    sh = _swing_highs(highs, order=3)
    sl = _swing_lows(lows, order=3)

    if len(sh) < 2 or len(sl) < 2:
        return result

    # Highs expanding (each higher than prior)
    highs_expanding = all(sh[i + 1][1] > sh[i][1] for i in range(len(sh) - 1))
    # Lows expanding (each lower than prior)
    lows_expanding = all(sl[i + 1][1] < sl[i][1] for i in range(len(sl) - 1))

    if not (highs_expanding and lows_expanding):
        return result

    # Typically bearish (volatile tops)
    cur = float(df.iloc[-1]["close"])
    mid = (highs[-1] + lows[-1]) / 2 if len(highs) > 0 else cur
    pat_dir = "bearish" if cur > mid else "bullish"

    if direction == "long" and pat_dir == "bearish":
        return result
    if direction == "short" and pat_dir == "bullish":
        return result

    atr = _atr_14(df)
    if atr <= 0:
        return result

    expansion = (sh[-1][1] - sh[0][1]) + (sl[0][1] - sl[-1][1])
    conf = int(min(100, 45 + (expansion / atr) * 10))
    if conf < MIN_CONFIDENCE:
        return result

    result.update({"detected": True, "direction": pat_dir, "confidence": conf})
    return result


# ---------------------------------------------------------------------------
# 19. Bump and Run
# ---------------------------------------------------------------------------

def detect_bump_and_run(
    df: pd.DataFrame,
    direction: str,
    lookback: int = 60,
) -> dict:
    """Detect bump and run reversal -- steep advance (bump) then breakdown.

    Compare slope of first half (lead-in) vs second half (bump).  If bump
    slope is >2x lead-in slope and price now breaking below lead-in trend,
    it is a bearish bump-and-run.  Reverse for bullish.
    """
    result = {"detected": False, "direction": "neutral", "confidence": 0}

    if df is None or df.empty or len(df) < lookback:
        return result

    window = df.tail(lookback)
    closes = window["close"].values.astype(float)
    n = len(closes)
    half = n // 2

    x1 = np.arange(half)
    x2 = np.arange(half, n)

    lead_slope = np.polyfit(x1, closes[:half], 1)[0]
    bump_slope = np.polyfit(np.arange(len(closes[half:])), closes[half:], 1)[0]

    atr = _atr_14(df)
    if atr <= 0:
        return result

    # Bearish: steep up bump, price now falling back
    if direction == "short" and bump_slope > 0 and lead_slope > 0:
        ratio = bump_slope / max(lead_slope, 1e-12)
        if ratio > 2.0:
            # Price should be declining from peak
            peak = float(closes[half:].max())
            cur = float(closes[-1])
            if (peak - cur) > atr * 0.5:
                conf = int(min(100, 40 + ratio * 10 + (peak - cur) / atr * 10))
                if conf >= MIN_CONFIDENCE:
                    result.update({"detected": True, "direction": "bearish", "confidence": conf})
                    return result

    # Bullish: steep down bump, price now recovering
    if direction == "long" and bump_slope < 0 and lead_slope < 0:
        ratio = bump_slope / min(lead_slope, -1e-12)
        if ratio > 2.0:
            trough = float(closes[half:].min())
            cur = float(closes[-1])
            if (cur - trough) > atr * 0.5:
                conf = int(min(100, 40 + ratio * 10 + (cur - trough) / atr * 10))
                if conf >= MIN_CONFIDENCE:
                    result.update({"detected": True, "direction": "bullish", "confidence": conf})
                    return result

    return result


# ---------------------------------------------------------------------------
# 20. Order Block (ICT / Smart Money)
# ---------------------------------------------------------------------------

def detect_order_block(
    df: pd.DataFrame,
    direction: str,
    lookback: int = 30,
    impulse_atr_mult: float = 2.0,
) -> dict:
    """Detect order block -- last opposite candle before strong impulsive move.

    Bullish OB: last bearish candle before a bullish impulse (>2 ATR).
    Bearish OB: last bullish candle before a bearish impulse (>2 ATR).
    Price must be near the OB zone for a re-test signal.
    """
    result = {"detected": False, "direction": "neutral", "ob_high": 0.0,
              "ob_low": 0.0, "confidence": 0}

    if df is None or df.empty or len(df) < lookback:
        return result

    atr = _atr_14(df)
    if atr <= 0:
        return result

    thresh = impulse_atr_mult * atr
    cur = float(df.iloc[-1]["close"])

    # Scan recent bars for impulse moves
    for i in range(len(df) - 2, max(len(df) - lookback, 1), -1):
        impulse_body = float(df.iloc[i]["close"] - df.iloc[i]["open"])
        if abs(impulse_body) < thresh:
            continue

        # Find last opposite candle before impulse
        ob_idx = i - 1
        if ob_idx < 0:
            continue

        ob_body = float(df.iloc[ob_idx]["close"] - df.iloc[ob_idx]["open"])

        if impulse_body > 0 and ob_body < 0:
            # Bullish OB: bearish candle before bullish impulse
            if direction == "short":
                continue
            ob_high = float(df.iloc[ob_idx]["high"])
            ob_low = float(df.iloc[ob_idx]["low"])
            # Price should be near OB zone (within 1 ATR)
            if cur < ob_low - atr or cur > ob_high + atr:
                continue
            pat_dir = "bullish"
        elif impulse_body < 0 and ob_body > 0:
            # Bearish OB: bullish candle before bearish impulse
            if direction == "long":
                continue
            ob_high = float(df.iloc[ob_idx]["high"])
            ob_low = float(df.iloc[ob_idx]["low"])
            if cur < ob_low - atr or cur > ob_high + atr:
                continue
            pat_dir = "bearish"
        else:
            continue

        proximity = 1.0 - min(abs(cur - (ob_high + ob_low) / 2) / atr, 1.0)
        impulse_str = min(abs(impulse_body) / atr, 4.0) / 4.0
        conf = int(min(100, proximity * 50 + impulse_str * 50))
        if conf < MIN_CONFIDENCE:
            continue

        result.update({"detected": True, "direction": pat_dir,
                       "ob_high": round(ob_high, 6), "ob_low": round(ob_low, 6),
                       "confidence": conf})
        return result

    return result


# ---------------------------------------------------------------------------
# 21. Fair Value Gap (ICT)
# ---------------------------------------------------------------------------

def detect_fair_value_gap(
    df: pd.DataFrame,
    direction: str,
    lookback: int = 20,
) -> dict:
    """Detect fair value gap -- 3-candle imbalance.

    Bullish FVG: candle_1_high < candle_3_low (gap up).
    Bearish FVG: candle_1_low > candle_3_high (gap down).
    Price returning to fill the gap signals an entry.
    """
    result = {"detected": False, "direction": "neutral", "gap_high": 0.0,
              "gap_low": 0.0, "confidence": 0}

    if df is None or df.empty or len(df) < lookback:
        return result

    atr = _atr_14(df)
    if atr <= 0:
        return result

    cur = float(df.iloc[-1]["close"])

    # Scan recent completed triplets
    for i in range(len(df) - 3, max(len(df) - lookback, 0), -1):
        c1_high = float(df.iloc[i]["high"])
        c1_low = float(df.iloc[i]["low"])
        c3_high = float(df.iloc[i + 2]["high"])
        c3_low = float(df.iloc[i + 2]["low"])

        # Bullish FVG
        if c1_high < c3_low and direction != "short":
            gap_size = c3_low - c1_high
            if gap_size < atr * 0.3:
                continue
            # Price near gap zone?
            if cur > c3_low + atr or cur < c1_high - atr:
                continue
            proximity = 1.0 - min(abs(cur - (c1_high + c3_low) / 2) / gap_size, 1.5)
            conf = int(min(100, 40 + max(proximity, 0) * 30 + gap_size / atr * 20))
            if conf >= MIN_CONFIDENCE:
                result.update({"detected": True, "direction": "bullish",
                               "gap_high": round(c3_low, 6), "gap_low": round(c1_high, 6),
                               "confidence": conf})
                return result

        # Bearish FVG
        if c1_low > c3_high and direction != "long":
            gap_size = c1_low - c3_high
            if gap_size < atr * 0.3:
                continue
            if cur < c3_high - atr or cur > c1_low + atr:
                continue
            proximity = 1.0 - min(abs(cur - (c3_high + c1_low) / 2) / gap_size, 1.5)
            conf = int(min(100, 40 + max(proximity, 0) * 30 + gap_size / atr * 20))
            if conf >= MIN_CONFIDENCE:
                result.update({"detected": True, "direction": "bearish",
                               "gap_high": round(c1_low, 6), "gap_low": round(c3_high, 6),
                               "confidence": conf})
                return result

    return result


# ---------------------------------------------------------------------------
# 22. Breaker Block (ICT)
# ---------------------------------------------------------------------------

def detect_breaker_block(
    df: pd.DataFrame,
    direction: str,
    lookback: int = 40,
) -> dict:
    """Detect breaker block -- a broken order block that gets reclaimed.

    Bullish breaker: bearish OB swept to downside, price then reclaims above.
    Bearish breaker: bullish OB swept to upside, price then reclaims below.
    """
    result = {"detected": False, "direction": "neutral", "confidence": 0}

    if df is None or df.empty or len(df) < lookback:
        return result

    atr = _atr_14(df)
    if atr <= 0:
        return result

    cur = float(df.iloc[-1]["close"])
    thresh = 1.5 * atr

    for i in range(len(df) - 5, max(len(df) - lookback, 1), -1):
        ob_body = float(df.iloc[i]["close"] - df.iloc[i]["open"])
        if abs(ob_body) < atr * 0.5:
            continue

        ob_high = float(df.iloc[i]["high"])
        ob_low = float(df.iloc[i]["low"])

        # Check if OB was swept then reclaimed
        post = df.iloc[i + 1:]
        if len(post) < 3:
            continue

        post_lows = post["low"].values.astype(float)
        post_highs = post["high"].values.astype(float)

        # Bullish breaker: bearish candle, price swept below, then reclaimed above
        if ob_body < 0 and direction != "short":
            swept = float(post_lows.min()) < ob_low
            reclaimed = cur > ob_high
            if swept and reclaimed:
                sweep_depth = ob_low - float(post_lows.min())
                conf = int(min(100, 45 + sweep_depth / atr * 15 + 10))
                if conf >= MIN_CONFIDENCE:
                    result.update({"detected": True, "direction": "bullish", "confidence": conf})
                    return result

        # Bearish breaker: bullish candle, price swept above, then reclaimed below
        if ob_body > 0 and direction != "long":
            swept = float(post_highs.max()) > ob_high
            reclaimed = cur < ob_low
            if swept and reclaimed:
                sweep_depth = float(post_highs.max()) - ob_high
                conf = int(min(100, 45 + sweep_depth / atr * 15 + 10))
                if conf >= MIN_CONFIDENCE:
                    result.update({"detected": True, "direction": "bearish", "confidence": conf})
                    return result

    return result


# ---------------------------------------------------------------------------
# 23. Market Structure Shift (BOS)
# ---------------------------------------------------------------------------

def detect_market_structure_shift(
    df: pd.DataFrame,
    direction: str,
    lookback: int = 50,
) -> dict:
    """Detect market structure shift -- break of structure (BOS).

    Bullish MSS: price breaks above recent swing high after a downtrend.
    Bearish MSS: price breaks below recent swing low after an uptrend.
    """
    result = {"detected": False, "direction": "neutral", "confidence": 0}

    if df is None or df.empty or len(df) < lookback:
        return result

    window = df.tail(lookback)
    highs = window["high"].values.astype(float)
    lows = window["low"].values.astype(float)
    closes = window["close"].values.astype(float)

    sh = _swing_highs(highs, order=3)
    sl = _swing_lows(lows, order=3)

    atr = _atr_14(df)
    if atr <= 0:
        return result

    cur = float(closes[-1])

    # Bullish MSS: downtrend (lower lows), then break above last swing high
    if direction != "short" and len(sl) >= 2 and len(sh) >= 1:
        downtrend = sl[-1][1] < sl[-2][1]  # lower lows
        if downtrend and cur > sh[-1][1]:
            break_dist = (cur - sh[-1][1]) / atr
            conf = int(min(100, 50 + break_dist * 20))
            if conf >= MIN_CONFIDENCE:
                result.update({"detected": True, "direction": "bullish", "confidence": conf})
                return result

    # Bearish MSS: uptrend (higher highs), then break below last swing low
    if direction != "long" and len(sh) >= 2 and len(sl) >= 1:
        uptrend = sh[-1][1] > sh[-2][1]  # higher highs
        if uptrend and cur < sl[-1][1]:
            break_dist = (sl[-1][1] - cur) / atr
            conf = int(min(100, 50 + break_dist * 20))
            if conf >= MIN_CONFIDENCE:
                result.update({"detected": True, "direction": "bearish", "confidence": conf})
                return result

    return result


# ---------------------------------------------------------------------------
# 24. Harmonic AB=CD
# ---------------------------------------------------------------------------

def detect_harmonic_abcd(
    df: pd.DataFrame,
    direction: str,
    lookback: int = 80,
    tolerance: float = 0.25,
) -> dict:
    """Detect harmonic AB=CD -- swing-based legs with roughly equal length.

    Uses swing points.  AB and CD legs should be within ``tolerance`` of
    each other.  BC retracement should be 38-78% of AB (Fibonacci zone).
    """
    result = {"detected": False, "direction": "neutral", "ab_cd_ratio": 0.0,
              "confidence": 0}

    if df is None or df.empty or len(df) < lookback:
        return result

    window = df.tail(lookback)
    highs = window["high"].values.astype(float)
    lows = window["low"].values.astype(float)

    sh = _swing_highs(highs, order=3)
    sl = _swing_lows(lows, order=3)

    pivots = [(idx, val, "H") for idx, val in sh] + [(idx, val, "L") for idx, val in sl]
    pivots.sort(key=lambda x: x[0])

    if len(pivots) < 4:
        return result

    # Check last 4 pivots
    for i in range(len(pivots) - 3):
        a_idx, a_val, a_type = pivots[i]
        b_idx, b_val, b_type = pivots[i + 1]
        c_idx, c_val, c_type = pivots[i + 2]
        d_idx, d_val, d_type = pivots[i + 3]

        if a_type == b_type or b_type == c_type or c_type == d_type:
            continue

        leg_ab = abs(b_val - a_val)
        leg_bc = abs(c_val - b_val)
        leg_cd = abs(d_val - c_val)

        if leg_ab <= 0:
            continue

        ratio = leg_cd / leg_ab
        if abs(ratio - 1.0) > tolerance:
            continue

        # BC retracement check (38-78% of AB)
        bc_retrace = leg_bc / leg_ab
        if bc_retrace < 0.38 or bc_retrace > 0.78:
            continue

        # D should be recent
        if d_idx < len(highs) * 0.7:
            continue

        pat_dir = "bullish" if d_type == "L" else "bearish"
        if direction == "long" and pat_dir == "bearish":
            continue
        if direction == "short" and pat_dir == "bullish":
            continue

        symmetry = 1.0 - abs(ratio - 1.0)
        fib_score = 1.0 - abs(bc_retrace - 0.618) / 0.382
        conf = int(min(100, symmetry * 50 + max(fib_score, 0) * 30 + 20))
        if conf < MIN_CONFIDENCE:
            continue

        result.update({"detected": True, "direction": pat_dir,
                       "ab_cd_ratio": round(ratio, 3), "confidence": conf})
        return result

    return result


# ---------------------------------------------------------------------------
# 25. Channel Breakout (Regression)
# ---------------------------------------------------------------------------

def detect_channel_breakout(
    df: pd.DataFrame,
    direction: str,
    channel_bars: int = 30,
) -> dict:
    """Detect channel breakout -- price closing outside 2-sigma regression channel.

    Fit linear regression on last ``channel_bars``.  If current close is
    beyond 2 standard deviations, signal a breakout.
    """
    result = {"detected": False, "direction": "neutral", "confidence": 0}

    if df is None or df.empty or len(df) < channel_bars + 5:
        return result

    channel = df.iloc[-(channel_bars + 1):-1]
    closes = channel["close"].values.astype(float)
    x = np.arange(len(closes))

    coeffs = np.polyfit(x, closes, 1)
    fitted = np.polyval(coeffs, x)
    residuals = closes - fitted
    std = float(np.std(residuals))

    if std <= 0:
        return result

    # Project regression to current bar
    cur_x = len(closes)
    projected = float(np.polyval(coeffs, cur_x))
    cur_close = float(df.iloc[-1]["close"])
    deviation = (cur_close - projected) / std

    if direction != "short" and deviation > 2.0:
        conf = int(min(100, 40 + (deviation - 2.0) * 30))
        if conf >= MIN_CONFIDENCE:
            result.update({"detected": True, "direction": "bullish", "confidence": conf})
            return result

    if direction != "long" and deviation < -2.0:
        conf = int(min(100, 40 + (abs(deviation) - 2.0) * 30))
        if conf >= MIN_CONFIDENCE:
            result.update({"detected": True, "direction": "bearish", "confidence": conf})
            return result

    return result


# ---------------------------------------------------------------------------
# 26. Donchian Breakout
# ---------------------------------------------------------------------------

def detect_donchian_breakout(
    df: pd.DataFrame,
    direction: str,
    period: int = 20,
) -> dict:
    """Detect Donchian breakout -- price breaking above period-high or below
    period-low.  Classic trend-following signal."""
    result = {"detected": False, "direction": "neutral", "confidence": 0}

    if df is None or df.empty or len(df) < period + 2:
        return result

    channel = df.iloc[-(period + 1):-1]
    donchian_high = float(channel["high"].max())
    donchian_low = float(channel["low"].min())

    cur_close = float(df.iloc[-1]["close"])
    cur_high = float(df.iloc[-1]["high"])
    cur_low = float(df.iloc[-1]["low"])

    atr = _atr_14(df)
    if atr <= 0:
        return result

    # Bullish breakout
    if direction != "short" and cur_close > donchian_high:
        excess = (cur_close - donchian_high) / atr
        conf = int(min(100, 50 + excess * 25))
        if conf >= MIN_CONFIDENCE:
            result.update({"detected": True, "direction": "bullish", "confidence": conf})
            return result

    # Bearish breakout
    if direction != "long" and cur_close < donchian_low:
        excess = (donchian_low - cur_close) / atr
        conf = int(min(100, 50 + excess * 25))
        if conf >= MIN_CONFIDENCE:
            result.update({"detected": True, "direction": "bearish", "confidence": conf})
            return result

    return result


# ---------------------------------------------------------------------------
# 27. Keltner Squeeze
# ---------------------------------------------------------------------------

def detect_keltner_squeeze(
    df: pd.DataFrame,
    direction: str,
    bb_period: int = 20,
    kc_period: int = 20,
    kc_mult: float = 1.5,
) -> dict:
    """Detect Keltner squeeze -- Bollinger Bands inside Keltner Channel,
    then expansion.  Signals volatility explosion.

    Squeeze: BB width < KC width for recent bars.
    Expansion: BB breaks outside KC on current bar.
    Direction from momentum (close vs midline).
    """
    result = {"detected": False, "direction": "neutral", "confidence": 0}

    need = max(bb_period, kc_period) + 10
    if df is None or df.empty or len(df) < need:
        return result

    closes = df["close"].values.astype(float)
    highs = df["high"].values.astype(float)
    lows = df["low"].values.astype(float)

    # Bollinger Bands
    bb_ma = float(np.mean(closes[-bb_period:]))
    bb_std = float(np.std(closes[-bb_period:]))
    bb_upper = bb_ma + 2 * bb_std
    bb_lower = bb_ma - 2 * bb_std
    bb_width = bb_upper - bb_lower

    # Keltner Channel (using ATR)
    tr = np.maximum(highs[1:] - lows[1:],
                    np.maximum(np.abs(highs[1:] - closes[:-1]),
                               np.abs(lows[1:] - closes[:-1])))
    kc_atr = float(np.mean(tr[-kc_period:]))
    kc_ma = float(np.mean(closes[-kc_period:]))
    kc_upper = kc_ma + kc_mult * kc_atr
    kc_lower = kc_ma - kc_mult * kc_atr
    kc_width = kc_upper - kc_lower

    if kc_width <= 0 or bb_width <= 0:
        return result

    # Check if squeeze was active recently (BB inside KC)
    # Look back 3-8 bars for squeeze condition
    squeeze_count = 0
    for offset in range(2, min(9, len(closes) - bb_period)):
        idx = -offset
        past_closes = closes[idx - bb_period:idx]
        if len(past_closes) < bb_period:
            continue
        p_ma = float(np.mean(past_closes))
        p_std = float(np.std(past_closes))
        p_bb_upper = p_ma + 2 * p_std
        p_bb_lower = p_ma - 2 * p_std

        past_tr = tr[idx - kc_period:idx] if abs(idx) <= len(tr) else tr[-kc_period:]
        if len(past_tr) < 3:
            continue
        p_kc_atr = float(np.mean(past_tr))
        p_kc_upper = p_ma + kc_mult * p_kc_atr
        p_kc_lower = p_ma - kc_mult * p_kc_atr

        if p_bb_upper < p_kc_upper and p_bb_lower > p_kc_lower:
            squeeze_count += 1

    if squeeze_count < 2:
        return result

    # Current bar: BB should be expanding (outside KC)
    expanding = bb_upper > kc_upper or bb_lower < kc_lower
    if not expanding:
        return result

    # Direction from momentum
    cur = float(closes[-1])
    pat_dir = "bullish" if cur > bb_ma else "bearish"

    if direction == "long" and pat_dir == "bearish":
        return result
    if direction == "short" and pat_dir == "bullish":
        return result

    conf = int(min(100, 40 + squeeze_count * 10 + abs(cur - bb_ma) / max(kc_atr, 1e-12) * 15))
    if conf < MIN_CONFIDENCE:
        return result

    result.update({"detected": True, "direction": pat_dir, "confidence": conf})
    return result


# ---------------------------------------------------------------------------
# Unified interface
# ---------------------------------------------------------------------------

def detect_patterns(df: pd.DataFrame, direction: str) -> dict:
    """Run all pattern detectors and return unified result.

    Returns:
        dict with sub-dicts for each pattern type,
        plus any_detected, best_pattern, best_confidence.
    """
    flag = detect_flag(df, direction)
    cup = detect_cup_handle(df, direction)
    double = detect_double_pattern(df, direction)
    triangle = detect_triangle(df, direction)
    wedge = detect_wedge(df, direction)
    hs = detect_head_shoulders(df, direction)
    triple = detect_triple_pattern(df, direction)
    rectangle = detect_rectangle(df, direction)
    rounded = detect_rounded_reversal(df, direction)
    diamond = detect_diamond(df, direction)
    island = detect_island_reversal(df, direction)
    pipe = detect_pipe(df, direction)
    fail_swing = detect_failure_swing(df, direction)
    pennant = detect_pennant(df, direction)
    measured = detect_measured_move(df, direction)
    asc_scallop = detect_ascending_scallop(df, direction)
    desc_scallop = detect_descending_scallop(df, direction)
    broadening = detect_broadening(df, direction)
    bump_run = detect_bump_and_run(df, direction)
    order_block = detect_order_block(df, direction)
    fvg = detect_fair_value_gap(df, direction)
    breaker = detect_breaker_block(df, direction)
    mss = detect_market_structure_shift(df, direction)
    harmonic = detect_harmonic_abcd(df, direction)
    chan_break = detect_channel_breakout(df, direction)
    donchian = detect_donchian_breakout(df, direction)
    keltner = detect_keltner_squeeze(df, direction)

    patterns = {
        "flag": flag,
        "cup_handle": cup,
        "double_pattern": double,
        "triangle": triangle,
        "wedge": wedge,
        "head_shoulders": hs,
        "triple_pattern": triple,
        "rectangle": rectangle,
        "rounded_reversal": rounded,
        "diamond": diamond,
        "island_reversal": island,
        "pipe": pipe,
        "failure_swing": fail_swing,
        "pennant": pennant,
        "measured_move": measured,
        "ascending_scallop": asc_scallop,
        "descending_scallop": desc_scallop,
        "broadening": broadening,
        "bump_and_run": bump_run,
        "order_block": order_block,
        "fair_value_gap": fvg,
        "breaker_block": breaker,
        "market_structure_shift": mss,
        "harmonic_abcd": harmonic,
        "channel_breakout": chan_break,
        "donchian_breakout": donchian,
        "keltner_squeeze": keltner,
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
