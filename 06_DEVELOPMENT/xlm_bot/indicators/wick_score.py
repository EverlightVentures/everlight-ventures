"""Quantitative wick scoring engine.

Measures wick-to-body ratios, confirms reclaim/rejection patterns,
and produces a 0-100 score for the liquidation sweep strategy.

Used by Lane V (Liquidity Sweep) and enhances Lane K (Wick Rejection).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass
class WickAnalysis:
    """Result of quantitative wick analysis on a candle."""
    wick_ratio: float          # 0.0-1.0 -- wick length / total range
    wick_type: str             # "lower", "upper", "none"
    wick_length: float         # absolute wick length in price
    body_ratio: float          # body / total range
    score: int                 # 0-100 composite wick quality score
    close_position: str        # "upper_third", "middle_third", "lower_third"
    wick_vs_atr: float         # wick length / ATR
    confirmation: bool         # next candle did NOT break wick extreme
    volume_above_avg: bool     # candle volume > 20-bar average


@dataclass
class ReclaimRejectResult:
    """Whether a reclaim (bullish) or rejection (bearish) is confirmed."""
    reclaim_confirmed: bool
    rejection_confirmed: bool
    level: float
    type: str  # "reclaim_above", "rejection_below", "none"


def analyze_wick(
    df: pd.DataFrame,
    atr_value: float,
    direction: str = "auto",
    config: dict | None = None,
) -> WickAnalysis:
    """Analyze the most recent candle for wick quality.

    Args:
        df: OHLCV DataFrame (needs at least 2 rows for confirmation)
        atr_value: current ATR(14) value
        direction: "long" (check lower wick), "short" (check upper wick),
                   or "auto" (pick the larger wick)
        config: optional overrides for thresholds

    Returns:
        WickAnalysis with score 0-100
    """
    cfg = config or {}
    min_wick_ratio = float(cfg.get("wick_min_ratio", 0.35) or 0.35)
    strong_wick_ratio = float(cfg.get("wick_strong_ratio", 0.50) or 0.50)
    min_wick_atr = float(cfg.get("wick_min_atr", 0.3) or 0.3)

    if df is None or df.empty or len(df) < 2:
        return WickAnalysis(0, "none", 0, 0, 0, "middle_third", 0, False, False)

    candle = df.iloc[-1]
    o = float(candle["open"])
    h = float(candle["high"])
    l = float(candle["low"])
    c = float(candle["close"])
    vol = float(candle.get("volume", 0))

    total_range = h - l
    if total_range <= 0:
        return WickAnalysis(0, "none", 0, 0, 0, "middle_third", 0, False, False)

    body = abs(c - o)
    body_ratio = body / total_range

    lower_wick = min(o, c) - l
    upper_wick = h - max(o, c)

    # Determine which wick to analyze
    if direction == "long":
        wick_length = lower_wick
        wick_type = "lower"
    elif direction == "short":
        wick_length = upper_wick
        wick_type = "upper"
    else:  # auto
        if lower_wick >= upper_wick:
            wick_length = lower_wick
            wick_type = "lower"
        else:
            wick_length = upper_wick
            wick_type = "upper"

    wick_ratio = wick_length / total_range if total_range > 0 else 0
    wick_vs_atr = wick_length / atr_value if atr_value > 0 else 0

    # Close position within candle range
    close_pct = (c - l) / total_range if total_range > 0 else 0.5
    if close_pct >= 0.667:
        close_position = "upper_third"
    elif close_pct <= 0.333:
        close_position = "lower_third"
    else:
        close_position = "middle_third"

    # Volume check: above 20-bar average
    vol_avg = 0.0
    if len(df) >= 20 and "volume" in df.columns:
        vol_avg = float(df["volume"].rolling(20).mean().iloc[-1])
    volume_above_avg = vol > vol_avg if vol_avg > 0 else False

    # Confirmation: check if the current candle did not break a prior wick extreme
    confirmation = True
    if len(df) >= 3:
        prev_candle = df.iloc[-2]
        prev_h = float(prev_candle["high"])
        prev_l = float(prev_candle["low"])
        prev_range = prev_h - prev_l
        prev_lower_wick = min(float(prev_candle["open"]), float(prev_candle["close"])) - prev_l
        prev_upper_wick = prev_h - max(float(prev_candle["open"]), float(prev_candle["close"]))

        if wick_type == "lower" and prev_range > 0:
            prev_wick_ratio = prev_lower_wick / prev_range
            if prev_wick_ratio >= min_wick_ratio:
                confirmation = l >= prev_l
        elif wick_type == "upper" and prev_range > 0:
            prev_wick_ratio = prev_upper_wick / prev_range
            if prev_wick_ratio >= min_wick_ratio:
                confirmation = h <= prev_h

    # Score calculation (0-100)
    score = 0

    # Wick ratio component (0-40 points)
    if wick_ratio >= strong_wick_ratio:
        score += 40
    elif wick_ratio >= min_wick_ratio:
        score += 25
    elif wick_ratio >= 0.20:
        score += 10

    # Wick vs ATR component (0-20 points)
    if wick_vs_atr >= 0.5:
        score += 20
    elif wick_vs_atr >= min_wick_atr:
        score += 12
    elif wick_vs_atr >= 0.15:
        score += 5

    # Close position component (0-15 points)
    if wick_type == "lower" and close_position == "upper_third":
        score += 15
    elif wick_type == "upper" and close_position == "lower_third":
        score += 15
    elif close_position == "middle_third":
        score += 5

    # Volume component (0-10 points)
    if volume_above_avg:
        score += 10

    # Confirmation component (0-15 points)
    if confirmation:
        score += 15

    return WickAnalysis(
        wick_ratio=round(wick_ratio, 4),
        wick_type=wick_type,
        wick_length=round(wick_length, 8),
        body_ratio=round(body_ratio, 4),
        score=min(100, score),
        close_position=close_position,
        wick_vs_atr=round(wick_vs_atr, 3),
        confirmation=confirmation,
        volume_above_avg=volume_above_avg,
    )


def detect_reclaim_reject(
    df: pd.DataFrame,
    sweep_level: float,
    direction: str,
    atr_value: float,
    config: dict | None = None,
) -> ReclaimRejectResult:
    """Detect if price has reclaimed above or rejected below a sweep level.

    For longs (sweep below):
      - Price swept below sweep_level (wick below)
      - Current close is back above sweep_level
      - = reclaim confirmed

    For shorts (sweep above):
      - Price swept above sweep_level (wick above)
      - Current close is back below sweep_level
      - = rejection confirmed
    """
    if df is None or df.empty or sweep_level <= 0:
        return ReclaimRejectResult(False, False, 0, "none")

    candle = df.iloc[-1]
    c = float(candle["close"])
    h = float(candle["high"])
    l = float(candle["low"])

    d = direction.lower().strip()

    if d == "long":
        swept = l < sweep_level
        reclaimed = c > sweep_level
        if swept and reclaimed:
            return ReclaimRejectResult(True, False, sweep_level, "reclaim_above")

    elif d == "short":
        swept = h > sweep_level
        rejected = c < sweep_level
        if swept and rejected:
            return ReclaimRejectResult(False, True, sweep_level, "rejection_below")

    return ReclaimRejectResult(False, False, sweep_level, "none")


def score_for_lane_v(
    wick: WickAnalysis,
    reclaim_reject: ReclaimRejectResult,
    cluster_strength: float,
    fib_band_tag: bool,
    ema_vwap_stretch: bool,
    funding_confirms: bool,
    volume_spike: bool,
    config: dict | None = None,
) -> dict[str, Any]:
    """Compute Lane V (Liquidity Sweep) composite score.

    Requires 4 of 6 non-bonus signals to fire (A+ filter).

    Returns:
        dict with score (0-100), pass (bool), signals (dict), mode (str)
    """
    cfg = config or {}
    min_signals = int(cfg.get("min_signals", 4) or 4)
    threshold = int(cfg.get("threshold", 55) or 55)

    w_cluster = int(cfg.get("w_cluster", 20) or 20)
    w_fib = int(cfg.get("w_fib", 15) or 15)
    w_ema_stretch = int(cfg.get("w_ema_stretch", 15) or 15)
    w_wick = int(cfg.get("w_wick", 15) or 15)
    w_reclaim = int(cfg.get("w_reclaim", 15) or 15)
    w_funding = int(cfg.get("w_funding", 10) or 10)
    w_volume = int(cfg.get("w_volume", 10) or 10)

    min_wick_ratio = float(cfg.get("wick_min_ratio", 0.35) or 0.35)

    signals = {
        "cluster_strong": cluster_strength >= 30,
        "fib_band_tag": fib_band_tag,
        "ema_vwap_stretch": ema_vwap_stretch,
        "large_wick": wick.wick_ratio >= min_wick_ratio,
        "reclaim_reject": reclaim_reject.reclaim_confirmed or reclaim_reject.rejection_confirmed,
        "funding_confirms": funding_confirms,
        "volume_spike": volume_spike,
    }

    # Core signals (non-bonus) -- need min_signals of these
    core_signals = {k: v for k, v in signals.items() if k not in ("funding_confirms", "volume_spike")}
    core_count = sum(1 for v in core_signals.values() if v)

    score = 0
    if signals["cluster_strong"]:
        score += int(min(w_cluster, cluster_strength * w_cluster / 100))
    if signals["fib_band_tag"]:
        score += w_fib
    if signals["ema_vwap_stretch"]:
        score += w_ema_stretch
    if signals["large_wick"]:
        wick_factor = min(1.0, wick.score / 70)
        score += int(w_wick * wick_factor)
    if signals["reclaim_reject"]:
        score += w_reclaim
    if signals["funding_confirms"]:
        score += w_funding
    if signals["volume_spike"]:
        score += w_volume

    if reclaim_reject.reclaim_confirmed or reclaim_reject.rejection_confirmed:
        mode = "reversal"
    else:
        mode = "continuation"

    passed = score >= threshold and core_count >= min_signals

    return {
        "score": min(100, score),
        "threshold": threshold,
        "pass": passed,
        "signals": signals,
        "core_count": core_count,
        "min_signals": min_signals,
        "mode": mode,
        "wick_score": wick.score,
        "wick_ratio": wick.wick_ratio,
        "wick_type": wick.wick_type,
    }
