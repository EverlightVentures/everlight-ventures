"""
Analytics service -- trade quality scoring, parameter performance, operator metrics.

All functions return safe defaults on error (empty dict/list/DataFrame).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd

from .formatters import safe_float, safe_str


# ---------------------------------------------------------------------------
# Trade quality scoring
# ---------------------------------------------------------------------------

def trade_quality_score(trade: dict, timeseries_df: pd.DataFrame | None = None) -> dict:
    """Score a closed trade on entry timing, exit efficiency, and stop quality.

    Returns dict with grade (A-D), numeric score 0-100, and component breakdowns.
    Returns ``{"ok": False}`` when scoring is not possible.
    """
    try:
        entry_price = float(trade.get("entry_price") or 0)
        exit_price = float(trade.get("exit_price") or 0)
        pnl_usd = float(trade.get("pnl_usd") or 0)
        direction = str(trade.get("side") or trade.get("direction") or "long").lower()
        entry_time_raw = trade.get("entry_time") or trade.get("timestamp")
        exit_time_raw = trade.get("exit_time")

        if not entry_price or not exit_price or entry_time_raw is None:
            return {"ok": False}

        entry_ts = pd.Timestamp(entry_time_raw, tz="UTC") if entry_time_raw else None
        exit_ts = pd.Timestamp(exit_time_raw, tz="UTC") if exit_time_raw else None
        if entry_ts is None:
            return {"ok": False}

        # Without timeseries data we cannot compute path-based metrics.
        if timeseries_df is None or timeseries_df.empty or "timestamp" not in timeseries_df.columns:
            return {"ok": False}

        mask = timeseries_df["timestamp"] >= entry_ts
        if exit_ts is not None:
            mask = mask & (timeseries_df["timestamp"] <= exit_ts)
        path_df = timeseries_df.loc[mask].head(200)
        if path_df.empty or len(path_df) < 2:
            return {"ok": False}

        prices = path_df["price"].astype(float).tolist()
        pnls: list[float] = []
        for px in prices:
            if direction == "short":
                pnls.append((entry_price - px) / entry_price * 100)
            else:
                pnls.append((px - entry_price) / entry_price * 100)

        mfe_idx = max(range(len(pnls)), key=lambda i: pnls[i])
        mae_idx = min(range(len(pnls)), key=lambda i: pnls[i])
        mfe_pct = pnls[mfe_idx]
        mae_pct = pnls[mae_idx]

        # Entry timing (40%): MFE before MAE = better entry.
        if len(pnls) > 1:
            timing_score = 100 if mfe_idx < mae_idx else (50 if mfe_idx == mae_idx else 20)
            if mfe_idx < len(pnls) / 3:
                timing_score = min(100, timing_score + 15)
        else:
            timing_score = 50

        # Exit efficiency (40%): pnl_pct / mfe_pct.
        pnl_pct = float(trade.get("pnl_pct") or 0)
        if mfe_pct > 0.01:
            efficiency = max(0, min(100, (pnl_pct / mfe_pct) * 100))
        elif pnl_pct > 0:
            efficiency = 80.0
        else:
            efficiency = 10.0

        # Stop quality (20%).
        exit_reason = str(trade.get("exit_reason") or "").lower()
        stop_hit = "stop" in exit_reason or "stopped" in exit_reason
        if stop_hit and mfe_pct > 0.5:
            stop_score = 15.0
        elif stop_hit and mfe_pct <= 0.1:
            stop_score = 70.0
        elif not stop_hit and pnl_usd > 0:
            stop_score = 90.0
        else:
            stop_score = 50.0

        total = timing_score * 0.40 + efficiency * 0.40 + stop_score * 0.20
        grade = "A" if total >= 80 else "B" if total >= 60 else "C" if total >= 40 else "D"

        return {
            "ok": True,
            "score": round(total, 1),
            "grade": grade,
            "timing_score": round(timing_score, 1),
            "efficiency": round(efficiency, 1),
            "stop_score": round(stop_score, 1),
            "mfe_pct": round(mfe_pct, 3),
            "mae_pct": round(mae_pct, 3),
            "pnl_usd": pnl_usd,
        }
    except Exception:
        return {"ok": False}


# ---------------------------------------------------------------------------
# Closed-trade extraction
# ---------------------------------------------------------------------------

def get_closed_trades(trades_df: pd.DataFrame) -> pd.DataFrame:
    """Filter DataFrame to rows with entry_price, exit_price, and pnl_usd."""
    if trades_df is None or trades_df.empty:
        return pd.DataFrame()
    df = trades_df.copy()
    for col in ("entry_price", "exit_price", "pnl_usd"):
        if col not in df.columns:
            return pd.DataFrame()
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df[
        df["exit_price"].notna() & df["pnl_usd"].notna() & df["entry_price"].notna()
    ].copy()


# ---------------------------------------------------------------------------
# Parameter performance
# ---------------------------------------------------------------------------

def _group_stats(series_pnl: pd.Series, series_win: pd.Series) -> dict | None:
    n = len(series_pnl)
    if n == 0:
        return None
    wins = int(series_win.sum())
    losses = n - wins
    wr = wins / n if n else 0
    avg_pnl = float(series_pnl.mean())
    win_pnls = series_pnl[series_win]
    loss_pnls = series_pnl[~series_win]
    avg_win = float(win_pnls.mean()) if len(win_pnls) > 0 else 0
    avg_loss = float(loss_pnls.mean()) if len(loss_pnls) > 0 else 0
    expectancy = avg_win * wr + avg_loss * (1 - wr)
    return {
        "count": n,
        "wins": wins,
        "losses": losses,
        "win_rate": round(wr, 3),
        "avg_pnl": round(avg_pnl, 2),
        "expectancy": round(expectancy, 3),
    }


def parameter_performance(closed_trades_df: pd.DataFrame) -> dict:
    """Group closed trades by entry_type, strategy_regime, and score bucket.

    Returns dict with keys 'by_entry_type', 'by_regime', 'by_score_bucket',
    each mapping group name to stats dict.
    """
    result: dict = {"by_entry_type": {}, "by_regime": {}, "by_score_bucket": {}}
    if closed_trades_df is None or closed_trades_df.empty:
        return result

    df = closed_trades_df.copy()
    df["pnl_usd"] = pd.to_numeric(df.get("pnl_usd"), errors="coerce").fillna(0)
    df["win"] = df["pnl_usd"] > 0

    if "entry_type" in df.columns:
        for name, grp in df.groupby("entry_type", dropna=True):
            s = _group_stats(grp["pnl_usd"], grp["win"])
            if s:
                result["by_entry_type"][str(name)] = s

    if "strategy_regime" in df.columns:
        for name, grp in df.groupby("strategy_regime", dropna=True):
            s = _group_stats(grp["pnl_usd"], grp["win"])
            if s:
                result["by_regime"][str(name)] = s

    if "confluence_score" in df.columns:
        df["_score"] = pd.to_numeric(df["confluence_score"], errors="coerce")
        df["_bucket"] = (df["_score"] // 10 * 10).astype("Int64")
        for name, grp in df.groupby("_bucket", dropna=True):
            label = f"{int(name)}-{int(name) + 9}"
            s = _group_stats(grp["pnl_usd"], grp["win"])
            if s:
                result["by_score_bucket"][label] = s

    return result


# ---------------------------------------------------------------------------
# Operator metrics
# ---------------------------------------------------------------------------

def operator_metrics(
    decisions: list[dict] | pd.DataFrame | None,
    trades_df: pd.DataFrame | None,
    config: dict,
    *,
    lookback_days: int = 7,
) -> dict:
    """Compute operational metrics: win_rate, avg_trade_time, pnl_per_hour, etc."""
    out: dict = {
        "max_trades_per_day": int(((config.get("risk") or {}).get("max_trades_per_day", 0) or 0)),
        "max_losses_per_day": int(((config.get("risk") or {}).get("max_losses_per_day", 0) or 0)),
        "avg_trades_per_day": None,
        "avg_time_in_trade_min": None,
        "median_time_in_trade_min": None,
        "avg_wait_between_entries_min": None,
        "pnl_per_trade_hour": None,
        "avg_pnl_per_closed_trade": None,
        "ready_cycle_pct": None,
        "entry_cycles": 0,
        "closed_trades": 0,
        "win_rate": None,
        "total_trades": 0,
    }

    # Convert decisions list[dict] to DataFrame if needed.
    decisions_df: pd.DataFrame | None = None
    if isinstance(decisions, pd.DataFrame):
        decisions_df = decisions
    elif isinstance(decisions, list) and decisions:
        try:
            decisions_df = pd.DataFrame(decisions)
        except Exception:
            decisions_df = None

    if decisions_df is not None and not decisions_df.empty:
        d = decisions_df.copy()
        if "timestamp" in d.columns:
            d["timestamp"] = pd.to_datetime(d["timestamp"], utc=True, errors="coerce")
            d = d.dropna(subset=["timestamp"])
        if not d.empty:
            total = len(d)
            ready = d
            if "gates_pass" in ready.columns:
                ready = ready[ready["gates_pass"] == True]  # noqa: E712
            if "entry_signal" in ready.columns:
                ready = ready[ready["entry_signal"].notna()]
            out["entry_cycles"] = int(len(ready))
            if total > 0:
                out["ready_cycle_pct"] = float(len(ready) / total * 100.0)

    if trades_df is None or trades_df.empty:
        return out

    t = trades_df.copy()
    if "timestamp" in t.columns:
        t["timestamp"] = pd.to_datetime(t["timestamp"], utc=True, errors="coerce")
    for c in ("entry_time", "exit_time"):
        if c in t.columns:
            t[c] = pd.to_datetime(t[c], utc=True, errors="coerce")
    if "entry_price" in t.columns:
        t["entry_price"] = pd.to_numeric(t["entry_price"], errors="coerce")
    if "exit_price" in t.columns:
        t["exit_price"] = pd.to_numeric(t["exit_price"], errors="coerce")
    if "pnl_usd" in t.columns:
        t["pnl_usd"] = pd.to_numeric(t["pnl_usd"], errors="coerce")
    if "time_in_trade_min" in t.columns:
        t["time_in_trade_min"] = pd.to_numeric(t["time_in_trade_min"], errors="coerce")
    else:
        t["time_in_trade_min"] = pd.NA

    # Entry rows: rows without an exit price.
    entry_rows = t.copy()
    if "exit_price" in entry_rows.columns:
        entry_rows = entry_rows[entry_rows["exit_price"].isna()]
    entry_rows = entry_rows.dropna(subset=["entry_price"])
    if "entry_time" in entry_rows.columns:
        entry_rows["entry_ts"] = entry_rows["entry_time"]
    elif "timestamp" in entry_rows.columns:
        entry_rows["entry_ts"] = entry_rows["timestamp"]
    else:
        entry_rows["entry_ts"] = pd.NaT
    entry_rows = entry_rows.dropna(subset=["entry_ts"]).sort_values("entry_ts")

    if not entry_rows.empty:
        by_day = entry_rows.groupby(entry_rows["entry_ts"].dt.date).size()
        if len(by_day) > 0:
            out["avg_trades_per_day"] = float(by_day.mean())
        if len(entry_rows) >= 2:
            waits = entry_rows["entry_ts"].diff().dropna().dt.total_seconds() / 60.0
            waits = waits[waits >= 0]
            if len(waits) > 0:
                out["avg_wait_between_entries_min"] = float(waits.mean())

    # Closed trades.
    closed = t.copy()
    if "exit_price" in closed.columns:
        closed = closed[closed["exit_price"].notna()]
    if "pnl_usd" in closed.columns:
        closed = closed[closed["pnl_usd"].notna()]
    out["closed_trades"] = int(len(closed))
    out["total_trades"] = int(len(t))
    if closed.empty:
        return out

    # Win rate.
    if "pnl_usd" in closed.columns:
        wins = int((closed["pnl_usd"] > 0).sum())
        out["win_rate"] = round(wins / len(closed) * 100, 1) if len(closed) > 0 else None

    # Backfill time-in-trade when missing.
    try:
        missing = closed["time_in_trade_min"].isna()
        if missing.any() and "entry_time" in closed.columns and "exit_time" in closed.columns:
            delta = (
                closed.loc[missing, "exit_time"] - closed.loc[missing, "entry_time"]
            ).dt.total_seconds() / 60.0
            closed.loc[missing, "time_in_trade_min"] = delta
    except Exception:
        pass

    dur = pd.to_numeric(closed["time_in_trade_min"], errors="coerce")
    dur = dur[dur.notna() & (dur >= 0)]
    if len(dur) > 0:
        out["avg_time_in_trade_min"] = float(dur.mean())
        out["median_time_in_trade_min"] = float(dur.median())
        hours = float(dur.sum()) / 60.0
        if hours > 0 and "pnl_usd" in closed.columns:
            out["pnl_per_trade_hour"] = float(closed["pnl_usd"].sum() / hours)
    if "pnl_usd" in closed.columns and len(closed) > 0:
        out["avg_pnl_per_closed_trade"] = float(closed["pnl_usd"].mean())

    return out
