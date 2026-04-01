"""Pyramiding strategy -- scale into winners.

Instead of entering full size, enter 60% at signal, add 20% on first
pullback that holds, add final 20% on continuation.

GATED: Only activates when equity >= BUILD_B ($750+) and config
pyramiding.enabled = true. At BUILD_A (current), this module documents
the logic but returns neutral sizing.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PyramidPlan:
    """Plan for scaling into a position."""
    enabled: bool = False
    initial_pct: float = 0.6
    add1_pct: float = 0.2
    add1_pullback_atr: float = 0.4
    add2_pct: float = 0.2
    max_adds: int = 2
    reason: str = ""


@dataclass
class PyramidState:
    """Track current pyramid progress for an active position."""
    entry_price: float = 0.0
    direction: str = ""
    initial_size: int = 0
    current_size: int = 0
    adds_completed: int = 0
    add1_triggered: bool = False
    add2_triggered: bool = False
    add1_price: Optional[float] = None
    add2_price: Optional[float] = None


def create_pyramid_plan(config: dict) -> PyramidPlan:
    """Create pyramid plan from config.

    Config expected under 'pyramiding' key:
        enabled: false
        initial_pct: 0.6
        add1_pct: 0.2
        add1_pullback_atr: 0.4
        add2_pct: 0.2
        max_adds: 2
    """
    cfg = config.get("pyramiding", {}) if isinstance(config, dict) else {}
    return PyramidPlan(
        enabled=bool(cfg.get("enabled", False)),
        initial_pct=float(cfg.get("initial_pct", 0.6)),
        add1_pct=float(cfg.get("add1_pct", 0.2)),
        add1_pullback_atr=float(cfg.get("add1_pullback_atr", 0.4)),
        add2_pct=float(cfg.get("add2_pct", 0.2)),
        max_adds=int(cfg.get("max_adds", 2)),
        reason="disabled" if not cfg.get("enabled") else "active",
    )


def compute_initial_size(full_size: int, plan: PyramidPlan) -> int:
    """Compute initial entry size when pyramiding is active.

    If pyramiding disabled, returns full_size unchanged.
    If enabled, returns ceil(full_size * initial_pct).
    """
    if not plan.enabled or full_size <= 1:
        return full_size
    initial = max(1, round(full_size * plan.initial_pct))
    return initial


def check_add_trigger(
    state: PyramidState,
    current_price: float,
    atr_value: float,
    plan: PyramidPlan,
) -> Optional[dict]:
    """Check if conditions are met for a pyramid add.

    Returns dict with add details if triggered, None otherwise.
    Conditions:
        Add #1: price pulls back 0.3-0.5 ATR from entry but holds above entry
        Add #2: price makes new high/low beyond initial impulse
    """
    if not plan.enabled or state.adds_completed >= plan.max_adds:
        return None
    if atr_value <= 0 or state.entry_price <= 0:
        return None

    pullback_dist = abs(current_price - state.entry_price)
    pullback_atr = pullback_dist / atr_value if atr_value > 0 else 0

    # Add #1: pullback that holds
    if not state.add1_triggered and state.adds_completed == 0:
        if state.direction == "long":
            # Price pulled back but still above entry
            if current_price < state.entry_price and current_price > state.entry_price - plan.add1_pullback_atr * atr_value:
                return None  # Still pulling back, wait
            if pullback_atr >= 0.3 * plan.add1_pullback_atr and current_price > state.entry_price:
                return {
                    "add_number": 1,
                    "add_pct": plan.add1_pct,
                    "trigger_price": current_price,
                    "reason": f"pullback_hold_long (pullback {pullback_atr:.2f} ATR, price holding above entry)",
                }
        elif state.direction == "short":
            if current_price > state.entry_price and current_price < state.entry_price + plan.add1_pullback_atr * atr_value:
                return None
            if pullback_atr >= 0.3 * plan.add1_pullback_atr and current_price < state.entry_price:
                return {
                    "add_number": 1,
                    "add_pct": plan.add1_pct,
                    "trigger_price": current_price,
                    "reason": f"pullback_hold_short (pullback {pullback_atr:.2f} ATR, price holding below entry)",
                }

    # Add #2: continuation beyond initial impulse
    if state.add1_triggered and not state.add2_triggered and state.adds_completed == 1:
        if state.direction == "long" and current_price > state.entry_price * 1.005:
            return {
                "add_number": 2,
                "add_pct": plan.add2_pct,
                "trigger_price": current_price,
                "reason": "continuation_long (new high beyond entry)",
            }
        elif state.direction == "short" and current_price < state.entry_price * 0.995:
            return {
                "add_number": 2,
                "add_pct": plan.add2_pct,
                "trigger_price": current_price,
                "reason": "continuation_short (new low beyond entry)",
            }

    return None
