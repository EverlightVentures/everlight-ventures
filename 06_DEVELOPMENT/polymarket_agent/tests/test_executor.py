import json
import os
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock
import pytest
from polymarket_agent.execution.exceptions import (
    LiveTradingDisabledError, KillSwitchActiveError, UnauthorizedInstrumentError,
    DollarCapExceededError, OnChainBalanceShortfallError, OrderRejectedByVenueError,
    PolymarketExecutorError,
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
    ex.wallet.address = "0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266"
    bet = ex.submit_order(make_req())
    assert bet.id == "bet_id_1"
    assert wallet.sign_clob_order.call_count == 1
    assert clob.submit_order.call_count == 1
    open_bets = json.loads((tmp_path / "open_bets.json").read_text())
    assert len(open_bets) == 1


def test_check_6_open_positions_cap(tmp_path, monkeypatch):
    monkeypatch.setenv("LIVE_TRADING", "true")
    monkeypatch.delenv("EV_TRADER_HALT", raising=False)
    ex, _, _ = make_executor(tmp_path, max_open_positions=2)
    # Pre-populate 2 open bets
    (tmp_path / "open_bets.json").write_text(json.dumps([{"id": "a"}, {"id": "b"}]))
    with pytest.raises(DollarCapExceededError):
        ex.submit_order(make_req())


def test_check_7_daily_loss_exceeded(tmp_path, monkeypatch):
    monkeypatch.setenv("LIVE_TRADING", "true")
    monkeypatch.delenv("EV_TRADER_HALT", raising=False)
    state_path = tmp_path / "bankroll.json"
    state_path.write_text(json.dumps({
        "cash_usdc": 250.0, "open_positions_value_usdc": 0.0,
        "daily_pnl_usdc": -50.0,  # exceeds -15% of 250 = -37.5
    }))
    halt_path = tmp_path / "HALT"
    open_bets_path = tmp_path / "open_bets.json"
    open_bets_path.write_text(json.dumps([]))
    wallet = MagicMock(); wallet.get_usdc_balance.return_value = Decimal("250")
    clob = MagicMock()
    cfg = {"live_trading_enabled": True, "max_bet_pct": 5.0,
           "max_open_positions": 10, "max_daily_loss_pct": 15.0,
           "active_whitelist": {"mkt_1"}}
    ex = PolymarketExecutor(wallet=wallet, clob=clob, config=cfg,
                            bankroll_state_path=state_path, halt_path=halt_path,
                            open_bets_path=open_bets_path)
    with pytest.raises(KillSwitchActiveError):
        ex.submit_order(make_req())


def test_check_9_clob_rejection_wrapped(tmp_path, monkeypatch):
    monkeypatch.setenv("LIVE_TRADING", "true")
    monkeypatch.delenv("EV_TRADER_HALT", raising=False)
    ex, wallet, clob = make_executor(tmp_path)
    ex.wallet.address = "0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266"
    clob.submit_order.side_effect = RuntimeError("network down")
    with pytest.raises(OrderRejectedByVenueError):
        ex.submit_order(make_req())


def test_eip712_builder_returns_valid_typed_data(tmp_path, monkeypatch):
    """EIP-712 builder produces a dict that satisfies wallet.sign_clob_order contract."""
    monkeypatch.setenv("LIVE_TRADING", "true")
    monkeypatch.delenv("EV_TRADER_HALT", raising=False)
    ex, _, _ = make_executor(tmp_path)
    # wallet.address needs to exist on the mock
    ex.wallet.address = "0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266"
    req = BetRequest(market_id="123456", outcome="YES",
                     amount_usdc=Decimal("10"), limit_price=Decimal("0.5"))
    typed_data = ex._build_eip712(req)

    # Required keys per wallet.sign_clob_order
    assert {"types", "primaryType", "domain", "message"} <= typed_data.keys()
    # Domain chainId must be 137
    assert typed_data["domain"]["chainId"] == 137
    assert typed_data["domain"]["name"] == "Polymarket CTF Exchange"
    # Order envelope structure
    assert typed_data["primaryType"] == "Order"
    msg = typed_data["message"]
    assert msg["maker"] == "0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266"
    assert msg["signer"] == msg["maker"]
    assert msg["taker"] == "0x0000000000000000000000000000000000000000"
    # makerAmount = 10 USDC * 1e6 = 10_000_000
    assert msg["makerAmount"] == 10_000_000
    # takerAmount = (10 / 0.5) * 1e6 = 20_000_000
    assert msg["takerAmount"] == 20_000_000
    assert msg["side"] == 0
    assert msg["signatureType"] == 0


def test_eip712_rejects_zero_limit_price(tmp_path, monkeypatch):
    monkeypatch.setenv("LIVE_TRADING", "true")
    monkeypatch.delenv("EV_TRADER_HALT", raising=False)
    ex, _, _ = make_executor(tmp_path)
    ex.wallet.address = "0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266"
    req = BetRequest(market_id="123456", outcome="YES",
                     amount_usdc=Decimal("10"), limit_price=Decimal("0"))
    from polymarket_agent.execution.exceptions import PolymarketExecutorError
    with pytest.raises(PolymarketExecutorError):
        ex._build_eip712(req)


def test_amount_must_be_decimal_not_float(tmp_path, monkeypatch):
    monkeypatch.setenv("LIVE_TRADING", "true")
    monkeypatch.delenv("EV_TRADER_HALT", raising=False)
    ex, _, _ = make_executor(tmp_path)
    bad = BetRequest(market_id="mkt_1", outcome="YES",
                     amount_usdc=10.0,  # float, not Decimal
                     limit_price=Decimal("0.5"))
    with pytest.raises(PolymarketExecutorError):
        ex.submit_order(bad)


def test_atomic_ledger_write_uses_temp_then_rename(tmp_path, monkeypatch):
    """Verify the ledger write goes through a temp file (no partial corruption)."""
    monkeypatch.setenv("LIVE_TRADING", "true")
    monkeypatch.delenv("EV_TRADER_HALT", raising=False)
    ex, _, _ = make_executor(tmp_path)
    ex.wallet.address = "0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266"
    bet = ex.submit_order(make_req())
    # Final file present, no .tmp leftover
    assert (tmp_path / "open_bets.json").exists()
    assert not (tmp_path / "open_bets.json.tmp").exists()


def test_missing_whitelist_config_key_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("LIVE_TRADING", "true")
    monkeypatch.delenv("EV_TRADER_HALT", raising=False)
    state_path = tmp_path / "bankroll.json"
    state_path.write_text(json.dumps({"cash_usdc": 250.0, "daily_pnl_usdc": 0.0}))
    halt_path = tmp_path / "HALT"
    open_bets_path = tmp_path / "open_bets.json"
    open_bets_path.write_text(json.dumps([]))
    wallet = MagicMock(); wallet.get_usdc_balance.return_value = Decimal("250")
    clob = MagicMock()
    cfg = {"live_trading_enabled": True, "max_bet_pct": 5.0,
           "max_open_positions": 10, "max_daily_loss_pct": 15.0}
           # no active_whitelist
    ex = PolymarketExecutor(wallet=wallet, clob=clob, config=cfg,
                            bankroll_state_path=state_path, halt_path=halt_path,
                            open_bets_path=open_bets_path)
    with pytest.raises(PolymarketExecutorError):
        ex.submit_order(make_req())
