#!/usr/bin/env python3
"""
Grid Trading Strategy
Places buy/sell orders at regular price intervals
Profits from sideways price movement
"""

import logging
from typing import Dict, Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class GridLevel:
    price: float
    side: str  # 'buy' or 'sell'
    order_id: Optional[str] = None
    filled: bool = False


class GridStrategy:
    """
    Grid Trading: Place orders at set price levels
    - Buy orders below current price
    - Sell orders above current price
    - When buy fills, place sell at next level up
    - When sell fills, place buy at next level down
    """

    def __init__(self, api, config: dict, trading_pair: str):
        self.api = api
        self.config = config
        self.trading_pair = trading_pair
        self.grid_levels: List[GridLevel] = []
        self.initialized = False

    def initialize_grid(self, current_price: float):
        """Set up the grid around current price"""
        levels = self.config["grid_levels"]
        spacing = self.config["grid_spacing_percent"] / 100

        # Calculate upper and lower bounds if not set
        upper = self.config.get("upper_price") or current_price * (1 + spacing * levels / 2)
        lower = self.config.get("lower_price") or current_price * (1 - spacing * levels / 2)

        step = (upper - lower) / levels

        self.grid_levels = []
        for i in range(levels + 1):
            price = lower + (step * i)
            side = "buy" if price < current_price else "sell"
            self.grid_levels.append(GridLevel(price=price, side=side))

        logger.info(f"Grid initialized: {levels} levels from ${lower:.2f} to ${upper:.2f}")
        self.initialized = True

    def place_grid_orders(self):
        """Place all grid orders"""
        for level in self.grid_levels:
            if level.order_id is None and not level.filled:
                try:
                    if level.side == "buy":
                        order = self.api.place_buy_order(
                            self.trading_pair,
                            self.config["order_size"],
                            level.price
                        )
                    else:
                        order = self.api.place_sell_order(
                            self.trading_pair,
                            self.config["order_size"],
                            level.price
                        )

                    if order:
                        level.order_id = order.get("order_id")
                        logger.info(f"Grid order placed: {level.side} @ ${level.price:.2f}")

                except Exception as e:
                    logger.error(f"Failed to place grid order: {e}")

    def check_filled_orders(self):
        """Check for filled orders and place counter orders"""
        for level in self.grid_levels:
            if level.order_id and not level.filled:
                order = self.api.get_order(level.order_id)
                if order and order.get("status") == "FILLED":
                    level.filled = True
                    logger.info(f"Grid order filled: {level.side} @ ${level.price:.2f}")

                    # Place counter order
                    self._place_counter_order(level)

    def _place_counter_order(self, filled_level: GridLevel):
        """When a level fills, place order on opposite side"""
        spacing = self.config["grid_spacing_percent"] / 100

        if filled_level.side == "buy":
            # Bought - now place sell above
            sell_price = filled_level.price * (1 + spacing)
            self.api.place_sell_order(
                self.trading_pair,
                self.config["order_size"],
                sell_price
            )
            logger.info(f"Counter SELL placed @ ${sell_price:.2f}")
        else:
            # Sold - now place buy below
            buy_price = filled_level.price * (1 - spacing)
            self.api.place_buy_order(
                self.trading_pair,
                self.config["order_size"],
                buy_price
            )
            logger.info(f"Counter BUY placed @ ${buy_price:.2f}")

    def analyze(self, market_data: dict) -> Optional[dict]:
        """Main analysis loop"""
        current_price = market_data["price"]

        # Initialize grid on first run
        if not self.initialized:
            self.initialize_grid(current_price)
            self.place_grid_orders()
            return {"action": "hold", "reason": "Grid initialized"}

        # Check for filled orders
        self.check_filled_orders()

        # Grid strategy is passive - just manage orders
        return {"action": "hold", "reason": "Grid managing orders"}

    def get_status(self) -> dict:
        """Get grid status"""
        active = sum(1 for l in self.grid_levels if l.order_id and not l.filled)
        filled = sum(1 for l in self.grid_levels if l.filled)
        return {
            "initialized": self.initialized,
            "total_levels": len(self.grid_levels),
            "active_orders": active,
            "filled_orders": filled
        }
