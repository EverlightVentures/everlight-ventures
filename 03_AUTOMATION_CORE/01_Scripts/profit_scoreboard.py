#!/usr/bin/env python3
"""Profit Scoreboard -- weekly/monthly ROI summary from trades.csv.

Usage:
    python3 profit_scoreboard.py              # current week + month
    python3 profit_scoreboard.py --slack      # also post to Slack
"""

import json, csv, sys, os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from collections import defaultdict

PT = ZoneInfo("America/Los_Angeles")
SYNC_DIR = Path("/mnt/sdcard/AA_MY_DRIVE/_logs/sync/xlm_bot_oracle")
REPORT_DIR = Path("/mnt/sdcard/AA_MY_DRIVE/09_DASHBOARD/reports")
REPORT_DIR.mkdir(parents=True, exist_ok=True)

INFRA_COST_DAILY = 0.0  # Oracle free tier


def load_trades():
    p = SYNC_DIR / "trades.csv"
    if not p.exists():
        return []
    with open(p) as f:
        return list(csv.DictReader(f))


def parse_ts(ts_str):
    try:
        return datetime.fromisoformat(ts_str[:26].replace("Z", "+00:00"))
    except Exception:
        return None


def bucket_trades(trades):
    """Group trades by day, week, month."""
    by_day = defaultdict(list)
    by_week = defaultdict(list)
    by_month = defaultdict(list)

    for t in trades:
        dt = parse_ts(t.get("timestamp", ""))
        if not dt:
            continue
        dt_pt = dt.astimezone(PT)
        by_day[dt_pt.strftime("%Y-%m-%d")].append(t)
        # ISO week
        by_week[dt_pt.strftime("%Y-W%W")].append(t)
        by_month[dt_pt.strftime("%Y-%m")].append(t)

    return by_day, by_week, by_month


def summarize(trades, days=1):
    wins = sum(1 for t in trades if t.get("result") == "win")
    losses = sum(1 for t in trades if t.get("result") == "loss")
    total = wins + losses
    wr = f"{wins/total*100:.0f}%" if total > 0 else "N/A"
    pnl = sum(float(t.get("pnl_usd", 0)) for t in trades)
    fees = sum(float(t.get("total_fees_usd", 0)) for t in trades)
    infra = INFRA_COST_DAILY * days
    net = pnl - fees - infra

    # Streaks
    max_win_streak = 0
    max_loss_streak = 0
    cur_win = 0
    cur_loss = 0
    for t in trades:
        if t.get("result") == "win":
            cur_win += 1
            cur_loss = 0
            max_win_streak = max(max_win_streak, cur_win)
        elif t.get("result") == "loss":
            cur_loss += 1
            cur_win = 0
            max_loss_streak = max(max_loss_streak, cur_loss)

    return {
        "trades": total,
        "wins": wins,
        "losses": losses,
        "win_rate": wr,
        "gross_pnl": round(pnl, 2),
        "fees": round(fees, 2),
        "infra_cost": round(infra, 2),
        "net_pnl": round(net, 2),
        "max_win_streak": max_win_streak,
        "max_loss_streak": max_loss_streak,
        "avg_win": round(
            sum(float(t.get("pnl_usd", 0)) for t in trades if t.get("result") == "win") / wins, 2
        ) if wins > 0 else 0,
        "avg_loss": round(
            sum(float(t.get("pnl_usd", 0)) for t in trades if t.get("result") == "loss") / losses, 2
        ) if losses > 0 else 0,
    }


def format_section(title, stats):
    return f"""### {title}
- Trades: {stats['trades']} (W:{stats['wins']} L:{stats['losses']}) | WR: {stats['win_rate']}
- Gross PnL: ${stats['gross_pnl']:+.2f}
- Fees: ${stats['fees']:.2f} | Infra: ${stats['infra_cost']:.2f}
- **Net PnL: ${stats['net_pnl']:+.2f}**
- Avg win: ${stats['avg_win']:+.2f} | Avg loss: ${stats['avg_loss']:+.2f}
- Best streak: {stats['max_win_streak']}W | Worst: {stats['max_loss_streak']}L"""


def generate_scoreboard():
    trades = load_trades()
    if not trades:
        return "# Profit Scoreboard\n\nNo trades found."

    by_day, by_week, by_month = bucket_trades(trades)
    now_pt = datetime.now(PT)

    # Current week
    cur_week = now_pt.strftime("%Y-W%W")
    week_trades = by_week.get(cur_week, [])
    week_days = now_pt.weekday() + 1

    # Current month
    cur_month = now_pt.strftime("%Y-%m")
    month_trades = by_month.get(cur_month, [])
    month_days = now_pt.day

    # All time
    all_stats = summarize(trades, days=len(by_day))

    lines = [
        f"# Profit Scoreboard",
        f"Generated: {now_pt.strftime('%Y-%m-%d %I:%M %p PT')}",
        "",
        format_section(f"This Week ({cur_week})", summarize(week_trades, week_days)),
        "",
        format_section(f"This Month ({cur_month})", summarize(month_trades, month_days)),
        "",
        format_section("All Time", all_stats),
        "",
        "### Daily Breakdown",
        "| Date | Trades | W/L | PnL | Fees | Net |",
        "|------|--------|-----|-----|------|-----|",
    ]

    for day in sorted(by_day.keys(), reverse=True)[:14]:
        dt = by_day[day]
        s = summarize(dt)
        lines.append(
            f"| {day} | {s['trades']} | {s['wins']}/{s['losses']} "
            f"| ${s['gross_pnl']:+.2f} | ${s['fees']:.2f} | ${s['net_pnl']:+.2f} |"
        )

    lines.append("")
    return "\n".join(lines)


def slack_post(msg):
    webhook = os.environ.get("SLACK_WEBHOOK_URL", "")
    if not webhook:
        # Try reading from synced config
        try:
            import yaml
            cfg = yaml.safe_load(open(
                "/mnt/sdcard/AA_MY_DRIVE/xlm_bot/config.yaml"
            ))
            webhook = cfg.get("slack_webhook_url", "")
        except Exception:
            pass
    if webhook:
        import urllib.request
        req = urllib.request.Request(
            webhook,
            data=json.dumps({"text": msg}).encode(),
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=10)


if __name__ == "__main__":
    report = generate_scoreboard()
    out = REPORT_DIR / "profit_scoreboard.md"
    out.write_text(report)
    print(report)
    print(f"\nSaved to: {out}")

    if "--slack" in sys.argv:
        slack_post(report)
        print("Posted to Slack.")
