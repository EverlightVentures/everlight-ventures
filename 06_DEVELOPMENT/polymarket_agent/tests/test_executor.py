import json
import os
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock
import pytest
from polymarket_agent.execution.exceptions import (
    LiveTradingDisabledError, KillSwitchActiveError, UnauthorizedInstrumentError,
    DollarCapExceededError, OnChainBalanceShortfallError, OrderRejectedByVenueError,
)
from polymarket_agent.execution.executor_polymarket import PolymarketExecutor, BetRequest


def make_executor(tmp_path, **overrides):
    state_path = tmp_path / "bankroll.json"
    state_path.write_text(json.dumps({
        "cash_usdc": 250.0,
        "open_positions_value_usdc": 0.0,
        "daily_pnl_usdc": 0.0,
    }))
    halt_path = tmp_path / "HALT"
    open_bets_path = tmp_path / "open_bets.json"
    open_bets_path.write_text(json.dumps([]))

    wallet = MagicMock()
    wallet.get_usdc_balance.return_value = Decimal("250")
    wallet.sign_clob_order.return_value = "0xfake"

    clob = MagicMock()
    clob.submit_order.return_value = "bet_id_1"

    cfg = {
        "live_trading_enabled": True,
        "max_bet_pct": 5.0,
        "max_open_positions": 10,
        "max_daily_loss_pct": 15.0,
        "active_whitelist": {"mkt_1"},
    }
    cfg.update(overrides)

    return PolymarketExecutor(
        wallet=wallet, clob=clob, config=cfg,
        bankroll_state_path=state_path, halt_path=halt_path,
        open_bets_path=open_bets_path,
    ), wallet, clob


def make_req():
    return BetRequest(market_id="mkt_1", outcome="YES", amount_usdc=Decimal("10"), limit_price=Decimal("0.5"))


def test_check_1_live_trading_disabled(tmp_path, monkeypatch):
    monkeypatch.delenv("LIVE_TRADING", raising=False)
    ex, _, _ = make_executor(tmp_path, live_trading_enabled=False)
    with pytest.raises(LiveTradingDisabledError):
        ex.submit_order(make_req())


def test_check_1_requires_env_var_too(tmp_path, monkeypatch):
    monkeypatch.delenv("LIVE_TRADING", raising=False)
    ex, _, _ = make_executor(tmp_path)
    with pytest.raises(LiveTradingDisabledError):
        ex.submit_order(make_req())


def test_check_2_halt_flag_exists(tmp_path, monkeypatch):
    monkeypatch.setenv("LIVE_TRADING", "true")
    ex, _, _ = make_executor(tmp_path)
    (tmp_path / "HALT").write_text("{}")
    with pytest.raises(KillSwitchActiveError):
        ex.submit_order(make_req())


def test_check_3_env_kill_switch(tmp_path, monkeypatch):
    monkeypatch.setenv("LIVE_TRADING", "true")
    monkeypatch.setenv("EV_TRADER_HALT", "true")
    ex, _, _ = make_executor(tmp_path)
    with pytest.raises(KillSwitchActiveError):
        ex.submit_order(make_req())


def test_check_4_market_not_whitelisted(tmp_path, monkeypatch):
    monkeypatch.setenv("LIVE_TRADING", "true")
    monkeypatch.delenv("EV_TRADER_HALT", raising=False)
    ex, _, _ = make_executor(tmp_path, active_whitelist={"other_mkt"})
    with pytest.raises(UnauthorizedInstrumentError):
        ex.submit_order(make_req())


def test_check_5_exceeds_max_bet_pct(tmp_path, monkeypatch):
    monkeypatch.setenv("LIVE_TRADING", "true")
    monkeypatch.delenv("EV_TRADER_HALT", raising=False)
    ex, _, _ = make_executor(tmp_path)
    big = BetRequest(market_id="mkt_1", outcome="YES",
                     amount_usdc=Decimal("100"), limit_price=Decimal("0.5"))
    with pytest.raises(DollarCapExceededError):
        ex.submit_order(big)


def test_check_8_on_chain_balance_short(tmp_path, monkeypatch):
    monkeypatch.setenv("LIVE_TRADING", "true")
    monkeypatch.delenv("EV_TRADER_HALT", raising=False)
    ex, wallet, _ = make_executor(tmp_path)
    wallet.get_usdc_balance.return_value = Decimal("5")
    with pytest.raises(OnChainBalanceShortfallError):
        ex.submit_order(make_req())


def test_happy_path_submits_signs_updates_ledger(tmp_path, monkeypatch):
    monkeypatch.setenv("LIVE_TRADING", "true")
    monkeypatch.delenv("EV_TRADER_HALT", raising=False)
    ex, wallet, clob = make_executor(tmp_path)
    bet = ex.submit_order(make_req())
    assert bet.id == "bet_id_1"
    assert wallet.sign_clob_order.call_count == 1
    assert clob.submit_order.call_count == 1
    open_bets = json.loads((tmp_path / "open_bets.json").read_text())
    assert len(open_bets) == 1
