"""Per-lane trading performance tracker.

Reads closed trades from the CSV trade log, groups them by entry lane
(A through O, plus X for ai_executive), and computes win rate, PnL,
and score-bucket statistics per lane.  Output is consumed by the AI
executive prompt builder and the dashboard.
"""
from __future__ import annotations

import json
import math
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Entry-type to lane-letter mapping
# ---------------------------------------------------------------------------

ENTRY_TYPE_TO_LANE: dict[str, str] = {
    "pullback": "A",
    "breakout_retest": "B",
    "reversal_impulse": "C",
    "early_impulse": "E",
    "compression_breakout": "F",
    "compression_range": "G",
    "trend_continuation": "H",
    "fib_retrace": "I",
    "slow_bleed_hunter": "J",
    "wick_rejection": "K",
    "volume_climax_reversal": "M",
    "vwap_reversion": "N",
    "grid_range": "P",
    # Score-10 upgrade lanes
    "funding_arb_bias": "Q",
    "regime_low_vol": "R",
    "stat_arb_proxy": "S",
    "orderflow_imbalance": "T",
    "macro_ma_cross": "U",
    "ai_executive": "X",
}

LANE_TO_ENTRY_TYPE: dict[str, str] = {v: k for k, v in ENTRY_TYPE_TO_LANE.items()}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _score_bucket_label(floor: int) -> str:
    """Return a label for a 5-point score bucket, e.g. floor=70 -> '70-74'."""
    return f"{floor}-{floor + 4}"


def _best_worst_buckets(
    scores: pd.Series,
    wins: pd.Series,
    min_bucket_trades: int = 2,
) -> tuple[str, str]:
    """Find 5-point score bucket with highest and lowest win rate."""
    if scores.empty:
        return "--", "--"

    floors = (scores // 5) * 5
    bucket_df = pd.DataFrame({"floor": floors.values, "win": wins.values})
    grouped = bucket_df.groupby("floor")["win"]
    counts = grouped.count()
    wr = grouped.mean()

    valid = counts[counts >= min_bucket_trades].index
    if valid.empty:
        return "--", "--"

    wr_valid = wr.loc[valid]
    best_floor = int(wr_valid.idxmax())
    worst_floor = int(wr_valid.idxmin())
    return _score_bucket_label(best_floor), _score_bucket_label(worst_floor)


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------


def compute_lane_stats(
    trades_csv_path: str | Path,
    lookback: int = 50,
) -> dict[str, dict]:
    """Read the trade log and compute per-lane statistics.

    Returns dict keyed by lane letter with: wins, losses, count, win_rate,
    avg_pnl_usd, total_pnl_usd, best_score_range, worst_score_range.
    """
    path = Path(trades_csv_path)
    try:
        df = pd.read_csv(path)
    except Exception:
        return {}

    if df.empty:
        return {}

    df.columns = [c.strip().lower() for c in df.columns]

    if "exit_price" not in df.columns or "entry_type" not in df.columns:
        return {}

    df["exit_price"] = pd.to_numeric(df["exit_price"], errors="coerce")
    df = df[df["exit_price"].notna()].copy()

    df["entry_type"] = df["entry_type"].astype(str).str.strip().str.lower()
    df = df[~df["entry_type"].str.contains("test", case=False, na=False)]

    if df.empty:
        return {}

    df["pnl_usd"] = pd.to_numeric(df.get("pnl_usd"), errors="coerce").fillna(0.0)
    df["confluence_score"] = pd.to_numeric(
        df.get("confluence_score"), errors="coerce"
    ).fillna(0.0)

    has_fees = "total_fees_usd" in df.columns
    if has_fees:
        df["total_fees_usd"] = pd.to_numeric(
            df["total_fees_usd"], errors="coerce"
        ).fillna(0.0)

    df = df.tail(lookback).copy()

    df["lane"] = df["entry_type"].map(ENTRY_TYPE_TO_LANE)
    df = df[df["lane"].notna()]

    if df.empty:
        return {}

    df["win"] = df["pnl_usd"] > 0

    stats: dict[str, dict] = {}

    for lane, group in df.groupby("lane"):
        lane_str = str(lane)
        wins = int(group["win"].sum())
        losses = int((~group["win"]).sum())
        count = len(group)
        win_rate = round(wins / count, 4) if count > 0 else 0.0
        avg_pnl = round(float(group["pnl_usd"].mean()), 4)
        total_pnl = round(float(group["pnl_usd"].sum()), 4)

        best_range, worst_range = _best_worst_buckets(
            group["confluence_score"], group["win"]
        )

        # Separate win/loss PnL for Kelly sizing
        win_mask = group["pnl_usd"] > 0
        avg_win_usd = round(float(group.loc[win_mask, "pnl_usd"].mean()), 4) if win_mask.any() else 0.0
        avg_loss_usd = round(float(group.loc[~win_mask, "pnl_usd"].mean()), 4) if (~win_mask).any() else 0.0

        # Sharpe ratio (per-trade, no risk-free)
        sharpe = _lane_sharpe(group["pnl_usd"].tolist())

        # Max drawdown
        max_dd = _lane_max_drawdown(group["pnl_usd"].tolist())

        entry: dict = {
            "wins": wins,
            "losses": losses,
            "count": count,
            "win_rate": win_rate,
            "avg_pnl_usd": avg_pnl,
            "avg_win_usd": avg_win_usd,
            "avg_loss_usd": avg_loss_usd,
            "total_pnl_usd": total_pnl,
            "sharpe": sharpe,
            "max_drawdown_usd": max_dd,
            "best_score_range": best_range,
            "worst_score_range": worst_range,
        }

        if has_fees:
            entry["avg_fees_usd"] = round(float(group["total_fees_usd"].mean()), 4)

        stats[lane_str] = entry

    return stats


def update_lane_performance(
    trades_csv_path: str | Path,
    output_path: str | Path,
    lookback: int = 50,
) -> dict[str, dict]:
    """Compute lane stats and atomically write to output_path.

    Returns the lanes stats dict.
    """
    lane_stats = compute_lane_stats(trades_csv_path, lookback=lookback)

    envelope = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "lookback_trades": lookback,
        "lanes": lane_stats,
    }

    out = Path(output_path)
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(
            dir=str(out.parent), suffix=".tmp", prefix=".lane_perf_"
        )
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(envelope, f, indent=2)
            os.replace(tmp_path, str(out))
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
    except Exception:
        pass

    return lane_stats


def get_lane_overrides(
    lane_stats: dict[str, dict],
    min_trades: int = 15,
    min_win_rate: float = 0.15,
    threshold_boost: int = 20,
) -> dict[str, dict]:
    """Derive per-lane override actions from performance stats.

    Returns dict keyed by lane letter with: action, reason, and optionally amount.
    Possible actions: 'disable', 'raise_threshold', 'observe'.
    """
    overrides: dict[str, dict] = {}

    for lane, s in lane_stats.items():
        count = s.get("count", 0)
        wr = s.get("win_rate", 0.0)

        if count < min_trades:
            overrides[lane] = {
                "action": "observe",
                "reason": f"only {count} trades, need more data",
            }
            continue

        wr_pct = round(wr * 100, 1)

        if wr < min_win_rate:
            overrides[lane] = {
                "action": "disable",
                "reason": f"{wr_pct}% WR < {round(min_win_rate * 100)}% min over {count} trades",
            }
        elif wr < min_win_rate * 2:
            overrides[lane] = {
                "action": "raise_threshold",
                "amount": threshold_boost,
                "reason": f"{wr_pct}% WR is marginal",
            }

    return overrides


def _lane_sharpe(pnls: list[float]) -> float | None:
    """Per-trade Sharpe ratio for a lane (no risk-free rate)."""
    if len(pnls) < 2:
        return None
    mean = sum(pnls) / len(pnls)
    variance = sum((p - mean) ** 2 for p in pnls) / (len(pnls) - 1)
    std = math.sqrt(variance)
    if std == 0:
        return None
    return round(mean / std, 3)


def _lane_max_drawdown(pnls: list[float]) -> float:
    """Peak-to-trough drawdown in USD from sequential lane PnLs."""
    cumulative = 0.0
    peak = 0.0
    max_dd = 0.0
    for p in pnls:
        cumulative += p
        if cumulative > peak:
            peak = cumulative
        dd = peak - cumulative
        if dd > max_dd:
            max_dd = dd
    return round(max_dd, 2)


def format_for_prompt(lane_stats: dict[str, dict]) -> str:
    """Format lane performance as an ASCII table for AI prompt injection."""
    overrides = get_lane_overrides(lane_stats)

    action_to_status = {
        "disable": "DISABLED",
        "raise_threshold": "BOOSTED",
        "observe": "OBSERVING",
    }

    header = "Lane | Entry Type               | W/L   | Win Rate | Avg PnL  | Sharpe | MaxDD   | Status"
    sep = "---- | ------------------------ | ----- | -------- | -------- | ------ | ------- | ---------"
    lines = [header, sep]

    for lane in sorted(lane_stats.keys()):
        s = lane_stats[lane]
        entry_type = LANE_TO_ENTRY_TYPE.get(lane, "unknown")
        wl = f"{s['wins']}/{s['losses']}"
        wr = f"{s['win_rate']:.0%}"
        avg_pnl = f"${s['avg_pnl_usd']:+.2f}"
        sharpe = s.get("sharpe")
        sharpe_str = f"{sharpe:.2f}" if sharpe is not None else "  --"
        max_dd = s.get("max_drawdown_usd", 0.0)
        max_dd_str = f"${max_dd:.2f}"
        status = action_to_status.get(
            overrides.get(lane, {}).get("action", ""), "ACTIVE"
        )

        lines.append(
            f"  {lane:2s} | {entry_type:24s} | {wl:5s} | {wr:>8s} | {avg_pnl:>8s} | "
            f"{sharpe_str:>6s} | {max_dd_str:>7s} | {status}"
        )

    return "\n".join(lines)
