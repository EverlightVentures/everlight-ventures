#!/usr/bin/env python3
"""
Liquidation Strategy - Trade Based on Liquidation Levels

Reads position data from exchange, identifies liquidation risks,
and creates trading strategy around saving positions or taking advantage
of liquidation cascades in the market.

Key Features:
1. Monitor all open positions for liquidation risk
2. Create strategy to save positions (add margin 3 times)
3. Identify market liquidation zones for entry opportunities
4. Only take 2% loss AFTER 3 saves fail
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class LiquidationZone:
    """Market liquidation zone - where many traders get liquidated"""
    price_level: float
    zone_type: str  # 'long_liquidation' or 'short_liquidation'
    estimated_volume: float  # Estimated liquidation volume
    strength: float  # 0-1, how significant this zone is


@dataclass
class PositionRisk:
    """Risk assessment for a position"""
    position_id: str
    pair: str
    side: str
    entry_price: float
    current_price: float
    liquidation_price: float
    distance_to_liq_pct: float
    saves_used: int
    saves_remaining: int
    unrealized_pnl: float
    risk_level: str  # 'safe', 'warning', 'critical', 'final_stand'
    recommended_action: str


class LiquidationStrategy:
    """
    Strategy that focuses on liquidation management and opportunities

    Rules:
    1. Fight for every position with up to 3 margin saves
    2. Only accept 2% loss after ALL saves exhausted
    3. Identify liquidation zones in the market for entries
    4. Don't enter new positions near liquidation zones (risk of cascade)
    """

    def __init__(self, config: dict, api=None, position_manager=None, balance_manager=None):
        self.config = config
        self.api = api
        self.position_manager = position_manager
        self.balance_manager = balance_manager

        # Settings
        margin_config = config.get("margin_protection", {})
        self.trigger_distance = margin_config.get("add_margin_at_distance_percent", 5)
        self.critical_distance = margin_config.get("critical_distance_percent", 2)
        self.max_saves = margin_config.get("max_topups_per_position", 3)
        self.margin_amount = margin_config.get("margin_topup_usd", 100)

        # Risk management
        self.max_loss_after_saves = config.get("risk_management", {}).get("max_loss_after_saves_percent", 2.0)

        # Check if perpetuals/futures are enabled
        self.use_perpetuals = config.get("exchange", {}).get("use_perpetuals", False)
        self.futures_type = config.get("exchange", {}).get("futures_type", "intx")

        logger.info(f"LiquidationStrategy initialized: {self.max_saves} saves, "
                   f"trigger at {self.trigger_distance}%, critical at {self.critical_distance}%")

    def analyze_positions(self) -> List[PositionRisk]:
        """
        Analyze all open positions for liquidation risk

        Returns list of PositionRisk assessments sorted by urgency
        """
        if not self.api:
            return []

        # Skip perpetuals API if not enabled (spot trading mode)
        if not self.use_perpetuals:
            # Use position_manager's tracked positions instead
            if self.position_manager:
                return self._analyze_managed_positions()
            return []

        risks = []

        try:
            # Get positions from exchange (CFM or INTX)
            if self.futures_type == "cfm":
                exchange_positions = self.api.get_futures_positions()
            else:
                exchange_positions = self.api.get_perpetuals_positions()

            if not exchange_positions:
                return []

            for pos in exchange_positions:
                pair = pos.get("product_id", pos.get("pair", ""))
                side = pos.get("side", "buy")
                entry_price = float(pos.get("avg_entry_price", pos.get("entry_price", 0)))
                size = float(pos.get("position_size", pos.get("size", 0)))
                leverage = float(pos.get("leverage", 4))
                unrealized_pnl = float(pos.get("unrealized_pnl", 0))

                # Get current price
                current_price = self.api.get_current_price(pair)
                if not current_price or not entry_price:
                    continue

                # Calculate liquidation price
                if side.lower() in ("buy", "long"):
                    liq_price = entry_price * (1 - 1/leverage)
                    distance_pct = (current_price - liq_price) / current_price * 100
                else:
                    liq_price = entry_price * (1 + 1/leverage)
                    distance_pct = (liq_price - current_price) / current_price * 100

                # Get saves used from position manager
                saves_used = 0
                if self.position_manager:
                    managed = self.position_manager.get_position_by_pair(pair)
                    if managed:
                        saves_used = managed.margin_topups

                saves_remaining = self.max_saves - saves_used

                # Determine risk level and action
                risk_level, action = self._assess_risk_level(
                    distance_pct, saves_used, saves_remaining
                )

                risks.append(PositionRisk(
                    position_id=pos.get("id", pair),
                    pair=pair,
                    side=side,
                    entry_price=entry_price,
                    current_price=current_price,
                    liquidation_price=round(liq_price, 2),
                    distance_to_liq_pct=round(distance_pct, 2),
                    saves_used=saves_used,
                    saves_remaining=saves_remaining,
                    unrealized_pnl=round(unrealized_pnl, 2),
                    risk_level=risk_level,
                    recommended_action=action
                ))

        except Exception as e:
            logger.error(f"Failed to analyze positions: {e}")

        # Sort by risk (critical first)
        risk_order = {"critical": 0, "final_stand": 1, "warning": 2, "safe": 3}
        risks.sort(key=lambda r: risk_order.get(r.risk_level, 4))

        return risks

    def _analyze_managed_positions(self) -> List[PositionRisk]:
        """Analyze positions tracked by position_manager (spot trading mode)"""
        risks = []

        if not self.position_manager:
            return risks

        for pos_id, pos in self.position_manager.positions.items():
            if pos.status != "open":
                continue

            current_price = self.api.get_current_price(pos.pair) if self.api else 0
            if not current_price:
                continue

            # Calculate distance to liquidation
            if pos.side.lower() in ("buy", "long"):
                distance_pct = (current_price - pos.liquidation_price) / current_price * 100
            else:
                distance_pct = (pos.liquidation_price - current_price) / current_price * 100

            saves_used = pos.margin_topups
            saves_remaining = self.max_saves - saves_used

            # Calculate unrealized PnL
            if pos.side.lower() in ("buy", "long"):
                pnl_pct = (current_price - pos.entry_price) / pos.entry_price
            else:
                pnl_pct = (pos.entry_price - current_price) / pos.entry_price
            unrealized_pnl = pos.size_usd * pos.leverage * pnl_pct

            risk_level, action = self._assess_risk_level(distance_pct, saves_used, saves_remaining)

            risks.append(PositionRisk(
                position_id=pos_id,
                pair=pos.pair,
                side=pos.side,
                entry_price=pos.entry_price,
                current_price=current_price,
                liquidation_price=pos.liquidation_price,
                distance_to_liq_pct=round(distance_pct, 2),
                saves_used=saves_used,
                saves_remaining=saves_remaining,
                unrealized_pnl=round(unrealized_pnl, 2),
                risk_level=risk_level,
                recommended_action=action
            ))

        # Sort by risk (critical first)
        risk_order = {"critical": 0, "final_stand": 1, "warning": 2, "safe": 3}
        risks.sort(key=lambda r: risk_order.get(r.risk_level, 4))

        return risks

    def _assess_risk_level(self, distance_pct: float, saves_used: int, saves_remaining: int) -> Tuple[str, str]:
        """
        Assess risk level and recommend action

        Returns (risk_level, recommended_action)
        """
        # Critical: within 2% of liquidation
        if distance_pct <= self.critical_distance:
            if saves_remaining > 0:
                return "critical", f"ADD_MARGIN_NOW (save {saves_used + 1}/{self.max_saves})"
            else:
                return "final_stand", "CLOSE_POSITION (all saves used, take 2% max loss)"

        # Warning: within 5% of liquidation
        elif distance_pct <= self.trigger_distance:
            if saves_remaining > 0:
                return "warning", f"PREPARE_MARGIN (save {saves_used + 1}/{self.max_saves} ready)"
            else:
                return "final_stand", "MONITOR_CLOSELY (all saves used)"

        # Safe: more than 5% from liquidation
        else:
            return "safe", "HOLD (position healthy)"

    def get_liquidation_zones(self, pair: str) -> List[LiquidationZone]:
        """
        Identify market liquidation zones where cascades might occur

        These are price levels where many leveraged positions would get liquidated,
        causing potential price cascades and trading opportunities.
        """
        zones = []

        try:
            # Get recent candle data
            candles = self.api.get_candles_public(pair, "ONE_HOUR", 168)  # 1 week

            if not candles or len(candles) < 24:
                return zones

            # Extract price data
            closes = [float(c['close']) if isinstance(c, dict) else float(c[4]) for c in candles]
            highs = [float(c['high']) if isinstance(c, dict) else float(c[2]) for c in candles]
            lows = [float(c['low']) if isinstance(c, dict) else float(c[1]) for c in candles]

            current_price = closes[0]

            # Identify swing highs/lows as potential liquidation zones
            # Traders often place stops near these levels

            # Recent swing high (resistance) - long liquidation zone if price drops here
            recent_high = max(highs[:24])
            # Leveraged longs from the top would get liquidated below this
            long_liq_zone = recent_high * 0.75  # Assuming 4x leverage average

            # Recent swing low (support) - short liquidation zone if price rises here
            recent_low = min(lows[:24])
            # Leveraged shorts from the bottom would get liquidated above this
            short_liq_zone = recent_low * 1.33  # Assuming 4x leverage average

            # Weekly high/low for larger zones
            weekly_high = max(highs)
            weekly_low = min(lows)

            # Add zones
            if long_liq_zone < current_price:
                zones.append(LiquidationZone(
                    price_level=round(long_liq_zone, 2),
                    zone_type="long_liquidation",
                    estimated_volume=abs(recent_high - long_liq_zone) * 1000,  # Rough estimate
                    strength=0.7
                ))

            if short_liq_zone > current_price:
                zones.append(LiquidationZone(
                    price_level=round(short_liq_zone, 2),
                    zone_type="short_liquidation",
                    estimated_volume=abs(short_liq_zone - recent_low) * 1000,
                    strength=0.7
                ))

            # Add weekly extremes as major zones
            if weekly_low * 0.75 < current_price:
                zones.append(LiquidationZone(
                    price_level=round(weekly_low * 0.75, 2),
                    zone_type="major_long_liquidation",
                    estimated_volume=abs(weekly_high - weekly_low) * 5000,
                    strength=0.9
                ))

        except Exception as e:
            logger.error(f"Failed to identify liquidation zones: {e}")

        return zones

    def generate_save_strategy(self, position_risk: PositionRisk) -> Dict:
        """
        Generate strategy to save a position at risk

        Returns detailed action plan
        """
        if position_risk.saves_remaining <= 0:
            return {
                "action": "accept_loss",
                "reason": "All saves exhausted",
                "max_loss_percent": self.max_loss_after_saves,
                "details": "Close position to limit loss to 2% of balance"
            }

        # Calculate margin needed to push liquidation further
        margin_to_add = self.margin_amount

        # Estimate new liquidation after adding margin
        # More margin = lower effective leverage = further liquidation
        current_margin = position_risk.entry_price * (1 / 4)  # Rough estimate
        new_margin = current_margin + margin_to_add

        leverage = 4  # Default
        if position_risk.side.lower() in ("buy", "long"):
            new_liq = position_risk.entry_price * (1 - new_margin / (position_risk.entry_price * leverage))
        else:
            new_liq = position_risk.entry_price * (1 + new_margin / (position_risk.entry_price * leverage))

        return {
            "action": "add_margin",
            "margin_amount": margin_to_add,
            "save_number": position_risk.saves_used + 1,
            "saves_remaining_after": position_risk.saves_remaining - 1,
            "current_liquidation": position_risk.liquidation_price,
            "estimated_new_liquidation": round(new_liq, 2),
            "urgency": position_risk.risk_level,
            "details": f"Add ${margin_to_add} margin to push liquidation from ${position_risk.liquidation_price} to ~${new_liq:.2f}"
        }

    def analyze(self, market_data: dict = None) -> Dict:
        """
        Main analysis method - called by bot each cycle

        Returns action recommendations for all positions
        """
        results = {
            "timestamp": datetime.now().isoformat(),
            "positions_analyzed": 0,
            "positions_at_risk": 0,
            "critical_positions": [],
            "actions_needed": []
        }

        # Analyze all positions
        risks = self.analyze_positions()
        results["positions_analyzed"] = len(risks)

        for risk in risks:
            if risk.risk_level in ("critical", "final_stand", "warning"):
                results["positions_at_risk"] += 1

            if risk.risk_level == "critical":
                results["critical_positions"].append({
                    "pair": risk.pair,
                    "distance_to_liq": f"{risk.distance_to_liq_pct:.2f}%",
                    "saves_remaining": risk.saves_remaining
                })

                # Generate save strategy
                strategy = self.generate_save_strategy(risk)
                results["actions_needed"].append({
                    "pair": risk.pair,
                    "action": strategy["action"],
                    "urgency": risk.risk_level,
                    "details": strategy
                })

            elif risk.risk_level == "final_stand":
                # All saves used, monitor for 2% max loss
                results["actions_needed"].append({
                    "pair": risk.pair,
                    "action": "monitor_for_close",
                    "urgency": "high",
                    "max_loss_percent": self.max_loss_after_saves,
                    "details": f"All {self.max_saves} saves used. Close if loss exceeds 2%."
                })

        return results

    def get_status(self) -> Dict:
        """Get strategy status summary"""
        risks = self.analyze_positions()

        return {
            "total_positions": len(risks),
            "safe": len([r for r in risks if r.risk_level == "safe"]),
            "warning": len([r for r in risks if r.risk_level == "warning"]),
            "critical": len([r for r in risks if r.risk_level == "critical"]),
            "final_stand": len([r for r in risks if r.risk_level == "final_stand"]),
            "positions": [
                {
                    "pair": r.pair,
                    "side": r.side,
                    "distance_to_liq": f"{r.distance_to_liq_pct:.2f}%",
                    "saves": f"{r.saves_used}/{self.max_saves}",
                    "risk": r.risk_level,
                    "action": r.recommended_action
                }
                for r in risks
            ]
        }
