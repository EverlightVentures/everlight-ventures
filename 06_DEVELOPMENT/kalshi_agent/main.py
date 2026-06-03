#!/usr/bin/env python3
"""Polymarket Agent orchestrator. Thin cycle: scan -> research -> predict -> risk -> execute."""
import json
import logging
import os
import sys
import time
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path

import yaml

from kalshi_agent.dataflows.polymarket_clob import PolymarketCLOB
from kalshi_agent.dataflows.rss_news import RSSNews
from kalshi_agent.dataflows.rsshub_client import RSSHubClient
from kalshi_agent.dataflows.telegram_signals import TelegramBridge
from kalshi_agent.dataflows.orderbook_sentinel import OrderbookSentinel
from kalshi_agent.dataflows.perplexity_sonar import Sonar
from kalshi_agent.agents.scanner import Scanner
from kalshi_agent.agents.researcher import Researcher
from kalshi_agent.agents.predictor import Predictor
from kalshi_agent.agents.risk_manager import RiskManager
from kalshi_agent.execution.executor_polymarket_paper import (
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

    # SCAN -- direct unless the CF proxy is explicitly enabled (direct works
    # from the US Oracle region; proxy is the documented geo-block fallback).
    proxy_cfg = cfg.get("proxy", {})
    proxy_url = proxy_cfg.get("url") if proxy_cfg.get("enabled") else None
    clob = PolymarketCLOB(proxy_url=proxy_url)
    markets = clob.scan_markets(limit=cfg["polymarket"]["max_markets_scan"])
    _cal = cfg.get("calibration", {})
    _maxh = _cal.get("max_hours_to_resolution") if _cal.get("prefer_short_horizon") else None
    scanner = Scanner(max_hours_to_resolution=_maxh)
    filtered = scanner.filter(markets)
    (data_dir / "active_markets.json").write_text(
        json.dumps([asdict(m) for m in filtered], indent=2)
    )

    # RESEARCH -- gather real signals from every enabled free source
    signals = gather_signals(cfg, filtered, data_dir)
    researcher = Researcher()
    briefs = researcher.aggregate(filtered, signals)
    # Inject prices/outcomes for predictor (both sides for NO-side betting)
    for m in filtered:
        if m.id in briefs:
            outcome = m.outcomes[0] if m.outcomes else "YES"
            briefs[m.id]["_market_price"] = m.prices.get(outcome, m.prices.get("YES", 0.5))
            briefs[m.id]["_outcome"] = outcome
            briefs[m.id]["_prices"] = dict(m.prices)
            briefs[m.id]["_outcomes"] = list(m.outcomes)
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
    cv = cfg.get("convexity", {})
    rm = RiskManager(
        max_bet_pct=Decimal(str(cfg["risk"]["max_bet_pct"])),
        max_daily_loss_pct=Decimal(str(cfg["risk"]["max_daily_loss_pct"])),
        max_open_positions=cfg["risk"]["max_open_positions"],
        min_edge=Decimal(str(cfg["risk"]["min_edge"])),
        min_confidence=float(cfg["risk"].get("min_confidence", 0.65)),
        # Convexity lane active in calibration too, so paper data reflects it.
        convex_max_price=Decimal(str(cv.get("max_price", 0.20))),
        convex_min_edge=Decimal(str(cv.get("min_edge", 0.03))),
        convex_min_confidence=float(cv.get("min_confidence", 0.45)),
        convex_budget_pct=Decimal(str(cv.get("budget_pct", 15.0))),
        convex_stake_pct=Decimal(str(cv.get("stake_pct", 1.0))),
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

    # SETTLE: resolve any paper bets whose markets have closed -> calibration data.
    # This is what makes the 20-trade Brier gate actually accumulate over time.
    try:
        from kalshi_agent.settle_paper import settle
        s = settle(data_dir)
        log.info("paper cycle: %d approved, settled %d resolved (%d still open)",
                 len(approved), s["resolved"], s["still_open"])
    except Exception as e:
        log.warning("paper settlement failed: %s", e)


def _apply_egress(cfg: dict):
    """Route HTTPS (incl. ClobClient order POSTs) through the non-US egress proxy
    when configured -- this is what clears Polymarket's US order geoblock. The
    proxy is a CONNECT tunnel, so TLS stays end-to-end (creds never exposed)."""
    proxy = (cfg.get("egress", {}) or {}).get("proxy_url", "")
    if proxy:
        os.environ["HTTPS_PROXY"] = proxy
        os.environ["https_proxy"] = proxy
        log.info("egress: routing live HTTPS through %s (non-US exit)", proxy)
    return bool(proxy)


def _make_notifier(cfg: dict, data_dir: Path):
    """Build the shared-services bridge from config (branded Slack + brain).
    Disabled gracefully if no Slack channels configured."""
    from kalshi_agent.notify import Notifier
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

    # Smart-money copy-trade -- follow vetted profitable wallets (the most-cited
    # real retail edge from the research transcripts). Free, on-chain.
    try:
        sm = cfg.get("smart_money", {})
        if sm.get("enabled") and sm.get("wallets"):
            from kalshi_agent.dataflows.smart_money import SmartMoney
            signals += SmartMoney(wallets=sm["wallets"],
                                  min_size_usd=float(sm.get("min_size_usd", 100))) \
                .get_smart_money_signals(last_minutes=120)
    except Exception as e:
        log.warning("Smart-money source failed: %s", e)

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
        # Full price/outcome map so the predictor can evaluate BOTH sides
        # (bet NO when YES is overpriced -- fades longshots).
        briefs[m.id]["_prices"] = dict(m.prices)
        briefs[m.id]["_outcomes"] = list(m.outcomes)
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
    from kalshi_agent.execution.clob_live import LiveClobBackend, read_key_file
    from kalshi_agent.execution.wallet import PolygonWallet
    from kalshi_agent.execution.executor_polymarket import (
        PolymarketExecutor, BetRequest,
    )
    from kalshi_agent.execution.reconcile import Reconciler
    from kalshi_agent.execution.exceptions import PolymarketExecutorError

    _apply_egress(cfg)  # route order POSTs through the non-US proxy (clears 403)
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
    # Resolve the key path cross-host (phone -> e5 -> oracle) with a config override.
    from kalshi_agent.paths import wallet_key_path
    cfg_key = cfg.get("wallet", {}).get("key_path")
    key_path = cfg_key if (cfg_key and os.path.isfile(cfg_key)) else wallet_key_path()
    if backend is None:
        key = read_key_file(key_path)
        backend = LiveClobBackend(
            private_key=key, host="https://clob.polymarket.com",
            chain_id=137, auto_auth=True,
        )
    if wallet is None:
        wallet = PolygonWallet(private_key_path=key_path)

    # SCAN (direct -- the live API is reachable without the proxy)
    clob = PolymarketCLOB()
    markets = clob.scan_markets(limit=cfg["polymarket"]["max_markets_scan"])
    _cal = cfg.get("calibration", {})
    _maxh = _cal.get("max_hours_to_resolution") if _cal.get("prefer_short_horizon") else None
    scanner = Scanner(max_hours_to_resolution=_maxh)
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
    # Growth-ladder absolute bet ceiling for the current bankroll band.
    from kalshi_agent import growth
    state_now = json.loads(state_path.read_text())
    bankroll_now = Decimal(str(state_now.get("cash_usdc") or 0))
    tier_cap = growth.max_bet_for(bankroll_now, cfg)
    cv = cfg.get("convexity", {})
    rm = RiskManager(
        max_bet_pct=Decimal(str(cfg["risk"]["max_bet_pct"])),
        max_daily_loss_pct=Decimal(str(cfg["risk"]["max_daily_loss_pct"])),
        max_open_positions=cfg["risk"]["max_open_positions"],
        min_edge=Decimal(str(cfg["risk"]["min_edge"])),
        # Thread min_confidence so the risk gate matches the predictor gate;
        # the brain-bridge halves raw confidence when no brain policy is set.
        min_confidence=float(cfg["risk"].get("min_confidence", 0.65)),
        max_bet_abs=tier_cap,  # operator compound-growth ladder ceiling
        # Convexity lane: catch the big asymmetric/moonshot trades (bounded).
        convex_max_price=Decimal(str(cv.get("max_price", 0.20))),
        convex_min_edge=Decimal(str(cv.get("min_edge", 0.03))),
        convex_min_confidence=float(cv.get("min_confidence", 0.45)),
        convex_budget_pct=Decimal(str(cv.get("budget_pct", 15.0))),
        convex_stake_pct=Decimal(str(cv.get("stake_pct", 1.0))),
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
    # Shared intelligence: Codex/Gemini cross-check + OSINT + brain (the O-cent layer).
    from kalshi_agent.intelligence import SharedIntelligence
    intel = SharedIntelligence(
        enabled_osint=cfg.get("intelligence", {}).get("osint", True),
        enabled_crosscheck=cfg.get("intelligence", {}).get("cross_check", True),
    )

    placed = 0
    for b in approved:
        mkt = by_id.get(b.market_id)
        if mkt is None:
            continue
        token_id = mkt.token_id_for(b.outcome)
        if not token_id:
            log.warning("no CLOB token id for %s / %s -- skipping", b.market_id, b.outcome)
            continue
        # 9-phase doctrine: red-team high-stakes bets with Codex + Gemini before
        # risking money. A reviewer that ANSWERS and disagrees vetoes the bet;
        # unavailable reviewers degrade open (the 9 executor checks still gate).
        verdict = intel.cross_check(
            question=mkt.question, outcome=b.outcome,
            predicted_prob=b.predicted_prob, market_price=float(b.limit_price),
            reasoning=getattr(b, "reasoning", ""),
        )
        if verdict.get("vetoed"):
            log.warning("cross-check VETO on %s/%s -- skipping (%s)",
                        mkt.id, b.outcome, verdict)
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


def run_candle_cycle(cfg: dict):
    """High-activity 5-min crypto candle lane (paper). Run every ~1 min so we can
    enter LATE in each window. For each configured asset: decide via momentum,
    place a small bounded paper bet on strong late moves, and settle finished
    windows deterministically from the price feed. NO REAL MONEY (paper)."""
    from kalshi_agent.dataflows.crypto_candle import candle_decision, window_outcome
    import uuid
    cc = cfg.get("crypto_candle", {})
    data_dir = Path(cfg.get("data_dir", "data"))
    data_dir.mkdir(parents=True, exist_ok=True)
    _ensure_state(data_dir, cfg["bankroll"]["initial"])
    open_path = data_dir / "candle_open_bets.json"
    closed_path = data_dir / "candle_closed_bets.json"
    shadow_path = data_dir / "candle_shadow_open.json"
    ledger = data_dir / "calibration_ledger.jsonl"
    openb = json.loads(open_path.read_text()) if open_path.exists() else []
    closed = json.loads(closed_path.read_text()) if closed_path.exists() else []
    shadow_open = json.loads(shadow_path.read_text()) if shadow_path.exists() else []
    stake = float(cc.get("stake_usd", 2.0))
    min_edge = float(cc.get("min_edge", 0.05))

    def _calib(lane, rec, outcome, won, pnl):
        with open(ledger, "a") as f:
            f.write(json.dumps({"ts": time.time(), "lane": lane, "asset": rec["asset"],
                                "predicted_prob": rec["predicted_prob"], "bet_outcome": rec["outcome"],
                                "market_price": rec.get("price"), "outcome_resolved": outcome,
                                "won": won, "pnl_usdc": str(pnl)}) + "\n")

    # 1) SETTLE finished REAL bets by price (deterministic, no oracle wait)
    still_open = []
    for b in openb:
        out = window_outcome(b["asset"], b["window_ts"])
        if out is None:
            still_open.append(b); continue
        won = out == b["outcome"]
        price = Decimal(str(b["price"]))
        amt = Decimal(str(b["amount_usdc"]))
        pnl = (amt / price - amt) if won else -amt
        b.update({"status": "won" if won else "lost", "pnl_usdc": str(pnl), "outcome_resolved": out})
        closed.append(b)
        _calib("candle", b, out, won, pnl)
    openb = still_open

    # 1b) SETTLE finished SHADOW predictions (no money -- pure accuracy signal).
    # These are the coin-flip candles the cost gate correctly refuses to bet, but
    # whose prediction-vs-outcome still tells us if momentum has any real edge.
    still_shadow = []
    settled_shadow = 0
    for s in shadow_open:
        out = window_outcome(s["asset"], s["window_ts"])
        if out is None:
            still_shadow.append(s); continue
        _calib("candle_shadow", s, out, out == s["outcome"], "0")
        settled_shadow += 1
    shadow_open = still_shadow

    # 2) DECIDE: record ONE prediction per asset per window. Bet when every cost
    #    gate clears; otherwise log a SHADOW prediction so calibration accrues.
    placed = shadowed = 0
    for asset in cc.get("assets", ["BTC"]):
        d = candle_decision(asset, min_edge=min_edge,
                            enter_after_min=float(cc.get("enter_after_min", 3.0)),
                            stake=stake, fee_rate=float(cc.get("fee_rate", 0.02)),
                            gas_usd=float(cc.get("gas_usd", 0.01)),
                            min_net_ev_pct=float(cc.get("min_net_ev_pct", 0.05)))
        if not d or not d.get("outcome") or d.get("window_ts") is None:
            continue  # no directional claim this tick
        wts = int(d["window_ts"])
        if any(o["asset"] == asset and o["window_ts"] == wts for o in openb) \
           or any(s["asset"] == asset and s["window_ts"] == wts for s in shadow_open):
            continue  # already predicted this window
        if d.get("bet"):
            openb.append({
                "id": f"candle_{uuid.uuid4().hex[:10]}", "asset": asset,
                "window_ts": wts, "outcome": d["outcome"], "amount_usdc": str(stake),
                "price": str(d["market_price"]), "predicted_prob": d["predicted_prob"],
                "edge": d["edge"], "ts": time.time(),
            })
            placed += 1
            log.info("candle: BET %s %s @ %.3f (pred %.2f edge %+.3f) -- %s",
                     asset, d["outcome"], d["market_price"], d["predicted_prob"], d["edge"],
                     d.get("question", "")[:40])
        else:
            shadow_open.append({
                "id": f"shadow_{uuid.uuid4().hex[:10]}", "asset": asset,
                "window_ts": wts, "outcome": d["outcome"],
                "price": str(d["market_price"]), "predicted_prob": d["predicted_prob"],
                "edge": d["edge"], "skip_reason": d.get("skip_reason"), "ts": time.time(),
            })
            shadowed += 1
            log.info("candle: SHADOW %s %s pred %.2f vs price %.3f (%s)",
                     asset, d["outcome"], d["predicted_prob"], d["market_price"], d.get("skip_reason"))

    open_path.write_text(json.dumps(openb, indent=2))
    closed_path.write_text(json.dumps(closed, indent=2))
    shadow_path.write_text(json.dumps(shadow_open, indent=2))
    log.info("candle cycle: %d bet, %d shadow, %d open, %d closed, %d shadow-open",
             placed, shadowed, len(openb), len(closed), len(shadow_open))
    return {"placed": placed, "shadow": shadowed, "open": len(openb),
            "closed": len(closed), "shadow_open": len(shadow_open),
            "settled_shadow": settled_shadow}


def _cw(decision):
    """Window ts from a candle decision's slug (…-5m-{ts})."""
    try:
        return int(decision["slug"].rsplit("-", 1)[1])
    except Exception:
        return 0


def main():
    cfg_path = Path(__file__).parent / "config.yaml"
    cfg = yaml.safe_load(cfg_path.read_text())
    cfg.setdefault("data_dir", str(Path(__file__).parent / "data"))
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
    mode = sys.argv[1] if len(sys.argv) > 1 else "paper"
    if mode == "live":
        run_live_cycle(cfg)
    elif mode == "candle":
        run_candle_cycle(cfg)
    else:
        run_paper_cycle(cfg)


if __name__ == "__main__":
    main()
