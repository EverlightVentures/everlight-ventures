#!/usr/bin/env python3
"""
funnel_nurture.py -- Email Drip Sequence Runner
Runs hourly via cron. Checks Lead table, sends scheduled emails via SMTP.

Usage:
    python funnel_nurture.py --dry-run    # simulate without sending
    python funnel_nurture.py              # send pending emails

Env vars:
    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS
    SMTP_PROVIDER (resend | brevo | proton | generic)
    SLACK_WEBHOOK_URL (optional, for notifications)
    DJANGO_SETTINGS_MODULE=hive_dashboard.settings
"""

import os
import sys
import json
import logging
import argparse
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from pathlib import Path

# Django setup
WORKSPACE = Path("/mnt/sdcard/AA_MY_DRIVE")
DJANGO_DIR = WORKSPACE / "09_DASHBOARD/hive_dashboard"
sys.path.insert(0, str(DJANGO_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hive_dashboard.settings")

import django
django.setup()

from funnel.models import Lead, FunnelEvent
from django.utils import timezone

CONFIG_DIR = WORKSPACE / "03_AUTOMATION_CORE/02_Config/funnel_emails"
LOG_DIR = WORKSPACE / "_logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "funnel_nurture.log"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("funnel_nurture")

# SMTP presets
SMTP_PRESETS = {
    "resend": {"host": "smtp.resend.com", "port": 465, "ssl": True},
    "brevo": {"host": "smtp-relay.brevo.com", "port": 587, "ssl": False},
    "proton": {"host": "smtp.protonmail.ch", "port": 465, "ssl": True},
    "generic": {"host": "", "port": 587, "ssl": False},
}


def load_sequence(product: str) -> dict:
    path = CONFIG_DIR / f"{product}_sequence.json"
    if not path.exists():
        log.error(f"Sequence config not found: {path}")
        return {}
    return json.loads(path.read_text())


def load_template(template_name: str, lead: Lead) -> str:
    path = CONFIG_DIR / template_name
    if not path.exists():
        log.warning(f"Template not found: {path}")
        return f"Hi {lead.name or 'there'},\n\nThanks for signing up!\n"
    content = path.read_text()
    content = content.replace("{{name}}", lead.name or "there")
    content = content.replace("{{email}}", lead.email)
    return content


def get_smtp_connection():
    provider = os.environ.get("SMTP_PROVIDER", "generic")
    preset = SMTP_PRESETS.get(provider, SMTP_PRESETS["generic"])

    host = os.environ.get("SMTP_HOST", preset["host"])
    port = int(os.environ.get("SMTP_PORT", preset["port"]))
    user = os.environ.get("SMTP_USER", "")
    password = os.environ.get("SMTP_PASS", "")

    if not host or not user:
        return None

    if preset.get("ssl") or port == 465:
        server = smtplib.SMTP_SSL(host, port, timeout=30)
    else:
        server = smtplib.SMTP(host, port, timeout=30)
        server.starttls()

    server.login(user, password)
    return server


def send_email(server, from_addr: str, from_name: str, to_addr: str, subject: str, body: str, dry_run: bool) -> bool:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{from_name} <{from_addr}>"
    msg["To"] = to_addr
    msg.attach(MIMEText(body, "plain"))

    if dry_run:
        log.info(f"  [DRY RUN] Would send to {to_addr}: {subject}")
        return True

    try:
        server.sendmail(from_addr, to_addr, msg.as_string())
        log.info(f"  Sent to {to_addr}: {subject}")
        return True
    except Exception as e:
        log.error(f"  Failed to send to {to_addr}: {e}")
        return False


def process_leads(dry_run: bool):
    now = timezone.now()
    leads = Lead.objects.filter(funnel_stage__in=["captured", "welcome_sent", "nurturing"])
    log.info(f"Processing {leads.count()} active leads")

    smtp = None
    if not dry_run:
        smtp = get_smtp_connection()
        if not smtp:
            log.error("No SMTP connection -- set SMTP_HOST/SMTP_USER/SMTP_PASS env vars")
            return

    sent_count = 0

    for lead in leads:
        seq = load_sequence(lead.product)
        if not seq:
            continue

        from_email = seq.get("from_email") or os.environ.get("SMTP_USER", "")
        from_name = seq.get("from_name", "Everlight")
        days_since_signup = (now - lead.created_at).days

        for step in seq.get("sequence", []):
            if step["day"] > days_since_signup:
                continue
            if lead.emails_sent > seq["sequence"].index(step):
                continue

            # Check if this specific email was already sent
            already_sent = FunnelEvent.objects.filter(
                lead=lead,
                event_type="email_sent",
                metadata__template=step["template"],
            ).exists()
            if already_sent:
                continue

            body = load_template(step["template"], lead)
            success = send_email(smtp, from_email, from_name, lead.email, step["subject"], body, dry_run)

            if success:
                FunnelEvent.objects.create(
                    lead=lead,
                    event_type="email_sent",
                    metadata={"template": step["template"], "subject": step["subject"], "day": step["day"]},
                )
                lead.emails_sent += 1
                lead.last_email_at = now
                if step.get("stage_after"):
                    lead.funnel_stage = step["stage_after"]
                lead.save()
                sent_count += 1
                break  # One email per lead per run

    if smtp:
        smtp.quit()

    log.info(f"Nurture run complete: {sent_count} emails {'would be ' if dry_run else ''}sent")
    _notify_slack(sent_count, dry_run)


def _notify_slack(count: int, dry_run: bool):
    webhook = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook or count == 0:
        return
    try:
        import requests
        prefix = "[DRY RUN] " if dry_run else ""
        requests.post(webhook, json={
            "text": f"{prefix}Funnel nurture: {count} emails sent",
            "channel": "#04-content-factory",
        }, timeout=5)
    except Exception:
        pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Funnel Email Nurture Runner")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without sending emails")
    args = parser.parse_args()

    process_leads(args.dry_run)
