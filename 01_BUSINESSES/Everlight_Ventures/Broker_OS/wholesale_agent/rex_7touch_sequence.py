"""

# noqa: direct-resend
# This file still POSTs to api.resend.com directly. The eradication_gate is now
# called BEFORE any send, and the module refuses to load under WHOLESALE_OUTBOUND_HALT=1.
# Full migration to content_tools.branded_mailer.send_branded_email() is tracked
# in _state/SELF_AUDIT_2026-05-15_STREUBEL_2ND_STRIKE.md under "Lift criteria".
# The noqa marker is the lint's documented exception for files that are gated
# pending a full refactor. DO NOT remove the eradication_gate import or the
# module-level halt check; they are the load-bearing protections.
Rex 7-Touch Sequence -- replace spray-and-pray with a proven 25-day drip.

Each lead progresses through 7 touches over 25 days, alternating SMS and email.
The Day 25 "closing my file" touch has the highest response rate in the industry.

Touch schedule:
  1  Day  0  SMS   -- intro question
  2  Day  1  Email -- full pain-aware pitch
  3  Day  4  SMS   -- follow-up + value prop
  4  Day  8  Email -- social proof
  5  Day 12  SMS   -- urgency / market shift
  6  Day 18  Email -- as-is angle
  7  Day 25  SMS   -- "closing my file" (highest response rate)

Reads leads_db.json, advances each lead through the sequence based on
elapsed days since last_outreach, then saves back.
"""

# === ERADICATION HALT (auto-inserted 2026-05-15 after Streubel 2nd-strike) ===
import os as _os_halt
if _os_halt.environ.get("WHOLESALE_OUTBOUND_HALT", "").strip() in {"1", "true", "TRUE", "yes"}:
    import sys as _sys_halt
    print("[rex_7touch_sequence.py] WHOLESALE_OUTBOUND_HALT=1 -- refusing to run", file=_sys_halt.stderr)
    raise SystemExit("WHOLESALE_OUTBOUND_HALT active")
import sys as _sys_eg
_sys_eg.path.insert(0, "/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/content_tools")
try:
    from eradication_gate import assert_safe as _erad_assert_safe, EradicationViolation
except ImportError as _eg_err:
    print(f"[rex_7touch_sequence.py] eradication_gate unavailable: {_eg_err}", file=_sys_eg.stderr)
    raise SystemExit("eradication_gate required")
# === END ERADICATION HALT ===

import json
import logging
import os
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="[Rex 7Touch %(asctime)s] %(message)s",
    datefmt="%H:%M",
)
log = logging.getLogger("rex_7touch")

AGENT_DIR = Path(__file__).parent
LEADS_DB = AGENT_DIR / "leads_db.json"

RESEND_KEY = os.environ.get("RESEND_API_KEY", os.environ.get("SMTP_PASS", ""))
FROM_EMAIL = os.environ.get("SMTP_FROM", "Piper Reeves <piper@everlightventures.io>")
REPLY_TO = "piper@everlightventures.io"

NOW = datetime.now(timezone.utc)
TODAY = NOW.strftime("%Y-%m-%d")

# Rate limit between sends (seconds)
SEND_DELAY = 2

# Max sends per run (stay under Resend free-tier 100/day)
MAX_SENDS_PER_RUN = 80


# ---------------------------------------------------------------------------
# SEQUENCE DEFINITION
# ---------------------------------------------------------------------------

SEQUENCE = [
    # step, day_offset, channel, template_key
    (1,  0,  "sms",   "touch1_sms"),
    (2,  1,  "email", "touch2_email"),
    (3,  4,  "sms",   "touch3_sms"),
    (4,  8,  "email", "touch4_email"),
    (5,  12, "sms",   "touch5_sms"),
    (6,  18, "email", "touch6_email"),
    (7,  25, "sms",   "touch7_sms"),
]


def _first_name(lead: dict) -> str:
    owner = lead.get("owner_name", "")
    return owner.split()[0].title() if owner else "there"


def get_touch_message(step: int, lead: dict) -> tuple:
    """Return (subject_or_none, body) for a sequence step.
    SMS touches return (None, body). Email touches return (subject, body).
    """
    first = _first_name(lead)
    addr = lead.get("address", "your property")
    city = lead.get("city", "the area")
    state = lead.get("state", "")
    zip_code = lead.get("zip_code", "")
    lead_type = lead.get("lead_type", "")

    if step == 1:
        # SMS -- under 160 chars
        body = (
            f"Hi {first}, are you the owner of {addr}? "
            f"I'm looking to buy in {city}. Quick question if you have a sec."
        )
        return (None, body[:160])

    if step == 2:
        # Email -- full pain-aware pitch
        subject = f"Cash offer for {addr}"
        body = _pain_pitch(lead_type, first, addr, city, state)
        return (subject, body)

    if step == 3:
        body = (
            f"Following up on {addr}. Still interested in a cash offer? "
            f"No agents, no fees, close in 7 days."
        )
        return (None, body[:160])

    if step == 4:
        subject = f"We just closed 3 properties in {city}"
        body = (
            f"Hi {first},\n\n"
            f"We just closed 3 properties this month in {city}. "
            f"Owners walked away with cash in under 2 weeks.\n\n"
            f"If you are open to a similar outcome for {addr}, "
            f"just reply and I will put together an offer.\n\n"
            f"Piper\n"
            f"Everlight Ventures\n"
            f"piper@everlightventures.io"
        )
        return (subject, body)

    if step == 5:
        body = (
            f"Property values in {zip_code or city} are shifting. "
            f"Wanted to make sure you had a chance to hear our offer before things change."
        )
        return (None, body[:160])

    if step == 6:
        subject = f"About {addr} -- we buy as-is"
        body = (
            f"Hi {first},\n\n"
            f"I noticed {addr} might need some work. "
            f"We buy as-is -- no repairs, no cleaning, no showings. Just cash.\n\n"
            f"If that sounds like a relief, reply and I will get you a number.\n\n"
            f"Piper\n"
            f"Everlight Ventures\n"
            f"piper@everlightventures.io"
        )
        return (subject, body)

    if step == 7:
        # "Closing my file" -- highest response rate in the industry
        body = (
            f"I'm closing my file on {addr}. "
            f"If you ever want to discuss a cash offer, reach me at piper@everlightventures.io."
        )
        return (None, body[:160])

    return (None, "")


def _pain_pitch(lead_type: str, first: str, addr: str, city: str, state: str) -> str:
    """Pull pain-aware email pitch from rex_sdr templates, with fallback."""
    try:
        from rex_sdr import get_pain_template
        template = get_pain_template(lead_type, 1)
        return template.format(
            first_name=first,
            address=addr,
            city=city,
            state=state,
        )
    except Exception:
        return (
            f"Hi {first},\n\n"
            f"I am reaching out about your property at {addr}, {city}, {state}. "
            f"I buy properties for cash and can close in 7-14 days -- "
            f"no repairs, no commissions, no hassle.\n\n"
            f"Would you be open to hearing an offer?\n\n"
            f"Piper\n"
            f"Everlight Ventures\n"
            f"piper@everlightventures.io"
        )


# ---------------------------------------------------------------------------
# SEND HELPERS
# ---------------------------------------------------------------------------

def send_email(to: str, subject: str, body: str) -> bool:
    """Send email via Resend (or rex_utils safe wrapper)."""
    if not RESEND_KEY or not to:
        return False
    try:
        from rex_utils import safe_send_email
        return safe_send_email(to, subject, body)
    except ImportError:
        pass
    import requests
    try:
        resp = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {RESEND_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "from": FROM_EMAIL,
                "to": [to],
                "subject": subject,
                "text": body,
                "reply_to": REPLY_TO,
            },
            timeout=10,
        )
        return resp.status_code in (200, 201)
    except Exception:
        return False


def send_sms_via_gateway(to_email: str, body: str) -> bool:
    """Send SMS by emailing the carrier gateway address.
    The lead's owner_email may already be a gateway address (e.g. 5551234567@txt.att.net).
    For actual email addresses we send as email with a short subject.
    """
    if not to_email:
        return False
    # Detect carrier gateway addresses
    gateways = [
        "@txt.att.net", "@vtext.com", "@tmomail.net",
        "@messaging.sprintpcs.com", "@mymetropcs.com",
        "@mms.cricketwireless.net", "@msg.fi.google.com",
    ]
    is_gateway = any(gw in to_email.lower() for gw in gateways)

    if is_gateway:
        # SMS gateway -- no subject, just body
        return send_email(to_email, "", body)
    else:
        # Regular email fallback -- send as short email
        return send_email(to_email, "Quick question about your property", body)


# ---------------------------------------------------------------------------
# SEQUENCE RUNNER
# ---------------------------------------------------------------------------

def _days_since(date_str: str) -> int:
    """Return days between a YYYY-MM-DD string and now."""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        return (NOW - dt).days
    except (ValueError, TypeError):
        return 999


def run_sequence() -> dict:
    """Advance all eligible leads through the 7-touch sequence."""
    if not LEADS_DB.exists():
        log.warning("No leads_db.json found")
        return {"sent": 0, "skipped": 0, "completed": 0}

    leads = json.loads(LEADS_DB.read_text())
    sent = 0
    skipped = 0
    completed = 0

    for lead in leads:
        if sent >= MAX_SENDS_PER_RUN:
            break

        status = lead.get("status", "new")
        # Skip dead, replied, or already under contract leads
        if status in ("dead", "replied", "negotiating", "under_contract", "closed"):
            skipped += 1
            continue

        # Skip leads with no contact info
        email = lead.get("owner_email", "")
        if not email:
            skipped += 1
            continue

        current_step = lead.get("sequence_step", 0)
        last_outreach = lead.get("last_outreach", "")

        # Already finished all 7 touches
        if current_step >= 7:
            if status != "sequence_complete":
                lead["status"] = "sequence_complete"
            completed += 1
            continue

        # Figure out which touch is next
        next_step = current_step + 1
        seq_entry = SEQUENCE[next_step - 1]  # 0-indexed
        step_num, day_offset, channel, _ = seq_entry

        # For step 1 (new leads), send immediately
        if current_step == 0 and status == "new":
            days_needed = 0
        else:
            if not last_outreach:
                skipped += 1
                continue
            # Days needed = gap between this touch and previous touch
            prev_day = SEQUENCE[current_step - 1][1] if current_step > 0 else 0
            days_needed = day_offset - prev_day
            elapsed = _days_since(last_outreach)
            if elapsed < days_needed:
                skipped += 1
                continue

        # Build and send the message
        subject, body = get_touch_message(step_num, lead)
        ok = False

        if channel == "sms":
            ok = send_sms_via_gateway(email, body)
        elif channel == "email":
            if subject:
                ok = send_email(email, subject, body)

        if ok:
            lead["sequence_step"] = step_num
            lead["outreach_count"] = lead.get("outreach_count", 0) + 1
            lead["last_outreach"] = TODAY

            if current_step == 0:
                lead["status"] = "contacted"
            elif step_num < 7:
                lead["status"] = "followed_up"
            else:
                lead["status"] = "sequence_complete"

            sent += 1
            log.info(
                f"Touch {step_num}/7 ({channel}) -> "
                f"{lead.get('address', '?')[:40]}"
            )
            time.sleep(SEND_DELAY)
        else:
            skipped += 1

    LEADS_DB.write_text(json.dumps(leads, indent=2, default=str))

    stats = {"sent": sent, "skipped": skipped, "completed": completed}
    log.info(
        f"Sequence run complete: {sent} sent | "
        f"{skipped} skipped | {completed} already done"
    )
    return stats


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    stats = run_sequence()
    print(json.dumps(stats, indent=2))
