#!/usr/bin/env python3
"""
Trade Optimizer - Smart Enhancements for Maximum Profit

Data-backed features:
1. Break-even stop after 1R profit
2. Trailing TP after 2R
3. Correlation filter (avoid double exposure)
4. Drawdown circuit breaker
5. Cool-down after losses
6. Smart pair selection (best opportunity)
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import json
from pathlib import Path

logger = logging.getLogger(__name__)


# Correlation matrix for major crypto pairs (based on historical data)
# Values > 0.7 = highly correlated, avoid holding both
CORRELATION_MATRIX = {
    ("BTC-USD", "ETH-USD"): 0.85,
    ("BTC-USD", "SOL-USD"): 0.78,
    ("BTC-USD", "AVAX-USD"): 0.75,
    ("ETH-USD", "SOL-USD"): 0.82,
    ("ETH-USD", "AVAX-USD"): 0.80,
    ("SOL-USD", "AVAX-USD"): 0.88,
}


@dataclass
class PairAnalysis:
    """Analysis of a trading pair's opportunity"""
    pair: str
    current_price: float

    # Trend metrics
    trend_direction: str  # bullish, bearish, neutral
    trend_strength: float  # 0-1

    # Distance metrics
    distance_from_support_pct: float
    distance_from_resistance_pct: float

    # Volatility
    atr_percent: float  # Average True Range as % of price

    # Opportunity score (higher = better)
    opportunity_score: float = 0.0

    # Room for growth (distance to next resistance)
    upside_potential_pct: float = 0.0
    downside_risk_pct: float = 0.0
    risk_reward_ratio: float = 0.0


class TradeOptimizer:
    """
    Optimizes trade selection and management

    Features:
    - Selects best pair based on opportunity score
    - Filters correlated positions
    - Manages break-even stops
    - Circuit breaker for drawdowns
    """

    def __init__(self, config: dict, api=None, data_dir: str = None):
        self.config = config
        self.api = api

        optimizer_config = config.get("trade_optimizer", {})

        # Break-even settings
        self.breakeven_at_r = optimizer_config.get("breakeven_at_r", 1.0)  # Move to BE after 1R
        self.trail_after_r = optimizer_config.get("trail_after_r", 2.0)  # Start trailing after 2R
        self.trail_percent = optimizer_config.get("trail_percent", 1.5)  # Trail by 1.5%

        # Correlation filter
        self.correlation_threshold = optimizer_config.get("correlation_threshold", 0.7)
        self.max_correlated_positions = optimizer_config.get("max_correlated_positions", 1)

        # Drawdown circuit breaker
        self.daily_drawdown_limit_pct = optimizer_config.get("daily_drawdown_limit_pct", 5.0)
        self.circuit_breaker_active = False
        self.circuit_breaker_until = None

        # Cool-down after losses
        self.cooldown_after_losses = optimizer_config.get("cooldown_after_losses", 2)
        self.cooldown_minutes = optimizer_config.get("cooldown_minutes", 60)
        self.consecutive_losses = 0
        self.cooldown_until = None

        # Daily tracking
        self.daily_pnl = 0.0
        self.daily_starting_capital = config.get("account", {}).get("starting_capital_usd", 1000)
        self.last_reset = datetime.now().date()

        # Data storage
        if data_dir:
            self.data_dir = Path(data_dir)
        else:
            self.data_dir = Path(__file__).parent.parent / "data"

        self.state_file = self.data_dir / "optimizer_state.json"
        self._load_state()

        logger.info(f"TradeOptimizer initialized: BE at {self.breakeven_at_r}R, "
                   f"trail after {self.trail_after_r}R, "
                   f"drawdown limit {self.daily_drawdown_limit_pct}%")

    # === Smart Pair Selection ===

    def analyze_pair(self, pair: str, candles: list, key_levels: dict = None) -> PairAnalysis:
        """
        Analyze a pair for trading opportunity

        Scores based on:
        - Trend strength (EMA alignment)
        - Distance from support (room to fall = risk)
        - Distance from resistance (room to grow = reward)
        - Risk/reward ratio
        - Volatility (higher = more opportunity but more risk)
        """
        if not candles or len(candles) < 20:
            return PairAnalysis(
                pair=pair, current_price=0, trend_direction="neutral",
                trend_strength=0, distance_from_support_pct=0,
                distance_from_resistance_pct=0, atr_percent=0
            )

        # Get prices
        closes = [float(c['close']) if isinstance(c, dict) else float(c[4]) for c in candles]
        highs = [float(c['high']) if isinstance(c, dict) else float(c[2]) for c in candles]
        lows = [float(c['low']) if isinstance(c, dict) else float(c[1]) for c in candles]

        current_price = closes[0]

        # Calculate EMAs
        ema_20 = self._calc_ema(closes, 20)
        ema_50 = self._calc_ema(closes, 50) if len(closes) >= 50 else ema_20

        # Trend direction and strength
        if ema_20 > ema_50:
            trend_direction = "bullish"
            trend_strength = min((ema_20 - ema_50) / ema_50 * 100, 1.0)
        elif ema_20 < ema_50:
            trend_direction = "bearish"
            trend_strength = min((ema_50 - ema_20) / ema_50 * 100, 1.0)
        else:
            trend_direction = "neutral"
            trend_strength = 0

        # ATR for volatility
        atr = self._calc_atr(highs, lows, closes, 14)
        atr_percent = (atr / current_price) * 100

        # Key levels (support/resistance)
        recent_low = min(lows[:20])
        recent_high = max(highs[:20])

        if key_levels:
            support = key_levels.get("support", recent_low)
            resistance = key_levels.get("resistance", recent_high)
        else:
            support = recent_low
            resistance = recent_high

        # Distance calculations
        distance_from_support = ((current_price - support) / current_price) * 100
        distance_from_resistance = ((resistance - current_price) / current_price) * 100

        # Risk/Reward ratio
        downside_risk = distance_from_support
        upside_potential = distance_from_resistance

        if downside_risk > 0:
            rr_ratio = upside_potential / downside_risk
        else:
            rr_ratio = upside_potential if upside_potential > 0 else 0

        # Opportunity score calculation
        # Higher score = better opportunity
        # Factors: trend strength, R:R ratio, moderate volatility
        score = 0

        # Trend alignment (0-30 points)
        score += trend_strength * 30

        # Risk/Reward (0-40 points) - prefer 2:1 or better
        if rr_ratio >= 3:
            score += 40
        elif rr_ratio >= 2:
            score += 30
        elif rr_ratio >= 1.5:
            score += 20
        elif rr_ratio >= 1:
            score += 10

        # Volatility sweet spot (0-20 points) - 1-3% ATR is ideal
        if 1 <= atr_percent <= 3:
            score += 20
        elif 0.5 <= atr_percent <= 4:
            score += 10

        # Room for growth (0-10 points)
        if upside_potential >= 10:
            score += 10
        elif upside_potential >= 5:
            score += 5

        return PairAnalysis(
            pair=pair,
            current_price=current_price,
            trend_direction=trend_direction,
            trend_strength=trend_strength,
            distance_from_support_pct=round(distance_from_support, 2),
            distance_from_resistance_pct=round(distance_from_resistance, 2),
            atr_percent=round(atr_percent, 2),
            opportunity_score=round(score, 1),
            upside_potential_pct=round(upside_potential, 2),
            downside_risk_pct=round(downside_risk, 2),
            risk_reward_ratio=round(rr_ratio, 2)
        )

    def select_best_pair(self, pairs: List[str], open_positions: List[str] = None) -> Optional[PairAnalysis]:
        """
        Select the best pair to trade based on opportunity score

        Filters:
        1. Remove pairs correlated with open positions
        2. Rank by opportunity score
        3. Return best opportunity
        """
        if not self.api:
            return None

        open_positions = open_positions or []
        analyses = []

        for pair in pairs:
            # Skip if correlated with open position
            if self._is_correlated_with_positions(pair, open_positions):
                logger.debug(f"Skipping {pair}: correlated with open position")
                continue

            # Get candle data
            try:
                candles = self.api.get_candles_public(pair, "ONE_HOUR", 100)
                if candles:
                    analysis = self.analyze_pair(pair, candles)
                    analyses.append(analysis)
            except Exception as e:
                logger.warning(f"Could not analyze {pair}: {e}")

        if not analyses:
            return None

        # Sort by opportunity score (highest first)
        analyses.sort(key=lambda x: x.opportunity_score, reverse=True)

        best = analyses[0]
        logger.info(f"Best opportunity: {best.pair} (score: {best.opportunity_score}, "
                   f"R:R {best.risk_reward_ratio}, trend: {best.trend_direction})")

        return best

    # === Correlation Filter ===

    def _is_correlated_with_positions(self, pair: str, open_positions: List[str]) -> bool:
        """Check if pair is highly correlated with any open position"""
        for open_pair in open_positions:
            correlation = self._get_correlation(pair, open_pair)
            if correlation >= self.correlation_threshold:
                return True
        return False

    def _get_correlation(self, pair1: str, pair2: str) -> float:
        """Get correlation between two pairs"""
        if pair1 == pair2:
            return 1.0

        # Check both orderings
        key1 = (pair1, pair2)
        key2 = (pair2, pair1)

        if key1 in CORRELATION_MATRIX:
            return CORRELATION_MATRIX[key1]
        if key2 in CORRELATION_MATRIX:
            return CORRELATION_MATRIX[key2]

        return 0.0  # Assume uncorrelated if not in matrix

    def get_uncorrelated_pairs(self, pairs: List[str], open_positions: List[str]) -> List[str]:
        """Filter to only uncorrelated pairs"""
        return [p for p in pairs if not self._is_correlated_with_positions(p, open_positions)]

    # === Break-Even Stop Management ===

    def calculate_stop_adjustment(self, position: dict, current_price: float) -> Optional[dict]:
        """
        Calculate if stop should be moved to break-even or trailed

        Rules:
        1. After 1R profit: move stop to entry (break-even)
        2. After 2R profit: start trailing
        """
        entry = position.get("entry_price", 0)
        stop = position.get("stop_loss", 0)
        side = position.get("side", "buy")
        current_stop = position.get("current_stop", stop)

        if not entry or not stop:
            return None

        # Calculate R (risk per unit)
        risk = abs(entry - stop)

        # Calculate current profit in R
        if side.lower() in ("buy", "long"):
            profit = current_price - entry
            profit_r = profit / risk if risk > 0 else 0
        else:
            profit = entry - current_price
            profit_r = profit / risk if risk > 0 else 0

        result = {
            "current_profit_r": round(profit_r, 2),
            "current_stop": current_stop,
            "new_stop": None,
            "action": "none",
            "reason": ""
        }

        # Check for trailing (after 2R)
        if profit_r >= self.trail_after_r:
            if side.lower() in ("buy", "long"):
                trail_stop = current_price * (1 - self.trail_percent / 100)
                if trail_stop > current_stop:
                    result["new_stop"] = round(trail_stop, 2)
                    result["action"] = "trail"
                    result["reason"] = f"Trailing at {profit_r:.1f}R profit"
            else:
                trail_stop = current_price * (1 + self.trail_percent / 100)
                if trail_stop < current_stop:
                    result["new_stop"] = round(trail_stop, 2)
                    result["action"] = "trail"
                    result["reason"] = f"Trailing at {profit_r:.1f}R profit"

        # Check for break-even (after 1R)
        elif profit_r >= self.breakeven_at_r:
            if side.lower() in ("buy", "long"):
                if current_stop < entry:
                    result["new_stop"] = entry
                    result["action"] = "breakeven"
                    result["reason"] = f"Moving to break-even at {profit_r:.1f}R"
            else:
                if current_stop > entry:
                    result["new_stop"] = entry
                    result["action"] = "breakeven"
                    result["reason"] = f"Moving to break-even at {profit_r:.1f}R"

        return result

    # === Drawdown Circuit Breaker ===

    def record_pnl(self, pnl: float):
        """Record P&L and check circuit breaker"""
        self._check_daily_reset()

        self.daily_pnl += pnl

        # Check drawdown
        drawdown_pct = (self.daily_pnl / self.daily_starting_capital) * 100

        if drawdown_pct <= -self.daily_drawdown_limit_pct:
            self.circuit_breaker_active = True
            self.circuit_breaker_until = datetime.now() + timedelta(hours=24)
            logger.warning(f"CIRCUIT BREAKER ACTIVATED: {drawdown_pct:.1f}% daily drawdown")

        # Track consecutive losses for cool-down
        if pnl < 0:
            self.consecutive_losses += 1
            if self.consecutive_losses >= self.cooldown_after_losses:
                self.cooldown_until = datetime.now() + timedelta(minutes=self.cooldown_minutes)
                logger.info(f"Cool-down activated: {self.consecutive_losses} consecutive losses, "
                           f"waiting {self.cooldown_minutes} minutes")
        else:
            self.consecutive_losses = 0
            self.cooldown_until = None

        self._save_state()

    def can_trade(self) -> Tuple[bool, str]:
        """Check if trading is allowed"""
        self._check_daily_reset()

        # Circuit breaker check
        if self.circuit_breaker_active:
            if self.circuit_breaker_until and datetime.now() < self.circuit_breaker_until:
                remaining = (self.circuit_breaker_until - datetime.now()).total_seconds() / 3600
                return False, f"Circuit breaker active ({remaining:.1f}h remaining)"
            else:
                self.circuit_breaker_active = False
                self.circuit_breaker_until = None

        # Cool-down check
        if self.cooldown_until and datetime.now() < self.cooldown_until:
            remaining = (self.cooldown_until - datetime.now()).total_seconds() / 60
            return False, f"Cool-down active ({remaining:.0f}m remaining)"

        return True, "Trading allowed"

    def _check_daily_reset(self):
        """Reset daily counters at midnight"""
        if datetime.now().date() > self.last_reset:
            logger.info(f"Daily reset. Yesterday's P&L: ${self.daily_pnl:.2f}")
            self.daily_pnl = 0
            self.consecutive_losses = 0
            self.circuit_breaker_active = False
            self.last_reset = datetime.now().date()
            self._save_state()

    # === Helper Methods ===

    def _calc_ema(self, prices: list, period: int) -> float:
        """Calculate EMA"""
        if len(prices) < period:
            return prices[0] if prices else 0

        multiplier = 2 / (period + 1)
        ema = sum(prices[:period]) / period  # Start with SMA

        for price in prices[period:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))

        return ema

    def _calc_atr(self, highs: list, lows: list, closes: list, period: int) -> float:
        """Calculate Average True Range"""
        if len(highs) < period + 1:
            return 0

        true_ranges = []
        for i in range(1, min(len(highs), period + 1)):
            high_low = highs[i] - lows[i]
            high_close = abs(highs[i] - closes[i-1])
            low_close = abs(lows[i] - closes[i-1])
            true_ranges.append(max(high_low, high_close, low_close))

        return sum(true_ranges) / len(true_ranges) if true_ranges else 0

    # === State Persistence ===

    def _save_state(self):
        """Save state to JSON"""
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)

            state = {
                "last_updated": datetime.now().isoformat(),
                "daily_pnl": self.daily_pnl,
                "consecutive_losses": self.consecutive_losses,
                "circuit_breaker_active": self.circuit_breaker_active,
                "circuit_breaker_until": self.circuit_breaker_until.isoformat() if self.circuit_breaker_until else None,
                "cooldown_until": self.cooldown_until.isoformat() if self.cooldown_until else None,
                "last_reset": self.last_reset.isoformat()
            }

            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save optimizer state: {e}")

    def _load_state(self):
        """Load state from JSON"""
        try:
            if self.state_file.exists():
                with open(self.state_file) as f:
                    state = json.load(f)

                self.daily_pnl = state.get("daily_pnl", 0)
                self.consecutive_losses = state.get("consecutive_losses", 0)
                self.circuit_breaker_active = state.get("circuit_breaker_active", False)

                if state.get("circuit_breaker_until"):
                    self.circuit_breaker_until = datetime.fromisoformat(state["circuit_breaker_until"])
                if state.get("cooldown_until"):
                    self.cooldown_until = datetime.fromisoformat(state["cooldown_until"])
                if state.get("last_reset"):
                    self.last_reset = datetime.fromisoformat(state["last_reset"]).date()

                logger.info(f"Loaded optimizer state: daily P&L ${self.daily_pnl:.2f}")
        except Exception as e:
            logger.warning(f"Could not load optimizer state: {e}")

    # === Status ===

    def get_status(self) -> dict:
        """Get optimizer status"""
        can_trade, reason = self.can_trade()

        return {
            "can_trade": can_trade,
            "reason": reason,
            "daily_pnl": round(self.daily_pnl, 2),
            "daily_drawdown_pct": round((self.daily_pnl / self.daily_starting_capital) * 100, 2),
            "drawdown_limit_pct": self.daily_drawdown_limit_pct,
            "consecutive_losses": self.consecutive_losses,
            "circuit_breaker_active": self.circuit_breaker_active,
            "breakeven_at_r": self.breakeven_at_r,
            "trail_after_r": self.trail_after_r
        }
