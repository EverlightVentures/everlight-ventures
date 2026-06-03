"""Tests for paper settlement -- the link that makes calibration complete."""
import json
from pathlib import Path
from kalshi_agent.settle_paper import settle


def _seed(tmp_path, bets, cash=240.0):
    (tmp_path / "paper_open_bets.json").write_text(json.dumps(bets))
    (tmp_path / "paper_bankroll.json").write_text(json.dumps({"cash_usdc": cash}))


def _bet(mid, outcome="Yes", amt="10", price="0.5", prob=0.65):
    return {"id": f"paper_{mid}", "market_id": mid, "outcome": outcome,
            "amount_usdc": amt, "limit_price": price, "timestamp": "t",
            "status": "open", "pnl_usdc": "0.0", "predicted_prob": prob}


def test_won_bet_pays_out_and_records_calibration(tmp_path):
    _seed(tmp_path, [_bet("m1", outcome="Yes", amt="10", price="0.5", prob=0.7)])
    # Yes won
    res = settle(tmp_path, resolver=lambda mid: (True, "Yes"), now_ts=1000)
    assert res["resolved"] == 1 and res["still_open"] == 0
    closed = json.loads((tmp_path / "closed_bets.json").read_text())
    assert closed[0]["status"] == "won"
    # $10 at 0.5 -> 20 shares -> $20 payout -> pnl +10
    from decimal import Decimal
    assert Decimal(closed[0]["pnl_usdc"]) == Decimal("10")
    # bankroll credited the $20 payout: 240 + 20 = 260
    state = json.loads((tmp_path / "paper_bankroll.json").read_text())
    assert state["cash_usdc"] == 260.0
    led = (tmp_path / "calibration_ledger.jsonl").read_text().strip()
    row = json.loads(led)
    assert row["won"] is True and row["predicted_prob"] == 0.7


def test_lost_bet_records_loss(tmp_path):
    _seed(tmp_path, [_bet("m2", outcome="Yes", amt="10", price="0.5")])
    res = settle(tmp_path, resolver=lambda mid: (True, "No"), now_ts=1000)
    assert res["resolved"] == 1
    closed = json.loads((tmp_path / "closed_bets.json").read_text())
    assert closed[0]["status"] == "lost"
    assert closed[0]["pnl_usdc"] == "-10"
    # no payout -> bankroll unchanged
    assert json.loads((tmp_path / "paper_bankroll.json").read_text())["cash_usdc"] == 240.0


def test_unresolved_bet_stays_open(tmp_path):
    _seed(tmp_path, [_bet("m3")])
    res = settle(tmp_path, resolver=lambda mid: (False, None), now_ts=1000)
    assert res["resolved"] == 0 and res["still_open"] == 1
    assert json.loads((tmp_path / "paper_open_bets.json").read_text())  # still there


def test_void_market_refunds_stake(tmp_path):
    _seed(tmp_path, [_bet("m4", amt="10", price="0.5")])
    res = settle(tmp_path, resolver=lambda mid: (True, None), now_ts=1000)  # closed, no winner
    closed = json.loads((tmp_path / "closed_bets.json").read_text())
    assert closed[0]["status"] == "void"
    assert closed[0]["pnl_usdc"] == "0"
    # stake refunded: 240 + 10 = 250
    assert json.loads((tmp_path / "paper_bankroll.json").read_text())["cash_usdc"] == 250.0


def test_mixed_batch(tmp_path):
    _seed(tmp_path, [_bet("a", outcome="Yes"), _bet("b", outcome="Yes"), _bet("c")])
    def resolver(mid):
        return {"a": (True, "Yes"), "b": (True, "No"), "c": (False, None)}[mid]
    res = settle(tmp_path, resolver=resolver, now_ts=1000)
    assert res == {"checked": 3, "resolved": 2, "still_open": 1}
