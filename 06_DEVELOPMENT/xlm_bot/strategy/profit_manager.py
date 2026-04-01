"""Profit Manager -- Partial profit taking + break-even SL management.

Implements the key insight from trading knowledge:
- Take partial profits at TP1, move SL to break-even
- Take more at TP2, trail stop
- Let remainder run to TP3 or trailing stop

CONTRACT MATH (XLP perps):
- 1 contract = 5,000 XLM
- $0.01 move = $50/contract
- Min trade size on Coinbase = 1 contract (no fractional)
- Partial close only works with size >= 2 contracts

When size=1 (current), this module still provides:
- SL-to-break-even after reaching TP1 distance
- Trailing stop tightening at TP2 distance
- Full exit at TP3
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ProfitState:
    """Tracks profit-taking progress for an open position."""
    tp1_reached: bool = False
    tp2_reached: bool = False
    sl_at_breakeven: bool = False
    partial_close_1_done: bool = False
    partial_close_2_done: bool = False
    trail_price: float = 0.0
    original_size: int = 0
    remaining_size: int = 0


def evaluate_profit_management(
    price: float,
    direction: str,
    entry_price: float,
    size: int,
    tp1_price: float,
    tp2_price: float,
    tp3_price: float,
    atr: float,
    profit_state: dict | None = None,
) -> dict:
    """Evaluate profit management actions for the current price.

    Returns dict with:
        action: "HOLD" | "MOVE_SL_TO_BE" | "PARTIAL_CLOSE" | "TRAIL_TIGHTEN" | "FULL_EXIT"
        new_sl: float (updated stop loss price, 0 = no change)
        close_size: int (number of contracts to close, 0 = none)
        reason: str
        profit_state: dict (updated state to persist)
    """
    ps = profit_state or {}
    tp1_reached = bool(ps.get("tp1_reached", False))
    tp2_reached = bool(ps.get("tp2_reached", False))
    sl_at_be = bool(ps.get("sl_at_breakeven", False))
    trail = float(ps.get("trail_price", 0))

    result = {
        "action": "HOLD",
        "new_sl": 0.0,
        "close_size": 0,
        "reason": "no action needed",
        "profit_state": dict(ps),
    }

    if entry_price <= 0 or price <= 0:
        return result

    # Check if price has reached TP levels
    if direction == "long":
        at_tp1 = price >= tp1_price
        at_tp2 = price >= tp2_price
        at_tp3 = price >= tp3_price
    else:
        at_tp1 = price <= tp1_price
        at_tp2 = price <= tp2_price
        at_tp3 = price <= tp3_price

    # TP3 hit -- full exit
    if at_tp3:
        result["action"] = "FULL_EXIT"
        result["close_size"] = size
        result["reason"] = "tp3_hit_full_exit"
        return result

    # TP2 hit -- tighten trailing stop + partial close if possible
    if at_tp2 and not tp2_reached:
        result["profit_state"]["tp2_reached"] = True
        # Trail at 1x ATR behind price
        if direction == "long":
            new_trail = price - atr
        else:
            new_trail = price + atr
        result["profit_state"]["trail_price"] = new_trail

        if size >= 3 and not ps.get("partial_close_2_done"):
            # Close 30% (1 of 3+ contracts)
            close_qty = max(1, int(size * 0.3))
            result["action"] = "PARTIAL_CLOSE"
            result["close_size"] = close_qty
            result["new_sl"] = new_trail
            result["reason"] = f"tp2_partial_close_{close_qty}_of_{size}_trail_at_{new_trail:.6f}"
            result["profit_state"]["partial_close_2_done"] = True
            result["profit_state"]["remaining_size"] = size - close_qty
        else:
            result["action"] = "TRAIL_TIGHTEN"
            result["new_sl"] = new_trail
            result["reason"] = f"tp2_trail_tighten_to_{new_trail:.6f}"
        return result

    # TP1 hit -- move SL to break-even + partial close if possible
    if at_tp1 and not tp1_reached:
        result["profit_state"]["tp1_reached"] = True
        # Break-even = entry + small buffer (0.15% to cover fees)
        if direction == "long":
            be_price = entry_price * 1.0015
        else:
            be_price = entry_price * 0.9985
        result["profit_state"]["sl_at_breakeven"] = True

        if size >= 2 and not ps.get("partial_close_1_done"):
            # Close 40% (or 1 contract if size=2)
            close_qty = max(1, int(size * 0.4))
            result["action"] = "PARTIAL_CLOSE"
            result["close_size"] = close_qty
            result["new_sl"] = be_price
            result["reason"] = f"tp1_partial_close_{close_qty}_of_{size}_sl_to_be_{be_price:.6f}"
            result["profit_state"]["partial_close_1_done"] = True
            result["profit_state"]["remaining_size"] = size - close_qty
        else:
            result["action"] = "MOVE_SL_TO_BE"
            result["new_sl"] = be_price
            result["reason"] = f"tp1_move_sl_to_breakeven_{be_price:.6f}"
        return result

    # Already past TP2 -- update trailing stop
    if tp2_reached and trail > 0:
        if direction == "long":
            new_trail = max(trail, price - atr)
            if price <= trail:
                result["action"] = "FULL_EXIT"
                result["close_size"] = size
                result["reason"] = f"trail_stop_hit_at_{trail:.6f}"
                return result
        else:
            new_trail = min(trail, price + atr) if trail > 0 else price + atr
            if price >= trail:
                result["action"] = "FULL_EXIT"
                result["close_size"] = size
                result["reason"] = f"trail_stop_hit_at_{trail:.6f}"
                return result
        if new_trail != trail:
            result["profit_state"]["trail_price"] = new_trail
            result["action"] = "TRAIL_TIGHTEN"
            result["new_sl"] = new_trail
            result["reason"] = f"trail_updated_{trail:.6f}_to_{new_trail:.6f}"

    # Already past TP1 with SL at BE -- check if BE stop hit
    if sl_at_be and tp1_reached and not tp2_reached:
        if direction == "long":
            be_price = entry_price * 1.0015
            if price <= be_price:
                result["action"] = "FULL_EXIT"
                result["close_size"] = size
                result["reason"] = f"breakeven_stop_hit_at_{be_price:.6f}"
                return result
        else:
            be_price = entry_price * 0.9985
            if price >= be_price:
                result["action"] = "FULL_EXIT"
                result["close_size"] = size
                result["reason"] = f"breakeven_stop_hit_at_{be_price:.6f}"
                return result

    return result
