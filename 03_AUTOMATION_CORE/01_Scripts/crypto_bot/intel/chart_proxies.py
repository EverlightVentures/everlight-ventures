#!/usr/bin/env python3
"""
Chart-derived liquidation proxies and magnet levels.
Uses only candles (no external dependencies).
"""

from __future__ import annotations

import time
import math
from typing import Dict, List, Optional


def _sma(values: List[float], period: int) -> Optional[float]:
    if not values or len(values) < period:
        return None
    return sum(values[-period:]) / period


def _range(candle: dict) -> float:
    return float(candle["high"]) - float(candle["low"])


def _body(candle: dict) -> float:
    return abs(float(candle["close"]) - float(candle["open"]))


def _merge_levels(levels: List[dict], tolerance_pct: float = 0.2) -> List[dict]:
    levels = sorted(levels, key=lambda x: x["price"])
    merged: List[dict] = []
    for lvl in levels:
        if not merged:
            merged.append(lvl)
            continue
        last = merged[-1]
        dist_pct = abs(lvl["price"] - last["price"]) / max(last["price"], 1e-9) * 100
        if dist_pct <= tolerance_pct:
            last["strength"] = max(last["strength"], lvl["strength"])
            last["label"] = f"{last['label']}+{lvl['label']}"
        else:
            merged.append(lvl)
    return merged


def forced_move_proxy(candles: List[dict], lookback: int = 30) -> dict:
    if not candles or len(candles) < max(lookback, 10):
        return {
            "ok": False,
            "source": "proxy",
            "timestamp": time.time(),
            "liq_event_score": None,
            "liq_bias": "NONE",
            "notes": ["Not enough candles for forced-move proxy"],
        }

    recent = candles[-lookback:]
    ranges = [_range(c) / max(float(c["close"]), 1e-9) for c in recent]
    bodies = [_body(c) / max(float(c["close"]), 1e-9) for c in recent]
    volumes = [float(c.get("volume", 0)) for c in recent]

    r_sma = _sma(ranges, min(20, len(ranges)))
    v_sma = _sma(volumes, min(20, len(volumes)))

    last = recent[-1]
    last_range = _range(last) / max(float(last["close"]), 1e-9)
    last_body = _body(last) / max(float(last["close"]), 1e-9)
    wick_ratio = (last_range - last_body) / max(last_range, 1e-9)

    range_spike = (last_range / max(r_sma, 1e-9)) if r_sma else 0
    volume_spike = (float(last.get("volume", 0)) / max(v_sma, 1e-9)) if v_sma else 0

    score = 0.0
    notes: List[str] = []

    if volume_spike >= 2.0 and range_spike >= 1.8 and (last_body / max(last_range, 1e-9)) >= 0.55:
        score = 0.85
        notes.append("Continuation squeeze proxy")
    elif volume_spike >= 2.0 and wick_ratio >= 0.55:
        score = 0.7
        notes.append("Stop-hunt wick proxy")
    else:
        score = min(0.5, max(0.0, (range_spike + volume_spike) / 6))

    # Bias based on candle direction
    liq_bias = "NONE"
    if float(last["close"]) > float(last["open"]):
        liq_bias = "SHORT_SQUEEZE"
    elif float(last["close"]) < float(last["open"]):
        liq_bias = "LONG_SQUEEZE"

    return {
        "ok": True,
        "source": "proxy",
        "timestamp": time.time(),
        "liq_event_score": round(score, 3),
        "liq_bias": liq_bias,
        "notes": notes,
    }


def magnet_proxy(candles: List[dict], max_levels: int = 10) -> dict:
    if not candles or len(candles) < 20:
        return {
            "ok": False,
            "source": "proxy",
            "timestamp": time.time(),
            "magnet_levels": [],
            "nearest_magnet_distance_pct": None,
            "notes": ["Not enough candles for magnet proxy"],
        }

    levels: List[dict] = []
    closes = [float(c["close"]) for c in candles]
    highs = [float(c["high"]) for c in candles]
    lows = [float(c["low"]) for c in candles]

    # Previous day high/low (approx last 24 candles if 1h)
    day_slice = candles[-24:] if len(candles) >= 24 else candles
    day_high = max(float(c["high"]) for c in day_slice)
    day_low = min(float(c["low"]) for c in day_slice)
    levels.append({"price": day_high, "strength": 0.6, "label": "prev_day_high"})
    levels.append({"price": day_low, "strength": 0.6, "label": "prev_day_low"})

    # Rolling 8h session high/low
    session = candles[-8:] if len(candles) >= 8 else candles
    session_high = max(float(c["high"]) for c in session)
    session_low = min(float(c["low"]) for c in session)
    levels.append({"price": session_high, "strength": 0.4, "label": "session_high"})
    levels.append({"price": session_low, "strength": 0.4, "label": "session_low"})

    # Swing highs/lows (fractals)
    for i in range(2, len(highs) - 2):
        if highs[i] > highs[i - 1] and highs[i] > highs[i - 2] and highs[i] > highs[i + 1] and highs[i] > highs[i + 2]:
            levels.append({"price": highs[i], "strength": 0.5, "label": "swing_high"})
        if lows[i] < lows[i - 1] and lows[i] < lows[i - 2] and lows[i] < lows[i + 1] and lows[i] < lows[i + 2]:
            levels.append({"price": lows[i], "strength": 0.5, "label": "swing_low"})

    merged = _merge_levels(levels)
    merged = sorted(merged, key=lambda x: x["strength"], reverse=True)[:max_levels]

    current_price = closes[-1]
    nearest = None
    nearest_dist = None
    for lvl in merged:
        dist = abs(lvl["price"] - current_price) / max(current_price, 1e-9) * 100
        if nearest_dist is None or dist < nearest_dist:
            nearest = lvl
            nearest_dist = dist

    return {
        "ok": True,
        "source": "proxy",
        "timestamp": time.time(),
        "magnet_levels": merged,
        "nearest_magnet_distance_pct": round(nearest_dist, 4) if nearest_dist is not None else None,
        "notes": [],
    }
