"""Tiered Slack alerting system for XLM trading bot.

Three severity tiers with rate limiting:
  INFO     (green)  -- daily PnL, entries/exits, bot lifecycle, position updates
  WARN     (yellow) -- slippage, rate limits, stale heartbeat, memory, margin
  CRITICAL (red)    -- circuit breaker, API down, bot dead, near-liquidation

Fire-and-forget: all sends happen in a daemon thread so the bot cycle
is never blocked. Rate limits prevent flooding Slack.

Usage:
    from alerts.tiered_alerts import init, alert_info, alert_warn, alert_critical
    from alerts.tiered_alerts import alert_position_update, alert_daily_summary
    init(config)
    alert_info("Bot started", "Session abc123 | Equity $626.40")
    alert_warn("High slippage", "Entry slipped 0.12% on LONG 5000 XLM")
    alert_critical("Circuit breaker tripped", "3 consecutive losses, halting")
"""
from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import requests

# ---------------------------------------------------------------------------
# Module state
# ---------------------------------------------------------------------------
_WEBHOOK_URL: str = ""
_ENABLED: bool = False

# Rate-limit tracking -- {tier: last_send_epoch}
_last_send: Dict[str, float] = {"INFO": 0.0, "WARN": 0.0, "CRITICAL": 0.0}
_lock = threading.Lock()

# Rate-limit windows (seconds)
_RATE_LIMITS = {
    "INFO": 300,      # max 1 per 5 min
    "WARN": 120,      # max 1 per 2 min
    "CRITICAL": 0,    # always sends
}

# Tier formatting
_TIER_META = {
    "INFO": {
        "emoji": ":green_circle:",
        "color": "#2eb886",
        "label": "INFO",
    },
    "WARN": {
        "emoji": ":warning:",
        "color": "#daa038",
        "label": "WARN",
    },
    "CRITICAL": {
        "emoji": ":rotating_light:",
        "color": "#cc0000",
        "label": "CRITICAL",
    },
}


# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------
def init(config: dict | None = None) -> None:
    """Load webhook URL from config or env var.

    Config path: slack.webhook_url
    Env fallback: SLACK_WEBHOOK_URL
    """
    global _WEBHOOK_URL, _ENABLED
    slack_cfg = (config or {}).get("slack") or {}
    _WEBHOOK_URL = (
        os.environ.get("SLACK_WEBHOOK_URL")
        or slack_cfg.get("webhook_url")
        or (config or {}).get("slack_webhook_url")
        or ""
    )
    _ENABLED = bool(_WEBHOOK_URL)


def is_enabled() -> bool:
    return _ENABLED


# ---------------------------------------------------------------------------
# Timestamp helper
# ---------------------------------------------------------------------------
def _now_pt() -> str:
    """Current time formatted in Pacific Time."""
    try:
        from zoneinfo import ZoneInfo
        return (
            datetime.now(timezone.utc)
            .astimezone(ZoneInfo("America/Los_Angeles"))
            .strftime("%I:%M %p PT  %b %d")
        )
    except Exception:
        return datetime.now(timezone.utc).strftime("%H:%M UTC")


# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------
def _rate_ok(tier: str) -> bool:
    """Return True if this tier is allowed to send right now."""
    window = _RATE_LIMITS.get(tier, 0)
    if window <= 0:
        return True
    now = time.monotonic()
    with _lock:
        last = _last_send.get(tier, 0.0)
        if now - last < window:
            return False
        _last_send[tier] = now
    return True


# ---------------------------------------------------------------------------
# Low-level sender
# ---------------------------------------------------------------------------
def _post(payload: dict) -> None:
    """POST to Slack webhook. Runs inside a daemon thread -- never blocks."""
    if not _WEBHOOK_URL:
        return
    try:
        requests.post(_WEBHOOK_URL, json=payload, timeout=5)
    except Exception:
        pass  # Never crash the bot for an alert failure


def _send(tier: str, title: str, body: str = "") -> None:
    """Build a Slack message and fire it in a background thread.

    Respects rate limits per tier.
    """
    if not _ENABLED:
        return
    if not _rate_ok(tier):
        return

    meta = _TIER_META.get(tier, _TIER_META["INFO"])
    ts = _now_pt()

    text_lines = [
        f"{meta['emoji']}  *[{meta['label']}]  {title}*",
    ]
    if body:
        text_lines.append(body)
    text_lines.append(f"_{ts}_")

    payload: Dict[str, Any] = {
        "text": "\n".join(text_lines),
        "attachments": [
            {
                "color": meta["color"],
                "text": body if body else title,
                "footer": ts,
            }
        ],
    }

    threading.Thread(target=_post, args=(payload,), daemon=True).start()


# ---------------------------------------------------------------------------
# Public API -- three tiers
# ---------------------------------------------------------------------------
def alert_info(title: str, body: str = "") -> None:
    """Green tier -- informational. Rate limited to 1 per 5 min."""
    _send("INFO", title, body)


def alert_warn(title: str, body: str = "") -> None:
    """Yellow tier -- warning. Rate limited to 1 per 2 min."""
    _send("WARN", title, body)


def alert_critical(title: str, body: str = "") -> None:
    """Red tier -- critical. Always sends immediately."""
    _send("CRITICAL", title, body)


# ---------------------------------------------------------------------------
# Convenience: position update
# ---------------------------------------------------------------------------
def alert_position_update(
    direction: str,
    entry: float,
    pnl: float,
    state: str = "",
) -> None:
    """INFO-tier position monitoring alert.

    Args:
        direction: 'long' or 'short'
        entry: entry price
        pnl: current unrealized PnL in USD
        state: trade state label (EARLY, BUILDING, SECURED, etc.)
    """
    sign = "+" if pnl >= 0 else ""
    emoji_dir = ":arrow_up:" if direction.lower() == "long" else ":arrow_down:"
    state_str = f"  |  State: {state}" if state else ""
    alert_info(
        f"Position Update {emoji_dir} {direction.upper()}",
        (
            f"Entry: ${entry:.5f}  |  PnL: {sign}${pnl:.2f}{state_str}"
        ),
    )


# ---------------------------------------------------------------------------
# Convenience: daily summary
# ---------------------------------------------------------------------------
def alert_daily_summary(
    trades: int = 0,
    pnl: float = 0.0,
    wins: int = 0,
    losses: int = 0,
    equity: float | None = None,
) -> None:
    """INFO-tier end-of-day summary. Bypasses rate limit (forced send)."""
    win_rate = f"{wins / trades * 100:.0f}%" if trades > 0 else "n/a"
    sign = "+" if pnl >= 0 else ""
    lines = [
        f"Trades: {trades}  ({wins}W / {losses}L)  WR: {win_rate}",
        f"PnL: {sign}${pnl:.2f}",
    ]
    if equity is not None:
        lines.append(f"Equity: ${equity:.2f}")

    # Force send -- bypass INFO rate limit for daily summary
    with _lock:
        _last_send["INFO"] = 0.0

    result_emoji = ":trophy:" if pnl > 0 else ":chart_with_downwards_trend:" if pnl < 0 else ":zzz:"
    alert_info(
        f"Daily Summary {result_emoji}",
        "\n".join(lines),
    )
