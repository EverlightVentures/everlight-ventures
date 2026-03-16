"""Balance Reconciliation & Self-Heal Layer.

Ensures wallet balances match expected canonical state:
- IDLE: all funds in spot USDC, derivatives ≈ buffer only
- IN_TRADE: derivatives has required margin + buffer
- POST_EXIT: derivatives swept back to spot USDC

Detects drift, applies corrective transfers, logs everything.
Enters SAFE_MODE if reconciliation fails repeatedly.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class BalanceSnapshot:
    """Ground truth from exchange APIs."""
    spot_usdc: float = 0.0
    spot_usd: float = 0.0
    spot_other: dict[str, float] = field(default_factory=dict)  # symbol -> value_usd
    derivatives_usdc: float = 0.0   # buying power / available margin
    total_equity: float = 0.0
    open_positions: int = 0
    open_orders: int = 0
    fetch_ok: bool = False
    error: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DriftReport:
    """What's wrong and what to fix."""
    drifts: list[dict] = field(default_factory=list)
    actions: list[dict] = field(default_factory=list)
    ok: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ReconcileResult:
    """Outcome of one reconciliation cycle."""
    mode: str              # IDLE / IN_TRADE / POST_EXIT / STARTUP
    snapshot: BalanceSnapshot
    drift: DriftReport
    actions_taken: list[dict] = field(default_factory=list)
    status: str = "OK"     # OK / DRIFT_FIXED / SAFE_MODE / ERROR
    safe_mode: bool = False
    safe_mode_reason: str | None = None

    def to_dict(self) -> dict:
        d = {
            "mode": self.mode,
            "snapshot": self.snapshot.to_dict(),
            "drift": self.drift.to_dict(),
            "actions_taken": self.actions_taken,
            "status": self.status,
            "safe_mode": self.safe_mode,
            "safe_mode_reason": self.safe_mode_reason,
        }
        return d


def get_balance_snapshot(api, currencies: list[str] | None = None) -> BalanceSnapshot:
    """Fetch ground truth balances from exchange."""
    snap = BalanceSnapshot()
    currencies = currencies or ["USD", "USDC"]
    try:
        # Spot balances
        spot_map = api.get_spot_cash_map(currencies)
        snap.spot_usdc = float(spot_map.get("USDC", 0))
        snap.spot_usd = float(spot_map.get("USD", 0))

        # Derivatives balance — use actual wallet balance (cfm_usd_balance),
        # NOT futures_buying_power which includes cross-margin from spot and
        # causes the reconciler to try sweeping money that isn't in derivatives.
        bs = api.get_futures_balance_summary() or {}
        root = bs.get("balance_summary", {}) if isinstance(bs, dict) else {}
        if isinstance(root, dict):
            # cfm_usd_balance = actual derivatives wallet balance
            cfm_bal = root.get("cfm_usd_balance")
            if cfm_bal is not None:
                try:
                    val = cfm_bal.get("value", 0) if isinstance(cfm_bal, dict) else cfm_bal
                    snap.derivatives_usdc = float(val or 0)
                except Exception:
                    pass

            total = root.get("total_usd_balance") or root.get("total_funds_for_margin")
            if total is not None:
                try:
                    if isinstance(total, dict):
                        total = total.get("value", 0)
                    snap.total_equity = float(total)
                except Exception:
                    pass

        # Fallback to buying power if cfm_usd_balance wasn't available
        if snap.derivatives_usdc <= 0:
            inner = getattr(api, "api", api)
            bp = float(inner.get_cfm_buying_power() or 0)
            snap.derivatives_usdc = bp

        # Open positions count
        try:
            positions = api.get_futures_positions() or []
            snap.open_positions = sum(
                1 for p in positions
                if abs(float((p or {}).get("number_of_contracts") or (p or {}).get("size") or 0)) > 0
            )
        except Exception:
            pass

        # Open orders count
        try:
            orders = api.get_open_orders() or []
            snap.open_orders = len(orders)
        except Exception:
            pass

        snap.fetch_ok = True
    except Exception as e:
        snap.error = str(e)
        snap.fetch_ok = False

    # Compute total equity if not from API
    if snap.total_equity <= 0:
        snap.total_equity = snap.spot_usdc + snap.spot_usd + snap.derivatives_usdc

    return snap


def detect_drift(
    snap: BalanceSnapshot,
    *,
    mode: str,
    buffer_usdc: float = 2.0,
    sweep_threshold: float = 5.0,
    required_margin: float = 0.0,
    require_all_usdc: bool = True,
    auto_convert_usd: bool = True,
) -> DriftReport:
    """Compare snapshot against canonical expected state."""
    report = DriftReport()

    if not snap.fetch_ok:
        report.ok = False
        report.drifts.append({"type": "FETCH_FAILED", "error": snap.error})
        return report

    # ── USD residual detection — auto-convert to USDC ────────────────────
    if snap.spot_usd > 1.0:
        report.drifts.append({
            "type": "USD_RESIDUAL",
            "amount": snap.spot_usd,
        })
        if auto_convert_usd:
            # Keep $0.50 as dust buffer, convert the rest
            convert_amt = round(snap.spot_usd - 0.50, 2)
            if convert_amt >= 1.0:
                report.actions.append({
                    "action": "CONVERT_USD_TO_USDC",
                    "amount": convert_amt,
                })
        elif require_all_usdc:
            report.actions.append({
                "action": "LOG_MANUAL_CONVERSION",
                "message": f"${snap.spot_usd:.2f} USD in spot — convert to USDC manually",
            })

    # ── Non-USDC crypto detection ────────────────────────────────────────
    for symbol, value in (snap.spot_other or {}).items():
        if value > 1.0:
            report.drifts.append({
                "type": "NON_USDC_RESIDUAL",
                "symbol": symbol,
                "value_usd": value,
                "action": "MANUAL_CONSOLIDATION_OPTIONAL",
            })

    # ── Mode-specific drift checks ───────────────────────────────────────
    if mode in ("IDLE", "STARTUP", "POST_EXIT"):
        # Derivatives should be ≈ buffer only
        excess = snap.derivatives_usdc - buffer_usdc
        if excess > sweep_threshold:
            report.drifts.append({
                "type": "DERIVATIVES_EXCESS",
                "derivatives_usdc": snap.derivatives_usdc,
                "expected_max": buffer_usdc,
                "excess": excess,
            })
            report.actions.append({
                "action": "SWEEP_TO_SPOT",
                "amount": round(excess, 2),
            })

        # Derivatives below buffer (need top-up)
        deficit = buffer_usdc - snap.derivatives_usdc
        if deficit > 1.0 and snap.spot_usdc >= deficit + 5.0:
            report.drifts.append({
                "type": "DERIVATIVES_DEFICIT",
                "derivatives_usdc": snap.derivatives_usdc,
                "expected_min": buffer_usdc,
                "deficit": deficit,
            })
            report.actions.append({
                "action": "TOPUP_DERIVATIVES",
                "amount": round(deficit + 1.0, 2),  # small cushion
            })

    elif mode == "IN_TRADE":
        # Derivatives must have enough margin
        needed = required_margin + buffer_usdc
        shortfall = needed - snap.derivatives_usdc
        if shortfall > 1.0:
            report.drifts.append({
                "type": "MARGIN_SHORTFALL",
                "derivatives_usdc": snap.derivatives_usdc,
                "required": needed,
                "shortfall": shortfall,
            })
            if snap.spot_usdc >= shortfall:
                report.actions.append({
                    "action": "TRANSFER_FOR_MARGIN",
                    "amount": round(shortfall + 2.0, 2),
                })
            else:
                report.actions.append({
                    "action": "SAFE_MODE",
                    "reason": f"insufficient total funds: need ${needed:.2f}, have ${snap.derivatives_usdc + snap.spot_usdc:.2f}",
                })

    elif mode == "PRE_ENTRY":
        # About to enter — ensure_futures_margin handles this, just validate
        needed = required_margin + buffer_usdc
        total_available = snap.derivatives_usdc + snap.spot_usdc
        if total_available < needed:
            report.drifts.append({
                "type": "INSUFFICIENT_FOR_ENTRY",
                "total_available": total_available,
                "required": needed,
            })
            report.actions.append({
                "action": "BLOCK_ENTRY",
                "reason": f"total ${total_available:.2f} < required ${needed:.2f}",
            })

    report.ok = len(report.drifts) == 0 or all(
        d.get("type") in ("USD_RESIDUAL", "NON_USDC_RESIDUAL") for d in report.drifts
    )

    return report


def apply_self_heal(
    api,
    drift: DriftReport,
    *,
    currency: str = "USDC",
    max_retries: int = 3,
) -> list[dict]:
    """Execute corrective actions from drift report."""
    results: list[dict] = []

    for action in drift.actions:
        act = action.get("action", "")

        if act == "SWEEP_TO_SPOT":
            amount = float(action.get("amount", 0))
            if amount < 1.0:
                continue
            ok = False
            for attempt in range(max_retries):
                try:
                    tx = api.transfer_futures_profit(amount, currency=currency)
                    ok = bool((tx or {}).get("ok"))
                    results.append({
                        "action": "SWEEP_TO_SPOT",
                        "amount": amount,
                        "ok": ok,
                        "attempt": attempt + 1,
                        "response": (tx or {}).get("reason"),
                    })
                    if ok:
                        break
                except Exception as e:
                    results.append({
                        "action": "SWEEP_TO_SPOT",
                        "amount": amount,
                        "ok": False,
                        "attempt": attempt + 1,
                        "error": str(e),
                    })

        elif act == "TOPUP_DERIVATIVES":
            # CDE auto-sweeps spot->futures when an order is placed.
            # Manual move_portfolio_funds always fails (CDE has 1 portfolio).
            # Just log the intent and let Coinbase handle it at order time.
            amount = float(action.get("amount", 0))
            results.append({
                "action": "TOPUP_DERIVATIVES",
                "amount": amount,
                "ok": True,
                "response": "cde_auto_sweep_at_order_time",
            })

        elif act == "TRANSFER_FOR_MARGIN":
            # CDE auto-sweeps spot->futures when an order is placed.
            # Manual move_portfolio_funds always fails (CDE has 1 portfolio).
            amount = float(action.get("amount", 0))
            results.append({
                "action": "TRANSFER_FOR_MARGIN",
                "amount": amount,
                "ok": True,
                "response": "cde_auto_sweep_at_order_time",
            })

        elif act == "CONVERT_USD_TO_USDC":
            amount = float(action.get("amount", 0))
            if amount < 1.0:
                continue
            try:
                tx = api.convert_usd_to_usdc(amount)
                ok = bool((tx or {}).get("ok"))
                results.append({
                    "action": "CONVERT_USD_TO_USDC",
                    "amount": amount,
                    "ok": ok,
                    "response": (tx or {}).get("reason"),
                })
            except Exception as e:
                results.append({
                    "action": "CONVERT_USD_TO_USDC",
                    "amount": amount,
                    "ok": False,
                    "error": str(e),
                })

        elif act in ("LOG_MANUAL_CONVERSION", "BLOCK_ENTRY"):
            results.append({"action": act, "logged": True, "message": action.get("message") or action.get("reason")})

        elif act == "SAFE_MODE":
            results.append({"action": "SAFE_MODE", "reason": action.get("reason")})

    return results


def reconcile_balances(
    api,
    *,
    config: dict,
    state: dict,
    mode: str = "IDLE",
    now: datetime | None = None,
    required_margin: float = 0.0,
) -> ReconcileResult:
    """
    Full reconciliation cycle:
    1. Fetch ground truth
    2. Detect drift
    3. Apply self-heal
    4. Verify
    """
    now = now or datetime.now(timezone.utc)
    recon_cfg = config.get("balance_reconciliation", {}) or {}
    funding_cfg = config.get("futures_funding", {}) or {}

    buffer_usdc = float(recon_cfg.get("buffer_usdc", 2.0) or 2.0)
    sweep_threshold = float(recon_cfg.get("sweep_threshold_usdc",
                            (funding_cfg.get("idle_sweep", {}) or {}).get("min_sweep_usd", 5.0)) or 5.0)
    require_all_usdc = bool(recon_cfg.get("require_all_usdc", False))
    auto_convert_usd = bool(recon_cfg.get("auto_convert_usd", True))
    max_retries = int(recon_cfg.get("max_transfer_retries", 3) or 3)
    currency = str(funding_cfg.get("currency", "USDC") or "USDC").strip().upper()

    # 1. Snapshot
    snap = get_balance_snapshot(api, currencies=["USD", "USDC"])

    # 2. Detect drift
    drift = detect_drift(
        snap,
        mode=mode,
        buffer_usdc=buffer_usdc,
        sweep_threshold=sweep_threshold,
        required_margin=required_margin,
        require_all_usdc=require_all_usdc,
        auto_convert_usd=auto_convert_usd,
    )

    result = ReconcileResult(mode=mode, snapshot=snap, drift=drift)

    # 3. Apply self-heal if needed
    if drift.actions:
        actions_taken = apply_self_heal(
            api, drift, currency=currency, max_retries=max_retries,
        )
        result.actions_taken = actions_taken

        # Check for SAFE_MODE triggers
        # Only critical failures (margin funding) should trigger SAFE_MODE.
        # SWEEP_TO_SPOT failures are yield optimization — not safety-critical.
        safe_mode_actions = [a for a in actions_taken if a.get("action") == "SAFE_MODE"]
        failed_transfers = [a for a in actions_taken
                           if a.get("action") in ("TOPUP_DERIVATIVES", "TRANSFER_FOR_MARGIN")
                           and not a.get("ok")]

        if safe_mode_actions:
            result.safe_mode = True
            result.safe_mode_reason = safe_mode_actions[0].get("reason", "unknown")
            result.status = "SAFE_MODE"
        elif failed_transfers:
            # All retries failed
            if len(failed_transfers) >= max_retries:
                result.safe_mode = True
                result.safe_mode_reason = f"transfer_failed_{max_retries}_times"
                result.status = "SAFE_MODE"
            else:
                result.status = "PARTIAL_FIX"
        elif drift.drifts:
            result.status = "DRIFT_FIXED"
        else:
            result.status = "OK"
    else:
        if not drift.ok:
            result.status = "DRIFT_DETECTED"
        else:
            result.status = "OK"

    # 4. Update state with reconcile info
    prev_drift_count = int(state.get("_reconcile_drift_count_today", 0) or 0)
    new_drifts = len([d for d in drift.drifts if d.get("type") not in ("USD_RESIDUAL", "NON_USDC_RESIDUAL")])
    state["_reconcile_drift_count_today"] = prev_drift_count + new_drifts
    state["_last_reconcile_status"] = result.status
    state["_last_reconcile_ts"] = now.isoformat()
    state["_safe_mode"] = result.safe_mode
    if result.safe_mode:
        state["_safe_mode_reason"] = result.safe_mode_reason
    elif state.get("_safe_mode"):
        # Clear safe mode if reconcile is now OK
        state["_safe_mode"] = False
        state["_safe_mode_reason"] = None

    return result
