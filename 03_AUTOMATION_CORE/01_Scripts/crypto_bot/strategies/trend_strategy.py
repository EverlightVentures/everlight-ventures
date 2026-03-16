#!/usr/bin/env python3
"""
Trend Following Strategy
- Only trade WITH the trend (never against)
- Enter on pullbacks to moving average
- Use trailing stops to ride winners
"""

import logging
from typing import Optional
from collections import deque
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class Position:
    entry_price: float
    size_usd: float
    side: str
    stop_loss: float
    take_profit: float
    highest_price: float = 0
    lowest_price: float = float('inf')
    entry_time: datetime = None


class TrendStrategy:
    """
    Trend Following: The most reliable edge in trading

    Rules:
    1. Identify trend using 50 EMA slope
    2. Wait for pullback to EMA (1-2%)
    3. Enter with tight stop below recent swing
    4. Trail stop as price moves in favor
    5. Let winners run, cut losers fast
    """

    def __init__(self, api, config: dict, trading_pair: str):
        self.api = api
        self.config = config
        self.trading_pair = trading_pair

        self.prices = deque(maxlen=200)
        self.highs = deque(maxlen=50)
        self.lows = deque(maxlen=50)

        self.position: Optional[Position] = None
        self.ema_period = config.get("ema_trend_period", 50)

    def _calc_ema(self, period: int) -> Optional[float]:
        if len(self.prices) < period:
            return None

        prices = list(self.prices)[-period:]
        multiplier = 2 / (period + 1)
        ema = prices[0]
        for price in prices[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        return ema

    def _get_trend(self) -> Optional[str]:
        """Determine trend direction"""
        ema = self._calc_ema(self.ema_period)
        if not ema or len(self.prices) < self.ema_period + 10:
            return None

        current_price = self.prices[-1]
        ema_10_ago = self._calc_ema_at(self.ema_period, -10)

        if not ema_10_ago:
            return None

        # Trend = price above EMA AND EMA rising
        ema_slope = (ema - ema_10_ago) / ema_10_ago * 100

        min_strength = self.config.get("min_trend_strength", 0.5)

        if current_price > ema and ema_slope > min_strength:
            return "UP"
        elif current_price < ema and ema_slope < -min_strength:
            return "DOWN"
        return "SIDEWAYS"

    def _calc_ema_at(self, period: int, offset: int) -> Optional[float]:
        """Calculate EMA at a past point"""
        if len(self.prices) < period + abs(offset):
            return None

        prices = list(self.prices)[:offset] if offset < 0 else list(self.prices)
        prices = prices[-period:]

        multiplier = 2 / (period + 1)
        ema = prices[0]
        for price in prices[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        return ema

    def _check_pullback(self, price: float, trend: str) -> bool:
        """Check if price pulled back to EMA"""
        ema = self._calc_ema(self.ema_period)
        if not ema:
            return False

        pullback_threshold = self.config.get("entry_pullback_percent", 1.0)
        distance_percent = abs(price - ema) / ema * 100

        if trend == "UP":
            # Price should be near EMA from above (pulled back)
            return price > ema and distance_percent < pullback_threshold
        elif trend == "DOWN":
            # Price should be near EMA from below
            return price < ema and distance_percent < pullback_threshold

        return False

    def _calculate_stop_loss(self, price: float, trend: str) -> float:
        """Set stop below recent swing low (or above swing high for shorts)"""
        stop_percent = self.config.get("stop_loss_percent", 1.5)

        if trend == "UP":
            # Stop below recent low
            recent_low = min(list(self.lows)[-10:]) if len(self.lows) >= 10 else price
            stop = min(recent_low, price * (1 - stop_percent / 100))
            return stop
        else:
            # Stop above recent high
            recent_high = max(list(self.highs)[-10:]) if len(self.highs) >= 10 else price
            stop = max(recent_high, price * (1 + stop_percent / 100))
            return stop

    def _update_trailing_stop(self, price: float) -> float:
        """Move stop loss to lock in profits"""
        if not self.position:
            return 0

        trail_percent = self.config.get("trailing_stop_percent", 1.0)
        break_even_at = self.config.get("break_even_at_percent", 1.5)

        if self.position.side == "buy":
            # Track highest price
            self.position.highest_price = max(self.position.highest_price, price)

            # Calculate profit
            profit_percent = (price - self.position.entry_price) / self.position.entry_price * 100

            # Move to break-even first
            if profit_percent >= break_even_at:
                new_stop = max(
                    self.position.stop_loss,
                    self.position.entry_price,  # Break even
                    self.position.highest_price * (1 - trail_percent / 100)  # Trailing
                )
                return new_stop

        return self.position.stop_loss

    def analyze(self, market_data: dict) -> Optional[dict]:
        """Main analysis"""
        price = market_data["price"]
        high = market_data.get("high", price)
        low = market_data.get("low", price)

        self.prices.append(price)
        self.highs.append(high)
        self.lows.append(low)

        # Need enough data
        if len(self.prices) < self.ema_period + 20:
            return {"action": "hold", "reason": f"Collecting data ({len(self.prices)}/{self.ema_period + 20})"}

        trend = self._get_trend()

        # Manage existing position
        if self.position:
            return self._manage_position(price, trend)

        # Look for entry
        if trend in ["UP", "DOWN"] and self._check_pullback(price, trend):
            return self._generate_entry(price, trend)

        return {"action": "hold", "reason": f"Trend: {trend}, waiting for pullback"}

    def _manage_position(self, price: float, trend: str) -> dict:
        """Manage open position"""
        # Update trailing stop
        new_stop = self._update_trailing_stop(price)
        if new_stop > self.position.stop_loss:
            self.position.stop_loss = new_stop
            logger.info(f"Trailing stop moved to ${new_stop:.2f}")

        # Check stop loss
        if self.position.side == "buy" and price <= self.position.stop_loss:
            pnl = (price - self.position.entry_price) / self.position.entry_price * 100
            self.position = None
            return {
                "action": "sell",
                "side": "sell",
                "pair": self.trading_pair,
                "amount": self.config["lot_size_usd"],
                "reason": f"Stop loss hit ({pnl:.1f}%)",
                "strategy": "trend_follow"
            }

        # Check take profit
        if self.position.side == "buy" and price >= self.position.take_profit:
            pnl = (price - self.position.entry_price) / self.position.entry_price * 100
            self.position = None
            return {
                "action": "sell",
                "side": "sell",
                "pair": self.trading_pair,
                "amount": self.config["lot_size_usd"],
                "reason": f"Take profit hit ({pnl:.1f}%)",
                "strategy": "trend_follow"
            }

        return {"action": "hold", "reason": "Managing position"}

    def _generate_entry(self, price: float, trend: str) -> dict:
        """Generate entry signal"""
        stop = self._calculate_stop_loss(price, trend)

        # Calculate take profit for 2:1 ratio minimum
        risk = abs(price - stop)
        take_profit_percent = self.config.get("take_profit_percent", 3.0)
        take_profit = price + (risk * 2) if trend == "UP" else price - (risk * 2)

        # Verify reward:risk
        reward = abs(take_profit - price)
        if reward / risk < 2:
            return {"action": "hold", "reason": "Reward:risk below 2:1"}

        self.position = Position(
            entry_price=price,
            size_usd=self.config["lot_size_usd"],
            side="buy" if trend == "UP" else "sell",
            stop_loss=stop,
            take_profit=take_profit,
            entry_time=datetime.now()
        )

        side = "buy" if trend == "UP" else "sell"

        logger.info(f"TREND ENTRY: {side} @ ${price:.2f}, Stop: ${stop:.2f}, TP: ${take_profit:.2f}")

        return {
            "action": side,
            "side": side,
            "pair": self.trading_pair,
            "amount": self.config["lot_size_usd"],
            "price": None,
            "stop_loss": stop,
            "take_profit": take_profit,
            "reason": f"Trend {trend} pullback entry (R:R = {reward/risk:.1f}:1)",
            "strategy": "trend_follow"
        }

    def get_status(self) -> dict:
        return {
            "trend": self._get_trend(),
            "ema": self._calc_ema(self.ema_period),
            "in_position": self.position is not None,
            "data_points": len(self.prices)
        }
