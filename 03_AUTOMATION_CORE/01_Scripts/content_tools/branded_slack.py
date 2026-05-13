"""branded_slack -- the SINGLE path every Slack post must take.

Auto-archive
------------
By default every branded post is also written to disk as a standalone
branded HTML page on Oracle (`hive_reports/`) so the "View full report"
button in Slack ALWAYS deep-links to the specific post, not a directory.
The archive uses the same Playfair/Inter gold theme as every other Hive
report, so the post reads identically in Slack and on the dashboard.
Set `auto_archive=False` to suppress (e.g. for ephemeral pings).

Why this exists
---------------
Slack is the surface the team actually looks at every day. If half the bots
post plain text and the other half post Block Kit, the brand reads as a
patchwork. This module enforces ONE post format so every message looks like
it came from the same company.

Brand contract (Everlight)
--------------------------
Every branded post produces a Block Kit message with:

  1. Header block      -- "Everlight Ventures" mini-wordmark + title
  2. Divider
  3. Summary block     -- one-line headline, mrkdwn
  4. Body block        -- main content, mrkdwn (optional)
  5. Fields block      -- key/value pairs (optional, max 8)
  6. Actions block     -- "View full report" + "Open in dashboard" buttons (optional)
  7. Context block     -- agent attribution, timestamp, brand sigil

The result mirrors the Everlight gold-and-Playfair email/HTML theme as
closely as Slack's Block Kit allows. No emoji clutter unless explicitly
allowed by the caller.

Public API
----------
    from content_tools.branded_slack import post_branded_slack

    res = post_branded_slack(
        channel="#war-room",
        title="Daily Pipeline Brief",
        summary="42 leads scouted, 7 matched, 1 deal closed today.",
        body="..." ,                    # optional markdown body
        fields={"Leads":"42","Matched":"7","Closed":"1"},   # optional
        report_url="http://127.0.0.1:2200/reports/...html",  # optional
        doc_url="https://docs.google.com/...",              # optional
        agent_name="Marcus Cole",
        agent_title="Chief Operator",
    )
    # -> {"ok": True, "ts": "...", "channel": "...", "permalink": "..."}

Categories
----------
The `category` argument hints which channel charter the post belongs to.
Used for color-coded accents on Slack and for analytics:
  "report"  | "alert" | "deal" | "intel" | "ops" | "system"
"""
from __future__ import annotations

import json
import logging
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

log = logging.getLogger("branded_slack")

WORKSPACE_CANDIDATES = [
    Path("/mnt/sdcard/AA_MY_DRIVE"),
    Path("/home/opc/AA_MY_DRIVE"),
    Path("/home/opc"),
]

SLACK_API = "https://slack.com/api/chat.postMessage"

# Brand color (Everlight gold) -- used for attachment color stripe
BRAND_GOLD = "#D4A843"

# Category accent colors
CATEGORY_COLORS = {
    "report":  BRAND_GOLD,
    "alert":   "#EF4444",
    "deal":    "#22C55E",
    "intel":   "#6C3FA0",
    "ops":     "#3B82F6",
    "system":  "#999999",
}

# Channel ID map -- only the IDs we have ground-truth for.
# Slack chat.postMessage accepts the channel name directly when the bot is
# in the channel, so we only NEED the ID for the warroom (most posted).
# Add more IDs here as you confirm them via slack.conversations.list.
CHANNEL_NAME_TO_ID = {
    "#war-room":         "C0ANAU30UQ2",
    "#deploy-log":       "C0AN4GSTMT5",
}


def _workspace() -> Path:
    for p in WORKSPACE_CANDIDATES:
        if p.exists():
            return p
    return WORKSPACE_CANDIDATES[0]


def _load_env_once() -> None:
    if os.environ.get("_BRANDED_SLACK_ENV_LOADED"):
        return
    for env_path in (
        _workspace() / "03_AUTOMATION_CORE" / "03_Credentials" / ".env",
        Path("/home/opc/.env"),
    ):
        if not env_path.exists():
            continue
        try:
            for line in env_path.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("export "):
                    line = line[7:]
                if "=" not in line:
                    continue
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
        except Exception:
            pass
    os.environ["_BRANDED_SLACK_ENV_LOADED"] = "1"


# Hosts where /reports/ is served (used to detect "generic landing" URLs)
_REPORT_HOSTS = ["163.192.19.196:8504", "localhost:8504"]


def _is_generic_reports_url(url: str | None) -> bool:
    """True if the URL just points at the reports directory, not a specific file."""
    if not url:
        return False
    u = url.rstrip("/").lower()
    if u.endswith("/reports") or u.endswith("/reports/"):
        return True
    # Also flag bare host roots
    for h in _REPORT_HOSTS:
        if u in (f"http://{h}", f"https://{h}"):
            return True
    return False


def _slugify(text: str, max_len: int = 60) -> str:
    """Convert title to a filesystem-safe slug for the archive filename."""
    s = re.sub(r"[^\w\s\-]", "", (text or "").lower()).strip()
    s = re.sub(r"[\s_-]+", "_", s)
    return (s[:max_len] or "post").rstrip("_")


def _archive_dirs() -> tuple[Path, str]:
    """Return (filesystem_dir, public_url_base) for the archive.

    Django's report_detail view at /reports/<hash>/ auto-appends `.html`
    when looking up the file, so we expose the URL WITHOUT the .html
    extension and with a trailing slash. The view will resolve
    `<dir>/<hash>.html` on disk.
    """
    if Path("/home/opc/hive_reports").exists():
        return Path("/home/opc/hive_reports"), "http://127.0.0.1:2200/reports"
    return _workspace() / "09_DASHBOARD" / "reports", "http://127.0.0.1:2200/reports"


def _build_archive_html(
    *,
    title: str,
    summary: str,
    body: str | None,
    fields: dict[str, Any] | None,
    agent_name: str,
    agent_title: str,
    category: str,
) -> str:
    """Render this post as a standalone branded HTML page.

    Tries to use report_template.render_report() for full Hive consistency;
    falls back to an inline branded layout if the template module is absent.
    """
    # Convert Slack mrkdwn body to a simple HTML body
    def md_to_html(s: str) -> str:
        if not s:
            return ""
        out = s
        # *bold* -> <strong>
        out = re.sub(r"\*([^*\n]+)\*", r"<strong>\1</strong>", out)
        # _italic_ -> <em>
        out = re.sub(r"_([^_\n]+)_", r"<em>\1</em>", out)
        # `code`
        out = re.sub(r"`([^`\n]+)`", r"<code>\1</code>", out)
        # Lines starting with "- " -> list items (group consecutive)
        lines = out.split("\n")
        rendered: list[str] = []
        in_list = False
        for ln in lines:
            stripped = ln.strip()
            if stripped.startswith("- "):
                if not in_list:
                    rendered.append("<ul>")
                    in_list = True
                rendered.append(f"<li>{stripped[2:]}</li>")
            else:
                if in_list:
                    rendered.append("</ul>")
                    in_list = False
                if stripped:
                    rendered.append(f"<p>{stripped}</p>")
        if in_list:
            rendered.append("</ul>")
        return "\n".join(rendered)

    summary_html = f'<p style="font-weight:600;color:#D4A843;font-size:17px;">{summary}</p>' if summary else ""
    body_html = md_to_html(body or "")

    # Optional fields table
    fields_html = ""
    if fields:
        rows = "".join(
            f"<tr><th>{k}</th><td>{v}</td></tr>"
            for k, v in list(fields.items())[:8]
        )
        fields_html = f'<h3>Details</h3><table>{rows}</table>'

    inner = (
        f"<p><em>Category: {category}</em></p>"
        f"{summary_html}"
        f"{body_html}"
        f"{fields_html}"
    )

    # Try the canonical report template first
    try:
        ws = _workspace()
        for cand in (
            ws / "03_AUTOMATION_CORE" / "01_Scripts" / "content_tools",
            Path("/home/opc/content_tools"),
        ):
            if cand.exists() and str(cand) not in sys.path:
                sys.path.insert(0, str(cand))
        from report_template import render_report  # type: ignore
        return render_report(
            title=title or "Hive Update",
            content_html=inner,
            agent_name=agent_name,
            agent_title=agent_title,
            agent_email="",
        )
    except Exception:
        pass

    # Fallback inline gold theme (rarely hit -- report_template is always shipped)
    return (
        '<!DOCTYPE html><html><head><meta charset="UTF-8">'
        f'<title>{title} | Everlight Ventures</title>'
        '<style>'
        'body{background:#0A0A0A;color:#E8E8E8;font-family:Inter,system-ui,sans-serif;line-height:1.7;}'
        '.wrap{max-width:800px;margin:40px auto;padding:0 24px;}'
        '.h{background:linear-gradient(135deg,#0A0A0A,#1A1A1A);border-bottom:2px solid #D4A843;padding:28px;text-align:center;}'
        '.h .logo{font-family:Playfair Display,serif;color:#D4A843;letter-spacing:4px;font-size:13px;text-transform:uppercase;}'
        '.h h1{font-family:Playfair Display,serif;color:#E8E8E8;font-size:26px;margin:8px 0 0;}'
        '.body{padding:32px 0;}'
        '.body h2,.body h3{font-family:Playfair Display,serif;color:#D4A843;}'
        'table{width:100%;border-collapse:collapse;margin:14px 0;}'
        'th{background:#1A1A1A;color:#D4A843;text-align:left;padding:10px;}'
        'td{padding:10px;border-bottom:1px solid #1a1a1a;}'
        'code{background:#1a1a1a;padding:2px 6px;border-radius:3px;color:#D4A843;}'
        '.ftr{text-align:center;color:#999;font-size:12px;letter-spacing:2px;border-top:1px solid #1a1a1a;padding:24px;}'
        '</style></head><body>'
        '<div class="wrap">'
        f'<div class="h"><div class="logo">EVERLIGHT VENTURES</div><h1>{title}</h1></div>'
        f'<div class="body">{inner}</div>'
        '<div class="ftr">EVERLIGHT VENTURES · The Mind Behind the Money</div>'
        "</div></body></html>"
    )


def _archive_post(
    *,
    title: str,
    summary: str,
    body: str | None,
    fields: dict[str, Any] | None,
    agent_name: str,
    agent_title: str,
    category: str,
) -> str:
    """Write this post to disk as a standalone branded HTML page.

    Returns the public URL. On any error returns "" (caller falls back to
    not rendering the button at all).
    """
    try:
        dir_, base_url = _archive_dirs()
        dir_.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        slug = _slugify(title or summary or "post")
        hash_id = f"{ts}_{slug}"  # Django view receives this as report_hash
        fname = f"{hash_id}.html"
        html = _build_archive_html(
            title=title, summary=summary, body=body, fields=fields,
            agent_name=agent_name, agent_title=agent_title, category=category,
        )
        (dir_ / fname).write_text(html, encoding="utf-8")
        # URL without .html and with trailing slash -- Django's report_detail
        # view appends .html on lookup and requires the trailing slash.
        return f"{base_url}/{hash_id}/"
    except Exception as exc:
        log.warning("auto_archive failed: %s", exc)
        return ""


def _resolve_channel(channel: str) -> str:
    """Accept #name, name, or raw channel ID.

    Strategy: if we have a ground-truth ID for this name, use it. Otherwise
    pass the name (with or without #) straight to Slack -- chat.postMessage
    accepts channel names when the bot is a member.
    """
    c = (channel or "").strip()
    if not c:
        return ""
    if c.startswith("C") or c.startswith("D") or c.startswith("G"):
        return c  # already an ID
    key = c if c.startswith("#") else "#" + c
    if key in CHANNEL_NAME_TO_ID:
        return CHANNEL_NAME_TO_ID[key]
    # Fall back to the name itself; Slack will resolve it server-side
    return key


def _slack_token() -> str:
    """Pick the warroom bot token first, fall back to generic SLACK_BOT_TOKEN."""
    _load_env_once()
    return (
        os.environ.get("SLACK_WARROOM_TOKEN")
        or os.environ.get("SLACK_BOT_TOKEN")
        or os.environ.get("WARROOM_BOT_TOKEN")
        or ""
    )


@dataclass
class SlackResult:
    ok: bool
    ts: str = ""
    channel: str = ""
    permalink: str = ""
    error: str = ""


def _build_blocks(
    *,
    title: str,
    summary: str,
    body: str | None,
    fields: dict[str, Any] | None,
    report_url: str | None,
    doc_url: str | None,
    agent_name: str,
    agent_title: str,
    category: str,
) -> list[dict]:
    """Construct the canonical Block Kit array for a branded post."""
    blocks: list[dict] = []

    # 1. Header (uses Slack's plain_text header block; bold + larger size)
    if title:
        blocks.append({
            "type": "header",
            "text": {"type": "plain_text", "text": title[:150], "emoji": False},
        })

    # 2. Wordmark context line
    blocks.append({
        "type": "context",
        "elements": [
            {"type": "mrkdwn", "text": "*EVERLIGHT VENTURES*  ·  _The Mind Behind the Money_"},
        ],
    })

    # 3. Divider
    blocks.append({"type": "divider"})

    # 4. Summary
    if summary:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*{summary}*"},
        })

    # 5. Body (markdown)
    if body:
        # Slack section text limit is 3000 chars
        body_text = body if len(body) <= 2900 else body[:2880] + "  …_(truncated)_"
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": body_text},
        })

    # 6. Fields (max 10 fields per Slack spec; we cap at 8 for readability)
    if fields:
        items = list(fields.items())[:8]
        if items:
            blocks.append({
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*{k}*\n{v}"}
                    for k, v in items
                ],
            })

    # 7. Actions (buttons) -- only render if at least one URL provided
    elements: list[dict] = []
    if report_url:
        elements.append({
            "type": "button",
            "text": {"type": "plain_text", "text": "View full report", "emoji": False},
            "url": report_url[:3000],
            "style": "primary",
        })
    if doc_url:
        elements.append({
            "type": "button",
            "text": {"type": "plain_text", "text": "Open Google Doc", "emoji": False},
            "url": doc_url[:3000],
        })
    if elements:
        blocks.append({"type": "actions", "elements": elements})

    # 8. Context footer -- agent attribution + brand sigil + timestamp
    ts_text = datetime.now().strftime("%Y-%m-%d %H:%M PT")
    sigil = f"_{agent_name} · {agent_title}_  ·  *{ts_text}*  ·  category: `{category}`"
    blocks.append({
        "type": "context",
        "elements": [
            {"type": "mrkdwn", "text": sigil},
        ],
    })

    return blocks


def post_branded_slack(
    *,
    channel: str,
    title: str = "",
    summary: str = "",
    body: str | None = None,
    fields: dict[str, Any] | None = None,
    report_url: str | None = None,
    doc_url: str | None = None,
    agent_name: str = "Hive Mind",
    agent_title: str = "Everlight Ventures",
    category: str = "report",
    fallback_text: str | None = None,
    thread_ts: str | None = None,
    timeout: int = 10,
    auto_archive: bool = True,
) -> SlackResult:
    """Post one branded Slack message. Returns SlackResult, never raises.

    Behavior of the "View full report" button:
      - If `report_url` is a specific URL (a file on the dashboard), it is used.
      - If `report_url` is empty/missing AND `auto_archive=True` (default),
        a standalone branded HTML page is written to Oracle's `hive_reports/`
        and the button links to THAT specific page.
      - If `report_url` looks like a generic landing (e.g. `/reports/` root),
        the button is suppressed entirely.
    """
    token = _slack_token()
    if not token:
        return SlackResult(ok=False, error="no_slack_token_in_env")

    chan = _resolve_channel(channel)
    if not chan:
        return SlackResult(ok=False, error="empty_channel")

    # Sanitize / auto-archive the report URL before block-building
    if _is_generic_reports_url(report_url):
        report_url = None  # never link to the directory root
    if not report_url and auto_archive:
        archived_url = _archive_post(
            title=title, summary=summary, body=body, fields=fields,
            agent_name=agent_name, agent_title=agent_title, category=category,
        )
        if archived_url and not _is_generic_reports_url(archived_url):
            report_url = archived_url

    blocks = _build_blocks(
        title=title,
        summary=summary,
        body=body,
        fields=fields,
        report_url=report_url,
        doc_url=doc_url,
        agent_name=agent_name,
        agent_title=agent_title,
        category=category,
    )

    # Plain-text fallback for notifications and clients that don't render blocks
    fb = fallback_text or f"{title} -- {summary}".strip(" -")[:300] or "Hive update"

    payload: dict[str, Any] = {
        "channel": chan,
        "text": fb,
        "blocks": blocks,
        "unfurl_links": False,
        "unfurl_media": False,
    }
    if thread_ts:
        payload["thread_ts"] = thread_ts

    body_bytes = json.dumps(payload).encode("utf-8")
    req = Request(
        SLACK_API,
        data=body_bytes,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "everlight-branded-slack/1.0",
        },
        method="POST",
    )
    try:
        with urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8") or "{}")
    except (HTTPError, URLError, TimeoutError) as exc:
        return SlackResult(ok=False, error=str(exc))
    except Exception as exc:
        return SlackResult(ok=False, error=repr(exc))

    if not data.get("ok"):
        return SlackResult(ok=False, error=str(data.get("error", "unknown_slack_error")))

    return SlackResult(
        ok=True,
        ts=str(data.get("ts", "")),
        channel=str(data.get("channel", chan)),
        permalink="",  # could fetch via chat.getPermalink in a follow-up call
    )


def post_branded_alert(
    *,
    channel: str,
    title: str,
    detail: str,
    severity: str = "warning",
    agent_name: str = "Hive Watchdog",
    report_url: str | None = None,
) -> SlackResult:
    """Convenience wrapper for system alerts (uses red category accent)."""
    return post_branded_slack(
        channel=channel,
        title=f"[{severity.upper()}] {title}",
        summary=detail[:300],
        report_url=report_url,
        agent_name=agent_name,
        agent_title="System Health",
        category="alert",
        fallback_text=f"ALERT: {title} -- {detail[:140]}",
    )


# ── CLI ────────────────────────────────────────────────────────────

def _cli() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--channel", required=True)
    ap.add_argument("--title", default="")
    ap.add_argument("--summary", required=True)
    ap.add_argument("--body", default="")
    ap.add_argument("--report-url", default="")
    ap.add_argument("--agent-name", default="Hive Mind")
    ap.add_argument("--agent-title", default="Everlight Ventures")
    ap.add_argument("--category", default="report")
    args = ap.parse_args()

    res = post_branded_slack(
        channel=args.channel,
        title=args.title,
        summary=args.summary,
        body=args.body or None,
        report_url=args.report_url or None,
        agent_name=args.agent_name,
        agent_title=args.agent_title,
        category=args.category,
    )
    print(json.dumps({"ok": res.ok, "ts": res.ts, "channel": res.channel, "error": res.error}, indent=2))
    return 0 if res.ok else 1


if __name__ == "__main__":
    sys.exit(_cli())
