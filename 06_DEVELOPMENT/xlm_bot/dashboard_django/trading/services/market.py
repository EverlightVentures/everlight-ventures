"""
Market service -- equity series, trade markers, and operator metrics wrapper.

Provides data for charting (Lightweight Charts) and summary panels.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
from django.conf import settings
from django.core.cache import cache

from .file_reader import file_sig
from .formatters import safe_float

LOGS_DIR: Path = settings.XLM_LOGS_DIR
EQUITY_SERIES_PATH = LOGS_DIR / "equity_series.jsonl"


# ---------------------------------------------------------------------------
# Equity series
# ---------------------------------------------------------------------------

def load_equity_series(hours: float | None = None) -> list[dict]:
    """Load equity_series.jsonl and optionally filter by time window.

    Returns list of ``{time, value}`` dicts suitable for Lightweight Charts.
    ``time`` is a UTC epoch int; ``value`` is a float.
    """
    sig = file_sig(EQUITY_SERIES_PATH)
    key = f"eqseries_{sig[0]}_{sig[1]}_{hours}"
    cached = cache.get(key)
    if cached is not None:
        return cached

    result: list[dict] = []
    try:
        if not EQUITY_SERIES_PATH.exists():
            cache.set(key, result, timeout=60)
            return result
        lines = EQUITY_SERIES_PATH.read_text(errors="ignore").strip().splitlines()
        if not lines:
            cache.set(key, result, timeout=60)
            return result

        cutoff = None
        if hours is not None:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

        for line in lines:
            try:
                row = json.loads(line)
                ts_str = row.get("ts", "")
                ts = datetime.fromisoformat(ts_str)
                if cutoff and ts < cutoff:
                    continue
                # Lightweight Charts expects {time: epoch_int, value: float}.
                result.append({
                    "time": int(ts.timestamp()),
                    "value": float(row.get("equity") or row.get("value") or 0),
                })
            except Exception:
                continue
    except Exception:
        result = []

    cache.set(key, result, timeout=60)
    return result


# ---------------------------------------------------------------------------
# Operator metrics (thin wrapper)
# ---------------------------------------------------------------------------

def operator_metrics(
    decisions: list[dict] | pd.DataFrame | None,
    trades_df: pd.DataFrame | None,
    config: dict,
) -> dict:
    """Convenience wrapper that delegates to analytics.operator_metrics."""
    from .analytics import operator_metrics as _op_metrics
    return _op_metrics(decisions, trades_df, config)


# ---------------------------------------------------------------------------
# Trade markers for chart overlay
# ---------------------------------------------------------------------------

def build_trade_markers(trades_df: pd.DataFrame | None, hours: float | None = None) -> list[dict]:
    """Build Lightweight Charts marker list from trades DataFrame.

    Returns list of dicts with keys: time, position, color, shape, text.
    """
    markers: list[dict] = []
    try:
        if trades_df is None or trades_df.empty:
            return []

        cutoff = None
        if hours is not None:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

        for _, row in trades_df.iterrows():
            # Entry marker.
            entry_time = row.get("entry_time") or row.get("timestamp")
            if entry_time:
                try:
                    et = pd.to_datetime(entry_time, utc=True)
                    if cutoff and et < cutoff:
                        continue
                    side = str(row.get("side", "")).lower()
                    entry_px = float(row.get("entry_price") or 0)
                    if entry_px > 0:
                        markers.append({
                            "time": int(et.timestamp()),
                            "position": "belowBar" if side == "long" else "aboveBar",
                            "color": "#10b981" if side == "long" else "#ef4444",
                            "shape": "arrowUp" if side == "long" else "arrowDown",
                            "text": f"{'L' if side == 'long' else 'S'} ${entry_px:.5f}",
                        })
                except Exception:
                    pass

            # Exit marker.
            exit_time = row.get("exit_time")
            exit_reason = str(row.get("exit_reason", "") or "")
            exit_px = row.get("exit_price")
            if exit_time and exit_px:
                try:
                    xt = pd.to_datetime(exit_time, utc=True)
                    if cutoff and xt < cutoff:
                        continue
                    pnl = float(row.get("pnl_usd") or 0)
                    is_tp = "tp" in exit_reason.lower()
                    is_sl = "stop" in exit_reason.lower() or "sl" in exit_reason.lower()
                    if is_tp:
                        color = "#10b981"
                    elif is_sl:
                        color = "#ef4444"
                    elif pnl >= 0:
                        color = "#fbbf24"
                    else:
                        color = "#ef4444"
                    label = exit_reason.upper()[:6]
                    if pnl != 0:
                        label += f" {'+'if pnl > 0 else ''}${pnl:.2f}"
                    markers.append({
                        "time": int(xt.timestamp()),
                        "position": "aboveBar",
                        "color": color,
                        "shape": "circle",
                        "text": label,
                    })
                except Exception:
                    pass
    except Exception:
        pass

    return sorted(markers, key=lambda m: m.get("time", 0))
