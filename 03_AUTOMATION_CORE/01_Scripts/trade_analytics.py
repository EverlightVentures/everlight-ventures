#!/usr/bin/env python3
"""Trade Analytics Pipeline -- analyzes trades.csv for edge by regime/entry/time.

Usage:
    python3 trade_analytics.py              # full analysis
    python3 trade_analytics.py --brief      # one-page summary
"""

import csv, json, sys
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from zoneinfo import ZoneInfo

PT = ZoneInfo("America/Los_Angeles")
SYNC_DIR = Path("/mnt/sdcard/AA_MY_DRIVE/_logs/sync/xlm_bot_oracle")
REPORT_DIR = Path("/mnt/sdcard/AA_MY_DRIVE/09_DASHBOARD/reports")
REPORT_DIR.mkdir(parents=True, exist_ok=True)


def load_trades():
    p = SYNC_DIR / "trades.csv"
    if not p.exists():
        print(f"No trades.csv at {p}")
        print("Run: bash cloud_monitor.sh --once  (to sync from Oracle)")
        return []
    with open(p) as f:
        return list(csv.DictReader(f))


def parse_ts(ts_str):
    try:
        return datetime.fromisoformat(ts_str[:26].replace("Z", "+00:00"))
    except Exception:
        return None


def analyze_group(trades):
    """Stats for a group of trades."""
    if not trades:
        return None
    wins = [t for t in trades if t.get("result") == "win"]
    losses = [t for t in trades if t.get("result") == "loss"]
    total = len(wins) + len(losses)
    if total == 0:
        return None

    pnls = [float(t.get("pnl_usd", 0)) for t in trades]
    fees = [float(t.get("total_fees_usd", 0)) for t in trades]
    win_pnls = [float(t.get("pnl_usd", 0)) for t in wins]
    loss_pnls = [float(t.get("pnl_usd", 0)) for t in losses]

    return {
        "trades": total,
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(len(wins) / total * 100, 1),
        "gross_pnl": round(sum(pnls), 2),
        "fees": round(sum(fees), 2),
        "net_pnl": round(sum(pnls) - sum(fees), 2),
        "avg_win": round(sum(win_pnls) / len(wins), 2) if wins else 0,
        "avg_loss": round(sum(loss_pnls) / len(losses), 2) if losses else 0,
        "best_trade": round(max(pnls), 2) if pnls else 0,
        "worst_trade": round(min(pnls), 2) if pnls else 0,
        "expectancy": round(sum(pnls) / total, 2),
    }


def by_field(trades, field):
    """Group trades by a CSV field value."""
    groups = defaultdict(list)
    for t in trades:
        val = t.get(field, "unknown")
        groups[val].append(t)
    return {k: analyze_group(v) for k, v in groups.items() if analyze_group(v)}


def by_hour(trades):
    """Group trades by hour of day (PT)."""
    groups = defaultdict(list)
    for t in trades:
        dt = parse_ts(t.get("timestamp", ""))
        if dt:
            hour = dt.astimezone(PT).hour
            groups[f"{hour:02d}:00"].append(t)
    return {k: analyze_group(v) for k, v in sorted(groups.items()) if analyze_group(v)}


def format_table(title, data, sort_by="net_pnl"):
    """Format analysis group as markdown table."""
    if not data:
        return f"### {title}\nNo data.\n"

    sorted_items = sorted(data.items(), key=lambda x: x[1].get(sort_by, 0), reverse=True)
    lines = [
        f"### {title}",
        "| Category | Trades | WR | Net PnL | Avg Win | Avg Loss | Expectancy |",
        "|----------|--------|----|---------|---------|----------|------------|",
    ]
    for name, stats in sorted_items:
        lines.append(
            f"| {name} | {stats['trades']} | {stats['win_rate']}% "
            f"| ${stats['net_pnl']:+.2f} | ${stats['avg_win']:+.2f} "
            f"| ${stats['avg_loss']:+.2f} | ${stats['expectancy']:+.2f} |"
        )
    lines.append("")
    return "\n".join(lines)


def generate_analytics(brief=False):
    trades = load_trades()
    if not trades:
        return "# Trade Analytics\n\nNo trades found."

    overall = analyze_group(trades)
    now_pt = datetime.now(PT).strftime("%Y-%m-%d %I:%M %p PT")

    lines = [
        "# Trade Analytics Report",
        f"Generated: {now_pt}",
        f"Total trades analyzed: {len(trades)}",
        "",
    ]

    if overall:
        lines.extend([
            "## Overall Performance",
            f"- Trades: {overall['trades']} (W:{overall['wins']} L:{overall['losses']})",
            f"- Win rate: {overall['win_rate']}%",
            f"- Gross PnL: ${overall['gross_pnl']:+.2f}",
            f"- Fees: ${overall['fees']:.2f}",
            f"- **Net PnL: ${overall['net_pnl']:+.2f}**",
            f"- Expectancy per trade: ${overall['expectancy']:+.2f}",
            f"- Best trade: ${overall['best_trade']:+.2f}",
            f"- Worst trade: ${overall['worst_trade']:+.2f}",
            "",
        ])

    if brief:
        return "\n".join(lines)

    # Edge analysis by different dimensions
    lines.append(format_table("By Side (Long vs Short)", by_field(trades, "side")))
    lines.append(format_table("By Exit Reason", by_field(trades, "exit_reason")))
    lines.append(format_table("By Hour of Day (PT)", by_hour(trades), sort_by="win_rate"))

    # Leverage math section
    lines.extend([
        "## 4x Leverage Math",
        "At 4x leverage on XLP-20DEC30-CDE:",
        "- 1% XLM move = 4% account return",
        "- 5% XLM move = 20% account return",
        "- 10% XLM move = 40% account return",
        "- 20% XLM move = 80% account return",
        "",
        "Compounding targets:",
        "- 100% return (2x): ~4 winning 20% trades",
        "- 500% return (6x): ~9 winning 20% trades",
        "- 1000% return (11x): ~13 winning 20% trades",
        "",
    ])

    return "\n".join(lines)


if __name__ == "__main__":
    brief = "--brief" in sys.argv
    report = generate_analytics(brief)
    out = REPORT_DIR / "trade_analytics.md"
    out.write_text(report)
    print(report)
    print(f"\nSaved to: {out}")
