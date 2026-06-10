#!/usr/bin/env python3
"""
Balance Manager - Dynamic Position Sizing Based on Account Balance

Features:
1. Fetches real balance from Coinbase
2. Optimizes trade size based on available capital
3. Scales position size as balance grows
4. Protects capital when balance is low
5. Only takes 2% loss AFTER 3 liquidation saves fail
"""

import logging
from datetime import datetime
from typing import Dict, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class BalanceInfo:
    """Current account balance info"""
    total_balance_usd: float
    available_balance_usd: float
    in_positions_usd: float
    unrealized_pnl: float
    timestamp: str


class BalanceManager:
    """
    Manages position sizing based on actual account balance

    Rules:
    - Under $500: Trade 10% of balance (conservative)
    - $500-$1000: Trade 15% of balance
    - $1000-$2000: Trade 20% of balance
    - Over $2000 (surplus): Trade up to 25% with more aggressive scaling

    Loss Management:
    - Max 2% loss PER TRADE only after 3 liquidation saves fail
    - Before 3 saves: fight for the position
    """

    SURPLUS_THRESHOLD = 2000  # $2k = surplus capital

    # Position sizing tiers
    SIZING_TIERS = [
        (500, 0.10),    # Under $500: 10%
        (1000, 0.15),   # $500-$1000: 15%
        (2000, 0.20),   # $1000-$2000: 20%
        (float('inf'), 0.25)  # Over $2000: 25%
    ]

    def __init__(self, config: dict, api=None):
        self.config = config
        self.api = api

        # Settings
        self.max_loss_percent = config.get("risk_management", {}).get("max_loss_after_saves_percent", 2.0)
        self.surplus_threshold = config.get("balance_manager", {}).get("surplus_threshold", 2000)

        # Cached balance
        self._cached_balance: Optional[BalanceInfo] = None
        self._cache_time: Optional[datetime] = None
        self._cache_ttl_seconds = 60  # Refresh every 60 seconds

        logger.info(f"BalanceManager initialized: surplus threshold ${self.surplus_threshold}")

    def get_balance(self, force_refresh: bool = False) -> Optional[BalanceInfo]:
        """
        Get current account balance from Coinbase

        Returns BalanceInfo with total, available, and in-position amounts
        """
        # Check cache
        if not force_refresh and self._cached_balance and self._cache_time:
            age = (datetime.now() - self._cache_time).total_seconds()
            if age < self._cache_ttl_seconds:
                return self._cached_balance

        if not self.api:
            logger.warning("No API available for balance check")
            return None

        try:
            # Get account info from Coinbase
            # Use regular accounts endpoint (works for all accounts)
            accounts = self.api.get_accounts()
            total = 0
            available = 0

            if accounts:
                for account in accounts:
                    currency = account.get("currency", "")
                    # Sum USD and USDC balances
                    if currency in ("USD", "USDC"):
                        bal = account.get("available_balance", {})
                        avail = float(bal.get("value", 0)) if isinstance(bal, dict) else float(bal or 0)
                        available += avail
                        total += avail

            in_positions = 0
            unrealized = 0

            # Skip perpetuals check - using spot trading
            # Perpetuals portfolio endpoint returns 404 if not enabled

            self._cached_balance = BalanceInfo(
                total_balance_usd=total,
                available_balance_usd=available,
                in_positions_usd=in_positions,
                unrealized_pnl=unrealized,
                timestamp=datetime.now().isoformat()
            )
            self._cache_time = datetime.now()

            logger.info(f"Balance updated: Total ${total:.2f}, Available ${available:.2f}")

            return self._cached_balance

        except Exception as e:
            logger.error(f"Failed to get balance: {e}")
            return self._cached_balance  # Return cached if available

    def has_surplus_capital(self) -> bool:
        """Check if account has surplus capital ($2k+)"""
        balance = self.get_balance()
        if not balance:
            return False
        return balance.total_balance_usd >= self.surplus_threshold

    def get_optimal_position_size(self, leverage: int = 4) -> Dict:
        """
        Calculate optimal position size based on current balance

        Returns dict with:
        - position_size_usd: Recommended position size
        - max_risk_usd: Maximum loss allowed (2% after 3 saves)
        - tier: Current balance tier
        - leverage_adjusted: Position value after leverage
        """
        balance = self.get_balance()

        if not balance:
            # Fallback to config defaults
            default_size = self.config.get("strategy", {}).get("lot_size_usd", 100)
            return {
                "position_size_usd": default_size,
                "max_risk_usd": default_size * 0.02,
                "tier": "unknown",
                "leverage_adjusted": default_size * leverage,
                "balance": 0,
                "available": 0
            }

        total = balance.total_balance_usd
        available = balance.available_balance_usd

        # Capital boundaries (keep cash reserve, cap usable trading cash)
        boundaries = self.config.get("capital_boundaries", {})
        reserve_usd = float(boundaries.get("spot_reserve_usd", 0.0) or 0.0)
        trade_cap_pct = float(boundaries.get("spot_trade_cap_pct", 1.0) or 1.0)
        effective_available = max(0.0, available - reserve_usd)
        if trade_cap_pct > 0 and trade_cap_pct < 1.0:
            effective_available = effective_available * trade_cap_pct
        if effective_available <= 0:
            return {
                "position_size_usd": 0,
                "max_risk_usd": 0,
                "tier": "reserve_only",
                "leverage_adjusted": 0,
                "balance": total,
                "available": available
            }

        # Determine sizing tier
        size_percent = 0.10  # Default conservative
        tier_name = "conservative"

        sizing_cfg = self.config.get("position_sizing", {})
        if sizing_cfg.get("mode") == "fixed_percent":
            size_percent = float(sizing_cfg.get("percent", size_percent))
            tier_name = f"fixed_{int(size_percent * 100)}"

        for threshold, percent in self.SIZING_TIERS:
            if total < threshold:
                size_percent = percent
                if threshold == 500:
                    tier_name = "micro"
                elif threshold == 1000:
                    tier_name = "small"
                elif threshold == 2000:
                    tier_name = "growth"
                else:
                    tier_name = "surplus"
                break

        # Calculate position size (based on available, not total)
        raw_size = effective_available * size_percent

        # Apply minimum and maximum (DYNAMIC for small accounts)
        # Minimum: 5% of available OR $5, whichever is larger
        min_size = max(5, effective_available * 0.05)
        # Max size can be controlled by risk caps
        risk_caps = self.config.get("risk_caps", {})
        max_pos_pct = risk_caps.get("max_position_percent")
        max_size = effective_available * 0.5  # Default safety
        if max_pos_pct is not None:
            try:
                max_size = available * (float(max_pos_pct) / 100.0)
            except Exception:
                pass

        position_size = max(min_size, min(raw_size, max_size))

        # Enforce minimum entry size once balance reaches threshold
        min_entry_cfg = self.config.get("min_entry", {})
        if min_entry_cfg.get("enabled", False):
            threshold = float(min_entry_cfg.get("threshold_usd", 0))
            min_size_override = float(min_entry_cfg.get("min_size_usd", 0))
            if total >= threshold and min_size_override > 0:
                position_size = max(position_size, min_size_override)

        # Hard cap: max position percent of available (risk caps)
        risk_caps = self.config.get("risk_caps", {})
        max_pos_pct = risk_caps.get("max_position_percent")
        cap_applied = False
        if max_pos_pct is not None:
            try:
                cap_size = available * (float(max_pos_pct) / 100.0)
                if cap_size >= 0:
                    if position_size > cap_size:
                        position_size = cap_size
                        cap_applied = True
            except Exception:
                pass

        # Max risk is 2% of total balance (but only applied after 3 saves fail)
        max_risk = total * (self.max_loss_percent / 100)

        result = {
            "position_size_usd": round(position_size, 2),
            "max_risk_usd": round(max_risk, 2),
            "tier": tier_name,
            "tier_percent": size_percent * 100,
            "leverage": leverage,
            "leverage_adjusted": round(position_size * leverage, 2),
            "balance": round(total, 2),
            "available": round(available, 2),
            "has_surplus": total >= self.surplus_threshold,
            "cap_applied": cap_applied
        }

        logger.info(f"Position sizing: ${position_size:.2f} ({tier_name} tier, {size_percent*100:.0f}% of ${available:.2f} available)")

        return result

    def calculate_max_loss_for_position(self, position_size: float, saves_used: int) -> Dict:
        """
        Calculate max loss based on saves used

        Rules:
        - 0-2 saves used: No max loss (fight for position)
        - 3 saves used: Apply 2% max loss rule
        """
        balance = self.get_balance()
        total = balance.total_balance_usd if balance else 1000

        if saves_used < 3:
            # Still fighting for position - no forced close
            return {
                "max_loss_usd": None,  # No limit yet
                "saves_remaining": 3 - saves_used,
                "status": "fighting",
                "message": f"Position protected - {3 - saves_used} saves remaining"
            }
        else:
            # All saves used - apply 2% max loss
            max_loss = total * (self.max_loss_percent / 100)
            return {
                "max_loss_usd": round(max_loss, 2),
                "saves_remaining": 0,
                "status": "final_stop",
                "message": f"All saves used - max loss ${max_loss:.2f} (2% of ${total:.2f})"
            }

    def should_close_position(self, position: dict, current_price: float, saves_used: int) -> Tuple[bool, str]:
        """
        Determine if position should be closed based on loss and saves

        Returns (should_close, reason)
        """
        entry = position.get("entry_price", 0)
        side = position.get("side", "buy")
        size = position.get("size_usd", 0)
        leverage = position.get("leverage", 4)

        if not entry:
            return False, "No entry price"

        # Calculate current loss
        if side.lower() in ("buy", "long"):
            pnl_pct = (current_price - entry) / entry
        else:
            pnl_pct = (entry - current_price) / entry

        pnl_usd = size * leverage * pnl_pct

        # If in profit, don't close
        if pnl_usd >= 0:
            return False, f"Position in profit: ${pnl_usd:.2f}"

        # Check if saves are exhausted
        loss_rules = self.calculate_max_loss_for_position(size, saves_used)

        if loss_rules["max_loss_usd"] is None:
            # Still have saves - don't force close
            return False, loss_rules["message"]

        # All saves used - check if loss exceeds 2%
        if abs(pnl_usd) >= loss_rules["max_loss_usd"]:
            return True, f"Max loss exceeded after 3 saves: ${abs(pnl_usd):.2f} > ${loss_rules['max_loss_usd']:.2f}"

        return False, f"Loss ${abs(pnl_usd):.2f} within limit ${loss_rules['max_loss_usd']:.2f}"

    def get_status(self) -> Dict:
        """Get balance manager status"""
        balance = self.get_balance()
        sizing = self.get_optimal_position_size()

        return {
            "balance": {
                "total": balance.total_balance_usd if balance else 0,
                "available": balance.available_balance_usd if balance else 0,
                "in_positions": balance.in_positions_usd if balance else 0,
                "unrealized_pnl": balance.unrealized_pnl if balance else 0
            },
            "sizing": sizing,
            "surplus_capital": self.has_surplus_capital(),
            "surplus_threshold": self.surplus_threshold,
            "max_loss_rule": "2% of balance AFTER 3 liquidation saves fail"
        }
