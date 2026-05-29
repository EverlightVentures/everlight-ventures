from datetime import datetime, timezone, timedelta
from polymarket_agent.agents.scanner import Scanner
from polymarket_agent.dataflows.polymarket_clob import Market


def make_market(id, liq=10000, vol=2000, end_days=7, spread=0.02):
    end = (datetime.now(timezone.utc) + timedelta(days=end_days)).isoformat()
    return Market(
        id=id, question=f"Q{id}?", slug=f"q{id}", outcomes=["YES", "NO"],
        prices={"YES": 0.5, "NO": 0.5}, liquidity=liq, volume_24h=vol,
        end_date=end, category="Politics", spread=spread,
    )


def test_filters_by_liquidity():
    s = Scanner(min_liquidity=5000, min_volume_24h=1000, min_hours_to_resolution=4, max_spread=0.05)
    markets = [make_market("hi", liq=10000), make_market("lo", liq=100)]
    filtered = s.filter(markets)
    assert {m.id for m in filtered} == {"hi"}


def test_filters_by_volume():
    s = Scanner(min_liquidity=5000, min_volume_24h=1000, min_hours_to_resolution=4, max_spread=0.05)
    markets = [make_market("hi", vol=2000), make_market("lo", vol=100)]
    filtered = s.filter(markets)
    assert {m.id for m in filtered} == {"hi"}


def test_filters_by_time_to_resolution():
    s = Scanner(min_liquidity=5000, min_volume_24h=1000, min_hours_to_resolution=4, max_spread=0.05)
    end_soon = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    m_soon = Market(id="soon", question="?", slug="s", outcomes=["YES","NO"],
                    prices={"YES":0.5,"NO":0.5}, liquidity=10000, volume_24h=2000,
                    end_date=end_soon, category="", spread=0.02)
    m_ok = make_market("ok", end_days=2)
    filtered = s.filter([m_soon, m_ok])
    assert {m.id for m in filtered} == {"ok"}


def test_skips_subjective_resolution_markets():
    s = Scanner(min_liquidity=5000, min_volume_24h=1000, min_hours_to_resolution=4, max_spread=0.05)
    objective = make_market("obj")          # "Qobj?" -- objective
    novelty = make_market("nov"); novelty.category = "Pop Culture"
    joke = make_market("joke"); joke.question = "Will Jesus return before GTA VI?"
    filtered = s.filter([objective, novelty, joke])
    assert {m.id for m in filtered} == {"obj"}  # only the objective one survives


def test_skip_subjective_can_be_disabled():
    s = Scanner(min_liquidity=5000, min_volume_24h=1000, min_hours_to_resolution=4,
                max_spread=0.05, skip_subjective=False)
    novelty = make_market("nov"); novelty.category = "Pop Culture"
    assert any(m.id == "nov" for m in s.filter([novelty]))
