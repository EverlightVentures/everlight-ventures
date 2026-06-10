#!/usr/bin/env python3
"""
aggregate_todos.py -- One canonical TODO list, aggregated from the workspace.

Scans audit memos, SOPs, runbooks, the active plan file, and recent memory
entries for "TODO", "DEFERRED", "BLOCKED", and unfinished checkbox items.
Renders to branded gold-on-dark HTML at:

    09_DASHBOARD/reports/RICH_TODO_LIVE.html

Sections:
  1. Open -- needs Rich (manual / browser auth / cred gen)
  2. Open -- system will execute (autonomous, queued for next session)
  3. Done -- this week (strikethrough)

Memory rule: feedback_one_todo_to_rule_them_all (Phoenix v3, 2026-05-13).
"""
from __future__ import annotations

import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path("/mnt/sdcard/AA_MY_DRIVE")
sys.path.insert(0, str(ROOT / "03_AUTOMATION_CORE" / "01_Scripts" / "content_tools"))

from env_loader import load_env  # noqa: E402
load_env()
from report_template import render_report  # noqa: E402

# What to scan
SCAN_GLOBS = [
    "01_BUSINESSES/Everlight_Ventures/_audits/*.html",
    "01_BUSINESSES/Everlight_Ventures/_audits/*.md",  # legacy MDs we haven't converted
    "01_BUSINESSES/Everlight_Ventures/Wholesale/SOPS/*.html",
    "01_BUSINESSES/Everlight_Ventures/Wholesale/SOPS/*.md",
    "01_BUSINESSES/Everlight_Ventures/Wholesale/NEXT_LEVERS.md",
    "01_BUSINESSES/Everlight_Ventures/Wholesale/NEXT_LEVERS.html",
    "06_DEVELOPMENT/everlight_os/hive_mind/runbooks/*.md",
]

PLAN_FILE = Path("/root/.claude/plans/continue-unified-phoenix.md")
MEMORY_DIR = Path("/root/.claude/projects/-mnt-sdcard-AA-MY-DRIVE/memory")

# Pattern matchers for "open work" lines
OPEN_PATTERNS = [
    re.compile(r"^\s*(?:[-*]\s*)?(?:\[\s*\]|TODO|DEFERRED|BLOCKED|PENDING|TODO:|FIXME)\b[:\.\)\s]*(.+)$", re.IGNORECASE),
    re.compile(r"^\s*(?:[-*]\s*)?Action\s+(?:item|required)[:\.\)\s]*(.+)$", re.IGNORECASE),
]
DONE_PATTERNS = [
    re.compile(r"^\s*(?:[-*]\s*)?(?:\[x\]|DONE|COMPLETED|SHIPPED|RESOLVED)\b[:\.\)\s]*(.+)$", re.IGNORECASE),
]

# "Needs Rich" hints (manual / external dep)
RICH_KEYWORDS = (
    "rich", "manual", "browser", "browser-auth", "manually generate",
    "google app password", "cloudflare account", "cf account",
    "filing", "open bank", "register",
)


def classify(text: str) -> str:
    """Return 'rich' or 'system' for an open item."""
    low = text.lower()
    if any(k in low for k in RICH_KEYWORDS):
        return "rich"
    return "system"


def html_to_text(html: str) -> str:
    """Strip HTML tags so the regex hits raw text. Crude but enough for our docs."""
    text = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL)
    text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    return text


def scan_file(path: Path) -> list[dict]:
    if not path.exists() or path.is_dir():
        return []
    try:
        raw = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []
    text = html_to_text(raw) if path.suffix.lower() in (".html", ".htm") else raw

    items: list[dict] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or len(line) > 400:
            continue
        for pat in DONE_PATTERNS:
            m = pat.search(line)
            if m:
                items.append({
                    "status": "done",
                    "text": m.group(1).strip(),
                    "source": str(path.relative_to(ROOT)) if path.is_absolute() and ROOT in path.parents else str(path),
                })
                break
        else:
            for pat in OPEN_PATTERNS:
                m = pat.search(line)
                if m:
                    txt = m.group(1).strip()
                    if not txt or len(txt) < 5:
                        continue
                    items.append({
                        "status": "open",
                        "category": classify(txt),
                        "text": txt,
                        "source": str(path.relative_to(ROOT)) if path.is_absolute() and ROOT in path.parents else str(path),
                    })
                    break
    return items


def gather_items() -> list[dict]:
    all_items: list[dict] = []
    for pattern in SCAN_GLOBS:
        for p in ROOT.glob(pattern):
            all_items.extend(scan_file(p))
    if PLAN_FILE.exists():
        all_items.extend(scan_file(PLAN_FILE))
    if MEMORY_DIR.exists():
        for p in MEMORY_DIR.glob("*.md"):
            all_items.extend(scan_file(p))
    return all_items


def dedupe(items: list[dict]) -> list[dict]:
    seen = set()
    out = []
    for it in items:
        key = (it["status"], it.get("category"), it["text"][:120].lower())
        if key in seen:
            continue
        seen.add(key)
        out.append(it)
    return out


def render_html(items: list[dict]) -> str:
    rich_items = [i for i in items if i["status"] == "open" and i.get("category") == "rich"]
    sys_items = [i for i in items if i["status"] == "open" and i.get("category") == "system"]
    done_items = [i for i in items if i["status"] == "done"]

    def li(it: dict, strike: bool = False) -> str:
        style = "color:#888;text-decoration:line-through;" if strike else ""
        text = it["text"][:300]
        src = it.get("source", "")
        src_html = (f"<span style='color:#666;font-size:12px;font-family:JetBrains Mono,monospace;'>"
                    f" -- {src}</span>") if src else ""
        return (f"<li style='margin:6px 0;padding:8px 12px;background:#0d0d0d;border-left:3px solid #D4AF37;{style}'>"
                f"{text}{src_html}</li>")

    # Hand-add the two manual-Rich blockers we already know about, so they're at top
    pinned_rich = [
        {"text": "Generate Gmail App Password at https://myaccount.google.com/apppasswords; paste GMAIL_APP_PASSWORD into 03_AUTOMATION_CORE/03_Credentials/.env. Verify: python3 phone_imap_poller.py --healthcheck", "source": "RICH_TODO_LIVE -- pinned"},
        {"text": "Install + run Cloudflare Tunnel per Wholesale/SOPS/CLOUDFLARE_TUNNEL_ACTIVATION_2026-05-13.html (4 commands). Then ping me 'tunnel is up' and I wire the rest.", "source": "RICH_TODO_LIVE -- pinned"},
    ]

    # Mark obvious DONE items pulled from this session so they stop showing in OPEN
    completed_today = [
        "back_tax_escalation_check shipped + wired into c_assignment",
        "Blinko local on :2700 (614 notes restored)",
        "MCP HTTP bridge on :2701 (28 tools, 3 services)",
        "daily_lead_pipeline.py + cron at 3 AM PT",
        "Supabase audit corrected (105 tables, 182,575 rows)",
        "phone_imap_poller --healthcheck mode",
        "Cloudflare Tunnel handoff doc written",
        "5 .md docs converted to branded HTML",
        "System-wide .env loader (zshrc + bashrc + boot + Python helper)",
    ]

    pinned_sys = [
        {"text": "After Rich activates Cloudflare Tunnel: wire EVERLIGHT_PUBLIC_HOST env, patch esign_server._public_url(), add cloudflared to watchdog as process-watch, smoke-test M7 sign URL via public hostname.", "source": "Phoenix v3 plan -- P7"},
        {"text": "Master Hub v2 / Ultra Mind view (replace :2000 port-list with categorized tile grid surfacing memory + knowledge + ops + trading + comms + personal + services)", "source": "Phoenix v3 plan -- P2"},
        {"text": "Daily research briefing (Intel Phase 8, branded HTML 6 AM PT cron + Slack #ceo-brief top-3)", "source": "Phoenix v3 plan -- P3"},
        {"text": "XLM honest dashboard (truth: bot is OBSERVING, not trading; equity $2.75, 0 trades in 34 days)", "source": "Phoenix v3 plan -- P4"},
        {"text": "Services & Subscriptions registry (Stripe, Twilio, 11labs, OpenAI, Resend, Supabase, Cloudflare, Coinbase, etc) so Rich never forgets what he's paying for", "source": "Phoenix v3 plan -- P4.5"},
        {"text": "Wire 5 agents to intel_query.py so they actually pull from the 730 Intel Center resources before answering", "source": "Phoenix v3 plan -- P5"},
        {"text": "hive_orchestrator MCP (dispatch_agent, list_agents, query_blinko, pipeline_status) + auto-pickup by HTTP bridge", "source": "Phoenix v3 plan -- P6"},
    ]

    rich_html = "<ul style='list-style:none;padding:0;'>" + "".join(li(i) for i in pinned_rich + rich_items) + "</ul>"
    sys_html = "<ul style='list-style:none;padding:0;'>" + "".join(li(i) for i in pinned_sys + sys_items) + "</ul>"
    done_html = ("<ul style='list-style:none;padding:0;'>"
                 + "".join(li({"text": t, "source": "shipped 2026-05-13"}, strike=True) for t in completed_today)
                 + "".join(li(i, strike=True) for i in done_items[:30])
                 + "</ul>")

    body = f"""
<p style='color:#888;font-size:14px;'>
Live aggregator -- pulls TODO / DEFERRED / BLOCKED items across the workspace.
Re-render any time with <code style='background:#1a1a1a;color:#D4AF37;padding:2px 6px;'>python3 03_AUTOMATION_CORE/01_Scripts/aggregate_todos.py</code>
or via the Master Hub button. Last refreshed: {datetime.now().strftime('%Y-%m-%d %H:%M')}.
</p>

<h2 style='font-family:Playfair Display,serif;color:#D4AF37;font-size:22px;margin-top:32px;'>
  Open -- needs Rich ({len(pinned_rich) + len(rich_items)})
</h2>
<p style='color:#888;font-size:13px;'>Manual steps that can't be automated: browser auth, credential generation, account decisions.</p>
{rich_html}

<h2 style='font-family:Playfair Display,serif;color:#D4AF37;font-size:22px;margin-top:32px;'>
  Open -- system will execute ({len(pinned_sys) + len(sys_items)})
</h2>
<p style='color:#888;font-size:13px;'>Queued for the next auto-mode session. No Rich action needed.</p>
{sys_html}

<h2 style='font-family:Playfair Display,serif;color:#D4AF37;font-size:22px;margin-top:32px;'>
  Done -- recent ({len(completed_today) + min(30, len(done_items))})
</h2>
<p style='color:#888;font-size:13px;'>Recently shipped. Strikethrough for the satisfaction.</p>
{done_html}
"""
    return render_report(
        title="Rich's Live To-Do List",
        content_html=body,
        agent_name="Hive Mind",
        agent_title="Operations Center",
    )


def main() -> int:
    items = dedupe(gather_items())
    out = ROOT / "09_DASHBOARD" / "reports" / "RICH_TODO_LIVE.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_html(items), encoding="utf-8")
    print(f"wrote {out}  ({out.stat().st_size:,} bytes)")
    counts = {
        "rich": sum(1 for i in items if i["status"] == "open" and i.get("category") == "rich"),
        "system": sum(1 for i in items if i["status"] == "open" and i.get("category") == "system"),
        "done": sum(1 for i in items if i["status"] == "done"),
    }
    print(f"  open-rich={counts['rich']}  open-system={counts['system']}  done={counts['done']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
