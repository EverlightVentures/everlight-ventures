"""Position IQ -- Real-time position intelligence and decision engine.

Constantly evaluates: Is this STILL the right trade?
Options every cycle:
  HOLD   -- trade thesis intact, stay in
  CUT    -- thesis weakening, exit now at smaller loss, wait for better entry
  FLIP   -- thesis reversed, exit and enter opposite direction immediately
  TRAIL  -- thesis confirmed, tighten stop to lock profit

This is what separates a bot from a trader. A trader MANAGES positions.
They don't just set a stop and wait. They read the tape and adapt.
"""
from __future__ import annotations


def evaluate_position(
    direction: str,
    entry_price: float,
    current_price: float,
    stop_price: float,
    df_15m=None,
    df_1h=None,
    atr_value: float = 0,
    rsi_15m: float = 50,
    ema8: float = 0,
    ema21: float = 0,
    bars_since_entry: int = 0,
    max_loss_usd: float = 8.0,
) -> dict:
    """Evaluate current position and recommend action.

    Returns:
        action: HOLD | CUT | FLIP | TRAIL
        confidence: 0-100
        reason: why this action
        urgency: low | medium | high | critical
        cut_price: suggested exit price if CUT
        flip_direction: opposite direction if FLIP
    """
    if entry_price <= 0 or current_price <= 0:
        return {"action": "HOLD", "confidence": 0, "reason": "no_data"}

    is_long = direction == "long"
    pnl_usd = (current_price - entry_price) * 5000 if is_long else (entry_price - current_price) * 5000
    pnl_pct = pnl_usd / (entry_price * 5000) * 100
    dist_to_stop_pct = abs(current_price - stop_price) / current_price * 100 if stop_price > 0 else 99

    # Momentum signals
    price_above_ema8 = current_price > ema8 if ema8 > 0 else None
    price_above_ema21 = current_price > ema21 if ema21 > 0 else None
    ema_bullish = price_above_ema8 and price_above_ema21
    ema_bearish = not price_above_ema8 and not price_above_ema21 if price_above_ema8 is not None else None
    rsi_bullish = rsi_15m > 55
    rsi_bearish = rsi_15m < 45

    # Count signals AGAINST our position
    against = 0
    for_us = 0

    if is_long:
        if ema_bearish: against += 2
        elif ema_bullish: for_us += 2
        if rsi_bearish: against += 1
        elif rsi_bullish: for_us += 1
    else:  # short
        if ema_bullish: against += 2
        elif ema_bearish: for_us += 2
        if rsi_bullish: against += 1
        elif rsi_bearish: for_us += 1

    # 1H structure check
    if df_1h is not None and len(df_1h) >= 4:
        last_3_closes = [float(df_1h["close"].iloc[i]) for i in range(-3, 0)]
        if is_long:
            if all(last_3_closes[i] < last_3_closes[i-1] for i in range(1, len(last_3_closes))):
                against += 2  # falling closes against long
            elif all(last_3_closes[i] > last_3_closes[i-1] for i in range(1, len(last_3_closes))):
                for_us += 2
        else:
            if all(last_3_closes[i] > last_3_closes[i-1] for i in range(1, len(last_3_closes))):
                against += 2  # rising closes against short
            elif all(last_3_closes[i] < last_3_closes[i-1] for i in range(1, len(last_3_closes))):
                for_us += 2

    # Decision matrix
    total_signals = against + for_us
    against_pct = against / max(total_signals, 1) * 100

    result = {
        "pnl_usd": round(pnl_usd, 2),
        "pnl_pct": round(pnl_pct, 3),
        "dist_to_stop_pct": round(dist_to_stop_pct, 2),
        "signals_against": against,
        "signals_for": for_us,
        "against_pct": round(against_pct, 1),
        "rsi": round(rsi_15m, 1),
        "ema_aligned": ema_bullish if is_long else ema_bearish,
    }

    # TRAIL: in profit + signals confirm
    if pnl_usd > 2.0 and for_us > against:
        result.update({
            "action": "TRAIL",
            "confidence": min(90, 50 + for_us * 10),
            "reason": "in_profit_signals_confirm",
            "urgency": "low",
        })
        return result

    # HOLD: signals mixed, trade still has room
    if against <= for_us and dist_to_stop_pct > 0.3:
        result.update({
            "action": "HOLD",
            "confidence": min(80, 40 + for_us * 10),
            "reason": "thesis_intact" if for_us > against else "mixed_signals_hold",
            "urgency": "low",
        })
        return result

    # CUT: losing + majority signals against + taking -$1 to -$3 beats waiting for -$8
    if pnl_usd < 0 and against > for_us and abs(pnl_usd) < max_loss_usd * 0.5:
        result.update({
            "action": "CUT",
            "confidence": min(85, 40 + against * 15),
            "reason": f"signals_against_{against}v{for_us}_loss_${abs(pnl_usd):.1f}_better_than_${max_loss_usd:.0f}",
            "urgency": "high" if against >= 4 else "medium",
            "save_usd": round(max_loss_usd - abs(pnl_usd), 2),
        })
        return result

    # FLIP: strong reversal signals + underwater
    if pnl_usd < 0 and against >= 4 and against_pct >= 75:
        result.update({
            "action": "FLIP",
            "confidence": min(90, 50 + against * 10),
            "reason": f"reversal_confirmed_{against}_signals_against",
            "urgency": "critical",
            "flip_direction": "long" if direction == "short" else "short",
        })
        return result

    # CUT: very close to stop + signals against (save what you can)
    if pnl_usd < 0 and dist_to_stop_pct < 0.3 and against > for_us:
        result.update({
            "action": "CUT",
            "confidence": 70,
            "reason": f"near_stop_signals_against_save_${max_loss_usd - abs(pnl_usd):.1f}",
            "urgency": "high",
            "save_usd": round(max_loss_usd - abs(pnl_usd), 2),
        })
        return result

    # Default: HOLD
    result.update({
        "action": "HOLD",
        "confidence": 30,
        "reason": "default_no_clear_signal",
        "urgency": "low",
    })
    return result
