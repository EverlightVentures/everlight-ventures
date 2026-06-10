"""
Send Authority Gate -- Layer 3a of the outbound defense stack.

Born from the Marquise -> support@groundfloor.us rogue send on 2026-05-17.
Marquise is a back-of-house intel persona who, per v2 roster doctrine, must
NEVER email a counterparty. Something signed his name and pitched a Georgia
property to an REO lender, fully outside the canonical pipeline (zero entries
in branded_mailer_audit.jsonl, zero entries in resend_budget.jsonl).

This gate stops that bypass class permanently by enforcing:

  1. Persona must be a known sender in senders_authority.yaml.
  2. Persona must have status == "LIVE" (STAGING/FROZEN -> blocked).
  3. Recipient's state must be in the persona's allowed territory.
  4. Back-office personas (Marquise, Marcus, Lucrex, legal team, etc.)
     can NEVER appear as senders.

Architecture (5 layers of defense, this is Layer 3a):

  Layer 1: WHOLESALE_OUTBOUND_HALT env flag      -- top-level kill switch
  Layer 2: ERADICATED list (eradication_gate.py)  -- permanent DNC
  Layer 3: branded_mailer.send_branded_email()    -- canonical pipe
  Layer 3a: send_authority_gate.assert_authorized -- THIS FILE
  Layer 4: DNC + resend_guard                     -- recipient-class filter
  Layer 5: resend_budget                          -- monthly pacing

USAGE (from any send script):

    from send_authority_gate import assert_authorized, SendAuthorityViolation

    try:
        assert_authorized(
            persona_id="piper_reeves",
            recipient_email="seller@example.com",
            recipient_state="TN",
            caller="rex_negotiator.py",
        )
    except SendAuthorityViolation as e:
        # HARD HALT. Do not send. Alert operator.
        post_to_slack("#hive-alerts", f"AUTHORITY VIOLATION: {e}")
        raise

The YAML policy is authoritative for persona territory/status. The
back_office_never_send list is dual-stored (YAML + this file's
_HARDCODED_BACK_OFFICE) so a corrupted YAML cannot accidentally
promote a back-office persona.
"""
from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

log = logging.getLogger("send_authority_gate")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_WORKSPACE = Path("/mnt/sdcard/AA_MY_DRIVE")
_AUTHORITY_YAML = _WORKSPACE / "06_DEVELOPMENT/everlight_os/hive_mind/senders_authority.yaml"
_AUDIT_LOG = _WORKSPACE / "_logs/send_authority_gate.jsonl"

# Oracle fallback (when run from prod)
if not _AUTHORITY_YAML.exists():
    _alt = Path("/home/opc/hive/senders_authority.yaml")
    if _alt.exists():
        _AUTHORITY_YAML = _alt

# ---------------------------------------------------------------------------
# Hardcoded back-office blacklist. Dual-stored with YAML on purpose.
# A corrupted/missing YAML cannot accidentally promote one of these.
# ---------------------------------------------------------------------------
_HARDCODED_BACK_OFFICE: set[str] = {
    "marquise_reed",
    "marquise_reed_acquisitions",
    "marquise",
    "filter_banks",
    "cupid",
    "chart_dawson",
    "charles_dawson",
    "cash",
    "rex_blackwell",
    "rex",
    "penny",
    "marcus_cole",
    "marcus",
    "lucrex",
    "solomon_vale",
    "atlas_vega",
    "everlight_architect",
    "everlight_packager",
    "everlight_qa_gate",
    "everlight_content_director",
    "everlight_researcher",
    "everlight_saas_pm",
    "everlight_saas_builder",
    "everlight_saas_growth",
    "everlight_seo_formatter",
    "everlight_trading_risk",
    "ellie_vaughn",
    "bernie_kowalski",
    "mags_diaz",
    "mona_castile",
    "lupe_salazar",
    "walt_henning",
    "lo_hines",
    "legal_theo_briggs",
    "legal_imani_calder",
    "legal_lia_knight",
    "legal_priya_bhattacharya",
    "legal_wen_marsh",
    "legal_heck_aurelio",
}


class SendAuthorityViolation(Exception):
    """Raised when a send is attempted outside the authority policy."""


# ---------------------------------------------------------------------------
# Audit trail. Every gate call -- pass OR fail -- is logged.
# ---------------------------------------------------------------------------
def _audit(verdict: str, **fields) -> None:
    try:
        _AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
        row = {
            "ts_utc": datetime.now(timezone.utc).isoformat(),
            "verdict": verdict,
            "pid": os.getpid(),
            **fields,
        }
        with open(_AUDIT_LOG, "a") as f:
            f.write(json.dumps(row) + "\n")
    except Exception as e:  # never let audit logging break the gate
        log.warning("audit log write failed: %s", e)


# ---------------------------------------------------------------------------
# YAML loader -- intentionally permissive on missing yaml lib so the gate
# still functions on minimal Python installs. Hardcoded back-office check
# runs even if YAML loading fails.
# ---------------------------------------------------------------------------
def _load_policy() -> dict:
    if not _AUTHORITY_YAML.exists():
        return {}
    try:
        import yaml  # type: ignore
        with open(_AUTHORITY_YAML) as f:
            return yaml.safe_load(f) or {}
    except ImportError:
        log.warning("PyYAML missing -- running with hardcoded back-office check only")
        return {}
    except Exception as e:
        log.error("authority yaml load failed: %s", e)
        return {}


def _normalize_persona(persona_id: str) -> str:
    return (persona_id or "").strip().lower().replace("-", "_").replace(" ", "_")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def assert_authorized(
    *,
    persona_id: str,
    recipient_email: str,
    recipient_state: str = "",
    caller: str = "unknown",
    override: bool = False,
) -> bool:
    """Raise SendAuthorityViolation if the send is not authorized.

    Args:
        persona_id:      canonical persona id (e.g. "piper_reeves", "atlas_king").
                          Snake case. Case-insensitive match.
        recipient_email: the recipient address. Logged, not parsed.
        recipient_state: 2-letter state code of the recipient (TN, GA, etc.).
                          Used for territory check. If empty, territory check
                          is SKIPPED (but persona/status/back-office checks
                          still run).
        caller:          script name that invoked the send. Audit only.
        override:        operator break-glass. Requires
                          OPERATOR_OVERRIDE_TOKEN env var to be set.

    Returns:
        True on authorization. Raises on denial.
    """
    pid = _normalize_persona(persona_id)
    state = (recipient_state or "").strip().upper()

    base_fields = {
        "persona_id": pid,
        "to": recipient_email,
        "state": state,
        "caller": caller,
    }

    # ---- Operator override (Rich only) ----
    if override:
        token = os.environ.get("OPERATOR_OVERRIDE_TOKEN", "").strip()
        if not token:
            _audit("override_rejected_no_token", **base_fields)
            raise SendAuthorityViolation(
                "override=True requested but OPERATOR_OVERRIDE_TOKEN env var is missing. "
                "Operator must set the token to break glass."
            )
        _audit("override_granted", token_present=True, **base_fields)
        return True

    # ---- Hardcoded back-office check (runs even if YAML fails) ----
    if pid in _HARDCODED_BACK_OFFICE:
        _audit("blocked_back_office_hardcoded", **base_fields)
        raise SendAuthorityViolation(
            f"persona_id={pid!r} is BACK-OFFICE per Constitutional roster v2. "
            f"Back-office personas never email counterparties. "
            f"Caller={caller}. To send to {recipient_email} ({state}), "
            f"route through the designated front-of-house sender for that territory."
        )

    # ---- YAML-driven policy ----
    policy = _load_policy()
    senders = policy.get("senders", {}) or {}

    # ---- TN-ONLY LOCKDOWN (2026-05-18 operator order, expires 2026-06-17) ----
    # This is an EXTRA layer on top of per-persona territory. While active,
    # any send to a non-TN state is blocked regardless of who's sending.
    # Internal-only personas (system_router, compliance buddies) bypass this
    # because they don't email counterparties.
    lockdown = policy.get("lockdown", {}) or {}
    if lockdown.get("tn_only") and state:
        exception_states = {s.upper() for s in (lockdown.get("exception_states") or [])}
        allowed = {"TN"} | exception_states
        # internal_only personas don't touch counterparties; skip this gate for them
        is_internal_persona = (senders.get(pid) or {}).get("internal_only", False)
        if not is_internal_persona and state not in allowed:
            _audit(
                "blocked_tn_lockdown",
                lockdown_set_at=lockdown.get("set_at"),
                lockdown_expires_at=lockdown.get("expires_at"),
                allowed=sorted(allowed),
                **base_fields,
            )
            raise SendAuthorityViolation(
                f"TN-only lockdown is active (set {lockdown.get('set_at')!r}, "
                f"expires {lockdown.get('expires_at')!r}). Recipient state {state!r} "
                f"is not in allowed={sorted(allowed)}. "
                f"Lift in senders_authority.yaml > lockdown.tn_only after Deal 1. "
                f"Caller={caller}."
            )

    # Defense in depth: re-check YAML back-office list
    yaml_back_office = {_normalize_persona(p) for p in policy.get("back_office_never_send", [])}
    if pid in yaml_back_office:
        _audit("blocked_back_office_yaml", **base_fields)
        raise SendAuthorityViolation(
            f"persona_id={pid!r} is in back_office_never_send (yaml). Caller={caller}."
        )

    # Unknown persona = fail closed
    if pid not in senders:
        _audit("blocked_unknown_persona", policy_loaded=bool(policy), **base_fields)
        raise SendAuthorityViolation(
            f"persona_id={pid!r} is not a registered sender in senders_authority.yaml. "
            f"Add the persona with explicit status + territory before sending. "
            f"Caller={caller}."
        )

    record = senders[pid] or {}

    # Status must be LIVE
    status = (record.get("status") or "").upper()
    if status != "LIVE":
        _audit(
            "blocked_not_live",
            persona_status=status,
            promote_blocker=record.get("promote_blocker"),
            **base_fields,
        )
        raise SendAuthorityViolation(
            f"persona_id={pid!r} has status={status!r}, not LIVE. "
            f"Promote_blocker: {record.get('promote_blocker','(none specified)')!r}. "
            f"Operator must promote to LIVE in senders_authority.yaml before sending. "
            f"Caller={caller}."
        )

    # Internal-only check: system_router and similar may ONLY send to @everlightventures.io
    if record.get("internal_only"):
        if not recipient_email.lower().strip().endswith("@everlightventures.io"):
            _audit("blocked_internal_only", **base_fields)
            raise SendAuthorityViolation(
                f"persona_id={pid!r} is internal_only -- recipient {recipient_email!r} "
                f"is not @everlightventures.io. Caller={caller}."
            )

    # Territory check (only if state was provided)
    territory_raw = record.get("territory") or []
    if isinstance(territory_raw, str):
        territory_raw = [territory_raw]
    territory = {str(s).upper() for s in territory_raw}

    if state and territory and "ALL" not in territory:
        if state not in territory:
            _audit("blocked_wrong_territory", allowed=sorted(territory), **base_fields)
            raise SendAuthorityViolation(
                f"persona_id={pid!r} territory is {sorted(territory)}, "
                f"but recipient state is {state!r}. "
                f"Route to the designated agent for {state}. "
                f"Caller={caller}."
            )

    _audit("authorized", allowed=sorted(territory) if territory else ["(any)"], **base_fields)
    return True


def is_back_office(persona_id: str) -> bool:
    """Convenience: True if persona is structurally a non-sender."""
    return _normalize_persona(persona_id) in _HARDCODED_BACK_OFFICE


def derive_persona_id(from_email: str, agent_name: str = "") -> str:
    """Best-effort persona_id from a from_email / agent_name pair.

    Used by branded_mailer when the caller didn't pass persona_id explicitly.
    Examples:
      ("piper@everlightventures.io", "Piper Reeves") -> "piper_reeves"
      ("henry@everlightventures.io", "")             -> "henry_hammond"
      ("noreply@everlightventures.io", "")           -> "" (forces caller to be explicit)
    """
    if agent_name:
        guess = _normalize_persona(agent_name)
        if guess and guess not in {"everlight_ventures", "automated_intelligence"}:
            return guess

    local = (from_email or "").split("@", 1)[0].lower()
    # Map known local parts to canonical persona ids
    LOCAL_MAP = {
        "piper": "piper_reeves",
        "henry": "henry_hammond",
        "marvin": "marvin_cohen",
        "vaughn": "vaughn_sterling",
        "king": "atlas_king",
        "atlas": "atlas_king",
        "daria": "daria_voss",
        "cleo": "cleo_vance",
        "jasper": "jasper_reeves",
        "phin": "phin_reyes",
        "stella": "stella_marquez",
    }
    return LOCAL_MAP.get(local, "")


# ---------------------------------------------------------------------------
# CLI for self-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="Send Authority Gate self-test")
    p.add_argument("--persona", required=True, help="persona_id to test")
    p.add_argument("--to", required=True, help="recipient email")
    p.add_argument("--state", default="", help="recipient state (TN, GA, etc.)")
    p.add_argument("--override", action="store_true", help="apply operator override")
    args = p.parse_args()

    try:
        assert_authorized(
            persona_id=args.persona,
            recipient_email=args.to,
            recipient_state=args.state,
            caller="send_authority_gate.cli",
            override=args.override,
        )
        print(f"OK    -> {args.persona} authorized to send to {args.to} ({args.state or 'any'})")
        sys.exit(0)
    except SendAuthorityViolation as e:
        print(f"BLOCK -> {e}")
        sys.exit(1)
