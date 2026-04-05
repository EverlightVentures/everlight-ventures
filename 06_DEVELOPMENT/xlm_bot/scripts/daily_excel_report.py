#!/usr/bin/env python3
"""
Daily Excel Report Generator for XLM Bot
Reads audit logs and decisions.jsonl, produces a branded Excel workbook.

Outputs:
  - Trade Journal sheet (every trade with entry/exit/R:R/PnL)
  - Daily Summary sheet (win rate, total P&L, best/worst trade)
  - Pattern Analysis sheet (missed setups, time-of-day performance)
  - Score Analysis sheet (confluence scores vs outcomes)

Run daily via cron or manually:
    python3 scripts/daily_excel_report.py
    python3 scripts/daily_excel_report.py --date 2026-04-05
"""
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Add parent for imports
BOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BOT_DIR))
sys.path.insert(0, str(BOT_DIR.parent.parent / "03_AUTOMATION_CORE" / "01_Scripts"))

LOGS_DIR = BOT_DIR / "logs"
DATA_DIR = BOT_DIR / "data"
OUTPUT_DIR = BOT_DIR / "reports"
OUTPUT_DIR.mkdir(exist_ok=True)


def load_decisions(date_str: str) -> list[dict]:
    """Load trade decisions from decisions.jsonl for a given date."""
    decisions = []
    jsonl_path = LOGS_DIR / "decisions.jsonl"
    if not jsonl_path.exists():
        return decisions

    with open(jsonl_path) as f:
        for line in f:
            try:
                d = json.loads(line)
                ts = d.get("timestamp", d.get("ts", ""))
                if date_str in ts:
                    decisions.append(d)
            except json.JSONDecodeError:
                continue
    return decisions


def load_audit_trades(date_str: str) -> list[dict]:
    """Load structured trade records from audit logs."""
    # Check audit directory structure: logs/audit/YYYY/MM/DD/
    parts = date_str.split("-")
    if len(parts) != 3:
        return []

    audit_dir = LOGS_DIR / "audit" / parts[0] / parts[1] / parts[2]
    metrics_path = audit_dir / "metrics.json"

    trades = []
    # Also check state_snapshots.jsonl
    snapshots_path = audit_dir / "state_snapshots.jsonl"
    if snapshots_path.exists():
        with open(snapshots_path) as f:
            for line in f:
                try:
                    trades.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    return trades


def load_state(date_str: str) -> dict:
    """Load latest bot state."""
    state_path = DATA_DIR / "state.json"
    if state_path.exists():
        try:
            return json.load(open(state_path))
        except Exception:
            pass
    return {}


def generate_daily_excel(date_str: str = "") -> str:
    """Generate the daily Excel report."""
    if not date_str:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    decisions = load_decisions(date_str)
    audit_trades = load_audit_trades(date_str)
    state = load_state(date_str)

    # Build trade journal rows
    trade_rows = []
    for d in decisions:
        action = d.get("action", d.get("decision", ""))
        if action in ("HOLD", "FLAT", "WAIT", ""):
            continue

        trade_rows.append({
            "time": d.get("timestamp", d.get("ts", ""))[:19],
            "action": action,
            "direction": d.get("direction", d.get("side", "")),
            "price": d.get("price", d.get("entry_price", 0)),
            "contracts": d.get("contracts", d.get("size", 0)),
            "confluence_score": d.get("confluence_score", d.get("score", 0)),
            "regime": d.get("regime", ""),
            "strategy": d.get("strategy", d.get("lane", "")),
            "pnl": d.get("pnl", d.get("pnl_usd", 0)),
            "reason": d.get("reason", d.get("rationale", ""))[:100],
        })

    # Summary stats
    total_trades = len(trade_rows)
    wins = sum(1 for t in trade_rows if (t.get("pnl") or 0) > 0)
    losses = sum(1 for t in trade_rows if (t.get("pnl") or 0) < 0)
    total_pnl = sum(t.get("pnl", 0) or 0 for t in trade_rows)
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0

    summary_rows = [{
        "metric": "Date",
        "value": date_str,
    }, {
        "metric": "Total Trades",
        "value": total_trades,
    }, {
        "metric": "Wins",
        "value": wins,
    }, {
        "metric": "Losses",
        "value": losses,
    }, {
        "metric": "Win Rate",
        "value": f"{win_rate:.1f}%",
    }, {
        "metric": "Total P&L",
        "value": f"${total_pnl:.2f}",
    }, {
        "metric": "Best Trade",
        "value": f"${max((t.get('pnl', 0) or 0 for t in trade_rows), default=0):.2f}",
    }, {
        "metric": "Worst Trade",
        "value": f"${min((t.get('pnl', 0) or 0 for t in trade_rows), default=0):.2f}",
    }, {
        "metric": "Bot State",
        "value": state.get("mode", state.get("status", "unknown")),
    }]

    # HOLD/FLAT decisions = potential missed setups
    missed_rows = []
    for d in decisions:
        action = d.get("action", d.get("decision", ""))
        if action in ("HOLD", "FLAT"):
            score = d.get("confluence_score", d.get("score", 0))
            if score and score >= 50:  # Had signal but didn't trade
                missed_rows.append({
                    "time": d.get("timestamp", "")[:19],
                    "action": action,
                    "score": score,
                    "regime": d.get("regime", ""),
                    "reason": d.get("reason", d.get("rationale", ""))[:120],
                    "price": d.get("price", 0),
                })

    # Time-of-day performance
    hour_stats = {}
    for t in trade_rows:
        try:
            hour = int(t["time"][11:13])
            if hour not in hour_stats:
                hour_stats[hour] = {"trades": 0, "pnl": 0, "wins": 0}
            hour_stats[hour]["trades"] += 1
            hour_stats[hour]["pnl"] += t.get("pnl", 0) or 0
            if (t.get("pnl", 0) or 0) > 0:
                hour_stats[hour]["wins"] += 1
        except (ValueError, IndexError):
            continue

    time_rows = [
        {
            "hour_utc": f"{h}:00",
            "trades": s["trades"],
            "wins": s["wins"],
            "pnl": f"${s['pnl']:.2f}",
            "win_rate": f"{s['wins']/s['trades']*100:.0f}%" if s["trades"] else "0%",
        }
        for h, s in sorted(hour_stats.items())
    ]

    # Generate Excel
    try:
        from hive_deliverables import generate_excel
        filepath = generate_excel(
            title=f"XLM Bot Daily Report {date_str}",
            sheets={
                "Trade Journal": trade_rows or [{"note": "No trades today"}],
                "Daily Summary": summary_rows,
                "Missed Setups": missed_rows or [{"note": "No high-score misses"}],
                "Time Analysis": time_rows or [{"note": "No time data"}],
            },
        )
        # Copy to bot reports dir
        import shutil
        dest = OUTPUT_DIR / Path(filepath).name
        shutil.copy2(filepath, dest)
        print(f"Report saved: {dest}")
        return str(dest)

    except ImportError:
        # Fallback to CSV
        import csv
        filepath = OUTPUT_DIR / f"xlm_daily_{date_str}.csv"
        with open(filepath, "w", newline="") as f:
            if trade_rows:
                w = csv.DictWriter(f, fieldnames=trade_rows[0].keys())
                w.writeheader()
                w.writerows(trade_rows)
        print(f"CSV fallback saved: {filepath}")
        return str(filepath)


if __name__ == "__main__":
    date = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1].startswith("--date") == False else ""
    if "--date" in sys.argv:
        idx = sys.argv.index("--date")
        date = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else ""
    print(generate_daily_excel(date))
