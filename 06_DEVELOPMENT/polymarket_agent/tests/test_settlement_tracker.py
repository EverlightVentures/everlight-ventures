import json
from decimal import Decimal
from pathlib import Path
from polymarket_agent.execution.settlement_tracker import SettlementTracker


def _write(p: Path, obj):
    p.write_text(json.dumps(obj))


def test_sums_today_pnl_into_state(tmp_path):
    state = tmp_path / "bankroll.json"
    _write(state, {"cash_usdc": 250.0, "daily_pnl_usdc": 0.0, "daily_pnl_date": "2026-05-28"})
    closed = tmp_path / "closed_bets.json"
    _write(closed, [
        {"id": "a", "pnl_usdc": "5.0", "settled_date": "2026-05-28T10:00:00+00:00"},
        {"id": "b", "pnl_usdc": "-3.0", "settled_date": "2026-05-28T12:00:00+00:00"},
        {"id": "c", "pnl_usdc": "100.0", "settled_date": "2026-05-27T12:00:00+00:00"},  # yesterday, excluded
    ])
    t = SettlementTracker(state_path=state, closed_bets_path=closed, today="2026-05-28")
    result = t.recompute_daily_pnl()
    assert result == Decimal("2.0")  # 5 - 3
    saved = json.loads(state.read_text())
    assert Decimal(str(saved["daily_pnl_usdc"])) == Decimal("2.0")
    assert saved["daily_pnl_date"] == "2026-05-28"


def test_rolls_over_on_new_day(tmp_path):
    state = tmp_path / "bankroll.json"
    _write(state, {"cash_usdc": 250.0, "daily_pnl_usdc": -40.0, "daily_pnl_date": "2026-05-27"})
    closed = tmp_path / "closed_bets.json"
    _write(closed, [
        {"id": "a", "pnl_usdc": "-40.0", "settled_date": "2026-05-27T10:00:00+00:00"},
    ])
    t = SettlementTracker(state_path=state, closed_bets_path=closed, today="2026-05-28")
    result = t.recompute_daily_pnl()
    assert result == Decimal("0")  # no bets settled today -> fresh day
    saved = json.loads(state.read_text())
    assert Decimal(str(saved["daily_pnl_usdc"])) == Decimal("0")
    assert saved["daily_pnl_date"] == "2026-05-28"


def test_missing_closed_bets_file_yields_zero(tmp_path):
    state = tmp_path / "bankroll.json"
    _write(state, {"cash_usdc": 250.0, "daily_pnl_usdc": 0.0, "daily_pnl_date": "2026-05-28"})
    closed = tmp_path / "closed_bets.json"  # does not exist
    t = SettlementTracker(state_path=state, closed_bets_path=closed, today="2026-05-28")
    result = t.recompute_daily_pnl()
    assert result == Decimal("0")


def test_corrupt_closed_bets_raises(tmp_path):
    state = tmp_path / "bankroll.json"
    _write(state, {"cash_usdc": 250.0, "daily_pnl_usdc": 0.0, "daily_pnl_date": "2026-05-28"})
    closed = tmp_path / "closed_bets.json"
    closed.write_text("{ not valid json")
    t = SettlementTracker(state_path=state, closed_bets_path=closed, today="2026-05-28")
    import pytest
    with pytest.raises(Exception):
        t.recompute_daily_pnl()


def test_atomic_state_write(tmp_path):
    state = tmp_path / "bankroll.json"
    _write(state, {"cash_usdc": 250.0, "daily_pnl_usdc": 0.0, "daily_pnl_date": "2026-05-28"})
    closed = tmp_path / "closed_bets.json"
    _write(closed, [{"id": "a", "pnl_usdc": "7.0", "settled_date": "2026-05-28T10:00:00+00:00"}])
    t = SettlementTracker(state_path=state, closed_bets_path=closed, today="2026-05-28")
    t.recompute_daily_pnl()
    # No leftover temp file, final file is valid JSON
    assert not (tmp_path / "bankroll.json.tmp").exists()
    json.loads(state.read_text())  # must parse
