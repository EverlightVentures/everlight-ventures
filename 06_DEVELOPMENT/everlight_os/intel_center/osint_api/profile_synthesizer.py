"""
profile_synthesizer -- turn raw investigation findings into a structured Profile.

The OSINT API returns per-investigator findings as flat key/value rows. That's
useful for debugging but ugly for humans. This module distills those findings
into named sections an operator can scan in 30 seconds:

    - Identity        (subject info + DNC banner)
    - Contact         (email/phone/addresses with confidence)
    - Online Presence (verified social profiles, web mentions)
    - Property        (addresses owned / linked)
    - Business        (corporate filings, SEC, OpenCorporates)
    - Risk Signals    (breaches, threat intel, archive history)
    - Verification    (what we matched on, what we rejected, why)
    - Sources         (which investigators ran, elapsed time, dead ones)

Public API:
    synthesize(investigation_payload) -> dict
"""
from __future__ import annotations

from datetime import datetime
from typing import Any


def _bucket(inv_id: str) -> str:
    """Map investigator_id -> profile section."""
    return {
        "skip_trace":         "contact",
        "property_records":   "property",
        "public_records":     "risk",        # court records, business filings -> risk
        "leak_check":         "risk",
        "sec_edgar":          "business",
        "opencorporates":     "business",
        "social_recon":       "online",
        "social_bio_scraper": "online",      # bio + interests + location
        "domain_intel":       "risk",
        "archive_org":        "online",
        "whois_lookup":       "online",
        "google_dorks":       "online",
        "resource_lookup":    "research",
    }.get(inv_id, "online")


def _confidence_class(conf: int | None) -> str:
    if conf is None:
        return "neutral"
    if conf >= 70: return "high"
    if conf >= 50: return "medium"
    return "low"


def _is_garbage(finding: dict, investigator_id: str, target: str) -> tuple[bool, str]:
    """
    Spot the ugly: dead links, auth-gated dummies, irrelevant archive results,
    raw .json dumps. Returns (is_garbage, reason).
    """
    val = (finding.get("value") or "").lower()
    label = (finding.get("label") or "").lower()
    url = (finding.get("url") or "").lower()
    target_lc = (target or "").lower()
    target_tokens = set(t for t in target_lc.split() if len(t) > 2)

    if "login required" in val or "login required" in label:
        return True, "auth_gated"
    if "http 403" in val or "http 404" in val or "http 5" in val:
        return True, "dead_link"
    if url.endswith(".json") and "archive.org" in url:
        return True, "raw_json_dump"
    # Archive.org "items" with no target-name overlap = irrelevant book/audio
    if investigator_id == "archive_org" and label == "archive item":
        if not any(t in val for t in target_tokens):
            return True, "irrelevant_archive_item"
    # Generic "Search (login required)" links
    if val.strip() == "search" or val.strip() == "search (login required)":
        return True, "manual_lookup_only"
    return False, ""


def _humanize_url(url: str) -> tuple[str, str]:
    """
    For ugly URLs (raw JSON, court dockets), return (humanized_url, label).
    Otherwise return (url, '').
    """
    if not url:
        return url, ""
    u = url.lower()
    # Archive.org JSON -> details page
    if u.endswith(".json") and "archive.org" in u and "/items/" in u:
        item_id = url.split("/items/")[-1].split("/")[0]
        return f"https://archive.org/details/{item_id}", "Archive.org item"
    # PACER court docket
    if "uscourts." in u and ".docket.json" in u:
        case_id = url.split("/items/")[-1].split("/")[0] if "/items/" in url else ""
        return f"https://www.courtlistener.com/?q={case_id}", "Court docket (CourtListener)"
    return url, ""


def _build_tldr(target: str, kind: str, sections: dict, stats: dict,
                  verification_summary: dict, dnc_blocked: bool, state_rules: dict | None) -> dict:
    """
    Plain-English summary the operator can read in 30 seconds.
    No jargon, no chips, no math. Just: who, what, trust, what to do.
    """
    verified_count = stats.get("verified_findings", 0)
    raw_count = stats.get("total_findings", 0)
    high_conf = stats.get("high_confidence", 0)

    # WHO
    if kind == "person":
        who = f"{target} appears to be an individual."
    elif kind == "company":
        who = f"{target} appears to be a company or entity."
    elif kind == "address":
        who = f"{target} is a property address."
    elif kind == "domain":
        who = f"{target} is an internet domain."
    elif kind == "email":
        who = f"{target} is an email address."
    else:
        who = f"{target} (kind: {kind})."

    # WHAT WE FOUND -- counts per section
    bits = []
    n_social = len(sections.get("online", []))
    n_property = len(sections.get("property", []))
    n_risk = len(sections.get("risk", []))
    n_business = len(sections.get("business", []))
    n_contact = len(sections.get("contact", []))
    if n_social: bits.append(f"{n_social} online presence signal{'s' if n_social!=1 else ''}")
    if n_property: bits.append(f"{n_property} property record{'s' if n_property!=1 else ''}")
    if n_risk: bits.append(f"{n_risk} risk signal{'s' if n_risk!=1 else ''}")
    if n_business: bits.append(f"{n_business} business filing{'s' if n_business!=1 else ''}")
    if n_contact: bits.append(f"{n_contact} contact channel{'s' if n_contact!=1 else ''}")
    what_found = "We surfaced " + (", ".join(bits) if bits else "no verified signals") + "."

    # TRUST -- how much can you trust this?
    if dnc_blocked:
        trust = "⛔ This person is on the Everlight DNC list. The data below is for KNOWLEDGE ONLY -- no contact permitted on any channel."
    elif raw_count == 0:
        trust = "Nothing returned from any investigator. Either the target is genuinely off-grid, or all sources were blocked. Try again with more lead context (state + city + email)."
    elif verified_count == 0:
        trust = (f"None of the {raw_count} raw findings could be verified as belonging to THIS specific {kind}. "
                 "The internet has multiple people/entities with this name. Add more lead context "
                 "(state, city, email, phone) to filter further before acting on any signal.")
    elif high_conf > 0:
        trust = f"{verified_count} of {raw_count} findings passed identity verification, with {high_conf} at high confidence (≥70%). Treat the verified items as actionable; the rest is raw data for the operator to verify manually."
    else:
        trust = f"{verified_count} of {raw_count} findings passed identity verification at medium confidence. Review them; do not treat as ground truth."

    # WHAT TO DO -- action recommendations from state + DNC
    action_lines = []
    if dnc_blocked:
        action_lines.append("**No contact permitted.** This entry is permanent DNC.")
    elif state_rules:
        if not state_rules.get("covered"):
            action_lines.append(f"**State unknown** -- consult Justine before contacting. All channels treated as blocked.")
        else:
            ch = state_rules.get("channels_allowed", {})
            allowed_ch = [k.replace("_", " ") for k, v in ch.items() if v is True]
            blocked_ch = [k.replace("_", " ") for k, v in ch.items() if v is False]
            if allowed_ch:
                action_lines.append(f"**Allowed channels in {state_rules.get('state','?')}**: " + ", ".join(allowed_ch))
            if blocked_ch:
                action_lines.append(f"**BLOCKED channels** (state law): " + ", ".join(blocked_ch))
            for r in state_rules.get("active_restrictions", [])[:3]:
                action_lines.append(f"⚠ {r.get('statute','')}: {r.get('summary','')}")
    else:
        action_lines.append("**No state context provided** -- re-run with `--verify-state=XX` to get per-state contact rules.")

    return {
        "who": who,
        "what_found": what_found,
        "trust": trust,
        "action_lines": action_lines,
    }


def synthesize(payload: dict) -> dict:
    """
    Take an investigation payload (as written to cache/investigations/<id>.json)
    and return a structured Profile dict ready for HTML rendering.
    """
    if not isinstance(payload, dict):
        return {"error": "no payload"}

    target = payload.get("target", "(unknown)")
    kind = payload.get("kind", "unknown")
    inv_id = payload.get("investigation_id", "")
    started = payload.get("started_at", "")
    elapsed = payload.get("elapsed_ms", 0)
    triggered_by = payload.get("triggered_by", "unknown")
    lead_id = payload.get("lead_id")
    verification_summary = payload.get("verification_summary") or {}
    results = payload.get("results", []) or []

    # DNC short-circuit (look across results in case any investigator surfaced it)
    # We don't have direct DNC info here; the wholesale enricher writes it separately.
    # For the OSINT report view, a banner appears only if business_purpose explicitly
    # marked dnc.
    dnc_blocked = bool(payload.get("dnc_blocked"))
    dnc_reason = payload.get("dnc_reason", "")

    # Section buckets
    sections: dict[str, list] = {
        "identity": [], "contact": [], "online": [], "property": [],
        "business": [], "risk": [], "research": [],
    }

    sources_run = []
    rejected_count = 0
    high_conf_count = 0
    med_conf_count = 0
    low_conf_count = 0
    garbage_findings: list = []  # NEW: collected separately, shown collapsed

    for inv in results:
        if not isinstance(inv, dict): continue
        iid = inv.get("investigator_id") or inv.get("investigator", "").lower().replace(" ", "_")
        inv_name = inv.get("investigator", iid)
        section = _bucket(iid)
        findings = inv.get("findings", [])
        ok_findings = []
        for f in findings:
            v = f.get("verification") or {}
            conf = v.get("confidence")
            is_garbage, garbage_reason = _is_garbage(f, iid, target)
            humanized_url, humanized_label = _humanize_url(f.get("url", "") or "")
            cls = _confidence_class(conf)
            scored = {
                "label": f.get("label", ""),
                "value": (f.get("value", "") or "")[:300],
                "url": f.get("url", ""),
                "humanized_url": humanized_url if humanized_url != f.get("url", "") else "",
                "humanized_label": humanized_label,
                "confidence": conf,
                "confidence_class": cls,
                "matched_signals": v.get("matched_signals", []),
                "investigator": inv_name,
                "garbage_reason": garbage_reason,
            }
            if v.get("rejected"):
                rejected_count += 1
                scored["garbage_reason"] = garbage_reason or f"unverified_conf_{conf}"
                garbage_findings.append(scored)
                continue
            if is_garbage:
                garbage_findings.append(scored)
                continue
            if cls == "high": high_conf_count += 1
            elif cls == "medium": med_conf_count += 1
            elif cls == "low": low_conf_count += 1
            ok_findings.append(scored)
        if ok_findings:
            sections[section].extend(ok_findings)
        sources_run.append({
            "id": iid,
            "name": inv_name,
            "elapsed_ms": inv.get("elapsed_ms", 0),
            "ok": bool(inv.get("ok")),
            "raw_count": len(findings),
            "verified_count": len(ok_findings),
            "error": inv.get("error", ""),
        })

    # Identity card -- target metadata
    identity_card = {
        "target": target,
        "kind": kind,
        "first_seen": started,
        "investigation_id": inv_id,
        "triggered_by": triggered_by,
        "lead_id": lead_id,
    }

    stats = {
        "total_findings": sum(s.get("raw_count", 0) for s in sources_run),
        "verified_findings": sum(s.get("verified_count", 0) for s in sources_run),
        "rejected": rejected_count,
        "high_confidence": high_conf_count,
        "medium_confidence": med_conf_count,
        "low_confidence": low_conf_count,
        "investigators_run": len(sources_run),
        "sources_returning_data": sum(1 for s in sources_run if s.get("verified_count", 0) > 0),
        "garbage_filtered": len(garbage_findings),
    }
    sections_out = {
        "contact":  sections["contact"],
        "online":   sections["online"],
        "property": sections["property"],
        "business": sections["business"],
        "risk":     sections["risk"],
        "research": sections["research"],
    }

    # Personality synthesis + 5-stage marketing pipeline + depth scoring
    personality = {}
    pitch_hooks_list = []
    pitch_package = {}
    depth = {}
    try:
        from .personality_synth import synthesize_personality
        from .pitch_hooks import generate_hooks
        from .marketing_pipeline import run_pipeline
        from .profile_depth import score as score_depth
        personality = synthesize_personality(results)
        lead_ctx = {"target": target, "owner_name": target}
        if isinstance(payload.get("verify_context"), dict):
            lead_ctx.update({k: v for k, v in payload["verify_context"].items() if v})
        if isinstance(payload.get("lead_context"), dict):
            lead_ctx.update({k: v for k, v in payload["lead_context"].items() if v})
        # Keep one-liner hooks for back-compat
        pitch_hooks_list = generate_hooks(personality, lead_context=lead_ctx)
        # NEW: full multi-touchpoint pitch package via the 5-stage pipeline
        pitch_package = run_pipeline(personality, lead_context=lead_ctx)
        depth = score_depth(personality, sections_out, verification_summary)
    except Exception as e:
        personality = {"error": str(e)[:120]}

    profile = {
        "investigation_id": inv_id,
        "target": target,
        "kind": kind,
        "started_at": started,
        "elapsed_ms": elapsed,
        "triggered_by": triggered_by,
        "lead_id": lead_id,
        "dnc_blocked": dnc_blocked,
        "dnc_reason": dnc_reason,
        "identity": identity_card,
        "verification_summary": verification_summary,
        "stats": stats,
        "sections": sections_out,
        "garbage_findings": garbage_findings,
        "sources_run": sources_run,
        "personality": personality,
        "pitch_hooks": pitch_hooks_list,
        "pitch_package": pitch_package,
        "depth": depth,
        "rendered_at": datetime.now().isoformat(),
    }
    # TLDR is built last so it has all the aggregated counts
    # state_rules will be plumbed in via render_profile_html, but we can stub here
    profile["tldr"] = _build_tldr(target, kind, sections_out, stats,
                                    verification_summary, dnc_blocked,
                                    state_rules=None)

    return profile
