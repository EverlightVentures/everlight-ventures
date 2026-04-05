#!/usr/bin/env python3
"""
Polymarket Prediction Agent - Everlight Ventures
5-Agent Pipeline: Scanner -> Researcher -> Predictor -> Risk Manager -> Postmortem

Runs on Oracle E5 alongside XLM bot. Same infrastructure, different market.
Cipher Wolfe leads. Rex Thornton manages risk. Bull Archer does research.

Usage:
    python3 main.py              # Full cycle (scan + research + predict + bet)
    python3 main.py scan         # Scan markets only
    python3 main.py research     # Research current opportunities
    python3 main.py status       # Portfolio status
    python3 main.py postmortem   # Review settled bets
"""
import os
import sys
import json
import time
import logging
import hashlib
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass, field, asdict

import yaml

# Setup
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_DIR / "polymarket.log"),
    ],
)
log = logging.getLogger("polymarket")

# Load config
CONFIG_PATH = Path(__file__).parent / "config.yaml"
with open(CONFIG_PATH) as f:
    config = yaml.safe_load(f)


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class Market:
    """A Polymarket prediction market."""
    id: str
    question: str
    slug: str
    outcomes: list
    prices: dict  # outcome -> price (0-1)
    liquidity: float
    volume_24h: float
    end_date: str
    category: str = ""
    spread: float = 0.0

    def edge(self, predicted_prob: float, outcome: str) -> float:
        """Calculate edge: predicted probability - market price."""
        market_price = self.prices.get(outcome, 0.5)
        return predicted_prob - market_price


@dataclass
class Signal:
    """A news/social signal that may affect a market."""
    source: str  # twitter, telegram, rss
    text: str
    url: str = ""
    author: str = ""
    timestamp: str = ""
    credibility: float = 0.5
    sentiment: float = 0.0  # -1 to 1
    market_ids: list = field(default_factory=list)


@dataclass
class Prediction:
    """A prediction on a market outcome."""
    market_id: str
    question: str
    outcome: str
    predicted_prob: float
    market_price: float
    edge: float
    confidence: float
    reasoning: str
    signals: list = field(default_factory=list)


@dataclass
class Bet:
    """A placed bet."""
    id: str
    market_id: str
    outcome: str
    amount: float
    price: float
    predicted_prob: float
    edge: float
    timestamp: str
    status: str = "open"  # open, won, lost, cancelled
    pnl: float = 0.0


# ============================================================================
# AGENT 1: SCANNER (Cipher Wolfe)
# Filters 300+ markets by liquidity, volume, spread, time-to-resolution
# ============================================================================

def scan_markets() -> list[Market]:
    """Scan Polymarket for tradeable markets."""
    log.info("[SCANNER] Cipher Wolfe scanning markets...")

    gamma_url = config["polymarket"]["gamma_url"]
    min_liq = config["polymarket"]["min_liquidity"]
    max_scan = config["polymarket"]["max_markets_scan"]

    try:
        req = urllib.request.Request(
            f"{gamma_url}/markets?limit={max_scan}&active=true&closed=false",
            headers={"User-Agent": "EverLightPolyAgent/1.0"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw_markets = json.loads(resp.read())
    except Exception as e:
        log.error(f"[SCANNER] Failed to fetch markets: {e}")
        return []

    markets = []
    for m in raw_markets:
        try:
            liquidity = float(m.get("liquidityNum", 0) or 0)
            volume = float(m.get("volume24hr", 0) or 0)
            if liquidity < min_liq:
                continue

            outcomes = m.get("outcomes", ["Yes", "No"])
            prices = {}
            for i, outcome in enumerate(outcomes):
                price_key = f"outcomePrices"
                raw_prices = m.get(price_key, "")
                if isinstance(raw_prices, str) and raw_prices:
                    try:
                        price_list = json.loads(raw_prices)
                        if i < len(price_list):
                            prices[outcome] = float(price_list[i])
                    except (json.JSONDecodeError, IndexError):
                        prices[outcome] = 0.5
                else:
                    prices[outcome] = 0.5

            spread = abs(prices.get("Yes", 0.5) - prices.get("No", 0.5))

            market = Market(
                id=m.get("conditionId", m.get("id", "")),
                question=m.get("question", ""),
                slug=m.get("slug", ""),
                outcomes=outcomes,
                prices=prices,
                liquidity=liquidity,
                volume_24h=volume,
                end_date=m.get("endDate", ""),
                category=m.get("category", ""),
                spread=spread,
            )
            markets.append(market)
        except Exception as e:
            log.debug(f"[SCANNER] Skip market: {e}")
            continue

    # Sort by volume (most active first)
    markets.sort(key=lambda x: x.volume_24h, reverse=True)
    log.info(f"[SCANNER] Found {len(markets)} tradeable markets (min ${min_liq} liquidity)")

    # Save scan results
    scan_path = DATA_DIR / "latest_scan.json"
    with open(scan_path, "w") as f:
        json.dump([asdict(m) for m in markets[:50]], f, indent=2)

    return markets


# ============================================================================
# AGENT 2: RESEARCHER (Bull Archer + Perplexity Intel)
# Scrapes Twitter, Reddit, RSS for signals. Runs sentiment analysis.
# ============================================================================

def research_markets(markets: list[Market]) -> list[Signal]:
    """Research top markets via social media and news feeds."""
    log.info("[RESEARCHER] Bull Archer gathering intelligence...")
    signals = []

    # RSS feeds (always available, no API key needed)
    for feed_url in config["sources"]["rss"]["feeds"]:
        try:
            req = urllib.request.Request(feed_url, headers={"User-Agent": "EverLightPolyAgent/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                content = resp.read().decode("utf-8", errors="replace")

            # Simple XML parsing for RSS items
            items = content.split("<item>")[1:10]  # Top 10 items
            for item in items:
                title = _extract_xml_tag(item, "title")
                link = _extract_xml_tag(item, "link")
                pub_date = _extract_xml_tag(item, "pubDate")

                if not title:
                    continue

                # Check if any market keywords match
                matched_markets = []
                for m in markets[:20]:
                    keywords = m.question.lower().split()
                    if any(kw in title.lower() for kw in keywords if len(kw) > 3):
                        matched_markets.append(m.id)

                if matched_markets:
                    signals.append(Signal(
                        source="rss",
                        text=title,
                        url=link,
                        timestamp=pub_date,
                        credibility=0.7,
                        market_ids=matched_markets,
                    ))
        except Exception as e:
            log.debug(f"[RESEARCHER] RSS feed failed ({feed_url}): {e}")

    # Twitter (if API key available)
    twitter_key = os.environ.get("TWITTER_BEARER_TOKEN", "")
    if twitter_key and config["sources"]["twitter"]["enabled"]:
        for account in config["sources"]["twitter"]["accounts_watch"][:5]:
            try:
                username = account.lstrip("@")
                req = urllib.request.Request(
                    f"https://api.twitter.com/2/tweets/search/recent?query=from:{username}&max_results=10&tweet.fields=created_at",
                    headers={
                        "Authorization": f"Bearer {twitter_key}",
                        "User-Agent": "EverLightPolyAgent/1.0",
                    },
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read())

                for tweet in data.get("data", []):
                    text = tweet.get("text", "")
                    matched = [m.id for m in markets[:20]
                               if any(kw in text.lower() for kw in m.question.lower().split() if len(kw) > 3)]
                    if matched:
                        signals.append(Signal(
                            source="twitter",
                            text=text,
                            author=username,
                            timestamp=tweet.get("created_at", ""),
                            credibility=0.85,
                            market_ids=matched,
                        ))
            except Exception as e:
                log.debug(f"[RESEARCHER] Twitter failed ({account}): {e}")

    log.info(f"[RESEARCHER] Collected {len(signals)} relevant signals")

    # Save signals
    signals_path = DATA_DIR / "latest_signals.json"
    with open(signals_path, "w") as f:
        json.dump([asdict(s) for s in signals], f, indent=2)

    return signals


def _extract_xml_tag(xml: str, tag: str) -> str:
    """Simple XML tag extraction without dependencies."""
    start = xml.find(f"<{tag}>")
    end = xml.find(f"</{tag}>")
    if start == -1 or end == -1:
        return ""
    # Handle CDATA
    content = xml[start + len(tag) + 2:end]
    if content.startswith("<![CDATA["):
        content = content[9:]
        if content.endswith("]]>"):
            content = content[:-3]
    return content.strip()


# ============================================================================
# AGENT 3: PREDICTOR (Cipher Wolfe + Claude LLM)
# Calibrates true probability vs market price. Uses LLM for narrative analysis.
# ============================================================================

def predict(markets: list[Market], signals: list[Signal]) -> list[Prediction]:
    """Generate predictions for markets with signals."""
    log.info("[PREDICTOR] Cipher Wolfe calibrating predictions...")
    predictions = []
    threshold = config["prediction"]["confidence_threshold"]
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")

    for market in markets[:20]:  # Top 20 by volume
        relevant_signals = [s for s in signals if market.id in s.market_ids]

        if not relevant_signals and not anthropic_key:
            continue

        # Base prediction from market price (wisdom of crowd)
        yes_price = market.prices.get("Yes", 0.5)

        # Adjust based on signal sentiment
        signal_adjustment = 0.0
        for sig in relevant_signals:
            # Credible bullish signals push probability up
            weight = sig.credibility * 0.1
            if any(word in sig.text.lower() for word in ["confirmed", "approved", "passed", "won", "signed"]):
                signal_adjustment += weight
            elif any(word in sig.text.lower() for word in ["denied", "rejected", "lost", "failed", "blocked"]):
                signal_adjustment -= weight

        # LLM-enhanced prediction (if API key available)
        llm_adjustment = 0.0
        reasoning = "Signal-based prediction"
        if anthropic_key and relevant_signals:
            try:
                llm_result = _llm_predict(market, relevant_signals, anthropic_key)
                llm_adjustment = llm_result.get("adjustment", 0.0)
                reasoning = llm_result.get("reasoning", reasoning)
            except Exception as e:
                log.debug(f"[PREDICTOR] LLM prediction failed: {e}")

        # Final predicted probability
        predicted = min(0.95, max(0.05, yes_price + signal_adjustment + llm_adjustment))
        edge = predicted - yes_price
        confidence = min(0.95, abs(edge) * 2 + len(relevant_signals) * 0.05)

        if confidence >= threshold and abs(edge) >= config["risk"]["min_edge"]:
            outcome = "Yes" if edge > 0 else "No"
            pred = Prediction(
                market_id=market.id,
                question=market.question,
                outcome=outcome,
                predicted_prob=predicted if outcome == "Yes" else (1 - predicted),
                market_price=market.prices.get(outcome, 0.5),
                edge=abs(edge),
                confidence=confidence,
                reasoning=reasoning,
                signals=[s.text[:100] for s in relevant_signals[:3]],
            )
            predictions.append(pred)
            log.info(
                f"[PREDICTOR] {market.question[:60]}... "
                f"-> {outcome} @ {pred.predicted_prob:.1%} "
                f"(market: {pred.market_price:.1%}, edge: {pred.edge:.1%})"
            )

    log.info(f"[PREDICTOR] Generated {len(predictions)} actionable predictions")
    return predictions


def _llm_predict(market: Market, signals: list[Signal], api_key: str) -> dict:
    """Use Claude to analyze signals and predict market outcome."""
    signal_text = "\n".join(f"- [{s.source}] {s.text[:200]}" for s in signals[:5])
    prompt = (
        f"You are a prediction market analyst. Given this market and signals, "
        f"estimate the TRUE probability of the 'Yes' outcome.\n\n"
        f"Market: {market.question}\n"
        f"Current price: Yes={market.prices.get('Yes', 0.5):.1%}, No={market.prices.get('No', 0.5):.1%}\n"
        f"Liquidity: ${market.liquidity:,.0f}\n"
        f"Signals:\n{signal_text}\n\n"
        f"Respond in JSON: {{\"predicted_yes_prob\": 0.XX, \"adjustment\": +/-0.XX, \"reasoning\": \"...\"}}"
    )

    payload = json.dumps({
        "model": config["prediction"]["llm_model"],
        "max_tokens": 300,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read())

    text = result["content"][0]["text"]
    # Extract JSON from response
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        return json.loads(text[start:end])
    return {}


# ============================================================================
# AGENT 4: RISK MANAGER (Rex Thornton)
# Kelly criterion sizing. Blocks oversized bets. Daily loss limits.
# ============================================================================

def manage_risk(predictions: list[Prediction]) -> list[dict]:
    """Size bets using Kelly criterion with safety limits."""
    log.info("[RISK] Rex Thornton reviewing positions...")

    bankroll = _get_bankroll()
    daily_bets = _get_daily_bets()
    daily_pnl = sum(b.get("pnl", 0) for b in daily_bets)

    max_bets = config["risk"]["max_daily_bets"]
    max_loss = config["risk"]["max_daily_loss_pct"] / 100.0
    max_bet_pct = config["risk"]["max_bet_pct"] / 100.0
    kelly_frac = config["risk"]["kelly_fraction"]

    if len(daily_bets) >= max_bets:
        log.warning(f"[RISK] Daily bet limit reached ({max_bets}). No new bets.")
        return []

    if daily_pnl < -(bankroll * max_loss):
        log.warning(f"[RISK] Daily loss limit hit (${daily_pnl:.2f}). Shutting down.")
        return []

    approved = []
    for pred in predictions:
        # Kelly criterion: f* = (bp - q) / b
        # b = odds (payout ratio), p = true prob, q = 1-p
        p = pred.predicted_prob
        q = 1 - p
        b = (1 / pred.market_price) - 1  # implied odds
        if b <= 0:
            continue

        kelly = ((b * p) - q) / b
        if kelly <= 0:
            log.info(f"[RISK] Negative Kelly for {pred.question[:40]}... Skipping.")
            continue

        # Quarter-Kelly for safety
        position_size = bankroll * kelly * kelly_frac
        # Cap at max bet percentage
        position_size = min(position_size, bankroll * max_bet_pct)
        # Minimum $1 bet
        position_size = max(1.0, round(position_size, 2))

        if position_size > bankroll * 0.5:
            log.warning(f"[RISK] Bet too large (${position_size:.2f}). Capping at 50% bankroll.")
            position_size = round(bankroll * 0.5, 2)

        approved.append({
            "prediction": pred,
            "amount": position_size,
            "kelly": kelly,
            "bankroll": bankroll,
        })
        log.info(
            f"[RISK] APPROVED: {pred.question[:40]}... "
            f"${position_size:.2f} (Kelly: {kelly:.3f}, Edge: {pred.edge:.1%})"
        )

    log.info(f"[RISK] Approved {len(approved)}/{len(predictions)} bets")
    return approved


def _get_bankroll() -> float:
    """Get current bankroll from portfolio file."""
    portfolio_path = DATA_DIR / "portfolio.json"
    if portfolio_path.exists():
        with open(portfolio_path) as f:
            portfolio = json.load(f)
            return portfolio.get("bankroll", config["bankroll"]["initial"])
    return config["bankroll"]["initial"]


def _get_daily_bets() -> list:
    """Get today's bets from log."""
    bets_path = DATA_DIR / "bets.jsonl"
    if not bets_path.exists():
        return []
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    bets = []
    with open(bets_path) as f:
        for line in f:
            try:
                bet = json.loads(line)
                if bet.get("timestamp", "").startswith(today):
                    bets.append(bet)
            except json.JSONDecodeError:
                continue
    return bets


# ============================================================================
# AGENT 5: POSTMORTEM (Thomas Rourke - Data Verifier)
# Reviews settled bets. Figures out what went wrong. Updates system.
# ============================================================================

def run_postmortem():
    """Review settled bets and learn from mistakes."""
    log.info("[POSTMORTEM] Thomas Rourke reviewing settled bets...")

    bets_path = DATA_DIR / "bets.jsonl"
    if not bets_path.exists():
        log.info("[POSTMORTEM] No bets to review.")
        return

    open_bets = []
    settled = []
    with open(bets_path) as f:
        for line in f:
            try:
                bet = json.loads(line)
                if bet.get("status") == "open":
                    open_bets.append(bet)
                else:
                    settled.append(bet)
            except json.JSONDecodeError:
                continue

    if not settled:
        log.info("[POSTMORTEM] No settled bets yet.")
        return

    wins = [b for b in settled if b.get("status") == "won"]
    losses = [b for b in settled if b.get("status") == "lost"]
    total_pnl = sum(b.get("pnl", 0) for b in settled)
    win_rate = len(wins) / len(settled) if settled else 0

    report = {
        "date": datetime.now(timezone.utc).isoformat(),
        "total_bets": len(settled),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": win_rate,
        "total_pnl": total_pnl,
        "avg_edge": sum(b.get("edge", 0) for b in settled) / len(settled) if settled else 0,
        "open_positions": len(open_bets),
    }

    # Save postmortem
    pm_path = DATA_DIR / "postmortem.json"
    with open(pm_path, "w") as f:
        json.dump(report, f, indent=2)

    log.info(
        f"[POSTMORTEM] {len(settled)} bets | "
        f"Win rate: {win_rate:.1%} | "
        f"P&L: ${total_pnl:.2f} | "
        f"Open: {len(open_bets)}"
    )

    return report


# ============================================================================
# EXECUTION + SLACK REPORTING
# ============================================================================

def execute_bets(approved: list[dict]):
    """Place approved bets (paper trading mode until live wallet connected)."""
    log.info("[EXECUTION] Placing bets (PAPER MODE)...")

    bets_path = DATA_DIR / "bets.jsonl"
    placed = []

    for item in approved:
        pred = item["prediction"]
        amount = item["amount"]

        bet = Bet(
            id=hashlib.md5(f"{pred.market_id}{time.time()}".encode()).hexdigest()[:12],
            market_id=pred.market_id,
            outcome=pred.outcome,
            amount=amount,
            price=pred.market_price,
            predicted_prob=pred.predicted_prob,
            edge=pred.edge,
            timestamp=datetime.now(timezone.utc).isoformat(),
            status="open",
        )

        # Log bet
        with open(bets_path, "a") as f:
            f.write(json.dumps(asdict(bet)) + "\n")

        placed.append(bet)
        log.info(f"[BET] {pred.outcome} on '{pred.question[:50]}...' @ ${amount:.2f}")

    # Update bankroll
    if placed:
        bankroll = _get_bankroll()
        total_bet = sum(b.amount for b in placed)
        portfolio = {
            "bankroll": bankroll - total_bet,
            "invested": total_bet,
            "open_positions": len(placed),
            "updated": datetime.now(timezone.utc).isoformat(),
        }
        with open(DATA_DIR / "portfolio.json", "w") as f:
            json.dump(portfolio, f, indent=2)

    return placed


def slack_report(markets, signals, predictions, bets, postmortem=None):
    """Post summary to Slack."""
    token = os.environ.get("SLACK_BOT_TOKEN", "")
    if not token:
        return

    channel = config["slack"]["channels"]["markets"]
    bankroll = _get_bankroll()

    msg = (
        f"*Polymarket Agent -- Cycle Report*\n"
        f"Markets scanned: {len(markets)} | Signals: {len(signals)} | "
        f"Predictions: {len(predictions)} | Bets placed: {len(bets)}\n"
        f"Bankroll: ${bankroll:.2f}"
    )

    if bets:
        msg += "\n*New Bets:*\n"
        for b in bets:
            msg += f"  {b.outcome} @ ${b.amount:.2f} -- edge {b.edge:.1%}\n"

    if postmortem:
        msg += (
            f"\n*Performance:* {postmortem['wins']}W/{postmortem['losses']}L "
            f"({postmortem['win_rate']:.0%}) | P&L: ${postmortem['total_pnl']:.2f}"
        )

    payload = json.dumps({"channel": channel, "text": msg}).encode()
    try:
        req = urllib.request.Request(
            "https://slack.com/api/chat.postMessage",
            data=payload,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        log.error(f"Slack report failed: {e}")


# ============================================================================
# MAIN CYCLE
# ============================================================================

def run_full_cycle():
    """Full pipeline: scan -> research -> predict -> risk -> bet -> report."""
    log.info("=" * 60)
    log.info("POLYMARKET AGENT -- Full Cycle")
    log.info("=" * 60)

    # Agent 1: Scanner
    markets = scan_markets()
    if not markets:
        log.warning("No markets found. Exiting.")
        return

    # Agent 2: Researcher
    signals = research_markets(markets)

    # Agent 3: Predictor
    predictions = predict(markets, signals)

    # Agent 4: Risk Manager
    approved = manage_risk(predictions)

    # Execute approved bets
    bets = execute_bets(approved) if approved else []

    # Agent 5: Postmortem
    pm = run_postmortem()

    # Report to Slack
    slack_report(markets, signals, predictions, bets, pm)

    log.info("=" * 60)
    log.info(f"Cycle complete. {len(bets)} bets placed.")
    log.info("=" * 60)


def run_status():
    """Print current portfolio status."""
    bankroll = _get_bankroll()
    daily_bets = _get_daily_bets()
    pm_path = DATA_DIR / "postmortem.json"
    pm = json.load(open(pm_path)) if pm_path.exists() else {}

    print(f"Bankroll: ${bankroll:.2f}")
    print(f"Today's bets: {len(daily_bets)}")
    if pm:
        print(f"Win rate: {pm.get('win_rate', 0):.0%}")
        print(f"Total P&L: ${pm.get('total_pnl', 0):.2f}")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "full"

    if mode == "scan":
        scan_markets()
    elif mode == "research":
        markets = scan_markets()
        research_markets(markets)
    elif mode == "status":
        run_status()
    elif mode == "postmortem":
        run_postmortem()
    else:
        run_full_cycle()
