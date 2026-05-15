"""
Eradication Gate -- the last line of defense against contacting a permanently DNC'd subject.

Born from the Streubel 2nd-strike on 2026-05-15. Three prior operator commands ("never
contact David A. Streubel") were honored in their moment by writing to dnc_list.json,
opted_out_emails.json, and recipient_classifier.py. Then a 4th code path
(rex_belfort_sequence.py Day-2 follow-up) bypassed all three by calling api.resend.com
directly without invoking the canonical branded_mailer pipeline.

THIS MODULE EXISTS SO THAT BYPASS CANNOT HAPPEN AGAIN.

Architecture (4 layers of defense, this is Layer 2):

  Layer 1: WHOLESALE_OUTBOUND_HALT env flag      -- top-level kill switch
  Layer 2: ERADICATED list HARDCODED IN PYTHON   -- this file
  Layer 3: branded_mailer.send_branded_email()   -- the canonical pipe, gates Layer 2
  Layer 4: memory_gate at /root/.claude/...      -- reads MEMORY.md eradication entries

Every outbound script MUST call eradication_gate.assert_safe(...) BEFORE sending.
The gate raises EradicationViolation and writes to the audit log if a hit occurs.

USAGE (from any send script):

    from eradication_gate import assert_safe, EradicationViolation

    try:
        assert_safe(email=to, address=property_address, lead_id=lead_id)
    except EradicationViolation as e:
        # HARD HALT. Do not send. Alert operator.
        post_to_slack("#hive-alerts", f"ERADICATION VIOLATION: {e}")
        raise

The list is intentionally HARDCODED -- not loaded from JSON -- because JSON files can
be overwritten, missing, corrupted, or simply not consulted. Source code edits leave
a git trail and require deliberate intent.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

log = logging.getLogger("eradication_gate")

# ---------------------------------------------------------------------------
# THE LIST. Forever-DNC contacts. Hardcoded. Do not remove without operator sign-off.
# Each entry is matched against multiple fields: email (exact + domain), name (case-
# insensitive substring), address (case-insensitive substring), lead_id (exact).
# ---------------------------------------------------------------------------
ERADICATED: list[dict] = [
    {
        # Strike chain: 1st outreach 2026-04-24 -> "no" reply. 2nd outreach 2026-04-26 ->
        # threatened BBB complaint. Operator: "delete and never contact again."
        # 2nd-strike outreach 2026-05-15 (rex_belfort Day-2 follow-up bypass) ->
        # "wtf - No thanks. No need to contact me again." This entry exists so there is
        # no 3rd strike.
        "subject_name": "David A. Streubel",
        "emails": ["dave@municipalfirm.com"],
        "domains": ["municipalfirm.com", "cunninghamvogel.com"],
        "addresses": ["4435 westminster pl", "4435 westminster"],
        "lead_ids": ["leg_afee1a472d"],
        "name_substrings": ["streubel"],
        "reason": "BBB complainant. 3 operator commands. Permanent eradication. All channels.",
        "since": "2026-04-26",
        "memory_ref": "feedback-streubel-permanent-eradication",
    },
]


class EradicationViolation(Exception):
    """Raised when an outbound action targets a permanently-eradicated subject."""


# ---------------------------------------------------------------------------
# Audit trail. Every gate call -- pass OR fail -- is logged.
# ---------------------------------------------------------------------------
AUDIT_LOG = Path(
    os.environ.get(
        "ERADICATION_GATE_AUDIT_LOG",
        "/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale/compliance/eradication_gate_audit.log",
    )
)


def _audit(event: str, payload: dict) -> None:
    try:
        AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
        row = {
            "ts_utc": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "payload": payload,
        }
        with AUDIT_LOG.open("a") as fh:
            fh.write(json.dumps(row) + "\n")
    except Exception:
        # Never let audit failure mask a real violation. Best-effort logging.
        pass


# ---------------------------------------------------------------------------
# Layer 1 check -- env halt
# ---------------------------------------------------------------------------
def outbound_halted() -> bool:
    return os.environ.get("WHOLESALE_OUTBOUND_HALT", "").strip() in {"1", "true", "TRUE", "yes"}


# ---------------------------------------------------------------------------
# Layer 2 check -- the hardcoded list
# ---------------------------------------------------------------------------
def _match(value: Optional[str], needles: list[str], mode: str = "exact") -> bool:
    if not value:
        return False
    v = value.strip().lower()
    if not v:
        return False
    if mode == "exact":
        return any(v == n.lower() for n in needles)
    if mode == "substring":
        return any(n.lower() in v for n in needles)
    if mode == "domain":
        # match "foo@x.com" against domain "x.com"
        return any(v.endswith("@" + n.lower()) or v == n.lower() for n in needles)
    return False


def find_hit(
    email: Optional[str] = None,
    name: Optional[str] = None,
    address: Optional[str] = None,
    lead_id: Optional[str] = None,
    phone: Optional[str] = None,
) -> Optional[dict]:
    """
    Return the eradication record if any field matches; else None.
    Match is OR across fields (any single hit kills the send).
    """
    for record in ERADICATED:
        if email and _match(email, record.get("emails", []), mode="exact"):
            return record
        if email and _match(email, record.get("domains", []), mode="domain"):
            return record
        if name and _match(name, record.get("name_substrings", []), mode="substring"):
            return record
        if address and _match(address, record.get("addresses", []), mode="substring"):
            return record
        if lead_id and _match(lead_id, record.get("lead_ids", []), mode="exact"):
            return record
    return None


def assert_safe(
    email: Optional[str] = None,
    name: Optional[str] = None,
    address: Optional[str] = None,
    lead_id: Optional[str] = None,
    phone: Optional[str] = None,
    caller: Optional[str] = None,
) -> None:
    """
    Top-level guard. Call BEFORE any outbound send. Raises EradicationViolation on hit.

    Also enforces Layer 1 (env halt). If WHOLESALE_OUTBOUND_HALT=1 and the caller did
    not pass override=True, the send is blocked.
    """
    caller = caller or "unknown"

    # Layer 1 -- env halt
    if outbound_halted():
        _audit("halted_by_env", {"caller": caller, "email": email, "address": address})
        raise EradicationViolation(
            f"WHOLESALE_OUTBOUND_HALT=1 active. Send from {caller!r} blocked. "
            f"Lift halt only after operator greenlight."
        )

    # Layer 2 -- hardcoded list
    hit = find_hit(email=email, name=name, address=address, lead_id=lead_id, phone=phone)
    if hit:
        _audit(
            "violation",
            {
                "caller": caller,
                "email": email,
                "name": name,
                "address": address,
                "lead_id": lead_id,
                "phone": phone,
                "matched_record": hit["subject_name"],
                "reason": hit["reason"],
                "memory_ref": hit.get("memory_ref"),
            },
        )
        raise EradicationViolation(
            f"ERADICATION VIOLATION: attempted contact with {hit['subject_name']} "
            f"from {caller!r}. Reason: {hit['reason']}. "
            f"Memory: {hit.get('memory_ref')}. "
            f"Email={email}, address={address}, lead_id={lead_id}."
        )

    _audit("pass", {"caller": caller, "email": email, "address": address, "lead_id": lead_id})


# ---------------------------------------------------------------------------
# CLI for self-test and audit
# ---------------------------------------------------------------------------
def selftest() -> int:
    """Confirm the gate trips on Streubel and passes on a clean contact."""
    failures = 0

    cases = [
        # (label, kwargs, expect_violation)
        ("streubel_email", {"email": "dave@municipalfirm.com"}, True),
        ("streubel_email_caps", {"email": "Dave@MunicipalFirm.com"}, True),
        ("streubel_domain", {"email": "anyone@municipalfirm.com"}, True),
        ("streubel_name", {"name": "David A. Streubel"}, True),
        ("streubel_address", {"address": "4435 WESTMINSTER PL, SAINT LOUIS, MO 63108"}, True),
        ("streubel_lead_id", {"lead_id": "leg_afee1a472d"}, True),
        ("clean_homeowner", {"email": "owner@gmail.com", "address": "123 Main St"}, False),
    ]

    # Force halt off for selftest so we exercise Layer 2 in isolation.
    saved = os.environ.pop("WHOLESALE_OUTBOUND_HALT", None)
    try:
        for label, kwargs, expect in cases:
            kwargs["caller"] = f"selftest:{label}"
            try:
                assert_safe(**kwargs)
                got = False
            except EradicationViolation:
                got = True
            ok = got == expect
            print(f"  [{'PASS' if ok else 'FAIL'}] {label}: expected_violation={expect}, got={got}")
            if not ok:
                failures += 1
    finally:
        if saved is not None:
            os.environ["WHOLESALE_OUTBOUND_HALT"] = saved

    if failures:
        print(f"\nFAILED: {failures} case(s)")
        return 1
    print("\nALL PASS")
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "selftest":
        sys.exit(selftest())
    print("Usage: python3 eradication_gate.py selftest")
    sys.exit(2)
