"""Pattern Performance Tracker - Learn which patterns win/lose on XLM.

After each trade closes, log the active patterns at entry time and the outcome.
On next entry, check historical performance and adjust pattern score bonuses.
"""
from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict


def log_trade_patterns(
    log_path: str,
    trade_id: str,
    direction: str,
    outcome: str,
    pnl_usd: float,
    patterns_at_entry: list,
    candle_patterns: list,
    lane: str,
    entry_type: str,
):
    """Log which patterns were active when this trade was entered."""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "trade_id": trade_id,
        "direction": direction,
        "outcome": outcome,
        "pnl_usd": round(pnl_usd, 4),
        "lane": lane,
        "entry_type": entry_type,
        "chart_patterns": patterns_at_entry,
        "candle_patterns": candle_patterns,
    }
    try:
        p = Path(log_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass


def get_pattern_adjustments(
    log_path: str,
    min_samples: int = 20,
    weak_threshold: float = 0.30,
    strong_threshold: float = 0.60,
    weak_penalty: float = 0.50,
    strong_boost: float = 1.50,
) -> dict:
    """Analyze pattern performance and return score adjustment multipliers.

    Returns: {"pattern_name": multiplier, ...}
    1.0 = neutral, 0.5 = weak (<30% WR), 1.5 = strong (>60% WR)
    """
    adjustments = {}
    try:
        p = Path(log_path)
        if not p.exists():
            return adjustments

        pattern_stats = defaultdict(lambda: {"wins": 0, "losses": 0})

        with open(p) as f:
            for line in f:
                try:
                    d = json.loads(line.strip())
                    outcome = d.get("outcome", "")
                    for pat in d.get("chart_patterns", []) + d.get("candle_patterns", []):
                        if outcome == "win":
                            pattern_stats[pat]["wins"] += 1
                        elif outcome == "loss":
                            pattern_stats[pat]["losses"] += 1
                except Exception:
                    continue

        for pat, stats in pattern_stats.items():
            total = stats["wins"] + stats["losses"]
            if total < min_samples:
                continue
            win_rate = stats["wins"] / total
            if win_rate < weak_threshold:
                adjustments[pat] = weak_penalty
            elif win_rate > strong_threshold:
                adjustments[pat] = strong_boost
            else:
                adjustments[pat] = 1.0

    except Exception:
        pass

    return adjustments
