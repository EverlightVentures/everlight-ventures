import json
from decimal import Decimal
from pathlib import Path
from polymarket_agent.agents.risk_manager import RiskManager, Prediction


def test_quarter_kelly_sizing():
    # bankroll=$250, edge=10% (predicted 0.6, market 0.5), odds at 0.5 -> Kelly=20%
    # quarter-kelly = 5%, * $250 = $12.50, capped at max_bet (5% = $12.50). Result $12.50.
    rm = RiskManager(max_bet_pct=Decimal("5.0"), max_daily_loss_pct=Decimal("15.0"),
                     max_open_positions=10)
    sized = rm._quarter_kelly_size(bankroll=Decimal("250"), edge=0.10, odds=0.5)
    assert sized == Decimal("12.50")


def test_low_edge_gets_smaller_size():
    rm = RiskManager(max_bet_pct=Decimal("5.0"), max_daily_loss_pct=Decimal("15.0"),
                     max_open_positions=10)
    sized = rm._quarter_kelly_size(bankroll=Decimal("250"), edge=0.06, odds=0.5)
    # Kelly = 12%, quarter = 3%, *250 = $7.50. Below cap.
    assert sized == Decimal("7.50")


def test_evaluate_drops_predictions_under_min_edge(tmp_path: Path):
    state_path = tmp_path / "bankroll.json"
    state_path.write_text(json.dumps({"cash_usdc": 250.0, "daily_pnl_usdc": 0.0}))
    bets_path = tmp_path / "open_bets.json"
    bets_path.write_text(json.dumps([]))

    rm = RiskManager(max_bet_pct=Decimal("5.0"), max_daily_loss_pct=Decimal("15.0"),
                     max_open_positions=10, min_edge=Decimal("0.05"))
    preds = [
        Prediction(market_id="mkt_1", outcome="YES", predicted_prob=0.6,
                   market_price=0.5, edge=0.10, confidence=0.7),
        Prediction(market_id="mkt_2", outcome="YES", predicted_prob=0.52,
                   market_price=0.5, edge=0.02, confidence=0.7),
    ]
    approved = rm.evaluate(preds, state_path=state_path, open_bets_path=bets_path)
    assert {b.market_id for b in approved} == {"mkt_1"}


def test_evaluate_stops_at_daily_loss(tmp_path: Path):
    state_path = tmp_path / "bankroll.json"
    state_path.write_text(json.dumps({"cash_usdc": 250.0, "daily_pnl_usdc": -50.0}))
    bets_path = tmp_path / "open_bets.json"
    bets_path.write_text(json.dumps([]))

    rm = RiskManager(max_bet_pct=Decimal("5.0"), max_daily_loss_pct=Decimal("15.0"),
                     max_open_positions=10, min_edge=Decimal("0.05"))
    preds = [Prediction(market_id="mkt_1", outcome="YES", predicted_prob=0.6,
                        market_price=0.5, edge=0.10, confidence=0.7)]
    approved = rm.evaluate(preds, state_path=state_path, open_bets_path=bets_path)
    assert approved == []
