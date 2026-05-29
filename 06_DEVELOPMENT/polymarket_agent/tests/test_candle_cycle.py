"""Test the 5-min candle lane: places a bounded bet on a strong late move, then
settles it by price-feed outcome. crypto_candle network calls are mocked."""
import json
from unittest.mock import patch
from pathlib import Path
from polymarket_agent.main import run_candle_cycle


def _cfg(tmp_path):
    return {"bankroll": {"initial": 250.0}, "data_dir": str(tmp_path),
            "crypto_candle": {"enabled": True, "assets": ["BTC"], "stake_usd": 2.0,
                              "min_edge": 0.05, "enter_after_min": 3.0}}


def test_candle_cycle_places_bet_on_actionable_decision(tmp_path):
    decision = {"asset": "BTC", "market_id": "TOKEN_UP", "outcome": "Up",
                "market_price": 0.50, "predicted_prob": 0.74, "edge": 0.24,
                "strength": 0.6, "slug": "btc-updown-5m-1780000000", "question": "BTC Up?"}
    with patch("polymarket_agent.dataflows.crypto_candle.candle_decision", return_value=decision), \
         patch("polymarket_agent.dataflows.crypto_candle.window_outcome", return_value=None):
        res = run_candle_cycle(_cfg(tmp_path))
    assert res["placed"] == 1
    openb = json.loads((tmp_path / "candle_open_bets.json").read_text())
    assert openb[0]["outcome"] == "Up" and openb[0]["amount_usdc"] == "2.0"


def test_candle_cycle_settles_won_bet_by_price(tmp_path):
    # pre-seed an open candle bet, then settle it as a WIN (price says Up)
    (tmp_path / "candle_open_bets.json").write_text(json.dumps([{
        "id": "candle_x", "asset": "BTC", "window_ts": 1780000000, "outcome": "Up",
        "amount_usdc": "2.0", "price": "0.5", "predicted_prob": 0.74, "edge": 0.24, "ts": 1}]))
    (tmp_path / "paper_bankroll.json").write_text(json.dumps({"cash_usdc": 250.0}))
    with patch("polymarket_agent.dataflows.crypto_candle.candle_decision", return_value=None), \
         patch("polymarket_agent.dataflows.crypto_candle.window_outcome", return_value="Up"):
        res = run_candle_cycle(_cfg(tmp_path))
    assert res["closed"] == 1
    closed = json.loads((tmp_path / "candle_closed_bets.json").read_text())
    assert closed[0]["status"] == "won"
    # $2 at 0.5 -> 4 shares -> $4 payout -> pnl +2
    from decimal import Decimal
    assert Decimal(closed[0]["pnl_usdc"]) == Decimal("2.0")


def test_candle_cycle_skips_when_no_decision(tmp_path):
    with patch("polymarket_agent.dataflows.crypto_candle.candle_decision",
               return_value={"skip": "doji"}), \
         patch("polymarket_agent.dataflows.crypto_candle.window_outcome", return_value=None):
        res = run_candle_cycle(_cfg(tmp_path))
    assert res["placed"] == 0
