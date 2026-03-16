from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yaml

from data.candles import CandleStore, load_or_fetch
from indicators.ema import ema
from strategy.regime import run_regime_gates
from structure.levels import compute_structure_levels
from structure.fib import find_swing, fib_levels
from strategy.entries import pullback_continuation, breakout_retest
from strategy.risk import stop_loss_price, sl_distance_ok
from strategy.exits import tp_prices
from strategy.confluence import confluence_count


BASE_DIR = Path(__file__).parents[1]


def load_config() -> dict:
    with open(BASE_DIR / "config.yaml", "r") as f:
        return yaml.safe_load(f)


def run(start: str, end: str) -> None:
    config = load_config()
    symbol = "XLM"
    product_id = config["product_id"]
    store = CandleStore(data_dir=BASE_DIR / "data")
    df_15m = load_or_fetch(store, product_id, symbol, "15m", days=365)
    df_1h = load_or_fetch(store, product_id, symbol, "1h", days=365)
    df_4h = load_or_fetch(store, product_id, symbol, "4h", days=365)

    start_dt = pd.to_datetime(start, utc=True)
    end_dt = pd.to_datetime(end, utc=True)

    df_15m = df_15m[(df_15m["timestamp"] >= start_dt) & (df_15m["timestamp"] <= end_dt)]
    if df_15m.empty:
        return

    trades = []
    i = 60
    while i < len(df_15m):
        advanced = False
        slice_15m = df_15m.iloc[: i + 1]
        ts = slice_15m["timestamp"].iloc[-1].to_pydatetime()
        price = float(slice_15m["close"].iloc[-1])

        df1 = df_1h[df_1h["timestamp"] <= slice_15m["timestamp"].iloc[-1]]
        df4 = df_4h[df_4h["timestamp"] <= slice_15m["timestamp"].iloc[-1]]
        if df1.empty or df4.empty:
            i += 1
            continue

        e21_1h = float(ema(df1["close"], 21).iloc[-1])
        spread_estimate = 0.001
        gates = run_regime_gates(df1, price, e21_1h, spread_estimate, config, ts)
        if not all(gates.values()):
            i += 1
            continue

        levels = compute_structure_levels(df4)
        swing_high, swing_low = find_swing(df4, 60)
        fibs = fib_levels(swing_high, swing_low)

        long_entry = pullback_continuation(price, df1, df4, slice_15m, levels, fibs, "long")
        long_entry = long_entry or breakout_retest(price, slice_15m, levels, fibs, "long")
        short_entry = pullback_continuation(price, df1, df4, slice_15m, levels, fibs, "short")
        short_entry = short_entry or breakout_retest(price, slice_15m, levels, fibs, "short")
        entry = None
        direction = None
        if long_entry and short_entry:
            if confluence_count(long_entry["confluence"]) >= confluence_count(short_entry["confluence"]):
                entry = long_entry
                direction = "long"
            else:
                entry = short_entry
                direction = "short"
        elif long_entry:
            entry = long_entry
            direction = "long"
        elif short_entry:
            entry = short_entry
            direction = "short"
        if not entry:
            i += 1
            continue

        stop_price = stop_loss_price(price, df1, direction)
        if not sl_distance_ok(price, stop_price, config["risk"]["max_sl_pct"]):
            i += 1
            continue

        leverage = min(int(config["leverage"]), 4)
        tp_plan = tp_prices(
            price,
            leverage,
            direction,
            config["exits"]["tp1_move"],
            config["exits"]["tp2_move"],
            config["exits"]["tp3_move"],
            full_close_at_tp1=config["exits"]["tp_full_close_if_single_contract"],
        )
        # Simulate exits forward
        entry_time = ts
        adverse = 0
        exit_reason = "none"
        exit_price = price
        for j in range(i + 1, min(len(df_15m), i + 1 + 200)):
            bar = df_15m.iloc[j]
            exit_price = float(bar["close"])
            pnl_pct = (exit_price - price) / price
            if direction == "short":
                pnl_pct = -pnl_pct
            if pnl_pct <= -config["exits"]["early_save_adverse_pct"]:
                adverse += 1
            elif pnl_pct > -0.005:
                adverse = 0
            bars_since = j - i
            time_stop = bars_since >= config["exits"]["time_stop_bars"] and pnl_pct < config["exits"]["time_stop_min_move_pct"]
            tp_hit = exit_price >= tp_plan.tp1 if direction == "long" else exit_price <= tp_plan.tp1
            if adverse >= config["exits"]["early_save_bars"]:
                exit_reason = "early_save"
                i = j
                advanced = True
                break
            if time_stop:
                exit_reason = "time_stop"
                i = j
                advanced = True
                break
            if tp_hit and config["exits"]["tp_full_close_if_single_contract"]:
                exit_reason = "tp1"
                i = j
                advanced = True
                break
        trades.append({
            "timestamp": entry_time.isoformat(),
            "entry_price": price,
            "stop_loss": stop_price,
            "tp1": tp_plan.tp1,
            "tp2": tp_plan.tp2,
            "tp3": tp_plan.tp3,
            "exit_price": exit_price,
            "exit_reason": exit_reason,
            "entry_type": entry["type"],
            "direction": direction,
        })
        if not advanced:
            i += 1

    out_path = BASE_DIR / "logs" / "backtest_trades.csv"
    if trades:
        with open(out_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(trades[0].keys()))
            writer.writeheader()
            writer.writerows(trades)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    args = parser.parse_args()
    run(args.start, args.end)


if __name__ == "__main__":
    main()
