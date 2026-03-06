#!/usr/bin/env python3
"""
Risk Management Module - Optimized for profitability
"""

import logging
from typing import Dict, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class RiskManager:
    """
    Smart Risk Management

    Key Rules:
    1. Never risk more than 1% of account per trade
    2. Minimum 2:1 reward-to-risk ratio
    3. Max 2 open positions at once
    4. Daily loss limit = 3 losing trades worth
    5. Trailing stops to protect profits
    """

    def __init__(self, config: dict):
        self.config = config
        self.daily_pnl = 0.0
        self.daily_trades = 0
        self.wins = 0
        self.losses = 0
        self.total_pnl = 0.0
        self.open_positions = []
        self.last_reset = datetime.now().date()

    def validate_trade(self, signal: dict) -> tuple[bool, str]:
        """
        Validate trade against risk rules
        Returns (allowed, reason)
        """
        self._check_daily_reset()

        # Emergency stop
        if self.config.get("emergency_stop", False):
            return False, "Emergency stop active"

        # Daily loss limit
        max_daily_loss = self.config.get("max_daily_loss_usd", 150)
        if self.daily_pnl <= -max_daily_loss:
            return False, f"Daily loss limit reached (${self.daily_pnl:.2f})"

        # Max open positions
        max_positions = self.config.get("max_open_positions", 2)
        if len(self.open_positions) >= max_positions:
            return False, f"Max positions reached ({len(self.open_positions)}/{max_positions})"

        # Check reward:risk ratio
        if "stop_loss" in signal and "take_profit" in signal:
            entry = signal.get("price") or signal.get("current_price", 0)
            if entry:
                risk = abs(entry - signal["stop_loss"])
                reward = abs(signal["take_profit"] - entry)

                if risk > 0:
                    rr_ratio = reward / risk
                    min_rr = self.config.get("min_reward_risk_ratio", 2.0)

                    if rr_ratio < min_rr:
                        return False, f"R:R too low ({rr_ratio:.1f}:1, need {min_rr}:1)"

        return True, "Trade approved"

    def calculate_position_size(self, entry: float, stop_loss: float, account_balance: float) -> float:
        """
        Calculate position size based on risk

        Risk 1% of account per trade
        Position size = (Account * Risk%) / (Entry - Stop)
        """
        risk_percent = self.config.get("max_risk_per_trade_percent", 1.0)
        risk_amount = account_balance * (risk_percent / 100)

        price_risk = abs(entry - stop_loss)
        if price_risk == 0:
            return 0

        # Position size in base currency
        position_size = risk_amount / price_risk

        # Convert to USD value
        position_usd = position_size * entry

        # Cap at lot size from config
        max_lot = self.config.get("max_lot_size_usd", 1000)
        return min(position_usd, max_lot)

    def record_trade_result(self, pnl: float, strategy: str):
        """Record completed trade"""
        self.daily_pnl += pnl
        self.total_pnl += pnl
        self.daily_trades += 1

        if pnl > 0:
            self.wins += 1
            logger.info(f"WIN: +${pnl:.2f} ({strategy})")
        else:
            self.losses += 1
            logger.info(f"LOSS: ${pnl:.2f} ({strategy})")

        # Log stats
        win_rate = self.wins / max(1, self.wins + self.losses) * 100
        logger.info(f"Stats: {self.wins}W/{self.losses}L ({win_rate:.0f}%), Daily: ${self.daily_pnl:.2f}")

    def add_position(self, position: dict):
        """Track open position"""
        self.open_positions.append(position)

    def remove_position(self, position_id: str):
        """Remove closed position"""
        self.open_positions = [p for p in self.open_positions if p.get("id") != position_id]

    def should_move_to_breakeven(self, entry: float, current: float, side: str) -> bool:
        """Check if stop should move to breakeven"""
        breakeven_trigger = self.config.get("break_even_at_percent", 1.5)

        if side == "buy":
            profit_percent = (current - entry) / entry * 100
        else:
            profit_percent = (entry - current) / entry * 100

        return profit_percent >= breakeven_trigger

    def calculate_trailing_stop(self, entry: float, current: float, side: str, current_stop: float) -> float:
        """Calculate new trailing stop"""
        if not self.config.get("use_trailing_stops", True):
            return current_stop

        trail_percent = self.config.get("trailing_stop_percent", 1.0)

        if side == "buy":
            # Trail below current price
            new_stop = current * (1 - trail_percent / 100)
            # Only move stop up, never down
            return max(current_stop, new_stop, entry)  # At least breakeven
        else:
            new_stop = current * (1 + trail_percent / 100)
            return min(current_stop, new_stop, entry)

    def _check_daily_reset(self):
        """Reset daily counters at midnight"""
        if datetime.now().date() > self.last_reset:
            logger.info(f"Daily reset. Yesterday: ${self.daily_pnl:.2f}, {self.daily_trades} trades")
            self.daily_pnl = 0.0
            self.daily_trades = 0
            self.last_reset = datetime.now().date()

    def get_stats(self) -> dict:
        """Get performance stats"""
        total_trades = self.wins + self.losses
        win_rate = self.wins / max(1, total_trades) * 100

        return {
            "total_pnl": self.total_pnl,
            "daily_pnl": self.daily_pnl,
            "wins": self.wins,
            "losses": self.losses,
            "win_rate": win_rate,
            "open_positions": len(self.open_positions),
            "daily_trades": self.daily_trades
        }

    def get_status(self) -> dict:
        """Quick status check"""
        return {
            "can_trade": self.validate_trade({})[0],
            "daily_pnl": self.daily_pnl,
            "open_positions": len(self.open_positions),
            "emergency_stop": self.config.get("emergency_stop", False)
        }
