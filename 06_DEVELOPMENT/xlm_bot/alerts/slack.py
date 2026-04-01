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

def _send_canvas(text: str, title: str, channel: str = "xlmbot", metadata: dict[str, Any] | None = None) -> None:
    """Redirects raw text to the Canvas Bridge in a background thread."""
    threading.Thread(
        target=slack_canvas_bridge.create_native_canvas,
        args=(text, title, channel),
        kwargs={"metadata": metadata},
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
    _send_canvas(
        f"[{prefix}] {text}",
        f"System Alert: {prefix}",
        "xlmbot",
        metadata={"report_kind": "system_alert", "level": prefix.lower()},
    )

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

def _belfort_entry_flavor(direction: str, score: int) -> str:
    """Pick a Belfort-style one-liner for entry alerts."""
    if score >= 80:
        return "The confluence is SCREAMING. This is the play. Let's GO."
    if score >= 70:
        return "Setup looks strong. The chart says it, we take it. No hesitation."
    return "Decent setup. Calculated entry. We execute the plan."

def _belfort_exit_flavor(pnl: float | None, exit_reason: str) -> str:
    """Pick a Belfort-style one-liner for exit alerts."""
    if pnl is not None and pnl > 0:
        if pnl >= 20:
            return "THAT is how you do it. Feast mode. The winners take care of everything."
        return "Cash it. Another one in the bag. This is the game."
    if pnl is not None and pnl < 0:
        return "Cost of doing business. Next play. We don't look back."
    return "Position closed. Eyes forward. What's the next setup?"

def trade_entry(direction: str, product_id: str, size: int, entry_price: float, stop_loss: float, **kw) -> None:
    # Safety gate: skip alert if fill was not verified on exchange
    if kw.get("fill_verified") is False:
        return
    _score = kw.get('score', 0)
    _flavor = _belfort_entry_flavor(direction, int(_score or 0))
    lines = [
        f"# Trade Entry: {direction.upper()}",
        "",
        f"> {_flavor}",
        "",
        f"- Contract: {product_id or 'unknown'}",
        f"- Entry: ${entry_price:.5f}",
        f"- Stop Loss: ${stop_loss:.5f}",
        f"- Size: {size}",
        f"- Score: {_score}",
    ]
    if kw.get("entry_type"):
        lines.append(f"- Setup Type: {kw.get('entry_type')}")
    if kw.get("expected_hold_min") is not None:
        lines.append(f"- Expected Hold: {_fmt_hold(float(kw.get('expected_hold_min') or 0))}")
    if kw.get("ai_action"):
        lines.append(
            f"- AI View: {kw.get('ai_action')} ({float(kw.get('ai_confidence') or 0):.2f})"
        )
    if kw.get("ai_reasoning"):
        lines.append(f"- Reasoning: {str(kw.get('ai_reasoning')).strip()[:600]}")
    if kw.get("margin_reason"):
        lines.append(f"- Margin Context: {str(kw.get('margin_reason')).strip()[:280]}")
    lines.append(f"- Logged: {_now_pt()}")
    text = "\n".join(lines)
    _send_canvas(
        text,
        f"{direction.upper()} Entry Alert",
        "xlmbot",
        metadata={
            "report_kind": "trade_entry",
            "direction": direction,
            "product_id": product_id,
            "size": size,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "score": kw.get("score"),
            "entry_type": kw.get("entry_type"),
            "ai_action": kw.get("ai_action"),
        },
    )

def trade_exit(direction: str, exit_reason: str, entry_price: float, exit_price: float, pnl_usd: float | None, **kw) -> None:
    _flavor = _belfort_exit_flavor(pnl_usd, exit_reason)
    lines = [
        f"# Trade Exit: {direction.upper()}",
        "",
        f"> {_flavor}",
        "",
        f"- Exit Reason: {exit_reason}",
        f"- Price Path: ${entry_price:.5f} -> ${exit_price:.5f}",
        f"- PnL: {_fmt_usd(pnl_usd)}",
    ]
    if kw.get("pnl_pct") is not None:
        lines.append(f"- PnL %: {_fmt_pct(float(kw.get('pnl_pct') or 0))}")
    if kw.get("held_min") is not None:
        lines.append(f"- Held: {_fmt_hold(float(kw.get('held_min') or 0))}")
    if kw.get("expected_hold_min") is not None:
        lines.append(f"- Expected Hold: {_fmt_hold(float(kw.get('expected_hold_min') or 0))}")
    if kw.get("ai_exit_urgency"):
        lines.append(f"- AI Exit Urgency: {kw.get('ai_exit_urgency')}")
    if kw.get("ai_exit_reasoning"):
        lines.append(f"- Exit Reasoning: {str(kw.get('ai_exit_reasoning')).strip()[:600]}")
    if kw.get("runner_bars"):
        lines.append(f"- Runner Bars: {kw.get('runner_bars')}")
    lines.append(f"- Logged: {_now_pt()}")
    text = "\n".join(lines)
    _send_canvas(
        text,
        f"{direction.upper()} Exit Report",
        "xlmbot",
        metadata={
            "report_kind": "trade_exit",
            "direction": direction,
            "exit_reason": exit_reason,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "pnl_usd": pnl_usd,
            "pnl_pct": kw.get("pnl_pct"),
        },
    )

def bot_started(session_id: str = "", **kw) -> None:
    _send_canvas(
        f"Bot Session `{session_id}` Started at {_now_pt()}",
        "Bot Lifecycle: Started",
        "xlmbot",
        metadata={"report_kind": "bot_started", "session_id": session_id},
    )

def bot_error(error_type: str, details: str = "") -> None:
    _send_canvas(
        f"ERROR: {error_type}\n{details}",
        "System Error Alert",
        "xlmbot",
        metadata={"report_kind": "bot_error", "error_type": error_type},
    )

def daily_summary(trades: int = 0, pnl_usd: float = 0, **kw) -> None:
    if pnl_usd >= 50:
        _daily_flavor = "Monster day. The market paid us. We showed up and we collected."
    elif pnl_usd > 0:
        _daily_flavor = "Green day. Stack the wins. Consistency is the game."
    elif pnl_usd == 0 and trades == 0:
        _daily_flavor = "Zero trades, zero dollars. Can't win if you don't play. Tomorrow we show up."
    elif pnl_usd < -20:
        _daily_flavor = "Tough day. Cost of tuition. We learn, we adapt, we come back stronger."
    else:
        _daily_flavor = "Small red. Part of the game. The edge plays out over time."
    text = f"DAILY SUMMARY\n\n> {_daily_flavor}\n\n• Trades: {trades}\n• PnL: {_fmt_usd(pnl_usd)}\n• {_now_pt()}"
    _send_canvas(
        text,
        "Daily Performance Report",
        "xlmbot",
        metadata={"report_kind": "daily_summary", "trades": trades, "pnl_usd": pnl_usd},
    )

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
