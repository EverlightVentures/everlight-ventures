import pytest
from dataclasses import asdict
from polymarket_agent.dataflows.interface import Signal


def test_signal_basic_construction():
    s = Signal(source="rss", text="Fed raised rates 25bp", url="https://reuters.com/x")
    assert s.source == "rss"
    assert s.text == "Fed raised rates 25bp"
    assert s.credibility == 0.5
    assert s.sentiment == 0.0
    assert s.market_ids == []


def test_signal_serializable():
    s = Signal(source="telegram", text="X", market_ids=["mkt_1", "mkt_2"])
    d = asdict(s)
    assert d["market_ids"] == ["mkt_1", "mkt_2"]


def test_signal_market_ids_independent():
    a = Signal(source="x", text="x")
    b = Signal(source="x", text="x")
    a.market_ids.append("mkt_1")
    assert b.market_ids == [], "mutable-default leak between Signals"
