"""Tests for the REAL Perplexity Sonar dataflow. The HTTP call is mocked here;
verify_live / a live smoke hits the real API. Proves: parse, TTL cache,
graceful-degrade, sentiment clamping."""
from unittest.mock import patch
from polymarket_agent.dataflows.perplexity_sonar import Sonar


def _sonar(tmp_path, **kw):
    return Sonar(api_key="dummy", cache_path=tmp_path / "sonar_cache.json", **kw)


def test_parses_json_array_into_signals(tmp_path):
    s = _sonar(tmp_path)
    raw = ('[{"text":"Fed signals cut","url":"https://r/1","sentiment":0.8},'
           '{"text":"Strike announced","url":"https://espn/2","sentiment":-0.4}]')
    with patch.object(s, "_call_sonar", return_value=raw):
        out = s.get_news_velocity(category="politics", last_minutes=10, now_ts=1000)
    assert len(out) == 2
    assert all(x.source == "perplexity_sonar" for x in out)
    assert out[0].sentiment == 0.8
    assert out[0].url == "https://r/1"


def test_strips_prose_and_fences_around_json(tmp_path):
    s = _sonar(tmp_path)
    raw = 'Here you go:\n```json\n[{"text":"X","url":"u","sentiment":0.1}]\n```\nDone.'
    with patch.object(s, "_call_sonar", return_value=raw):
        out = s.get_news_velocity("crypto", now_ts=1000)
    assert len(out) == 1
    assert out[0].text == "X"


def test_sentiment_clamped(tmp_path):
    s = _sonar(tmp_path)
    raw = '[{"text":"a","url":"","sentiment":5},{"text":"b","url":"","sentiment":-9}]'
    with patch.object(s, "_call_sonar", return_value=raw):
        out = s.get_news_velocity("x", now_ts=1000)
    assert out[0].sentiment == 1.0
    assert out[1].sentiment == -1.0


def test_cache_hit_avoids_second_call(tmp_path):
    s = _sonar(tmp_path, cache_ttl=600)
    raw = '[{"text":"once","url":"u","sentiment":0}]'
    with patch.object(s, "_call_sonar", return_value=raw) as mock_call:
        s.get_news_velocity("politics", now_ts=1000)
        s.get_news_velocity("politics", now_ts=1300)  # within TTL
    assert mock_call.call_count == 1


def test_cache_expires_after_ttl(tmp_path):
    s = _sonar(tmp_path, cache_ttl=600)
    raw = '[{"text":"x","url":"u","sentiment":0}]'
    with patch.object(s, "_call_sonar", return_value=raw) as mock_call:
        s.get_news_velocity("politics", now_ts=1000)
        s.get_news_velocity("politics", now_ts=2000)  # past TTL
    assert mock_call.call_count == 2


def test_no_key_returns_empty(tmp_path):
    s = Sonar(api_key="", cache_path=tmp_path / "c.json")
    out = s.get_news_velocity("x", now_ts=1000)
    assert out == []


def test_api_failure_degrades_to_empty(tmp_path):
    s = _sonar(tmp_path)
    with patch.object(s, "_call_sonar", side_effect=RuntimeError("502")):
        out = s.get_news_velocity("x", now_ts=1000)
    assert out == []


def test_malformed_json_returns_empty(tmp_path):
    s = _sonar(tmp_path)
    with patch.object(s, "_call_sonar", return_value="not json at all"):
        out = s.get_news_velocity("x", now_ts=1000)
    assert out == []
