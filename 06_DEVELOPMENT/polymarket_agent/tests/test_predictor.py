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


def _brief(signals, price=0.50):
    return {"question": "Will Fed cut?", "category": "Econ",
            "signals": signals, "_market_price": price, "_outcome": "YES"}


def test_predict_skips_markets_with_no_signals():
    """No matched signals -> no information edge -> skip (no LLM call, no bet)."""
    p = Predictor(min_edge=0.05, min_confidence=0.4)
    briefs = {"mkt_1": _brief(signals=[])}
    with patch.object(p, "_llm_predict", return_value=(0.9, 0.9, "x")) as mock_llm:
        preds = p.predict(briefs, brain_policy={})
    assert preds == []
    assert mock_llm.call_count == 0  # never spent an LLM call


def test_predict_filters_low_edge():
    p = Predictor(min_edge=0.05, min_confidence=0.4)
    briefs = {"mkt_1": _brief(signals=[Signal(source="x", text="Fed cut likely")])}
    # Predicted 0.51 vs market 0.50 -> edge 0.01 < 0.05
    with patch.object(p, "_llm_predict", return_value=(0.51, 0.9, "r")):
        preds = p.predict(briefs, brain_policy={})
    assert preds == []


def test_predict_emits_when_edge_and_confidence_pass():
    p = Predictor(min_edge=0.05, min_confidence=0.4)
    briefs = {"mkt_1": _brief(signals=[Signal(source="x", text="Fed cut likely")])}
    # edge 0.65-0.5=0.15; raw conf 0.95 * default-brain 0.5 = 0.475 >= 0.4
    with patch.object(p, "_llm_predict", return_value=(0.65, 0.95, "strong signal")):
        preds = p.predict(briefs, brain_policy={})
    assert len(preds) == 1
    assert abs(preds[0].edge - 0.15) < 1e-6
    assert preds[0].outcome == "YES"


def test_llm_predict_no_key_degrades_to_market_price():
    """Safe default: no key -> (market_price, 0.0) -> edge 0 -> never bet blind."""
    p = Predictor(api_key="")  # explicit empty -> no key
    with patch("polymarket_agent.agents.predictor._load_anthropic_key", return_value=None):
        prob, conf, reason = p._llm_predict(_brief(signals=[], price=0.42))
    assert prob == 0.42
    assert conf == 0.0
    assert "no_key" in reason


def test_llm_predict_parses_real_claude_json(monkeypatch):
    """Mock the anthropic client; verify JSON parse + clamping."""
    p = Predictor(api_key="sk-test")

    class _Block:
        text = 'Here: {"predicted_prob": 1.5, "confidence": 0.8, "reasoning": "edge"}'

    class _Msg:
        content = [_Block()]

    class _Client:
        def __init__(self, api_key=None):
            self.messages = self

        def create(self, **kw):
            return _Msg()

    import sys, types
    fake = types.ModuleType("anthropic")
    fake.Anthropic = _Client
    monkeypatch.setitem(sys.modules, "anthropic", fake)

    prob, conf, reason = p._llm_predict(_brief(signals=[Signal(source="x", text="y")]))
    assert prob == 1.0  # clamped from 1.5
    assert conf == 0.8
    assert reason == "edge"
