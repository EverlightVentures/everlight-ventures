#!/usr/bin/env python3
"""
Hive Smart Post -- Every message sounds human, looks professional.

Replaces raw post() across all hive systems. Three modes:
1. Quick update (1-3 lines): Human intro + data. No doc.
2. Report (4-10 lines): Human intro + Slack Canvas + HTML luxury link.
3. Document (10+ lines): Human intro + Canvas + HTML + Blinko log.

Usage:
    from hive_smart_post import smart_post
    smart_post("ft-hunters", "Rex Blackwell",
               "Pipeline: 436 leads, 20 buyers, 4872 matches",
               event_type="work_complete")

Convenience:
    from hive_smart_post import rex_posts, piper_posts, marcus_posts
    rex_posts("ft-hunters", "Pipeline: 436 leads, 20 buyers")
"""
from __future__ import annotations

import json
import logging
import os
import re
import requests
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

log = logging.getLogger("smart_post")

# ---------------------------------------------------------------------------
# Slack config -- matches hive_shift_system.py exactly
# ---------------------------------------------------------------------------
SLACK_BOT_TOKEN = os.environ.get(
    "SLACK_BOT_TOKEN",
    "xoxb-8645963765681-10594020158069-eJRt13YP8qedI6DnQwupuFfy",
)

CHANNELS = {
    "war-room": "C0ANAU30UQ2",
    "ft-hunters": "C0AMVEWLT9D",
    "ft-consult": "C0ANEG19WQ4",
    "ft-markets": "C0AP56SFQG0",
    "ft-profit-engine": "C0AN7FT5JBF",
    "ai-consulting": "C0AN8SGAS22",
    "xlm-trading": "C0AN8SG030W",
    "ceo-brief": "C0AP56SQM08",
    "hive-alerts": "C0ANPRCA4AD",
    "watercooler": "C0AN0NQR17Z",
    "deploy-log": "C0AN8SG030W",
    "content-factory": "C0AN0NQR17Z",
    "revenue-dashboard": "C0AN7FT5JBF",
    "broker-pipeline": "C0AMVEWLT9D",
}

BLINKO_URL = "http://129.159.38.250:1111"
PT = timezone(timedelta(hours=-7))  # PDT

# HTML reports served from Oracle
HTML_REPORT_DIR = Path("/home/opc/hive_reports")
HTML_REPORT_URL_BASE = "http://129.159.38.250:8200/reports"

# ---------------------------------------------------------------------------
# Agent personality lookup -- callers don't need to pass style
# ---------------------------------------------------------------------------
AGENT_STYLES: Dict[str, str] = {
    "Rex Blackwell": "Texas drawl. 'Partner.' 'Let me tell you what.' Numbers under the charm.",
    "Piper Reeves": "Nashville warmth. 'Y'all.' Genuine, disarming, always encouraging.",
    "Penny Vance": "Numerical, sharp. 'What's the margin on that?' Chai only. Spreadsheet brain.",
    "Rex Thornton": "Precise, parenthetical. 'Non-trivial.' 'Concerning.' Midwestern quant.",
    "Marcus Cole": "British exec. 'Right then.' 'Sorted.' Short sentences. No hedging.",
    "Harrison Knox": "Relentless closer. 'Champ, when do we close?' Never takes no.",
    "Ryan Kim": "High energy. 'When do we launch?' Metric-driven. Moves fast.",
    "Quinn Sharp": "Systems thinker. Methodical. Quiet satisfaction when uptime hits 99.9%.",
    "Justine Park": "Precise, cautious. 'Let me review that before we proceed.'",
    "Miguel Reyes": "Quant-speak. 'IV rank at 85th percentile.' Numbers before narrative.",
    "Christopher Voss": "Clipped intel-speak. 'Signal confirmed.' Dry humor.",
    "Christopher Wolfe": "Skeptical. 'Source?' Verifies everything twice.",
    "Major Dex": "Military precision. 'Execute.' 'Status report.' Zero fluff.",
    "Charles Dawson": "Data storyteller. Sees patterns in dashboards. Calm.",
    "Samuel Navarro": "Careful, thorough. Flags risk before it becomes a problem.",
    "Atlas Vega": "Strategic. Big picture. Calm under pressure.",
    "Nora Blaine": "Detail-oriented. Catches what others miss. Quietly proud.",
    "Filter Banks": "Numbers only. No small talk. 'Score: 87. Next.'",
    "Cash Monroe": "Revenue-obsessed. 'What's the take?' Always closing.",
    "Cupid Chase": "Matchmaker energy. 'This buyer and this deal? Perfect fit.'",
    "Chart Dawson": "Analytics geek. 'Look at this trend line.' Loves dashboards.",
    "Hammer Voss": "Follow-up machine. 'Champ, circling back.' Never lets a lead drop.",
    "Forge Maddox": "Builder. 'Shipped.' Cares about clean code and fast deploys.",
    "Cipher Voss": "Intel analyst. 'Pattern detected.' Connects dots no one else sees.",
    "Lucrex": "King of Divine Light. Confident, calculated, street-smart. Never hedges. The mind behind the money.",
}

# ---------------------------------------------------------------------------
# AI humanization -- uses hive_model_router for smart routing
# ---------------------------------------------------------------------------

def _get_agent_style(agent_name: str, style_override: Optional[str] = None) -> str:
    """Resolve agent style. Override wins, then lookup, then generic."""
    if style_override:
        return style_override
    return AGENT_STYLES.get(agent_name, "Professional, concise, human.")


def _humanize(agent_name: str, agent_style: str, raw_data: str, event_type: str) -> str:
    """Generate a 1-2 sentence human intro in the agent's voice.

    Uses Gemini (free) via hive_model_router, falls back to gpt-4o-mini,
    falls back to a simple template if all AI fails.
    """
    system_prompt = (
        f"You are {agent_name}. Speech style: {agent_style}\n"
        f"Write a 1-line intro to this data update. Sound like yourself -- "
        f"your personality, your catchphrases, your quirks.\n"
        f"Then state the key takeaway from the data in your own words.\n"
        f"DO NOT just repeat the data. Interpret it. React to it. Be a person.\n"
        f"Max 2 sentences. No hashtags. No emojis. No markdown."
    )

    user_prompt = (
        f"Event: {event_type}\n"
        f"Raw data:\n{raw_data[:1500]}"
    )

    # Try hive_model_router first (handles Gemini -> OpenAI fallback)
    try:
        from hive_model_router import route_and_call
        result = route_and_call(system_prompt, user_prompt, task_type="social", max_tokens=120)
        if result and len(result.strip()) > 5:
            return result.strip()
    except Exception as e:
        log.warning("hive_model_router failed: %s", e)

    # Direct Gemini fallback
    try:
        gemini_key = os.environ.get("GEMINI_API_KEY", "")
        if gemini_key:
            r = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={gemini_key}",
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": f"{system_prompt}\n\n{user_prompt}"}]}],
                    "generationConfig": {"maxOutputTokens": 120, "temperature": 0.9},
                },
                timeout=15,
            )
            r.raise_for_status()
            text = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            if len(text) > 5:
                return text
    except Exception as e:
        log.warning("Direct Gemini fallback failed: %s", e)

    # Direct OpenAI fallback
    try:
        openai_key = os.environ.get("OPENAI_API_KEY", "")
        if openai_key:
            r = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"},
                json={
                    "model": "gpt-4o-mini",
                    "max_tokens": 120,
                    "temperature": 0.9,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                },
                timeout=15,
            )
            r.raise_for_status()
            text = r.json()["choices"][0]["message"]["content"].strip()
            if len(text) > 5:
                return text
    except Exception as e:
        log.warning("Direct OpenAI fallback failed: %s", e)

    # Dead-simple template fallback -- still sounds better than raw
    templates = {
        "Rex Blackwell": "Partner, here's what I'm seeing.",
        "Piper Reeves": "Hey y'all, quick update for you.",
        "Penny Vance": "Ran the numbers. Here's where we stand.",
        "Rex Thornton": "Data's in. Non-trivial findings.",
        "Marcus Cole": "Right then. Here's the situation.",
        "Harrison Knox": "Champ, got the latest for you.",
        "Major Dex": "Status report.",
        "Lucrex": "The numbers speak. Listen.",
    }
    return templates.get(agent_name, f"{agent_name} here. Quick update.")


# ---------------------------------------------------------------------------
# HTML luxury report generation
# ---------------------------------------------------------------------------

_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} -- Everlight Ventures</title>
<style>
  :root {{ --gold: #D4AF37; --dark: #0A0A0A; --card: #141414; --text: #E8E8E8; --muted: #888; }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: 'Segoe UI', system-ui, -apple-system, sans-serif; background: var(--dark); color: var(--text); line-height: 1.6; }}
  .container {{ max-width: 720px; margin: 0 auto; padding: 40px 24px; }}
  .header {{ border-bottom: 2px solid var(--gold); padding-bottom: 20px; margin-bottom: 32px; }}
  .header h1 {{ color: var(--gold); font-size: 1.5rem; font-weight: 600; letter-spacing: 0.5px; }}
  .header .meta {{ color: var(--muted); font-size: 0.85rem; margin-top: 8px; }}
  .agent-badge {{ display: inline-block; background: var(--gold); color: var(--dark); padding: 2px 10px; border-radius: 3px; font-size: 0.8rem; font-weight: 700; letter-spacing: 0.5px; }}
  .content {{ background: var(--card); border-radius: 8px; padding: 28px; margin-bottom: 24px; border: 1px solid #222; }}
  .content pre {{ white-space: pre-wrap; word-wrap: break-word; font-family: 'SF Mono', 'Fira Code', monospace; font-size: 0.9rem; line-height: 1.7; color: var(--text); }}
  .intro {{ font-style: italic; color: var(--gold); margin-bottom: 20px; font-size: 1.05rem; border-left: 3px solid var(--gold); padding-left: 16px; }}
  .footer {{ text-align: center; color: var(--muted); font-size: 0.75rem; margin-top: 40px; padding-top: 20px; border-top: 1px solid #222; }}
  .footer span {{ color: var(--gold); }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>{title}</h1>
    <div class="meta">
      <span class="agent-badge">{agent_name}</span> &nbsp; {timestamp}
    </div>
  </div>
  {intro_block}
  <div class="content">
    <pre>{content}</pre>
  </div>
  <div class="footer">
    <span>Everlight Ventures</span> &mdash; Hive Intelligence Report
  </div>
</div>
</body>
</html>"""


def _generate_html_report(
    title: str, content: str, agent_name: str, intro: str = ""
) -> Tuple[Optional[str], Optional[str]]:
    """Generate a gold-branded HTML report file.

    Returns (url, file_path) or (None, None) on failure.
    """
    ts = datetime.now(PT).strftime("%Y%m%d_%H%M%S")
    slug = re.sub(r"[^a-z0-9]+", "_", title.lower())[:40].strip("_")
    filename = f"{ts}_{slug}.html"

    intro_block = ""
    if intro:
        safe_intro = intro.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        intro_block = f'<div class="intro">{safe_intro}</div>'

    safe_content = content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    timestamp = datetime.now(PT).strftime("%B %d, %Y at %I:%M %p PT")

    html = _HTML_TEMPLATE.format(
        title=title.replace("&", "&amp;").replace("<", "&lt;"),
        agent_name=agent_name,
        timestamp=timestamp,
        intro_block=intro_block,
        content=safe_content,
    )

    # Try writing to Oracle report dir
    try:
        report_dir = HTML_REPORT_DIR
        report_dir.mkdir(parents=True, exist_ok=True)
        file_path = report_dir / filename
        file_path.write_text(html, encoding="utf-8")
        url = f"{HTML_REPORT_URL_BASE}/{filename}"
        log.info("HTML report: %s", url)
        return url, str(file_path)
    except OSError:
        pass

    # Fallback: /tmp for local dev
    try:
        fallback = Path("/tmp/hive_reports")
        fallback.mkdir(parents=True, exist_ok=True)
        file_path = fallback / filename
        file_path.write_text(html, encoding="utf-8")
        log.info("HTML report (local): %s", file_path)
        return None, str(file_path)
    except Exception as e:
        log.error("HTML report generation failed: %s", e)
        return None, None


# ---------------------------------------------------------------------------
# Slack Canvas creation
# ---------------------------------------------------------------------------

def _create_canvas(channel: str, title: str, content: str) -> Optional[str]:
    """Create a Slack Canvas (canvases.create) and return its ID.

    Slack Canvas API requires a paid plan. If it fails, returns None
    and the caller gracefully skips the canvas link.
    """
    cid = CHANNELS.get(channel, channel)
    try:
        # Format content as Slack Canvas document sections
        sections = []
        for line in content.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            if line.startswith("#") or line.startswith("="):
                sections.append({
                    "type": "heading",
                    "text": line.lstrip("#= ").strip(),
                })
            else:
                sections.append({
                    "type": "markdown",
                    "text": line,
                })

        r = requests.post(
            "https://slack.com/api/canvases.create",
            headers={
                "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
                "Content-Type": "application/json",
            },
            json={
                "title": title[:150],
                "document_content": {"type": "markdown", "markdown": content[:4000]},
            },
            timeout=15,
        )
        data = r.json()
        if data.get("ok"):
            canvas_id = data.get("canvas_id", "")
            log.info("Canvas created: %s", canvas_id)

            # Share canvas to channel
            if canvas_id:
                requests.post(
                    "https://slack.com/api/canvases.access.set",
                    headers={
                        "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "canvas_id": canvas_id,
                        "access_level": "read",
                        "channel_ids": [cid],
                    },
                    timeout=10,
                )
            return canvas_id
        else:
            log.debug("Canvas creation failed: %s", data.get("error", "unknown"))
            return None
    except Exception as e:
        log.debug("Canvas creation error: %s", e)
        return None


# ---------------------------------------------------------------------------
# Dual-format handler (Canvas + HTML for longer content)
# ---------------------------------------------------------------------------

def _maybe_dual_format(
    channel: str, agent_name: str, title: str, content: str, intro: str = ""
) -> Dict[str, str]:
    """If content > 3 lines, create Canvas + HTML luxury report. Return links dict."""
    lines = [l for l in content.strip().split("\n") if l.strip()]
    if len(lines) <= 3:
        return {}

    links: Dict[str, str] = {}

    # HTML luxury report
    try:
        url, path = _generate_html_report(title, content, agent_name, intro)
        if url:
            links["html"] = url
        elif path:
            links["html_local"] = path
    except Exception as e:
        log.warning("HTML report failed: %s", e)

    # Slack Canvas
    try:
        canvas_id = _create_canvas(channel, title, content)
        if canvas_id:
            links["canvas"] = f"Canvas: {title}"
            links["canvas_id"] = canvas_id
    except Exception as e:
        log.warning("Canvas creation failed: %s", e)

    return links


# ---------------------------------------------------------------------------
# Blinko logging for document-length content
# ---------------------------------------------------------------------------

def _log_to_blinko(agent_name: str, title: str, content: str, event_type: str):
    """Log longer reports to Blinko for RAG retrieval."""
    lines = [l for l in content.strip().split("\n") if l.strip()]
    if len(lines) < 10:
        return

    note = (
        f"# {title}\n"
        f"#hive/report #hive/{agent_name.lower().replace(' ', '-')} "
        f"#hive/{event_type}\n\n"
        f"Agent: {agent_name}\n"
        f"Time: {datetime.now(PT).strftime('%Y-%m-%d %I:%M %p PT')}\n\n"
        f"{content[:3000]}"
    )

    try:
        r = requests.post(
            f"{BLINKO_URL}/api/v1/note/upsert",
            json={"content": note, "type": 1},
            timeout=10,
        )
        if r.status_code == 200:
            log.info("Blinko log saved for %s: %s", agent_name, title)
    except Exception as e:
        log.debug("Blinko log failed: %s", e)


# ---------------------------------------------------------------------------
# Slack posting (core)
# ---------------------------------------------------------------------------

def _post_to_slack(channel: str, text: str, thread_ts: Optional[str] = None) -> bool:
    """Post a message to Slack. Returns True on success."""
    cid = CHANNELS.get(channel, channel)
    if not cid or not text:
        log.warning("Cannot post: channel=%s text_len=%d", channel, len(text or ""))
        return False

    payload: Dict[str, Any] = {
        "channel": cid,
        "text": text,
        "unfurl_links": False,
    }
    if thread_ts:
        payload["thread_ts"] = thread_ts

    try:
        r = requests.post(
            "https://slack.com/api/chat.postMessage",
            headers={
                "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=15,
        )
        data = r.json()
        if data.get("ok"):
            return True
        log.warning("Slack post failed: %s", data.get("error", "unknown"))
        return False
    except Exception as e:
        log.error("Slack post error: %s", e)
        return False


# ---------------------------------------------------------------------------
# smart_post -- the main function
# ---------------------------------------------------------------------------

def smart_post(
    channel: str,
    agent_name: str,
    raw_data: str,
    event_type: str = "update",
    title: Optional[str] = None,
    agent_style: Optional[str] = None,
    skip_humanize: bool = False,
    thread_ts: Optional[str] = None,
) -> Dict[str, Any]:
    """Post like a human, not a machine.

    Flow:
    1. Resolve agent style from AGENT_STYLES (or use override)
    2. If skip_humanize=False, use AI to generate a 1-line human intro
    3. If raw_data > 3 lines: generate Canvas + HTML luxury report
    4. Post to Slack: human intro + links (if applicable)
    5. If raw_data > 10 lines: also log to Blinko for RAG retrieval

    Args:
        channel:        Slack channel name (key in CHANNELS dict)
        agent_name:     Name of the posting agent (e.g. "Rex Blackwell")
        raw_data:       The actual data/report content
        event_type:     Context for the humanization ("update", "work_complete", etc.)
        title:          Optional title for reports. Auto-generated if None.
        agent_style:    Override style string. Uses AGENT_STYLES lookup if None.
        skip_humanize:  If True, post raw_data with no AI rewrite.
        thread_ts:      Optional Slack thread timestamp for threaded replies.

    Returns:
        Dict with keys: ok (bool), intro (str), links (dict), channel (str)
    """
    result: Dict[str, Any] = {
        "ok": False,
        "intro": "",
        "links": {},
        "channel": channel,
        "agent": agent_name,
    }

    if not raw_data or not raw_data.strip():
        log.warning("smart_post called with empty data from %s", agent_name)
        return result

    style = _get_agent_style(agent_name, agent_style)
    report_title = title or f"{agent_name} -- {event_type.replace('_', ' ').title()}"
    lines = [l for l in raw_data.strip().split("\n") if l.strip()]
    line_count = len(lines)

    # --- Step 1: Humanize the intro ---
    if skip_humanize:
        intro = ""
        message_body = raw_data.strip()
    else:
        intro = _humanize(agent_name, style, raw_data, event_type)
        result["intro"] = intro

        if line_count <= 3:
            # Short update: intro + data on same message
            message_body = f"{intro}\n\n{raw_data.strip()}"
        else:
            # Longer: intro is the main message, data goes to docs
            message_body = intro

    # --- Step 2: Dual format for longer content ---
    links = {}
    if line_count > 3:
        links = _maybe_dual_format(channel, agent_name, report_title, raw_data, intro)
        result["links"] = links

        # Append link lines to the message
        link_lines = []
        if links.get("html"):
            link_lines.append(f"Full report: {links['html']}")
        if links.get("canvas_id"):
            link_lines.append(f"Canvas: {report_title}")

        if link_lines:
            message_body += "\n" + "\n".join(link_lines)
        else:
            # No links available -- include truncated data inline
            truncated = "\n".join(lines[:15])
            if line_count > 15:
                truncated += f"\n... ({line_count - 15} more lines)"
            message_body += f"\n\n```\n{truncated}\n```"

    # --- Step 3: Post to Slack ---
    ok = _post_to_slack(channel, message_body, thread_ts)
    result["ok"] = ok

    # --- Step 4: Blinko log for document-length content ---
    if line_count >= 10:
        _log_to_blinko(agent_name, report_title, raw_data, event_type)

    if ok:
        log.info("smart_post OK: %s -> #%s (%d lines, %d links)",
                 agent_name, channel, line_count, len(links))
    else:
        log.warning("smart_post FAILED: %s -> #%s", agent_name, channel)

    return result


# ---------------------------------------------------------------------------
# Convenience functions -- one-call posting for frequent agents
# ---------------------------------------------------------------------------

def rex_posts(channel: str, data: str, event_type: str = "update", title: Optional[str] = None, **kw) -> Dict[str, Any]:
    """Rex Blackwell posts to Slack in his Texas drawl."""
    return smart_post(channel, "Rex Blackwell", data, event_type, title, **kw)

def piper_posts(channel: str, data: str, event_type: str = "update", title: Optional[str] = None, **kw) -> Dict[str, Any]:
    """Piper Reeves posts with Nashville warmth."""
    return smart_post(channel, "Piper Reeves", data, event_type, title, **kw)

def penny_posts(channel: str, data: str, event_type: str = "update", title: Optional[str] = None, **kw) -> Dict[str, Any]:
    """Penny Vance posts with sharp numerical precision."""
    return smart_post(channel, "Penny Vance", data, event_type, title, **kw)

def marcus_posts(channel: str, data: str, event_type: str = "update", title: Optional[str] = None, **kw) -> Dict[str, Any]:
    """Marcus Cole posts with British exec brevity."""
    return smart_post(channel, "Marcus Cole", data, event_type, title, **kw)

def lucrex_posts(channel: str, data: str, event_type: str = "update", title: Optional[str] = None, **kw) -> Dict[str, Any]:
    """Lucrex posts as the King of Divine Light."""
    return smart_post(channel, "Lucrex", data, event_type, title, **kw)

def rex_t_posts(channel: str, data: str, event_type: str = "update", title: Optional[str] = None, **kw) -> Dict[str, Any]:
    """Rex Thornton posts with Midwestern quant precision."""
    return smart_post(channel, "Rex Thornton", data, event_type, title, **kw)

def major_dex_posts(channel: str, data: str, event_type: str = "update", title: Optional[str] = None, **kw) -> Dict[str, Any]:
    """Major Dex posts with military precision."""
    return smart_post(channel, "Major Dex", data, event_type, title, **kw)

def hammer_posts(channel: str, data: str, event_type: str = "update", title: Optional[str] = None, **kw) -> Dict[str, Any]:
    """Hammer Voss posts as the follow-up machine."""
    return smart_post(channel, "Hammer Voss", data, event_type, title, **kw)

def forge_posts(channel: str, data: str, event_type: str = "update", title: Optional[str] = None, **kw) -> Dict[str, Any]:
    """Forge Maddox posts as the builder."""
    return smart_post(channel, "Forge Maddox", data, event_type, title, **kw)

def cipher_posts(channel: str, data: str, event_type: str = "update", title: Optional[str] = None, **kw) -> Dict[str, Any]:
    """Cipher Voss posts with intel analyst precision."""
    return smart_post(channel, "Cipher Voss", data, event_type, title, **kw)

def filter_posts(channel: str, data: str, event_type: str = "update", title: Optional[str] = None, **kw) -> Dict[str, Any]:
    """Filter Banks posts with numbers only."""
    return smart_post(channel, "Filter Banks", data, event_type, title, **kw)

def chart_posts(channel: str, data: str, event_type: str = "update", title: Optional[str] = None, **kw) -> Dict[str, Any]:
    """Chart Dawson posts with analytics."""
    return smart_post(channel, "Chart Dawson", data, event_type, title, **kw)


# ---------------------------------------------------------------------------
# Drop-in replacement for legacy post()
# ---------------------------------------------------------------------------

def post(channel_name: str, text: str) -> bool:
    """Drop-in replacement for hive_shift_system.post().

    Same signature, same return type. But now the message gets humanized
    if it contains an agent name pattern like '[AGENT_NAME]' or 'Agent: Name'.
    Otherwise posts raw (for backward compat with non-agent messages).
    """
    # Try to detect agent name from common patterns
    agent_match = re.match(
        r"^(?:\*\*)?([A-Z][a-z]+ [A-Z][a-z]+)(?:\*\*)?\s*[\[\(:]",
        text,
    )
    if agent_match:
        agent_name = agent_match.group(1)
        if agent_name in AGENT_STYLES:
            # Strip the agent prefix and brackets from raw data
            cleaned = re.sub(
                r"^(?:\*\*)?[A-Z][a-z]+ [A-Z][a-z]+(?:\*\*)?\s*\[.*?\]\s*",
                "",
                text,
            ).strip()
            result = smart_post(channel_name, agent_name, cleaned or text)
            return result.get("ok", False)

    # No agent detected -- post raw (backward compat)
    return _post_to_slack(channel_name, text)


# ---------------------------------------------------------------------------
# CLI test mode
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.DEBUG, format="%(name)s %(levelname)s: %(message)s")

    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        print("=== Smart Post Test Mode ===\n")

        # Test short update
        print("--- Short update (Rex) ---")
        r = smart_post(
            "watercooler", "Rex Blackwell",
            "Pipeline: 436 leads, 20 buyers, 4872 matches",
            event_type="work_complete",
            skip_humanize=("--no-ai" in sys.argv),
        )
        print(f"  OK: {r['ok']}")
        print(f"  Intro: {r['intro']}")
        print()

        # Test longer report
        print("--- Report (Penny) ---")
        report_data = "\n".join([
            "Revenue Summary -- March 2026",
            "Broker OS: $2,400 (3 deals closed)",
            "AI Consulting: $4,000 (2 retainers)",
            "XLM Bot: $312 (paper gains)",
            "Onyx POS: $147 (3 subscribers)",
            "Publishing: $89 (KDP royalties)",
            "Total: $6,948",
            "Target: $10,000",
            "Gap: $3,052",
            "Projection: On track if consulting pipeline converts",
        ])
        r = smart_post(
            "revenue-dashboard", "Penny Vance",
            report_data,
            event_type="revenue_report",
            title="March 2026 Revenue Summary",
            skip_humanize=("--no-ai" in sys.argv),
        )
        print(f"  OK: {r['ok']}")
        print(f"  Intro: {r['intro']}")
        print(f"  Links: {r['links']}")
        print()

        # Test convenience function
        print("--- Convenience (marcus_posts) ---")
        r = marcus_posts("ceo-brief", "All systems nominal. Bot running. Pipeline active.")
        print(f"  OK: {r['ok']}")
        print(f"  Intro: {r['intro']}")

    elif len(sys.argv) > 1 and sys.argv[1] == "--agents":
        print("=== Registered Agent Styles ===\n")
        for name, style in sorted(AGENT_STYLES.items()):
            print(f"  {name:25s}  {style}")

    else:
        print("Hive Smart Post -- Human-sounding, dual-format posting for 63 agents")
        print()
        print("Usage:")
        print("  python3 hive_smart_post.py --test        Run live test posts")
        print("  python3 hive_smart_post.py --test --no-ai  Test without AI humanization")
        print("  python3 hive_smart_post.py --agents      List registered agent styles")
        print()
        print("Import:")
        print("  from hive_smart_post import smart_post, rex_posts, marcus_posts")
        print()
        print(f"  {len(AGENT_STYLES)} agents registered")
        print(f"  {len(CHANNELS)} channels configured")
