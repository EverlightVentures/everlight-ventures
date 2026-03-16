"""Rolling trade expectancy gate.

Reads recent closed trades from trades.csv and computes rolling
performance metrics. When the bot is in a cold streak, blocks or
shrinks entries to protect capital. Cache: 30s on-disk so CSV isn't
re-parsed every 5s cycle.

Pattern: identical to sentiment_gate.py -- pure functions, no init().
"""
from __future__ import annotations

import csv
import json
import math
import time
from pathlib import Path
from typing import Any

_CACHE_FILE = Path(__file__).resolve().parent.parent / "data" / "rolling_expectancy_cache.json"
_CACHE_TTL_S = 30  # recompute every 30 seconds (trades close infrequently)


def _read_cache() -> dict:
    try:
        if _CACHE_FILE.exists():
            out = json.loads(_CACHE_FILE.read_text())
            return out if isinstance(out, dict) else {}
    except Exception:
        pass
    return {}


def _write_cache(payload: dict) -> None:
    try:
        _CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = _CACHE_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, separators=(",", ":")))
        tmp.replace(_CACHE_FILE)
    except Exception:
        pass


def compute_rolling_expectancy(
    trades_csv_path: str | Path,
    lookback: int = 20,
) -> dict:
    """Read last N closed trades, compute rolling stats.

    Returns:
        trade_count: int - number of closed trades in window
        win_rate: float - wins / total (0.0-1.0)
        avg_pnl_usd: float - average PnL per trade (expectancy)
        profit_factor: float - gross_profit / abs(gross_loss), inf if no losses
        gross_profit: float
        gross_loss: float
        best_trade: float
        worst_trade: float
        avg_winner: float
        avg_loser: float
        streak_losses: int - current consecutive loss count (tail of window)
    """
    empty = {
        "trade_count": 0,
        "win_rate": 0.0,
        "avg_pnl_usd": 0.0,
        "profit_factor": 0.0,
        "gross_profit": 0.0,
        "gross_loss": 0.0,
        "best_trade": 0.0,
        "worst_trade": 0.0,
        "avg_winner": 0.0,
        "avg_loser": 0.0,
        "streak_losses": 0,
    }

    path = Path(trades_csv_path)
    if not path.exists():
        return empty

    try:
        closed_trades: list[float] = []
        with open(path, "r", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                ep = (row.get("exit_price") or "").strip()
                pnl_str = (row.get("pnl_usd") or "").strip()
                if ep and pnl_str:
                    try:
                        pnl = float(pnl_str)
                        closed_trades.append(pnl)
                    except (ValueError, TypeError):
                        continue

        if not closed_trades:
            return empty

        # Take last N trades
        window = closed_trades[-lookback:]
        n = len(window)

        wins = [p for p in window if p > 0]
        losses = [p for p in window if p < 0]
        gross_profit = sum(wins)
        gross_loss = sum(losses)  # negative number

        win_rate = len(wins) / n if n > 0 else 0.0
        avg_pnl = sum(window) / n if n > 0 else 0.0
        pf = gross_profit / abs(gross_loss) if gross_loss != 0 else (
            float("inf") if gross_profit > 0 else 0.0
        )

        avg_winner = gross_profit / len(wins) if wins else 0.0
        avg_loser = gross_loss / len(losses) if losses else 0.0

        # Tail streak: count consecutive losses from the end
        streak_losses = 0
        for p in reversed(window):
            if p < 0:
                streak_losses += 1
            else:
                break

        return {
            "trade_count": n,
            "win_rate": round(win_rate, 3),
            "avg_pnl_usd": round(avg_pnl, 2),
            "profit_factor": round(pf, 3) if not math.isinf(pf) else 999.0,
            "gross_profit": round(gross_profit, 2),
            "gross_loss": round(gross_loss, 2),
            "best_trade": round(max(window), 2),
            "worst_trade": round(min(window), 2),
            "avg_winner": round(avg_winner, 2),
            "avg_loser": round(avg_loser, 2),
            "streak_losses": streak_losses,
        }
    except Exception:
        return empty


def kelly_size_multiplier(
    expectancy: dict,
    min_trades: int = 10,
    kelly_fraction: float = 0.4,
    min_mult: float = 0.25,
    max_mult: float = 1.5,
) -> tuple:
    """Kelly Criterion position sizing from rolling trade expectancy.

    Computes fractional Kelly (kelly_fraction=0.4 = 40% Kelly) to size
    positions proportionally to edge.  Returns (multiplier, reason).

    Kelly formula: f* = (p*b - q) / b
      p = win_rate, q = 1-p, b = avg_winner / abs(avg_loser)

    Multiplier is centered on 1.0: >1.0 = oversize, <1.0 = undersize.
    Hard clamped to [min_mult, max_mult] for safety.
    """
    trade_count = int(expectancy.get("trade_count", 0))
    if trade_count < min_trades:
        return 1.0, f"kelly_n={trade_count}<{min_trades}_use_default"

    win_rate = float(expectancy.get("win_rate", 0.5))
    avg_winner = float(expectancy.get("avg_winner", 0.0))
    avg_loser = float(expectancy.get("avg_loser", 0.0))
    pf = float(expectancy.get("profit_factor", 0.0))

    if avg_loser == 0.0 or avg_winner <= 0.0:
        return 1.0, f"kelly_no_trade_data_pf={pf:.2f}"

    b = avg_winner / abs(avg_loser)
    p = win_rate
    q = 1.0 - p

    if b <= 0:
        return min_mult, "kelly_negative_b_min_size"

    kelly_full = (p * b - q) / b
    kelly_adj = kelly_full * kelly_fraction

    # Map kelly fraction to size multiplier centered at 1.0
    mult = max(min_mult, min(max_mult, 1.0 + kelly_adj))
    reason = (
        f"kelly_f={kelly_full:.3f}_adj={kelly_adj:.3f}"
        f"_pf={pf:.2f}_wr={p:.0%}_mult={mult:.3f}"
    )
    return round(mult, 3), reason


def get_rolling_expectancy(
    trades_csv_path: str | Path,
    lookback: int = 20,
) -> dict:
    """Cached wrapper: reads from disk cache, recomputes if stale."""
    cache = _read_cache()
    now_ts = time.time()
    cache_ts = float(cache.get("_ts", 0))

    if (now_ts - cache_ts) < _CACHE_TTL_S and cache.get("trade_count") is not None:
        return {k: v for k, v in cache.items() if not k.startswith("_")}

    fresh = compute_rolling_expectancy(trades_csv_path, lookback)
    payload = {**fresh, "_ts": now_ts}
    _write_cache(payload)
    return fresh


def evaluate_expectancy_gate(
    expectancy: dict,
    config: dict,
) -> dict:
    """Evaluate whether rolling expectancy allows entry.

    Args:
        expectancy: output from get_rolling_expectancy()
        config: the rolling_expectancy config section

    Returns:
        allowed: bool
        reason: str
        size_mult: float (1.0 = full, 0.5 = reduced, 0.0 = blocked)
        expectancy_data: dict (the full metrics for logging)
        action: str ("normal", "reduce_size", "block")
    """
    result: dict[str, Any] = {
        "allowed": True,
        "reason": "expectancy_ok",
        "size_mult": 1.0,
        "expectancy_data": expectancy,
        "action": "normal",
    }

    if not config.get("enabled", False):
        result["reason"] = "expectancy_gate_disabled"
        return result

    trade_count = int(expectancy.get("trade_count", 0))
    min_trades = int(config.get("min_trades", 10))

    # Not enough data to judge -- allow trading
    if trade_count < min_trades:
        result["reason"] = f"expectancy_insufficient_data_{trade_count}_of_{min_trades}"
        return result

    win_rate = float(expectancy.get("win_rate", 0))
    avg_pnl = float(expectancy.get("avg_pnl_usd", 0))
    pf = float(expectancy.get("profit_factor", 0))
    streak = int(expectancy.get("streak_losses", 0))

    min_win_rate = float(config.get("min_win_rate", 0.25))
    reduce_win_rate = float(config.get("reduce_win_rate", 0.35))
    reduce_mult = float(config.get("reduce_size_mult", 0.5))
    min_ev = float(config.get("min_ev_usd", -3.0))
    min_pf = float(config.get("min_profit_factor", 0.5))
    max_tail = int(config.get("max_tail_losses", 5))

    # Priority 1: Tail streak kill switch
    if streak >= max_tail:
        result["allowed"] = False
        result["reason"] = f"expectancy_tail_streak_{streak}_losses"
        result["size_mult"] = 0.0
        result["action"] = "block"
        return result

    # Priority 2: Hard block -- win rate, EV, or PF catastrophic
    if win_rate < min_win_rate:
        result["allowed"] = False
        result["reason"] = f"expectancy_low_win_rate_{win_rate:.0%}"
        result["size_mult"] = 0.0
        result["action"] = "block"
        return result

    if avg_pnl < min_ev:
        result["allowed"] = False
        result["reason"] = f"expectancy_negative_ev_${avg_pnl:.2f}"
        result["size_mult"] = 0.0
        result["action"] = "block"
        return result

    if pf < min_pf:
        result["allowed"] = False
        result["reason"] = f"expectancy_low_pf_{pf:.2f}"
        result["size_mult"] = 0.0
        result["action"] = "block"
        return result

    # Priority 3: Warning zone -- reduce size
    if win_rate < reduce_win_rate:
        result["size_mult"] = reduce_mult
        result["reason"] = f"expectancy_reduced_wr_{win_rate:.0%}"
        result["action"] = "reduce_size"
        return result

    return result
