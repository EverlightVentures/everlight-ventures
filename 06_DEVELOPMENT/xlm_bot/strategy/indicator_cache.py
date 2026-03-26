"""Indicator Cache - Skip redundant computation on same candle."""
from __future__ import annotations
from typing import Any

_CACHE = {}
_MAX_ENTRIES = 200


def cache_key(timeframe: str, last_ts: str, indicator: str) -> str:
    return f"{timeframe}:{last_ts}:{indicator}"


def get_cached(key: str) -> Any:
    return _CACHE.get(key)


def set_cached(key: str, value: Any) -> None:
    if len(_CACHE) > _MAX_ENTRIES:
        keys = list(_CACHE.keys())
        for k in keys[:len(keys)//2]:
            del _CACHE[k]
    _CACHE[key] = value


def invalidate(timeframe: str = None) -> None:
    if timeframe is None:
        _CACHE.clear()
        return
    prefix = f"{timeframe}:"
    to_delete = [k for k in _CACHE if k.startswith(prefix)]
    for k in to_delete:
        del _CACHE[k]
