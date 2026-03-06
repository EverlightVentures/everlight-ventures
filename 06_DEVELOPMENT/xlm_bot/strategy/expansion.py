"""Expansion detection & volatility state machine.

Proactive volatility awareness: detect COMPRESSION (setup), IGNITION (early
warning), EXPANSION (confirmed move), EXHAUSTION (fading).

This module is *read-only context* — it does NOT change risk sizing or gate
logic.  The bot and dashboard consume the state object for logging and display.
"""
from __future__ import annotations

import pandas as pd

from indicators.atr import atr as calc_atr
from indicators.rsi import rsi as calc_rsi


# ---------------------------------------------------------------------------
# Core measurements
# ---------------------------------------------------------------------------

def _true_range(df: pd.DataFrame) -> pd.Series:
    """Per-candle true range."""
    high = df["high"]
    low = df["low"]
    prev_close = df["close"].shift(1)
    return pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)


def _consolidation_range(df: pd.DataFrame, lookback: int = 30) -> tuple[float, float]:
    """High/low bounds of recent consolidation.

    Uses the middle 80% of the lookback window (trims the top/bottom 10%
    of closes) to avoid a single spike setting the range.
    """
    if df.empty or len(df) < lookback:
        lookback = max(len(df), 5)
    closes = df["close"].iloc[-lookback:]
    highs = df["high"].iloc[-lookback:]
    lows = df["low"].iloc[-lookback:]
    # Simple: use rolling high/low of the lookback window
    range_high = float(highs.max())
    range_low = float(lows.min())
    return range_high, range_low


# ---------------------------------------------------------------------------
# compute_expansion()
# ---------------------------------------------------------------------------

def compute_expansion(
    df_15m: pd.DataFrame,
    df_1h: pd.DataFrame | None = None,
    *,
    consolidation_lookback: int = 30,
) -> dict:
    """Compute expansion state from OHLCV candles.

    Returns a dict with:
        phase:      COMPRESSION | IGNITION | EXPANSION | EXHAUSTION
        direction:  LONG | SHORT | NEUTRAL
        confidence: 0-100
        reasons:    list of reason codes
        metrics:    { tr_ratio, vol_ratio, atr, atr_prev, atr_slope, rsi, ... }
        range:      { high, low }
    """
    result = {
        "phase": "COMPRESSION",
        "direction": "NEUTRAL",
        "confidence": 0,
        "reasons": [],
        "metrics": {},
        "range": {"high": None, "low": None},
    }

    if df_15m is None or df_15m.empty or len(df_15m) < 30:
        result["reasons"] = ["INSUFFICIENT_DATA"]
        return result

    # --- Compute indicators ---
    tr = _true_range(df_15m)
    avg_tr = tr.rolling(20).mean()
    atr_series = calc_atr(df_15m, 14)
    rsi_series = calc_rsi(df_15m["close"], 14)
    vol_avg = df_15m["volume"].rolling(20).mean()

    # Current values (last candle)
    tr_now = float(tr.iloc[-1]) if not pd.isna(tr.iloc[-1]) else 0.0
    avg_tr_now = float(avg_tr.iloc[-1]) if not pd.isna(avg_tr.iloc[-1]) else tr_now
    atr_now = float(atr_series.iloc[-1]) if not pd.isna(atr_series.iloc[-1]) else 0.0
    atr_prev = float(atr_series.iloc[-2]) if len(atr_series) > 1 and not pd.isna(atr_series.iloc[-2]) else atr_now
    atr_2ago = float(atr_series.iloc[-3]) if len(atr_series) > 2 and not pd.isna(atr_series.iloc[-3]) else atr_prev
    rsi_now = float(rsi_series.iloc[-1]) if not pd.isna(rsi_series.iloc[-1]) else 50.0
    rsi_prev = float(rsi_series.iloc[-2]) if len(rsi_series) > 1 and not pd.isna(rsi_series.iloc[-2]) else rsi_now
    vol_now = float(df_15m["volume"].iloc[-1]) if not pd.isna(df_15m["volume"].iloc[-1]) else 0.0
    vol_avg_now = float(vol_avg.iloc[-1]) if not pd.isna(vol_avg.iloc[-1]) else vol_now
    close = float(df_15m["close"].iloc[-1])

    # Ratios
    tr_ratio = (tr_now / avg_tr_now) if avg_tr_now > 0 else 1.0
    atr_slope = atr_now - atr_prev
    atr_slope_prev = atr_prev - atr_2ago
    atr_slope_rising_2bars = atr_slope > 0 and atr_slope_prev > 0
    vol_ratio = (vol_now / vol_avg_now) if vol_avg_now > 0 else 1.0

    # Consolidation range
    range_high, range_low = _consolidation_range(df_15m, consolidation_lookback)

    # Wickiness: (high-low - abs(close-open)) / (high-low) — higher = more wicks
    last_bar = df_15m.iloc[-1]
    bar_range = float(last_bar["high"]) - float(last_bar["low"])
    bar_body = abs(float(last_bar["close"]) - float(last_bar["open"]))
    wickiness = 1.0 - (bar_body / bar_range) if bar_range > 0 else 0.0

    metrics = {
        "tr": round(tr_now, 8),
        "avg_tr": round(avg_tr_now, 8),
        "tr_ratio": round(tr_ratio, 3),
        "atr": round(atr_now, 8),
        "atr_prev": round(atr_prev, 8),
        "atr_slope": round(atr_slope, 8),
        "atr_slope_rising_2bars": atr_slope_rising_2bars,
        "vol": round(vol_now, 2),
        "vol_avg": round(vol_avg_now, 2),
        "vol_ratio": round(vol_ratio, 3),
        "rsi": round(rsi_now, 2),
        "rsi_prev": round(rsi_prev, 2),
        "close": round(close, 8),
        "range_high": round(range_high, 8),
        "range_low": round(range_low, 8),
        "wickiness": round(wickiness, 3),
    }
    result["metrics"] = metrics
    result["range"] = {"high": round(range_high, 8), "low": round(range_low, 8)}

    # --- Phase detection (bottom-up: check most advanced phase first) ---
    reasons = []

    # Direction from price vs range
    range_break_long = close > range_high
    range_break_short = close < range_low
    rsi_bullish = rsi_now > 60
    rsi_bearish = rsi_now < 40
    rsi_near_50 = 42 <= rsi_now <= 58

    # IGNITION checks (early warning — low bar, meant to fire BEFORE expansion)
    ignition_tr = tr_ratio >= 1.3
    ignition_atr_slope = atr_slope_rising_2bars
    ignition_vol = vol_ratio >= 1.2
    ignition = ignition_tr or ignition_atr_slope or ignition_vol

    if ignition_tr:
        reasons.append("TR_RATIO")
    if ignition_atr_slope:
        reasons.append("ATR_SLOPE_RISING")
    if ignition_vol:
        reasons.append("VOL_RATIO")

    # EXPANSION checks (full confirmation)
    expansion_tr = tr_ratio >= 1.5
    expansion_range_break = range_break_long or range_break_short
    expansion_vol = vol_ratio >= 1.2
    expansion_momentum = (rsi_bullish and range_break_long) or (rsi_bearish and range_break_short)
    expansion = expansion_tr and expansion_range_break and expansion_vol and expansion_momentum

    if expansion_tr:
        reasons.append("TR_EXPANSION")
    if expansion_range_break:
        reasons.append("RANGE_BREAK")
    if expansion_momentum:
        reasons.append("RSI_CONFIRM")

    # CONFIRMATION: look at previous candle to see if expansion was confirmed
    # (next candle didn't close back inside range OR made continuation)
    confirmed = False
    if len(df_15m) >= 3:
        prev_close = float(df_15m["close"].iloc[-2])
        prev_high = float(df_15m["high"].iloc[-2])
        prev_low = float(df_15m["low"].iloc[-2])
        if range_break_long and (prev_close > range_high or prev_high > range_high):
            confirmed = True
            reasons.append("CONFIRMED_CONTINUATION")
        elif range_break_short and (prev_close < range_low or prev_low < range_low):
            confirmed = True
            reasons.append("CONFIRMED_CONTINUATION")

    # EXHAUSTION checks (after expansion, signs of fading)
    # We detect this by looking for: RSI was extreme and now rolling back,
    # or TR ratio spiked then falling, or wickiness increasing + vol fading
    rsi_rolling_back = False
    if rsi_now > 65 and rsi_now < rsi_prev:
        rsi_rolling_back = True
    elif rsi_now < 35 and rsi_now > rsi_prev:
        rsi_rolling_back = True

    tr_prev = float(tr.iloc[-2]) if len(tr) > 1 and not pd.isna(tr.iloc[-2]) else 0.0
    avg_tr_prev = float(avg_tr.iloc[-2]) if len(avg_tr) > 1 and not pd.isna(avg_tr.iloc[-2]) else avg_tr_now
    tr_ratio_prev = (tr_prev / avg_tr_prev) if avg_tr_prev > 0 else 1.0
    tr_fading = tr_ratio_prev >= 1.5 and tr_ratio < tr_ratio_prev * 0.75

    vol_prev = float(df_15m["volume"].iloc[-2]) if len(df_15m) > 1 else vol_now
    vol_fading = wickiness > 0.5 and vol_now < vol_prev * 0.8

    exhaustion = False
    exhaustion_reasons = []
    if rsi_rolling_back:
        exhaustion_reasons.append("RSI_ROLLBACK")
    if tr_fading:
        exhaustion_reasons.append("TR_FADING")
    if vol_fading:
        exhaustion_reasons.append("VOL_WICKS_FADING")
    if len(exhaustion_reasons) >= 2:
        exhaustion = True
        reasons.extend(exhaustion_reasons)

    # COMPRESSION checks
    compression = (
        atr_slope <= 0
        and tr_ratio < 1.1
        and vol_ratio <= 1.05
        and rsi_near_50
    )
    if compression:
        reasons.append("TIGHT_RANGE")

    # --- Assign phase (priority: EXHAUSTION > EXPANSION > IGNITION > COMPRESSION) ---
    # Exhaustion only applies if we were already in an expansion-like state
    if exhaustion and (expansion or (tr_ratio >= 1.3 and expansion_range_break)):
        phase = "EXHAUSTION"
    elif expansion and confirmed:
        phase = "EXPANSION"
    elif expansion:
        # Expansion conditions met but not yet confirmed — still call it expansion
        # with lower confidence
        phase = "EXPANSION"
    elif ignition:
        phase = "IGNITION"
    elif compression:
        phase = "COMPRESSION"
    else:
        phase = "COMPRESSION"  # default neutral state

    # Direction
    if phase in ("EXPANSION", "IGNITION", "EXHAUSTION"):
        if range_break_long or rsi_bullish:
            direction = "LONG"
        elif range_break_short or rsi_bearish:
            direction = "SHORT"
        else:
            direction = "NEUTRAL"
    else:
        direction = "NEUTRAL"

    # Confidence scoring (0-100)
    conf = 0
    if phase == "COMPRESSION":
        conf = 20 if compression else 10
    elif phase == "IGNITION":
        hits = sum([ignition_tr, ignition_atr_slope, ignition_vol])
        conf = 30 + (hits * 10)  # 40-60
    elif phase == "EXPANSION":
        base = 60
        if confirmed:
            base = 75
        if expansion_momentum:
            base += 10
        if vol_ratio >= 1.5:
            base += 5
        conf = min(100, base)
    elif phase == "EXHAUSTION":
        conf = 40 + len(exhaustion_reasons) * 15  # 55-85

    result["phase"] = phase
    result["direction"] = direction
    result["confidence"] = conf
    result["reasons"] = reasons

    return result


# ---------------------------------------------------------------------------
# derive_vol_state() — wrapper for state machine with explicit transitions
# ---------------------------------------------------------------------------

def derive_vol_state(
    df_15m: pd.DataFrame,
    df_1h: pd.DataFrame | None = None,
    prev_state: str = "COMPRESSION",
    *,
    consolidation_lookback: int = 30,
) -> dict:
    """Volatility state machine with hysteresis.

    Uses compute_expansion() as the raw signal, then applies transition rules
    to prevent noisy flipping.  Accepts prev_state so the caller can persist it.

    Returns same schema as compute_expansion() plus 'prev_state' and 'transitioned'.
    """
    raw = compute_expansion(df_15m, df_1h, consolidation_lookback=consolidation_lookback)
    new_phase = raw["phase"]

    # Transition rules (forward-only with one exception: EXHAUSTION → COMPRESSION)
    valid_transitions = {
        "COMPRESSION": {"IGNITION", "EXPANSION"},  # can skip ignition on violent move
        "IGNITION": {"EXPANSION", "COMPRESSION"},   # can fall back if false alarm
        "EXPANSION": {"EXHAUSTION", "COMPRESSION"},  # can jump to compression if very fast
        "EXHAUSTION": {"COMPRESSION", "IGNITION"},   # cycle resets
    }

    allowed = valid_transitions.get(prev_state, {"COMPRESSION", "IGNITION", "EXPANSION", "EXHAUSTION"})

    if new_phase == prev_state:
        transitioned = False
    elif new_phase in allowed:
        transitioned = True
    else:
        # Invalid transition — stay in current state but note the raw reading
        new_phase = prev_state
        transitioned = False
        raw["reasons"].append(f"HELD_{prev_state}")

    raw["phase"] = new_phase
    raw["prev_state"] = prev_state
    raw["transitioned"] = transitioned

    return raw
