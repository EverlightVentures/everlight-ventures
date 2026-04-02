"""Trading Mindset -- The bot's ideology and work ethic.

Losses aren't losses -- they're tuition. Every bad trade becomes a lesson.
The bot doesn't dwell, it FIXES. Then gets the money back plus interest.

This isn't about emotion. It's about efficiency. The math works.
If the bot is sitting on its hands while money walks away, that's
a system failure, not a market problem. The bot should be HUNGRIER.

Mindset modes:
  GRIND: Behind. Work smarter not harder. Don't force but DON'T sit out.
         Find the edge and execute. Get it back plus interest.
  STEADY: On track. Good. Now double it. Never satisfied.
  CRUISE: Ahead. This is what it's supposed to look like.
          Don't get comfortable. There's more.
  BEAST: Crushing it. Don't coast. $200 today means aim for $500.
         Always hungry, never satisfied, disciplined about HOW you hunt.
"""
from __future__ import annotations


def compute_mindset(
    daily_pnl: float = 0,
    daily_min_goal: float = 25,
    daily_ideal_goal: float = 100,
    loss_debt: float = 0,
    consecutive_losses: int = 0,
    consecutive_wins: int = 0,
    trades_today: int = 0,
    wins_today: int = 0,
    losses_today: int = 0,
) -> dict:
    pnl = daily_pnl
    goal_pct = (pnl / daily_min_goal * 100) if daily_min_goal > 0 else 0

    all_strats = [
        "htf_swing", "range_fvg_retest", "breakout_retest", "trend_continuation",
        "fib_retrace", "hourly_continuation", "pullback", "wick_rejection",
        "compression_range", "micro_sweep", "liquidity_sweep",
    ]
    proven_strats = [
        "htf_swing", "range_fvg_retest", "breakout_retest", "trend_continuation",
        "fib_retrace", "hourly_continuation",
    ]

    # === BEAST: $100+ day. Don't coast. There's more. ===
    if pnl >= daily_ideal_goal:
        return {
            "mode": "BEAST",
            "threshold_adj": -3,  # slight edge -- earned it
            "size_mult": 1.15,    # can push slightly harder
            "stop_width_mult": 1.2,  # let winners breathe more
            "allowed_strategies": all_strats,
            "message": f"BEAST: ${pnl:.0f} today. This is what it looks like. Don't get comfortable. There's more.",
            "work_ethic": 90,
            "protect_bag": pnl >= 250,  # only protect at $250+
            "goal_pct": round(goal_pct, 1),
            "ideology": "Always hungry. Never satisfied. Disciplined about HOW you hunt.",
        }

    # === CRUISE: met daily min. Good. Now double it. ===
    if pnl >= daily_min_goal * 0.75:
        return {
            "mode": "CRUISE",
            "threshold_adj": -2,
            "size_mult": 1.0,
            "stop_width_mult": 1.1,
            "allowed_strategies": all_strats,
            "message": f"CRUISE: ${pnl:.0f} / ${daily_min_goal:.0f}. Good. Now double it.",
            "work_ethic": 75,
            "protect_bag": False,
            "goal_pct": round(goal_pct, 1),
            "ideology": "On track doesn't mean done. Push for ideal.",
        }

    # === GRIND: behind. Work smarter. Don't sit out. Get it back + interest. ===
    if pnl < 0 or consecutive_losses >= 2:
        # Don't over-restrict. "Don't force but DON'T sit out either."
        # Small threshold raise (not huge), keep size reasonable
        # After a loss: "What did I miss? Fix it. Get it back plus interest."
        streak_adj = min(10, consecutive_losses * 2)  # max +10 after 5 losses
        size_cut = max(0.7, 1.0 - consecutive_losses * 0.05)  # max 30% cut

        # But don't cripple the bot. It needs to trade to recover.
        # "Don't force but DON'T sit out" = moderate threshold, not extreme
        if consecutive_losses >= 5:
            msg = f"GRIND: ${pnl:.0f} | {consecutive_losses}L streak. What are we missing? Time to adapt, not quit."
        elif consecutive_losses >= 3:
            msg = f"GRIND: ${pnl:.0f} | {consecutive_losses}L. Tuition paid. Get it back plus interest."
        else:
            msg = f"GRIND: ${pnl:.0f} behind. Find the edge. Execute. Don't sit out."

        return {
            "mode": "GRIND",
            "threshold_adj": streak_adj,
            "size_mult": size_cut,
            "stop_width_mult": 0.9,  # slightly tighter, not crippling
            "allowed_strategies": proven_strats if consecutive_losses >= 4 else all_strats,
            "message": msg,
            "work_ethic": min(100, 60 + consecutive_losses * 8),
            "protect_bag": False,
            "goal_pct": round(goal_pct, 1),
            "ideology": "Losses are tuition. Learn. Fix. Get it back plus interest.",
        }

    # === STEADY: normal. Execute the plan. ===
    return {
        "mode": "STEADY",
        "threshold_adj": 0,
        "size_mult": 1.0,
        "stop_width_mult": 1.0,
        "allowed_strategies": all_strats,
        "message": f"STEADY: ${pnl:.0f} / ${daily_min_goal:.0f}. Plan is working. Execute. Don't overthink.",
        "work_ethic": 65,
        "protect_bag": False,
        "goal_pct": round(goal_pct, 1),
        "ideology": "The math works. Trust the system. Execute.",
    }
