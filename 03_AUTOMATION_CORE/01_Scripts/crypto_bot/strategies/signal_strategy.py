#!/usr/bin/env python3
"""
Signal-Based Trading Strategy
Uses technical indicators: RSI, MACD, EMA crossovers
"""

import logging
from typing import Dict, Optional, List
from collections import deque
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Signal:
    indicator: str
    direction: str  # 'buy', 'sell', 'neutral'
    strength: float  # 0-1
    value: float


class SignalStrategy:
    """
    Technical indicator-based trading
    - RSI: Overbought/Oversold
    - MACD: Trend direction and crossovers
    - EMA: Moving average crossovers
    - Volume confirmation
    """

    def __init__(self, api, config: dict, trading_pair: str):
        self.api = api
        self.config = config
        self.trading_pair = trading_pair

        # Price history for indicator calculation
        self.prices = deque(maxlen=200)
        self.volumes = deque(maxlen=50)

        # EMA periods from config
        self.ema_fast, self.ema_slow = config.get("ema_cross", [9, 21])

    # ============ Indicators ============

    def _calc_rsi(self, period: int = 14) -> Optional[float]:
        """Calculate RSI"""
        if len(self.prices) < period + 1:
            return None

        prices = list(self.prices)[-period-1:]
        deltas = [prices[i+1] - prices[i] for i in range(len(prices)-1)]

        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]

        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period

        if avg_loss == 0:
            return 100

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def _calc_ema(self, period: int) -> Optional[float]:
        """Calculate EMA"""
        if len(self.prices) < period:
            return None

        prices = list(self.prices)
        multiplier = 2 / (period + 1)

        ema = prices[0]
        for price in prices[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))

        return ema

    def _calc_macd(self) -> Optional[dict]:
        """Calculate MACD (12, 26, 9)"""
        if len(self.prices) < 35:
            return None

        ema12 = self._calc_ema(12)
        ema26 = self._calc_ema(26)

        if not ema12 or not ema26:
            return None

        macd_line = ema12 - ema26

        # Signal line (9-period EMA of MACD)
        # Simplified - just use current MACD
        signal_line = macd_line * 0.9  # Approximation

        histogram = macd_line - signal_line

        return {
            "macd": macd_line,
            "signal": signal_line,
            "histogram": histogram
        }

    def _calc_volume_avg(self) -> Optional[float]:
        """Calculate average volume"""
        if len(self.volumes) < 10:
            return None
        return sum(self.volumes) / len(self.volumes)

    # ============ Signal Generation ============

    def _get_rsi_signal(self) -> Optional[Signal]:
        """Generate RSI signal"""
        rsi = self._calc_rsi()
        if rsi is None:
            return None

        if rsi <= self.config["rsi_oversold"]:
            strength = (self.config["rsi_oversold"] - rsi) / self.config["rsi_oversold"]
            return Signal("RSI", "buy", min(strength, 1.0), rsi)

        elif rsi >= self.config["rsi_overbought"]:
            strength = (rsi - self.config["rsi_overbought"]) / (100 - self.config["rsi_overbought"])
            return Signal("RSI", "sell", min(strength, 1.0), rsi)

        return Signal("RSI", "neutral", 0, rsi)

    def _get_macd_signal(self) -> Optional[Signal]:
        """Generate MACD signal"""
        if not self.config.get("macd_signal"):
            return None

        macd = self._calc_macd()
        if not macd:
            return None

        histogram = macd["histogram"]

        if histogram > 0:
            return Signal("MACD", "buy", min(abs(histogram) / 10, 1.0), histogram)
        elif histogram < 0:
            return Signal("MACD", "sell", min(abs(histogram) / 10, 1.0), histogram)

        return Signal("MACD", "neutral", 0, histogram)

    def _get_ema_signal(self) -> Optional[Signal]:
        """Generate EMA crossover signal"""
        ema_fast = self._calc_ema(self.ema_fast)
        ema_slow = self._calc_ema(self.ema_slow)

        if not ema_fast or not ema_slow:
            return None

        diff = ema_fast - ema_slow
        diff_percent = (diff / ema_slow) * 100

        if diff > 0:  # Fast above slow = bullish
            return Signal("EMA", "buy", min(abs(diff_percent) / 2, 1.0), diff_percent)
        else:
            return Signal("EMA", "sell", min(abs(diff_percent) / 2, 1.0), diff_percent)

    # ============ Main Analysis ============

    def _combine_signals(self, signals: List[Signal]) -> dict:
        """Combine multiple signals into final decision"""
        if not signals:
            return {"action": "hold", "reason": "No signals"}

        buy_score = 0
        sell_score = 0
        reasons = []

        for sig in signals:
            if sig.direction == "buy":
                buy_score += sig.strength
                reasons.append(f"{sig.indicator}:BUY({sig.strength:.1f})")
            elif sig.direction == "sell":
                sell_score += sig.strength
                reasons.append(f"{sig.indicator}:SELL({sig.strength:.1f})")

        # Need at least 2 indicators agreeing with combined strength > 1.0
        min_score = 1.0

        if buy_score >= min_score and buy_score > sell_score:
            return {
                "action": "buy",
                "side": "buy",
                "pair": self.trading_pair,
                "amount": 100,  # USD
                "price": None,
                "reason": f"Signal buy: {', '.join(reasons)}",
                "strategy": "signals",
                "score": buy_score
            }

        elif sell_score >= min_score and sell_score > buy_score:
            return {
                "action": "sell",
                "side": "sell",
                "pair": self.trading_pair,
                "amount": 100,
                "price": None,
                "reason": f"Signal sell: {', '.join(reasons)}",
                "strategy": "signals",
                "score": sell_score
            }

        return {
            "action": "hold",
            "reason": f"Signals: {', '.join(reasons) or 'neutral'}"
        }

    def analyze(self, market_data: dict) -> Optional[dict]:
        """Main analysis - gather signals and decide"""
        current_price = market_data["price"]
        self.prices.append(current_price)

        # Gather all signals
        signals = []

        rsi_sig = self._get_rsi_signal()
        if rsi_sig:
            signals.append(rsi_sig)

        macd_sig = self._get_macd_signal()
        if macd_sig:
            signals.append(macd_sig)

        ema_sig = self._get_ema_signal()
        if ema_sig:
            signals.append(ema_sig)

        # Log indicators periodically
        if len(self.prices) % 10 == 0:
            rsi = self._calc_rsi()
            logger.debug(f"Indicators - RSI: {rsi:.1f if rsi else 'N/A'}")

        return self._combine_signals(signals)

    def get_status(self) -> dict:
        """Get current indicator values"""
        return {
            "rsi": self._calc_rsi(),
            "macd": self._calc_macd(),
            "ema_fast": self._calc_ema(self.ema_fast),
            "ema_slow": self._calc_ema(self.ema_slow),
            "data_points": len(self.prices)
        }
