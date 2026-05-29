"""Tests for the shared intelligence layer (OSINT + cross-check + brain).
External engines (codex/gemini CLI, osint_api, Blinko) are mocked. The contract
is graceful degradation: missing engine/key never crashes, never blocks."""
from unittest.mock import patch, MagicMock
from polymarket_agent.intelligence import SharedIntelligence


def test_entities_extracted_skipping_generics():
    si = SharedIntelligence()
    ents = si._entities("Will Joe Biden beat Ron DeSantis in Iowa?")
    assert "Joe Biden" in ents or "Biden" in " ".join(ents)
    assert "Will" not in ents  # generic stop-word filtered


def test_osint_enrich_degrades_when_engine_absent(tmp_path):
    si = SharedIntelligence(enabled_osint=True)
    # No osint_api importable in test env -> degrade, still returns entities
    out = si.osint_enrich("Will Apple ship the Vision Pro 2?")
    assert "entities" in out
    assert out["osint"] is None  # engine unavailable -> degraded, not crashed


def test_osint_disabled_returns_entities_only():
    si = SharedIntelligence(enabled_osint=False)
    out = si.osint_enrich("Will Tesla hit 300?")
    assert out["osint"] is None


def test_cross_check_veto_when_reviewer_disagrees():
    si = SharedIntelligence(enabled_crosscheck=True)
    codex_no = {"available": True, "agree": False, "confidence": 0.8, "note": "overpriced"}
    gemini_yes = {"available": True, "agree": True, "confidence": 0.6, "note": "ok"}
    with patch.object(si, "_ask_cli", side_effect=[codex_no, gemini_yes]):
        v = si.cross_check("Q?", "YES", 0.65, 0.50, "edge")
    assert v["reviewed"] is True
    assert v["vetoed"] is True  # one reviewer that answered said no


def test_cross_check_no_veto_when_all_agree():
    si = SharedIntelligence(enabled_crosscheck=True)
    yes = {"available": True, "agree": True, "confidence": 0.7, "note": "ok"}
    with patch.object(si, "_ask_cli", side_effect=[yes, yes]):
        v = si.cross_check("Q?", "YES", 0.65, 0.50, "edge")
    assert v["reviewed"] is True
    assert v["vetoed"] is False


def test_cross_check_degrades_open_when_clis_absent():
    si = SharedIntelligence(enabled_crosscheck=True)
    unavail = {"available": False}
    with patch.object(si, "_ask_cli", side_effect=[unavail, unavail]):
        v = si.cross_check("Q?", "YES", 0.65, 0.50, "edge")
    assert v["reviewed"] is False
    assert v["vetoed"] is False  # no reviewer answered -> do not block (9 checks still gate)


def test_cross_check_disabled():
    si = SharedIntelligence(enabled_crosscheck=False)
    v = si.cross_check("Q?", "YES", 0.65, 0.50, "edge")
    assert v["reviewed"] is False and v["vetoed"] is False


def test_brain_query_degrades_to_empty_when_unreachable():
    si = SharedIntelligence(brain_endpoints=["http://127.0.0.1:59999"])
    with patch("urllib.request.urlopen", side_effect=OSError("refused")):
        assert si.brain_query("Fed rate cut") == ""


def test_brain_query_parses_notes():
    si = SharedIntelligence(brain_endpoints=["http://x"])
    fake = MagicMock()
    fake.read.return_value = b'[{"content":"Fed cut prior"},{"content":"rate history"}]'
    fake.__enter__ = lambda s: s
    fake.__exit__ = lambda *a: None
    with patch("urllib.request.urlopen", return_value=fake):
        out = si.brain_query("Fed")
    assert "Fed cut prior" in out
