import json
from unittest.mock import patch, MagicMock
import pytest
from polymarket_agent.dataflows.polymarket_clob import PolymarketCLOB, Market


def test_scan_markets_uses_proxy_url():
    clob = PolymarketCLOB(proxy_url="https://clob-proxy.example.com")
    fake_resp = MagicMock()
    fake_resp.read.return_value = json.dumps([
        {
            "id": "mkt_1", "question": "Q1?", "slug": "q1",
            "outcomes": ["YES", "NO"], "outcomePrices": ["0.6", "0.4"],
            "liquidity": "10000", "volume24hr": "5000",
            "endDate": "2026-12-31T00:00:00Z", "category": "Politics",
        },
    ]).encode()
    fake_resp.__enter__ = lambda s: s
    fake_resp.__exit__ = lambda *a: None

    with patch("urllib.request.urlopen", return_value=fake_resp) as mock_url:
        markets = clob.scan_markets(limit=10)

    assert len(markets) == 1
    assert markets[0].id == "mkt_1"
    assert markets[0].prices == {"YES": 0.6, "NO": 0.4}
    assert markets[0].liquidity == 10000.0
    # Verify proxy URL was used
    called_url = mock_url.call_args[0][0].full_url
    assert called_url.startswith("https://clob-proxy.example.com/gamma/")


def test_scan_markets_direct_mode_and_string_encoded_arrays():
    """Direct mode (no proxy) hits gamma host; live gamma encodes arrays as
    JSON strings -- parser must handle that + capture clobTokenIds."""
    clob = PolymarketCLOB()  # direct
    fake_resp = MagicMock()
    fake_resp.read.return_value = json.dumps([
        {
            "id": 12345, "question": "Q?", "slug": "q",
            "outcomes": "[\"Yes\", \"No\"]",
            "outcomePrices": "[\"0.51\", \"0.49\"]",
            "clobTokenIds": "[\"98022490269692\", \"53831553061883\"]",
            "liquidity": "10000", "volume24hr": "5000",
            "endDate": "2026-12-31T00:00:00Z", "category": "Politics",
        },
    ]).encode()
    fake_resp.__enter__ = lambda s: s
    fake_resp.__exit__ = lambda *a: None

    with patch("urllib.request.urlopen", return_value=fake_resp) as mock_url:
        markets = clob.scan_markets(limit=10)

    assert len(markets) == 1
    m = markets[0]
    assert m.id == "12345"
    assert m.outcomes == ["Yes", "No"]
    assert m.prices == {"Yes": 0.51, "No": 0.49}
    assert m.clob_token_ids == ["98022490269692", "53831553061883"]
    # direct mode hits the gamma host, not the proxy
    called_url = mock_url.call_args[0][0].full_url
    assert called_url.startswith("https://gamma-api.polymarket.com/markets")


def test_token_id_for_maps_outcome_to_token():
    m = Market(
        id="m", question="?", slug="s", outcomes=["Yes", "No"],
        prices={"Yes": 0.5, "No": 0.5}, liquidity=1000, volume_24h=500,
        end_date="2026-12-31", category="",
        clob_token_ids=["TOKEN_YES", "TOKEN_NO"],
    )
    assert m.token_id_for("Yes") == "TOKEN_YES"
    assert m.token_id_for("No") == "TOKEN_NO"
    assert m.token_id_for("yes") == "TOKEN_YES"  # case-insensitive fallback
    assert m.token_id_for("Maybe") is None


def test_token_id_for_returns_none_when_unmapped():
    m = Market(
        id="m", question="?", slug="s", outcomes=["Yes", "No"],
        prices={}, liquidity=0, volume_24h=0, end_date="", category="",
    )  # no clob_token_ids
    assert m.token_id_for("Yes") is None


def test_market_edge_calculation():
    m = Market(
        id="m", question="?", slug="s", outcomes=["YES", "NO"],
        prices={"YES": 0.5, "NO": 0.5}, liquidity=1000, volume_24h=500,
        end_date="2026-12-31", category="",
    )
    assert m.edge(0.7, "YES") == pytest.approx(0.2)
    assert m.edge(0.3, "YES") == pytest.approx(-0.2)
