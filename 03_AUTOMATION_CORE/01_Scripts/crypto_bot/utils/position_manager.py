#!/usr/bin/env python3
"""
Position Manager - Smart Liquidation Protection System

Tracks positions, calculates liquidation prices, manages margin additions.
Adds margin up to 3 times to save positions, then closes to prevent liquidation.
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


@dataclass
class ManagedPosition:
    """Position with liquidation tracking"""
    position_id: str
    pair: str
    side: str  # 'buy' or 'sell' (long/short)
    entry_price: float
    size_usd: float
    leverage: int
    initial_margin: float
    stop_loss: float = 0.0
    take_profit: float = 0.0
    initial_size_usd: float = 0.0
    remaining_size_usd: float = 0.0
    partial_taken: bool = False
    breakout_type: str = ""
    breakout_tf: str = ""

    # Liquidation tracking
    liquidation_price: float = 0.0
    current_margin: float = 0.0
    margin_topups: int = 0
    total_margin_added: float = 0.0

    # Timestamps
    opened_at: str = ""
    last_margin_add: str = ""

    # State
    status: str = "open"  # open, closed, liquidated, protective_close

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'ManagedPosition':
        return cls(**data)


class PositionManager:
    """
    Manages position lifecycle with liquidation protection

    Key Features:
    1. Calculates exact liquidation price
    2. Tracks margin additions per position (max 3)
    3. Persists state to JSON for restart recovery
    4. Integrates trend analysis before margin decisions

    Rules:
    - Add margin up to 3 times to save position
    - Check trend before adding margin (don't throw good money after bad)
    - Close position after 3 failed saves to prevent liquidation loss
    """

    def __init__(self, config: dict, api=None, data_dir: str = None):
        self.config = config
        self.api = api
        self.margin_config = config.get("margin_protection", {})

        # Settings from config - trigger based on DISTANCE to liquidation price
        self.enabled = self.margin_config.get("enabled", True)
        self.trigger_distance = self.margin_config.get("add_margin_at_distance_percent", 5)  # Add margin when 5% from liquidation
        self.critical_distance = self.margin_config.get("critical_distance_percent", 2)  # Critical when 2% from liquidation

        # Margin topup: percentage-based for small accounts, with fallback to fixed amount
        self.topup_percent = self.margin_config.get("margin_topup_percent", 5)  # 5% of balance per topup
        self._topup_fixed = self.margin_config.get("margin_topup_usd", 100)  # Fallback if no balance
        self.max_topups = self.margin_config.get("max_topups_per_position", 2)  # Reduced for small accounts

        # Data storage
        if data_dir:
            self.data_dir = Path(data_dir)
        else:
            self.data_dir = Path(__file__).parent.parent / "data"

        self.state_file = self.data_dir / "position_state.json"

        # Active positions
        self.positions: Dict[str, ManagedPosition] = {}

        # Load persisted state
        self._load_state()

        logger.info(f"PositionManager initialized: max {self.max_topups} topups, "
                   f"{self.topup_percent}% each, trigger at {self.trigger_distance}% from liquidation")

    def get_topup_amount(self, balance: float = None) -> float:
        """Calculate topup amount based on balance (percentage-based for small accounts)"""
        if balance and balance > 0:
            # Use percentage of balance
            amount = balance * (self.topup_percent / 100)
            # Minimum $5, maximum the fixed fallback
            return max(5, min(amount, self._topup_fixed))
        return self._topup_fixed  # Fallback to fixed amount

    # === Liquidation Price Calculation ===

    def calculate_liquidation_price(self, entry_price: float, leverage: int,
                                    side: str) -> float:
        """
        Calculate liquidation price for a leveraged position

        Formula:
        - Long:  Liq = Entry * (1 - 1/Leverage)
        - Short: Liq = Entry * (1 + 1/Leverage)

        Example: BTC Long at $100,000 with 4x leverage
        Liq = $100,000 * (1 - 1/4) = $100,000 * 0.75 = $75,000
        """
        # Add small buffer (exchanges typically liquidate slightly before theoretical price)
        buffer_factor = 0.005  # 0.5% buffer

        if side.lower() in ('buy', 'long'):
            # Long position: liquidated when price drops
            base_liq = entry_price * (1 - 1/leverage)
            liquidation_price = base_liq * (1 + buffer_factor)
        else:
            # Short position: liquidated when price rises
            base_liq = entry_price * (1 + 1/leverage)
            liquidation_price = base_liq * (1 - buffer_factor)

        return round(liquidation_price, 2)

    def recalculate_liquidation_after_margin(self, position: ManagedPosition,
                                              added_margin: float) -> float:
        """
        Recalculate liquidation price after adding margin

        Adding margin effectively reduces leverage and moves liquidation price
        further from current price.

        Example: Add $100 to $500 margin on $2000 position
        New_Leverage = $2000 / $600 = 3.33x
        New_Liq = $100,000 * 0.70 = $70,000 (pushed further away)
        """
        new_total_margin = position.current_margin + added_margin

        # Calculate effective leverage after margin addition
        # Position value = initial margin * leverage
        position_value = position.initial_margin * position.leverage
        effective_leverage = position_value / new_total_margin

        return self.calculate_liquidation_price(
            position.entry_price,
            effective_leverage,
            position.side
        )

    # === Distance Calculations ===

    def get_distance_to_liquidation(self, position: ManagedPosition,
                                     current_price: float) -> float:
        """
        Calculate distance to liquidation as percentage

        Returns: percentage distance (positive = safe, approaching 0 = danger)
        """
        if position.side.lower() in ('buy', 'long'):
            # For longs, liquidation is below current price
            if current_price <= position.liquidation_price:
                return 0.0  # Already at or past liquidation
            distance = (current_price - position.liquidation_price) / current_price * 100
        else:
            # For shorts, liquidation is above current price
            if current_price >= position.liquidation_price:
                return 0.0
            distance = (position.liquidation_price - current_price) / current_price * 100

        return round(distance, 2)

    def get_margin_usage_percent(self, position: ManagedPosition,
                                  current_price: float) -> float:
        """
        Calculate what percentage of margin is "used" by unrealized loss

        Returns: 0-100+ (0 = no loss, 100 = liquidation imminent)

        Formula: margin_usage = |leveraged_loss_percent|
        """
        # Calculate unrealized PnL percentage
        if position.side.lower() in ('buy', 'long'):
            pnl_percent = (current_price - position.entry_price) / position.entry_price
        else:
            pnl_percent = (position.entry_price - current_price) / position.entry_price

        # Apply leverage to get actual margin impact
        leveraged_pnl = pnl_percent * position.leverage

        if leveraged_pnl >= 0:
            return 0.0  # In profit, no margin pressure

        # Convert loss to margin usage percentage
        # If leveraged loss equals 100% of margin, we're at liquidation
        margin_usage = abs(leveraged_pnl) * 100

        return round(min(margin_usage, 100), 2)

    def get_unrealized_pnl(self, position: ManagedPosition, current_price: float) -> float:
        """Calculate unrealized PnL in USD"""
        if position.side.lower() in ('buy', 'long'):
            pnl_percent = (current_price - position.entry_price) / position.entry_price
        else:
            pnl_percent = (position.entry_price - current_price) / position.entry_price

        # PnL on the leveraged position
        return round(position.size_usd * pnl_percent, 2)

    # === Position Management ===

    def register_position(self, position_id: str, pair: str, side: str,
                          entry_price: float, size_usd: float,
                          leverage: int, stop_loss: float = 0.0,
                          take_profit: float = 0.0,
                          breakout_type: str = "",
                          breakout_tf: str = "") -> ManagedPosition:
        """Register a new position for liquidation tracking"""

        # Initial margin = position size (what we actually put up)
        initial_margin = size_usd

        liquidation_price = self.calculate_liquidation_price(
            entry_price, leverage, side
        )

        position = ManagedPosition(
            position_id=position_id,
            pair=pair,
            side=side,
            entry_price=entry_price,
            size_usd=size_usd * leverage,  # Actual position value (leveraged)
            leverage=leverage,
            initial_margin=initial_margin,
            stop_loss=stop_loss or 0.0,
            take_profit=take_profit or 0.0,
            initial_size_usd=size_usd,
            remaining_size_usd=size_usd,
            partial_taken=False,
            breakout_type=breakout_type or "",
            breakout_tf=breakout_tf or "",
            liquidation_price=liquidation_price,
            current_margin=initial_margin,
            margin_topups=0,
            total_margin_added=0.0,
            opened_at=datetime.now().isoformat(),
            status="open"
        )

        self.positions[position_id] = position
        self._save_state()

        logger.info(f"Position registered: {pair} {side.upper()} @ ${entry_price:.2f}, "
                   f"Liquidation @ ${liquidation_price:.2f}, Leverage: {leverage}x")

        return position

    def close_position(self, position_id: str, reason: str = "closed") -> Optional[ManagedPosition]:
        """Mark position as closed and remove from tracking"""
        if position_id in self.positions:
            position = self.positions[position_id]
            position.status = reason

            logger.info(f"Position closed: {position.pair} ({reason}), "
                       f"Total margin invested: ${position.current_margin:.2f}")

            # Remove from active tracking
            del self.positions[position_id]
            self._save_state()

            return position
        return None

    def get_position_by_pair(self, pair: str) -> Optional[ManagedPosition]:
        """Find position by trading pair"""
        for pos in self.positions.values():
            if pos.pair == pair and pos.status == "open":
                return pos
        return None

    # === Margin Protection Logic ===

    def check_liquidation_risk(self, position_id: str, current_price: float,
                                trend_direction: str = None) -> dict:
        """
        Main method: Check if position needs margin protection

        Decision Logic (Distance-Based - triggers close to liquidation):
        1. If within 2% of liquidation (critical) AND topups < 3 -> ADD MARGIN immediately
        2. If within 2% of liquidation AND topups >= 3 -> CLOSE POSITION
        3. If within 5% of liquidation AND trend favorable -> ADD MARGIN
        4. If within 5% of liquidation AND trend unfavorable AND topups >= 2 -> CLOSE
        5. If within 5% of liquidation AND trend unfavorable AND topups < 2 -> ADD (last chance)

        Args:
            position_id: Position to check
            current_price: Current market price
            trend_direction: 'bullish', 'bearish', or 'neutral' from EMA analysis

        Returns:
            dict with action recommendation
        """
        if not self.enabled:
            return {"action": "none", "reason": "Margin protection disabled"}

        if position_id not in self.positions:
            return {"action": "none", "reason": "Position not found"}

        position = self.positions[position_id]

        if position.status != "open":
            return {"action": "none", "reason": "Position not open"}

        # Calculate risk metrics
        distance_to_liq = self.get_distance_to_liquidation(position, current_price)
        margin_usage = self.get_margin_usage_percent(position, current_price)
        unrealized_pnl = self.get_unrealized_pnl(position, current_price)

        result = {
            "position_id": position_id,
            "pair": position.pair,
            "side": position.side,
            "entry_price": position.entry_price,
            "current_price": current_price,
            "liquidation_price": position.liquidation_price,
            "distance_to_liquidation_percent": distance_to_liq,
            "margin_usage_percent": margin_usage,
            "unrealized_pnl": unrealized_pnl,
            "topups_done": position.margin_topups,
            "max_topups": self.max_topups,
            "topups_remaining": self.max_topups - position.margin_topups,
            "total_margin_invested": position.current_margin,
            "trend": trend_direction
        }

        # === Decision Logic (Distance-Based) ===

        # CRITICAL: Within 2% of liquidation - act immediately
        if distance_to_liq <= self.critical_distance:
            if position.margin_topups >= self.max_topups:
                result["action"] = "close_position"
                result["reason"] = f"CRITICAL: {distance_to_liq:.2f}% from liquidation, all {self.max_topups} topups used - closing to prevent liquidation"
                result["urgency"] = "critical"
            else:
                result["action"] = "add_margin"
                result["amount"] = self.get_topup_amount(position.current_margin)
                result["reason"] = f"CRITICAL: {distance_to_liq:.2f}% from liquidation! Adding margin (save {position.margin_topups + 1}/{self.max_topups})"
                result["urgency"] = "critical"

        # WARNING: Within 5% of liquidation - last chance zone
        elif distance_to_liq <= self.trigger_distance:

            # All topups exhausted
            if position.margin_topups >= self.max_topups:
                result["action"] = "close_position"
                result["reason"] = f"WARNING: {distance_to_liq:.2f}% from liquidation, all {self.max_topups} saves used - cutting losses"
                result["urgency"] = "high"

            # Check trend for smart decision
            elif trend_direction:
                trend_favorable = self._is_trend_favorable(position.side, trend_direction)

                if trend_favorable:
                    result["action"] = "add_margin"
                    result["amount"] = self.get_topup_amount(position.current_margin)
                    result["reason"] = f"{distance_to_liq:.2f}% from liquidation, trend favorable ({trend_direction}) - adding margin (save {position.margin_topups + 1}/{self.max_topups})"
                    result["urgency"] = "medium"
                else:
                    # Trend against us
                    if position.margin_topups >= 2:
                        # Already tried twice with bad trend - cut losses
                        result["action"] = "close_position"
                        result["reason"] = f"Trend unfavorable ({trend_direction}), already used {position.margin_topups} saves - cutting losses"
                        result["urgency"] = "high"
                    else:
                        # Give one more chance but warn
                        result["action"] = "add_margin"
                        result["amount"] = self.get_topup_amount(position.current_margin)
                        result["reason"] = f"{distance_to_liq:.2f}% from liquidation, trend UNFAVORABLE but allowing last chance (save {position.margin_topups + 1}/{self.max_topups})"
                        result["urgency"] = "high"
            else:
                # No trend data available, proceed with caution
                result["action"] = "add_margin"
                result["amount"] = self.get_topup_amount(position.current_margin)
                result["reason"] = f"{distance_to_liq:.2f}% from liquidation, no trend data (save {position.margin_topups + 1}/{self.max_topups})"
                result["urgency"] = "medium"

        else:
            # Position is safe - more than 5% from liquidation
            result["action"] = "none"
            result["reason"] = f"Position safe: {distance_to_liq:.1f}% from liquidation"
            result["urgency"] = "low"

        return result

    def _is_trend_favorable(self, position_side: str, trend: str) -> bool:
        """Check if market trend supports the position direction"""
        if position_side.lower() in ('buy', 'long'):
            return trend.lower() in ('bullish', 'up', 'uptrend')
        else:
            return trend.lower() in ('bearish', 'down', 'downtrend')

    def execute_margin_addition(self, position_id: str, amount: float = None) -> dict:
        """
        Execute margin addition via API and update state

        Returns: result dict with success status
        """
        if position_id not in self.positions:
            return {"success": False, "error": "Position not found"}

        position = self.positions[position_id]
        # Use dynamic topup amount based on position size
        add_amount = amount or self.get_topup_amount(position.current_margin or position.initial_margin)

        # Check topup limit
        if position.margin_topups >= self.max_topups:
            return {
                "success": False,
                "error": f"Max topups ({self.max_topups}) already reached"
            }

        # Call API to add margin
        try:
            if self.api:
                result = self.api.add_margin_to_position(position.pair, add_amount)
                if not result:
                    return {"success": False, "error": "API call returned no result"}

            # Update position state
            old_liq = position.liquidation_price

            position.margin_topups += 1
            position.total_margin_added += add_amount
            position.current_margin += add_amount
            position.last_margin_add = datetime.now().isoformat()

            # Recalculate liquidation price with new margin
            position.liquidation_price = self.recalculate_liquidation_after_margin(
                position, add_amount
            )

            self._save_state()

            logger.info(f"MARGIN ADDED: ${add_amount} to {position.pair}, "
                       f"topup {position.margin_topups}/{self.max_topups}, "
                       f"liquidation moved from ${old_liq:.2f} to ${position.liquidation_price:.2f}")

            return {
                "success": True,
                "amount_added": add_amount,
                "topup_count": position.margin_topups,
                "topups_remaining": self.max_topups - position.margin_topups,
                "old_liquidation_price": old_liq,
                "new_liquidation_price": position.liquidation_price,
                "total_margin": position.current_margin
            }

        except Exception as e:
            logger.error(f"Failed to add margin to {position.pair}: {e}")
            return {"success": False, "error": str(e)}

    # === State Persistence ===

    def _save_state(self):
        """Save position state to JSON file for restart recovery"""
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)

            state = {
                "last_updated": datetime.now().isoformat(),
                "settings": {
                    "max_topups": self.max_topups,
                    "topup_percent": self.topup_percent,
                    "trigger_percent": self.trigger_distance
                },
                "positions": {
                    pid: pos.to_dict() for pid, pos in self.positions.items()
                }
            }

            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to save position state: {e}")

    def _load_state(self):
        """Load position state from JSON file on startup"""
        try:
            if self.state_file.exists():
                with open(self.state_file) as f:
                    state = json.load(f)

                for pid, pos_data in state.get("positions", {}).items():
                    self.positions[pid] = ManagedPosition.from_dict(pos_data)

                if self.positions:
                    logger.info(f"Loaded {len(self.positions)} positions from state file")
                    for pos in self.positions.values():
                        logger.info(f"  - {pos.pair} {pos.side}: {pos.margin_topups}/{self.max_topups} topups used")

        except Exception as e:
            logger.warning(f"Could not load position state: {e}")
            self.positions = {}

    # === Utility Methods ===

    def get_all_positions(self) -> List[dict]:
        """Get all tracked positions as dicts"""
        return [pos.to_dict() for pos in self.positions.values()]

    def get_position(self, position_id: str) -> Optional[ManagedPosition]:
        """Get specific position by ID"""
        return self.positions.get(position_id)

    def get_status_summary(self, prices: dict = None) -> dict:
        """
        Get summary of all positions and risk levels

        Args:
            prices: dict of {pair: current_price} for risk calculation
        """
        summary = {
            "total_positions": len(self.positions),
            "total_margin_invested": 0,
            "total_margin_added": 0,
            "positions_at_risk": 0,
            "positions": []
        }

        for pos in self.positions.values():
            summary["total_margin_invested"] += pos.current_margin
            summary["total_margin_added"] += pos.total_margin_added

            pos_summary = {
                "id": pos.position_id,
                "pair": pos.pair,
                "side": pos.side,
                "entry": pos.entry_price,
                "liquidation": pos.liquidation_price,
                "topups": f"{pos.margin_topups}/{self.max_topups}",
                "margin": pos.current_margin
            }

            # Add current risk if prices provided
            if prices and pos.pair in prices:
                current_price = prices[pos.pair]
                pos_summary["current_price"] = current_price
                pos_summary["margin_usage"] = self.get_margin_usage_percent(pos, current_price)
                pos_summary["distance_to_liq"] = self.get_distance_to_liquidation(pos, current_price)

                if pos_summary["margin_usage"] >= self.trigger_percent:
                    summary["positions_at_risk"] += 1

            summary["positions"].append(pos_summary)

        return summary

    def sync_with_exchange(self, exchange_positions: list):
        """
        Sync local state with exchange positions

        Call this on startup to reconcile any positions that might have
        been opened/closed while bot was offline.
        """
        exchange_pairs = {p.get("pair") for p in exchange_positions}
        local_pairs = {p.pair for p in self.positions.values()}

        # Remove positions that no longer exist on exchange
        for pid, pos in list(self.positions.items()):
            if pos.pair not in exchange_pairs:
                logger.info(f"Position {pos.pair} no longer exists on exchange, removing from tracking")
                del self.positions[pid]

        self._save_state()

        # Note: New exchange positions should be registered via register_position()
        # when the bot opens them, not auto-added here
