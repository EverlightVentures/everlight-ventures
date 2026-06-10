#!/usr/bin/env python3
"""
Public derivatives intel (no API keys).

Uses public derivatives endpoints as a proxy for liquidation pressure.
Currently uses Binance USD-M futures as a macro proxy.
"""

from __future__ import annotations

import time
import logging
from typing import Dict, Optional

import requests

logger = logging.getLogger(__name__)

_CACHE: Dict[str, dict] = {}
_CACHE_TTL_SECONDS = 60

_BINANCE_FAPI = "https://fapi.binance.com"

_SYMBOL_MAP = {
    "BTC-USD": "BTCUSDT",
    "ETH-USD": "ETHUSDT",
    "SOL-USD": "SOLUSDT",
    "AVAX-USD": "AVAXUSDT",
    "XRP-USD": "XRPUSDT",
    "ADA-USD": "ADAUSDT",
    "DOGE-USD": "DOGEUSDT",
    "LINK-USD": "LINKUSDT",
    "LTC-USD": "LTCUSDT",
    "BCH-USD": "BCHUSDT",
}


def _map_symbol(symbol: str) -> Optional[str]:
    return _SYMBOL_MAP.get(symbol)


def _cache_get(key: str) -> Optional[dict]:
    entry = _CACHE.get(key)
    if not entry:
        return None
    if time.time() - entry["timestamp"] > _CACHE_TTL_SECONDS:
        return None
    return entry


def _cache_set(key: str, payload: dict) -> None:
    _CACHE[key] = {"timestamp": time.time(), "payload": payload}


def fetch_public_derivs(symbol: str, timeframe: str = "1h") -> dict:
    """
    Fetch public derivatives context (OI, funding, volume/price change).

    Returns normalized dict:
      ok, source, timestamp, oi_now, oi_prev, oi_delta_pct,
      funding_rate_now, vol_5m, price_change_5m_pct, notes[]
    """
    mapped = _map_symbol(symbol)
    if not mapped:
        return {
            "ok": False,
            "source": "public",
            "timestamp": time.time(),
            "oi_now": None,
            "oi_prev": None,
            "oi_delta_pct": None,
            "funding_rate_now": None,
            "vol_5m": None,
            "price_change_5m_pct": None,
            "notes": [f"No public symbol mapping for {symbol}"],
        }

    cache_key = f"{mapped}:{timeframe}"
    cached = _cache_get(cache_key)
    if cached:
        return cached["payload"]

    notes = [f"OI/funding proxy from Binance futures for {mapped}"]
    ok = True
    oi_now = None
    oi_prev = None
    oi_delta_pct = None
    funding_rate_now = None
    vol_5m = None
    price_change_5m_pct = None

    try:
        oi_resp = requests.get(
            f"{_BINANCE_FAPI}/fapi/v1/openInterest",
            params={"symbol": mapped},
            timeout=10,
        )
        if oi_resp.status_code == 200:
            oi_now = float(oi_resp.json().get("openInterest", 0) or 0)
        else:
            ok = False
            notes.append(f"OI HTTP {oi_resp.status_code}")
    except Exception as e:
        ok = False
        notes.append(f"OI error: {e}")

    try:
        oi_hist = requests.get(
            f"{_BINANCE_FAPI}/fapi/v1/openInterestHist",
            params={"symbol": mapped, "period": "5m", "limit": 2},
            timeout=10,
        )
        if oi_hist.status_code == 200:
            data = oi_hist.json()
            if isinstance(data, list) and len(data) >= 2:
                oi_prev = float(data[-2].get("sumOpenInterest", 0) or 0)
        else:
            notes.append(f"OI hist HTTP {oi_hist.status_code}")
    except Exception as e:
        notes.append(f"OI hist error: {e}")

    if oi_now is not None and oi_prev:
        try:
            oi_delta_pct = (oi_now - oi_prev) / max(oi_prev, 1e-9)
        except Exception:
            oi_delta_pct = None

    try:
        fr = requests.get(
            f"{_BINANCE_FAPI}/fapi/v1/fundingRate",
            params={"symbol": mapped, "limit": 1},
            timeout=10,
        )
        if fr.status_code == 200:
            data = fr.json()
            if isinstance(data, list) and data:
                funding_rate_now = float(data[0].get("fundingRate", 0) or 0)
        else:
            notes.append(f"Funding HTTP {fr.status_code}")
    except Exception as e:
        notes.append(f"Funding error: {e}")

    try:
        k = requests.get(
            f"{_BINANCE_FAPI}/fapi/v1/klines",
            params={"symbol": mapped, "interval": "5m", "limit": 2},
            timeout=10,
        )
        if k.status_code == 200:
            data = k.json()
            if isinstance(data, list) and len(data) >= 2:
                prev = data[-2]
                last = data[-1]
                prev_close = float(prev[4])
                last_close = float(last[4])
                vol_5m = float(last[5])
                price_change_5m_pct = (last_close - prev_close) / max(prev_close, 1e-9) * 100
        else:
            notes.append(f"Klines HTTP {k.status_code}")
    except Exception as e:
        notes.append(f"Klines error: {e}")

    payload = {
        "ok": ok,
        "source": "public",
        "timestamp": time.time(),
        "oi_now": oi_now,
        "oi_prev": oi_prev,
        "oi_delta_pct": oi_delta_pct,
        "funding_rate_now": funding_rate_now,
        "vol_5m": vol_5m,
        "price_change_5m_pct": price_change_5m_pct,
        "notes": notes,
    }
    _cache_set(cache_key, payload)
    return payload
