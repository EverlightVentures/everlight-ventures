from unittest.mock import patch
from polymarket_agent.agents.predictor import Predictor
from polymarket_agent.dataflows.interface import Signal


def test_brain_bridge_multiplies_confidence():
    p = Predictor(min_edge=0.05)
    raw_conf = 0.8
    brain_policy = {"decisive_score": 0.8, "logical_score": 0.7,
                    "self_healing_score": 0.5, "plasticity_score": 0.6}
    adjusted = p._brain_adjust(raw_conf, brain_policy)
    # weights: 0.3, 0.3, 0.2, 0.2 -> 0.8*0.3 + 0.7*0.3 + 0.5*0.2 + 0.6*0.2
    # = 0.24 + 0.21 + 0.10 + 0.12 = 0.67; raw 0.8 * 0.67 = 0.536
    assert 0.53 <= adjusted <= 0.54


def test_predict_filters_low_edge():
    p = Predictor(min_edge=0.05)
    # Predicted 0.51, market 0.50 -> edge 0.01 below threshold
    briefs = {
        "mkt_1": {"question": "?", "category": "", "signals": [],
                  "_market_price": 0.50, "_outcome": "YES"},
    }
    with patch.object(p, "_llm_predict", return_value=(0.51, 0.8, "reasoning")):
        preds = p.predict(briefs, brain_policy={})
    assert preds == []
