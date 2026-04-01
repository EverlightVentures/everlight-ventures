#!/usr/bin/env python3
"""Market intelligence runner -- polls all 3 intel modules in sequence.

Designed to be cron'd every 5-10 minutes on Oracle:
  */5 * * * * cd /home/opc/xlm_bot && python3 -m market.intel_runner >> logs/intel_runner.log 2>&1

Each module is fault-isolated: if one fails, the others still run.
Total runtime target: under 30 seconds (3 modules x ~8s timeout each).
"""
from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

# Ensure the bot root is on sys.path so relative imports work
_BOT_ROOT = Path(__file__).resolve().parent.parent
if str(_BOT_ROOT) not in sys.path:
    sys.path.insert(0, str(_BOT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("intel_runner")


def run_all() -> dict:
    """Run all market intel modules in sequence. Returns status dict."""
    results = {}
    t0 = time.monotonic()

    # Module 1: Sentiment Monitor
    try:
        from market.sentiment_monitor import fetch_sentiment
        sentiment = fetch_sentiment()
        results["sentiment"] = {
            "ok": True,
            "score": sentiment.get("score"),
            "direction": sentiment.get("direction"),
        }
    except Exception as exc:
        logger.error("sentiment_monitor failed: %s", exc)
        results["sentiment"] = {"ok": False, "error": str(exc)}

    # Module 2: On-Chain Intelligence
    try:
        from market.onchain_intelligence import fetch_onchain_intel
        onchain = fetch_onchain_intel()
        results["onchain"] = {
            "ok": True,
            "health": onchain.get("network_health"),
            "whale_level": onchain.get("whale_alert_level"),
            "signals": len(onchain.get("signals", [])),
        }
    except Exception as exc:
        logger.error("onchain_intelligence failed: %s", exc)
        results["onchain"] = {"ok": False, "error": str(exc)}

    # Module 3: Correlation Drift
    try:
        from market.correlation_drift import fetch_correlation_data
        corr = fetch_correlation_data()
        results["correlation"] = {
            "ok": True,
            "correlation": corr.get("btc_xlm_correlation_24h"),
            "trend": corr.get("correlation_trend"),
            "divergence": corr.get("divergence_flag"),
        }
    except Exception as exc:
        logger.error("correlation_drift failed: %s", exc)
        results["correlation"] = {"ok": False, "error": str(exc)}

    elapsed = time.monotonic() - t0
    ok_count = sum(1 for v in results.values() if v.get("ok"))
    results["_summary"] = {
        "modules_ok": ok_count,
        "modules_total": 3,
        "elapsed_sec": round(elapsed, 1),
    }

    logger.info(
        "intel_runner complete: %d/3 modules OK in %.1fs",
        ok_count, elapsed,
    )
    return results


if __name__ == "__main__":
    status = run_all()
    # Print compact summary
    for module, info in status.items():
        if module.startswith("_"):
            continue
        if info.get("ok"):
            details = ", ".join(f"{k}={v}" for k, v in info.items() if k != "ok")
            print(f"  [OK] {module}: {details}")
        else:
            print(f"  [FAIL] {module}: {info.get('error', 'unknown')}")
    summary = status.get("_summary", {})
    print(f"\nMarket intel updated: {summary.get('modules_ok', 0)}/3 in {summary.get('elapsed_sec', 0)}s")
