"""On-chain and exchange flow monitoring for XLM using FREE APIs.

Sources:
- Stellar Horizon API (free, no key) -- network stats, transaction volume
- CoinGecko exchange tickers -- volume by exchange (spot flow proxy)
- Stellar Horizon payments -- whale movement detection

Writes output to data/onchain_alerts.json.
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

_UA = {"User-Agent": "xlm-bot/onchain-intel/1.0"}
_TIMEOUT = 8.0
_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_CACHE_PATH = _DATA_DIR / "onchain_alerts.json"
_STALE_AFTER_MIN = 15
_WHALE_THRESHOLD_XLM = 1_000_000  # 1M XLM minimum for whale alert


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
        logger.warning("onchain_intel: cache write failed: %s", exc)


# ── Stellar Horizon: ledger stats ───────────────────────────────────

def _poll_stellar_horizon() -> dict:
    """Fetch recent ledger stats from Stellar Horizon (free, no key).

    Returns tx count trends and operation volume from the last 10 ledgers.
    """
    url = "https://horizon.stellar.org/ledgers"
    try:
        resp = requests.get(
            url,
            params={"order": "desc", "limit": 10},
            headers=_UA,
            timeout=_TIMEOUT,
        )
        if resp.status_code != 200:
            logger.debug("horizon ledgers returned %d", resp.status_code)
            return {"available": False}

        data = resp.json()
        records = data.get("_embedded", {}).get("records", [])
        if not records:
            return {"available": False}

        tx_counts = []
        op_counts = []
        for rec in records:
            tx_counts.append(int(rec.get("successful_transaction_count", 0)))
            op_counts.append(int(rec.get("operation_count", 0)))

        avg_tx = sum(tx_counts) / len(tx_counts) if tx_counts else 0
        avg_ops = sum(op_counts) / len(op_counts) if op_counts else 0
        latest_tx = tx_counts[0] if tx_counts else 0

        # Compare latest to average for trend
        if avg_tx > 0:
            tx_ratio = latest_tx / avg_tx
        else:
            tx_ratio = 1.0

        if tx_ratio >= 1.5:
            tx_trend = "surging"
        elif tx_ratio >= 1.1:
            tx_trend = "increasing"
        elif tx_ratio <= 0.7:
            tx_trend = "decreasing"
        else:
            tx_trend = "stable"

        # Compare to previous cache for longer-term trend
        prev = _read_cache()
        prev_avg_tx = None
        if prev and isinstance(prev.get("_horizon_avg_tx"), (int, float)):
            prev_avg_tx = float(prev["_horizon_avg_tx"])

        volume_trend = "stable"
        if prev_avg_tx and prev_avg_tx > 0:
            change_pct = ((avg_tx - prev_avg_tx) / prev_avg_tx) * 100
            if change_pct >= 20:
                volume_trend = "increasing"
            elif change_pct <= -20:
                volume_trend = "decreasing"

        return {
            "available": True,
            "latest_tx_count": latest_tx,
            "avg_tx_count_10_ledgers": round(avg_tx, 1),
            "avg_op_count_10_ledgers": round(avg_ops, 1),
            "tx_trend": tx_trend,
            "volume_trend": volume_trend,
            "ledger_count": len(records),
        }
    except Exception as exc:
        logger.debug("horizon ledgers fetch failed: %s", exc)
        return {"available": False}


# ── CoinGecko exchange tickers: volume by exchange ──────────────────

def _estimate_exchange_flows() -> dict:
    """Fetch XLM ticker data from CoinGecko to estimate exchange flows.

    Large volume spikes on specific exchanges can signal inflow/outflow.
    """
    url = "https://api.coingecko.com/api/v3/coins/stellar/tickers"
    try:
        resp = requests.get(
            url,
            params={"include_exchange_logo": "false", "depth": "false"},
            headers=_UA,
            timeout=_TIMEOUT,
        )
        if resp.status_code != 200:
            logger.debug("coingecko tickers returned %d", resp.status_code)
            return {"available": False}

        data = resp.json()
        tickers = data.get("tickers", [])
        if not tickers:
            return {"available": False}

        exchange_volumes: dict[str, float] = {}
        total_volume_usd = 0.0

        for ticker in tickers:
            exchange = str(ticker.get("market", {}).get("name", "Unknown"))
            vol_usd = _to_float(ticker.get("converted_volume", {}).get("usd"), 0.0)
            if vol_usd and vol_usd > 0:
                exchange_volumes[exchange] = exchange_volumes.get(exchange, 0.0) + vol_usd
                total_volume_usd += vol_usd

        # Sort by volume descending
        sorted_exchanges = sorted(exchange_volumes.items(), key=lambda x: x[1], reverse=True)
        top_exchanges = [
            {"exchange": name, "volume_usd": round(vol, 2)}
            for name, vol in sorted_exchanges[:8]
        ]

        # Detect concentration: if top exchange has >50% of volume, flag it
        volume_spike = False
        concentration_pct = 0.0
        if sorted_exchanges and total_volume_usd > 0:
            concentration_pct = round(sorted_exchanges[0][1] / total_volume_usd * 100, 1)
            if concentration_pct > 50:
                volume_spike = True

        # Compare total volume to cached previous
        prev = _read_cache()
        prev_total = None
        if prev and isinstance(prev.get("_total_exchange_volume"), (int, float)):
            prev_total = float(prev["_total_exchange_volume"])

        volume_change_pct = None
        if prev_total and prev_total > 0:
            volume_change_pct = round(((total_volume_usd - prev_total) / prev_total) * 100, 1)
            if abs(volume_change_pct) > 50:
                volume_spike = True

        return {
            "available": True,
            "total_volume_usd": round(total_volume_usd, 2),
            "top_exchanges": top_exchanges,
            "top_exchange_concentration_pct": concentration_pct,
            "volume_change_pct": volume_change_pct,
            "exchange_volume_spike": volume_spike,
            "exchange_count": len(exchange_volumes),
        }
    except Exception as exc:
        logger.debug("coingecko tickers fetch failed: %s", exc)
        return {"available": False}


# ── Stellar Horizon: whale payment detection ────────────────────────

def _detect_whale_movements() -> dict:
    """Check recent Stellar payments for large transfers (>1M XLM).

    Uses Horizon payments endpoint (free, no key).
    """
    url = "https://horizon.stellar.org/payments"
    try:
        resp = requests.get(
            url,
            params={"order": "desc", "limit": 50, "include_failed": "false"},
            headers=_UA,
            timeout=_TIMEOUT,
        )
        if resp.status_code != 200:
            logger.debug("horizon payments returned %d", resp.status_code)
            return {"available": False, "whale_transfers": [], "count": 0}

        data = resp.json()
        records = data.get("_embedded", {}).get("records", [])

        whale_transfers: list[dict] = []
        total_whale_volume = 0.0

        for rec in records:
            # Only look at native XLM payments and path payments
            op_type = str(rec.get("type") or "")
            if op_type not in ("payment", "path_payment_strict_send", "path_payment_strict_receive"):
                continue

            asset_type = str(rec.get("asset_type") or "")
            if asset_type != "native":
                continue

            amount = _to_float(rec.get("amount"), 0.0)
            if amount and amount >= _WHALE_THRESHOLD_XLM:
                whale_transfers.append({
                    "amount": round(amount, 0),
                    "type": op_type,
                    "timestamp": str(rec.get("created_at") or ""),
                    "from": str(rec.get("from") or "")[:12] + "...",
                    "to": str(rec.get("to") or "")[:12] + "...",
                })
                total_whale_volume += amount

        count = len(whale_transfers)

        # Alert level based on whale activity
        if count >= 5 or total_whale_volume >= 50_000_000:
            alert_level = "critical"
        elif count >= 3 or total_whale_volume >= 20_000_000:
            alert_level = "warning"
        elif count >= 1:
            alert_level = "watch"
        else:
            alert_level = "none"

        return {
            "available": True,
            "whale_transfers": whale_transfers[:10],
            "count": count,
            "total_whale_volume_xlm": round(total_whale_volume, 0),
            "whale_alert_level": alert_level,
        }
    except Exception as exc:
        logger.debug("horizon payments fetch failed: %s", exc)
        return {"available": False, "whale_transfers": [], "count": 0}


# ── Signal generation ───────────────────────────────────────────────

def _generate_signals(horizon: dict, flows: dict, whales: dict) -> list[dict]:
    """Generate actionable signals from on-chain data."""
    signals: list[dict] = []

    # Whale signals
    whale_level = whales.get("whale_alert_level", "none")
    if whale_level in ("warning", "critical"):
        whale_vol = whales.get("total_whale_volume_xlm", 0)
        signals.append({
            "signal": f"whale_activity_{whale_vol/1e6:.0f}M_xlm",
            "severity": "high" if whale_level == "critical" else "medium",
            "direction": "unknown",  # can't determine in/out from payments alone
            "detail": f"{whales.get('count', 0)} whale transfers totaling {whale_vol/1e6:.1f}M XLM",
        })

    # Volume spike signals
    if flows.get("exchange_volume_spike"):
        vol_change = flows.get("volume_change_pct")
        signals.append({
            "signal": "exchange_volume_spike",
            "severity": "medium",
            "direction": "neutral",
            "detail": f"Exchange volume spike detected"
                + (f" ({vol_change:+.1f}% vs prev)" if vol_change is not None else ""),
        })

    # Network activity signals
    tx_trend = horizon.get("tx_trend", "stable")
    if tx_trend == "surging":
        signals.append({
            "signal": "network_activity_surge",
            "severity": "medium",
            "direction": "bullish",
            "detail": f"Stellar network tx count surging (avg {horizon.get('avg_tx_count_10_ledgers', 0):.0f}/ledger)",
        })
    elif tx_trend == "decreasing":
        signals.append({
            "signal": "network_activity_declining",
            "severity": "low",
            "direction": "bearish",
            "detail": "Stellar network activity declining",
        })

    return signals[:6]


# ── Public API ──────────────────────────────────────────────────────

def fetch_onchain_intel(symbol: str = "XLM") -> dict:
    """Gather on-chain intelligence for XLM.

    Returns dict with keys: network_health, tx_volume_trend,
    exchange_volume_spike, whale_transfers, whale_alert_level,
    signals, timestamp, stale_after_minutes.
    """
    logger.info("onchain_intel: fetching on-chain data for %s", symbol)
    t0 = time.monotonic()

    horizon = _poll_stellar_horizon()
    flows = _estimate_exchange_flows()
    whales = _detect_whale_movements()

    # Determine overall network health
    tx_trend = horizon.get("tx_trend", "stable")
    if tx_trend == "surging":
        network_health = "surging"
    elif tx_trend in ("increasing", "stable"):
        network_health = "active"
    else:
        network_health = "quiet"

    signals = _generate_signals(horizon, flows, whales)

    result = {
        "network_health": network_health,
        "tx_volume_trend": horizon.get("volume_trend", "stable"),
        "exchange_volume_spike": flows.get("exchange_volume_spike", False),
        "whale_transfers": whales.get("whale_transfers", [])[:5],
        "whale_alert_level": whales.get("whale_alert_level", "none"),
        "signals": signals,
        "details": {
            "horizon": {k: v for k, v in horizon.items() if k != "available"},
            "exchange_flows": {k: v for k, v in flows.items() if k != "available"},
            "whale_detection": {k: v for k, v in whales.items() if k not in ("available", "whale_transfers")},
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "stale_after_minutes": _STALE_AFTER_MIN,
        # Internal fields for trend tracking (prefixed with _)
        "_horizon_avg_tx": horizon.get("avg_tx_count_10_ledgers"),
        "_total_exchange_volume": flows.get("total_volume_usd"),
    }

    _save_cache(result)

    elapsed = time.monotonic() - t0
    logger.info(
        "onchain_intel: health=%s whales=%d signals=%d elapsed=%.1fs",
        network_health, whales.get("count", 0), len(signals), elapsed,
    )
    return result


def get_latest_onchain() -> dict | None:
    """Non-blocking read of latest cached on-chain intel."""
    cached = _read_cache()
    if cached and isinstance(cached.get("network_health"), str):
        return cached
    return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    result = fetch_onchain_intel()
    print(json.dumps(result, indent=2))
