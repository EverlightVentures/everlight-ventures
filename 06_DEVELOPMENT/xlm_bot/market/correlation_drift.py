"""BTC/XLM correlation and macro divergence monitor.

Tracks rolling 24h price correlation between BTC and XLM using
CoinGecko free API. Detects decoupling, relative strength, and
divergence signals.

Writes output to data/correlation_drift.json.
Designed for cron every 5-10 min on resource-constrained Oracle Micro VM.
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

logger = logging.getLogger(__name__)

_UA = {"User-Agent": "xlm-bot/correlation-drift/1.0"}
_TIMEOUT = 8.0
_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_CACHE_PATH = _DATA_DIR / "correlation_drift.json"
_STALE_AFTER_MIN = 15


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
        logger.warning("correlation_drift: cache write failed: %s", exc)


def _fetch_market_chart(coin_id: str) -> list[list[float]] | None:
    """Fetch 24h hourly prices from CoinGecko (free, no key).

    Returns list of [timestamp_ms, price_usd] pairs.
    """
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
    try:
        resp = requests.get(
            url,
            params={"vs_currency": "usd", "days": "1"},
            headers=_UA,
            timeout=_TIMEOUT,
        )
        if resp.status_code != 200:
            logger.debug("coingecko market_chart %s returned %d", coin_id, resp.status_code)
            return None
        data = resp.json()
        prices = data.get("prices")
        if isinstance(prices, list) and len(prices) >= 5:
            return prices
        return None
    except Exception as exc:
        logger.debug("coingecko market_chart %s failed: %s", coin_id, exc)
        return None


def _compute_correlation(prices_a: list[float], prices_b: list[float]) -> float | None:
    """Compute Pearson correlation between two price series.

    Uses pure Python to avoid numpy dependency on constrained VM.
    Returns correlation coefficient (-1 to 1) or None on failure.
    """
    n = min(len(prices_a), len(prices_b))
    if n < 5:
        return None

    a = prices_a[:n]
    b = prices_b[:n]

    mean_a = sum(a) / n
    mean_b = sum(b) / n

    cov = sum((a[i] - mean_a) * (b[i] - mean_b) for i in range(n))
    var_a = sum((x - mean_a) ** 2 for x in a)
    var_b = sum((x - mean_b) ** 2 for x in b)

    denom = (var_a * var_b) ** 0.5
    if denom == 0:
        return None

    return cov / denom


def _align_price_series(
    raw_a: list[list[float]], raw_b: list[list[float]]
) -> tuple[list[float], list[float]]:
    """Align two CoinGecko price series by nearest timestamp.

    Both inputs are [[ts_ms, price], ...]. Returns aligned price arrays.
    """
    # Build timestamp -> price maps
    map_a = {int(p[0]): p[1] for p in raw_a if len(p) >= 2}
    map_b = {int(p[0]): p[1] for p in raw_b if len(p) >= 2}

    # Find common timestamps (within 5 min tolerance)
    aligned_a: list[float] = []
    aligned_b: list[float] = []

    ts_a_sorted = sorted(map_a.keys())
    ts_b_sorted = sorted(map_b.keys())

    # Simple nearest-match alignment
    bi = 0
    for ta in ts_a_sorted:
        # Find closest ts_b
        while bi < len(ts_b_sorted) - 1 and abs(ts_b_sorted[bi + 1] - ta) < abs(ts_b_sorted[bi] - ta):
            bi += 1
        if bi < len(ts_b_sorted) and abs(ts_b_sorted[bi] - ta) < 300_000:  # 5 min tolerance
            aligned_a.append(map_a[ta])
            aligned_b.append(map_b[ts_b_sorted[bi]])

    return aligned_a, aligned_b


def _pct_change_24h(raw_prices: list[list[float]]) -> float | None:
    """Calculate 24h percent change from raw CoinGecko price series."""
    if not raw_prices or len(raw_prices) < 2:
        return None
    first_price = _to_float(raw_prices[0][1]) if len(raw_prices[0]) >= 2 else None
    last_price = _to_float(raw_prices[-1][1]) if len(raw_prices[-1]) >= 2 else None
    if first_price and last_price and first_price > 0:
        return round(((last_price - first_price) / first_price) * 100, 2)
    return None


# ── Public API ──────────────────────────────────────────────────────

def fetch_correlation_data() -> dict:
    """Track BTC/XLM price correlation and macro divergence.

    Returns dict with keys: btc_xlm_correlation_24h, correlation_trend,
    xlm_relative_strength, btc_24h_change, xlm_24h_change,
    divergence_flag, timestamp.
    """
    logger.info("correlation_drift: fetching BTC/XLM correlation data")
    t0 = time.monotonic()

    btc_raw = _fetch_market_chart("bitcoin")
    xlm_raw = _fetch_market_chart("stellar")

    correlation: float | None = None
    btc_24h: float | None = None
    xlm_24h: float | None = None
    relative_strength = "inline"
    correlation_trend = "stable"
    divergence_flag = False

    if btc_raw and xlm_raw:
        # Align and compute correlation
        prices_btc, prices_xlm = _align_price_series(btc_raw, xlm_raw)
        correlation = _compute_correlation(prices_btc, prices_xlm)
        if correlation is not None:
            correlation = round(correlation, 4)

        btc_24h = _pct_change_24h(btc_raw)
        xlm_24h = _pct_change_24h(xlm_raw)

        # Determine relative strength
        if btc_24h is not None and xlm_24h is not None:
            diff = xlm_24h - btc_24h
            if diff > 1.5:
                relative_strength = "leading"
            elif diff < -1.5:
                relative_strength = "lagging"
            else:
                relative_strength = "inline"

        # Correlation trend: compare to previous reading
        prev = _read_cache()
        prev_corr = None
        if prev and isinstance(prev.get("btc_xlm_correlation_24h"), (int, float)):
            prev_corr = float(prev["btc_xlm_correlation_24h"])

        if correlation is not None:
            if prev_corr is not None:
                corr_change = correlation - prev_corr
                if corr_change < -0.15:
                    correlation_trend = "decoupling"
                elif corr_change > 0.15:
                    correlation_trend = "re-coupling"
                else:
                    correlation_trend = "stable"

            # Absolute check: low correlation = potential decoupling
            if correlation < 0.5:
                correlation_trend = "decoupling"
                divergence_flag = True

            # Divergence: moving in opposite directions with >2% moves
            if btc_24h is not None and xlm_24h is not None:
                if (btc_24h > 2.0 and xlm_24h < -1.0) or (btc_24h < -2.0 and xlm_24h > 1.0):
                    divergence_flag = True

    result = {
        "btc_xlm_correlation_24h": correlation,
        "correlation_trend": correlation_trend,
        "xlm_relative_strength": relative_strength,
        "btc_24h_change": btc_24h,
        "xlm_24h_change": xlm_24h,
        "divergence_flag": divergence_flag,
        "data_points": min(
            len(btc_raw) if btc_raw else 0,
            len(xlm_raw) if xlm_raw else 0,
        ),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "stale_after_minutes": _STALE_AFTER_MIN,
    }

    _save_cache(result)

    elapsed = time.monotonic() - t0
    logger.info(
        "correlation_drift: corr=%s trend=%s strength=%s diverge=%s elapsed=%.1fs",
        correlation, correlation_trend, relative_strength, divergence_flag, elapsed,
    )
    return result


def get_latest_correlation() -> dict | None:
    """Non-blocking read of latest cached correlation data."""
    cached = _read_cache()
    if cached and "btc_xlm_correlation_24h" in cached:
        return cached
    return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    result = fetch_correlation_data()
    print(json.dumps(result, indent=2))
