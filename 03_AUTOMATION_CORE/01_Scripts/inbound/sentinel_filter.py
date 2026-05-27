"""Decide whether an inbound email is a stranger worth surfacing.

triage_keep(msg) -> (keep: bool, reason: str)
  reason in {stranger_inbound, bulk_marketing, known_contact,
             critical_service_defer, no_signal}
Order matters: known + critical + bulk are dropped before we keep.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_KNOWN = _HERE / "known_contacts.json"

# Senders handled by critical_email_monitor (billing/legal/security). Deferred, not kept.
# Substring-by-design: matches only domains that START with "@brand." (brand-owned,
# e.g. notifications@stripe.com, alerts@aws.amazon.com). A stranger domain that merely
# contains the word (e.g. @mygithub-consulting.com) does NOT match -- no "@brand." prefix.
_CRITICAL_SENDER = re.compile(
    r"@(stripe|paypal|oracle|aws|amazonwebservices|namecheap|godaddy|cloudflare|"
    r"github|chase|bankofamerica|wellsfargo|capitalone|chime|irs|resend|sendgrid)\.",
    re.I,
)


def _load_known() -> dict:
    try:
        return json.loads(_KNOWN.read_text())
    except Exception as exc:
        # Fail loud: a missing/corrupt allowlist means known contacts get
        # surfaced as strangers. Make that visible instead of silent.
        print(f"sentinel_filter: known_contacts.json unreadable ({exc}); "
              f"treating all senders as unknown", file=sys.stderr)
        return {"domains": [], "emails": []}


def is_bulk_marketing(msg: dict) -> bool:
    if msg.get("list_unsubscribe"):
        return True
    if msg.get("precedence") in {"bulk", "list", "junk"}:
        return True
    return False


def is_known_contact(msg: dict, known: dict | None = None) -> bool:
    known = known or _load_known()
    sender = msg.get("from_email", "")
    if sender in {e.lower() for e in known.get("emails", [])}:
        return True
    domain = (sender.split("@")[-1] if "@" in sender else "").lower()
    return domain in {d.lower() for d in known.get("domains", [])}


def is_critical_service(msg: dict) -> bool:
    return bool(_CRITICAL_SENDER.search(msg.get("from_email", "")))


def triage_keep(msg: dict, known: dict | None = None) -> tuple[bool, str]:
    if is_known_contact(msg, known):
        return False, "known_contact"
    if is_critical_service(msg):
        return False, "critical_service_defer"
    if is_bulk_marketing(msg):
        return False, "bulk_marketing"
    # A stranger that got past the noise gates. Keep it.
    if msg.get("from_email"):
        return True, "stranger_inbound"
    return False, "no_signal"
