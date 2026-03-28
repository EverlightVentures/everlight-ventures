"""
Self-Awareness Engine -- XLM Bot
Adapts bot behavior based on its own performance patterns.
Pure introspection: lane win rates, time-of-day edges, streak management.
"""

from typing import Dict, Any


def lane_performance_auto_tuner(state: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Track win rate and avg PnL per entry lane.
    Recommends boosting, reducing, or disabling lanes based on historical performance.
    Lanes with < 10 trades are left at neutral -- not enough data to judge.
    """
    lane_stats = state.get("lane_stats") or {}

    lane_adjustments = {}
    disabled_lanes = []
    boosted_lanes = []

    for lane, stats in lane_stats.items():
        wins = stats.get("wins", 0)
        losses = stats.get("losses", 0)
        total_pnl = stats.get("total_pnl", 0.0)
        trades = stats.get("trades", wins + losses)

        if trades < 10:
            # Not enough data -- keep neutral
            lane_adjustments[lane] = {
                "action": "neutral",
                "score_adj": 0,
                "win_rate": (wins / trades) if trades > 0 else 0.0,
                "trades": trades,
                "reason": "insufficient_data",
            }
            continue

        win_rate = wins / trades if trades > 0 else 0.0

        if win_rate < 0.35:
            action = "disable"
            score_adj = -20
            disabled_lanes.append(lane)
        elif win_rate < 0.50:
            action = "reduce"
            score_adj = -10
        elif win_rate <= 0.60:
            action = "normal"
            score_adj = 0
        else:
            action = "boost"
            score_adj = 10
            boosted_lanes.append(lane)

        lane_adjustments[lane] = {
            "action": action,
            "score_adj": score_adj,
            "win_rate": round(win_rate, 4),
            "trades": trades,
            "total_pnl": round(total_pnl, 2),
        }

    return {
        "lane_adjustments": lane_adjustments,
        "disabled_lanes": disabled_lanes,
        "boosted_lanes": boosted_lanes,
    }


def time_of_day_performance(
    state: Dict[str, Any], config: Dict[str, Any], current_hour_pt: int
) -> Dict[str, Any]:
    """
    Track PnL by hour of day (Pacific Time).
    Returns a size multiplier and recommendation for the current hour.
    Hours with < 5 trades get neutral treatment -- not enough signal.
    """
    hourly_stats = state.get("hourly_stats") or {}
    hour_key = str(current_hour_pt)
    hour_data = hourly_stats.get(hour_key, {})

    wins = hour_data.get("wins", 0)
    losses = hour_data.get("losses", 0)
    total_pnl = hour_data.get("total_pnl", 0.0)
    trades = wins + losses

    # Default -- not enough data
    if trades < 5:
        return {
            "recommendation": "normal",
            "size_mult": 1.0,
            "current_hour": current_hour_pt,
            "hour_stats": {
                "wins": wins,
                "losses": losses,
                "win_rate": (wins / trades) if trades > 0 else 0.0,
                "trades": trades,
                "total_pnl": round(total_pnl, 2),
                "reason": "insufficient_data",
            },
        }

    win_rate = wins / trades

    if win_rate < 0.30:
        recommendation = "skip"
        size_mult = 0.0
    elif win_rate < 0.40:
        recommendation = "reduce"
        size_mult = 0.5
    elif win_rate > 0.60:
        recommendation = "press"
        size_mult = 1.25
    else:
        recommendation = "normal"
        size_mult = 1.0

    return {
        "recommendation": recommendation,
        "size_mult": size_mult,
        "current_hour": current_hour_pt,
        "hour_stats": {
            "wins": wins,
            "losses": losses,
            "win_rate": round(win_rate, 4),
            "trades": trades,
            "total_pnl": round(total_pnl, 2),
        },
    }


def loss_streak_escalation(state: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Escalating cooldown and size reduction based on consecutive losses.
    The more you lose in a row, the longer you wait and the smaller you size.
    Designed to prevent tilt-trading and drawdown spirals.
    """
    consecutive_losses = state.get("consecutive_losses", 0)
    session_losses = state.get("session_losses", consecutive_losses)

    # Use the worse of the two signals
    streak = max(consecutive_losses, session_losses)

    if streak <= 0:
        cooldown_mult = 1.0
        size_mult = 1.0
        recommendation = "normal"
    elif streak == 1:
        cooldown_mult = 1.0
        size_mult = 0.85
        recommendation = "slight_reduction"
    elif streak == 2:
        cooldown_mult = 2.0
        size_mult = 0.65
        recommendation = "reduce_and_wait"
    else:
        # 3+ losses -- max defensive posture
        cooldown_mult = 4.0
        size_mult = 0.50
        recommendation = "heavy_reduction"

    return {
        "cooldown_mult": cooldown_mult,
        "size_mult": size_mult,
        "consecutive_losses": consecutive_losses,
        "session_losses": session_losses,
        "streak_used": streak,
        "recommendation": recommendation,
    }


def win_streak_compounding(state: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Press when winning. Increase position size after consecutive wins.
    Capped at 1.75x to prevent overexposure -- never exceed 2x base size.
    The idea: when your reads are hitting, lean into them.
    """
    consecutive_wins = state.get("consecutive_wins", 0)

    if consecutive_wins <= 1:
        size_mult = 1.0
        recommendation = "normal"
    elif consecutive_wins == 2:
        size_mult = 1.25
        recommendation = "press"
    elif consecutive_wins == 3:
        size_mult = 1.50
        recommendation = "strong_press"
    else:
        # 4+ wins -- cap at 1.75x, never go above 2x
        size_mult = 1.75
        recommendation = "max_press"

    return {
        "size_mult": size_mult,
        "consecutive_wins": consecutive_wins,
        "recommendation": recommendation,
    }
