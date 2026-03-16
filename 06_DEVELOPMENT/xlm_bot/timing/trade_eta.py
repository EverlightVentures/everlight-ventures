"""Trade timing intelligence — close ETAs and next-entry estimates."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pandas as pd


# ── Helpers ──────────────────────────────────────────────────────────

def _fmt_dur(minutes: float) -> str:
    """Human-readable duration string."""
    if minutes < 1:
        return "< 1m"
    m = int(round(minutes))
    if m < 60:
        return f"{m}m"
    h, r = divmod(m, 60)
    return f"{h}h {r}m" if r else f"{h}h"


# Trade-state multipliers for expected hold time
_STATE_MULT = {
    "DECAY": 0.10,
    "UNDERWATER": 0.50,
    "SECURED": 0.70,
    "EARLY": 1.0,
    "BUILDING": 1.0,
    "EXPANSION": 1.5,
}


# ── Close ETA ────────────────────────────────────────────────────────

def estimate_close_eta(
    open_position: dict[str, Any],
    trades_df: pd.DataFrame,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Estimate when the current trade will close, based on historical data."""
    now = now or datetime.now(timezone.utc)
    result: dict[str, Any] = {}

    # Elapsed
    entry_time_str = open_position.get("entry_time") or ""
    try:
        entry_dt = datetime.fromisoformat(entry_time_str)
        if entry_dt.tzinfo is None:
            entry_dt = entry_dt.replace(tzinfo=timezone.utc)
    except Exception:
        entry_dt = now
    elapsed_min = max(0.0, (now - entry_dt).total_seconds() / 60.0)
    result["elapsed_min"] = round(elapsed_min, 1)
    result["elapsed_display"] = _fmt_dur(elapsed_min)

    # Build group key
    et = str(open_position.get("entry_type") or "")
    tf = str(open_position.get("breakout_tf") or "")
    regime = str(open_position.get("strategy_regime") or "")

    # Filter historical trades (real trades only — exclude phantom/test)
    hist = _filter_real_trades(trades_df)
    confidence = "high"

    # Try exact match first
    matched = hist
    if et:
        m = hist[hist["entry_type"].astype(str) == et]
        if len(m) >= 5:
            matched = m
        else:
            confidence = "low"

    # Further narrow by tf + regime if enough data
    if len(matched) >= 10 and tf:
        m2 = matched[matched["breakout_tf"].astype(str) == tf]
        if len(m2) >= 5:
            matched = m2
            if confidence == "high" and regime:
                m3 = matched[matched["strategy_regime"].astype(str) == regime]
                if len(m3) >= 5:
                    matched = m3

    if confidence != "low" and len(matched) < 10:
        confidence = "medium"

    # Compute historical stats
    hold_times = matched["time_in_trade_min"].dropna()
    if hold_times.empty:
        result.update({
            "expected_hold_min": None, "expected_display": "no data",
            "remaining_min": None, "remaining_display": "—",
            "progress_pct": 0, "overdue": False,
            "historical_avg_min": None, "historical_range": "—",
            "historical_count": 0, "confidence": "low",
        })
        return result

    hist_avg = float(hold_times.median())
    hist_min_val = float(hold_times.min())
    hist_max_val = float(hold_times.max())
    hist_count = int(len(hold_times))

    # Adjust by trade state
    ew = open_position.get("exit_watch") or {}
    trade_state = str(ew.get("trade_state") or "EARLY")
    state_mult = _STATE_MULT.get(trade_state, 1.0)
    expected = hist_avg * state_mult

    # Adjust for TP proximity
    try:
        tp1 = float(ew.get("tp1") or 0)
        entry_price = float(open_position.get("entry_price") or 0)
        direction = str(open_position.get("direction") or "")
        mark = float(ew.get("dynamic_tp") or 0) or tp1
        if entry_price > 0 and tp1 > 0 and mark > 0:
            if direction == "long":
                total_move = tp1 - entry_price
                current_move = mark - entry_price if mark > entry_price else 0
            else:
                total_move = entry_price - tp1
                current_move = entry_price - mark if mark < entry_price else 0
            if total_move > 0:
                tp_progress = current_move / total_move
                if tp_progress > 0.80:
                    expected *= 0.60  # close to TP → speed up estimate
    except Exception:
        pass

    # Ensure minimum expected of 1 minute
    expected = max(expected, 1.0)
    remaining = expected - elapsed_min
    progress = (elapsed_min / expected * 100) if expected > 0 else 0

    if remaining > 0:
        remaining_display = f"~{_fmt_dur(remaining)} left"
    elif remaining > -1:
        remaining_display = "any moment"
    else:
        remaining_display = f"{_fmt_dur(abs(remaining))} overdue"

    result.update({
        "expected_hold_min": round(expected, 1),
        "expected_display": f"~{_fmt_dur(expected)}",
        "remaining_min": round(remaining, 1),
        "remaining_display": remaining_display,
        "progress_pct": round(progress, 1),
        "overdue": remaining < 0,
        "historical_avg_min": round(hist_avg, 1),
        "historical_range": f"{_fmt_dur(hist_min_val)}-{_fmt_dur(hist_max_val)}",
        "historical_count": hist_count,
        "confidence": confidence,
    })
    return result


# ── Next Entry ETA ───────────────────────────────────────────────────

def estimate_next_entry(
    state: dict[str, Any],
    last_decision: dict[str, Any],
    trades_df: pd.DataFrame,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Estimate when the next trade entry might happen."""
    now = now or datetime.now(timezone.utc)
    result: dict[str, Any] = {}

    # Best candidate from latest decision
    score_l = int(last_decision.get("v4_score_long") or 0)
    score_s = int(last_decision.get("v4_score_short") or 0)
    thresh_l = int(last_decision.get("v4_threshold_long") or 55)
    thresh_s = int(last_decision.get("v4_threshold_short") or 55)
    thought = str(last_decision.get("thought") or "")

    if score_s >= score_l:
        best_score, best_thresh, best_dir = score_s, thresh_s, "short"
    else:
        best_score, best_thresh, best_dir = score_l, thresh_l, "long"

    # Extract entry type from thought
    entry_type = ""
    for et_name in ("pullback", "breakout_retest", "compression_range", "early_impulse",
                     "compression_breakout", "fib_retrace", "slow_bleed_hunter", "trend_continuation"):
        if et_name.replace("_", " ") in thought.lower() or et_name in thought.lower():
            entry_type = et_name
            break

    if best_score > 0:
        result["watching_setup"] = f"{entry_type or 'signal'} {best_dir} ({best_score}/{best_thresh})"
        result["readiness_pct"] = round(best_score / max(best_thresh, 1) * 100, 0)
    else:
        result["watching_setup"] = "No setup visible"
        result["readiness_pct"] = 0

    # Blocking reasons
    blocking = None
    safe_mode = bool(state.get("_safe_mode"))
    cooldown = state.get("cooldown_until")
    if safe_mode:
        blocking = "safe mode"
    elif cooldown:
        try:
            cd_dt = datetime.fromisoformat(str(cooldown))
            if cd_dt.tzinfo is None:
                cd_dt = cd_dt.replace(tzinfo=timezone.utc)
            if cd_dt > now:
                remaining = (cd_dt - now).total_seconds() / 60.0
                blocking = f"cooldown ({_fmt_dur(remaining)})"
        except Exception:
            pass
    elif state.get("open_position"):
        blocking = "in trade"
    elif best_score > 0 and best_score < best_thresh:
        blocking = "score below threshold"
    elif "r:r" in thought.lower() or "rr" in thought.lower():
        blocking = "R:R too low"
    result["blocking_reason"] = blocking

    # Time since last exit
    last_exit_str = str(state.get("last_exit_time") or "")
    if last_exit_str:
        try:
            last_exit_dt = datetime.fromisoformat(last_exit_str)
            if last_exit_dt.tzinfo is None:
                last_exit_dt = last_exit_dt.replace(tzinfo=timezone.utc)
            result["time_since_exit_min"] = round((now - last_exit_dt).total_seconds() / 60.0, 1)
        except Exception:
            result["time_since_exit_min"] = None
    else:
        result["time_since_exit_min"] = None

    # Average gap between trades from history
    hist = _filter_real_trades(trades_df)
    if len(hist) >= 3 and "entry_time" in hist.columns:
        try:
            entry_times = pd.to_datetime(hist["entry_time"], utc=True, errors="coerce").dropna().sort_values()
            if len(entry_times) >= 3:
                gaps = entry_times.diff().dropna().dt.total_seconds() / 60.0
                # Filter out sub-2-min gaps (phantom re-entries)
                gaps = gaps[gaps >= 2.0]
                if not gaps.empty:
                    avg_gap = float(gaps.median())
                    # Adjust by vol state
                    vol = str(state.get("vol_state") or "")
                    if vol == "COMPRESSION":
                        avg_gap *= 1.5
                    elif vol == "EXPANSION":
                        avg_gap *= 0.6
                    result["avg_gap_min"] = round(avg_gap, 1)
                else:
                    result["avg_gap_min"] = None
            else:
                result["avg_gap_min"] = None
        except Exception:
            result["avg_gap_min"] = None
    else:
        result["avg_gap_min"] = None

    # Build display string
    if blocking:
        result["estimated_display"] = f"Blocked: {blocking}"
    elif best_score >= best_thresh and best_score > 0:
        result["estimated_display"] = "Setup ready"
    elif result.get("avg_gap_min"):
        result["estimated_display"] = f"~{_fmt_dur(result['avg_gap_min'])}"
    else:
        result["estimated_display"] = "Watching..."

    return result


# ── Internal ─────────────────────────────────────────────────────────

def _filter_real_trades(trades_df: pd.DataFrame) -> pd.DataFrame:
    """Build merged trade records from entry + exit row pairs in trades.csv.

    In this CSV, entry rows have entry_type/breakout_tf/strategy_regime but no
    time_in_trade_min, while exit rows have time_in_trade_min but no entry_type.
    We pair them by matching entry_time fields.
    """
    if trades_df is None or trades_df.empty:
        return pd.DataFrame()
    df = trades_df.copy()

    # Identify exit rows (have time_in_trade) and entry rows (have entry_type)
    if "time_in_trade_min" in df.columns:
        df["time_in_trade_min"] = pd.to_numeric(df["time_in_trade_min"], errors="coerce")
    if "entry_type" not in df.columns or "time_in_trade_min" not in df.columns:
        return pd.DataFrame()

    # Entry rows: have a non-empty entry_type
    entry_rows = df[df["entry_type"].astype(str).str.strip().ne("") & ~df["entry_type"].isna()].copy()
    entry_rows = entry_rows[~entry_rows["entry_type"].astype(str).isin(["test_fire", "live_test_fire"])]

    # Exit rows: have a numeric time_in_trade >= 1 min and a result
    exit_rows = df[df["time_in_trade_min"].notna() & (df["time_in_trade_min"] >= 3.0)].copy()
    if "result" in exit_rows.columns:
        exit_rows = exit_rows[exit_rows["result"].astype(str).isin(["win", "loss", "flat"])]

    if exit_rows.empty:
        return pd.DataFrame()

    # Build lookup: entry_time → entry metadata from entry rows
    if "entry_time" not in df.columns:
        return exit_rows  # fallback: no pairing possible

    entry_lookup = {}
    for _, row in entry_rows.iterrows():
        et_str = str(row.get("entry_time") or row.get("timestamp") or "")
        if et_str:
            entry_lookup[et_str] = {
                "entry_type": str(row.get("entry_type") or ""),
                "breakout_tf": str(row.get("breakout_tf") or ""),
                "strategy_regime": str(row.get("strategy_regime") or ""),
                "breakout_type": str(row.get("breakout_type") or ""),
            }

    # Merge entry metadata into exit rows
    def _merge_entry(row):
        et_str = str(row.get("entry_time") or "")
        meta = entry_lookup.get(et_str, {})
        for k, v in meta.items():
            cur = row.get(k)
            if cur is None or (isinstance(cur, float) and pd.isna(cur)) or str(cur).strip() in ("", "nan"):
                row[k] = v
        return row

    merged = exit_rows.apply(_merge_entry, axis=1)
    return merged
