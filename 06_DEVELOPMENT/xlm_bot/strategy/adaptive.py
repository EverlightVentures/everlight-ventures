"""Adaptive score threshold computation based on recent trade performance."""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Tuple


def compute_adaptive_threshold(
    trades_csv_path: str | Path,
    config: dict,
    default_threshold: int,
) -> Tuple[int, str]:
    """Compute an adaptive score threshold from recent closed trades.

    Walks 5-point v4 score buckets from lowest up and finds the first bucket
    where win_rate >= target with at least min_sample_size trades.

    Returns (threshold, reason).  Only raises, never lowers below default.
    """
    v4_cfg = (config.get("v4") or {}) if isinstance(config.get("v4"), dict) else {}
    adapt_cfg = (v4_cfg.get("adaptive_threshold") or {}) if isinstance(v4_cfg.get("adaptive_threshold"), dict) else {}

    if not adapt_cfg.get("enabled", False):
        return default_threshold, "adaptive_disabled"

    lookback = int(adapt_cfg.get("lookback_trades", 30) or 30)
    min_sample = int(adapt_cfg.get("min_sample_size", 5) or 5)
    target_wr = float(adapt_cfg.get("target_win_rate", 0.50) or 0.50)

    path = Path(trades_csv_path)
    if not path.exists():
        return default_threshold, "no_trades_file"

    # Read closed trades (rows with both entry_price and exit_price set)
    closed: list[dict] = []
    try:
        with open(path, "r", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                ep = (row.get("entry_price") or "").strip()
                xp = (row.get("exit_price") or "").strip()
                pnl_raw = (row.get("pnl_usd") or "").strip()
                score_raw = (row.get("confluence_score") or "").strip()
                if not ep or not xp or not pnl_raw or not score_raw:
                    continue
                # Skip test entries
                entry_type = (row.get("entry_type") or "").upper()
                if "TEST" in entry_type:
                    continue
                try:
                    pnl = float(pnl_raw)
                    score = int(float(score_raw))
                except (ValueError, TypeError):
                    continue
                closed.append({"score": score, "pnl": pnl, "win": pnl > 0})
    except Exception:
        return default_threshold, "trades_read_error"

    if len(closed) < min_sample:
        return default_threshold, f"insufficient_trades({len(closed)}<{min_sample})"

    # Take last N closed trades
    recent = closed[-lookback:]

    # Group into 5-point buckets: 60-64, 65-69, 70-74, ...
    buckets: dict[int, list[bool]] = {}
    for t in recent:
        floor = (t["score"] // 5) * 5
        buckets.setdefault(floor, []).append(t["win"])

    # Walk from lowest bucket up, find first where wr >= target with enough samples
    new_threshold = default_threshold
    reason_parts = []
    for floor in sorted(buckets.keys()):
        wins_in_bucket = buckets[floor]
        n = len(wins_in_bucket)
        if n < min_sample:
            reason_parts.append(f"{floor}:{n}n_skip")
            continue
        wr = sum(wins_in_bucket) / n
        if wr >= target_wr:
            # This bucket meets the target — use it if it's higher than default
            if floor > default_threshold:
                new_threshold = floor
                reason_parts.append(f"{floor}:{wr:.0%}wr_ok_raise")
            else:
                reason_parts.append(f"{floor}:{wr:.0%}wr_ok_at_default")
            break
        else:
            # Below target — all scores in this bucket lose too much, raise above it
            candidate = floor + 5
            if candidate > new_threshold:
                new_threshold = candidate
            reason_parts.append(f"{floor}:{wr:.0%}wr_low")

    # Never lower below default
    if new_threshold < default_threshold:
        new_threshold = default_threshold

    reason = f"adaptive({'|'.join(reason_parts)})={new_threshold}"
    return new_threshold, reason


def compute_vol_adaptive_threshold(
    base_threshold: int,
    atr_value: float,
    atr_20bar_mean: float,
) -> Tuple[int, str]:
    """Volatility-aware threshold scaling.

    Raises the entry threshold in high-volatility regimes to filter noise.
    Lowers slightly in dead-market compression to catch early setups.

    ATR ratio = atr_value / atr_20bar_mean:
      >= 2.2 : shock volatility  → +25 pts
      >= 1.6 : high volatility   → +15 pts
      >= 1.2 : elevated vol      → +8 pts
      <= 0.5 : dead market       → -5 pts (never lowers below base)
      else   : normal            →  0 pts

    Returns (new_threshold, reason).  Never lowers below base_threshold.
    """
    if atr_20bar_mean <= 0 or atr_value <= 0:
        return base_threshold, "vol_adapt_no_atr_data"

    atr_ratio = atr_value / atr_20bar_mean

    if atr_ratio >= 2.2:
        delta = 25
        label = f"shock_{atr_ratio:.1f}x"
    elif atr_ratio >= 1.6:
        delta = 15
        label = f"high_{atr_ratio:.1f}x"
    elif atr_ratio >= 1.2:
        delta = 8
        label = f"elevated_{atr_ratio:.1f}x"
    elif atr_ratio <= 0.5:
        delta = -5
        label = f"dead_{atr_ratio:.1f}x"
    else:
        delta = 0
        label = "normal"

    # Never lower below the base threshold passed in
    new_threshold = max(base_threshold, base_threshold + delta)
    reason = f"vol_adapt({label}):{base_threshold}→{new_threshold}"
    return new_threshold, reason
