"""
trade_reviewer.py -- Post-trade learning & shadow tracking for the XLM bot.

Tracks what WOULD have happened after every exit, generates lessons,
and provides pre-entry consultation from accumulated experience.

Integration (add to main.py):
    import trade_reviewer
    # After every exit:
    trade_reviewer.on_trade_exit({...trade_data...})
    # Every cycle:
    trade_reviewer.tick_shadows(current_price, now)
    # Before entry:
    advice = trade_reviewer.consult_lessons(direction, entry_signal, price, market_conditions)

Files written:
    data/shadow_trades.jsonl   -- shadow tracking records
    data/trade_lessons.jsonl   -- generated lessons
    data/pending_shadows.json  -- in-flight shadow tracking state
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"

SHADOW_TRADES_PATH = DATA_DIR / "shadow_trades.jsonl"
TRADE_LESSONS_PATH = DATA_DIR / "trade_lessons.jsonl"
PENDING_SHADOWS_PATH = DATA_DIR / "pending_shadows.json"
LIVE_TICK_PATH = LOGS_DIR / "live_tick.json"

logger = logging.getLogger("trade_reviewer")

# Shadow observation windows (minutes after exit)
SHADOW_WINDOWS = [5, 15, 30, 60]
# How many recent lessons to load for consultation
MAX_LESSONS_FOR_CONSULT = 50
# Premature exit threshold: missed at least this much USD
PREMATURE_EXIT_MIN_USD = 0.50
# Premature exit threshold: missed at least this % of position value
PREMATURE_EXIT_MIN_PCT = 0.003  # 0.3%


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _parse_iso(s: str) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s))
    except (ValueError, TypeError):
        return None


def _append_jsonl(path: Path, record: dict) -> None:
    """Append one JSON record to a .jsonl file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, default=str) + "\n"
    try:
        with open(path, "a") as f:
            f.write(line)
    except Exception as e:
        logger.error("Failed to append to %s: %s", path, e)


def _read_jsonl(path: Path, max_lines: int = 0) -> list[dict]:
    """Read .jsonl file. If max_lines > 0, return only the last N lines."""
    if not path.exists():
        return []
    lines: list[str] = []
    try:
        with open(path, "r") as f:
            lines = f.readlines()
    except Exception as e:
        logger.error("Failed to read %s: %s", path, e)
        return []
    if max_lines > 0:
        lines = lines[-max_lines:]
    records = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


def _read_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return None


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    try:
        with open(tmp, "w") as f:
            json.dump(data, f, default=str, indent=2)
        os.replace(str(tmp), str(path))
    except Exception as e:
        logger.error("Failed to write %s: %s", path, e)
        try:
            tmp.unlink(missing_ok=True)
        except Exception:
            pass


def _get_live_price() -> Optional[float]:
    """Read current price from live_tick.json."""
    data = _read_json(LIVE_TICK_PATH)
    if data and isinstance(data, dict):
        p = data.get("price")
        if p is not None:
            try:
                return float(p)
            except (ValueError, TypeError):
                pass
    return None


def _compute_shadow_pnl(
    side: str, entry_price: float, exit_price: float,
    shadow_price: float, size: int = 1
) -> dict:
    """
    Compute what PnL would have been if we held to shadow_price
    instead of exiting at exit_price.
    """
    if side == "long":
        actual_pnl_pct = (exit_price - entry_price) / entry_price if entry_price else 0
        shadow_pnl_pct = (shadow_price - entry_price) / entry_price if entry_price else 0
    else:  # short
        actual_pnl_pct = (entry_price - exit_price) / entry_price if entry_price else 0
        shadow_pnl_pct = (entry_price - shadow_price) / entry_price if entry_price else 0

    # Rough USD: Coinbase perp 1 contract ~ notional = price * size
    notional = entry_price * size
    shadow_pnl_usd = shadow_pnl_pct * notional
    actual_pnl_usd = actual_pnl_pct * notional

    return {
        "shadow_pnl_pct": round(shadow_pnl_pct, 6),
        "shadow_pnl_usd": round(shadow_pnl_usd, 4),
        "missed_vs_actual_usd": round(shadow_pnl_usd - actual_pnl_usd, 4),
    }


# ---------------------------------------------------------------------------
# 1. Pending Shadows State
# ---------------------------------------------------------------------------

def _load_pending() -> list[dict]:
    data = _read_json(PENDING_SHADOWS_PATH)
    if isinstance(data, list):
        return data
    return []


def _save_pending(pending: list[dict]) -> None:
    _write_json(PENDING_SHADOWS_PATH, pending)


# ---------------------------------------------------------------------------
# 2. on_trade_exit -- called by main.py after every exit
# ---------------------------------------------------------------------------

def on_trade_exit(trade_data: dict) -> None:
    """
    Start shadow tracking for a completed trade.

    trade_data should contain at minimum:
        entry_price, exit_price, side, pnl_usd, pnl_pct,
        exit_reason, entry_time, exit_time, size,
        strategy_regime, confluence_score, entry_type, breakout_type
    """
    try:
        exit_time = trade_data.get("exit_time") or _iso(_utcnow())
        exit_dt = _parse_iso(str(exit_time)) or _utcnow()

        entry_price = float(trade_data.get("entry_price") or 0)
        exit_price = float(trade_data.get("exit_price") or 0)
        if entry_price <= 0 or exit_price <= 0:
            logger.warning("Skipping shadow: invalid prices entry=%.6f exit=%.6f",
                           entry_price, exit_price)
            return

        shadow = {
            "trade_id": f"{exit_dt.strftime('%Y%m%d_%H%M%S')}_{trade_data.get('side', 'unk')}",
            "entry_price": entry_price,
            "exit_price": exit_price,
            "side": str(trade_data.get("side") or "").lower(),
            "size": int(trade_data.get("size") or 1),
            "pnl_usd": float(trade_data.get("pnl_usd") or 0),
            "pnl_pct": float(trade_data.get("pnl_pct") or 0),
            "exit_reason": str(trade_data.get("exit_reason") or "unknown"),
            "entry_time": str(trade_data.get("entry_time") or ""),
            "exit_time": str(exit_time),
            "strategy_regime": str(trade_data.get("strategy_regime") or ""),
            "confluence_score": trade_data.get("confluence_score"),
            "entry_type": str(trade_data.get("entry_type") or ""),
            "breakout_type": str(trade_data.get("breakout_type") or ""),
            "hold_minutes": _compute_hold_min(trade_data),
            # Shadow fields -- filled in by tick_shadows()
            "shadow_5m_due": _iso(exit_dt + timedelta(minutes=5)),
            "shadow_15m_due": _iso(exit_dt + timedelta(minutes=15)),
            "shadow_30m_due": _iso(exit_dt + timedelta(minutes=30)),
            "shadow_60m_due": _iso(exit_dt + timedelta(minutes=60)),
            "shadow_5m_price": None,
            "shadow_15m_price": None,
            "shadow_30m_price": None,
            "shadow_60m_price": None,
            "shadow_5m_pnl": None,
            "shadow_15m_pnl": None,
            "shadow_30m_pnl": None,
            "shadow_60m_pnl": None,
            "price_samples": [],  # track all prices seen for optimal exit calc
            "completed": False,
            "created_at": _iso(_utcnow()),
        }

        pending = _load_pending()
        pending.append(shadow)
        _save_pending(pending)
        logger.info("Shadow tracking started: %s (exit_reason=%s, pnl=$%.2f)",
                     shadow["trade_id"], shadow["exit_reason"], shadow["pnl_usd"])
    except Exception as e:
        logger.error("on_trade_exit failed: %s", e, exc_info=True)


def _compute_hold_min(td: dict) -> float:
    entry_t = _parse_iso(str(td.get("entry_time") or ""))
    exit_t = _parse_iso(str(td.get("exit_time") or ""))
    if entry_t and exit_t:
        return round((exit_t - entry_t).total_seconds() / 60.0, 2)
    return float(td.get("time_in_trade_min") or 0)


# ---------------------------------------------------------------------------
# 3. tick_shadows -- called every bot cycle
# ---------------------------------------------------------------------------

def tick_shadows(current_price: float, now: Optional[datetime] = None) -> None:
    """
    Update all pending shadow trades with current price.
    Fill in shadow window prices when enough time has elapsed.
    Finalize and generate lessons when 60m window completes.
    """
    if current_price <= 0:
        return

    if now is None:
        now = _utcnow()

    try:
        pending = _load_pending()
    except Exception:
        pending = []

    if not pending:
        return

    changed = False
    still_pending = []

    for shadow in pending:
        if shadow.get("completed"):
            continue

        # Record price sample for optimal exit tracking
        shadow.setdefault("price_samples", [])
        shadow["price_samples"].append({
            "ts": _iso(now),
            "price": current_price,
        })
        # Cap samples to avoid unbounded growth (~60 min / 5 sec cycle = 720 max)
        if len(shadow["price_samples"]) > 800:
            shadow["price_samples"] = shadow["price_samples"][-800:]

        side = shadow.get("side", "long")
        entry_price = float(shadow.get("entry_price") or 0)
        exit_price = float(shadow.get("exit_price") or 0)
        size = int(shadow.get("size") or 1)

        # Fill shadow window prices as they come due
        all_filled = True
        for window in SHADOW_WINDOWS:
            price_key = f"shadow_{window}m_price"
            pnl_key = f"shadow_{window}m_pnl"
            due_key = f"shadow_{window}m_due"

            if shadow.get(price_key) is not None:
                continue  # already filled

            due_dt = _parse_iso(str(shadow.get(due_key) or ""))
            if due_dt and now >= due_dt:
                shadow[price_key] = current_price
                pnl_info = _compute_shadow_pnl(side, entry_price, exit_price,
                                                current_price, size)
                shadow[pnl_key] = pnl_info["shadow_pnl_usd"]
                changed = True
                logger.info("Shadow %s: %dm price=%.6f shadow_pnl=$%.4f",
                            shadow.get("trade_id", "?"), window,
                            current_price, pnl_info["shadow_pnl_usd"])
            else:
                all_filled = False

        if all_filled:
            # All windows filled -- finalize
            _finalize_shadow(shadow)
            changed = True
        else:
            still_pending.append(shadow)

    # Expire stale shadows (> 90 min old, somehow never completed)
    cutoff = now - timedelta(minutes=90)
    cleaned = []
    for s in still_pending:
        created = _parse_iso(str(s.get("created_at") or ""))
        if created and created < cutoff:
            logger.warning("Expiring stale shadow %s", s.get("trade_id", "?"))
            s["completed"] = True
            _finalize_shadow(s, expired=True)
            changed = True
        else:
            cleaned.append(s)

    if changed:
        _save_pending(cleaned)


def _finalize_shadow(shadow: dict, expired: bool = False) -> None:
    """Compute optimal exit, premature flag, missed profit. Write to JSONL + generate lesson."""
    shadow["completed"] = True
    shadow["expired"] = expired

    side = shadow.get("side", "long")
    entry_price = float(shadow.get("entry_price") or 0)
    exit_price = float(shadow.get("exit_price") or 0)
    size = int(shadow.get("size") or 1)
    actual_pnl_usd = float(shadow.get("pnl_usd") or 0)

    # Find optimal exit price from all samples
    samples = shadow.get("price_samples") or []
    if samples:
        prices = [s["price"] for s in samples if isinstance(s.get("price"), (int, float))]
        if prices:
            if side == "long":
                optimal_price = max(prices)
            else:
                optimal_price = min(prices)
        else:
            optimal_price = exit_price
    else:
        optimal_price = exit_price

    shadow["optimal_exit_price"] = optimal_price

    # Compute what PnL would have been at optimal
    optimal_info = _compute_shadow_pnl(side, entry_price, exit_price, optimal_price, size)
    optimal_pnl_usd = optimal_info["shadow_pnl_usd"]
    missed_profit = optimal_info["missed_vs_actual_usd"]
    shadow["optimal_pnl_usd"] = optimal_pnl_usd
    shadow["missed_profit_usd"] = round(missed_profit, 4)

    # Premature exit check
    is_premature = (
        missed_profit >= PREMATURE_EXIT_MIN_USD
        and entry_price > 0
        and abs(missed_profit / (entry_price * size)) >= PREMATURE_EXIT_MIN_PCT
    )
    shadow["premature_exit"] = is_premature

    # Strip bulky price_samples before writing to JSONL (keep count only)
    shadow["sample_count"] = len(samples)
    shadow.pop("price_samples", None)
    # Strip due timestamps (internal bookkeeping)
    for w in SHADOW_WINDOWS:
        shadow.pop(f"shadow_{w}m_due", None)

    shadow["finalized_at"] = _iso(_utcnow())
    _append_jsonl(SHADOW_TRADES_PATH, shadow)
    logger.info("Shadow finalized: %s premature=%s missed=$%.4f",
                shadow.get("trade_id", "?"), is_premature, missed_profit)

    # Generate lesson
    _generate_lesson(shadow)


# ---------------------------------------------------------------------------
# 4. Lesson Generation
# ---------------------------------------------------------------------------

def _generate_lesson(shadow: dict) -> None:
    """Generate a plain-English lesson from a finalized shadow trade."""
    try:
        side = shadow.get("side", "long")
        entry_price = float(shadow.get("entry_price") or 0)
        exit_price = float(shadow.get("exit_price") or 0)
        pnl_usd = float(shadow.get("pnl_usd") or 0)
        missed = float(shadow.get("missed_profit_usd") or 0)
        exit_reason = shadow.get("exit_reason", "unknown")
        is_premature = shadow.get("premature_exit", False)
        strategy = shadow.get("strategy_regime", "")
        entry_type = shadow.get("entry_type", "")
        breakout_type = shadow.get("breakout_type", "")
        hold_min = float(shadow.get("hold_minutes") or 0)
        confluence = shadow.get("confluence_score")

        # Shadow PnL at each window
        s5 = shadow.get("shadow_5m_pnl")
        s15 = shadow.get("shadow_15m_pnl")
        s30 = shadow.get("shadow_30m_pnl")
        s60 = shadow.get("shadow_60m_pnl")

        # Determine lesson type
        if is_premature and pnl_usd >= 0:
            lesson_type = "premature_profitable_exit"
        elif is_premature and pnl_usd < 0:
            lesson_type = "premature_loss_exit"
        elif pnl_usd < 0 and missed <= PREMATURE_EXIT_MIN_USD:
            lesson_type = "genuine_loss"
        elif pnl_usd >= 0 and not is_premature:
            lesson_type = "good_exit"
        else:
            lesson_type = "neutral"

        # Build lesson text
        lesson_text = ""
        tags = []

        if lesson_type == "premature_profitable_exit":
            lesson_text = (
                f"Exited {side.upper()} too early via '{exit_reason}' after {hold_min:.0f}min. "
                f"Actual PnL: ${pnl_usd:.2f}. Optimal was ${shadow.get('optimal_pnl_usd', 0):.2f} "
                f"(missed ${missed:.2f}). "
            )
            # Which windows showed improvement?
            improving_windows = []
            for w, sv in [(5, s5), (15, s15), (30, s30), (60, s60)]:
                if sv is not None and sv > pnl_usd:
                    improving_windows.append(f"{w}m=${sv:.2f}")
            if improving_windows:
                lesson_text += f"Shadow PnL improved at: {', '.join(improving_windows)}. "
            lesson_text += f"Lesson: consider holding longer when exit_reason='{exit_reason}' "
            if strategy:
                lesson_text += f"in {strategy} regime "
            if entry_type:
                lesson_text += f"with {entry_type} entries"
            lesson_text += "."
            tags = ["premature_exit", exit_reason, strategy, entry_type]

        elif lesson_type == "premature_loss_exit":
            lesson_text = (
                f"Exited {side.upper()} at a loss (${pnl_usd:.2f}) via '{exit_reason}' "
                f"but price recovered. Missed ${missed:.2f} of recovery. "
                f"Shadow 30m: ${s30 if s30 is not None else '?'}, "
                f"Shadow 60m: ${s60 if s60 is not None else '?'}. "
                f"Lesson: '{exit_reason}' exits on {side} {entry_type or 'trades'} "
                f"may be too aggressive -- price often recovers."
            )
            tags = ["premature_exit", "loss_recovered", exit_reason, side, entry_type]

        elif lesson_type == "genuine_loss":
            move_pct = abs((exit_price - entry_price) / entry_price * 100) if entry_price else 0
            lesson_text = (
                f"Genuine loss on {side.upper()} entry at ${entry_price:.6f}. "
                f"Lost ${abs(pnl_usd):.2f} ({move_pct:.2f}% against). "
                f"Exit: '{exit_reason}' after {hold_min:.0f}min. "
            )
            # Did price keep moving against us after exit?
            if s60 is not None and s60 < pnl_usd:
                extra_loss = abs(s60 - pnl_usd)
                lesson_text += (
                    f"Good exit -- price moved further against us "
                    f"(60m shadow: ${s60:.2f}, saved ${extra_loss:.2f}). "
                )
                tags.append("good_stop")
            else:
                lesson_text += (
                    f"Price did not continue against -- stop may have been too tight. "
                )
                tags.append("tight_stop")

            lesson_text += (
                f"Lesson: avoid {side} {entry_type or 'entries'} "
                f"in {strategy or 'this'} regime "
                f"when confluence is {confluence or 'low'}."
            )
            tags.extend(["genuine_loss", exit_reason, side, strategy, entry_type])

        elif lesson_type == "good_exit":
            lesson_text = (
                f"Good exit on {side.upper()}. PnL: ${pnl_usd:.2f}. "
                f"'{exit_reason}' was the right call -- shadow confirms no significant upside left "
                f"(60m shadow: ${s60 if s60 is not None else '?'})."
            )
            tags = ["good_exit", exit_reason, side, strategy]

        else:
            lesson_text = (
                f"{side.upper()} trade exited via '{exit_reason}'. "
                f"PnL: ${pnl_usd:.2f}. Shadow 60m: ${s60 if s60 is not None else '?'}. "
                f"Neutral outcome."
            )
            tags = ["neutral", exit_reason, side]

        # Clean tags
        tags = [t for t in tags if t]

        lesson = {
            "trade_id": shadow.get("trade_id", ""),
            "timestamp": _iso(_utcnow()),
            "lesson_type": lesson_type,
            "lesson_text": lesson_text,
            "tags": tags,
            "side": side,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "pnl_usd": pnl_usd,
            "missed_profit_usd": missed,
            "exit_reason": exit_reason,
            "strategy_regime": strategy,
            "entry_type": entry_type,
            "breakout_type": breakout_type,
            "hold_minutes": hold_min,
            "confluence_score": confluence,
            "premature_exit": shadow.get("premature_exit", False),
            "shadow_5m_pnl": s5,
            "shadow_15m_pnl": s15,
            "shadow_30m_pnl": s30,
            "shadow_60m_pnl": s60,
        }

        _append_jsonl(TRADE_LESSONS_PATH, lesson)
        logger.info("Lesson generated: [%s] %s", lesson_type, lesson_text[:120])

    except Exception as e:
        logger.error("Lesson generation failed: %s", e, exc_info=True)


# ---------------------------------------------------------------------------
# 5. Pre-Entry Consultation
# ---------------------------------------------------------------------------

def consult_lessons(
    direction: str,
    entry_signal: str,
    price: float,
    market_conditions: Optional[dict] = None,
) -> dict:
    """
    Consult accumulated lessons before entering a trade.

    Returns:
        {
            "lesson_score_modifier": int,   # -10 to +10
            "warnings": [str, ...],
            "supporting": [str, ...],
            "stats": {...},
            "consulted_count": int,
        }
    """
    result = {
        "lesson_score_modifier": 0,
        "warnings": [],
        "supporting": [],
        "stats": {},
        "consulted_count": 0,
    }

    try:
        lessons = _read_jsonl(TRADE_LESSONS_PATH, max_lines=MAX_LESSONS_FOR_CONSULT)
    except Exception:
        lessons = []

    if not lessons:
        return result

    result["consulted_count"] = len(lessons)
    direction = str(direction).lower()
    entry_signal = str(entry_signal).lower() if entry_signal else ""
    strategy = str((market_conditions or {}).get("strategy_regime", "")).lower()
    regime = str((market_conditions or {}).get("vol_state", "")).lower()

    # Aggregate stats from matching lessons
    same_dir = [l for l in lessons if l.get("side", "").lower() == direction]
    same_signal = [l for l in same_dir if entry_signal and entry_signal in str(l.get("entry_type", "")).lower()]
    same_strategy = [l for l in same_dir if strategy and strategy in str(l.get("strategy_regime", "")).lower()]

    # --- Stat: recent same-direction win rate ---
    recent_same = same_dir[-10:] if len(same_dir) >= 3 else same_dir
    wins = sum(1 for l in recent_same if (l.get("pnl_usd") or 0) > 0)
    losses = sum(1 for l in recent_same if (l.get("pnl_usd") or 0) < 0)
    total = wins + losses
    win_rate = wins / total if total > 0 else 0.5

    result["stats"]["same_direction_trades"] = len(same_dir)
    result["stats"]["recent_win_rate"] = round(win_rate, 2)
    result["stats"]["recent_wins"] = wins
    result["stats"]["recent_losses"] = losses

    # --- Warning: losing streak ---
    if total >= 3 and win_rate < 0.35:
        result["warnings"].append(
            f"Last {total} {direction} trades: {wins}W/{losses}L "
            f"({win_rate:.0%} win rate). Caution."
        )
        result["lesson_score_modifier"] -= 5

    # --- Warning: same entry type losing ---
    if same_signal and len(same_signal) >= 2:
        sig_losses = sum(1 for l in same_signal[-5:] if (l.get("pnl_usd") or 0) < 0)
        sig_total = min(len(same_signal), 5)
        if sig_losses >= 3:
            result["warnings"].append(
                f"Last {sig_total} '{entry_signal}' {direction} entries: "
                f"{sig_losses} losses. This signal is underperforming."
            )
            result["lesson_score_modifier"] -= 3

    # --- Warning: premature exit pattern ---
    premature_count = sum(1 for l in same_dir if l.get("premature_exit"))
    if premature_count >= 2 and same_dir:
        premature_pct = premature_count / len(same_dir)
        avg_missed = 0.0
        premature_lessons = [l for l in same_dir if l.get("premature_exit")]
        if premature_lessons:
            avg_missed = sum(l.get("missed_profit_usd", 0) for l in premature_lessons) / len(premature_lessons)
        if premature_pct >= 0.3:
            result["warnings"].append(
                f"{premature_pct:.0%} of recent {direction} exits were premature "
                f"(avg missed ${avg_missed:.2f}). Consider wider stops/longer holds."
            )
            # Informational, slight positive modifier since exits are too aggressive
            result["lesson_score_modifier"] += 1

    # --- Warning: specific exit_reason is consistently premature ---
    exit_reason_stats: dict[str, dict] = {}
    for l in same_dir:
        er = l.get("exit_reason", "")
        if not er:
            continue
        if er not in exit_reason_stats:
            exit_reason_stats[er] = {"total": 0, "premature": 0, "missed_total": 0.0}
        exit_reason_stats[er]["total"] += 1
        if l.get("premature_exit"):
            exit_reason_stats[er]["premature"] += 1
            exit_reason_stats[er]["missed_total"] += float(l.get("missed_profit_usd") or 0)

    for er, stats in exit_reason_stats.items():
        if stats["total"] >= 3 and stats["premature"] / stats["total"] >= 0.5:
            avg_m = stats["missed_total"] / stats["premature"] if stats["premature"] else 0
            result["warnings"].append(
                f"Exit reason '{er}' is premature {stats['premature']}/{stats['total']} times "
                f"(avg missed ${avg_m:.2f}). Shadow data says hold through these."
            )

    # --- Supporting: good exits in same conditions ---
    good_exits = [l for l in same_dir if l.get("lesson_type") == "good_exit"]
    if good_exits and len(good_exits) >= 2:
        result["supporting"].append(
            f"{len(good_exits)} recent {direction} trades had well-timed exits."
        )
        result["lesson_score_modifier"] += 1

    # --- Supporting: same strategy has positive recent PnL ---
    if same_strategy:
        strat_pnl = sum(l.get("pnl_usd", 0) for l in same_strategy[-5:])
        if strat_pnl > 0:
            result["supporting"].append(
                f"Recent {strategy} {direction} trades net +${strat_pnl:.2f}."
            )
            result["lesson_score_modifier"] += 2
        elif strat_pnl < -2.0:
            result["warnings"].append(
                f"Recent {strategy} {direction} trades net ${strat_pnl:.2f}. Regime unfavorable."
            )
            result["lesson_score_modifier"] -= 3

    # --- Clamp modifier ---
    result["lesson_score_modifier"] = max(-10, min(10, result["lesson_score_modifier"]))

    return result


# ---------------------------------------------------------------------------
# 6. Summary / Analytics (for dashboard or manual review)
# ---------------------------------------------------------------------------

def get_shadow_summary(last_n: int = 20) -> dict:
    """
    Return aggregate shadow stats for the dashboard.
    """
    shadows = _read_jsonl(SHADOW_TRADES_PATH, max_lines=last_n)
    if not shadows:
        return {
            "total": 0, "premature_exits": 0, "premature_pct": 0,
            "total_missed_usd": 0, "avg_missed_usd": 0,
            "genuine_losses": 0, "good_exits": 0, "top_premature_reasons": {},
        }

    premature_count = sum(1 for s in shadows if s.get("premature_exit"))
    total_missed = sum(float(s.get("missed_profit_usd") or 0) for s in shadows if s.get("premature_exit"))
    genuine_losses = sum(1 for s in shadows if not s.get("premature_exit") and float(s.get("pnl_usd") or 0) < 0)
    good_exits = sum(1 for s in shadows if not s.get("premature_exit") and float(s.get("pnl_usd") or 0) >= 0)

    # Most common premature exit reasons
    premature_reasons: dict[str, int] = {}
    for s in shadows:
        if s.get("premature_exit"):
            er = s.get("exit_reason", "unknown")
            premature_reasons[er] = premature_reasons.get(er, 0) + 1

    return {
        "total": len(shadows),
        "premature_exits": premature_count,
        "premature_pct": round(premature_count / len(shadows) * 100, 1) if shadows else 0,
        "total_missed_usd": round(total_missed, 2),
        "avg_missed_usd": round(total_missed / premature_count, 2) if premature_count else 0,
        "genuine_losses": genuine_losses,
        "good_exits": good_exits,
        "top_premature_reasons": dict(sorted(premature_reasons.items(), key=lambda x: -x[1])[:5]),
    }


def get_recent_lessons(n: int = 10) -> list[dict]:
    """Return the last N lessons for display."""
    return _read_jsonl(TRADE_LESSONS_PATH, max_lines=n)


# ---------------------------------------------------------------------------
# 7. CLI -- run standalone for manual review
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if len(sys.argv) > 1 and sys.argv[1] == "summary":
        summary = get_shadow_summary(last_n=50)
        print("\n=== Shadow Trade Summary ===")
        print(f"Total tracked:     {summary['total']}")
        print(f"Premature exits:   {summary['premature_exits']} ({summary['premature_pct']}%)")
        print(f"Total missed:      ${summary['total_missed_usd']}")
        print(f"Avg missed/trade:  ${summary['avg_missed_usd']}")
        print(f"Genuine losses:    {summary['genuine_losses']}")
        print(f"Good exits:        {summary['good_exits']}")
        if summary.get("top_premature_reasons"):
            print("\nTop premature exit reasons:")
            for reason, count in summary["top_premature_reasons"].items():
                print(f"  {reason}: {count}x")

    elif len(sys.argv) > 1 and sys.argv[1] == "lessons":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        lessons = get_recent_lessons(n)
        print(f"\n=== Last {len(lessons)} Lessons ===\n")
        for l in lessons:
            pnl = l.get("pnl_usd", 0)
            marker = "+" if pnl >= 0 else ""
            print(f"[{l.get('lesson_type', '?')}] {l.get('side', '?').upper()} "
                  f"{marker}${pnl:.2f} | {l.get('lesson_text', '')}")
            print()

    elif len(sys.argv) > 1 and sys.argv[1] == "consult":
        direction = sys.argv[2] if len(sys.argv) > 2 else "long"
        signal = sys.argv[3] if len(sys.argv) > 3 else "pullback"
        advice = consult_lessons(direction, signal, 0.0)
        print(f"\n=== Consultation for {direction.upper()} {signal} ===")
        print(f"Score modifier: {advice['lesson_score_modifier']}")
        print(f"Consulted: {advice['consulted_count']} lessons")
        if advice["warnings"]:
            print("\nWarnings:")
            for w in advice["warnings"]:
                print(f"  - {w}")
        if advice["supporting"]:
            print("\nSupporting:")
            for s in advice["supporting"]:
                print(f"  + {s}")
        print(f"\nStats: {json.dumps(advice['stats'], indent=2)}")

    elif len(sys.argv) > 1 and sys.argv[1] == "pending":
        pending = _load_pending()
        print(f"\n=== {len(pending)} Pending Shadows ===\n")
        for p in pending:
            filled = sum(1 for w in SHADOW_WINDOWS if p.get(f"shadow_{w}m_price") is not None)
            print(f"  {p.get('trade_id', '?')} | {p.get('side', '?').upper()} "
                  f"| filled {filled}/{len(SHADOW_WINDOWS)} | "
                  f"samples: {len(p.get('price_samples', []))}")

    else:
        print("Usage: python trade_reviewer.py [summary|lessons [N]|consult [dir] [signal]|pending]")
