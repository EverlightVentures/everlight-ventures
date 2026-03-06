#!/usr/bin/env python3
"""House Money Protocol -- auto-sweep initial capital once account doubles.

When equity reaches 2x the starting capital, sweep the original stake
back to spot USDC. From that point, you're trading with pure profit
("house money") -- zero risk to original capital.

Run via cron every 30 min on Oracle:
  */30 * * * * cd /home/opc/xlm-bot && venv/bin/python house_money.py

Or call from main.py post-exit hook.
"""

import json, os, time
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(os.environ.get("CRYPTO_BOT_DIR", os.path.dirname(os.path.abspath(__file__))))
DATA = BASE / "data"
STATE_FILE = DATA / "state.json"
HM_FILE = DATA / "house_money.json"
SLACK_WEBHOOK = "https://hooks.slack.com/services/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"

# Config
INITIAL_CAPITAL = 310.55   # starting equity when bot went live
DOUBLE_TARGET = INITIAL_CAPITAL * 2  # sweep when equity hits this
SWEEP_AMOUNT = INITIAL_CAPITAL       # sweep back the original stake


def load_json(path):
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def save_json(path, data):
    tmp = str(path) + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2, default=str)
    os.rename(tmp, str(path))


def slack(msg):
    try:
        import urllib.request
        req = urllib.request.Request(
            SLACK_WEBHOOK,
            data=json.dumps({"text": msg}).encode(),
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception:
        pass


def get_equity():
    """Get current derivatives equity from state."""
    state = load_json(STATE_FILE)
    eq = state.get("exchange_equity_usd") or state.get("equity_start_usd", 0)
    return float(eq) if eq else 0.0


def check_and_sweep():
    hm = load_json(HM_FILE)
    now = datetime.now(timezone.utc).isoformat()

    # Already swept
    if hm.get("swept"):
        return

    equity = get_equity()
    if equity <= 0:
        return

    # Check if we've doubled
    if equity >= DOUBLE_TARGET:
        print(f"House Money triggered! Equity ${equity:.2f} >= target ${DOUBLE_TARGET:.2f}")
        print(f"Would sweep ${SWEEP_AMOUNT:.2f} back to spot USDC")

        # Try to do the sweep via API
        swept = False
        try:
            import sys
            sys.path.insert(0, str(BASE))
            cfg = json.load(open(BASE / "secrets" / "config.json"))
            ex = cfg["exchange"]
            from utils.coinbase_api import CoinbaseAPI
            api = CoinbaseAPI(ex["api_key"], ex["api_secret"])

            # Schedule a CFM sweep (derivatives -> spot)
            resp = api._request("POST", "/api/v3/brokerage/cfm/sweeps/schedule",
                                body={"usd_amount": str(SWEEP_AMOUNT)})
            print(f"Sweep response: {resp}")
            swept = True
        except Exception as e:
            print(f"Auto-sweep failed: {e}")
            print("Manual sweep required -- Coinbase cross-margin may handle this automatically")
            swept = False

        # Record the event
        hm = {
            "swept": True,
            "swept_at": now,
            "equity_at_trigger": equity,
            "initial_capital": INITIAL_CAPITAL,
            "sweep_amount": SWEEP_AMOUNT,
            "auto_sweep_success": swept,
            "remaining_equity": equity - SWEEP_AMOUNT,
            "note": "Trading with house money from here"
        }
        save_json(HM_FILE, hm)

        slack(
            f"*House Money Protocol activated!*\n"
            f"Equity ${equity:.2f} hit 2x target (${DOUBLE_TARGET:.2f}).\n"
            f"Sweeping ${SWEEP_AMOUNT:.2f} initial capital back to spot.\n"
            f"Remaining: ${equity - SWEEP_AMOUNT:.2f} (pure profit).\n"
            f"Auto-sweep: {'success' if swept else 'manual needed'}"
        )
    else:
        pct = (equity / DOUBLE_TARGET) * 100
        print(f"House Money: ${equity:.2f} / ${DOUBLE_TARGET:.2f} ({pct:.0f}%)")
        # Save progress
        hm["last_check"] = now
        hm["equity"] = equity
        hm["progress_pct"] = round(pct, 1)
        hm["target"] = DOUBLE_TARGET
        save_json(HM_FILE, hm)


if __name__ == "__main__":
    check_and_sweep()
