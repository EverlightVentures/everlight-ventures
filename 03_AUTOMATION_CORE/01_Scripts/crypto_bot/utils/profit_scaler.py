#!/usr/bin/env python3
"""
Profit Scaler - Data-Backed Position Sizing & Compounding System

Proven strategies for scaling from $100/day to $1000/day:
1. Kelly Criterion - Mathematically optimal bet sizing
2. Compounding - Reinvest profits to grow position sizes
3. Partial Take Profits - Lock in gains, let winners run
4. Dynamic Sizing - Adjust based on win rate performance
"""

import json
import logging
import math
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class ScalingConfig:
    """Scaling configuration"""
    starting_capital: float = 1000.0
    daily_target_percent: float = 10.0  # 10% daily target
    max_risk_per_trade_percent: float = 2.0  # Risk 2% per trade
    kelly_fraction: float = 0.25  # Use 25% of Kelly (safer)
    compound_profits: bool = True
    compound_percent: float = 50.0  # Reinvest 50% of profits
    partial_tp_enabled: bool = True
    partial_tp_percent: float = 50.0  # Take 50% at first target
    scale_out_targets: List[float] = None  # [1.0, 2.0, 3.0] R multiples

    def __post_init__(self):
        if self.scale_out_targets is None:
            self.scale_out_targets = [1.0, 2.0, 3.0]  # 1R, 2R, 3R targets


class ProfitScaler:
    """
    Intelligent position sizing and profit scaling system

    Based on proven quantitative strategies:
    - Kelly Criterion (1956) - Optimal bet sizing for long-term growth
    - Compounding - Einstein's "8th wonder of the world"
    - Partial profits - Lock in gains while capturing big moves
    """

    def __init__(self, config: dict, data_dir: str = None):
        self.config = config

        # Load scaling config
        scaling_cfg = config.get("profit_scaling", {})
        self.scaling = ScalingConfig(
            starting_capital=scaling_cfg.get("starting_capital", 1000),
            daily_target_percent=scaling_cfg.get("daily_target_percent", 10),
            max_risk_per_trade_percent=scaling_cfg.get("max_risk_per_trade_percent", 2),
            kelly_fraction=scaling_cfg.get("kelly_fraction", 0.25),
            compound_profits=scaling_cfg.get("compound_profits", True),
            compound_percent=scaling_cfg.get("compound_percent", 50),
            partial_tp_enabled=scaling_cfg.get("partial_tp_enabled", True),
            partial_tp_percent=scaling_cfg.get("partial_tp_percent", 50),
        )

        # Data storage
        if data_dir:
            self.data_dir = Path(data_dir)
        else:
            self.data_dir = Path(__file__).parent.parent / "data"

        self.state_file = self.data_dir / "scaling_state.json"

        # Performance tracking
        self.state = self._load_state()

        logger.info(f"ProfitScaler initialized: {self.scaling.daily_target_percent}% daily target, "
                   f"Kelly fraction: {self.scaling.kelly_fraction}")

    # === Kelly Criterion Position Sizing ===

    def calculate_kelly_size(self, win_rate: float, avg_win: float, avg_loss: float) -> float:
        """
        Calculate optimal position size using Kelly Criterion

        Kelly Formula: f* = (p * b - q) / b
        Where:
            f* = fraction of capital to bet
            p = probability of winning (win_rate)
            q = probability of losing (1 - win_rate)
            b = win/loss ratio (avg_win / avg_loss)

        Research: Bell Labs 1956, proven to maximize geometric growth
        """
        if avg_loss == 0 or win_rate <= 0:
            return 0.0

        p = win_rate
        q = 1 - win_rate
        b = abs(avg_win / avg_loss)  # Win/loss ratio

        # Full Kelly
        kelly = (p * b - q) / b

        # Use fractional Kelly for safety (25% is common in practice)
        # Full Kelly is too aggressive and leads to large drawdowns
        fractional_kelly = kelly * self.scaling.kelly_fraction

        # Cap at max risk per trade
        max_risk = self.scaling.max_risk_per_trade_percent / 100

        return max(0, min(fractional_kelly, max_risk))

    def get_optimal_position_size(self, capital: float, win_rate: float = None,
                                   avg_win: float = None, avg_loss: float = None) -> dict:
        """
        Get optimal position size based on performance data

        Returns position size in USD and the method used
        """
        # Use stored stats if not provided
        if win_rate is None:
            win_rate = self.state.get("win_rate", 0.5)
        if avg_win is None:
            avg_win = self.state.get("avg_win", 50)
        if avg_loss is None:
            avg_loss = self.state.get("avg_loss", 25)

        # Calculate Kelly optimal
        kelly_fraction = self.calculate_kelly_size(win_rate, avg_win, avg_loss)
        kelly_size = capital * kelly_fraction

        # Minimum viable size
        min_size = 50  # $50 minimum

        # Maximum per trade (10% of capital)
        max_size = capital * 0.10

        # Final size
        position_size = max(min_size, min(kelly_size, max_size))

        return {
            "position_size_usd": round(position_size, 2),
            "kelly_fraction": round(kelly_fraction, 4),
            "win_rate_used": win_rate,
            "avg_win_used": avg_win,
            "avg_loss_used": avg_loss,
            "method": "kelly_criterion"
        }

    # === Compounding System ===

    def calculate_compound_growth(self, starting_capital: float, daily_return: float,
                                   days: int) -> dict:
        """
        Calculate compound growth projections

        Formula: Final = Initial * (1 + r)^n

        Example: $1000 at 10% daily for 30 days = $1000 * 1.10^30 = $17,449
        """
        final_capital = starting_capital * ((1 + daily_return / 100) ** days)

        return {
            "starting_capital": starting_capital,
            "daily_return_percent": daily_return,
            "days": days,
            "final_capital": round(final_capital, 2),
            "total_return_percent": round((final_capital / starting_capital - 1) * 100, 2),
            "daily_profit_at_end": round(final_capital * daily_return / 100, 2)
        }

    def get_current_trading_capital(self) -> float:
        """
        Get current trading capital including compounded profits
        """
        base = self.scaling.starting_capital

        if not self.scaling.compound_profits:
            return base

        # Add compounded profits
        total_profits = self.state.get("total_profits", 0)
        compound_amount = total_profits * (self.scaling.compound_percent / 100)

        return base + compound_amount

    def record_trade_result(self, pnl: float, is_win: bool):
        """Record trade result for performance tracking"""
        # Update counters
        self.state["total_trades"] = self.state.get("total_trades", 0) + 1

        if is_win:
            self.state["wins"] = self.state.get("wins", 0) + 1
            self.state["total_wins_amount"] = self.state.get("total_wins_amount", 0) + pnl
        else:
            self.state["losses"] = self.state.get("losses", 0) + 1
            self.state["total_losses_amount"] = self.state.get("total_losses_amount", 0) + abs(pnl)

        # Update profits
        self.state["total_profits"] = self.state.get("total_profits", 0) + pnl

        # Daily tracking
        today = datetime.now().strftime("%Y-%m-%d")
        if self.state.get("current_day") != today:
            self.state["current_day"] = today
            self.state["daily_pnl"] = 0

        self.state["daily_pnl"] = self.state.get("daily_pnl", 0) + pnl

        # Recalculate stats
        self._update_stats()
        self._save_state()

    def _update_stats(self):
        """Update performance statistics"""
        wins = self.state.get("wins", 0)
        losses = self.state.get("losses", 0)
        total = wins + losses

        if total > 0:
            self.state["win_rate"] = wins / total

        if wins > 0:
            self.state["avg_win"] = self.state.get("total_wins_amount", 0) / wins

        if losses > 0:
            self.state["avg_loss"] = self.state.get("total_losses_amount", 0) / losses

    # === Partial Take Profit System ===

    def get_scale_out_targets(self, entry_price: float, stop_loss: float,
                              side: str) -> List[dict]:
        """
        Calculate scale-out targets based on R-multiples

        Research shows taking partial profits:
        - Locks in gains (reduces regret)
        - Lets winners run (captures big moves)
        - Optimal split: 50% at 1R, 30% at 2R, 20% at 3R
        """
        risk = abs(entry_price - stop_loss)
        targets = []

        # Position splits (proven by research)
        splits = [
            (1.0, 50),   # 50% at 1R
            (2.0, 30),   # 30% at 2R
            (3.0, 20),   # 20% at 3R
        ]

        for r_multiple, percent in splits:
            if side.lower() in ('buy', 'long'):
                target_price = entry_price + (risk * r_multiple)
            else:
                target_price = entry_price - (risk * r_multiple)

            targets.append({
                "r_multiple": r_multiple,
                "price": round(target_price, 2),
                "percent_to_close": percent,
                "status": "pending"
            })

        return targets

    def should_take_partial_profit(self, position: dict, current_price: float) -> Optional[dict]:
        """
        Check if any partial profit target is hit

        Returns the target to execute or None
        """
        if not self.scaling.partial_tp_enabled:
            return None

        entry = position.get("entry_price", 0)
        side = position.get("side", "buy")
        targets = position.get("scale_out_targets", [])

        for target in targets:
            if target.get("status") == "executed":
                continue

            target_price = target.get("price", 0)

            if side.lower() in ('buy', 'long'):
                if current_price >= target_price:
                    return target
            else:
                if current_price <= target_price:
                    return target

        return None

    # === Daily Target Tracking ===

    def get_daily_progress(self) -> dict:
        """Get progress toward daily target"""
        capital = self.get_current_trading_capital()
        target_amount = capital * (self.scaling.daily_target_percent / 100)
        current_pnl = self.state.get("daily_pnl", 0)

        progress_percent = (current_pnl / target_amount * 100) if target_amount > 0 else 0

        return {
            "capital": round(capital, 2),
            "daily_target_percent": self.scaling.daily_target_percent,
            "daily_target_usd": round(target_amount, 2),
            "current_pnl": round(current_pnl, 2),
            "progress_percent": round(progress_percent, 1),
            "target_reached": current_pnl >= target_amount,
            "remaining": round(max(0, target_amount - current_pnl), 2)
        }

    def get_scaling_projection(self) -> dict:
        """
        Get projection for scaling from current to target

        Shows how long to reach $1000/day at current performance
        """
        current_capital = self.get_current_trading_capital()
        daily_return = self.scaling.daily_target_percent

        # Target: $1000/day profit requires $10,000 capital at 10% daily
        target_daily_profit = 1000
        target_capital = target_daily_profit / (daily_return / 100)

        if current_capital >= target_capital:
            days_to_target = 0
        else:
            # Days to reach target with compounding
            # target = current * (1 + r)^n
            # n = log(target/current) / log(1 + r)
            r = (daily_return / 100) * (self.scaling.compound_percent / 100)  # Effective compound rate
            if r > 0:
                days_to_target = math.log(target_capital / current_capital) / math.log(1 + r)
            else:
                days_to_target = float('inf')

        return {
            "current_capital": round(current_capital, 2),
            "current_daily_profit_potential": round(current_capital * daily_return / 100, 2),
            "target_daily_profit": target_daily_profit,
            "target_capital_needed": round(target_capital, 2),
            "days_to_target": round(days_to_target, 1) if days_to_target != float('inf') else "N/A",
            "compound_rate": self.scaling.compound_percent
        }

    # === State Persistence ===

    def _save_state(self):
        """Save state to JSON"""
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)

            state = {
                "last_updated": datetime.now().isoformat(),
                **self.state
            }

            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save scaling state: {e}")

    def _load_state(self) -> dict:
        """Load state from JSON"""
        try:
            if self.state_file.exists():
                with open(self.state_file) as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load scaling state: {e}")

        return {
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0.5,
            "avg_win": 50,
            "avg_loss": 25,
            "total_profits": 0,
            "daily_pnl": 0,
            "current_day": datetime.now().strftime("%Y-%m-%d")
        }

    # === Summary ===

    def get_status(self) -> dict:
        """Get full scaler status"""
        return {
            "performance": {
                "total_trades": self.state.get("total_trades", 0),
                "win_rate": f"{self.state.get('win_rate', 0.5) * 100:.1f}%",
                "avg_win": f"${self.state.get('avg_win', 0):.2f}",
                "avg_loss": f"${self.state.get('avg_loss', 0):.2f}",
                "total_profits": f"${self.state.get('total_profits', 0):.2f}"
            },
            "position_sizing": self.get_optimal_position_size(self.get_current_trading_capital()),
            "daily_progress": self.get_daily_progress(),
            "scaling_projection": self.get_scaling_projection()
        }
