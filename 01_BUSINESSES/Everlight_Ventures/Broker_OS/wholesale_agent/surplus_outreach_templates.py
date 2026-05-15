#!/usr/bin/env python3

# === ERADICATION HALT (auto-inserted 2026-05-15) ===
# noqa: direct-resend
# Gated by eradication_gate; halts under WHOLESALE_OUTBOUND_HALT=1.
import os as _os_halt
if _os_halt.environ.get("WHOLESALE_OUTBOUND_HALT", "").strip() in {"1", "true", "TRUE", "yes"}:
    import sys as _sys_halt
    print(f"[{__file__}] WHOLESALE_OUTBOUND_HALT=1 -- refusing to run", file=_sys_halt.stderr)
    raise SystemExit("WHOLESALE_OUTBOUND_HALT active")
import sys as _sys_eg
_sys_eg.path.insert(0, "/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/content_tools")
try:
    from eradication_gate import assert_safe as _erad_assert_safe, EradicationViolation
except ImportError as _eg_err:
    print(f"eradication_gate unavailable: {_eg_err}", file=_sys_eg.stderr)
    raise SystemExit("eradication_gate required")
# === END ERADICATION HALT ===
"""
Surplus Funds Recovery -- Outreach Templates
=============================================
Piper Reeves handles all surplus fund owner outreach.
Nashville warmth. No pressure. No upfront cost messaging.

Templates for SMS, email, follow-ups, and voicemail drops.
Integrates with Resend for email delivery.

Usage:
    from surplus_outreach_templates import render_sms, render_email, send_surplus_email
"""

import json
import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

try:
    import requests
except ImportError:
    requests = None  # type: ignore

logger = logging.getLogger("surplus_outreach")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
FROM_EMAIL = "piper@everlightventures.io"
FROM_NAME = "Piper Reeves | Everlight Ventures"
COMPANY_PHONE = os.environ.get("EVERLIGHT_PHONE", "(888) 555-0199")  # Update with real number

BASE_DIR = Path(__file__).resolve().parent
OUTREACH_LOG = BASE_DIR / "outreach" / "surplus_outreach_log.json"
OUTREACH_LOG.parent.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

# --- SMS Templates ---

SMS_INITIAL = (
    "Hi {owner_name}, this is Piper from Everlight Ventures. "
    "We discovered that {county} County is holding ${surplus_amount:,.2f} in "
    "excess proceeds from a property sale linked to you at {property_address}. "
    "We can help you recover these funds at absolutely no upfront cost. "
    "Would you like to learn more? Reply YES or call us at {phone}."
)

SMS_FOLLOW_UP_1 = (
    "Hi {owner_name}, following up on my previous message about the "
    "${surplus_amount:,.2f} being held by {county} County from your property "
    "at {property_address}. This money is legally yours and we can help you "
    "claim it at no upfront cost. The deadline to claim is approaching. "
    "Would you like to discuss? - Piper, Everlight Ventures"
)

SMS_FOLLOW_UP_2 = (
    "Hi {owner_name}, just a final note -- {county} County is holding "
    "${surplus_amount:,.2f} from the sale of your former property. "
    "The claim deadline is {deadline}. After that, the funds may revert to "
    "the county. We handle all the paperwork at no cost to you unless we "
    "recover your money. Reply STOP to opt out. - Piper"
)

SMS_SIGNED_CONFIRMATION = (
    "Hi {owner_name}, this is Piper. Thank you for signing the recovery "
    "authorization. We have filed your claim with {county} County for "
    "${surplus_amount:,.2f}. I will keep you updated on the progress. "
    "Feel free to call me anytime at {phone}."
)

# --- Email Templates ---

EMAIL_SUBJECT = (
    "Unclaimed Funds of ${surplus_amount:,.2f} from {county} County Property Sale"
)

EMAIL_BODY = """Dear {owner_name},

We are writing because {county} County is currently holding ${surplus_amount:,.2f} in excess proceeds from the sale of a property previously associated with you at {property_address}.

These funds are legally yours, but they must be claimed before the deadline of {deadline}. Many property owners are unaware these funds exist.

Our firm, Everlight Ventures, specializes in helping former property owners recover these unclaimed funds. Our service is completely free upfront -- we only earn a fee if we successfully recover your money.

Here is what we need from you:
1. Confirm your identity as the former property owner
2. Sign our simple recovery authorization form
3. We handle all the paperwork and filing with the county

There is no risk to you. If we do not recover your funds, you owe us nothing.

Please reply to this email or call us at {phone} to discuss your claim.

Sincerely,
Piper Reeves
Surplus Recovery Division
Everlight Ventures
{from_email}
{phone}"""

EMAIL_FOLLOW_UP_1_SUBJECT = (
    "Following Up: ${surplus_amount:,.2f} in Unclaimed Funds -- {county} County"
)

EMAIL_FOLLOW_UP_1_BODY = """Dear {owner_name},

I wanted to follow up on my previous email regarding the ${surplus_amount:,.2f} in excess proceeds being held by {county} County from the sale of the property at {property_address}.

I understand that an email like this can seem too good to be true, so I want to be transparent about who we are and how this works:

- Everlight Ventures is a licensed surplus recovery firm.
- {county} County publishes lists of unclaimed excess proceeds from foreclosure sales. Your name appeared on that list.
- Under California law, these funds belong to you as the former property owner.
- Counties are required to hold these funds, but they do not actively seek out owners. That is where we come in.

Our fee structure is simple: we only get paid if we successfully recover your funds. There is zero upfront cost and zero risk to you.

The claim deadline is {deadline}. After that date, the funds may be forfeited to the county permanently.

If you have any questions or would like to proceed, please reply to this email or call me directly at {phone}.

Warm regards,
Piper Reeves
Surplus Recovery Division
Everlight Ventures
{from_email}"""

EMAIL_FOLLOW_UP_2_SUBJECT = (
    "Final Notice: ${surplus_amount:,.2f} Claim Deadline Approaching -- {county} County"
)

EMAIL_FOLLOW_UP_2_BODY = """Dear {owner_name},

This is my final outreach regarding the ${surplus_amount:,.2f} in excess proceeds held by {county} County from the property at {property_address}.

The claim deadline is {deadline}. After this date, the county may permanently retain these funds.

I have reached out twice before because I genuinely want to help you recover money that is rightfully yours. There is no cost to you unless we are successful.

If you are interested, please contact me before {deadline}:
- Email: {from_email}
- Phone: {phone}

If you prefer not to be contacted further, simply reply with STOP and I will remove you from our list immediately.

All the best,
Piper Reeves
Surplus Recovery Division
Everlight Ventures"""

# --- Voicemail Drop ---

VOICEMAIL_SCRIPT = (
    "Hi {owner_name}, this is Piper Reeves calling from Everlight Ventures. "
    "I am reaching out because {county} County is holding ${surplus_amount:,.2f} "
    "in excess proceeds from the sale of a property that was associated with you "
    "at {property_address}. These funds are legally yours and we can help you "
    "recover them at absolutely no upfront cost. Please give me a call back at "
    "{phone} or reply to the text message I sent. Again, my name is Piper and "
    "my number is {phone}. Have a great day."
)

# --- Letter Template (for direct mail) ---

LETTER_TEMPLATE = """
                                                    {date}

{owner_name}
{owner_address}

Dear {owner_name},

RE: Unclaimed Excess Proceeds -- {county} County
    Parcel: {parcel_id}
    Amount: ${surplus_amount:,.2f}

We are writing to inform you that {county} County is currently holding
${surplus_amount:,.2f} in excess proceeds from the foreclosure sale of a
property previously associated with you at {property_address}.

Under California Code of Civil Procedure Section 1542 and Revenue and
Taxation Code Section 4675, these excess proceeds belong to you as the
former owner of record.

Everlight Ventures specializes in helping former property owners recover
these funds. Our service is provided at NO UPFRONT COST to you. We only
earn a fee if we successfully recover your money.

To begin the recovery process, please contact us:

    Phone:  {phone}
    Email:  {from_email}
    Web:    everlightventures.io

    IMPORTANT: The deadline to file a claim is {deadline}.

We look forward to helping you recover what is rightfully yours.

Sincerely,


Piper Reeves
Surplus Recovery Division
Everlight Ventures
"""


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

@dataclass
class OutreachContext:
    """Data needed to render any template."""
    owner_name: str
    county: str
    surplus_amount: float
    property_address: str
    deadline: str
    parcel_id: str = ""
    owner_address: str = ""
    phone: str = COMPANY_PHONE
    from_email: str = FROM_EMAIL
    date: str = ""

    def __post_init__(self):
        if not self.date:
            self.date = datetime.now(timezone.utc).strftime("%B %d, %Y")

    def to_dict(self) -> dict:
        return {
            "owner_name": self.owner_name,
            "county": self.county,
            "surplus_amount": self.surplus_amount,
            "property_address": self.property_address,
            "deadline": self.deadline,
            "parcel_id": self.parcel_id,
            "owner_address": self.owner_address,
            "phone": self.phone,
            "from_email": self.from_email,
            "date": self.date,
        }


def render_template(template: str, ctx: OutreachContext) -> str:
    """Render a template string with the outreach context."""
    return template.format(**ctx.to_dict())


def render_sms(ctx: OutreachContext, stage: str = "initial") -> str:
    """Render an SMS template for the given stage."""
    templates = {
        "initial": SMS_INITIAL,
        "follow_up_1": SMS_FOLLOW_UP_1,
        "follow_up_2": SMS_FOLLOW_UP_2,
        "signed": SMS_SIGNED_CONFIRMATION,
    }
    template = templates.get(stage, SMS_INITIAL)
    return render_template(template, ctx)


def render_email(ctx: OutreachContext, stage: str = "initial") -> dict:
    """Render email subject and body for the given stage. Returns dict with subject, body."""
    if stage == "initial":
        subject = EMAIL_SUBJECT
        body = EMAIL_BODY
    elif stage == "follow_up_1":
        subject = EMAIL_FOLLOW_UP_1_SUBJECT
        body = EMAIL_FOLLOW_UP_1_BODY
    elif stage == "follow_up_2":
        subject = EMAIL_FOLLOW_UP_2_SUBJECT
        body = EMAIL_FOLLOW_UP_2_BODY
    else:
        subject = EMAIL_SUBJECT
        body = EMAIL_BODY

    return {
        "subject": render_template(subject, ctx),
        "body": render_template(body, ctx),
    }


def render_voicemail(ctx: OutreachContext) -> str:
    """Render the voicemail drop script."""
    return render_template(VOICEMAIL_SCRIPT, ctx)


def render_letter(ctx: OutreachContext) -> str:
    """Render the direct mail letter."""
    return render_template(LETTER_TEMPLATE, ctx)


# ---------------------------------------------------------------------------
# Email delivery via Resend
# ---------------------------------------------------------------------------


def send_surplus_email(
    to_email: str,
    ctx: OutreachContext,
    stage: str = "initial",
) -> bool:
    """
    Send a surplus recovery email via Resend API.
    Returns True if sent successfully.
    """
    if not RESEND_API_KEY:
        logger.error("RESEND_API_KEY not set. Cannot send email.")
        return False

    if requests is None:
        logger.error("requests library not installed.")
        return False

    rendered = render_email(ctx, stage)

    # Convert plain text body to simple HTML
    html_body = rendered["body"].replace("\n", "<br>\n")

    payload = {
        "from": f"{FROM_NAME} <{FROM_EMAIL}>",
        "to": [to_email],
        "subject": rendered["subject"],
        "html": html_body,
        "text": rendered["body"],
    }

    try:
        resp = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=15,
        )

        if resp.status_code in (200, 201):
            result = resp.json()
            logger.info("Email sent to %s (ID: %s)", to_email, result.get("id", "unknown"))
            _log_outreach("email", to_email, ctx, stage, success=True)
            return True
        else:
            logger.error("Resend API error %d: %s", resp.status_code, resp.text[:200])
            _log_outreach("email", to_email, ctx, stage, success=False, error=resp.text[:200])
            return False

    except Exception as e:
        logger.error("Failed to send email to %s: %s", to_email, e)
        _log_outreach("email", to_email, ctx, stage, success=False, error=str(e))
        return False


# ---------------------------------------------------------------------------
# Outreach logging
# ---------------------------------------------------------------------------


def _log_outreach(
    channel: str,
    recipient: str,
    ctx: OutreachContext,
    stage: str,
    success: bool = True,
    error: str = "",
) -> None:
    """Log outreach attempt to JSON file for tracking."""
    entry = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "channel": channel,
        "recipient": recipient,
        "owner_name": ctx.owner_name,
        "parcel_id": ctx.parcel_id,
        "county": ctx.county,
        "surplus_amount": ctx.surplus_amount,
        "stage": stage,
        "success": success,
        "error": error,
    }

    try:
        if OUTREACH_LOG.exists():
            with open(OUTREACH_LOG, "r") as f:
                log_data = json.load(f)
        else:
            log_data = {"outreach_log": []}

        log_data["outreach_log"].append(entry)

        with open(OUTREACH_LOG, "w") as f:
            json.dump(log_data, f, indent=2)
    except Exception as e:
        logger.error("Failed to write outreach log: %s", e)


# ---------------------------------------------------------------------------
# Bulk outreach
# ---------------------------------------------------------------------------


def run_outreach_for_leads(leads_file: str, stage: str = "initial", channel: str = "email") -> dict:
    """
    Run outreach for all leads in a surplus_leads.json file.

    Args:
        leads_file: Path to surplus_leads.json
        stage: Outreach stage (initial, follow_up_1, follow_up_2)
        channel: Channel to use (email, sms, letter)

    Returns:
        Summary dict with sent/failed counts.
    """
    with open(leads_file, "r") as f:
        data = json.load(f)

    leads = data.get("leads", [])
    sent = 0
    failed = 0
    skipped = 0

    for lead in leads:
        # Skip leads that are not in actionable status
        if lead.get("status") not in ("new", "contacted"):
            skipped += 1
            continue

        ctx = OutreachContext(
            owner_name=lead.get("former_owner", "Property Owner"),
            county=lead.get("county", ""),
            surplus_amount=lead.get("surplus_amount", 0),
            property_address=lead.get("property_address", "your former property"),
            deadline=lead.get("deadline", ""),
            parcel_id=lead.get("parcel_id", ""),
            owner_address=lead.get("owner_last_address", ""),
        )

        if channel == "email":
            emails = lead.get("owner_email", [])
            if not emails:
                logger.info("No email for %s. Skipping.", lead.get("former_owner"))
                skipped += 1
                continue
            success = send_surplus_email(emails[0], ctx, stage)
            if success:
                sent += 1
            else:
                failed += 1

        elif channel == "sms":
            sms_text = render_sms(ctx, stage)
            phones = lead.get("owner_phone", [])
            if not phones:
                skipped += 1
                continue
            # SMS sending would integrate with Twilio or similar
            logger.info("SMS ready for %s at %s: %s", lead.get("former_owner"), phones[0], sms_text[:80])
            _log_outreach("sms", phones[0], ctx, stage, success=True)
            sent += 1

        elif channel == "letter":
            letter_text = render_letter(ctx)
            logger.info("Letter generated for %s (%d chars)", lead.get("former_owner"), len(letter_text))
            # Save letter to outreach directory
            letter_dir = BASE_DIR / "outreach" / "surplus_letters"
            letter_dir.mkdir(parents=True, exist_ok=True)
            safe_name = re.sub(r'[^\w\-]', '_', lead.get("parcel_id", "unknown"))
            letter_path = letter_dir / f"letter_{safe_name}_{stage}.txt"
            with open(letter_path, "w") as f:
                f.write(letter_text)
            _log_outreach("letter", lead.get("owner_last_address", ""), ctx, stage, success=True)
            sent += 1

    summary = {
        "channel": channel,
        "stage": stage,
        "sent": sent,
        "failed": failed,
        "skipped": skipped,
        "total": len(leads),
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    logger.info("Outreach complete: %d sent, %d failed, %d skipped out of %d", sent, failed, skipped, len(leads))
    return summary


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    parser = argparse.ArgumentParser(description="Surplus Funds Outreach Engine")
    parser.add_argument("--leads-file", default=str(BASE_DIR / "surplus_leads.json"), help="Path to leads JSON")
    parser.add_argument("--stage", default="initial", choices=["initial", "follow_up_1", "follow_up_2"])
    parser.add_argument("--channel", default="email", choices=["email", "sms", "letter"])
    parser.add_argument("--preview", action="store_true", help="Preview templates without sending")
    args = parser.parse_args()

    if args.preview:
        sample = OutreachContext(
            owner_name="John Smith",
            county="Los Angeles",
            surplus_amount=15234.56,
            property_address="123 Main St, Los Angeles, CA 90001",
            deadline="2026-05-24",
            parcel_id="1234-567-890",
            owner_address="456 Oak Ave, Pasadena, CA 91101",
        )
        print("=== SMS ===")
        print(render_sms(sample, args.stage))
        print("\n=== EMAIL ===")
        email = render_email(sample, args.stage)
        print(f"Subject: {email['subject']}")
        print(email["body"])
        print("\n=== VOICEMAIL ===")
        print(render_voicemail(sample))
        print("\n=== LETTER ===")
        print(render_letter(sample))
    else:
        run_outreach_for_leads(args.leads_file, args.stage, args.channel)
