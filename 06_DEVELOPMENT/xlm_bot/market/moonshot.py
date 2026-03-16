"""Moonshot "let it ride" trade management mode.

When a breakout becomes unusually strong (velocity + OI participation),
suppress fixed TP exits and use a trailing stop instead. Protects profits
while allowing parabolic continuation.

Does NOT change position sizing. Only changes exit logic.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Optional


@dataclass
class MoonshotState:
    active: bool = False
    activation_reason: str | None = None
    activation_ts: str | None = None
    trailing_stop_price: float | None = None
    peak_price: float | None = None
    bars_active: int = 0
    stale_bars: int = 0
    swing_floor: float | None = None


def evaluate_moonshot(
    *,
    direction: str,
    price: float,
    entry_price: float,
    pnl_pct: float,
    contract_ctx: dict,
    atr_value: float,
    regime: str,
    bars_since_entry: int,
    current_moonshot: MoonshotState | None,
    config: dict,
    df_15m=None,
    df_1h=None,
) -> MoonshotState:
    """Evaluate whether to activate, maintain, or deactivate moonshot mode.

    Args:
        direction: "long" or "short"
        price: current price
        entry_price: trade entry price
        pnl_pct: current PnL as decimal (0.01 = 1%)
        contract_ctx: latest ContractSnapshot as dict
        atr_value: current ATR(14) on 15m
        regime: current regime ("trend", "mean_reversion", etc.)
        bars_since_entry: bars since entry
        current_moonshot: previous moonshot state (None if first eval)
        config: moonshot config section from config.yaml
    """
    if not config.get("enabled", False):
        return MoonshotState()

    d = direction.lower().strip()
    vel_thresh = float(config.get("velocity_threshold_pct", 0.02) or 0.02)
    min_pnl = float(config.get("min_pnl_pct", 0.01) or 0.01)
    trail_mult = float(config.get("trail_atr_mult", 2.0) or 2.0)
    require_oi = bool(config.get("require_oi_rising", True))
    require_trend = bool(config.get("require_trend_regime", True))
    max_stale = int(config.get("max_stale_bars", 3) or 3)

    oi_trend = str(contract_ctx.get("oi_trend") or "UNKNOWN")
    price_delta = _velocity_pct(entry_price, price, d)

    # ── Already in moonshot mode ──
    if current_moonshot and current_moonshot.active:
        ms = MoonshotState(
            active=True,
            activation_reason=current_moonshot.activation_reason,
            activation_ts=current_moonshot.activation_ts,
            peak_price=current_moonshot.peak_price,
            trailing_stop_price=current_moonshot.trailing_stop_price,
            bars_active=current_moonshot.bars_active + 1,
            stale_bars=current_moonshot.stale_bars,
        )

        # Compute swing structure floor
        swing_floor = _compute_swing_floor(d, df_15m, df_1h)
        ms.swing_floor = swing_floor

        # Velocity-aware trail widening
        effective_mult = trail_mult
        if df_15m is not None and hasattr(df_15m, "empty") and not df_15m.empty and len(df_15m) >= 20:
            try:
                pv = abs(price - float(df_15m["close"].iloc[-3])) / price if price > 0 else 0
                vn = float(df_15m["volume"].iloc[-1])
                va = float(df_15m["volume"].rolling(20).mean().iloc[-1])
                if pv > 0.015 and va > 0 and vn > va * 1.3:
                    effective_mult = trail_mult * 1.3  # Widen trail during velocity
            except Exception:
                pass

        # Update peak and trail with structure floor
        if d == "long":
            new_peak = max(price, ms.peak_price or price)
            ms.peak_price = new_peak
            atr_trail = new_peak - (atr_value * effective_mult)
            ms.trailing_stop_price = max(atr_trail, swing_floor) if swing_floor and swing_floor > 0 else atr_trail
        else:
            new_peak = min(price, ms.peak_price or price)
            ms.peak_price = new_peak
            atr_trail = new_peak + (atr_value * effective_mult)
            ms.trailing_stop_price = min(atr_trail, swing_floor) if swing_floor and swing_floor > 0 else atr_trail

        # Check for new peak
        old_peak = current_moonshot.peak_price
        if old_peak is not None and ms.peak_price == old_peak:
            ms.stale_bars = current_moonshot.stale_bars + 1
        else:
            ms.stale_bars = 0

        # Deactivation: OI flipped or stale
        if require_oi and oi_trend == "FALLING":
            ms.active = False
            ms.activation_reason = "deactivated_oi_falling"
        elif ms.stale_bars >= max_stale:
            ms.active = False
            ms.activation_reason = "deactivated_stale"

        return ms

    # ── Check activation conditions ──
    if bars_since_entry < 2:
        return MoonshotState()

    if abs(pnl_pct) < min_pnl:
        return MoonshotState()

    # Velocity check: current bar move relative to entry
    if abs(price_delta) < vel_thresh:
        return MoonshotState()

    # Direction match
    if d == "long" and price <= entry_price:
        return MoonshotState()
    if d == "short" and price >= entry_price:
        return MoonshotState()

    # OI participation
    if require_oi and oi_trend != "RISING":
        return MoonshotState()

    # Regime
    if require_trend and regime.lower().strip() != "trend":
        return MoonshotState()

    # All conditions met — activate with structure-aware trail
    swing_floor = _compute_swing_floor(d, df_15m, df_1h)
    if d == "long":
        atr_trail = price - (atr_value * trail_mult)
        trail = max(atr_trail, swing_floor) if swing_floor and swing_floor > 0 else atr_trail
    else:
        atr_trail = price + (atr_value * trail_mult)
        trail = min(atr_trail, swing_floor) if swing_floor and swing_floor > 0 else atr_trail

    reasons = [f"velocity={abs(price_delta)*100:.2f}%", f"oi={oi_trend}", f"regime={regime}"]

    return MoonshotState(
        active=True,
        activation_reason=", ".join(reasons),
        activation_ts=datetime.now(timezone.utc).isoformat(),
        trailing_stop_price=trail,
        peak_price=price,
        bars_active=1,
        stale_bars=0,
        swing_floor=swing_floor,
    )


def moonshot_trail_hit(moonshot: MoonshotState, price: float, direction: str) -> bool:
    """Check if price has crossed the moonshot trailing stop."""
    if not moonshot or not moonshot.active or moonshot.trailing_stop_price is None:
        return False
    d = direction.lower().strip()
    if d == "long":
        return price <= moonshot.trailing_stop_price
    else:
        return price >= moonshot.trailing_stop_price


# Exits that moonshot suppresses (replaced by trailing stop)
_SUPPRESSED_EXITS = {"tp1", "time_stop", "early_save", "reversal_signal"}
# Exits that are ALWAYS respected even during moonshot -- hard risk controls NEVER suppressed
_PRESERVED_EXITS = {
    "cutoff_derisk", "trend_flip", "profit_lock", "recovery_take_profit",
    "min_profit_floor", "profit_decay",
    "max_hold_time",           # hard wall: position held too long
    "single_trade_max_loss",   # hard dollar-loss stop
}


def moonshot_overrides_exit(
    moonshot: MoonshotState,
    exit_reason: str | None,
    price: float,
    direction: str,
) -> tuple[bool, str | None]:
    """Check if moonshot should suppress or replace an exit.

    Returns:
        (should_suppress, replacement_reason)
        - (True, None): suppress the exit entirely
        - (False, "moonshot_trail_stop"): replace with trail stop exit
        - (False, None): let original exit through
    """
    if not moonshot or not moonshot.active:
        return False, None

    # Always check trailing stop first
    if moonshot_trail_hit(moonshot, price, direction):
        return False, "moonshot_trail_stop"

    # Preserved exits pass through
    if exit_reason in _PRESERVED_EXITS:
        return False, None

    # Suppress standard exits
    if exit_reason in _SUPPRESSED_EXITS:
        return True, None

    # Unknown exit type — let it through to be safe
    return False, None


def moonshot_as_dict(ms: MoonshotState | None) -> dict | None:
    if ms is None:
        return None
    return asdict(ms)


def _velocity_pct(entry: float, current: float, direction: str) -> float:
    if entry <= 0:
        return 0.0
    raw = (current - entry) / entry
    return raw if direction == "long" else -raw


def _compute_swing_floor(direction: str, df_15m, df_1h) -> float | None:
    """Compute swing structure floor for trailing stop.

    For longs: returns swing_low (trail should never drop below this).
    For shorts: returns swing_high (trail should never rise above this).
    """
    try:
        from structure.fib import find_swing
        swing_df = df_1h if (df_1h is not None and hasattr(df_1h, "empty") and not df_1h.empty and len(df_1h) >= 20) else df_15m
        if swing_df is None or not hasattr(swing_df, "empty") or swing_df.empty:
            return None
        swing_high, swing_low = find_swing(swing_df, 50)
        if direction == "long" and swing_low > 0:
            return swing_low
        elif direction == "short" and swing_high > 0:
            return swing_high
    except Exception:
        pass
    return None
