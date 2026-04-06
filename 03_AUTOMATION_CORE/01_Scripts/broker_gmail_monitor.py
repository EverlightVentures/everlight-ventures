#!/usr/bin/env python3
"""
Broker OS -- Gmail Reply Monitor

Scans sage@everlightventures.io for seller replies and updates
the broker pipeline accordingly. Designed to run as a cron job
or be called from n8n.

Usage:
    python3 broker_gmail_monitor.py check     # Check for new replies
    python3 broker_gmail_monitor.py digest    # Daily reply digest to Slack
"""

import os
import sys
import json
import logging
import argparse
import requests
from datetime import datetime, timezone
from pathlib import Path

# Django setup -- works on both phone and Oracle
for _djp in [
    str(Path(__file__).resolve().parent.parent.parent / "09_DASHBOARD" / "hive_dashboard"),
    "/home/opc/hive_django",
]:
    if os.path.isdir(_djp):
        sys.path.insert(0, _djp)
        break
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hive_dashboard.settings")

import django
django.setup()

from broker_ops.models import OfferListing, LeadProfile, BrokerMatch, Deal

# Wire neuromorphic NLP for intelligent reply classification
try:
    for _nd in [
        str(Path(__file__).resolve().parent.parent.parent / "06_DEVELOPMENT" / "everlight_os"),
        "/home/opc/06_DEVELOPMENT/everlight_os",
    ]:
        if os.path.isdir(_nd) and _nd not in sys.path:
            sys.path.insert(0, _nd)
    from neuromorphic.nlp_engine import analyze_email_reply as nlp_analyze_reply
except ImportError:
    nlp_analyze_reply = None

# Wire pipeline API for reply path recommendations
try:
    from neuromorphic.pipeline_api import recommend_reply_path
except ImportError:
    recommend_reply_path = None

log = logging.getLogger("broker_gmail")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Load credentials
CREDS_DIR = Path(__file__).resolve().parent.parent / "03_Credentials"

def _load_env():
    env_file = CREDS_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip())

_load_env()

SLACK_WEBHOOK = os.environ.get("SLACK_WEBHOOK_URL", "")

# Known seller email domains (from our outreach)
SELLER_DOMAINS = set()

def _load_seller_domains():
    """Load all seller email domains from the database."""
    global SELLER_DOMAINS
    offers = OfferListing.objects.exclude(
        seller_email__contains="@placeholder.io"
    ).values_list("seller_email", flat=True)
    for email in offers:
        if "@" in email:
            domain = email.split("@")[1].lower()
            SELLER_DOMAINS.add(domain)
    log.info(f"Loaded {len(SELLER_DOMAINS)} seller domains to watch")


def _slack(msg):
    if not SLACK_WEBHOOK:
        log.warning("No Slack webhook configured")
        return
    try:
        requests.post(SLACK_WEBHOOK, json={"text": msg}, timeout=10)
    except Exception as e:
        log.error(f"Slack error: {e}")


def _is_seller_reply(from_email):
    """Check if the sender matches a known seller domain."""
    if not from_email or "@" not in from_email:
        return False
    domain = from_email.split("@")[1].lower().strip(">").strip()
    return domain in SELLER_DOMAINS


def _find_offer_by_domain(domain):
    """Find the OfferListing matching this email domain."""
    offers = OfferListing.objects.filter(
        seller_email__icontains=domain
    ).first()
    return offers


def _classify_reply(subject, snippet):
    """Classify reply intent using NLP engine (with keyword fallback).

    Uses neuromorphic.nlp_engine.analyze_email_reply when available for
    sentiment scoring, interest detection, and urgency analysis.
    Falls back to keyword matching if NLP is not installed.
    """
    text = (subject + " " + snippet).lower()
    full_text = f"Subject: {subject}\n\n{snippet}"

    # Try NLP-powered classification first
    if nlp_analyze_reply is not None:
        try:
            analysis = nlp_analyze_reply(full_text)
            sentiment = analysis.get("reply_sentiment", 0)
            is_interested = analysis.get("is_interested", False)
            is_objection = analysis.get("is_objection", False)

            if is_objection or sentiment < -0.3:
                intent = "negative"
            elif is_interested or sentiment > 0.3:
                intent = "positive"
            else:
                intent = "neutral"

            # Get recommended next action from pipeline API
            next_action = None
            if recommend_reply_path is not None:
                try:
                    path = recommend_reply_path(intent, reply_analysis=analysis)
                    next_action = path.get("recommended_action")
                except Exception:
                    pass

            log.info(f"NLP classification: {intent} (sentiment={sentiment:.2f}, "
                     f"interested={is_interested}, next_action={next_action})")
            return intent
        except Exception as e:
            log.warning(f"NLP classification failed, falling back to keywords: {e}")

    # Keyword fallback
    positive_signals = [
        "interested", "yes", "sure", "let's", "sounds good",
        "tell me more", "send details", "how does it work",
        "happy to", "let us know", "schedule", "call"
    ]
    negative_signals = [
        "not interested", "no thanks", "unsubscribe", "remove",
        "stop", "don't contact", "not at this time", "pass"
    ]

    for sig in negative_signals:
        if sig in text:
            return "negative"
    for sig in positive_signals:
        if sig in text:
            return "positive"
    return "neutral"


def check_replies(gmail_results=None):
    """
    Check for seller replies. Can accept pre-fetched Gmail results
    or will need external Gmail data passed in.

    In production, this is called by n8n which fetches Gmail via its
    Gmail node, then passes results to this script via stdin JSON.
    """
    _load_seller_domains()

    # Read Gmail results from stdin if not passed directly
    if gmail_results is None:
        if not sys.stdin.isatty():
            try:
                raw = sys.stdin.read()
                gmail_results = json.loads(raw) if raw.strip() else []
            except json.JSONDecodeError:
                gmail_results = []
        else:
            log.info("No Gmail data provided. Pass JSON via stdin or use n8n integration.")
            log.info(f"Watching {len(SELLER_DOMAINS)} seller domains: {sorted(SELLER_DOMAINS)[:10]}...")
            return

    seller_replies = []
    other_emails = []

    for msg in gmail_results:
        from_email = msg.get("from", "")
        subject = msg.get("subject", "")
        snippet = msg.get("snippet", "")
        msg_id = msg.get("id", "")

        if _is_seller_reply(from_email):
            domain = from_email.split("@")[1].lower().strip(">").strip()
            offer = _find_offer_by_domain(domain)
            intent = _classify_reply(subject, snippet)

            seller_replies.append({
                "from": from_email,
                "subject": subject,
                "snippet": snippet[:200],
                "intent": intent,
                "offer": offer.title if offer else "Unknown",
                "msg_id": msg_id,
            })

            # Update the offer notes
            if offer:
                note = f"\n[REPLY_RECEIVED] {datetime.now(timezone.utc).isoformat()} | Intent: {intent} | Subject: {subject[:80]}"
                offer.notes = (offer.notes or "") + note
                offer.save(update_fields=["notes", "updated_at"])
                log.info(f"Seller reply: {from_email} -> {offer.title} (intent: {intent})")

                # If positive, create a Deal
                if intent == "positive":
                    existing_deal = Deal.objects.filter(offer=offer).first()
                    if not existing_deal:
                        deal = Deal.objects.create(
                            offer=offer,
                            stage="intro",
                            notes=f"Auto-created from positive seller reply on {datetime.now().strftime('%Y-%m-%d %H:%M PT')}"
                        )
                        log.info(f"Deal CREATED: {deal.id} for {offer.title}")
                        _slack(
                            f"DEAL ALERT! {offer.title} replied positively!\n"
                            f"From: {from_email}\n"
                            f"Subject: {subject}\n"
                            f"Deal ID: {deal.id} -- Stage: intro\n"
                            f"Next: Generate contract and send partnership details"
                        )
        else:
            other_emails.append({
                "from": from_email,
                "subject": subject,
            })

    # Publish to Google Docs + Slack summary
    if seller_replies:
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
            from content_tools.gdocs_bridge import publish_report

            doc_lines = [
                "# Broker Gmail Monitor -- Seller Replies",
                f"**Scan Time:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M PT')}",
                f"**Replies Found:** {len(seller_replies)}",
                "",
                "| Offer | Intent | From | Subject |",
                "|-------|--------|------|---------|",
            ]
            for r in seller_replies:
                doc_lines.append(
                    f"| {r['offer']} | {r['intent'].upper()} | {r['from']} | {r['subject'][:60]} |"
                )

            summary = f"{len(seller_replies)} seller replies detected. {sum(1 for r in seller_replies if r['intent'] == 'positive')} positive."
            publish_report(
                title="Seller Reply Analysis",
                content="\n".join(doc_lines),
                folder="01_Broker_OS/Seller_Replies",
                summary=summary,
            )
        except ImportError:
            reply_text = "\n".join([
                f"  - {r['offer']}: {r['intent'].upper()} -- {r['from']} -- {r['subject'][:60]}"
                for r in seller_replies
            ])
            _slack(f"Broker Gmail Monitor -- {len(seller_replies)} seller replies detected:\n{reply_text}")
    else:
        log.info(f"No seller replies found. {len(other_emails)} other emails to sage@.")

    # Output results as JSON for n8n
    result = {
        "seller_replies": seller_replies,
        "other_count": len(other_emails),
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "domains_watched": len(SELLER_DOMAINS),
    }
    print(json.dumps(result, indent=2))
    return result


def daily_digest():
    """Send a daily digest of all seller interaction status to Google Docs."""
    _load_seller_domains()

    pitched = OfferListing.objects.filter(notes__contains="[OUTREACH_SENT]")
    replied = OfferListing.objects.filter(notes__contains="[REPLY_RECEIVED]")
    deals = Deal.objects.all()

    doc_lines = [
        f"# Broker OS Daily Digest",
        f"**Date:** {datetime.now().strftime('%Y-%m-%d %I:%M %p PT')}",
        "",
        "## Summary",
        f"| Metric | Count |",
        f"|--------|-------|",
        f"| Sellers Pitched | {pitched.count()} |",
        f"| Replies Received | {replied.count()} |",
        f"| Active Deals | {deals.count()} |",
        "",
        "## Replied Sellers",
    ]

    for offer in replied:
        doc_lines.append(f"- **{offer.title}** ({offer.seller_email})")

    doc_lines.append("")
    doc_lines.append("## Awaiting Reply")

    no_reply = pitched.exclude(notes__contains="[REPLY_RECEIVED]")
    for offer in no_reply:
        doc_lines.append(f"- {offer.title} ({offer.seller_email})")

    summary = f"Pitched: {pitched.count()} | Replied: {replied.count()} | Deals: {deals.count()}"

    try:
        from content_tools.gdocs_bridge import publish_report
        publish_report(
            title="Broker Daily Digest",
            content="\n".join(doc_lines),
            folder="01_Broker_OS/Daily_KPI",
            summary=summary,
        )
    except ImportError:
        _slack("\n".join(doc_lines))

    log.info("Daily digest sent")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Broker Gmail Monitor")
    parser.add_argument("action", choices=["check", "digest", "domains"],
                        help="check=scan for replies, digest=daily summary, domains=list watched domains")
    args = parser.parse_args()

    if args.action == "check":
        check_replies()
    elif args.action == "digest":
        daily_digest()
    elif args.action == "domains":
        _load_seller_domains()
        for d in sorted(SELLER_DOMAINS):
            print(f"  {d}")
