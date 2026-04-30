#!/usr/bin/env python3
"""
Broker OS SDR -- Automated outreach for AI-scored BrokerMatch leads.

Queries high-quality pending matches from the Broker OS database, sends
personalized emails via Resend API, updates match status, creates
OutreachSequence records, and posts a summary to Slack.

Cron: 0 17 * * * cd /mnt/sdcard/AA_MY_DRIVE/09_DASHBOARD/hive_dashboard && python /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/broker_outreach_sdr.py

Requires:
  RESEND_API_KEY or SMTP_PASS  -- Resend API key
  SLACK_BOT_TOKEN              -- Slack posting (optional)
"""

import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta, timezone

# ---------------------------------------------------------------------------
# Django bootstrap -- must happen before any model imports
# Works on both phone (/mnt/sdcard/...) and Oracle (/home/opc/hive_django)
# ---------------------------------------------------------------------------
_DJANGO_PATHS = [
    "/mnt/sdcard/AA_MY_DRIVE/09_DASHBOARD/hive_dashboard",
    "/home/opc/hive_django",
]
for _dp in _DJANGO_PATHS:
    if os.path.isdir(_dp):
        DJANGO_PROJECT = _dp
        break
else:
    DJANGO_PROJECT = _DJANGO_PATHS[0]
sys.path.insert(0, DJANGO_PROJECT)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hive_dashboard.settings")

import django  # noqa: E402
django.setup()

from broker_ops.models import BrokerMatch, LeadProfile, OutreachSequence  # noqa: E402

# Wire LLM Gateway for AI-powered email personalization
try:
    for _nd in [
        os.path.join(os.path.dirname(__file__), "..", "..", "06_DEVELOPMENT", "everlight_os"),
        "/home/opc/06_DEVELOPMENT/everlight_os",
    ]:
        if os.path.isdir(_nd) and _nd not in sys.path:
            sys.path.insert(0, _nd)
    from neuromorphic.llm_gateway import ask as llm_ask
except ImportError:
    llm_ask = None

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="[BrokerSDR %(asctime)s] %(message)s",
    datefmt="%H:%M",
)
log = logging.getLogger("broker_outreach_sdr")

RESEND_KEY = os.environ.get("RESEND_API_KEY", os.environ.get("SMTP_PASS", ""))
FROM_EMAIL = os.environ.get("SMTP_FROM", "noreply@everlightventures.io")
REPLY_TO = "support@everlightventures.io"
SLACK_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
SLACK_CHANNEL = os.environ.get("BROKER_SLACK_CHANNEL", "C0ANLLV8JAC")  # #wholesale-deals

NOW = datetime.now(timezone.utc)
TODAY = NOW.strftime("%Y-%m-%d")

# Limits
FRESH_OUTREACH_LIMIT = 30       # Max first-touch emails per run
FOLLOWUP_LIMIT = 20             # Max follow-up emails per run
MIN_MATCH_SCORE = float(os.environ.get("BROKER_MIN_SCORE", "60"))  # Configurable threshold
FOLLOWUP_WAIT_DAYS = 5          # Days before follow-up
EMAIL_DELAY_SECONDS = 2         # Delay between sends to avoid spam flags


# ---------------------------------------------------------------------------
# Email sender (same pattern as rex_sdr.py)
# ---------------------------------------------------------------------------

SIGNATURE_HTML = """
<div style="margin-top:24px;padding-top:16px;border-top:1px solid #e0e0e0;font-family:Arial,Helvetica,sans-serif;font-size:13px;color:#555;">
  <table cellpadding="0" cellspacing="0" border="0">
    <tr>
      <td style="padding-right:16px;border-right:2px solid #d4a017;">
        <img src="https://everlightventures.io/favicon.ico" alt="EV" width="48" height="48" style="border-radius:8px;" />
      </td>
      <td style="padding-left:16px;">
        <div style="font-size:15px;font-weight:bold;color:#1a1a1a;">{name}</div>
        <div style="font-size:12px;color:#888;margin-bottom:4px;">{title}</div>
        <div style="font-size:12px;">
          <a href="https://everlightventures.io" style="color:#d4a017;text-decoration:none;">everlightventures.io</a>
          &nbsp;|&nbsp;
          <a href="mailto:{email}" style="color:#d4a017;text-decoration:none;">{email}</a>
        </div>
      </td>
    </tr>
  </table>
  <div style="margin-top:12px;font-size:11px;color:#999;">
    Everlight Ventures &mdash; AI-Powered Business Solutions<br/>
    To unsubscribe, <a href="mailto:noreply@everlightventures.io?subject=unsubscribe" style="color:#999;">click here</a>.
  </div>
</div>
"""


def _body_to_html(text: str, agent_name="Sage Holloway", agent_title="Business Development",
                  agent_email="sage@everlightventures.io") -> str:
    """Convert plain text to branded HTML email with signature."""
    paragraphs = "".join(
        f"<p style='margin:0 0 12px;font-family:Arial,Helvetica,sans-serif;font-size:14px;color:#333;line-height:1.5;'>{line}</p>"
        for line in text.strip().split("\n") if line.strip()
    )
    sig = SIGNATURE_HTML.format(name=agent_name, title=agent_title, email=agent_email)
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="margin:0;padding:20px;background:#fafafa;">
<div style="max-width:600px;margin:0 auto;background:#fff;padding:24px;border-radius:8px;">
{paragraphs}
{sig}
</div></body></html>"""


def send_email(to: str, subject: str, body: str, agent_name: str = "Sage Holloway",
               agent_title: str = "Business Development",
               agent_email: str = "sage@everlightventures.io") -> bool:
    """Send a single email via Resend API with HTML signature. Returns True on success."""
    if not RESEND_KEY:
        log.warning("No RESEND_API_KEY or SMTP_PASS set -- skipping send to %s", to)
        return False
    if not to:
        return False

    plain_footer = (
        f"\n\n---\n{agent_name} | {agent_title}\n"
        f"Everlight Ventures | everlightventures.io\n"
        f"{agent_email}\n\nTo unsubscribe, reply with 'unsubscribe'."
    )
    html = _body_to_html(body, agent_name, agent_title, agent_email)

    # Route every SDR send through the branded mailer so the gold template
    # wraps the inner HTML, the resend_guard blocks owner/internal addresses,
    # and the monthly budget gate paces the send against Resend quota.
    try:
        import sys as _sys
        for _p in ("/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/content_tools",
                   "/home/opc/content_tools"):
            if _p not in _sys.path:
                _sys.path.insert(0, _p)
        from branded_mailer import send_branded_email  # type: ignore
    except Exception as exc:
        log.error("branded_mailer unavailable, send aborted for %s: %s", to, exc)
        return False

    result = send_branded_email(
        to=to,
        subject=subject,
        content_html=html,
        title=subject,
        from_name=f"{agent_name} at Everlight",
        from_email=FROM_EMAIL,
        reply_to=agent_email,
        agent_name=agent_name,
        agent_title=agent_title,
        agent_email=agent_email,
        plain_text_fallback=body + plain_footer,
        budget_category="bulk",
    )
    if result.ok:
        return True
    log.error("branded_mailer send failed for %s: %s", to, result.error)
    return False


# ---------------------------------------------------------------------------
# Email templates
# ---------------------------------------------------------------------------

def _ai_personalize_subject(lead_name: str, need: str, offer_title: str) -> str:
    """Use LLM Gateway to generate a personalized subject line. Falls back to template."""
    if llm_ask is None:
        return ""
    try:
        prompt = (
            f"Write a short, personalized email subject line (under 60 chars) for a cold outreach.\n"
            f"Recipient: {lead_name}\n"
            f"Their need: {need[:200]}\n"
            f"Tool we're recommending: {offer_title}\n"
            f"Tone: professional, helpful, not salesy. No emojis. No ALL CAPS.\n"
            f"Return ONLY the subject line, nothing else."
        )
        result = llm_ask(prompt, model="fast", max_tokens=80, agent_name="piper_reeves")
        result = result.strip().strip('"').strip("'")
        if result and len(result) < 80:
            return result
    except Exception as e:
        log.debug("AI subject personalization failed: %s", e)
    return ""


def build_intro_email(lead, offer, match):
    """Build the first-touch personalized email for a broker match.
    Uses AI personalization for subject lines when LLM Gateway is available."""
    first_name = lead.name.split()[0] if lead.name else "there"
    pricing = format_pricing(offer)
    category_label = dict(offer.CATEGORY_CHOICES).get(offer.category, offer.category)

    # Try AI-personalized subject, fall back to template
    subject = _ai_personalize_subject(
        lead.name or "there",
        lead.need_description or "",
        offer.title,
    )
    if not subject:
        subject = f"Found a tool that fits: {offer.title}"

    body = (
        f"Hi {first_name},\n\n"
        f"I came across your profile and saw that you are looking for help with: "
        f"{lead.need_description[:300]}\n\n"
        f"I think {offer.title} could be a strong fit. It is a {category_label.lower()} "
        f"solution{pricing}.\n\n"
        f"Here is why it matched:\n"
        f"{match.match_reasoning[:500] if match.match_reasoning else 'Your stated needs align closely with what this tool does.'}\n\n"
    )

    if offer.seller_url:
        body += f"You can check it out here: {offer.seller_url}\n\n"

    body += (
        f"If you are interested, just reply to this email and I will make an introduction "
        f"to the team behind {offer.title}. No pressure -- I only connect people when it "
        f"is genuinely a good fit.\n\n"
        f"Rich\n"
        f"Everlight Ventures -- Tool Matching\n"
        f"support@everlightventures.io"
    )

    return subject, body


def build_followup_email(lead, offer, match):
    """Build a follow-up email for a match that was emailed but got no reply."""
    first_name = lead.name.split()[0] if lead.name else "there"

    subject = f"Quick follow-up -- {offer.title}"

    body = (
        f"Hi {first_name},\n\n"
        f"I reached out a few days ago about {offer.title} as a potential fit for "
        f"what you described:\n\n"
        f'"{lead.need_description[:200]}"\n\n'
        f"Just checking if you had a chance to look into it. If the timing is off or "
        f"you have already found a solution, no worries at all -- just let me know and "
        f"I will close the loop on my end.\n\n"
        f"If you are still looking, reply here and I will set up an intro.\n\n"
        f"Rich\n"
        f"Everlight Ventures -- Tool Matching\n"
        f"support@everlightventures.io"
    )

    return subject, body


def format_pricing(offer):
    """Format pricing into a readable string."""
    model_labels = {
        "one_time": "one-time",
        "monthly": "/mo",
        "annual": "/yr",
        "revenue_share": "revenue share",
    }
    suffix = model_labels.get(offer.pricing_model, "")

    price_min = float(offer.price_min)
    price_max = float(offer.price_max)

    if price_min > 0 and price_max > 0 and price_min != price_max:
        return f" priced at ${price_min:,.0f}-${price_max:,.0f}{suffix}"
    elif price_max > 0:
        return f" priced at ${price_max:,.0f}{suffix}"
    elif price_min > 0:
        return f" starting at ${price_min:,.0f}{suffix}"
    return ""


# ---------------------------------------------------------------------------
# Lead email audit
# ---------------------------------------------------------------------------

def auto_enrich_leads(max_leads: int = 30) -> int:
    """Attempt to enrich leads that have a website URL in their description but no email.
    Returns number of leads successfully enriched."""
    try:
        # Try multiple paths (phone vs Oracle)
        for bp in [os.path.join(os.path.dirname(__file__), "broker"), "/home/opc/broker"]:
            if os.path.isdir(bp) and bp not in sys.path:
                sys.path.insert(0, bp)
        from contact_enrichment import extract_email_from_text, _fetch_text
    except ImportError:
        log.warning("Could not import contact_enrichment -- skipping auto-enrich")
        return 0

    # Find leads with no email OR placeholder email that have descriptions to work with
    from django.db.models import Q
    leads_needing_email = LeadProfile.objects.filter(
        Q(email="") | Q(email__contains="@placeholder")
    ).exclude(need_description="")[:max_leads]

    enriched = 0
    for lead in leads_needing_email:
        desc = lead.need_description or ""
        # Extract website from description
        website = ""
        if "Website:" in desc:
            after_website = desc.split("Website:")[1].strip()
            # Take until next period-space or newline
            website = after_website.split(". ")[0].split("\n")[0].strip()
            if website in ("N/A", "None", ""):
                continue

        if not website:
            continue

        if not website.startswith("http"):
            website = f"https://{website}"

        # Try to extract email from website
        for suffix in ["", "/contact", "/about", "/contact-us"]:
            try:
                html = _fetch_text(website.rstrip("/") + suffix, timeout=8, max_bytes=20000)
                email = extract_email_from_text(html) if html else ""
                if email:
                    lead.email = email
                    lead.save(update_fields=["email", "updated_at"])
                    enriched += 1
                    log.info("AUTO-ENRICH: %s -> %s", lead.name, email)
                    break
            except Exception:
                continue

    return enriched


def audit_lead_emails():
    """Check how many LeadProfile records have REAL email addresses.
    Filters out @placeholder.io (fake) emails. AUTO-ENRICHES when coverage is low."""
    total = LeadProfile.objects.count()
    # Real emails: non-empty AND not placeholder
    with_email = LeadProfile.objects.exclude(email="").exclude(
        email__contains="@placeholder"
    ).count()
    without_email = total - with_email
    pct = (with_email / total * 100) if total else 0

    log.info("LEAD EMAIL AUDIT: %d total | %d with email (%.0f%%) | %d missing email",
             total, with_email, pct, without_email)

    if pct < 50 and without_email > 0:
        log.info(
            "REVENUE ACTION: Only %.0f%% email coverage (%d/%d). "
            "Auto-enriching leads with website scraping...",
            pct, with_email, total,
        )
        enriched = auto_enrich_leads(max_leads=30)
        if enriched > 0:
            with_email += enriched
            without_email -= enriched
            pct = (with_email / total * 100) if total else 0
            log.info("AUTO-ENRICH RESULT: +%d emails. New coverage: %d/%d (%.0f%%)",
                     enriched, with_email, total, pct)
        else:
            log.info("AUTO-ENRICH: No new emails found from website scraping.")

    return {"total": total, "with_email": with_email, "without_email": without_email}


# ---------------------------------------------------------------------------
# Fresh outreach: pending matches with score > threshold, or approved
# matches that were never actually emailed
# ---------------------------------------------------------------------------

def run_fresh_outreach():
    """
    Send first-touch emails for BrokerMatch objects that need outreach.

    Targets two groups:
    1. status="pending" with match_score > MIN_MATCH_SCORE
    2. status="approved" but outreach_sent_at is NULL (marked approved
       by the matching engine but never actually emailed)

    Limits to FRESH_OUTREACH_LIMIT per run.
    """
    log.info("=== FRESH OUTREACH ===")

    from django.db.models import Q

    matches = (
        BrokerMatch.objects
        .filter(
            Q(status="pending", match_score__gt=MIN_MATCH_SCORE)
            | Q(status="approved", outreach_sent_at__isnull=True, match_score__gt=MIN_MATCH_SCORE)
        )
        .select_related("lead", "offer")
        .order_by("-match_score")
    )

    log.info("Found %d matches eligible for outreach (score > %.0f)",
             matches.count(), MIN_MATCH_SCORE)

    sent = 0
    skipped_no_email = 0
    skipped_unsub = 0
    errors = 0

    for match in matches:
        if sent >= FRESH_OUTREACH_LIMIT:
            break

        lead = match.lead
        offer = match.offer

        # Skip leads without real email (blank or placeholder)
        if not lead.email or "@placeholder" in lead.email:
            skipped_no_email += 1
            continue

        # Skip unsubscribed leads
        if lead.unsubscribed:
            skipped_unsub += 1
            continue

        # Skip inactive offers
        if offer.status != "active":
            continue

        subject, body = build_intro_email(lead, offer, match)

        if send_email(lead.email, subject, body):
            # Update BrokerMatch
            match.status = "approved"
            match.outreach_sent_at = NOW
            match.outreach_channel = "email"
            match.outreach_template = "broker_intro_v1"
            match.save(update_fields=[
                "status", "outreach_sent_at", "outreach_channel",
                "outreach_template", "updated_at",
            ])

            # Create OutreachSequence record
            OutreachSequence.objects.update_or_create(
                match=match,
                step="buyer_intro",
                defaults={
                    "status": "sent",
                    "subject": subject,
                    "body": body,
                    "to_email": lead.email,
                    "scheduled_at": NOW,
                    "sent_at": NOW,
                },
            )

            # Update lead contact tracking
            lead.last_contacted = NOW
            lead.contact_count = (lead.contact_count or 0) + 1
            lead.save(update_fields=["last_contacted", "contact_count", "updated_at"])

            sent += 1
            log.info("Sent intro to %s (%s) for offer: %s [score: %.0f]",
                     lead.name, lead.email, offer.title[:40], match.match_score)
            time.sleep(EMAIL_DELAY_SECONDS)
        else:
            errors += 1

    log.info(
        "Fresh outreach complete: %d sent | %d skipped (no email) | "
        "%d skipped (unsubscribed) | %d errors",
        sent, skipped_no_email, skipped_unsub, errors,
    )
    return {
        "sent": sent,
        "skipped_no_email": skipped_no_email,
        "skipped_unsub": skipped_unsub,
        "errors": errors,
    }


# ---------------------------------------------------------------------------
# Follow-up: re-contact matches emailed 5+ days ago with no reply
# ---------------------------------------------------------------------------

def run_followups():
    """
    Send follow-up emails for matches that were emailed 5+ days ago
    and have not received a reply (still in "approved" status, not "converted").
    """
    log.info("=== FOLLOW-UPS ===")

    cutoff = NOW - timedelta(days=FOLLOWUP_WAIT_DAYS)

    # Find matches that were emailed but not replied/converted
    matches = (
        BrokerMatch.objects
        .filter(
            status="approved",
            outreach_sent_at__isnull=False,
            outreach_sent_at__lt=cutoff,
        )
        .select_related("lead", "offer")
        .order_by("-match_score")
    )

    sent = 0
    skipped = 0

    for match in matches:
        if sent >= FOLLOWUP_LIMIT:
            break

        lead = match.lead
        offer = match.offer

        if not lead.email or "@placeholder" in lead.email or lead.unsubscribed:
            skipped += 1
            continue

        # Check if we already sent a follow-up for this match
        already_followed_up = OutreachSequence.objects.filter(
            match=match, step="followup_1", status="sent"
        ).exists()
        if already_followed_up:
            continue

        subject, body = build_followup_email(lead, offer, match)

        if send_email(lead.email, subject, body):
            OutreachSequence.objects.update_or_create(
                match=match,
                step="followup_1",
                defaults={
                    "status": "sent",
                    "subject": subject,
                    "body": body,
                    "to_email": lead.email,
                    "scheduled_at": NOW,
                    "sent_at": NOW,
                },
            )

            lead.last_contacted = NOW
            lead.contact_count = (lead.contact_count or 0) + 1
            lead.save(update_fields=["last_contacted", "contact_count", "updated_at"])

            sent += 1
            log.info("Sent follow-up to %s (%s) for offer: %s",
                     lead.name, lead.email, offer.title[:40])
            time.sleep(EMAIL_DELAY_SECONDS)

    log.info("Follow-ups complete: %d sent | %d skipped", sent, skipped)
    return {"sent": sent, "skipped": skipped}


# ---------------------------------------------------------------------------
# Slack summary
# ---------------------------------------------------------------------------

def post_slack_summary(audit, fresh, followups):
    """Post a run summary to Slack."""
    if not SLACK_TOKEN:
        log.info("No SLACK_BOT_TOKEN set -- skipping Slack post")
        return

    import requests

    pending_count = BrokerMatch.objects.filter(
        status="pending", match_score__gt=MIN_MATCH_SCORE
    ).count()

    total_sent = fresh['sent'] + followups['sent']
    email_pct = (audit['with_email'] / audit['total'] * 100) if audit['total'] else 0

    if total_sent > 0:
        status_icon = ":rocket:"
        status_line = f"{total_sent} emails sent ({fresh['sent']} fresh, {followups['sent']} follow-ups)"
    elif fresh['skipped_no_email'] > 0:
        status_icon = ":warning:"
        status_line = f"BLOCKED: {fresh['skipped_no_email']} matches skipped (no email). Auto-enrichment active."
    else:
        status_icon = ":mag:"
        status_line = f"No eligible matches. {pending_count} pending (score>{MIN_MATCH_SCORE:.0f})."

    msg = (
        f"{status_icon} *Broker OS SDR -- {TODAY}*\n"
        f"{status_line}\n"
        f"Email coverage: {audit['with_email']}/{audit['total']} ({email_pct:.0f}%)\n"
        f"Pipeline: {pending_count} pending matches"
    )

    if fresh['errors'] > 0:
        msg += f"\n:x: {fresh['errors']} send errors -- check Resend dashboard"

    try:
        requests.post(
            "https://slack.com/api/chat.postMessage",
            headers={
                "Authorization": f"Bearer {SLACK_TOKEN}",
                "Content-Type": "application/json",
            },
            json={"channel": SLACK_CHANNEL, "text": msg},
            timeout=10,
        )
    except Exception as exc:
        log.warning("Slack post failed: %s", exc)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_diagnostics():
    """Print pipeline diagnostics without sending anything."""
    from django.db.models import Avg, Count, Q

    log.info("=== BROKER SDR DIAGNOSTICS ===")

    audit = audit_lead_emails()

    # Match status breakdown
    log.info("MATCH STATUS BREAKDOWN:")
    for row in BrokerMatch.objects.values("status").annotate(c=Count("id")).order_by("-c"):
        log.info("  %s: %d", row["status"], row["c"])

    # Score distribution
    log.info("SCORE DISTRIBUTION (all matches):")
    for threshold in [90, 80, 70, 60, 50, 40, 30, 20, 10]:
        ct = BrokerMatch.objects.filter(match_score__gt=threshold).count()
        log.info("  score > %d: %d", threshold, ct)

    # Approved but never emailed
    ghost_approved = BrokerMatch.objects.filter(
        status="approved", outreach_sent_at__isnull=True
    ).count()
    log.info("GHOST APPROVED (status=approved but never emailed): %d", ghost_approved)

    # Actionable right now
    actionable = (
        BrokerMatch.objects
        .filter(
            Q(status="pending", match_score__gt=MIN_MATCH_SCORE)
            | Q(status="approved", outreach_sent_at__isnull=True, match_score__gt=MIN_MATCH_SCORE)
        )
        .exclude(lead__email="")
        .exclude(lead__unsubscribed=True)
        .count()
    )
    log.info("ACTIONABLE NOW (score>%.0f, has email, not unsub): %d", MIN_MATCH_SCORE, actionable)

    if actionable == 0:
        log.warning(
            "Zero actionable matches at score>%.0f. Try lowering the threshold: "
            "BROKER_MIN_SCORE=40 python3 broker_outreach_sdr.py",
            MIN_MATCH_SCORE,
        )


def main(mode: str = "send"):
    log.info("Broker OS SDR starting -- mode: %s", mode)

    if mode == "audit":
        run_diagnostics()
        return 0

    # Step 1: Audit lead emails
    audit = audit_lead_emails()

    if mode == "dry-run":
        log.info("DRY RUN -- showing what would be sent without sending")
        from django.db.models import Q
        matches = (
            BrokerMatch.objects
            .filter(
                Q(status="pending", match_score__gt=MIN_MATCH_SCORE)
                | Q(status="approved", outreach_sent_at__isnull=True, match_score__gt=MIN_MATCH_SCORE)
            )
            .select_related("lead", "offer")
            .exclude(lead__email="")
            .exclude(lead__email__contains="@placeholder")
            .exclude(lead__unsubscribed=True)
            .order_by("-match_score")[:FRESH_OUTREACH_LIMIT]
        )
        for m in matches:
            subj, body = build_intro_email(m.lead, m.offer, m)
            log.info("WOULD SEND to %s <%s> -- %s [score: %.0f]",
                     m.lead.name, m.lead.email, subj, m.match_score)
        log.info("Total that would send: %d", matches.count())
        return 0

    # Step 2: Verify Resend API key is set
    if not RESEND_KEY:
        log.error(
            "FATAL: No RESEND_API_KEY or SMTP_PASS environment variable set. "
            "Cannot send emails. Exiting."
        )
        sys.exit(1)

    # Step 3: Fresh outreach
    fresh = run_fresh_outreach()

    # Step 4: Follow-ups
    followups = run_followups()

    # Step 5: Slack summary
    post_slack_summary(audit, fresh, followups)

    total = fresh["sent"] + followups["sent"]
    log.info("Broker OS SDR complete -- %d total emails sent", total)
    return total


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "send"
    if mode not in ("send", "audit", "dry-run"):
        print("Usage: broker_outreach_sdr.py [send|audit|dry-run]")
        sys.exit(1)
    main(mode)
