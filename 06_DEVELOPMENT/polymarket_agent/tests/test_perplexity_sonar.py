from unittest.mock import patch
from polymarket_agent.dataflows.perplexity_sonar import Sonar


def test_get_news_velocity_returns_signals_with_sonar_source():
    fake_brief = {
        "headlines": [
            {"text": "Fed cut rates", "url": "https://reuters.com/a", "sentiment": 0.8},
            {"text": "Sports league announces strike", "url": "https://espn.com/b", "sentiment": -0.5},
        ],
    }
    with patch("polymarket_agent.dataflows.perplexity_sonar.get_brief",
               return_value=fake_brief):
        sonar = Sonar(api_key="dummy")
        signals = sonar.get_news_velocity(category="politics", last_minutes=10)

    assert len(signals) == 2
    assert all(s.source == "perplexity_sonar" for s in signals)
    assert signals[0].sentiment == 0.8
