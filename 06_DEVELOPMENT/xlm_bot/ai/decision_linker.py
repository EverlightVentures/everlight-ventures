"""Decision-to-outcome linker.

Links trading decisions from logs/decisions.jsonl to their trade outcomes
in logs/trades.csv.  Uses a byte-offset watermark so the 110MB+ decisions
file is never re-read from scratch -- only new lines since the last run
are processed.

Output: one JSONL line per linked decision written to
logs/decision_outcomes.jsonl (append mode).
"""
from __future__ import annotations

import csv
import json
import os
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# -- Lane mapping (entry_type -> lane letter) --------------------------
LANE_MAP: dict[str, str] = {
    "pullback": "A",
    "breakout_retest": "B",
    "reversal_impulse": "C",
    "early_impulse": "E",
    "compression_breakout": "F",
    "compression_range": "G",
    "trend_continuation": "H",
    "fib_retrace": "I",
    "slow_bleed_hunter": "J",
    "wick_rejection": "K",
    "volume_climax_reversal": "M",
    "vwap_reversion": "N",
    "ai_executive": "X",
}

_BASE_DIR = Path(__file__).resolve().parent.parent


# -- Watermark helpers -------------------------------------------------

def _read_watermark(path: Path) -> int:
    """Return byte offset stored in path, or 0 if missing/corrupt."""
    try:
        text = path.read_text().strip()
        return int(text) if text else 0
    except (FileNotFoundError, ValueError, OSError):
        return 0


def _write_watermark(path: Path, offset: int) -> None:
    """Atomically write offset to path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        os.write(fd, str(offset).encode())
        os.close(fd)
        os.replace(tmp, str(path))
    except Exception:
        try:
            os.close(fd)
        except OSError:
            pass
        try:
            os.unlink(tmp)
        except OSError:
            pass


# -- Internal helpers --------------------------------------------------

def _parse_iso(ts_str: str) -> datetime | None:
    """Parse an ISO-8601 timestamp string, returning None on failure."""
    if not ts_str:
        return None
    try:
        dt = datetime.fromisoformat(ts_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


def _is_entry_decision(record: dict[str, Any]) -> bool:
    """True when the decision record represents an entry-related event."""
    reason = record.get("reason", "") or ""
    if "entry" in reason or "ai_executive" in reason:
        return True
    entry_sig = record.get("entry_signal")
    if entry_sig and isinstance(entry_sig, str):
        return True
    return False


def _direction_from_record(record: dict[str, Any]) -> str | None:
    """Extract normalised direction ('long' / 'short') from a decision."""
    d = record.get("direction")
    if isinstance(d, str) and d in ("long", "short"):
        return d
    return None


def _read_new_decisions(
    decisions_path: Path,
    start_offset: int,
) -> tuple[list[dict[str, Any]], int]:
    """Read decision lines from start_offset onward.

    Returns (list_of_entry_decisions, new_byte_offset).
    """
    entries: list[dict[str, Any]] = []
    end_offset = start_offset
    try:
        with open(decisions_path, "rb") as fh:
            fh.seek(start_offset)
            for raw_line in fh:
                end_offset += len(raw_line)
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if _is_entry_decision(record):
                    entries.append(record)
    except (FileNotFoundError, OSError):
        pass
    return entries, end_offset


def _read_trades(trades_path: Path) -> list[dict[str, Any]]:
    """Read trades.csv and return rows that have both entry_time and exit_time."""
    trades: list[dict[str, Any]] = []
    try:
        with open(trades_path, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                entry_ts = row.get("entry_time", "").strip()
                exit_ts = row.get("exit_time", "").strip()
                if not entry_ts or not exit_ts:
                    continue
                trades.append(row)
    except (FileNotFoundError, OSError):
        pass
    return trades


# -- Public API --------------------------------------------------------

def link_decisions(
    decisions_path: str | Path,
    trades_path: str | Path,
    output_path: str | Path,
    watermark_path: str | Path | None = None,
    time_window_sec: int = 120,
) -> int:
    """Link new decisions to trade outcomes and append results.

    Returns number of newly linked decision-outcome records written.
    """
    decisions_path = Path(decisions_path)
    trades_path = Path(trades_path)
    output_path = Path(output_path)
    if watermark_path is None:
        watermark_path = _BASE_DIR / "data" / ".linker_watermark"
    else:
        watermark_path = Path(watermark_path)

    start_offset = _read_watermark(watermark_path)
    entry_decisions, new_offset = _read_new_decisions(decisions_path, start_offset)

    if new_offset == start_offset:
        return 0

    trades = _read_trades(trades_path)

    if not trades or not entry_decisions:
        _write_watermark(watermark_path, new_offset)
        return 0

    # Sort entry decisions by timestamp
    for d in entry_decisions:
        d["_ts"] = _parse_iso(d.get("timestamp", ""))
    entry_decisions = [d for d in entry_decisions if d["_ts"] is not None]
    entry_decisions.sort(key=lambda d: d["_ts"])

    linked_count = 0
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(output_path, "a", encoding="utf-8") as out:
            for trade in trades:
                trade_entry_ts = _parse_iso(trade.get("entry_time", ""))
                if trade_entry_ts is None:
                    continue

                trade_side = (trade.get("side") or "").strip().lower()
                trade_entry_type = (trade.get("entry_type") or "").strip().lower()

                best: dict[str, Any] | None = None
                best_gap: float = float("inf")

                for dec in entry_decisions:
                    dec_ts: datetime = dec["_ts"]
                    gap = (trade_entry_ts - dec_ts).total_seconds()

                    if gap < 0 or gap > time_window_sec:
                        continue

                    dec_dir = _direction_from_record(dec)
                    if dec_dir is not None and trade_side and dec_dir != trade_side:
                        continue

                    if gap < best_gap:
                        best_gap = gap
                        best = dec

                if best is None:
                    continue

                pnl_raw = trade.get("pnl_usd", "")
                try:
                    pnl_usd = float(pnl_raw)
                except (ValueError, TypeError):
                    pnl_usd = 0.0

                try:
                    confluence_score = float(trade.get("confluence_score", ""))
                except (ValueError, TypeError):
                    confluence_score = None

                try:
                    score_threshold = float(trade.get("score_threshold", ""))
                except (ValueError, TypeError):
                    score_threshold = None

                try:
                    duration_min = float(trade.get("time_in_trade_min", ""))
                except (ValueError, TypeError):
                    duration_min = None

                lane = LANE_MAP.get(trade_entry_type, "?")
                dec_reason = best.get("reason", "")
                if not dec_reason and best.get("entry_signal"):
                    dec_reason = "entry_signal:" + str(best["entry_signal"])

                record = {
                    "decision_ts": best.get("timestamp", ""),
                    "trade_entry_ts": trade.get("entry_time", ""),
                    "direction": trade_side,
                    "entry_type": trade_entry_type,
                    "lane": lane,
                    "confluence_score": confluence_score,
                    "score_threshold": score_threshold,
                    "pnl_usd": pnl_usd,
                    "won": pnl_usd > 0,
                    "exit_reason": (trade.get("exit_reason") or "").strip(),
                    "duration_min": duration_min,
                    "decision_reason": dec_reason,
                }

                out.write(json.dumps(record, default=str) + "\n")
                linked_count += 1
    except OSError:
        pass

    _write_watermark(watermark_path, new_offset)
    return linked_count


def get_lane_decision_stats(
    outcomes_path: str | Path,
    lookback: int = 100,
) -> dict[str, dict[str, Any]]:
    """Aggregate per-lane stats from the last lookback linked outcomes.

    Returns dict keyed by lane letter with: count, wins, losses, win_rate,
    avg_pnl, top_exit_reason, avg_score_at_entry.
    """
    outcomes_path = Path(outcomes_path)
    lines: list[dict[str, Any]] = []

    try:
        with open(outcomes_path, encoding="utf-8") as fh:
            all_lines = fh.readlines()
            tail = all_lines[-lookback:] if len(all_lines) > lookback else all_lines
            for raw in tail:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    lines.append(json.loads(raw))
                except json.JSONDecodeError:
                    continue
    except (FileNotFoundError, OSError):
        return {}

    lanes: dict[str, list[dict[str, Any]]] = {}
    for rec in lines:
        lane = rec.get("lane", "?")
        lanes.setdefault(lane, []).append(rec)

    result: dict[str, dict[str, Any]] = {}
    for lane, recs in sorted(lanes.items()):
        count = len(recs)
        wins = sum(1 for r in recs if r.get("won"))
        losses = count - wins
        pnls = [r.get("pnl_usd", 0.0) for r in recs if r.get("pnl_usd") is not None]
        avg_pnl = sum(pnls) / len(pnls) if pnls else 0.0

        exit_reasons = [r.get("exit_reason", "") for r in recs if r.get("exit_reason")]
        top_exit = Counter(exit_reasons).most_common(1)
        top_exit_reason = top_exit[0][0] if top_exit else ""

        scores = [
            r["confluence_score"]
            for r in recs
            if r.get("confluence_score") is not None
        ]
        avg_score = sum(scores) / len(scores) if scores else None

        result[lane] = {
            "count": count,
            "wins": wins,
            "losses": losses,
            "win_rate": round(wins / count, 4) if count else 0.0,
            "avg_pnl": round(avg_pnl, 4),
            "top_exit_reason": top_exit_reason,
            "avg_score_at_entry": round(avg_score, 2) if avg_score is not None else None,
        }

    return result
