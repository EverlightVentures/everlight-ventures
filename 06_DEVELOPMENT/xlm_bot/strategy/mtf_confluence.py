"""Multi-Timeframe Confluence Scoring System.

Stage 1: Calculates a score adjustment (-20 to +20) based on alignment between
15-minute and 1-hour volatility phases.

Stage 2: Progressive timeframe nesting. Auto-detects trade timeframe from
signal ATR, resamples higher timeframes (4H, Daily), and scores alignment
across look-up and look-down pairs.

The module is pure scoring -- it never blocks trades.
"""
from __future__ import annotations

from typing import Any

import pandas as pd

from strategy.expansion import compute_expansion
from indicators.rsi import rsi as calc_rsi
from indicators.atr import atr as calc_atr


# ---------------------------------------------------------------------------
# Progressive nesting map
# ---------------------------------------------------------------------------

NESTING = {
    "15m": {"down": "5m",  "up": "1h"},
    "1h":  {"down": "15m", "up": "4h"},
    "4h":  {"down": "1h",  "up": "daily"},
}

# Minimum candles required for reliable phase detection
_MIN_CANDLES = 20


# ---------------------------------------------------------------------------
# 1H phase computation (reuses existing compute_expansion)
# ---------------------------------------------------------------------------

def compute_1h_phase(df_1h: pd.DataFrame | None) -> dict:
    """Run expansion detection on 1H candles."""
    if df_1h is None or len(df_1h) < 30:
        return {
            "phase": "COMPRESSION",
            "direction": "NEUTRAL",
            "confidence": 0,
            "reasons": [],
            "metrics": {},
        }
    return compute_expansion(df_1h, None, consolidation_lookback=20)


def _compute_phase(df: pd.DataFrame | None, min_candles: int = _MIN_CANDLES) -> dict | None:
    """Run expansion detection on any timeframe. Returns None if insufficient data."""
    if df is None or len(df) < min_candles:
        return None
    try:
        return compute_expansion(df, None, consolidation_lookback=min(20, len(df) - 5))
    except Exception:
        return None


def _compute_rsi(df: pd.DataFrame | None, period: int = 14) -> float:
    """Compute RSI for any timeframe. Returns 50.0 on failure."""
    if df is None or len(df) < period + 5:
        return 50.0
    try:
        rsi_series = calc_rsi(df["close"], period)
        val = float(rsi_series.iloc[-1])
        return val if not pd.isna(val) else 50.0
    except Exception:
        return 50.0


# ---------------------------------------------------------------------------
# Timeframe inference
# ---------------------------------------------------------------------------

def infer_trade_timeframe(df_15m: pd.DataFrame | None, signal_atr: float | None = None) -> str:
    """Infer the trade timeframe from signal ATR vs 15m ATR.

    - signal_atr > 6x 15m ATR -> 4H timeframe
    - signal_atr > 3x 15m ATR -> 1H timeframe
    - Otherwise -> 15m timeframe
    """
    if df_15m is None or len(df_15m) < 20 or signal_atr is None or signal_atr <= 0:
        return "15m"

    try:
        atr_15m = float(calc_atr(df_15m, 14).iloc[-1])
        if pd.isna(atr_15m) or atr_15m <= 0:
            return "15m"
    except Exception:
        return "15m"

    ratio = signal_atr / atr_15m
    if ratio > 6.0:
        return "4h"
    elif ratio > 3.0:
        return "1h"
    return "15m"


# ---------------------------------------------------------------------------
# Progressive candle building
# ---------------------------------------------------------------------------

def build_progressive_candles(
    df_15m: pd.DataFrame | None,
    df_1h: pd.DataFrame | None,
) -> dict[str, pd.DataFrame | None]:
    """Resample available data into higher timeframes.

    Returns dict with keys: 5m, 15m, 1h, 4h, daily.
    5m is always None (bot doesn't have 5m data).
    """
    result: dict[str, pd.DataFrame | None] = {
        "5m": None,
        "15m": df_15m,
        "1h": df_1h,
        "4h": None,
        "daily": None,
    }

    # Build 4H from 1H
    if df_1h is not None and len(df_1h) >= _MIN_CANDLES:
        try:
            df_4h = df_1h.resample("4h").agg({
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "volume": "sum",
            }).dropna()
            if len(df_4h) >= _MIN_CANDLES:
                result["4h"] = df_4h
        except Exception:
            pass

    # Build Daily from 4H (or from 1H if 4H failed)
    source_for_daily = result["4h"] if result["4h"] is not None else df_1h
    if source_for_daily is not None and len(source_for_daily) >= _MIN_CANDLES:
        try:
            df_daily = source_for_daily.resample("1D").agg({
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "volume": "sum",
            }).dropna()
            if len(df_daily) >= _MIN_CANDLES:
                result["daily"] = df_daily
        except Exception:
            pass

    return result


# ---------------------------------------------------------------------------
# Phase alignment tables (Stage 1 -- preserved for backward compat)
# ---------------------------------------------------------------------------

# (15m_phase, 1h_phase) -> adjustment for LONG entries
_LONG_TABLE: dict[tuple[str, str], int] = {
    ("COMPRESSION", "EXPANSION"):   +15,
    ("COMPRESSION", "IGNITION"):    +10,
    ("IGNITION",    "EXPANSION"):   +15,
    ("EXPANSION",   "EXPANSION"):   +20,
    ("EXPANSION",   "EXHAUSTION"):  -5,
    ("EXHAUSTION",  "EXHAUSTION"):  -15,
    ("COMPRESSION", "COMPRESSION"): 0,
    ("COMPRESSION", "EXHAUSTION"):  -10,
    ("IGNITION",    "IGNITION"):    +5,
    ("IGNITION",    "COMPRESSION"): 0,
    ("IGNITION",    "EXHAUSTION"):  -5,
    ("EXPANSION",   "COMPRESSION"): +5,
    ("EXPANSION",   "IGNITION"):    +10,
    ("EXHAUSTION",  "COMPRESSION"): -5,
    ("EXHAUSTION",  "IGNITION"):    0,
    ("EXHAUSTION",  "EXPANSION"):   -10,
}

# (15m_phase, 1h_phase) -> adjustment for SHORT entries (mirrored)
_SHORT_TABLE: dict[tuple[str, str], int] = {
    ("COMPRESSION", "EXHAUSTION"):  +15,
    ("EXPANSION",   "EXHAUSTION"):  +10,
    ("EXHAUSTION",  "EXHAUSTION"):  +15,
    ("IGNITION",    "EXPANSION"):   -10,
    ("EXPANSION",   "EXPANSION"):   -15,
    ("COMPRESSION", "COMPRESSION"): 0,
    ("COMPRESSION", "EXPANSION"):   -10,
    ("COMPRESSION", "IGNITION"):    -5,
    ("IGNITION",    "IGNITION"):    0,
    ("IGNITION",    "COMPRESSION"): 0,
    ("IGNITION",    "EXHAUSTION"):  +5,
    ("EXPANSION",   "COMPRESSION"): 0,
    ("EXPANSION",   "IGNITION"):    -5,
    ("EXHAUSTION",  "COMPRESSION"): +5,
    ("EXHAUSTION",  "IGNITION"):    +5,
    ("EXHAUSTION",  "EXPANSION"):   -10,
}

# Lane classification for entry-type modifiers
_BREAKOUT_LANES = {"B", "F"}
_MEAN_REVERSION_LANES = {"C", "G", "I", "K", "N"}
_TREND_CONTINUATION_LANES = {"A", "H"}
_REVERSAL_LANES = {"M"}

# Bullish phases (favor longs)
_BULLISH_PHASES = {"EXPANSION", "IGNITION"}
# Bearish phases (favor shorts)
_BEARISH_PHASES = {"EXHAUSTION"}


# ---------------------------------------------------------------------------
# Alignment label
# ---------------------------------------------------------------------------

def _alignment_label(adj: int) -> str:
    if adj >= 15:
        return "STRONG_ALIGN"
    if adj >= 5:
        return "WEAK_ALIGN"
    if adj >= -4:
        return "NEUTRAL"
    if adj >= -10:
        return "CONFLICTING"
    return "STRONG_CONFLICT"


# ---------------------------------------------------------------------------
# Progressive nesting scorer
# ---------------------------------------------------------------------------

def _score_progressive_nesting(
    *,
    trade_tf: str,
    candles: dict[str, pd.DataFrame | None],
    direction: str,
) -> dict[str, Any]:
    """Score alignment across look-up and look-down timeframes.

    Returns a dict with progressive scoring details.
    """
    nesting = NESTING.get(trade_tf)
    if nesting is None:
        return {"prog_adjustment": 0, "look_up": None, "look_down": None,
                "alignment": "NEUTRAL", "timeframes_aligned": 1, "prog_reasons": []}

    is_long = direction == "long"
    prog_adj = 0
    prog_reasons: list[str] = []
    tfs_aligned = 1  # trade TF always counts as aligned with itself

    # --- Look-up ---
    look_up_tf = nesting["up"]
    look_up_df = candles.get(look_up_tf)
    look_up_info: dict[str, Any] | None = None

    if look_up_df is not None and len(look_up_df) >= _MIN_CANDLES:
        lu_result = _compute_phase(look_up_df)
        lu_rsi = _compute_rsi(look_up_df)

        if lu_result is not None:
            lu_phase = str(lu_result.get("phase", "COMPRESSION")).upper()
            look_up_info = {"tf": look_up_tf, "phase": lu_phase, "rsi": round(lu_rsi, 1)}

            # Does the look-up agree with our direction?
            if is_long:
                if lu_phase in _BULLISH_PHASES:
                    prog_adj += 10
                    prog_reasons.append(f"{look_up_tf.upper()}={lu_phase}(+10)")
                    tfs_aligned += 1
                elif lu_phase in _BEARISH_PHASES:
                    prog_adj -= 10
                    prog_reasons.append(f"{look_up_tf.upper()}={lu_phase}(-10)")
                else:
                    prog_reasons.append(f"{look_up_tf.upper()}={lu_phase}(0)")
            else:  # short
                if lu_phase in _BEARISH_PHASES:
                    prog_adj += 10
                    prog_reasons.append(f"{look_up_tf.upper()}={lu_phase}(+10)")
                    tfs_aligned += 1
                elif lu_phase in _BULLISH_PHASES:
                    prog_adj -= 10
                    prog_reasons.append(f"{look_up_tf.upper()}={lu_phase}(-10)")
                else:
                    prog_reasons.append(f"{look_up_tf.upper()}={lu_phase}(0)")

            # RSI extreme on look-up
            if is_long and lu_rsi > 80:
                prog_adj -= 5
                prog_reasons.append(f"{look_up_tf.upper()}_RSI_OB({lu_rsi:.0f})(-5)")
            elif is_long and lu_rsi < 20:
                prog_adj += 5
                prog_reasons.append(f"{look_up_tf.upper()}_RSI_OS({lu_rsi:.0f})(+5)")
            elif not is_long and lu_rsi > 80:
                prog_adj += 5
                prog_reasons.append(f"{look_up_tf.upper()}_RSI_OB({lu_rsi:.0f})(+5)")
            elif not is_long and lu_rsi < 20:
                prog_adj -= 5
                prog_reasons.append(f"{look_up_tf.upper()}_RSI_OS({lu_rsi:.0f})(-5)")

    # --- Look-down ---
    look_down_tf = nesting["down"]
    look_down_df = candles.get(look_down_tf)
    look_down_info: dict[str, Any] | None = None

    if look_down_df is not None and len(look_down_df) >= _MIN_CANDLES:
        ld_result = _compute_phase(look_down_df)
        ld_rsi = _compute_rsi(look_down_df)

        if ld_result is not None:
            ld_phase = str(ld_result.get("phase", "COMPRESSION")).upper()
            look_down_info = {"tf": look_down_tf, "phase": ld_phase, "rsi": round(ld_rsi, 1)}

            # Does the look-down confirm our direction?
            if is_long:
                if ld_phase in _BULLISH_PHASES:
                    prog_adj += 5
                    prog_reasons.append(f"{look_down_tf.upper()}={ld_phase}(+5)")
                    tfs_aligned += 1
                elif ld_phase in _BEARISH_PHASES:
                    prog_adj -= 5
                    prog_reasons.append(f"{look_down_tf.upper()}={ld_phase}(-5)")
                else:
                    prog_reasons.append(f"{look_down_tf.upper()}={ld_phase}(0)")
            else:  # short
                if ld_phase in _BEARISH_PHASES:
                    prog_adj += 5
                    prog_reasons.append(f"{look_down_tf.upper()}={ld_phase}(+5)")
                    tfs_aligned += 1
                elif ld_phase in _BULLISH_PHASES:
                    prog_adj -= 5
                    prog_reasons.append(f"{look_down_tf.upper()}={ld_phase}(-5)")
                else:
                    prog_reasons.append(f"{look_down_tf.upper()}={ld_phase}(0)")

    # --- Triple alignment bonus/penalty ---
    if tfs_aligned >= 3:
        prog_adj += 5
        prog_reasons.append("3TF_ALIGNED(+5)")
    elif look_up_info and look_down_info:
        # Both exist but check if neither aligned
        lu_agrees = False
        ld_agrees = False
        if look_up_info:
            lu_ph = look_up_info["phase"]
            lu_agrees = (is_long and lu_ph in _BULLISH_PHASES) or (not is_long and lu_ph in _BEARISH_PHASES)
        if look_down_info:
            ld_ph = look_down_info["phase"]
            ld_agrees = (is_long and ld_ph in _BULLISH_PHASES) or (not is_long and ld_ph in _BEARISH_PHASES)

        if not lu_agrees and not ld_agrees:
            prog_adj -= 5
            prog_reasons.append("3TF_CONFLICT(-5)")

    alignment = _alignment_label(prog_adj)

    return {
        "prog_adjustment": prog_adj,
        "look_up": look_up_info,
        "look_down": look_down_info,
        "alignment": alignment,
        "timeframes_aligned": tfs_aligned,
        "prog_reasons": prog_reasons,
    }


# ---------------------------------------------------------------------------
# Core scoring function
# ---------------------------------------------------------------------------

def score_mtf_confluence(
    *,
    vol_state_15m: str,
    df_1h: pd.DataFrame | None = None,
    df_15m: pd.DataFrame | None = None,
    vol_state_1h: str | None = None,
    trade_direction: str,
    entry_type: str = "",
    lane: str = "",
    signal_atr: float | None = None,
) -> dict[str, Any]:
    """Calculate MTF confluence score adjustment.

    Stage 1 (backward compat): phase alignment from 15m vs 1H lookup tables.
    Stage 2 (progressive): auto-detect trade TF, build higher TFs, score
    look-up/look-down pairs progressively.

    Args:
        vol_state_15m: Current 15m vol phase (COMPRESSION/IGNITION/EXPANSION/EXHAUSTION)
        df_1h: 1-hour candle DataFrame
        df_15m: 15-minute candle DataFrame (optional, enables progressive nesting)
        vol_state_1h: Override 1H vol phase (if None, computed from df_1h)
        trade_direction: "long" or "short"
        entry_type: Signal type (breakout, mean_reversion, etc.)
        lane: Lane letter (A, B, C, etc.)
        signal_atr: ATR of the signal that triggered entry (for TF inference)

    Returns:
        dict with score_adjustment, htf_phase, alignment, reasons, confidence_boost,
        plus progressive nesting fields (trade_timeframe, look_up, look_down, etc.)
    """
    reasons: list[str] = []
    adjustment = 0

    # Normalize inputs
    phase_15m = str(vol_state_15m or "COMPRESSION").upper().strip()
    direction = str(trade_direction or "long").lower().strip()
    lane_upper = str(lane or "").upper().strip()
    et = str(entry_type or "").lower().strip()

    # Compute 1H phase if not provided
    if vol_state_1h:
        phase_1h = str(vol_state_1h).upper().strip()
    else:
        htf_result = compute_1h_phase(df_1h)
        phase_1h = str(htf_result.get("phase", "COMPRESSION")).upper().strip()

    # Compute 1H RSI for extreme checks
    rsi_1h = _compute_rsi(df_1h)

    # --- Stage 1: Phase alignment base adjustment (preserved) ---
    key = (phase_15m, phase_1h)
    if direction == "long":
        base_adj = _LONG_TABLE.get(key, 0)
    else:
        base_adj = _SHORT_TABLE.get(key, 0)

    adjustment += base_adj
    reasons.append(f"15m={phase_15m},1H={phase_1h}:{base_adj:+d}")

    # --- RSI extreme adjustments ---
    rsi_adj = 0
    if direction == "long":
        if rsi_1h > 80:
            rsi_adj = -10
            reasons.append(f"1H_RSI_overbought({rsi_1h:.0f}):-10")
        elif rsi_1h < 20:
            rsi_adj = +10
            reasons.append(f"1H_RSI_oversold({rsi_1h:.0f}):+10")
    else:  # short
        if rsi_1h > 80:
            rsi_adj = +10
            reasons.append(f"1H_RSI_overbought({rsi_1h:.0f}):+10")
        elif rsi_1h < 20:
            rsi_adj = -10
            reasons.append(f"1H_RSI_oversold({rsi_1h:.0f}):-10")
    adjustment += rsi_adj

    # --- Entry type / lane modifiers ---
    entry_adj = 0
    if lane_upper in _BREAKOUT_LANES and phase_15m == "EXPANSION":
        entry_adj += 5
        reasons.append(f"breakout_lane_{lane_upper}_in_EXPANSION:+5")

    if lane_upper in _MEAN_REVERSION_LANES and phase_15m == "EXHAUSTION":
        entry_adj += 5
        reasons.append(f"mr_lane_{lane_upper}_in_EXHAUSTION:+5")

    if lane_upper in _TREND_CONTINUATION_LANES and phase_15m == "EXPANSION" and phase_1h == "EXPANSION":
        entry_adj += 5
        reasons.append(f"trend_lane_{lane_upper}_double_EXPANSION:+5")

    if lane_upper in _REVERSAL_LANES:
        if direction == "short" and phase_1h == "EXPANSION":
            entry_adj -= 10
            reasons.append("reversal_lane_M_short_vs_HTF_EXPANSION:-10")

    if lane_upper in _REVERSAL_LANES and phase_1h == "EXHAUSTION":
        entry_adj += 5
        reasons.append("reversal_lane_M_HTF_EXHAUSTION_confirms:+5")

    if not lane_upper:
        if "breakout" in et and phase_15m == "EXPANSION":
            entry_adj += 5
            reasons.append("breakout_entry_in_EXPANSION:+5")
        if ("mean_reversion" in et or "wick" in et) and phase_15m == "EXHAUSTION":
            entry_adj += 5
            reasons.append("mr_entry_in_EXHAUSTION:+5")

    adjustment += entry_adj

    # --- Stage 2: Progressive nesting (when df_15m is available) ---
    trade_tf = "15m"
    prog_result: dict[str, Any] = {
        "prog_adjustment": 0,
        "look_up": None,
        "look_down": None,
        "alignment": "NEUTRAL",
        "timeframes_aligned": 1,
        "prog_reasons": [],
    }

    if df_15m is not None and len(df_15m) >= _MIN_CANDLES:
        # Infer trade timeframe
        trade_tf = infer_trade_timeframe(df_15m, signal_atr)

        # Build all available timeframe candles
        candles = build_progressive_candles(df_15m, df_1h)

        # Score progressive nesting
        prog_result = _score_progressive_nesting(
            trade_tf=trade_tf,
            candles=candles,
            direction=direction,
        )

        # Add progressive adjustment to total
        adjustment += prog_result["prog_adjustment"]
        reasons.extend(prog_result["prog_reasons"])

    # --- Clamp to [-20, +20] ---
    adjustment = max(-20, min(20, adjustment))

    # --- Confidence boost (0.0 to 1.0 based on adjustment) ---
    confidence_boost = max(0.0, min(1.0, (adjustment + 20) / 40.0))

    alignment = _alignment_label(adjustment)

    return {
        "score_adjustment": adjustment,
        "htf_phase": phase_1h,
        "ltf_phase": phase_15m,
        "alignment": alignment,
        "reasons": reasons,
        "confidence_boost": round(confidence_boost, 3),
        "rsi_1h": round(rsi_1h, 1),
        # Stage 2 progressive fields
        "trade_timeframe": trade_tf,
        "look_up": prog_result.get("look_up"),
        "look_down": prog_result.get("look_down"),
        "timeframes_aligned": prog_result.get("timeframes_aligned", 1),
    }
