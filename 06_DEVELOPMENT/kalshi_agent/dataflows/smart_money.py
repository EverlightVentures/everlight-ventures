"""Smart-money copy-trade signal -- the most-cited REAL retail edge.

Across the operator's research transcripts, the one accessible edge that keeps
recurring is following sharp, consistently-profitable wallets (the leaderboard
'copy-trade' play). This reads Polymarket's public trade feed for a watchlist of
vetted wallets and emits a Signal when one takes a fresh position -- free,
on-chain, no paid tool (the videos sell Creo Bot / 'AI Match' for this).

Discipline (from the research): copy-trading is FRAGILE -- wallets drift, most
'top' wallets are fast bots whose fills are stale by the time we see them. So
this is ONE signal among many (it feeds the researcher + 360 synthesis, it does
NOT auto-fire a trade), and the watchlist must be VETTED, not the raw top-N.
"""
import json
import logging
import time
import urllib.request
from datetime import datetime, timezone

from kalshi_agent.dataflows.interface import Signal

log = logging.getLogger("polymarket.smartmoney")
DATA_API = "https://data-api.polymarket.com"


class SmartMoney:
    def __init__(self, wallets: list = None, min_size_usd: float = 100.0):
        # wallets: vetted profitable proxy-wallet addresses to follow.
        self.wallets = [w.lower() for w in (wallets or [])]
        self.min_size_usd = min_size_usd

    def _recent_trades(self, wallet: str, limit: int = 20) -> list:
        url = f"{DATA_API}/trades?user={wallet}&limit={limit}"
        req = urllib.request.Request(url, headers={"User-Agent": "ev-sm/1.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
        return data if isinstance(data, list) else data.get("data", [])

    def get_smart_money_signals(self, last_minutes: int = 60, now_ts: float = None) -> list:
        if not self.wallets:
            return []
        now = now_ts if now_ts is not None else time.time()
        cutoff = now - last_minutes * 60
        signals = []
        for w in self.wallets:
            try:
                trades = self._recent_trades(w)
            except Exception as e:
                log.warning("smart-money fetch failed for %s: %s", w[:10], e)
                continue
            for t in trades:
                try:
                    ts = float(t.get("timestamp", 0))
                    if ts < cutoff:
                        continue
                    size = float(t.get("size", 0)) * float(t.get("price", 0))
                    if size < self.min_size_usd:
                        continue
                    if str(t.get("side", "")).upper() != "BUY":
                        continue  # fresh entries, not exits
                    name = t.get("name") or t.get("pseudonym") or w[:8]
                    title = t.get("title", "")
                    outcome = t.get("outcome", "")
                    signals.append(Signal(
                        source="smart_money",
                        text=f"Smart-money {name} bought {outcome} on: {title}",
                        url=f"https://polymarket.com/event/{t.get('eventSlug','')}",
                        author=name,
                        timestamp=datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(),
                        credibility=0.9,  # vetted profitable wallet action
                        # sentiment: a BUY of an outcome is bullish that outcome
                        sentiment=0.6,
                    ))
                except (TypeError, ValueError):
                    continue
        return signals
