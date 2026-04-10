"""
Google Docs Bridge -- publish markdown reports and share links in Slack.

All bot/agent outputs go to Google Docs (formatted markdown).
Slack gets summary + report links (Google Doc and Canvas when available).

Two modes:
  1. n8n mode (default): POST to n8n webhook which creates the Google Doc
     via its Google Docs node and posts the link to Slack.
  2. Direct mode: Uses Google Docs/Drive API directly with service account
     credentials (fallback if n8n is down).

Usage:
    from content_tools.gdocs_bridge import publish_report

    publish_report(
        title="Broker Scout Report",
        content=markdown_string,
        folder="01_Broker_OS/Scout_Reports",
        slack_channel="#all-everlightventures",
        summary="Found 3 new sellers, 2 new buyers. 1 high-confidence match.",
    )

CLI:
    python3 gdocs_bridge.py <file.md> --folder 01_Broker_OS/Scout_Reports
    python3 gdocs_bridge.py <file.md> --channel "#all-everlightventures"
"""

import os
import sys
import json
import time
import logging
import requests
from datetime import datetime
from pathlib import Path

log = logging.getLogger("gdocs_bridge")

GOOGLE_DOCS_SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive.file",
]

# --- Configuration ---

def _candidate_webhook_urls():
    urls = []
    preferred = os.environ.get("N8N_GDOCS_WEBHOOK", "").strip()
    defaults = [
        "http://127.0.0.1:5678/webhook/SU0qTaKHBX1r3oLX/r/hive-log-to-gdoc",
        "http://localhost:5678/webhook/SU0qTaKHBX1r3oLX/r/hive-log-to-gdoc",
    ]
    for url in ([preferred] if preferred else []) + defaults:
        clean = str(url or "").strip()
        if clean and clean not in urls:
            urls.append(clean)
    return urls


def _n8n_enabled():
    value = str(
        os.environ.get("GDOCS_DISABLE_N8N", os.environ.get("N8N_GDOCS_DISABLE", ""))
    ).strip().lower()
    return value not in {"1", "true", "yes", "on"}

# Slack webhook (for posting summary + link)
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "")

# Slack bot tokens for targeted channel posting (from env vars only, no hardcoded fallbacks)
SLACK_TOKENS = {
    "xlmbot": os.environ.get("SLACK_TOKEN_XLMBOT", "") or os.environ.get("SLACK_BOT_TOKEN", ""),
    "warroom": os.environ.get("SLACK_TOKEN_WARROOM", "") or os.environ.get("SLACK_WARROOM_TOKEN", ""),
}

# Slack channel name -> ID mapping (populated on first use)
_channel_cache = {}

# Google Drive folder mapping (matches google_drive_structure.md)
FOLDER_MAP = {
    "00_Command_Center/Daily_Briefings": "daily_briefing",
    "00_Command_Center/War_Room": "war_room",
    "00_Command_Center/System_Status": "system_status",
    "01_Broker_OS/Scout_Reports": "broker_scout",
    "01_Broker_OS/Match_Reports": "broker_match",
    "01_Broker_OS/Outreach_Logs": "broker_outreach",
    "01_Broker_OS/Seller_Replies": "broker_replies",
    "01_Broker_OS/Deal_Pipeline": "broker_deals",
    "01_Broker_OS/Daily_KPI": "broker_kpi",
    "01_Broker_OS/Follow_Up_Tracker": "broker_followup",
    "02_XLM_Bot/Trade_Reports": "xlm_trades",
    "02_XLM_Bot/Daily_Scoreboard": "xlm_daily",
    "02_XLM_Bot/Risk_Alerts": "xlm_risk",
    "02_XLM_Bot/AI_Advisor_Decisions": "xlm_advisor",
    "03_Content_Factory/Social_Posts": "content_social",
    "03_Content_Factory/Avatar_Output": "content_avatar",
    "03_Content_Factory/Funnel_Reports": "content_funnel",
    "03_Content_Factory/Publishing_Pipeline": "content_publishing",
    "04_Revenue_Dashboard/Stripe_Reports": "rev_stripe",
    "04_Revenue_Dashboard/Monthly_Revenue": "rev_monthly",
    "05_AI_Workers/Hive_Mind_Logs": "ai_hive",
    "05_AI_Workers/Blinko_Knowledge": "ai_blinko",
    "06_Infrastructure/Oracle_Cloud": "infra_oracle",
    "06_Infrastructure/N8N_Workflow_Logs": "infra_n8n",
    "07_Logistics/Client_Files": "logistics_clients",
    "08_Legal_Compliance/Contracts": "legal_contracts",
}

# Default Slack channel per folder category
FOLDER_CHANNEL_MAP = {
    "00_Command_Center": "#all-everlightventures",
    "01_Broker_OS": "#all-everlightventures",
    "02_XLM_Bot": "#all-everlightventures",
    "03_Content_Factory": "#all-everlightventures",
    "04_Revenue_Dashboard": "#all-everlightventures",
    "05_AI_Workers": "#gpt_bot_30",
    "06_Infrastructure": "#all-everlightventures",
    "07_Logistics": "#all-everlightlogistics",
    "08_Legal_Compliance": "#all-everlightventures",
}


def _timestamp():
    """Current PT timestamp for filenames."""
    from datetime import timezone, timedelta
    pt = timezone(timedelta(hours=-7))  # PDT
    now = datetime.now(pt)
    return now.strftime("%Y-%m-%d_%H-%M-PT")


def _make_doc_title(title, folder=None):
    """Generate standardized doc title with timestamp."""
    ts = _timestamp()
    # Extract source tag from folder path
    source_tag = ""
    if folder and folder in FOLDER_MAP:
        source_tag = FOLDER_MAP[folder]
    elif folder:
        source_tag = folder.split("/")[-1].lower().replace(" ", "_")
    if source_tag:
        return f"{ts}_{source_tag}_{title.replace(' ', '_')}"
    return f"{ts}_{title.replace(' ', '_')}"


def _extract_links(payload):
    """Extract doc/canvas links from n8n response payload."""
    if not isinstance(payload, dict):
        return {"doc_link": "", "canvas_link": ""}

    doc_link = ""
    canvas_link = ""

    # Preferred explicit keys first
    for key in (
        "webViewLink",
        "doc_link",
        "docLink",
        "google_doc_url",
        "googleDocUrl",
    ):
        val = payload.get(key)
        if isinstance(val, str) and val.strip():
            doc_link = val.strip()
            break

    for key in (
        "canvas_link",
        "canvasLink",
        "canvas_url",
        "canvasUrl",
        "slack_canvas_url",
        "canvasDeepLink",
        "deep_link",
    ):
        val = payload.get(key)
        if isinstance(val, str) and val.strip():
            canvas_link = val.strip()
            break

    # Heuristic fallback from generic URL fields
    for key in ("url", "link"):
        val = payload.get(key)
        if not isinstance(val, str) or not val.strip():
            continue
        v = val.strip()
        if not doc_link and "docs.google.com" in v:
            doc_link = v
        if not canvas_link and "slack.com" in v and "canvas" in v.lower():
            canvas_link = v

    # Last pass: scan string values in response
    for val in payload.values():
        if not isinstance(val, str):
            continue
        v = val.strip()
        if not doc_link and "docs.google.com" in v:
            doc_link = v
        if not canvas_link and "slack.com" in v and "canvas" in v.lower():
            canvas_link = v

    return {"doc_link": doc_link, "canvas_link": canvas_link}


def _post_to_n8n(title, content, folder=None, metadata=None):
    """
    Send content to n8n webhook for Google Doc creation.
    Returns the response (which should contain webViewLink).
    """
    payload = {
        "filename": title,
        "content": content,
        "timestamp": _timestamp(),
        "source": "Everlight Automation",
        "doc_type": folder or "general",
        "folder_path": folder or "",
    }
    if metadata:
        payload.update(metadata)

    last_error = "n8n_unreachable"
    attempted = []
    for webhook_url in _candidate_webhook_urls():
        attempted.append(webhook_url)
        try:
            resp = requests.post(webhook_url, json=payload, timeout=30)
            if resp.status_code == 200:
                data = resp.json() if resp.text.strip() else {}
                links = _extract_links(data)
                doc_link = links.get("doc_link", "")
                canvas_link = links.get("canvas_link", "")
                if doc_link:
                    log.info(f"Google Doc created via n8n: {doc_link}")
                if canvas_link:
                    log.info(f"Canvas link returned by n8n: {canvas_link}")
                return {
                    "ok": True,
                    "link": doc_link,
                    "doc_link": doc_link,
                    "canvas_link": canvas_link,
                    "data": data,
                    "webhook_url": webhook_url,
                }
            last_error = f"HTTP {resp.status_code}"
            log.warning(f"n8n webhook {webhook_url} returned {resp.status_code}: {resp.text[:200]}")
        except requests.ConnectionError:
            last_error = "n8n_unreachable"
            log.warning(f"n8n webhook unreachable: {webhook_url}")
        except Exception as e:
            last_error = str(e)
            log.error(f"n8n error via {webhook_url}: {e}")
    log.warning(f"n8n Google Docs workflow unavailable ({last_error}) -- falling back to direct Google Docs or local file save")
    return {"ok": False, "error": last_error, "attempted": attempted}


def _default_bot_dir():
    raw = os.environ.get("CRYPTO_BOT_DIR", "").strip()
    if raw:
        return Path(raw).expanduser()
    return Path(__file__).resolve().parent.parent


def _candidate_google_client_secret_paths():
    bot_dir = _default_bot_dir()
    paths = [
        os.environ.get("GOOGLE_DOCS_CLIENT_SECRET_FILE", "").strip(),
        str(bot_dir / "secrets" / "google_client_secret.json"),
        "/mnt/sdcard/AA_MY_DRIVE/08_BACKUPS/Credentials_Plaintext_Backup/client_secret_864189495801-pssn6fg438ahieth9vqih41a188smghu.apps.googleusercontent.com.json",
    ]
    return [Path(p).expanduser() for p in paths if p]


def _candidate_google_token_paths():
    bot_dir = _default_bot_dir()
    paths = [
        os.environ.get("GOOGLE_DOCS_TOKEN_FILE", "").strip(),
        str(bot_dir / "secrets" / "google_docs_token.json"),
    ]
    return [Path(p).expanduser() for p in paths if p]


def _persist_google_token(token_path, creds):
    try:
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(creds.to_json(), encoding="utf-8")
    except Exception as exc:
        log.warning(f"Failed to persist Google token {token_path}: {exc}")


def _load_google_credentials():
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
    except Exception as exc:
        log.warning(f"Google API dependencies unavailable: {exc}")
        return None

    for token_path in _candidate_google_token_paths():
        if not token_path.exists():
            continue
        try:
            creds = Credentials.from_authorized_user_file(str(token_path), GOOGLE_DOCS_SCOPES)
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
                _persist_google_token(token_path, creds)
            if creds.valid:
                return creds
        except Exception as exc:
            log.warning(f"Google token load failed from {token_path}: {exc}")
    return None


def _direct_docs_ready():
    return any(path.exists() for path in _candidate_google_client_secret_paths()) and any(
        path.exists() for path in _candidate_google_token_paths()
    )


def _ensure_drive_folder(drive_service, folder_path):
    folder_path = str(folder_path or "").strip().strip("/")
    if not folder_path:
        return ""

    parent_id = os.environ.get("GOOGLE_DOCS_ROOT_FOLDER_ID", "").strip() or None
    for segment in [part.strip() for part in folder_path.split("/") if part.strip()]:
        safe_segment = segment.replace("'", "\\'")
        query = [
            "mimeType='application/vnd.google-apps.folder'",
            "trashed=false",
            f"name='{safe_segment}'",
        ]
        if parent_id:
            query.append(f"'{parent_id}' in parents")

        response = drive_service.files().list(
            q=" and ".join(query),
            spaces="drive",
            fields="files(id,name)",
            pageSize=10,
        ).execute()
        matches = response.get("files") or []
        if matches:
            parent_id = matches[0]["id"]
            continue

        body = {
            "name": segment,
            "mimeType": "application/vnd.google-apps.folder",
        }
        if parent_id:
            body["parents"] = [parent_id]
        created = drive_service.files().create(body=body, fields="id").execute()
        parent_id = created["id"]

    return parent_id or ""


def _post_direct_google_doc(title, content, folder=None):
    if not _direct_docs_ready():
        return {"ok": False, "error": "google_oauth_not_ready"}

    creds = _load_google_credentials()
    if not creds:
        return {"ok": False, "error": "google_oauth_missing_token"}

    try:
        from googleapiclient.discovery import build
    except Exception as exc:
        log.warning(f"Google API client unavailable: {exc}")
        return {"ok": False, "error": "google_api_client_unavailable"}

    try:
        docs_service = build("docs", "v1", credentials=creds, cache_discovery=False)
        drive_service = build("drive", "v3", credentials=creds, cache_discovery=False)

        created = docs_service.documents().create(body={"title": title}).execute()
        document_id = created["documentId"]
        text = str(content or "")
        if text:
            docs_service.documents().batchUpdate(
                documentId=document_id,
                body={"requests": [{"insertText": {"location": {"index": 1}, "text": text}}]},
            ).execute()

        folder_id = _ensure_drive_folder(drive_service, folder)
        file_meta = drive_service.files().get(fileId=document_id, fields="id,webViewLink,parents").execute()
        previous_parents = ",".join(file_meta.get("parents") or [])
        if folder_id:
            update_args = {
                "fileId": document_id,
                "addParents": folder_id,
                "fields": "id,webViewLink",
            }
            if previous_parents:
                update_args["removeParents"] = previous_parents
            file_meta = drive_service.files().update(**update_args).execute()

        doc_link = file_meta.get("webViewLink") or f"https://docs.google.com/document/d/{document_id}/edit"
        log.info(f"Google Doc created via direct API: {doc_link}")
        return {
            "ok": True,
            "link": doc_link,
            "doc_link": doc_link,
            "canvas_link": "",
            "mode": "direct",
        }
    except Exception as exc:
        log.warning(f"Direct Google Docs publish failed: {exc}")
        return {"ok": False, "error": str(exc)}


def _resolve_channel_id(channel_name, token):
    """Resolve a Slack channel name to its ID."""
    if channel_name in _channel_cache:
        return _channel_cache[channel_name]

    clean_name = channel_name.lstrip("#")
    try:
        resp = requests.get(
            "https://slack.com/api/conversations.list",
            headers={"Authorization": f"Bearer {token}"},
            params={"types": "public_channel,private_channel", "limit": 200},
            timeout=10,
        )
        data = resp.json()
        if data.get("ok"):
            for ch in data.get("channels", []):
                _channel_cache[f"#{ch['name']}"] = ch["id"]
                if ch["name"] == clean_name:
                    return ch["id"]
    except Exception as e:
        log.error(f"Channel resolve error: {e}")
    return None


# Agent commentary styles for Slack posts
AGENT_COMMENTARY = {
    "rex_blackwell": {
        "prefix": "Just wrapped up the numbers.",
        "emoji": ":cowboy_hat_face:",
        "style": "direct and short",
    },
    "piper_reeves": {
        "prefix": "Hey y'all, here's the latest.",
        "emoji": ":wave:",
        "style": "warm and personable",
    },
    "frederick_banks": {
        "prefix": "Data's in. Here are the scores.",
        "emoji": ":bar_chart:",
        "style": "numbers only",
    },
    "harrison_knox": {
        "prefix": "Champ, got an update for you.",
        "emoji": ":handshake:",
        "style": "closer energy",
    },
    "adrian_morgan": {
        "prefix": "Put together something for you.",
        "emoji": ":briefcase:",
        "style": "polished and professional",
    },
    "carlos_moreno": {
        "prefix": "Revenue update. Let's talk money.",
        "emoji": ":money_with_wings:",
        "style": "revenue-focused",
    },
    "calvin_osei": {
        "prefix": "Found a match you're going to love.",
        "emoji": ":sparkles:",
        "style": "excited connector",
    },
    "charles_dawson": {
        "prefix": "Look at this trend line.",
        "emoji": ":chart_with_upwards_trend:",
        "style": "data storyteller",
    },
    "marcus_cole": {
        "prefix": "Here's the brief.",
        "emoji": ":crown:",
        "style": "executive summary",
    },
}


def _post_to_slack(channel, summary, title, links=None, local_path=None, app="warroom", agent=None):
    """Post report BY the responsible agent, in their voice, with all 3 format links."""
    links = links or {}
    doc_link = links.get("doc_link", "")
    html_link = links.get("html_link", "")
    canvas_link = links.get("canvas_link", "")

    # Agent personality
    sig = AGENT_SIGNATURES.get(agent or "", AGENT_SIGNATURES.get("default", {}))
    commentary = AGENT_COMMENTARY.get(agent or "", {})
    agent_name = sig.get("name", "Everlight Ventures")
    agent_emoji = commentary.get("emoji", ":robot_face:")
    agent_intro = commentary.get("prefix", "Report ready.")

    # Build links row
    link_parts = []
    if html_link:
        link_parts.append(f":page_facing_up: <{html_link}|Styled Report>")
    if doc_link:
        link_parts.append(f":memo: <{doc_link}|Google Doc>")
    if canvas_link:
        link_parts.append(f":clipboard: <{canvas_link}|Canvas>")
    if local_path and not link_parts:
        link_parts.append(f"File: `{local_path}`")
    links_line = "  |  ".join(link_parts) if link_parts else ""

    message = (
        f"{agent_emoji} *{agent_name}*\n"
        f"{agent_intro}\n\n"
        f"*{title}*\n"
        f"{summary}\n"
        f"{links_line}"
    )

    # Try chat.postMessage first (richer formatting)
    token = SLACK_TOKENS.get(app, SLACK_TOKENS.get("warroom"))
    if token and channel:
        channel_id = _resolve_channel_id(channel, token)
        if channel_id:
            try:
                resp = requests.post(
                    "https://slack.com/api/chat.postMessage",
                    headers={"Authorization": f"Bearer {token}"},
                    json={
                        "channel": channel_id,
                        "text": message,
                        "unfurl_links": False,
                    },
                    timeout=10,
                )
                data = resp.json()
                if data.get("ok"):
                    log.info(f"Posted to {channel} via API")
                    return True
                else:
                    log.warning(f"chat.postMessage failed: {data.get('error')}")
            except Exception as e:
                log.warning(f"Slack API error: {e}")

    # Fallback: webhook
    if SLACK_WEBHOOK_URL:
        try:
            requests.post(SLACK_WEBHOOK_URL, json={"text": message}, timeout=10)
            log.info("Posted to Slack via webhook")
            return True
        except Exception as e:
            log.error(f"Slack webhook error: {e}")

    return False


def _save_local_fallback(title, content, folder=None):
    """
    Save report locally when both n8n and Google Docs are unavailable.
    Files saved to 09_DASHBOARD/reports/gdocs_queue/ for later upload.
    """
    queue_dir_env = os.environ.get("GDOCS_QUEUE_DIR", "").strip()
    if queue_dir_env:
        queue_dir = Path(queue_dir_env)
    else:
        bot_dir = Path(os.environ.get("CRYPTO_BOT_DIR", "")).expanduser()
        if not str(bot_dir):
            bot_dir = Path(__file__).resolve().parents[3]
        queue_dir = bot_dir / "09_DASHBOARD" / "reports" / "gdocs_queue"
    try:
        queue_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        queue_dir = Path("/tmp/gdocs_queue")
        queue_dir.mkdir(parents=True, exist_ok=True)

    safe_title = title.replace("/", "_").replace(" ", "_")[:100]
    filename = f"{_timestamp()}_{safe_title}.md"
    filepath = queue_dir / filename

    # Add metadata header
    header = (
        f"---\n"
        f"title: {title}\n"
        f"folder: {folder or 'unspecified'}\n"
        f"created: {_timestamp()}\n"
        f"status: pending_upload\n"
        f"---\n\n"
    )

    filepath.write_text(header + content)
    log.info(f"Saved locally for later upload: {filepath}")
    return str(filepath)


# --- Agent Signatures for Professional Reports ---
AGENT_SIGNATURES = {
    "rex_blackwell": {
        "name": "Rex Blackwell",
        "title": "Director of Acquisitions",
        "email": "rex.b@everlightventures.io",
        "sign_off": "Regards,",
        "style": "Direct, numbers-first, no fluff.",
    },
    "piper_reeves": {
        "name": "Piper Reeves",
        "title": "Outreach Specialist",
        "email": "piper@everlightventures.io",
        "sign_off": "Best,",
        "style": "Warm, personable, detail-oriented.",
    },
    "frederick_banks": {
        "name": "Frederick Banks",
        "title": "Lead Qualification Analyst",
        "email": "filter@everlightventures.io",
        "sign_off": "Regards,",
        "style": "Data-driven, concise, scores and metrics.",
    },
    "harrison_knox": {
        "name": "Harrison Knox",
        "title": "Deal Closer",
        "email": "hammer@everlightventures.io",
        "sign_off": "Looking forward,",
        "style": "Relentless follow-up, professional urgency.",
    },
    "adrian_morgan": {
        "name": "Adrian Morgan",
        "title": "Investment Analyst",
        "email": "ace@everlightventures.io",
        "sign_off": "Best regards,",
        "style": "Polished, investment-grade presentation.",
    },
    "carlos_moreno": {
        "name": "Carlos Moreno",
        "title": "Revenue & Commission Auditor",
        "email": "cash@everlightventures.io",
        "sign_off": "Regards,",
        "style": "Revenue-focused, audit-ready numbers.",
    },
    "calvin_osei": {
        "name": "Calvin Osei",
        "title": "Matching Specialist",
        "email": "cupid@everlightventures.io",
        "sign_off": "Best,",
        "style": "Connector energy, compatibility analysis.",
    },
    "charles_dawson": {
        "name": "Charles Dawson",
        "title": "Analytics Lead",
        "email": "chart@everlightventures.io",
        "sign_off": "Regards,",
        "style": "Data storyteller, KPI-focused.",
    },
    "marcus_cole": {
        "name": "Marcus Cole",
        "title": "Chief Operating Officer",
        "email": "marcus@everlightventures.io",
        "sign_off": "Best,",
        "style": "Executive summary, strategic oversight.",
    },
    "default": {
        "name": "Everlight Ventures",
        "title": "Automated Intelligence",
        "email": "hello@everlightventures.io",
        "sign_off": "Regards,",
        "style": "Professional, clean, branded.",
    },
}


def _wrap_professional_report(title, content, agent=None):
    """Wrap raw content into a professional branded report with agent signature.

    Adds:
    - Everlight branded header with timestamp
    - Agent introduction line
    - The actual content
    - Professional sign-off with agent signature block
    """
    ts = _timestamp()
    sig = AGENT_SIGNATURES.get(agent or "", AGENT_SIGNATURES["default"])

    header = (
        f"# {title}\n\n"
        f"**EVERLIGHT VENTURES**\n"
        f"*{ts}*\n\n"
        f"---\n\n"
    )

    # Agent intro
    if agent and agent != "default":
        header += f"*Prepared by {sig['name']}, {sig['title']}*\n\n"

    # Professional sign-off
    footer = (
        f"\n\n---\n\n"
        f"{sig['sign_off']}\n\n"
        f"**{sig['name']}**\n"
        f"{sig['title']}\n"
        f"Everlight Ventures\n"
        f"{sig['email']} | everlightventures.io\n\n"
        f"---\n"
        f"*This report was generated by the Everlight Hive Mind automation platform.*\n"
        f"*Everlight Ventures | Sacramento, CA | everlightventures.io*"
    )

    return header + content + footer


def _save_styled_html_report(title, content_md, agent=None, folder=None):
    """Generate a styled HTML report and save it to hive_reports/ on Oracle.

    Returns: {"ok": bool, "html_link": str, "html_path": str}
    """
    try:
        from report_template import render_report, safe_filename, kpi_grid, table, card
    except ImportError:
        return {"ok": False, "error": "report_template not available"}

    sig = AGENT_SIGNATURES.get(agent or "", AGENT_SIGNATURES["default"])

    # Convert markdown-ish content to HTML
    import re
    html_content = content_md

    # Convert markdown tables to HTML tables
    lines = html_content.split("\n")
    out_lines = []
    in_table = False
    table_rows = []
    headers = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if all(c.replace("-", "").strip() == "" for c in cells):
                continue  # separator row
            if not in_table:
                headers = cells
                in_table = True
            else:
                table_rows.append(cells)
        else:
            if in_table:
                # Flush table
                th = "".join(f"<th>{h}</th>" for h in headers)
                trs = "\n".join(
                    "<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>"
                    for row in table_rows
                )
                out_lines.append(f"<table><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table>")
                in_table = False
                table_rows = []
                headers = []
            # Convert markdown to HTML
            if stripped.startswith("### "):
                out_lines.append(f"<h3>{stripped[4:]}</h3>")
            elif stripped.startswith("## "):
                out_lines.append(f"<h2>{stripped[3:]}</h2>")
            elif stripped.startswith("# "):
                out_lines.append(f"<h2>{stripped[2:]}</h2>")
            elif stripped.startswith("- "):
                out_lines.append(f"<li>{stripped[2:]}</li>")
            elif stripped.startswith("**") and stripped.endswith("**"):
                out_lines.append(f"<p><strong>{stripped[2:-2]}</strong></p>")
            elif stripped:
                # Bold markers inline
                processed = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', stripped)
                out_lines.append(f"<p>{processed}</p>")
            else:
                out_lines.append("")
    # Flush any remaining table
    if in_table and headers:
        th = "".join(f"<th>{h}</th>" for h in headers)
        trs = "\n".join(
            "<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>"
            for row in table_rows
        )
        out_lines.append(f"<table><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table>")

    html_body = "\n".join(out_lines)

    html = render_report(
        title=title,
        content_html=html_body,
        agent_name=sig["name"],
        agent_title=sig["title"],
        agent_email=sig["email"],
    )

    filename = safe_filename(title)

    # Save locally
    for local_dir in [
        Path("/home/opc/hive_reports"),
        Path("/mnt/sdcard/AA_MY_DRIVE/09_DASHBOARD/reports"),
    ]:
        try:
            local_dir.mkdir(parents=True, exist_ok=True)
            (local_dir / filename).write_text(html)
        except Exception:
            pass

    # The report is served at :8504/reports/ via Django staticfiles
    html_link = f"http://129.159.38.250:8504/reports/{filename}"

    return {"ok": True, "html_link": html_link, "html_path": filename, "html": html}


def publish_report(title, content, folder=None, slack_channel=None,
                   summary=None, app="warroom", metadata=None,
                   post_to_slack=True, agent=None):
    """
    Main entry point. Creates a professional branded HTML report, saves it to
    Oracle's hive_reports/ (served at :8504/reports/), creates a Google Doc backup,
    and posts the link to Slack.

    Args:
        title: Report title (e.g. "Broker Scout Report")
        content: Full markdown content
        folder: Google Drive folder path (e.g. "01_Broker_OS/Scout_Reports")
        slack_channel: Override Slack channel (e.g. "#all-everlightventures")
        summary: 1-2 line summary for Slack (auto-generated if None)
        app: Slack app to use ("warroom" or "xlmbot")
        metadata: Extra metadata dict to pass to n8n
        agent: Agent key (e.g. "rex_blackwell") for signature block

    Returns:
        dict with keys: ok, link, doc_link, html_link, local_path, slack_posted
    """
    # Step 0: Generate styled HTML report
    html_result = _save_styled_html_report(title, content, agent=agent, folder=folder)

    # Wrap content for GDoc (markdown with agent sig)
    content = _wrap_professional_report(title, content, agent=agent)

    # Generate doc title
    doc_title = _make_doc_title(title, folder)

    # Auto-generate summary if not provided
    if not summary:
        # Take first 2 non-empty, non-header lines
        lines = [l.strip() for l in content.split("\n") if l.strip() and not l.startswith("#")]
        summary = " ".join(lines[:2])[:200] + ("..." if len(lines) > 2 else "")

    # Determine Slack channel
    if not slack_channel and folder:
        category = folder.split("/")[0] if "/" in folder else folder
        slack_channel = FOLDER_CHANNEL_MAP.get(category, "#all-everlightventures")
    elif not slack_channel:
        slack_channel = "#all-everlightventures"

    result = {
        "ok": False,
        "link": None,
        "doc_link": None,
        "html_link": None,
        "canvas_link": None,
        "local_path": None,
        "slack_posted": False,
    }

    # Step 0 result: styled HTML report
    if html_result.get("ok"):
        result["ok"] = True
        result["html_link"] = html_result.get("html_link", "")
        result["link"] = result["html_link"]  # primary link is the styled HTML

    # Step 1: Create Google Doc via n8n or direct API (backup/searchable copy)
    n8n_result = {"ok": False, "error": "n8n_disabled"}
    if _n8n_enabled():
        n8n_result = _post_to_n8n(doc_title, content, folder, metadata)

    if n8n_result["ok"] and n8n_result.get("doc_link"):
        result["ok"] = True
        result["doc_link"] = n8n_result.get("doc_link")
        result["canvas_link"] = n8n_result.get("canvas_link") or None
        if not result["link"]:
            result["link"] = result["doc_link"]
    else:
        direct_result = _post_direct_google_doc(doc_title, content, folder)
        if direct_result.get("ok") and direct_result.get("doc_link"):
            result["ok"] = True
            result["doc_link"] = direct_result.get("doc_link")
            if not result["link"]:
                result["link"] = result["doc_link"]
        elif not result.get("ok"):
            # Both HTML and GDoc failed - save locally
            local_path = _save_local_fallback(title, content, folder)
            result["local_path"] = local_path
            log.warning(f"All report methods failed, saved locally: {local_path}")

    # Step 2: Post all 3 links to Slack BY the responsible agent in their voice
    if post_to_slack:
        slack_ok = _post_to_slack(
            slack_channel,
            summary,
            title,
            links={
                "html_link": result.get("html_link") or "",
                "doc_link": result.get("doc_link") or "",
                "canvas_link": result.get("canvas_link") or "",
            },
            local_path=result.get("local_path"),
            app=app,
            agent=agent,
        )
        result["slack_posted"] = slack_ok

    return result


def publish_file(file_path, folder=None, slack_channel=None, app="warroom"):
    """Convenience: read a file and publish it as a Google Doc."""
    path = Path(file_path)
    if not path.exists():
        log.error(f"File not found: {file_path}")
        return {"ok": False, "error": "file_not_found"}

    content = path.read_text()
    title = path.stem.replace("_", " ").title()

    return publish_report(
        title=title,
        content=content,
        folder=folder,
        slack_channel=slack_channel,
        app=app,
    )


def publish_dict(title, data, folder=None, slack_channel=None,
                 summary=None, app="warroom"):
    """
    Convenience: convert a dict/list to a formatted markdown table
    and publish as a Google Doc.
    """
    if isinstance(data, list) and data and isinstance(data[0], dict):
        # List of dicts -> markdown table
        headers = list(data[0].keys())
        lines = [
            f"# {title}",
            f"*Generated: {_timestamp()}*",
            "",
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join(["---"] * len(headers)) + " |",
        ]
        for row in data:
            vals = [str(row.get(h, "")) for h in headers]
            lines.append("| " + " | ".join(vals) + " |")
        content = "\n".join(lines)
    elif isinstance(data, dict):
        # Single dict -> key-value list
        lines = [
            f"# {title}",
            f"*Generated: {_timestamp()}*",
            "",
        ]
        for k, v in data.items():
            lines.append(f"- **{k}**: {v}")
        content = "\n".join(lines)
    else:
        content = f"# {title}\n\n{json.dumps(data, indent=2, default=str)}"

    return publish_report(
        title=title,
        content=content,
        folder=folder,
        slack_channel=slack_channel,
        summary=summary,
        app=app,
    )


# --- CLI ---

if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    parser = argparse.ArgumentParser(description="Publish markdown file as Google Doc + Slack link")
    parser.add_argument("file", help="Path to markdown file")
    parser.add_argument("--folder", help="Google Drive folder path (e.g. 01_Broker_OS/Scout_Reports)")
    parser.add_argument("--channel", help="Slack channel (e.g. #all-everlightventures)")
    parser.add_argument("--app", default="warroom", help="Slack app (warroom or xlmbot)")
    parser.add_argument("--summary", help="Custom summary for Slack message")
    args = parser.parse_args()

    result = publish_file(
        args.file,
        folder=args.folder,
        slack_channel=args.channel,
        app=args.app,
    )

    if result["ok"]:
        print(f"Published: {result['link']}")
    elif result.get("local_path"):
        print(f"Saved locally (n8n unavailable): {result['local_path']}")
    else:
        print("Failed to publish report")

    if result.get("slack_posted"):
        print("Slack notification sent")
    else:
        print("Slack notification failed")
