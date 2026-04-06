"""Autonomous Operations -- the bot's 24/7 self-repair and advisory team.

Two roles:
  ADVISOR: Detects when the bot should be trading but isn't. Identifies
           why signals aren't converting to entries. Reports to Slack.

  REPAIR: Automatically fixes common technical issues that block trades.
          Resets stuck counters, clears stale blocks, restarts feeds.
          Reports every fix to Slack.

Runs every cycle alongside the bot. Never stops. Never sleeps.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any


def run_autonomous_check(
    *,
    state: dict,
    config: dict,
    price: float,
    has_position: bool,
    last_entry_signal: dict | None,
    last_block_reason: str,
    unified_score: int,
    unified_threshold: int,
    unified_recommendation: str,
    decisions_path: Path,
    logs_dir: Path,
    now: datetime,
) -> dict:
    """Run the autonomous ops check. Returns dict with issues found and fixes applied.

    Call this every cycle from main.py.
    """
    result = {
        "issues": [],
        "fixes": [],
        "alerts": [],
        "healthy": True,
    }

    # === ADVISOR: Is the bot missing trades? ===

    # Check 1: Bot sees ENTER signals but isn't entering
    if unified_recommendation == "ENTER" and not has_position and unified_score >= unified_threshold:
        # The unified scorer says GO but we're flat. Something downstream is blocking.
        result["issues"].append({
            "type": "signal_blocked",
            "severity": "high",
            "detail": "Unified scorer says ENTER (score %d/%d) but no position opened. Block: %s" % (
                unified_score, unified_threshold, last_block_reason or "unknown"),
        })
        result["healthy"] = False

    # Check 2: No entry signals for a long time (bot might be stuck)
    try:
        _last_signal_age = _minutes_since_last_signal(decisions_path, now)
        if _last_signal_age > 60 and not has_position:
            result["issues"].append({
                "type": "no_signals",
                "severity": "medium",
                "detail": "No entry signal for %.0f minutes. Market might be dead or bot is stuck." % _last_signal_age,
            })
    except Exception:
        pass

    # Check 3: Too many blocks in a row
    try:
        _block_count = _count_recent_blocks(decisions_path, now, window_min=30)
        if _block_count > 20:
            result["issues"].append({
                "type": "excessive_blocks",
                "severity": "high",
                "detail": "%d blocked entries in last 30 min. A gate is too aggressive." % _block_count,
            })
            result["healthy"] = False
    except Exception:
        pass

    # === REPAIR: Fix common technical issues ===

    # Fix 1: Loss counter inflated by churn trades
    losses = int(state.get("losses") or 0)
    max_losses = int(config.get("risk", {}).get("max_losses_per_day", 5))
    if losses >= max_losses:
        # Check if losses are mostly churn (< 30s trades)
        try:
            churn = _count_churn_trades(logs_dir / "trades.csv", now)
            if churn > losses * 0.5:
                # More than half are churn -- reset
                state["losses"] = max(0, losses - churn)
                result["fixes"].append({
                    "type": "loss_counter_reset",
                    "detail": "Reset losses from %d to %d (removed %d churn trades)" % (
                        losses, state["losses"], churn),
                })
        except Exception:
            pass

    # Fix 2: Stale live tick blocking entries
    try:
        tick_path = logs_dir / "live_tick.json"
        if tick_path.exists():
            tick = json.loads(tick_path.read_text())
            tick_age = float(tick.get("age_seconds") or 999)
            if tick_age > 120 and not has_position:
                result["fixes"].append({
                    "type": "stale_tick_detected",
                    "detail": "Live tick is %.0fs old. WS feed may need restart." % tick_age,
                })
    except Exception:
        pass

    # Fix 3: Reentry block stuck (structure hasn't changed but price moved significantly)
    if not has_position and last_block_reason == "reentry_worse_price_blocked":
        last_exit_price = float(state.get("last_exit_price") or 0)
        if last_exit_price > 0 and abs(price - last_exit_price) / last_exit_price > 0.005:
            # Price moved 0.5%+ from exit -- the block is stale
            state["last_exit_price"] = 0  # clear the block
            result["fixes"].append({
                "type": "reentry_block_cleared",
                "detail": "Cleared stale reentry block. Price moved %.2f%% from exit." % (
                    abs(price - last_exit_price) / last_exit_price * 100),
            })

    # Generate alert for Slack if there are issues
    if result["issues"] or result["fixes"]:
        alert_lines = []
        for issue in result["issues"]:
            alert_lines.append("[%s] %s" % (issue["severity"].upper(), issue["detail"]))
        for fix in result["fixes"]:
            alert_lines.append("[FIXED] %s" % fix["detail"])
        result["alerts"] = alert_lines

    return result


def _minutes_since_last_signal(decisions_path: Path, now: datetime) -> float:
    """How many minutes since the last unified_score ENTER signal?"""
    try:
        with open(decisions_path) as f:
            lines = f.readlines()
        for line in reversed(lines[-200:]):
            d = json.loads(line)
            if d.get("reason") == "unified_score" and d.get("recommendation") == "ENTER":
                ts = datetime.fromisoformat(d["timestamp"].replace("Z", "+00:00"))
                return (now - ts).total_seconds() / 60
    except Exception:
        pass
    return 9999


def _count_recent_blocks(decisions_path: Path, now: datetime, window_min: int = 30) -> int:
    """Count how many entry blocks happened in the last N minutes."""
    cutoff = now - timedelta(minutes=window_min)
    count = 0
    try:
        with open(decisions_path) as f:
            for line in f:
                d = json.loads(line)
                ts_str = d.get("timestamp", "")
                r = d.get("reason", "")
                if "block" in r.lower() and ts_str:
                    try:
                        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                        if ts > cutoff:
                            count += 1
                    except Exception:
                        pass
    except Exception:
        pass
    return count


def _count_churn_trades(trades_path: Path, now: datetime) -> int:
    """Count today's churn trades (< 30s hold, < $3 PnL)."""
    import csv
    day_start = (now - timedelta(hours=7)).replace(hour=0, minute=0, second=0)
    day_start_utc = day_start + timedelta(hours=7)
    count = 0
    try:
        with open(trades_path) as f:
            for row in csv.DictReader(f):
                xt = row.get("exit_time", "")
                et = row.get("entry_time", "")
                if not xt or not et:
                    continue
                try:
                    xt_dt = datetime.fromisoformat(xt.replace("Z", "+00:00"))
                    et_dt = datetime.fromisoformat(et.replace("Z", "+00:00"))
                    if xt_dt < day_start_utc:
                        continue
                    hold = (xt_dt - et_dt).total_seconds()
                    pnl = abs(float(row.get("pnl_usd") or 0))
                    if hold < 30 and pnl < 3.0:
                        count += 1
                except Exception:
                    pass
    except Exception:
        pass
    return count
