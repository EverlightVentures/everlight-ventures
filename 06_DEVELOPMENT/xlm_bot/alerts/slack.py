"""Slack native Canvas alerts for XLM bot trade events."""
from __future__ import annotations

import os
import sys
import threading
from datetime import datetime, timezone
from typing import Any

# Ensure bridge can be imported
ROOT_DIR = "/mnt/sdcard/AA_MY_DRIVE"

from . import slack_canvas_bridge

def init(config: dict | None = None) -> None:
    """Initialize (No-op since bridge uses hardcoded token)."""
    pass

def is_enabled() -> bool:
    return True

def _send_canvas(text: str, title: str, channel: str = "xlmbot") -> None:
    """Redirects raw text to the Canvas Bridge in a background thread."""
    threading.Thread(
        target=slack_canvas_bridge.create_native_canvas,
        args=(text, title, channel),
        daemon=True
    ).start()

def _send(text: str) -> None:
    """Internal catch-all for raw text sends."""
    # Derive title from first line if possible
    first_line = text.split('\n')[0].strip(':').strip('*')
    _send_canvas(text, first_line or "Bot Alert", "xlmbot")

def send(text: str, level: str = "info") -> None:
    """Public send for critical alerts."""
    prefix = {"warning": "WARNING", "error": "CRITICAL", "info": "INFO"}.get(level, "INFO")
    _send_canvas(f"[{prefix}] {text}", f"System Alert: {prefix}", "xlmbot")

def _fmt_usd(val: float | None) -> str:
    if val is None: return "—"
    sign = "+" if val >= 0 else ""
    return f"{sign}${val:.2f}"

def _fmt_pct(val: float | None) -> str:
    if val is None: return "—"
    return f"{val*100:+.2f}%"

def _fmt_hold(minutes: float) -> str:
    if minutes < 1: return "< 1m"
    m = int(round(minutes))
    if m < 60: return f"{m}m"
    h, r = divmod(m, 60)
    return f"{h}h {r}m" if r else f"{h}h"

def _now_pt() -> str:
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(timezone.utc).astimezone(ZoneInfo("America/Los_Angeles")).strftime("%I:%M %p PT")
    except Exception:
        return datetime.now(timezone.utc).strftime("%H:%M UTC")

# -- Redirection of existing alert functions to Canvas Links --

def trade_entry(direction: str, product_id: str, size: int, entry_price: float, stop_loss: float, **kw) -> None:
    text = (
        f"*TRADE ENTRY: {direction.upper()}*\n"
        f"• Price: ${entry_price:.5f} | SL: ${stop_loss:.5f}\n"
        f"• Size: {size} | Score: {kw.get('score', 0)}\n"
        f"• {_now_pt()}"
    )
    _send_canvas(text, f"{direction.upper()} Entry Alert", "xlmbot")

def trade_exit(direction: str, exit_reason: str, entry_price: float, exit_price: float, pnl_usd: float | None, **kw) -> None:
    text = (
        f"*TRADE EXIT: {direction.upper()}*\n"
        f"• Reason: {exit_reason}\n"
        f"• Price: ${entry_price:.5f} -> ${exit_price:.5f}\n"
        f"• PnL: {_fmt_usd(pnl_usd)}\n"
        f"• {_now_pt()}"
    )
    _send_canvas(text, f"{direction.upper()} Exit Report", "xlmbot")

def bot_started(session_id: str = "", **kw) -> None:
    _send_canvas(f"Bot Session `{session_id}` Started at {_now_pt()}", "Bot Lifecycle: Started", "xlmbot")

def bot_error(error_type: str, details: str = "") -> None:
    _send_canvas(f"ERROR: {error_type}\n{details}", "System Error Alert", "xlmbot")

def daily_summary(trades: int = 0, pnl_usd: float = 0, **kw) -> None:
    text = f"DAILY SUMMARY\n• Trades: {trades}\n• PnL: {_fmt_usd(pnl_usd)}\n• {_now_pt()}"
    _send_canvas(text, "Daily Performance Report", "xlmbot")

def shift_summary(shift_name: str, **kw) -> None:
    _send_canvas(f"SHIFT SUMMARY: {shift_name}\nPNL: {kw.get('pnl_usd', 0)}", f"Shift Summary: {shift_name}", "xlmbot")

def reconciler_exit(direction: str, **kw) -> None:
    _send_canvas(f"RECONCILER EXIT: {direction}", "Reconciler Report", "xlmbot")

def margin_warning(tier: str, margin_ratio: float, **kw) -> None:
    _send_canvas(f"MARGIN {tier.upper()}: {margin_ratio:.1%}", "Margin Warning", "xlmbot")

# -- War Room redirections (using 'warroom' app identity) --

def war_room_assessment(agent_name: str, assessment: dict) -> None:
    text = f"AGENT: {agent_name.upper()}\nACTION: {assessment.get('action', '?')}\nREASONING: {assessment.get('reasoning', '')}"
    _send_canvas(text, f"Agent Assessment: {agent_name}", "warroom")

def war_room_consensus(result: dict) -> None:
    text = f"CONSENSUS REACHED\nACTION: {result.get('action', '?')}\nREASONING: {result.get('reasoning', '')}"
    _send_canvas(text, "Hive Consensus Report", "warroom")

def war_room_status(message: str) -> None:
    _send_canvas(message, "War Room Status Update", "warroom")
