"""Goal Tracker -- Dynamic P&L goals with loss recovery.

Daily minimum: $25 base + accumulated losses today
Daily ideal: $100 base + accumulated losses today  
Weekly: sum of remaining daily goals this week
Monthly: sum of remaining weekly goals this month

Losses don't disappear -- they raise the bar. You have to earn back
what you lost PLUS hit the original target. That's how real traders think.
"""
from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta


GOAL_FILE = Path("/home/opc/xlm_bot/data/goal_state.json")
MONTHLY_ARCHIVE = Path("/home/opc/xlm_bot/data/monthly_pnl_archive.json")


def _load_state() -> dict:
    if GOAL_FILE.exists():
        try:
            return json.loads(GOAL_FILE.read_text())
        except Exception:
            pass
    return {}


def _save_state(state: dict):
    GOAL_FILE.parent.mkdir(parents=True, exist_ok=True)
    GOAL_FILE.write_text(json.dumps(state, indent=2))


def _today_str():
    return datetime.now(timezone(timedelta(hours=-7))).strftime("%Y-%m-%d")


def _week_str():
    now = datetime.now(timezone(timedelta(hours=-7)))
    return now.strftime("%Y-W%W")


def _month_str():
    return datetime.now(timezone(timedelta(hours=-7))).strftime("%Y-%m")


def compute_goals(
    trades_today: list = None,
    base_daily_min: float = 25.0,
    base_daily_ideal: float = 100.0,
    trading_days_per_week: int = 7,
    trading_days_per_month: int = 30,
) -> dict:
    """Compute dynamic goals based on today's P&L.

    Returns:
        daily_min_goal: $25 + losses today
        daily_ideal_goal: $100 + losses today
        daily_pnl: actual P&L today
        daily_progress_min: % toward min goal
        daily_progress_ideal: % toward ideal goal
        weekly_goal_min: remaining daily goals this week
        weekly_pnl: actual P&L this week
        weekly_progress: % toward weekly goal
        monthly_goal_min: remaining weekly goals this month
        monthly_pnl: actual P&L this month
        monthly_progress: % toward monthly goal
        loss_debt_today: how much losses added to today's goal
    """
    state = _load_state()
    today = _today_str()
    week = _week_str()
    month = _month_str()

    # Check for month/week/day rollover
    if state.get("current_month") != month:
        # Archive previous month
        prev_month = state.get("current_month")
        if prev_month and state.get("monthly_pnl", 0) != 0:
            _archive_month(prev_month, state)
        # Reset monthly
        state["current_month"] = month
        state["monthly_pnl"] = 0
        state["monthly_wins"] = 0
        state["monthly_losses"] = 0
        state["monthly_trades"] = 0
        state["weekly_pnl"] = 0
        state["daily_pnl"] = 0
        state["daily_losses"] = 0
        state["current_week"] = week
        state["current_day"] = today
        state["days_traded_this_month"] = 0

    if state.get("current_week") != week:
        state["current_week"] = week
        state["weekly_pnl"] = 0

    if state.get("current_day") != today:
        state["current_day"] = today
        state["daily_pnl"] = 0
        state["daily_losses"] = 0
        state["daily_wins_count"] = 0
        state["daily_losses_count"] = 0
        state["days_traded_this_month"] = state.get("days_traded_this_month", 0) + 1

    # Process trades
    if trades_today:
        total_pnl = 0
        total_losses = 0
        wins = 0
        losses = 0
        for t in trades_today:
            pnl = float(t.get("pnl_usd", 0) or 0)
            total_pnl += pnl
            if pnl < 0:
                total_losses += abs(pnl)
                losses += 1
            elif pnl > 0:
                wins += 1

        state["daily_pnl"] = total_pnl
        state["daily_losses"] = total_losses
        state["daily_wins_count"] = wins
        state["daily_losses_count"] = losses

        # Update weekly/monthly
        state["weekly_pnl"] = state.get("weekly_pnl", 0) + total_pnl - state.get("_last_daily_pnl", 0)
        state["monthly_pnl"] = state.get("monthly_pnl", 0) + total_pnl - state.get("_last_daily_pnl", 0)
        state["_last_daily_pnl"] = total_pnl

    daily_pnl = float(state.get("daily_pnl", 0))
    daily_losses = float(state.get("daily_losses", 0))
    weekly_pnl = float(state.get("weekly_pnl", 0))
    monthly_pnl = float(state.get("monthly_pnl", 0))

    # Dynamic goals: base + losses
    daily_min = base_daily_min + daily_losses
    daily_ideal = base_daily_ideal + daily_losses

    # Weekly: remaining trading days * daily min
    now = datetime.now(timezone(timedelta(hours=-7)))
    days_left_this_week = max(1, 7 - now.weekday())
    weekly_min = daily_min + (days_left_this_week - 1) * base_daily_min
    # Add weekly losses to weekly goal too
    weekly_losses = max(0, -weekly_pnl) if weekly_pnl < 0 else 0
    weekly_min += weekly_losses

    # Monthly: remaining days * daily min
    import calendar
    days_in_month = calendar.monthrange(now.year, now.month)[1]
    days_left_this_month = max(1, days_in_month - now.day + 1)
    monthly_min = daily_min + (days_left_this_month - 1) * base_daily_min
    monthly_losses = max(0, -monthly_pnl) if monthly_pnl < 0 else 0
    monthly_min += monthly_losses

    # Progress bars (can exceed 100%)
    daily_progress_min = (daily_pnl / daily_min * 100) if daily_min > 0 else 0
    daily_progress_ideal = (daily_pnl / daily_ideal * 100) if daily_ideal > 0 else 0
    weekly_progress = (weekly_pnl / weekly_min * 100) if weekly_min > 0 else 0
    monthly_progress = (monthly_pnl / monthly_min * 100) if monthly_min > 0 else 0

    _save_state(state)

    return {
        "daily_min_goal": round(daily_min, 2),
        "daily_ideal_goal": round(daily_ideal, 2),
        "daily_pnl": round(daily_pnl, 2),
        "daily_losses": round(daily_losses, 2),
        "daily_progress_min": round(max(-100, daily_progress_min), 1),
        "daily_progress_ideal": round(max(-100, daily_progress_ideal), 1),
        "daily_wins": state.get("daily_wins_count", 0),
        "daily_loss_count": state.get("daily_losses_count", 0),

        "weekly_min_goal": round(weekly_min, 2),
        "weekly_pnl": round(weekly_pnl, 2),
        "weekly_progress": round(max(-100, weekly_progress), 1),

        "monthly_min_goal": round(monthly_min, 2),
        "monthly_pnl": round(monthly_pnl, 2),
        "monthly_progress": round(max(-100, monthly_progress), 1),
        "monthly_trades": state.get("monthly_trades", 0),

        "loss_debt_today": round(daily_losses, 2),
        "base_daily_min": base_daily_min,
        "base_daily_ideal": base_daily_ideal,
        "today": today,
        "month": month,
    }


def _archive_month(month_str: str, state: dict):
    """Save completed month to archive for long-term analytics."""
    archive = {}
    if MONTHLY_ARCHIVE.exists():
        try:
            archive = json.loads(MONTHLY_ARCHIVE.read_text())
        except Exception:
            archive = {}

    archive[month_str] = {
        "pnl": state.get("monthly_pnl", 0),
        "trades": state.get("monthly_trades", 0),
        "wins": state.get("monthly_wins", 0),
        "losses": state.get("monthly_losses", 0),
        "days_traded": state.get("days_traded_this_month", 0),
    }

    MONTHLY_ARCHIVE.write_text(json.dumps(archive, indent=2))
