import json
from decimal import Decimal
from pathlib import Path
from kalshi_agent.agents.risk_manager import RiskManager, Prediction


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


def test_convex_lane_takes_cheap_moonshot_on_relaxed_gate(tmp_path):
    """A 5c outcome (20x payout) with modest edge + modest confidence should be
    taken as a small lottery ticket even though it fails the CORE confidence gate."""
    import json
    from decimal import Decimal
    state = tmp_path / "bankroll.json"; state.write_text(json.dumps({"cash_usdc": 250.0, "daily_pnl_usdc": 0.0}))
    bets = tmp_path / "open_bets.json"; bets.write_text(json.dumps([]))
    rm = RiskManager(max_bet_pct=Decimal("5.0"), max_daily_loss_pct=Decimal("15"),
                     max_open_positions=10, min_edge=Decimal("0.05"), min_confidence=0.65,
                     convex_max_price=Decimal("0.20"), convex_min_edge=Decimal("0.03"),
                     convex_min_confidence=0.45, convex_budget_pct=Decimal("15"),
                     convex_stake_pct=Decimal("1.0"))
    # price 0.05 (20x), edge 0.04, confidence 0.50 -> fails core (0.65) but passes convex
    preds = [Prediction(market_id="moon", outcome="Yes", predicted_prob=0.09,
                        market_price=0.05, edge=0.04, confidence=0.50)]
    approved = rm.evaluate(preds, state_path=state, open_bets_path=bets)
    assert len(approved) == 1
    # convex stake = 1% of 250 = $2.50 (small lottery ticket)
    assert approved[0].amount_usdc == Decimal("2.50")


def test_convex_budget_caps_total_moonshot_exposure(tmp_path):
    import json
    from decimal import Decimal
    state = tmp_path / "bankroll.json"; state.write_text(json.dumps({"cash_usdc": 250.0, "daily_pnl_usdc": 0.0}))
    bets = tmp_path / "open_bets.json"; bets.write_text(json.dumps([]))
    # budget 15% of 250 = $37.50; stake $2.50 each -> max 15 convex bets
    rm = RiskManager(max_bet_pct=Decimal("5.0"), max_daily_loss_pct=Decimal("15"),
                     max_open_positions=100, min_edge=Decimal("0.05"), min_confidence=0.65,
                     convex_budget_pct=Decimal("4.0"), convex_stake_pct=Decimal("1.0"))  # budget $10 -> 4 bets
    preds = [Prediction(market_id=f"m{i}", outcome="Yes", predicted_prob=0.09,
                        market_price=0.05, edge=0.04, confidence=0.50) for i in range(10)]
    approved = rm.evaluate(preds, state_path=state, open_bets_path=bets)
    # $10 budget / $2.50 stake = 4 convex bets max
    assert len(approved) == 4
