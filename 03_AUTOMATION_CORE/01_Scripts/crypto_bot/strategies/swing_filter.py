#!/usr/bin/env python3
"""
Swing Filter - Only trade large moves
Filters out small movements, enforces weekly trade limits,
and manages leverage/margin protection
"""

import logging
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import json
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class TradeRecord:
    """Record of a trade for frequency tracking"""
    timestamp: datetime
    pair: str
    side: str
    entry_price: float
    size_usd: float
    leverage: float


@dataclass
class SwingMove:
    """Detected swing movement"""
    pair: str
    direction: str  # 'up' or 'down'
    start_price: float
    current_price: float
    move_percent: float
    duration_hours: float
    from_level: str  # e.g., "weekly_low", "fib_0.618"


class SwingFilter:
    """
    Filters trades to only execute on large swing moves

    Rules:
    1. Minimum move of X% from key level before entry
    2. Maximum N trades per week
    3. Must be approaching (not leaving) key level
    4. Leverage position sizing with margin protection
    """

    def __init__(self, config: dict):
        self.config = config
        self.strategy_config = config.get("strategy", {})
        self.margin_config = config.get("margin_protection", {})

        # Swing detection settings
        self.min_move_pct = self.strategy_config.get("min_move_percent", 3.0)
        self.swing_threshold = self.strategy_config.get("swing_threshold_percent", 5.0)
        self.only_large_swings = self.strategy_config.get("only_large_swings", True)

        # Trade frequency limits
        self.min_weekly = self.strategy_config.get("min_weekly_trades", 1)
        self.max_weekly = self.strategy_config.get("max_weekly_trades", 5)

        # Leverage settings
        self.leverage = self.strategy_config.get("leverage", 4)
        self.lot_size = self.strategy_config.get("lot_size_usd", 500)

        # Margin protection (distance-based triggers)
        self.margin_enabled = self.margin_config.get("enabled", True)
        self.trigger_distance = self.margin_config.get("add_margin_at_distance_percent", 5)  # 5% from liquidation
        self.critical_distance = self.margin_config.get("critical_distance_percent", 2)  # 2% from liquidation
        self.margin_topup = self.margin_config.get("margin_topup_usd", 100)
        self.max_topups = self.margin_config.get("max_topups_per_position", 3)

        # Trade history
        self.trades_this_week: List[TradeRecord] = []
        self.week_start = self._get_week_start()

        # Swing tracking per pair
        self.swing_highs: Dict[str, float] = {}
        self.swing_lows: Dict[str, float] = {}
        self.last_prices: Dict[str, List[float]] = {}

        # State file for persistence
        self.state_file = Path(__file__).parent.parent / "data" / "swing_state.json"
        self._load_state()

        logger.info(f"SwingFilter initialized: {self.leverage}x leverage, "
                   f"min {self.min_move_pct}% move, {self.max_weekly} trades/week max")

    def _get_week_start(self) -> datetime:
        """Get start of current week (Monday)"""
        now = datetime.now()
        return now - timedelta(days=now.weekday())

    def _load_state(self):
        """Load persistent state"""
        try:
            if self.state_file.exists():
                with open(self.state_file) as f:
                    state = json.load(f)
                    # Restore trade history
                    for t in state.get("trades", []):
                        trade = TradeRecord(
                            timestamp=datetime.fromisoformat(t["timestamp"]),
                            pair=t["pair"],
                            side=t["side"],
                            entry_price=t["entry_price"],
                            size_usd=t["size_usd"],
                            leverage=t["leverage"]
                        )
                        # Only keep this week's trades
                        if trade.timestamp >= self.week_start:
                            self.trades_this_week.append(trade)
        except Exception as e:
            logger.warning(f"Could not load swing state: {e}")

    def _save_state(self):
        """Save persistent state"""
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            state = {
                "trades": [
                    {
                        "timestamp": t.timestamp.isoformat(),
                        "pair": t.pair,
                        "side": t.side,
                        "entry_price": t.entry_price,
                        "size_usd": t.size_usd,
                        "leverage": t.leverage
                    }
                    for t in self.trades_this_week
                ],
                "swing_highs": self.swing_highs,
                "swing_lows": self.swing_lows
            }
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save swing state: {e}")

    def _reset_week_if_needed(self):
        """Reset weekly counters if new week"""
        current_week_start = self._get_week_start()
        if current_week_start > self.week_start:
            logger.info("New week - resetting trade counters")
            self.trades_this_week = []
            self.week_start = current_week_start
            self._save_state()

    def _update_swing_tracking(self, pair: str, price: float):
        """Track swing highs and lows"""
        if pair not in self.last_prices:
            self.last_prices[pair] = []

        self.last_prices[pair].append(price)

        # Keep last 100 prices for swing detection
        if len(self.last_prices[pair]) > 100:
            self.last_prices[pair] = self.last_prices[pair][-100:]

        prices = self.last_prices[pair]
        if len(prices) >= 20:
            recent_high = max(prices[-20:])
            recent_low = min(prices[-20:])

            # Update swing levels
            if pair not in self.swing_highs or recent_high > self.swing_highs[pair]:
                self.swing_highs[pair] = recent_high
            if pair not in self.swing_lows or recent_low < self.swing_lows[pair]:
                self.swing_lows[pair] = recent_low

    def detect_swing(self, pair: str, price: float, key_levels: dict) -> Optional[SwingMove]:
        """
        Detect if current price represents a significant swing

        Args:
            pair: Trading pair
            price: Current price
            key_levels: Dict with yearly/monthly/weekly high/low

        Returns:
            SwingMove if significant swing detected, None otherwise
        """
        self._update_swing_tracking(pair, price)

        if not self.only_large_swings:
            return None

        # Check distance from each key level
        levels_to_check = [
            ("yearly_low", key_levels.get("yearly_low")),
            ("yearly_high", key_levels.get("yearly_high")),
            ("monthly_low", key_levels.get("monthly_low")),
            ("monthly_high", key_levels.get("monthly_high")),
            ("weekly_low", key_levels.get("weekly_low")),
            ("weekly_high", key_levels.get("weekly_high")),
        ]

        for level_name, level_price in levels_to_check:
            if not level_price:
                continue

            distance_pct = ((price - level_price) / level_price) * 100

            # Check if we've moved significantly FROM a level
            if abs(distance_pct) >= self.swing_threshold:
                direction = "up" if distance_pct > 0 else "down"

                return SwingMove(
                    pair=pair,
                    direction=direction,
                    start_price=level_price,
                    current_price=price,
                    move_percent=abs(distance_pct),
                    duration_hours=0,  # Would need timestamp tracking
                    from_level=level_name
                )

        return None

    def can_trade(self, pair: str) -> tuple[bool, str]:
        """
        Check if trading is allowed based on weekly limits

        Returns:
            (allowed, reason)
        """
        self._reset_week_if_needed()

        trades_count = len(self.trades_this_week)

        if trades_count >= self.max_weekly:
            return False, f"Weekly limit reached ({trades_count}/{self.max_weekly})"

        # Check per-pair limit (max 2 per pair per week)
        pair_trades = len([t for t in self.trades_this_week if t.pair == pair])
        if pair_trades >= 2:
            return False, f"Pair limit reached for {pair} ({pair_trades}/2)"

        return True, f"OK ({trades_count}/{self.max_weekly} weekly trades)"

    def filter_signal(self, signal: dict, key_levels: dict) -> dict:
        """
        Filter a trading signal through swing requirements

        Args:
            signal: Signal dict from strategy (action, pair, etc.)
            key_levels: Key levels dict

        Returns:
            Modified signal (may change action to 'hold')
        """
        if signal.get("action") == "hold":
            return signal

        pair = signal.get("pair", "")
        price = signal.get("entry_price", 0)

        # Check weekly trade limits
        can_trade, reason = self.can_trade(pair)
        if not can_trade:
            return {
                "action": "hold",
                "reason": f"Trade filtered: {reason}",
                "original_signal": signal
            }

        # Check for significant swing (if enabled)
        if self.only_large_swings:
            swing = self.detect_swing(pair, price, key_levels)

            if not swing:
                # Check minimum move from nearest level
                nearest_distance = float('inf')
                for level_name, level_price in key_levels.items():
                    if level_price:
                        dist = abs((price - level_price) / level_price * 100)
                        nearest_distance = min(nearest_distance, dist)

                if nearest_distance < self.min_move_pct:
                    return {
                        "action": "hold",
                        "reason": f"Move too small ({nearest_distance:.1f}% < {self.min_move_pct}% min)",
                        "original_signal": signal
                    }

        # Signal passes filters - apply leverage sizing
        signal["leverage"] = self.leverage
        signal["effective_size"] = signal.get("amount", self.lot_size) * self.leverage
        signal["margin_required"] = signal.get("amount", self.lot_size)

        return signal

    def record_trade(self, signal: dict):
        """Record a trade for frequency tracking"""
        trade = TradeRecord(
            timestamp=datetime.now(),
            pair=signal.get("pair", ""),
            side=signal.get("side", ""),
            entry_price=signal.get("entry_price", 0),
            size_usd=signal.get("amount", 0),
            leverage=signal.get("leverage", self.leverage)
        )
        self.trades_this_week.append(trade)
        self._save_state()

        logger.info(f"Trade recorded: {trade.pair} {trade.side} @ ${trade.entry_price:,.2f} "
                   f"({len(self.trades_this_week)}/{self.max_weekly} this week)")

    def check_margin_health(self, position: dict, current_price: float,
                            position_manager=None, trend: str = None) -> dict:
        """
        Check if position needs margin protection

        Delegates to PositionManager if available for accurate liquidation-based calculations.

        Args:
            position: Current position dict
            current_price: Current market price
            position_manager: PositionManager instance for accurate calculations
            trend: 'bullish', 'bearish', or 'neutral' from EMA analysis

        Returns:
            Dict with margin status and recommended action
        """
        if not self.margin_enabled:
            return {"action": "none", "reason": "Margin protection disabled"}

        # If PositionManager is available, delegate to it for accurate calculations
        if position_manager and position.get("id"):
            return position_manager.check_liquidation_risk(
                position["id"],
                current_price,
                trend
            )

        # Fallback to distance-based calculation
        entry_price = position.get("entry_price", 0)
        side = position.get("side", "buy")
        leverage = position.get("leverage", self.leverage)
        topups_done = position.get("topups", 0)

        if not entry_price:
            return {"action": "none", "reason": "No position data"}

        # Calculate liquidation price
        if side == "buy":
            liq_price = entry_price * (1 - 1/leverage)
        else:
            liq_price = entry_price * (1 + 1/leverage)

        # Calculate distance to liquidation
        if side == "buy":
            if current_price <= liq_price:
                distance_pct = 0
            else:
                distance_pct = (current_price - liq_price) / current_price * 100
        else:
            if current_price >= liq_price:
                distance_pct = 0
            else:
                distance_pct = (liq_price - current_price) / current_price * 100

        result = {
            "liquidation_price": round(liq_price, 2),
            "distance_to_liquidation": round(distance_pct, 2),
            "topups_done": topups_done,
            "max_topups": self.max_topups,
            "topups_remaining": self.max_topups - topups_done
        }

        # Decision logic based on distance to liquidation
        if distance_pct <= self.critical_distance:
            # CRITICAL - within 2% of liquidation
            if topups_done >= self.max_topups:
                result["action"] = "close_position"
                result["reason"] = f"CRITICAL: {distance_pct:.2f}% from liquidation, all {self.max_topups} saves exhausted"
                result["urgency"] = "critical"
            else:
                result["action"] = "add_margin"
                result["amount"] = self.margin_topup
                result["reason"] = f"CRITICAL: {distance_pct:.2f}% from liquidation! (save {topups_done + 1}/{self.max_topups})"
                result["urgency"] = "critical"

        elif distance_pct <= self.trigger_distance:
            # WARNING - within 5% of liquidation
            if topups_done >= self.max_topups:
                result["action"] = "close_position"
                result["reason"] = f"WARNING: {distance_pct:.2f}% from liquidation, all {self.max_topups} saves used"
                result["urgency"] = "high"
            else:
                result["action"] = "add_margin"
                result["amount"] = self.margin_topup
                result["reason"] = f"WARNING: {distance_pct:.2f}% from liquidation (save {topups_done + 1}/{self.max_topups})"
                result["urgency"] = "medium"
        else:
            result["action"] = "none"
            result["reason"] = f"Position safe: {distance_pct:.1f}% from liquidation"
            result["urgency"] = "low"

        return result

    def get_weekly_stats(self) -> dict:
        """Get trading stats for current week"""
        self._reset_week_if_needed()

        return {
            "week_start": self.week_start.isoformat(),
            "trades_count": len(self.trades_this_week),
            "max_trades": self.max_weekly,
            "trades_remaining": self.max_weekly - len(self.trades_this_week),
            "pairs_traded": list(set(t.pair for t in self.trades_this_week)),
            "total_volume": sum(t.size_usd * t.leverage for t in self.trades_this_week),
            "trades": [
                {
                    "time": t.timestamp.strftime("%Y-%m-%d %H:%M"),
                    "pair": t.pair,
                    "side": t.side,
                    "size": f"${t.size_usd:,.0f} x{t.leverage}"
                }
                for t in self.trades_this_week
            ]
        }
