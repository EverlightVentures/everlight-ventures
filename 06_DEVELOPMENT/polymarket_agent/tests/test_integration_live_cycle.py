"""Integration test for run_live_cycle -- the real autonomous loop.

Network (scan) + backend + wallet are mocked so this runs offline. It proves
the wiring that matters for real money: outcome -> CLOB token_id mapping, the
per-cycle fresh whitelist, and that an approved bet reaches the live backend's
place_order with the correct token id (not the gamma market id)."""
import json
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from polymarket_agent.main import run_live_cycle
from polymarket_agent.dataflows.polymarket_clob import Market
from polymarket_agent.dataflows.interface import Signal


@pytest.fixture(autouse=True)
def _isolated_cycle():
    """Isolate the cycle from network: mock the notifier (Slack/Blinko tested in
    test_notify.py) and inject one matching signal (the predictor now skips
    markets with zero signals, so a Fed signal lets the 'Will Fed cut?' market
    reach the LLM step, which the tests mock via Predictor._llm_predict)."""
    sig = [Signal(source="test", text="Fed rate cut expected this meeting")]
    with patch("polymarket_agent.main._make_notifier", return_value=MagicMock()), \
         patch("polymarket_agent.main.gather_signals", return_value=sig):
        yield


def _cfg(tmp_path):
    return {
        "polymarket": {"max_markets_scan": 10},
        "proxy": {"url": "https://x", "enabled": False},
        # min_confidence 0.4: the brain-bridge halves raw confidence when no brain
        # policy is supplied (0.95 -> ~0.475), so the live threshold must account
        # for that. Real threshold calibration is a Phase I tuning item.
        "risk": {"max_bet_pct": 5.0, "max_daily_loss_pct": 15.0,
                 "max_open_positions": 10, "min_edge": 0.05, "min_confidence": 0.4},
        "bankroll": {"initial": 250.0},
        "live_trading": {"enabled": True},
        # Disable network signal sources in unit tests (no live HTTP)
        "sonar": {"enabled": False},
        "rss_news": {"enabled": False},
        "rsshub": {"enabled": False},
        "telegram": {"enabled": False},
        "wallet": {"key_path": "/unused/in/test"},
        "data_dir": str(tmp_path),
        "halt_path": str(tmp_path / "HALT"),
    }


def _market():
    return Market(
        id="999", question="Will Fed cut?", slug="fed",
        outcomes=["Yes", "No"], prices={"Yes": 0.5, "No": 0.5},
        liquidity=10000, volume_24h=2000,
        end_date="2026-12-31T00:00:00+00:00", category="Economics", spread=0.02,
        clob_token_ids=["TOKEN_YES_123", "TOKEN_NO_456"],
    )


def test_live_cycle_maps_outcome_to_token_and_calls_backend(tmp_path, monkeypatch):
    monkeypatch.setenv("LIVE_TRADING", "true")
    monkeypatch.delenv("EV_TRADER_HALT", raising=False)

    # Bankroll funded so check 5/8 pass
    (tmp_path / "bankroll.json").write_text(json.dumps({
        "cash_usdc": 250.0, "open_positions_value_usdc": 0.0, "daily_pnl_usdc": 0.0,
    }))
    (tmp_path / "open_bets.json").write_text(json.dumps([]))

    # Injected backend: accepts the order, reports balance for check 8 + reconcile
    backend = MagicMock()
    backend.place_order.return_value = {"orderID": "LIVE_ORDER_1"}
    wallet = MagicMock()
    wallet.get_usdc_balance.return_value = Decimal("250")

    with patch("polymarket_agent.main.PolymarketCLOB") as MockCLOB, \
         patch("polymarket_agent.agents.predictor.Predictor._llm_predict",
               return_value=(0.65, 0.95, "edge=15%")):
        MockCLOB.return_value.scan_markets.return_value = [_market()]
        result = run_live_cycle(_cfg(tmp_path), backend=backend, wallet=wallet)

    # An order was placed through the live backend
    assert backend.place_order.call_count == 1
    _, kwargs = backend.place_order.call_args
    # CRITICAL: the token id, not the gamma market id "999"
    assert kwargs["token_id"] == "TOKEN_YES_123"
    assert kwargs["side"] == "BUY"
    assert result["placed"] == 1
    assert result["halt"] is False


def test_live_cycle_skips_when_no_token_id(tmp_path, monkeypatch):
    monkeypatch.setenv("LIVE_TRADING", "true")
    monkeypatch.delenv("EV_TRADER_HALT", raising=False)
    (tmp_path / "bankroll.json").write_text(json.dumps({
        "cash_usdc": 250.0, "open_positions_value_usdc": 0.0, "daily_pnl_usdc": 0.0,
    }))
    (tmp_path / "open_bets.json").write_text(json.dumps([]))

    backend = MagicMock()
    wallet = MagicMock()
    wallet.get_usdc_balance.return_value = Decimal("250")

    m = _market()
    m.clob_token_ids = []  # no token ids -> cannot trade

    with patch("polymarket_agent.main.PolymarketCLOB") as MockCLOB, \
         patch("polymarket_agent.agents.predictor.Predictor._llm_predict",
               return_value=(0.65, 0.95, "edge=15%")):
        MockCLOB.return_value.scan_markets.return_value = [m]
        result = run_live_cycle(_cfg(tmp_path), backend=backend, wallet=wallet)

    # No token id -> no order placed, no crash
    assert backend.place_order.call_count == 0
    assert result["placed"] == 0


def test_live_cycle_reconcile_drift_halts(tmp_path, monkeypatch):
    monkeypatch.setenv("LIVE_TRADING", "true")
    monkeypatch.delenv("EV_TRADER_HALT", raising=False)
    # Internal says 250, wallet says 100 -> drift -> halt
    (tmp_path / "bankroll.json").write_text(json.dumps({
        "cash_usdc": 250.0, "open_positions_value_usdc": 0.0, "daily_pnl_usdc": 0.0,
    }))
    (tmp_path / "open_bets.json").write_text(json.dumps([]))

    backend = MagicMock()
    backend.place_order.return_value = {"orderID": "X"}
    wallet = MagicMock()
    wallet.get_usdc_balance.return_value = Decimal("100")  # drift vs 250

    with patch("polymarket_agent.main.PolymarketCLOB") as MockCLOB, \
         patch("polymarket_agent.agents.predictor.Predictor._llm_predict",
               return_value=(0.5, 0.95, "flat")):  # edge 0 -> no order, isolate reconcile
        MockCLOB.return_value.scan_markets.return_value = [_market()]
        result = run_live_cycle(_cfg(tmp_path), backend=backend, wallet=wallet)

    assert result["halt"] is True
    assert (tmp_path / "HALT").exists()
