"""
Google Docs Bridge -- publish reports in the standard 3 formats.

Every report should exist as:
  1. Styled HTML served from :8504/reports/
  2. Google Doc in Drive
  3. Slack post linking to the other formats

Two Google Docs modes:
  1. Direct mode (preferred): Uses Google Docs/Drive API directly
  2. n8n mode (fallback): POST to the n8n webhook which creates the Google Doc

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
    # Local (Oracle) + phone-reachable (public IP through the n8n port) + DNS name if configured
    defaults = [
        "http://127.0.0.1:5678/webhook/SU0qTaKHBX1r3oLX/r/hive-log-to-gdoc",
        "http://localhost:5678/webhook/SU0qTaKHBX1r3oLX/r/hive-log-to-gdoc",
        "http://129.159.38.250:5678/webhook/SU0qTaKHBX1r3oLX/r/hive-log-to-gdoc",
        "https://n8n.everlightventures.io/webhook/SU0qTaKHBX1r3oLX/r/hive-log-to-gdoc",
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
        str(Path("/home/opc/secrets/google_client_secret.json")),
        str(Path("/home/opc/xlm-bot/secrets/google_client_secret.json")),
        str(Path("/mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/xlm_bot/secrets/google_client_secret.json")),
        "/mnt/sdcard/AA_MY_DRIVE/08_BACKUPS/Credentials_Plaintext_Backup/client_secret_864189495801-pssn6fg438ahieth9vqih41a188smghu.apps.googleusercontent.com.json",
    ]
    return [Path(p).expanduser() for p in paths if p]


def _candidate_google_token_paths():
    bot_dir = _default_bot_dir()
    paths = [
        os.environ.get("GOOGLE_DOCS_TOKEN_FILE", "").strip(),
        str(bot_dir / "secrets" / "google_docs_token.json"),
        str(Path("/home/opc/secrets/google_docs_token.json")),
        str(Path("/home/opc/xlm-bot/secrets/google_docs_token.json")),
        str(Path("/mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/xlm_bot/secrets/google_docs_token.json")),
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


def _load_authorized_user_info():
    for token_path in _candidate_google_token_paths():
        if not token_path.exists():
            continue
        try:
            data = json.loads(token_path.read_text(encoding="utf-8"))
        except Exception as exc:
            log.warning(f"Google token load failed from {token_path}: {exc}")
            continue
        if data.get("refresh_token") and data.get("client_id") and data.get("client_secret"):
            return data
    return None


def _refresh_google_access_token(auth_info):
    token_uri = auth_info.get("token_uri") or "https://oauth2.googleapis.com/token"
    resp = requests.post(
        token_uri,
        data={
            "client_id": auth_info["client_id"],
            "client_secret": auth_info["client_secret"],
            "refresh_token": auth_info["refresh_token"],
            "grant_type": "refresh_token",
        },
        timeout=30,
    )
    resp.raise_for_status()
    payload = resp.json()
    access_token = payload.get("access_token", "").strip()
    if not access_token:
        raise RuntimeError("google_oauth_missing_access_token")
    return access_token


def _google_api_request(method, url, access_token, *, params=None, json_body=None):
    resp = requests.request(
        method,
        url,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        params=params,
        json=json_body,
        timeout=30,
    )
    resp.raise_for_status()
    if not resp.text.strip():
        return {}
    return resp.json()


def _ensure_drive_folder(access_token, folder_path):
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

        response = _google_api_request(
            "GET",
            "https://www.googleapis.com/drive/v3/files",
            access_token,
            params={
                "q": " and ".join(query),
                "spaces": "drive",
                "fields": "files(id,name)",
                "pageSize": 10,
            },
        )
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
        created = _google_api_request(
            "POST",
            "https://www.googleapis.com/drive/v3/files",
            access_token,
            params={"fields": "id"},
            json_body=body,
        )
        parent_id = created["id"]

    return parent_id or ""


def _post_direct_google_doc(title, content, folder=None):
    if not _direct_docs_ready():
        return {"ok": False, "error": "google_oauth_not_ready"}

    auth_info = _load_authorized_user_info()
    if not auth_info:
        return {"ok": False, "error": "google_oauth_missing_token"}

    try:
        access_token = _refresh_google_access_token(auth_info)
        created = _google_api_request(
            "POST",
            "https://docs.googleapis.com/v1/documents",
            access_token,
            json_body={"title": title},
        )
        document_id = created["documentId"]
        text = str(content or "")
        if text:
            _google_api_request(
                "POST",
                f"https://docs.googleapis.com/v1/documents/{document_id}:batchUpdate",
                access_token,
                json_body={"requests": [{"insertText": {"location": {"index": 1}, "text": text}}]},
            )

        folder_id = _ensure_drive_folder(access_token, folder)
        file_meta = _google_api_request(
            "GET",
            f"https://www.googleapis.com/drive/v3/files/{document_id}",
            access_token,
            params={"fields": "id,webViewLink,parents"},
        )
        previous_parents = ",".join(file_meta.get("parents") or [])
        if folder_id:
            params = {"addParents": folder_id, "fields": "id,webViewLink"}
            if previous_parents:
                params["removeParents"] = previous_parents
            file_meta = _google_api_request(
                "PATCH",
                f"https://www.googleapis.com/drive/v3/files/{document_id}",
                access_token,
                params=params,
            )

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


# Agent commentary styles for Slack posts.
AGENT_COMMENTARY = {
    "rex_blackwell": {"prefix": "Just wrapped up the numbers.", "emoji": ":cowboy_hat_face:"},
    "piper_reeves": {"prefix": "Hey y'all, here's the latest.", "emoji": ":wave:"},
    "frederick_banks": {"prefix": "Data's in. Here are the scores.", "emoji": ":bar_chart:"},
    "harrison_knox": {"prefix": "Champ, got an update for you.", "emoji": ":handshake:"},
    "adrian_morgan": {"prefix": "Put together something for you.", "emoji": ":briefcase:"},
    "carlos_moreno": {"prefix": "Revenue update. Let's talk money.", "emoji": ":money_with_wings:"},
    "calvin_osei": {"prefix": "Found a match you're going to love.", "emoji": ":sparkles:"},
    "charles_dawson": {"prefix": "Look at this trend line.", "emoji": ":chart_with_upwards_trend:"},
    "marcus_cole": {"prefix": "Here's the brief.", "emoji": ":crown:"},
}


def _post_to_slack(channel, summary, title, links=None, local_path=None, app="warroom", agent=None):
    """Post a summary + report links to Slack."""
    links = links or {}
    doc_link = links.get("doc_link", "")
    html_link = links.get("html_link", "")
    canvas_link = links.get("canvas_link", "")

    sig = AGENT_SIGNATURES.get(agent or "", AGENT_SIGNATURES["default"])
    commentary = AGENT_COMMENTARY.get(agent or "", {})
    agent_name = sig.get("name", "Everlight Ventures")
    agent_emoji = commentary.get("emoji", ":robot_face:")
    agent_intro = commentary.get("prefix", "Report ready.")

    link_parts = []
    if html_link:
        link_parts.append(f":page_facing_up: <{html_link}|Styled Report>")
    if doc_link:
        link_parts.append(f":memo: <{doc_link}|Google Doc>")
    if canvas_link:
        link_parts.append(f":clipboard: <{canvas_link}|Canvas>")
    if local_path and not link_parts:
        link_parts.append(f"File: `{local_path}`")
    links_line = "  |  ".join(link_parts) if link_parts else "(report link unavailable)"

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


def _save_styled_html_report(title, content_md, agent=None):
    """Generate and save the styled HTML report served by Django at :8504/reports/."""
    try:
        from report_template import render_report, safe_filename
    except ImportError:
        return {"ok": False, "error": "report_template not available"}

    sig = AGENT_SIGNATURES.get(agent or "", AGENT_SIGNATURES["default"])

    import re

    lines = str(content_md or "").split("\n")
    out_lines = []
    in_list = False
    in_table = False
    table_rows = []
    headers = []

    def close_list():
        nonlocal in_list
        if in_list:
            out_lines.append("</ul>")
            in_list = False

    def close_table():
        nonlocal in_table, table_rows, headers
        if not in_table or not headers:
            return
        th = "".join(f"<th>{h}</th>" for h in headers)
        trs = "\n".join(
            "<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>"
            for row in table_rows
        )
        out_lines.append(f"<table><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table>")
        in_table = False
        table_rows = []
        headers = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            close_list()
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if all(c.replace("-", "").strip() == "" for c in cells):
                continue
            if not in_table:
                headers = cells
                in_table = True
            else:
                table_rows.append(cells)
            continue

        close_table()

        if stripped.startswith("- "):
            if not in_list:
                out_lines.append("<ul>")
                in_list = True
            processed = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", stripped[2:])
            out_lines.append(f"<li>{processed}</li>")
            continue

        close_list()

        if stripped.startswith("### "):
            out_lines.append(f"<h3>{stripped[4:]}</h3>")
        elif stripped.startswith("## "):
            out_lines.append(f"<h2>{stripped[3:]}</h2>")
        elif stripped.startswith("# "):
            out_lines.append(f"<h2>{stripped[2:]}</h2>")
        elif stripped:
            processed = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", stripped)
            out_lines.append(f"<p>{processed}</p>")
        else:
            out_lines.append("")

    close_table()
    close_list()

    html = render_report(
        title=title,
        content_html="\n".join(out_lines),
        agent_name=sig["name"],
        agent_title=sig["title"],
        agent_email=sig["email"],
    )

    filename = safe_filename(title)
    html_dirs = [
        Path(os.environ.get("HIVE_REPORTS_DIR", "")).expanduser() if os.environ.get("HIVE_REPORTS_DIR") else None,
        Path("/home/opc/hive_reports"),
        Path("/mnt/sdcard/AA_MY_DRIVE/09_DASHBOARD/reports"),
    ]
    saved = False
    for html_dir in html_dirs:
        if not html_dir:
            continue
        try:
            html_dir.mkdir(parents=True, exist_ok=True)
            (html_dir / filename).write_text(html, encoding="utf-8")
            saved = True
        except Exception as exc:
            log.warning(f"Failed to save HTML report to {html_dir}: {exc}")

    if not saved:
        return {"ok": False, "error": "html_save_failed"}

    report_base = os.environ.get("REPORT_URL_BASE", "http://129.159.38.250:8504/reports/").rstrip("/") + "/"
    return {"ok": True, "html_link": f"{report_base}{filename}", "html_path": filename, "html": html}


def publish_report(title, content, folder=None, slack_channel=None,
                   summary=None, app="warroom", metadata=None,
                   post_to_slack=True, agent=None):
    """
    Main entry point. Creates a professional branded HTML report, creates a
    Google Doc backup, and posts both links to Slack.

    Args:
        title: Report title (e.g. "Broker Scout Report")
        content: Full markdown content for the Google Doc
        folder: Google Drive folder path (e.g. "01_Broker_OS/Scout_Reports")
        slack_channel: Override Slack channel (e.g. "#all-everlightventures")
        summary: 1-2 line summary for Slack (auto-generated if None)
        app: Slack app to use ("warroom" or "xlmbot")
        metadata: Extra metadata dict to pass to n8n
        agent: Agent key (e.g. "rex_blackwell") for signature block

    Returns:
        dict with keys: ok, link, doc_link, html_link, canvas_link, local_path, slack_posted
    """
    html_result = _save_styled_html_report(title, content, agent=agent)

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

    if html_result.get("ok"):
        result["ok"] = True
        result["html_link"] = html_result.get("html_link")
        result["link"] = result["html_link"]

    direct_result = _post_direct_google_doc(doc_title, content, folder)
    if direct_result.get("ok") and direct_result.get("doc_link"):
        result["ok"] = True
        result["doc_link"] = direct_result.get("doc_link")
        if not result["link"]:
            result["link"] = result["doc_link"]
    else:
        n8n_result = {"ok": False, "error": "n8n_disabled"}
        if _n8n_enabled():
            n8n_result = _post_to_n8n(doc_title, content, folder, metadata)
        if n8n_result["ok"] and n8n_result.get("doc_link"):
            result["ok"] = True
            result["doc_link"] = n8n_result.get("doc_link")
            result["canvas_link"] = n8n_result.get("canvas_link") or None
            if not result["link"]:
                result["link"] = result["doc_link"]
        elif not result.get("ok"):
            local_path = _save_local_fallback(title, content, folder)
            result["local_path"] = local_path
            log.warning(f"All report methods failed, saved locally: {local_path}")

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
