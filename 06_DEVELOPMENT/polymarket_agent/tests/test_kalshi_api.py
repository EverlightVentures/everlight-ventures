"""Kalshi data-layer mapping tests (no network -- pure parse/price logic)."""
from polymarket_agent.dataflows.kalshi_api import KalshiMarket


def test_from_api_maps_fields():
    m = KalshiMarket.from_api({
        "ticker": "KXBTC-26JUN0317-T79249.99", "title": "Bitcoin price range?",
        "status": "open", "yes_bid": 42, "yes_ask": 46, "no_bid": 54, "no_ask": 58,
        "volume": 1200, "close_time": "2026-06-03T17:00:00Z"})
    assert m.ticker.startswith("KXBTC") and m.status == "open" and m.volume == 1200


def test_prob_is_cents_midpoint_as_0_1():
    m = KalshiMarket.from_api({"yes_bid": 42, "yes_ask": 46, "no_bid": 54, "no_ask": 58})
    assert m.prob("yes") == (42 + 46) / 200.0          # 0.44
    assert m.prob("no") == (54 + 58) / 200.0           # 0.56


def test_prob_none_when_one_sided():
    # illiquid strike bucket (no resting orders) -> no tradeable probability
    m = KalshiMarket.from_api({"yes_bid": None, "yes_ask": None})
    assert m.prob("yes") is None
