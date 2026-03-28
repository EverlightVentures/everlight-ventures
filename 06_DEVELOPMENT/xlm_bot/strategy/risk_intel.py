"""Risk Intelligence Module -- advanced risk guards for the XLM bot.

Three functions for legendary-level risk management:
  1. daily_equity_highwater  -- track intraday peak, protect gains on drawdown
  2. correlation_guard       -- detect BTC macro moves that drag XLM with a lag
  3. spread_spike_detector   -- catch liquidity pulls when MMs widen spreads

All functions are pure Python (datetime, typing only). Every function handles
None, empty, or missing state gracefully with safe defaults.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# 1. Daily Equity Highwater
# ---------------------------------------------------------------------------

def daily_equity_highwater(
    state: Dict[str, Any],
    current_equity: float,
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Track intraday peak equity and scale position size on drawdown.

    Args:
        state: Bot state dict. Reads equity_highwater_usd, equity_start_usd.
        current_equity: Current account equity in USD.
        config: Optional overrides (unused today, reserved for threshold tuning).

    Returns:
        Dict with size_mult, mode, highwater, drawdown_pct, daily_pnl_pct,
        and update_state containing the new equity_highwater_usd.
    """
    if state is None:
        state = {}

    # Safe defaults -- if we have no history, assume we started at current equity
    equity_start = _safe_float(state.get("equity_start_usd"), current_equity)
    stored_hw = _safe_float(state.get("equity_highwater_usd"), current_equity)

    # Current equity must be positive to do any math
    if current_equity <= 0:
        return {
            "size_mult": 0.0,
            "mode": "capital_preservation",
            "highwater": stored_hw,
            "drawdown_pct": 100.0,
            "daily_pnl_pct": 0.0,
            "update_state": {"equity_highwater_usd": stored_hw},
        }

    # Update highwater mark
    new_hw = max(stored_hw, current_equity)

    # Drawdown from peak
    if new_hw > 0:
        dd_pct = (new_hw - current_equity) / new_hw * 100.0
    else:
        dd_pct = 0.0

    # Daily PnL
    if equity_start > 0:
        daily_pnl_pct = (current_equity - equity_start) / equity_start * 100.0
    else:
        daily_pnl_pct = 0.0

    # Tiered drawdown response
    if dd_pct < 1.0:
        size_mult = 1.0
        mode = "full_risk"
    elif dd_pct < 3.0:
        size_mult = 0.75
        mode = "protecting_gains"
    elif dd_pct < 5.0:
        size_mult = 0.50
        mode = "defensive"
    else:
        size_mult = 0.25
        mode = "capital_preservation"

    return {
        "size_mult": size_mult,
        "mode": mode,
        "highwater": round(new_hw, 4),
        "drawdown_pct": round(dd_pct, 4),
        "daily_pnl_pct": round(daily_pnl_pct, 4),
        "update_state": {"equity_highwater_usd": new_hw},
    }


# ---------------------------------------------------------------------------
# 2. Correlation Guard (BTC macro move detector)
# ---------------------------------------------------------------------------

def correlation_guard(
    state: Dict[str, Any],
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Check if BTC had a large 1h move that XLM will follow with a lag.

    A 2%+ BTC dump means XLM longs are dangerous (and vice versa).

    Args:
        state: Bot state dict. Reads btc_last_price, btc_price_1h_ago.
        config: Optional overrides (unused today).

    Returns:
        Dict with action, btc_change_pct, size_mult, block_minutes,
        btc_direction, danger_direction.
    """
    if state is None:
        state = {}

    btc_now = _safe_float(state.get("btc_last_price"), 0.0)
    btc_1h = _safe_float(state.get("btc_price_1h_ago"), 0.0)

    # If we have no BTC data, pass through -- do not block
    if btc_now <= 0 or btc_1h <= 0:
        return {
            "action": "clear",
            "btc_change_pct": 0.0,
            "size_mult": 1.0,
            "block_minutes": 0,
            "btc_direction": "flat",
            "danger_direction": "none",
        }

    btc_change_pct = (btc_now - btc_1h) / btc_1h * 100.0
    abs_change = abs(btc_change_pct)

    # Direction
    if btc_change_pct > 0.1:
        btc_direction = "up"
    elif btc_change_pct < -0.1:
        btc_direction = "down"
    else:
        btc_direction = "flat"

    # Danger: if BTC dumped, XLM longs are dangerous. If BTC pumped, shorts are.
    if btc_direction == "down":
        danger_direction = "long"
    elif btc_direction == "up":
        danger_direction = "short"
    else:
        danger_direction = "none"

    # Tiered response
    if abs_change < 1.0:
        action = "clear"
        size_mult = 1.0
        block_minutes = 0
    elif abs_change < 2.0:
        action = "caution"
        size_mult = 0.50
        block_minutes = 0
    else:
        action = "block"
        size_mult = 0.0
        block_minutes = 15

    return {
        "action": action,
        "btc_change_pct": round(btc_change_pct, 4),
        "size_mult": size_mult,
        "block_minutes": block_minutes,
        "btc_direction": btc_direction,
        "danger_direction": danger_direction,
    }


# ---------------------------------------------------------------------------
# 3. Spread Spike Detector
# ---------------------------------------------------------------------------

def spread_spike_detector(
    state: Dict[str, Any],
    current_spread_pct: float,
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Detect when market makers pull liquidity and the spread widens.

    Tracks a rolling window of recent spreads. If the current spread exceeds
    2x the average for 3+ consecutive readings, entries are blocked.

    Args:
        state: Bot state dict. Reads recent_spreads (list of floats, last 20).
        current_spread_pct: Current bid-ask spread as a percentage.
        config: Optional overrides (unused today).

    Returns:
        Dict with action, current_spread_pct, avg_spread_pct, spike_ratio,
        size_mult, consecutive_wide.
    """
    if state is None:
        state = {}

    recent: List[float] = state.get("recent_spreads") or []

    # Filter out any garbage values
    clean_recent = [s for s in recent if isinstance(s, (int, float)) and s >= 0]

    # Compute average spread from history
    if clean_recent:
        avg_spread = sum(clean_recent) / len(clean_recent)
    else:
        # No history -- use current as baseline, treat as normal
        avg_spread = current_spread_pct if current_spread_pct > 0 else 0.01

    # Avoid division by zero
    if avg_spread <= 0:
        avg_spread = 0.01

    spike_ratio = current_spread_pct / avg_spread

    # Count consecutive wide readings (>= 2x) at the tail of history
    # We check how many of the most recent readings (including current) are wide
    consecutive_wide = 0
    all_readings = clean_recent + [current_spread_pct]
    for spread_val in reversed(all_readings):
        if spread_val >= 2.0 * avg_spread:
            consecutive_wide += 1
        else:
            break

    # Tiered response
    if spike_ratio < 1.5:
        action = "normal"
        size_mult = 1.0
    elif spike_ratio < 2.0:
        action = "elevated"
        size_mult = 0.75
    else:
        # Spread is >= 2x average
        if consecutive_wide >= 3:
            action = "spike"
            size_mult = 0.0
        else:
            # Wide but not yet persistent -- treat as elevated
            action = "elevated"
            size_mult = 0.75

    return {
        "action": action,
        "current_spread_pct": round(current_spread_pct, 6),
        "avg_spread_pct": round(avg_spread, 6),
        "spike_ratio": round(spike_ratio, 4),
        "size_mult": size_mult,
        "consecutive_wide": consecutive_wide,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_float(val: Any, default: float = 0.0) -> float:
    """Convert a value to float safely, returning default on failure."""
    if val is None:
        return default
    try:
        result = float(val)
        return result
    except (ValueError, TypeError):
        return default
