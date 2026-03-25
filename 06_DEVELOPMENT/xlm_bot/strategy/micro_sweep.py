"""5m Micro-Sweep Detector.

Catches fast liquidation-style wick flushes on the 5m timeframe that
collapse into a single noisy 15m bar.  The detector looks for:

1. A large downside (or upside) wick relative to ATR and candle range
2. Immediate reclaim: close back above the swept level within 1-2 bars
3. Volume adequate (not a thin air wick)
4. HTF context is not directly hostile

If the 5m event passes, it is promoted into a valid entry candidate
compatible with the existing lane system.

Used by main.py to supplement the 15m-driven wick_rejection and
liquidity_sweep lanes.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from indicators.wick_score import WickAnalysis, analyze_wick


@dataclass
class MicroSweepResult:
    """Result of a 5m micro-sweep scan."""
    detected: bool
    direction: str              # "long" or "short"
    score: int                  # 0-100 composite quality
    sweep_low: float            # wick extreme (low for longs, high for shorts)
    reclaim_price: float        # close that reclaimed the level
    swept_level: float          # the level that was pierced
    wick_ratio: float           # wick / total range of sweep candle
    wick_vs_atr: float          # wick length / ATR
    reclaim_bars: int           # how many 5m bars until reclaim
    volume_ok: bool             # volume >= threshold
    htf_hostile: bool           # True if 15m/1h context opposes
    reason: str                 # human-readable tag
    wick_analysis: WickAnalysis | None = None


_EMPTY = MicroSweepResult(
    detected=False, direction="", score=0, sweep_low=0, reclaim_price=0,
    swept_level=0, wick_ratio=0, wick_vs_atr=0, reclaim_bars=0,
    volume_ok=False, htf_hostile=False, reason="no_signal",
)


def detect_micro_sweep(
    df_5m: pd.DataFrame,
    df_15m: pd.DataFrame,
    df_1h: pd.DataFrame,
    direction: str,
    config: dict | None = None,
) -> MicroSweepResult:
    """Scan the last N 5m candles for a liquidation-style wick + reclaim.

    Args:
        df_5m:  5-minute OHLCV DataFrame (needs >= 12 rows)
        df_15m: 15-minute OHLCV for HTF context validation
        df_1h:  1-hour OHLCV for HTF context validation
        direction: "long" or "short"
        config: optional micro_sweep config overrides

    Returns:
        MicroSweepResult -- .detected=True when a valid setup is found.
    """
    if df_5m is None or df_5m.empty or len(df_5m) < 6:
        return _EMPTY

    cfg = config or {}
    d = direction.lower().strip()

    # --- Thresholds (tunable via config.yaml micro_sweep section) ---
    min_wick_ratio = float(cfg.get("min_wick_ratio", 0.40) or 0.40)
    min_wick_atr = float(cfg.get("min_wick_atr", 0.50) or 0.50)
    max_reclaim_bars = int(cfg.get("max_reclaim_bars", 3) or 3)
    min_volume_mult = float(cfg.get("min_volume_mult", 0.8) or 0.8)
    lookback = int(cfg.get("lookback_bars", 6) or 6)
    min_score = int(cfg.get("min_score", 50) or 50)
    max_chase_atr = float(cfg.get("max_chase_atr", 1.5) or 1.5)

    # --- Compute 5m ATR ---
    atr_series = _atr(df_5m, 14)
    if atr_series is None or atr_series.empty:
        return _EMPTY
    atr_val = float(atr_series.iloc[-1])
    if atr_val <= 0:
        return _EMPTY

    # --- Volume baseline ---
    vol_avg = 0.0
    if "volume" in df_5m.columns and len(df_5m) >= 20:
        vol_avg = float(df_5m["volume"].rolling(20).mean().iloc[-1])

    # --- Scan recent 5m candles for sweep candidate ---
    window = df_5m.tail(lookback + 2).copy()
    best: MicroSweepResult | None = None

    for offset in range(1, min(lookback + 1, len(window))):
        candle = window.iloc[-(offset + 1)]  # candidate sweep candle
        o = float(candle["open"])
        h = float(candle["high"])
        l = float(candle["low"])
        c = float(candle["close"])
        vol = float(candle.get("volume", 0))
        total_range = h - l
        if total_range <= 0:
            continue

        # Compute wick metrics
        if d == "long":
            wick_length = min(o, c) - l
            wick_type = "lower"
            swept_level = l
        else:
            wick_length = h - max(o, c)
            wick_type = "upper"
            swept_level = h

        wick_ratio = wick_length / total_range
        wick_vs_atr = wick_length / atr_val if atr_val > 0 else 0

        # Filter: wick must be significant
        if wick_ratio < min_wick_ratio:
            continue
        if wick_vs_atr < min_wick_atr:
            continue

        # Volume check
        volume_ok = vol >= vol_avg * min_volume_mult if vol_avg > 0 else True

        # --- Check reclaim in subsequent bars ---
        reclaim_confirmed = False
        reclaim_bars = 0
        reclaim_price = 0.0

        # Look at bars AFTER the sweep candle
        future_start = len(window) - offset
        future_end = min(future_start + max_reclaim_bars, len(window))
        for j in range(future_start, future_end):
            bar = window.iloc[j]
            bar_c = float(bar["close"])
            bar_h = float(bar["high"])
            bar_l = float(bar["low"])
            reclaim_bars = j - future_start + 1

            if d == "long":
                # Reclaim: close back above the body of the sweep candle
                body_top = max(o, c)
                if bar_c > body_top:
                    reclaim_confirmed = True
                    reclaim_price = bar_c
                    break
                # Also accept if close is above the midpoint and wick held
                if bar_c > (l + total_range * 0.5) and bar_l >= l:
                    reclaim_confirmed = True
                    reclaim_price = bar_c
                    break
            else:
                body_bottom = min(o, c)
                if bar_c < body_bottom:
                    reclaim_confirmed = True
                    reclaim_price = bar_c
                    break
                if bar_c < (h - total_range * 0.5) and bar_h <= h:
                    reclaim_confirmed = True
                    reclaim_price = bar_c
                    break

        if not reclaim_confirmed:
            continue

        # --- Chase guard: current price shouldn't be too far from reclaim level ---
        # Measure from reclaim_price (body top for longs, body bottom for shorts),
        # NOT from the wick extreme. The entry is on the reclaim, not the wick.
        current_price = float(df_5m["close"].iloc[-1])
        reclaim_anchor = max(o, c) if d == "long" else min(o, c)
        if d == "long":
            chase_dist = (current_price - reclaim_anchor) / atr_val if atr_val > 0 else 99
        else:
            chase_dist = (reclaim_anchor - current_price) / atr_val if atr_val > 0 else 99
        if chase_dist > max_chase_atr:
            continue

        # --- Score the setup ---
        score = 0

        # Wick quality (0-35)
        if wick_ratio >= 0.60:
            score += 35
        elif wick_ratio >= 0.50:
            score += 28
        elif wick_ratio >= min_wick_ratio:
            score += 20

        # Wick depth vs ATR (0-20)
        if wick_vs_atr >= 1.0:
            score += 20
        elif wick_vs_atr >= 0.75:
            score += 15
        elif wick_vs_atr >= min_wick_atr:
            score += 10

        # Reclaim speed (0-15)
        if reclaim_bars == 1:
            score += 15
        elif reclaim_bars == 2:
            score += 10
        elif reclaim_bars <= max_reclaim_bars:
            score += 5

        # Volume (0-10)
        if volume_ok:
            if vol_avg > 0 and vol >= vol_avg * 1.5:
                score += 10
            else:
                score += 5

        # Close position of sweep candle (0-10)
        close_pct = (c - l) / total_range if total_range > 0 else 0.5
        if d == "long" and close_pct >= 0.65:
            score += 10  # closed in upper third = strong rejection
        elif d == "short" and close_pct <= 0.35:
            score += 10
        elif 0.35 <= close_pct <= 0.65:
            score += 3

        # Freshness bonus (0-10)
        if offset <= 2:
            score += 10
        elif offset <= 4:
            score += 5

        # --- HTF context check ---
        htf_hostile = _check_htf_hostile(df_15m, df_1h, d, atr_val)
        if htf_hostile:
            score -= 15  # penalize but don't auto-reject

        # --- Use wick_score module for enriched analysis ---
        wick_analysis = None
        try:
            # Analyze the sweep candle window
            sweep_window = window.iloc[-(offset + 2):]
            wick_analysis = analyze_wick(
                sweep_window, atr_val, direction=d,
                config={"wick_inspect_bars": 3, "wick_confirm_bars": 2},
            )
            # Bonus from wick_score module
            if wick_analysis.score >= 60:
                score += 5
            if wick_analysis.followthrough_confirmed:
                score += 5
        except Exception:
            pass

        score = max(0, min(100, score))

        result = MicroSweepResult(
            detected=score >= min_score,
            direction=d,
            score=score,
            sweep_low=l if d == "long" else h,
            reclaim_price=reclaim_price,
            swept_level=swept_level,
            wick_ratio=round(wick_ratio, 4),
            wick_vs_atr=round(wick_vs_atr, 3),
            reclaim_bars=reclaim_bars,
            volume_ok=volume_ok,
            htf_hostile=htf_hostile,
            reason=f"micro_sweep_{d}_{wick_type}_wick",
            wick_analysis=wick_analysis,
        )

        if best is None or result.score > best.score:
            best = result

    return best if best is not None and best.detected else _EMPTY


def _check_htf_hostile(
    df_15m: pd.DataFrame,
    df_1h: pd.DataFrame,
    direction: str,
    atr_5m: float,
) -> bool:
    """Check if 15m/1h trend is directly hostile to the micro-sweep direction.

    Returns True only for STRONG opposition -- mild chop is not hostile.
    """
    if df_15m is None or df_15m.empty or len(df_15m) < 21:
        return False
    if df_1h is None or df_1h.empty or len(df_1h) < 21:
        return False

    try:
        # 15m EMA slope
        e21_15 = df_15m["close"].ewm(span=21, adjust=False).mean()
        slope_15 = float(e21_15.diff().tail(3).mean())

        # 1h EMA slope
        e21_1h = df_1h["close"].ewm(span=21, adjust=False).mean()
        slope_1h = float(e21_1h.diff().tail(3).mean())

        # RSI check (strong overbought for longs = hostile, strong oversold for shorts = hostile)
        # Wait, actually: if we're catching a LONG after a flush, RSI being LOW is fine.
        # Hostile = RSI > 70 for longs (already overbought, flush was deserved)
        # Hostile = RSI < 30 for shorts (already oversold, flush was deserved)
        delta = df_15m["close"].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss.replace(0, 1e-10)
        rsi = 100 - (100 / (1 + rs))
        rsi_val = float(rsi.iloc[-1])

        if direction == "long":
            # Hostile if both timeframes trending down AND RSI already high (flush was deserved)
            strong_downtrend = slope_15 < 0 and slope_1h < 0
            rsi_hostile = rsi_val > 65
            return strong_downtrend and rsi_hostile
        else:
            strong_uptrend = slope_15 > 0 and slope_1h > 0
            rsi_hostile = rsi_val < 35
            return strong_uptrend and rsi_hostile

    except Exception:
        return False


def _atr(df: pd.DataFrame, period: int = 14) -> pd.Series | None:
    """Simple ATR calculation."""
    if df is None or df.empty or len(df) < period + 1:
        return None
    h = df["high"].astype(float)
    l = df["low"].astype(float)
    c = df["close"].astype(float)
    tr = pd.concat([
        h - l,
        (h - c.shift(1)).abs(),
        (l - c.shift(1)).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()
