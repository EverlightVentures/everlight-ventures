#!/usr/bin/env python3
"""
Piper Reeves -- Personalized Outreach Engine v2
================================================
Every email is unique. Every email has market data charts.
Piper has PERMISSION TO SEND (not just draft) as of 2026-03-30.

Uses:
- piper_unique_engine.py for AI-driven uniqueness (the "date test")
- piper_market_data.py for county-level housing/demographic stats
- piper_chart_engine.py for inline chart generation
- Resend API for delivery from piper@everlightventures.io

The Date Test: If three sellers compared Piper's emails,
each would hear a completely different story.
"""
from __future__ import annotations

import json
import os
import random
import requests
from datetime import datetime, timezone
from pathlib import Path

# Import the new engines
from piper_market_data import get_market_data, get_holding_cost_breakdown, get_seller_motivation_stats
from piper_chart_engine import generate_email_charts
from piper_unique_engine import generate_unique_email, generate_unique_subject, generate_followup_email

RESEND_KEY = os.environ.get("RESEND_API_KEY", "re_6S6DgX94_BDzaAU3r3Y5Syca6F58m2aEt")
SLACK_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
LOG_DIR = Path(__file__).parent / "outreach_sent"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Opted-out emails (CAN-SPAM compliance)
OPTOUT_FILE = Path(__file__).parent / "opted_out_emails.json"

# CAN-SPAM footer
CANSPAM_FOOTER = """
<div style="margin-top:30px;padding-top:15px;border-top:1px solid #333;font-size:11px;color:#888;font-family:Arial,sans-serif;">
  <p>Everlight Logistics LLC | Sacramento, CA</p>
  <p>You received this because your property appeared in public records.
  <a href="mailto:unsubscribe@everlightventures.io?subject=Unsubscribe&body=Please remove me from future emails." style="color:#D4AF37;">Unsubscribe</a></p>
</div>
"""


def _is_opted_out(email: str) -> bool:
    """Check if this email has opted out."""
    if not OPTOUT_FILE.exists():
        return False
    try:
        opted = json.loads(OPTOUT_FILE.read_text())
        return email.lower() in [e.lower() for e in opted]
    except Exception:
        return False


def _log_sent(to_email: str, owner_name: str, subject: str, lead_type: str, style: dict):
    """Log sent email for tracking."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
    log = {
        "to": to_email,
        "owner": owner_name,
        "subject": subject,
        "lead_type": lead_type,
        "style": style,
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "agent": "Piper Reeves",
    }
    log_file = LOG_DIR / f"{ts}_{owner_name.replace(' ', '_')[:20]}.json"
    log_file.write_text(json.dumps(log, indent=2))


def _slack_notify(message: str):
    """Post to Slack about sent email."""
    if not SLACK_TOKEN:
        return
    try:
        requests.post(
            "https://slack.com/api/chat.postMessage",
            headers={"Authorization": f"Bearer {SLACK_TOKEN}", "Content-Type": "application/json"},
            json={"channel": "C08N1KV3WMW", "text": message},  # hive-alerts
            timeout=5,
        )
    except Exception:
        pass


def build_full_html_email(body_html: str, charts_html: str = "", include_charts: bool = True) -> str:
    """Assemble the complete HTML email with branding, charts, and CAN-SPAM footer."""
    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#f5f5f5;font-family:Georgia,serif;">
  <div style="max-width:620px;margin:0 auto;background:#ffffff;padding:30px 25px;border-radius:8px;">
    <!-- Personal message -->
    <div style="color:#333;font-size:15px;line-height:1.7;">
      {body_html}
    </div>
"""
    if include_charts and charts_html:
        html += f"""
    <!-- Market data section -->
    <div style="margin-top:25px;">
      <p style="color:#666;font-size:13px;font-style:italic;">
        I put together some quick numbers on your area -- thought you might find this interesting:
      </p>
      {charts_html}
    </div>
"""
    html += f"""
    {CANSPAM_FOOTER}
  </div>
</body>
</html>"""
    return html


def send_piper_email(
    to_email: str,
    owner_name: str,
    address: str,
    city: str,
    state: str,
    lead_type: str,
    arv: int = 0,
    county: str = "",
    notes: str = "",
    include_charts: bool = True,
    dry_run: bool = False,
) -> tuple[bool, str]:
    """Send a unique, personalized Piper email with market data charts.

    Args:
        to_email: Recipient email
        owner_name: Property owner name
        address: Property address
        city: City
        state: State code (2-letter)
        lead_type: One of: pre_foreclosure, tax_delinquent, expired_listing, etc.
        arv: After-repair value estimate
        county: County name (optional, will be inferred)
        notes: Additional context about the lead
        include_charts: Include market data charts (True for first touch)
        dry_run: If True, don't actually send -- return the HTML

    Returns:
        (success: bool, message_id_or_error: str)
    """
    # CAN-SPAM check
    if _is_opted_out(to_email):
        return False, "opted_out"

    # Get market data
    market_data = get_market_data(city, state, county)
    holding_data = get_holding_cost_breakdown(arv or market_data.get("median_home_price", 300000), state)

    # Generate unique email body
    email = generate_unique_email(
        owner_name=owner_name,
        address=address,
        city=city,
        state=state,
        lead_type=lead_type,
        market_data=market_data,
        holding_data=holding_data,
        arv=arv,
        notes=notes,
    )

    # Generate charts (first touch only)
    charts_html = ""
    if include_charts:
        try:
            charts_html = generate_email_charts(market_data, holding_data, include_satisfaction=True)
        except Exception as e:
            charts_html = ""  # Send without charts if generation fails

    # Assemble full HTML
    full_html = build_full_html_email(email["body_html"], charts_html, include_charts)

    if dry_run:
        return True, full_html

    # Send via Resend
    try:
        r = requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {RESEND_KEY}", "Content-Type": "application/json"},
            json={
                "from": "Piper Reeves <piper@everlightventures.io>",
                "to": [to_email],
                "subject": email["subject"],
                "html": full_html,
                "reply_to": "piper@everlightventures.io",
                "tags": [
                    {"name": "lead_type", "value": lead_type},
                    {"name": "city", "value": city},
                    {"name": "agent", "value": "piper"},
                ],
            },
            timeout=15,
        )

        if r.status_code in (200, 201):
            msg_id = r.json().get("id", "")
            _log_sent(to_email, owner_name, email["subject"], lead_type, email["style"])
            _slack_notify(
                f"Piper sent email to {owner_name} ({city}, {state}) "
                f"| Style: {email['style']['tone']} / {email['style']['opening']} "
                f"| Subject: {email['subject']}"
            )
            return True, msg_id
        else:
            error = r.text[:200]
            return False, f"HTTP {r.status_code}: {error}"

    except Exception as e:
        return False, str(e)


def send_piper_followup(
    to_email: str,
    owner_name: str,
    address: str,
    city: str,
    state: str,
    lead_type: str,
    touch_number: int,
    previous_subject: str = "",
    dry_run: bool = False,
) -> tuple[bool, str]:
    """Send a follow-up email (no charts on follow-ups)."""
    if _is_opted_out(to_email):
        return False, "opted_out"

    email = generate_followup_email(
        owner_name=owner_name,
        address=address,
        city=city,
        state=state,
        lead_type=lead_type,
        touch_number=touch_number,
        previous_subject=previous_subject,
    )

    full_html = build_full_html_email(email["body_html"], charts_html="", include_charts=False)

    if dry_run:
        return True, full_html

    try:
        r = requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {RESEND_KEY}", "Content-Type": "application/json"},
            json={
                "from": "Piper Reeves <piper@everlightventures.io>",
                "to": [to_email],
                "subject": email["subject"],
                "html": full_html,
                "reply_to": "piper@everlightventures.io",
                "tags": [
                    {"name": "lead_type", "value": lead_type},
                    {"name": "touch", "value": str(touch_number)},
                    {"name": "agent", "value": "piper"},
                ],
            },
            timeout=15,
        )

        if r.status_code in (200, 201):
            msg_id = r.json().get("id", "")
            _log_sent(to_email, owner_name, email["subject"], lead_type, {"touch": touch_number})
            return True, msg_id
        else:
            return False, f"HTTP {r.status_code}: {r.text[:200]}"

    except Exception as e:
        return False, str(e)


def preview_outreach(lead: dict) -> str:
    """Preview what Piper would send to this lead (generates HTML, doesn't send)."""
    owner = lead.get("owner_name", "")
    addr = lead.get("address", "")
    city = lead.get("city", "")
    state = lead.get("state", "")
    ltype = lead.get("lead_type", "")
    arv = lead.get("estimated_arv", lead.get("arv", 0))

    success, html = send_piper_email(
        to_email="preview@example.com",
        owner_name=owner,
        address=addr,
        city=city,
        state=state,
        lead_type=ltype,
        arv=arv,
        dry_run=True,
    )
    return html if success else "Failed to generate preview"


if __name__ == "__main__":
    # Preview 3 different emails to show uniqueness
    examples = [
        {"owner_name": "DONNA T BROOKS", "address": "1522 HOGAN ST, SAINT LOUIS, MO 63106", "city": "St Louis", "state": "MO", "lead_type": "high_equity", "arv": 101062},
        {"owner_name": "ERICA KAUFFMAN LANCASTER", "address": "27 ATLANTA AVE SE, ATLANTA, GA 30315", "city": "Atlanta", "state": "GA", "lead_type": "expired_listing", "arv": 578200},
        {"owner_name": "KARL JOHNSON", "address": "003-33-082, CLEVELAND, OH", "city": "Cleveland", "state": "OH", "lead_type": "tax_delinquent", "arv": 0},
    ]

    for i, ex in enumerate(examples):
        print(f"\n{'='*60}")
        print(f"PREVIEW #{i+1}: {ex['owner_name']} | {ex['lead_type']} | {ex['city']}")
        print(f"{'='*60}")
        html = preview_outreach(ex)
        # Save preview
        out = Path(f"preview_{i+1}.html")
        out.write_text(html)
        print(f"Saved to {out} ({len(html):,} chars)")
