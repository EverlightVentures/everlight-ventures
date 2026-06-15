#!/usr/bin/env python3
"""ops_dashboard.py -- Rich's one-page admin hub (asked for 2026-06-15).

"One page where I do all my admin: the watchdog memos, the agent mailbox, the HTML
reports, and a to-do list -- a nice pretty file right there." This is that page.

Aggregates (all read-only, never blocks):
  - WATCHDOG: the latest CEO memo + the live brakes/gas state (quarantines + lean-ins)
  - TO-DO: rendered from _state/ops_todo.md (edit that file; checkboxes render here)
  - AGENT MAILBOX: the latest entries from _state/AGENT_MAILBOX.md
  - REPORTS: links to the kalshi dashboard, watchdog memos, and hive HTML reports

Writes ops.html next to the other dashboards; the cron sudo-copies it to the nginx
docroot so it serves at http://e5-mother/ops.html.

    PYTHONPATH=/home/ubuntu/AA_MY_DRIVE/06_DEVELOPMENT python3 -m kalshi_agent.ops_dashboard
"""
import html
import json
import time
from pathlib import Path

HERE = Path(__file__).parent
DATA = HERE / "data"
MEMOS = DATA / "watchdog_memos.jsonl"
STATE = DATA / "watchdog_state.json"
MAILBOX_PATHS = ["/home/ubuntu/AA_MY_DRIVE/_state/AGENT_MAILBOX.md",
                 "/mnt/sdcard/AA_MY_DRIVE/_state/AGENT_MAILBOX.md"]
TODO_PATHS = ["/home/ubuntu/AA_MY_DRIVE/_state/ops_todo.md",
              "/mnt/sdcard/AA_MY_DRIVE/_state/ops_todo.md"]
HIVE_REPORTS = Path("/home/ubuntu/hive_reports")
HTML_DIRS = [str(HIVE_REPORTS), str(HERE)]

G, DK, CARD, MUTED = "#D4AF37", "#0A0A0A", "#141414", "#888"


def _read_first(paths):
    for p in paths:
        try:
            return Path(p).read_text()
        except Exception:
            continue
    return ""


def _esc(s):
    return html.escape(s or "")


def _card(title, body):
    return ("<div style='background:%s;border-radius:10px;padding:18px 22px;margin:16px 0'>"
            "<div style='color:%s;font-weight:700;font-size:17px;font-family:\"Playfair Display\",Georgia,serif;"
            "margin-bottom:10px'>%s</div>%s</div>" % (CARD, G, title, body))


def watchdog_block():
    memos = []
    if MEMOS.exists():
        memos = [json.loads(l) for l in MEMOS.read_text().splitlines() if l.strip()]
    if not memos:
        body = "<i style='color:%s'>No watchdog memos yet.</i>" % MUTED
    else:
        m = memos[-1]
        when = time.strftime("%Y-%m-%d %H:%M PT", time.localtime(m["ts"] - 8 * 3600))
        bar = "#c0392b" if m.get("alert") else G
        body = ("<div style='border-left:4px solid %s;padding-left:14px'>"
                "<div style='color:%s;font-weight:600'>%s</div>"
                "<div style='color:%s;font-size:12px;margin-bottom:8px'>%s</div>"
                "<div><b style='color:%s'>What changed:</b> %s</div>"
                "<div><b style='color:%s'>Why:</b> %s</div>"
                "<div><b style='color:%s'>Action taken:</b> %s</div></div>"
                "<div style='margin-top:8px'><a style='color:%s' href='/watchdog.html'>Full memo feed &rarr;</a></div>" % (
                    bar, bar, _esc(m["title"]), MUTED, when, G, _esc(m["what_changed"]),
                    G, _esc(m["why"]), G, _esc(m["action_taken"]), G))
    # live brakes/gas
    chips = []
    try:
        st = json.loads(STATE.read_text())
        now = time.time()
        for seg, v in st.get("quarantine", {}).items():
            if v.get("until", 0) > now:
                chips.append("<span style='background:#3a1414;color:#e88;padding:3px 9px;border-radius:12px;margin:3px;display:inline-block'>BRAKES %s (%s)</span>" % (seg.upper(), _esc(v.get("reason", ""))))
        for seg, v in st.get("lean_in", {}).items():
            if v.get("until", 0) > now:
                chips.append("<span style='background:#143a18;color:#8e8;padding:3px 9px;border-radius:12px;margin:3px;display:inline-block'>GAS %s x%.2f</span>" % (seg.upper(), v.get("mult", 1)))
    except Exception:
        pass
    if chips:
        body += "<div style='margin-top:12px'>" + "".join(chips) + "</div>"
    else:
        body += "<div style='margin-top:12px;color:%s'>No active quarantines or lean-ins -- engine running normal.</div>" % MUTED
    return _card("&#128081; Self-Healing Watchdog", body)


def todo_block():
    md = _read_first(TODO_PATHS)
    if not md.strip():
        return _card("&#9745; To-Do", "<i style='color:%s'>No ops_todo.md yet.</i>" % MUTED)
    out = []
    for ln in md.splitlines():
        s = ln.strip()
        if not s:
            continue
        if s.startswith("#"):
            out.append("<div style='color:%s;font-weight:600;margin:10px 0 4px'>%s</div>" % (G, _esc(s.lstrip("# "))))
        elif s.startswith("- [x]") or s.startswith("- [X]"):
            out.append("<div style='color:%s'>&#9745; <s>%s</s></div>" % (MUTED, _esc(s[5:].strip())))
        elif s.startswith("- [ ]"):
            out.append("<div>&#9744; %s</div>" % _esc(s[5:].strip()))
        elif s.startswith("- "):
            out.append("<div>&bull; %s</div>" % _esc(s[2:].strip()))
        else:
            out.append("<div>%s</div>" % _esc(s))
    return _card("&#9745; To-Do", "<div style='line-height:1.7'>" + "".join(out) + "</div>")


def mailbox_block(n=12):
    md = _read_first(MAILBOX_PATHS)
    entries = [l for l in md.splitlines() if l.strip().startswith("[")]
    entries = entries[-n:][::-1]
    if not entries:
        return _card("&#128235; Agent Mailbox", "<i style='color:%s'>No mailbox entries found.</i>" % MUTED)
    rows = "".join("<div style='border-bottom:1px solid #222;padding:6px 0;font-size:13px'>%s</div>" % _esc(e) for e in entries)
    return _card("&#128235; Agent Mailbox (latest %d)" % len(entries), "<div style='line-height:1.5'>" + rows + "</div>")


def reports_block():
    links = ["<a style='color:%s' href='/kalshi.html'>Kalshi P&amp;L dashboard</a>" % G,
             "<a style='color:%s' href='/watchdog.html'>Watchdog memos</a>" % G]
    try:
        for f in sorted(HIVE_REPORTS.glob("*.html")):
            if f.name in ("ops.html", "watchdog.html", "kalshi_dashboard.html"):
                continue
            links.append("<a style='color:%s' href='/%s'>%s</a>" % (G, f.name, f.stem.replace("_", " ")))
    except Exception:
        pass
    return _card("&#128202; Reports", "<div style='line-height:2'>" + "<br>".join(links[:25]) + "</div>")


def build():
    updated = time.strftime("%Y-%m-%d %H:%M PT", time.localtime(time.time() - 8 * 3600))
    return ("<!doctype html><html><head><meta charset='utf-8'><meta http-equiv='refresh' content='120'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'><title>Everlight Ops Hub</title></head>"
            "<body style='background:%s;color:#E8E8E8;font-family:Inter,system-ui,sans-serif;max-width:860px;margin:0 auto;padding:26px'>"
            "<h1 style='font-family:\"Playfair Display\",Georgia,serif;color:%s;margin-bottom:0'>Everlight Ops Hub</h1>"
            "<div style='color:%s;margin-bottom:6px'>One page, all the admin. Auto-refresh 120s &middot; updated %s</div>"
            "%s%s%s%s</body></html>" % (
                DK, G, MUTED, updated,
                watchdog_block(), todo_block(), mailbox_block(), reports_block()))


def main():
    html_doc = build()
    for d in HTML_DIRS:
        try:
            Path(d).mkdir(parents=True, exist_ok=True)
            (Path(d) / "ops.html").write_text(html_doc)
            print("ops_dashboard: wrote", Path(d) / "ops.html")
            return 0
        except Exception:
            continue
    print("ops_dashboard: could not write ops.html anywhere")
    return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
