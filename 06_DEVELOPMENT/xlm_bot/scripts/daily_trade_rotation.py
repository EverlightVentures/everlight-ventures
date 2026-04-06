#!/usr/bin/env python3
"""Daily trade log rotation. Run at 11:59 PM PT via cron.

1. Reads trades_organized.csv
2. Archives completed trades into monthly files: trades_2026-04.csv
3. Keeps current month in trades_organized.csv
4. Re-runs the organizer to keep columns fresh
5. Posts daily summary to Slack

Cron: 59 6 * * * cd /home/opc/xlm-bot && python3 scripts/daily_trade_rotation.py
(6:59 UTC = 11:59 PM PT)
"""
import csv
import json
import os
import shutil
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

BOT_DIR = Path(os.environ.get("CRYPTO_BOT_DIR", "/home/opc/xlm-bot"))
LOGS_DIR = BOT_DIR / "logs"
ARCHIVE_DIR = LOGS_DIR / "monthly"
ARCHIVE_DIR.mkdir(exist_ok=True)

PT = timedelta(hours=-7)


def get_pt_now():
    return datetime.now(timezone.utc) + PT


def rotate():
    trades_file = LOGS_DIR / "trades_organized.csv"
    if not trades_file.exists():
        trades_file = LOGS_DIR / "trades.csv"
    if not trades_file.exists():
        print("No trades file found.")
        return

    with open(trades_file) as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames
        rows = list(reader)

    now = get_pt_now()
    current_month = now.strftime("%Y-%m")

    # Group by month
    months = {}
    for r in rows:
        date_pt = r.get("date_pt", "")
        if not date_pt or len(date_pt) < 7:
            # Try parsing from timestamp
            ts = r.get("entry_time") or r.get("timestamp", "")
            try:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                pt_dt = dt + PT
                date_pt = pt_dt.strftime("%Y-%m-%d")
            except Exception:
                date_pt = current_month + "-01"
        month = date_pt[:7]
        if month not in months:
            months[month] = []
        months[month].append(r)

    # Archive past months (not current)
    for month, month_rows in months.items():
        if month == current_month:
            continue
        archive_file = ARCHIVE_DIR / f"trades_{month}.csv"
        # Append if exists, create if not
        write_header = not archive_file.exists()
        with open(archive_file, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            if write_header:
                writer.writeheader()
            writer.writerows(month_rows)
        print(f"Archived {len(month_rows)} trades to {archive_file.name}")

    # Keep only current month in main file
    current_rows = months.get(current_month, [])
    with open(trades_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(current_rows)
    print(f"Main file: {len(current_rows)} trades (current month {current_month})")

    return current_rows


def daily_summary_to_slack():
    """Post today's trade summary to Slack."""
    trades_file = LOGS_DIR / "trades_organized.csv"
    if not trades_file.exists():
        return

    now = get_pt_now()
    today = now.strftime("%Y-%m-%d")

    with open(trades_file) as f:
        reader = csv.DictReader(f)
        today_trades = [r for r in reader
                        if r.get("date_pt") == today
                        and r.get("exit_price")
                        and r.get("pnl_usd")]

    if not today_trades:
        return

    wins = sum(1 for t in today_trades if t.get("result") == "win")
    losses = sum(1 for t in today_trades if t.get("result") == "loss")
    total = wins + losses
    pnl = sum(float(t.get("pnl_usd", 0)) for t in today_trades)
    fees = sum(float(t.get("total_fees_usd", 0)) for t in today_trades)
    wr = f"{wins/total*100:.0f}%" if total > 0 else "N/A"

    day_name = now.strftime("%A")
    msg = (
        f"*XLM Bot Daily Close -- {day_name} {today}*\n"
        f"Trades: {total} ({wins}W / {losses}L) | WR: {wr}\n"
        f"Net P&L: ${pnl:+.2f} | Fees: ${fees:.2f}\n"
    )

    # Add best/worst trade
    if today_trades:
        best = max(today_trades, key=lambda t: float(t.get("pnl_usd", 0)))
        worst = min(today_trades, key=lambda t: float(t.get("pnl_usd", 0)))
        msg += f"Best: {best['side']} ${float(best['pnl_usd']):+.2f} | Worst: {worst['side']} ${float(worst['pnl_usd']):+.2f}"

    token = os.environ.get("SLACK_BOT_TOKEN", "")
    if token:
        try:
            data = json.dumps({"channel": "C0AN8SG030W", "text": msg}).encode()
            req = urllib.request.Request(
                "https://slack.com/api/chat.postMessage",
                data=data, method="POST",
                headers={"Content-Type": "application/json",
                         "Authorization": f"Bearer {token}"},
            )
            urllib.request.urlopen(req, timeout=10)
            print(f"Posted daily summary to Slack")
        except Exception as e:
            print(f"Slack post failed: {e}")


if __name__ == "__main__":
    rotate()
    daily_summary_to_slack()
