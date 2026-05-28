import json
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock
from polymarket_agent.execution.reconcile import Reconciler


def make_wallet(usdc):
    w = MagicMock()
    w.get_usdc_balance.return_value = Decimal(str(usdc))
    return w


def make_clob(positions):
    c = MagicMock()
    c.get_positions.return_value = positions
    return c


def test_no_drift_returns_pass(tmp_path: Path):
    state_path = tmp_path / "bankroll.json"
    state_path.write_text(json.dumps({"cash_usdc": 250.0, "open_positions_value_usdc": 0.0}))
    halt_path = tmp_path / "HALT"
    wallet = make_wallet(250.0)
    clob = make_clob([])
    r = Reconciler(wallet, clob, bankroll_state_path=state_path,
                   halt_path=halt_path, drift_threshold_usd=Decimal("0.01"))
    result = r.reconcile_now()
    assert result.halt_required is False
    assert not halt_path.exists()


def test_drift_above_threshold_writes_halt(tmp_path: Path):
    state_path = tmp_path / "bankroll.json"
    state_path.write_text(json.dumps({"cash_usdc": 250.0, "open_positions_value_usdc": 0.0}))
    halt_path = tmp_path / "HALT"
    wallet = make_wallet(240.0)  # 10 USDC drift
    clob = make_clob([])
    r = Reconciler(wallet, clob, bankroll_state_path=state_path,
                   halt_path=halt_path, drift_threshold_usd=Decimal("0.01"))
    result = r.reconcile_now()
    assert result.halt_required is True
    assert halt_path.exists()
    halt_data = json.loads(halt_path.read_text())
    assert halt_data["drift_usd"] == "10.00"


def test_sticky_halt_not_cleared_by_subsequent_clean_cycle(tmp_path: Path):
    state_path = tmp_path / "bankroll.json"
    state_path.write_text(json.dumps({"cash_usdc": 250.0, "open_positions_value_usdc": 0.0}))
    halt_path = tmp_path / "HALT"
    halt_path.write_text(json.dumps({"drift_usd": "10.00", "ts": "earlier"}))
    wallet = make_wallet(250.0)
    clob = make_clob([])
    r = Reconciler(wallet, clob, bankroll_state_path=state_path,
                   halt_path=halt_path, drift_threshold_usd=Decimal("0.01"))
    result = r.reconcile_now()
    assert result.halt_required is True  # Sticky
    assert halt_path.exists()
