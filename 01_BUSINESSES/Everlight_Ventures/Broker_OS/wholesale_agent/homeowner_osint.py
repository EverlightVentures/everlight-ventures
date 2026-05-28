"""
homeowner_osint.py -- Wholesale pipeline adapter: owner name -> normalized identity result.

Wraps osint_api.orchestrator.run_investigation_sync and normalizes the raw
investigator payloads into a single contract dict the downstream email gate
and outreach agents consume.

Contract shape returned by resolve():
    {
        "candidate_emails": [
            {"email": str, "confidence": int|None, "verified": bool, "sources": list},
            ...
        ],
        "identity_score": int,          # 0-100 from profile_depth.score()["overall_score"]
        "verdict": str,                 # from profile_depth or "osint_unavailable"
        "raw_investigation_id": str,
    }

On any failure (missing libs, network error, empty results) the function returns
the same shape with empty candidates and identity_score=0. It never raises.

How emails are extracted from osint_api payloads
-------------------------------------------------
run_investigation_sync returns a list of per-investigator payload dicts. The
email_discovery investigator payload has:
    payload["investigator_id"] == "email_discovery"
    payload["raw"]["full_results"] = [
        {
            "email": str,
            "score": int(0-100),         # email deliverability confidence
            "mx_ok": bool,
            "emailrep": {"reputation": str, "suspicious": bool, "deliverable": bool|None},
            "hibp_exists": bool|None,
            "summary": str,
        },
        ...
    ]

We map email_discovery.score -> candidate["confidence"], and we derive
"verified" as True when emailrep.deliverable is True OR hibp_exists is True.
This matches the logic in email_discovery._score_candidate (the same signals
that add points are the same signals that confirm deliverability).

"sources" is constructed from the signals that fired for each candidate so the
gate has a human-readable audit trail.

identity_score comes from profile_depth.score() if the synthesizer is available,
otherwise we derive a simple heuristic from the investigation payload.
"""
from __future__ import annotations

import sys
import os
from typing import Any

# ---------------------------------------------------------------------------
# Path injection so we can import osint_api from its intel_center home
# ---------------------------------------------------------------------------
_INTEL_CENTER = "/mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/intel_center"
if _INTEL_CENTER not in sys.path:
    sys.path.insert(0, _INTEL_CENTER)

# We also need the wholesale package itself (for skip_trace etc.) -- osint_api
# already does this internally, but we insert it here so our error-handling
# path stays clean.
_WHOLESALE_ROOT = "/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale"
if _WHOLESALE_ROOT not in sys.path:
    sys.path.insert(0, _WHOLESALE_ROOT)


_EMPTY_RESULT: dict = {
    "candidate_emails": [],
    "identity_score": 0,
    "verdict": "osint_unavailable",
    "raw_investigation_id": "",
}


def _derive_verified(raw_candidate: dict) -> bool:
    """
    A candidate is considered 'verified deliverable' when at least one hard
    signal confirmed the mailbox exists:
      - EmailRep reported deliverable=True
      - HIBP confirmed the account appeared in a breach (existence proof)
    mx_ok alone is NOT sufficient (catch-all servers accept anything).
    """
    emailrep = raw_candidate.get("emailrep") or {}
    if emailrep.get("deliverable") is True:
        return True
    if raw_candidate.get("hibp_exists") is True:
        return True
    return False


def _build_sources(raw_candidate: dict) -> list:
    """Build a human-readable list of signals that fired for this candidate."""
    sources = []
    if raw_candidate.get("mx_ok"):
        sources.append("mx_check")
    emailrep = raw_candidate.get("emailrep") or {}
    if emailrep.get("deliverable") is True:
        sources.append("emailrep_deliverable")
    if emailrep.get("reputation") in ("high", "medium"):
        sources.append(f"emailrep_rep_{emailrep['reputation']}")
    if raw_candidate.get("hibp_exists") is True:
        sources.append("hibp_exists")
    return sources


def _extract_emails(result_payloads: list[dict]) -> list[dict]:
    """
    Walk the list of investigator payloads and pull candidate emails from the
    email_discovery payload's raw["full_results"].

    Falls back gracefully: if full_results is absent, tries to parse the top-3
    findings text as a last resort (findings["value"] contains the email address
    before the first space character).

    Returns a list of normalized candidate dicts:
        [{"email": str, "confidence": int|None, "verified": bool, "sources": list}]
    sorted by confidence descending.
    """
    candidates: list[dict] = []

    for payload in (result_payloads or []):
        if not isinstance(payload, dict):
            continue
        iid = payload.get("investigator_id") or ""
        if iid != "email_discovery":
            continue

        # Primary path: full_results in raw
        raw = payload.get("raw") or {}
        full_results = raw.get("full_results") or []

        if full_results:
            for r in full_results:
                email = (r.get("email") or "").strip().lower()
                if not email or "@" not in email:
                    continue
                candidates.append({
                    "email": email,
                    "confidence": r.get("score"),   # email_discovery uses "score"
                    "verified": _derive_verified(r),
                    "sources": _build_sources(r),
                })
        else:
            # Fallback: parse findings text  "candidate@domain.com (MX->...)"
            # Assumption: email is the token before the first space inside value.
            for finding in payload.get("findings") or []:
                value = (finding.get("value") or "").strip()
                email_part = value.split("(")[0].strip().split()[0] if value else ""
                if "@" in email_part:
                    candidates.append({
                        "email": email_part.lower(),
                        "confidence": None,   # no numeric score available in text
                        "verified": False,
                        "sources": ["findings_text_fallback"],
                    })

    # Sort best confidence first; None treated as 0 for ordering
    candidates.sort(key=lambda c: (c.get("confidence") or 0), reverse=True)
    return candidates


def _extract_identity_score(result_payloads: list[dict]) -> tuple[int, str]:
    """
    Run profile_depth.score() against the aggregated results to get the overall
    identity confidence score.

    Returns (overall_score, verdict).
    Degrades gracefully: returns (0, "osint_unavailable") on any failure.
    """
    try:
        from osint_api.profile_depth import score as depth_score  # type: ignore
        from osint_api.profile_synthesizer import synthesize  # type: ignore

        # Build a minimal investigation payload the synthesizer expects
        mock_payload = {
            "target": "",
            "kind": "person",
            "investigation_id": "",
            "started_at": "",
            "elapsed_ms": 0,
            "triggered_by": "homeowner_osint",
            "lead_id": None,
            "dnc_blocked": False,
            "dnc_reason": "",
            "results": result_payloads or [],
            "verify_context": {},
            "verification_summary": {},
            "business_purpose": "wholesale_lead_enrichment",
        }
        profile = synthesize(mock_payload)
        depth = profile.get("depth") or {}
        overall = int(depth.get("overall_score") or 0)
        verdict = str(depth.get("verdict") or "unknown")
        return overall, verdict
    except Exception:
        # Graceful fallback: count verified findings heuristically
        try:
            verified_count = sum(
                len([f for f in p.get("findings", []) if p.get("ok")])
                for p in (result_payloads or [])
                if isinstance(p, dict)
            )
            heuristic_score = min(verified_count * 15, 60)
            return heuristic_score, "osint_heuristic"
        except Exception:
            return 0, "osint_unavailable"


def resolve(
    name: str,
    address: str = "",
    city: str = "",
    state: str = "",
    mailing_address: str = "",
    lead_id: Any = None,
) -> dict:
    """
    Run the owner name through osint_api anchored on the property/mailing
    address, then normalize the output into the wholesale pipeline contract:

        {
            "candidate_emails": [{"email", "confidence", "verified", "sources"}, ...],
            "identity_score": int,
            "verdict": str,
            "raw_investigation_id": str,
        }

    Parameters
    ----------
    name : str
        Owner name as it appears on the assessor record, e.g. "HOWARD EDDIE".
    address : str
        Property address -- used as a verification anchor to disambiguate
        common names.
    city : str
        Property city.
    state : str
        Property state (2-letter code preferred, e.g. "TN").
    mailing_address : str
        Owner's mailing/out-of-state address if different from property.
    lead_id : any
        Passed through to the investigation record for audit linkage.

    Returns
    -------
    dict
        Contract dict. Never raises -- on any error returns empty-but-valid dict
        with verdict="osint_unavailable".
    """
    if not (name or "").strip():
        empty = dict(_EMPTY_RESULT)
        empty["verdict"] = "no_name_provided"
        return empty

    try:
        from osint_api.orchestrator import run_investigation_sync  # type: ignore
    except Exception:
        return dict(_EMPTY_RESULT)

    verify_context: dict = {}
    if address:
        verify_context["address"] = address
    if city:
        verify_context["city"] = city
    if state:
        verify_context["state"] = state
    if mailing_address:
        verify_context["mailing_address"] = mailing_address

    prior_addresses = [mailing_address] if mailing_address else None

    try:
        result_payloads, investigation_id = run_investigation_sync(
            target=name.strip(),
            kind="person",
            triggered_by="homeowner_osint",
            lead_id=lead_id,
            verify_context=verify_context if verify_context else None,
            business_purpose=(
                "wholesale_lead_enrichment: locate owner contact for direct acquisition offer"
            ),
            prior_addresses=prior_addresses,
        )
    except Exception:
        return dict(_EMPTY_RESULT)

    if not result_payloads:
        return dict(_EMPTY_RESULT)

    candidate_emails = _extract_emails(result_payloads)
    identity_score, verdict = _extract_identity_score(result_payloads)

    return {
        "candidate_emails": candidate_emails,
        "identity_score": identity_score,
        "verdict": verdict,
        "raw_investigation_id": investigation_id or "",
    }
