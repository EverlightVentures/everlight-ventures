"""Perplexity Context Poller - Macro technical context for the unified scorer.

Computes the same data as the Perplexity watchlist analyzer on the phone:
  - RSI(14) on daily candles
  - Fibonacci levels (90-day swing high/low)
  - Volume ratio (current vs 20-day avg)
  - Breakout proximity (distance to 90-day range edges)
  - Momentum bias (LEAN_BULLISH / LEAN_BEARISH / NEUTRAL)
  - Crypto sentiment label

Writes to data/perplexity_context.json for the unified scorer to consume.
Designed to run hourly via cron on Oracle.

Usage:
    python perplexity_poller.py              # normal run
    python perplexity_poller.py --force      # ignore cache TTL
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

# --- Paths ---
_ROOT = Path(__file__).parent
_DATA_DIR = _ROOT / "data"
_OUTPUT = _DATA_DIR / "perplexity_context.json"
_CANDLE_CACHE = _DATA_DIR / "xlm_30d_candles.json"
_MARKET_INTEL = _DATA_DIR / "market_intel_cache.json"
_STATE = _DATA_DIR / "state.json"
_LOG = _DATA_DIR / "perplexity_integration_log.json"
_CACHE_TTL_SEC = 3300  # 55 min (runs hourly, 5 min buffer)

# --- Fib levels ---
FIB_LEVELS = [0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0]
FIB_LABELS = ["0% (Swing Low)", "23.6%", "38.2%", "50%", "61.8%", "78.6%", "100% (Swing High)"]


def _read_json(path: Path) -> dict | None:
    try:
        if path.exists():
            return json.loads(path.read_text())
    except Exception:
        pass
    return None


def _write_json(path: Path, data: dict) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    tmp.replace(path)


def _is_fresh() -> bool:
    """Check if output file is still fresh (within TTL)."""
    try:
        if _OUTPUT.exists():
            data = json.loads(_OUTPUT.read_text())
            updated = data.get("updated_at", "")
            if updated:
                ts = datetime.fromisoformat(updated)
                age = (datetime.now(timezone.utc) - ts).total_seconds()
                return age < _CACHE_TTL_SEC
    except Exception:
        pass
    return False


def _fetch_daily_candles() -> list[dict]:
    """Fetch 90 days of daily XLM-USD candles from Coinbase REST API."""
    try:
        from urllib.request import urlopen, Request
        import urllib.error

        end = datetime.now(timezone.utc)
        start = end - timedelta(days=90)
        # Coinbase candles endpoint: granularity 86400 = 1 day
        url = (
            f"https://api.exchange.coinbase.com/products/XLM-USD/candles"
            f"?start={start.isoformat()}&end={end.isoformat()}&granularity=86400"
        )
        req = Request(url, headers={"User-Agent": "xlm-bot/1.0"})
        resp = urlopen(req, timeout=15)
        raw = json.loads(resp.read())
        # Coinbase returns [[timestamp, low, high, open, close, volume], ...]
        # Sort by timestamp ascending
        candles = sorted(raw, key=lambda c: c[0])
        return [
            {
                "timestamp": c[0],
                "open": float(c[3]),
                "high": float(c[2]),
                "low": float(c[1]),
                "close": float(c[4]),
                "volume": float(c[5]),
            }
            for c in candles
        ]
    except Exception as e:
        print(f"[perplexity_poller] candle fetch error: {e}", file=sys.stderr)
        return []


def _compute_rsi(closes: list[float], period: int = 14) -> float:
    """RSI(14) from a list of close prices."""
    if len(closes) < period + 1:
        return 50.0
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    recent = deltas[-(period):]
    gains = [d for d in recent if d > 0]
    losses = [-d for d in recent if d < 0]
    avg_gain = sum(gains) / period if gains else 0.0001
    avg_loss = sum(losses) / period if losses else 0.0001
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)


def _compute_fib_levels(swing_high: float, swing_low: float) -> list[dict]:
    """Compute fib retrace levels from swing range."""
    spread = swing_high - swing_low
    levels = []
    for fib, label in zip(FIB_LEVELS, FIB_LABELS):
        price = swing_low + (spread * fib)
        levels.append({"level": label, "fib": fib, "price": round(price, 6)})
    return levels


def _find_nearest_fib(price: float, fib_levels: list[dict]) -> dict:
    """Find the fib level closest to current price."""
    nearest = min(fib_levels, key=lambda f: abs(f["price"] - price))
    distance_pct = abs(price - nearest["price"]) / price * 100 if price > 0 else 0
    return {
        "level": nearest["level"],
        "fib": nearest["fib"],
        "price": nearest["price"],
        "distance_pct": round(distance_pct, 2),
    }


def _compute_momentum_bias(rsi: float, price: float, swing_high: float, swing_low: float,
                           change_7d: float, volume_ratio: float) -> str:
    """Determine momentum bias from multiple signals."""
    bullish_signals = 0
    bearish_signals = 0

    # RSI
    if rsi > 55:
        bullish_signals += 1
    elif rsi < 45:
        bearish_signals += 1

    # Price position in range
    range_pos = (price - swing_low) / (swing_high - swing_low) if swing_high > swing_low else 0.5
    if range_pos > 0.6:
        bullish_signals += 1
    elif range_pos < 0.4:
        bearish_signals += 1

    # 7-day change
    if change_7d > 2:
        bullish_signals += 1
    elif change_7d < -2:
        bearish_signals += 1

    # Volume confirmation (high volume = trend confirmation)
    if volume_ratio > 1.3:
        if rsi > 50:
            bullish_signals += 1
        else:
            bearish_signals += 1

    if bullish_signals >= 3:
        return "LEAN_BULLISH"
    elif bearish_signals >= 3:
        return "LEAN_BEARISH"
    elif bullish_signals > bearish_signals:
        return "LEAN_BULLISH"
    elif bearish_signals > bullish_signals:
        return "LEAN_BEARISH"
    return "NEUTRAL"


def _compute_crypto_sentiment(rsi: float, change_24h: float, change_7d: float,
                               volume_ratio: float) -> str:
    """Simple sentiment label."""
    if change_24h > 3 and rsi > 60:
        return "BULLISH"
    if change_24h < -3 and rsi < 40:
        return "BEARISH"
    if abs(change_24h) < 1 and abs(change_7d) < 2:
        return "NEUTRAL"
    return "UNCERTAIN"


def _build_alerts(rsi: float, price: float, swing_high: float, swing_low: float,
                  volume_ratio: float, change_24h: float) -> list[str]:
    """Generate alert strings for notable conditions."""
    alerts = []
    if rsi <= 30:
        alerts.append(f"RSI OVERSOLD ({rsi:.1f})")
    elif rsi >= 70:
        alerts.append(f"RSI OVERBOUGHT ({rsi:.1f})")

    if price >= swing_high * 0.97:
        alerts.append("NEAR 90-DAY HIGH (within 3%)")
    elif price <= swing_low * 1.03:
        alerts.append("NEAR 90-DAY LOW (within 3%)")

    if volume_ratio >= 1.5:
        alerts.append(f"VOLUME SPIKE ({volume_ratio:.1f}x avg)")

    if abs(change_24h) >= 5:
        direction = "UP" if change_24h > 0 else "DOWN"
        alerts.append(f"BIG MOVE {direction} ({change_24h:+.1f}% 24h)")

    return alerts


def poll() -> dict[str, Any]:
    """Main poll function: fetch candles, compute context, write JSON."""
    now = datetime.now(timezone.utc)
    candles = _fetch_daily_candles()

    if not candles or len(candles) < 20:
        print(f"[perplexity_poller] insufficient candles ({len(candles)}), skipping", file=sys.stderr)
        # Return stale data if available
        existing = _read_json(_OUTPUT)
        if existing:
            existing["stale"] = True
            return existing
        return {"error": "no_data", "stale": True}

    closes = [c["close"] for c in candles]
    highs = [c["high"] for c in candles]
    lows = [c["low"] for c in candles]
    volumes = [c["volume"] for c in candles]
    price = closes[-1]

    # 90-day swing range
    swing_high = max(highs)
    swing_low = min(lows)

    # RSI(14) on daily closes
    rsi = _compute_rsi(closes, 14)

    # Fibonacci levels
    fib_levels = _compute_fib_levels(swing_high, swing_low)
    nearest_fib = _find_nearest_fib(price, fib_levels)

    # Volume ratio (last day vs 20-day average)
    vol_20d_avg = sum(volumes[-20:]) / min(20, len(volumes[-20:])) if volumes else 1
    volume_ratio = round(volumes[-1] / vol_20d_avg, 2) if vol_20d_avg > 0 else 1.0

    # Price changes
    change_24h = round((price - closes[-2]) / closes[-2] * 100, 2) if len(closes) >= 2 else 0
    change_7d = round((price - closes[-7]) / closes[-7] * 100, 2) if len(closes) >= 7 else 0
    change_30d = round((price - closes[-30]) / closes[-30] * 100, 2) if len(closes) >= 30 else 0

    # Breakout proximity
    to_high_pct = round((swing_high - price) / price * 100, 2)
    to_low_pct = round((price - swing_low) / price * 100, 2)
    range_position = round((price - swing_low) / (swing_high - swing_low), 4) if swing_high > swing_low else 0.5

    # Momentum bias and sentiment
    momentum_bias = _compute_momentum_bias(rsi, price, swing_high, swing_low, change_7d, volume_ratio)
    crypto_sentiment = _compute_crypto_sentiment(rsi, change_24h, change_7d, volume_ratio)

    # Alerts
    alerts = _build_alerts(rsi, price, swing_high, swing_low, volume_ratio, change_24h)

    context = {
        "updated_at": now.isoformat(),
        "price": round(price, 6),
        "price_change_24h_pct": change_24h,
        "price_change_7d_pct": change_7d,
        "price_change_30d_pct": change_30d,
        "momentum_bias": momentum_bias,
        "crypto_sentiment": crypto_sentiment,
        "rsi_14": rsi,
        "nearest_fib": nearest_fib["level"],
        "nearest_fib_price": nearest_fib["price"],
        "fib_distance_pct": nearest_fib["distance_pct"],
        "volume_ratio": volume_ratio,
        "breakout_proximity": {
            "to_90d_high_pct": to_high_pct,
            "to_90d_low_pct": to_low_pct,
            "range_position": range_position,
            "swing_high": swing_high,
            "swing_low": swing_low,
        },
        "fib_levels": fib_levels,
        "alerts": alerts,
        "stale": False,
        "candle_count": len(candles),
    }

    # Write output
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    _write_json(_OUTPUT, context)

    # Append to integration log feed_history (keep last 100)
    try:
        log = _read_json(_LOG) or {}
        history = log.get("feed_history", {}).get("entries", [])
        snapshot = {
            "ts": now.isoformat(),
            "price": price,
            "rsi": rsi,
            "bias": momentum_bias,
            "vol_ratio": volume_ratio,
            "range_pos": range_position,
            "alerts": len(alerts),
        }
        history.append(snapshot)
        history = history[-100:]  # keep last 100
        if "feed_history" not in log:
            log["feed_history"] = {"description": "Last 100 hourly snapshots", "entries": []}
        log["feed_history"]["entries"] = history
        _write_json(_LOG, log)
    except Exception:
        pass  # never let logging break the poller

    print(f"[perplexity_poller] OK | price=${price:.5f} | RSI={rsi} | bias={momentum_bias} | vol={volume_ratio}x | alerts={len(alerts)}")
    return context


def read_context() -> dict[str, Any] | None:
    """Non-blocking read of latest context (for bot import)."""
    data = _read_json(_OUTPUT)
    if not data:
        return None
    # Check staleness (>2 hours old)
    try:
        updated = datetime.fromisoformat(data["updated_at"])
        age_sec = (datetime.now(timezone.utc) - updated).total_seconds()
        data["stale"] = age_sec > 7200
    except Exception:
        data["stale"] = True
    return data


if __name__ == "__main__":
    force = "--force" in sys.argv
    if not force and _is_fresh():
        print("[perplexity_poller] context still fresh, skipping")
        sys.exit(0)
    result = poll()
    if result.get("error"):
        print(f"[perplexity_poller] FAILED: {result.get('error')}", file=sys.stderr)
        sys.exit(1)
