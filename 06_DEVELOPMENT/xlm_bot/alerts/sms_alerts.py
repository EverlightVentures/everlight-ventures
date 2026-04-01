#!/usr/bin/env python3
"""
XLM Bot -- SMS Trade Alerts via Twilio REST API

Sends SMS on trade entries, exits, and critical events.
Rate limited to 10 SMS/day to control Twilio costs.

No Twilio SDK needed -- uses requests.post to the REST API directly.

Integration points in main.py:
  - After quality_tier_entry block (~line 8654): call sms_trade_entry()
  - After exit_order_sent block (~line 6366): call sms_trade_exit()
  - After consecutive loss detection: call sms_critical_alert()

Usage:
    from alerts.sms_alerts import sms_trade_entry, sms_trade_exit, sms_critical_alert
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

log = logging.getLogger("sms_alerts")

# --- Configuration ---
# Use corrected Account SID (ACf38...), not the org SID (OR...)
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID_REAL", "ACf38fd83f8ebdea75944943e35e1b653c")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "0b67cf19f64bc1b31f2e9fa4d0a7f937")
TWILIO_PHONE_FROM = os.environ.get("TWILIO_PHONE_NUMBER", "+17073869709")
BOSS_PHONE = os.environ.get("BOSS_PHONE", "+18888966772")

TWILIO_SMS_URL = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json"

# Rate limiting
MAX_SMS_PER_DAY = 10
STATE_FILE = Path("/tmp/sms_alert_state.json")

# --- State Management ---

def _load_state() -> dict:
    """Load daily SMS count from state file."""
    try:
        if STATE_FILE.exists():
            data = json.loads(STATE_FILE.read_text())
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            if data.get("date") == today:
                return data
    except Exception:
        pass
    return {"date": datetime.now(timezone.utc).strftime("%Y-%m-%d"), "count": 0, "messages": []}


def _save_state(state: dict) -> None:
    """Persist daily SMS count."""
    try:
        STATE_FILE.write_text(json.dumps(state, indent=2))
    except Exception as e:
        log.warning(f"SMS state save failed: {e}")


def _rate_limited() -> bool:
    """Check if we've hit the daily SMS limit."""
    state = _load_state()
    return state["count"] >= MAX_SMS_PER_DAY


def _increment_count(message: str) -> None:
    """Increment the daily send count."""
    state = _load_state()
    state["count"] += 1
    state["messages"].append({
        "time": datetime.now(timezone.utc).isoformat(),
        "preview": message[:60],
    })
    _save_state(state)


# --- Core Send ---

def _send_sms(body: str, to: str = BOSS_PHONE) -> bool:
    """
    Send SMS via Twilio REST API (no SDK).
    Returns True on success, False on failure.
    """
    if not HAS_REQUESTS:
        log.error("SMS: requests library not available")
        return False

    if _rate_limited():
        log.warning(f"SMS rate limit hit ({MAX_SMS_PER_DAY}/day). Skipping: {body[:40]}")
        return False

    try:
        resp = requests.post(
            TWILIO_SMS_URL,
            auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN),
            data={
                "From": TWILIO_PHONE_FROM,
                "To": to,
                "Body": body[:1600],  # Twilio limit
            },
            timeout=10,
        )
        if resp.status_code in (200, 201):
            _increment_count(body)
            log.info(f"SMS sent ({_load_state()['count']}/{MAX_SMS_PER_DAY} today): {body[:60]}")
            return True
        else:
            log.error(f"SMS failed ({resp.status_code}): {resp.text[:200]}")
            return False
    except Exception as e:
        log.error(f"SMS send error: {e}")
        return False


def _send_sms_async(body: str, to: str = BOSS_PHONE) -> None:
    """Fire-and-forget SMS in background thread (non-blocking for bot cycle)."""
    threading.Thread(target=_send_sms, args=(body, to), daemon=True).start()


# --- Public API ---

def sms_trade_entry(
    direction: str,
    entry_price: float,
    size: int = 1,
    stop_loss: float = 0.0,
    tp_floor: float = 0.0,
    score: int = 0,
    product_id: str = "",
) -> None:
    """Send SMS when bot enters a trade."""
    sl_part = f" SL: ${stop_loss:.4f}" if stop_loss else ""
    tp_part = f" TP floor: ${tp_floor:.4f}" if tp_floor else ""
    score_part = f" Score: {score}" if score else ""
    body = (
        f"XLM BOT: Entered {direction.upper()} at ${entry_price:.4f}, "
        f"{size} contract(s).{sl_part}{tp_part}{score_part}"
    )
    _send_sms_async(body)


def sms_trade_exit(
    direction: str,
    exit_price: float,
    pnl: Optional[float] = None,
    pnl_pct: Optional[float] = None,
    exit_reason: str = "",
    hold_min: Optional[float] = None,
) -> None:
    """Send SMS when bot exits a trade."""
    pnl_str = ""
    if pnl is not None:
        sign = "+" if pnl >= 0 else ""
        pnl_str = f" PnL: {sign}${pnl:.2f}"
        if pnl_pct is not None:
            pnl_str += f" ({pnl_pct*100:+.1f}%)"
    hold_str = ""
    if hold_min is not None:
        if hold_min < 60:
            hold_str = f" Hold: {int(hold_min)}m"
        else:
            hold_str = f" Hold: {int(hold_min//60)}h{int(hold_min%60)}m"
    reason_str = f" ({exit_reason})" if exit_reason else ""
    body = f"XLM BOT: Exited {direction.upper()} at ${exit_price:.4f}{pnl_str}{hold_str}{reason_str}"
    _send_sms_async(body)


def sms_critical_alert(message: str) -> None:
    """Send SMS for critical bot events (consecutive losses, low equity, etc)."""
    body = f"XLM BOT ALERT: {message}"
    _send_sms_async(body)


def sms_daily_summary(
    trades: int = 0,
    win_rate: float = 0.0,
    pnl: float = 0.0,
    equity: float = 0.0,
) -> None:
    """Optional: daily summary SMS."""
    sign = "+" if pnl >= 0 else ""
    body = (
        f"XLM BOT Daily: {trades} trades, "
        f"{win_rate*100:.0f}% WR, {sign}${pnl:.2f} PnL, ${equity:.2f} equity"
    )
    _send_sms_async(body)


# --- Integration Documentation ---
"""
WHERE TO ADD SMS CALLS IN main.py (DO NOT AUTO-MODIFY -- manual integration):

1. ENTRY (after fill is verified, ~line 9589-9600):
   Look for: "entry_order_id": res.order_id
   After the slack_alert.trade_entry() call, add:
       from alerts.sms_alerts import sms_trade_entry
       sms_trade_entry(
           direction=direction,
           entry_price=fill_price,
           size=contracts,
           stop_loss=sl_price,
           score=int((selected_v4 or {}).get("score", 0)),
       )

2. EXIT (after position is closed, ~line 6366-6375):
   Look for: "reason": "exit_order_sent"
   After the slack_alert.trade_exit() call (~line 6574), add:
       from alerts.sms_alerts import sms_trade_exit
       sms_trade_exit(
           direction=pos_direction,
           exit_price=current_price,
           pnl=realized_pnl,
           exit_reason=exit_reason,
       )

3. CRITICAL (after consecutive loss detection):
   Search for: "consecutive" or "loss_streak"
   Add:
       from alerts.sms_alerts import sms_critical_alert
       sms_critical_alert(f"{loss_streak} consecutive losses, equity at ${equity:.2f}")

4. DAILY SUMMARY (in daily_summary function):
   After slack_alert.daily_summary(), add sms_daily_summary() call.

All SMS calls are async (fire-and-forget) so they won't slow the bot cycle.
"""
