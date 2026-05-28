#!/usr/bin/env python3
"""Polymarket Agent orchestrator. Thin cycle: scan -> research -> predict -> risk -> execute."""
import json
import logging
import sys
import time
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path

import yaml

from polymarket_agent.dataflows.polymarket_clob import PolymarketCLOB
from polymarket_agent.dataflows.rss_news import RSSNews
from polymarket_agent.dataflows.rsshub_client import RSSHubClient
from polymarket_agent.dataflows.telegram_signals import TelegramBridge
from polymarket_agent.dataflows.orderbook_sentinel import OrderbookSentinel
from polymarket_agent.dataflows.perplexity_sonar import Sonar
from polymarket_agent.agents.scanner import Scanner
from polymarket_agent.agents.researcher import Researcher
from polymarket_agent.agents.predictor import Predictor
from polymarket_agent.agents.risk_manager import RiskManager
from polymarket_agent.execution.executor_polymarket_paper import (
    PaperExecutor, PaperBetRequest,
)


log = logging.getLogger("polymarket")


def _ensure_state(data_dir: Path, initial: float):
    bankroll_path = data_dir / "paper_bankroll.json"
    if not bankroll_path.exists():
        bankroll_path.write_text(json.dumps({
            "cash_usdc": initial, "open_positions_value_usdc": 0.0,
            "daily_pnl_usdc": 0.0,
        }))
    open_bets = data_dir / "paper_open_bets.json"
    if not open_bets.exists():
        open_bets.write_text(json.dumps([]))


def run_paper_cycle(cfg: dict):
    """One full paper cycle. Writes JSON ledgers across agent boundaries."""
    data_dir = Path(cfg.get("data_dir", "data"))
    data_dir.mkdir(parents=True, exist_ok=True)
    _ensure_state(data_dir, cfg["bankroll"]["initial"])

    # SCAN
    clob = PolymarketCLOB(cfg["proxy"]["url"])
    markets = clob.scan_markets(limit=cfg["polymarket"]["max_markets_scan"])
    scanner = Scanner()
    filtered = scanner.filter(markets)
    (data_dir / "active_markets.json").write_text(
        json.dumps([asdict(m) for m in filtered], indent=2)
    )

    # RESEARCH (signals = empty for unit test; integration test will populate)
    signals = []
    researcher = Researcher()
    briefs = researcher.aggregate(filtered, signals)
    # Inject market prices for predictor
    for m in filtered:
        if m.id in briefs:
            briefs[m.id]["_market_price"] = m.prices.get("YES", 0.5)
            briefs[m.id]["_outcome"] = "YES"
    (data_dir / "research_briefs.json").write_text(json.dumps(
        {k: {kk: vv if kk != "signals" else [asdict(s) for s in vv]
             for kk, vv in v.items()} for k, v in briefs.items()},
        indent=2,
    ))

    # PREDICT
    predictor = Predictor(
        min_edge=cfg["risk"]["min_edge"],
        min_confidence=cfg["risk"]["min_confidence"],
    )
    predictions = predictor.predict(briefs, brain_policy={})
    (data_dir / "predictions.json").write_text(json.dumps(
        [asdict(p) for p in predictions], indent=2,
    ))

    # RISK
    rm = RiskManager(
        max_bet_pct=Decimal(str(cfg["risk"]["max_bet_pct"])),
        max_daily_loss_pct=Decimal(str(cfg["risk"]["max_daily_loss_pct"])),
        max_open_positions=cfg["risk"]["max_open_positions"],
        min_edge=Decimal(str(cfg["risk"]["min_edge"])),
    )
    approved = rm.evaluate(
        predictions,
        state_path=data_dir / "paper_bankroll.json",
        open_bets_path=data_dir / "paper_open_bets.json",
    )
    (data_dir / "approved_bets.json").write_text(json.dumps(
        [{"market_id": b.market_id, "outcome": b.outcome,
          "amount_usdc": str(b.amount_usdc), "limit_price": str(b.limit_price)}
         for b in approved], indent=2,
    ))

    # EXECUTE (paper)
    executor = PaperExecutor(
        paper_state_path=data_dir / "paper_bankroll.json",
        paper_open_bets_path=data_dir / "paper_open_bets.json",
    )
    for b in approved:
        try:
            executor.submit_order(PaperBetRequest(
                market_id=b.market_id, outcome=b.outcome,
                amount_usdc=b.amount_usdc, limit_price=b.limit_price,
                predicted_prob=b.predicted_prob, edge=b.edge,
            ))
        except ValueError:
            continue


def main():
    cfg_path = Path(__file__).parent / "config.yaml"
    cfg = yaml.safe_load(cfg_path.read_text())
    cfg.setdefault("data_dir", str(Path(__file__).parent / "data"))
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
    run_paper_cycle(cfg)


if __name__ == "__main__":
    main()
