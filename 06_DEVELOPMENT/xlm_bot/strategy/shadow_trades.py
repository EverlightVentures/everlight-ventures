"""Shadow Trade Tracker -- tracks blocked trades to learn from hindsight.

Every time the unified scorer says ENTER but a downstream gate blocks it,
we log a "shadow trade" with the entry price, direction, strategy, score,
and block reason. Each cycle, we check open shadows against current price
to see if the trade would have been profitable.

This gives the bot EVIDENCE for whether its blocks are helping or hurting.
Over time, the bot can learn: "range_guard blocked 20 shorts, 15 would
have won -- maybe loosen the guard" or "rr_ratio blocked 30 trades,
25 would have lost -- good filter."
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


@dataclass
class ShadowTrade:
    timestamp: str = ""
    direction: str = ""
    entry_price: float = 0.0
    entry_type: str = ""
    score: int = 0
    threshold: int = 60
    quality_tier: str = ""
    block_reason: str = ""
    # Tracked outcomes
    peak_favorable: float = 0.0  # best price in our favor
    peak_adverse: float = 0.0    # worst price against us
    price_15m: float = 0.0
    price_30m: float = 0.0
    price_60m: float = 0.0
    # Computed
    pnl_peak: float = 0.0       # PnL at peak favorable
    pnl_15m: float = 0.0
    pnl_30m: float = 0.0
    pnl_60m: float = 0.0
    would_have_won: bool = False
    closed: bool = False
    close_reason: str = ""


_SHADOW_FILE = "shadow_trades.jsonl"
_MAX_AGE_HOURS = 2  # track shadows for 2 hours max
_CS = 5000.0  # contract size


def _load_shadows(path: Path) -> list[dict]:
    try:
        if path.exists():
            shadows = []
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        shadows.append(json.loads(line))
            return shadows
    except Exception:
        pass
    return []


def _save_shadows(path: Path, shadows: list[dict]):
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            for s in shadows:
                f.write(json.dumps(s, default=str) + "\n")
    except Exception:
        pass


def log_shadow_trade(
    logs_dir: Path,
    *,
    timestamp: str,
    direction: str,
    entry_price: float,
    entry_type: str,
    score: int,
    threshold: int,
    quality_tier: str,
    block_reason: str,
) -> None:
    """Log a new shadow trade when a scored ENTER signal gets blocked."""
    path = logs_dir / _SHADOW_FILE
    shadows = _load_shadows(path)

    # Deduplicate: don't log same direction + price zone within 5 minutes
    for s in shadows[-10:]:
        if (s.get("direction") == direction
            and abs(s.get("entry_price", 0) - entry_price) < 0.0002
            and not s.get("closed")):
            return  # already tracking this one

    shadow = ShadowTrade(
        timestamp=timestamp,
        direction=direction,
        entry_price=entry_price,
        entry_type=entry_type,
        score=score,
        threshold=threshold,
        quality_tier=quality_tier,
        block_reason=block_reason,
    )
    shadows.append(asdict(shadow))
    _save_shadows(path, shadows)


def tick_shadows(logs_dir: Path, current_price: float, now_iso: str) -> list[dict]:
    """Update all open shadow trades with current price. Returns closed shadows for logging."""
    path = logs_dir / _SHADOW_FILE
    shadows = _load_shadows(path)
    if not shadows:
        return []

    from datetime import datetime, timezone, timedelta

    try:
        now = datetime.fromisoformat(now_iso.replace("Z", "+00:00"))
    except Exception:
        return []

    closed_this_tick = []

    for s in shadows:
        if s.get("closed"):
            continue

        entry = s.get("entry_price", 0)
        direction = s.get("direction", "")
        if entry <= 0 or not direction:
            s["closed"] = True
            s["close_reason"] = "invalid"
            continue

        # Calculate PnL
        if direction == "short":
            pnl = (entry - current_price) * _CS
            if current_price < s.get("peak_favorable", entry) or s.get("peak_favorable", 0) == 0:
                s["peak_favorable"] = current_price
            if current_price > s.get("peak_adverse", entry) or s.get("peak_adverse", 0) == 0:
                s["peak_adverse"] = current_price
        else:
            pnl = (current_price - entry) * _CS
            if current_price > s.get("peak_favorable", entry) or s.get("peak_favorable", 0) == 0:
                s["peak_favorable"] = current_price
            if current_price < s.get("peak_adverse", entry) or s.get("peak_adverse", 0) == 0:
                s["peak_adverse"] = current_price

        # Update PnL at peak
        if direction == "short":
            s["pnl_peak"] = round((entry - s["peak_favorable"]) * _CS, 2)
        else:
            s["pnl_peak"] = round((s["peak_favorable"] - entry) * _CS, 2)

        # Track price at intervals
        try:
            entry_dt = datetime.fromisoformat(s["timestamp"].replace("Z", "+00:00"))
            age_min = (now - entry_dt).total_seconds() / 60

            if age_min >= 15 and s.get("price_15m", 0) == 0:
                s["price_15m"] = current_price
                s["pnl_15m"] = round(pnl, 2)
            if age_min >= 30 and s.get("price_30m", 0) == 0:
                s["price_30m"] = current_price
                s["pnl_30m"] = round(pnl, 2)
            if age_min >= 60 and s.get("price_60m", 0) == 0:
                s["price_60m"] = current_price
                s["pnl_60m"] = round(pnl, 2)

            # Close after max age
            if age_min >= _MAX_AGE_HOURS * 60:
                s["closed"] = True
                s["close_reason"] = "max_age"
                # Would it have won? (peak PnL > $1.50 after fees)
                s["would_have_won"] = s.get("pnl_peak", 0) > 1.50
                closed_this_tick.append(dict(s))

            # Close if it would have hit stop ($6.60 loss)
            if pnl < -6.60:
                s["closed"] = True
                s["close_reason"] = "would_have_stopped"
                s["would_have_won"] = False
                closed_this_tick.append(dict(s))

            # Close if it would have hit TP ($3.30 profit)
            if pnl >= 3.30 and not s.get("closed"):
                s["closed"] = True
                s["close_reason"] = "would_have_tp"
                s["would_have_won"] = True
                closed_this_tick.append(dict(s))

        except Exception:
            pass

    _save_shadows(path, shadows)
    return closed_this_tick


def get_shadow_summary(logs_dir: Path) -> dict:
    """Get summary stats for dashboard display."""
    path = logs_dir / _SHADOW_FILE
    shadows = _load_shadows(path)

    total = len(shadows)
    closed = [s for s in shadows if s.get("closed")]
    active = [s for s in shadows if not s.get("closed")]
    winners = [s for s in closed if s.get("would_have_won")]
    losers = [s for s in closed if not s.get("would_have_won")]

    # Group by block reason
    by_reason = {}
    for s in closed:
        r = s.get("block_reason", "unknown")
        if r not in by_reason:
            by_reason[r] = {"total": 0, "wins": 0, "losses": 0, "pnl_sum": 0}
        by_reason[r]["total"] += 1
        if s.get("would_have_won"):
            by_reason[r]["wins"] += 1
            by_reason[r]["pnl_sum"] += min(s.get("pnl_peak", 0), 3.30) - 1.50
        else:
            by_reason[r]["losses"] += 1
            by_reason[r]["pnl_sum"] += max(s.get("pnl_peak", 0), -6.60) - 1.50

    return {
        "total_shadows": total,
        "active": len(active),
        "closed": len(closed),
        "would_have_won": len(winners),
        "would_have_lost": len(losers),
        "win_rate": round(len(winners) / max(len(closed), 1) * 100, 1),
        "by_block_reason": by_reason,
        "active_trades": [
            {
                "direction": s.get("direction"),
                "entry_price": s.get("entry_price"),
                "entry_type": s.get("entry_type"),
                "score": s.get("score"),
                "block_reason": s.get("block_reason"),
                "pnl_peak": s.get("pnl_peak", 0),
                "timestamp": s.get("timestamp", "")[-8:],
            }
            for s in active[-10:]
        ],
    }
