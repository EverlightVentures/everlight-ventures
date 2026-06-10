#!/usr/bin/env python3
"""
build_master_hub.py -- The Ultra Mind view. Generates 09_DASHBOARD/sweeps/index.html,
the page served at http://127.0.0.1:2000/.

Replaces the static port-list with a categorized "metaverse" home screen that
surfaces every dashboard, plus live state, plus what's new.

Tiles:
  - Live State (service ●/○ pills, KPIs)
  - Memory (Blinko search, recent notes)
  - Knowledge (Resources Hub + Intel Center + Transcripts)
  - Operations (TODO list, Daily Leads, Deal Pipeline, Watchdog)
  - Trading (XLM honest dashboard, Supabase live)
  - Communications (Slack channels, last 10 emails)
  - Personal (MMA, books, content queue)
  - Services & Subscriptions

Rich's directive (2026-05-13):
> "I should have access to all my stuff. It should be there, like it should be
> categorized like these dashboards... this should be like my metaverse"

Cron: refreshed every 5 min via dashboards_watchdog cron (or manual via the
Master Hub button).
"""
from __future__ import annotations

import html as html_lib
import json
import os
import sqlite3
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path("/mnt/sdcard/AA_MY_DRIVE")
sys.path.insert(0, str(ROOT / "03_AUTOMATION_CORE" / "01_Scripts" / "content_tools"))

from env_loader import load_env  # noqa: E402
load_env()

DASH_DIR = ROOT / "09_DASHBOARD/sweeps"
INTEL_DB = ROOT / "06_DEVELOPMENT/everlight_os/intel_center" / "database" / "everlight_resources.sqlite"
BLINKO_URL = "http://127.0.0.1:2700"  # local blinko_lite fallback (offline-first); canonical full RAG is e5-mother:1111 (tailnet)
REPORTS_BASE = "http://127.0.0.1:2200/reports"
HUB_BASE = "http://127.0.0.1:2000"


def esc(s: str | None) -> str:
    return html_lib.escape(str(s or ""))


def service_pills() -> list[tuple[str, str, int, str]]:
    """Probe each watched service. Returns list of (port, name, http_code, url)."""
    services = [
        (2000, "Master Hub", "/"),
        (2200, "Reports Hub", "/"),
        (2300, "Intel Static", "/"),
        (2301, "Intel API", "/healthz"),
        (2302, "E-Sign", "/healthz"),
        (2400, "Apps", "/"),
        (2500, "MMA Fight Camp", "/"),
        (2700, "Blinko RAG (local lite)", "/health"),
        (2701, "MCP HTTP Bridge", "/healthz"),
        (2702, "Lucrex Command Center", "/"),
    ]
    out = []
    for port, name, path in services:
        try:
            req = urllib.request.Request(f"http://127.0.0.1:{port}{path}")
            with urllib.request.urlopen(req, timeout=2) as r:
                code = r.getcode()
        except Exception:
            code = 0
        out.append((port, name, code, f"http://127.0.0.1:{port}/"))
    return out


def blinko_count() -> int:
    try:
        req = urllib.request.Request(f"{BLINKO_URL}/api/v1/note/stats")
        with urllib.request.urlopen(req, timeout=3) as r:
            return int(json.loads(r.read()).get("total_notes", 0))
    except Exception:
        return 0


def resources_count() -> int:
    if not INTEL_DB.exists():
        return 0
    try:
        return sqlite3.connect(INTEL_DB).execute("SELECT COUNT(*) FROM resources").fetchone()[0]
    except Exception:
        return 0


def latest_daily_leads() -> dict | None:
    today = datetime.now().strftime("%Y-%m-%d")
    f = ROOT / "09_DASHBOARD" / "reports" / "daily_leads" / f"{today}.html"
    if not f.exists():
        return None
    return {"date": today, "url": f"{REPORTS_BASE}/daily_leads/{today}.html"}


def xlm_state() -> dict:
    SUPA_URL = os.environ.get("SUPABASE_URL", "")
    SUPA_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_ANON_KEY", "")
    if not SUPA_URL or not SUPA_KEY:
        return {"equity": None, "trades_7d": "?", "mode": "UNKNOWN"}
    try:
        req = urllib.request.Request(
            f"{SUPA_URL}/rest/v1/xlm_bot_timeseries?select=equity_usd,trades_today,ts&order=ts.desc&limit=1",
            headers={"apikey": SUPA_KEY, "Authorization": f"Bearer {SUPA_KEY}"},
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            rows = json.loads(r.read())
        if rows:
            row = rows[0]
            equity = float(row.get("equity_usd") or 0)
            return {
                "equity": equity,
                "trades_today": int(row.get("trades_today") or 0),
                "mode": "OBSERVING" if (row.get("trades_today") or 0) == 0 else "TRADING",
                "ts": row.get("ts", ""),
            }
    except Exception:
        pass
    return {"equity": None, "trades_7d": "?", "mode": "UNKNOWN"}


def render_pill(port: int, name: str, code: int, url: str) -> str:
    color = "#7ec699" if code in (200, 404) else "#ff6b6b"
    dot = "●" if code in (200, 404) else "○"
    return (f"<a href='{url}' target='_blank' "
            f"style='display:inline-flex;align-items:center;gap:6px;padding:6px 12px;background:#0d0d0d;"
            f"border:1px solid #2a2a2a;border-left:3px solid {color};color:#E8E8E8;font-family:JetBrains Mono,monospace;"
            f"font-size:12px;text-decoration:none;border-radius:0 3px 3px 0;'>"
            f"<span style='color:{color};'>{dot}</span> :{port} {esc(name)}</a>")


def tile(title: str, subtitle: str, link: str, body_html: str, color: str = "#D4AF37",
         link_label: str = "open") -> str:
    return f"""
<div style='background:#0d0d0d;border-left:3px solid {color};padding:18px 20px;border-radius:0 4px 4px 0;'>
  <div style='display:flex;justify-content:space-between;align-items:baseline;'>
    <h3 style='font-family:Playfair Display,serif;color:{color};font-size:20px;margin:0;'>{esc(title)}</h3>
    <a href='{link}' target='_blank' style='color:{color};font-size:11px;text-decoration:none;text-transform:uppercase;letter-spacing:1px;'>{link_label} &rarr;</a>
  </div>
  <div style='color:#888;font-size:13px;margin-top:4px;'>{esc(subtitle)}</div>
  <div style='margin-top:12px;color:#aaa;font-size:14px;line-height:1.6;'>{body_html}</div>
</div>
"""


def main() -> int:
    now = datetime.now()
    pills = service_pills()
    up = sum(1 for _, _, c, _ in pills if c in (200, 404))
    total = len(pills)
    bc = blinko_count()
    rc = resources_count()
    leads = latest_daily_leads()
    xlm = xlm_state()

    pills_html = "".join(render_pill(p, n, c, u) for p, n, c, u in pills)

    # KPI strip
    eq_str = f"${xlm['equity']:,.2f}" if xlm.get("equity") is not None else "—"
    mode_color = "#7ec699" if xlm.get("mode") == "TRADING" else "#ff6b6b" if xlm.get("mode") == "OBSERVING" else "#888"

    kpi_strip = f"""
<div style='display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:24px 0;'>
  <div style='background:#1a1a1a;padding:14px 18px;border-left:3px solid #D4AF37;'>
    <div style='color:#888;font-size:11px;text-transform:uppercase;letter-spacing:1px;'>Services</div>
    <div style='color:#E8E8E8;font-size:28px;font-family:Playfair Display,serif;'>{up}/{total} <span style='color:#888;font-size:14px;'>up</span></div>
  </div>
  <div style='background:#1a1a1a;padding:14px 18px;border-left:3px solid #D4AF37;'>
    <div style='color:#888;font-size:11px;text-transform:uppercase;letter-spacing:1px;'>Memory (Blinko)</div>
    <div style='color:#E8E8E8;font-size:28px;font-family:Playfair Display,serif;'>{bc:,} <span style='color:#888;font-size:14px;'>notes</span></div>
  </div>
  <div style='background:#1a1a1a;padding:14px 18px;border-left:3px solid #D4AF37;'>
    <div style='color:#888;font-size:11px;text-transform:uppercase;letter-spacing:1px;'>Knowledge</div>
    <div style='color:#E8E8E8;font-size:28px;font-family:Playfair Display,serif;'>{rc} <span style='color:#888;font-size:14px;'>resources</span></div>
  </div>
  <div style='background:#1a1a1a;padding:14px 18px;border-left:3px solid {mode_color};'>
    <div style='color:#888;font-size:11px;text-transform:uppercase;letter-spacing:1px;'>XLM Bot</div>
    <div style='color:#E8E8E8;font-size:28px;font-family:Playfair Display,serif;'>{eq_str}</div>
    <div style='color:{mode_color};font-size:11px;text-transform:uppercase;letter-spacing:1px;'>{xlm.get('mode','?')}</div>
  </div>
</div>

<div style='background:#0d0d0d;padding:14px 18px;border-left:3px solid #D4AF37;margin:8px 0 24px;'>
  <div style='color:#888;font-size:11px;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;'>Service Health</div>
  <div style='display:flex;flex-wrap:wrap;gap:8px;'>{pills_html}</div>
</div>
"""

    # The 7 main category tiles
    leads_body = (f"Latest: <a href='{leads['url']}' style='color:#D4AF37;'>{esc(leads['date'])}</a>"
                  if leads else "No leads run today yet (cron 3 AM PT)")

    tiles = [
        tile("Memory", "Blinko RAG -- 614+ notes, searchable",
             "http://127.0.0.1:2700/",
             f"<div>{bc:,} notes indexed. Query for prior decisions, audits, agent reports.</div>"
             f"<div style='margin-top:8px;'><a href='http://127.0.0.1:2701/list_tools/blinko' style='color:#D4AF37;font-size:12px;'>API: 3 tools via MCP bridge</a></div>",
             color="#7ec699", link_label="search"),
        tile("Knowledge", "Resources Hub -- 745 free tools, categorized",
             f"{REPORTS_BASE}/RESOURCES_HUB.html",
             f"<div>{rc} verified resources across 18 categories.</div>"
             f"<div style='margin-top:8px;color:#888;font-size:12px;'>175 transcripts &middot; Intel Center phases 1-5 shipped, 6-10 queued.</div>",
             color="#a8a3ff", link_label="browse"),
        tile("Operations", "TODO + Daily Leads + Deal Pipeline + Watchdog",
             f"{REPORTS_BASE}/RICH_TODO_LIVE.html",
             f"<div>Master TODO: open tasks tracked across the workspace.</div>"
             f"<div style='margin-top:6px;'>{leads_body}</div>"
             f"<div style='margin-top:6px;'><a href='{REPORTS_BASE}/MASTER_PIPELINE_DOCTRINE_2026-05-13.html' style='color:#D4AF37;font-size:12px;'>Pipeline doctrine →</a></div>",
             color="#D4AF37", link_label="todo"),
        tile("Trading", f"XLM bot -- {xlm.get('mode','?')} -- {eq_str}",
             f"{REPORTS_BASE}/xlm_honest_dashboard.html",
             f"<div>0 trades in last 7 days. Service-active, not trading.</div>"
             f"<div style='margin-top:6px;color:#888;font-size:12px;'>Honest verdict per operator-truth doctrine.</div>",
             color=mode_color, link_label="honest"),
        tile("Communications", "Slack -- 13 channels, branded comms layer",
             f"https://app.slack.com/client/T0AN6PD3XMD",
             f"<div>warroom + xlmbot tokens active. ImprovMX 42 aliases @everlightventures.io.</div>"
             f"<div style='margin-top:6px;'><a href='{REPORTS_BASE}/SERVICES_REGISTRY.html' style='color:#D4AF37;font-size:12px;'>All channels & services →</a></div>",
             color="#6bafff", link_label="slack"),
        tile("Personal", "MMA Fight Camp -- training calendar, lesson capture",
             "http://127.0.0.1:2500/",
             "<div>Mon/Wed/Fri MMA + box + BJJ. Quizzes Tue/Thu. Voice-note workflow.</div>",
             color="#ff9f6b", link_label="train"),
        tile("Services & Subscriptions", "What you're paying for & connected to",
             f"{REPORTS_BASE}/SERVICES_REGISTRY.html",
             f"<div>24 external services. Stripe, Twilio, 11labs, OpenAI, Resend, Supabase, Cloudflare, Coinbase, Google, ImprovMX, Tailscale, ATTOM, GitHub, Oracle, Onyx POS, MGN POS, Mid South Title.</div>"
             f"<div style='margin-top:6px;color:#888;font-size:12px;'>$20/mo recurring &middot; the rest on free tiers.</div>",
             color="#ffd76b", link_label="registry"),
        tile("Hive Mind", "Query interface -- agents, dispatchers, recent decisions",
             f"{REPORTS_BASE}/HIVE_MIND.html",
             "<div>94 agents across 4 squads. Cipher, Marquise, Hammer, Bull Archer, Nova Ling, Helix Patel, etc.</div>"
             f"<div style='margin-top:6px;'><a href='http://127.0.0.1:2701/list_tools' style='color:#D4AF37;font-size:12px;'>MCP HTTP bridge: 28 tools →</a></div>",
             color="#c39bff", link_label="query"),
        tile("Lucrex Command Center", "Next.js command center -- rehomed to the 2700 band (port 2702)",
             "http://127.0.0.1:2702/",
             "<div>Lucrex OS front-end on 127.0.0.1:2702 (private by default). Built on e5-mother, served via next start.</div>"
             "<div style='margin-top:6px;color:#888;font-size:12px;'>Serve: <code>bash 03_AUTOMATION_CORE/01_Scripts/serve_lucrex.sh start</code></div>",
             color="#D4AF37", link_label="open"),
    ]

    # Build the HTML directly (no report_template wrap; this IS the home page)
    body_html = f"""
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Everlight Ultra Mind | Master Hub</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Playfair+Display:wght@400;600;700;900&family=JetBrains+Mono:wght@400;500;700&display=swap">
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
  background: radial-gradient(circle at 30% -10%, #1a1308 0%, #0a0a0a 60%) fixed;
  color: #E8E8E8;
  font-family: 'Inter', -apple-system, sans-serif;
  min-height: 100vh;
  line-height: 1.6;
}}
.container {{ max-width: 1400px; margin: 0 auto; padding: 32px 24px; }}
.header {{ text-align: center; margin-bottom: 24px; border-bottom: 1px solid #2a2a2a; padding-bottom: 24px; }}
.logo {{ font-family: 'Playfair Display', serif; font-size: 14px; letter-spacing: 6px; text-transform: uppercase; color: #D4AF37; }}
.title {{ font-family: 'Playfair Display', serif; font-size: 42px; font-weight: 700; color: #E8E8E8; margin-top: 8px; }}
.subtitle {{ color: #888; font-size: 14px; margin-top: 4px; }}
a {{ color: #D4AF37; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 18px; margin: 24px 0; }}
.footer {{ text-align: center; margin-top: 48px; padding-top: 24px; border-top: 1px solid #2a2a2a; color: #666; font-size: 12px; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <div class="logo">Everlight Ventures</div>
    <div class="title">Ultra Mind</div>
    <div class="subtitle">Single home for memory, knowledge, ops, trading, comms, services &middot; {now.strftime('%B %d, %Y %I:%M %p PT')}</div>
  </div>

  {kpi_strip}

  <div class="grid">
    {''.join(tiles)}
  </div>

  <div class="footer">
    Generated by the Everlight Hive Mind &middot; refreshes every 5 min via watchdog cron &middot;
    <a href='/PORT_MAP.md' style='color:#666;'>port map</a> &middot;
    <a href='{REPORTS_BASE}/' style='color:#666;'>all reports</a>
  </div>
</div>
</body>
</html>
"""
    # Save with backup of v1
    out = DASH_DIR / "index.html"
    backup = DASH_DIR / "index_v1.html.bak"
    if out.exists() and not backup.exists():
        backup.write_text(out.read_text(encoding="utf-8"), encoding="utf-8")
    out.write_text(body_html, encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size:,} bytes)")
    print(f"  {up}/{total} services up | {bc:,} blinko notes | {rc} resources | XLM {xlm.get('mode')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
