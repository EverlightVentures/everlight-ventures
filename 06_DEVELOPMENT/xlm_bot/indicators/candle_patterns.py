"""Candlestick pattern detection for v4 scoring.

Detects classic patterns from OHLC data — no new indicators needed.
Returns a dict of pattern flags for the most recent candle(s).

Pure function — operates on existing 15m DataFrame.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass
class CandlePatternResult:
    """Detected candlestick patterns and their directional bias."""
    bullish_engulfing: bool = False
    bearish_engulfing: bool = False
    hammer: bool = False             # bullish reversal (long lower wick)
    shooting_star: bool = False      # bearish reversal (long upper wick)
    doji: bool = False               # indecision
    morning_star: bool = False       # 3-candle bullish reversal
    evening_star: bool = False       # 3-candle bearish reversal
    bullish_pin_bar: bool = False    # rejection of lows
    bearish_pin_bar: bool = False    # rejection of highs

    score_modifier: int = 0          # net bonus/penalty for v4 score
    direction_bias: str = "neutral"  # "bullish" | "bearish" | "neutral"
    reasons: list[str] = field(default_factory=list)

    @property
    def has_pattern(self) -> bool:
        return bool(self.reasons)


def detect_candle_patterns(
    df: pd.DataFrame,
    direction: str = "",
    config: dict | None = None,
) -> CandlePatternResult:
    """Detect candlestick patterns on the last 3 candles.

    Args:
        df: 15m OHLC DataFrame (needs at least 3 rows)
        direction: proposed trade direction ("long" | "short")
        config: optional thresholds

    Returns:
        CandlePatternResult with flags and score modifier.
    """
    cfg = config or {}
    bonus_pts = int(cfg.get("bonus_pts", 5) or 5)
    penalty_pts = int(cfg.get("penalty_pts", 3) or 3)
    result = CandlePatternResult()

    if df is None or df.empty or len(df) < 3:
        return result

    # Get last 3 candles
    c0 = df.iloc[-3]  # 2 bars ago
    c1 = df.iloc[-2]  # previous bar
    c2 = df.iloc[-1]  # current bar

    o2, h2, l2, cl2 = float(c2["open"]), float(c2["high"]), float(c2["low"]), float(c2["close"])
    o1, h1, l1, cl1 = float(c1["open"]), float(c1["high"]), float(c1["low"]), float(c1["close"])
    o0, h0, l0, cl0 = float(c0["open"]), float(c0["high"]), float(c0["low"]), float(c0["close"])

    body2 = abs(cl2 - o2)
    body1 = abs(cl1 - o1)
    body0 = abs(cl0 - o0)
    range2 = h2 - l2
    range1 = h1 - l1

    if range2 <= 0 or range1 <= 0:
        return result

    upper_wick2 = h2 - max(o2, cl2)
    lower_wick2 = min(o2, cl2) - l2

    # Average body from last 10 candles for relative sizing
    if len(df) >= 10:
        recent = df.tail(10)
        avg_body = float((recent["close"] - recent["open"]).abs().mean())
    else:
        avg_body = body2

    if avg_body <= 0:
        avg_body = body2 if body2 > 0 else range2 * 0.5

    # --- Engulfing ---
    if cl2 > o2 and cl1 < o1:  # current green, previous red
        if body2 > body1 * 1.0 and cl2 > o1 and o2 <= cl1:
            result.bullish_engulfing = True
            result.reasons.append("bullish_engulfing")

    if cl2 < o2 and cl1 > o1:  # current red, previous green
        if body2 > body1 * 1.0 and cl2 < o1 and o2 >= cl1:
            result.bearish_engulfing = True
            result.reasons.append("bearish_engulfing")

    # --- Hammer (bullish) / Shooting Star (bearish) ---
    # Hammer: small body at top, long lower wick (>2x body)
    if lower_wick2 > body2 * 2.0 and upper_wick2 < body2 * 0.5 and body2 > 0:
        result.hammer = True
        result.reasons.append("hammer")

    # Shooting star: small body at bottom, long upper wick (>2x body)
    if upper_wick2 > body2 * 2.0 and lower_wick2 < body2 * 0.5 and body2 > 0:
        result.shooting_star = True
        result.reasons.append("shooting_star")

    # --- Pin Bars (directional wick rejection) ---
    # Bullish pin: lower wick > 60% of range, body in top 30%
    if lower_wick2 > range2 * 0.60 and (max(o2, cl2) > l2 + range2 * 0.70):
        result.bullish_pin_bar = True
        if "hammer" not in result.reasons:
            result.reasons.append("bullish_pin_bar")

    # Bearish pin: upper wick > 60% of range, body in bottom 30%
    if upper_wick2 > range2 * 0.60 and (min(o2, cl2) < l2 + range2 * 0.30):
        result.bearish_pin_bar = True
        if "shooting_star" not in result.reasons:
            result.reasons.append("bearish_pin_bar")

    # --- Doji (body < 10% of range) ---
    if body2 < range2 * 0.10:
        result.doji = True
        result.reasons.append("doji")

    # --- Morning Star (3-bar bullish reversal) ---
    # Bar 0: big red, Bar 1: small body (star), Bar 2: big green closing above Bar 0 midpoint
    if (cl0 < o0 and body0 > avg_body * 0.8 and    # Bar 0: bearish
        body1 < avg_body * 0.4 and                   # Bar 1: small (star)
        cl2 > o2 and body2 > avg_body * 0.6 and     # Bar 2: bullish
        cl2 > (o0 + cl0) / 2):                       # closes above Bar 0 midpoint
        result.morning_star = True
        result.reasons.append("morning_star")

    # --- Evening Star (3-bar bearish reversal) ---
    # Bar 0: big green, Bar 1: small body, Bar 2: big red closing below Bar 0 midpoint
    if (cl0 > o0 and body0 > avg_body * 0.8 and    # Bar 0: bullish
        body1 < avg_body * 0.4 and                   # Bar 1: small (star)
        cl2 < o2 and body2 > avg_body * 0.6 and     # Bar 2: bearish
        cl2 < (o0 + cl0) / 2):                       # closes below Bar 0 midpoint
        result.evening_star = True
        result.reasons.append("evening_star")

    # --- Compute direction bias and score modifier ---
    bullish_count = sum([
        result.bullish_engulfing,
        result.hammer,
        result.morning_star,
        result.bullish_pin_bar,
    ])
    bearish_count = sum([
        result.bearish_engulfing,
        result.shooting_star,
        result.evening_star,
        result.bearish_pin_bar,
    ])

    if bullish_count > bearish_count:
        result.direction_bias = "bullish"
    elif bearish_count > bullish_count:
        result.direction_bias = "bearish"
    else:
        result.direction_bias = "neutral"

    # Score modifier: patterns that confirm trade direction = bonus
    d = direction.lower().strip() if direction else ""
    if d == "long" and result.direction_bias == "bullish":
        result.score_modifier = bonus_pts
    elif d == "short" and result.direction_bias == "bearish":
        result.score_modifier = bonus_pts
    elif d == "long" and result.direction_bias == "bearish":
        result.score_modifier = -penalty_pts
    elif d == "short" and result.direction_bias == "bullish":
        result.score_modifier = -penalty_pts

    return result
