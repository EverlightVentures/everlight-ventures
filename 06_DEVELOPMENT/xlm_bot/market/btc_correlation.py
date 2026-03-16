"""BTC correlation gate for XLM trading.

BTC drives altcoin moves. This module fetches a short window of BTC-USD
15m candles and computes short-term momentum. If BTC is moving strongly
against the proposed trade direction, penalize the score.

Uses the same public Coinbase API as XLM candles — no auth needed.
Caches result for 5 minutes to avoid hitting API every 30s cycle.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import pandas as pd
import requests

# Module-level cache: avoid re-fetching BTC data every bot cycle
_cache: dict = {"df": None, "ts": 0.0}
_CACHE_TTL_S = 300  # 5 minutes


@dataclass
class BTCSignal:
    """BTC momentum signal for XLM trade gating."""
    btc_momentum_pct: float = 0.0    # BTC price change over lookback
    btc_trend: str = "neutral"        # "bullish" | "bearish" | "neutral"
    btc_rsi: float = 50.0             # approximate RSI
    score_modifier: int = 0           # bonus/penalty to apply to v4 score
    reasons: list[str] = field(default_factory=list)
    stale: bool = False               # True if using cached/failed data


def fetch_btc_candles(lookback_bars: int = 20) -> pd.DataFrame:
    """Fetch recent BTC-USD 15m candles from Coinbase public API.

    Returns DataFrame with columns: timestamp, open, high, low, close, volume.
    Uses module cache to avoid hammering API.
    """
    now = time.time()
    if _cache["df"] is not None and (now - _cache["ts"]) < _CACHE_TTL_S:
        return _cache["df"]

    end = datetime.now(timezone.utc)
    start = end - timedelta(minutes=15 * (lookback_bars + 5))
    url = "https://api.exchange.coinbase.com/products/BTC-USD/candles"
    params = {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "granularity": 900,  # 15 minutes
    }
    try:
        resp = requests.get(url, params=params, timeout=4)
        if resp.status_code != 200:
            return _cache.get("df") or pd.DataFrame()
        data = resp.json()
        if not data:
            return _cache.get("df") or pd.DataFrame()
        df = pd.DataFrame(data, columns=["time", "low", "high", "open", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["time"], unit="s", utc=True)
        df = df.sort_values("timestamp").reset_index(drop=True)
        df = df[["timestamp", "open", "high", "low", "close", "volume"]]
        for c in ["open", "high", "low", "close", "volume"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        _cache["df"] = df
        _cache["ts"] = now
        return df
    except Exception:
        return _cache.get("df") or pd.DataFrame()


def compute_btc_signal(
    direction: str,
    config: dict | None = None,
) -> BTCSignal:
    """Compute BTC momentum signal and score modifier.

    Args:
        direction: proposed XLM trade direction ("long" or "short")
        config: optional config overrides

    Returns:
        BTCSignal with score_modifier to add to v4 score.
    """
    cfg = config or {}
    lookback = int(cfg.get("lookback_bars", 8) or 8)
    strong_move_pct = float(cfg.get("strong_move_pct", 0.005) or 0.005)  # 0.5%
    bonus_pts = int(cfg.get("bonus_pts", 5) or 5)
    penalty_pts = int(cfg.get("penalty_pts", 5) or 5)

    result = BTCSignal()
    df = fetch_btc_candles(lookback + 5)

    if df.empty or len(df) < lookback:
        result.stale = True
        result.reasons.append("btc_data_unavailable")
        return result

    # Price change over lookback period
    recent = df.tail(lookback)
    open_price = float(recent.iloc[0]["open"])
    close_price = float(recent.iloc[-1]["close"])
    if open_price <= 0:
        result.stale = True
        return result

    pct_change = (close_price - open_price) / open_price
    result.btc_momentum_pct = round(pct_change, 6)

    # Classify BTC trend
    if pct_change > strong_move_pct:
        result.btc_trend = "bullish"
    elif pct_change < -strong_move_pct:
        result.btc_trend = "bearish"
    else:
        result.btc_trend = "neutral"

    # Approximate RSI from recent closes (simple method)
    closes = recent["close"].values
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [d for d in deltas if d > 0]
    losses = [-d for d in deltas if d < 0]
    avg_gain = sum(gains) / len(deltas) if deltas else 0
    avg_loss = sum(losses) / len(deltas) if deltas else 0
    if avg_loss > 0:
        rs = avg_gain / avg_loss
        result.btc_rsi = round(100 - (100 / (1 + rs)), 1)
    else:
        result.btc_rsi = 100.0 if avg_gain > 0 else 50.0

    # Score modifier: reward alignment, penalize divergence
    d = direction.lower().strip()
    if result.btc_trend == "bullish":
        if d == "long":
            result.score_modifier = bonus_pts
            result.reasons.append(f"btc_aligned_bullish ({pct_change*100:+.2f}%)")
        elif d == "short":
            result.score_modifier = -penalty_pts
            result.reasons.append(f"btc_against_short ({pct_change*100:+.2f}% bullish)")
    elif result.btc_trend == "bearish":
        if d == "short":
            result.score_modifier = bonus_pts
            result.reasons.append(f"btc_aligned_bearish ({pct_change*100:+.2f}%)")
        elif d == "long":
            result.score_modifier = -penalty_pts
            result.reasons.append(f"btc_against_long ({pct_change*100:+.2f}% bearish)")
    else:
        result.reasons.append(f"btc_neutral ({pct_change*100:+.2f}%)")

    return result
