"""Polymarket gamma + CLOB REST client. Goes through CF Worker proxy."""
import json
import urllib.request
from dataclasses import dataclass, field


@dataclass
class Market:
    id: str
    question: str
    slug: str
    outcomes: list
    prices: dict
    liquidity: float
    volume_24h: float
    end_date: str
    category: str = ""
    spread: float = 0.0

    def edge(self, predicted_prob: float, outcome: str) -> float:
        return predicted_prob - self.prices.get(outcome, 0.5)


class PolymarketCLOB:
    def __init__(self, proxy_url: str, timeout: int = 15):
        self.proxy_url = proxy_url.rstrip("/")
        self.timeout = timeout

    def _fetch_json(self, path: str) -> object:
        req = urllib.request.Request(
            f"{self.proxy_url}{path}",
            headers={"User-Agent": "polymarket-agent/0.1"},
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read())

    def scan_markets(self, limit: int = 300) -> list:
        data = self._fetch_json(
            f"/gamma/markets?limit={limit}&active=true&closed=false"
        )
        markets = []
        for m in data:
            try:
                prices = dict(zip(m["outcomes"], [float(p) for p in m["outcomePrices"]]))
                markets.append(Market(
                    id=m["id"], question=m["question"], slug=m.get("slug", ""),
                    outcomes=m["outcomes"], prices=prices,
                    liquidity=float(m.get("liquidity", 0)),
                    volume_24h=float(m.get("volume24hr", 0)),
                    end_date=m.get("endDate", ""), category=m.get("category", ""),
                ))
            except (KeyError, ValueError, TypeError):
                continue
        return markets
