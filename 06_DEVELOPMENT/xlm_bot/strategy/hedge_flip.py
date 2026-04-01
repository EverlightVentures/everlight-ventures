"""Hedge Flip Engine -- Auto-reverse on stop loss.

When a stop loss hits, instead of going flat, evaluate whether to flip
direction. This recovers from wrong-direction trades when the move confirms.

From trading knowledge:
- "If your short gets stopped, flip to long at the stop level"
- "If it doesn't go in my direction, I know for sure it's going the other way"

SAFETY RULES:
- Only flip when structure confirms the breakout (not blindly)
- Require HTF bias alignment with flip direction
- Cap at 1 flip per day (prevent whipsaw chains)
- Size flip at 70% of original position (reduced conviction)
- Set tight SL on flip trade (1x ATR)
"""
from __future__ import annotations

from datetime import datetime, timezone


def should_hedge_flip(
    exit_reason: str,
    exited_direction: str,
    price: float,
    entry_price: float,
    htf_bias: dict | None = None,
    v4_score_opposite: int = 0,
    atr: float = 0.0,
    flips_today: int = 0,
    max_flips_per_day: int = 1,
    min_score: int = 45,
    enabled: bool = True,
) -> dict:
    """Evaluate whether to flip direction after a stop-loss exit.

    Args:
        exit_reason: why the position was closed
        exited_direction: the direction that just got stopped ("long" or "short")
        price: current price
        entry_price: entry price of the stopped trade
        htf_bias: higher timeframe bias dict (from classify_htf_trend_bias)
        v4_score_opposite: v4 confluence score for the opposite direction
        atr: current ATR value
        flips_today: number of hedge flips already done today
        max_flips_per_day: max allowed flips per day
        min_score: minimum v4 score to allow flip
        enabled: master enable flag

    Returns dict with:
        flip: bool
        direction: str ("long" or "short")
        reason: str
        size_mult: float (multiplier on original size)
        stop_price: float (SL for the flip trade)
        meta: dict (debugging info)
    """
    result = {
        "flip": False,
        "direction": "",
        "reason": "no_flip",
        "size_mult": 0.7,
        "stop_price": 0.0,
        "meta": {},
    }

    if not enabled:
        result["reason"] = "hedge_flip_disabled"
        return result

    # Only flip on stop-loss type exits
    sl_exits = {
        "stop_loss", "sl_hit", "emergency_floor", "structure_break",
        "runner_trail_stop", "runner_floor_hit", "break_even",
        "breakeven_stop_hit", "exchange_side_close_detected",
    }
    # Also catch SL-like exits from smart_exit
    is_sl_exit = (
        exit_reason in sl_exits
        or "stop" in str(exit_reason).lower()
        or "break" in str(exit_reason).lower()
        or "emergency" in str(exit_reason).lower()
    )

    if not is_sl_exit:
        result["reason"] = f"not_sl_exit_{exit_reason}"
        return result

    # Cap flips per day
    if flips_today >= max_flips_per_day:
        result["reason"] = f"max_flips_reached_{flips_today}"
        return result

    flip_direction = "long" if exited_direction == "short" else "short"

    # Check HTF alignment
    htf_state = str((htf_bias or {}).get("bias", "neutral"))
    htf_aligned = False
    if flip_direction == "long" and htf_state in ("bullish_trend", "bullish_expansion"):
        htf_aligned = True
    elif flip_direction == "short" and htf_state in ("bearish_trend", "bearish_crash"):
        htf_aligned = True
    elif htf_state == "neutral":
        htf_aligned = True  # neutral = allow either direction

    if not htf_aligned:
        result["reason"] = f"htf_not_aligned_{htf_state}_vs_{flip_direction}"
        result["meta"] = {"htf_state": htf_state, "flip_direction": flip_direction}
        return result

    # Check minimum score
    if v4_score_opposite < min_score:
        result["reason"] = f"score_too_low_{v4_score_opposite}_vs_{min_score}_min"
        result["meta"] = {"score": v4_score_opposite, "min": min_score}
        return result

    # Calculate stop price for flip trade (1x ATR from current price)
    if atr > 0:
        if flip_direction == "long":
            stop_price = price - atr
        else:
            stop_price = price + atr
    else:
        # Fallback: 0.5% from price
        if flip_direction == "long":
            stop_price = price * 0.995
        else:
            stop_price = price * 1.005

    result["flip"] = True
    result["direction"] = flip_direction
    result["stop_price"] = stop_price
    result["reason"] = (
        f"hedge_flip_{exited_direction}_to_{flip_direction}"
        f"_htf={htf_state}_score={v4_score_opposite}"
    )
    result["meta"] = {
        "exited_direction": exited_direction,
        "exit_reason": exit_reason,
        "htf_state": htf_state,
        "v4_score": v4_score_opposite,
        "atr": atr,
        "flips_today": flips_today,
    }

    return result
