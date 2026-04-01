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
    followthrough_confirmed: bool = False
    body_failure: bool = False
    reclaim_speed_bars: int = 0
    rejection_speed_bars: int = 0
    candidate_offset: int = 0   # bars back from latest candle for chosen sweep bar
    sweep_depth_atr: float = 0.0
    fib_hit: bool = False
    ema_stretch: bool = False
    vwap_stretch: bool = False


@dataclass
class ReclaimRejectResult:
    """Whether a reclaim (bullish) or rejection (bearish) is confirmed."""
    reclaim_confirmed: bool
    rejection_confirmed: bool
    level: float
    type: str  # "reclaim_above", "rejection_below", "none"
    followthrough_confirmed: bool = False
    failed_reclaim: bool = False
    failed_rejection: bool = False
    confirm_bars: int = 0


def analyze_wick(
    df: pd.DataFrame,
    atr_value: float,
    direction: str = "auto",
    config: dict | None = None,
    *,
    fib_hit: bool = False,
    ema_stretch: bool = False,
    vwap_stretch: bool = False,
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
    inspect_bars = max(2, int(cfg.get("wick_inspect_bars", 4) or 4))
    confirm_bars = max(1, int(cfg.get("wick_confirm_bars", 3) or 3))

    if df is None or df.empty or len(df) < 2:
        return WickAnalysis(0, "none", 0, 0, 0, "middle_third", 0, False, False)

    window = df.tail(max(inspect_bars, confirm_bars + 1)).copy()
    best: WickAnalysis | None = None
    best_idx = len(window) - 1

    for idx in range(len(window) - 1, -1, -1):
        candle = window.iloc[idx]
        o = float(candle["open"])
        h = float(candle["high"])
        l = float(candle["low"])
        c = float(candle["close"])
        vol = float(candle.get("volume", 0))

        total_range = h - l
        if total_range <= 0:
            continue

        body = abs(c - o)
        body_ratio = body / total_range

        lower_wick = min(o, c) - l
        upper_wick = h - max(o, c)

        if direction == "long":
            wick_length = lower_wick
            wick_type = "lower"
        elif direction == "short":
            wick_length = upper_wick
            wick_type = "upper"
        else:
            if lower_wick >= upper_wick:
                wick_length = lower_wick
                wick_type = "lower"
            else:
                wick_length = upper_wick
                wick_type = "upper"

        wick_ratio = wick_length / total_range if total_range > 0 else 0
        wick_vs_atr = wick_length / atr_value if atr_value > 0 else 0

        close_pct = (c - l) / total_range if total_range > 0 else 0.5
        if close_pct >= 0.667:
            close_position = "upper_third"
        elif close_pct <= 0.333:
            close_position = "lower_third"
        else:
            close_position = "middle_third"

        vol_avg = 0.0
        if len(df) >= 20 and "volume" in df.columns:
            vol_avg = float(df["volume"].rolling(20).mean().iloc[-1])
        volume_above_avg = vol > vol_avg if vol_avg > 0 else False

        future = window.iloc[idx + 1: idx + 1 + confirm_bars]
        confirmation = True
        followthrough_confirmed = False
        body_failure = False
        reclaim_speed_bars = 0
        rejection_speed_bars = 0

        if not future.empty:
            if wick_type == "lower":
                confirmation = float(future["low"].min()) >= l
                future_closes = future["close"].astype(float)
                future_highs = future["high"].astype(float)
                followthrough_confirmed = bool((future_closes > c).any() or (future_highs > h).any())
                body_failure = bool((future_closes < min(o, c)).any())
                if followthrough_confirmed:
                    for i, row in enumerate(future.itertuples(index=False), 1):
                        if float(getattr(row, "close")) > c:
                            reclaim_speed_bars = i
                            break
            else:
                confirmation = float(future["high"].max()) <= h
                future_closes = future["close"].astype(float)
                future_lows = future["low"].astype(float)
                followthrough_confirmed = bool((future_closes < c).any() or (future_lows < l).any())
                body_failure = bool((future_closes > max(o, c)).any())
                if followthrough_confirmed:
                    for i, row in enumerate(future.itertuples(index=False), 1):
                        if float(getattr(row, "close")) < c:
                            rejection_speed_bars = i
                            break

        score = 0
        if wick_ratio >= strong_wick_ratio:
            score += 32
        elif wick_ratio >= min_wick_ratio:
            score += 22
        elif wick_ratio >= 0.20:
            score += 8

        if wick_vs_atr >= 0.5:
            score += 16
        elif wick_vs_atr >= min_wick_atr:
            score += 10
        elif wick_vs_atr >= 0.15:
            score += 4

        if wick_type == "lower" and close_position == "upper_third":
            score += 12
        elif wick_type == "upper" and close_position == "lower_third":
            score += 12
        elif close_position == "middle_third":
            score += 4

        if volume_above_avg:
            score += 10
        if confirmation:
            score += 8
        if followthrough_confirmed:
            score += 12
        if not body_failure:
            score += 6
        if fib_hit:
            score += 5
        if ema_stretch:
            score += 5
        if vwap_stretch:
            score += 4

        analysis = WickAnalysis(
            wick_ratio=round(wick_ratio, 4),
            wick_type=wick_type,
            wick_length=round(wick_length, 8),
            body_ratio=round(body_ratio, 4),
            score=min(100, score),
            close_position=close_position,
            wick_vs_atr=round(wick_vs_atr, 3),
            confirmation=confirmation,
            volume_above_avg=volume_above_avg,
            followthrough_confirmed=followthrough_confirmed,
            body_failure=body_failure,
            reclaim_speed_bars=reclaim_speed_bars,
            rejection_speed_bars=rejection_speed_bars,
            candidate_offset=(len(window) - 1 - idx),
            sweep_depth_atr=round(wick_vs_atr, 3),
            fib_hit=bool(fib_hit),
            ema_stretch=bool(ema_stretch),
            vwap_stretch=bool(vwap_stretch),
        )
        if best is None or analysis.score > best.score:
            best = analysis
            best_idx = idx

    if best is not None:
        return best
    return WickAnalysis(0, "none", 0, 0, 0, "middle_third", 0, False, False)


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

    cfg = config or {}
    confirm_bars = max(1, int(cfg.get("confirm_bars", 3) or 3))
    fail_buffer_atr = float(cfg.get("fail_buffer_atr", 0.10) or 0.10)
    fail_buffer = atr_value * fail_buffer_atr if atr_value > 0 else 0.0
    window = df.tail(confirm_bars + 1).copy()

    d = direction.lower().strip()
    reclaim_confirmed = False
    rejection_confirmed = False
    followthrough_confirmed = False
    failed_reclaim = False
    failed_rejection = False
    confirm_speed = 0

    for i, candle in enumerate(window.itertuples(index=False), 1):
        c = float(getattr(candle, "close"))
        h = float(getattr(candle, "high"))
        l = float(getattr(candle, "low"))
        if d == "long":
            if l < sweep_level and c > sweep_level and not reclaim_confirmed:
                reclaim_confirmed = True
                confirm_speed = i
            if reclaim_confirmed and c > sweep_level + fail_buffer:
                followthrough_confirmed = True
            if reclaim_confirmed and c < sweep_level - fail_buffer:
                failed_reclaim = True
        elif d == "short":
            if h > sweep_level and c < sweep_level and not rejection_confirmed:
                rejection_confirmed = True
                confirm_speed = i
            if rejection_confirmed and c < sweep_level - fail_buffer:
                followthrough_confirmed = True
            if rejection_confirmed and c > sweep_level + fail_buffer:
                failed_rejection = True

    if d == "long" and reclaim_confirmed:
        return ReclaimRejectResult(
            True,
            False,
            sweep_level,
            "reclaim_above",
            followthrough_confirmed=followthrough_confirmed,
            failed_reclaim=failed_reclaim,
            failed_rejection=False,
            confirm_bars=confirm_speed,
        )
    if d == "short" and rejection_confirmed:
        return ReclaimRejectResult(
            False,
            True,
            sweep_level,
            "rejection_below",
            followthrough_confirmed=followthrough_confirmed,
            failed_reclaim=False,
            failed_rejection=failed_rejection,
            confirm_bars=confirm_speed,
        )
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
        "followthrough": reclaim_reject.followthrough_confirmed or wick.followthrough_confirmed,
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
    if signals["followthrough"]:
        score += min(8, max(4, int(w_reclaim * 0.5)))
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
        "followthrough_confirmed": signals["followthrough"],
        "failed_reclaim": reclaim_reject.failed_reclaim,
        "failed_rejection": reclaim_reject.failed_rejection,
    }
