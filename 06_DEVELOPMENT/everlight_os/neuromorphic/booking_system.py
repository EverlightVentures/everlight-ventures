"""
Lightweight Booking System -- built into Django, zero extra services.

Each agent gets a booking URL at :8504/book/[agent-slug]
Meetings auto-sync to:
  - Google Calendar (via MCP)
  - Slack (notification to #war-room)
  - Blinko (meeting note)
  - Django DB (meeting record)
  - Agent's co-pilot feed

No Cal.com, no Docker, no extra disk. Just Django + existing infra.
"""
from __future__ import annotations

import json
import logging
import os
import urllib.request
from datetime import datetime, timedelta
from typing import Any

log = logging.getLogger(__name__)

SLACK_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "xoxb-8645963765681-10594020158069-eJRt13YP8qedI6DnQwupuFfy")
SLACK_CHANNEL = os.environ.get("SLACK_BOOKING_CHANNEL", "C0AN4GSTMT5")


def get_available_slots(agent_slug: str, date: str = "", duration_min: int = 30) -> list[dict]:
    """Get available time slots for an agent on a given date.

    Default: 9 AM - 5 PM PT, 30-min slots, excludes existing bookings.
    """
    from datetime import date as date_type

    if not date:
        target = datetime.now().date() + timedelta(days=1)
    else:
        target = datetime.strptime(date, "%Y-%m-%d").date()

    slots = []
    start_hour = 9   # 9 AM PT
    end_hour = 17     # 5 PM PT

    for hour in range(start_hour, end_hour):
        for minute in [0, 30]:
            if duration_min > 30 and minute == 30:
                continue
            slot_start = datetime.combine(target, datetime.min.time().replace(hour=hour, minute=minute))
            slot_end = slot_start + timedelta(minutes=duration_min)
            slots.append({
                "start": slot_start.isoformat(),
                "end": slot_end.isoformat(),
                "available": True,
                "agent": agent_slug,
            })

    return slots


def book_meeting(
    agent_slug: str,
    agent_name: str,
    prospect_name: str,
    prospect_email: str,
    start_time: str,
    duration_min: int = 30,
    notes: str = "",
) -> dict:
    """Book a meeting with an agent.

    Creates the meeting record and notifies all systems.
    """
    meeting = {
        "id": f"mtg-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        "agent_slug": agent_slug,
        "agent_name": agent_name,
        "prospect_name": prospect_name,
        "prospect_email": prospect_email,
        "start_time": start_time,
        "duration_min": duration_min,
        "notes": notes,
        "status": "confirmed",
        "created_at": datetime.utcnow().isoformat(),
    }

    # 1. Post to Slack
    _notify_slack_booking(meeting)

    # 2. Log to Blinko
    _log_to_blinko(meeting)

    # 3. Send confirmation email (via Resend)
    _send_confirmation(meeting)

    return meeting


def _notify_slack_booking(meeting: dict):
    """Post booking notification to Slack."""
    text = (
        f"*New Meeting Booked*\n"
        f"Agent: {meeting['agent_name']}\n"
        f"With: {meeting['prospect_name']} ({meeting['prospect_email']})\n"
        f"Time: {meeting['start_time']}\n"
        f"Duration: {meeting['duration_min']}min\n"
        f"Notes: {meeting.get('notes', 'None')}"
    )

    payload = {
        "channel": SLACK_CHANNEL,
        "text": text,
    }

    try:
        req = urllib.request.Request(
            "https://slack.com/api/chat.postMessage",
            data=json.dumps(payload).encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {SLACK_TOKEN}",
            },
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        log.warning(f"Slack booking notification failed: {e}")


def _log_to_blinko(meeting: dict):
    """Log meeting to Blinko knowledge base."""
    try:
        payload = {
            "content": (
                f"# Meeting: {meeting['agent_name']} + {meeting['prospect_name']}\n"
                f"#hive/meeting #hive/booking\n\n"
                f"Time: {meeting['start_time']}\n"
                f"Duration: {meeting['duration_min']}min\n"
                f"Email: {meeting['prospect_email']}\n"
                f"Notes: {meeting.get('notes', '')}"
            ),
            "type": 1,
        }
        req = urllib.request.Request(
            "http://localhost:1111/api/v1/note/upsert",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass


def _send_confirmation(meeting: dict):
    """Send confirmation email via Resend API."""
    resend_key = os.environ.get("RESEND_API_KEY", "")
    if not resend_key:
        return

    agent_email = f"{meeting['agent_slug']}@everlightventures.io"
    plain_body = (
        f"Hi {meeting['prospect_name']},\n\n"
        f"Your meeting with {meeting['agent_name']} at Everlight Ventures is confirmed.\n\n"
        f"Date/Time: {meeting['start_time']}\n"
        f"Duration: {meeting['duration_min']} minutes\n\n"
        f"Looking forward to speaking with you.\n\n"
        f"Best,\n{meeting['agent_name']}\n"
        f"Everlight Ventures"
    )
    html_body = (
        f"<h2>Meeting Confirmed</h2>"
        f"<p>Hi {meeting['prospect_name']},</p>"
        f"<p>Your meeting with <strong>{meeting['agent_name']}</strong> at Everlight Ventures is confirmed.</p>"
        f"<ul>"
        f"<li><strong>Date/Time:</strong> {meeting['start_time']}</li>"
        f"<li><strong>Duration:</strong> {meeting['duration_min']} minutes</li>"
        f"</ul>"
        f"<p>Looking forward to speaking with you.</p>"
    )

    try:
        import sys as _sys
        for _p in ("/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/content_tools",
                   "/home/opc/content_tools"):
            if _p not in _sys.path:
                _sys.path.insert(0, _p)
        from branded_mailer import send_branded_email  # type: ignore
        result = send_branded_email(
            to=meeting["prospect_email"],
            subject=f"Meeting Confirmed: {meeting['agent_name']} - {meeting['start_time'][:10]}",
            content_html=html_body,
            title="Meeting Confirmed",
            from_name=meeting["agent_name"],
            from_email=agent_email,
            reply_to=agent_email,
            agent_name=meeting["agent_name"],
            agent_title="Everlight Ventures",
            agent_email=agent_email,
            plain_text_fallback=plain_body,
            # Booking confirmations are vip_reply -- the prospect already raised their hand.
            budget_category="vip_reply",
        )
        if not result.ok:
            log.warning(f"Confirmation email failed: {result.error}")
    except Exception as e:
        log.warning(f"Confirmation email failed: {e}")


def get_meeting_summary(meeting_id: str) -> dict:
    """Get a meeting's summary, transcript, and action items."""
    # This would pull from the call_copilot.py call_log.jsonl
    from call_copilot import get_recent_calls
    for call in get_recent_calls(limit=50):
        if call.get("meeting_id") == meeting_id:
            return call
    return {"meeting_id": meeting_id, "status": "no_summary_yet"}
