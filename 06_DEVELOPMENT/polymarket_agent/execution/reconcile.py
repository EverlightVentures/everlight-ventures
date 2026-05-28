"""Reconciliation -- on-chain truth vs internal accounting. Drift halts."""
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path


@dataclass
class ReconcileResult:
    halt_required: bool
    drift_usd: Decimal
    on_chain_usdc: Decimal
    internal_cash: Decimal


class Reconciler:
    def __init__(self, wallet, clob, bankroll_state_path: Path, halt_path: Path,
                 drift_threshold_usd: Decimal = Decimal("0.01")):
        self.wallet = wallet
        self.clob = clob
        self.bankroll_state_path = Path(bankroll_state_path)
        self.halt_path = Path(halt_path)
        self.drift_threshold = drift_threshold_usd

    def reconcile_now(self) -> ReconcileResult:
        # Sticky halt -- if HALT exists, stay halted regardless of current state
        if self.halt_path.exists():
            return ReconcileResult(
                halt_required=True,
                drift_usd=Decimal("0"),
                on_chain_usdc=Decimal("0"),
                internal_cash=Decimal("0"),
            )

        on_chain = self.wallet.get_usdc_balance()
        state = json.loads(self.bankroll_state_path.read_text())
        internal_cash = Decimal(str(state.get("cash_usdc", 0)))
        drift = abs(on_chain - internal_cash)

        if drift > self.drift_threshold:
            self.halt_path.write_text(json.dumps({
                "drift_usd": f"{drift:.2f}",
                "on_chain_usdc": f"{on_chain:.6f}",
                "internal_cash_usdc": f"{internal_cash:.6f}",
                "ts": datetime.now(timezone.utc).isoformat(),
            }, indent=2))
            return ReconcileResult(
                halt_required=True,
                drift_usd=drift,
                on_chain_usdc=on_chain,
                internal_cash=internal_cash,
            )

        return ReconcileResult(
            halt_required=False,
            drift_usd=drift,
            on_chain_usdc=on_chain,
            internal_cash=internal_cash,
        )
