#!/usr/bin/env python3
"""
Breakout Strategy
- Trade when price breaks out of consolidation range
- Volume confirmation required
- False breakout filter
"""

import logging
from typing import Optional
from collections import deque
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class Range:
    high: float
    low: float
    periods: int


class BreakoutStrategy:
    """
    Breakout Trading: Catch big moves early

    Rules:
    1. Identify consolidation (price in tight range)
    2. Wait for breakout above/below range
    3. Confirm with volume spike
    4. Enter with stop just inside the range
    5. Target 2.5x the risk
    """

    def __init__(self, api, config: dict, trading_pair: str):
        self.api = api
        self.config = config
        self.trading_pair = trading_pair

        self.prices = deque(maxlen=100)
        self.highs = deque(maxlen=100)
        self.lows = deque(maxlen=100)
        self.volumes = deque(maxlen=50)

        self.position = None
        self.current_range: Optional[Range] = None
        self.breakout_confirmed = False

    def _find_range(self) -> Optional[Range]:
        """Find consolidation range"""
        lookback = self.config.get("lookback_periods", 20)

        if len(self.highs) < lookback:
            return None

        recent_highs = list(self.highs)[-lookback:]
        recent_lows = list(self.lows)[-lookback:]

        range_high = max(recent_highs)
        range_low = min(recent_lows)

        # Check if it's actually consolidating (range < 5% of price)
        range_percent = (range_high - range_low) / range_low * 100

        if range_percent < 5:  # Tight consolidation
            return Range(high=range_high, low=range_low, periods=lookback)

        return None

    def _check_volume_confirmation(self) -> bool:
        """Check if volume confirms breakout"""
        if len(self.volumes) < 20:
            return True  # Can't confirm, allow trade

        recent_vol = self.volumes[-1] if self.volumes else 0
        avg_vol = sum(list(self.volumes)[:-1]) / max(1, len(self.volumes) - 1)

        multiplier = self.config.get("volume_confirm_multiplier", 1.5)
        return recent_vol > avg_vol * multiplier

    def _is_false_breakout(self, price: float, direction: str) -> bool:
        """Filter out false breakouts"""
        if not self.config.get("false_breakout_filter", True):
            return False

        # Wait for candle close above/below range
        # In live trading, you'd check if current candle closed
        # Here we use a simple momentum check

        if len(self.prices) < 3:
            return True

        recent = list(self.prices)[-3:]

        if direction == "UP":
            # All 3 recent prices should be above range
            return not all(p > self.current_range.high for p in recent[-2:])
        else:
            return not all(p < self.current_range.low for p in recent[-2:])

    def analyze(self, market_data: dict) -> Optional[dict]:
        """Main analysis"""
        price = market_data["price"]
        high = market_data.get("high", price * 1.001)
        low = market_data.get("low", price * 0.999)
        volume = market_data.get("volume", 0)

        self.prices.append(price)
        self.highs.append(high)
        self.lows.append(low)
        self.volumes.append(volume)

        # Manage existing position
        if self.position:
            return self._manage_position(price)

        # Find consolidation range
        self.current_range = self._find_range()

        if not self.current_range:
            return {"action": "hold", "reason": "No consolidation range found"}

        # Check for breakout
        if price > self.current_range.high:
            if self._is_false_breakout(price, "UP"):
                return {"action": "hold", "reason": "Potential false breakout UP"}

            if not self._check_volume_confirmation():
                return {"action": "hold", "reason": "No volume confirmation"}

            return self._enter_breakout(price, "UP")

        elif price < self.current_range.low:
            if self._is_false_breakout(price, "DOWN"):
                return {"action": "hold", "reason": "Potential false breakout DOWN"}

            if not self._check_volume_confirmation():
                return {"action": "hold", "reason": "No volume confirmation"}

            return self._enter_breakout(price, "DOWN")

        range_size = (self.current_range.high - self.current_range.low) / self.current_range.low * 100
        return {"action": "hold", "reason": f"In range (${self.current_range.low:.0f}-${self.current_range.high:.0f}, {range_size:.1f}%)"}

    def _enter_breakout(self, price: float, direction: str) -> dict:
        """Enter breakout trade"""
        stop_percent = self.config.get("stop_loss_percent", 1.0)

        if direction == "UP":
            # Stop just below the breakout level
            stop = self.current_range.high * (1 - stop_percent / 100)
            risk = price - stop
            take_profit = price + (risk * 2.5)  # 2.5:1 reward
            side = "buy"
        else:
            stop = self.current_range.low * (1 + stop_percent / 100)
            risk = stop - price
            take_profit = price - (risk * 2.5)
            side = "sell"

        self.position = {
            "entry": price,
            "stop": stop,
            "target": take_profit,
            "side": side,
            "time": datetime.now()
        }

        reward = abs(take_profit - price)
        risk_amt = abs(price - stop)

        logger.info(f"BREAKOUT {direction}: {side} @ ${price:.2f}, Stop: ${stop:.2f}, Target: ${take_profit:.2f}")

        return {
            "action": side,
            "side": side,
            "pair": self.trading_pair,
            "amount": self.config["lot_size_usd"],
            "price": None,
            "stop_loss": stop,
            "take_profit": take_profit,
            "reason": f"Breakout {direction} confirmed (R:R = {reward/risk_amt:.1f}:1)",
            "strategy": "breakout"
        }

    def _manage_position(self, price: float) -> dict:
        """Manage open position"""
        if self.position["side"] == "buy":
            # Check stop
            if price <= self.position["stop"]:
                pnl = (price - self.position["entry"]) / self.position["entry"] * 100
                self.position = None
                return {
                    "action": "sell",
                    "side": "sell",
                    "pair": self.trading_pair,
                    "amount": self.config["lot_size_usd"],
                    "reason": f"Breakout stop hit ({pnl:.1f}%)",
                    "strategy": "breakout"
                }

            # Check target
            if price >= self.position["target"]:
                pnl = (price - self.position["entry"]) / self.position["entry"] * 100
                self.position = None
                return {
                    "action": "sell",
                    "side": "sell",
                    "pair": self.trading_pair,
                    "amount": self.config["lot_size_usd"],
                    "reason": f"Breakout target hit ({pnl:.1f}%)",
                    "strategy": "breakout"
                }

        return {"action": "hold", "reason": "Managing breakout position"}

    def get_status(self) -> dict:
        return {
            "range": {
                "high": self.current_range.high if self.current_range else None,
                "low": self.current_range.low if self.current_range else None
            },
            "in_position": self.position is not None,
            "data_points": len(self.prices)
        }
