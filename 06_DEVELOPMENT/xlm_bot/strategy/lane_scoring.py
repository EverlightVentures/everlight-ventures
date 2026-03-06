"""Multi-lane scoring system.

Routes trades through different scoring lanes with lane-specific thresholds
and weights.  Lane C (Sweep Recovery) catches post-dump bounces that the
standard scoring engine misses because trend indicators lag at reversals.
Lane E (Squeeze Impulse) catches reclaim->compression->ignition breakouts
that don't print clean retests before ripping.

Lane A -- Trend Continuation  (threshold ~75, trend weights)
Lane B -- Breakout            (threshold ~65, trend weights)
Lane C -- Sweep Recovery      (threshold ~50, reversal_impulse weights, ATR gate bypass)
Lane D -- Moonshot            (handled separately in market/moonshot.py)
Lane E -- Squeeze Impulse     (threshold ~55, reversal_impulse weights, distance gate bypass)
Lane F -- Compression Breakout (threshold ~60, distance gate bypass)
Lane G -- Compression Range  (threshold ~40, ATR + distance bypass, MR inside box)
Lane H -- Trend Structure    (threshold ~45, trend weights, ATR gate bypass)
Lane I -- Fib Retrace        (threshold ~45, reversal_impulse weights, ATR + distance bypass)
Lane P -- Grid Range         (threshold ~35, ATR + distance bypass, range edges)
Lane Q -- Funding Arb Bias   (threshold ~60, directional bias from funding rate)
Lane R -- Regime Low Vol     (threshold ~55, BB squeeze + range edge scalps)
Lane S -- Stat Arb Proxy     (threshold ~50, z-score mean reversion)
Lane T -- Orderflow Imbalance (threshold ~65, volume delta proxy)
Lane U -- Macro MA Cross     (threshold ~45, 200 MA breakout on higher TF)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd

from structure.fib import find_swing


@dataclass
class LaneResult:
    lane: str               # "A", "B", "C", "E"
    label: str              # "trend", "breakout", "sweep_recovery", "squeeze_impulse"
    threshold: int          # lane-specific score threshold
    rescore_as: str | None  # "reversal_impulse" for Lane C/E, else None
    atr_gate_bypass: bool   # True for Lane C
    distance_gate_bypass: bool = False  # True for Lane E
    reason: str = ""        # human-readable reason


def detect_sweep(
    df_15m: pd.DataFrame,
    df_1h: pd.DataFrame,
    direction: str,
    config: dict,
) -> dict | None:
    """Detect a liquidity sweep -- price wicks beyond swing level then reclaims.

    For longs:  recent candle low pierced swing_low, current close above swing_low
    For shorts: recent candle high pierced swing_high, current close below swing_high

    Returns dict with sweep details or None.
    """
    if df_15m is None or df_15m.empty or len(df_15m) < 10:
        return None

    lookback = int(config.get("sweep_lookback", 3) or 3)
    reclaim_pct = float(config.get("sweep_reclaim_pct", 0.002) or 0.002)

    # Use 1h for swing structure (more meaningful levels), fall back to 15m
    swing_df = df_1h if (df_1h is not None and not df_1h.empty and len(df_1h) >= 20) else df_15m
    swing_high, swing_low = find_swing(swing_df, 50)

    if swing_high <= 0 or swing_low <= 0:
        return None

    current_close = float(df_15m["close"].iloc[-1])
    d = direction.lower().strip()

    # Check recent candles (last `lookback`) for wick beyond swing level
    check_range = min(lookback, len(df_15m) - 1)

    if d == "long":
        # Sweep low: a recent candle wicked below swing_low, current close reclaimed
        for i in range(1, check_range + 1):
            candle = df_15m.iloc[-i]
            candle_low = float(candle["low"])
            if candle_low < swing_low and current_close > swing_low:
                reclaim_dist = (current_close - swing_low) / current_close if current_close > 0 else 0
                if reclaim_dist >= reclaim_pct:
                    return {
                        "detected": True,
                        "type": "sweep_low",
                        "level": swing_low,
                        "wick_low": candle_low,
                        "reclaim_price": current_close,
                        "reclaim_pct": round(reclaim_dist, 6),
                        "candles_ago": i,
                    }
    else:
        # Sweep high: a recent candle wicked above swing_high, current close reclaimed
        for i in range(1, check_range + 1):
            candle = df_15m.iloc[-i]
            candle_high = float(candle["high"])
            if candle_high > swing_high and current_close < swing_high:
                reclaim_dist = (swing_high - current_close) / current_close if current_close > 0 else 0
                if reclaim_dist >= reclaim_pct:
                    return {
                        "detected": True,
                        "type": "sweep_high",
                        "level": swing_high,
                        "wick_high": candle_high,
                        "reclaim_price": current_close,
                        "reclaim_pct": round(reclaim_dist, 6),
                        "candles_ago": i,
                    }

    return None


def detect_reclaim_impulse(
    df_15m: pd.DataFrame,
    df_1h: pd.DataFrame,
    direction: str,
    expansion_state: dict,
    config: dict,
) -> dict | None:
    """Detect a reclaim->squeeze->impulse setup (Lane E trigger).

    Fires when:
      1. Vol state is transitioning COMPRESSION -> IGNITION (or already IGNITION)
      2. Price reclaims a key level (EMA21 or swing) within the last few candles
      3. Current candle is an impulse candle (strong body, volume above average)

    For longs:  price crossed back above EMA21 or swing_low with bullish impulse
    For shorts: price crossed back below EMA21 or swing_high with bearish impulse

    Returns dict with reclaim details or None.
    """
    if df_15m is None or df_15m.empty or len(df_15m) < 25:
        return None

    phase = str(expansion_state.get("phase", "COMPRESSION")).upper()
    if phase not in ("IGNITION", "COMPRESSION"):
        return None

    # In pure COMPRESSION, require that ignition signals are starting to appear
    if phase == "COMPRESSION":
        metrics = expansion_state.get("metrics") or {}
        tr_ratio = float(metrics.get("tr_ratio", 0))
        atr_slope_rising = bool(metrics.get("atr_slope_rising_2bars", False))
        vol_ratio = float(metrics.get("vol_ratio", 0))
        # Need at least one early ignition hint
        if not (tr_ratio >= 1.15 or atr_slope_rising or vol_ratio >= 1.1):
            return None

    lookback = int(config.get("squeeze_lookback", 4) or 4)
    impulse_body_ratio = float(config.get("squeeze_impulse_body_ratio", 0.6) or 0.6)
    impulse_vol_ratio = float(config.get("squeeze_impulse_vol_ratio", 1.1) or 1.1)

    # Compute EMA21 on 15m
    ema21 = df_15m["close"].ewm(span=21, adjust=False).mean()
    ema21_now = float(ema21.iloc[-1])

    # Swing levels from 1h (or fall back to 15m)
    swing_df = df_1h if (df_1h is not None and not df_1h.empty and len(df_1h) >= 20) else df_15m
    swing_high, swing_low = find_swing(swing_df, 50)

    current = df_15m.iloc[-1]
    close = float(current["close"])
    open_ = float(current["open"])
    high = float(current["high"])
    low = float(current["low"])
    vol_now = float(current["volume"]) if "volume" in current.index else 0.0
    vol_avg = float(df_15m["volume"].rolling(20).mean().iloc[-1]) if "volume" in df_15m.columns else 0.0

    bar_range = high - low
    body = abs(close - open_)
    body_ratio = (body / bar_range) if bar_range > 0 else 0.0

    # Impulse candle check: strong body + volume
    is_impulse = (
        body_ratio >= impulse_body_ratio
        and (vol_avg <= 0 or vol_now >= vol_avg * impulse_vol_ratio)
    )
    if not is_impulse:
        return None

    d = direction.lower().strip()
    check_range = min(lookback, len(df_15m) - 2)

    if d == "long":
        bullish = close > open_
        if not bullish:
            return None

        # Check: was price below EMA21 or swing_low recently, now reclaimed above
        reclaim_level = None
        reclaim_type = None
        for i in range(1, check_range + 1):
            prev_close = float(df_15m["close"].iloc[-(i + 1)])
            prev_ema = float(ema21.iloc[-(i + 1)])
            # EMA21 reclaim: was below, now above
            if prev_close < prev_ema and close > ema21_now:
                reclaim_level = ema21_now
                reclaim_type = "ema21_reclaim"
                break
            # Swing low reclaim
            if swing_low > 0 and prev_close < swing_low and close > swing_low:
                reclaim_level = swing_low
                reclaim_type = "swing_low_reclaim"
                break

        if reclaim_level is None:
            return None

        return {
            "detected": True,
            "type": reclaim_type,
            "direction": "long",
            "level": round(reclaim_level, 8),
            "close": round(close, 8),
            "body_ratio": round(body_ratio, 3),
            "vol_ratio": round(vol_now / vol_avg if vol_avg > 0 else 0, 3),
            "phase": phase,
        }

    else:  # short
        bearish = close < open_
        if not bearish:
            return None

        reclaim_level = None
        reclaim_type = None
        for i in range(1, check_range + 1):
            prev_close = float(df_15m["close"].iloc[-(i + 1)])
            prev_ema = float(ema21.iloc[-(i + 1)])
            # EMA21 reclaim: was above, now below
            if prev_close > prev_ema and close < ema21_now:
                reclaim_level = ema21_now
                reclaim_type = "ema21_reclaim"
                break
            # Swing high reclaim
            if swing_high > 0 and prev_close > swing_high and close < swing_high:
                reclaim_level = swing_high
                reclaim_type = "swing_high_reclaim"
                break

        if reclaim_level is None:
            return None

        return {
            "detected": True,
            "type": reclaim_type,
            "direction": "short",
            "level": round(reclaim_level, 8),
            "close": round(close, 8),
            "body_ratio": round(body_ratio, 3),
            "vol_ratio": round(vol_now / vol_avg if vol_avg > 0 else 0, 3),
            "phase": phase,
        }


def select_lane(
    *,
    entry_type: str | None,
    regime: str,
    expansion_phase: str,
    sweep: dict | None,
    squeeze: dict | None = None,
    contract_ctx: dict | None,
    config: dict,
) -> LaneResult | None:
    """Select the appropriate scoring lane based on market context.

    Priority:
      1. Sweep detected -> Lane C (Sweep Recovery)
      2. reversal_impulse + vol expansion -> Lane C
      3. Squeeze impulse detected -> Lane E (Squeeze Impulse)
      4. breakout_retest -> Lane B (Breakout)
      5. pullback + trend -> Lane A (Trend)
      6. Default -> Lane A with MR threshold
    """
    if not config.get("enabled", False):
        return None

    et = str(entry_type or "").strip().lower()
    reg = str(regime or "neutral").strip().lower()
    phase = str(expansion_phase or "COMPRESSION").strip().upper()

    thresh_a = int(config.get("lane_a_threshold", 75) or 75)
    thresh_b = int(config.get("lane_b_threshold", 65) or 65)
    thresh_c = int(config.get("lane_c_threshold", 50) or 50)
    atr_bypass = bool(config.get("lane_c_atr_bypass", True))
    atr_bypass_b = bool(config.get("lane_b_atr_bypass", False))

    # --- Lane C: Sweep Recovery ---
    if sweep and sweep.get("detected"):
        return LaneResult(
            lane="C",
            label="sweep_recovery",
            threshold=thresh_c,
            rescore_as="reversal_impulse",
            atr_gate_bypass=atr_bypass,
            reason=f"sweep_{sweep.get('type', 'unknown')}_at_{sweep.get('level', '?')}",
        )

    # Lane C fallback: reversal_impulse entry during vol expansion/ignition
    if et == "reversal_impulse" and phase in ("IGNITION", "EXPANSION"):
        return LaneResult(
            lane="C",
            label="sweep_recovery",
            threshold=thresh_c,
            rescore_as=None,  # already scored as RI by v4_engine
            atr_gate_bypass=atr_bypass,
            reason=f"reversal_impulse_during_{phase.lower()}",
        )

    # --- Lane E: Squeeze Impulse ---
    thresh_e = int(config.get("lane_e_threshold", 55) or 55)
    dist_bypass = bool(config.get("lane_e_distance_bypass", True))
    if squeeze and squeeze.get("detected"):
        return LaneResult(
            lane="E",
            label="squeeze_impulse",
            threshold=thresh_e,
            rescore_as="reversal_impulse",
            atr_gate_bypass=False,
            distance_gate_bypass=dist_bypass,
            reason=f"squeeze_{squeeze.get('type', 'unknown')}_at_{squeeze.get('level', '?')}",
        )

    # --- Lane G: Compression Range (mean reversion inside the box) ---
    thresh_g = int(config.get("lane_g_threshold", 40) or 40)
    if et == "compression_range" and phase == "COMPRESSION":
        return LaneResult(
            lane="G",
            label="compression_range",
            threshold=thresh_g,
            rescore_as="reversal_impulse",
            atr_gate_bypass=True,
            distance_gate_bypass=True,
            reason="compression_range_scalp",
        )

    # --- Lane F: Compression Breakout ---
    thresh_f = int(config.get("lane_f_threshold", 60) or 60)
    dist_bypass_f = bool(config.get("lane_f_distance_bypass", True))
    if et == "compression_breakout" and phase in ("IGNITION", "EXPANSION"):
        return LaneResult(
            lane="F",
            label="compression_breakout",
            threshold=thresh_f,
            rescore_as=None,
            atr_gate_bypass=False,
            distance_gate_bypass=dist_bypass_f,
            reason=f"compression_breakout_in_{phase.lower()}",
        )

    # --- Early Impulse: routes to Lane A/B (high threshold, no structure) ---
    if et == "early_impulse":
        if reg == "trend":
            return LaneResult(
                lane="A",
                label="trend",
                threshold=thresh_a,
                rescore_as=None,
                atr_gate_bypass=False,
                reason="early_impulse_in_trend",
            )
        else:
            return LaneResult(
                lane="B",
                label="breakout",
                threshold=thresh_b,
                rescore_as=None,
                atr_gate_bypass=atr_bypass_b,
                reason="early_impulse_in_mr",
            )

    # --- Lane H: Trend Structure (structure-confirmed continuation) ---
    thresh_h = int(config.get("lane_h_threshold", 45) or 45)
    if et == "trend_continuation" and bool(config.get("lane_h_enabled", True)):
        return LaneResult(
            lane="H",
            label="trend_structure",
            threshold=thresh_h,
            rescore_as=None,
            atr_gate_bypass=True,
            distance_gate_bypass=False,
            reason="trend_continuation_structure",
        )

    # --- Lane I: Fib Retrace (countertrend retracement entries) ---
    thresh_i = int(config.get("lane_i_threshold", 45) or 45)
    if et == "fib_retrace" and bool(config.get("lane_i_enabled", True)):
        return LaneResult(
            lane="I",
            label="fib_retrace",
            threshold=thresh_i,
            rescore_as="reversal_impulse",
            atr_gate_bypass=True,
            distance_gate_bypass=True,
            reason="fib_retrace_entry",
        )

    # --- Lane J: Slow Bleed Hunter ---
    if et == "slow_bleed_hunter":
        thresh_j = int(config.get("lane_j_threshold", 35) or 35)
        return LaneResult(
            lane="J",
            label="slow_bleed",
            threshold=thresh_j,
            rescore_as=None,
            atr_gate_bypass=True,
            distance_gate_bypass=True,
            reason="slow_bleed_detection",
        )

    # --- Lane K: Wick Rejection at Structure ---
    if et == "wick_rejection" and bool(config.get("lane_k_enabled", True)):
        thresh_k = int(config.get("lane_k_threshold", 50) or 50)
        return LaneResult(
            lane="K",
            label="wick_rejection",
            threshold=thresh_k,
            rescore_as="reversal_impulse",
            atr_gate_bypass=True,
            distance_gate_bypass=True,
            reason="wick_rejection_at_structure",
        )

    # --- Lane M: Volume Climax Reversal ---
    if et == "volume_climax_reversal" and bool(config.get("lane_m_enabled", True)):
        thresh_m = int(config.get("lane_m_threshold", 55) or 55)
        return LaneResult(
            lane="M",
            label="volume_climax",
            threshold=thresh_m,
            rescore_as="reversal_impulse",
            atr_gate_bypass=True,
            distance_gate_bypass=True,
            reason="volume_climax_reversal",
        )

    # --- Lane N: VWAP Reversion ---
    if et == "vwap_reversion" and bool(config.get("lane_n_enabled", True)):
        thresh_n = int(config.get("lane_n_threshold", 50) or 50)
        return LaneResult(
            lane="N",
            label="vwap_reversion",
            threshold=thresh_n,
            rescore_as="reversal_impulse",
            atr_gate_bypass=True,
            distance_gate_bypass=False,
            reason="vwap_reversion_entry",
        )

    # --- Lane P: Grid Range (grid-style mean-reversion at range edges) ---
    # Fires when price is at support/resistance in COMPRESSION with RSI extreme.
    # Mimics grid bot behavior: buy low / sell high within range bounds.
    # Low threshold because range edges are high-probability turns.
    if et == "grid_range" and bool(config.get("lane_p_enabled", True)):
        thresh_p = int(config.get("lane_p_threshold", 35) or 35)
        return LaneResult(
            lane="P",
            label="grid_range",
            threshold=thresh_p,
            rescore_as="reversal_impulse",
            atr_gate_bypass=True,
            distance_gate_bypass=True,
            reason="grid_range_edge_trade",
        )

    # --- Lane Q: Funding Arb Bias ---
    if et == "funding_arb_bias" and bool(config.get("lane_q_enabled", True)):
        thresh_q = int(config.get("lane_q_threshold", 60) or 60)
        return LaneResult(
            lane="Q",
            label="funding_arb",
            threshold=thresh_q,
            rescore_as=None,
            atr_gate_bypass=False,
            distance_gate_bypass=False,
            reason="funding_rate_directional_bias",
        )

    # --- Lane R: Regime Low Vol ---
    if et == "regime_low_vol" and bool(config.get("lane_r_enabled", True)):
        thresh_r = int(config.get("lane_r_threshold", 55) or 55)
        return LaneResult(
            lane="R",
            label="regime_low_vol",
            threshold=thresh_r,
            rescore_as="reversal_impulse",
            atr_gate_bypass=True,
            distance_gate_bypass=True,
            reason="low_vol_range_edge_scalp",
        )

    # --- Lane S: Stat Arb Proxy ---
    if et == "stat_arb_proxy" and bool(config.get("lane_s_enabled", True)):
        thresh_s = int(config.get("lane_s_threshold", 50) or 50)
        return LaneResult(
            lane="S",
            label="stat_arb",
            threshold=thresh_s,
            rescore_as="reversal_impulse",
            atr_gate_bypass=True,
            distance_gate_bypass=True,
            reason="zscore_mean_reversion",
        )

    # --- Lane T: Orderflow Imbalance ---
    if et == "orderflow_imbalance" and bool(config.get("lane_t_enabled", True)):
        thresh_t = int(config.get("lane_t_threshold", 65) or 65)
        return LaneResult(
            lane="T",
            label="orderflow",
            threshold=thresh_t,
            rescore_as=None,
            atr_gate_bypass=False,
            distance_gate_bypass=False,
            reason="volume_delta_imbalance",
        )

    # --- Lane U: Macro MA Cross ---
    if et == "macro_ma_cross" and bool(config.get("lane_u_enabled", True)):
        thresh_u = int(config.get("lane_u_threshold", 45) or 45)
        return LaneResult(
            lane="U",
            label="macro_ma",
            threshold=thresh_u,
            rescore_as=None,
            atr_gate_bypass=False,
            distance_gate_bypass=False,
            reason="200ma_breakout_higher_tf",
        )

    # --- Lane B: Breakout ---
    if et == "breakout_retest":
        return LaneResult(
            lane="B",
            label="breakout",
            threshold=thresh_b,
            rescore_as=None,
            atr_gate_bypass=atr_bypass_b,
            reason="breakout_retest_entry",
        )

    # --- Lane A: Trend Continuation ---
    if et == "pullback" and reg == "trend":
        return LaneResult(
            lane="A",
            label="trend",
            threshold=thresh_a,
            rescore_as=None,
            atr_gate_bypass=False,
            reason="pullback_in_trend",
        )

    # Default: Lane A with regime-appropriate threshold
    mr_thresh = int(config.get("lane_a_mr_threshold", 70) or 70)
    default_thresh = thresh_a if reg == "trend" else mr_thresh

    return LaneResult(
        lane="A",
        label="trend" if reg == "trend" else "mean_reversion",
        threshold=default_thresh,
        rescore_as=None,
        atr_gate_bypass=False,
        reason=f"default_{reg}",
    )


# -- Lane Regime Classification ------------------------------------------------
# Maps each lane to one of: "trend", "mr", "breakout".
# Used by auto-regime mutex to prevent lane collision (e.g. Lane A says buy
# while Lane M says sell simultaneously).

LANE_REGIME_MAP: dict[str, str] = {
    "A": "trend",       # Trend Continuation
    "H": "trend",       # Trend Structure
    "Q": "trend",       # Funding Arb Bias (directional)
    "T": "trend",       # Orderflow Imbalance (directional)
    "U": "trend",       # Macro MA Cross (200 MA)
    "B": "breakout",    # Breakout Retest
    "C": "breakout",    # Sweep Recovery
    "D": "breakout",    # Moonshot
    "E": "breakout",    # Squeeze Impulse
    "F": "breakout",    # Compression Breakout
    "G": "mr",          # Compression Range
    "I": "mr",          # Fib Retrace
    "J": "mr",          # Slow Bleed Hunter
    "K": "mr",          # Wick Rejection
    "M": "mr",          # Volume Climax Reversal
    "N": "mr",          # VWAP Reversion
    "P": "mr",          # Grid Range
    "R": "mr",          # Regime Low Vol
    "S": "mr",          # Stat Arb Proxy
}

# Which lane regimes are allowed under each market regime.
# Breakout lanes always pass -- they have strong independent quality gates.
_ALLOWED_REGIMES: dict[str, set[str]] = {
    "trend":           {"trend", "breakout"},
    "mean_reversion":  {"mr", "breakout"},
    "neutral":         {"trend", "mr", "breakout"},  # no strong signal -- allow all
}


def lane_allowed_by_regime(lane_result: LaneResult | None, market_regime: str) -> bool:
    """Check if a lane is permitted under the current market regime (auto-mutex).

    Returns True if the lane should be allowed, False if blocked.
    """
    if lane_result is None:
        return True  # no lane selected -- nothing to block
    lane_regime = LANE_REGIME_MAP.get(lane_result.lane, "breakout")
    allowed = _ALLOWED_REGIMES.get(market_regime, {"trend", "mr", "breakout"})
    return lane_regime in allowed
