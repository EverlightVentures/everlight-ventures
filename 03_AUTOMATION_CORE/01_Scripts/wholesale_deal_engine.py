#!/usr/bin/env python3
"""Wholesale Deal Engine - Fully Autonomous Pipeline.

Runs every hour on Oracle. Checks every lead and fires the next action:

  New + hot (70+) + has email -> Piper sends outreach
  Contacted + positive reply -> Harrison sends offer
  Negotiating + verbal yes -> Generate contract, send to seller
  Under contract + seller signed -> Send deal to matched buyer
  Assigned + buyer accepted -> Engage title company
  Closing + title confirms -> Log commission, mark closed

Every action creates a styled HTML report and posts the specific link to Slack.
You just check your bank.

Usage:
    python3 wholesale_deal_engine.py           # process all leads
    python3 wholesale_deal_engine.py --dry-run # preview actions
"""
from __future__ import annotations

import json
import os
import random
import smtplib
import sys
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

# Django setup
for _djp in [
    "/mnt/sdcard/AA_MY_DRIVE/09_DASHBOARD/hive_dashboard",
    "/home/opc/hive_django",
]:
    if os.path.isdir(_djp) and _djp not in sys.path:
        sys.path.insert(0, _djp)
        break
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hive_dashboard.settings")

import django
django.setup()

from django.utils import timezone as tz
from broker_ops.models import PropertyLead, InvestorBuyer, Deal, ClientFile, ClientDocument
from broker_ops.wholesale import score_property, match_property_to_buyers

# Workbook + GDocs bridge
for _p in [
    "/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Broker_OS/wholesale_agent",
    "/home/opc/wholesale_agent",
]:
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

try:
    from gdocs_bridge import publish_report
except ImportError:
    publish_report = None

try:
    from workbook_logger import wb
except ImportError:
    wb = None

# Load env
for env_path in [
    "/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/03_Credentials/.env",
    "/home/opc/.env",
]:
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    k, v = line.strip().split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())
        break

SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.resend.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "465"))
SMTP_USER = os.environ.get("SMTP_USER", "resend")
SMTP_PASS = os.environ.get("SMTP_PASS", os.environ.get("RESEND_API_KEY", ""))
DRY_RUN = "--dry-run" in sys.argv

DAILY_EMAIL_LIMIT = 20
_emails_sent_today = 0


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def send_email(from_name, from_email, to_email, subject, body_text, body_html=None):
    """Send an email via Resend SMTP. Returns True on success."""
    global _emails_sent_today
    if _emails_sent_today >= DAILY_EMAIL_LIMIT:
        log(f"  SKIP: daily limit ({DAILY_EMAIL_LIMIT}) reached")
        return False
    if DRY_RUN:
        log(f"  [DRY] Would send to {to_email}: {subject}")
        return True
    if not SMTP_PASS:
        log("  ERROR: no SMTP credentials")
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = f"{from_name} <{from_email}>"
        msg["To"] = to_email
        msg["Reply-To"] = from_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body_text, "plain"))
        if body_html:
            msg.attach(MIMEText(body_html, "html"))
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(from_email, [to_email], msg.as_string())
        _emails_sent_today += 1
        return True
    except Exception as e:
        log(f"  SEND FAILED: {e}")
        return False


def post_action(title, content, agent, folder="01_Broker_OS/Outreach_Logs"):
    """Create styled report + post link to Slack."""
    if publish_report:
        try:
            publish_report(
                title=title, content=content, agent=agent,
                folder=folder, slack_channel="#wholesale-deals", app="warroom",
                summary=content[:150],
            )
        except Exception as e:
            log(f"  WARN: post_action failed: {e}")


# ============================================================================
# STAGE HANDLERS
# ============================================================================

def handle_new_leads():
    """Stage 1: Piper auto-outreaches new hot leads with email."""
    leads = PropertyLead.objects.filter(
        status="new",
        motivation_score__gte=70,
    ).exclude(owner_email="").exclude(owner_email__isnull=True).exclude(
        notes__contains="[PIPER_OUTREACH]"
    ).order_by("-motivation_score")[:10]

    count = 0
    for lead in leads:
        log(f"PIPER -> {lead.owner_email} ({lead.address[:30]}, score={lead.motivation_score})")

        hooks = [
            f"I came across your property on {lead.address.split(',')[0]} while researching {lead.city}, and wanted to reach out personally.",
            f"I've been working with homeowners in {lead.city} who are looking for simple, no-hassle solutions.",
            f"A colleague flagged your property at {lead.address.split(',')[0]} and I thought the timing might work.",
        ]
        lead_context = {
            "pre_foreclosure": "I understand there may be some financial pressure on the property, and I want you to know there are options.",
            "tax_lien": "Tax situations can be stressful -- y'all shouldn't have to lose a property over back taxes.",
            "probate": "I know dealing with an inherited property on top of everything else can feel overwhelming.",
            "absentee": "Managing a property from a distance is no small thing. A lot of folks I work with just want a clean transaction.",
            "divorce": "I completely understand this is a difficult time. My goal is to make the property side stress-free.",
            "code_violation": "Code violations pile up fast. Our buyers take properties as-is -- no repairs needed on your end.",
            "vacant": "Vacant properties become a headache with maintenance, taxes, and liability. I'd love to take that off your plate.",
            "expired_listing": "I noticed your listing didn't work out on the MLS. Our approach is different -- direct, fast, no commissions.",
        }
        context_line = lead_context.get(lead.lead_type, "I'd love to chat about your property and see if we might be a good fit.")
        owner_first = lead.owner_name.split()[0] if lead.owner_name else "there"

        body = f"""Hi {owner_first},

{random.choice(hooks)}

{context_line}

We work with cash buyers who can close quickly -- usually 10 to 14 days -- and we handle all the paperwork and closing costs. No repairs, no showings, no agent fees.

If you'd be open to a quick conversation, I'd love to hear from you. No pressure at all.

Best,
Piper Reeves
Outreach Specialist | Everlight Ventures
piper@everlightventures.io | everlightventures.io"""

        subject = random.choice([
            f"Quick question about {lead.address.split(',')[0]}",
            f"Reaching out about your {lead.city} property",
            f"Cash offer for your property -- no obligation",
        ])

        if send_email("Piper Reeves", "piper@everlightventures.io", lead.owner_email, subject, body):
            lead.status = "contacted"
            lead.notes = (lead.notes or "") + f"\n[PIPER_OUTREACH] {tz.now().strftime('%Y-%m-%d %H:%M')} | {subject}"
            lead.save(update_fields=["status", "notes", "updated_at"])
            count += 1

            post_action(
                f"Piper Outreach -- {lead.city}, {lead.state}",
                f"**To:** {lead.owner_email}\n**Subject:** {subject}\n**Property:** {lead.address}\n**Score:** {lead.motivation_score}\n\n---\n\n{body}",
                agent="piper_reeves",
            )
            if wb:
                wb.log_email_sent(lead_id=str(lead.id), to_email=lead.owner_email, subject=subject, sender_persona="piper")

    log(f"Piper sent {count} outreach emails")
    return count


def handle_positive_replies():
    """Stage 2: Harrison auto-responds to positive seller replies."""
    leads = PropertyLead.objects.filter(
        status="contacted",
        notes__contains="[REPLY_POSITIVE]",
    ).exclude(notes__contains="[HARRISON_FOLLOWUP]")[:5]

    count = 0
    for lead in leads:
        log(f"HARRISON -> {lead.owner_email} (positive reply, sending offer)")
        owner_first = lead.owner_name.split()[0] if lead.owner_name else "there"
        arv = lead.estimated_arv or 0
        mao = lead.max_offer or (arv * 0.7 - (lead.estimated_repair or 0) - (lead.assignment_fee or 10000))

        body = f"""Hi {owner_first},

Great to hear back from you. I appreciate you taking the time.

I've reviewed your property at {lead.address} and here's where we're at:

Based on comparable sales in {lead.city} and the current condition, we can offer ${int(mao):,} cash, closing in as little as 10 days. We cover all closing costs.

Here's what happens next if you're interested:
1. We send you a simple purchase agreement (no obligation)
2. You review it -- take your time
3. If it works, we open escrow and close on your timeline

No pressure. If the number doesn't work, no hard feelings. But I wanted to put a real offer on the table so you know exactly where we stand.

Looking forward to hearing from you.

Harrison Knox
Deal Closer | Everlight Ventures
hammer@everlightventures.io"""

        subject = f"Your property at {lead.address.split(',')[0]} -- here's our offer"

        if send_email("Harrison Knox", "hammer@everlightventures.io", lead.owner_email, subject, body):
            lead.status = "negotiating"
            lead.notes = (lead.notes or "") + f"\n[HARRISON_FOLLOWUP] {tz.now().strftime('%Y-%m-%d %H:%M')} | Offer: ${int(mao):,}"
            lead.save(update_fields=["status", "notes", "updated_at"])
            count += 1

            post_action(
                f"Harrison Offer -- {lead.city}, {lead.state}",
                f"**To:** {lead.owner_email}\n**Offer:** ${int(mao):,}\n**Property:** {lead.address}\n\n---\n\n{body}",
                agent="harrison_knox",
                folder="01_Broker_OS/Deal_Pipeline",
            )

    log(f"Harrison sent {count} offer follow-ups")
    return count


def handle_contracts():
    """Stage 3: Auto-generate contract when negotiating leads say yes."""
    leads = PropertyLead.objects.filter(
        status="negotiating",
        notes__contains="[SELLER_VERBAL_YES]",
    ).exclude(notes__contains="[CONTRACT_SENT]")[:3]

    count = 0
    for lead in leads:
        log(f"CONTRACT -> {lead.owner_email} (generating assignment contract)")

        # Create client file if not exists
        cf, created = ClientFile.objects.get_or_create(
            property_lead=lead,
            defaults={
                "property_address": lead.address,
                "city": lead.city,
                "state": lead.state,
                "status": "active",
            }
        )

        # Generate contract using client_files.py
        try:
            from broker_ops.client_files import generate_assignment_contract
            doc = generate_assignment_contract(cf)
            log(f"  Contract generated: {doc.doc_type}")

            # Send contract to seller
            if lead.owner_email:
                body = f"""Hi {lead.owner_name.split()[0] if lead.owner_name else 'there'},

As discussed, I've attached the purchase agreement for your property at {lead.address}.

Please review it carefully. Key points:
- Purchase price: ${int(lead.max_offer or 0):,}
- Closing timeline: 10-14 days
- We cover all closing costs
- Standard inspection period per your state's requirements

If everything looks good, please sign and return. If you have any questions at all, don't hesitate to reach out.

Harrison Knox
Deal Closer | Everlight Ventures
hammer@everlightventures.io"""

                subject = f"Purchase Agreement -- {lead.address.split(',')[0]}"
                if send_email("Harrison Knox", "hammer@everlightventures.io", lead.owner_email, subject, body):
                    lead.notes = (lead.notes or "") + f"\n[CONTRACT_SENT] {tz.now().strftime('%Y-%m-%d %H:%M')}"
                    lead.save(update_fields=["notes", "updated_at"])
                    count += 1

                    post_action(
                        f"Contract Sent -- {lead.city}, {lead.state}",
                        f"**To:** {lead.owner_email}\n**Property:** {lead.address}\n**Price:** ${int(lead.max_offer or 0):,}\n\n---\n\n{body}",
                        agent="harrison_knox",
                        folder="01_Broker_OS/Deal_Pipeline",
                    )
        except Exception as e:
            log(f"  Contract generation failed: {e}")

    log(f"Contracts sent: {count}")
    return count


def handle_buyer_assignment():
    """Stage 4: After seller signs, send deal to top-matched buyer."""
    leads = PropertyLead.objects.filter(
        status="under_contract",
    ).exclude(notes__contains="[BUYER_PITCH_SENT]")[:3]

    count = 0
    for lead in leads:
        # Find best buyer match
        matches = match_property_to_buyers(lead)
        if not matches:
            log(f"  No buyer matches for {lead.address[:30]}")
            continue

        buyer = matches[0]
        log(f"ADRIAN -> {buyer.email} (pitching deal: {lead.address[:30]})")

        arv = lead.estimated_arv or 0
        buyer_price = (lead.max_offer or 0) + (lead.assignment_fee or 10000)
        profit_est = arv - buyer_price - (lead.estimated_repair or 0)

        body = f"""Hi {buyer.contact_name or buyer.company_name},

I have an exclusive deal that matches your buy criteria in {lead.city}, {lead.state}.

Property: {lead.address}
Type: {lead.get_property_type_display()}
Beds/Baths: {lead.bedrooms}/{lead.bathrooms}
Sqft: {lead.sqft:,}

The Numbers:
- Your purchase price: ${int(buyer_price):,}
- Estimated ARV: ${int(arv):,}
- Estimated repairs: ${int(lead.estimated_repair or 0):,}
- Projected profit: ${int(profit_est):,}
- ROI: {int(profit_est / buyer_price * 100) if buyer_price > 0 else 0}%

This property is under contract and ready for assignment. We can close in as little as 10 days.

If you'd like to move forward, I can send the assignment agreement today.

Best regards,
Adrian Morgan
Investment Analyst | Everlight Ventures
ace@everlightventures.io"""

        subject = f"Exclusive Deal: {lead.city}, {lead.state} -- ${int(buyer_price):,}"

        if send_email("Adrian Morgan", "ace@everlightventures.io", buyer.email, subject, body):
            lead.notes = (lead.notes or "") + f"\n[BUYER_PITCH_SENT] {tz.now().strftime('%Y-%m-%d %H:%M')} | Buyer: {buyer.company_name}"
            lead.save(update_fields=["notes", "updated_at"])
            count += 1

            post_action(
                f"Buyer Pitch -- {lead.city}, {lead.state}",
                f"**To:** {buyer.email} ({buyer.company_name})\n**Property:** {lead.address}\n**Buyer Price:** ${int(buyer_price):,}\n**Projected Profit:** ${int(profit_est):,}\n\n---\n\n{body}",
                agent="adrian_morgan",
                folder="01_Broker_OS/Deal_Pipeline",
            )

    log(f"Buyer pitches sent: {count}")
    return count


def handle_title_engagement():
    """Stage 5: After buyer accepts, engage title company."""
    leads = PropertyLead.objects.filter(
        status="assigned",
    ).exclude(notes__contains="[TITLE_ENGAGED]")[:3]

    count = 0
    for lead in leads:
        # Find title company for the state
        title_cos = []
        try:
            tc_path = Path("/home/opc/wholesale_agent/title_companies.json")
            if not tc_path.exists():
                tc_path = Path("/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Broker_OS/wholesale_agent/title_companies.json")
            if tc_path.exists():
                title_cos = json.loads(tc_path.read_text())
        except Exception as e:
            log(f"  WARN: failed to load title companies: {e}")

        # Find a company that serves this state
        tc = None
        for co in title_cos:
            if isinstance(co, dict) and lead.state.upper() in str(co.get("states", co.get("state", ""))).upper():
                tc = co
                break
        if not tc and title_cos:
            tc = title_cos[0]  # fallback to first

        if not tc:
            log(f"  No title company found for {lead.state}")
            continue

        tc_email = tc.get("email", "")
        tc_name = tc.get("name", tc.get("company", "Title Company"))
        if not tc_email:
            continue

        log(f"TITLE -> {tc_email} (engaging for {lead.address[:30]})")

        body = f"""Dear {tc_name},

We are reaching out to engage your services for the closing of the following property assignment:

Property: {lead.address}, {lead.city}, {lead.state} {lead.zip_code}
Seller: {lead.owner_name}
Purchase Price: ${int(lead.max_offer or 0):,}
Assignment Fee: ${int(lead.assignment_fee or 10000):,}
Buyer Price: ${int((lead.max_offer or 0) + (lead.assignment_fee or 10000)):,}

We anticipate closing within 10-14 business days. Please confirm your availability and provide wire instructions for the earnest money deposit.

We will forward all executed contracts and buyer information upon confirmation.

Regards,
Harrison Knox
Deal Closer | Everlight Ventures
hammer@everlightventures.io
(916) 555-0100"""

        subject = f"Closing Request: {lead.address.split(',')[0]}, {lead.city} {lead.state}"

        if send_email("Harrison Knox", "hammer@everlightventures.io", tc_email, subject, body):
            lead.notes = (lead.notes or "") + f"\n[TITLE_ENGAGED] {tz.now().strftime('%Y-%m-%d %H:%M')} | {tc_name}"
            lead.status = "assigned"  # stays assigned until close
            lead.save(update_fields=["status", "notes", "updated_at"])
            count += 1

            post_action(
                f"Title Company Engaged -- {lead.city}, {lead.state}",
                f"**Title Co:** {tc_name} ({tc_email})\n**Property:** {lead.address}\n**Purchase:** ${int(lead.max_offer or 0):,}\n**Assignment Fee:** ${int(lead.assignment_fee or 10000):,}\n\n---\n\n{body}",
                agent="harrison_knox",
                folder="01_Broker_OS/Deal_Pipeline",
            )

    log(f"Title companies engaged: {count}")
    return count


def handle_closings():
    """Stage 6: Detect closed deals, log commission."""
    from django.db.models import Q
    leads = PropertyLead.objects.filter(
        Q(status="assigned") &
        Q(notes__contains="[TITLE_ENGAGED]") &
        Q(notes__contains="[CLOSING_CONFIRMED]")
    ).exclude(notes__contains="[COMMISSION_LOGGED]")[:3]

    count = 0
    for lead in leads:
        fee = lead.assignment_fee or 10000
        log(f"CLOSED -> {lead.address[:30]} | Commission: ${int(fee):,}")

        lead.status = "closed"
        lead.notes = (lead.notes or "") + f"\n[COMMISSION_LOGGED] {tz.now().strftime('%Y-%m-%d %H:%M')} | ${int(fee):,}"
        lead.save(update_fields=["status", "notes", "updated_at"])
        count += 1

        post_action(
            f"DEAL CLOSED -- {lead.city}, {lead.state}",
            f"**Property:** {lead.address}\n**Assignment Fee:** ${int(fee):,}\n**Status:** CLOSED AND PAID\n\nCommission logged to immutable ledger.",
            agent="carlos_moreno",
            folder="01_Broker_OS/Deal_Pipeline",
        )

        if wb:
            wb.log_commission(str(lead.id), float(fee), commission_type="earned")
            wb.flush()

    log(f"Deals closed: {count}")
    return count


# ============================================================================
# MAIN
# ============================================================================

def main():
    log("=" * 50)
    log("WHOLESALE DEAL ENGINE -- Autonomous Pipeline")
    log(f"Mode: {'DRY RUN' if DRY_RUN else 'LIVE'}")
    log("=" * 50)

    results = {}

    # Process each stage
    results["piper_outreach"] = handle_new_leads()
    results["harrison_offers"] = handle_positive_replies()
    results["contracts_sent"] = handle_contracts()
    results["buyer_pitches"] = handle_buyer_assignment()
    results["title_engaged"] = handle_title_engagement()
    results["deals_closed"] = handle_closings()

    total = sum(results.values())
    log(f"\nTotal actions: {total}")
    for k, v in results.items():
        if v > 0:
            log(f"  {k}: {v}")

    # Flush workbook
    if wb:
        wb.log_agent_task("deal_engine", "cycle", success=True, count=total)
        wb.snapshot_daily()
        wb.flush()
        wb.sync_to_supabase()

    log("Deal engine cycle complete.")


if __name__ == "__main__":
    main()
