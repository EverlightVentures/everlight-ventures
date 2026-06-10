#!/usr/bin/env python3
"""
build_xlm_honest_dashboard.py -- The truth about the XLM bot.

Per memory rule feedback_operator_truth_doctrine.md:
> Service-active is never proof of work.
> "It's running" != "It's trading"

This page tells the unembellished truth:
  - Equity (live from Supabase)
  - Days since last trade
  - Mode: OBSERVING (no trades) | TRADING (>=1 in last 7d)
  - 7d / 30d realized P&L
  - Honest verdict line

Output: 09_DASHBOARD/reports/xlm_honest_dashboard.html
Cron suggested: 0 * * * * (hourly refresh)
"""
from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path("/mnt/sdcard/AA_MY_DRIVE")
sys.path.insert(0, str(ROOT / "03_AUTOMATION_CORE" / "01_Scripts" / "content_tools"))

from env_loader import load_env  # noqa: E402
load_env()
from report_template import render_report  # noqa: E402

SUPA_URL = os.environ.get("SUPABASE_URL", "https://jdqqmsmwmbsnlnstyavl.supabase.co").rstrip("/")
SUPA_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_ANON_KEY", "")


def supa_get(path: str) -> list:
    url = f"{SUPA_URL}/rest/v1/{path}"
    req = urllib.request.Request(
        url,
        headers={
            "apikey": SUPA_KEY,
            "Authorization": f"Bearer {SUPA_KEY}",
        },
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


def main() -> int:
    ts_now = datetime.now(timezone.utc)
    out_path = ROOT / "09_DASHBOARD" / "reports" / "xlm_honest_dashboard.html"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. Latest 5 timeseries rows (status snapshot)
    try:
        recent = supa_get("xlm_bot_timeseries?select=ts,equity_usd,pnl_today_usd,trades_today,win_rate_pct&order=ts.desc&limit=5")
    except Exception as e:
        recent = []
        err = str(e)
    else:
        err = None

    if not recent:
        body = f"<p style='color:#ff6b6b;'>UNREACHABLE: {err or 'no data'}</p>"
        html = render_report(title="XLM Honest Dashboard -- UNREACHABLE",
                             content_html=body, agent_name="Hive Trading", agent_title="Truth Layer")
        out_path.write_text(html, encoding="utf-8")
        print(f"wrote (error state) {out_path}")
        return 1

    latest = recent[0]
    equity = float(latest.get("equity_usd") or 0)
    trades_today = int(latest.get("trades_today") or 0)
    pnl_today = float(latest.get("pnl_today_usd") or 0)
    win_rate = float(latest.get("win_rate_pct") or 0)
    last_ts = latest.get("ts", "")

    # 2. Trades count over last 7 days
    seven_days_ago = (ts_now - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%S")
    try:
        seven_day_rows = supa_get(f"xlm_bot_timeseries?select=ts,trades_today,equity_usd&ts=gt.{urllib.parse.quote(seven_days_ago)}&order=ts.desc&limit=10080")
    except Exception:
        seven_day_rows = []

    trades_7d = max([int(r.get("trades_today") or 0) for r in seven_day_rows], default=0)
    equity_7d_ago = float(seven_day_rows[-1].get("equity_usd") or equity) if seven_day_rows else equity
    equity_change_7d = equity - equity_7d_ago

    # 3. Days since last actual trade (look back through xlm_bot_report_history)
    try:
        reports = supa_get("xlm_bot_report_history?select=*&order=created_at.desc&limit=20")
    except Exception:
        try:
            reports = supa_get("xlm_bot_report_history?select=*&order=ts.desc&limit=20")
        except Exception:
            reports = []

    last_trade_date = None
    for r in reports:
        # heuristic: if any report has trades_today > 0 OR contains "trade" in summary
        body_text = json.dumps(r)
        if "trade" in body_text.lower() and ("opened" in body_text.lower() or "closed" in body_text.lower() or "entered" in body_text.lower()):
            ts = r.get("created_at") or r.get("ts") or r.get("inserted_at")
            if ts:
                try:
                    last_trade_date = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                except Exception:
                    pass
                break

    days_since_trade = (ts_now - last_trade_date).days if last_trade_date else None
    if days_since_trade is None:
        days_since_trade_text = "unknown -- no recent reports mention trades"
    else:
        days_since_trade_text = f"{days_since_trade} days ago ({last_trade_date.strftime('%Y-%m-%d')})"

    # 4. Mode classification
    if trades_7d > 0:
        mode = "TRADING"
        mode_color = "#7ec699"
        verdict = f"Bot opened {trades_7d} trade(s) this week. Live trading mode."
    else:
        mode = "OBSERVING"
        mode_color = "#ff6b6b"
        verdict = ("Bot is signal-generating but NOT trading. "
                   "Either the approval gate / confidence threshold is too high, "
                   "or the strategy hasn't found qualifying setups. "
                   "Service-active is not the same as trading-active.")

    # 5. Most recent report content (what the bot is "thinking")
    last_report = reports[0] if reports else {}
    last_report_summary = ""
    for k in ("summary", "report", "content", "body", "notes"):
        v = last_report.get(k)
        if v and isinstance(v, str):
            last_report_summary = v[:600]
            break
    if not last_report_summary and last_report:
        last_report_summary = json.dumps({k: v for k, v in last_report.items() if k not in ("id",)}, indent=2)[:600]

    # Render
    body = f"""
<div style='display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px;margin:20px 0;'>
  <div style='background:#0d0d0d;padding:20px;border-left:3px solid #D4AF37;'>
    <div style='color:#888;font-size:12px;text-transform:uppercase;letter-spacing:1px;'>Equity</div>
    <div style='color:#E8E8E8;font-size:36px;font-family:Playfair Display,serif;margin-top:4px;'>${equity:,.2f}</div>
    <div style='color:#888;font-size:12px;margin-top:4px;'>{'+' if equity_change_7d >= 0 else ''}${equity_change_7d:,.2f} in 7d</div>
  </div>

  <div style='background:#0d0d0d;padding:20px;border-left:3px solid {mode_color};'>
    <div style='color:#888;font-size:12px;text-transform:uppercase;letter-spacing:1px;'>Mode</div>
    <div style='color:{mode_color};font-size:36px;font-family:Playfair Display,serif;margin-top:4px;'>{mode}</div>
    <div style='color:#888;font-size:12px;margin-top:4px;'>{trades_7d} trades in last 7 days</div>
  </div>

  <div style='background:#0d0d0d;padding:20px;border-left:3px solid #D4AF37;'>
    <div style='color:#888;font-size:12px;text-transform:uppercase;letter-spacing:1px;'>Last Trade</div>
    <div style='color:#E8E8E8;font-size:24px;font-family:Playfair Display,serif;margin-top:4px;'>{days_since_trade_text}</div>
  </div>

  <div style='background:#0d0d0d;padding:20px;border-left:3px solid #D4AF37;'>
    <div style='color:#888;font-size:12px;text-transform:uppercase;letter-spacing:1px;'>Today PnL</div>
    <div style='color:#E8E8E8;font-size:24px;font-family:Playfair Display,serif;margin-top:4px;'>${pnl_today:,.2f}</div>
    <div style='color:#888;font-size:12px;margin-top:4px;'>win rate: {win_rate:.0f}%</div>
  </div>
</div>

<h2 style='font-family:Playfair Display,serif;color:#D4AF37;font-size:22px;margin-top:32px;'>Honest Verdict</h2>
<div style='background:#1a1a1a;padding:20px;border-left:3px solid {mode_color};margin:12px 0;'>
  <p style='color:#E8E8E8;line-height:1.7;'>{verdict}</p>
</div>

<h2 style='font-family:Playfair Display,serif;color:#D4AF37;font-size:22px;margin-top:32px;'>Latest Bot Report (what it's thinking)</h2>
<pre style='background:#0d0d0d;color:#E8E8E8;padding:16px;border-left:3px solid #D4AF37;overflow-x:auto;font-family:JetBrains Mono,monospace;font-size:13px;line-height:1.5;'>{last_report_summary or '(no recent report)'}</pre>

<h2 style='font-family:Playfair Display,serif;color:#D4AF37;font-size:22px;margin-top:32px;'>Last 5 Heartbeats</h2>
<table style='width:100%;border-collapse:collapse;font-size:14px;'>
  <thead>
    <tr style='background:#1a1a1a;color:#D4AF37;'>
      <th style='padding:8px;text-align:left;border-bottom:2px solid #D4AF37;'>Timestamp</th>
      <th style='padding:8px;text-align:right;border-bottom:2px solid #D4AF37;'>Equity</th>
      <th style='padding:8px;text-align:right;border-bottom:2px solid #D4AF37;'>Trades</th>
      <th style='padding:8px;text-align:right;border-bottom:2px solid #D4AF37;'>PnL</th>
      <th style='padding:8px;text-align:right;border-bottom:2px solid #D4AF37;'>Win%</th>
    </tr>
  </thead>
  <tbody>
""" + "".join(
        f"<tr><td style='padding:8px;border-bottom:1px solid #2a2a2a;'>{r.get('ts','')[:19]}</td>"
        f"<td style='padding:8px;border-bottom:1px solid #2a2a2a;text-align:right;'>${float(r.get('equity_usd') or 0):,.2f}</td>"
        f"<td style='padding:8px;border-bottom:1px solid #2a2a2a;text-align:right;'>{int(r.get('trades_today') or 0)}</td>"
        f"<td style='padding:8px;border-bottom:1px solid #2a2a2a;text-align:right;'>${float(r.get('pnl_today_usd') or 0):,.2f}</td>"
        f"<td style='padding:8px;border-bottom:1px solid #2a2a2a;text-align:right;'>{float(r.get('win_rate_pct') or 0):.0f}%</td></tr>"
        for r in recent
    ) + """
  </tbody>
</table>

<p style='color:#888;font-size:12px;margin-top:24px;'>
Last refresh: """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S PT") + """ | Data source: Supabase xlm_bot_timeseries + xlm_bot_report_history
</p>
"""
    html = render_report(
        title=f"XLM Bot Honest Dashboard -- {mode}",
        content_html=body,
        agent_name="Hive Trading Truth Layer",
        agent_title="Operator Truth Doctrine",
    )
    out_path.write_text(html, encoding="utf-8")
    print(f"wrote {out_path} ({out_path.stat().st_size:,} bytes)")
    print(f"  mode={mode}  equity=${equity:.2f}  trades_7d={trades_7d}  last_trade={days_since_trade_text}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
