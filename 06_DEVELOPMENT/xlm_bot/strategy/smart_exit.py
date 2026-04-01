"""Smart Structural Exit Engine v2 -- The Tank.

5-LAYER EXIT ARCHITECTURE:
1. Regime context -- how to behave in each market state
2. Structure map -- scored support/resistance with strength ratings
3. Noise model -- dynamic buffer based on ATR + wicks + regime
4. Confirmation model -- multi-candle confirmation before exit
5. Exit ladder -- HOLD / TRIM / EXIT / REVERSE

PHILOSOPHY:
- A dip to support that bounces is NOT an exit. It is a BUY signal.
- A dip THROUGH support with volume and follow-through IS an exit.
- Winners ride until structure breaks. Losers die when thesis dies.
- The ONLY hard stop is the $10 emergency floor to prevent exchange force-close.
- Everything else is structural.

CONTRACT MATH:
- 1 XLP contract = 5,000 XLM
- $0.01 move = $50/contract, $100 with 2 contracts
- $0.001 move = $5/contract, $10 with 2 contracts
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from indicators.atr import atr
from indicators.rsi import compute_rsi


# ============================================================
# LAYER 1: REGIME CONTEXT
# ============================================================

def classify_regime(df_15m: pd.DataFrame, df_1h: pd.DataFrame | None = None) -> dict:
    """Classify current market regime for exit behavior."""
    if df_15m is None or len(df_15m) < 30:
        return {"regime": "unknown", "buffer_mult": 1.0, "patience": 1.0}

    closes = df_15m["close"].values
    highs = df_15m["high"].values
    lows = df_15m["low"].values

    # EMA slope
    ema_fast = pd.Series(closes).ewm(span=8).mean().values
    ema_slow = pd.Series(closes).ewm(span=21).mean().values
    slope_fast = (ema_fast[-1] - ema_fast[-5]) / max(ema_fast[-5], 1e-9) if len(ema_fast) > 5 else 0
    trending_up = ema_fast[-1] > ema_slow[-1] and slope_fast > 0.001
    trending_down = ema_fast[-1] < ema_slow[-1] and slope_fast < -0.001

    # ATR expansion/contraction
    atr_series = atr(df_15m, 14)
    if not atr_series.empty and len(atr_series) > 10:
        atr_now = float(atr_series.iloc[-1])
        atr_avg = float(atr_series.tail(20).mean())
        atr_ratio = atr_now / max(atr_avg, 1e-9)
    else:
        atr_ratio = 1.0

    # Range detection
    high_20 = float(np.max(highs[-20:]))
    low_20 = float(np.min(lows[-20:]))
    range_pct = (high_20 - low_20) / max(low_20, 1e-9)
    is_tight_range = range_pct < 0.015  # less than 1.5% range = compression

    if atr_ratio > 1.5:
        return {"regime": "breakout_expansion", "buffer_mult": 1.5, "patience": 1.5}
    elif trending_up:
        return {"regime": "trend_up", "buffer_mult": 1.0, "patience": 1.3}
    elif trending_down:
        return {"regime": "trend_down", "buffer_mult": 1.0, "patience": 1.3}
    elif is_tight_range:
        return {"regime": "compression", "buffer_mult": 0.8, "patience": 1.5}
    else:
        return {"regime": "chop", "buffer_mult": 0.7, "patience": 0.8}


# ============================================================
# LAYER 2: STRUCTURE MAP (scored support/resistance)
# ============================================================

def find_scored_supports(df_15m: pd.DataFrame, df_1h: pd.DataFrame | None = None, lookback: int = 60) -> list[dict]:
    """Find support levels with strength scores."""
    if df_15m is None or len(df_15m) < 10:
        return []

    window = df_15m.tail(lookback)
    lows = window["low"].values
    closes = window["close"].values
    volumes = window["volume"].values if "volume" in window.columns else np.ones(len(window))
    avg_vol = float(np.mean(volumes)) if len(volumes) > 0 else 1

    supports = []
    # Find swing lows
    for i in range(2, len(lows) - 2):
        if lows[i] <= lows[i-1] and lows[i] <= lows[i-2] and lows[i] <= lows[i+1] and lows[i] <= lows[i+2]:
            level = float(lows[i])
            score = 0

            # +3 if level was tested multiple times (within 0.1%)
            tests = sum(1 for l in lows if abs(l - level) / max(level, 1e-9) < 0.001)
            if tests >= 3:
                score += 3
            elif tests >= 2:
                score += 2

            # +2 if bounce happened on strong volume
            if volumes[i] > avg_vol * 1.3:
                score += 2

            # +1 if close was above the low (wick = buying pressure)
            if closes[i] > lows[i] * 1.001:
                score += 1

            # +2 if HTF support aligns
            if df_1h is not None and len(df_1h) >= 10:
                htf_lows = df_1h["low"].tail(20).values
                htf_match = any(abs(hl - level) / max(level, 1e-9) < 0.002 for hl in htf_lows)
                if htf_match:
                    score += 2

            # +1 if near EMA
            ema21 = pd.Series(closes).ewm(span=21).mean().values
            if len(ema21) > i and abs(ema21[i] - level) / max(level, 1e-9) < 0.002:
                score += 1

            supports.append({"level": level, "score": score, "tests": tests})

    # Deduplicate close levels (within 0.1%)
    unique = []
    for s in sorted(supports, key=lambda x: -x["score"]):
        if not any(abs(s["level"] - u["level"]) / max(u["level"], 1e-9) < 0.001 for u in unique):
            unique.append(s)

    return sorted(unique, key=lambda x: -x["level"])


def find_scored_resistances(df_15m: pd.DataFrame, df_1h: pd.DataFrame | None = None, lookback: int = 60) -> list[dict]:
    """Find resistance levels with strength scores."""
    if df_15m is None or len(df_15m) < 10:
        return []

    window = df_15m.tail(lookback)
    highs = window["high"].values
    closes = window["close"].values
    volumes = window["volume"].values if "volume" in window.columns else np.ones(len(window))
    avg_vol = float(np.mean(volumes)) if len(volumes) > 0 else 1

    resistances = []
    for i in range(2, len(highs) - 2):
        if highs[i] >= highs[i-1] and highs[i] >= highs[i-2] and highs[i] >= highs[i+1] and highs[i] >= highs[i+2]:
            level = float(highs[i])
            score = 0

            tests = sum(1 for h in highs if abs(h - level) / max(level, 1e-9) < 0.001)
            if tests >= 3:
                score += 3
            elif tests >= 2:
                score += 2

            if volumes[i] > avg_vol * 1.3:
                score += 2

            if closes[i] < highs[i] * 0.999:
                score += 1

            if df_1h is not None and len(df_1h) >= 10:
                htf_highs = df_1h["high"].tail(20).values
                htf_match = any(abs(hh - level) / max(level, 1e-9) < 0.002 for hh in htf_highs)
                if htf_match:
                    score += 2

            ema21 = pd.Series(closes).ewm(span=21).mean().values
            if len(ema21) > i and abs(ema21[i] - level) / max(level, 1e-9) < 0.002:
                score += 1

            resistances.append({"level": level, "score": score, "tests": tests})

    unique = []
    for r in sorted(resistances, key=lambda x: -x["score"]):
        if not any(abs(r["level"] - u["level"]) / max(u["level"], 1e-9) < 0.001 for u in unique):
            unique.append(r)

    return sorted(unique, key=lambda x: x["level"])


# ============================================================
# LAYER 3: NOISE MODEL (dynamic buffer)
# ============================================================

def volume_delta(candle: pd.Series) -> float:
    """Estimate buy vs sell pressure from candle body position.

    Returns -1.0 (pure sell) to +1.0 (pure buy).
    Close near high = buyers dominated. Close near low = sellers dominated.
    """
    o = float(candle["open"])
    h = float(candle["high"])
    l = float(candle["low"])
    c = float(candle["close"])
    rng = h - l
    if rng < 1e-9:
        return 0.0
    # Where did price close relative to the range?
    position = (c - l) / rng  # 0 = closed at low, 1 = closed at high
    return (position - 0.5) * 2  # scale to -1 to +1


def body_to_range_ratio(candle: pd.Series) -> float:
    """Ratio of candle body to total range. 0 = doji, 1 = full body.

    < 0.30 = noise candle (indecision, don't exit)
    > 0.70 = conviction candle (take seriously)
    """
    o = float(candle["open"])
    h = float(candle["high"])
    l = float(candle["low"])
    c = float(candle["close"])
    rng = h - l
    if rng < 1e-9:
        return 0.0
    body = abs(c - o)
    return body / rng


def wick_rejection_count(df_15m: pd.DataFrame, level: float, direction: str, tolerance: float = 0.001) -> int:
    """Count how many times a level was tested (wicked to) and held (closed away from).

    More rejections = stronger level = more patience before calling a break.
    """
    if df_15m is None or len(df_15m) < 5:
        return 0

    count = 0
    window = df_15m.tail(40)
    for _, c in window.iterrows():
        low = float(c["low"])
        high = float(c["high"])
        close = float(c["close"])

        if direction == "long":
            # Wicked near/below support but closed above
            touched = low <= level * (1 + tolerance)
            held = close > level
            if touched and held:
                count += 1
        else:
            # Wicked near/above resistance but closed below
            touched = high >= level * (1 - tolerance)
            held = close < level
            if touched and held:
                count += 1

    return count


def atr_rate_of_change(df_15m: pd.DataFrame) -> float:
    """Rate of change of ATR. Positive = expanding (breakout), negative = compressing (squeeze).

    > 0.1 = expanding rapidly, exits are serious
    < -0.1 = compressing, be patient, big move coming
    """
    atr_series = atr(df_15m, 14)
    if atr_series.empty or len(atr_series) < 10:
        return 0.0
    atr_now = float(atr_series.iloc[-1])
    atr_5_ago = float(atr_series.iloc[-5])
    if atr_5_ago < 1e-9:
        return 0.0
    return (atr_now - atr_5_ago) / atr_5_ago


def wick_asymmetry(df_15m: pd.DataFrame, lookback: int = 10) -> float:
    """Directional wick bias. Positive = buyers defending (larger lower wicks).
    Negative = sellers in control (larger upper wicks).

    > 0.3 = strong buy-side defense
    < -0.3 = strong sell-side pressure
    """
    if df_15m is None or len(df_15m) < lookback:
        return 0.0

    window = df_15m.tail(lookback)
    lower_total = 0.0
    upper_total = 0.0
    for _, c in window.iterrows():
        o = float(c["open"])
        h = float(c["high"])
        l = float(c["low"])
        cl = float(c["close"])
        body_low = min(o, cl)
        body_high = max(o, cl)
        lower_total += body_low - l
        upper_total += h - body_high

    total = lower_total + upper_total
    if total < 1e-9:
        return 0.0
    return (lower_total - upper_total) / total  # -1 to +1


def calculate_noise_buffer(df_15m: pd.DataFrame, regime: dict) -> float:
    """Calculate how much room to give price before calling a break.

    Uses ATR + wick size + ATR rate of change for a dynamic buffer.
    """
    if df_15m is None or len(df_15m) < 14:
        return 0.0005  # fallback

    # ATR component
    atr_series = atr(df_15m, 14)
    atr_val = float(atr_series.iloc[-1]) if not atr_series.empty and not pd.isna(atr_series.iloc[-1]) else 0.0005

    # Wick component -- average wick size tells us normal noise
    window = df_15m.tail(20)
    wick_sizes = []
    for _, c in window.iterrows():
        lower_wick = abs(float(c["low"]) - min(float(c["open"]), float(c["close"])))
        upper_wick = abs(float(c["high"]) - max(float(c["open"]), float(c["close"])))
        wick_sizes.append(max(lower_wick, upper_wick))
    avg_wick = float(np.mean(wick_sizes)) if wick_sizes else 0.0003

    # ATR rate of change -- if compressing, widen buffer (big move coming, don't get shaken out)
    atr_roc = atr_rate_of_change(df_15m)
    roc_mult = 1.0
    if atr_roc < -0.1:
        roc_mult = 1.3  # compressing = widen buffer, be patient
    elif atr_roc > 0.15:
        roc_mult = 0.85  # expanding = tighten slightly, breaks are real

    # Regime multiplier
    regime_mult = regime.get("buffer_mult", 1.0)

    # Buffer = max of ATR-based and wick-based, scaled by regime and ATR rate
    buffer = max(atr_val * 0.25, avg_wick * 0.5) * regime_mult * roc_mult

    # Floor and ceiling
    buffer = max(buffer, 0.00015)  # min ~$0.75/contract
    buffer = min(buffer, 0.002)    # max ~$10/contract

    return buffer


# ============================================================
# LAYER 4: CONFIRMATION MODEL (multi-candle)
# ============================================================

def check_break_confirmation(
    price: float,
    level: float,
    direction: str,
    df_15m: pd.DataFrame,
    buffer: float,
) -> dict:
    """Check if a level break is confirmed or just noise.

    Returns:
        dict with: confirmed (bool), type (str), confidence (float), detail (str)
    """
    if df_15m is None or len(df_15m) < 3:
        return {"confirmed": False, "type": "insufficient_data", "confidence": 0, "detail": ""}

    c0 = df_15m.iloc[-1]  # current candle
    c1 = df_15m.iloc[-2]  # previous candle
    c2 = df_15m.iloc[-3]  # 2 candles ago

    close_0 = float(c0["close"])
    close_1 = float(c1["close"])
    low_0 = float(c0["low"])
    high_0 = float(c0["high"])
    low_1 = float(c1["low"])
    high_1 = float(c1["high"])

    vol_0 = float(c0.get("volume", 0))
    avg_vol = float(df_15m["volume"].tail(20).mean()) if "volume" in df_15m.columns else 1
    high_volume = vol_0 > avg_vol * 1.3

    # RSI
    rsi_series = compute_rsi(df_15m["close"], 14)
    rsi = float(rsi_series.iloc[-1]) if not rsi_series.empty and not pd.isna(rsi_series.iloc[-1]) else 50

    # NEW LAYER: Volume delta, body ratio, wick rejections, wick asymmetry
    vd_0 = volume_delta(c0)  # -1 (sell) to +1 (buy)
    br_0 = body_to_range_ratio(c0)  # 0 (doji) to 1 (full body)
    rejections = wick_rejection_count(df_15m, level, direction)
    wick_asym = wick_asymmetry(df_15m, 10)  # + = buyers defending, - = sellers pressing

    if direction == "long":
        # Checking if SUPPORT broke
        buffered_level = level - buffer

        # Just a wick -- support held
        if low_0 < level and close_0 > level:
            # Wick test. Stronger if buy-side volume delta and this is a repeated rejection
            hold_strength = "strong" if rejections >= 3 else "moderate" if rejections >= 1 else "new test"
            return {
                "confirmed": False,
                "type": "wick_test",
                "confidence": 0.05,
                "detail": f"wicked to ${low_0:.5f} but closed above support ${level:.5f}. "
                          f"Rejections: {rejections} ({hold_strength}). Volume delta: {vd_0:+.2f}. HOLDING.",
            }

        # Body close below support
        body_break = close_0 < buffered_level

        # Second candle confirmation (previous also closed below)
        double_close = close_1 < level and close_0 < level

        # Failed reclaim -- tried to get back above and couldn't
        failed_reclaim = close_1 < level and high_0 < level

        # RSI oversold bounce potential
        bounce_likely = rsi < 25

        # NEW: Is this a noise candle (doji/spinning top) or conviction candle?
        noise_candle = br_0 < 0.30  # tiny body = indecision, NOT a real break
        conviction_candle = br_0 > 0.70  # full body = real selling

        # NEW: Is volume delta showing sell pressure or buy defense?
        sell_pressure = vd_0 < -0.3  # close near low = sellers dominating
        buy_defense = vd_0 > 0.3  # close near high = buyers absorbing

        # NEW: Multiple wick rejections = strong support, give it more patience
        strong_rejection_history = rejections >= 3

        # NEW: Wick asymmetry shows who is in control
        buyers_defending = wick_asym > 0.2

        if body_break and double_close and high_volume and conviction_candle and sell_pressure:
            return {
                "confirmed": True,
                "type": "confirmed_break",
                "confidence": 0.95,
                "detail": f"2 full-body closes below support ${level:.5f} on high volume. "
                          f"Sell pressure {vd_0:+.2f}. Body ratio {br_0:.0%}. RSI {rsi:.0f}. Structure dead.",
            }
        elif body_break and failed_reclaim and conviction_candle:
            return {
                "confirmed": True,
                "type": "failed_reclaim",
                "confidence": 0.8,
                "detail": f"closed below support with {br_0:.0%} body. Failed reclaim -- high at ${high_0:.5f}.",
            }
        elif body_break and high_volume and not bounce_likely and not noise_candle:
            return {
                "confirmed": True,
                "type": "volume_break",
                "confidence": 0.75,
                "detail": f"closed below support ${level:.5f} on high volume. Body ratio {br_0:.0%}.",
            }
        elif body_break and noise_candle:
            # Doji/spinning top at support = indecision, NOT a confirmed break
            return {
                "confirmed": False,
                "type": "noise_candle_at_support",
                "confidence": 0.15,
                "detail": f"below support but candle is noise (body {br_0:.0%} of range). "
                          f"Doji/spinning top = indecision, not conviction. HOLD.",
            }
        elif body_break and bounce_likely:
            return {
                "confirmed": False,
                "type": "oversold_at_support",
                "confidence": 0.15,
                "detail": f"below support but RSI {rsi:.0f} = oversold. Bounce probability high. HOLD.",
            }
        elif body_break and buy_defense:
            return {
                "confirmed": False,
                "type": "buy_defense",
                "confidence": 0.2,
                "detail": f"below support but volume delta {vd_0:+.2f} = buyers absorbing. "
                          f"Close near high of candle. HOLD.",
            }
        elif body_break and strong_rejection_history:
            return {
                "confirmed": False,
                "type": "strong_support_history",
                "confidence": 0.2,
                "detail": f"below support but level tested {rejections} times and held every time. "
                          f"Strong support. HOLD.",
            }
        elif body_break and buyers_defending:
            return {
                "confirmed": False,
                "type": "wick_asymmetry_bullish",
                "confidence": 0.25,
                "detail": f"below support but wick asymmetry {wick_asym:+.2f} = buyers are defending. "
                          f"Larger lower wicks = buy pressure. HOLD.",
            }
        elif body_break and not high_volume:
            return {
                "confirmed": False,
                "type": "weak_break",
                "confidence": 0.35,
                "detail": f"closed below support but low volume + no conviction. Stop hunt likely. Wait.",
            }
        else:
            return {
                "confirmed": False,
                "type": "no_break",
                "confidence": 0.0,
                "detail": f"price ${close_0:.5f} above support ${level:.5f}. "
                          f"Rejections: {rejections}. Wick asym: {wick_asym:+.2f}. Structure intact.",
            }

    elif direction == "short":
        buffered_level = level + buffer

        noise_candle = br_0 < 0.30
        conviction_candle = br_0 > 0.70
        buy_pressure = vd_0 > 0.3  # close near high = buyers winning
        sell_defense = vd_0 < -0.3  # close near low = sellers absorbing
        strong_rejection_history = rejections >= 3
        sellers_defending = wick_asym < -0.2  # larger upper wicks = sell pressure

        if high_0 > level and close_0 < level:
            hold_strength = "strong" if rejections >= 3 else "moderate" if rejections >= 1 else "new test"
            return {
                "confirmed": False,
                "type": "wick_test",
                "confidence": 0.05,
                "detail": f"wicked to ${high_0:.5f} but closed below resistance ${level:.5f}. "
                          f"Rejections: {rejections} ({hold_strength}). Volume delta: {vd_0:+.2f}. HOLDING.",
            }

        body_break = close_0 > buffered_level
        double_close = close_1 > level and close_0 > level
        failed_rejection = close_1 > level and low_0 > level
        rejection_likely = rsi > 75

        if body_break and double_close and high_volume and conviction_candle and buy_pressure:
            return {
                "confirmed": True,
                "type": "confirmed_break",
                "confidence": 0.95,
                "detail": f"2 full-body closes above resistance ${level:.5f} on high volume. "
                          f"Buy pressure {vd_0:+.2f}. Body ratio {br_0:.0%}. RSI {rsi:.0f}. Structure dead.",
            }
        elif body_break and failed_rejection and conviction_candle:
            return {
                "confirmed": True,
                "type": "failed_rejection",
                "confidence": 0.8,
                "detail": f"closed above resistance with {br_0:.0%} body. Failed rejection -- low at ${low_0:.5f}.",
            }
        elif body_break and high_volume and not rejection_likely and not noise_candle:
            return {
                "confirmed": True,
                "type": "volume_break",
                "confidence": 0.75,
                "detail": f"closed above resistance ${level:.5f} on high volume. Body ratio {br_0:.0%}.",
            }
        elif body_break and noise_candle:
            return {
                "confirmed": False,
                "type": "noise_candle_at_resistance",
                "confidence": 0.15,
                "detail": f"above resistance but candle is noise (body {br_0:.0%} of range). "
                          f"Doji/spinning top = indecision, not conviction. HOLD.",
            }
        elif body_break and rejection_likely:
            return {
                "confirmed": False,
                "type": "overbought_at_resistance",
                "confidence": 0.15,
                "detail": f"above resistance but RSI {rsi:.0f} = overbought. Rejection likely. HOLD.",
            }
        elif body_break and sell_defense:
            return {
                "confirmed": False,
                "type": "sell_defense",
                "confidence": 0.2,
                "detail": f"above resistance but volume delta {vd_0:+.2f} = sellers absorbing. "
                          f"Close near low of candle. HOLD.",
            }
        elif body_break and strong_rejection_history:
            return {
                "confirmed": False,
                "type": "strong_resistance_history",
                "confidence": 0.2,
                "detail": f"above resistance but level tested {rejections} times and held. "
                          f"Strong resistance. HOLD.",
            }
        elif body_break and sellers_defending:
            return {
                "confirmed": False,
                "type": "wick_asymmetry_bearish",
                "confidence": 0.25,
                "detail": f"above resistance but wick asymmetry {wick_asym:+.2f} = sellers defending. "
                          f"Larger upper wicks = sell pressure. HOLD.",
            }
        elif body_break and not high_volume:
            return {
                "confirmed": False,
                "type": "weak_break",
                "confidence": 0.35,
                "detail": f"closed above resistance but low volume. Fake breakout likely. Wait.",
            }
        else:
            return {
                "confirmed": False,
                "type": "no_break",
                "confidence": 0.0,
                "detail": f"price ${close_0:.5f} below resistance ${level:.5f}. "
                          f"Rejections: {rejections}. Wick asym: {wick_asym:+.2f}. Structure intact.",
            }

    return {"confirmed": False, "type": "unknown", "confidence": 0, "detail": ""}


# ============================================================
# LAYER 5: EXIT LADDER (HOLD / TRIM / EXIT / REVERSE)
# ============================================================

def should_exit(
    price: float,
    direction: str,
    entry_price: float,
    df_15m: pd.DataFrame,
    df_1h: pd.DataFrame | None = None,
    pnl_usd: float = 0.0,
    max_loss_usd: float = 10.0,
    contracts: int = 2,
) -> dict:
    """Master exit decision using all 5 layers.

    Returns:
        dict with:
            exit: bool
            action: "HOLD" | "EXIT" | "EMERGENCY"
            reason: str
            confidence: float
            structure_detail: str
            support: float
            resistance: float
    """
    result = {
        "exit": False,
        "action": "HOLD",
        "reason": "structure intact",
        "confidence": 0.0,
        "structure_detail": "",
        "support": 0.0,
        "resistance": 0.0,
    }

    # === EMERGENCY FLOOR ===
    # Only hard stop -- prevents exchange force-close at worse price
    if pnl_usd < -max_loss_usd:
        return {
            "exit": True,
            "action": "EMERGENCY",
            "reason": f"emergency_floor: ${pnl_usd:.2f} loss exceeds ${max_loss_usd} floor. Preventing exchange force-close.",
            "confidence": 1.0,
            "structure_detail": "N/A -- emergency override",
            "support": 0.0,
            "resistance": 0.0,
        }

    if df_15m is None or len(df_15m) < 10:
        return result

    # === LAYER 1: REGIME ===
    regime = classify_regime(df_15m, df_1h)

    # === LAYER 2: STRUCTURE MAP ===
    if direction == "long":
        levels = find_scored_supports(df_15m, df_1h, 60)
        # Find the strongest support below entry
        relevant = [s for s in levels if s["level"] < entry_price]
        if not relevant and df_1h is not None and len(df_1h) >= 5:
            fallback = float(df_1h["low"].tail(10).min())
            relevant = [{"level": fallback, "score": 2, "tests": 1}]
    else:
        levels = find_scored_resistances(df_15m, df_1h, 60)
        relevant = [r for r in levels if r["level"] > entry_price]
        if not relevant and df_1h is not None and len(df_1h) >= 5:
            fallback = float(df_1h["high"].tail(10).max())
            relevant = [{"level": fallback, "score": 2, "tests": 1}]

    if not relevant:
        result["reason"] = "no clear structure levels found -- holding by default"
        return result

    # Use the strongest (highest scored) relevant level
    best_level = max(relevant, key=lambda x: x["score"])
    level = best_level["level"]
    level_score = best_level["score"]

    if direction == "long":
        result["support"] = level
    else:
        result["resistance"] = level

    # === LAYER 3: NOISE BUFFER ===
    buffer = calculate_noise_buffer(df_15m, regime)

    # Strong support gets MORE buffer (we trust it to hold)
    if level_score >= 5:
        buffer *= 1.3  # strong support = give extra room
    elif level_score <= 2:
        buffer *= 0.8  # weak support = tighter leash

    # === LAYER 4: CONFIRMATION ===
    confirmation = check_break_confirmation(price, level, direction, df_15m, buffer)

    result["structure_detail"] = confirmation["detail"]
    result["confidence"] = confirmation["confidence"]

    # === LAYER 5: EXIT DECISION ===
    if confirmation["confirmed"] and confirmation["confidence"] >= 0.7:
        result["exit"] = True
        result["action"] = "EXIT"
        result["reason"] = f"structure_break ({confirmation['type']}): {confirmation['detail']}"
    elif confirmation["confirmed"] and confirmation["confidence"] >= 0.5:
        # Borderline -- consider regime
        if regime["regime"] == "chop":
            result["exit"] = True
            result["action"] = "EXIT"
            result["reason"] = f"weak_break_in_chop: {confirmation['detail']}"
        else:
            # In trend or expansion, give benefit of the doubt
            result["exit"] = False
            result["action"] = "HOLD"
            result["reason"] = f"borderline_break_in_{regime['regime']}: {confirmation['detail']}. Holding -- regime supports patience."
    else:
        result["exit"] = False
        result["action"] = "HOLD"
        result["reason"] = f"structure_intact: {confirmation['detail']}"

    return result
