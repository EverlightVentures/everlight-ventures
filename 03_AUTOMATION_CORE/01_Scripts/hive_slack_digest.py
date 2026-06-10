"""hive_slack_digest.py - Hourly digest of Hive activity to a single Slack post.

Source: 05_PERSONAL/A_Personal_Notebook/NOTEPAD/Trranscripts/03_Slack_and_Communication/slack_tutorial_for_remote_work.txt
Source: 05_PERSONAL/A_Personal_Notebook/NOTEPAD/Trranscripts/03_Slack_and_Communication/master_communication_and_coordination.txt

Pulls the last hour of activity from Blinko tags and posts ONE summary to #war-room.
Real-time alerts (XLM stops, payment failures, service outages) are NOT batched; they
still go to #hive-alerts immediately via their own paths.

Install on phone cron (or Oracle cron):
    0 * * * * /usr/bin/python3 /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/hive_slack_digest.py

Run manually:
    python3 hive_slack_digest.py --window 1h
"""
from __future__ import annotations

import argparse
import json
import os
import re
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

BLINKO_URL = os.environ.get("BLINKO_URL", "http://163.192.19.196:1111")
WAR_ROOM_CHANNEL = "C0ANAU30UQ2"
DEFAULT_WINDOW_MINUTES = 60

# Load token from env file (matches pattern in hive_llm_router.py)
_token_loaded = False
_token = ""


def _load_token() -> str:
    global _token_loaded, _token
    if _token_loaded:
        return _token
    _token = os.environ.get("SLACK_WARROOM_TOKEN", "")
    if not _token:
        env_path = Path("/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/03_Credentials/.env")
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.startswith("SLACK_WARROOM_TOKEN="):
                    _token = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    _token_loaded = True
    return _token


# ---------------------------------------------------------------------------
# Blinko fetch
# ---------------------------------------------------------------------------

def fetch_blinko_notes(since_utc: datetime, page_size: int = 100) -> list[dict]:
    """Pull Blinko notes created after `since_utc`. Paginates until exhausted."""
    out: list[dict] = []
    page = 1
    while True:
        body = json.dumps({"page": page, "size": page_size, "searchText": ""}).encode()
        req = urllib.request.Request(
            f"{BLINKO_URL}/api/v1/note/list",
            data=body,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode())
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            break
        items = data.get("items") or []
        if not items:
            break
        # Filter by timestamp client-side (Blinko doesn't have since filter)
        recent = []
        for item in items:
            ts = item.get("created_at") or ""
            try:
                created = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                continue
            if created >= since_utc:
                recent.append(item)
        out.extend(recent)
        # Stop if the last item in this page is older than window
        oldest_ts = items[-1].get("created_at") or ""
        try:
            oldest_dt = datetime.fromisoformat(oldest_ts.replace("Z", "+00:00"))
            if oldest_dt < since_utc:
                break
        except (ValueError, TypeError):
            break
        if len(items) < page_size:
            break
        page += 1
        if page > 10:
            break  # safety cap
    return out


# ---------------------------------------------------------------------------
# Analyze notes
# ---------------------------------------------------------------------------

TAG_AGENT_RX = re.compile(r"#hive/([a-z0-9_-]+)")


def analyze_notes(notes: list[dict]) -> dict:
    """Group notes by agent/domain tag and produce summary counts."""
    by_tag: dict[str, int] = Counter()
    highlights: list[str] = []
    agents_seen: set[str] = set()
    domains: Counter[str] = Counter()

    agent_names = {
        "rex-thornton", "rex-blackwell", "piper", "hammer", "marcus", "cipher",
        "filter", "penny", "cash", "forge", "justine", "cupid", "chart",
        "harrison", "charles", "writer",
    }
    domain_tags = {
        "xlm", "wholesale", "broker", "consulting", "content", "payments",
        "deploy", "session", "slack", "blinko", "transcript", "receptionist",
    }

    for note in notes:
        content = note.get("content", "")
        tags_blob = note.get("tags", "") + " " + content[:500]
        found = TAG_AGENT_RX.findall(tags_blob)
        for f in found:
            by_tag[f] += 1
            if f in agent_names:
                agents_seen.add(f)
            if f in domain_tags:
                domains[f] += 1

        # Build highlights: first non-header line that mentions an agent or dollar amount or "alert"
        lines = [l.strip() for l in content.splitlines() if l.strip()]
        for line in lines[:6]:
            if len(line) > 200:
                continue
            if any(kw in line.lower() for kw in ["closed", "booked", "$", "alert", "error", "shipped", "approved"]):
                highlights.append(f"- {line[:160]}")
                break

    return {
        "total_notes": len(notes),
        "top_tags": by_tag.most_common(6),
        "agents_seen": sorted(agents_seen),
        "domains": dict(domains.most_common()),
        "highlights": highlights[:6],
    }


# ---------------------------------------------------------------------------
# Compose digest
# ---------------------------------------------------------------------------

def compose_digest(analysis: dict, window_label: str) -> dict:
    """Return Slack blocks payload."""
    domains = analysis["domains"] or {}
    agents = analysis["agents_seen"]
    highlights = analysis["highlights"]

    summary_line = (
        f"Past {window_label}: {analysis['total_notes']} Hive events logged. "
        f"Domains active: {', '.join(domains.keys()) or 'quiet'}. "
        f"Agents active: {', '.join(agents) or 'none'}."
    )

    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": f"Hive Digest ({window_label})"}},
        {"type": "section", "text": {"type": "mrkdwn", "text": summary_line}},
    ]
    if highlights:
        blocks.append(
            {"type": "section", "text": {"type": "mrkdwn", "text": "*Highlights:*\n" + "\n".join(highlights)}}
        )
    if domains:
        breakdown = " - ".join(f"{d}:{n}" for d, n in domains.items())
        blocks.append(
            {"type": "context", "elements": [{"type": "mrkdwn", "text": f"By domain: {breakdown}"}]}
        )
    if analysis["total_notes"] == 0:
        blocks = [
            {"type": "section", "text": {"type": "mrkdwn", "text": f"Past {window_label}: quiet hour. No significant Hive events."}},
        ]
    return {"channel": WAR_ROOM_CHANNEL, "text": summary_line, "blocks": blocks}


# ---------------------------------------------------------------------------
# Slack send
# ---------------------------------------------------------------------------

def post_to_slack(payload: dict) -> bool:
    token = _load_token()
    if not token:
        print("no slack token; skipping post")
        return False
    req = urllib.request.Request(
        "https://slack.com/api/chat.postMessage",
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        return bool(data.get("ok"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_window(s: str) -> int:
    """Parse '1h', '30m', '15m' into minutes."""
    s = s.strip().lower()
    if s.endswith("h"):
        return int(s[:-1]) * 60
    if s.endswith("m"):
        return int(s[:-1])
    return int(s)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--window", default="1h", help="window like '1h', '30m', '4h'")
    ap.add_argument("--dry-run", action="store_true", help="compose but do not post")
    args = ap.parse_args()

    minutes = parse_window(args.window)
    since = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    print(f"Fetching Blinko notes since {since.isoformat()}")
    notes = fetch_blinko_notes(since)
    print(f"  {len(notes)} notes in window")

    analysis = analyze_notes(notes)
    payload = compose_digest(analysis, args.window)

    if args.dry_run:
        print(json.dumps(payload, indent=2))
        return 0

    ok = post_to_slack(payload)
    print("posted ok" if ok else "post failed")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
