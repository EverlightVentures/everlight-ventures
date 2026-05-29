"""Tests for the smart-money copy-trade signal (Polymarket trade feed mocked)."""
from unittest.mock import patch
from polymarket_agent.dataflows.smart_money import SmartMoney


def _trade(ts, side="BUY", size=100, price=0.5, title="Will X win?", outcome="Yes", name="Sharp"):
    return {"timestamp": ts, "side": side, "size": size, "price": price,
            "title": title, "outcome": outcome, "name": name, "eventSlug": "x"}


def test_emits_signal_for_recent_large_buy():
    sm = SmartMoney(wallets=["0xABC"], min_size_usd=100)
    trades = [_trade(ts=1000, size=300, price=0.5)]  # $150 buy
    with patch.object(sm, "_recent_trades", return_value=trades):
        sigs = sm.get_smart_money_signals(last_minutes=60, now_ts=1000)
    assert len(sigs) == 1
    assert sigs[0].source == "smart_money"
    assert "Will X win?" in sigs[0].text
    assert sigs[0].credibility == 0.9


def test_skips_old_trades():
    sm = SmartMoney(wallets=["0xABC"], min_size_usd=100)
    trades = [_trade(ts=1000 - 9999, size=300)]  # way past cutoff
    with patch.object(sm, "_recent_trades", return_value=trades):
        sigs = sm.get_smart_money_signals(last_minutes=60, now_ts=1000)
    assert sigs == []


def test_skips_small_trades():
    sm = SmartMoney(wallets=["0xABC"], min_size_usd=100)
    trades = [_trade(ts=1000, size=10, price=0.5)]  # $5 buy < $100
    with patch.object(sm, "_recent_trades", return_value=trades):
        sigs = sm.get_smart_money_signals(last_minutes=60, now_ts=1000)
    assert sigs == []


def test_skips_sells_only_fresh_entries():
    sm = SmartMoney(wallets=["0xABC"], min_size_usd=100)
    trades = [_trade(ts=1000, side="SELL", size=300)]
    with patch.object(sm, "_recent_trades", return_value=trades):
        sigs = sm.get_smart_money_signals(last_minutes=60, now_ts=1000)
    assert sigs == []


def test_no_wallets_returns_empty():
    sm = SmartMoney(wallets=[])
    assert sm.get_smart_money_signals(now_ts=1000) == []


def test_fetch_failure_degrades():
    sm = SmartMoney(wallets=["0xABC"])
    with patch.object(sm, "_recent_trades", side_effect=OSError("api down")):
        assert sm.get_smart_money_signals(now_ts=1000) == []
