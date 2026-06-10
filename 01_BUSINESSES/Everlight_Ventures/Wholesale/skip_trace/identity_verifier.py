"""
identity_verifier -- the integrity layer.

When `intel investigate "Linda Smith"` returns findings, those findings might
belong to ANY Linda Smith on the public internet. This module scores each
finding against known attributes of OUR specific lead and emits a confidence
score + matched signals.

Public API:
    verify_finding(lead_context, finding, investigator_id) -> dict
    verify_investigation(lead_context, results) -> dict

Per Operator Truth doctrine: never invent confidence. If we have no context,
return base score honestly. If signals don't match, reject and explain why.

lead_context shape (all keys optional):
    {
      "owner_name":    "Linda Smith",
      "address":       "123 Maple St",
      "city":          "Sacramento",
      "state":         "CA",
      "zip":           "95814",
      "owner_phone":   "9165550100",
      "owner_email":   "linda@example.com",
    }

Returns per-finding:
    {
      "confidence":      0..100,
      "matched_signals": ["name_exact_match", "state_match", ...],
      "rejected":        bool,
      "reason":          "why rejected, or '' if accepted",
      "base":            int,
      "boost":           int,
    }
"""
from __future__ import annotations

import difflib
import os
import re
from typing import Any

# Pull area-code-to-state map from existing owner_intel module
try:
    from ..pitches.owner_intel import AC_TO_STATE  # type: ignore
except (ImportError, ValueError):
    AC_TO_STATE = {}

# Default rejection threshold (env override allowed)
DEFAULT_THRESHOLD = int(os.environ.get("INTEL_VERIFY_THRESHOLD", "50"))

# Base confidence per investigator (no signal matches)
INVESTIGATOR_BASE = {
    "skip_trace":       40,   # cascade has its own confidence; we'll override below
    "property_records": 30,
    "leak_check":       20,
    "sec_edgar":        30,
    "opencorporates":   30,
    "social_recon":     25,
    "domain_intel":     50,   # domain match is binary, base already high
    "archive_org":      25,   # web presence is not identity proof
    "whois_lookup":     40,
    "google_dorks":     20,
}


def _normalize(s: str | None) -> str:
    if not s:
        return ""
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def _name_parts(full: str) -> tuple[str, str]:
    """Return (first, last) lowercase. Empty strings if malformed."""
    parts = (full or "").strip().split()
    if not parts:
        return "", ""
    if "," in (full or "") and len(parts) >= 2:
        last, first = (full.split(",", 1) + [""])[:2]
        return first.strip().lower(), last.strip().lower()
    return parts[0].lower(), parts[-1].lower() if len(parts) > 1 else ""


def _haystack(finding: dict) -> str:
    """Concatenate every text field of a finding into one searchable haystack."""
    bits = [
        str(finding.get("label", "")),
        str(finding.get("value", "")),
        str(finding.get("url", "")),
        str(finding.get("summary", "")),
        str(finding.get("title", "")),
    ]
    return " ".join(bits).lower()


def _fuzzy_match(a: str, b: str, threshold: float = 0.85) -> bool:
    if not a or not b:
        return False
    return difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio() >= threshold


def _phone_state(phone: str) -> str | None:
    digits = "".join(c for c in (phone or "") if c.isdigit())
    if len(digits) >= 10:
        return AC_TO_STATE.get(digits[-10:][:3])
    return None


# ---------- per-investigator scoring -----------------------------------------

def _score_skip_trace(lead: dict, finding: dict, hay: str, signals: list[str]) -> tuple[int, int]:
    """Skip-trace findings inherit cascade.trace_confidence if available."""
    raw_conf = finding.get("trace_confidence")
    if isinstance(raw_conf, (int, float)) and 0 <= raw_conf <= 1:
        base = int(round(raw_conf * 100))
    else:
        base = INVESTIGATOR_BASE["skip_trace"]
    # +20 if the phone in the finding matches lead phone
    boost = 0
    lead_phone = "".join(c for c in (lead.get("owner_phone", "") or "") if c.isdigit())
    if lead_phone and lead_phone[-10:] in re.sub(r"\D", "", hay)[-300:]:
        boost += 20; signals.append("phone_exact_match")
    return base, boost


def _score_generic(lead: dict, finding: dict, hay: str, signals: list[str], investigator_id: str) -> tuple[int, int]:
    base = INVESTIGATOR_BASE.get(investigator_id, 20)
    boost = 0

    # Name signals
    owner_name = (lead.get("owner_name") or "").strip()
    first, last = _name_parts(owner_name)
    full_lc = _normalize(owner_name)
    if owner_name and full_lc and full_lc in _normalize(hay):
        boost += 30; signals.append("name_exact_match")
    elif first and last:
        # fuzzy on combined first+last
        if _fuzzy_match(first + " " + last, _normalize(hay)[:200]):
            boost += 20; signals.append("name_fuzzy_match")

    # State match: 2-letter code or area code
    state = (lead.get("state") or "").upper()
    if state and len(state) == 2:
        if re.search(rf"\b{state}\b", hay.upper()):
            boost += 15; signals.append("state_match")
        else:
            # Phone area code present in hay?
            phones_in_hay = re.findall(r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b", hay)
            for p in phones_in_hay:
                if _phone_state(p) == state:
                    boost += 15; signals.append("state_match_via_phone")
                    break

    # City match
    city = (lead.get("city") or "").strip().lower()
    if city and len(city) >= 4 and city in hay:
        boost += 20; signals.append("city_match")

    # Address fuzzy match (street name portion only -- strip unit numbers)
    addr = (lead.get("address") or "").strip().lower()
    if addr:
        # Pull street name token (e.g., "123 maple st" -> "maple")
        m = re.match(r"^\d+\s+(\w+)", addr)
        street_word = m.group(1) if m else ""
        if street_word and len(street_word) >= 4 and street_word in hay:
            boost += 25; signals.append("address_fuzzy_match")

    # Email exact
    email = (lead.get("owner_email") or "").strip().lower()
    if email and "@" in email and email in hay:
        boost += 30; signals.append("email_exact_match")

    # Phone exact
    phone = "".join(c for c in (lead.get("owner_phone") or "") if c.isdigit())
    if phone and len(phone) >= 10:
        if phone[-10:] in re.sub(r"\D", "", hay):
            boost += 30; signals.append("phone_exact_match")

    return base, boost


def _score_entity(lead: dict, finding: dict, hay: str, signals: list[str], investigator_id: str) -> tuple[int, int]:
    """For company targets via opencorporates / sec_edgar."""
    base = INVESTIGATOR_BASE.get(investigator_id, 30)
    boost = 0
    target = (lead.get("owner_name") or lead.get("target") or "").strip().lower()
    if target and len(target) >= 3:
        if target in hay:
            boost += 25; signals.append("entity_match")
        elif _fuzzy_match(target, hay[:200]):
            boost += 15; signals.append("entity_fuzzy_match")
    # State match for SEC filings
    state = (lead.get("state") or "").upper()
    if state and len(state) == 2 and re.search(rf"\b{state}\b", hay.upper()):
        boost += 10; signals.append("state_match")
    return base, boost


# ---------- public API -------------------------------------------------------

def verify_finding(lead_context: dict, finding: dict, investigator_id: str,
                   threshold: int | None = None) -> dict:
    """Score one finding. Returns confidence + matched_signals + rejected flag."""
    threshold = threshold if threshold is not None else DEFAULT_THRESHOLD
    if not isinstance(lead_context, dict):
        lead_context = {}
    if not isinstance(finding, dict):
        finding = {}

    hay = _haystack(finding)
    signals: list[str] = []

    if investigator_id == "skip_trace":
        base, boost = _score_skip_trace(lead_context, finding, hay, signals)
    elif investigator_id in ("opencorporates", "sec_edgar"):
        base, boost = _score_entity(lead_context, finding, hay, signals, investigator_id)
    else:
        base, boost = _score_generic(lead_context, finding, hay, signals, investigator_id)

    # Cap at 100; clamp at 0
    confidence = max(0, min(100, base + boost))

    # If no context provided, signal that explicitly
    has_context = any(lead_context.get(k) for k in
                      ("owner_name", "address", "city", "state", "owner_phone", "owner_email"))
    if not has_context:
        signals.append("no_context_provided")
        confidence = min(confidence, base)  # base only, no boosts possible

    # Multi-signal requirement: single name_exact alone caps at 50 (could be different person)
    if not has_context:
        reason = "no_context_provided"
    elif signals == ["name_exact_match"] and confidence > 50:
        confidence = 50
        reason = ""
    elif signals == ["name_fuzzy_match"] and confidence > 40:
        confidence = 40
        reason = ""
    else:
        reason = ""

    rejected = confidence < threshold
    if rejected and not reason:
        if not signals or signals == ["no_context_provided"]:
            reason = "no_signals_matched"
        else:
            reason = f"below_threshold ({confidence} < {threshold})"

    return {
        "confidence": confidence,
        "matched_signals": signals,
        "rejected": rejected,
        "reason": reason,
        "base": base,
        "boost": boost,
        "investigator_id": investigator_id,
    }


def verify_investigation(lead_context: dict, results: list[dict],
                         threshold: int | None = None) -> dict:
    """
    Batch-verify every finding across every investigator. Returns the verified
    results (deep copy with verification block attached) + summary.
    """
    threshold = threshold if threshold is not None else DEFAULT_THRESHOLD
    if not isinstance(results, list):
        results = []

    out_results = []
    total = 0; verified = 0
    sum_conf = 0
    highest_per_signal: dict[str, int] = {}

    for inv in results:
        if not isinstance(inv, dict):
            continue
        iid = inv.get("investigator_id") or inv.get("investigator", "").lower().replace(" ", "_")
        verified_findings = []
        rejected_findings = []
        for f in inv.get("findings", []):
            v = verify_finding(lead_context, f, iid, threshold)
            total += 1
            sum_conf += v["confidence"]
            for sig in v["matched_signals"]:
                highest_per_signal[sig] = max(highest_per_signal.get(sig, 0), v["confidence"])
            scored = {**f, "verification": v}
            if v["rejected"]:
                rejected_findings.append(scored)
            else:
                verified += 1
                verified_findings.append(scored)
        out_results.append({
            **inv,
            "findings_verified": verified_findings,
            "findings_rejected": rejected_findings,
        })

    summary = {
        "total_findings": total,
        "verified": verified,
        "rejected": total - verified,
        "avg_confidence": int(sum_conf / total) if total else 0,
        "threshold": threshold,
        "highest_confidence_per_signal": highest_per_signal,
        "lead_context_keys_provided": [k for k in lead_context.keys() if lead_context.get(k)],
    }

    return {"results": out_results, "summary": summary}


# ---------- CLI smoke ---------------------------------------------------------

if __name__ == "__main__":
    import json
    import sys
    if len(sys.argv) < 2:
        print("usage: identity_verifier.py <owner_name> [--state=CA] [--city=Sacramento]")
        sys.exit(2)
    lead = {"owner_name": sys.argv[1]}
    for arg in sys.argv[2:]:
        if arg.startswith("--state="):
            lead["state"] = arg.split("=", 1)[1]
        elif arg.startswith("--city="):
            lead["city"] = arg.split("=", 1)[1]
    sample = {"label": "Profile match", "value": f"{sys.argv[1]} in {lead.get('city','?')}, {lead.get('state','?')}", "url": "https://example.com/u/x"}
    print(json.dumps(verify_finding(lead, sample, "social_recon"), indent=2))
