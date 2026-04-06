"""Shadow System -- the bot's intuition engine.

Tracks parallel-universe versions of every decision to build hindsight.
All shadow data is 100% SEPARATE from real trades. Never touches trades.csv,
events table, or PnL calculations. Shadow data lives in its own directory.

Shadow Types:
  ENTRY   - blocked entries: what would have happened if we entered?
  EXIT    - after every exit: did we leave money on the table?
  ALT     - alternative strategies: which strategy would have been best?
  FLIP    - direction shadow: what would the opposite direction have done?
  REENTRY - after exit: when was the optimal re-entry point?

Each shadow tracks price for up to 2 hours with 5m/15m/30m/60m snapshots.
Shadows are categorized by strategy and block reason for per-strategy learning.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

_CS = 5000.0  # contract size for XLP perps
_MAX_AGE_MIN = 120  # track for 2 hours
_TP_TARGET = 3.30   # realistic TP
_SL_LIMIT = -6.60   # realistic SL
_FEE = 1.50         # round-trip fees


def _shadow_dir(logs_dir: Path) -> Path:
    d = logs_dir / "shadows"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _load_file(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        with open(path) as f:
            return [json.loads(line) for line in f if line.strip()]
    except Exception:
        return []


def _save_file(path: Path, items: list[dict]):
    try:
        with open(path, "w") as f:
            for item in items:
                f.write(json.dumps(item, default=str) + "\n")
    except Exception:
        pass


def _calc_pnl(direction: str, entry: float, current: float) -> float:
    if direction == "short":
        return (entry - current) * _CS
    return (current - entry) * _CS


def _age_minutes(ts_str: str, now: datetime) -> float:
    try:
        dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        return (now - dt).total_seconds() / 60
    except Exception:
        return 9999


# =====================================================================
# ENTRY SHADOW -- blocked entries
# =====================================================================

def log_entry_shadow(
    logs_dir: Path, *,
    timestamp: str, direction: str, entry_price: float,
    entry_type: str, score: int, threshold: int,
    quality_tier: str, block_reason: str,
):
    """Log a blocked entry as a shadow trade."""
    path = _shadow_dir(logs_dir) / "entry_shadows.jsonl"
    shadows = _load_file(path)

    # Deduplicate: same direction + zone within 3 minutes
    for s in shadows[-10:]:
        if (not s.get("closed")
            and s.get("direction") == direction
            and abs(s.get("entry_price", 0) - entry_price) < 0.0002):
            return

    shadow = {
        "type": "ENTRY",
        "timestamp": timestamp,
        "direction": direction,
        "entry_price": entry_price,
        "entry_type": entry_type,
        "score": score,
        "threshold": threshold,
        "quality_tier": quality_tier,
        "block_reason": block_reason,
        "peak_pnl": 0.0,
        "worst_pnl": 0.0,
        "price_5m": 0.0, "price_15m": 0.0, "price_30m": 0.0, "price_60m": 0.0,
        "pnl_5m": 0.0, "pnl_15m": 0.0, "pnl_30m": 0.0, "pnl_60m": 0.0,
        "would_have_won": False,
        "closed": False,
        "close_reason": "",
    }
    shadows.append(shadow)
    _save_file(path, shadows)


# =====================================================================
# EXIT SHADOW -- track price after every real exit
# =====================================================================

def log_exit_shadow(
    logs_dir: Path, *,
    timestamp: str, direction: str, exit_price: float,
    exit_reason: str, entry_type: str, pnl_at_exit: float,
    quality_tier: str, hold_minutes: float,
):
    """After a real exit, track what price does next. Did we leave money?"""
    path = _shadow_dir(logs_dir) / "exit_shadows.jsonl"
    shadows = _load_file(path)

    shadow = {
        "type": "EXIT",
        "timestamp": timestamp,
        "direction": direction,
        "exit_price": exit_price,
        "exit_reason": exit_reason,
        "entry_type": entry_type,
        "pnl_at_exit": round(pnl_at_exit, 2),
        "quality_tier": quality_tier,
        "hold_minutes": round(hold_minutes, 1),
        # Track what happens AFTER exit (same direction -- did we exit too early?)
        "continued_peak_pnl": 0.0,  # how much more we could have made
        "continued_worst_pnl": 0.0, # how much we avoided by exiting
        "price_5m": 0.0, "price_15m": 0.0, "price_30m": 0.0, "price_60m": 0.0,
        "exited_too_early": False,  # True if holding would have made $2+ more
        "exited_too_late": False,   # True if price reversed $2+ in our favor after
        "optimal_exit_pnl": 0.0,   # best PnL achievable in the 60min after entry
        "closed": False,
    }
    shadows.append(shadow)
    _save_file(path, shadows)


# =====================================================================
# ALT SHADOW -- alternative strategies at time of entry
# =====================================================================

def log_alt_shadow(
    logs_dir: Path, *,
    timestamp: str, chosen_type: str, chosen_direction: str,
    chosen_score: int, alternatives: list[dict],
):
    """When entering a trade, log what other strategies scored."""
    path = _shadow_dir(logs_dir) / "alt_shadows.jsonl"
    shadows = _load_file(path)

    shadow = {
        "type": "ALT",
        "timestamp": timestamp,
        "chosen_type": chosen_type,
        "chosen_direction": chosen_direction,
        "chosen_score": chosen_score,
        "alternatives": alternatives,  # [{name, direction, score, normalized}]
        "chosen_outcome": None,  # filled when real trade closes
        "closed": False,
    }
    shadows.append(shadow)
    _save_file(path, shadows)


# =====================================================================
# FLIP SHADOW -- opposite direction at time of entry
# =====================================================================

def log_flip_shadow(
    logs_dir: Path, *,
    timestamp: str, actual_direction: str, entry_price: float,
    entry_type: str, score: int,
    opposite_score: int,
):
    """Track what the opposite direction would have done."""
    path = _shadow_dir(logs_dir) / "flip_shadows.jsonl"
    shadows = _load_file(path)

    opp_dir = "long" if actual_direction == "short" else "short"
    shadow = {
        "type": "FLIP",
        "timestamp": timestamp,
        "actual_direction": actual_direction,
        "opposite_direction": opp_dir,
        "entry_price": entry_price,
        "entry_type": entry_type,
        "actual_score": score,
        "opposite_score": opposite_score,
        "opposite_peak_pnl": 0.0,
        "opposite_pnl_30m": 0.0,
        "opposite_would_have_won": False,
        "price_5m": 0.0, "price_15m": 0.0, "price_30m": 0.0,
        "closed": False,
    }
    shadows.append(shadow)
    _save_file(path, shadows)


# =====================================================================
# REENTRY SHADOW -- after exit, when was optimal re-entry?
# =====================================================================

def log_reentry_shadow(
    logs_dir: Path, *,
    timestamp: str, last_direction: str, exit_price: float,
    exit_reason: str,
):
    """After exit, track when the best re-entry would have been."""
    path = _shadow_dir(logs_dir) / "reentry_shadows.jsonl"
    shadows = _load_file(path)

    shadow = {
        "type": "REENTRY",
        "timestamp": timestamp,
        "last_direction": last_direction,
        "exit_price": exit_price,
        "exit_reason": exit_reason,
        # Track optimal re-entry for SAME direction (continuation)
        "best_reentry_price_same": 0.0,
        "best_reentry_time_same": "",
        "best_reentry_pnl_same": 0.0,
        # Track optimal re-entry for OPPOSITE direction (reversal)
        "best_reentry_price_opp": 0.0,
        "best_reentry_time_opp": "",
        "best_reentry_pnl_opp": 0.0,
        "price_5m": 0.0, "price_15m": 0.0, "price_30m": 0.0,
        "closed": False,
    }
    shadows.append(shadow)
    _save_file(path, shadows)


# =====================================================================
# TICK ALL SHADOWS -- called every cycle with current price
# =====================================================================

def tick_all_shadows(logs_dir: Path, price: float, now_iso: str) -> list[dict]:
    """Update all open shadows with current price. Returns newly closed ones."""
    try:
        now = datetime.fromisoformat(now_iso.replace("Z", "+00:00"))
    except Exception:
        return []

    closed_events = []
    shadow_dir = _shadow_dir(logs_dir)

    for filename in ["entry_shadows.jsonl", "exit_shadows.jsonl",
                     "flip_shadows.jsonl", "reentry_shadows.jsonl"]:
        path = shadow_dir / filename
        shadows = _load_file(path)
        changed = False

        for s in shadows:
            if s.get("closed"):
                continue

            age = _age_minutes(s.get("timestamp", ""), now)
            stype = s.get("type", "")

            if stype == "ENTRY":
                entry = s.get("entry_price", 0)
                d = s.get("direction", "")
                if entry <= 0:
                    s["closed"] = True; changed = True; continue

                pnl = _calc_pnl(d, entry, price)
                if pnl > s.get("peak_pnl", 0): s["peak_pnl"] = round(pnl, 2)
                if pnl < s.get("worst_pnl", 0): s["worst_pnl"] = round(pnl, 2)

                # Time snapshots
                if age >= 5 and not s.get("price_5m"):
                    s["price_5m"] = price; s["pnl_5m"] = round(pnl, 2); changed = True
                if age >= 15 and not s.get("price_15m"):
                    s["price_15m"] = price; s["pnl_15m"] = round(pnl, 2); changed = True
                if age >= 30 and not s.get("price_30m"):
                    s["price_30m"] = price; s["pnl_30m"] = round(pnl, 2); changed = True
                if age >= 60 and not s.get("price_60m"):
                    s["price_60m"] = price; s["pnl_60m"] = round(pnl, 2); changed = True

                # Close conditions
                if pnl >= _TP_TARGET:
                    s["closed"] = True; s["close_reason"] = "would_tp"; s["would_have_won"] = True
                    closed_events.append(s); changed = True
                elif pnl <= _SL_LIMIT:
                    s["closed"] = True; s["close_reason"] = "would_stop"; s["would_have_won"] = False
                    closed_events.append(s); changed = True
                elif age >= _MAX_AGE_MIN:
                    s["closed"] = True; s["close_reason"] = "max_age"
                    s["would_have_won"] = s.get("peak_pnl", 0) > _FEE
                    closed_events.append(s); changed = True
                else:
                    changed = True  # peak/worst update

            elif stype == "EXIT":
                ep = s.get("exit_price", 0)
                d = s.get("direction", "")
                if ep <= 0:
                    s["closed"] = True; changed = True; continue

                # "If we had held" PnL (same direction from exit price)
                cont_pnl = _calc_pnl(d, ep, price)
                if cont_pnl > s.get("continued_peak_pnl", 0):
                    s["continued_peak_pnl"] = round(cont_pnl, 2)
                if cont_pnl < s.get("continued_worst_pnl", 0):
                    s["continued_worst_pnl"] = round(cont_pnl, 2)

                if age >= 5 and not s.get("price_5m"):
                    s["price_5m"] = price; changed = True
                if age >= 15 and not s.get("price_15m"):
                    s["price_15m"] = price; changed = True
                if age >= 30 and not s.get("price_30m"):
                    s["price_30m"] = price; changed = True
                if age >= 60 and not s.get("price_60m"):
                    s["price_60m"] = price; changed = True

                if age >= _MAX_AGE_MIN:
                    s["closed"] = True
                    s["exited_too_early"] = s.get("continued_peak_pnl", 0) > 2.0
                    s["exited_too_late"] = s.get("continued_worst_pnl", 0) < -2.0
                    s["optimal_exit_pnl"] = round(
                        s.get("pnl_at_exit", 0) + s.get("continued_peak_pnl", 0), 2)
                    closed_events.append(s)
                    changed = True
                else:
                    changed = True

            elif stype == "FLIP":
                ep = s.get("entry_price", 0)
                opp = s.get("opposite_direction", "")
                if ep <= 0:
                    s["closed"] = True; changed = True; continue

                opp_pnl = _calc_pnl(opp, ep, price)
                if opp_pnl > s.get("opposite_peak_pnl", 0):
                    s["opposite_peak_pnl"] = round(opp_pnl, 2)

                if age >= 5 and not s.get("price_5m"):
                    s["price_5m"] = price; changed = True
                if age >= 15 and not s.get("price_15m"):
                    s["price_15m"] = price; changed = True
                if age >= 30 and not s.get("price_30m"):
                    s["opposite_pnl_30m"] = round(opp_pnl, 2); s["price_30m"] = price; changed = True

                if age >= _MAX_AGE_MIN:
                    s["closed"] = True
                    s["opposite_would_have_won"] = s.get("opposite_peak_pnl", 0) > _FEE
                    closed_events.append(s)
                    changed = True
                else:
                    changed = True

            elif stype == "REENTRY":
                ep = s.get("exit_price", 0)
                ld = s.get("last_direction", "")
                if ep <= 0:
                    s["closed"] = True; changed = True; continue

                # Best re-entry same direction: price moved AGAINST us then came back
                same_pnl = _calc_pnl(ld, price, price)  # dummy -- track best entry price
                opp_dir = "long" if ld == "short" else "short"

                # For same direction: best entry is the worst price for that direction
                if ld == "short":
                    # Best short re-entry = highest price after exit
                    if price > (s.get("best_reentry_price_same") or 0):
                        s["best_reentry_price_same"] = price
                        s["best_reentry_time_same"] = now_iso[11:19]
                        s["best_reentry_pnl_same"] = round((price - ep) * _CS, 2)  # how much better than original
                else:
                    if price < (s.get("best_reentry_price_same") or 999):
                        s["best_reentry_price_same"] = price
                        s["best_reentry_time_same"] = now_iso[11:19]
                        s["best_reentry_pnl_same"] = round((ep - price) * _CS, 2)

                # For opposite direction: best entry is current extreme
                opp_pnl = _calc_pnl(opp_dir, ep, price)
                if opp_pnl > (s.get("best_reentry_pnl_opp") or 0):
                    s["best_reentry_price_opp"] = price
                    s["best_reentry_time_opp"] = now_iso[11:19]
                    s["best_reentry_pnl_opp"] = round(opp_pnl, 2)

                if age >= 5 and not s.get("price_5m"):
                    s["price_5m"] = price; changed = True
                if age >= 15 and not s.get("price_15m"):
                    s["price_15m"] = price; changed = True
                if age >= 30 and not s.get("price_30m"):
                    s["price_30m"] = price; changed = True

                if age >= _MAX_AGE_MIN:
                    s["closed"] = True
                    closed_events.append(s)
                    changed = True
                else:
                    changed = True

        if changed:
            _save_file(path, shadows)

    return closed_events


# =====================================================================
# SUMMARY -- organized stats for dashboard and self-tuning
# =====================================================================

def get_full_shadow_summary(logs_dir: Path) -> dict:
    """Complete shadow system summary, organized by type and strategy."""
    shadow_dir = _shadow_dir(logs_dir)
    result = {}

    # Entry shadows
    entries = _load_file(shadow_dir / "entry_shadows.jsonl")
    closed_entries = [s for s in entries if s.get("closed")]
    entry_by_reason = {}
    entry_by_strategy = {}
    for s in closed_entries:
        r = s.get("block_reason", "unknown")
        st = s.get("entry_type", "unknown")
        won = s.get("would_have_won", False)

        for grp, key in [(entry_by_reason, r), (entry_by_strategy, st)]:
            if key not in grp:
                grp[key] = {"total": 0, "wins": 0, "losses": 0, "avg_peak": 0, "peaks": []}
            grp[key]["total"] += 1
            grp[key]["wins" if won else "losses"] += 1
            grp[key]["peaks"].append(s.get("peak_pnl", 0))

    for grp in [entry_by_reason, entry_by_strategy]:
        for v in grp.values():
            peaks = v.pop("peaks", [])
            v["avg_peak"] = round(sum(peaks) / max(len(peaks), 1), 2)
            v["win_rate"] = round(v["wins"] / max(v["total"], 1) * 100, 1)

    result["entry_shadows"] = {
        "total": len(entries),
        "active": sum(1 for s in entries if not s.get("closed")),
        "closed": len(closed_entries),
        "by_block_reason": entry_by_reason,
        "by_strategy": entry_by_strategy,
    }

    # Exit shadows
    exits = _load_file(shadow_dir / "exit_shadows.jsonl")
    closed_exits = [s for s in exits if s.get("closed")]
    exit_by_reason = {}
    exit_by_strategy = {}
    too_early_count = 0
    too_late_count = 0
    for s in closed_exits:
        r = s.get("exit_reason", "unknown")
        st = s.get("entry_type", "unknown")
        if s.get("exited_too_early"): too_early_count += 1
        if s.get("exited_too_late"): too_late_count += 1

        for grp, key in [(exit_by_reason, r), (exit_by_strategy, st)]:
            if key not in grp:
                grp[key] = {"total": 0, "too_early": 0, "too_late": 0, "avg_left_on_table": 0, "lefts": []}
            grp[key]["total"] += 1
            if s.get("exited_too_early"): grp[key]["too_early"] += 1
            if s.get("exited_too_late"): grp[key]["too_late"] += 1
            grp[key]["lefts"].append(s.get("continued_peak_pnl", 0))

    for grp in [exit_by_reason, exit_by_strategy]:
        for v in grp.values():
            lefts = v.pop("lefts", [])
            v["avg_left_on_table"] = round(sum(lefts) / max(len(lefts), 1), 2)

    result["exit_shadows"] = {
        "total": len(exits),
        "closed": len(closed_exits),
        "exited_too_early": too_early_count,
        "exited_too_late": too_late_count,
        "by_exit_reason": exit_by_reason,
        "by_strategy": exit_by_strategy,
    }

    # Flip shadows
    flips = _load_file(shadow_dir / "flip_shadows.jsonl")
    closed_flips = [s for s in flips if s.get("closed")]
    opp_wins = sum(1 for s in closed_flips if s.get("opposite_would_have_won"))
    result["flip_shadows"] = {
        "total": len(flips),
        "closed": len(closed_flips),
        "opposite_would_have_won": opp_wins,
        "opposite_win_rate": round(opp_wins / max(len(closed_flips), 1) * 100, 1),
    }

    # Re-entry shadows
    reentries = _load_file(shadow_dir / "reentry_shadows.jsonl")
    closed_re = [s for s in reentries if s.get("closed")]
    avg_better_same = 0
    avg_better_opp = 0
    if closed_re:
        avg_better_same = round(sum(s.get("best_reentry_pnl_same", 0) for s in closed_re) / len(closed_re), 2)
        avg_better_opp = round(sum(s.get("best_reentry_pnl_opp", 0) for s in closed_re) / len(closed_re), 2)
    result["reentry_shadows"] = {
        "total": len(reentries),
        "closed": len(closed_re),
        "avg_better_reentry_same_dir": avg_better_same,
        "avg_better_reentry_opp_dir": avg_better_opp,
    }

    return result
