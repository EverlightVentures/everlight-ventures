"""Hard Risk Gate -- binary pass/fail checks that CANNOT be overridden.

These are the ONLY things that can block a trade outright.
Everything else feeds into the unified score as a modifier.

Returns (passed: bool, reason: str). If passed is False, do not trade.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass
class RiskGateResult:
    passed: bool = True
    reason: str = ""
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "reason": self.reason,
            "details": self.details or {},
        }


def evaluate_risk_gate(
    *,
    # Per-trade risk (the ONLY loss control -- no daily max)
    stop_price: float = 0.0,
    entry_price: float = 0.0,
    size: int = 0,
    contract_size: float = 0.0,
    equity: float = 0.0,
    risk_pct: float = 0.0,

    # Margin
    margin_ok: bool = True,
    enforce_funding: bool = False,

    # Hard caps
    trades_today: int = 0,
    max_trades_per_day: int = 999,
    losses_today: int = 0,
    max_losses_per_day: int = 999,

    # Product availability
    product_available: bool = True,

    # Kill switch
    fail_safe: bool = False,
    runtime_unstable: bool = False,

    # Data freshness
    live_tick_age_sec: float = 0.0,
    max_tick_age_sec: float = 60.0,
    tick_health: str = "ok",
    no_data: bool = False,

    # Pulse danger
    pulse_regime: str = "normal",
    freshness_gates_enabled: bool = True,
) -> RiskGateResult:
    """Run all hard risk checks. Returns immediately on first failure."""

    # Gate 1: No data at all
    if no_data:
        return RiskGateResult(False, "no_data", {"detail": "candle data missing"})

    # Gate 2: Kill switch / fail safe
    if fail_safe:
        return RiskGateResult(False, "kill_switch")
    if runtime_unstable:
        return RiskGateResult(False, "runtime_unstable")

    # Gate 3: Product must exist
    if not product_available:
        return RiskGateResult(False, "product_unavailable")

    # Gate 4: Data freshness (live tick)
    if freshness_gates_enabled:
        if tick_health == "dead":
            return RiskGateResult(False, "live_tick_dead")
        if live_tick_age_sec >= max_tick_age_sec and max_tick_age_sec > 0:
            return RiskGateResult(False, "live_tick_stale", {
                "age_sec": live_tick_age_sec,
                "max_sec": max_tick_age_sec,
            })
        if pulse_regime == "danger":
            return RiskGateResult(False, "market_pulse_danger")

    # Gate 5: Max trades per day
    if trades_today >= max_trades_per_day:
        return RiskGateResult(False, "max_trades_per_day", {
            "trades": trades_today,
            "max": max_trades_per_day,
        })

    # Gate 6: Max losses per day
    if losses_today >= max_losses_per_day:
        return RiskGateResult(False, "max_losses_per_day", {
            "losses": losses_today,
            "max": max_losses_per_day,
        })

    # Gate 7: Margin check
    if enforce_funding and not margin_ok:
        return RiskGateResult(False, "insufficient_margin")

    # Gate 8: Per-trade risk budget (the ONLY loss control)
    if risk_pct > 0 and equity > 0 and contract_size > 0 and stop_price > 0 and entry_price > 0:
        risk_budget = equity * risk_pct
        risk_usd = abs(entry_price - stop_price) * contract_size * size
        if risk_usd > risk_budget:
            return RiskGateResult(False, "per_trade_risk_exceeded", {
                "risk_usd": round(risk_usd, 2),
                "risk_budget": round(risk_budget, 2),
                "risk_pct": risk_pct,
            })

    # All hard gates passed
    return RiskGateResult(True, "all_clear")
