"""Real-time crypto sentiment scanning from FREE public APIs.

Sources:
- Reddit r/Stellar and r/cryptocurrency (public JSON API)
- CoinGecko community data (free, no key)

Writes composite sentiment to data/sentiment_shift.json.
Designed for cron every 5-10 min on resource-constrained Oracle Micro VM.
"""
from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

logger = logging.getLogger(__name__)

_UA = {"User-Agent": "xlm-bot/sentiment-monitor/1.0"}
_TIMEOUT = 8.0
_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_CACHE_PATH = _DATA_DIR / "sentiment_shift.json"
_STALE_AFTER_MIN = 30

# ── Keyword lists for Reddit title scoring ──────────────────────────
_BULL_KEYWORDS = [
    "moon", "pump", "bullish", "breakout", "buy", "ath", "rally",
    "surge", "soar", "gain", "upside", "accumulate", "launch", "green",
]
_BEAR_KEYWORDS = [
    "dump", "crash", "bearish", "sell", "fear", "scam", "rug",
    "plunge", "tank", "drop", "red", "liquidat", "panic", "decline",
]
_BULL_RE = re.compile("|".join(_BULL_KEYWORDS), re.IGNORECASE)
_BEAR_RE = re.compile("|".join(_BEAR_KEYWORDS), re.IGNORECASE)


def _to_float(v: Any, default: float | None = None) -> float | None:
    try:
        return float(v)
    except Exception:
        return default


def _read_cache() -> dict | None:
    try:
        if _CACHE_PATH.exists():
            data = json.loads(_CACHE_PATH.read_text())
            return data if isinstance(data, dict) else None
    except Exception:
        pass
    return None


def _save_cache(payload: dict) -> None:
    try:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        tmp = _CACHE_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
        tmp.replace(_CACHE_PATH)
    except Exception as exc:
        logger.warning("sentiment_monitor: cache write failed: %s", exc)


# ── Reddit sentiment ────────────────────────────────────────────────

def _fetch_reddit_sub(subreddit: str, limit: int = 25) -> list[str]:
    """Fetch hot post titles from a subreddit via public JSON API."""
    url = f"https://www.reddit.com/r/{subreddit}/hot.json"
    try:
        resp = requests.get(
            url,
            params={"limit": limit, "raw_json": 1},
            headers={**_UA, "Accept": "application/json"},
            timeout=_TIMEOUT,
        )
        if resp.status_code != 200:
            logger.debug("reddit %s returned %d", subreddit, resp.status_code)
            return []
        data = resp.json()
        children = data.get("data", {}).get("children", [])
        titles = []
        for child in children:
            d = child.get("data", {})
            title = str(d.get("title") or "").strip()
            if title and not d.get("stickied"):
                titles.append(title)
        return titles
    except Exception as exc:
        logger.debug("reddit %s fetch failed: %s", subreddit, exc)
        return []


def _score_titles(titles: list[str]) -> dict:
    """Count bull/bear keyword hits across a list of titles."""
    bull_count = 0
    bear_count = 0
    hot_topics: list[str] = []
    for title in titles:
        bulls = len(_BULL_RE.findall(title))
        bears = len(_BEAR_RE.findall(title))
        bull_count += bulls
        bear_count += bears
        if bulls or bears:
            hot_topics.append(title[:120])
    total = bull_count + bear_count
    ratio = bull_count / total if total > 0 else 0.5
    return {
        "bull_count": bull_count,
        "bear_count": bear_count,
        "ratio": round(ratio, 3),
        "hot_topics": hot_topics[:5],
        "posts_scanned": len(titles),
    }


def _poll_reddit_sentiment() -> dict:
    """Poll r/Stellar and r/cryptocurrency, return combined score."""
    stellar_titles = _fetch_reddit_sub("Stellar", limit=25)
    crypto_titles = _fetch_reddit_sub("cryptocurrency", limit=25)

    stellar_score = _score_titles(stellar_titles)
    crypto_score = _score_titles(crypto_titles)

    # Combine: weight Stellar 60%, general crypto 40%
    s_ratio = stellar_score["ratio"]
    c_ratio = crypto_score["ratio"]
    combined_ratio = (s_ratio * 0.6 + c_ratio * 0.4) if (stellar_titles or crypto_titles) else 0.5

    all_topics = stellar_score["hot_topics"] + crypto_score["hot_topics"]

    return {
        "combined_ratio": round(combined_ratio, 3),
        "stellar": stellar_score,
        "cryptocurrency": crypto_score,
        "hot_topics": all_topics[:5],
        "available": bool(stellar_titles or crypto_titles),
    }


# ── CoinGecko social data ──────────────────────────────────────────

def _poll_coingecko_social() -> dict:
    """Fetch CoinGecko community/social data for Stellar (free, no key)."""
    url = "https://api.coingecko.com/api/v3/coins/stellar"
    try:
        resp = requests.get(
            url,
            params={"localization": "false", "tickers": "false",
                    "market_data": "false", "community_data": "true",
                    "developer_data": "false", "sparkline": "false"},
            headers=_UA,
            timeout=_TIMEOUT,
        )
        if resp.status_code != 200:
            logger.debug("coingecko social returned %d", resp.status_code)
            return {"available": False}

        data = resp.json()
        community = data.get("community_data") or {}
        sentiment = data.get("sentiment_votes_up_percentage")

        return {
            "community_score": _to_float(data.get("community_score"), 0.0),
            "developer_score": _to_float(data.get("developer_score"), 0.0),
            "public_interest_score": _to_float(data.get("public_interest_score"), 0.0),
            "twitter_followers": community.get("twitter_followers"),
            "reddit_subscribers": community.get("reddit_subscribers"),
            "reddit_active_accounts": community.get("reddit_accounts_active_48h"),
            "sentiment_votes_up_pct": _to_float(sentiment, 50.0),
            "available": True,
        }
    except Exception as exc:
        logger.debug("coingecko social fetch failed: %s", exc)
        return {"available": False}


# ── Composite score ─────────────────────────────────────────────────

def _compute_composite(reddit: dict, coingecko: dict) -> dict:
    """Weighted composite: reddit 60%, coingecko 40%. Score 0-100."""
    now = datetime.now(timezone.utc)

    # Reddit ratio is 0-1 (bull fraction), map to 0-100
    reddit_score = reddit.get("combined_ratio", 0.5) * 100.0

    # CoinGecko sentiment_votes_up_pct is already 0-100 scale
    cg_score = float(coingecko.get("sentiment_votes_up_pct", 50.0) or 50.0)

    reddit_available = reddit.get("available", False)
    cg_available = coingecko.get("available", False)

    if reddit_available and cg_available:
        score = reddit_score * 0.6 + cg_score * 0.4
    elif reddit_available:
        score = reddit_score
    elif cg_available:
        score = cg_score
    else:
        score = 50.0  # neutral fallback

    score = round(max(0.0, min(100.0, score)), 1)

    if score >= 65:
        direction = "bullish"
    elif score <= 35:
        direction = "bearish"
    else:
        direction = "neutral"

    # Momentum: compare to previous cache
    momentum_pct = 0.0
    prev = _read_cache()
    if prev and isinstance(prev.get("score"), (int, float)):
        prev_score = float(prev["score"])
        if prev_score > 0:
            momentum_pct = round(((score - prev_score) / prev_score) * 100.0, 1)

    return {
        "score": score,
        "direction": direction,
        "momentum_pct": momentum_pct,
        "hot_topics": reddit.get("hot_topics", [])[:3],
        "sources": {
            "reddit": {
                "available": reddit_available,
                "ratio": reddit.get("combined_ratio", 0.5),
                "posts_scanned": reddit.get("stellar", {}).get("posts_scanned", 0)
                    + reddit.get("cryptocurrency", {}).get("posts_scanned", 0),
            },
            "coingecko": {
                "available": cg_available,
                "community_score": coingecko.get("community_score"),
                "sentiment_up_pct": coingecko.get("sentiment_votes_up_pct"),
            },
        },
        "timestamp": now.isoformat(),
        "stale_after_minutes": _STALE_AFTER_MIN,
    }


# ── Public API ──────────────────────────────────────────────────────

def fetch_sentiment(symbol: str = "XLM") -> dict:
    """Poll all sentiment sources, return composite score.

    Returns dict with keys: score, direction, momentum_pct, hot_topics,
    sources, timestamp, stale_after_minutes.
    """
    logger.info("sentiment_monitor: fetching sentiment for %s", symbol)
    t0 = time.monotonic()

    reddit = _poll_reddit_sentiment()
    coingecko = _poll_coingecko_social()
    composite = _compute_composite(reddit, coingecko)

    _save_cache(composite)

    elapsed = time.monotonic() - t0
    logger.info(
        "sentiment_monitor: score=%.1f direction=%s elapsed=%.1fs",
        composite["score"], composite["direction"], elapsed,
    )
    return composite


def get_latest_sentiment() -> dict | None:
    """Non-blocking read of latest cached sentiment."""
    cached = _read_cache()
    if cached and isinstance(cached.get("score"), (int, float)):
        return cached
    return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    result = fetch_sentiment()
    print(json.dumps(result, indent=2))
