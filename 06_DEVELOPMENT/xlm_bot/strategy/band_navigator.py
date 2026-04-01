"""Band Navigator -- Adaptive multi-timeframe band zone + momentum turn engine.

Replaces the rigid dip_retrace_gate with intelligent band-aware entry timing.
Instead of "block if RSI rising," this asks: "where is price in the band
structure, and has momentum turned in our favor?"

ZONES (per timeframe):
  STRONG_SHORT: price above upper BB + above VWAP
  WEAK_SHORT:   price between VWAP and upper BB, rejecting
  NEUTRAL:      price near VWAP, no clear edge
  WEAK_LONG:    price between lower BB and VWAP, bouncing
  STRONG_LONG:  price below lower BB + below VWAP

MOMENTUM TURN DETECTION:
  RSI rising then flattens/turns down = short turn confirmed
  RSI falling then flattens/turns up = long turn confirmed
  "Don't fight the micro-bounce, wait for it to exhaust, then enter"

MULTI-TIMEFRAME:
  Scores each timeframe (15m, 1h, 4h) independently
  Aggregates: if 2/3 timeframes agree on zone + turn, signal is valid
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def _bollinger_bands(closes: np.ndarray, period: int = 20, std_mult: float = 2.0):
    """Calculate Bollinger Bands."""
    if len(closes) < period:
        mid = closes[-1] if len(closes) > 0 else 0
        return mid, mid, mid
    sma = np.mean(closes[-period:])
    std = np.std(closes[-period:])
    return sma + std_mult * std, sma, sma - std_mult * std


def _vwap(df: pd.DataFrame, lookback: int = 50) -> float:
    """Calculate VWAP from OHLCV data."""
    if df is None or len(df) < 5 or "volume" not in df.columns:
        return 0.0
    window = df.tail(lookback)
    typical = (window["high"] + window["low"] + window["close"]) / 3
    vol = window["volume"]
    total_vol = vol.sum()
    if total_vol <= 0:
        return float(typical.iloc[-1])
    return float((typical * vol).sum() / total_vol)


def _ema(values: np.ndarray, period: int) -> np.ndarray:
    """Calculate EMA series."""
    if len(values) < period:
        return values.copy()
    k = 2 / (period + 1)
    ema = np.zeros(len(values))
    ema[0] = values[0]
    for i in range(1, len(values)):
        ema[i] = values[i] * k + ema[i - 1] * (1 - k)
    return ema


def _rsi(closes: np.ndarray, period: int = 14) -> np.ndarray:
    """Calculate RSI series."""
    if len(closes) < period + 1:
        return np.full(len(closes), 50.0)
    deltas = np.diff(closes)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    rsi_out = np.full(len(closes), 50.0)
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            rsi_out[i + 1] = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi_out[i + 1] = 100 - (100 / (1 + rs))
    return rsi_out


def _detect_momentum_turn(rsi_series: np.ndarray, lookback: int = 5) -> dict:
    """Detect if RSI momentum has turned.

    Returns:
        direction: "turning_down" | "turning_up" | "rising" | "falling" | "flat"
        strength: 0-1 how confident the turn is
        rsi_current: current RSI value
        rsi_peak: recent peak/trough value
    """
    if len(rsi_series) < lookback + 2:
        return {"direction": "flat", "strength": 0, "rsi_current": 50, "rsi_peak": 50}

    recent = rsi_series[-lookback:]
    current = float(recent[-1])
    prev = float(recent[-2])

    # Find peak/trough in the lookback window
    peak_idx = np.argmax(recent)
    trough_idx = np.argmin(recent)
    peak_val = float(recent[peak_idx])
    trough_val = float(recent[trough_idx])

    # RSI was rising, now the latest bar is lower than the peak = turning down
    if peak_idx < len(recent) - 1 and current < peak_val - 1.5:
        strength = min(1.0, (peak_val - current) / 10)
        return {"direction": "turning_down", "strength": round(strength, 3),
                "rsi_current": round(current, 1), "rsi_peak": round(peak_val, 1)}

    # RSI was falling, now the latest bar is higher than the trough = turning up
    if trough_idx < len(recent) - 1 and current > trough_val + 1.5:
        strength = min(1.0, (current - trough_val) / 10)
        return {"direction": "turning_up", "strength": round(strength, 3),
                "rsi_current": round(current, 1), "rsi_peak": round(trough_val, 1)}

    # Still rising or falling
    if current > prev + 0.5:
        return {"direction": "rising", "strength": 0, "rsi_current": round(current, 1), "rsi_peak": round(peak_val, 1)}
    elif current < prev - 0.5:
        return {"direction": "falling", "strength": 0, "rsi_current": round(current, 1), "rsi_peak": round(trough_val, 1)}

    return {"direction": "flat", "strength": 0, "rsi_current": round(current, 1), "rsi_peak": round(current, 1)}


def classify_band_zone(
    df: pd.DataFrame,
    bb_period: int = 20,
    bb_std: float = 2.0,
) -> dict:
    """Classify where price sits in the band structure for one timeframe.

    Returns:
        zone: "STRONG_SHORT" | "WEAK_SHORT" | "NEUTRAL" | "WEAK_LONG" | "STRONG_LONG"
        price: current price
        bb_upper, bb_mid, bb_lower: Bollinger Band levels
        vwap: VWAP level
        ema21: EMA21 level
        rsi: current RSI
        momentum: dict from _detect_momentum_turn
        band_position: 0-1 (0=at lower band, 1=at upper band)
    """
    if df is None or len(df) < bb_period + 5:
        return {"zone": "NEUTRAL", "price": 0, "confidence": 0, "momentum": {"direction": "flat"}}

    closes = df["close"].values
    price = float(closes[-1])
    bb_upper, bb_mid, bb_lower = _bollinger_bands(closes, bb_period, bb_std)
    vwap = _vwap(df)
    ema21 = float(_ema(closes, 21)[-1])
    rsi_series = _rsi(closes)
    rsi_now = float(rsi_series[-1])
    momentum = _detect_momentum_turn(rsi_series)

    # Band position: 0 = at lower band, 1 = at upper band
    bb_range = bb_upper - bb_lower
    band_pos = (price - bb_lower) / bb_range if bb_range > 0 else 0.5
    band_pos = max(0, min(1, band_pos))

    # Zone classification
    above_vwap = price > vwap
    above_bb_mid = price > bb_mid
    above_ema21 = price > ema21
    near_upper = band_pos > 0.85
    near_lower = band_pos < 0.15

    if near_upper and above_vwap and rsi_now > 65:
        zone = "STRONG_SHORT"
        confidence = min(1.0, (band_pos - 0.8) * 5 + (rsi_now - 60) / 40)
    elif above_bb_mid and above_vwap and band_pos > 0.6:
        zone = "WEAK_SHORT"
        confidence = (band_pos - 0.5) * 2
    elif near_lower and not above_vwap and rsi_now < 35:
        zone = "STRONG_LONG"
        confidence = min(1.0, (0.2 - band_pos) * 5 + (40 - rsi_now) / 40)
    elif not above_bb_mid and not above_vwap and band_pos < 0.4:
        zone = "WEAK_LONG"
        confidence = (0.5 - band_pos) * 2
    else:
        zone = "NEUTRAL"
        confidence = 0.0

    return {
        "zone": zone,
        "price": round(price, 6),
        "bb_upper": round(bb_upper, 6),
        "bb_mid": round(bb_mid, 6),
        "bb_lower": round(bb_lower, 6),
        "vwap": round(vwap, 6),
        "ema21": round(ema21, 6),
        "rsi": round(rsi_now, 1),
        "momentum": momentum,
        "band_position": round(band_pos, 3),
        "confidence": round(max(0, min(1, confidence)), 3),
    }


def evaluate_band_entry(
    direction: str,
    df_15m: pd.DataFrame | None = None,
    df_1h: pd.DataFrame | None = None,
    df_4h: pd.DataFrame | None = None,
    require_turn: bool = True,
    min_timeframes_agree: int = 2,
) -> dict:
    """Multi-timeframe band navigation decision.

    Evaluates whether to allow entry based on band zone + momentum turn
    across multiple timeframes.

    Args:
        direction: "long" or "short"
        df_15m, df_1h, df_4h: OHLCV DataFrames for each timeframe
        require_turn: if True, momentum must have turned in our favor
        min_timeframes_agree: how many timeframes must agree (1-3)

    Returns:
        allowed: bool
        reason: str
        score_adjustment: int (bonus/penalty to add to v4 score)
        zones: dict of per-timeframe zone info
        meta: dict with full analysis
    """
    result = {
        "allowed": True,
        "reason": "band_nav_pass",
        "score_adjustment": 0,
        "zones": {},
        "meta": {},
    }

    timeframes = {}
    if df_15m is not None and len(df_15m) >= 25:
        timeframes["15m"] = classify_band_zone(df_15m)
    if df_1h is not None and len(df_1h) >= 25:
        timeframes["1h"] = classify_band_zone(df_1h)
    if df_4h is not None and len(df_4h) >= 25:
        timeframes["4h"] = classify_band_zone(df_4h)

    if not timeframes:
        result["reason"] = "no_data"
        return result

    result["zones"] = timeframes

    # Count how many timeframes agree with the direction
    agree_count = 0
    turn_confirmed = 0
    total_confidence = 0
    score_adj = 0

    for tf_name, zone_info in timeframes.items():
        zone = zone_info["zone"]
        momentum = zone_info.get("momentum", {})
        mom_dir = momentum.get("direction", "flat")
        conf = zone_info.get("confidence", 0)

        if direction == "short":
            # Zone agreement for shorts
            if zone in ("STRONG_SHORT", "WEAK_SHORT"):
                agree_count += 1
                total_confidence += conf
                # Bonus for strong zone
                if zone == "STRONG_SHORT":
                    score_adj += 5
            elif zone == "NEUTRAL":
                pass  # neutral doesn't help or hurt
            else:
                # Zone says long, we want short -- penalty
                score_adj -= 5

            # Momentum turn for shorts
            if mom_dir == "turning_down":
                turn_confirmed += 1
                score_adj += 3
            elif mom_dir == "rising":
                # RSI still rising -- momentum against us
                score_adj -= 3

        elif direction == "long":
            if zone in ("STRONG_LONG", "WEAK_LONG"):
                agree_count += 1
                total_confidence += conf
                if zone == "STRONG_LONG":
                    score_adj += 5
            elif zone == "NEUTRAL":
                pass
            else:
                score_adj -= 5

            if mom_dir == "turning_up":
                turn_confirmed += 1
                score_adj += 3
            elif mom_dir == "falling":
                score_adj -= 3

    # Decision logic
    enough_agreement = agree_count >= min(min_timeframes_agree, len(timeframes))
    has_turn = turn_confirmed > 0

    if not enough_agreement:
        result["allowed"] = False
        result["reason"] = f"band_zone_disagree_{agree_count}_of_{len(timeframes)}"
        result["score_adjustment"] = score_adj
        return result

    if require_turn and not has_turn:
        # Zones agree but momentum hasn't turned yet -- WAIT
        result["allowed"] = False
        result["reason"] = f"waiting_for_momentum_turn_{direction}"
        result["score_adjustment"] = score_adj
        result["meta"]["waiting_for"] = "turning_down" if direction == "short" else "turning_up"
        # Check how close we are to turning
        for tf_name, zone_info in timeframes.items():
            mom = zone_info.get("momentum", {})
            if mom.get("direction") == "flat":
                result["meta"]["almost_turning"] = True
                result["reason"] += "_almost"
                break
        return result

    # All checks pass -- allow with score adjustment
    result["allowed"] = True
    result["score_adjustment"] = max(-10, min(15, score_adj))
    result["reason"] = (
        f"band_nav_confirmed_{direction}_"
        f"{agree_count}tf_agree_"
        f"{turn_confirmed}tf_turned"
    )
    result["meta"] = {
        "agree_count": agree_count,
        "turn_confirmed": turn_confirmed,
        "total_timeframes": len(timeframes),
        "avg_confidence": round(total_confidence / max(agree_count, 1), 3),
    }

    return result
