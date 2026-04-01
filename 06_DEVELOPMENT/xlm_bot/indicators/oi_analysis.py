"""Open Interest Rate of Change analysis.

Tracks OI changes over time from contract_context.jsonl.
OI rising + price rising = new money, bullish
OI rising + price flat = accumulation, breakout coming
OI falling + price falling = capitulation, reversal near
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional


def oi_roc(oi_history: list[float], window: int = 12) -> tuple[float, str]:
    """Rate of change of Open Interest.

    Returns: (roc float, signal str).
    Signal: 'rising', 'falling', or 'flat'.
    """
    if not oi_history or len(oi_history) < window:
        return 0.0, "insufficient_data"
    past = oi_history[-window]
    current = oi_history[-1]
    if past == 0:
        return 0.0, "flat"
    roc = (current - past) / past
    if roc > 0.02:
        signal = "rising"
    elif roc < -0.02:
        signal = "falling"
    else:
        signal = "flat"
    return round(roc, 6), signal


def oi_price_divergence(
    oi_history: list[float],
    price_history: list[float],
    window: int = 12,
) -> dict:
    """Detect OI vs price divergences.

    Returns dict with oi_roc, price_roc, divergence type, and signal strength.
    """
    if len(oi_history) < window or len(price_history) < window:
        return {"oi_roc": 0.0, "price_roc": 0.0, "divergence": "insufficient_data", "strength": 0}

    oi_past = oi_history[-window]
    oi_now = oi_history[-1]
    p_past = price_history[-window]
    p_now = price_history[-1]

    oi_change = (oi_now - oi_past) / oi_past if oi_past != 0 else 0.0
    p_change = (p_now - p_past) / p_past if p_past != 0 else 0.0

    # Classify
    if oi_change > 0.02 and p_change > 0.005:
        div = "bullish_new_money"
        strength = 5
    elif oi_change > 0.02 and abs(p_change) <= 0.005:
        div = "accumulation"
        strength = 3
    elif oi_change < -0.02 and p_change < -0.005:
        div = "capitulation"
        strength = 4
    elif oi_change < -0.02 and p_change > 0.005:
        div = "short_squeeze"
        strength = 5
    elif oi_change > 0.02 and p_change < -0.005:
        div = "distribution"
        strength = 4
    else:
        div = "neutral"
        strength = 0

    return {
        "oi_roc": round(oi_change, 6),
        "price_roc": round(p_change, 6),
        "divergence": div,
        "strength": strength,
    }


def extract_oi_history(contract_history_path: Path, max_entries: int = 200) -> list[float]:
    """Extract OI history from contract_context.jsonl.
    Returns list of open_interest values (most recent last)."""
    history: list[float] = []
    if not contract_history_path.exists():
        return history
    try:
        lines: list[str] = []
        with open(contract_history_path, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    lines.append(line)
        for line in lines[-max_entries:]:
            try:
                d = json.loads(line)
                oi = d.get("open_interest")
                if oi is not None:
                    history.append(float(oi))
            except Exception:
                continue
    except Exception:
        pass
    return history


def extract_price_history(contract_history_path: Path, max_entries: int = 200) -> list[float]:
    """Extract mark price history from contract_context.jsonl."""
    history: list[float] = []
    if not contract_history_path.exists():
        return history
    try:
        lines: list[str] = []
        with open(contract_history_path, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    lines.append(line)
        for line in lines[-max_entries:]:
            try:
                d = json.loads(line)
                price = d.get("mark_price")
                if price is not None:
                    history.append(float(price))
            except Exception:
                continue
    except Exception:
        pass
    return history
