"""practice_call_setup -- create a test ConsentLedger row + practice
PropertyLead so you can test-dial yourself end-to-end with real pitch data.

Usage
-----
    python3 practice_call_setup.py --phone "+14045551234" --name "Rich Test"
    # creates consent + lead, returns a CallbackTask id and a CLI to fire the call

The created PropertyLead uses a real Atlanta address from your callable list
(or a synthetic one) so when Piper-Wholesale calls you, she has actual
property details, real Zillow market data, and a real cash-offer range to
quote during the conversation.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

for sub in (
    "/home/opc/hive_django",
    "/home/opc/wholesale/voice",
    "/home/opc/wholesale/compliance",
    "/home/opc/wholesale/pitches",
):
    if sub not in sys.path:
        sys.path.insert(0, sub)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hive_dashboard.settings")

import django  # noqa: E402
django.setup()

from broker_ops.models import (CallbackTask, ConsentLedger, PropertyLead)  # noqa: E402


def normalize_phone(p: str) -> str:
    digits = "".join(c for c in (p or "") if c.isdigit())
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    return digits[-10:] if len(digits) >= 10 else digits


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phone", required=True, help="Your phone number, E.164 or US 10-digit")
    ap.add_argument("--name", default="Practice Caller")
    ap.add_argument("--email", default="practice@everlightventures.io")
    ap.add_argument("--address", default="1842 Windsor Dr SW, Atlanta, GA 30311")
    ap.add_argument("--zip", default="30311")
    ap.add_argument("--state", default="GA")
    ap.add_argument("--city", default="Atlanta")
    ap.add_argument("--arv", type=int, default=235000)
    ap.add_argument("--repair", type=int, default=22000)
    args = ap.parse_args()

    phone10 = normalize_phone(args.phone)
    if len(phone10) != 10:
        print("invalid phone format -- need 10 US digits or +1 E.164")
        return 1
    e164 = "+1" + phone10

    # 1. Create a practice PropertyLead so the call has real pitch context
    lead, lead_created = PropertyLead.objects.update_or_create(
        address=args.address,
        city=args.city,
        state=args.state,
        defaults={
            "zip_code": args.zip,
            "owner_name": args.name,
            "owner_phone": e164,
            "owner_email": args.email,
            "lead_type": "absentee",
            "is_absentee": True,
            "estimated_arv": args.arv,
            "estimated_repair": args.repair,
            "asking_price": 0,
            "sqft": 1180,
            "bedrooms": 3,
            "bathrooms": 2,
            "status": "new",
            "source": "practice_call_setup",
            "raw_data": {"practice": True},
        },
    )

    # 2. Create a non-revoked ConsentLedger row covering ai_call channel
    consent, consent_created = ConsentLedger.objects.update_or_create(
        contact_phone=phone10,
        revoked=False,
        defaults={
            "contact_type": "seller",
            "contact_name": args.name,
            "contact_email": args.email,
            "channels": ["ai_call", "autodialed_call", "sms_marketing", "email_marketing"],
            "disclosure_text": (
                "PRACTICE CONSENT (do not use for real prospects). "
                "Contact authorized AI voice calls + autodialed + SMS + email marketing "
                "for testing the Everlight wholesale calling system. "
                "This row was created via practice_call_setup.py."
            ),
            "signature_text": args.name,
            "signature_ip": "127.0.0.1",
            "signature_user_agent": "practice_call_setup CLI",
            "consent_token": f"practice_{phone10}",
        },
    )

    # 3. Create a CallbackTask wired to the lead
    cb, cb_created = CallbackTask.objects.update_or_create(
        lead_id=str(lead.id),
        phone=e164,
        defaults={
            "contact_name": args.name,
            "priority": "urgent",
            "status": "pending",
            "reason": "PRACTICE call to test Piper-Wholesale on real pitch data",
            "talking_points": "Practice run -- Piper should run the 5-qualifier flow.",
            "source": "practice_call_setup",
        },
    )

    # 4. Tell the user how to fire the actual call
    cli = (
        "python3 /home/opc/wholesale/voice/ai_caller.py dial "
        f"--phone '{e164}' --state {args.state} --name '{args.name}' "
        f"--lead-id '{lead.id}' --role seller_acquisition"
    )

    print(json.dumps({
        "ok": True,
        "lead_id": str(lead.id),
        "lead_created": lead_created,
        "lead_address": lead.address,
        "lead_arv": int(lead.estimated_arv),
        "consent_id": consent.id,
        "consent_created": consent_created,
        "consent_channels": consent.channels,
        "callback_task_id": cb.id,
        "callback_created": cb_created,
        "test_call_cli": cli,
        "note": (
            "Run the CLI on Oracle to place the practice call. "
            "Piper-Wholesale will dial you from +1 (404) 800-4380 within 30 seconds. "
            "She will use the address, ARV, and offer range loaded above."
        ),
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
