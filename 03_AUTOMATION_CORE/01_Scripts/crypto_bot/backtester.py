#!/usr/bin/env python3
"""
Backtester & Simulator
Test strategies on historical data before risking real money
"""

import json
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from collections import deque
import random

try:
    import requests
except ImportError:
    print("pip install requests")
    raise

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


@dataclass
class Trade:
    entry_time: datetime
    exit_time: datetime = None
    entry_price: float = 0
    exit_price: float = 0
    side: str = "buy"
    size_usd: float = 0
    leverage: float = 1
    stop_loss: float = 0
    take_profit: float = 0
    pnl: float = 0
    pnl_percent: float = 0
    exit_reason: str = ""
    strategy: str = ""


@dataclass
class BacktestResult:
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0
    total_pnl: float = 0
    max_drawdown: float = 0
    avg_win: float = 0
    avg_loss: float = 0
    profit_factor: float = 0
    sharpe_ratio: float = 0
    avg_trade_duration: float = 0
    best_trade: float = 0
    worst_trade: float = 0
    daily_avg_pnl: float = 0
    trades: List[Trade] = field(default_factory=list)


class DataFetcher:
    """Fetch historical price data"""

    @staticmethod
    def get_historical_prices(pair: str, days: int = 30, interval: str = "5min") -> List[dict]:
        """
        Fetch historical candles from Coinbase
        interval: 1min, 5min, 15min, 1hour, 1day
        """
        logger.info(f"Fetching {days} days of {pair} data...")

        # Map interval to seconds
        granularity_map = {
            "1min": 60,
            "5min": 300,
            "15min": 900,
            "1hour": 3600,
            "1day": 86400
        }
        granularity = granularity_map.get(interval, 300)

        candles = []
        end_time = datetime.now()

        # Coinbase limits to 300 candles per request
        candles_per_request = 300
        total_candles_needed = days * 24 * 3600 // granularity

        while len(candles) < total_candles_needed:
            try:
                url = f"https://api.exchange.coinbase.com/products/{pair}/candles"
                params = {
                    "granularity": granularity,
                    "end": end_time.isoformat(),
                    "start": (end_time - timedelta(seconds=granularity * candles_per_request)).isoformat()
                }

                response = requests.get(url, params=params, timeout=10)

                if response.status_code == 200:
                    data = response.json()
                    if not data:
                        break

                    for candle in data:
                        candles.append({
                            "time": datetime.fromtimestamp(candle[0]),
                            "low": candle[1],
                            "high": candle[2],
                            "open": candle[3],
                            "close": candle[4],
                            "volume": candle[5]
                        })

                    # Move window back
                    end_time = datetime.fromtimestamp(data[-1][0]) - timedelta(seconds=granularity)
                else:
                    logger.warning(f"API error: {response.status_code}")
                    break

            except Exception as e:
                logger.error(f"Error fetching data: {e}")
                break

        # Sort by time ascending
        candles.sort(key=lambda x: x["time"])
        logger.info(f"Fetched {len(candles)} candles")

        return candles


class Backtester:
    """
    Run strategies on historical data
    """

    def __init__(self, config: dict):
        self.config = config
        self.initial_balance = config.get("initial_balance_usd", 1000)
        self.leverage = config.get("leverage", 3)
        self.commission = config.get("commission_percent", 0.1) / 100
        self.slippage = config.get("slippage_percent", 0.05) / 100

        self.balance = self.initial_balance
        self.equity_curve = []
        self.trades: List[Trade] = []
        self.open_trade: Optional[Trade] = None

        # For indicators
        self.prices = deque(maxlen=200)
        self.highs = deque(maxlen=200)
        self.lows = deque(maxlen=200)
        self.volumes = deque(maxlen=200)

    def _calc_ema(self, period: int) -> Optional[float]:
        if len(self.prices) < period:
            return None
        prices = list(self.prices)[-period:]
        multiplier = 2 / (period + 1)
        ema = prices[0]
        for price in prices[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        return ema

    def _calc_rsi(self, period: int = 14) -> Optional[float]:
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

    def _check_entry(self, candle: dict, strategy_config: dict) -> Optional[dict]:
        """Check for entry signal based on strategy"""
        price = candle["close"]

        # Scalp Momentum Strategy
        rsi = self._calc_rsi()
        ema_fast = self._calc_ema(strategy_config.get("ema_fast", 8))
        ema_slow = self._calc_ema(strategy_config.get("ema_slow", 21))

        if not all([rsi, ema_fast, ema_slow]):
            return None

        rsi_low = strategy_config.get("rsi_entry_low", 35)
        rsi_high = strategy_config.get("rsi_entry_high", 65)
        stop_pct = strategy_config.get("stop_loss_percent", 0.5)
        tp_pct = strategy_config.get("take_profit_percent", 1.2)

        # Buy signal: RSI recovering from oversold + EMA bullish
        if rsi < rsi_low and ema_fast > ema_slow:
            return {
                "side": "buy",
                "stop_loss": price * (1 - stop_pct / 100),
                "take_profit": price * (1 + tp_pct / 100)
            }

        # Sell signal: RSI overbought + EMA bearish
        if rsi > rsi_high and ema_fast < ema_slow:
            return {
                "side": "sell",
                "stop_loss": price * (1 + stop_pct / 100),
                "take_profit": price * (1 - tp_pct / 100)
            }

        return None

    def _check_exit(self, candle: dict) -> Optional[str]:
        """Check if open trade should exit"""
        if not self.open_trade:
            return None

        price = candle["close"]
        high = candle["high"]
        low = candle["low"]

        if self.open_trade.side == "buy":
            # Stop loss hit
            if low <= self.open_trade.stop_loss:
                return "stop_loss"
            # Take profit hit
            if high >= self.open_trade.take_profit:
                return "take_profit"
        else:  # sell/short
            if high >= self.open_trade.stop_loss:
                return "stop_loss"
            if low <= self.open_trade.take_profit:
                return "take_profit"

        return None

    def _execute_entry(self, candle: dict, signal: dict, strategy: str):
        """Execute trade entry"""
        price = candle["close"]
        # Apply slippage
        if signal["side"] == "buy":
            entry_price = price * (1 + self.slippage)
        else:
            entry_price = price * (1 - self.slippage)

        position_size = self.balance * self.leverage

        self.open_trade = Trade(
            entry_time=candle["time"],
            entry_price=entry_price,
            side=signal["side"],
            size_usd=position_size,
            leverage=self.leverage,
            stop_loss=signal["stop_loss"],
            take_profit=signal["take_profit"],
            strategy=strategy
        )

    def _execute_exit(self, candle: dict, reason: str):
        """Execute trade exit"""
        if not self.open_trade:
            return

        # Determine exit price
        if reason == "stop_loss":
            exit_price = self.open_trade.stop_loss
        elif reason == "take_profit":
            exit_price = self.open_trade.take_profit
        else:
            exit_price = candle["close"]

        # Apply slippage
        if self.open_trade.side == "buy":
            exit_price = exit_price * (1 - self.slippage)
        else:
            exit_price = exit_price * (1 + self.slippage)

        # Calculate P&L
        if self.open_trade.side == "buy":
            pnl_percent = (exit_price - self.open_trade.entry_price) / self.open_trade.entry_price
        else:
            pnl_percent = (self.open_trade.entry_price - exit_price) / self.open_trade.entry_price

        # Apply leverage
        pnl_percent *= self.leverage

        # Subtract commission (both ways)
        pnl_percent -= (self.commission * 2)

        # Calculate dollar P&L
        pnl_usd = self.balance * pnl_percent

        # Update trade record
        self.open_trade.exit_time = candle["time"]
        self.open_trade.exit_price = exit_price
        self.open_trade.pnl = pnl_usd
        self.open_trade.pnl_percent = pnl_percent * 100
        self.open_trade.exit_reason = reason

        # Update balance
        self.balance += pnl_usd

        # Save trade
        self.trades.append(self.open_trade)
        self.open_trade = None

    def run(self, candles: List[dict], strategy_config: dict, strategy_name: str = "test") -> BacktestResult:
        """Run backtest on historical data"""
        logger.info(f"\nRunning backtest: {strategy_name}")
        logger.info(f"Data: {len(candles)} candles")
        logger.info(f"Initial: ${self.initial_balance}, Leverage: {self.leverage}x")
        logger.info("-" * 50)

        self.balance = self.initial_balance
        self.trades = []
        self.open_trade = None
        self.prices.clear()
        self.highs.clear()
        self.lows.clear()

        peak_balance = self.initial_balance
        max_drawdown = 0

        for candle in candles:
            self.prices.append(candle["close"])
            self.highs.append(candle["high"])
            self.lows.append(candle["low"])
            self.volumes.append(candle["volume"])

            # Track equity
            self.equity_curve.append(self.balance)

            # Check drawdown
            if self.balance > peak_balance:
                peak_balance = self.balance
            drawdown = (peak_balance - self.balance) / peak_balance * 100
            max_drawdown = max(max_drawdown, drawdown)

            # Check exit first
            exit_reason = self._check_exit(candle)
            if exit_reason:
                self._execute_exit(candle, exit_reason)

            # Check entry (only if no position)
            if not self.open_trade and len(self.prices) > 50:
                signal = self._check_entry(candle, strategy_config)
                if signal:
                    self._execute_entry(candle, signal, strategy_name)

        # Close any open trade at end
        if self.open_trade:
            self._execute_exit(candles[-1], "end_of_data")

        return self._calculate_results(max_drawdown, len(candles))

    def _calculate_results(self, max_drawdown: float, num_candles: int) -> BacktestResult:
        """Calculate backtest statistics"""
        result = BacktestResult()

        result.total_trades = len(self.trades)
        result.max_drawdown = max_drawdown
        result.trades = self.trades

        if not self.trades:
            return result

        wins = [t for t in self.trades if t.pnl > 0]
        losses = [t for t in self.trades if t.pnl <= 0]

        result.winning_trades = len(wins)
        result.losing_trades = len(losses)
        result.win_rate = len(wins) / len(self.trades) * 100

        result.total_pnl = sum(t.pnl for t in self.trades)
        result.avg_win = sum(t.pnl for t in wins) / len(wins) if wins else 0
        result.avg_loss = sum(t.pnl for t in losses) / len(losses) if losses else 0

        result.best_trade = max(t.pnl for t in self.trades)
        result.worst_trade = min(t.pnl for t in self.trades)

        # Profit factor
        gross_profit = sum(t.pnl for t in wins)
        gross_loss = abs(sum(t.pnl for t in losses))
        result.profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

        # Average trade duration
        durations = [(t.exit_time - t.entry_time).total_seconds() / 60 for t in self.trades if t.exit_time]
        result.avg_trade_duration = sum(durations) / len(durations) if durations else 0

        # Estimate daily P&L (assuming 5-min candles)
        days = num_candles * 5 / 60 / 24
        result.daily_avg_pnl = result.total_pnl / days if days > 0 else 0

        return result


def print_results(result: BacktestResult, initial_balance: float):
    """Pretty print backtest results"""
    print("\n" + "=" * 60)
    print("BACKTEST RESULTS")
    print("=" * 60)

    final_balance = initial_balance + result.total_pnl
    roi = (result.total_pnl / initial_balance) * 100

    print(f"\nPerformance:")
    print(f"  Initial Balance:  ${initial_balance:,.2f}")
    print(f"  Final Balance:    ${final_balance:,.2f}")
    print(f"  Total P&L:        ${result.total_pnl:,.2f} ({roi:+.1f}%)")
    print(f"  Max Drawdown:     {result.max_drawdown:.1f}%")

    print(f"\nTrades:")
    print(f"  Total Trades:     {result.total_trades}")
    print(f"  Winners:          {result.winning_trades} ({result.win_rate:.1f}%)")
    print(f"  Losers:           {result.losing_trades}")
    print(f"  Profit Factor:    {result.profit_factor:.2f}")

    print(f"\nAverages:")
    print(f"  Avg Win:          ${result.avg_win:,.2f}")
    print(f"  Avg Loss:         ${result.avg_loss:,.2f}")
    print(f"  Avg Duration:     {result.avg_trade_duration:.0f} min")
    print(f"  Daily Avg P&L:    ${result.daily_avg_pnl:,.2f}")

    print(f"\nBest/Worst:")
    print(f"  Best Trade:       ${result.best_trade:,.2f}")
    print(f"  Worst Trade:      ${result.worst_trade:,.2f}")

    # Daily target check
    target = 200
    if result.daily_avg_pnl >= target:
        print(f"\n✓ MEETS ${target}/day target!")
    else:
        needed_improvement = ((target / result.daily_avg_pnl) - 1) * 100 if result.daily_avg_pnl > 0 else float('inf')
        print(f"\n✗ Below ${target}/day target (need {needed_improvement:.0f}% improvement)")

    print("=" * 60)


def run_simulation(iterations: int = 100, config: dict = None):
    """
    Monte Carlo simulation to estimate realistic outcomes
    """
    print(f"\nRunning {iterations} Monte Carlo simulations...")

    if not config:
        config = {"initial_balance_usd": 1000, "leverage": 3}

    # Simulate based on realistic win rates and R:R
    results = []

    for _ in range(iterations):
        balance = config.get("initial_balance_usd", 1000)
        daily_pnls = []

        # Simulate 30 days
        for day in range(30):
            daily_pnl = 0
            trades_today = random.randint(3, 6)

            for _ in range(trades_today):
                # 55% win rate, 2:1 R:R
                win = random.random() < 0.55
                risk = balance * 0.01 * config.get("leverage", 3)  # 1% risk * leverage

                if win:
                    daily_pnl += risk * 2  # 2:1 reward
                else:
                    daily_pnl -= risk

            balance += daily_pnl
            daily_pnls.append(daily_pnl)

            # Stop if blown
            if balance <= 0:
                break

        results.append({
            "final_balance": balance,
            "total_pnl": balance - config.get("initial_balance_usd", 1000),
            "avg_daily": sum(daily_pnls) / len(daily_pnls) if daily_pnls else 0,
            "days_positive": sum(1 for p in daily_pnls if p > 0)
        })

    # Analyze results
    avg_pnl = sum(r["total_pnl"] for r in results) / len(results)
    avg_daily = sum(r["avg_daily"] for r in results) / len(results)
    profitable = sum(1 for r in results if r["total_pnl"] > 0) / len(results) * 100
    hit_target = sum(1 for r in results if r["avg_daily"] >= 200) / len(results) * 100

    print("\n" + "=" * 60)
    print("MONTE CARLO SIMULATION RESULTS")
    print("=" * 60)
    print(f"Simulations: {iterations}")
    print(f"Period: 30 days")
    print(f"\nOutcomes:")
    print(f"  Profitable runs:  {profitable:.0f}%")
    print(f"  Hit $200/day:     {hit_target:.0f}%")
    print(f"  Avg Total P&L:    ${avg_pnl:,.2f}")
    print(f"  Avg Daily P&L:    ${avg_daily:,.2f}")
    print("=" * 60)

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Crypto Strategy Backtester")
    parser.add_argument("--pair", default="BTC-USD", help="Trading pair")
    parser.add_argument("--days", type=int, default=30, help="Days of data")
    parser.add_argument("--leverage", type=int, default=3, help="Leverage")
    parser.add_argument("--balance", type=float, default=1000, help="Starting balance")
    parser.add_argument("--simulate", action="store_true", help="Run Monte Carlo simulation")
    args = parser.parse_args()

    if args.simulate:
        run_simulation(100, {"initial_balance_usd": args.balance, "leverage": args.leverage})
    else:
        # Fetch data
        candles = DataFetcher.get_historical_prices(args.pair, args.days, "5min")

        if candles:
            # Run backtest
            config = {
                "initial_balance_usd": args.balance,
                "leverage": args.leverage,
                "commission_percent": 0.1,
                "slippage_percent": 0.05
            }

            strategy = {
                "stop_loss_percent": 0.5,
                "take_profit_percent": 1.2,
                "ema_fast": 8,
                "ema_slow": 21,
                "rsi_entry_low": 35,
                "rsi_entry_high": 65
            }

            bt = Backtester(config)
            result = bt.run(candles, strategy, "Scalp Momentum 3x")
            print_results(result, args.balance)
        else:
            print("Failed to fetch data")
