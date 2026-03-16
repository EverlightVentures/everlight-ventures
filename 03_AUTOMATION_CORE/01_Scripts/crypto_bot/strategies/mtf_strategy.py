#!/usr/bin/env python3
"""
Multi-Timeframe (MTF) Strategy
- Yearly, Monthly, Weekly highs/lows as key levels
- EMA confluence across timeframes (20, 50, 100, 200)
- RSI divergence detection
- Fibonacci retracement zones
- Volume confirmation
- MACD momentum confirmation
- VWAP price position
"""

import logging
import json
from pathlib import Path
from typing import Dict, Optional, List, Tuple
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from intel.intel_router import get_liq_event_intel, get_magnet_intel
import pandas as pd
from strategies.breakout_classifier import dominant_timeframe as breakout_tf, classify_breakout

logger = logging.getLogger(__name__)


class Timeframe(Enum):
    YEARLY = "yearly"
    MONTHLY = "monthly"
    WEEKLY = "weekly"
    DAILY = "daily"


@dataclass
class KeyLevel:
    """Support/Resistance level with metadata"""
    price: float
    level_type: str  # 'high', 'low', 'fib'
    timeframe: str
    strength: float = 1.0  # Higher = more touches/confirmations
    last_tested: datetime = None


@dataclass
class FibLevel:
    """Fibonacci retracement level"""
    ratio: float
    price: float
    label: str


@dataclass
class Signal:
    """Trading signal with confluence score"""
    direction: str  # 'buy', 'sell', 'neutral'
    strength: float  # 0-1
    source: str
    details: str


@dataclass
class Position:
    entry_price: float
    size_usd: float
    side: str
    stop_loss: float
    take_profit: float
    entry_time: datetime = None
    highest_price: float = 0
    lowest_price: float = float('inf')


class MTFStrategy:
    """
    Multi-Timeframe Confluence Strategy

    Entry Criteria (need 3+ signals agreeing):
    1. Price near key level (yearly/monthly/weekly high or low)
    2. Fibonacci confluence (price at 0.382, 0.5, or 0.618 level)
    3. EMA alignment (20 > 50 > 100 > 200 for longs)
    4. RSI not extreme (30-70 range, or divergence)
    5. Volume above average

    Exit: Trailing stop + Fibonacci extension targets
    """

    FIB_RATIOS = [
        (0.236, "0.236"),
        (0.382, "0.382"),
        (0.5, "0.5"),
        (0.618, "0.618"),
        (0.786, "0.786"),
    ]

    FIB_EXTENSIONS = [
        (1.0, "1.0"),
        (1.272, "1.272"),
        (1.618, "1.618"),
        (2.0, "2.0"),
    ]

    # MACD defaults (can be overridden by config)
    MACD_FAST = 12
    MACD_SLOW = 26
    MACD_SIGNAL = 9

    def __init__(self, api, config: dict, trading_pair: str):
        self.api = api
        self.config = config
        self.trading_pair = trading_pair

        # Price history (5-min candles, ~1 year = 105,000 candles)
        self.cache_maxlen = int(self.config.get("warmup_cache_maxlen", 500))
        self.prices = deque(maxlen=self.cache_maxlen)
        self.highs = deque(maxlen=self.cache_maxlen)
        self.lows = deque(maxlen=self.cache_maxlen)
        self.volumes = deque(maxlen=self.cache_maxlen)
        self.timestamps = deque(maxlen=self.cache_maxlen)
        self.tf_defs = {
            "30m": 30 * 60,
            "1h": 60 * 60,
            "4h": 4 * 60 * 60,
            "1d": 24 * 60 * 60,
            "1w": 7 * 24 * 60 * 60,
            "1m": 30 * 24 * 60 * 60,
            "1y": 365 * 24 * 60 * 60
        }
        self.tf_cache_maxlen = int(self.config.get("tf_cache_maxlen", 500))
        self.tf_candles = {tf: deque(maxlen=self.tf_cache_maxlen) for tf in self.tf_defs}
        self.tf_current = {tf: None for tf in self.tf_defs}

        # Restore warmup cache if available
        try:
            cache = self._load_warmup_cache()
            if cache:
                self.prices.extend(cache.get("prices", [])[-self.cache_maxlen:])
                self.highs.extend(cache.get("highs", [])[-self.cache_maxlen:])
                self.lows.extend(cache.get("lows", [])[-self.cache_maxlen:])
                self.volumes.extend(cache.get("volumes", [])[-self.cache_maxlen:])
                self.timestamps.extend(cache.get("timestamps", [])[-self.cache_maxlen:])
                self.cache_loaded = True
                self.cache_loaded_points = len(self.prices)
                self._rebuild_tf_aggregates_from_cache()
        except Exception:
            pass
        if not hasattr(self, "cache_loaded"):
            self.cache_loaded = False
            self.cache_loaded_points = 0

        # Key levels storage
        self.key_levels: List[KeyLevel] = []
        self.fib_levels: List[FibLevel] = []

        # Historical data for multi-timeframe
        self.yearly_high = None
        self.yearly_low = None
        self.monthly_high = None
        self.monthly_low = None
        self.weekly_high = None
        self.weekly_low = None
        self.daily_high = None
        self.daily_low = None

        # Current position
        self.position: Optional[Position] = None

        # Config
        self.min_confluence = config.get("min_confluence_signals", 3)
        self.level_proximity_pct = config.get("level_proximity_percent", 0.5)
        self.scalp_relaxed = bool(config.get("scalp_relaxed", False))
        self.scalp_min_rr = float(config.get("scalp_min_rr", 1.8))
        self.scalp_min_volume_ratio = float(config.get("scalp_min_volume_ratio", 1.3))
        self.scalp_min_score = float(config.get("scalp_min_score", 1.0))

        # EMA periods
        self.ema_periods = self.config.get("ema_periods", [20, 50, 100, 200])

        # RSI + MACD settings (configurable for crypto tuning)
        self.rsi_period = self.config.get("rsi_period", 14)
        self.macd_fast = self.config.get("macd_fast", self.MACD_FAST)
        self.macd_slow = self.config.get("macd_slow", self.MACD_SLOW)
        self.macd_signal = self.config.get("macd_signal", self.MACD_SIGNAL)
        self.data_interval_seconds = int(self.config.get("data_interval_seconds", 10))

        # Momentum confirmation settings
        self.use_momentum_confirmation = config.get("use_momentum_confirmation", True)
        self.volume_spike_threshold = config.get("volume_spike_threshold", 1.5)
        self.require_volume_spike = config.get("require_volume_spike", True)
        self.momentum_soft_gate = config.get("momentum_soft_gate", {"enabled": False})

        logger.info(f"MTF Strategy initialized for {trading_pair}")

    def _momentum_allowed(self, direction: str, rr: float, conf_count: int) -> Tuple[bool, List[str], bool]:
        """Return (allowed, details, confirmed) where confirmed means momentum aligned."""
        momentum_ok, momentum_details = self._check_momentum_confirmation(direction)
        if momentum_ok:
            return True, momentum_details, True
        soft_cfg = self.momentum_soft_gate or {}
        if soft_cfg.get("enabled"):
            min_conf = soft_cfg.get("min_confluence", 3)
            min_rr = soft_cfg.get("min_rr", 1.5)
            if conf_count is not None and rr is not None and conf_count >= min_conf and rr >= min_rr:
                return True, momentum_details, False
        return False, momentum_details, False

    def _rebuild_tf_aggregates_from_cache(self):
        """Rebuild multi-timeframe aggregates from cached ticks."""
        try:
            for tf in self.tf_defs:
                self.tf_candles[tf].clear()
                self.tf_current[tf] = None
            for ts, price, high, low, vol in zip(self.timestamps, self.prices, self.highs, self.lows, self.volumes):
                self._update_tf_aggregates(ts, price, high, low, vol, rebuild=True)
        except Exception:
            pass

    def _update_tf_aggregates(self, ts: datetime, price: float, high: float, low: float, volume: float, rebuild: bool = False):
        """Update rolling OHLCV aggregates for multiple timeframes."""
        if isinstance(ts, str):
            try:
                ts = datetime.fromisoformat(ts)
            except Exception:
                ts = datetime.now()
        epoch = int(ts.timestamp())
        for tf, tf_sec in self.tf_defs.items():
            bucket = (epoch // tf_sec) * tf_sec
            current = self.tf_current.get(tf)
            if current is None or current["bucket"] != bucket:
                if current is not None:
                    self.tf_candles[tf].append(current)
                self.tf_current[tf] = {
                    "bucket": bucket,
                    "open": price,
                    "high": high,
                    "low": low,
                    "close": price,
                    "volume": volume,
                    "ts": datetime.fromtimestamp(bucket)
                }
            else:
                current["high"] = max(current["high"], high)
                current["low"] = min(current["low"], low)
                current["close"] = price
                current["volume"] = (current["volume"] or 0) + (volume or 0)

    # ============ Data Collection ============

    def _fetch_historical_levels(self):
        """Fetch historical data to calculate key levels"""
        try:
            # Get daily candles for yearly/monthly/weekly levels
            # Use public endpoint which returns dict format
            candles = self.api.get_candles_public(self.trading_pair, "ONE_DAY", 365)

            if not candles or len(candles) < 7:
                logger.warning("Not enough historical data for key levels")
                return

            # Parse candles (dict format from public endpoint)
            all_highs = []
            all_lows = []

            for candle in candles:
                # Public endpoint returns dict: {start, low, high, open, close, volume}
                if isinstance(candle, dict):
                    all_highs.append(float(candle['high']))
                    all_lows.append(float(candle['low']))
                elif len(candle) >= 6:
                    # Fallback for list format: [start, low, high, open, close, volume]
                    all_highs.append(float(candle[2]))  # high
                    all_lows.append(float(candle[1]))   # low

            if not all_highs:
                return

            # Calculate levels
            self.yearly_high = max(all_highs)
            self.yearly_low = min(all_lows)

            # Helper to extract high/low from candle (dict or list)
            def get_high(c):
                return float(c['high']) if isinstance(c, dict) else float(c[2])

            def get_low(c):
                return float(c['low']) if isinstance(c, dict) else float(c[1])

            # Monthly (last 30 candles)
            monthly_data = candles[:30] if len(candles) >= 30 else candles
            monthly_highs = [get_high(c) for c in monthly_data]
            monthly_lows = [get_low(c) for c in monthly_data]
            self.monthly_high = max(monthly_highs) if monthly_highs else None
            self.monthly_low = min(monthly_lows) if monthly_lows else None

            # Weekly (last 7 candles)
            weekly_data = candles[:7] if len(candles) >= 7 else candles
            weekly_highs = [get_high(c) for c in weekly_data]
            weekly_lows = [get_low(c) for c in weekly_data]
            self.weekly_high = max(weekly_highs) if weekly_highs else None
            self.weekly_low = min(weekly_lows) if weekly_lows else None

            # Daily (most recent candle)
            if candles:
                self.daily_high = get_high(candles[0])
                self.daily_low = get_low(candles[0])

            # Build key levels list
            self._build_key_levels()

            logger.info(f"Key levels loaded: Y({self.yearly_low:.0f}-{self.yearly_high:.0f}), "
                       f"M({self.monthly_low:.0f}-{self.monthly_high:.0f}), "
                       f"W({self.weekly_low:.0f}-{self.weekly_high:.0f}), "
                       f"D({self.daily_low:.0f}-{self.daily_high:.0f})")

        except Exception as e:
            logger.error(f"Failed to fetch historical levels: {e}")

    def _build_key_levels(self):
        """Build sorted list of key levels"""
        self.key_levels = []

        levels_data = [
            (self.yearly_high, "high", "yearly", 3.0),
            (self.yearly_low, "low", "yearly", 3.0),
            (self.monthly_high, "high", "monthly", 2.0),
            (self.monthly_low, "low", "monthly", 2.0),
            (self.weekly_high, "high", "weekly", 1.5),
            (self.weekly_low, "low", "weekly", 1.5),
            (self.daily_high, "high", "daily", 1.0),
            (self.daily_low, "low", "daily", 1.0),
        ]

        for price, level_type, timeframe, strength in levels_data:
            if price:
                self.key_levels.append(KeyLevel(
                    price=price,
                    level_type=level_type,
                    timeframe=timeframe,
                    strength=strength
                ))

        # Sort by price
        self.key_levels.sort(key=lambda x: x.price)

    def _intraday_points(self, minutes: int) -> int:
        return max(2, int((minutes * 60) / max(self.data_interval_seconds, 1)))

    def _update_intraday_key_levels(self):
        # Remove old intraday levels
        self.key_levels = [l for l in self.key_levels if l.timeframe not in ("30m", "1h", "4h")]

        def add_level(tf: str, points: int):
            if len(self.prices) < points:
                return
            highs = list(self.highs)[-points:]
            lows = list(self.lows)[-points:]
            if highs and lows:
                self.key_levels.append(KeyLevel(price=max(highs), level_type="high", timeframe=tf, strength=0.8))
                self.key_levels.append(KeyLevel(price=min(lows), level_type="low", timeframe=tf, strength=0.8))

        add_level("30m", self._intraday_points(30))
        add_level("1h", self._intraday_points(60))
        add_level("4h", self._intraday_points(240))

        self.key_levels.sort(key=lambda x: x.price)

    # ============ Warmup Cache ============

    def _warmup_cache_path(self) -> Path:
        cache_dir = Path(__file__).parent.parent / "logs" / "warmup_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        safe_pair = self.trading_pair.replace("/", "_").replace("-", "_")
        return cache_dir / f"{safe_pair}.json"

    def _load_warmup_cache(self) -> Optional[dict]:
        path = self._warmup_cache_path()
        if not path.exists():
            return None
        try:
            with open(path, "r") as f:
                data = json.load(f)
            # Coerce timestamps back to datetime if present
            ts = data.get("timestamps", [])
            if ts:
                parsed = []
                for t in ts:
                    try:
                        parsed.append(datetime.fromisoformat(t))
                    except Exception:
                        continue
                data["timestamps"] = parsed
            return data
        except Exception:
            return None

    def _save_warmup_cache(self):
        path = self._warmup_cache_path()
        try:
            data = {
                "prices": list(self.prices)[-self.cache_maxlen:],
                "highs": list(self.highs)[-self.cache_maxlen:],
                "lows": list(self.lows)[-self.cache_maxlen:],
                "volumes": list(self.volumes)[-self.cache_maxlen:],
                "timestamps": [t.isoformat() for t in list(self.timestamps)[-self.cache_maxlen:]],
            }
            with open(path, "w") as f:
                json.dump(data, f)
        except Exception:
            pass

    def _calculate_fib_levels(self, swing_high: float, swing_low: float) -> List[FibLevel]:
        """Calculate Fibonacci retracement levels between swing points"""
        fib_levels = []
        swing_range = swing_high - swing_low

        # Retracement levels (from high going down)
        for ratio, label in self.FIB_RATIOS:
            price = swing_high - (swing_range * ratio)
            fib_levels.append(FibLevel(ratio=ratio, price=price, label=f"Fib {label}"))

        # Extension levels (beyond the swing)
        for ratio, label in self.FIB_EXTENSIONS:
            # Bullish extension (above swing high)
            price_up = swing_high + (swing_range * (ratio - 1))
            fib_levels.append(FibLevel(ratio=ratio, price=price_up, label=f"Ext {label}"))

        return fib_levels

    # ============ Technical Indicators ============

    def _calc_ema(self, period: int, prices: list = None) -> Optional[float]:
        """Calculate EMA"""
        data = prices if prices else list(self.prices)
        if len(data) < period:
            return None

        multiplier = 2 / (period + 1)
        ema = data[0]
        for price in data[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        return ema

    def _calc_rsi(self, period: int = None) -> Optional[float]:
        """Calculate RSI"""
        if period is None:
            period = self.rsi_period
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
        return 100 - (100 / (1 + rs))

    def _get_ema_alignment(self) -> Tuple[str, float]:
        """
        Check EMA alignment across periods
        Returns: (direction, strength)
        - Perfect bullish: 20 > 50 > 100 > 200, all rising
        - Perfect bearish: 20 < 50 < 100 < 200, all falling
        """
        emas = {}
        for period in self.ema_periods:
            ema = self._calc_ema(period)
            if ema:
                emas[period] = ema

        if len(emas) < 4:
            return "neutral", 0

        # Check alignment
        bullish_count = 0
        bearish_count = 0

        sorted_periods = sorted(self.ema_periods)
        for i in range(len(sorted_periods) - 1):
            shorter = emas[sorted_periods[i]]
            longer = emas[sorted_periods[i + 1]]

            if shorter > longer:
                bullish_count += 1
            elif shorter < longer:
                bearish_count += 1

        # Calculate strength (0-1)
        max_comparisons = len(sorted_periods) - 1

        if bullish_count == max_comparisons:
            return "bullish", 1.0
        elif bearish_count == max_comparisons:
            return "bearish", 1.0
        elif bullish_count > bearish_count:
            return "bullish", bullish_count / max_comparisons
        elif bearish_count > bullish_count:
            return "bearish", bearish_count / max_comparisons

        return "neutral", 0

    def _check_volume_confirmation(self) -> bool:
        """Check if current volume is above average"""
        if len(self.volumes) < 20:
            return True  # Not enough data, assume OK

        avg_volume = sum(list(self.volumes)[-20:]) / 20
        current_volume = self.volumes[-1] if self.volumes else 0

        return current_volume > avg_volume * 0.8

    def _check_volume_spike(self) -> Tuple[bool, float]:
        """
        Check if volume is spiking (1.5x+ average)
        Returns: (is_spike, ratio)
        """
        if len(self.volumes) < 20:
            return True, 1.0  # Not enough data, allow trade

        volumes = list(self.volumes)
        current_volume = volumes[-1] if volumes else 0
        avg_volume = sum(volumes[-21:-1]) / 20 if len(volumes) > 20 else sum(volumes[:-1]) / max(1, len(volumes)-1)

        if avg_volume == 0:
            return True, 1.0

        ratio = current_volume / avg_volume
        return ratio >= self.volume_spike_threshold, ratio

    def _calc_macd(self) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """
        Calculate MACD indicator
        Returns: (macd_line, signal_line, histogram)
        """
        if len(self.prices) < self.macd_slow + self.macd_signal:
            return None, None, None

        prices = list(self.prices)

        # Calculate EMAs
        ema_fast = self._calc_ema(self.macd_fast, prices)
        ema_slow = self._calc_ema(self.macd_slow, prices)

        if ema_fast is None or ema_slow is None:
            return None, None, None

        macd_line = ema_fast - ema_slow

        # For signal line, we need historical MACD values
        # Simplified: calculate approximate signal using recent data
        macd_values = []
        for i in range(self.macd_signal + 5):
            if len(prices) > i:
                slice_prices = prices[i:]
                fast = self._calc_ema(self.macd_fast, slice_prices)
                slow = self._calc_ema(self.macd_slow, slice_prices)
                if fast and slow:
                    macd_values.append(fast - slow)

        if len(macd_values) >= self.macd_signal:
            signal_line = sum(macd_values[:self.macd_signal]) / self.macd_signal
            histogram = macd_line - signal_line
        else:
            signal_line = macd_line
            histogram = 0

        return macd_line, signal_line, histogram

    def _calc_vwap(self, period: int = 20) -> Optional[float]:
        """Calculate Volume Weighted Average Price"""
        if len(self.prices) < period or len(self.volumes) < period:
            return None

        prices = list(self.prices)[-period:]
        volumes = list(self.volumes)[-period:]

        total_volume = sum(volumes)
        if total_volume == 0:
            return sum(prices) / len(prices)

        vwap = sum(p * v for p, v in zip(prices, volumes)) / total_volume
        return vwap

    def _check_momentum_confirmation(self, direction: str) -> Tuple[bool, List[str]]:
        """
        Check if momentum confirms trade direction

        For BUY: RSI rising, MACD positive, price above VWAP
        For SELL: RSI falling, MACD negative, price below VWAP

        Returns: (confirmed, list of confirmations)
        """
        if not self.use_momentum_confirmation:
            return True, ["Momentum check disabled"]

        confirmations = []
        required = 2  # Need at least 2 of 3 confirmations
        count = 0

        # 1. RSI Direction
        rsi = self._calc_rsi()
        prev_rsi = self._calc_rsi_at_offset(3)  # RSI 3 periods ago

        if rsi is not None and prev_rsi is not None:
            rsi_rising = rsi > prev_rsi
            if direction == "buy" and rsi_rising:
                count += 1
                confirmations.append(f"RSI rising ({prev_rsi:.0f}->{rsi:.0f})")
            elif direction == "sell" and not rsi_rising:
                count += 1
                confirmations.append(f"RSI falling ({prev_rsi:.0f}->{rsi:.0f})")
            else:
                confirmations.append(f"RSI {'rising' if rsi_rising else 'falling'} (opposite)")

        # 2. MACD Histogram
        macd, signal, histogram = self._calc_macd()
        if histogram is not None:
            if direction == "buy" and histogram > 0:
                count += 1
                confirmations.append(f"MACD positive ({histogram:.4f})")
            elif direction == "sell" and histogram < 0:
                count += 1
                confirmations.append(f"MACD negative ({histogram:.4f})")
            else:
                confirmations.append(f"MACD {'positive' if histogram > 0 else 'negative'} (opposite)")

        # 3. Price vs VWAP
        vwap = self._calc_vwap()
        current_price = self.prices[-1] if self.prices else 0
        if vwap is not None and current_price:
            above_vwap = current_price > vwap
            if direction == "buy" and above_vwap:
                count += 1
                confirmations.append(f"Price above VWAP ({current_price:.0f} > {vwap:.0f})")
            elif direction == "sell" and not above_vwap:
                count += 1
                confirmations.append(f"Price below VWAP ({current_price:.0f} < {vwap:.0f})")
            else:
                confirmations.append(f"Price {'above' if above_vwap else 'below'} VWAP (opposite)")

        return count >= required, confirmations

    def _calc_rsi_at_offset(self, offset: int) -> Optional[float]:
        """Calculate RSI at a previous offset"""
        period = self.rsi_period
        if len(self.prices) < period + offset + 1:
            return None

        prices = list(self.prices)[:-offset] if offset > 0 else list(self.prices)
        if len(prices) < period + 1:
            return None

        prices = prices[-(period + 1):]
        deltas = [prices[i+1] - prices[i] for i in range(len(prices)-1)]

        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]

        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period

        if avg_loss == 0:
            return 100

        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    # ============ Level Analysis ============

    def _find_nearest_level(self, price: float) -> Tuple[Optional[KeyLevel], float]:
        """Find nearest key level and distance percentage"""
        if not self.key_levels:
            return None, 0

        nearest = None
        min_distance = float('inf')

        for level in self.key_levels:
            distance = abs(price - level.price) / price * 100
            if distance < min_distance:
                min_distance = distance
                nearest = level

        return nearest, min_distance

    def _find_fib_confluence(self, price: float) -> Tuple[Optional[FibLevel], float]:
        """Check if price is at a Fibonacci level"""
        if not self.fib_levels:
            # Calculate fib levels using weekly high/low
            if self.weekly_high and self.weekly_low:
                self.fib_levels = self._calculate_fib_levels(self.weekly_high, self.weekly_low)

        if not self.fib_levels:
            return None, 0

        for fib in self.fib_levels:
            distance = abs(price - fib.price) / price * 100
            if distance < self.level_proximity_pct:
                return fib, distance

        return None, 0

    def _get_support_resistance_context(self, price: float) -> dict:
        """Determine if price is near support or resistance"""
        result = {
            "near_support": False,
            "near_resistance": False,
            "support_levels": [],
            "resistance_levels": []
        }

        for level in self.key_levels:
            distance_pct = abs(price - level.price) / price * 100

            if distance_pct < self.level_proximity_pct * 2:  # Within 2x proximity
                if level.price < price:
                    result["support_levels"].append(level)
                    if distance_pct < self.level_proximity_pct:
                        result["near_support"] = True
                else:
                    result["resistance_levels"].append(level)
                    if distance_pct < self.level_proximity_pct:
                        result["near_resistance"] = True

        return result

    def _detect_breakout_signals(self, price: float) -> List[Signal]:
        """Detect breakout setups around prior monthly highs/lows."""
        cfg = self.config.get("breakout_zones", {})
        if not cfg.get("enabled", True):
            return []

        if not self.monthly_high or not self.monthly_low:
            return []

        if len(self.prices) < 3:
            return []

        buffer_pct = cfg.get("buffer_pct", 0.3)
        retest_window = int(cfg.get("retest_window", 6))
        continuation_confirm_pct = cfg.get("continuation_confirm_pct", 0.3)
        false_break_wick_pct = cfg.get("false_break_wick_pct", 0.3)
        fast_breakout_pct = cfg.get("fast_breakout_pct", 0.2)
        fast_strength = cfg.get("fast_strength", 0.5)
        confirm_strength = cfg.get("confirm_strength", 1.0)
        fast_require_volume = cfg.get("fast_require_volume", True)
        confirm_require_volume = cfg.get("confirm_require_volume", True)
        fast_volume_mult = cfg.get("fast_volume_mult", 1.2)
        confirm_volume_mult = cfg.get("confirm_volume_mult", 1.5)
        volume_lookback = int(cfg.get("volume_lookback", 20))
        fast_requires_close = cfg.get("fast_requires_close", False)
        tf_weights = cfg.get("tf_weights", {})

        signals = []
        close = price
        prev_close = self.prices[-2]
        current_high = self.highs[-1] if self.highs else price
        current_low = self.lows[-1] if self.lows else price
        prev_high = self.highs[-2] if len(self.highs) > 1 else current_high
        prev_low = self.lows[-2] if len(self.lows) > 1 else current_low
        current_vol = self.volumes[-1] if self.volumes else None
        avg_vol = None
        if self.volumes and len(self.volumes) >= max(2, volume_lookback):
            vols = list(self.volumes)[-volume_lookback:]
            avg_vol = sum(vols) / max(len(vols), 1)

        def pct_from(level: float, value: float) -> float:
            return abs(value - level) / level * 100

        # === Breakout + retest (monthly high) ===
        mh = self.monthly_high
        recent_closes = list(self.prices)[-max(retest_window, 2):]
        has_breakout = max(recent_closes) > mh * (1 + continuation_confirm_pct / 100)
        near_level = pct_from(mh, close) <= buffer_pct
        if has_breakout and near_level and close >= mh * (1 - buffer_pct / 100):
            signals.append(Signal(
                direction="buy",
                strength=1.0,
                source="breakout_retest",
                details=f"Retest of monthly high ${mh:.0f}"
            ))

        # === FAST breakout (previous candle high) ===
        fast_breakout_level = prev_high * (1 + fast_breakout_pct / 100) if prev_high else None
        fast_breakout_hit = False
        if fast_breakout_level:
            if fast_requires_close:
                fast_breakout_hit = close > fast_breakout_level
            else:
                fast_breakout_hit = current_high > fast_breakout_level
        vol_ok_fast = True
        if fast_require_volume and avg_vol and current_vol is not None:
            vol_ok_fast = current_vol >= avg_vol * fast_volume_mult
        if fast_breakout_hit and vol_ok_fast:
            signals.append(Signal(
                direction="buy",
                strength=fast_strength,
                source="breakout_fast",
                details=f"Fast breakout above prior high ${prev_high:.0f}"
            ))

        # === Breakout continuation (monthly high) ===
        vol_ok_confirm = True
        if confirm_require_volume and avg_vol and current_vol is not None:
            vol_ok_confirm = current_vol >= avg_vol * confirm_volume_mult
        if close > mh * (1 + continuation_confirm_pct / 100) and prev_close > mh and vol_ok_confirm:
            signals.append(Signal(
                direction="buy",
                strength=confirm_strength,
                source="breakout_confirmed",
                details=f"Continuation above monthly high ${mh:.0f}"
            ))

        # === False breakout (monthly high) ===
        if current_high > mh * (1 + false_break_wick_pct / 100) and close < mh * (1 - buffer_pct / 100):
            signals.append(Signal(
                direction="sell",
                strength=0.9,
                source="false_breakout",
                details=f"Failed breakout above monthly high ${mh:.0f}"
            ))

        # === Breakout + retest (monthly low) ===
        ml = self.monthly_low
        has_breakdown = min(recent_closes) < ml * (1 - continuation_confirm_pct / 100)
        near_low = pct_from(ml, close) <= buffer_pct
        if has_breakdown and near_low and close <= ml * (1 + buffer_pct / 100):
            signals.append(Signal(
                direction="sell",
                strength=1.0,
                source="breakout_retest",
                details=f"Retest of monthly low ${ml:.0f}"
            ))

        # === FAST breakdown (previous candle low) ===
        fast_breakdown_level = prev_low * (1 - fast_breakout_pct / 100) if prev_low else None
        fast_breakdown_hit = False
        if fast_breakdown_level:
            if fast_requires_close:
                fast_breakdown_hit = close < fast_breakdown_level
            else:
                fast_breakdown_hit = current_low < fast_breakdown_level
        if fast_breakdown_hit and vol_ok_fast:
            signals.append(Signal(
                direction="sell",
                strength=fast_strength,
                source="breakout_fast",
                details=f"Fast breakdown below prior low ${prev_low:.0f}"
            ))

        # === Breakdown continuation (monthly low) ===
        if close < ml * (1 - continuation_confirm_pct / 100) and prev_close < ml and vol_ok_confirm:
            signals.append(Signal(
                direction="sell",
                strength=confirm_strength,
                source="breakout_confirmed",
                details=f"Continuation below monthly low ${ml:.0f}"
            ))

        # === Multi-timeframe breakouts (weighted) ===
        for tf, weight in tf_weights.items():
            candles = self.tf_candles.get(tf)
            current_tf = self.tf_current.get(tf)
            if not candles or len(candles) < 2 or not current_tf:
                continue
            prev = candles[-1]
            prev2 = candles[-2]
            prev_high = prev.get("high", 0)
            prev_low = prev.get("low", 0)
            prev_close = prev.get("close", 0)
            prev2_high = prev2.get("high", 0)
            prev2_low = prev2.get("low", 0)
            prev2_close = prev2.get("close", 0)
            tf_close = current_tf.get("close", close)
            tf_high = current_tf.get("high", current_high)
            tf_low = current_tf.get("low", current_low)
            tf_vol = current_tf.get("volume", 0)

            tf_avg_vol = None
            if candles and len(candles) >= max(2, volume_lookback):
                vols = [c.get("volume", 0) for c in list(candles)[-volume_lookback:]]
                tf_avg_vol = sum(vols) / max(len(vols), 1)

            tf_vol_ok_fast = True
            tf_vol_ok_confirm = True
            if fast_require_volume and tf_avg_vol is not None:
                tf_vol_ok_fast = tf_vol >= tf_avg_vol * fast_volume_mult
            if confirm_require_volume and tf_avg_vol is not None:
                tf_vol_ok_confirm = tf_vol >= tf_avg_vol * confirm_volume_mult

            fast_breakout_level = prev_high * (1 + fast_breakout_pct / 100) if prev_high else None
            fast_breakdown_level = prev_low * (1 - fast_breakout_pct / 100) if prev_low else None
            fast_breakout_hit = False
            fast_breakdown_hit = False
            if fast_breakout_level:
                fast_breakout_hit = tf_close > fast_breakout_level if fast_requires_close else tf_high > fast_breakout_level
            if fast_breakdown_level:
                fast_breakdown_hit = tf_close < fast_breakdown_level if fast_requires_close else tf_low < fast_breakdown_level

            if fast_breakout_hit and tf_vol_ok_fast:
                signals.append(Signal(
                    direction="buy",
                    strength=fast_strength * float(weight),
                    source=f"breakout_fast_{tf}",
                    details=f"{tf} fast breakout above {prev_high:.0f}"
                ))
            if fast_breakdown_hit and tf_vol_ok_fast:
                signals.append(Signal(
                    direction="sell",
                    strength=fast_strength * float(weight),
                    source=f"breakout_fast_{tf}",
                    details=f"{tf} fast breakdown below {prev_low:.0f}"
                ))

            confirm_level_high = prev2_high * (1 + continuation_confirm_pct / 100) if prev2_high else None
            confirm_level_low = prev2_low * (1 - continuation_confirm_pct / 100) if prev2_low else None
            if confirm_level_high and prev_close > confirm_level_high and prev2_close > confirm_level_high and tf_vol_ok_confirm:
                signals.append(Signal(
                    direction="buy",
                    strength=confirm_strength * float(weight),
                    source=f"breakout_confirmed_{tf}",
                    details=f"{tf} confirmed breakout above {prev2_high:.0f}"
                ))
            if confirm_level_low and prev_close < confirm_level_low and prev2_close < confirm_level_low and tf_vol_ok_confirm:
                signals.append(Signal(
                    direction="sell",
                    strength=confirm_strength * float(weight),
                    source=f"breakout_confirmed_{tf}",
                    details=f"{tf} confirmed breakdown below {prev2_low:.0f}"
                ))

        # === False breakdown (monthly low) ===
        if current_low < ml * (1 - false_break_wick_pct / 100) and close > ml * (1 + buffer_pct / 100):
            signals.append(Signal(
                direction="buy",
                strength=0.9,
                source="false_breakout",
                details=f"Failed breakdown below monthly low ${ml:.0f}"
            ))

        return signals

    def _detect_liquidation_zone_signals(self, price: float) -> List[Signal]:
        """Treat liquidation zones as potential support/resistance with caution."""
        cfg = self.config.get("liquidation_zones", {})
        if not cfg.get("enabled", True):
            return []

        if len(self.prices) < 20:
            return []

        lookback = int(cfg.get("lookback", 50))
        proximity_pct = cfg.get("proximity_pct", 1.0)
        strength = cfg.get("strength", 0.6)
        avg_leverage = cfg.get("avg_leverage", 4)

        prices = list(self.prices)[-lookback:]
        recent_high = max(prices)
        recent_low = min(prices)

        # Approx liquidation zones based on average leverage
        long_liq_zone = recent_high * (1 - 1 / max(avg_leverage, 1))
        short_liq_zone = recent_low * (1 + 1 / max(avg_leverage, 1))

        signals = []
        if abs(price - long_liq_zone) / price * 100 <= proximity_pct:
            signals.append(Signal(
                direction="buy",
                strength=strength,
                source="liquidation_zone_support",
                details=f"Near long liquidation zone ${long_liq_zone:.0f}"
            ))

        if abs(price - short_liq_zone) / price * 100 <= proximity_pct:
            signals.append(Signal(
                direction="sell",
                strength=strength,
                source="liquidation_zone_resistance",
                details=f"Near short liquidation zone ${short_liq_zone:.0f}"
            ))

        return signals

    # ============ Signal Generation ============

    def _generate_signals(self, price: float) -> List[Signal]:
        """Generate signals from all indicators"""
        signals = []

        # 1. Key Level Signal
        nearest_level, level_distance = self._find_nearest_level(price)
        if nearest_level and level_distance < self.level_proximity_pct:
            if nearest_level.level_type == "low":
                signals.append(Signal(
                    direction="buy",
                    strength=nearest_level.strength * (1 - level_distance / self.level_proximity_pct),
                    source="key_level",
                    details=f"Near {nearest_level.timeframe} low ${nearest_level.price:.0f}"
                ))
            elif nearest_level.level_type == "high":
                # Could be resistance (sell) or breakout (buy if breaking above)
                if price > nearest_level.price:
                    signals.append(Signal(
                        direction="buy",
                        strength=nearest_level.strength * 0.5,
                        source="breakout",
                        details=f"Breaking {nearest_level.timeframe} high ${nearest_level.price:.0f}"
                    ))
                else:
                    signals.append(Signal(
                        direction="sell",
                        strength=nearest_level.strength * 0.7,
                        source="resistance",
                        details=f"At {nearest_level.timeframe} resistance ${nearest_level.price:.0f}"
                    ))

        # 1b. Breakout / retest / false-break signals on monthly levels
        signals.extend(self._detect_breakout_signals(price))

        # 1c. Liquidation zone support/resistance (cautious)
        signals.extend(self._detect_liquidation_zone_signals(price))

        # 2. Fibonacci Signal
        fib_level, fib_distance = self._find_fib_confluence(price)
        if fib_level:
            # Golden ratio emphasis
            if fib_level.ratio == 0.618:
                fib_strength = 1.2
            elif fib_level.ratio == 0.5:
                fib_strength = 1.0
            else:
                fib_strength = 0.8
            ema_dir, _ = self._get_ema_alignment()

            # Buy at fib support in uptrend, sell at fib resistance in downtrend
            if fib_level.ratio <= 0.618 and ema_dir == "bullish":
                signals.append(Signal(
                    direction="buy",
                    strength=fib_strength,
                    source="fibonacci",
                    details=f"At {fib_level.label} (${fib_level.price:.0f})"
                ))
            elif fib_level.ratio >= 0.382 and ema_dir == "bearish":
                signals.append(Signal(
                    direction="sell",
                    strength=fib_strength,
                    source="fibonacci",
                    details=f"At {fib_level.label} (${fib_level.price:.0f})"
                ))

        # 3. EMA Alignment Signal
        ema_direction, ema_strength = self._get_ema_alignment()
        if ema_strength >= 0.5:
            signals.append(Signal(
                direction="buy" if ema_direction == "bullish" else "sell",
                strength=ema_strength,
                source="ema_alignment",
                details=f"EMA stack {ema_direction} ({ema_strength:.0%})"
            ))

        # 4. RSI Signal
        rsi = self._calc_rsi()
        if rsi:
            rsi_oversold = self.config.get("rsi_oversold", 30)
            rsi_overbought = self.config.get("rsi_overbought", 70)

            if rsi <= rsi_oversold:
                strength = (rsi_oversold - rsi) / rsi_oversold
                signals.append(Signal(
                    direction="buy",
                    strength=min(strength + 0.3, 1.0),
                    source="rsi",
                    details=f"RSI oversold ({rsi:.0f})"
                ))
            elif rsi >= rsi_overbought:
                strength = (rsi - rsi_overbought) / (100 - rsi_overbought)
                signals.append(Signal(
                    direction="sell",
                    strength=min(strength + 0.3, 1.0),
                    source="rsi",
                    details=f"RSI overbought ({rsi:.0f})"
                ))
            elif 40 <= rsi <= 60:
                # Neutral zone - slight confirmation of existing trend
                ema_dir, _ = self._get_ema_alignment()
                if ema_dir != "neutral":
                    signals.append(Signal(
                        direction="buy" if ema_dir == "bullish" else "sell",
                        strength=0.3,
                        source="rsi",
                        details=f"RSI neutral zone ({rsi:.0f})"
                    ))

        # 5. Volume Confirmation
        if self._check_volume_confirmation():
            # Volume confirms existing signals
            if signals:
                strongest = max(signals, key=lambda s: s.strength)
                signals.append(Signal(
                    direction=strongest.direction,
                    strength=0.3,
                    source="volume",
                    details="Volume above average"
                ))

        return signals

    def _get_intel_candles(self, tf: str = "1h", max_len: int = 200) -> List[dict]:
        candles = list(self.tf_candles.get(tf, []))
        current = self.tf_current.get(tf)
        if current:
            candles = candles + [current]
        if max_len and len(candles) > max_len:
            candles = candles[-max_len:]
        return candles

    def _get_tf_df(self, tf: str, max_len: int = 200) -> pd.DataFrame:
        candles = self._get_intel_candles(tf, max_len=max_len)
        if not candles:
            return pd.DataFrame()
        return pd.DataFrame(candles)

    def _get_intel_votes(self, price: float) -> dict:
        cfg = self.config.get("liq_intel", {})
        if not cfg.get("enabled", True):
            return {}

        tf = cfg.get("timeframe", "1h")
        candles = self._get_intel_candles(tf, max_len=int(cfg.get("max_candles", 200)))
        if not candles:
            return {}

        liq = get_liq_event_intel(self.trading_pair, tf, candles)
        magnet = get_magnet_intel(self.trading_pair, tf, candles)

        liq_threshold = float(cfg.get("liq_event_threshold", 0.7))
        liq_score = liq.get("liq_event_score")
        liq_event_vote = bool(liq_score is not None and liq_score >= liq_threshold)

        magnet_min = float(cfg.get("magnet_min_distance_pct", 0.35))
        nearest_dist = magnet.get("nearest_magnet_distance_pct")
        magnet_vote = None
        magnet_note = None
        if nearest_dist is not None:
            magnet_vote = nearest_dist >= magnet_min
            if not magnet_vote:
                magnet_note = f"magnet {nearest_dist:.2f}% < {magnet_min:.2f}%"

        return {
            "liq_event_vote": liq_event_vote,
            "liq_event_score": liq_score,
            "liq_bias": liq.get("liq_bias"),
            "magnet_vote": magnet_vote,
            "magnet_distance_pct": nearest_dist,
            "magnet_note": magnet_note,
            "magnet_levels": magnet.get("magnet_levels", []),
        }

    def _combine_signals(self, signals: List[Signal], price: float, intel: dict = None) -> dict:
        """Combine signals into trading decision using confluence"""
        if not signals:
            return {"action": "hold", "reason": "No signals"}

        buy_signals = [s for s in signals if s.direction == "buy"]
        sell_signals = [s for s in signals if s.direction == "sell"]

        buy_score = sum(s.strength for s in buy_signals)
        sell_score = sum(s.strength for s in sell_signals)

        buy_count = len(buy_signals)
        sell_count = len(sell_signals)

        # Format signal details
        buy_details = [f"{s.source}:{s.strength:.1f}" for s in buy_signals]
        sell_details = [f"{s.source}:{s.strength:.1f}" for s in sell_signals]

        setup_tags = set()
        for s in signals:
            if s.source in ("breakout_retest", "breakout_continuation", "false_breakout",
                            "liquidation_zone_support", "liquidation_zone_resistance"):
                setup_tags.add(s.source)

        # Breakout classifier (dominant timeframe)
        df_4h = self._get_tf_df("4h")
        df_1h = self._get_tf_df("1h")
        df_30m = self._get_tf_df("30m")
        breakout_tf_label = breakout_tf(df_4h, df_1h, df_30m)
        tf_df = df_30m if breakout_tf_label == "30m" else df_1h if breakout_tf_label == "1h" else df_4h
        breakout_type_buy = classify_breakout(tf_df, "buy")
        breakout_type_sell = classify_breakout(tf_df, "sell")

        # Need minimum confluence (3+ by default; optional 2/3 scalp mode)
        min_signals = self.min_confluence
        min_score = 1.5  # Combined strength threshold for high-conviction entries
        early_enabled = False
        aggressive_enabled = False
        reset_ready_buy = self._reset_confirmed("buy")
        reset_ready_sell = self._reset_confirmed("sell")
        vol_ok, vol_ratio = self._check_volume_spike()
        rr_buy = self._risk_reward_ratio(price, "buy")
        rr_sell = self._risk_reward_ratio(price, "sell")
        allow_buy_relaxed = self.scalp_relaxed and buy_count == 2 and rr_buy >= self.scalp_min_rr and vol_ratio >= self.scalp_min_volume_ratio
        allow_sell_relaxed = self.scalp_relaxed and sell_count == 2 and rr_sell >= self.scalp_min_rr and vol_ratio >= self.scalp_min_volume_ratio

        intel = intel or {}
        liq_vote = bool(intel.get("liq_event_vote"))
        magnet_vote = intel.get("magnet_vote")
        magnet_note = intel.get("magnet_note")
        intel_note = ""
        if liq_vote:
            intel_note = " | Intel: liq_event_vote"
        if magnet_vote is False and magnet_note:
            intel_note = f"{intel_note} | Intel: {magnet_note}"

        buy_min_signals = 2 if allow_buy_relaxed else min_signals
        buy_min_score = self.scalp_min_score if allow_buy_relaxed else min_score
        if buy_count >= buy_min_signals and buy_score >= buy_min_score and buy_score > sell_score:
            if magnet_vote is False:
                return {
                    "action": "hold",
                    "reason": f"BUY confluence met but magnet too close ({magnet_note})"
                }
            # Check momentum confirmation
            rr = self._risk_reward_ratio(price, "buy")
            momentum_allowed, momentum_details, momentum_confirmed = self._momentum_allowed("buy", rr, buy_count)
            if not momentum_allowed:
                return {
                    "action": "hold",
                    "reason": f"BUY confluence met but momentum not aligned: {', '.join(momentum_details)}"
                }

            # Check volume spike
            if self.require_volume_spike and not allow_buy_relaxed:
                volume_ok, volume_ratio = self._check_volume_spike()
                if not volume_ok:
                    return {
                        "action": "hold",
                        "reason": f"BUY confluence met but volume too low ({volume_ratio:.1f}x, need {self.volume_spike_threshold}x)"
                    }

            # Calculate stop loss and take profit
            stop_loss = self._calculate_stop_loss(price, "buy")
            take_profit = self._calculate_take_profit(price, "buy", stop_loss)
            dom_level = self._dominant_level(price, "support", self.config.get("breakout_tp", {}).get("dominance_order", ["monthly", "weekly", "daily"]))

            return {
                "action": "buy",
                "side": "buy",
                "pair": self.trading_pair,
                "amount": self.config.get("lot_size_usd", 100),
                "price": None,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "reason": f"MTF BUY ({buy_count} signals, score {buy_score:.1f}): {', '.join(buy_details)} | Momentum: {', '.join(momentum_details)}{' (soft)' if not momentum_confirmed else ''}{intel_note}",
                "strategy": "mtf_confluence",
                "confluence_count": buy_count,
                "confluence_score": buy_score,
                "momentum_confirmed": momentum_confirmed,
                "setups": sorted(setup_tags),
                "dominant_timeframe": dom_level.timeframe if dom_level else None,
                "reset_ready_buy": reset_ready_buy,
                "liq_event_vote": liq_vote,
                "magnet_vote": magnet_vote,
                "breakout_tf": breakout_tf_label,
                "breakout_type": breakout_type_buy
            }

        sell_min_signals = 2 if allow_sell_relaxed else min_signals
        sell_min_score = self.scalp_min_score if allow_sell_relaxed else min_score
        if sell_count >= sell_min_signals and sell_score >= sell_min_score and sell_score > buy_score:
            if magnet_vote is False:
                return {
                    "action": "hold",
                    "reason": f"SELL confluence met but magnet too close ({magnet_note})"
                }
            # Check momentum confirmation
            rr = self._risk_reward_ratio(price, "sell")
            momentum_allowed, momentum_details, momentum_confirmed = self._momentum_allowed("sell", rr, sell_count)
            if not momentum_allowed:
                return {
                    "action": "hold",
                    "reason": f"SELL confluence met but momentum not aligned: {', '.join(momentum_details)}"
                }

            # Check volume spike
            if self.require_volume_spike and not allow_sell_relaxed:
                volume_ok, volume_ratio = self._check_volume_spike()
                if not volume_ok:
                    return {
                        "action": "hold",
                        "reason": f"SELL confluence met but volume too low ({volume_ratio:.1f}x, need {self.volume_spike_threshold}x)"
                    }

            stop_loss = self._calculate_stop_loss(price, "sell")
            take_profit = self._calculate_take_profit(price, "sell", stop_loss)
            dom_level = self._dominant_level(price, "resistance", self.config.get("breakout_tp", {}).get("dominance_order", ["monthly", "weekly", "daily"]))

            return {
                "action": "sell",
                "side": "sell",
                "pair": self.trading_pair,
                "amount": self.config.get("lot_size_usd", 100),
                "price": None,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "reason": f"MTF SELL ({sell_count} signals, score {sell_score:.1f}): {', '.join(sell_details)} | Momentum: {', '.join(momentum_details)}{' (soft)' if not momentum_confirmed else ''}{intel_note}",
                "strategy": "mtf_confluence",
                "confluence_count": sell_count,
                "confluence_score": sell_score,
                "momentum_confirmed": momentum_confirmed,
                "setups": sorted(setup_tags),
                "dominant_timeframe": dom_level.timeframe if dom_level else None,
                "reset_ready_sell": reset_ready_sell,
                "liq_event_vote": liq_vote,
                "magnet_vote": magnet_vote,
                "breakout_tf": breakout_tf_label,
                "breakout_type": breakout_type_sell
            }

        reason_parts = []
        if buy_signals:
            reason_parts.append(f"Buy: {', '.join(buy_details)}")
        if sell_signals:
            reason_parts.append(f"Sell: {', '.join(sell_details)}")

        dominant_breakout = breakout_type_buy if buy_count >= sell_count else breakout_type_sell
        return {
            "action": "hold",
            "reason": f"Insufficient confluence ({max(buy_count, sell_count)}/{min_signals}). {' | '.join(reason_parts)}",
            "breakout_tf": breakout_tf_label,
            "breakout_type": dominant_breakout
        }

    def _reset_confirmed(self, side: str) -> bool:
        cfg = self.config.get("breakout_tp", {})
        buffer_pct = float(cfg.get("buffer_pct", 0.3))
        confirm_closes = int(cfg.get("confirm_closes", 2))
        volume_mult = float(cfg.get("volume_mult", 1.5))
        dominance = cfg.get("dominance_order", ["monthly", "weekly", "daily"])

        if side == "buy":
            level = self._dominant_level(self.prices[-1] if self.prices else 0, "support", dominance)
            if not level:
                return False
            recent_closes = list(self.prices)[-max(confirm_closes, 2):]
            if len(recent_closes) < confirm_closes:
                return False
            near = abs(self.prices[-1] - level.price) / self.prices[-1] * 100 <= buffer_pct
            confirmed = all(c > level.price * (1 + buffer_pct / 100) for c in recent_closes[-confirm_closes:])
        else:
            level = self._dominant_level(self.prices[-1] if self.prices else 0, "resistance", dominance)
            if not level:
                return False
            recent_closes = list(self.prices)[-max(confirm_closes, 2):]
            if len(recent_closes) < confirm_closes:
                return False
            near = abs(self.prices[-1] - level.price) / self.prices[-1] * 100 <= buffer_pct
            confirmed = all(c < level.price * (1 - buffer_pct / 100) for c in recent_closes[-confirm_closes:])

        vol_ok, vol_ratio = self._check_volume_spike()
        if vol_ratio is not None and vol_ratio < volume_mult:
            vol_ok = False
        return bool(near and confirmed and vol_ok)

    # ============ Risk Management ============

    def _calculate_stop_loss(self, price: float, side: str) -> float:
        """Calculate stop loss based on key levels and ATR-like volatility"""
        stop_pct = self.config.get("stop_loss_percent", 1.5)

        if side == "buy":
            # Find nearest support below price
            supports = [l for l in self.key_levels if l.price < price]
            if supports:
                nearest_support = max(supports, key=lambda l: l.price)
                # Stop just below support
                level_stop = nearest_support.price * 0.995
                percentage_stop = price * (1 - stop_pct / 100)
                # Use the tighter stop
                return max(level_stop, percentage_stop)
            return price * (1 - stop_pct / 100)

        else:  # sell
            # Find nearest resistance above price
            resistances = [l for l in self.key_levels if l.price > price]
            if resistances:
                nearest_resistance = min(resistances, key=lambda l: l.price)
                level_stop = nearest_resistance.price * 1.005
                percentage_stop = price * (1 + stop_pct / 100)
                return min(level_stop, percentage_stop)
            return price * (1 + stop_pct / 100)

    def _calculate_take_profit(self, price: float, side: str, stop_loss: float) -> float:
        """Calculate take profit using Fibonacci extensions and risk:reward"""
        risk = abs(price - stop_loss)
        min_rr = self.config.get("min_risk_reward", 2.0)

        if side == "buy":
            # Find next resistance or fib extension
            min_target = price + (risk * min_rr)

            # Check for fib extension targets
            for ext_ratio, _ in self.FIB_EXTENSIONS:
                if self.weekly_high and self.weekly_low:
                    swing_range = self.weekly_high - self.weekly_low
                    ext_target = self.weekly_high + (swing_range * (ext_ratio - 1))
                    if ext_target > min_target:
                        min_target = ext_target

            adj = self._breakout_tp_adjust(price, side)
            if adj:
                if adj["mode"] == "extend":
                    return max(min_target, adj["target"])
                if adj["mode"] == "early":
                    return min(min_target, adj["target"])
            return min_target

        else:  # sell
            min_target = price - (risk * min_rr)

            for ext_ratio, _ in self.FIB_EXTENSIONS:
                if self.weekly_high and self.weekly_low:
                    swing_range = self.weekly_high - self.weekly_low
                    ext_target = self.weekly_low - (swing_range * (ext_ratio - 1))
                    if ext_target < min_target:
                        min_target = ext_target

            adj = self._breakout_tp_adjust(price, side)
            if adj:
                if adj["mode"] == "extend":
                    return min(min_target, adj["target"])
                if adj["mode"] == "early":
                    return max(min_target, adj["target"])
            return min_target

    def _risk_reward_ratio(self, price: float, side: str) -> float:
        """Estimate risk:reward ratio based on current stop and target."""
        try:
            stop_loss = self._calculate_stop_loss(price, side)
            take_profit = self._calculate_take_profit(price, side, stop_loss)
            if side == "buy":
                risk = max(price - stop_loss, 0)
                reward = max(take_profit - price, 0)
            else:
                risk = max(stop_loss - price, 0)
                reward = max(price - take_profit, 0)
            return (reward / risk) if risk > 0 else 0.0
        except Exception:
            return 0.0

    def _breakout_tp_adjust(self, price: float, side: str) -> Optional[dict]:
        cfg = self.config.get("breakout_tp", {})
        if not cfg.get("enabled", False):
            return None

        buffer_pct = float(cfg.get("buffer_pct", 0.3))
        confirm_closes = int(cfg.get("confirm_closes", 2))
        volume_mult = float(cfg.get("volume_mult", 1.5))
        dominance = cfg.get("dominance_order", ["monthly", "weekly", "daily"])

        def near_level(level_price: float) -> bool:
            return abs(price - level_price) / price * 100 <= buffer_pct

        recent_closes = list(self.prices)[-max(confirm_closes, 2):]
        recent_highs = list(self.highs)[-max(confirm_closes, 2):]
        recent_lows = list(self.lows)[-max(confirm_closes, 2):]

        vol_ok, vol_ratio = self._check_volume_spike()
        if vol_ratio is not None and vol_ratio < volume_mult:
            vol_ok = False

        if side == "buy":
            level = self._dominant_level(price, "resistance", dominance)
            if not level:
                return None
            confirmed = len(recent_closes) >= confirm_closes and all(
                c > level.price * (1 + buffer_pct / 100) for c in recent_closes[-confirm_closes:]
            )
            if confirmed and vol_ok:
                next_level = self._next_level_above(level.price, "resistance", dominance)
                if next_level:
                    return {"mode": "extend", "target": next_level.price}
            failed = near_level(level.price) and max(recent_highs) > level.price * (1 + buffer_pct / 100) and recent_closes[-1] < level.price
            if failed:
                return {"mode": "early", "target": level.price * (1 - buffer_pct / 100)}
        else:
            level = self._dominant_level(price, "support", dominance)
            if not level:
                return None
            confirmed = len(recent_closes) >= confirm_closes and all(
                c < level.price * (1 - buffer_pct / 100) for c in recent_closes[-confirm_closes:]
            )
            if confirmed and vol_ok:
                next_level = self._next_level_below(level.price, "support", dominance)
                if next_level:
                    return {"mode": "extend", "target": next_level.price}
            failed = near_level(level.price) and min(recent_lows) < level.price * (1 - buffer_pct / 100) and recent_closes[-1] > level.price
            if failed:
                return {"mode": "early", "target": level.price * (1 + buffer_pct / 100)}

        return None

    def _dominant_level(self, price: float, level_kind: str, dominance: list) -> Optional[KeyLevel]:
        candidates = []
        for level in self.key_levels:
            if level_kind == "resistance" and level.level_type != "high":
                continue
            if level_kind == "support" and level.level_type != "low":
                continue
            if (level_kind == "resistance" and level.price > price) or (level_kind == "support" and level.price < price):
                candidates.append(level)
        if not candidates:
            return None

        # Sort by timeframe dominance then distance to price
        def dom_rank(l: KeyLevel) -> int:
            try:
                return dominance.index(l.timeframe)
            except Exception:
                return len(dominance)

        candidates.sort(key=lambda l: (dom_rank(l), abs(l.price - price)))
        return candidates[0]

    def _next_level_above(self, price: float, level_kind: str, dominance: list) -> Optional[KeyLevel]:
        candidates = []
        for level in self.key_levels:
            if level_kind == "resistance" and level.level_type != "high":
                continue
            if level.price > price:
                candidates.append(level)
        if not candidates:
            return None
        def dom_rank(l: KeyLevel) -> int:
            try:
                return dominance.index(l.timeframe)
            except Exception:
                return len(dominance)
        candidates.sort(key=lambda l: (dom_rank(l), l.price))
        return candidates[0]

    def _next_level_below(self, price: float, level_kind: str, dominance: list) -> Optional[KeyLevel]:
        candidates = []
        for level in self.key_levels:
            if level_kind == "support" and level.level_type != "low":
                continue
            if level.price < price:
                candidates.append(level)
        if not candidates:
            return None
        def dom_rank(l: KeyLevel) -> int:
            try:
                return dominance.index(l.timeframe)
            except Exception:
                return len(dominance)
        candidates.sort(key=lambda l: (dom_rank(l), -l.price))
        return candidates[0]

    def _update_trailing_stop(self, price: float) -> Optional[float]:
        """Update trailing stop for open position"""
        if not self.position:
            return None

        trail_pct = self.config.get("trailing_stop_percent", 1.0)
        break_even_pct = self.config.get("break_even_at_percent", 1.0)

        if self.position.side == "buy":
            self.position.highest_price = max(self.position.highest_price, price)
            profit_pct = (price - self.position.entry_price) / self.position.entry_price * 100

            if profit_pct >= break_even_pct:
                new_stop = max(
                    self.position.stop_loss,
                    self.position.entry_price,
                    self.position.highest_price * (1 - trail_pct / 100)
                )
                if new_stop > self.position.stop_loss:
                    self.position.stop_loss = new_stop
                    logger.info(f"Trailing stop updated to ${new_stop:.2f}")
                return new_stop

        else:  # sell
            self.position.lowest_price = min(self.position.lowest_price, price)
            profit_pct = (self.position.entry_price - price) / self.position.entry_price * 100

            if profit_pct >= break_even_pct:
                new_stop = min(
                    self.position.stop_loss,
                    self.position.entry_price,
                    self.position.lowest_price * (1 + trail_pct / 100)
                )
                if new_stop < self.position.stop_loss:
                    self.position.stop_loss = new_stop
                    logger.info(f"Trailing stop updated to ${new_stop:.2f}")
                return new_stop

        return self.position.stop_loss

    # ============ Main Methods ============

    def analyze(self, market_data: dict) -> Optional[dict]:
        """Main analysis method"""
        price = market_data["price"]
        high = market_data.get("high", price)
        low = market_data.get("low", price)
        volume = market_data.get("volume", 0)

        # Store data
        self.prices.append(price)
        self.highs.append(high)
        self.lows.append(low)
        self.volumes.append(volume)
        self.timestamps.append(datetime.now())
        self._update_tf_aggregates(self.timestamps[-1], price, high, low, volume)
        if len(self.prices) % 10 == 0:
            self._save_warmup_cache()

        # Load historical levels on first run
        if not self.key_levels:
            self._fetch_historical_levels()
        else:
            # Keep intraday levels fresh
            self._update_intraday_key_levels()

        # Need minimum data
        min_data = int(self.config.get("warmup_override", max(self.ema_periods) + 20))
        self.cache_ready = len(self.prices) >= min_data
        if self.cache_loaded and self.cache_ready and not getattr(self, "_cache_ready_logged", False):
            logger.info(f"[{self.trading_pair}] Cache warmup restored: {len(self.prices)}/{min_data} ready")
            self._cache_ready_logged = True
        if len(self.prices) < min_data:
            return {
                "action": "hold",
                "reason": f"Collecting data ({len(self.prices)}/{min_data})"
            }

        # Manage existing position
        if self.position:
            return self._manage_position(price)

        # Generate and combine signals
        signals = self._generate_signals(price)
        intel_votes = self._get_intel_votes(price)
        return self._combine_signals(signals, price, intel_votes)

    def _manage_position(self, price: float) -> dict:
        """Manage open position"""
        self._update_trailing_stop(price)

        if self.position.side == "buy":
            # Check stop loss
            if price <= self.position.stop_loss:
                pnl_pct = (price - self.position.entry_price) / self.position.entry_price * 100
                self.position = None
                return {
                    "action": "sell",
                    "side": "sell",
                    "pair": self.trading_pair,
                    "amount": self.config.get("lot_size_usd", 100),
                    "reason": f"Stop loss hit ({pnl_pct:.1f}%)",
                    "strategy": "mtf_confluence"
                }

            # Check take profit
            if price >= self.position.take_profit:
                pnl_pct = (price - self.position.entry_price) / self.position.entry_price * 100
                self.position = None
                return {
                    "action": "sell",
                    "side": "sell",
                    "pair": self.trading_pair,
                    "amount": self.config.get("lot_size_usd", 100),
                    "reason": f"Take profit hit ({pnl_pct:.1f}%)",
                    "strategy": "mtf_confluence"
                }

        else:  # sell position
            if price >= self.position.stop_loss:
                pnl_pct = (self.position.entry_price - price) / self.position.entry_price * 100
                self.position = None
                return {
                    "action": "buy",
                    "side": "buy",
                    "pair": self.trading_pair,
                    "amount": self.config.get("lot_size_usd", 100),
                    "reason": f"Stop loss hit ({pnl_pct:.1f}%)",
                    "strategy": "mtf_confluence"
                }

            if price <= self.position.take_profit:
                pnl_pct = (self.position.entry_price - price) / self.position.entry_price * 100
                self.position = None
                return {
                    "action": "buy",
                    "side": "buy",
                    "pair": self.trading_pair,
                    "amount": self.config.get("lot_size_usd", 100),
                    "reason": f"Take profit hit ({pnl_pct:.1f}%)",
                    "strategy": "mtf_confluence"
                }

        return {"action": "hold", "reason": "Managing position"}

    def get_status(self) -> dict:
        """Get current strategy status"""
        ema_dir, ema_str = self._get_ema_alignment()
        rsi = self._calc_rsi()
        nearest, distance = self._find_nearest_level(self.prices[-1] if self.prices else 0)

        # MACD
        macd, signal, histogram = self._calc_macd()
        macd_str = f"{histogram:+.4f}" if histogram is not None else "N/A"

        # VWAP
        vwap = self._calc_vwap()
        current_price = self.prices[-1] if self.prices else 0
        vwap_str = f"${vwap:,.0f}" if vwap else "N/A"
        vwap_pos = ""
        if vwap and current_price:
            vwap_pos = " (above)" if current_price > vwap else " (below)"

        # Volume
        volume_ok, volume_ratio = self._check_volume_spike()
        volume_str = f"{volume_ratio:.1f}x {'(spike)' if volume_ok else ''}"

        return {
            "pair": self.trading_pair,
            "data_points": len(self.prices),
            "key_levels_loaded": len(self.key_levels),
            "yearly_range": f"${self.yearly_low:,.0f} - ${self.yearly_high:,.0f}" if self.yearly_high else "N/A",
            "monthly_range": f"${self.monthly_low:,.0f} - ${self.monthly_high:,.0f}" if self.monthly_high else "N/A",
            "weekly_range": f"${self.weekly_low:,.0f} - ${self.weekly_high:,.0f}" if self.weekly_high else "N/A",
            "ema_alignment": f"{ema_dir} ({ema_str:.0%})",
            "rsi": f"{rsi:.0f}" if rsi else "N/A",
            "macd_histogram": macd_str,
            "vwap": f"{vwap_str}{vwap_pos}",
            "volume_ratio": volume_str,
            "nearest_level": f"{nearest.timeframe} {nearest.level_type} ${nearest.price:.0f} ({distance:.1f}%)" if nearest else "N/A",
            "in_position": self.position is not None,
            "position_side": self.position.side if self.position else None,
            "momentum_confirmation": self.use_momentum_confirmation,
            "volume_spike_required": self.require_volume_spike
        }

    def get_key_levels(self) -> List[dict]:
        """Get all key levels for display"""
        return [
            {
                "price": level.price,
                "type": level.level_type,
                "timeframe": level.timeframe,
                "strength": level.strength
            }
            for level in self.key_levels
        ]
