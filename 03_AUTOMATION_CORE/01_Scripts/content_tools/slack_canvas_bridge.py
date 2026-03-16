"""Slack output bridge -- routes all bot/agent reports to Google Docs + Slack link.

CANVAS CREATION DISABLED. All output now goes to Google Docs via gdocs_bridge,
with the doc link posted to the appropriate Slack channel as a plain message.

Drop-in replacement: create_native_canvas() and create_canvas_from_file() still
work with the same signature, but create Google Docs instead of Slack Canvases.

Used by: hive_cmd.py, war_room_watcher.py, xlm_bot alerts
"""
import os
import sys
import requests
import json
import time

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

# Google Docs folder mapping per app
APP_FOLDER_MAP = {
    "xlmbot": "02_XLM_Bot/Trade_Reports",
    "warroom": "00_Command_Center/War_Room",
}

# Import gdocs_bridge from same directory
_gdocs_available = False
try:
    from gdocs_bridge import publish_report
    _gdocs_available = True
except ImportError:
    try:
        _bridge_dir = os.path.dirname(os.path.abspath(__file__))
        if _bridge_dir not in sys.path:
            sys.path.insert(0, _bridge_dir)
        from gdocs_bridge import publish_report
        _gdocs_available = True
    except ImportError:
        _gdocs_available = False


def _get_bot_channel_ids(token):
    """Return list of channel IDs the bot is a member of."""
    try:
        ch_resp = requests.get(
            "https://slack.com/api/conversations.list",
            headers={"Authorization": f"Bearer {token}"},
            params={"types": "public_channel,private_channel", "limit": 200},
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


def create_native_canvas(content, title, app_name="warroom"):
    """Create a Google Doc with the content and post the link to Slack.

    This function used to create Slack Canvases. Now it routes to Google Docs
    via gdocs_bridge and posts the doc link to the appropriate Slack channel.

    Same signature as before for backward compatibility.
    """
    config = APP_CONFIG.get(app_name)
    if not config:
        print(f"  [bridge] Invalid app name {app_name}")
        return None

    token = config["token"]
    webhook_url = config["webhook"]
    folder = APP_FOLDER_MAP.get(app_name, "00_Command_Center/System_Status")

    print(f"  {app_name} publishing to Google Docs: {title}...")

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
                post_to_slack=True,  # gdocs_bridge handles the Slack post
            )
            if result.get("ok") and result.get("link"):
                doc_url = result["link"]
                print(f"  [bridge] Google Doc created: {doc_url}")
                return doc_url
            elif result.get("local_path"):
                print(f"  [bridge] Saved locally: {result['local_path']}")
                excerpt = "\n".join([line for line in content.splitlines() if line.strip()][:18])[:2600]
                msg = (
                    f"*{app_name.upper()} Report: {title}*\n"
                    f"{summary}\n"
                    f"Google Doc unavailable right now. Posting the report excerpt here instead.\n"
                    f"```{excerpt}```\n"
                    f"Saved locally: `{result['local_path']}`"
                )
                _post_message_to_channels(token, msg)
                return None
        except Exception as e:
            print(f"  [bridge] gdocs_bridge error: {e}")

    # Fallback: post content as plain Slack message (no Canvas, no Doc)
    print(f"  [bridge] Google Docs unavailable, posting as plain Slack message")
    msg = (
        f"*{app_name.upper()} Report: {title}*\n"
        f"```\n{content[:2800]}\n```"
    )
    posted = _post_message_to_channels(token, msg)
    if posted == 0:
        # Last resort: webhook
        try:
            requests.post(webhook_url, json={"text": msg}, timeout=10)
        except Exception:
            pass
    return None


def create_canvas_from_file(file_path, app_name="warroom"):
    """Convenience: read a file and publish it as a Google Doc."""
    if not os.path.exists(file_path):
        print(f"  [bridge] File not found: {file_path}")
        return None
    with open(file_path, 'r') as f:
        content = f.read()
    filename = os.path.basename(file_path)
    title = filename.replace("_", " ").replace(".md", "").title()
    return create_native_canvas(content, title, app_name)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 slack_canvas_bridge.py <path_to_file> <app_name>")
    else:
        create_canvas_from_file(sys.argv[1], sys.argv[2])
