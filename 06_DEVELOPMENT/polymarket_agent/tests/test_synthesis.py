"""Tests for the 360 decision-synthesis engine. All minds mocked. The contract:
multiple independent estimates -> median prob + agreement-weighted confidence;
disagreement LOWERS confidence; missing minds degrade, never crash."""
from unittest.mock import MagicMock
from polymarket_agent.synthesis import Decision360


def _brief(price=0.50):
    return {"question": "Will X happen?", "category": "Sports",
            "signals": [], "_market_price": price, "_outcome": "YES"}


def _engine(claude=None, perplexity=None, codex=None, gemini=None):
    predictor = MagicMock()
    predictor._llm_predict.return_value = claude or (0.5, 0.0, "x")
    intel = MagicMock()
    intel.brain_query.return_value = "prior"
    intel.osint_enrich.return_value = {"entities": [], "osint": None}
    # _ask_cli returns a note containing JSON for codex/gemini votes
    def ask(binary, prompt):
        v = codex if binary == "codex" else gemini
        if v is None:
            return {"available": False}
        return {"available": True, "confidence": v[1],
                "note": f'{{"predicted_prob": {v[0]}, "confidence": {v[1]}}}'}
    intel._ask_cli.side_effect = ask
    sonar = MagicMock()
    sonar.api_key = "k" if perplexity else None
    if perplexity:
        import json as _j
        sonar._call_sonar.return_value = _j.dumps(
            {"predicted_prob": perplexity[0], "confidence": perplexity[1]})
    d = Decision360(predictor=predictor, intel=intel, sonar=sonar, min_minds=1)
    return d


def test_consensus_when_minds_agree_high_confidence():
    # all four say ~0.70 -> tight spread -> high agreement -> high confidence
    d = _engine(claude=(0.70, 0.8, "c"), perplexity=(0.71, 0.8),
                codex=(0.69, 0.8), gemini=(0.70, 0.8))
    est = d.synthesize(_brief(price=0.50))
    assert est.n_minds == 4
    assert 0.69 <= est.predicted_prob <= 0.71
    assert est.agreement > 0.9              # tight
    assert est.confidence > 0.7             # high
    assert abs(est.edge - (est.predicted_prob - 0.50)) < 1e-9


def test_disagreement_lowers_confidence():
    # wide spread (0.30 vs 0.80) -> agreement ~0 -> confidence crushed
    d = _engine(claude=(0.30, 0.9, "c"), perplexity=(0.80, 0.9),
                codex=(0.35, 0.9), gemini=(0.78, 0.9))
    est = d.synthesize(_brief(price=0.50))
    assert est.n_minds == 4
    assert est.agreement < 0.2
    assert est.confidence < 0.2             # disagreement crushes confidence


def test_degrades_when_only_one_mind_answers():
    d = _engine(claude=(0.65, 0.7, "c"))  # others None
    est = d.synthesize(_brief(price=0.50))
    assert est.n_minds == 1
    assert est.predicted_prob == 0.65
    # single mind: confidence = its own (no agreement penalty applied)
    assert est.confidence == 0.7


def test_no_minds_answer_returns_zero_conf():
    predictor = MagicMock()
    predictor._llm_predict.return_value = (0.5, 0.0, "no key")  # conf 0 -> dropped
    intel = MagicMock()
    intel.brain_query.return_value = ""
    intel.osint_enrich.return_value = {}
    intel._ask_cli.return_value = {"available": False}
    sonar = MagicMock(); sonar.api_key = None
    d = Decision360(predictor=predictor, intel=intel, sonar=sonar, min_minds=1)
    est = d.synthesize(_brief())
    assert est.n_minds == 0
    assert est.confidence == 0.0
    assert est.edge == 0.0


def test_gathers_intel_provenance():
    d = _engine(claude=(0.6, 0.7, "c"))
    est = d.synthesize(_brief())
    assert "brain" in est.intel
    assert "osint" in est.intel
