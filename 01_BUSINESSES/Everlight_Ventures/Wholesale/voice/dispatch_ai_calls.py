"""dispatch_ai_calls -- pull consented CallbackTasks and fire AI calls.

Called from wholesale_dispatcher.handle_ai_call_consented_callbacks() at
the scheduled compliant windows (Tue 11 + 3, Wed 11, Sat 9 PT).

Hard caps
---------
  AI_CALL_PER_CYCLE     -- max calls fired per dispatcher run (default 5)
  AI_CALL_DAILY_CAP     -- enforced inside ai_caller (default 50)

The function is idempotent per CallbackTask: once fired, the row flips to
status=in_progress so the next dispatcher cycle skips it. If the AI call
goes to voicemail / no-answer, the post-call workflow flips it back to
pending after the configured cooldown (TODO: post_call_handler).
"""
from __future__ import annotations

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

from broker_ops.models import CallbackTask, PropertyLead  # noqa: E402
from ai_caller import dial_consented  # noqa: E402
from weekly_cadence import is_consent_on_file  # noqa: E402


MAX_PER_CYCLE = int(os.environ.get("AI_CALL_PER_CYCLE", "5"))


def main() -> int:
    candidates = (
        CallbackTask.objects
        .filter(status="pending")
        .exclude(phone="")
        .order_by("-priority", "-created_at")[:50]
    )

    fired = 0
    skipped: list[str] = []
    succeeded: list[str] = []

    for cb in candidates:
        if fired >= MAX_PER_CYCLE:
            break

        consented, why = is_consent_on_file(phone=cb.phone, channel="ai_call")
        if not consented:
            skipped.append(f"{cb.id}:no_consent:{why}")
            continue

        # Pull state from the linked lead if available
        state = ""
        if cb.lead_id:
            try:
                lead = PropertyLead.objects.filter(id=cb.lead_id).first()
                if lead:
                    state = (lead.state or "").upper()
            except Exception:
                pass

        res = dial_consented(
            contact_phone=cb.phone,
            contact_state=state or "GA",
            contact_name=cb.contact_name or "",
            agent_role="seller_acquisition",
            lead_id=cb.lead_id or "",
        )
        if res.get("ok"):
            cb.status = "in_progress"
            note = f"\nAI dial fired call_sid={res.get('call_sid','')} conv_id={res.get('conversation_id','')}"
            cb.disposition_notes = (cb.disposition_notes or "") + note
            cb.save(update_fields=["status", "disposition_notes"])
            fired += 1
            succeeded.append(f"{cb.id}:{res.get('call_sid','')[:20]}")
        else:
            skipped.append(f"{cb.id}:dial_fail:{(res.get('error') or '')[:60]}")

    print(json.dumps({
        "ok": True,
        "fired": fired,
        "succeeded": succeeded,
        "skipped_count": len(skipped),
        "skipped_first_10": skipped[:10],
        "max_per_cycle": MAX_PER_CYCLE,
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
