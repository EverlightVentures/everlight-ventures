from __future__ import annotations

from datetime import datetime, time
from typing import Dict, Tuple

import pandas as pd

from indicators.atr import atr


def atr_regime_gate(df_1h: pd.DataFrame, multiplier: float) -> bool:
    if df_1h.empty or len(df_1h) < 40:
        return False
    atr14 = atr(df_1h, 14)
    recent = atr14.iloc[-1]
    mean20 = atr14.rolling(20).mean().iloc[-1]
    if pd.isna(recent) or pd.isna(mean20):
        return False
    return recent > multiplier * mean20


def session_gate(now: datetime, windows: list[dict]) -> bool:
    if not windows:
        return True
    t = now.time()
    for w in windows:
        start_raw = w["start"]
        end_raw = w["end"]
        if isinstance(start_raw, int):
            start = time(hour=start_raw // 60, minute=start_raw % 60)
        else:
            start = start_raw if isinstance(start_raw, time) else time.fromisoformat(str(start_raw))
        if isinstance(end_raw, int):
            end = time(hour=end_raw // 60, minute=end_raw % 60)
        else:
            end = end_raw if isinstance(end_raw, time) else time.fromisoformat(str(end_raw))
        if start <= t <= end:
            return True
    return False


def distance_from_value_gate(price: float, ema21_1h: float, atr_1h: float, mult: float,
                              breakout_mult: float = 0.0, atr_expanding: bool = False) -> bool:
    if ema21_1h <= 0 or atr_1h <= 0:
        return False
    effective_mult = breakout_mult if (atr_expanding and breakout_mult > mult) else mult
    return abs(price - ema21_1h) <= effective_mult * atr_1h


def spread_gate(spread_estimate: float, max_pct: float) -> bool:
    if spread_estimate < 0:
        return False
    return spread_estimate <= max_pct


def run_regime_gates(
    df_1h: pd.DataFrame,
    price: float,
    ema21_1h: float,
    spread_estimate: float,
    config: dict,
    now: datetime,
) -> Dict[str, bool]:
    gates = {}
    gates["atr_regime"] = atr_regime_gate(df_1h, config["regime_gates"]["atr_multiplier"])
    gates["session"] = session_gate(now, config["session_filter"]["windows"] if config["session_filter"]["enabled"] else [])
    atr_1h_series = atr(df_1h, 14) if not df_1h.empty else pd.Series(dtype=float)
    atr_1h = float(atr_1h_series.iloc[-1]) if len(atr_1h_series) > 0 and not pd.isna(atr_1h_series.iloc[-1]) else 0.0
    # Detect 1h ATR expansion: current ATR > 1.15x its 20-bar mean
    atr_1h_expanding = False
    if len(atr_1h_series) >= 20:
        atr_1h_mean20 = atr_1h_series.rolling(20).mean().iloc[-1]
        if not pd.isna(atr_1h_mean20) and atr_1h_mean20 > 0:
            atr_1h_expanding = atr_1h > 1.15 * atr_1h_mean20
    breakout_mult = float(config["regime_gates"].get("distance_from_value_breakout_mult", 4.0))
    gates["distance_from_value"] = distance_from_value_gate(
        price, ema21_1h, float(atr_1h),
        config["regime_gates"]["distance_from_value_atr_mult"],
        breakout_mult=breakout_mult,
        atr_expanding=atr_1h_expanding,
    )
    gates["spread"] = spread_gate(spread_estimate, config["regime_gates"]["spread_max_pct"])
    return gates


def compute_route_tier(gates: Dict[str, bool], config: dict) -> str:
    """Determine gate routing tier.

    Returns:
        "full"    – all gates pass, all lanes available
        "reduced" – ATR or distance fails but spread+session pass → C/E/reversal only
        "blocked" – spread or session fails → no entry
    """
    gate_routing = bool(config.get("regime_gates", {}).get("gate_routing", False))
    if not gate_routing:
        # Legacy mode: all must pass or it's blocked
        return "full" if all(gates.values()) else "blocked"

    # Hard gates: spread and session must always pass
    if not gates.get("spread", False) or not gates.get("session", True):
        return "blocked"

    # If all pass, full access
    if all(gates.values()):
        return "full"

    # Soft fail: ATR or distance failed but hard gates pass → reduced
    return "reduced"
