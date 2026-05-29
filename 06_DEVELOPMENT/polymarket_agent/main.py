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

    # RESEARCH -- gather real signals from every enabled free source
    signals = gather_signals(cfg, filtered, data_dir)
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


def _make_notifier(cfg: dict, data_dir: Path):
    """Build the shared-services bridge from config (branded Slack + brain).
    Disabled gracefully if no Slack channels configured."""
    from polymarket_agent.notify import Notifier
    slack = cfg.get("slack", {}).get("channels", {})
    return Notifier(
        channel_trades=slack.get("trades", ""),
        channel_alerts=slack.get("alerts", ""),
        brain_log_path=data_dir / "brain_log.jsonl",
        enabled=bool(slack.get("trades") or slack.get("alerts")),
    )


def gather_signals(cfg: dict, filtered, data_dir: Path) -> list:
    """Invoke every ENABLED free signal source and merge into one Signal list.
    Each source is isolated in try/except -- one dead source (e.g. Sonar 401,
    Nitter down) must never kill the trade cycle. This is the step that makes
    the dataflows actually part of the pipeline (not just built + tested)."""
    signals = []

    # RSS news (Reuters/BBC/CoinDesk) -- free, always on
    try:
        rss_cfg = cfg.get("rss_news", {})
        if rss_cfg.get("enabled", True) and rss_cfg.get("feeds"):
            signals += RSSNews(feeds=rss_cfg["feeds"]).get_recent_items(last_minutes=30)
    except Exception as e:
        log.warning("RSS source failed: %s", e)

    # Perplexity Sonar -- real-time, source-cited (the Twitter-API replacement).
    # Query the distinct categories present in this cycle's markets (capped).
    try:
        if cfg.get("sonar", {}).get("enabled", True):
            cats = []
            for m in filtered:
                c = (m.category or "").strip()
                if c and c not in cats:
                    cats.append(c)
            sonar = Sonar()
            for c in cats[:3]:  # cap API calls per cycle
                signals += sonar.get_news_velocity(category=c, last_minutes=15)
    except Exception as e:
        log.warning("Sonar source failed: %s", e)

    # Self-hosted RSSHub Twitter mirror -- free, only if reachable
    try:
        rh = cfg.get("rsshub", {})
        if rh.get("enabled") and rh.get("accounts"):
            signals += RSSHubClient(base_url=rh.get("base_url", "http://e5-mother:1200")) \
                .get_recent_tweets(usernames=rh["accounts"], last_minutes=15)
    except Exception as e:
        log.warning("RSSHub source failed: %s", e)

    # Telegram mirror channels -- only if a bot token is configured + ledger exists
    try:
        tg = cfg.get("telegram", {})
        if tg.get("enabled"):
            signals += TelegramBridge(ledger_path=data_dir / "telegram_signals.jsonl") \
                .get_recent_signals(last_minutes=15)
    except Exception as e:
        log.warning("Telegram source failed: %s", e)

    log.info("gathered %d signals across enabled sources", len(signals))
    return signals


def _build_briefs(filtered, signals):
    """Aggregate signals per market and attach the bettable outcome + its price.
    Uses each market's real first outcome label (live gamma is 'Yes'/'No',
    not 'YES'); falls back to YES for fixtures."""
    researcher = Researcher()
    briefs = researcher.aggregate(filtered, signals)
    for m in filtered:
        if m.id not in briefs:
            continue
        outcome = m.outcomes[0] if m.outcomes else "YES"
        briefs[m.id]["_market_price"] = m.prices.get(outcome, m.prices.get("YES", 0.5))
        briefs[m.id]["_outcome"] = outcome
    return briefs


def run_live_cycle(cfg: dict, backend=None, wallet=None):
    """One REAL cycle: scan -> research -> predict -> risk -> place real orders
    via LiveClobBackend -> reconcile against on-chain truth.

    Requires a funded wallet AND config live_trading.enabled=true AND env
    LIVE_TRADING=true (the executor enforces the two-factor gate). The whitelist
    is rebuilt from this cycle's open markets (closes the stale-whitelist gap),
    and outcomes are mapped to CLOB token ids before any order is placed.

    backend/wallet are injectable for testing; built from the key file otherwise.
    """
    from polymarket_agent.execution.clob_live import LiveClobBackend, read_key_file
    from polymarket_agent.execution.wallet import PolygonWallet
    from polymarket_agent.execution.executor_polymarket import (
        PolymarketExecutor, BetRequest,
    )
    from polymarket_agent.execution.reconcile import Reconciler
    from polymarket_agent.execution.exceptions import PolymarketExecutorError

    data_dir = Path(cfg.get("data_dir", "data"))
    data_dir.mkdir(parents=True, exist_ok=True)
    state_path = data_dir / "bankroll.json"
    open_bets_path = data_dir / "open_bets.json"
    halt_path = Path(cfg.get("halt_path", str(data_dir / "HALT")))
    if not state_path.exists():
        state_path.write_text(json.dumps({
            "cash_usdc": 0.0, "open_positions_value_usdc": 0.0, "daily_pnl_usdc": 0.0,
        }))
    if not open_bets_path.exists():
        open_bets_path.write_text(json.dumps([]))

    # Real backend + wallet (key from the secure file) unless injected.
    if backend is None:
        key = read_key_file(cfg["wallet"]["key_path"])
        backend = LiveClobBackend(
            private_key=key, host="https://clob.polymarket.com",
            chain_id=137, auto_auth=True,
        )
    if wallet is None:
        wallet = PolygonWallet(private_key_path=cfg["wallet"]["key_path"])

    # SCAN (direct -- the live API is reachable without the proxy)
    clob = PolymarketCLOB()
    markets = clob.scan_markets(limit=cfg["polymarket"]["max_markets_scan"])
    scanner = Scanner()
    filtered = scanner.filter(markets)
    by_id = {m.id: m for m in filtered}
    (data_dir / "active_markets.json").write_text(
        json.dumps([asdict(m) for m in filtered], indent=2)
    )

    # RESEARCH -> PREDICT -> RISK (real signals from every enabled free source)
    signals = gather_signals(cfg, filtered, data_dir)
    briefs = _build_briefs(filtered, signals=signals)
    predictor = Predictor(
        min_edge=cfg["risk"]["min_edge"],
        min_confidence=cfg["risk"]["min_confidence"],
    )
    predictions = predictor.predict(briefs, brain_policy={})
    rm = RiskManager(
        max_bet_pct=Decimal(str(cfg["risk"]["max_bet_pct"])),
        max_daily_loss_pct=Decimal(str(cfg["risk"]["max_daily_loss_pct"])),
        max_open_positions=cfg["risk"]["max_open_positions"],
        min_edge=Decimal(str(cfg["risk"]["min_edge"])),
        # Thread min_confidence so the risk gate matches the predictor gate;
        # the brain-bridge halves raw confidence when no brain policy is set.
        min_confidence=float(cfg["risk"].get("min_confidence", 0.65)),
    )
    approved = rm.evaluate(predictions, state_path=state_path, open_bets_path=open_bets_path)

    # Whitelist = token ids of THIS cycle's open markets (fresh -> no stale markets).
    whitelist = set()
    for m in filtered:
        for o in m.outcomes:
            t = m.token_id_for(o)
            if t:
                whitelist.add(t)

    executor = PolymarketExecutor(
        wallet=wallet, clob=backend,
        config={
            "live_trading_enabled": cfg.get("live_trading", {}).get("enabled", False),
            "max_bet_pct": cfg["risk"]["max_bet_pct"],
            "max_open_positions": cfg["risk"]["max_open_positions"],
            "max_daily_loss_pct": cfg["risk"]["max_daily_loss_pct"],
            "active_whitelist": whitelist,
        },
        bankroll_state_path=state_path, halt_path=halt_path, open_bets_path=open_bets_path,
    )

    # Shared-services bridge: branded Slack + brain (degrades gracefully).
    notifier = _make_notifier(cfg, data_dir)

    placed = 0
    for b in approved:
        mkt = by_id.get(b.market_id)
        if mkt is None:
            continue
        token_id = mkt.token_id_for(b.outcome)
        if not token_id:
            log.warning("no CLOB token id for %s / %s -- skipping", b.market_id, b.outcome)
            continue
        try:
            bet = executor.submit_order(BetRequest(
                market_id=token_id, outcome=b.outcome,
                amount_usdc=b.amount_usdc, limit_price=b.limit_price,
                predicted_prob=b.predicted_prob, edge=b.edge,
            ))
            placed += 1
            notifier.order_placed(bet)  # branded deal card to #polymarket-trades
        except PolymarketExecutorError as e:
            log.warning("executor rejected bet: %s: %s", type(e).__name__, e)

    # RECONCILE against on-chain truth -- drift halts (the XLM-disaster preventer).
    reconciler = Reconciler(
        wallet, backend, bankroll_state_path=state_path, halt_path=halt_path,
    )
    result = reconciler.reconcile_now()
    if result.halt_required:
        log.error("RECONCILE HALT -- drift %s; no further trading until cleared",
                  result.drift_usd)
        notifier.halted("reconcile_drift", f"drift {result.drift_usd} -- trading halted")
    log.info("live cycle complete: %d order(s) placed, %d markets, halt=%s",
             placed, len(filtered), result.halt_required)
    summary = {"placed": placed, "markets": len(filtered), "halt": result.halt_required}
    notifier.cycle_summary(summary)  # brain log (local-first + best-effort Blinko)
    return summary


def main():
    cfg_path = Path(__file__).parent / "config.yaml"
    cfg = yaml.safe_load(cfg_path.read_text())
    cfg.setdefault("data_dir", str(Path(__file__).parent / "data"))
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
    mode = sys.argv[1] if len(sys.argv) > 1 else "paper"
    if mode == "live":
        run_live_cycle(cfg)
    else:
        run_paper_cycle(cfg)


if __name__ == "__main__":
    main()
