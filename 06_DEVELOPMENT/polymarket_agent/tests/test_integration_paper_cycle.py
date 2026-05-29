import json
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch, MagicMock
from polymarket_agent.main import run_paper_cycle


def test_paper_cycle_writes_all_ledgers(tmp_path: Path):
    cfg = {
        "polymarket": {"max_markets_scan": 10},
        "proxy": {"url": "https://x"},
        "risk": {"max_bet_pct": 5.0, "max_daily_loss_pct": 15.0,
                 "max_open_positions": 10, "min_edge": 0.05, "min_confidence": 0.5},
        "bankroll": {"initial": 250.0},
        "live_trading": {"enabled": False},
        # Disable network signal sources in unit tests (no live HTTP)
        "sonar": {"enabled": False},
        "rss_news": {"enabled": False},
        "rsshub": {"enabled": False},
        "telegram": {"enabled": False},
        "data_dir": str(tmp_path),
    }

    # Mock the CLOB to return one promising market
    fake_clob = MagicMock()
    from polymarket_agent.dataflows.polymarket_clob import Market
    fake_clob.scan_markets.return_value = [Market(
        id="mkt_1", question="Will Fed cut?", slug="x",
        outcomes=["YES","NO"], prices={"YES": 0.5, "NO": 0.5},
        liquidity=10000, volume_24h=2000,
        end_date="2026-12-31T00:00:00+00:00", category="Economics", spread=0.02,
    )]
    with patch("polymarket_agent.main.PolymarketCLOB", return_value=fake_clob), \
         patch("polymarket_agent.agents.predictor.Predictor._llm_predict",
               return_value=(0.65, 0.9, "edge=15%")):
        run_paper_cycle(cfg)

    assert (tmp_path / "active_markets.json").exists()
    assert (tmp_path / "research_briefs.json").exists()
    assert (tmp_path / "predictions.json").exists()
    assert (tmp_path / "approved_bets.json").exists()
    assert (tmp_path / "paper_open_bets.json").exists()
