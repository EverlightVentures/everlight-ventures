#!/usr/bin/env python3
"""
Universe Manager
Builds a dynamic trading universe from CoinGecko rankings and Coinbase availability.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional

try:
    import requests
except ImportError:
    print("Install requests: pip install requests")
    raise

logger = logging.getLogger(__name__)


class UniverseManager:
    def __init__(self, config: dict, api=None):
        self.api = api
        self.config = config.get("universe", {})
        self._cache_pairs: List[str] = []
        self._cache_time: Optional[datetime] = None
        self._products_cache = None
        self._products_cache_time: Optional[datetime] = None
        self._fallback_pairs = ["BTC-USD", "ETH-USD", "SOL-USD", "AVAX-USD"]
        self._last_failure_logged: Optional[datetime] = None

    def get_pairs(self) -> List[str]:
        if not self.config.get("enabled", False):
            return []

        refresh_minutes = self.config.get("refresh_minutes", 60)
        if self._cache_time and (datetime.now() - self._cache_time) < timedelta(minutes=refresh_minutes):
            return self._cache_pairs

        include_only = bool(self.config.get("include_only", False))
        include = [s.upper() for s in self.config.get("include_symbols", [])]
        include_pairs = [f"{sym}-{self.config.get('quote_currency', 'USD').upper()}" for sym in include]

        pairs = self._build_universe()
        if pairs:
            self._cache_pairs = pairs
            self._cache_time = datetime.now()
        else:
            # Use fallback pairs and cache for 5 minutes to avoid spamming
            if not self._cache_time or (datetime.now() - self._cache_time) > timedelta(minutes=5):
                if include_only and include_pairs:
                    self._cache_pairs = include_pairs
                    logger.info(f"Using include-only pairs: {include_pairs}")
                else:
                    self._cache_pairs = self._fallback_pairs
                self._cache_time = datetime.now()
                if not include_only:
                    logger.info(f"Using fallback pairs: {self._fallback_pairs}")
        return self._cache_pairs

    def _build_universe(self) -> List[str]:
        top_n_mc = int(self.config.get("top_n_marketcap", 5))
        top_n_vol = int(self.config.get("top_n_volume", 5))
        mode = self.config.get("mode", "union")
        quote = self.config.get("quote_currency", "USD").upper()
        cfm_only = self.config.get("cfm_only", False)
        exclude = set(s.upper() for s in self.config.get("exclude_symbols", []))
        include = set(s.upper() for s in self.config.get("include_symbols", []))
        include_only = bool(self.config.get("include_only", False))

        available_pairs = self._get_coinbase_pairs(quote)
        if not available_pairs:
            # Only log warning once per 5 minutes to avoid spam
            now = datetime.now()
            if not self._last_failure_logged or (now - self._last_failure_logged) > timedelta(minutes=5):
                logger.warning("UniverseManager: Coinbase API unavailable, using fallback pairs")
                self._last_failure_logged = now
            return []

        if cfm_only:
            cfm_pairs = self._get_cfm_pairs(quote)
            if cfm_pairs:
                available_pairs = [p for p in available_pairs if p in cfm_pairs]
            else:
                logger.warning("UniverseManager: No CFM-eligible pairs found; falling back to spot pairs")

        mc_list = self._fetch_top_by_marketcap(top_n_mc, quote)
        vol_list = self._fetch_top_by_volume(top_n_vol, quote)

        mc_pairs = [p for p in mc_list if p.split("-")[0] not in exclude and p in available_pairs]
        vol_pairs = [p for p in vol_list if p.split("-")[0] not in exclude and p in available_pairs]
        include_pairs = [f"{sym}-{quote}" for sym in include if f"{sym}-{quote}" in available_pairs]

        if include_only:
            pairs = sorted(set(include_pairs))
        elif mode == "intersection":
            pairs = sorted((set(mc_pairs) & set(vol_pairs)) | set(include_pairs))
        else:
            pairs = sorted(set(mc_pairs) | set(vol_pairs) | set(include_pairs))

        logger.info(f"UniverseManager: {mode} of top {top_n_mc} MC and top {top_n_vol} volume -> {pairs}")
        return pairs

    def _get_coinbase_pairs(self, quote: str) -> List[str]:
        # Cache products for 30 minutes
        if self._products_cache_time and (datetime.now() - self._products_cache_time) < timedelta(minutes=30):
            products = self._products_cache
        else:
            products = self.api.get_products() if self.api else None
            self._products_cache = products
            self._products_cache_time = datetime.now()

        if not products:
            # Fallback to public Coinbase Exchange products endpoint
            try:
                resp = requests.get("https://api.exchange.coinbase.com/products", timeout=10)
                if resp.status_code == 200:
                    products = resp.json()
            except Exception:
                products = None

        if not products:
            return []

        pairs = []
        for p in products:
            product_id = p.get("product_id") or p.get("id") or ""
            if not product_id:
                continue
            if product_id.endswith(f"-{quote}"):
                pairs.append(product_id)
        return pairs

    def _get_cfm_pairs(self, quote: str) -> List[str]:
        # Map CFM product prefixes to spot-style base symbols
        prefix_map = {
            "BIP": "BTC",
            "ETP": "ETH",
            "SLP": "SOL",
            "AVP": "AVAX",
            "DOP": "DOGE",
            "LNP": "LINK",
            "LCP": "LTC",
            "ADP": "ADA",
            "SHP": "SHIB",
            "HEP": "HBAR",
            "SUP": "SUI",
            "XLP": "XLM",
            "POP": "DOT",
            "XPP": "XRP",
        }

        products = self._products_cache
        if not products:
            products = self.api.get_products() if self.api else None
            self._products_cache = products
            self._products_cache_time = datetime.now()

        # Fallback immediately if products API failed
        if not products:
            # All major CFM perpetual pairs available on Coinbase
            fallback_cfm = [
                f"BTC-{quote}", f"ETH-{quote}", f"XRP-{quote}",
                f"SOL-{quote}", f"AVAX-{quote}", f"DOGE-{quote}",
                f"LINK-{quote}", f"LTC-{quote}", f"ADA-{quote}"
            ]
            logger.info(f"Products API unavailable, using fallback CFM pairs: {fallback_cfm}")
            return fallback_cfm

        pairs = set()
        for p in products:
            product_type = (p.get("product_type") or p.get("type") or "").upper()
            if "CFM" not in product_type and "FUTURE" not in product_type and "FUTURES" not in product_type:
                continue
            base = p.get("base_currency_id") or p.get("base_currency")
            quote_ccy = p.get("quote_currency_id") or p.get("quote_currency") or quote
            if not base:
                product_id = p.get("product_id") or p.get("id") or ""
                if product_id:
                    base = product_id.split("-")[0]
            # Map known CFM prefixes to spot-style symbols
            base = prefix_map.get(base, base)
            if base and quote_ccy:
                pairs.add(f"{base}-{quote_ccy}")

        return sorted(pairs) if pairs else [f"BTC-{quote}", f"ETH-{quote}"]

    def _fetch_top_by_marketcap(self, top_n: int, quote: str) -> List[str]:
        data = self._fetch_coingecko(order="market_cap_desc", per_page=max(50, top_n * 5), quote=quote)
        return self._pairs_from_coingecko(data, top_n, quote)

    def _fetch_top_by_volume(self, top_n: int, quote: str) -> List[str]:
        # Try volume-desc order first; fallback to local sort
        data = self._fetch_coingecko(order="volume_desc", per_page=250, quote=quote)
        if not data:
            data = self._fetch_coingecko(order="market_cap_desc", per_page=250, quote=quote)
            if data:
                data = sorted(data, key=lambda x: x.get("total_volume", 0), reverse=True)
        return self._pairs_from_coingecko(data, top_n, quote)

    def _fetch_coingecko(self, order: str, per_page: int, quote: str) -> List[dict]:
        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {
            "vs_currency": quote.lower(),
            "order": order,
            "per_page": per_page,
            "page": 1,
            "sparkline": "false"
        }
        try:
            resp = requests.get(url, params=params, timeout=15)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            logger.warning(f"CoinGecko fetch failed ({order}): {e}")
        return []

    def _pairs_from_coingecko(self, data: List[dict], top_n: int, quote: str) -> List[str]:
        pairs = []
        if not data:
            return pairs
        for coin in data:
            symbol = (coin.get("symbol") or "").upper()
            if not symbol:
                continue
            pairs.append(f"{symbol}-{quote}")
            if len(pairs) >= top_n:
                break
        return pairs
