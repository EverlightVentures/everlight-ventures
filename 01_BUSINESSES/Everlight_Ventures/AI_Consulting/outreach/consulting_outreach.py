#!/usr/bin/env python3
"""
AI Consulting Outreach System -- 7-touch email sequence via Resend API.

Modeled after broker_outreach_sdr.py. Sends personalized emails to scored
SMB leads from the prospect pipeline.

Usage:
    python3 consulting_outreach.py fresh    # Send to new leads
    python3 consulting_outreach.py followup # Send follow-ups
    python3 consulting_outreach.py status   # Pipeline status

Rate limits: 30 new + 20 follow-up per day.
"""

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

WORKSPACE = Path("/mnt/sdcard/AA_MY_DRIVE")
LOG_DIR = WORKSPACE / "_logs" / "ai_consulting"
OUTREACH_LOG = LOG_DIR / "outreach_log.jsonl"

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
FROM_EMAIL = "consulting@everlightventures.io"
FROM_NAME = "Piper Reeves | Everlight Ventures"

DAILY_FRESH_LIMIT = 30
DAILY_FOLLOWUP_LIMIT = 20

# 7-touch sequence over 21 days (Piper Reeves warm copy style)
SEQUENCE = [
    {
        "day": 0,
        "subject": "Quick question about {business_name}",
        "body": """Hey there,

I came across {business_name} and wanted to reach out. We help businesses like yours save 15-20 hours a week with AI-powered automation -- things like lead follow-up, appointment scheduling, and customer support that runs 24/7.

Meta just started using AI agents for everything from CEO tasks to employee reviews. We bring that same technology to local businesses, but affordable and practical.

Would you be open to a quick 15-min call this week? I can show you exactly what an AI agent would look like for {category} businesses.

No pressure at all -- just think it could be valuable.

Best,
Piper Reeves
Everlight Ventures
consulting@everlightventures.io""",
    },
    {
        "day": 3,
        "subject": "Re: Quick question about {business_name}",
        "body": """Hi again,

Just wanted to follow up on my note. I know you're busy running {business_name} -- that's actually exactly why I think this would help.

One of our clients went from spending 3 hours/day on lead follow-up to zero. Their AI agent handles the initial response, qualifies the lead, and books the appointment automatically.

I'd love to show you a 5-minute demo. No commitment, just a look.

Here's a $1 discovery session link if you're curious: [DISCOVERY_LINK]

Piper""",
    },
    {
        "day": 7,
        "subject": "A {category} business just saved 20hrs/week with AI",
        "body": """Hey,

Quick case study I thought you'd find interesting:

A {category} business similar to {business_name} was spending $4k/month on a receptionist for appointment scheduling and phone follow-ups. We replaced that with an AI agent for $2k/month that:

- Responds to every inquiry in under 60 seconds
- Books appointments directly into their calendar
- Follows up with no-shows automatically
- Never takes a sick day

The ROI was positive in month one.

Would something like this interest you? Happy to walk you through it.

Piper
Everlight Ventures""",
    },
    {
        "day": 10,
        "subject": "Last thought on AI for {business_name}",
        "body": """Hi,

I don't want to be a pest, so this will be my last email for a while.

If you ever want to explore how AI agents could help {business_name}:
- Save time on repetitive tasks
- Never miss a lead
- Provide 24/7 customer support

Just reply "interested" and I'll send you a quick demo link.

Either way, wishing you all the best with {business_name}.

Piper Reeves
consulting@everlightventures.io""",
    },
    {
        "day": 14,
        "subject": "New: AI agents for {category} (2-min video)",
        "body": """Hey,

We just put together a quick 2-minute video showing exactly how AI agents work for {category} businesses. No fluff, just a screen recording of the actual system.

Thought of you and {business_name}. Here's the link: [VIDEO_LINK]

If it sparks any ideas, I'm here.

Piper""",
    },
    {
        "day": 18,
        "subject": "Quick update + an offer",
        "body": """Hi,

We're offering our first 10 {location} businesses a special rate on AI agent setup. $1 gets you a full discovery session where we:

1. Audit your current workflow
2. Identify 3 things AI can automate immediately
3. Show you a live demo customized to {category}

No strings attached. Here's the link: [DISCOVERY_LINK]

Spots going fast since we can only handle so many builds at once.

Piper
Everlight Ventures""",
    },
    {
        "day": 21,
        "subject": "Closing the loop on {business_name}",
        "body": """Hey,

Just closing the loop on this. If AI automation isn't a priority for {business_name} right now, totally understand.

If anything changes in the future, you know where to find us. We'll be here building AI agents and helping businesses save time.

Wishing you a great rest of the year.

Piper Reeves
Everlight Ventures
consulting@everlightventures.io""",
    },
]


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _log_outreach(entry: dict):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTREACH_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def _send_email(to_email: str, subject: str, body: str) -> bool:
    """Send email via Resend API."""
    if not RESEND_API_KEY:
        print(f"[DRY RUN] Would send to {to_email}: {subject}")
        return True

    payload = json.dumps({
        "from": f"{FROM_NAME} <{FROM_EMAIL}>",
        "to": [to_email],
        "subject": subject,
        "text": body,
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {RESEND_API_KEY}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status == 200
    except Exception as e:
        print(f"[ERROR] Send failed: {e}")
        return False


def _get_sent_log() -> list[dict]:
    """Read outreach log."""
    if not OUTREACH_LOG.exists():
        return []
    entries = []
    for line in OUTREACH_LOG.read_text(encoding="utf-8").strip().splitlines():
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return entries


def _today_count(log: list[dict], touch_type: str) -> int:
    """Count emails sent today of a given type."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return sum(
        1 for e in log
        if e.get("sent_at", "").startswith(today) and e.get("type") == touch_type
    )


def send_fresh(scored_file: str, min_score: int = 30):
    """Send Touch 1 to new high-scoring leads."""
    path = Path(scored_file)
    if not path.is_absolute():
        path = LOG_DIR / scored_file

    if not path.exists():
        print(f"[ERROR] Scored file not found: {path}")
        return

    leads = json.loads(path.read_text(encoding="utf-8"))
    qualified = [l for l in leads if l.get("score", 0) >= min_score]
    print(f"[FRESH] {len(qualified)} qualified leads (score >= {min_score})")

    log = _get_sent_log()
    already_sent = {e.get("business_name") for e in log}
    today_sent = _today_count(log, "fresh")

    sent = 0
    for lead in qualified:
        if today_sent + sent >= DAILY_FRESH_LIMIT:
            print(f"[LIMIT] Daily fresh limit reached ({DAILY_FRESH_LIMIT})")
            break

        if lead["business_name"] in already_sent:
            continue

        # Need email -- skip if not available
        email = lead.get("email")
        if not email:
            continue

        touch = SEQUENCE[0]
        subject = touch["subject"].format(**lead)
        body = touch["body"].format(**lead)

        if _send_email(email, subject, body):
            _log_outreach({
                "business_name": lead["business_name"],
                "email": email,
                "type": "fresh",
                "touch": 1,
                "subject": subject,
                "sent_at": _now_iso(),
                "score": lead.get("score", 0),
            })
            sent += 1

    print(f"[SENT] {sent} fresh emails")


def send_followups():
    """Send follow-up touches based on timing."""
    log = _get_sent_log()
    today_sent = _today_count(log, "followup")

    # Group by business
    by_business = {}
    for entry in log:
        name = entry.get("business_name", "")
        if name not in by_business:
            by_business[name] = []
        by_business[name].append(entry)

    sent = 0
    now = datetime.now(timezone.utc)

    for name, entries in by_business.items():
        if today_sent + sent >= DAILY_FOLLOWUP_LIMIT:
            print(f"[LIMIT] Daily follow-up limit reached ({DAILY_FOLLOWUP_LIMIT})")
            break

        last_entry = max(entries, key=lambda e: e.get("sent_at", ""))
        last_touch = last_entry.get("touch", 1)

        if last_touch >= len(SEQUENCE):
            continue  # Sequence complete

        next_touch_idx = last_touch  # 0-indexed, so touch N means next is index N
        if next_touch_idx >= len(SEQUENCE):
            continue

        next_touch = SEQUENCE[next_touch_idx]
        days_since = (now - datetime.fromisoformat(last_entry["sent_at"])).days

        if days_since < next_touch["day"] - (SEQUENCE[next_touch_idx - 1]["day"] if next_touch_idx > 0 else 0):
            continue  # Not time yet

        email = last_entry.get("email")
        if not email:
            continue

        # Build template vars from first entry
        lead_data = {
            "business_name": name,
            "category": entries[0].get("category", "business"),
            "location": entries[0].get("location", "your area"),
        }

        subject = next_touch["subject"].format(**lead_data)
        body = next_touch["body"].format(**lead_data)

        if _send_email(email, subject, body):
            _log_outreach({
                "business_name": name,
                "email": email,
                "type": "followup",
                "touch": last_touch + 1,
                "subject": subject,
                "sent_at": _now_iso(),
            })
            sent += 1

    print(f"[SENT] {sent} follow-up emails")


def show_status():
    """Show pipeline status."""
    log = _get_sent_log()
    if not log:
        print("[STATUS] No outreach history yet")
        return

    by_business = {}
    for entry in log:
        name = entry.get("business_name", "unknown")
        by_business.setdefault(name, []).append(entry)

    total = len(by_business)
    touch_counts = {i: 0 for i in range(1, 8)}
    for entries in by_business.values():
        max_touch = max(e.get("touch", 1) for e in entries)
        touch_counts[max_touch] = touch_counts.get(max_touch, 0) + 1

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    today_fresh = sum(1 for e in log if e.get("sent_at", "").startswith(today) and e.get("type") == "fresh")
    today_followup = sum(1 for e in log if e.get("sent_at", "").startswith(today) and e.get("type") == "followup")

    print(f"[STATUS] AI Consulting Outreach Pipeline")
    print(f"  Total businesses: {total}")
    print(f"  Today: {today_fresh} fresh / {today_followup} follow-ups")
    print(f"  Sequence progress:")
    for touch, count in sorted(touch_counts.items()):
        bar = "#" * count
        print(f"    Touch {touch}: {count} {bar}")


def main():
    if len(sys.argv) < 2:
        print("Usage: consulting_outreach.py [fresh|followup|status]")
        return

    cmd = sys.argv[1]
    if cmd == "fresh":
        scored_file = sys.argv[2] if len(sys.argv) > 2 else ""
        if not scored_file:
            # Find latest scored file
            scored_files = sorted(LOG_DIR.glob("*_scored.json"), key=lambda f: f.stat().st_mtime, reverse=True)
            if scored_files:
                scored_file = str(scored_files[0])
            else:
                print("[ERROR] No scored file found. Run lead_scorer.py first.")
                return
        send_fresh(scored_file)
    elif cmd == "followup":
        send_followups()
    elif cmd == "status":
        show_status()
    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
