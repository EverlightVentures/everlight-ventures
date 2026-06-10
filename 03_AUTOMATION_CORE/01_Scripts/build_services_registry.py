#!/usr/bin/env python3
"""
build_services_registry.py -- Render the services_registry.json as branded HTML
card grid. Categorized like the Master Hub. Rich never forgets what he's
paying for or connected to.

Memory rule reference: feedback_services_registry_required (Phoenix v3).
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path("/mnt/sdcard/AA_MY_DRIVE")
sys.path.insert(0, str(ROOT / "03_AUTOMATION_CORE" / "01_Scripts" / "content_tools"))

from env_loader import load_env  # noqa: E402
load_env()
from report_template import render_report  # noqa: E402

REGISTRY = ROOT / "01_BUSINESSES" / "Everlight_Ventures" / "_audits" / "services_registry.json"
OUTPUT = ROOT / "09_DASHBOARD" / "reports" / "SERVICES_REGISTRY.html"

TIER_COLORS = {
    "active": "#7ec699",
    "planned": "#D4AF37",
    "dormant": "#888",
    "paused": "#ff6b6b",
}


def render_card(svc: dict) -> str:
    tier = svc.get("tier", "unknown")
    color = TIER_COLORS.get(tier, "#D4AF37")
    cost = svc.get("monthly_cost_usd")
    cost_label = f"${cost}/mo" if cost else "free" if cost == 0 else "tbd"
    used_by = svc.get("used_by", []) or []
    used_html = "<br>".join(f"  • {u}" for u in used_by[:5])
    keys = svc.get("auth_keys", [])
    if isinstance(keys, list):
        keys_html = ", ".join(f"<code>{k}</code>" for k in keys[:4])
    else:
        keys_html = str(keys)
    dash_url = svc.get("dashboard_url")
    dash_link = (f"<a href='{dash_url}' target='_blank' style='color:#D4AF37;text-decoration:none;'>"
                 f"&rarr; dashboard</a>") if dash_url else ""
    notes = svc.get("notes", "")
    return f"""
<div style='background:#0d0d0d;border-left:3px solid {color};padding:16px;border-radius:0 4px 4px 0;'>
  <div style='display:flex;justify-content:space-between;align-items:baseline;'>
    <h3 style='font-family:Playfair Display,serif;color:#E8E8E8;font-size:18px;margin:0;'>{svc['name']}</h3>
    <span style='color:{color};font-size:11px;text-transform:uppercase;letter-spacing:1px;'>{tier} &middot; {cost_label}</span>
  </div>
  <div style='color:#888;font-size:12px;margin-top:8px;font-family:JetBrains Mono,monospace;'>
    {keys_html}
  </div>
  <div style='color:#aaa;font-size:13px;line-height:1.5;margin-top:10px;'>
    <strong style='color:#D4AF37;'>Used by:</strong><br>
    {used_html or '  (not yet wired in)'}
  </div>
  {f'<div style="color:#999;font-size:12px;margin-top:8px;font-style:italic;">{notes}</div>' if notes else ''}
  <div style='margin-top:10px;'>{dash_link}</div>
</div>
"""


def main() -> int:
    if not REGISTRY.exists():
        print(f"missing: {REGISTRY}", file=sys.stderr)
        return 2
    reg = json.loads(REGISTRY.read_text())
    services = reg.get("services", [])

    # Group by category
    by_category: dict[str, list[dict]] = defaultdict(list)
    for svc in services:
        by_category[svc.get("category", "uncategorized")].append(svc)

    # Sort categories so the most "operational" surface up first
    CATEGORY_ORDER = [
        "payments", "email", "voice + sms", "voice generation", "llm",
        "research + search", "database", "dns + hosting + cdn", "trading",
        "real estate data", "skip trace", "proxy", "title firm (relationship)",
        "cash buyer (relationship)", "point of sale", "team comms",
        "email + calendar + drive + docs", "email forwarding", "code hosting",
        "compute", "vpn / mesh network", "internal knowledge layer",
    ]
    cats_in_order = [c for c in CATEGORY_ORDER if c in by_category] + \
                    [c for c in by_category if c not in CATEGORY_ORDER]

    total = len(services)
    active = sum(1 for s in services if s.get("tier") == "active")
    free = sum(1 for s in services if s.get("monthly_cost_usd") == 0)
    paid = sum(1 for s in services if (s.get("monthly_cost_usd") or 0) > 0)
    paid_total = sum((s.get("monthly_cost_usd") or 0) for s in services if s.get("monthly_cost_usd"))

    body = f"""
<div style='display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin:20px 0;'>
  <div style='background:#1a1a1a;padding:16px;border-left:3px solid #D4AF37;'>
    <div style='color:#888;font-size:11px;text-transform:uppercase;'>Services</div>
    <div style='color:#E8E8E8;font-size:28px;font-family:Playfair Display,serif;'>{total}</div>
  </div>
  <div style='background:#1a1a1a;padding:16px;border-left:3px solid #7ec699;'>
    <div style='color:#888;font-size:11px;text-transform:uppercase;'>Active</div>
    <div style='color:#7ec699;font-size:28px;font-family:Playfair Display,serif;'>{active}</div>
  </div>
  <div style='background:#1a1a1a;padding:16px;border-left:3px solid #D4AF37;'>
    <div style='color:#888;font-size:11px;text-transform:uppercase;'>Free Tier</div>
    <div style='color:#E8E8E8;font-size:28px;font-family:Playfair Display,serif;'>{free}</div>
  </div>
  <div style='background:#1a1a1a;padding:16px;border-left:3px solid #ff6b6b;'>
    <div style='color:#888;font-size:11px;text-transform:uppercase;'>Paid /mo</div>
    <div style='color:#E8E8E8;font-size:28px;font-family:Playfair Display,serif;'>${paid_total}</div>
  </div>
</div>

<p style='color:#888;font-size:14px;'>
Every external service Everlight Ventures connects to. Categorized like the
Master Hub. Updated: {reg.get('_meta',{}).get('last_updated','--')}.
</p>
"""
    for cat in cats_in_order:
        items = by_category[cat]
        body += f"""
<h2 style='font-family:Playfair Display,serif;color:#D4AF37;font-size:22px;margin:32px 0 12px;border-bottom:1px solid #2a2a2a;padding-bottom:6px;'>
  {cat.title()} <span style='color:#666;font-size:14px;font-family:Inter,sans-serif;'>({len(items)})</span>
</h2>
<div style='display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:16px;'>
{''.join(render_card(s) for s in items)}
</div>
"""
    body += f"""
<p style='color:#666;font-size:12px;margin-top:32px;'>
Source: <code>01_BUSINESSES/Everlight_Ventures/_audits/services_registry.json</code> &middot;
Rendered {datetime.now().strftime('%Y-%m-%d %H:%M')}
</p>
"""
    html = render_report(
        title="Services & Subscriptions",
        content_html=body,
        agent_name="Hive Mind",
        agent_title="Operations Registry",
    )
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(html, encoding="utf-8")
    print(f"wrote {OUTPUT} ({OUTPUT.stat().st_size:,} bytes)")
    print(f"  total={total} active={active} free={free} paid_monthly=${paid_total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
