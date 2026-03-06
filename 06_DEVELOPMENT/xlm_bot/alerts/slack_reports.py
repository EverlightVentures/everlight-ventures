"""
Slack Live Feed -- Native Canvas reporting for bot stats.
Enforced Policy: No raw text. All reports are Canvased.
"""
from __future__ import annotations
import time
import os
import sys
from datetime import datetime, timezone
from typing import Any

from . import slack as _slack

# Ensure Canvas bridge can be imported
from . import slack_canvas_bridge

_last_pulse_ts: float = 0
_last_health_ts: float = 0
_last_position_ts: float = 0

def _send_canvas(text: str, title: str) -> None:
    """Force the report through the autonomous Canvas Bridge."""
    slack_canvas_bridge.create_native_canvas(text, title, "xlmbot")

def _fmt_usd(v) -> str: return _slack._fmt_usd(v)
def _pnl_emoji(val: float) -> str:
    if val > 0: return ":large_green_circle:"
    elif val < 0: return ":red_circle:"
    return ":white_circle:"

def bot_pulse(state: dict, ctx: dict) -> None:
    """15-min pulse: regime, vol, gates, direction bias."""
    regime = state.get("regime") or ctx.get("regime", "?")
    vol_state = state.get("vol_state") or ctx.get("vol_state", "?")
    price = ctx.get("price") or ctx.get("mark_price", 0)
    
    lines = [
        f":satellite_antenna: *BOT PULSE* -- {_slack._now_pt()}",
        f"Price: ${price:.5f} | Regime: {regime} | Vol: {vol_state}",
        f"Thought: {ctx.get('thought', 'scanning...')}"
    ]
    _send_canvas("\n".join(lines), "Bot Pulse Status")

def account_health(state: dict, ctx: dict) -> None:
    """Hourly account health: balances, margin, PnL, equity, streaks."""
    pnl_today = state.get("exchange_pnl_today_usd") or state.get("pnl_today_usd", 0)
    total_balance = ctx.get("total_balance", 0)
    equity = ctx.get("equity", 0) or total_balance
    margin_ratio = ctx.get("margin_ratio", 1.0)
    
    lines = [
        f":bank: *ACCOUNT HEALTH REPORT* -- {_slack._now_pt()}",
        f"Balances: Total: ${total_balance:.2f} | Equity: ${equity:.2f}",
        f"P&L Today: {_pnl_emoji(pnl_today)} {_fmt_usd(pnl_today)}",
        f"Margin: {margin_ratio:.1%}",
        f"Position: {state.get('open_position', {}).get('direction', 'Flat')}"
    ]
    _send_canvas("\n".join(lines), "Account Health Summary")

def maybe_send_reports(state: dict, config: dict, ctx: dict) -> None:
    global _last_pulse_ts, _last_health_ts, _last_position_ts
    now = time.time()
    
    # Pulse (every 15 min)
    if now - _last_pulse_ts >= 900:
        bot_pulse(state, ctx)
        _last_pulse_ts = now

    # Account health (every 60 min)
    if now - _last_health_ts >= 3600:
        account_health(state, ctx)
        _last_health_ts = now
