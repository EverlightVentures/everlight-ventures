"""Crypto Fear & Greed sentiment gate.

Fetches the Crypto Fear & Greed Index (alternative.me) and provides
entry filtering based on market sentiment. Prevents toxic trades
during extreme fear/panic by blocking or reducing entries.

Cache: 15 min on-disk to keep bot cycles fast.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

_UA = {"User-Agent": "xlm-bot/sentiment-gate"}
_CACHE_FILE = Path(__file__).resolve().parent.parent / "data" / "sentiment_cache.json"
_CACHE_TTL_S = 900  # 15 minutes


def _read_cache() -> dict:
    try:
        if _CACHE_FILE.exists():
            out = json.loads(_CACHE_FILE.read_text())
            return out if isinstance(out, dict) else {}
    except Exception:
        pass
    return {}


def _write_cache(payload: dict) -> None:
    try:
        _CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = _CACHE_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, separators=(",", ":")))
        tmp.replace(_CACHE_FILE)
    except Exception:
        pass


def _fetch_fng() -> dict | None:
    """Fetch current Fear & Greed Index from alternative.me (free, no auth)."""
    try:
        r = requests.get(
            "https://api.alternative.me/fng/",
            headers=_UA,
            timeout=4.0,
        )
        if r.status_code != 200:
            return None
        data = r.json()
        if not isinstance(data, dict):
            return None
        entries = data.get("data", [])
        if not entries or not isinstance(entries[0], dict):
            return None
        entry = entries[0]
        return {
            "value": int(entry.get("value", 50)),
            "classification": str(entry.get("value_classification", "Neutral")),
            "timestamp": str(entry.get("timestamp", "")),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception:
        return None


def get_sentiment() -> dict:
    """Get current sentiment with caching.

    Returns dict with keys:
        score: int 0-100 (0=extreme fear, 100=extreme greed)
        classification: str (e.g. "Extreme Fear", "Fear", "Neutral", "Greed", "Extreme Greed")
        stale: bool -- True if cache is expired and fresh fetch failed
        age_min: float -- minutes since last successful fetch
    """
    cache = _read_cache()
    now_ts = time.time()
    cache_ts = float(cache.get("_ts", 0))
    age_s = now_ts - cache_ts

    if age_s < _CACHE_TTL_S and cache.get("score") is not None:
        return {
            "score": int(cache["score"]),
            "classification": str(cache.get("classification", "Unknown")),
            "stale": False,
            "age_min": round(age_s / 60, 1),
        }

    # Fetch fresh
    fresh = _fetch_fng()
    if fresh:
        payload = {
            "score": fresh["value"],
            "classification": fresh["classification"],
            "_ts": now_ts,
            "_fetched": fresh["fetched_at"],
        }
        _write_cache(payload)
        return {
            "score": fresh["value"],
            "classification": fresh["classification"],
            "stale": False,
            "age_min": 0.0,
        }

    # Fetch failed -- use stale cache if available
    if cache.get("score") is not None:
        return {
            "score": int(cache["score"]),
            "classification": str(cache.get("classification", "Unknown")),
            "stale": True,
            "age_min": round(age_s / 60, 1),
        }

    # No cache at all -- return neutral (don't block trades on API failure)
    return {
        "score": 50,
        "classification": "Neutral (no data)",
        "stale": True,
        "age_min": -1,
    }


def evaluate_sentiment_gate(
    sentiment: dict,
    direction: str,
    config: dict,
) -> dict:
    """Evaluate whether sentiment allows entry.

    Args:
        sentiment: output from get_sentiment()
        direction: "long" or "short"
        config: the sentiment_gate config section

    Returns dict:
        allowed: bool
        reason: str
        size_mult: float (1.0 = full size, 0.5 = half, etc.)
        score: int
        classification: str
    """
    score = int(sentiment.get("score", 50))
    classification = str(sentiment.get("classification", "Unknown"))

    # Config thresholds
    block_all_below = int(config.get("block_all_below", 10))
    block_longs_below = int(config.get("block_longs_below", 20))
    reduce_size_below = int(config.get("reduce_size_below", 30))
    fear_size_mult = float(config.get("fear_size_mult", 0.5))
    enabled = bool(config.get("enabled", True))

    result: dict[str, Any] = {
        "allowed": True,
        "reason": "sentiment_ok",
        "size_mult": 1.0,
        "score": score,
        "classification": classification,
    }

    if not enabled:
        result["reason"] = "sentiment_gate_disabled"
        return result

    # CATASTROPHIC: block ALL entries
    if score < block_all_below:
        result["allowed"] = False
        result["reason"] = f"sentiment_catastrophic_{score}"
        result["size_mult"] = 0.0
        return result

    # EXTREME FEAR: block longs, allow shorts
    if score < block_longs_below and direction == "long":
        result["allowed"] = False
        result["reason"] = f"sentiment_fear_blocks_long_{score}"
        result["size_mult"] = 0.0
        return result

    # FEAR: reduce position size for all trades
    if score < reduce_size_below:
        result["size_mult"] = fear_size_mult
        result["reason"] = f"sentiment_fear_reduced_size_{score}"
        return result

    return result
