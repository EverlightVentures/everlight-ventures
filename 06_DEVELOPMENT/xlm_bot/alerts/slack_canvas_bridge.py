"""Slack output bridge -- routes all bot reports to Google Docs + Slack link.

CANVAS CREATION DISABLED. All output now goes to Google Docs via gdocs_bridge,
with the doc link posted to the appropriate Slack channel.

Drop-in replacement: create_native_canvas() still works with same signature,
but creates a Google Doc instead of a Slack Canvas.
"""
import os
import sys
import json
import time
import requests
from pathlib import Path

# --- MULTI-APP TOKEN CONFIGURATION ---
APP_CONFIG = {
    "xlmbot": {
        "token": os.environ.get("SLACK_BOT_TOKEN", ""),
        "webhook": os.environ.get("SLACK_WEBHOOK_URL", ""),
        "team_id": "T08JZUBNHL1"
    },
    "warroom": {
        "token": os.environ.get("SLACK_WARROOM_TOKEN", ""),
        "webhook": os.environ.get("SLACK_WEBHOOK_WARROOM", ""),
        "team_id": "T08JZUBNHL1"
    }
}

# Google Docs folder mapping per app/channel
APP_FOLDER_MAP = {
    "xlmbot": "02_XLM_Bot/Trade_Reports",
    "warroom": "00_Command_Center/War_Room",
}

# Resolve path to gdocs_bridge.
# Priority:
# 1) explicit env override,
# 2) vendored copy in this repo (server-safe),
# 3) legacy phone/Termux path.
_HERE = Path(__file__).resolve()
_CANDIDATES = [
    os.environ.get("GDOCS_BRIDGE_DIR", "").strip(),
    str(_HERE.parent.parent),
    str(_HERE.parent.parent / "vendor"),
    "/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/content_tools",
]
for _p in _CANDIDATES:
    if _p and Path(_p).is_dir() and _p not in sys.path:
        sys.path.insert(0, _p)

_gdocs_available = False
try:
    from gdocs_bridge import publish_report
    _gdocs_available = True
except ImportError:
    _gdocs_available = False

try:
    from report_history import record_report
except ImportError:
    record_report = None


def _get_bot_channel_ids(token):
    """Return list of channel IDs the bot is a member of."""
    try:
        ch_resp = requests.get(
            "https://slack.com/api/conversations.list",
            headers={"Authorization": f"Bearer {token}"},
            params={"types": "public_channel,private_channel", "limit": 100},
            timeout=10,
        )
        ch_data = ch_resp.json()
        if not ch_data.get("ok"):
            print(f"  [bridge] conversations.list failed: {ch_data.get('error')}")
            return []
        return [c["id"] for c in (ch_data.get("channels") or []) if c.get("is_member")]
    except Exception as e:
        print(f"  [bridge] channel list error: {e}")
        return []


def _post_message_to_channels(token, text, channel_ids=None):
    """Post a plain text message to all bot channels."""
    if channel_ids is None:
        channel_ids = _get_bot_channel_ids(token)
    posted = 0
    for ch_id in channel_ids:
        try:
            resp = requests.post(
                "https://slack.com/api/chat.postMessage",
                headers={"Authorization": f"Bearer {token}"},
                json={"channel": ch_id, "text": text, "unfurl_links": False},
                timeout=10,
            )
            if resp.json().get("ok"):
                posted += 1
        except Exception:
            pass
    return posted


def _post_message(token, webhook_url, message):
    posted = _post_message_to_channels(token, message)
    if posted == 0:
        try:
            requests.post(webhook_url, json={"text": message}, timeout=10)
        except Exception:
            pass
    return posted


def _safe_filename(title: str) -> str:
    name = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in str(title or "report"))
    return (name.strip("_") or "report")[:96] + ".md"


def _upload_markdown_to_channels(token, title, content, channel_ids=None):
    """Upload a markdown file to Slack channels and return the first permalink."""
    if not str(token or "").strip():
        return {"uploaded": 0, "permalink": None}
    if channel_ids is None:
        channel_ids = _get_bot_channel_ids(token)
    first_link = None
    uploaded = 0
    filename = _safe_filename(title)
    payload = {
        "filename": filename,
        "title": title,
        "filetype": "markdown",
        "content": str(content or ""),
    }
    for ch_id in channel_ids:
        try:
            resp = requests.post(
                "https://slack.com/api/files.upload",
                headers={"Authorization": f"Bearer {token}"},
                data={**payload, "channels": ch_id},
                timeout=20,
            )
            data = resp.json()
            if data.get("ok"):
                uploaded += 1
                if not first_link:
                    first_link = ((data.get("file") or {}).get("permalink")) or ""
            elif data.get("error") == "invalid_auth":
                break
        except Exception:
            pass
    return {"uploaded": uploaded, "permalink": first_link}


def create_native_canvas(content, title, app_name="warroom", metadata=None):
    """Create a Google Doc with the content and post the link to Slack.

    This function used to create Slack Canvases. Now it routes to Google Docs
    via gdocs_bridge and posts the doc link to the appropriate Slack channel.

    Same signature as before for backward compatibility.
    """
    config = APP_CONFIG.get(app_name)
    if not config:
        print(f"  [bridge] Invalid app name {app_name}")
        return

    token = config["token"]
    webhook_url = config["webhook"]
    folder = APP_FOLDER_MAP.get(app_name, "00_Command_Center/System_Status")

    print(f"  {app_name} publishing to Google Docs: {title}...")

    doc_url = None
    history_entry = None

    # Primary path: Google Docs via gdocs_bridge
    if _gdocs_available:
        try:
            # Extract a short summary (first 2 non-empty lines)
            lines = [l.strip() for l in content.split("\n") if l.strip() and not l.startswith("#")]
            summary = " ".join(lines[:2])[:200]

            result = publish_report(
                title=title,
                content=content,
                folder=folder,
                app=app_name,
                summary=summary,
                post_to_slack=False,
            )
            if record_report:
                history_entry = record_report(
                    title=title,
                    content=content,
                    summary=summary,
                    app=app_name,
                    folder=folder,
                    doc_link=str(result.get("link") or ""),
                    local_path=str(result.get("local_path") or ""),
                    metadata=metadata or {},
                )
            if result.get("ok") and result.get("link"):
                doc_url = result["link"]
                message = (
                    f"*{app_name.upper()} Report: {title}*\n"
                    f"{summary}\n"
                    f"<{doc_url}|Open Google Doc>"
                )
                if history_entry and history_entry.get("history_link"):
                    message += f"\n<{history_entry['history_link']}|Open Report History>"
                elif history_entry:
                    message += f"\nReport ID: `{history_entry['report_id']}`"
                _post_message(token, webhook_url, message)
                print(f"  [bridge] Google Doc created: {doc_url}")
                return doc_url
            elif result.get("local_path"):
                print(f"  [bridge] Saved locally: {result['local_path']}")
                upload_result = _upload_markdown_to_channels(token, title, content)
                if upload_result.get("uploaded"):
                    msg = (
                        f"*{app_name.upper()} Report: {title}*\n"
                        f"{summary}\n"
                        f"External doc publishing is unavailable right now. Uploaded the markdown report to Slack instead.\n"
                    )
                    if history_entry and history_entry.get("history_link"):
                        msg += f"<{history_entry['history_link']}|Open Report Page>\n"
                    if upload_result.get("permalink"):
                        msg += f"<{upload_result['permalink']}|Open Markdown Report>\n"
                    elif history_entry:
                        msg += f"Report ID: `{history_entry['report_id']}`\n"
                    msg += f"Saved locally: `{result['local_path']}`"
                    _post_message(token, webhook_url, msg)
                else:
                    excerpt = "\n".join([line for line in content.splitlines() if line.strip()][:18])[:2600]
                    msg = (
                        f"*{app_name.upper()} Report: {title}*\n"
                        f"{summary}\n"
                        f"External doc publishing is unavailable right now. Posting the report excerpt here instead.\n"
                    )
                    if history_entry and history_entry.get("history_link"):
                        msg += f"<{history_entry['history_link']}|Open Report Page>\n"
                    elif history_entry:
                        msg += f"Report ID: `{history_entry['report_id']}`\n"
                    msg += (
                        f"```{excerpt}```\n"
                        f"Saved locally: `{result['local_path']}`"
                    )
                    _post_message(token, webhook_url, msg)
                return None
        except Exception as e:
            print(f"  [bridge] gdocs_bridge error: {e}")

    # Fallback: post content as plain Slack message (no Canvas, no Doc)
    print(f"  [bridge] Google Docs unavailable, posting as plain Slack message")
    summary = " ".join([l.strip() for l in content.splitlines() if l.strip()][:2])[:200]
    if record_report:
        history_entry = record_report(
            title=title,
            content=content,
            summary=summary,
            app=app_name,
            folder=folder,
            metadata=metadata or {},
        )
    msg = (
        f"*{app_name.upper()} Report: {title}*\n"
        f"{summary}\n"
    )
    if history_entry and history_entry.get("history_link"):
        msg += f"<{history_entry['history_link']}|Open Report History>\n"
    elif history_entry:
        msg += f"Report ID: `{history_entry['report_id']}`\n"
    msg += f"```\n{content[:2800]}\n```"
    _post_message(token, webhook_url, msg)
    return None


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 slack_canvas_bridge.py <path_to_file> <app_name>")
    else:
        file_path, app = sys.argv[1], sys.argv[2]
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                create_native_canvas(f.read(), os.path.basename(file_path), app)
