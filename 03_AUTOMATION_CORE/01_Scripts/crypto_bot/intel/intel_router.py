#!/usr/bin/env python3
"""
Intel router: public derivatives + chart proxies, normalized output.
"""

from __future__ import annotations

import time
from typing import Dict, List, Optional

from intel.public_derivs import fetch_public_derivs
from intel.chart_proxies import forced_move_proxy, magnet_proxy

_CACHE: Dict[str, dict] = {}
_CACHE_TTL_SECONDS = 60


def _cache_get(key: str) -> Optional[dict]:
    entry = _CACHE.get(key)
    if not entry:
        return None
    if time.time() - entry["timestamp"] > _CACHE_TTL_SECONDS:
        return None
    return entry["payload"]


def _cache_set(key: str, payload: dict) -> None:
    _CACHE[key] = {"timestamp": time.time(), "payload": payload}


def get_liq_event_intel(symbol: str, timeframe: str, candles: List[dict]) -> dict:
    cache_key = f"liq:{symbol}:{timeframe}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    public = fetch_public_derivs(symbol, timeframe)
    proxy = forced_move_proxy(candles)

    liq_event_score = proxy.get("liq_event_score")
    liq_bias = proxy.get("liq_bias", "NONE")
    notes = []

    if public.get("ok"):
        # Simple blend: boost score if OI spikes with price move
        oi_delta = public.get("oi_delta_pct")
        price_chg = public.get("price_change_5m_pct")
        if oi_delta is not None and price_chg is not None:
            bump = min(0.2, max(0.0, abs(oi_delta) * 5))
            liq_event_score = min(1.0, (liq_event_score or 0) + bump)
            notes.append("OI delta applied")
        notes.extend(public.get("notes", []))

    payload = {
        "ok": bool(proxy.get("ok") or public.get("ok")),
        "source": "mixed" if public.get("ok") else "proxy",
        "timestamp": time.time(),
        "liq_event_score": liq_event_score,
        "liq_bias": liq_bias,
        "notes": notes,
    }
    _cache_set(cache_key, payload)
    return payload


def get_magnet_intel(symbol: str, timeframe: str, candles: List[dict]) -> dict:
    cache_key = f"magnet:{symbol}:{timeframe}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    proxy = magnet_proxy(candles)
    payload = {
        "ok": proxy.get("ok", False),
        "source": "proxy",
        "timestamp": time.time(),
        "magnet_levels": proxy.get("magnet_levels", []),
        "nearest_magnet_distance_pct": proxy.get("nearest_magnet_distance_pct"),
        "notes": proxy.get("notes", []),
    }
    _cache_set(cache_key, payload)
    return payload
