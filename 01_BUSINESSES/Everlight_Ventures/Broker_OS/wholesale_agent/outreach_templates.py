"""outreach_templates -- persona-voiced email bodies for the wholesale pipeline.

Four external personas (Piper / Henry / Marvin / Vaughn), each with distinct
cadence, opener, Memphis-specific signal, data_lens interpretation, and
signature block. Same lead, four completely different characters.

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
# Persona registry -- deep character data pulled from agent dossiers
# ---------------------------------------------------------------------------

PERSONA: dict[str, dict] = {
    "piper": {
        "name": "Piper Reeves",
        "title": "Outreach Specialist | Wholesale Acquisitions",
        "email": "piper@everlightventures.io",
        "voice": "warm Southern professional, Nashville cadence, Memphis-aware",
        "background": (
            "Franklin TN raised, Vanderbilt psych grad, three years in nonprofit "
            "fundraising before pivoting to wholesale. Two years in Sacramento softened "
            "the twang but didn't kill it. Owns a Cavalier King Charles Spaniel named Biscuit."
        ),
        "catchphrases": [
            "First conversation, not a pitch.",
            "If the timing is ever right",
            "I'd genuinely love to hear your situation",
            "Honest with you",
        ],
        "openers": [
            "Hey {first_name},",
            "Hey {first_name} --",
            "Hi {first_name},",
        ],
        "data_lens_phrases": [
            "I see a real story here, not a number on a spreadsheet.",
            "When I look at {neighborhood}, I see long-time owners -- "
            "people who've put roots down and deserve a straight answer.",
            "What I notice most is how long you've held this one. That tells me something.",
            "A lot of the owners I reach out to in this part of Memphis are just "
            "ready for a clean exit -- no fuss, no agents in the middle.",
            "I noticed the property has been sitting -- and I don't read that as a problem, "
            "I read it as an opening.",
        ],
        "closers": [
            "Would a quick call or email work this week? No obligation, just a conversation.",
            "If the timing is right, I'd love to hear from you -- no rush at all.",
            "Just hit reply whenever it works for you.",
        ],
        "tells": [
            "uses 'honest with you' before any number",
            "calls a parcel a 'spot' or a 'lot', never 'property asset'",
            "drops 'y'all' at most once per email, never forced",
            "never apologizes for reaching out",
            "no em-dashes -- uses commas and periods",
        ],
    },
    "henry": {
        "name": "Henry Hammond",
        "title": "Senior Negotiator | Wholesale Acquisitions",
        "email": "henry@everlightventures.io",
        "voice": "math-first, Atlanta-professional, walks-away framing, never rattled",
        "background": (
            "Marietta GA raised, Georgia Tech industrial engineering, Emory MBA while "
            "working full-time. Twelve years at SunTrust then BB&T closing jumbo mortgages. "
            "Saw the wholesale side at a real estate meetup and never looked back. "
            "Coaches his daughters' soccer team. Chess.com player, USCF 1820."
        ),
        "catchphrases": [
            "Math first, feelings second.",
            "Here is where I can be today",
            "the spread",
            "no hard feelings -- we'll pass",
            "let me give you an honest read",
            "I hear you -- here's what I'm seeing",
        ],
        "openers": [
            "Hi {first_name} -- Henry here, picking up from Piper.",
            "Hi {first_name} --",
            "{first_name},",
        ],
        "data_lens_phrases": [
            "I pulled the Memphis comps for this block and the math tells a clear story.",
            "The spread between what the county has it at and what a cash buyer "
            "will pay right now -- that's the number that matters.",
            "I don't look at years of ownership with sentiment -- I look at "
            "accumulated equity and what that converts to in a 7-day close.",
            "Based on what I'm seeing in the neighborhood, I can build a number "
            "you can actually use to make a decision.",
            "The comps in this corridor have been moving. Let me show you where I land.",
        ],
        "closers": [
            "If the range works, let's talk today. If it doesn't -- no hard feelings, we'll pass.",
            "Math doesn't change. If the number makes sense when you're ready, I'm here.",
            "That's my ceiling on this one, honest read. No hard feelings if we don't connect.",
        ],
        "tells": [
            "presents numbers in tables",
            "never says 'I understand how you feel' -- says 'I hear you'",
            "attaches offers to logic, not opinion",
            "walks away after round 3, never desperate",
            "uses 'champ' once a week max -- usually reins it in",
        ],
    },
    "marvin": {
        "name": "Marvin Cohen",
        "title": "Closing Coordinator | Wholesale Acquisitions",
        "email": "marvin@everlightventures.io",
        "voice": "detail-obsessed, Memphis-Jewish-grandson cadence, calm under paperwork",
        "background": (
            "Born and raised East Memphis (38117), Rhodes College history BA, "
            "10 years paralegal at a TN real-estate law firm (closed ~800 deals). "
            "Married -- 'we have Justice,' a rescue beagle. Lives in a 1923 Tudor "
            "he's been restoring for 8 years. Season tickets to Memphis Tigers basketball. "
            "On first-name terms with Brenda Halloran at Mid-South Title."
        ),
        "catchphrases": [
            "If it's not in writing, it's not in writing.",
            "Two things to flag",
            "Three quick items",
            "I'll confirm receipt within 15 minutes",
            "Ping me",
            "Let me run that by Mid-South",
            "I'll have that to you by",
        ],
        "openers": [
            "Hi {first_name} -- Marvin Cohen here, Closing Coordinator at Everlight Ventures.",
            "Hi {first_name} --",
            "{first_name},",
        ],
        "data_lens_phrases": [
            "Looking at this property, what I see first is the title path -- "
            "and a clean title in Shelby County means we can move fast.",
            "The paperwork side of this one is straightforward. "
            "TN SB 909 disclosure, Mid-South Title holds the EMD, "
            "and we put a specific closing date in the contract -- not 'around the 15th.'",
            "I've coordinated a lot of Memphis closings and the ones that go smooth "
            "are the ones where every number is in writing before anyone moves.",
            "What I notice is that there's no encumbrance complexity here. "
            "That's actually good news for your timeline.",
            "From a closing standpoint, this one has a clean path. "
            "We protect you with a standard TN equitable-interest disclosure "
            "and everything goes through Mid-South Title -- not through us.",
        ],
        "closers": [
            "Ping me anytime -- I'll confirm receipt within 15 minutes.",
            "If something looks off, just reply. I'll have an answer back to you same day.",
            "Everything in writing, every step of the way -- that's my standard.",
        ],
        "tells": [
            "numbered lists for every multi-step item",
            "always gives a specific timestamp promise, never 'I'll get back to you'",
            "apologizes once and only once per thread",
            "calls his title contact by first name (Brenda)",
            "never says 'no problem' -- says 'confirmed' or 'got it'",
        ],
    },
    "vaughn": {
        "name": "Vaughn Sterling",
        "title": "Senior Partner | Everlight Ventures",
        "email": "vaughn@everlightventures.io",
        "voice": "old-money Charleston, Wharton polish, 25 years private wealth, "
                 "walks-away default, never desperate",
        "background": (
            "Charleston SC raised, Davidson College history, Wharton MBA. "
            "25 years at Northern Trust private wealth (Atlanta 18 years, "
            "Charleston 7 years). Joined Everlight in early 2026. "
            "Married 27 years to Eleanor. Sails a J/35 named Polaris at "
            "Charleston Harbor. Bourbon snob -- specifically a 18-year Talisker. "
            "Reads one biography a month, currently deep in Robert Caro LBJ."
        ),
        "catchphrases": [
            "I'd rather walk than wreck a relationship.",
            "I'd like to be direct with you.",
            "In my experience",
            "There is no deadline on my end.",
            "My line is always open.",
            "warm regards",
        ],
        "openers": [
            "Good afternoon,",
            "Dear Sir or Madam,",
            "Good morning,",
        ],
        "data_lens_phrases": [
            "In my experience, a property that has been held this long "
            "carries a different kind of weight -- and the conversation deserves to match that.",
            "What I see here is not a transaction. "
            "It's a stewardship question -- the right outcome for the property "
            "and for the people connected to it.",
            "Twenty-five years in private wealth taught me that the best decisions "
            "get made without a deadline. This is one of those situations.",
            "I've seen situations like this benefit most from a single, direct conversation "
            "rather than a long chain of offers and counters.",
            "The way I read this property's history -- and I've looked at it carefully -- "
            "is that it deserves a buyer who will close cleanly and not create complications.",
        ],
        "closers": [
            "There is no deadline on my end. My line is always open.",
            "If the timing is not right, I understand completely. "
            "We can revisit whenever it suits you.",
            "I'd rather we take the time to get this right than rush to a number "
            "that doesn't serve you well.",
        ],
        "tells": [
            "uses 'Mr.' or 'Mrs.' for sellers over 65 unless given a first name",
            "never uses 'Hey' or casual openers",
            "closes with 'warm regards' -- only person on the team who does",
            "references 25 years experience as context, never as a flex",
            "no exclamation points, no ALL CAPS, no bold unless essential",
            "long explanatory paragraphs, single decisive closing sentence",
        ],
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
        return "Hi there,"
    fname = first_name(owner_name)
    if fname.lower() == "there":
        return "Hi there,"
    return f"Hey {fname},"


# ---------------------------------------------------------------------------
# data_lens -- same lead, four different interpretations
# ---------------------------------------------------------------------------

def data_lens(persona_key: str, lead: dict) -> str:
    """Return a 1-2 sentence interpretation of the lead IN THAT PERSONA'S VOICE.

    This is the magic: same property data, four entirely different lenses.
    Piper sees the human story. Henry sees the math. Marvin sees the title path.
    Vaughn sees the stewardship question.
    """
    persona_key = persona_key.lower().strip()
    city = lead.get("city") or TN_CONSTANTS["metro"]
    address = lead.get("property_address") or lead.get("address") or "this Memphis property"
    years_owned = lead.get("years_owned") or 0
    lead_type = classify_lead(lead)

    if persona_key == "piper":
        if lead_type == "probate":
            return (
                "I noticed this property has an estate situation attached to it, "
                "and I want you to know upfront -- I'm not calling this a problem. "
                "A lot of families I talk to in Memphis just want a clean, quiet exit "
                "without agents and showings on top of everything else they're managing."
            )
        if lead_type == "absentee":
            return (
                "What I noticed is that you're managing this spot from a distance -- "
                "and honestly, that's exactly when a cash offer can feel like a relief "
                "instead of just another thing on the list."
            )
        if years_owned and int(years_owned) >= 10:
            return (
                f"What caught my attention is that you've held onto "
                f"{html.escape(address)} for a while now -- that tells me "
                "you've probably thought carefully about what you want to do with it. "
                "I'd love to be one of the options on the table."
            )
        return (
            "When I look at this part of "
            f"{html.escape(city)}, I see long-time owners -- "
            "real people who deserve a straight answer, not a runaround. "
            "That's the only reason I'm reaching out."
        )

    if persona_key == "henry":
        if lead_type == "probate":
            return (
                "I'll be straightforward: estate properties in Memphis carry a different "
                "comp profile. The spread between assessed value and a clean cash close "
                "is actually favorable right now -- I can show you exactly where I land "
                "in one email, no back-and-forth required."
            )
        appraisal = lead.get("county_appraisal") or 0
        if appraisal:
            offer_est = int(int(appraisal) * 0.68)
            return (
                f"I pulled the Memphis comps for the {html.escape(address)} corridor "
                f"and ran the spread. County has it at ${int(appraisal):,}. "
                f"Where I can be today is closer to ${offer_est:,} all cash, "
                "7-day close. That's not lowballing -- that's the math on a no-agent, "
                "no-repair, no-financing deal. Let me give you an honest read."
            )
        return (
            "I pulled the Memphis comps for this block and the spread is clear. "
            "What the county has it assessed at and what a cash buyer will pay "
            "right now -- that's the number that matters. "
            "Let me give you an honest read before you make any decisions."
        )

    if persona_key == "marvin":
        if lead_type == "probate":
            return (
                "Two things I look at immediately on an estate property: "
                "title chain and the TN SB 909 disclosure path. "
                "This one has a clean route -- "
                "the process is straightforward if you want to move forward. "
                "I've coordinated a lot of Memphis closings and the paperwork here is manageable."
            )
        return (
            "From a closing standpoint, what I see first is the title path. "
            "A clean Shelby County title with no encumbrance complexity means "
            "we can put a specific closing date in the contract -- not 'around the 15th,' "
            "an actual date -- and Mid-South Title holds the EMD, not us. "
            "If it's not in writing, it's not in writing."
        )

    if persona_key == "vaughn":
        if lead_type == "probate":
            return (
                "In my experience, estate situations benefit most from a single, "
                "direct conversation with someone who will not add pressure to an "
                "already complicated time. I want to be that conversation, not another "
                "offer letter in the stack."
            )
        if years_owned and int(years_owned) >= 15:
            return (
                "In my experience, a property held this long carries a different weight "
                "than a recent acquisition -- and the conversation deserves to reflect that. "
                "I would rather take the time to get the terms right than rush "
                "to a number that does not serve you."
            )
        return (
            "What I see here is not simply a transaction. "
            "It is a stewardship question -- the right outcome for the property "
            "and for the people connected to it. "
            "Twenty-five years in private wealth taught me that the best decisions "
            "get made without a deadline."
        )

    # Fallback
    return ""


# ---------------------------------------------------------------------------
# PIPER templates (warm Southern professional, Memphis-aware)
# ---------------------------------------------------------------------------

def _piper_first_touch(lead: dict, lead_type: str) -> dict:
    p_key = "piper"
    owner = lead.get("owner_name") or ""
    address = lead.get("property_address") or lead.get("address") or "your Memphis property"
    # Extract street portion for casual reference (e.g. "836 N Bellevue" not full address)
    street_address = html.escape(address)
    city = lead.get("city") or TN_CONSTANTS["metro"]
    years_owned = lead.get("years_owned") or 0

    # Build lead-type-specific warmth line (paragraph 3: something nice about the house/them)
    if lead_type == "probate":
        nice_line = (
            "Dealing with an estate property is a lot to manage on top of everything else -- "
            "I just want you to know we handle this kind of thing quietly and without any drama."
        )
    elif lead_type == "joint_couple":
        nice_line = (
            "I always love seeing two names on a deed -- "
            "it tells me y'all have taken care of this place together, and that means something."
        )
    elif lead_type == "absentee":
        nice_line = (
            "Managing a property from out of town is no small thing -- "
            "the fact that you've held onto it says a lot."
        )
    elif years_owned and int(years_owned) >= 10:
        nice_line = (
            f"Honest with you, when I see someone hold a spot for {int(years_owned)} years, "
            "it tells me they've been intentional about it -- that's not something you see every day."
        )
    else:
        nice_line = (
            "Memphis has some really solid blocks, and yours caught my eye -- "
            "good bones in this part of town."
        )

    # Paragraph 4: a little stat about the house / block
    stat_line = (
        "Places like yours in this part of Memphis have been moving "
        "in the $35-65k range depending on condition -- "
        "cash buyers are active right now and closings have been quick."
    )

    # Paragraph 5: casual ask
    if lead_type == "llc":
        cta = (
            "Anyway -- we're a private buyer picking up a few Memphis properties this month. "
            "Would your firm be down to have a quick conversation about a cash offer? "
            "No agents, no fees, no obligation -- just putting it on your radar."
        )
    elif lead_type == "probate":
        cta = (
            "Anyway -- we're a private buyer picking up a few Memphis homes this month. "
            "Are you down to talk through what a clean cash offer might look like? "
            "No fees, no agents, no showings -- just letting you know we're interested."
        )
    else:
        fname = first_name(owner)
        cta = (
            "Anyway -- we're a private buyer picking up a few homes in your area this month. "
            f"Would you be down for a quick conversation about a cash offer, {html.escape(fname)}? "
            "No fees, no agents, no obligation -- just letting you know we're interested."
        )

    # Paragraph 1: casual hello + intro
    if lead_type in ("llc", "probate"):
        salutation = _lead_type_salutation(lead_type, owner)
        intro = "I'm Piper with Everlight -- we're a small private buying group based out of the Sacramento area."
    else:
        salutation = _lead_type_salutation(lead_type, owner)
        intro = "I'm Piper with Everlight -- we're a small private buying group."

    # Paragraph 2: why I'm here
    why_here = (
        f"Your place on {street_address} came across my desk this morning "
        f"while I was going through properties in {html.escape(city)}, Tennessee, "
        "and I wanted to reach out."
    )

    # Paragraph 6: no-pressure close
    close = "If the timing isn't right, no worries at all -- you've got my line whenever. -- Piper"

    subject = f"Quick question about your Memphis property -- {street_address}"
    paragraphs = [salutation, intro, why_here, nice_line, stat_line, cta, close]
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
            "We still have a Memphis buyer who is active this month, "
            "and I'd hate for us to miss each other if the timing works on your end. "
            "Honest with you, this is just a check-in -- not a push."
        )
    else:
        fname = first_name(owner)
        opener = (
            f"One last note about {html.escape(address)} in Memphis -- "
            "I promise I'm not trying to be a nuisance."
        )
        body = (
            "If now is not the right time, that's completely fine. "
            "Just let me know and I'll respect that. "
            f"If things ever change, y'all know where to find us, {html.escape(fname)}. "
            "The door stays open."
        )

    subject = f"Re: Memphis property at {html.escape(address)}"
    paragraphs = [salutation, opener, body]
    body_html = _wrap(paragraphs, _sig(p_key))
    return {"subject": subject, "body_html": body_html, "persona": PERSONA[p_key]}


def _piper_first_touch_followup(lead: dict) -> dict:
    """Day-2 follow-up: bump the inbox, short and casual, no pressure language."""
    p_key = "piper"
    owner = lead.get("owner_name") or ""
    address = lead.get("property_address") or lead.get("address") or "your Memphis property"
    lead_type = classify_lead(lead)
    salutation = _lead_type_salutation(lead_type, owner)
    fname = first_name(owner)

    opener = (
        f"Hey {html.escape(fname)} -- just bumping my last note up the inbox "
        "in case it got buried."
    )
    body = (
        "We're still picking up a few homes in Memphis this month if the timing ever lines up. "
        "No rush on my end -- just wanted to make sure you saw it."
    )
    cta = "Shoot me a reply whenever. -- Piper"

    subject = f"Re: {html.escape(address)} -- Memphis"
    paragraphs = [salutation, opener, body, cta]
    body_html = _wrap(paragraphs, _sig(p_key))
    return {"subject": subject, "body_html": body_html, "persona": PERSONA[p_key]}


def _piper_first_touch_final(lead: dict) -> dict:
    """Day-4 final touch: warm closure, no false deadline, no expiration pressure."""
    p_key = "piper"
    owner = lead.get("owner_name") or ""
    address = lead.get("property_address") or lead.get("address") or "your Memphis property"
    lead_type = classify_lead(lead)
    salutation = _lead_type_salutation(lead_type, owner)
    fname = first_name(owner)

    opener = (
        f"Hey {html.escape(fname)} -- one last note from me."
    )
    body = (
        "If the timing isn't right that's completely okay -- "
        "no expiration on the offer. "
        "You know where to find me if anything changes."
    )
    close_note = (
        "Either way, I hope things are going well on your end. Take care. -- Piper"
    )

    subject = f"Last note -- {html.escape(address)}, Memphis"
    paragraphs = [salutation, opener, body, close_note]
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
    lens = data_lens("henry", lead)

    opener = (
        f"Hi {html.escape(first_name(owner))} -- Henry here, picking up from Piper. "
        "She mentioned you'd like to know where we land on the numbers, "
        "so let me give you an honest read."
    )
    lens_para = lens
    math_intro = (
        f"Based on the Memphis comps I'm looking at for {html.escape(address)}, "
        "here is where I can be today:"
    )

    appraisal = lead.get("county_appraisal") or 0
    if appraisal:
        offer_low = int(int(appraisal) * 0.65)
        offer_high = int(int(appraisal) * 0.72)
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
        "Math first, feelings second -- "
        "if that range doesn't move you, no hard feelings, we'll pass. "
        "But if it's in the right neighborhood, let's talk today."
    )

    subject = f"Numbers on {html.escape(address)} -- Memphis"
    body_html = (
        f"<p>{salutation}</p>"
        f"<p>{html.escape(opener)}</p>"
        f"<p>{lens_para}</p>"
        f"<p>{html.escape(math_intro)}</p>"
        f"{table}"
        f"<p>{html.escape(walk)}</p>"
        + _sig(p_key)
    )
    return {"subject": subject, "body_html": body_html, "persona": PERSONA[p_key]}


def _henry_followup(lead: dict, touch_index: int) -> dict:
    p_key = "henry"
    owner = lead.get("owner_name") or ""
    address = lead.get("property_address") or lead.get("address") or "your Memphis property"
    lead_type = classify_lead(lead)
    salutation = _lead_type_salutation(lead_type, owner)

    if touch_index == 1:
        body = (
            f"Following up on the numbers I sent for {html.escape(address)} in Memphis. "
            "Math hasn't changed. The spread I showed you still works at a 7-day close. "
            "If it works on your end, we can move today -- no back-and-forth required."
        )
    else:
        body = (
            f"Last note on {html.escape(address)}, Memphis. "
            "I'm not going to keep sending numbers that don't land -- "
            "if the math doesn't shake out for you, no hard feelings, we'll pass. "
            "But if something's changed on your end, I hear you -- here's what I'm seeing "
            "is still the same offer. My ceiling hasn't moved."
        )

    subject = f"Re: Numbers on {html.escape(address)} -- Memphis"
    body_html = _wrap([salutation, body], _sig(p_key))
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
    lens = data_lens("marvin", lead)

    opener = (
        f"Hi {html.escape(first_name(owner))} -- Marvin Cohen here, "
        "Closing Coordinator at Everlight Ventures. "
        "Henry just handed this over to me, which means we're moving. "
        "Two quick items to get on your calendar."
    )
    lens_para = lens
    steps = (
        "<ol>"
        "<li><strong>Purchase contract</strong> -- I'll have the agreement to you "
        "within 30 minutes. TN SB 909 equitable-interest disclosure is pre-baked in. "
        "If it's not in writing, it's not in writing -- so we make sure everything is. "
        "Sign at your convenience, no rush on time of day.</li>"
        "<li><strong>EMD (Earnest Money Deposit)</strong> -- held by "
        "Mid-South Title Company here in Memphis (not by us). "
        "I'll run the wire instructions by Brenda at Mid-South and "
        "send them with the contract.</li>"
        "<li><strong>Closing target</strong> -- 7 business days from your signature. "
        "A specific date goes in the contract. Not 'around the 15th' -- an actual date.</li>"
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
        f"<p>{lens_para}</p>"
        f"{steps}"
        f"<p>{html.escape(confirm)}</p>"
        + _sig(p_key)
    )
    return {"subject": subject, "body_html": body_html, "persona": PERSONA[p_key]}


def _marvin_followup(lead: dict, touch_index: int) -> dict:
    p_key = "marvin"
    owner = lead.get("owner_name") or ""
    address = lead.get("property_address") or lead.get("address") or "your Memphis property"
    lead_type = classify_lead(lead)
    salutation = _lead_type_salutation(lead_type, owner)

    if touch_index == 1:
        body = (
            f"Following up on the contract for {html.escape(address)}, Memphis. "
            "Two items still pending: your signature on the purchase agreement "
            "and the EMD wire to Mid-South Title. "
            "I'll have that to you again by end of day if you need another copy. "
            "Ping me -- I'll confirm receipt within 15 minutes."
        )
    else:
        body = (
            f"One more note on {html.escape(address)}, Memphis -- "
            "contract is still open on our end. "
            "Three quick items still outstanding: signature, EMD wire, closing date confirmation. "
            "Just reply and I'll walk you through each one in order. "
            "Nothing complicated -- if it's not in writing yet, we'll get it there."
        )

    subject = f"Re: Contract -- {html.escape(address)}, Memphis"
    body_html = _wrap([salutation, body], _sig(p_key))
    return {"subject": subject, "body_html": body_html, "persona": PERSONA[p_key]}


# ---------------------------------------------------------------------------
# VAUGHN templates (senior partner, institutional gravitas, probate / high-stakes)
# ---------------------------------------------------------------------------

def _vaughn_first_touch(lead: dict) -> dict:
    """Vaughn writes first-touch only on senior-care / probate / high-stakes leads."""
    p_key = "vaughn"
    owner = lead.get("owner_name") or ""
    address = lead.get("property_address") or lead.get("address") or "your property"
    lead_type = classify_lead(lead)
    lens = data_lens("vaughn", lead)

    if lead_type == "probate":
        salutation = "Dear Sir or Madam,"
    else:
        salutation = "Good afternoon,"

    opener = (
        "My name is Vaughn Sterling. I am a Senior Partner at Everlight Ventures, "
        f"and I am reaching out regarding the property located at {html.escape(address)} "
        "in Memphis, Tennessee."
    )
    lens_para = lens
    context = (
        "We work with a trusted Memphis buyer who closes on a weekly schedule, "
        "and we can put a no-obligation cash offer in writing within 24 hours "
        "if that would be useful. I would like to be direct with you: "
        "there is no pressure attached to this note."
    )
    close = (
        "There is no deadline on my end. "
        "If the timing is not right, my line is always open."
    )

    subject = f"Regarding your property in Memphis, Tennessee -- {html.escape(address)}"
    paragraphs = [salutation, opener, lens_para, context, close]
    body_html = _wrap(paragraphs, _sig(p_key))
    return {"subject": subject, "body_html": body_html, "persona": PERSONA[p_key]}


def _vaughn_followup(lead: dict, touch_index: int) -> dict:
    p_key = "vaughn"
    owner = lead.get("owner_name") or ""
    address = lead.get("property_address") or lead.get("address") or "your Memphis property"

    if touch_index == 1:
        body = (
            f"A brief follow-up regarding {html.escape(address)} in Memphis, Tennessee. "
            "In my experience, the timing on these decisions rarely follows a calendar. "
            "I am not writing to create urgency -- I am writing to let you know "
            "that my line remains open whenever you are ready."
        )
    else:
        body = (
            f"One final note regarding {html.escape(address)}, Memphis. "
            "I would rather walk away cleanly than push a conversation that is not wanted. "
            "If circumstances ever change on your end -- now or well into the future -- "
            "you have my contact. No expiration on that."
        )

    subject = f"Re: Memphis property -- {html.escape(address)}"
    body_html = _wrap(["Good afternoon,", body], _sig(p_key))
    return {"subject": subject, "body_html": body_html, "persona": PERSONA[p_key]}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def render_first_touch(lead: dict, persona_key: str = "piper") -> dict:
    """Day-0-hour-4 email. Returns {subject, body_html, persona}.

    body_html contains paragraph tags ready for the gold template wrapper
    in branded_mailer. Persona-voiced, Memphis-anchored, TN-only.
    Each persona interprets the lead through their own lens.

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


def render_first_touch_followup(lead: dict, persona_key: str = "piper") -> dict:
    """Day-2 follow-up email: social proof + soft urgency variant.

    Args:
        lead: lead dict
        persona_key: one of "piper" | "henry" | "marvin" | "vaughn"

    Returns:
        {"subject": str, "body_html": str, "persona": dict}
    """
    persona_key = persona_key.lower().strip()
    if persona_key not in PERSONA:
        raise ValueError(f"Unknown persona_key '{persona_key}'. Valid: {list(PERSONA)}")

    if persona_key == "piper":
        return _piper_first_touch_followup(lead)

    # Henry / Marvin / Vaughn use their standard follow-up at index 1
    return render_followup(lead, touch_index=1, persona_key=persona_key)


def render_first_touch_final(lead: dict, persona_key: str = "piper") -> dict:
    """Day-4 final touch: warm closure, no false deadline.

    Args:
        lead: lead dict
        persona_key: one of "piper" | "henry" | "marvin" | "vaughn"

    Returns:
        {"subject": str, "body_html": str, "persona": dict}
    """
    persona_key = persona_key.lower().strip()
    if persona_key not in PERSONA:
        raise ValueError(f"Unknown persona_key '{persona_key}'. Valid: {list(PERSONA)}")

    if persona_key == "piper":
        return _piper_first_touch_final(lead)

    # Henry / Marvin / Vaughn use their standard follow-up at index 2
    return render_followup(lead, touch_index=2, persona_key=persona_key)


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
    if persona_key == "henry":
        return _henry_followup(lead, touch_index)
    if persona_key == "marvin":
        return _marvin_followup(lead, touch_index)
    # vaughn
    return _vaughn_followup(lead, touch_index)


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
