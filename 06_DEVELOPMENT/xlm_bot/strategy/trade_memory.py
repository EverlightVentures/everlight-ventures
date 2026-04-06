"""Trade Memory -- learns from recent trades and adapts scoring in real time.

A legendary trader remembers what just happened and adjusts. This module:
1. Tracks what setups failed and WHY (post-trade analysis)
2. Penalizes repeating a failed setup at the same price zone
3. Boosts the opposite direction after same-direction consecutive losses
4. Adjusts the unified scorer based on per-strategy win rates
5. Recognizes when a reversal bounce is overdue after a directional run
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TradeMemoryResult:
    """Adjustments to apply to the unified scorer based on trade history."""
    # Score modifiers
    same_setup_penalty: int = 0       # penalty for repeating a recently-failed setup
    direction_fatigue: int = 0        # penalty for same-direction after consecutive losses
    reversal_bonus: int = 0           # bonus for opposite direction (bounce overdue)
    strategy_track_record: int = 0    # bonus/penalty based on strategy win rate
    loss_recovery_boost: int = 0      # boost to quality threshold after losses

    # Recommendations
    block_same_setup: bool = False     # hard block: exact same setup just failed
    preferred_direction: str = ""      # "long" or "short" or "" -- hint from memory
    min_score_override: int = 0        # raise minimum score after losses (be pickier)

    reasons: list[str] = field(default_factory=list)

    @property
    def total_modifier(self) -> int:
        return (self.same_setup_penalty + self.direction_fatigue +
                self.reversal_bonus + self.strategy_track_record +
                self.loss_recovery_boost)


def evaluate_trade_memory(
    *,
    # Current trade proposal
    direction: str = "",
    entry_type: str = "",
    price: float = 0,

    # Recent history from state
    last_exit_direction: str = "",
    last_exit_result: str = "",
    last_exit_entry_type: str = "",
    last_exit_price: float = 0,
    last_exit_pnl: float = 0,
    consecutive_losses: int = 0,
    consecutive_same_dir_losses: int = 0,

    # Per-strategy stats
    lane_stats: dict[str, Any] | None = None,

    # Adaptive direction history (last N trades)
    direction_history: list[dict] | None = None,

    # ATR for zone comparison
    atr_value: float = 0,
) -> TradeMemoryResult:
    """Evaluate trade memory and return score adjustments."""
    result = TradeMemoryResult()
    lane_stats = lane_stats or {}
    direction_history = direction_history or []

    # 1. SAME SETUP PENALTY
    # If the last trade was the same strategy + same direction and it lost,
    # penalize re-entering that exact setup. The market just said NO to this.
    if (last_exit_result == "loss"
        and entry_type == last_exit_entry_type
        and direction == last_exit_direction):
        # Check if we're in the same price zone (within 1 ATR)
        zone_dist = abs(price - last_exit_price) / max(atr_value, 0.0001) if atr_value > 0 and last_exit_price > 0 else 0
        if zone_dist < 2.0:  # within 2 ATR = same zone
            result.same_setup_penalty = -15
            result.reasons.append(
                f"{entry_type} {direction} just failed at ${last_exit_price:.5f} "
                f"(lost ${abs(last_exit_pnl):.2f}). Same zone. Find a different edge."
            )
            if zone_dist < 0.5:
                # Exact same spot -- hard block
                result.block_same_setup = True
                result.same_setup_penalty = -25
                result.reasons.append("Exact same setup + zone. Blocked. Wait for structure to change.")

    # 2. DIRECTION FATIGUE -- removed
    # Directions aren't penalized. The bot should trade any direction
    # if the setup is strong. The market doesn't care about our history.

    # 3. REVERSAL BONUS -- removed
    # No artificial boost for opposite direction. Let the signals speak.

    # 4. STRATEGY TRACK RECORD
    # If a strategy has a terrible win rate over recent trades, penalize it.
    # If it has a great win rate, boost it.
    stats = lane_stats.get(entry_type, {})
    total_trades = stats.get("trades", 0)
    if total_trades >= 3:  # need at least 3 trades to judge
        wr = stats.get("wins", 0) / total_trades
        avg_pnl = stats.get("total_pnl", 0) / total_trades
        if wr < 0.30 and avg_pnl < 0:
            penalty = min(12, int((0.30 - wr) * 40))
            result.strategy_track_record = -penalty
            result.reasons.append(
                f"{entry_type} has {wr:.0%} win rate over {total_trades} trades "
                f"(avg ${avg_pnl:.2f}). Penalizing by {penalty}."
            )
        elif wr > 0.55 and avg_pnl > 0:
            bonus = min(8, int((wr - 0.55) * 30))
            result.strategy_track_record = bonus
            result.reasons.append(
                f"{entry_type} has {wr:.0%} win rate. Bonus +{bonus}."
            )

    # 5. LOSS RECOVERY -- BE PICKIER
    # After consecutive losses, raise the bar. Don't take marginal setups.
    # A legendary trader gets MORE selective after losses, not less.
    if consecutive_losses >= 3:
        result.min_score_override = min(75, 60 + consecutive_losses * 3)
        result.loss_recovery_boost = -5  # general caution
        result.reasons.append(
            f"{consecutive_losses} consecutive losses. Raising minimum score to "
            f"{result.min_score_override}. Only take strong setups to recover."
        )
    elif consecutive_losses >= 2:
        result.min_score_override = 65
        result.reasons.append(
            f"{consecutive_losses} losses in a row. Minimum score raised to 65."
        )

    return result


def count_consecutive_same_dir_losses(direction_history: list[dict], direction: str) -> int:
    """Count how many of the most recent trades lost in the given direction."""
    count = 0
    for trade in reversed(direction_history):
        if trade.get("dir") == direction and trade.get("result") == "loss":
            count += 1
        else:
            break
    return count
