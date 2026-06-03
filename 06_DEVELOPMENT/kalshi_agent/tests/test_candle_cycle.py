"""Test the 5-min candle lane: places a bounded bet on a strong late move, then
settles it by price-feed outcome. crypto_candle network calls are mocked."""
import json
from unittest.mock import patch
from pathlib import Path
from kalshi_agent.main import run_candle_cycle


def _cfg(tmp_path):
    return {"bankroll": {"initial": 250.0}, "data_dir": str(tmp_path),
            "crypto_candle": {"enabled": True, "assets": ["BTC"], "stake_usd": 2.0,
                              "min_edge": 0.05, "enter_after_min": 3.0}}


def test_candle_cycle_places_bet_on_actionable_decision(tmp_path):
    decision = {"asset": "BTC", "market_id": "TOKEN_UP", "outcome": "Up",
                "market_price": 0.30, "predicted_prob": 0.74, "edge": 0.44,
                "strength": 0.6, "slug": "btc-updown-5m-1780000000",
                "window_ts": 1780000000, "question": "BTC Up?", "bet": True}
    with patch("kalshi_agent.dataflows.crypto_candle.candle_decision", return_value=decision), \
         patch("kalshi_agent.dataflows.crypto_candle.window_outcome", return_value=None):
        res = run_candle_cycle(_cfg(tmp_path))
    assert res["placed"] == 1 and res["shadow"] == 0
    openb = json.loads((tmp_path / "candle_open_bets.json").read_text())
    assert openb[0]["outcome"] == "Up" and openb[0]["amount_usdc"] == "2.0"


def test_candle_cycle_records_shadow_when_cost_gate_skips(tmp_path):
    # A formed directional prediction the cost gate refuses to bet (coin-flip ~0.50)
    # must still be recorded as a SHADOW prediction so calibration accrues.
    decision = {"asset": "BTC", "market_id": "TOKEN_UP", "outcome": "Up",
                "market_price": 0.52, "predicted_prob": 0.58, "edge": 0.06,
                "strength": 0.2, "slug": "btc-updown-5m-1780000000",
                "window_ts": 1780000000, "question": "BTC Up?",
                "bet": False, "skip_reason": "win payout < 2x stake + 2x gas"}
    with patch("kalshi_agent.dataflows.crypto_candle.candle_decision", return_value=decision), \
         patch("kalshi_agent.dataflows.crypto_candle.window_outcome", return_value=None):
        res = run_candle_cycle(_cfg(tmp_path))
    assert res["placed"] == 0 and res["shadow"] == 1
    shadow = json.loads((tmp_path / "candle_shadow_open.json").read_text())
    assert shadow[0]["outcome"] == "Up" and shadow[0]["predicted_prob"] == 0.58


def test_candle_cycle_settles_shadow_into_calibration_ledger(tmp_path):
    # pre-seed an open shadow prediction; settle it -> a calibration_ledger row, no money
    (tmp_path / "candle_shadow_open.json").write_text(json.dumps([{
        "id": "shadow_x", "asset": "BTC", "window_ts": 1780000000, "outcome": "Up",
        "price": "0.52", "predicted_prob": 0.58, "edge": 0.06, "ts": 1}]))
    with patch("kalshi_agent.dataflows.crypto_candle.candle_decision", return_value=None), \
         patch("kalshi_agent.dataflows.crypto_candle.window_outcome", return_value="Down"):
        res = run_candle_cycle(_cfg(tmp_path))
    assert res["settled_shadow"] == 1 and res["shadow_open"] == 0
    rows = [json.loads(l) for l in (tmp_path / "calibration_ledger.jsonl").read_text().splitlines()]
    assert rows[0]["lane"] == "candle_shadow" and rows[0]["won"] is False
    assert rows[0]["pnl_usdc"] == "0"  # shadow never touches money


def test_candle_cycle_settles_won_bet_by_price(tmp_path):
    # pre-seed an open candle bet, then settle it as a WIN (price says Up)
    (tmp_path / "candle_open_bets.json").write_text(json.dumps([{
        "id": "candle_x", "asset": "BTC", "window_ts": 1780000000, "outcome": "Up",
        "amount_usdc": "2.0", "price": "0.5", "predicted_prob": 0.74, "edge": 0.24, "ts": 1}]))
    (tmp_path / "paper_bankroll.json").write_text(json.dumps({"cash_usdc": 250.0}))
    with patch("kalshi_agent.dataflows.crypto_candle.candle_decision", return_value=None), \
         patch("kalshi_agent.dataflows.crypto_candle.window_outcome", return_value="Up"):
        res = run_candle_cycle(_cfg(tmp_path))
    assert res["closed"] == 1
    closed = json.loads((tmp_path / "candle_closed_bets.json").read_text())
    assert closed[0]["status"] == "won"
    # $2 at 0.5 -> 4 shares -> $4 payout -> pnl +2
    from decimal import Decimal
    assert Decimal(closed[0]["pnl_usdc"]) == Decimal("2.0")


def test_candle_cycle_skips_when_no_decision(tmp_path):
    # None == no directional claim (doji / too early) -> no bet AND no shadow
    with patch("kalshi_agent.dataflows.crypto_candle.candle_decision", return_value=None), \
         patch("kalshi_agent.dataflows.crypto_candle.window_outcome", return_value=None):
        res = run_candle_cycle(_cfg(tmp_path))
    assert res["placed"] == 0 and res["shadow"] == 0
