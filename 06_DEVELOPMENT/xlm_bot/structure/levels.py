from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Tuple

import pandas as pd


def _period_high_low(df: pd.DataFrame, freq: str) -> pd.DataFrame:
    out = df.copy()
    # Drop tz info to avoid noisy PeriodArray warnings
    out["period"] = out["timestamp"].dt.tz_localize(None).dt.to_period(freq)
    hl = out.groupby("period").agg(high=("high", "max"), low=("low", "min"))
    hl = hl.reset_index()
    return hl


def compute_structure_levels(df: pd.DataFrame) -> Dict[str, Tuple[float, float]]:
    if df.empty:
        return {}
    out = {}
    for label, freq in [
        ("yearly", "Y"),
        ("monthly", "M"),
        ("weekly", "W"),
        ("daily", "D"),
    ]:
        hl = _period_high_low(df, freq)
        if hl.empty:
            continue
        current = hl.iloc[-1]
        out[f"{label}_high"] = float(current["high"])
        out[f"{label}_low"] = float(current["low"])
        if len(hl) >= 2:
            prev = hl.iloc[-2]
            out[f"prev_{label}_high"] = float(prev["high"])
            out[f"prev_{label}_low"] = float(prev["low"])
    return out


def nearest_level(price: float, levels: Dict[str, float]) -> Tuple[str, float]:
    best_name = ""
    best_dist = float("inf")
    for name, lvl in levels.items():
        dist = abs(price - lvl)
        if dist < best_dist:
            best_dist = dist
            best_name = name
    return best_name, best_dist


def level_breakout(price: float, levels: Dict[str, float], direction: str) -> bool:
    if direction == "long":
        return any(price > lvl for lvl in levels.values())
    return any(price < lvl for lvl in levels.values())
