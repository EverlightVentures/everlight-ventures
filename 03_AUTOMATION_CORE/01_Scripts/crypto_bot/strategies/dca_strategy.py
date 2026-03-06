#!/usr/bin/env python3
"""
DCA (Dollar Cost Averaging) Strategy
Buy on dips, accumulate over time
"""

import logging
from typing import Dict, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class DCAStrategy:
    """
    Dollar Cost Averaging with dip detection
    - Buy fixed amount on schedule
    - Extra buys on significant dips
    - Track average entry price
    """

    def __init__(self, api, config: dict, trading_pair: str):
        self.api = api
        self.config = config
        self.trading_pair = trading_pair

        # State
        self.last_buy_time = None
        self.last_price = None
        self.price_high_24h = None
        self.buys_today = 0
        self.total_bought = 0.0
        self.total_spent = 0.0
        self.avg_entry_price = 0.0

    def _is_dip(self, current_price: float) -> bool:
        """Check if price dropped enough for a dip buy"""
        if not self.price_high_24h:
            return False

        drop_percent = ((self.price_high_24h - current_price) / self.price_high_24h) * 100
        return drop_percent >= self.config["dip_threshold_percent"]

    def _can_buy_scheduled(self) -> bool:
        """Check if it's time for scheduled buy"""
        if not self.last_buy_time:
            return True

        hours_since = (datetime.now() - self.last_buy_time).total_seconds() / 3600
        return hours_since >= self.config["interval_hours"]

    def _can_buy_dip(self) -> bool:
        """Check if we can do a dip buy"""
        return self.buys_today < self.config["max_buys_per_day"]

    def _execute_buy(self, price: float, reason: str) -> dict:
        """Execute a DCA buy"""
        amount_usd = self.config["buy_amount_usd"]

        return {
            "action": "buy",
            "side": "buy",
            "pair": self.trading_pair,
            "amount": amount_usd,
            "price": None,  # Market order
            "reason": reason,
            "strategy": "dca"
        }

    def _update_stats(self, price: float, amount_usd: float):
        """Update tracking stats after buy"""
        amount_crypto = amount_usd / price

        self.total_spent += amount_usd
        self.total_bought += amount_crypto
        self.avg_entry_price = self.total_spent / self.total_bought if self.total_bought > 0 else 0
        self.last_buy_time = datetime.now()
        self.buys_today += 1

        logger.info(f"DCA Stats - Avg Entry: ${self.avg_entry_price:.2f}, Total: {self.total_bought:.6f}")

    def analyze(self, market_data: dict) -> Optional[dict]:
        """Analyze market and decide on DCA action"""
        current_price = market_data["price"]

        # Update 24h high
        if not self.price_high_24h or current_price > self.price_high_24h:
            self.price_high_24h = current_price

        # Check for dip buy opportunity
        if self._is_dip(current_price) and self._can_buy_dip():
            drop = ((self.price_high_24h - current_price) / self.price_high_24h) * 100
            logger.info(f"DCA: Dip detected! {drop:.1f}% from high")
            self._update_stats(current_price, self.config["buy_amount_usd"])
            return self._execute_buy(current_price, f"Dip buy ({drop:.1f}% drop)")

        # Check for scheduled buy
        if self._can_buy_scheduled():
            logger.info("DCA: Scheduled buy time")
            self._update_stats(current_price, self.config["buy_amount_usd"])
            return self._execute_buy(current_price, "Scheduled DCA")

        # Update last price
        self.last_price = current_price

        return {"action": "hold", "reason": "Waiting for DCA trigger"}

    def reset_daily(self):
        """Reset daily counters"""
        self.buys_today = 0
        self.price_high_24h = None

    def get_status(self) -> dict:
        """Get strategy status"""
        return {
            "total_bought": self.total_bought,
            "total_spent": self.total_spent,
            "avg_entry": self.avg_entry_price,
            "buys_today": self.buys_today,
            "last_buy": self.last_buy_time.isoformat() if self.last_buy_time else None
        }
