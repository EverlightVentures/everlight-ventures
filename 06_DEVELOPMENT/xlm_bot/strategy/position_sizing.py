"""Kelly Criterion position sizing.

Calculates optimal bet fraction from actual trade history.
Half-Kelly is used for safety, capped at 25% of bankroll.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional


def kelly_fraction(win_rate: float, avg_win: float, avg_loss: float) -> float:
    """Kelly Criterion: optimal bet fraction.
    f* = (bp - q) / b where b=avg_win/avg_loss, p=win_rate, q=1-p
    Returns fraction of bankroll to risk (Half-Kelly, capped at 25%).
    Returns 0.0 if edge is negative or data is bad."""
    if avg_loss == 0 or win_rate <= 0 or win_rate > 1:
        return 0.0
    b = abs(avg_win / avg_loss)
    p = win_rate
    q = 1 - p
    kelly = (b * p - q) / b
    return max(0.0, min(kelly * 0.5, 0.25))  # Half-Kelly, capped at 25%


def kelly_from_trade_log(trade_log_path: Path, min_trades: int = 10) -> dict:
    """Calculate Kelly fraction from actual trade history.

    Reads trade_labels.jsonl, computes win rate and avg win/loss,
    then returns Kelly sizing recommendation.

    Returns dict with win_rate, avg_win, avg_loss, kelly_fraction, trades_analyzed.
    """
    result = {
        "win_rate": 0.0,
        "avg_win": 0.0,
        "avg_loss": 0.0,
        "kelly_fraction": 0.0,
        "kelly_pct": 0.0,
        "trades_analyzed": 0,
        "sufficient_data": False,
    }

    if not trade_log_path.exists():
        return result

    wins: list[float] = []
    losses: list[float] = []

    try:
        with open(trade_log_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                    if d.get("status") != "closed":
                        continue
                    pnl = d.get("pnl_usd")
                    if pnl is None:
                        continue
                    pnl = float(pnl)
                    if pnl > 0:
                        wins.append(pnl)
                    elif pnl < 0:
                        losses.append(abs(pnl))
                except Exception:
                    continue
    except Exception:
        return result

    total = len(wins) + len(losses)
    result["trades_analyzed"] = total

    if total < min_trades:
        return result

    result["sufficient_data"] = True
    result["win_rate"] = round(len(wins) / total, 4) if total > 0 else 0.0
    result["avg_win"] = round(sum(wins) / len(wins), 4) if wins else 0.0
    result["avg_loss"] = round(sum(losses) / len(losses), 4) if losses else 0.0

    kf = kelly_fraction(result["win_rate"], result["avg_win"], result["avg_loss"])
    result["kelly_fraction"] = round(kf, 4)
    result["kelly_pct"] = round(kf * 100, 2)

    return result
