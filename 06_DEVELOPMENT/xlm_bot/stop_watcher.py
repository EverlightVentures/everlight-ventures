#!/usr/bin/env python3
"""
Stop Watcher - Exchange-Independent Emergency Stop Process

Runs as a SEPARATE process from the main bot (xpb).
Purpose: if xpb goes offline with an open leveraged position, this process
still monitors price and fires a market close order when stop_loss is crossed.

This is the safety net for the Feb 25 scenario where a short ran 15 hours
without a stop because the main bot cycle was unmonitored.

Run: python stop_watcher.py
Startup: add to xon / docker entrypoint alongside xpb
"""
from __future__ import annotations

import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Allow running from any directory
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

CRYPTO_BOT_CONFIG = os.environ.get(
    "COINBASE_CONFIG_PATH",
    "/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/crypto_bot/config.json",
)
STATE_PATH = BASE_DIR / "data" / "state.json"
TICK_PATH = BASE_DIR / "logs" / "live_tick.json"
WATCHER_LOG = BASE_DIR / "logs" / "stop_watcher.log"
WATCHER_STATE = BASE_DIR / "logs" / "stop_watcher_state.json"

POLL_INTERVAL = 5         # seconds between checks
MAX_PRICE_AGE_SEC = 120   # reject stale tick data older than 2 minutes
MAX_CLOSE_RETRIES = 3     # attempts to close before giving up this cycle

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [StopWatcher] %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(WATCHER_LOG),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("stop_watcher")


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text()) if path.exists() else {}
    except Exception:
        return {}


def _current_price() -> float | None:
    """Read price from live_tick.json (written by live_ws.py every ~1s)."""
    tick = _read_json(TICK_PATH)
    if not tick:
        return None
    # Reject stale tick data
    ts_str = tick.get("timestamp") or tick.get("ts") or tick.get("time")
    if ts_str:
        try:
            ts = datetime.fromisoformat(str(ts_str).replace("Z", "+00:00"))
            age = (datetime.now(timezone.utc) - ts).total_seconds()
            if age > MAX_PRICE_AGE_SEC:
                log.debug(f"Stale tick ({age:.0f}s old), skipping")
                return None
        except Exception:
            pass
    price = tick.get("price") or tick.get("last") or tick.get("close")
    try:
        return float(price) if price else None
    except Exception:
        return None


def _open_position(state: dict) -> dict | None:
    pos = state.get("open_position")
    if not isinstance(pos, dict):
        return None
    if not pos.get("entry_price"):
        return None
    return pos


def _stop_crossed(pos: dict, price: float) -> bool:
    """Return True if current price has crossed the stored stop_loss."""
    stop = pos.get("stop_loss")
    direction = str(pos.get("direction") or pos.get("side") or "").lower()
    try:
        stop = float(stop)
    except (TypeError, ValueError):
        return False
    if stop <= 0:
        return False
    if "long" in direction:
        return price <= stop
    if "short" in direction:
        return price >= stop
    return False


def _max_loss_crossed(pos: dict, price: float, equity_start: float) -> bool:
    """Return True if trade has exceeded single_trade_max_loss hard cap ($10)."""
    entry = float(pos.get("entry_price") or 0)
    direction = str(pos.get("direction") or pos.get("side") or "").lower()
    size = int(pos.get("size") or 1)
    contract_size = float(pos.get("contract_size") or 5000)
    if entry <= 0:
        return False
    if "long" in direction:
        pnl = (price - entry) * contract_size * size
    else:
        pnl = (entry - price) * contract_size * size
    # Hard cap: $10 OR 3% of equity
    usd_cap = 10.0
    pct_cap = 0.03 * max(equity_start, 100.0)
    cap = min(usd_cap, pct_cap)
    return pnl <= -cap


def _fire_emergency_close(product_id: str) -> bool:
    """Place market close order via Coinbase API. Returns True on success."""
    try:
        vendor = BASE_DIR / "vendor"
        if str(vendor) not in sys.path:
            sys.path.insert(0, str(vendor))
        from execution.coinbase_advanced import CoinbaseAdvanced
        api = CoinbaseAdvanced(CRYPTO_BOT_CONFIG)
        result = api.close_cfm_position(product_id, paper=False)
        ok = bool(result and result.get("ok"))
        log.info(f"Emergency close result: ok={ok} method={result.get('method')} {result}")
        return ok
    except Exception as e:
        log.error(f"Emergency close FAILED: {e}")
        return False


def _write_watcher_state(event: str, detail: dict) -> None:
    try:
        WATCHER_STATE.write_text(json.dumps({
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": event,
            **detail,
        }, indent=2))
    except Exception:
        pass


def run() -> None:
    log.info("Stop Watcher starting. Monitoring every %ds.", POLL_INTERVAL)
    fired_for_entry: str | None = None  # track which entry_ts we last fired for

    while True:
        try:
            state = _read_json(STATE_PATH)
            pos = _open_position(state)

            if not pos:
                fired_for_entry = None
                time.sleep(POLL_INTERVAL)
                continue

            product_id = str(pos.get("product_id") or "XLP-20DEC30-CDE")
            entry_ts = str(pos.get("entry_time") or pos.get("entry_ts") or "unknown")
            direction = str(pos.get("direction") or pos.get("side") or "")
            stop = pos.get("stop_loss")
            entry_price = float(pos.get("entry_price") or 0)
            equity_start = float(state.get("equity_start_usd") or 300.0)

            price = _current_price()
            if price is None:
                log.debug("No live price available, skipping check")
                time.sleep(POLL_INTERVAL)
                continue

            stop_hit = _stop_crossed(pos, price)
            loss_hit = _max_loss_crossed(pos, price, equity_start)

            if not stop_hit and not loss_hit:
                time.sleep(POLL_INTERVAL)
                continue

            # Avoid duplicate fires for the same trade entry
            if entry_ts == fired_for_entry:
                log.debug(f"Already fired for entry {entry_ts}, waiting for main bot to clear state")
                time.sleep(POLL_INTERVAL)
                continue

            reason = "stop_loss" if stop_hit else "max_loss_cap"
            log.warning(
                f"STOP TRIGGERED: {direction} {product_id} @ price={price:.6f} "
                f"entry={entry_price:.6f} stop={stop} reason={reason}"
            )
            _write_watcher_state("stop_triggered", {
                "product_id": product_id,
                "direction": direction,
                "price": price,
                "entry_price": entry_price,
                "stop_loss": stop,
                "reason": reason,
                "entry_ts": entry_ts,
            })

            success = False
            for attempt in range(1, MAX_CLOSE_RETRIES + 1):
                log.warning(f"Firing emergency close (attempt {attempt}/{MAX_CLOSE_RETRIES})")
                success = _fire_emergency_close(product_id)
                if success:
                    break
                time.sleep(2)

            fired_for_entry = entry_ts
            _write_watcher_state("close_attempted", {
                "success": success,
                "reason": reason,
                "entry_ts": entry_ts,
            })

            if not success:
                log.error("Emergency close failed after all retries. Manual intervention required!")

        except Exception as e:
            log.error(f"Stop watcher loop error: {e}")

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    run()
