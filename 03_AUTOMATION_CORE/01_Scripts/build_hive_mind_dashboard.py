#!/usr/bin/env python3
"""
build_hive_mind_dashboard.py -- The query interface Rich asked for.

Rich (2026-05-13): "My hive mind dashboard, which is what I used to use to
query. You know is gone. I don't see that over there. That needs to be
organized as well."

This dashboard is the single page where Rich (or anyone) can:
  - See all 94 agents by squad / fire team / department
  - See live agent status (from any recent Blinko / hive_master_log entry)
  - Click through to an agent's full firmware
  - See the MCP HTTP bridge tool catalog
  - Quick-launch links to Blinko + Resources Hub for queries

Output: 09_DASHBOARD/reports/HIVE_MIND.html
"""
from __future__ import annotations

import html as html_lib
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path("/mnt/sdcard/AA_MY_DRIVE")
sys.path.insert(0, str(ROOT / "03_AUTOMATION_CORE" / "01_Scripts" / "content_tools"))

from env_loader import load_env  # noqa: E402
load_env()
from report_template import render_report  # noqa: E402

AGENTS_DIR = ROOT / ".claude" / "agents"
OUTPUT = ROOT / "09_DASHBOARD" / "reports" / "HIVE_MIND.html"

# Department -> color
DEPT_COLORS = {
    "Claude Corp": "#D4A843",
    "Gemini Ops": "#6bafff",
    "Codex Labs": "#7ec699",
    "Perplexity Intel": "#a8a3ff",
    "Operations": "#ff9f6b",
    "Content Engine": "#ffd76b",
    "Trading Desk": "#ff9f6b",
    "OSINT Desk": "#7ec699",
    "DevOps Desk": "#6bafff",
    "Disaster Response Desk": "#ff6b6b",
    "Everlight Newsroom": "#c39bff",
    "Product Desk": "#a8a3ff",
    "Wholesale Desk": "#D4A843",
    "Legal/Compliance Desk": "#ff6b6b",
}


def esc(s: str | None) -> str:
    return html_lib.escape(str(s or ""))


def parse_agent_md(path: Path) -> dict:
    """Pull Identity block fields from an agent's .md. Tolerant of formatting variance."""
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return {}
    info = {"file": path.name, "name_raw": path.stem}
    # Common Markdown identity fields
    patterns = {
        "name": r"\*\*Name:\*\*\s*(.+)",
        "email": r"\*\*Email:\*\*\s*(.+)",
        "slack": r"\*\*Slack:\*\*\s*(.+)",
        "department": r"\*\*Department:\*\*\s*(.+)",
        "personality": r"\*\*Personality:\*\*\s*(.+)",
        "role": r"^You are ([^\.\n]+)",
    }
    for k, pat in patterns.items():
        m = re.search(pat, text, re.MULTILINE)
        if m:
            info[k] = m.group(1).strip().rstrip(".")
    # First section after Identity could be Role description
    first_para = ""
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith("#") and not line.startswith("<!--") and not line.startswith("**"):
            first_para = line[:160]
            break
    info["snippet"] = first_para
    return info


def list_mcp_tools() -> list[dict]:
    """Query the local MCP HTTP bridge for the live tool catalog."""
    try:
        with urllib.request.urlopen("http://127.0.0.1:2701/list_tools", timeout=4) as r:
            j = json.loads(r.read())
        out = []
        for service, tools in (j or {}).items():
            for t in tools:
                if isinstance(t, dict) and "name" in t:
                    out.append({"service": service, "name": t["name"], "description": t.get("description", "")})
        return out
    except Exception:
        return []


def agent_card(info: dict) -> str:
    name = info.get("name") or info.get("name_raw", "?").replace("_", " ").title()
    dept = info.get("department", "—")
    color = DEPT_COLORS.get(dept, "#D4A843")
    role = info.get("role", info.get("snippet", ""))[:140]
    slack = info.get("slack", "")
    email = info.get("email", "")
    fwfile = info.get("file", "")
    return f"""
<div class='agent' data-name='{esc(name).lower()}' data-dept='{esc(dept).lower()}'
     data-role='{esc(role).lower()}'
     style='background:#0d0d0d;border-left:3px solid {color};padding:14px 16px;border-radius:0 3px 3px 0;'>
  <div style='display:flex;justify-content:space-between;align-items:baseline;'>
    <div style='font-family:Playfair Display,serif;color:#E8E8E8;font-size:16px;font-weight:600;'>{esc(name)}</div>
    <span style='color:{color};font-size:10px;text-transform:uppercase;letter-spacing:1px;'>{esc(dept)}</span>
  </div>
  <div style='color:#aaa;font-size:12px;margin-top:6px;line-height:1.5;'>{esc(role)}</div>
  <div style='color:#666;font-size:11px;font-family:JetBrains Mono,monospace;margin-top:8px;'>
    {esc(email)}{(' &middot; ' + esc(slack)) if slack else ''}
  </div>
  <div style='margin-top:6px;'>
    <a href='/agents/{esc(fwfile)}' style='color:{color};font-size:11px;text-decoration:none;'>firmware &rarr;</a>
  </div>
</div>
"""


def main() -> int:
    agents = []
    if AGENTS_DIR.exists():
        for p in sorted(AGENTS_DIR.glob("*.md")):
            info = parse_agent_md(p)
            if info:
                agents.append(info)

    by_dept = defaultdict(list)
    for a in agents:
        by_dept[a.get("department") or "Unassigned"].append(a)
    depts_sorted = sorted(by_dept.keys(), key=lambda d: -len(by_dept[d]))

    tools = list_mcp_tools()
    by_service = defaultdict(list)
    for t in tools:
        by_service[t["service"]].append(t)

    # Strip
    total_agents = len(agents)
    total_depts = len(by_dept)
    total_tools = len(tools)

    strip = f"""
<div style='display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:16px 0 24px;'>
  <div style='background:#1a1a1a;padding:14px 18px;border-left:3px solid #D4A843;'>
    <div style='color:#888;font-size:11px;text-transform:uppercase;letter-spacing:1px;'>Agents</div>
    <div style='color:#E8E8E8;font-size:28px;font-family:Playfair Display,serif;'>{total_agents}</div>
  </div>
  <div style='background:#1a1a1a;padding:14px 18px;border-left:3px solid #D4A843;'>
    <div style='color:#888;font-size:11px;text-transform:uppercase;letter-spacing:1px;'>Departments</div>
    <div style='color:#E8E8E8;font-size:28px;font-family:Playfair Display,serif;'>{total_depts}</div>
  </div>
  <div style='background:#1a1a1a;padding:14px 18px;border-left:3px solid #D4A843;'>
    <div style='color:#888;font-size:11px;text-transform:uppercase;letter-spacing:1px;'>MCP Tools</div>
    <div style='color:#E8E8E8;font-size:28px;font-family:Playfair Display,serif;'>{total_tools}</div>
  </div>
  <div style='background:#1a1a1a;padding:14px 18px;border-left:3px solid #7ec699;'>
    <div style='color:#888;font-size:11px;text-transform:uppercase;letter-spacing:1px;'>Bridge</div>
    <div style='color:#7ec699;font-size:18px;font-family:Playfair Display,serif;'>:2701</div>
    <div style='color:#888;font-size:11px;'>HTTP + stdio</div>
  </div>
</div>

<div style='display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:12px;margin:8px 0 24px;'>
  <a href='http://127.0.0.1:2700/' target='_blank' style='display:block;background:#0d0d0d;border-left:3px solid #7ec699;padding:14px 18px;color:#E8E8E8;text-decoration:none;'>
    <div style='color:#7ec699;font-size:11px;text-transform:uppercase;letter-spacing:1px;'>Quick Query</div>
    <div style='font-family:Playfair Display,serif;font-size:18px;margin-top:4px;'>Blinko RAG &rarr;</div>
    <div style='color:#888;font-size:12px;'>Search 614+ notes via API</div>
  </a>
  <a href='/reports/RESOURCES_HUB.html' target='_blank' style='display:block;background:#0d0d0d;border-left:3px solid #a8a3ff;padding:14px 18px;color:#E8E8E8;text-decoration:none;'>
    <div style='color:#a8a3ff;font-size:11px;text-transform:uppercase;letter-spacing:1px;'>Quick Query</div>
    <div style='font-family:Playfair Display,serif;font-size:18px;margin-top:4px;'>Resources Hub &rarr;</div>
    <div style='color:#888;font-size:12px;'>745 free tools, categorized</div>
  </a>
  <a href='http://127.0.0.1:2701/list_tools' target='_blank' style='display:block;background:#0d0d0d;border-left:3px solid #D4A843;padding:14px 18px;color:#E8E8E8;text-decoration:none;'>
    <div style='color:#D4A843;font-size:11px;text-transform:uppercase;letter-spacing:1px;'>Quick Query</div>
    <div style='font-family:Playfair Display,serif;font-size:18px;margin-top:4px;'>MCP HTTP Bridge &rarr;</div>
    <div style='color:#888;font-size:12px;'>Tool catalog (JSON)</div>
  </a>
</div>

<div style='margin:16px 0;'>
  <input id='hivesearch' type='text' placeholder='Search agents -- name, department, role'
         style='width:100%;padding:14px 16px;background:#0d0d0d;color:#E8E8E8;border:1px solid #2a2a2a;
                border-left:3px solid #D4A843;font-family:Inter,sans-serif;font-size:15px;'>
</div>

<div style='display:flex;flex-wrap:wrap;gap:8px;margin:16px 0;' id='deptfilters'>
  <button class='dfilter active' data-dept='' style='background:#D4A843;color:#0a0a0a;border:none;padding:6px 14px;font-family:Inter;font-size:12px;cursor:pointer;text-transform:uppercase;letter-spacing:1px;'>ALL</button>
"""
    for dept in depts_sorted:
        c = DEPT_COLORS.get(dept, "#D4A843")
        strip += (f"<button class='dfilter' data-dept='{esc(dept).lower()}' "
                  f"style='background:#1a1a1a;color:{c};border:1px solid {c};"
                  f"padding:6px 14px;font-family:Inter;font-size:12px;cursor:pointer;text-transform:uppercase;letter-spacing:1px;'>"
                  f"{esc(dept)} ({len(by_dept[dept])})</button>")
    strip += "</div>"

    # Sections per dept
    sections = []
    for dept in depts_sorted:
        c = DEPT_COLORS.get(dept, "#D4A843")
        sections.append(f"""
<section class='deptsection' data-dept='{esc(dept).lower()}' style='margin-top:32px;'>
  <h2 style='font-family:Playfair Display,serif;color:{c};font-size:22px;margin:0 0 10px;border-bottom:1px solid #2a2a2a;padding-bottom:6px;'>
    {esc(dept)} <span style='color:#666;font-size:13px;font-family:Inter,sans-serif;'>({len(by_dept[dept])} agents)</span>
  </h2>
  <div style='display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:12px;'>
    {''.join(agent_card(a) for a in by_dept[dept])}
  </div>
</section>
""")

    # MCP tool catalog section
    tools_html = ""
    for service, ts in by_service.items():
        tools_list = "".join(
            f"<div style='background:#0d0d0d;border-left:3px solid #D4A843;padding:10px 14px;margin:6px 0;'>"
            f"<code style='color:#D4A843;font-size:13px;font-family:JetBrains Mono,monospace;'>{esc(t['name'])}</code>"
            f"<div style='color:#aaa;font-size:12px;margin-top:4px;'>{esc(t.get('description','')[:200])}</div>"
            f"</div>"
            for t in ts
        )
        tools_html += f"""
<h3 style='font-family:Playfair Display,serif;color:#D4A843;font-size:18px;margin:18px 0 8px;'>{esc(service)} ({len(ts)} tools)</h3>
{tools_list}
"""

    js = """
<script>
(function() {
  const box = document.getElementById('hivesearch');
  const filters = document.querySelectorAll('.dfilter');
  const sections = document.querySelectorAll('.deptsection');
  const cards = document.querySelectorAll('.agent');
  let activeDept = '';
  function applyFilter() {
    const q = (box.value || '').toLowerCase().trim();
    cards.forEach(c => {
      const name = (c.dataset.name || '').toLowerCase();
      const dept = (c.dataset.dept || '').toLowerCase();
      const role = (c.dataset.role || '').toLowerCase();
      const matchesDept = !activeDept || dept === activeDept;
      const matchesQ = !q || name.includes(q) || dept.includes(q) || role.includes(q);
      c.style.display = (matchesDept && matchesQ) ? '' : 'none';
    });
    sections.forEach(s => {
      const visible = Array.from(s.querySelectorAll('.agent')).some(c => c.style.display !== 'none');
      const dept = (s.dataset.dept || '').toLowerCase();
      s.style.display = (visible && (!activeDept || dept === activeDept)) ? '' : 'none';
    });
  }
  box.addEventListener('input', applyFilter);
  filters.forEach(f => f.addEventListener('click', () => {
    filters.forEach(x => { x.classList.remove('active'); x.style.background='#1a1a1a'; x.style.color = x.style.borderColor || '#D4A843'; });
    f.classList.add('active');
    f.style.background = '#D4A843';
    f.style.color = '#0a0a0a';
    activeDept = f.dataset.dept;
    applyFilter();
  }));
})();
</script>
"""

    body = f"""
<p style='color:#888;font-size:14px;margin:8px 0 16px;'>
The Hive Mind. {total_agents} named agents across {total_depts} departments,
{total_tools} MCP tools live on the HTTP bridge. Query Blinko, browse the
Resources Hub, or click any agent for their firmware.
</p>
{strip}
{''.join(sections)}

<h2 style='font-family:Playfair Display,serif;color:#D4A843;font-size:24px;margin:48px 0 12px;border-bottom:2px solid #D4A843;padding-bottom:8px;'>
  MCP HTTP Bridge -- Tool Catalog
</h2>
<p style='color:#888;font-size:13px;margin-bottom:16px;'>
Every tool callable from cron / Workers / scripts via POST <code style='background:#1a1a1a;color:#D4A843;padding:2px 6px;'>http://127.0.0.1:2701/tool/&#123;service&#125;/&#123;tool_name&#125;</code>.
Same Python dispatchers as the stdio MCP path used by Claude Code.
</p>
{tools_html}
{js}
"""
    html = render_report(
        title="Hive Mind -- Agents & Tools",
        content_html=body,
        agent_name="Marcus Cole",
        agent_title="Chief Operator (orchestrating)",
    )
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(html, encoding="utf-8")
    print(f"wrote {OUTPUT} ({OUTPUT.stat().st_size:,} bytes)")
    print(f"  {total_agents} agents / {total_depts} depts / {total_tools} tools")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
