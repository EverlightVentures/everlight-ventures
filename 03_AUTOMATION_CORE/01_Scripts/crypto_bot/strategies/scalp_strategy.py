#!/usr/bin/env python3
"""
Scalping Strategy
Quick in-and-out trades on small price movements
"""

import logging
from typing import Dict, Optional
from datetime import datetime, timedelta
from collections import deque

logger = logging.getLogger(__name__)


class ScalpStrategy:
    """
    Scalping: Quick trades on small price moves
    - Enter on volume spikes or momentum
    - Small profit targets (0.3-0.5%)
    - Tight stop losses
    - Max hold time to avoid getting stuck
    """

    def __init__(self, api, config: dict, trading_pair: str):
        self.api = api
        self.config = config
        self.trading_pair = trading_pair

        # State
        self.in_position = False
        self.entry_price = None
        self.entry_time = None
        self.position_size = 0.0

        # Price/volume history for analysis
        self.price_history = deque(maxlen=60)  # Last 60 ticks
        self.volume_history = deque(maxlen=60)

    def _calculate_momentum(self) -> float:
        """Calculate short-term price momentum"""
        if len(self.price_history) < 10:
            return 0.0

        recent = list(self.price_history)[-10:]
        older = list(self.price_history)[-20:-10] if len(self.price_history) >= 20 else recent

        recent_avg = sum(recent) / len(recent)
        older_avg = sum(older) / len(older)

        return ((recent_avg - older_avg) / older_avg) * 100

    def _detect_volume_spike(self) -> bool:
        """Detect if current volume is above threshold"""
        if len(self.volume_history) < 20:
            return False

        recent_vol = list(self.volume_history)[-5:]
        avg_vol = sum(list(self.volume_history)[:-5]) / max(1, len(self.volume_history) - 5)

        current_vol = sum(recent_vol) / len(recent_vol)

        return current_vol > (avg_vol * self.config["volume_spike_threshold"])

    def _check_entry(self, price: float) -> Optional[dict]:
        """Check for scalp entry conditions"""
        momentum = self._calculate_momentum()
        volume_spike = self._detect_volume_spike()

        # Entry conditions:
        # 1. Positive momentum + volume spike (bullish)
        # 2. Strong momentum alone

        if volume_spike and momentum > 0.1:
            return {
                "action": "buy",
                "side": "buy",
                "pair": self.trading_pair,
                "amount": 50,  # USD amount
                "price": None,  # Market
                "reason": f"Scalp entry: momentum={momentum:.2f}%, volume spike",
                "strategy": "scalp"
            }

        return None

    def _check_exit(self, price: float) -> Optional[dict]:
        """Check for scalp exit conditions"""
        if not self.in_position or not self.entry_price:
            return None

        # Calculate P&L
        pnl_percent = ((price - self.entry_price) / self.entry_price) * 100
        hold_time = datetime.now() - self.entry_time
        hold_minutes = hold_time.total_seconds() / 60

        # Take profit
        if pnl_percent >= self.config["profit_target_percent"]:
            logger.info(f"Scalp: Take profit at {pnl_percent:.2f}%")
            return self._create_exit_signal(price, f"Take profit: {pnl_percent:.2f}%")

        # Stop loss (negative of profit target)
        stop_loss = -self.config["profit_target_percent"] * 1.5
        if pnl_percent <= stop_loss:
            logger.info(f"Scalp: Stop loss at {pnl_percent:.2f}%")
            return self._create_exit_signal(price, f"Stop loss: {pnl_percent:.2f}%")

        # Max hold time exceeded
        if hold_minutes >= self.config["max_hold_minutes"]:
            logger.info(f"Scalp: Max hold time reached ({hold_minutes:.0f} min)")
            return self._create_exit_signal(price, f"Max hold time: {hold_minutes:.0f} min")

        return None

    def _create_exit_signal(self, price: float, reason: str) -> dict:
        """Create exit/sell signal"""
        return {
            "action": "sell",
            "side": "sell",
            "pair": self.trading_pair,
            "amount": self.position_size,
            "price": None,  # Market
            "reason": reason,
            "strategy": "scalp"
        }

    def analyze(self, market_data: dict) -> Optional[dict]:
        """Main scalp analysis"""
        current_price = market_data["price"]

        # Update history
        self.price_history.append(current_price)
        # Note: In real implementation, fetch volume from API
        # self.volume_history.append(market_data.get("volume", 0))

        # If in position, check exit
        if self.in_position:
            exit_signal = self._check_exit(current_price)
            if exit_signal:
                self.in_position = False
                self.entry_price = None
                return exit_signal
            return {"action": "hold", "reason": "In scalp position"}

        # Check entry
        entry_signal = self._check_entry(current_price)
        if entry_signal:
            self.in_position = True
            self.entry_price = current_price
            self.entry_time = datetime.now()
            return entry_signal

        return {"action": "hold", "reason": "No scalp opportunity"}

    def get_status(self) -> dict:
        """Get strategy status"""
        return {
            "in_position": self.in_position,
            "entry_price": self.entry_price,
            "position_size": self.position_size,
            "momentum": self._calculate_momentum()
        }
