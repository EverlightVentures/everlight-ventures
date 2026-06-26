"""Polymarket gamma + CLOB REST client.

Direct by default (the live CLOB + gamma API return HTTP 200 from the US
Oracle region -- the geo-block is on the website, not the trading API). Pass
proxy_url to route through the CF Worker fallback if Polymarket ever blocks the
host IP; then paths are prefixed /gamma and /clob to match the Worker routes.
"""
import json
import urllib.request
from dataclasses import dataclass, field

DEFAULT_GAMMA = "https://gamma-api.polymarket.com"
DEFAULT_CLOB = "https://clob.polymarket.com"


def _as_list(v):
    """Gamma returns outcomes/outcomePrices/clobTokenIds as JSON-encoded
    strings on the live API but as native lists in fixtures. Accept both."""
    if isinstance(v, str):
        try:
            return json.loads(v)
        except (json.JSONDecodeError, ValueError):
            return []
    return v or []


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
    clob_token_ids: list = field(default_factory=list)  # parallel to outcomes

    def edge(self, predicted_prob: float, outcome: str) -> float:
        return predicted_prob - self.prices.get(outcome, 0.5)

    def token_id_for(self, outcome: str):
        """The CLOB token id for an outcome (what place_order needs). Matches
        by exact then case-insensitive outcome label. None if unknown."""
        if not self.clob_token_ids or len(self.clob_token_ids) != len(self.outcomes):
            return None
        for i, o in enumerate(self.outcomes):
            if o == outcome:
                return str(self.clob_token_ids[i])
        for i, o in enumerate(self.outcomes):
            if str(o).lower() == str(outcome).lower():
                return str(self.clob_token_ids[i])
        return None


class PolymarketCLOB:
    def __init__(self, proxy_url: str = None, gamma_url: str = DEFAULT_GAMMA,
                 clob_url: str = DEFAULT_CLOB, timeout: int = 15):
        self.proxy_url = proxy_url.rstrip("/") if proxy_url else None
        self.gamma_url = gamma_url.rstrip("/")
        self.clob_url = clob_url.rstrip("/")
        self.timeout = timeout

    def _fetch(self, url: str) -> object:
        req = urllib.request.Request(url, headers={"User-Agent": "polymarket-agent/0.1"})
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read())

    def _gamma(self, path: str) -> object:
        url = f"{self.proxy_url}/gamma{path}" if self.proxy_url else f"{self.gamma_url}{path}"
        return self._fetch(url)

    def scan_markets(self, limit: int = 300, offset: int = 0) -> list:
        data = self._gamma(f"/markets?limit={limit}&offset={offset}&active=true&closed=false&enableOrderBook=true")
        rows = data.get("data", data) if isinstance(data, dict) else data
        markets = []
        for m in rows:
            try:
                outcomes = _as_list(m["outcomes"])
                prices_raw = _as_list(m["outcomePrices"])
                prices = dict(zip(outcomes, [float(p) for p in prices_raw]))
                markets.append(Market(
                    id=str(m["id"]), question=m["question"], slug=m.get("slug", ""),
                    outcomes=outcomes, prices=prices,
                    liquidity=float(m.get("liquidity", 0) or 0),
                    volume_24h=float(m.get("volume24hr", 0) or 0),
                    end_date=m.get("endDate", ""), category=m.get("category", ""),
                    clob_token_ids=[str(t) for t in _as_list(m.get("clobTokenIds", []))],
                ))
            except (KeyError, ValueError, TypeError):
                continue
        return markets
