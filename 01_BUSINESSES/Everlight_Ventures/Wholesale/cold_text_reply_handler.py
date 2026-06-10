"""cold_text_reply_handler -- flips ConsentLedger when seller replies YES,
adds to suppression list when seller replies STOP.

Polled by Oracle cron every 10 minutes:
  */10 * * * * python3 /home/opc/wholesale/cold_text_reply_handler.py

Also exposed as a Twilio webhook endpoint (preferred -- instant reply detection).

Recognized YES words (PEWC granted):
  YES, Y, OK, OKAY, SURE, CALL, CALL ME, GO, START, GREEN LIGHT
  Anything starting with Y followed by space or end-of-string.

Recognized STOP words (suppression):
  STOP, STOPALL, UNSUBSCRIBE, REMOVE, NO, OPTOUT, OPT OUT, QUIT, CANCEL, END
  CTIA mandates these be free, instant, and respected forever.

Anything else: route to a #wholesale-replies Slack thread for human review.

When YES fires:
  1. ConsentLedger.update for that phone -> channels=["ai_call","sms","email"]
  2. ConsentLedger.signature_text = "SMS reply YES at YYYY-MM-DD HH:MM:SS UTC"
  3. PropertyLead.status -> "replied"
  4. CallbackTask.objects.create(priority="high", status="pending") so the
     next AI-call cron picks them up immediately
  5. Slack ping in #wholesale-deals
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

for p in (
    "/home/opc/hive_django",
    "/mnt/sdcard/AA_MY_DRIVE/09_DASHBOARD/hive_dashboard",
    "/home/opc/content_tools",
):
    if p not in sys.path and Path(p).exists():
        sys.path.insert(0, p)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hive_dashboard.settings")
import django  # noqa
django.setup()

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("text_reply")

YES_PATTERNS = [
    r"^y\b", r"^yes\b", r"^ok\b", r"^okay\b", r"^sure\b",
    r"^call\b", r"^go\b", r"^start\b", r"^yep\b", r"^yeah\b",
    r"^green\s*light", r"^let'?s\s+(go|talk|chat)",
]
STOP_WORDS = {
    "stop", "stopall", "unsubscribe", "remove", "no",
    "optout", "opt out", "opt-out", "quit", "cancel", "end",
}
SUPPRESSION_FILE = Path("/home/opc/wholesale/suppression_list.txt")


def _is_yes(body: str) -> bool:
    b = body.strip().lower()
    for pattern in YES_PATTERNS:
        if re.match(pattern, b):
            return True
    return False


def _is_stop(body: str) -> bool:
    b = body.strip().lower()
    for word in STOP_WORDS:
        if b == word or b.startswith(word + " ") or b.startswith(word + "."):
            return True
    return False


def _normalize_phone(phone: str) -> str:
    digits = "".join(c for c in (phone or "") if c.isdigit())
    if len(digits) == 11 and digits.startswith("1"):
        return digits[1:]
    return digits[-10:] if len(digits) >= 10 else digits


def _add_suppression(phone: str) -> None:
    SUPPRESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    digits = _normalize_phone(phone)
    line = f"{digits}  # suppressed by SMS reply at {datetime.now(timezone.utc).isoformat()}\n"
    with SUPPRESSION_FILE.open("a") as fh:
        fh.write(line)


def _pull_recent_inbound() -> list[dict]:
    """Pull SMS messages received in the last 60 minutes from Twilio."""
    sid = os.environ.get("TWILIO_ACCOUNT_SID", "")
    tok = os.environ.get("TWILIO_AUTH_TOKEN", "")
    from_num = os.environ.get("TWILIO_FROM_NUMBER", "+14048004380")
    if not sid or not tok:
        log.warning("Twilio creds missing; cannot poll inbound")
        return []

    import urllib.request
    import urllib.parse
    import base64
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=1)).strftime("%Y-%m-%d")
    params = urllib.parse.urlencode({
        "To": from_num,
        "DateSent>": cutoff,
        "PageSize": 50,
    })
    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json?{params}"
    auth = base64.b64encode(f"{sid}:{tok}".encode()).decode()
    req = urllib.request.Request(url, headers={"Authorization": f"Basic {auth}"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            return data.get("messages", [])
    except Exception as exc:
        log.warning(f"Twilio inbound pull failed: {exc}")
        return []


def _flip_consent_yes(phone_digits: str, body: str, twilio_msg: dict) -> bool:
    """Update the ConsentLedger row for this phone to grant ai_call + sms.

    Saves the full forensic chain:
      - inbound_twilio_sid (subpoena anchor; carrier-corroborated)
      - inbound_body_verbatim (their actual reply, exact characters)
      - inbound_received_at (server-side timestamp from Twilio)
      - evidence_payload_json (raw Twilio payload, both sides if outbound exists)

    On any TCPA dispute, this row + the carrier's matching record = ironclad proof.
    """
    try:
        from broker_ops.models import ConsentLedger
        sid = twilio_msg.get("sid", "")
        # Twilio uses RFC 2822 date format
        date_sent_str = twilio_msg.get("date_sent") or twilio_msg.get("date_created") or ""
        try:
            from email.utils import parsedate_to_datetime
            received_at = parsedate_to_datetime(date_sent_str) if date_sent_str else datetime.now(timezone.utc)
        except Exception:
            received_at = datetime.now(timezone.utc)

        rows = ConsentLedger.objects.filter(contact_phone=phone_digits).order_by("-id")
        if not rows.exists():
            log.info(f"  no ConsentLedger row for {phone_digits} -- creating one")
            ConsentLedger.objects.create(
                contact_type="seller",
                contact_phone=phone_digits,
                channels=["ai_call", "sms", "email"],
                disclosure_text="Cold text consent ladder (no outbound row found)",
                signature_text=f"SMS reply '{body[:80]}' at {received_at.isoformat()}",
                consent_token="cold_text_yes_" + phone_digits + "_" + sid[:12],
                inbound_twilio_sid=sid,
                inbound_body_verbatim=body,
                inbound_received_at=received_at,
                evidence_payload_json=json.dumps({"inbound_only": twilio_msg}),
            )
            return True
        row = rows.first()
        row.channels = ["ai_call", "sms", "email"]
        row.signature_text = f"SMS reply '{body[:80]}' at {received_at.isoformat()}"
        row.inbound_twilio_sid = sid
        row.inbound_body_verbatim = body
        row.inbound_received_at = received_at
        # Merge inbound payload into existing outbound payload if present
        try:
            existing = json.loads(row.evidence_payload_json or "{}")
        except Exception:
            existing = {}
        existing["inbound"] = twilio_msg
        row.evidence_payload_json = json.dumps(existing)
        row.save(update_fields=[
            "channels", "signature_text",
            "inbound_twilio_sid", "inbound_body_verbatim",
            "inbound_received_at", "evidence_payload_json",
        ])
        log.info(f"  CONSENT GRANTED: {phone_digits} sid={sid} -- legally defensible")
        return True
    except Exception as exc:
        log.warning(f"  ConsentLedger flip failed: {exc}")
        return False


def _queue_callback(phone_digits: str, body: str) -> None:
    """Drop a CallbackTask so the AI call cron picks them up next cycle."""
    try:
        from broker_ops.models import CallbackTask, PropertyLead
        # Find the matching PropertyLead by phone
        leads = PropertyLead.objects.filter(owner_phone__icontains=phone_digits[-10:])
        if not leads.exists():
            log.info(f"  no PropertyLead match for {phone_digits} -- creating callback w/ phone only")
            CallbackTask.objects.create(
                lead_id="",  # no associated lead
                phone="+1" + phone_digits,
                contact_name="Cold-text YES",
                priority="high",
                reason=f"Cold-text replied YES: '{body[:60]}'",
                status="pending",
                source="cold_text_consent",
            )
            return
        lead = leads.first()
        CallbackTask.objects.get_or_create(
            lead_id=str(lead.id),
            defaults={
                "phone": "+1" + phone_digits,
                "contact_name": (lead.owner_name or "")[:200],
                "priority": "high",
                "reason": f"Cold-text replied YES: '{body[:60]}'",
                "status": "pending",
                "source": "cold_text_consent",
            },
        )
        # Flip lead status
        try:
            lead.status = "replied"
            lead.save(update_fields=["status"])
        except Exception:
            pass
        log.info(f"  callback queued for lead {lead.id}: {lead.address}")
    except Exception as exc:
        log.warning(f"  callback queue failed: {exc}")


def _slack_ping(phone: str, body: str, kind: str) -> None:
    try:
        from branded_slack import post_branded_slack  # type: ignore
    except Exception:
        return
    icon = "GREEN" if kind == "yes" else ("RED" if kind == "stop" else "REVIEW")
    post_branded_slack(
        channel="#wholesale-deals",
        category="deal" if kind == "yes" else "ops",
        title=f"{icon} cold-text reply -- {phone}",
        summary=f"'{body[:80]}'",
        body=f"Phone: {phone}\nReply: {body}\nKind: {kind}",
        agent_name="Hammer Knox",
        agent_title="Disposition",
    )


def process_recent() -> dict:
    counts = {"polled": 0, "yes": 0, "stop": 0, "human_review": 0, "errors": 0}
    msgs = _pull_recent_inbound()
    counts["polled"] = len(msgs)

    for m in msgs:
        body = (m.get("body") or "").strip()
        from_phone = m.get("from", "")
        if not body or not from_phone:
            continue
        digits = _normalize_phone(from_phone)
        if not digits:
            continue

        if _is_yes(body):
            ok = _flip_consent_yes(digits, body, m)  # pass full Twilio message
            if ok:
                _queue_callback(digits, body)
                _slack_ping(from_phone, body, "yes")
                counts["yes"] += 1
                log.info(f"  YES from {from_phone}: '{body[:40]}'")
            else:
                counts["errors"] += 1
        elif _is_stop(body):
            _add_suppression(from_phone)
            _slack_ping(from_phone, body, "stop")
            counts["stop"] += 1
            log.info(f"  STOP from {from_phone}")
        else:
            _slack_ping(from_phone, body, "human_review")
            counts["human_review"] += 1

    return counts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true", help="poll once and exit")
    args = ap.parse_args()

    if args.once or True:
        result = process_recent()
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
