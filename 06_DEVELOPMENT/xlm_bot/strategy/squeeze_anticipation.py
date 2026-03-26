"""Squeeze Anticipation System - Detect and position for liquidation squeezes.

Connects crowding data, funding rates, OI trends, BB width, and volume into
a unified squeeze risk score. When the score is high enough, the bot exits
crowded-side positions and positions for the squeeze direction.

Also includes stop-hunt recovery: after a stop-loss exit, monitors for fake
spikes that reverse within 3 candles and re-enters the original direction.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Optional
import json


@dataclass
class SqueezeAssessment:
    """Squeeze risk assessment for current market conditions."""
    risk_score: int             # 0-100
    direction: str              # "short_squeeze" (longs win) | "long_squeeze" (shorts win) | "unknown"
    crowded_side: str           # "short" | "long" | "balanced"
    action: str                 # "none" | "warn" | "tighten" | "exit" | "flip"
    factors: list               # list of contributing factor strings
    recommended_side: str       # which side to be on: "long" | "short" | "flat"
    meta: dict = field(default_factory=dict)


def compute_squeeze_risk(
    crowding_data: dict = None,
    contract_data: dict = None,
    expansion_data: dict = None,
    volume_ratio: float = 1.0,
    rsi: float = 50.0,
    bb_width_pct: float = 2.0,
    config: dict = None,
) -> SqueezeAssessment:
    """Compute squeeze risk score from all available data sources.

    Args:
        crowding_data: from crowding_summary.json
        contract_data: from contract_context.json (funding, OI, basis)
        expansion_data: from expansion state (vol phase, metrics)
        volume_ratio: current vol / 20-bar avg
        rsi: current RSI value
        bb_width_pct: Bollinger Band width as percentage
        config: squeeze_anticipation config section
    """
    cfg = config or {}
    crowd = crowding_data or {}
    ctx = contract_data or {}
    exp = expansion_data or {}

    score = 0
    factors = []
    crowded_side = "balanced"

    # --- Factor 1: Crowding regime (0-25 pts) ---
    crowd_regime = str(crowd.get("regime", "")).lower()
    crowd_bias = str(crowd.get("bias", "")).lower()
    funding_bias = str(crowd.get("funding_bias", ctx.get("funding_bias", ""))).lower()

    if crowd_regime == "crowded":
        score += 25
        factors.append("crowding_regime_crowded")
    elif crowd_regime in ("heavy", "extreme"):
        score += 20
        factors.append("crowding_regime_heavy")

    # Determine which side is crowded
    if "short" in crowd_bias or "short" in funding_bias:
        crowded_side = "short"
    elif "long" in crowd_bias or "long" in funding_bias:
        crowded_side = "long"
    elif funding_bias == "shorts_pay" or funding_bias == "negative":
        crowded_side = "short"
    elif funding_bias == "longs_pay" or funding_bias == "positive":
        crowded_side = "long"

    # --- Factor 2: Funding rate (0-20 pts) ---
    funding_rate = float(ctx.get("funding_rate_hr", 0) or 0)
    if abs(funding_rate) > 0.5:
        score += 20
        factors.append(f"extreme_funding_{funding_rate:+.3f}")
        if funding_rate < 0:
            crowded_side = "short"  # shorts pay = too many shorts
        else:
            crowded_side = "long"   # longs pay = too many longs
    elif abs(funding_rate) > 0.1:
        score += 12
        factors.append(f"elevated_funding_{funding_rate:+.3f}")
    elif abs(funding_rate) > 0.01:
        score += 5
        factors.append(f"mild_funding_{funding_rate:+.3f}")

    # --- Factor 3: OI flat while price moves (0-15 pts) ---
    oi_trend = str(ctx.get("oi_trend", "")).upper()
    oi_change = float(crowd.get("oi_change_pct", 0) or 0)

    if oi_trend == "FLAT" and abs(oi_change) < 1.0:
        score += 15
        factors.append("oi_flat_stops_accumulating")
    elif oi_trend == "FALLING":
        score += 8
        factors.append("oi_falling_deleveraging")

    # --- Factor 4: BB width compression (0-20 pts) ---
    if bb_width_pct < 1.0:
        score += 20
        factors.append(f"extreme_bb_squeeze_{bb_width_pct:.2f}pct")
    elif bb_width_pct < 1.5:
        score += 15
        factors.append(f"tight_bb_squeeze_{bb_width_pct:.2f}pct")
    elif bb_width_pct < 2.0:
        score += 8
        factors.append(f"moderate_bb_squeeze_{bb_width_pct:.2f}pct")

    # --- Factor 5: Volume dead (0-10 pts) ---
    if volume_ratio < 0.3:
        score += 10
        factors.append(f"dead_volume_{volume_ratio:.2f}x")
    elif volume_ratio < 0.5:
        score += 7
        factors.append(f"low_volume_{volume_ratio:.2f}x")

    # --- Factor 6: RSI mid-range (0-10 pts) ---
    if 40 <= rsi <= 60:
        score += 10
        factors.append(f"rsi_midrange_{rsi:.0f}")
    elif 35 <= rsi <= 65:
        score += 5
        factors.append(f"rsi_near_mid_{rsi:.0f}")

    # Cap at 100
    score = min(100, score)

    # Determine direction
    if crowded_side == "short":
        direction = "short_squeeze"  # shorts get squeezed, longs win
        recommended = "long"
    elif crowded_side == "long":
        direction = "long_squeeze"   # longs get squeezed, shorts win
        recommended = "short"
    else:
        direction = "unknown"
        recommended = "flat"

    # Determine action
    warn_threshold = int(cfg.get("warn_threshold", 60) or 60)
    exit_threshold = int(cfg.get("exit_threshold", 75) or 75)
    flip_threshold = int(cfg.get("flip_threshold", 85) or 85)

    if score >= flip_threshold:
        action = "flip"
    elif score >= exit_threshold:
        action = "exit"
    elif score >= warn_threshold:
        action = "tighten"
    else:
        action = "none"

    return SqueezeAssessment(
        risk_score=score,
        direction=direction,
        crowded_side=crowded_side,
        action=action,
        factors=factors,
        recommended_side=recommended,
        meta={
            "funding_rate": funding_rate,
            "oi_trend": oi_trend,
            "bb_width": bb_width_pct,
            "volume_ratio": volume_ratio,
            "rsi": rsi,
            "crowd_regime": crowd_regime,
        },
    )


def should_exit_for_squeeze(
    assessment: SqueezeAssessment,
    current_direction: str,
) -> dict:
    """Check if current position should exit due to squeeze risk.

    Returns: {"exit": bool, "reason": str, "action": str, "flip_to": str}
    """
    if assessment.action == "none":
        return {"exit": False, "reason": "squeeze_risk_low", "action": "hold", "flip_to": ""}

    on_crowded_side = (
        (current_direction == "short" and assessment.crowded_side == "short") or
        (current_direction == "long" and assessment.crowded_side == "long")
    )

    if not on_crowded_side:
        return {"exit": False, "reason": "on_safe_side", "action": "hold", "flip_to": ""}

    if assessment.action == "flip":
        flip_dir = "long" if current_direction == "short" else "short"
        return {
            "exit": True,
            "reason": f"squeeze_risk_{assessment.risk_score}_flip",
            "action": "flip",
            "flip_to": flip_dir,
        }

    if assessment.action == "exit":
        return {
            "exit": True,
            "reason": f"squeeze_risk_{assessment.risk_score}_exit",
            "action": "exit",
            "flip_to": "",
        }

    if assessment.action == "tighten":
        return {
            "exit": False,
            "reason": f"squeeze_risk_{assessment.risk_score}_tighten",
            "action": "tighten",
            "flip_to": "",
        }

    return {"exit": False, "reason": "squeeze_risk_low", "action": "hold", "flip_to": ""}


def detect_stop_hunt(
    stop_price: float,
    direction: str,
    price_history_1m: list,
    atr_value: float,
    config: dict = None,
) -> dict:
    """Detect if a recent stop-loss was triggered by a stop hunt.

    A stop hunt is: price spikes through stops, then reverses back within
    3 candles. The spike was fake, the original trend resumes.

    Args:
        stop_price: the stop-loss price that was hit
        direction: the direction that was stopped out ("long" or "short")
        price_history_1m: last 5-10 1m candles as list of {high, low, close, open}
        atr_value: current ATR for threshold calculation
        config: squeeze_anticipation config section

    Returns: {"detected": bool, "type": "stop_hunt"|"real_breakout"|"pending",
              "reentry_side": str, "reentry_price": float}
    """
    cfg = config or {}
    if not price_history_1m or len(price_history_1m) < 3 or atr_value <= 0:
        return {"detected": False, "type": "insufficient_data", "reentry_side": "", "reentry_price": 0}

    min_spike_atr = float(cfg.get("min_spike_atr", 1.0) or 1.0)
    max_recovery_bars = int(cfg.get("max_recovery_bars", 3) or 3)

    # Find the spike candle (biggest range after stop was hit)
    spike_candle = None
    spike_idx = -1
    max_range = 0
    for i, bar in enumerate(price_history_1m[-5:]):
        bar_range = float(bar.get("high", 0)) - float(bar.get("low", 0))
        if bar_range > max_range:
            max_range = bar_range
            spike_candle = bar
            spike_idx = i

    if spike_candle is None or max_range < atr_value * min_spike_atr:
        return {"detected": False, "type": "no_spike", "reentry_side": "", "reentry_price": 0}

    spike_high = float(spike_candle.get("high", 0))
    spike_low = float(spike_candle.get("low", 0))

    # Check if price reversed back after the spike
    bars_after_spike = price_history_1m[-(5 - spike_idx):]
    if len(bars_after_spike) < 2:
        return {"detected": False, "type": "pending", "reentry_side": "", "reentry_price": 0}

    last_close = float(bars_after_spike[-1].get("close", 0))

    if direction == "short":
        # Short was stopped: price spiked UP through stop, then came back DOWN
        spike_went_above_stop = spike_high > stop_price
        came_back = last_close < stop_price
        if spike_went_above_stop and came_back:
            return {
                "detected": True,
                "type": "stop_hunt",
                "reentry_side": "short",  # re-enter short, the trend resumes
                "reentry_price": last_close,
                "stop": spike_high + atr_value * 0.3,
            }
        elif spike_went_above_stop and not came_back:
            return {
                "detected": True,
                "type": "real_breakout",
                "reentry_side": "long",  # it's real, go with it
                "reentry_price": last_close,
                "stop": spike_low - atr_value * 0.3,
            }

    elif direction == "long":
        # Long was stopped: price spiked DOWN through stop, then came back UP
        spike_went_below_stop = spike_low < stop_price
        came_back = last_close > stop_price
        if spike_went_below_stop and came_back:
            return {
                "detected": True,
                "type": "stop_hunt",
                "reentry_side": "long",
                "reentry_price": last_close,
                "stop": spike_low - atr_value * 0.3,
            }
        elif spike_went_below_stop and not came_back:
            return {
                "detected": True,
                "type": "real_breakout",
                "reentry_side": "short",
                "reentry_price": last_close,
                "stop": spike_high + atr_value * 0.3,
            }

    return {"detected": False, "type": "no_pattern", "reentry_side": "", "reentry_price": 0}
