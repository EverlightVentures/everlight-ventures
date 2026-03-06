import os
import sys
import requests
import json
import time

# --- MULTI-APP TOKEN CONFIGURATION ---
APP_CONFIG = {
    "xlmbot": {
        "token": "xoxb-8645963765681-10542494223845-M2gIADgkLB2HYJN4F8lGpbuI",
        "webhook": "https://hooks.slack.com/services/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",
        "team_id": "T08JZUBNHL1"
    },
    "warroom": {
        "token": "xoxb-8645963765681-10594020158069-eJRt13YP8qedI6DnQwupuFfy",
        "webhook": "https://hooks.slack.com/services/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",
        "team_id": "T08JZUBNHL1"
    }
}


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
            print(f"  [canvas] conversations.list failed: {ch_data.get('error')}")
            return []
        return [c["id"] for c in (ch_data.get("channels") or []) if c.get("is_member")]
    except Exception as e:
        print(f"  [canvas] channel list error: {e}")
        return []


def _set_canvas_access(token, canvas_id, channel_ids=None):
    """Grant read access to specified channels (or auto-detect bot channels)."""
    try:
        if channel_ids is None:
            channel_ids = _get_bot_channel_ids(token)
        if not channel_ids:
            print("  [canvas] no channels for access set, skipping")
            return
        access_resp = requests.post(
            "https://slack.com/api/canvases.access.set",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "canvas_id": canvas_id,
                "access_level": "read",
                "channel_ids": channel_ids,
            },
            timeout=10,
        )
        acc_data = access_resp.json()
        if acc_data.get("ok"):
            print(f"  [canvas] Access granted to {len(channel_ids)} channel(s)")
        else:
            print(f"  [canvas] access.set failed: {acc_data.get('error')}")
    except Exception as e:
        print(f"  [canvas] access set error: {e}")


def create_native_canvas(content, title, app_name="warroom"):
    """
    Create a Slack Canvas and share it with proper permissions.

    Flow (order matters for permissions):
      1. canvases.create  - create the canvas document
      2. chat.postMessage - share link in channel (establishes sharing context)
      3. canvases.access.set - grant read access (works now because canvas is shared)
    """
    config = APP_CONFIG.get(app_name)
    if not config:
        print(f"Error: Invalid app name {app_name}")
        return

    token = config["token"]
    webhook_url = config["webhook"]
    team_id = config["team_id"]

    print(f"  {app_name} generating Native Canvas: {title}...")

    try:
        # Step 1: Create the Canvas
        response = requests.post(
            "https://slack.com/api/canvases.create",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "title": title,
                "document_content": {"type": "markdown", "markdown": content}
            },
            timeout=30
        )

        result = response.json()
        if not result.get("ok"):
            error = result.get('error')
            print(f"  Canvas API Error ({app_name}): {error}")
            # Fallback to webhook with plain text
            requests.post(
                webhook_url,
                json={
                    "text": f"*{app_name.upper()} FALLBACK DUMP: {title}*\n"
                            f"(Canvas creation failed: {error})\n"
                            f"```markdown\n{content[:2800]}\n```"
                }
            )
            return None

        canvas_id = result.get("canvas_id")

        # Build links
        deep_link = f"slack://file?team={team_id}&id={canvas_id}"
        web_link = f"https://app.slack.com/docs/{team_id}/{canvas_id}"
        msg_text = (
            f"*{app_name.upper()} Report: {title}*\n"
            f"<{deep_link}|Open in Slack App> | <{web_link}|Open in Browser>"
        )

        # Step 2: Post via chat.postMessage FIRST (creates sharing context)
        # This MUST happen before canvases.access.set or access grant silently fails
        channel_ids = _get_bot_channel_ids(token)
        posted_channels = []
        for ch_id in channel_ids:
            post_resp = requests.post(
                "https://slack.com/api/chat.postMessage",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "channel": ch_id,
                    "text": msg_text,
                    "unfurl_links": False,
                },
                timeout=10,
            )
            post_data = post_resp.json()
            if post_data.get("ok"):
                posted_channels.append(ch_id)
            else:
                err = post_data.get('error')
                print(f"  [canvas] postMessage to {ch_id} failed: {err}")

        if not posted_channels:
            # Fallback: use webhook if chat.postMessage fails for all channels
            # (e.g. bot lacks chat:write scope)
            print("  [canvas] chat.postMessage failed everywhere, falling back to webhook")
            requests.post(webhook_url, json={"text": msg_text})

        # Step 3: NOW grant read access (canvas has been shared, so this should succeed)
        if posted_channels:
            _set_canvas_access(token, canvas_id, posted_channels)

        print(f"  Canvas {canvas_id} created and shared to {len(posted_channels)} channel(s).")
        return deep_link

    except Exception as e:
        print(f"Failed to connect to Slack API: {e}")
        return None


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 slack_canvas_bridge.py <path_to_file> <app_name>")
    else:
        file_path, app = sys.argv[1], sys.argv[2]
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                create_native_canvas(f.read(), os.path.basename(file_path), app)
