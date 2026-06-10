"""hammer_callback_watcher -- "wake me when there's a callback to do" watchdog.

Runs every 30 minutes during working hours (06:00-22:00 PT). Checks for:

  1. PropertyLead.status flipped to 'replied' since last check
  2. CallbackTask.status='pending' rows newer than last check
  3. ConsentLedger granted (channels populated) since last check
  4. Bid replies received in BidLedger since last check
  5. POFRequest.status='approved' (buyer verified) since last check

For each new event, posts ONE branded Slack ping to #hive-alerts with:
  - Lead context (address, owner, state, motivation tier)
  - The action expected ("call them back", "verify wire", "send contract")
  - The pipeline report URL so Rich sees the money chain instantly

A "last seen" timestamp lives at /home/opc/wholesale/_logs/hammer_watcher_seen.json
so we don't re-alert on the same event twice.

Cron line:
  */30 6-22 * * * cd /home/opc && source .env && \
    python3 /home/opc/wholesale/hammer_callback_watcher.py >> \
    /home/opc/_logs/hammer_watcher.log 2>&1
"""
from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

for p in ("/home/opc/hive_django",
          "/home/opc/wholesale",
          "/home/opc/content_tools"):
    if p not in sys.path and Path(p).exists():
        sys.path.insert(0, p)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hive_dashboard.settings")
import django  # noqa
django.setup()

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("hammer_watcher")

SEEN_FILE = Path("/home/opc/wholesale/_logs/hammer_watcher_seen.json")
SEEN_FILE.parent.mkdir(parents=True, exist_ok=True)


def _load_seen() -> dict:
    if SEEN_FILE.exists():
        try:
            return json.loads(SEEN_FILE.read_text())
        except Exception:
            return {}
    return {}


def _save_seen(d: dict) -> None:
    SEEN_FILE.write_text(json.dumps(d, indent=2, default=str))


def _slack_ping(title: str, body: str, summary: str = "", category: str = "deal") -> None:
    try:
        from branded_slack import post_branded_slack  # type: ignore
        post_branded_slack(
            channel="#hive-alerts",
            category=category,
            title=title,
            summary=summary or title,
            body=body,
            agent_name="Hammer Knox",
            agent_title="Disposition / Closer",
        )
        log.info(f"  ALERT: {title}")
    except Exception as exc:
        log.warning(f"  slack ping failed: {exc}")


def _pipeline_report_url(lead_id: str) -> str:
    """Find the most recent pipeline report for this lead."""
    try:
        reports = sorted(
            Path("/home/opc/hive_reports").glob(f"pipeline_{lead_id}*.html"),
            key=lambda x: x.stat().st_mtime, reverse=True,
        )
        if reports:
            return f"http://127.0.0.1:2200/reports/{reports[0].stem}/"
    except Exception:
        pass
    return ""


def check_replied_leads(seen: dict) -> int:
    """PropertyLead.status='replied' since last check."""
    from broker_ops.models import PropertyLead
    last = seen.get("last_replied_check") or "2026-01-01T00:00:00+00:00"
    last_dt = datetime.fromisoformat(last)
    n = 0
    qs = PropertyLead.objects.filter(status="replied")
    for lead in qs:
        # Use updated_at if available, else fallback to status flip detection
        ts = getattr(lead, "updated_at", None) or getattr(lead, "created_at", None)
        if not ts or ts <= last_dt:
            continue
        url = _pipeline_report_url(str(lead.id))
        body = (
            f"Lead {lead.id} just replied. Time to call.\n\n"
            f"Address: {lead.address}\n"
            f"Owner: {lead.owner_name or 'unknown'}\n"
            f"Phone: {lead.owner_phone or '(none)'}\n"
            f"Email: {lead.owner_email or '(none)'}\n"
            f"State: {lead.state}\n"
            f"Lead type: {lead.lead_type or 'unknown'}\n\n"
            f"Pipeline report (full money chain): {url or 'N/A'}\n\n"
            f"Next step: Hammer qualification call -- 30 min on the phone, then fire the lowball pack."
        )
        _slack_ping(
            f"REPLY -- {lead.address[:50] if lead.address else 'lead'}",
            body, category="deal",
        )
        n += 1
    seen["last_replied_check"] = datetime.now(timezone.utc).isoformat()
    return n


def check_pending_callbacks(seen: dict) -> int:
    """CallbackTask new pending rows."""
    from broker_ops.models import CallbackTask
    last = seen.get("last_callback_check") or "2026-01-01T00:00:00+00:00"
    last_dt = datetime.fromisoformat(last)
    n = 0
    qs = CallbackTask.objects.filter(status="pending")
    for cb in qs:
        ts = getattr(cb, "created_at", None)
        if not ts or ts <= last_dt:
            continue
        body = (
            f"New callback queued.\n\n"
            f"Phone: {cb.phone}\n"
            f"Contact: {cb.contact_name or 'unknown'}\n"
            f"Reason: {cb.reason}\n"
            f"Source: {cb.source}\n"
            f"Priority: {cb.priority}"
        )
        _slack_ping(
            f"CALLBACK -- {cb.contact_name or cb.phone}", body,
            category="ops",
        )
        n += 1
    seen["last_callback_check"] = datetime.now(timezone.utc).isoformat()
    return n


def check_consent_grants(seen: dict) -> int:
    """ConsentLedger rows where channels just got populated (YES received)."""
    from broker_ops.models import ConsentLedger
    last = seen.get("last_consent_check") or "2026-01-01T00:00:00+00:00"
    last_dt = datetime.fromisoformat(last)
    n = 0
    qs = ConsentLedger.objects.exclude(channels=[]).filter(inbound_received_at__gt=last_dt)
    for c in qs:
        body = (
            f"Consent GRANTED. AI calls now legal for this contact.\n\n"
            f"Phone: {c.contact_phone}\n"
            f"Name: {c.contact_name or 'unknown'}\n"
            f"Reply text: '{c.inbound_body_verbatim[:80]}'\n"
            f"Channels: {', '.join(c.channels)}\n"
            f"Forensically defensible: {c.is_legally_defensible()}\n\n"
            f"Next: dispatch_ai_calls cron will pick them up next cycle."
        )
        _slack_ping(
            f"CONSENT -- {c.contact_name or c.contact_phone}", body,
            category="deal",
        )
        n += 1
    seen["last_consent_check"] = datetime.now(timezone.utc).isoformat()
    return n


def check_pof_approvals(seen: dict) -> int:
    """POFRequest just-approved buyers."""
    from broker_ops.models import POFRequest
    last = seen.get("last_pof_check") or "2026-01-01T00:00:00+00:00"
    last_dt = datetime.fromisoformat(last)
    n = 0
    qs = POFRequest.objects.filter(status="approved", reviewed_at__gt=last_dt)
    for p in qs:
        body = (
            f"Buyer POF VERIFIED. Now bid-war eligible.\n\n"
            f"Buyer: {p.buyer.name if p.buyer else 'unknown'}\n"
            f"POF amount: ${p.pof_amount:,.0f}\n"
            f"POF dated: {p.pof_letter_dated}\n\n"
            f"This buyer is now in the priority pool for the next bid war."
        )
        _slack_ping(
            f"POF VERIFIED -- {p.buyer.name if p.buyer else 'buyer'}", body,
            category="deal",
        )
        n += 1
    seen["last_pof_check"] = datetime.now(timezone.utc).isoformat()
    return n


def main():
    seen = _load_seen()
    log.info(f"hammer_watcher tick at {datetime.now(timezone.utc).isoformat()}")

    total_alerts = 0
    for fn in (check_replied_leads, check_pending_callbacks,
                check_consent_grants, check_pof_approvals):
        try:
            n = fn(seen)
            total_alerts += n
            if n:
                log.info(f"  {fn.__name__}: {n} new alerts")
        except Exception as exc:
            log.warning(f"  {fn.__name__} failed: {exc}")

    _save_seen(seen)
    log.info(f"  total alerts this tick: {total_alerts}")


if __name__ == "__main__":
    main()
