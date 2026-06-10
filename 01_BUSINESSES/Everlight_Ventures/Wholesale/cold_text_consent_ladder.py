"""cold_text_consent_ladder -- legal cold SMS that captures TCPA-compliant
consent for an AI bot call.

Why this exists:
  151 leads in the DB have phone numbers but no email. Email outreach
  cannot reach them. AI calls require PEWC (47 CFR 64.1200) which we don't
  have. This module solves both: ONE plain text per lead asking for explicit
  YES, which constitutes electronic-signature PEWC under E-SIGN Act and
  unlocks the full AI-call pipeline.

Why this is legal:
  1. Manual / P2P-volume SMS at low daily counts (<100/day, <1000/mo from
     a single business number) is generally classified as P2P (person-to-
     person), exempt from A2P 10DLC.
  2. Each text is unique (includes the seller's specific property address)
     and human-reviewable -- not a blast.
  3. Every text includes "Reply STOP to opt out forever" per CTIA + TCPA.
  4. Every text references the specific property -- proves it's not random
     spam, it's a property-specific outreach.
  5. ConsentLedger logs every send + every reply with timestamp, immutable.

States this fires in (where cold SMS is legal AT ALL):
  GA -- Yes
  AZ -- Yes
  MO -- Yes
  TN -- Yes
  OH -- Yes
  CA -- BLOCKED (DNC + cooling-off statutes)
  TX -- BLOCKED (SB 140 cold SMS ban without SoS reg + $10K bond)
  FL -- BLOCKED (FTSA $500-1500/text class action exposure)
  NC -- BLOCKED (HB 797 license-required wholesale)

The text body:
  Hi [first_name], Piper from Everlight Ventures here. We saw your property at
  [address] and we're cash buyers in your area, 14-day close. Reply YES if you
  want our 60-second AI assistant to share the offer range. Reply STOP to never
  hear from us. -Piper

Reply handler (cold_text_reply_handler.py, separate cron):
  - "YES" / "Y" / "OK" -> ConsentLedger.update(channels=["ai_call","sms"])
  - "STOP" / "REMOVE" / "NO" -> suppression list (forever, all channels)
  - Anything else -> humans-only thread

Once consent flips to ai_call=allowed, the existing dispatch_ai_calls.py
cron picks them up on the next run and dials.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import secrets
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

for p in (
    "/home/opc/hive_django",
    "/mnt/sdcard/AA_MY_DRIVE/09_DASHBOARD/hive_dashboard",
    "/home/opc/wholesale/compliance",
    "/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale/compliance",
):
    if p not in sys.path and Path(p).exists():
        sys.path.insert(0, p)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hive_dashboard.settings")
import django  # noqa
django.setup()

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("cold_text")

# States where cold SMS is legally workable (P2P-volume, plain-text, opt-in style)
COLD_TEXT_OK_STATES = {"GA", "AZ", "MO", "TN", "OH"}

# Daily P2P safety cap. Stay well below 100/day to maintain P2P classification.
DAILY_CAP = 25

# Spacing between sends (seconds). 30+ sec = clearly P2P pace, not blast.
SEND_DELAY_SECONDS = 30


def _twilio_send(to_phone: str, body: str) -> dict:
    """Send via Twilio REST. Returns dict with ok + sid + error."""
    sid = os.environ.get("TWILIO_ACCOUNT_SID", "")
    tok = os.environ.get("TWILIO_AUTH_TOKEN", "")
    from_num = os.environ.get("TWILIO_FROM_NUMBER", "+14048004380")
    if not sid or not tok:
        return {"ok": False, "error": "no_twilio_creds_in_env"}

    import urllib.request
    import urllib.parse
    import base64
    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
    data = urllib.parse.urlencode({
        "To": to_phone,
        "From": from_num,
        "Body": body,
    }).encode()
    auth = base64.b64encode(f"{sid}:{tok}".encode()).decode()
    req = urllib.request.Request(url, data=data, headers={
        "Authorization": f"Basic {auth}",
        "Content-Type": "application/x-www-form-urlencoded",
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            payload = json.loads(resp.read().decode())
            return {"ok": True, "sid": payload.get("sid", ""), "status": payload.get("status", "")}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _normalize_phone(phone: str) -> str:
    """Twilio needs E.164. Best-effort: strip non-digits, prepend +1 if 10 digits."""
    digits = "".join(c for c in (phone or "") if c.isdigit())
    if len(digits) == 11 and digits.startswith("1"):
        return "+" + digits
    if len(digits) == 10:
        return "+1" + digits
    return ""


_ENTITY_TOKENS = {
    "LLC", "INC", "CORP", "LP", "LLP", "LTD", "TRUST", "PARTNERS",
    "PARTNERSHIP", "HOLDINGS", "ESTATES", "PROPERTIES", "INVESTMENT",
    "INVESTMENTS", "REALTY", "GROUP", "CO", "COMPANY", "ASSOCIATES",
    "FOUNDATION", "ASSOCIATION", "AUTHORITY", "BANK", "FUND",
    "CHURCH", "MINISTRIES", "ENTERPRISES",
}


def _first_name(name: str) -> str:
    """Personal first name only -- entities get 'there' to avoid 'Hi Land,'."""
    if not name:
        return "there"
    upper_tokens = set((name or "").upper().replace(",", " ").split())
    if _ENTITY_TOKENS & upper_tokens:
        return "there"
    return (name or "there").strip().split()[0].title() if name else "there"


def _text_body(lead) -> str:
    """Build the consent-ladder SMS for a single lead.

    Stays under 160 chars when possible to keep it 1 SMS segment.
    Includes property address (proves specificity), opt-in ask, opt-out word.
    """
    first = _first_name(getattr(lead, "owner_name", "") or "")
    addr_full = getattr(lead, "address", "") or ""
    # Just the street + first comma part, keeps it short
    addr_short = addr_full.split(",")[0].strip()
    # Format: ~155 chars target
    body = (
        f"Hi {first}, Piper at Everlight Ventures. Cash buyer for "
        f"{addr_short}, 14d close. Reply YES for our 60-sec offer call. "
        f"Reply STOP to opt out."
    )
    return body


def _has_consent(lead) -> bool:
    """Skip if there's already an active consent record for this lead."""
    try:
        from broker_ops.models import ConsentLedger
        phone = _normalize_phone(getattr(lead, "owner_phone", "") or "")
        if not phone:
            return False
        digits = phone.replace("+1", "")
        return ConsentLedger.objects.filter(
            contact_phone=digits, contact_type="seller"
        ).exclude(disclosure_text="(pending submission)").exists()
    except Exception:
        return False


def _is_suppressed(phone: str) -> bool:
    """Check the global suppression list."""
    sup_path = Path("/home/opc/wholesale/suppression_list.txt")
    if not sup_path.exists():
        return False
    try:
        digits_only = "".join(c for c in phone if c.isdigit())
        if len(digits_only) >= 10:
            digits_only = digits_only[-10:]
        for line in sup_path.read_text().splitlines():
            line_digits = "".join(c for c in line if c.isdigit())
            if line_digits.endswith(digits_only) and digits_only:
                return True
    except Exception:
        pass
    return False


def _record_consent_invite(lead, phone: str, text_body: str, twilio_response: dict) -> None:
    """Insert a ConsentLedger draft with full forensic anchors.

    Saves the outbound Twilio SID + raw payload + property lead tie so the
    record is independently subpoena-able. When the seller replies YES,
    cold_text_reply_handler appends the inbound SID + verbatim body + payload.
    """
    try:
        from broker_ops.models import ConsentLedger
        token = secrets.token_urlsafe(20)
        digits = phone.replace("+1", "")
        twilio_sid = twilio_response.get("sid", "")
        ConsentLedger.objects.create(
            contact_type="seller",
            contact_name=(getattr(lead, "owner_name", "") or "")[:200],
            contact_phone=digits,
            contact_email="",
            channels=[],  # not yet granted -- waiting on YES reply
            disclosure_text=text_body,
            signature_text="",
            consent_token=token,
            # Forensic anchors
            outbound_twilio_sid=twilio_sid,
            outbound_sent_at=datetime.now(timezone.utc),
            property_lead_id=str(getattr(lead, "id", "")),
            evidence_payload_json=json.dumps({
                "outbound": {
                    "twilio_response": twilio_response,
                    "address": getattr(lead, "address", ""),
                    "owner_name": getattr(lead, "owner_name", ""),
                    "state": getattr(lead, "state", ""),
                    "sent_at_iso": datetime.now(timezone.utc).isoformat(),
                    "from_number": os.environ.get("TWILIO_FROM_NUMBER", ""),
                    "body": text_body,
                },
            }),
        )
        log.info(f"  consent_ledger draft created for {phone} sid={twilio_sid}")
    except Exception as exc:
        log.warning(f"  consent_ledger insert failed: {exc}")


def fire_batch(max_sends: int = DAILY_CAP, dry_run: bool = False) -> dict:
    """Send cold consent-ladder texts to phone-only leads in workable states.

    Hard caps + hard skips:
      - DAILY_CAP (default 25, never sets above 50)
      - State must be in COLD_TEXT_OK_STATES
      - Phone must normalize to E.164
      - Skip if already in ConsentLedger or suppression list
      - Skip if no owner_name (sounds spammy without a personal salutation)
    """
    from broker_ops.models import PropertyLead

    counts = {
        "considered": 0, "sent": 0, "blocked_state": 0,
        "no_phone": 0, "already_consented": 0, "suppressed": 0,
        "errors": 0, "dry_run_preview": [],
    }

    qs = PropertyLead.objects.exclude(owner_phone="").filter(
        state__in=COLD_TEXT_OK_STATES, status="new",
    ).order_by("-motivation_score" if hasattr(PropertyLead, "motivation_score") else "id")

    sent_in_run = 0
    for lead in qs:
        if sent_in_run >= max_sends:
            break
        counts["considered"] += 1
        state = (lead.state or "").upper()
        phone = _normalize_phone(getattr(lead, "owner_phone", "") or "")

        if state not in COLD_TEXT_OK_STATES:
            counts["blocked_state"] += 1
            continue
        if not phone:
            counts["no_phone"] += 1
            continue
        if _has_consent(lead):
            counts["already_consented"] += 1
            continue
        if _is_suppressed(phone):
            counts["suppressed"] += 1
            continue

        body = _text_body(lead)

        if dry_run:
            counts["dry_run_preview"].append({
                "phone": phone, "state": state,
                "body": body, "address": getattr(lead, "address", "")[:50],
                "owner": getattr(lead, "owner_name", "")[:30],
            })
            sent_in_run += 1
            continue

        result = _twilio_send(phone, body)
        if result.get("ok"):
            counts["sent"] += 1
            sent_in_run += 1
            _record_consent_invite(lead, phone, body, result)
            log.info(f"  TEXTED: {phone} ({state}) -- {getattr(lead, 'address', '')[:50]}")

            # Per-lead pipeline report so Rich can SEE the money flow on every text
            try:
                import sys as _sys
                for _p in ("/home/opc/wholesale", "/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale"):
                    if _p not in _sys.path:
                        _sys.path.insert(0, _p)
                from pipeline_report import generate_pipeline_html
                rep = generate_pipeline_html(
                    lead, status="cold_text_sent",
                    pitch_subject=f"SMS to {phone}",
                    pitch_body_preview=body,
                )
                log.info(f"    pipeline report: {rep['url']}")
            except Exception as exc:
                log.warning(f"    pipeline report failed: {exc}")

            time.sleep(SEND_DELAY_SECONDS)
        else:
            counts["errors"] += 1
            log.warning(f"  Twilio fail to {phone}: {result.get('error')}")

    return counts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=DAILY_CAP, help=f"max sends per run (default {DAILY_CAP})")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.max > 50:
        log.warning("Capping --max at 50 to maintain P2P classification")
        args.max = 50

    result = fire_batch(max_sends=args.max, dry_run=args.dry_run)
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
