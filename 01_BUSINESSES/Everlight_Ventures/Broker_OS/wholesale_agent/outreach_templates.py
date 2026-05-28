"""outreach_templates -- persona-voiced email bodies for the wholesale pipeline.

Four external personas (Piper / Henry / Marvin / Vaughn), each with distinct
cadence, opener, Memphis-specific signal, and signature block.

TN-ONLY by design. Every template anchors to Memphis / Tennessee.
No other state name ever appears in rendered output.

Usage:
    from outreach_templates import render_first_touch, render_followup, ...

    body = render_first_touch(lead, persona_key="piper")
    # -> {"subject": str, "body_html": str, "persona": dict}
"""
from __future__ import annotations

import html

# ---------------------------------------------------------------------------
# Persona registry
# ---------------------------------------------------------------------------

PERSONA: dict[str, dict] = {
    "piper": {
        "name": "Piper Reeves",
        "title": "Outreach Specialist | Wholesale Acquisitions",
        "email": "piper@everlightventures.io",
        "voice": "warm Southern professional, Memphis-aware",
    },
    "henry": {
        "name": "Henry Hammond",
        "title": "Senior Negotiator | Wholesale Acquisitions",
        "email": "henry@everlightventures.io",
        "voice": "math-first, walks-away framing, never rattled",
    },
    "marvin": {
        "name": "Marvin Cohen",
        "title": "Closing Coordinator | Wholesale Acquisitions",
        "email": "marvin@everlightventures.io",
        "voice": "detail-obsessed, calm under paperwork",
    },
    "vaughn": {
        "name": "Vaughn Sterling",
        "title": "Senior Partner | Everlight Ventures",
        "email": "vaughn@everlightventures.io",
        "voice": "institutional gravitas, walks-away default",
    },
}

# ---------------------------------------------------------------------------
# Lead-type constants
# ---------------------------------------------------------------------------

LEAD_TYPES = ("individual", "llc", "joint_couple", "absentee", "probate", "unknown")

# ---------------------------------------------------------------------------
# Memphis / TN constants (TN-only doctrine -- no cross-state references)
# ---------------------------------------------------------------------------

TN_CONSTANTS: dict = {
    "metro": "Memphis",
    "median_tax_delinquent_sale": 45000,
    "wholesale_pct_of_arv": "50-70%",
    "anchor_buyer_note": "we partner with a Mid-South buyer who closes weekly",
    # do not reference any state other than TN in any template
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def first_name(owner_name: str) -> str:
    """Return the owner's first name from assessor-formatted 'LAST FIRST MIDDLE'.

    Assessor records store names as "TOWNSEND RITA M" (last first middle).
    Returns the SECOND token title-cased; falls back to first token if only
    one token is present; falls back to 'there' when name is blank.
    """
    parts = (owner_name or "").split()
    if len(parts) >= 2:
        return parts[1].title()
    return (parts[0] if parts else "there").title()


def classify_lead(lead: dict) -> str:
    """Return one of LEAD_TYPES based on owner_name and address fields."""
    name = (lead.get("owner_name") or "").upper()

    # Entity checks
    if any(tag in name for tag in (" LLC", " INC", " CORP", " TRUST", "L.L.C", "INC.")):
        return "llc"

    # Joint ownership
    if " AND " in name or " & " in name or "AMP;" in name:
        return "joint_couple"

    # Absentee: mailing address != property address (both present and different)
    pa = (lead.get("property_address") or lead.get("address") or "").upper().strip()
    ma = (lead.get("mailing_address") or "").upper().strip()
    if ma and pa and ma not in pa and pa not in ma:
        return "absentee"

    # Probate / estate signals
    if any(tag in name for tag in ("ESTATE", " HEIRS", " HEIR ", "DECEASED",
                                   " RS)", "TRUSTEE", "EXECUTOR")):
        return "probate"

    if not name.strip():
        return "unknown"

    return "individual"


def _sig(persona_key: str) -> str:
    """Build HTML signature block for the given persona."""
    p = PERSONA[persona_key]
    closing = "Warm regards," if persona_key == "vaughn" else "Best,"
    return (
        f"<p>{closing}<br>"
        f"<strong>{html.escape(p['name'])}</strong><br>"
        f"{html.escape(p['title'])}<br>"
        f"Everlight Ventures<br>"
        f"<a href=\"mailto:{p['email']}\">{p['email']}</a></p>"
    )


def _wrap(paragraphs: list[str], sig_html: str) -> str:
    """Wrap a list of paragraph strings into full body_html."""
    body = "".join(f"<p>{p}</p>" for p in paragraphs)
    return body + sig_html


def _lead_type_salutation(lead_type: str, owner_name: str) -> str:
    """Return the correct opener salutation for a given lead type."""
    if lead_type == "llc":
        return "Hi,"
    if lead_type == "probate":
        return "Hi,"
    if lead_type == "joint_couple":
        # Both owners -- use generic greeting
        return "Hi there,"
    fname = first_name(owner_name)
    if fname.lower() == "there":
        return "Hi there,"
    return f"Hey {fname},"


# ---------------------------------------------------------------------------
# PIPER templates (warm Southern professional, Memphis-aware)
# ---------------------------------------------------------------------------

def _piper_first_touch(lead: dict, lead_type: str) -> dict:
    p_key = "piper"
    owner = lead.get("owner_name") or ""
    address = lead.get("property_address") or lead.get("address") or "your Memphis property"
    salutation = _lead_type_salutation(lead_type, owner)
    city = lead.get("city") or TN_CONSTANTS["metro"]

    if lead_type == "llc":
        opener = (
            "My name is Piper Reeves with Everlight Ventures. "
            "I came across the property at "
            f"{html.escape(address)} in {html.escape(city)}, Tennessee "
            "while researching Memphis acquisitions, and I wanted to reach out directly."
        )
        hook = (
            "We work with a local Mid-South buyer who closes cash deals every week. "
            "If your firm has any interest in a straightforward off-market conversation, "
            "I'd love five minutes of your time."
        )
    elif lead_type == "probate":
        opener = (
            "My name is Piper Reeves with Everlight Ventures. "
            f"I noticed the property at {html.escape(address)} in {html.escape(city)} "
            "and wanted to reach out with care."
        )
        hook = (
            "I understand transitions like these take time, and there's absolutely no rush. "
            "If it would ever be helpful to have a no-obligation cash offer on the table "
            "so you have one less thing to manage, we'd be glad to help."
        )
    else:
        fname = first_name(owner)
        opener = (
            f"My name is Piper Reeves with Everlight Ventures -- "
            f"I came across the property at {html.escape(address)} in {html.escape(city)}, "
            "Tennessee and just wanted to introduce myself."
        )
        hook = (
            f"We buy Memphis homes directly from owners -- no agents, no showings, "
            "no fees on your end. If the timing is ever right for a cash conversation, "
            f"I'd genuinely love to hear your situation, {html.escape(fname)}. "
            "First conversation, not a pitch."
        )

    cta = (
        "Would a quick call or email work for you this week? "
        "No obligation, just a conversation."
    )

    subject = f"Quick question about your Memphis property -- {html.escape(address)}"

    paragraphs = [salutation, opener, hook, cta]
    body_html = _wrap(paragraphs, _sig(p_key))
    return {"subject": subject, "body_html": body_html, "persona": PERSONA[p_key]}


def _piper_followup(lead: dict, touch_index: int) -> dict:
    p_key = "piper"
    owner = lead.get("owner_name") or ""
    address = lead.get("property_address") or lead.get("address") or "your Memphis property"
    lead_type = classify_lead(lead)
    salutation = _lead_type_salutation(lead_type, owner)

    if touch_index == 1:
        opener = (
            f"Just circling back on my note about {html.escape(address)} in Memphis. "
            "I know inboxes get busy -- no worries at all."
        )
        body = (
            "We still have a Memphis buyer who's active this month, "
            "and I'd hate for us to miss each other if the timing works on your end."
        )
    else:
        opener = (
            f"One last note about {html.escape(address)} in Memphis, Tennessee -- "
            "I promise I'm not trying to be a nuisance."
        )
        body = (
            "If now isn't the right time, that's completely fine. "
            "Just let me know and I'll respect that. "
            "If things ever change, y'all know where to find us."
        )

    subject = f"Re: Memphis property at {html.escape(address)}"
    paragraphs = [salutation, opener, body]
    body_html = _wrap(paragraphs, _sig(p_key))
    return {"subject": subject, "body_html": body_html, "persona": PERSONA[p_key]}


# ---------------------------------------------------------------------------
# HENRY templates (math-first, walks-away, negotiation phase)
# ---------------------------------------------------------------------------

def _henry_negotiation(lead: dict) -> dict:
    p_key = "henry"
    owner = lead.get("owner_name") or ""
    address = lead.get("property_address") or lead.get("address") or "your Memphis property"
    lead_type = classify_lead(lead)
    salutation = _lead_type_salutation(lead_type, owner)

    opener = (
        f"Hi {html.escape(first_name(owner))} -- Henry here, picking up from Piper. "
        "She mentioned you'd like to know where we land on the numbers, "
        "so let me give you an honest read."
    )
    math = (
        f"Based on the Memphis comps I'm looking at for {html.escape(address)}, "
        "here is where I can be today:"
    )

    appraisal = lead.get("county_appraisal") or 0
    if appraisal:
        offer_low = int(appraisal * 0.65)
        offer_high = int(appraisal * 0.72)
        offer_line = f"${offer_low:,} -- ${offer_high:,} all cash, 7-day close through Mid-South Title."
    else:
        offer_line = "A competitive all-cash offer, 7-day close through Mid-South Title in Memphis."

    table = (
        f"<table style='border-collapse:collapse;font-family:inherit'>"
        f"<tr><td style='padding:4px 12px 4px 0'><strong>Offer range</strong></td>"
        f"<td style='padding:4px 0'>{offer_line}</td></tr>"
        f"<tr><td style='padding:4px 12px 4px 0'><strong>Terms</strong></td>"
        f"<td style='padding:4px 0'>Cash, as-is, no agent fee, no repairs</td></tr>"
        f"<tr><td style='padding:4px 12px 4px 0'><strong>Close window</strong></td>"
        f"<td style='padding:4px 0'>7 days from signed contract</td></tr>"
        f"</table>"
    )

    walk = (
        "If that range doesn't move you, no hard feelings -- we'll pass. "
        "But if it's in the right neighborhood, let's talk today."
    )

    subject = f"Numbers on {html.escape(address)} -- Memphis"
    body_html = (
        f"<p>{salutation}</p>"
        f"<p>{html.escape(opener)}</p>"
        f"<p>{html.escape(math)}</p>"
        f"{table}"
        f"<p>{html.escape(walk)}</p>"
        + _sig(p_key)
    )
    return {"subject": subject, "body_html": body_html, "persona": PERSONA[p_key]}


# ---------------------------------------------------------------------------
# MARVIN templates (closing coordinator, contract/title phase)
# ---------------------------------------------------------------------------

def _marvin_closing_handoff(lead: dict) -> dict:
    p_key = "marvin"
    owner = lead.get("owner_name") or ""
    address = lead.get("property_address") or lead.get("address") or "your Memphis property"
    lead_type = classify_lead(lead)
    salutation = _lead_type_salutation(lead_type, owner)

    opener = (
        f"Hi {html.escape(first_name(owner))} -- Marvin Cohen here, "
        "Closing Coordinator at Everlight Ventures. "
        "Henry just handed this over to me, which means we're moving. "
        "Two quick items to get on your calendar."
    )
    steps = (
        "<ol>"
        "<li><strong>Purchase contract</strong> -- I'll have the agreement to you "
        "within 30 minutes. TN SB 909 equitable-interest disclosure is pre-baked in. "
        "Sign at your convenience, no rush on time of day.</li>"
        "<li><strong>EMD (Earnest Money Deposit)</strong> -- held by "
        "Mid-South Title Company here in Memphis (not by us). "
        "Wire instructions come with the contract.</li>"
        "<li><strong>Closing target</strong> -- 7 business days from your signature. "
        "Specific date goes in the contract.</li>"
        "</ol>"
    )
    confirm = (
        "Ping me any time if something looks off. "
        "I'll confirm receipt of anything you send within 15 minutes -- "
        "that's my standard and I stick to it."
    )

    subject = f"Next steps -- {html.escape(address)}, Memphis"
    body_html = (
        f"<p>{salutation}</p>"
        f"<p>{html.escape(opener)}</p>"
        f"{steps}"
        f"<p>{html.escape(confirm)}</p>"
        + _sig(p_key)
    )
    return {"subject": subject, "body_html": body_html, "persona": PERSONA[p_key]}


# ---------------------------------------------------------------------------
# VAUGHN templates (senior partner, institutional gravitas, probate / high-stakes)
# ---------------------------------------------------------------------------

def _vaughn_first_touch(lead: dict) -> dict:
    """Vaughn writes first-touch only on senior-care / probate / high-stakes leads."""
    p_key = "vaughn"
    owner = lead.get("owner_name") or ""
    address = lead.get("property_address") or lead.get("address") or "your property"

    # Vaughn uses Mr./Mrs. for probate / estate leads as a sign of respect
    lead_type = classify_lead(lead)
    if lead_type == "probate":
        salutation = "Dear Sir or Madam,"
    else:
        salutation = "Good afternoon,"

    opener = (
        "My name is Vaughn Sterling. I am a Senior Partner at Everlight Ventures, "
        f"and I am reaching out regarding the property located at {html.escape(address)} "
        "in Memphis, Tennessee."
    )
    context = (
        "In my experience, situations like these benefit most from a straightforward "
        "conversation rather than a long negotiation. "
        "We work with a trusted Memphis buyer who closes on a weekly schedule, "
        "and we can put a no-obligation cash offer in writing within 24 hours "
        "if that would be useful."
    )
    close = (
        "There is no deadline on my end. "
        "If the timing is not right, my line is always open."
    )

    subject = f"Regarding your property in Memphis, Tennessee -- {html.escape(address)}"
    paragraphs = [salutation, opener, context, close]
    body_html = _wrap(paragraphs, _sig(p_key))
    return {"subject": subject, "body_html": body_html, "persona": PERSONA[p_key]}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def render_first_touch(lead: dict, persona_key: str = "piper") -> dict:
    """Day-0-hour-4 email. Returns {subject, body_html, persona}.

    body_html contains paragraph tags ready for the gold template wrapper
    in branded_mailer. Persona-voiced, Memphis-anchored, TN-only.

    Args:
        lead: dict with owner_name, property_address/address, city, mailing_address, etc.
        persona_key: one of "piper" | "henry" | "marvin" | "vaughn"

    Returns:
        {"subject": str, "body_html": str, "persona": dict}
    """
    persona_key = persona_key.lower().strip()
    if persona_key not in PERSONA:
        raise ValueError(f"Unknown persona_key '{persona_key}'. Valid: {list(PERSONA)}")

    lead_type = classify_lead(lead)

    if persona_key == "piper":
        return _piper_first_touch(lead, lead_type)
    if persona_key == "henry":
        return _henry_negotiation(lead)
    if persona_key == "marvin":
        return _marvin_closing_handoff(lead)
    if persona_key == "vaughn":
        return _vaughn_first_touch(lead)

    raise ValueError(f"Unhandled persona_key: {persona_key}")  # pragma: no cover


def render_followup(lead: dict, touch_index: int, persona_key: str = "piper") -> dict:
    """Touch 1+ follow-up email. touch_index=1 is day-4, touch_index=2 is day-14.

    Args:
        lead: lead dict
        touch_index: 1-based follow-up count
        persona_key: one of "piper" | "henry" | "marvin" | "vaughn"

    Returns:
        {"subject": str, "body_html": str, "persona": dict}
    """
    persona_key = persona_key.lower().strip()
    if persona_key not in PERSONA:
        raise ValueError(f"Unknown persona_key '{persona_key}'. Valid: {list(PERSONA)}")

    if persona_key == "piper":
        return _piper_followup(lead, touch_index)

    # For other personas, fall back to a generic follow-up in their voice
    address = lead.get("property_address") or lead.get("address") or "your Memphis property"
    lead_type = classify_lead(lead)
    owner = lead.get("owner_name") or ""
    salutation = _lead_type_salutation(lead_type, owner)
    p = PERSONA[persona_key]

    if persona_key == "henry":
        body = (
            f"Following up on the numbers I sent for {html.escape(address)} in Memphis. "
            "Math hasn't changed. If it works, we can move today."
        )
    elif persona_key == "marvin":
        body = (
            f"Checking in on the contract for {html.escape(address)}, Memphis. "
            "Two items still pending -- let me know if you have questions."
        )
    else:  # vaughn
        body = (
            f"A brief follow-up regarding {html.escape(address)} in Memphis, Tennessee. "
            "No urgency on my end. My line remains open whenever you are ready."
        )

    subject = f"Following up -- {html.escape(address)}, Memphis"
    body_html = _wrap([salutation, body], _sig(persona_key))
    return {"subject": subject, "body_html": body_html, "persona": p}


def render_negotiation(lead: dict, persona_key: str = "henry") -> dict:
    """Negotiation-phase email (Henry by default).

    Returns:
        {"subject": str, "body_html": str, "persona": dict}
    """
    persona_key = persona_key.lower().strip()
    if persona_key not in PERSONA:
        raise ValueError(f"Unknown persona_key '{persona_key}'. Valid: {list(PERSONA)}")
    return _henry_negotiation(lead)


def render_closing_handoff(lead: dict, persona_key: str = "marvin") -> dict:
    """Closing-phase handoff email (Marvin by default).

    Returns:
        {"subject": str, "body_html": str, "persona": dict}
    """
    persona_key = persona_key.lower().strip()
    if persona_key not in PERSONA:
        raise ValueError(f"Unknown persona_key '{persona_key}'. Valid: {list(PERSONA)}")
    return _marvin_closing_handoff(lead)
