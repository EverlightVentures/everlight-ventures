"""slack_export.py - Nightly export of Slack channel history to markdown.

Source: 05_PERSONAL/A_Personal_Notebook/NOTEPAD/Trranscripts/06_Knowledge_Management/ file-over-AI audit.

Every night, pull the last 48 hours of messages from each channel in our roster
and save as markdown under `08_BACKUPS/slack_exports/YYYY-MM/<channel>.md`. This
is the file-over-AI guarantee for Slack: if Slack goes away or we get kicked,
our operational memory survives in git-backed markdown.

Uses: conversations.history (Slack API free tier).

Install: cron on Oracle 2 AM UTC daily.
    0 2 * * * /usr/bin/python3 /home/opc/hive_scripts/slack_export.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WORKSPACE_CANDIDATES = [Path("/mnt/sdcard/AA_MY_DRIVE"), Path("/home/opc/AA_MY_DRIVE")]

# Channel IDs pulled from slack_routing.yaml (match the 13 we posted charters to)
CHANNELS = {
    "war-room": "C0ANAU30UQ2",
    "ceo-brief": "C0AP56SQM08",
    "hive-alerts": "C0ANPRCA4AD",
    "ft-hunters": "C0AMVEWLT9D",
    "ft-consult": "C0ANEG19WQ4",
    "ft-profit-engine": "C0AN7FT5JBF",
    "ft-markets": "C0AP56SFQG0",
    "ai-consulting": "C0AN8SGAS22",
    "wholesale-deals": "C0ANLLV8JAC",
    "broker-pipeline": "C0AN7FTTK2R",
    "xlm-trading": "C0AN8SG030W",
    "deploy-log": "C0AN4GSTMT5",
    "content-factory": "C0ANPRDUP0R",
}


def _workspace() -> Path:
    for p in WORKSPACE_CANDIDATES:
        if p.exists():
            return p
    return WORKSPACE_CANDIDATES[0]


def _load_token() -> str:
    for env_path in [
        _workspace() / "03_AUTOMATION_CORE" / "03_Credentials" / ".env",
        Path("/home/opc/.env"),
    ]:
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.startswith("SLACK_WARROOM_TOKEN="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    return os.environ.get("SLACK_WARROOM_TOKEN", "")


def fetch_history(channel_id: str, token: str, since_ts: float, limit: int = 300) -> list[dict]:
    """conversations.history. Returns list of message dicts."""
    url = "https://slack.com/api/conversations.history"
    params = {
        "channel": channel_id,
        "oldest": f"{since_ts:.6f}",
        "limit": str(limit),
    }
    query = urllib.parse.urlencode(params)
    req = urllib.request.Request(
        f"{url}?{query}",
        headers={"Authorization": f"Bearer {token}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"  HTTP error on {channel_id}: {e.code}", file=sys.stderr)
        return []
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        print(f"  fetch fail on {channel_id}: {e}", file=sys.stderr)
        return []
    if not data.get("ok"):
        err = data.get("error", "unknown")
        if err == "not_in_channel":
            print(f"  {channel_id}: bot not in channel (skip)")
        else:
            print(f"  {channel_id}: {err}")
        return []
    return data.get("messages", []) or []


def write_channel_archive(channel_name: str, messages: list[dict], base_dir: Path) -> Path:
    now = datetime.now(timezone.utc)
    month = now.strftime("%Y-%m")
    out_dir = base_dir / month
    out_dir.mkdir(parents=True, exist_ok=True)
    today = now.strftime("%Y-%m-%d")
    path = out_dir / f"{channel_name}_{today}.md"

    lines = [f"# Slack Archive: #{channel_name}",
             f"_Exported: {now.isoformat()}_",
             f"_Messages: {len(messages)}_",
             "",
             "---",
             ""]
    for msg in reversed(messages):  # oldest first
        ts_raw = msg.get("ts", "0")
        try:
            ts_int = float(ts_raw)
            ts_iso = datetime.fromtimestamp(ts_int, tz=timezone.utc).isoformat()
        except (TypeError, ValueError):
            ts_iso = ts_raw
        user = msg.get("user") or msg.get("bot_profile", {}).get("name") or msg.get("username", "unknown")
        text = msg.get("text", "")
        lines.append(f"**[{ts_iso}] {user}**")
        lines.append("")
        lines.append(text.replace("\n", "\n> "))
        lines.append("")
        lines.append("---")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=int, default=48, help="Export window in hours back from now")
    ap.add_argument("--channel", help="Single channel to export (slug). Default: all 13.")
    args = ap.parse_args()

    token = _load_token()
    if not token:
        print("ERROR: no SLACK_WARROOM_TOKEN in env or .env", file=sys.stderr)
        return 1

    since_ts = time.time() - (args.hours * 3600)
    base_dir = _workspace() / "08_BACKUPS" / "slack_exports"
    if not (_workspace() / "08_BACKUPS").exists():
        base_dir = Path("/home/opc/hive_reports/slack_exports")
    base_dir.mkdir(parents=True, exist_ok=True)

    targets = {args.channel: CHANNELS[args.channel]} if args.channel else CHANNELS

    total_messages = 0
    total_channels = 0
    for name, cid in targets.items():
        print(f"Fetching #{name}...")
        msgs = fetch_history(cid, token, since_ts)
        if msgs:
            p = write_channel_archive(name, msgs, base_dir)
            print(f"  wrote {len(msgs)} msgs to {p.name}")
            total_messages += len(msgs)
            total_channels += 1
        time.sleep(1)  # tier-1 rate limit friendly

    print(f"\nDone. {total_messages} messages across {total_channels} channels -> {base_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
