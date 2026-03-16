#!/usr/bin/env python3
"""
Strategy Optimizer
Find the best parameters to hit $200/day target
"""

import json
from backtester import Backtester, DataFetcher, print_results
from itertools import product
import logging

logging.basicConfig(level=logging.WARNING)


def optimize_strategy(candles: list, initial_balance: float = 1000):
    """
    Grid search for optimal parameters
    """
    print("\n" + "=" * 60)
    print("STRATEGY OPTIMIZER")
    print("Finding best parameters for $200/day...")
    print("=" * 60)

    # Parameter ranges to test
    param_grid = {
        "leverage": [3, 4],
        "stop_loss_percent": [0.3, 0.5, 0.7],
        "take_profit_percent": [0.8, 1.0, 1.5, 2.0],
        "ema_fast": [5, 8, 13],
        "ema_slow": [21, 34],
        "rsi_entry_low": [30, 35, 40],
        "rsi_entry_high": [60, 65, 70]
    }

    best_result = None
    best_params = None
    best_daily = 0

    total_combinations = 1
    for v in param_grid.values():
        total_combinations *= len(v)

    print(f"Testing {total_combinations} parameter combinations...")

    results = []
    tested = 0

    # Generate all combinations
    keys = list(param_grid.keys())
    for values in product(*param_grid.values()):
        params = dict(zip(keys, values))

        # Skip invalid combinations (TP must be > SL for good R:R)
        if params["take_profit_percent"] < params["stop_loss_percent"] * 1.5:
            continue

        if params["ema_fast"] >= params["ema_slow"]:
            continue

        config = {
            "initial_balance_usd": initial_balance,
            "leverage": params["leverage"],
            "commission_percent": 0.1,
            "slippage_percent": 0.05
        }

        strategy = {
            "stop_loss_percent": params["stop_loss_percent"],
            "take_profit_percent": params["take_profit_percent"],
            "ema_fast": params["ema_fast"],
            "ema_slow": params["ema_slow"],
            "rsi_entry_low": params["rsi_entry_low"],
            "rsi_entry_high": params["rsi_entry_high"]
        }

        bt = Backtester(config)
        result = bt.run(candles, strategy, "test")

        tested += 1

        if result.total_trades >= 5:  # Need minimum trades
            results.append({
                "params": params,
                "daily_pnl": result.daily_avg_pnl,
                "total_pnl": result.total_pnl,
                "win_rate": result.win_rate,
                "trades": result.total_trades,
                "drawdown": result.max_drawdown,
                "profit_factor": result.profit_factor
            })

            if result.daily_avg_pnl > best_daily:
                best_daily = result.daily_avg_pnl
                best_result = result
                best_params = params

        if tested % 50 == 0:
            print(f"  Tested {tested} combinations, best so far: ${best_daily:.2f}/day")

    # Sort by daily P&L
    results.sort(key=lambda x: x["daily_pnl"], reverse=True)

    print("\n" + "-" * 60)
    print("TOP 5 PARAMETER SETS:")
    print("-" * 60)

    for i, r in enumerate(results[:5], 1):
        print(f"\n#{i} - ${r['daily_pnl']:.2f}/day")
        print(f"   Leverage: {r['params']['leverage']}x")
        print(f"   SL: {r['params']['stop_loss_percent']}%, TP: {r['params']['take_profit_percent']}%")
        print(f"   EMA: {r['params']['ema_fast']}/{r['params']['ema_slow']}")
        print(f"   RSI: {r['params']['rsi_entry_low']}-{r['params']['rsi_entry_high']}")
        print(f"   Win Rate: {r['win_rate']:.1f}%, Trades: {r['trades']}, DD: {r['drawdown']:.1f}%")

    if best_params:
        print("\n" + "=" * 60)
        print("BEST PARAMETERS FOUND:")
        print("=" * 60)
        print(json.dumps(best_params, indent=2))

        # Check if hits target
        target = 200
        if best_daily >= target:
            print(f"\n✓ CAN hit ${target}/day target!")
        else:
            shortfall = target - best_daily
            leverage_needed = (target / best_daily) * best_params["leverage"] if best_daily > 0 else "N/A"
            print(f"\n✗ Best: ${best_daily:.2f}/day (${shortfall:.2f} short)")
            print(f"   Would need ~{leverage_needed:.1f}x leverage OR more volatile asset")

    return best_params, results


def suggest_improvements(results: list, target_daily: float = 200):
    """
    Analyze results and suggest how to hit target
    """
    print("\n" + "=" * 60)
    print("RECOMMENDATIONS TO HIT $200/DAY")
    print("=" * 60)

    if not results:
        print("No results to analyze")
        return

    best = results[0]
    current = best["daily_pnl"]

    if current <= 0:
        print("Strategy is not profitable. Consider:")
        print("  1. Different asset (higher volatility)")
        print("  2. Different strategy approach")
        return

    multiplier_needed = target_daily / current

    print(f"\nCurrent best: ${current:.2f}/day")
    print(f"Need {multiplier_needed:.1f}x improvement")

    print("\nOptions:")

    # Option 1: More leverage
    if best["params"]["leverage"] < 5:
        new_lev = min(best["params"]["leverage"] * multiplier_needed, 10)
        print(f"  1. Increase leverage to {new_lev:.0f}x (risky!)")

    # Option 2: Larger position
    new_balance = 1000 * multiplier_needed
    print(f"  2. Trade with ${new_balance:,.0f} instead of $1000")

    # Option 3: More trades
    trades_needed = best["trades"] * multiplier_needed
    print(f"  3. Find {trades_needed:.0f} trades instead of {best['trades']}")

    # Option 4: Better asset
    print(f"  4. Trade more volatile assets (ETH, SOL, altcoins)")

    # Option 5: Multiple strategies
    strategies_needed = multiplier_needed
    print(f"  5. Run {strategies_needed:.0f} strategies in parallel")

    print("\nREALISTIC PATH TO $200/DAY:")
    print("-" * 40)
    print("  • Start with $2,000-3,000 capital")
    print("  • Use 3-4x leverage")
    print("  • Trade 3-4 pairs (BTC, ETH, SOL)")
    print("  • Run 2-3 strategies simultaneously")
    print("  • Target $50-70 per strategy/pair")


if __name__ == "__main__":
    print("Fetching historical data...")
    candles = DataFetcher.get_historical_prices("BTC-USD", 14, "5min")

    if candles:
        best_params, results = optimize_strategy(candles, 1000)
        suggest_improvements(results, 200)
    else:
        print("Failed to fetch data")
