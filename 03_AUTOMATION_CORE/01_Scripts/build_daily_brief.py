#!/usr/bin/env python3
"""
build_daily_brief.py -- The "sciencey articles" feeling Rich asked for.

Per the new Phoenix v3 doctrine: this brief is what the Intel Center catalog
EARNS its keep on. Instead of paying Perplexity for "what's new", we surface:

  - Top resources per focus category (Trading, OSINT, Science, Tech, etc)
  - Recent Blinko notes that mention focus topics
  - Pipeline state summary (deal events, lead intake)
  - Honest XLM bot state

Renders to 09_DASHBOARD/reports/daily_brief/YYYY-MM-DD.html (branded HTML).
Posts top-3 items to #ceo-brief via branded_slack.

Cron: 0 14 * * *   (6 AM PT in UTC)
Manual: python3 build_daily_brief.py --date today
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path("/mnt/sdcard/AA_MY_DRIVE")
sys.path.insert(0, str(ROOT / "03_AUTOMATION_CORE" / "01_Scripts" / "content_tools"))
sys.path.insert(0, str(ROOT / "06_DEVELOPMENT/everlight_os/intel_center" / "lib"))

from env_loader import load_env  # noqa: E402
load_env()
from report_template import render_report  # noqa: E402

# Rich's focus areas (per CarMax thesis + current ops emphasis)
FOCUS_CATEGORIES = [
    ("Decision Intelligence", "#D4A843"),
    ("OSINT & Investigation", "#7ec699"),
    ("Trading & Finance", "#ff9f6b"),
    ("Real Estate & Property", "#a8a3ff"),
    ("News & Journalism", "#ff6b9f"),
    ("AI & Automation", "#6bafff"),
    ("Content Creation", "#ffd76b"),
    ("Self-Hosting & Privacy", "#6bafff"),
]


def intel_top_per_category(limit_per_cat: int = 4) -> dict[str, list]:
    from intel_query import search, list_categories  # type: ignore
    out = {}
    for cat, _ in FOCUS_CATEGORIES:
        # Use the existing token-OR search with a generic query that matches everything in the cat
        # Trick: search with a stopword the search() function rejects -> falls through to category filter only.
        # Simpler: hit SQLite directly via the same conn.
        import sqlite3
        db = ROOT / "06_DEVELOPMENT/everlight_os/intel_center" / "database" / "everlight_resources.sqlite"
        conn = sqlite3.connect(db)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT name, purpose, use_case, agent_owner, cost_level, url, tags "
            "FROM resources WHERE category = ? "
            "AND verified_status = 'checked' "
            "ORDER BY CAST(COALESCE(NULLIF(priority_score, ''), '0') AS INTEGER) DESC, name "
            "LIMIT ?",
            (cat, limit_per_cat),
        ).fetchall()
        out[cat] = [dict(r) for r in rows]
    return out


def xlm_snapshot() -> dict:
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_ANON_KEY", "")
    if not url or not key:
        return {}
    try:
        req = urllib.request.Request(
            f"{url}/rest/v1/xlm_bot_timeseries?select=equity_usd,trades_today,pnl_today_usd,ts&order=ts.desc&limit=1",
            headers={"apikey": key, "Authorization": f"Bearer {key}"},
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            rows = json.loads(r.read())
        return rows[0] if rows else {}
    except Exception:
        return {}


def blinko_recent(query: str = "", limit: int = 5) -> list[dict]:
    try:
        payload = json.dumps({"searchText": query, "page": 1, "size": limit}).encode()
        req = urllib.request.Request(
            "http://127.0.0.1:2700/api/v1/note/list",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=6) as r:
            j = json.loads(r.read())
        items = j.get("items") if isinstance(j, dict) else j
        return items[:limit] if items else []
    except Exception:
        return []


def pipeline_snapshot() -> dict:
    import sqlite3
    db = ROOT / "01_BUSINESSES" / "Everlight_Ventures" / "Wholesale" / "audit" / "deal_execution.sqlite"
    if not db.exists():
        return {}
    try:
        c = sqlite3.connect(db)
        c.row_factory = sqlite3.Row
        rows = c.execute(
            "SELECT deal_key, COUNT(*) c, MAX(ts) last_ts FROM deal_events "
            "GROUP BY deal_key ORDER BY last_ts DESC LIMIT 5"
        ).fetchall()
        return {"pipelines": [dict(r) for r in rows]}
    except Exception:
        return {}


def render_html(date_str: str, intel: dict, xlm: dict, notes: list, pipelines: dict) -> str:
    # XLM strip
    eq = float(xlm.get("equity_usd") or 0)
    trades = int(xlm.get("trades_today") or 0)
    mode_color = "#7ec699" if trades > 0 else "#ff6b6b"
    mode = "TRADING" if trades > 0 else "OBSERVING"

    strip = f"""
<div style='display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin:20px 0;'>
  <div style='background:#1a1a1a;padding:14px 18px;border-left:3px solid #D4A843;'>
    <div style='color:#888;font-size:11px;text-transform:uppercase;'>Date</div>
    <div style='color:#E8E8E8;font-size:22px;font-family:Playfair Display,serif;'>{date_str}</div>
  </div>
  <div style='background:#1a1a1a;padding:14px 18px;border-left:3px solid {mode_color};'>
    <div style='color:#888;font-size:11px;text-transform:uppercase;'>XLM Bot</div>
    <div style='color:#E8E8E8;font-size:22px;font-family:Playfair Display,serif;'>${eq:,.2f}</div>
    <div style='color:{mode_color};font-size:11px;'>{mode} &middot; {trades} trades today</div>
  </div>
  <div style='background:#1a1a1a;padding:14px 18px;border-left:3px solid #D4A843;'>
    <div style='color:#888;font-size:11px;text-transform:uppercase;'>Pipelines</div>
    <div style='color:#E8E8E8;font-size:22px;font-family:Playfair Display,serif;'>{len(pipelines.get("pipelines", []))}</div>
    <div style='color:#888;font-size:11px;'>active deal keys</div>
  </div>
  <div style='background:#1a1a1a;padding:14px 18px;border-left:3px solid #D4A843;'>
    <div style='color:#888;font-size:11px;text-transform:uppercase;'>Memory Hits</div>
    <div style='color:#E8E8E8;font-size:22px;font-family:Playfair Display,serif;'>{len(notes)}</div>
    <div style='color:#888;font-size:11px;'>recent Blinko notes</div>
  </div>
</div>
"""
    # Category sections
    sections = []
    for cat, color in FOCUS_CATEGORIES:
        items = intel.get(cat, [])
        if not items:
            continue
        rows_html = ""
        for r in items:
            name = r.get("name") or "?"
            use = (r.get("use_case") or "")[:140]
            agent = r.get("agent_owner") or "—"
            url = r.get("url") or ""
            link_html = (f"<a href='{url}' target='_blank' style='color:{color};font-size:11px;text-decoration:none;'>→ open</a>" if url else "")
            rows_html += (f"<div style='background:#0d0d0d;border-left:3px solid {color};padding:10px 14px;margin:6px 0;'>"
                          f"<div style='display:flex;justify-content:space-between;'>"
                          f"<strong style='color:#E8E8E8;'>{name}</strong>"
                          f"<span style='color:#666;font-size:11px;'>{agent}</span></div>"
                          f"<div style='color:#aaa;font-size:12px;margin-top:4px;'>{use}</div>"
                          f"{link_html}</div>")
        sections.append(f"""
<h3 style='font-family:Playfair Display,serif;color:{color};font-size:18px;margin:24px 0 8px;border-bottom:1px solid #2a2a2a;padding-bottom:6px;'>
  {cat} <span style='color:#666;font-size:13px;font-family:Inter,sans-serif;'>(top {len(items)})</span>
</h3>
{rows_html}
""")

    # Memory section
    mem_html = ""
    if notes:
        mem_html = "<h3 style='font-family:Playfair Display,serif;color:#D4A843;font-size:18px;margin:24px 0 8px;'>From Memory (Blinko, recent)</h3>"
        for n in notes[:5]:
            content = (n.get("content") or "")[:200]
            mem_html += f"<div style='background:#0d0d0d;border-left:3px solid #D4A843;padding:10px 14px;margin:6px 0;font-size:12px;color:#aaa;'>{content}…</div>"

    # Pipeline section
    pipe_html = ""
    if pipelines.get("pipelines"):
        pipe_html = "<h3 style='font-family:Playfair Display,serif;color:#D4A843;font-size:18px;margin:24px 0 8px;'>Active Deal Pipelines</h3>"
        for p in pipelines["pipelines"][:5]:
            pipe_html += (f"<div style='background:#0d0d0d;border-left:3px solid #D4A843;padding:10px 14px;margin:6px 0;'>"
                          f"<code style='color:#D4A843;'>{p.get('deal_key','?')}</code> "
                          f"&middot; {p.get('c',0)} events &middot; last {p.get('last_ts','?')[:19]}</div>")

    body = f"""
<p style='color:#888;font-size:14px;'>
6 AM PT briefing across Rich's focus areas. Surface free Intel Center resources
first, then Blinko memory, then live ops state. Per HARD LAW
<code style='background:#1a1a1a;color:#D4A843;padding:2px 6px;'>tool-search-first</code>.
</p>
{strip}
<h2 style='font-family:Playfair Display,serif;color:#D4A843;font-size:24px;margin-top:32px;border-bottom:2px solid #D4A843;padding-bottom:6px;'>
  Intelligence Surfaces
</h2>
{''.join(sections)}
{mem_html}
{pipe_html}
"""
    return render_report(
        title=f"Daily Brief -- {date_str}",
        content_html=body,
        agent_name="Marcus Cole",
        agent_title="Chief Operator",
    )


def post_slack(date_str: str, out_path: Path, top_picks: list[dict]) -> None:
    try:
        from branded_slack import post_branded_slack  # type: ignore
    except Exception:
        return
    body_lines = []
    for p in top_picks[:3]:
        body_lines.append(f"• *{p.get('name','?')}* — {p.get('cat','?')}")
    body = "\n".join(body_lines) if body_lines else "No fresh items today."
    try:
        post_branded_slack(
            channel="#ceo-brief",
            title=f"Daily Brief — {date_str}",
            summary=f"Top {len(top_picks)} from your focus areas",
            body=body,
            report_url=f"http://127.0.0.1:2200/reports/daily_brief/{date_str}.html",
            agent_name="Marcus Cole",
            agent_title="Chief Operator",
            category="report",
        )
    except Exception:
        pass


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="today")
    ap.add_argument("--no-slack", action="store_true")
    args = ap.parse_args()

    if args.date == "today":
        date_str = datetime.now().strftime("%Y-%m-%d")
    else:
        date_str = args.date

    intel = intel_top_per_category(limit_per_cat=4)
    xlm = xlm_snapshot()
    notes = blinko_recent("wholesale OR deal OR trading", limit=5)
    pipelines = pipeline_snapshot()

    html = render_html(date_str, intel, xlm, notes, pipelines)
    out = ROOT / "09_DASHBOARD" / "reports" / "daily_brief" / f"{date_str}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size:,} bytes)")

    if not args.no_slack:
        # Top picks = first 1 from each of the first 3 categories
        top_picks = []
        for cat, _ in FOCUS_CATEGORIES[:3]:
            items = intel.get(cat, [])
            if items:
                pick = dict(items[0])
                pick["cat"] = cat
                top_picks.append(pick)
        post_slack(date_str, out, top_picks)
        print(f"  posted top-{len(top_picks)} to #ceo-brief")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
