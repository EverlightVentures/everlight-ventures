from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from indicators.atr import atr


def _find_swing_points(series: pd.Series, order: int = 3) -> List[int]:
    """Find local extrema indices using a simple rolling window comparison."""
    indices = []
    values = series.values
    n = len(values)
    for i in range(order, n - order):
        is_high = all(values[i] >= values[i - j] for j in range(1, order + 1)) and \
                  all(values[i] >= values[i + j] for j in range(1, order + 1))
        is_low = all(values[i] <= values[i - j] for j in range(1, order + 1)) and \
                 all(values[i] <= values[i + j] for j in range(1, order + 1))
        if is_high or is_low:
            indices.append(i)
    return indices


def _linreg(x: np.ndarray, y: np.ndarray) -> tuple:
    """Simple linear regression returning (slope, intercept, r_squared)."""
    n = len(x)
    if n < 2:
        return 0.0, 0.0, 0.0
    x_mean = np.mean(x)
    y_mean = np.mean(y)
    ss_xy = np.sum((x - x_mean) * (y - y_mean))
    ss_xx = np.sum((x - x_mean) ** 2)
    if ss_xx == 0:
        return 0.0, y_mean, 0.0
    slope = ss_xy / ss_xx
    intercept = y_mean - slope * x_mean
    y_pred = slope * x + intercept
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - y_mean) ** 2)
    r_sq = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
    return slope, intercept, r_sq


def detect_channel(df: pd.DataFrame, lookback: int = 40) -> Optional[Dict]:
    """Detect price channel from swing structure.

    Returns dict with: type (ascending/descending/horizontal),
    upper_slope, lower_slope, upper_at_now, lower_at_now,
    width_atr, position (upper/middle/lower).
    Returns None if no clear channel detected.
    """
    if df.empty or len(df) < 20:
        return None

    window = df.tail(min(lookback, len(df)))
    n = len(window)
    if n < 20:
        return None

    highs = window["high"].reset_index(drop=True)
    lows = window["low"].reset_index(drop=True)

    # Find swing highs and lows
    swing_high_idx = _find_swing_points(highs, order=2)
    swing_low_idx = _find_swing_points(lows, order=2)

    # Filter to actual highs/lows
    sh_idx = [i for i in swing_high_idx if highs.iloc[i] >= lows.iloc[i]]
    sl_idx = [i for i in swing_low_idx if lows.iloc[i] <= highs.iloc[i]]

    if len(sh_idx) < 2 or len(sl_idx) < 2:
        return None

    # Fit lines through swing highs and swing lows
    x_hi = np.array(sh_idx, dtype=float)
    y_hi = np.array([float(highs.iloc[i]) for i in sh_idx])
    slope_hi, intercept_hi, r2_hi = _linreg(x_hi, y_hi)

    x_lo = np.array(sl_idx, dtype=float)
    y_lo = np.array([float(lows.iloc[i]) for i in sl_idx])
    slope_lo, intercept_lo, r2_lo = _linreg(x_lo, y_lo)

    # Both lines need reasonable fit (R² > 0.3)
    if r2_hi < 0.3 or r2_lo < 0.3:
        return None

    # Slopes should be roughly parallel (within 2x of each other)
    if slope_hi != 0 and slope_lo != 0:
        ratio = slope_hi / slope_lo if slope_lo != 0 else 999
        if ratio < 0.3 or ratio > 3.0:
            return None  # Not parallel enough

    # Classify channel type
    avg_slope = (slope_hi + slope_lo) / 2
    price_now = float(window["close"].iloc[-1])
    slope_pct = avg_slope / price_now if price_now > 0 else 0

    if slope_pct > 0.0001:
        chan_type = "ascending"
    elif slope_pct < -0.0001:
        chan_type = "descending"
    else:
        chan_type = "horizontal"

    # Current channel boundaries
    upper_now = slope_hi * (n - 1) + intercept_hi
    lower_now = slope_lo * (n - 1) + intercept_lo

    if upper_now <= lower_now:
        return None  # Inverted channel, invalid

    # Width in ATR units
    atr_series = atr(window, 14)
    atr_val = float(atr_series.iloc[-1]) if not atr_series.empty and not pd.isna(atr_series.iloc[-1]) else 0.0
    width_atr = (upper_now - lower_now) / atr_val if atr_val > 0 else 0.0

    # Where is price within the channel?
    chan_range = upper_now - lower_now
    if chan_range > 0:
        position_pct = (price_now - lower_now) / chan_range
        if position_pct >= 0.75:
            position = "upper"
        elif position_pct <= 0.25:
            position = "lower"
        else:
            position = "middle"
    else:
        position = "middle"

    return {
        "type": chan_type,
        "upper_slope": slope_hi,
        "lower_slope": slope_lo,
        "upper_at_now": upper_now,
        "lower_at_now": lower_now,
        "width_atr": width_atr,
        "position": position,
        "position_pct": position_pct if chan_range > 0 else 0.5,
    }


def channel_confluence(channel: Optional[Dict], direction: str, price: float) -> Dict[str, bool]:
    """Return confluence flags from channel analysis.

    CHANNEL_SUPPORT: at lower channel + long, or at upper channel + short
    CHANNEL_RESISTANCE: (same, alias for scoring)
    CHANNEL_BREAKOUT: price breaking above ascending or below descending channel
    """
    flags = {
        "CHANNEL_SUPPORT": False,
        "CHANNEL_RESISTANCE": False,
        "CHANNEL_BREAKOUT": False,
    }
    if not channel:
        return flags

    pos = channel.get("position", "middle")
    chan_type = channel.get("type", "horizontal")
    upper = channel.get("upper_at_now", 0)
    lower = channel.get("lower_at_now", 0)

    # Support/resistance at channel boundaries
    if direction == "long" and pos == "lower":
        flags["CHANNEL_SUPPORT"] = True
    elif direction == "short" and pos == "upper":
        flags["CHANNEL_RESISTANCE"] = True

    # Breakout detection
    if direction == "long" and price > upper and chan_type == "ascending":
        flags["CHANNEL_BREAKOUT"] = True
    elif direction == "short" and price < lower and chan_type == "descending":
        flags["CHANNEL_BREAKOUT"] = True

    return flags
