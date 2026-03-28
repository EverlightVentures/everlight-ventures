"""Execution Intelligence Module -- legendary-level execution helpers.

Four functions that upgrade every trade the bot takes:

1. structure_based_tp  -- TP from real structure, not arbitrary ATR multiples
2. fade_the_extreme    -- counter-trend entries at RSI + wick zone confluence
3. session_open_detector -- volatility regime around major session opens
4. compute_r_multiple  -- R-based position management and scale-out logic

CONTRACT MATH REMINDER:
- 1 XLP contract = 5,000 XLM
- $0.01 move = $50/contract
- $0.001 move = $5/contract
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd

from indicators.atr import atr as compute_atr
from indicators.rsi import rsi as compute_rsi


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_swing_highs(highs: np.ndarray, order: int = 3) -> list[float]:
    """Find swing highs using rolling window comparison.

    A bar is a swing high if its high is greater than the `order` bars
    on both sides.
    """
    if highs is None or len(highs) < 2 * order + 1:
        return []
    swings: list[float] = []
    for i in range(order, len(highs) - order):
        window_left = highs[i - order : i]
        window_right = highs[i + 1 : i + order + 1]
        if np.all(highs[i] > window_left) and np.all(highs[i] > window_right):
            swings.append(float(highs[i]))
    return swings


def _find_swing_lows(lows: np.ndarray, order: int = 3) -> list[float]:
    """Find swing lows -- mirror of swing highs."""
    if lows is None or len(lows) < 2 * order + 1:
        return []
    swings: list[float] = []
    for i in range(order, len(lows) - order):
        window_left = lows[i - order : i]
        window_right = lows[i + 1 : i + order + 1]
        if np.all(lows[i] < window_left) and np.all(lows[i] < window_right):
            swings.append(float(lows[i]))
    return swings


def _bollinger_bands(closes: pd.Series, length: int = 20, mult: float = 2.0) -> tuple[pd.Series, pd.Series]:
    """Return (upper_band, lower_band) Bollinger Bands."""
    sma = closes.rolling(length).mean()
    std = closes.rolling(length).std()
    return sma + mult * std, sma - mult * std


def _fib_extensions(swing_low: float, swing_high: float, direction: str) -> dict[str, float]:
    """Compute fib extension levels from a swing range.

    For LONG: extensions project above the swing high.
    For SHORT: extensions project below the swing low.
    """
    span = swing_high - swing_low
    if span <= 0:
        return {}
    if direction == "long":
        return {
            "fib_1.0": swing_low + span * 1.0,
            "fib_1.272": swing_low + span * 1.272,
            "fib_1.618": swing_low + span * 1.618,
        }
    else:
        return {
            "fib_1.0": swing_high - span * 1.0,
            "fib_1.272": swing_high - span * 1.272,
            "fib_1.618": swing_high - span * 1.618,
        }


# ---------------------------------------------------------------------------
# Function 1: Structure-Based Take-Profit
# ---------------------------------------------------------------------------

def structure_based_tp(
    df_15m: pd.DataFrame | None,
    df_1h: pd.DataFrame | None,
    direction: str,
    entry_price: float,
    atr_val: float,
    levels: dict[str, Any] | None = None,
    fibs: dict[str, float] | None = None,
) -> dict:
    """Compute TP from the nearest structural level.

    Scans swing highs/lows, fib extensions, Bollinger bands, and
    externally-provided levels to find a real structural target.
    Falls back to 2.5 ATR if nothing structural within 5 ATR.

    Args:
        df_15m: 15-minute OHLCV DataFrame (needs high, low, close).
        df_1h:  1-hour OHLCV DataFrame.
        direction: "long" or "short".
        entry_price: Trade entry price.
        atr_val: Current ATR value (float, same unit as price).
        levels: Optional dict with "resistance" and/or "support" lists.
        fibs: Optional dict of pre-computed fib levels (key -> price).

    Returns:
        Dict with tp_price, tp_source, distance_atr, rr_ratio.
    """
    fallback = {
        "tp_price": round(entry_price + (2.5 * atr_val if direction == "long" else -2.5 * atr_val), 6),
        "tp_source": "atr_fallback",
        "distance_atr": 2.5,
        "rr_ratio": 2.5 / 1.5,
    }

    if atr_val <= 0:
        return fallback

    stop_distance = 1.5 * atr_val
    min_tp_distance = 1.5 * stop_distance  # 1.5:1 R:R minimum
    max_tp_distance = 5.0 * atr_val

    # Collect all candidate target levels with source labels
    candidates: list[tuple[float, str]] = []

    # -- Swing highs/lows from 15m --
    if df_15m is not None and len(df_15m) >= 10:
        tail_15m = df_15m.tail(50)
        if direction == "long":
            for sh in _find_swing_highs(tail_15m["high"].values, order=3):
                candidates.append((sh, "swing_high"))
        else:
            for sl in _find_swing_lows(tail_15m["low"].values, order=3):
                candidates.append((sl, "swing_low"))

    # -- Swing highs/lows from 1h --
    if df_1h is not None and len(df_1h) >= 10:
        tail_1h = df_1h.tail(50)
        if direction == "long":
            for sh in _find_swing_highs(tail_1h["high"].values, order=3):
                candidates.append((sh, "swing_high_1h"))
        else:
            for sl in _find_swing_lows(tail_1h["low"].values, order=3):
                candidates.append((sl, "swing_low_1h"))

    # -- Fib extensions from last swing on 15m --
    if df_15m is not None and len(df_15m) >= 20:
        tail = df_15m.tail(50)
        swing_highs = _find_swing_highs(tail["high"].values, order=3)
        swing_lows = _find_swing_lows(tail["low"].values, order=3)
        if swing_highs and swing_lows:
            last_high = swing_highs[-1]
            last_low = swing_lows[-1]
            fib_levels = _fib_extensions(last_low, last_high, direction)
            for label, price in fib_levels.items():
                candidates.append((price, label))

    # -- Externally provided fibs --
    if fibs:
        for label, price in fibs.items():
            candidates.append((float(price), str(label)))

    # -- Externally provided levels --
    if levels:
        if direction == "long":
            for r in levels.get("resistance", []):
                candidates.append((float(r), "level_resistance"))
        else:
            for s in levels.get("support", []):
                candidates.append((float(s), "level_support"))

    # -- Bollinger bands from 15m --
    if df_15m is not None and len(df_15m) >= 22:
        bb_upper, bb_lower = _bollinger_bands(df_15m["close"])
        if direction == "long" and not bb_upper.empty:
            last_bb = float(bb_upper.iloc[-1])
            if not np.isnan(last_bb):
                candidates.append((last_bb, "bb_upper"))
        elif direction == "short" and not bb_lower.empty:
            last_bb = float(bb_lower.iloc[-1])
            if not np.isnan(last_bb):
                candidates.append((last_bb, "bb_lower"))

    # -- Filter candidates by direction and distance --
    valid: list[tuple[float, str, float]] = []
    for price, source in candidates:
        if direction == "long":
            dist = price - entry_price
        else:
            dist = entry_price - price

        if dist < min_tp_distance:
            continue  # too close -- below 1.5:1 R:R
        if dist > max_tp_distance:
            continue  # too far -- beyond 5 ATR

        valid.append((price, source, dist))

    if not valid:
        return fallback

    # Pick closest valid target
    valid.sort(key=lambda x: x[2])
    best_price, best_source, best_dist = valid[0]

    rr = best_dist / stop_distance if stop_distance > 0 else 0.0
    dist_atr = best_dist / atr_val if atr_val > 0 else 0.0

    return {
        "tp_price": round(best_price, 6),
        "tp_source": best_source,
        "distance_atr": round(dist_atr, 3),
        "rr_ratio": round(rr, 2),
    }


# ---------------------------------------------------------------------------
# Function 2: Fade the Extreme
# ---------------------------------------------------------------------------

def fade_the_extreme(
    df_15m: pd.DataFrame | None,
    price: float,
    atr_val: float,
    wick_zones: list[dict] | None = None,
) -> dict:
    """Detect extreme RSI + wick zone confluence for counter-trend entries.

    Looks for RSI < 20 at support or RSI > 80 at resistance to generate
    high-conviction fade signals.

    Args:
        df_15m: 15-minute OHLCV DataFrame (needs close, high, low).
        price: Current price.
        atr_val: Current ATR value.
        wick_zones: Optional list of wick zone dicts with "low" and "high" keys.

    Returns:
        Dict with signal, rsi, confidence, score_adj, reason.
    """
    no_signal = {
        "signal": "none",
        "rsi": 50.0,
        "confidence": 0,
        "score_adj": 0,
        "reason": "no extreme detected",
    }

    if df_15m is None or len(df_15m) < 20 or atr_val <= 0:
        return no_signal

    rsi_series = compute_rsi(df_15m["close"], length=14)
    if rsi_series.empty or rsi_series.isna().all():
        return no_signal

    current_rsi = float(rsi_series.iloc[-1])
    if np.isnan(current_rsi):
        return no_signal

    proximity = 0.5 * atr_val
    tail_48 = df_15m.tail(48)

    # Collect zone lows and zone highs
    zone_lows: list[float] = []
    zone_highs: list[float] = []
    if wick_zones:
        for wz in wick_zones:
            if isinstance(wz, dict):
                if "low" in wz:
                    zone_lows.append(float(wz["low"]))
                if "high" in wz:
                    zone_highs.append(float(wz["high"]))

    # Add 48-bar extremes as fallback anchors
    bar_low = float(tail_48["low"].min())
    bar_high = float(tail_48["high"].max())
    zone_lows.append(bar_low)
    zone_highs.append(bar_high)

    # -- Check bullish fade: RSI < 20 near a support zone --
    if current_rsi < 20:
        near_support = any(abs(price - zl) <= proximity for zl in zone_lows)
        if near_support:
            # Confidence scales with how extreme the RSI is
            # RSI 10 -> 100, RSI 19 -> 45
            confidence = max(0, min(100, int(100 - (current_rsi - 5) * (55 / 15))))
            score_adj = max(0, min(15, int((20 - current_rsi) * 1.5)))
            nearest_zone = min(zone_lows, key=lambda z: abs(price - z))
            return {
                "signal": "fade_long",
                "rsi": round(current_rsi, 2),
                "confidence": confidence,
                "score_adj": score_adj,
                "reason": f"RSI {current_rsi:.1f} near support zone {nearest_zone:.6f}",
            }

    # -- Check bearish fade: RSI > 80 near a resistance zone --
    if current_rsi > 80:
        near_resistance = any(abs(price - zh) <= proximity for zh in zone_highs)
        if near_resistance:
            confidence = max(0, min(100, int(100 - (95 - current_rsi) * (55 / 15))))
            score_adj = max(0, min(15, int((current_rsi - 80) * 1.5)))
            nearest_zone = min(zone_highs, key=lambda z: abs(price - z))
            return {
                "signal": "fade_short",
                "rsi": round(current_rsi, 2),
                "confidence": confidence,
                "score_adj": score_adj,
                "reason": f"RSI {current_rsi:.1f} near resistance zone {nearest_zone:.6f}",
            }

    return no_signal


# ---------------------------------------------------------------------------
# Function 3: Session Open Detector
# ---------------------------------------------------------------------------

# Session open times in UTC (hour, minute)
_SESSIONS: list[tuple[str, int, int]] = [
    ("asia", 0, 0),       # 00:00 UTC -- 4 PM PT
    ("london", 8, 0),     # 08:00 UTC -- midnight PT
    ("ny", 13, 30),       # 13:30 UTC -- 5:30 AM PT
    ("ny_equity", 14, 30),  # 14:30 UTC -- 6:30 AM PT
]


def session_open_detector(
    now_utc: datetime | None,
    config: dict | None = None,
) -> dict:
    """Detect proximity to major session opens.

    Returns phase info and multipliers for volatility and entry gates.

    Args:
        now_utc: Current time in UTC (timezone-aware or naive -- treated as UTC).
        config: Optional config dict (reserved for future session overrides).

    Returns:
        Dict with phase, session, minutes_to_open, vol_mult, gate_mult.
    """
    default = {
        "phase": "between_sessions",
        "session": "none",
        "minutes_to_open": 999,
        "vol_mult": 1.0,
        "gate_mult": 1.0,
    }

    if now_utc is None:
        return default

    # Ensure we work with a naive UTC representation
    if now_utc.tzinfo is not None:
        now_utc = now_utc.replace(tzinfo=None)

    now_minutes = now_utc.hour * 60 + now_utc.minute

    best_phase = "between_sessions"
    best_session = "none"
    best_minutes_to_open = 999
    best_vol_mult = 1.0
    best_gate_mult = 1.0

    for session_name, hour, minute in _SESSIONS:
        open_minutes = hour * 60 + minute

        # Minutes until the open (wrapping around midnight)
        diff = open_minutes - now_minutes
        if diff < -720:  # more than 12h behind -- wrap forward
            diff += 1440
        elif diff > 720:  # more than 12h ahead -- wrap backward
            diff -= 1440

        abs_diff = abs(diff)

        if 0 < diff <= 15:
            # Within 15 min BEFORE open
            phase = "pre_session"
            vol_mult = 1.2 + 0.3 * (1 - diff / 15)  # 1.2 to 1.5 as we approach
            gate_mult = 0.8 + 0.2 * (diff / 15)       # 0.8 to 1.0 -- tighter near open
        elif -30 <= diff <= 0:
            # Within 30 min AFTER open
            phase = "session_active"
            minutes_after = abs(diff)
            vol_mult = 1.5 - 0.5 * (minutes_after / 30)  # 1.5 decaying to 1.0
            gate_mult = 1.2 - 0.2 * (minutes_after / 30)  # 1.2 decaying to 1.0
        else:
            continue

        if abs_diff < abs(best_minutes_to_open):
            best_phase = phase
            best_session = session_name
            best_minutes_to_open = diff
            best_vol_mult = vol_mult
            best_gate_mult = gate_mult

    return {
        "phase": best_phase,
        "session": best_session,
        "minutes_to_open": int(best_minutes_to_open),
        "vol_mult": round(best_vol_mult, 3),
        "gate_mult": round(best_gate_mult, 3),
    }


# ---------------------------------------------------------------------------
# Function 4: R-Multiple Calculator
# ---------------------------------------------------------------------------

def compute_r_multiple(
    entry_price: float,
    current_price: float,
    stop_loss: float,
    direction: str,
) -> dict:
    """Compute current R-multiple for position management.

    R = distance from entry to stop (the initial risk).
    R-multiple = how many R's of profit (or loss) the trade has moved.

    Args:
        entry_price: Trade entry price.
        current_price: Current market price.
        stop_loss: Stop-loss price.
        direction: "long" or "short".

    Returns:
        Dict with r_multiple, risk_usd_per_contract, at_1r/2r/3r booleans,
        and scale_recommendation.
    """
    default = {
        "r_multiple": 0.0,
        "risk_usd_per_contract": 0.0,
        "at_1r": False,
        "at_2r": False,
        "at_3r": False,
        "scale_recommendation": "hold",
    }

    if entry_price <= 0 or current_price <= 0 or stop_loss <= 0:
        return default

    # Compute R (risk distance)
    if direction == "long":
        r_distance = entry_price - stop_loss
        profit_distance = current_price - entry_price
    elif direction == "short":
        r_distance = stop_loss - entry_price
        profit_distance = entry_price - current_price
    else:
        return default

    if r_distance <= 0:
        return default

    r_multiple = profit_distance / r_distance

    # 1 contract = 5,000 XLM, so $1 of price move = $5,000 per contract
    # But XLM is ~$0.10-$0.50, so risk in USD = r_distance * 5000
    risk_usd = r_distance * 5000

    at_1r = r_multiple >= 1.0
    at_2r = r_multiple >= 2.0
    at_3r = r_multiple >= 3.0

    # Scale-out recommendation
    if r_multiple < 0.5:
        recommendation = "hold"
    elif 1.0 <= r_multiple < 2.0:
        recommendation = "close_half"
    elif r_multiple >= 2.0:
        recommendation = "trail_tight"
    else:
        recommendation = "hold"

    return {
        "r_multiple": round(r_multiple, 3),
        "risk_usd_per_contract": round(risk_usd, 2),
        "at_1r": at_1r,
        "at_2r": at_2r,
        "at_3r": at_3r,
        "scale_recommendation": recommendation,
    }
