from polymarket_agent.agents.postmortem import Postmortem


def test_brier_score_perfect_calibration():
    pm = Postmortem()
    closed = [
        {"predicted_prob": 1.0, "outcome_resolved": "YES", "bet_outcome": "YES"},
        {"predicted_prob": 0.0, "outcome_resolved": "NO", "bet_outcome": "YES"},
    ]
    score = pm.brier_score(closed)
    assert score == 0.0


def test_brier_score_worst_case():
    pm = Postmortem()
    closed = [{"predicted_prob": 0.0, "outcome_resolved": "YES", "bet_outcome": "YES"}]
    score = pm.brier_score(closed)
    assert score == 1.0


def test_win_rate():
    pm = Postmortem()
    closed = [
        {"pnl_usdc": "5.0"},
        {"pnl_usdc": "-3.0"},
        {"pnl_usdc": "10.0"},
        {"pnl_usdc": "-2.0"},
    ]
    assert pm.win_rate(closed) == 0.5
