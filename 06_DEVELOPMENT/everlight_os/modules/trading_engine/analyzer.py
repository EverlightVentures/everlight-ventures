"""
Trading Engine — Log analyzer.
Reads xlm_bot JSONL/CSV logs and computes metrics.
"""

import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional

BOT_DIR = Path("/mnt/sdcard/AA_MY_DRIVE/xlm_bot")
LOGS = BOT_DIR / "logs"
DATA = BOT_DIR / "data"


def _read_jsonl(path: Path, since: str = None) -> List[dict]:
    """Read JSONL, optionally filtering by timestamp >= since."""
    if not path.exists():
        return []
    entries = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if since and entry.get("timestamp", "") < since:
                continue
            entries.append(entry)
    return entries


def _read_csv(path: Path) -> List[dict]:
    """Read CSV as list of dicts."""
    if not path.exists():
        return []
    with open(path) as f:
        reader = csv.DictReader(f)
        return list(reader)


def read_state() -> dict:
    """Read current bot state.json."""
    path = DATA / "state.json"
    if not path.exists():
        return {}
    with open(path) as f:
        return json.load(f)


def read_snapshot() -> dict:
    """Read latest dashboard snapshot."""
    path = LOGS / "dashboard_snapshot.json"
    if not path.exists():
        return {}
    with open(path) as f:
        return json.load(f)


def analyze_decisions(since: str = None) -> dict:
    """
    Analyze decision log entries.
    Returns gate pass rates, signal counts, block reasons, score distributions.
    """
    entries = _read_jsonl(LOGS / "decisions.jsonl", since)
    if not entries:
        return {"total_cycles": 0, "note": "no decision data"}

    total = len(entries)
    gates_pass = sum(1 for e in entries if e.get("gates_pass"))
    no_data = sum(1 for e in entries if e.get("reason") == "no_data")
    with_price = [e for e in entries if e.get("price")]

    # Gate-level pass rates
    gate_counts = defaultdict(lambda: {"pass": 0, "fail": 0})
    for e in with_price:
        gates = e.get("gates", {})
        for gate, passed in gates.items():
            if passed:
                gate_counts[gate]["pass"] += 1
            else:
                gate_counts[gate]["fail"] += 1

    gate_rates = {}
    for gate, counts in gate_counts.items():
        total_g = counts["pass"] + counts["fail"]
        gate_rates[gate] = {
            "pass_rate": round(counts["pass"] / total_g, 3) if total_g else 0,
            "total": total_g,
        }

    # Entry signals
    signals = Counter(e.get("entry_signal") for e in with_price if e.get("entry_signal"))

    # Block reasons (from snapshot-style fields)
    block_reasons = Counter()
    for e in with_price:
        for k, v in e.items():
            if k.startswith("entry_blocked") or (k.endswith("_block_reason") and v):
                block_reasons[str(v)] += 1

    # Confluence score distribution
    scores = [e.get("confluence_count", 0) or e.get("confluence_score", 0) for e in with_price]
    scores = [s for s in scores if s and isinstance(s, (int, float))]
    avg_score = round(sum(scores) / len(scores), 1) if scores else 0

    return {
        "total_cycles": total,
        "no_data_cycles": no_data,
        "gates_pass_total": gates_pass,
        "gates_pass_rate": round(gates_pass / total, 3) if total else 0,
        "gate_rates": dict(gate_rates),
        "entry_signals": dict(signals),
        "block_reasons": dict(block_reasons.most_common(10)),
        "avg_confluence_score": avg_score,
        "score_range": [min(scores) if scores else 0, max(scores) if scores else 0],
        "period_start": entries[0].get("timestamp", "?"),
        "period_end": entries[-1].get("timestamp", "?"),
    }


def analyze_trades() -> dict:
    """
    Analyze trades.csv for win/loss stats, PnL, streaks.
    """
    rows = _read_csv(LOGS / "trades.csv")
    if not rows:
        return {"total_trades": 0, "note": "no trade data"}

    # Filter out test/paper trades
    real = [r for r in rows if r.get("entry_price") not in ("TEST", "LIVE_TEST", "")]

    if not real:
        test_count = len(rows)
        return {"total_trades": 0, "test_trades": test_count, "note": "only test trades found"}

    wins = 0
    losses = 0
    total_pnl = 0.0
    pnl_list = []
    streak = 0
    max_win_streak = 0
    max_loss_streak = 0

    for r in real:
        try:
            pnl = float(r.get("pnl_usd", 0) or 0)
        except (ValueError, TypeError):
            continue

        pnl_list.append(pnl)
        total_pnl += pnl

        if pnl >= 0:
            wins += 1
            if streak >= 0:
                streak += 1
            else:
                streak = 1
            max_win_streak = max(max_win_streak, streak)
        else:
            losses += 1
            if streak <= 0:
                streak -= 1
            else:
                streak = -1
            max_loss_streak = max(max_loss_streak, abs(streak))

    total = wins + losses
    return {
        "total_trades": total,
        "wins": wins,
        "losses": losses,
        "win_rate": round(wins / total, 3) if total else 0,
        "total_pnl_usd": round(total_pnl, 2),
        "avg_pnl_usd": round(total_pnl / total, 2) if total else 0,
        "max_win_streak": max_win_streak,
        "max_loss_streak": max_loss_streak,
        "best_trade_usd": round(max(pnl_list), 2) if pnl_list else 0,
        "worst_trade_usd": round(min(pnl_list), 2) if pnl_list else 0,
        "trade_details": [
            {
                "timestamp": r.get("timestamp"),
                "side": r.get("side"),
                "entry": r.get("entry_price"),
                "exit": r.get("exit_price"),
                "pnl_usd": r.get("pnl_usd"),
                "exit_reason": r.get("exit_reason"),
            }
            for r in real
        ],
    }


def analyze_margin(since: str = None) -> dict:
    """Analyze margin policy log for tier distribution and trajectory."""
    entries = _read_jsonl(LOGS / "margin_policy.jsonl", since)
    if not entries:
        return {"total_entries": 0, "note": "no margin data"}

    tiers = Counter(e.get("tier") for e in entries)
    actions = Counter()
    for e in entries:
        for a in e.get("actions", []):
            actions[a] += 1

    # Latest margin state
    latest = entries[-1]

    return {
        "total_entries": len(entries),
        "tier_distribution": dict(tiers),
        "action_distribution": dict(actions),
        "latest_tier": latest.get("tier"),
        "latest_mr_intraday": latest.get("mr_intraday"),
        "latest_mr_overnight": latest.get("mr_overnight"),
        "latest_maintenance_margin": latest.get("maintenance_margin_requirement"),
        "latest_total_funds": latest.get("total_funds_for_margin"),
    }


def analyze_incidents(since: str = None) -> dict:
    """Analyze incident log for reconciliation issues."""
    entries = _read_jsonl(LOGS / "incidents.jsonl", since)
    if not entries:
        return {"total_incidents": 0}

    types = Counter(e.get("type") for e in entries)
    return {
        "total_incidents": len(entries),
        "types": dict(types),
        "latest": entries[-1] if entries else None,
    }


def full_analysis(lookback_hours: int = 24) -> dict:
    """Run full analysis across all log sources."""
    since = None
    if lookback_hours:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
        since = cutoff.isoformat()

    return {
        "state": read_state(),
        "snapshot": read_snapshot(),
        "decisions": analyze_decisions(since),
        "trades": analyze_trades(),
        "margin": analyze_margin(since),
        "incidents": analyze_incidents(since),
        "lookback_hours": lookback_hours,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
