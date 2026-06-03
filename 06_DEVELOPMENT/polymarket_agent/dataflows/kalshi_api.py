"""Kalshi market-data layer (PUBLIC endpoints, no auth) -- replaces polymarket_clob.py.

Kalshi is a CFTC-regulated US exchange: legal for US persons, no geoblock (the
whole reason we left Polymarket). Binary event contracts priced 1c-99c that settle
to $1 (Yes) or $0 (No) -- same structure as Polymarket, so the predictor/risk/
calibration brain ports unchanged. This module only READS (markets, prices,
orderbooks); signed order placement lives in execution/kalshi_exec.py (needs an
API key). Prices here are CENTS (1..99); .prob() converts to 0..1.

Docs: https://docs.kalshi.com  | base host confirmed live 2026-06-02.
"""
import json
import time
import urllib.request
import urllib.parse
from dataclasses import dataclass

BASE = "https://api.elections.kalshi.com/trade-api/v2"
# crypto range-market series (BTC/ETH price-range buckets at multiple frequencies)
CRYPTO_SERIES = {"BTC": "KXBTC", "ETH": "KXETH"}


def _get(path, params=None, attempts=3):
    """GET JSON with retries (transient TLS/timeout from the phone proot)."""
    url = f"{BASE}{path}"
    if params:
        url += "?" + urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    last = None
    for i in range(attempts):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ev-kalshi/1.0"})
            with urllib.request.urlopen(req, timeout=15) as r:
                return json.loads(r.read())
        except Exception as e:
            last = e
            time.sleep(0.6 * (i + 1))
    raise last


@dataclass
class KalshiMarket:
    ticker: str
    title: str
    status: str
    yes_bid: int        # cents (1..99) or None
    yes_ask: int
    no_bid: int
    no_ask: int
    volume: int
    close_time: str

    @staticmethod
    def from_api(m: dict) -> "KalshiMarket":
        return KalshiMarket(
            ticker=m.get("ticker", ""), title=m.get("title", ""),
            status=m.get("status", ""), yes_bid=m.get("yes_bid"), yes_ask=m.get("yes_ask"),
            no_bid=m.get("no_bid"), no_ask=m.get("no_ask"),
            volume=m.get("volume") or 0, close_time=m.get("close_time", ""),
        )

    def prob(self, side="yes"):
        """Mid-price as a 0..1 probability (None if no two-sided market)."""
        bid, ask = (self.yes_bid, self.yes_ask) if side == "yes" else (self.no_bid, self.no_ask)
        if bid is None or ask is None:
            return None
        return (bid + ask) / 200.0   # cents midpoint / 100


def get_markets(series_ticker=None, status="open", limit=100, cursor=None) -> list:
    """List markets (optionally one series). Public, no auth."""
    d = _get("/markets", {"series_ticker": series_ticker, "status": status,
                          "limit": limit, "cursor": cursor})
    return [KalshiMarket.from_api(m) for m in d.get("markets", [])]


def get_market(ticker: str) -> KalshiMarket | None:
    d = _get(f"/markets/{ticker}")
    m = d.get("market")
    return KalshiMarket.from_api(m) if m else None


def get_orderbook(ticker: str) -> dict:
    """Raw orderbook: {'yes': [[price_cents, size], ...], 'no': [...]}."""
    return _get(f"/markets/{ticker}/orderbook").get("orderbook", {})


def find_crypto_markets(asset="BTC", status="open", limit=50) -> list:
    """The live BTC/ETH price-range markets (15-min / hourly / daily buckets).
    These are the fast-resolution lane that replaces Polymarket's 5-min candles."""
    series = CRYPTO_SERIES.get(asset.upper())
    if not series:
        return []
    return get_markets(series_ticker=series, status=status, limit=limit)
