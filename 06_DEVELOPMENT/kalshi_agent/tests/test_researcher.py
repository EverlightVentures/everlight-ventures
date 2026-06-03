from kalshi_agent.agents.researcher import Researcher
from kalshi_agent.dataflows.interface import Signal
from kalshi_agent.dataflows.polymarket_clob import Market


def make_market(id, question="?"):
    return Market(id=id, question=question, slug="s", outcomes=["YES","NO"],
                  prices={"YES":0.5,"NO":0.5}, liquidity=10000, volume_24h=1000,
                  end_date="2026-12-31", category="")


def test_aggregates_signals_per_market():
    r = Researcher()
    markets = [make_market("mkt_1", "Will Fed cut rates in June?")]
    signals = [
        Signal(source="rss", text="Fed signals dovish stance"),
        Signal(source="telegram", text="WatcherGuru: Fed cut imminent"),
        Signal(source="other", text="Unrelated headline"),
    ]
    briefs = r.aggregate(markets, signals)
    assert "mkt_1" in briefs
    # Naive keyword match -- "fed" appears in 2 signals -> 2 should be linked
    assert len(briefs["mkt_1"]["signals"]) == 2


def test_empty_signals_yields_empty_brief():
    r = Researcher()
    markets = [make_market("mkt_1")]
    briefs = r.aggregate(markets, signals=[])
    assert briefs["mkt_1"]["signals"] == []
