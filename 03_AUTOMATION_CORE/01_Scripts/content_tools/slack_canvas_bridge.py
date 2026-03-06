"""
Slack Canvas Bridge - Canonical implementation.

Creates Slack Canvases with proper permission flow:
  1. canvases.create  - create the document
  2. chat.postMessage - share link in channel (establishes sharing context)
  3. canvases.access.set - grant read access (works because canvas is shared)

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
    """Return list of channel IDs the bot is a member of (public, private, and DMs)."""
    ids = []
    try:
        # Include im/mpim so DM channels are discoverable for access grants
        ch_resp = requests.get(
            "https://slack.com/api/conversations.list",
            headers={"Authorization": f"Bearer {token}"},
            params={"types": "public_channel,private_channel,im,mpim", "limit": 200},
            timeout=10,
        )
        ch_data = ch_resp.json()
        if not ch_data.get("ok"):
            print(f"  [canvas] conversations.list failed: {ch_data.get('error')}")
        else:
            ids = [c["id"] for c in (ch_data.get("channels") or []) if c.get("is_member")]
    except Exception as e:
        print(f"  [canvas] channel list error: {e}")
    return ids


def _set_canvas_access(token, canvas_id, channel_ids=None):
    """Grant read access to canvas. Tries workspace-level first, then channel-level."""
    # Step A: workspace-level grant (no channel_ids = accessible to all workspace members)
    try:
        ws_resp = requests.post(
            "https://slack.com/api/canvases.access.set",
            headers={"Authorization": f"Bearer {token}"},
            json={"canvas_id": canvas_id, "access_level": "read"},
            timeout=10,
        )
        ws_data = ws_resp.json()
        if ws_data.get("ok"):
            print("  [canvas] Workspace-level read access granted.")
        else:
            err = ws_data.get('error', 'unknown')
            print(f"  [canvas] workspace access.set failed: {err} -- falling back to channel-level")
            if err in ('missing_scope', 'not_allowed_token_type'):
                print("  [canvas] FIX: add 'canvases:write' scope at api.slack.com/apps -> OAuth & Permissions.")
    except Exception as e:
        print(f"  [canvas] workspace access set error: {e}")

    # Step B: channel-level grant (belt-and-suspenders)
    try:
        if channel_ids is None:
            channel_ids = _get_bot_channel_ids(token)
        if not channel_ids:
            print("  [canvas] no channels found for channel-level access set, skipping")
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
            print(f"  [canvas] Channel-level access granted to {len(channel_ids)} channel(s)")
        else:
            err = acc_data.get('error', 'unknown')
            print(f"  [canvas] channel access.set FAILED: {err} (HTTP {access_resp.status_code})")
    except Exception as e:
        print(f"  [canvas] channel access set error: {e}")


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
            print(f"  Canvas creation FAILED ({app_name}): {error}")
            if error in ('missing_scope', 'not_allowed_token_type'):
                needed = result.get('needed', 'canvases:write')
                print(f"  FIX: add '{needed}' scope at api.slack.com/apps -> OAuth & Permissions.")
            # Fallback: post content directly via webhook
            chunks = [content[i:i+3800] for i in range(0, min(len(content), 11400), 3800)]
            for idx, chunk in enumerate(chunks):
                part_label = f" (part {idx+1}/{len(chunks)})" if len(chunks) > 1 else ""
                requests.post(
                    webhook_url,
                    json={
                        "text": (
                            f"*{app_name.upper()} Report: {title}*{part_label}\n"
                            f"_(Canvas unavailable: {error})_\n"
                            f"```{chunk}```"
                        )
                    },
                    timeout=10,
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
            print("  [canvas] chat.postMessage failed everywhere, falling back to webhook")
            requests.post(webhook_url, json={"text": msg_text}, timeout=10)

        # Step 3: Grant read access regardless of whether postMessage succeeded.
        # Pass posted_channels as hint; _set_canvas_access always also attempts workspace-level.
        _set_canvas_access(token, canvas_id, posted_channels if posted_channels else None)

        print(f"  Canvas {canvas_id} created and shared to {len(posted_channels)} channel(s).")
        return deep_link

    except Exception as e:
        print(f"Failed to connect to Slack API: {e}")
        return None


def create_canvas_from_file(file_path, app_name="warroom"):
    """Convenience: read a file and create a canvas from its contents."""
    if not os.path.exists(file_path):
        return
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
