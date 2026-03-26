"""Candlestick Pattern Detection Engine v2 - Multi-TF + Context-Aware.

Detects 25 core candlestick patterns PLUS 30 context-aware doji strategies.
Scans ALL timeframes (15m, 1h, 4h, daily, weekly, monthly).
Every pattern is scored for BOTH long and short with equal weight.

Confirmation layer per pattern type:
  - Reversals: RSI + Volume confirmation
  - Continuations: MA alignment + BB squeeze
  - Doji: Context-aware (support/resistance/fib/BB/VWAP/EMA)

The short side and long side are EQUAL CITIZENS. No bias, no gates asymmetry.
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
    three_white_soldiers: bool = False
    three_black_crows: bool = False
    dark_cloud_cover: bool = False
    piercing_line: bool = False
    hanging_man: bool = False
    inverted_hammer: bool = False
    bullish_marubozu: bool = False
    bearish_marubozu: bool = False
    spinning_top: bool = False
    three_inside_up: bool = False
    three_inside_down: bool = False
    bullish_harami: bool = False
    bearish_harami: bool = False
    dragonfly_doji: bool = False
    gravestone_doji: bool = False
    tweezer_top: bool = False
    tweezer_bottom: bool = False
    bullish_kicker: bool = False
    bearish_kicker: bool = False

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
    *,
    at_structure_level: bool = False,
    at_fib_zone: bool = False,
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

    # --- Three White Soldiers (bullish) ---
    if (cl0 > o0 and cl1 > o1 and cl2 > o2 and        # all 3 bullish
        cl2 > cl1 > cl0 and                             # each closes higher
        o1 > o0 and o1 < cl0 and                        # bar1 opens within bar0 body
        o2 > o1 and o2 < cl1 and                        # bar2 opens within bar1 body
        body0 > 0 and body1 > 0 and body2 > 0):
        uw0 = h0 - cl0
        uw1 = h1 - cl1
        uw2_sol = h2 - cl2
        if uw0 < body0 * 0.3 and uw1 < body1 * 0.3 and uw2_sol < body2 * 0.3:
            result.three_white_soldiers = True
            result.reasons.append("three_white_soldiers")

    # --- Three Black Crows (bearish) ---
    if (cl0 < o0 and cl1 < o1 and cl2 < o2 and        # all 3 bearish
        cl2 < cl1 < cl0 and                             # each closes lower
        o1 < o0 and o1 > cl0 and                        # bar1 opens within bar0 body
        o2 < o1 and o2 > cl1 and                        # bar2 opens within bar1 body
        body0 > 0 and body1 > 0 and body2 > 0):
        lw0 = cl0 - l0
        lw1 = cl1 - l1
        lw2_crow = cl2 - l2
        if lw0 < body0 * 0.3 and lw1 < body1 * 0.3 and lw2_crow < body2 * 0.3:
            result.three_black_crows = True
            result.reasons.append("three_black_crows")

    # --- Dark Cloud Cover (bearish) ---
    mid1_body = (o1 + cl1) / 2
    if (cl1 > o1 and cl2 < o2 and                      # prev green, current red
        o2 > h1 and                                      # opens above prior high
        cl2 < mid1_body and cl2 > cl1 * 0.99):          # closes below prior midpoint
        result.dark_cloud_cover = True
        result.reasons.append("dark_cloud_cover")

    # --- Piercing Line (bullish) ---
    if (cl1 < o1 and cl2 > o2 and                      # prev red, current green
        o2 < l1 and                                      # opens below prior low
        cl2 > mid1_body and cl2 < o1 * 1.01):           # closes above prior midpoint
        result.piercing_line = True
        result.reasons.append("piercing_line")

    # --- Hanging Man (bearish -- hammer shape at top of uptrend) ---
    if (lower_wick2 > body2 * 2.0 and upper_wick2 < body2 * 0.5 and body2 > 0):
        # Check for uptrend in prior 5 candles
        if len(df) >= 6:
            lookback = df.iloc[-6:-1]
            if float(lookback.iloc[-1]["close"]) > float(lookback.iloc[0]["close"]):
                result.hanging_man = True
                result.reasons.append("hanging_man")

    # --- Inverted Hammer (bullish -- at bottom of downtrend) ---
    if (upper_wick2 > body2 * 2.0 and lower_wick2 < body2 * 0.5 and body2 > 0):
        if len(df) >= 6:
            lookback = df.iloc[-6:-1]
            if float(lookback.iloc[-1]["close"]) < float(lookback.iloc[0]["close"]):
                result.inverted_hammer = True
                result.reasons.append("inverted_hammer")

    # --- Bullish Marubozu (strong bullish, tiny wicks) ---
    if cl2 > o2 and body2 > avg_body * 0.8 and body2 > 0:
        if upper_wick2 < body2 * 0.05 and lower_wick2 < body2 * 0.05:
            result.bullish_marubozu = True
            result.reasons.append("bullish_marubozu")

    # --- Bearish Marubozu (strong bearish, tiny wicks) ---
    if cl2 < o2 and body2 > avg_body * 0.8 and body2 > 0:
        if upper_wick2 < body2 * 0.05 and lower_wick2 < body2 * 0.05:
            result.bearish_marubozu = True
            result.reasons.append("bearish_marubozu")

    # --- Spinning Top (neutral -- small body, long wicks both sides) ---
    if body2 < range2 * 0.25 and range2 > 0:
        if upper_wick2 >= body2 and lower_wick2 >= body2 and body2 > 0:
            result.spinning_top = True
            result.reasons.append("spinning_top")

    # --- Three Inside Up (bullish) ---
    if (cl0 < o0 and body0 > avg_body * 0.6 and       # bar0: bearish, decent size
        cl1 > o1 and                                     # bar1: bullish
        o1 >= cl0 and cl1 <= o0 and                      # bar1 inside bar0 body (harami)
        cl2 > o2 and cl2 > o0):                          # bar2: bullish, closes above bar0 open
        result.three_inside_up = True
        result.reasons.append("three_inside_up")

    # --- Three Inside Down (bearish) ---
    if (cl0 > o0 and body0 > avg_body * 0.6 and       # bar0: bullish, decent size
        cl1 < o1 and                                     # bar1: bearish
        o1 <= cl0 and cl1 >= o0 and                      # bar1 inside bar0 body (harami)
        cl2 < o2 and cl2 < o0):                          # bar2: bearish, closes below bar0 open
        result.three_inside_down = True
        result.reasons.append("three_inside_down")

    # --- Bullish Harami ---
    if (cl1 < o1 and body1 > avg_body * 0.6 and       # bar1: large bearish
        cl2 > o2 and                                     # bar2: bullish
        body2 < body1 * 0.5 and                          # bar2 is small relative to bar1
        o2 >= cl1 and cl2 <= o1):                        # bar2 body inside bar1 body
        result.bullish_harami = True
        result.reasons.append("bullish_harami")

    # --- Bearish Harami ---
    if (cl1 > o1 and body1 > avg_body * 0.6 and       # bar1: large bullish
        cl2 < o2 and                                     # bar2: bearish
        body2 < body1 * 0.5 and                          # bar2 is small relative to bar1
        o2 <= cl1 and cl2 >= o1):                        # bar2 body inside bar1 body
        result.bearish_harami = True
        result.reasons.append("bearish_harami")

    # --- Dragonfly Doji (bullish -- long lower wick, no upper wick) ---
    if body2 < range2 * 0.10 and range2 > 0 and body2 > 0:
        if lower_wick2 > body2 * 3.0 and upper_wick2 < body2 * 1.0:
            result.dragonfly_doji = True
            result.reasons.append("dragonfly_doji")

    # --- Gravestone Doji (bearish -- long upper wick, no lower wick) ---
    if body2 < range2 * 0.10 and range2 > 0 and body2 > 0:
        if upper_wick2 > body2 * 3.0 and lower_wick2 < body2 * 1.0:
            result.gravestone_doji = True
            result.reasons.append("gravestone_doji")

    # --- Tweezer Top (bearish -- matching highs, first bullish second bearish) ---
    if cl1 > o1 and cl2 < o2 and h1 > 0:
        if abs(h2 - h1) / h1 < 0.001:                   # highs within 0.1%
            result.tweezer_top = True
            result.reasons.append("tweezer_top")

    # --- Tweezer Bottom (bullish -- matching lows, first bearish second bullish) ---
    if cl1 < o1 and cl2 > o2 and l1 > 0:
        if abs(l2 - l1) / l1 < 0.001:                   # lows within 0.1%
            result.tweezer_bottom = True
            result.reasons.append("tweezer_bottom")

    # --- Kicker (crypto-adapted -- no true gaps) ---
    # Bullish kicker: bearish bar1, then large bullish bar2 opening at/above bar1 open
    if (cl1 < o1 and cl2 > o2 and body2 > avg_body * 1.0 and
        o2 >= o1):
        result.bullish_kicker = True
        result.reasons.append("bullish_kicker")

    # Bearish kicker: bullish bar1, then large bearish bar2 opening at/below bar1 open
    if (cl1 > o1 and cl2 < o2 and body2 > avg_body * 1.0 and
        o2 <= o1):
        result.bearish_kicker = True
        result.reasons.append("bearish_kicker")

    # --- Compute direction bias and score modifier ---
    bullish_count = sum([
        result.bullish_engulfing,
        result.hammer,
        result.morning_star,
        result.bullish_pin_bar,
        result.three_white_soldiers,
        result.piercing_line,
        result.inverted_hammer,
        result.bullish_marubozu,
        result.three_inside_up,
        result.bullish_harami,
        result.dragonfly_doji,
        result.tweezer_bottom,
        result.bullish_kicker,
    ])
    bearish_count = sum([
        result.bearish_engulfing,
        result.shooting_star,
        result.evening_star,
        result.bearish_pin_bar,
        result.three_black_crows,
        result.dark_cloud_cover,
        result.hanging_man,
        result.bearish_marubozu,
        result.three_inside_down,
        result.bearish_harami,
        result.gravestone_doji,
        result.tweezer_top,
        result.bearish_kicker,
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

    # Location-aware scoring: pattern at key level = stronger signal
    at_key_level = at_structure_level or at_fib_zone
    level_bonus = int(cfg.get("level_bonus_pts", 8) or 8)
    level_penalty = int(cfg.get("level_penalty_extra", 5) or 5)

    if at_key_level and result.score_modifier > 0:
        result.score_modifier += level_bonus
        result.reasons.append("pattern_at_key_level")
    elif at_key_level and result.score_modifier < 0:
        result.score_modifier -= level_penalty
        result.reasons.append("pattern_contradicts_at_level")

    # Doji at key level = indecision, never a positive signal
    if any("doji" in r.lower() for r in result.reasons) and result.score_modifier > 0:
        result.score_modifier = 0
        result.reasons.append("doji_suppressed")

    return result


# ============================================================================
# MULTI-TIMEFRAME CANDLE SCANNER
# ============================================================================

def scan_all_timeframes(
    df_15m: pd.DataFrame = None,
    df_1h: pd.DataFrame = None,
    df_4h: pd.DataFrame = None,
    df_daily: pd.DataFrame = None,
    df_weekly: pd.DataFrame = None,
    df_monthly: pd.DataFrame = None,
    direction: str = "",
    config: dict = None,
    context: dict = None,
) -> dict:
    """Scan candlestick patterns across ALL available timeframes.

    Returns a unified result with per-TF patterns and aggregate scoring.
    Higher timeframes carry more weight (weekly pattern > 15m pattern).

    Args:
        df_*: OHLCV DataFrames for each timeframe
        direction: proposed trade direction
        config: candle_patterns config section
        context: market context dict with keys like:
            price, support, resistance, fib_levels, bb_upper, bb_lower,
            bb_mid, ema21, ema50, ema200, vwap, rsi, atr, volume_ratio
    """
    cfg = config or {}
    ctx = context or {}
    results = {}
    tf_weights = {
        "15m": 1.0, "1h": 1.5, "4h": 2.0,
        "daily": 3.0, "weekly": 4.0, "monthly": 5.0,
    }
    frames = {
        "15m": df_15m, "1h": df_1h, "4h": df_4h,
        "daily": df_daily, "weekly": df_weekly, "monthly": df_monthly,
    }

    total_bull_score = 0.0
    total_bear_score = 0.0
    all_patterns = []

    for tf_name, df in frames.items():
        if df is None or df.empty or len(df) < 3:
            continue
        w = tf_weights.get(tf_name, 1.0)
        cp = detect_candle_patterns(df, direction, cfg)
        results[tf_name] = cp

        # Weight the bias by timeframe importance
        bull_count = sum([
            cp.bullish_engulfing, cp.hammer, cp.morning_star, cp.bullish_pin_bar,
            cp.three_white_soldiers, cp.piercing_line, cp.inverted_hammer,
            cp.bullish_marubozu, cp.three_inside_up, cp.bullish_harami,
            cp.dragonfly_doji, cp.tweezer_bottom, cp.bullish_kicker,
        ])
        bear_count = sum([
            cp.bearish_engulfing, cp.shooting_star, cp.evening_star, cp.bearish_pin_bar,
            cp.three_black_crows, cp.dark_cloud_cover, cp.hanging_man,
            cp.bearish_marubozu, cp.three_inside_down, cp.bearish_harami,
            cp.gravestone_doji, cp.tweezer_top, cp.bearish_kicker,
        ])

        total_bull_score += bull_count * w
        total_bear_score += bear_count * w

        for reason in cp.reasons:
            all_patterns.append({"tf": tf_name, "pattern": reason, "weight": w})

    # Doji context strategies (applied on top of base detection)
    doji_signals = _evaluate_doji_strategies(results, ctx, cfg)

    # Aggregate
    net_bias = "neutral"
    if total_bull_score > total_bear_score * 1.2:
        net_bias = "bullish"
    elif total_bear_score > total_bull_score * 1.2:
        net_bias = "bearish"

    # Compute unified score modifier
    d = direction.lower().strip() if direction else ""
    score_mod = 0
    bonus = int(cfg.get("bonus_pts", 12) or 12)
    penalty = int(cfg.get("penalty_pts", 8) or 8)

    if d == "long" and net_bias == "bullish":
        score_mod = bonus
    elif d == "short" and net_bias == "bearish":
        score_mod = bonus
    elif d == "long" and net_bias == "bearish":
        score_mod = -penalty
    elif d == "short" and net_bias == "bullish":
        score_mod = -penalty

    # Add doji strategy bonus
    for ds in doji_signals:
        if ds["direction"] == d:
            score_mod += ds.get("bonus", 5)
        elif ds["direction"] and ds["direction"] != d:
            score_mod -= ds.get("bonus", 5) // 2

    # HTF alignment bonus: if weekly/monthly agree with direction, extra points
    htf_bonus = int(cfg.get("htf_alignment_bonus", 10) or 10)
    for tf in ["weekly", "monthly"]:
        cp = results.get(tf)
        if cp and cp.has_pattern:
            if d == "long" and cp.direction_bias == "bullish":
                score_mod += htf_bonus
            elif d == "short" and cp.direction_bias == "bearish":
                score_mod += htf_bonus

    return {
        "per_tf": {k: {"bias": v.direction_bias, "patterns": v.reasons, "score_mod": v.score_modifier}
                   for k, v in results.items()},
        "all_patterns": all_patterns,
        "doji_signals": doji_signals,
        "bull_score": round(total_bull_score, 1),
        "bear_score": round(total_bear_score, 1),
        "net_bias": net_bias,
        "score_modifier": max(-25, min(25, score_mod)),
        "pattern_count": len(all_patterns),
    }


# ============================================================================
# 30 DOJI CONTEXT STRATEGIES
# ============================================================================

def _evaluate_doji_strategies(
    tf_results: dict,
    ctx: dict,
    cfg: dict,
) -> list:
    """Evaluate 30 context-aware doji strategies using market context.

    Each strategy checks if a doji was detected on any timeframe AND
    if the market context matches the strategy's conditions.

    Returns list of doji signal dicts with direction, confidence, bonus.
    """
    signals = []
    price = float(ctx.get("price", 0))
    if price <= 0:
        return signals

    support = float(ctx.get("support", 0))
    resistance = float(ctx.get("resistance", 0))
    bb_upper = float(ctx.get("bb_upper", 0))
    bb_lower = float(ctx.get("bb_lower", 0))
    bb_mid = float(ctx.get("bb_mid", 0))
    ema21 = float(ctx.get("ema21", 0))
    ema50 = float(ctx.get("ema50", 0))
    ema200 = float(ctx.get("ema200", 0))
    vwap = float(ctx.get("vwap", 0))
    rsi = float(ctx.get("rsi", 50))
    atr = float(ctx.get("atr", 0))
    vol_ratio = float(ctx.get("volume_ratio", 1.0))
    fib_levels = ctx.get("fib_levels", {})
    weekly_high = float(ctx.get("weekly_high", 0))
    weekly_low = float(ctx.get("weekly_low", 0))
    monthly_high = float(ctx.get("monthly_high", 0))
    monthly_low = float(ctx.get("monthly_low", 0))
    trend_up = bool(ctx.get("trend_up", False))
    trend_down = bool(ctx.get("trend_down", False))
    strong_trend = bool(ctx.get("strong_trend", False))
    squeeze = bool(ctx.get("bb_squeeze", False))
    channel_type = str(ctx.get("channel_type", ""))
    in_range = bool(ctx.get("in_range", False))
    sweep_detected = bool(ctx.get("sweep_detected", False))
    order_block_near = bool(ctx.get("order_block_near", False))

    # Helper: check if any TF has a doji-type pattern
    def _has_doji(tf_name=None):
        if tf_name:
            cp = tf_results.get(tf_name)
            if cp:
                return cp.doji or cp.dragonfly_doji or cp.gravestone_doji or cp.spinning_top
            return False
        for cp in tf_results.values():
            if cp.doji or cp.dragonfly_doji or cp.gravestone_doji or cp.spinning_top:
                return True
        return False

    def _has_dragonfly(tf_name=None):
        if tf_name:
            cp = tf_results.get(tf_name)
            return cp.dragonfly_doji if cp else False
        return any(cp.dragonfly_doji for cp in tf_results.values())

    def _has_gravestone(tf_name=None):
        if tf_name:
            cp = tf_results.get(tf_name)
            return cp.gravestone_doji if cp else False
        return any(cp.gravestone_doji for cp in tf_results.values())

    def _near(a, b, pct=0.003):
        return abs(a - b) / max(a, 0.0001) < pct if a > 0 else False

    # --- 30 Doji Strategies ---

    # 1. Doji at resistance -> short
    if _has_doji() and resistance > 0 and _near(price, resistance):
        signals.append({"id": 1, "name": "doji_at_resistance", "direction": "short",
            "confidence": 72, "bonus": 8, "reason": "Doji at resistance level"})

    # 2. Doji at support -> long
    if _has_doji() and support > 0 and _near(price, support):
        signals.append({"id": 2, "name": "doji_at_support", "direction": "long",
            "confidence": 72, "bonus": 8, "reason": "Doji at support level"})

    # 3. Dragonfly doji at support -> strong long
    if _has_dragonfly() and support > 0 and _near(price, support, 0.005):
        signals.append({"id": 3, "name": "dragonfly_at_support", "direction": "long",
            "confidence": 82, "bonus": 12, "reason": "Dragonfly doji at support - strong reversal"})

    # 4. Gravestone doji at resistance -> strong short
    if _has_gravestone() and resistance > 0 and _near(price, resistance, 0.005):
        signals.append({"id": 4, "name": "gravestone_at_resistance", "direction": "short",
            "confidence": 82, "bonus": 12, "reason": "Gravestone doji at resistance - strong reversal"})

    # 5. Doji after strong trend (exhaustion)
    if _has_doji() and strong_trend:
        d = "short" if trend_up else "long" if trend_down else ""
        if d:
            signals.append({"id": 5, "name": "doji_trend_exhaustion", "direction": d,
                "confidence": 70, "bonus": 8, "reason": f"Doji exhaustion after strong {'up' if trend_up else 'down'}trend"})

    # 6. Doji in overbought RSI -> short
    if _has_doji() and rsi > 70:
        signals.append({"id": 6, "name": "doji_overbought", "direction": "short",
            "confidence": 68, "bonus": 7, "reason": f"Doji with RSI {rsi:.0f} overbought"})

    # 7. Doji in oversold RSI -> long
    if _has_doji() and rsi < 30:
        signals.append({"id": 7, "name": "doji_oversold", "direction": "long",
            "confidence": 68, "bonus": 7, "reason": f"Doji with RSI {rsi:.0f} oversold"})

    # 8. Doji inside triangle/squeeze -> breakout anticipation
    if _has_doji() and squeeze:
        signals.append({"id": 8, "name": "doji_in_squeeze", "direction": "",
            "confidence": 60, "bonus": 5, "reason": "Doji in BB squeeze - breakout imminent"})

    # 9. Doji at double top -> short
    if _has_doji() and resistance > 0 and _near(price, resistance, 0.002):
        # Check if this is a retest (2nd touch)
        signals.append({"id": 9, "name": "doji_double_top", "direction": "short",
            "confidence": 75, "bonus": 10, "reason": "Doji at potential double top"})

    # 10. Doji at double bottom -> long
    if _has_doji() and support > 0 and _near(price, support, 0.002):
        signals.append({"id": 10, "name": "doji_double_bottom", "direction": "long",
            "confidence": 75, "bonus": 10, "reason": "Doji at potential double bottom"})

    # 11. Morning doji star (check 1h+)
    for tf in ["1h", "4h", "daily"]:
        cp = tf_results.get(tf)
        if cp and cp.morning_star and cp.doji:
            signals.append({"id": 11, "name": "morning_doji_star", "direction": "long",
                "confidence": 80, "bonus": 12, "reason": f"Morning doji star on {tf}"})
            break

    # 12. Evening doji star
    for tf in ["1h", "4h", "daily"]:
        cp = tf_results.get(tf)
        if cp and cp.evening_star and cp.doji:
            signals.append({"id": 12, "name": "evening_doji_star", "direction": "short",
                "confidence": 80, "bonus": 12, "reason": f"Evening doji star on {tf}"})
            break

    # 13. Doji in descending channel -> short at upper channel
    if _has_doji() and channel_type == "descending" and bb_upper > 0 and _near(price, bb_upper, 0.005):
        signals.append({"id": 13, "name": "doji_channel_rejection", "direction": "short",
            "confidence": 72, "bonus": 8, "reason": "Doji at upper channel in downtrend"})

    # 14. Doji in ascending channel -> long at lower channel
    if _has_doji() and channel_type == "ascending" and bb_lower > 0 and _near(price, bb_lower, 0.005):
        signals.append({"id": 14, "name": "doji_channel_support", "direction": "long",
            "confidence": 72, "bonus": 8, "reason": "Doji at lower channel in uptrend"})

    # 15. Doji at monthly support/resistance
    if _has_doji("weekly") or _has_doji("monthly"):
        if monthly_high > 0 and _near(price, monthly_high, 0.005):
            signals.append({"id": 15, "name": "doji_monthly_resistance", "direction": "short",
                "confidence": 85, "bonus": 15, "reason": "Doji at monthly resistance - high weight"})
        if monthly_low > 0 and _near(price, monthly_low, 0.005):
            signals.append({"id": 15, "name": "doji_monthly_support", "direction": "long",
                "confidence": 85, "bonus": 15, "reason": "Doji at monthly support - high weight"})

    # 16. Doji after breakout retest
    if _has_doji() and sweep_detected:
        signals.append({"id": 16, "name": "doji_breakout_retest", "direction": "",
            "confidence": 65, "bonus": 6, "reason": "Doji on breakout retest"})

    # 17. Doji at Fibonacci level
    for fib_name, fib_price in (fib_levels.items() if isinstance(fib_levels, dict) else []):
        fp = float(fib_price) if fib_price else 0
        if fp > 0 and _has_doji() and _near(price, fp, 0.003):
            d = "long" if price <= fp else "short"
            signals.append({"id": 17, "name": f"doji_at_fib_{fib_name}", "direction": d,
                "confidence": 74, "bonus": 9, "reason": f"Doji at Fib {fib_name} ({fp:.6f})"})
            break

    # 18. Doji after stop hunt / sweep
    if _has_doji() and sweep_detected:
        d = "long" if trend_down else "short" if trend_up else ""
        if d:
            signals.append({"id": 18, "name": "doji_stop_hunt_fade", "direction": d,
                "confidence": 76, "bonus": 10, "reason": "Doji after liquidity sweep - fade the spike"})

    # 19. Doji at VWAP
    if _has_doji() and vwap > 0 and _near(price, vwap, 0.003):
        d = "long" if price >= vwap else "short"
        signals.append({"id": 19, "name": "doji_at_vwap", "direction": d,
            "confidence": 66, "bonus": 6, "reason": f"Doji at VWAP ({vwap:.6f})"})

    # 20. Doji at 200 EMA
    if _has_doji() and ema200 > 0 and _near(price, ema200, 0.005):
        d = "long" if trend_down else "short" if trend_up else ""
        if d:
            signals.append({"id": 20, "name": "doji_at_ema200", "direction": d,
                "confidence": 78, "bonus": 10, "reason": f"Doji at 200 EMA - major level"})

    # 21. Doji confirming trend continuation
    if _has_doji() and not strong_trend:
        if trend_up and rsi > 45 and rsi < 65:
            signals.append({"id": 21, "name": "doji_trend_pause_long", "direction": "long",
                "confidence": 62, "bonus": 5, "reason": "Doji pause in uptrend - continuation"})
        elif trend_down and rsi > 35 and rsi < 55:
            signals.append({"id": 21, "name": "doji_trend_pause_short", "direction": "short",
                "confidence": 62, "bonus": 5, "reason": "Doji pause in downtrend - continuation"})

    # 22. Doji inside a flag
    if _has_doji() and channel_type in ("bull_flag", "bear_flag"):
        d = "long" if channel_type == "bull_flag" else "short"
        signals.append({"id": 22, "name": "doji_in_flag", "direction": d,
            "confidence": 68, "bonus": 7, "reason": f"Doji inside {channel_type} - breakout confirmation"})

    # 23. Doji at order block
    if _has_doji() and order_block_near:
        signals.append({"id": 23, "name": "doji_at_order_block", "direction": "",
            "confidence": 70, "bonus": 8, "reason": "Doji at order block level"})

    # 24. Doji at weekly high -> short
    if _has_doji() and weekly_high > 0 and _near(price, weekly_high, 0.004):
        signals.append({"id": 24, "name": "doji_weekly_high", "direction": "short",
            "confidence": 78, "bonus": 10, "reason": "Doji at weekly high - reversal zone"})

    # 25. Doji at weekly low -> long
    if _has_doji() and weekly_low > 0 and _near(price, weekly_low, 0.004):
        signals.append({"id": 25, "name": "doji_weekly_low", "direction": "long",
            "confidence": 78, "bonus": 10, "reason": "Doji at weekly low - reversal zone"})

    # 26. Doji with volume spike -> stronger signal
    if _has_doji() and vol_ratio > 1.5:
        signals.append({"id": 26, "name": "doji_volume_spike", "direction": "",
            "confidence": 70, "bonus": 6, "reason": f"Doji with {vol_ratio:.1f}x volume - high conviction"})

    # 27. Doji at BB lower band -> long
    if _has_doji() and bb_lower > 0 and _near(price, bb_lower, 0.003):
        signals.append({"id": 27, "name": "doji_bb_lower", "direction": "long",
            "confidence": 72, "bonus": 8, "reason": "Doji at BB lower band - mean reversion long"})

    # 28. Doji at BB upper band -> short
    if _has_doji() and bb_upper > 0 and _near(price, bb_upper, 0.003):
        signals.append({"id": 28, "name": "doji_bb_upper", "direction": "short",
            "confidence": 72, "bonus": 8, "reason": "Doji at BB upper band - mean reversion short"})

    # 29. Doji at EMA21 in trend
    if _has_doji() and ema21 > 0 and _near(price, ema21, 0.003):
        if trend_up:
            signals.append({"id": 29, "name": "doji_ema21_pullback_long", "direction": "long",
                "confidence": 68, "bonus": 7, "reason": "Doji at EMA21 pullback in uptrend"})
        elif trend_down:
            signals.append({"id": 29, "name": "doji_ema21_rejection_short", "direction": "short",
                "confidence": 68, "bonus": 7, "reason": "Doji at EMA21 rejection in downtrend"})

    # 30. Long-legged doji in range -> breakout imminent
    if _has_doji() and in_range:
        signals.append({"id": 30, "name": "doji_range_indecision", "direction": "",
            "confidence": 55, "bonus": 4, "reason": "Long-legged doji mid-range - breakout building"})

    return signals


# ============================================================================
# CONFIRMATION LAYER PER PATTERN TYPE
# ============================================================================

def confirm_pattern(
    pattern_type: str,
    direction: str,
    ctx: dict,
) -> dict:
    """Validate a pattern with indicator confirmation.

    Reversals need: RSI extreme + volume
    Continuations need: MA alignment + BB context
    Doji: context-aware (handled by doji strategies above)

    Returns: {"confirmed": bool, "strength": int 0-100, "reasons": []}
    """
    rsi = float(ctx.get("rsi", 50))
    vol_ratio = float(ctx.get("volume_ratio", 1.0))
    ema21 = float(ctx.get("ema21", 0))
    ema50 = float(ctx.get("ema50", 0))
    price = float(ctx.get("price", 0))
    bb_squeeze = bool(ctx.get("bb_squeeze", False))
    atr_expanding = bool(ctx.get("atr_expanding", False))

    result = {"confirmed": False, "strength": 0, "reasons": []}

    # Reversal patterns
    reversal_patterns = {
        "bearish_engulfing", "shooting_star", "evening_star", "dark_cloud_cover",
        "hanging_man", "three_black_crows", "gravestone_doji", "tweezer_top",
        "bearish_kicker", "bearish_harami", "three_inside_down", "bearish_marubozu",
        "bullish_engulfing", "hammer", "morning_star", "piercing_line",
        "inverted_hammer", "three_white_soldiers", "dragonfly_doji", "tweezer_bottom",
        "bullish_kicker", "bullish_harami", "three_inside_up", "bullish_marubozu",
    }

    continuation_patterns = {
        "three_white_soldiers", "three_black_crows", "bullish_marubozu", "bearish_marubozu",
    }

    strength = 0
    reasons = []

    if pattern_type in reversal_patterns:
        # RSI confirmation
        if direction == "long" and rsi < 35:
            strength += 25
            reasons.append("rsi_oversold")
        elif direction == "short" and rsi > 65:
            strength += 25
            reasons.append("rsi_overbought")

        # Volume confirmation
        if vol_ratio >= 1.3:
            strength += 20
            reasons.append("volume_confirms")
        elif vol_ratio >= 1.1:
            strength += 10
            reasons.append("volume_moderate")

        # ATR expanding (breakout energy)
        if atr_expanding:
            strength += 15
            reasons.append("atr_expanding")

    if pattern_type in continuation_patterns:
        # MA alignment
        if direction == "long" and ema21 > ema50 and price > ema21:
            strength += 25
            reasons.append("ma_aligned_bull")
        elif direction == "short" and ema21 < ema50 and price < ema21:
            strength += 25
            reasons.append("ma_aligned_bear")

        # BB squeeze before breakout
        if bb_squeeze:
            strength += 20
            reasons.append("bb_squeeze_ready")

    result["confirmed"] = strength >= 30
    result["strength"] = min(100, strength)
    result["reasons"] = reasons
    return result
