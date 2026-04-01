"""Funding Rate Slope indicator.

Tracks funding rate history and computes linear regression slope.
Rising funding = longs piling in (dangerous for longs).
Falling funding = shorts piling in (dangerous for shorts).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional


def funding_slope(funding_history: list[float], window: int = 12) -> float:
    """Linear regression slope of last N funding readings.
    Positive slope = longs increasing. Negative = shorts increasing.
    Returns 0.0 if insufficient data."""
    if not funding_history or len(funding_history) < 3:
        return 0.0
    import numpy as np
    y = np.array(funding_history[-window:], dtype=float)
    x = np.arange(len(y), dtype=float)
    if len(y) < 2:
        return 0.0
    try:
        slope = float(np.polyfit(x, y, 1)[0])
    except (np.linalg.LinAlgError, ValueError):
        slope = 0.0
    return slope


def funding_slope_signal(slope: float, direction: str, threshold: float = 0.0001) -> str:
    """Classify whether funding slope helps or hurts the trade direction.
    Returns: 'favorable', 'against', or 'neutral'."""
    if abs(slope) < threshold:
        return "neutral"
    if direction == "long":
        return "against" if slope > threshold else "favorable"
    elif direction == "short":
        return "against" if slope < -threshold else "favorable"
    return "neutral"


def extract_funding_history(contract_history_path: Path, max_entries: int = 200) -> list[float]:
    """Extract funding rate history from contract_context.jsonl.
    Returns list of funding_rate_hr values (most recent last)."""
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
                rate = d.get("funding_rate_hr")
                if rate is not None:
                    history.append(float(rate))
            except Exception:
                continue
    except Exception:
        pass
    return history
