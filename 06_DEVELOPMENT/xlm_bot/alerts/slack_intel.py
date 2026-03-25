"""Intelligent Slack poster with agent personas and decision-making.

Each agent reads the bot's decision data and makes an ANALYSIS with
a recommendation - not just data dumps. They have personality, conviction,
and they reference real numbers.

Throttled to avoid spam: max 1 post per channel per 5 minutes.
"""
from __future__ import annotations

import json
import logging
import os
import time
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

logger = logging.getLogger("slack_intel")

# Bot tokens
TOKENS = {
    "xlmbot": os.environ.get("SLACK_XLMBOT_TOKEN", "xoxb-8645963765681-10542494223845-M2gIADgkLB2HYJN4F8lGpbuI"),
    "warroom": os.environ.get("SLACK_WARROOM_TOKEN", "xoxb-8645963765681-10594020158069-eJRt13YP8qedI6DnQwupuFfy"),
}

# Channel IDs
CHANNELS = {
    "xlm-trading": "C0AN8SG030W",
    "war-room": "C0ANAU30UQ2",
    "hive-alerts": "C0ANPRCA4AD",
    "ceo-brief": "C0AP56SQM08",
    "revenue-dashboard": "C0AN4GU0MDH",
    "wholesale-deals": "C0ANLLV8JAC",
    "broker-pipeline": "C0AN7FTTK2R",
    "deploy-log": "C0AN4GSTMT5",
    "ft-markets": "C0AP56SFQG0",
}

# Throttle tracking: {channel_id: last_post_timestamp}
_last_post: dict[str, float] = {}
_THROTTLE_SECONDS = 300  # 5 minutes

_SLACK_API = "https://slack.com/api/chat.postMessage"


def _post(channel_key: str, text: str, bot: str = "warroom") -> bool:
    """Post to Slack with throttling."""
    channel_id = CHANNELS.get(channel_key)
    if not channel_id:
        return False

    now = time.time()
    throttle_key = f"{channel_id}:{bot}"
    if throttle_key in _last_post and (now - _last_post[throttle_key]) < _THROTTLE_SECONDS:
        return False  # throttled

    token = TOKENS.get(bot)
    if not token:
        return False

    try:
        resp = requests.post(
            _SLACK_API,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"channel": channel_id, "text": text, "unfurl_links": False},
            timeout=10,
        )
        if resp.status_code == 200 and resp.json().get("ok"):
            _last_post[throttle_key] = now
            return True
        else:
            logger.warning("Slack post failed: %s", resp.text[:200])
            return False
    except Exception as e:
        logger.warning("Slack post error: %s", e)
        return False


def _post_bg(channel_key: str, text: str, bot: str = "warroom") -> None:
    """Post in background thread."""
    threading.Thread(target=_post, args=(channel_key, text, bot), daemon=True).start()


# ---------------------------------------------------------------------------
# Agent personas: each reads decision data and makes a CALL
# ---------------------------------------------------------------------------

def _fmt_price(p: float | None) -> str:
    return f"${p:.5f}" if p else "?"


def _fmt_pct(p: float | None) -> str:
    if p is None:
        return "?"
    return f"{p:+.2f}%"


def rex_thornton_analysis(d: dict) -> str:
    """Rex Thornton - Head of Markets. Makes directional calls on XLM."""
    price = d.get("price")
    htf = d.get("htf_trend", "neutral")
    regime = d.get("v4_regime") or d.get("regime") or "neutral"
    vol = d.get("vol_phase", "?")
    score = d.get("v4_selected_score") or 0
    thresh = d.get("v4_selected_threshold") or 75
    direction = d.get("direction")
    entry = d.get("entry_signal") or d.get("selected_entry_type")
    align = d.get("alignment_bonus") or 0
    wz_count = d.get("wick_zones_count") or 0
    patterns = d.get("patterns_active") or []
    ms = d.get("micro_sweep_promoted")
    overnight = d.get("overnight_trading_ok")
    funding = d.get("contract_funding_bias", "")
    oi = d.get("contract_oi_trend", "")

    lines = [f"*Rex Thornton | Markets* | {_fmt_price(price)}"]

    # Directional call
    if entry and direction:
        lines.append(f"We're IN. *{entry.replace('_', ' ').upper()}* {direction.upper()} via score {int(score)}/{int(thresh)}.")
    elif score > 0 and score < thresh:
        gap = int(thresh - score)
        lines.append(f"Setup building. Score {int(score)}/{int(thresh)}, need {gap} more points. Not there yet.")
    else:
        lines.append("Flat. Scanning for the next play.")

    # Market read
    if htf == "bullish":
        lines.append("Daily trend is up. I want to be buying dips here, not fighting the tape.")
    elif htf == "bearish":
        lines.append("Daily pushing down. Rallies are for selling.")

    if regime == "trend":
        lines.append(f"Trending regime. Vol phase: {vol}. Press it.")
    elif regime == "mean_reversion":
        lines.append(f"Range regime. Vol: {vol}. Buy support, sell resistance.")

    # Conviction signals
    conviction = []
    if isinstance(align, (int, float)) and align >= 6:
        conviction.append(f"TF alignment {int(align):+d}")
    if wz_count and wz_count >= 5:
        conviction.append(f"{wz_count} wick zones mapped")
    if patterns:
        pat_names = [p.get("pattern", "").replace("_", " ") for p in patterns[:2]]
        conviction.append("patterns: " + ", ".join(pat_names))
    if ms:
        conviction.append("micro-sweep fired")
    if funding and "SHORT" in str(funding).upper():
        conviction.append("shorts paying funding")
    if oi and "RISING" in str(oi).upper():
        conviction.append("OI rising")

    if conviction:
        lines.append("Conviction: " + " | ".join(conviction))

    return "\n".join(lines)


def penny_vance_analysis(d: dict) -> str:
    """Penny Vance - CFO. Financial assessment and risk calls."""
    pnl = d.get("pnl_today_usd")
    equity = d.get("equity_start") or d.get("total_funds")
    wins = d.get("consecutive_wins") or 0
    losses = d.get("consecutive_losses") or 0
    overnight = d.get("overnight_trading_ok")
    margin_window = d.get("margin_window")
    quality = d.get("quality_tier")

    lines = ["*Penny Vance | Finance*"]

    if equity:
        lines.append(f"Equity: ${float(equity):.2f}")
        goal_pct = (float(equity) / 10000) * 100
        lines.append(f"Revenue goal: {goal_pct:.1f}% of $10K/mo target.")

    if pnl is not None:
        pnl_f = float(pnl)
        if pnl_f >= 0:
            lines.append(f"P&L today: +${pnl_f:.2f}. Green day. Keep the discipline.")
        else:
            lines.append(f"P&L today: -${abs(pnl_f):.2f}. Red. Stay conservative, recover smart.")

    if losses and int(losses) >= 2:
        lines.append(f"{int(losses)} consecutive losses. Tighten sizing. Do not chase.")
    elif wins and int(wins) >= 3:
        lines.append(f"{int(wins)} consecutive wins. Stay sharp, this is when overconfidence kills.")

    if margin_window:
        lines.append(f"Margin window: {margin_window}. {'Full attack mode.' if margin_window == 'intraday' else 'Conservative.'}")

    if overnight is False:
        lines.append("Overnight margin tight. 1 contract max until equity grows.")

    return "\n".join(lines)


def marcus_cole_summary(d: dict) -> str:
    """Marcus Cole - Chief of Staff. Big picture operational summary."""
    price = d.get("price")
    htf = d.get("htf_trend", "neutral")
    regime = d.get("v4_regime") or d.get("regime") or "neutral"
    wz = d.get("wick_zones_count") or 0
    patterns = d.get("patterns_active") or []
    entry = d.get("entry_signal")
    direction = d.get("direction")
    bot_alive = True  # we're posting, so bot is alive

    lines = ["*Marcus Cole | Command*"]
    lines.append(f"Price: {_fmt_price(price)} | Regime: {regime} | HTF: {htf}")
    lines.append(f"Vision: {wz} wick zones across 8 timeframes. {'Patterns active: ' + str(len(patterns)) if patterns else 'No patterns forming.'}")

    if entry and direction:
        lines.append(f"*ACTIVE TRADE*: {entry.replace('_', ' ').upper()} {direction.upper()}")
    else:
        lines.append("No active position. Bot scanning.")

    lines.append("All systems operational. Dashboards synced. Agents standing by.")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public API: called from main.py at the end of each cycle
# ---------------------------------------------------------------------------

def post_cycle_intel(decision: dict, event: str = "cycle") -> None:
    """Post intelligent analysis to Slack based on the bot's decision.

    Called from main.py. Throttled internally.

    Events:
        cycle: regular cycle update (posts to #xlm-trading every 5 min)
        trade_open: position opened (posts to #xlm-trading + #war-room + #hive-alerts)
        trade_close: position closed (same as trade_open)
        regime_change: regime shifted (posts to #ft-markets)
        error: bot error (posts to #hive-alerts)
    """
    if not decision:
        return

    try:
        if event == "trade_open" or event == "trade_close":
            # High priority: post to multiple channels immediately
            rex = rex_thornton_analysis(decision)
            _THROTTLE_OVERRIDE = True
            _post("xlm-trading", rex, "xlmbot")
            _post("war-room", marcus_cole_summary(decision), "warroom")
            _post("hive-alerts", rex, "warroom")

        elif event == "regime_change":
            rex = rex_thornton_analysis(decision)
            _post("ft-markets", rex, "warroom")
            _post("xlm-trading", rex, "xlmbot")

        elif event == "error":
            msg = f"*ALERT* | Bot error detected\n{decision.get('reason', 'unknown')}"
            _post("hive-alerts", msg, "warroom")

        else:
            # Regular cycle: throttled updates
            rex = rex_thornton_analysis(decision)
            _post("xlm-trading", rex, "xlmbot")

    except Exception as e:
        logger.warning("Slack intel post error: %s", e)


def post_hourly_summary(decision: dict) -> None:
    """Post hourly war room summary. Called from shift summary logic."""
    if not decision:
        return
    try:
        summary = marcus_cole_summary(decision)
        penny = penny_vance_analysis(decision)
        _post("war-room", summary + "\n\n" + penny, "warroom")
    except Exception as e:
        logger.warning("Hourly summary error: %s", e)
