#!/usr/bin/env python3
"""
build_resources_dashboard.py -- The 745 Intel Center resources rendered as a
categorized branded card grid (Master Hub aesthetic), NOT a flat ugly list.

Rich asked (2026-05-13): "my resources dashboard is just a list of 745 reboost.
I would kinda like for you in the same way that you did the 2000 as the master
hub. If you could make like a mask, I don't know, let's see, how do I say this,
categorize the like, similar resources group them together and then sub
bracket them off of the dashboard extension. That way, I can group them all
together. And what kind of search like-minded material, or same context,
material at 1 time? And it's all cart and their own cards."

Output: 09_DASHBOARD/reports/RESOURCES_HUB.html
Source: Everlight_Intel_Center/database/everlight_resources.sqlite
"""
from __future__ import annotations

import html as html_lib
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path("/mnt/sdcard/AA_MY_DRIVE")
sys.path.insert(0, str(ROOT / "03_AUTOMATION_CORE" / "01_Scripts" / "content_tools"))

from env_loader import load_env  # noqa: E402
load_env()
from report_template import render_report  # noqa: E402

DB = ROOT / "Everlight_Intel_Center" / "database" / "everlight_resources.sqlite"
OUTPUT = ROOT / "09_DASHBOARD" / "reports" / "RESOURCES_HUB.html"

# Category emoji-free icons (Playfair / unicode symbols) and accent colors
CATEGORY_META = {
    "Decision Intelligence":   {"color": "#D4A843", "icon": "◆"},
    "OSINT & Investigation":   {"color": "#7ec699", "icon": "▲"},
    "Education & Training":    {"color": "#a8a3ff", "icon": "✦"},
    "Trading & Finance":       {"color": "#ff9f6b", "icon": "▼"},
    "Self-Hosting & Privacy":  {"color": "#6bafff", "icon": "◇"},
    "Space & Science":         {"color": "#c39bff", "icon": "✺"},
    "Content Creation":        {"color": "#ffd76b", "icon": "✎"},
    "Health & Environment":    {"color": "#9fffb2", "icon": "✶"},
    "News & Journalism":       {"color": "#ff6b9f", "icon": "❘"},
    "Weather & Disaster Intel":{"color": "#ffb46b", "icon": "✱"},
    "Maps & Geospatial":       {"color": "#6bffd9", "icon": "✜"},
    "AI & Automation":         {"color": "#D4A843", "icon": "◉"},
    "Aviation & Maritime":     {"color": "#6b9fff", "icon": "✈"},
    "APIs & Developer Tools":  {"color": "#6bafff", "icon": "</>"},
    "eCommerce & Product Research": {"color": "#ffd76b", "icon": "$"},
    "Economics & Markets":     {"color": "#ff9f6b", "icon": "▼"},
    "Legal & Compliance":      {"color": "#ff6b6b", "icon": "§"},
    "Real Estate & Property":  {"color": "#a8a3ff", "icon": "⌂"},
}


def esc(s: str | None) -> str:
    return html_lib.escape(str(s or ""))


def card(row: dict) -> str:
    cat = row.get("category") or "Uncategorized"
    meta = CATEGORY_META.get(cat, {"color": "#D4A843", "icon": "●"})
    color = meta["color"]
    name = esc(row.get("name", "")[:60])
    purpose = esc((row.get("purpose") or "")[:140])
    use_case = esc((row.get("use_case") or "")[:200])
    agent = esc(row.get("agent_owner") or "—")
    cost = esc(row.get("cost_level") or "—")
    url = (row.get("url") or "").strip()
    link_html = (f"<a href='{esc(url)}' target='_blank' "
                 f"style='color:{color};text-decoration:none;font-size:11px;'>→ open</a>") if url else ""
    return f"""
<div class='card' data-category='{esc(cat).lower()}' data-name='{esc(row.get("name","")).lower()}'
     data-tags='{esc(row.get("tags",""))}'
     style='background:#0d0d0d;border-left:3px solid {color};padding:14px 16px;border-radius:0 3px 3px 0;'>
  <div style='display:flex;justify-content:space-between;align-items:baseline;'>
    <div style='font-family:Playfair Display,serif;color:#E8E8E8;font-size:15px;font-weight:600;'>{name}</div>
    <span style='color:{color};font-size:10px;text-transform:uppercase;letter-spacing:1px;'>{cost}</span>
  </div>
  <div style='color:#aaa;font-size:12px;line-height:1.5;margin-top:6px;'>{purpose}</div>
  <div style='color:#777;font-size:11px;margin-top:8px;'>{use_case[:160]}{'…' if len(use_case) > 160 else ''}</div>
  <div style='display:flex;justify-content:space-between;align-items:center;margin-top:10px;color:#666;font-size:11px;'>
    <span>{agent}</span>{link_html}
  </div>
</div>
"""


def main() -> int:
    if not DB.exists():
        print(f"missing: {DB}", file=sys.stderr)
        return 2
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in conn.execute("SELECT * FROM resources ORDER BY category, priority_score DESC, name").fetchall()]

    by_category: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_category[r.get("category") or "Uncategorized"].append(r)
    cats_sorted = sorted(by_category.keys(), key=lambda c: -len(by_category[c]))

    total = len(rows)
    departments = len({r.get("department") for r in rows if r.get("department")})
    agents = len({r.get("agent_owner") for r in rows if r.get("agent_owner")})

    # Top strip: counts + search
    strip = f"""
<div style='display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:16px 0 24px;'>
  <div style='background:#1a1a1a;padding:14px 16px;border-left:3px solid #D4A843;'>
    <div style='color:#888;font-size:11px;text-transform:uppercase;letter-spacing:1px;'>Resources</div>
    <div style='color:#E8E8E8;font-size:28px;font-family:Playfair Display,serif;'>{total}</div>
  </div>
  <div style='background:#1a1a1a;padding:14px 16px;border-left:3px solid #D4A843;'>
    <div style='color:#888;font-size:11px;text-transform:uppercase;letter-spacing:1px;'>Categories</div>
    <div style='color:#E8E8E8;font-size:28px;font-family:Playfair Display,serif;'>{len(by_category)}</div>
  </div>
  <div style='background:#1a1a1a;padding:14px 16px;border-left:3px solid #D4A843;'>
    <div style='color:#888;font-size:11px;text-transform:uppercase;letter-spacing:1px;'>Departments</div>
    <div style='color:#E8E8E8;font-size:28px;font-family:Playfair Display,serif;'>{departments}</div>
  </div>
  <div style='background:#1a1a1a;padding:14px 16px;border-left:3px solid #D4A843;'>
    <div style='color:#888;font-size:11px;text-transform:uppercase;letter-spacing:1px;'>Agent Owners</div>
    <div style='color:#E8E8E8;font-size:28px;font-family:Playfair Display,serif;'>{agents}</div>
  </div>
</div>

<div style='margin:16px 0;'>
  <input id='searchbox' type='text' placeholder='Search resources -- name, tag, purpose, agent'
         style='width:100%;padding:14px 16px;background:#0d0d0d;color:#E8E8E8;border:1px solid #2a2a2a;
                border-left:3px solid #D4A843;font-family:Inter,sans-serif;font-size:15px;'>
</div>

<div style='display:flex;flex-wrap:wrap;gap:8px;margin:16px 0;' id='catfilters'>
  <button class='catfilter active' data-cat='' style='background:#D4A843;color:#0a0a0a;border:none;padding:6px 14px;font-family:Inter;font-size:12px;cursor:pointer;text-transform:uppercase;letter-spacing:1px;'>ALL</button>
"""
    for cat in cats_sorted:
        meta = CATEGORY_META.get(cat, {"color": "#D4A843", "icon": "●"})
        cc = meta["color"]
        strip += (f"<button class='catfilter' data-cat='{esc(cat).lower()}' "
                  f"style='background:#1a1a1a;color:{cc};border:1px solid {cc};"
                  f"padding:6px 14px;font-family:Inter;font-size:12px;cursor:pointer;text-transform:uppercase;letter-spacing:1px;'>"
                  f"{esc(cat)} ({len(by_category[cat])})</button>")
    strip += "</div>"

    sections = []
    for cat in cats_sorted:
        meta = CATEGORY_META.get(cat, {"color": "#D4A843", "icon": "●"})
        sections.append(f"""
<section class='catsection' data-cat='{esc(cat).lower()}' style='margin-top:36px;'>
  <h2 style='font-family:Playfair Display,serif;color:{meta["color"]};font-size:22px;margin:0 0 12px;border-bottom:1px solid #2a2a2a;padding-bottom:6px;'>
    <span style='display:inline-block;width:24px;'>{meta['icon']}</span>
    {esc(cat)}
    <span style='color:#666;font-size:13px;font-family:Inter,sans-serif;margin-left:8px;'>({len(by_category[cat])} resources)</span>
  </h2>
  <div class='cardgrid' style='display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:14px;'>
    {''.join(card(r) for r in by_category[cat])}
  </div>
</section>
""")

    js = """
<script>
(function() {
  const box = document.getElementById('searchbox');
  const filters = document.querySelectorAll('.catfilter');
  const sections = document.querySelectorAll('.catsection');
  const cards = document.querySelectorAll('.card');
  let activeCat = '';
  function applyFilter() {
    const q = (box.value || '').toLowerCase().trim();
    cards.forEach(c => {
      const cat = (c.dataset.category || '').toLowerCase();
      const name = (c.dataset.name || '').toLowerCase();
      const tags = (c.dataset.tags || '').toLowerCase();
      const text = (c.textContent || '').toLowerCase();
      const matchesCat = !activeCat || cat === activeCat;
      const matchesQ = !q || name.includes(q) || tags.includes(q) || text.includes(q);
      c.style.display = (matchesCat && matchesQ) ? '' : 'none';
    });
    sections.forEach(s => {
      const cat = (s.dataset.cat || '').toLowerCase();
      const visible = Array.from(s.querySelectorAll('.card')).some(c => c.style.display !== 'none');
      s.style.display = (visible && (!activeCat || cat === activeCat)) ? '' : 'none';
    });
  }
  box.addEventListener('input', applyFilter);
  filters.forEach(f => f.addEventListener('click', () => {
    filters.forEach(x => { x.classList.remove('active'); x.style.background='#1a1a1a'; x.style.color = x.style.borderColor || '#D4A843'; });
    f.classList.add('active');
    f.style.background = '#D4A843';
    f.style.color = '#0a0a0a';
    activeCat = f.dataset.cat;
    applyFilter();
  }));
})();
</script>
"""

    body = f"""
<p style='color:#888;font-size:14px;margin:8px 0 16px;'>
The Everlight Intel Center catalogue. {total} verified free resources & tools,
grouped by capability. Click a category to focus, type to search across names,
tags, purposes, and use cases.
</p>
{strip}
{''.join(sections)}
<p style='color:#666;font-size:12px;margin-top:32px;'>
Source: <code style='background:#1a1a1a;color:#D4A843;padding:2px 6px;'>Everlight_Intel_Center/database/everlight_resources.sqlite</code>
&middot; Rendered {datetime.now().strftime('%Y-%m-%d %H:%M PT')}
</p>
{js}
"""
    html = render_report(
        title="Resources Hub -- 745 Free Tools",
        content_html=body,
        agent_name="Hive Mind",
        agent_title="Knowledge Layer",
    )
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(html, encoding="utf-8")
    print(f"wrote {OUTPUT} ({OUTPUT.stat().st_size:,} bytes)")
    print(f"  {total} resources / {len(by_category)} categories")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
