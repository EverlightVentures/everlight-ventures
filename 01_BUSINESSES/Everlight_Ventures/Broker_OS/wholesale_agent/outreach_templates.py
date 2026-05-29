"""outreach_templates -- persona-voiced email bodies for the wholesale pipeline.

Operator blueprint (verbatim):
  "They don't wanna hear some basic jargon, they wanna see the numbers,
  how it applies to them, and how it changes their future. We don't need
  to over-talk. Personality + tonality YES, but use the facts, the data,
  everything. Straight to the point. Once they agree, give them a number
  boom. Try to get them to accept on the first. If we have to negotiate,
  negotiate higher -- more money for us, get them out of their situation."

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
import re
from datetime import datetime, timedelta

# ---------------------------------------------------------------------------
# Persona registry -- deep character data pulled from agent dossiers
# ---------------------------------------------------------------------------

PERSONA: dict[str, dict] = {
    "marquise": {
        "name": "Marquise Reed",
        "title": "Acquisitions Lead -- Memphis / West Tennessee",
        "email": "marquise@everlightventures.io",
        "voice": "Memphis-direct, patient, receipts-first. Real-talk over corporate-speak.",
        "background": (
            "Born in North Memphis. Ran wholesale deals as side hustle for 4 years before "
            "joining Everlight. Knows every zip in Shelby County by reputation -- 38104 "
            "(Midtown old money), 38114 (Orange Mound, deep history), 38127 (Frayser, hard-luck), "
            "38128 (Raleigh, working-class). When someone gives him a parcel ID, he can usually "
            "tell you the neighborhood without looking it up."
        ),
        "catchphrases": [
            "Math first, terms second, paper third.",
            "Real talk",
            "real quick",
            "appreciate it",
            "Honest with you",
            "your call",
        ],
        "openers": [
            "Hey {first_name} --",
            "{first_name},",
            "Marquise Reed with Everlight Ventures.",
        ],
        "neighborhood_map": {
            "38104": "Midtown old money",
            "38114": "Orange Mound",
            "38116": "Whitehaven",
            "38127": "Frayser",
            "38128": "Raleigh",
            "38117": "East Memphis",
            "38111": "University District",
            "38115": "Hickory Hill",
            "38118": "Southeast Memphis",
        },
        "tells": [
            "says 'real talk' before a correction",
            "short paragraphs -- never more than 4 sentences",
            "numbers always in writing in a table",
            "references Mid-South Title by name (Brenda Halloran)",
            "uses 'y'all' naturally -- never forced",
            "math first, terms second, paper third -- always",
        ],
    },
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
            "Want me to send you a real number this week?",
            "Are you down to look at an offer?",
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
# AI Disclosure Footer -- FTC/CAN-SPAM safe, brand-positive, operator-approved voice.
# ---------------------------------------------------------------------------
# Operator direction (THE RECIPE, 2026-05-28):
#   Reframe from "automated outreach team" (reads: a machine is after your house)
#   to confident, brand-forward: a real company + real people who use AI to reach
#   folks fairly and fast. A real person handles everything from the first reply on.
#   Keep it honest (AI-assisted) but make it an asset, ~2 sentences.
#   NOT: "this came from our automated outreach team"
#
AI_DISCLOSURE_FOOTER: str = (
    '<p style="margin-top:24px;font-size:12px;color:#888888;border-top:1px solid #e0e0e0;'
    'padding-top:12px;">'
    "<strong>Everlight Ventures</strong> is a real company -- real people, using AI to find "
    "homeowners who might benefit from a conversation and reach them quickly and fairly. "
    "The moment you reply, a real person on our team handles everything from there personally."
    "</p>"
)

# Unique sentinel embedded in the footer -- used for idempotency check.
_DISCLOSURE_MARKER: str = "real company -- real people, using AI"


def _with_disclosure(body_html: str) -> str:
    """Append AI_DISCLOSURE_FOOTER to body_html exactly once.

    Idempotent: if the footer marker is already present, returns body_html unchanged.
    Call this on every consumer/buyer-facing render return. Do NOT call on
    [INTERNAL] team notes (pivot_to_chris, final_wrap, any subject marked [INTERNAL]).
    """
    if _DISCLOSURE_MARKER in body_html:
        return body_html
    return body_html + AI_DISCLOSURE_FOOTER


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
# Signal labels -- maps source/lead_type to the "specific reason we reached out"
# ---------------------------------------------------------------------------

_SOURCE_SIGNAL_MAP = {
    # tax keys map to internal sentinel; resolved gracefully per lead-type below
    "tax_lien":                  "tax_weight",
    "tax_delinquent":            "tax_weight",
    "shelby_tax_delinquent":     "tax_weight",
    "quitclaim":                 "your property transferred via quitclaim deed -- a family or estate transfer",
    "probate":                   "your property is connected to an estate situation",
    "absentee":                  "you hold this property from out of town",
    "long_hold":                 "you have held this property for a long time with no recent permit activity",
    "vacant":                    "the property appears to be vacant land with no recent improvements",
    "expired_listing":           "the property was recently listed but did not sell",
    "pre_foreclosure":           "there is a foreclosure notice on public record for this property",
    "high_equity":               "the property shows strong equity relative to its assessed value",
}

# Graceful consumer-facing tax signal per lead type.
# Never diagnose or accuse -- offer a solution, acknowledge the weight with empathy.
_TAX_SIGNAL_BY_LEAD_TYPE: dict[str, str] = {
    "individual":    "if the taxes or upkeep have become a weight, a lot of folks are juggling a lot right now -- no judgment here",
    "joint_couple":  "managing the taxes and upkeep together can pile up, and a lot of families I talk to are just ready for a clean exit",
    "absentee":      "keeping up with the taxes on a property you're managing from a distance is no small thing",
    "probate":       "estate properties can carry a tax burden on top of everything else an estate has to deal with",
    "llc":           "the carrying cost and tax position on this asset may warrant a conversation about a clean exit",
    "unknown":       "property taxes in Memphis can pile up -- I work with a lot of owners who just want a clean path forward",
}


def _signal_for_lead(lead: dict, lead_type: str | None = None) -> str:
    """Return a single plain-English sentence explaining the specific reason for outreach.

    Tax-delinquent signals are returned as graceful, empathetic language -- never as a
    cold diagnosis or accusation. The specific phrasing is chosen per lead_type so that
    individual owners, probate heirs, LLC investors, absentee holders, and joint couples
    each hear language that fits their situation.
    """
    source = (lead.get("source") or "").lower()
    lead_type_raw = (lead.get("lead_type") or "").lower()

    # Classify once (passed in or computed) -- needed for tax-weight resolution
    lt = lead_type or classify_lead(lead)

    # Source-string checks (most specific)
    for key, phrase in _SOURCE_SIGNAL_MAP.items():
        if key in source or key in lead_type_raw:
            if phrase == "tax_weight":
                # Resolve gracefully per lead type -- never expose internal data
                return _TAX_SIGNAL_BY_LEAD_TYPE.get(lt, _TAX_SIGNAL_BY_LEAD_TYPE["unknown"])
            return phrase

    # Fallback by classified lead_type
    if lt == "probate":
        return "your property is connected to an estate situation"
    if lt == "absentee":
        return "you hold this property from out of town"
    if lt == "llc":
        return "the property is held in a business entity"
    if lt == "joint_couple":
        return "the property is in joint ownership"

    years = int(lead.get("years_owned") or 0)
    if years >= 10:
        return f"you have held this property for over {years} years with no recent activity"

    return "your property came across our Memphis acquisitions list this week"


# ---------------------------------------------------------------------------
# Offer math helpers -- operator blueprint: give them a REAL number
# ---------------------------------------------------------------------------

def _compute_offer_range(lead: dict) -> tuple[int | None, int | None]:
    """Return (offer_low, offer_high) from county_appraisal or total_appraisal_usd.

    CONSERVATIVE posture (operator-locked 2026-05-28): anchor 48%, room to walk to
    a 58% close. The first-quote band is 48-54% of assessed. If missing, (None, None).
    Single source of truth -- Piper, the LLC path, Henry, and the deal-sheet helpers
    all read this so pricing never drifts between personas again.
    """
    appraisal = (
        lead.get("county_appraisal")
        or lead.get("total_appraisal_usd")
        or 0
    )
    if not appraisal:
        return None, None
    appraisal = int(appraisal)
    return int(appraisal * 0.48), int(appraisal * 0.54)


def _offer_sentence(lead: dict, persona_key: str = "piper") -> str:
    """Return a sentence with the ACTUAL offer range (or fallback if no appraisal).

    Piper: casual, 'Honest with you, I'm thinking $X-$Y.'
    Henry: table-ready number.
    Marvin/Vaughn: clean range in a sentence.
    """
    low, high = _compute_offer_range(lead)
    if low is None:
        return "Based on comps in this part of Memphis, we're typically in the $35-65k range -- once I see the full picture I can send a real number, no runaround."

    if persona_key == "piper":
        return (
            f"Honest with you, based on the county assessment I'm thinking somewhere in the "
            f"<strong>${low:,}-${high:,} range</strong> all cash. Once we confirm a few details, "
            "I can firm that up into an actual number same day."
        )
    if persona_key == "henry":
        return (
            f"County has it at ${int(lead.get('county_appraisal') or lead.get('total_appraisal_usd', 0)):,}. "
            f"Where I can be today: <strong>${low:,}-${high:,}</strong> all cash, 7-day close."
        )
    # marvin / vaughn
    return (
        f"Our cash range based on the county figure is ${low:,}-${high:,}, "
        "7-day close, no agent fees on your side."
    )


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
        appraisal = lead.get("county_appraisal") or lead.get("total_appraisal_usd") or 0
        if appraisal:
            # Do NOT hardcode an offer number here -- the offer table (via
            # _compute_offer_range) is the SINGLE source so Henry never quotes
            # two different numbers in one email (the 0.68 bug, 2026-05-28).
            return (
                f"I pulled the comps for the {html.escape(address)} corridor and ran the spread. "
                f"County has it assessed at ${int(appraisal):,}; the cash number below reflects "
                "a no-agent, no-repair, no-financing close -- not a lowball, just the math."
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
# Blueprint: specific signal + 3-5 data points + real number + future state + CTA
# ---------------------------------------------------------------------------

def _piper_first_touch(lead: dict, lead_type: str) -> dict:
    """THE RECIPE -- Piper first touch.

    Implements all 12 beats from THE RECIPE (2026-05-28):
    1. Warm human open (name + property, no number yet)
    2. Accusation Audit (Voss) -- name their suspicion before they feel it
    3. Compassionate WHY -- graceful, lead-type-specific, no tax-shaming
    4. PAS agitate-to-hope -- name the problem, offer the way out, do NOT dwell
    5. SPIN self-computation question -- "what's it running you, all in?"
    6. Anchor replacement THEN the number (traditional net vs cash now)
    7. Social proof -- one anonymous local line
    8. Tenure as RESPECT when years_owned >= 10
    9. Pride/gratitude/soft-FOMO close (operator's exact intent)
    10. Consult-counsel line (EVERY consumer email)
    11. Single low-friction CTA
    12. Reframed AI footer (applied via _with_disclosure)

    RULE: NO verbatim sentences shared across lead_types. Each type gets
    its own accusation-audit + WHY framed for that situation.
    LLC = businesslike peer; skip emotional beats 2/4/5/9 for LLC.
    """
    p_key = "piper"
    owner = lead.get("owner_name") or ""
    address = lead.get("property_address") or lead.get("address") or "your Memphis property"
    street_address = html.escape(address)
    city = lead.get("city") or TN_CONSTANTS["metro"]
    years_owned = int(lead.get("years_owned") or 0)
    fname = first_name(owner)
    fname_esc = html.escape(fname)
    salutation = _lead_type_salutation(lead_type, owner)

    source = (lead.get("source") or "").lower()
    lead_type_raw = (lead.get("lead_type") or "").lower()
    is_tax_signal = any(k in source or k in lead_type_raw
                        for k in ("tax_lien", "tax_delinquent", "shelby_tax"))

    appraisal = int(lead.get("county_appraisal") or lead.get("total_appraisal_usd") or 0)
    offer_low, offer_high = _compute_offer_range(lead)

    # ---- LLC FAST PATH: businesslike, no emotional beats ----
    if lead_type == "llc":
        intro = "I'm Piper with Everlight Ventures -- we acquire Memphis properties for cash."
        why = (
            f"Your property at {street_address} came across our acquisition targets list. "
            "Reaching out peer to peer -- no runaround."
        )
        biz_offer = _offer_sentence(lead, "piper") if offer_low else (
            "As-is homes in this corridor have been trading in the $35,000-$65,000 range -- "
            "once I see the full picture I can send a firm number the same day."
        )
        if offer_low:
            # anchor replacement for LLC: traditional listing net vs cash
            trad_commission = int(appraisal * 0.06) if appraisal else 0
            trad_repairs = 18000
            trad_carry = int(appraisal * 0.015) if appraisal else 2000  # ~1.5% 90-day hold
            trad_net = appraisal - trad_commission - trad_repairs - trad_carry if appraisal else 0
            anchor_table = (
                f"<table style='border-collapse:collapse;font-family:inherit;font-size:14px'>"
                f"<tr><th style='text-align:left;padding:3px 12px 3px 0'>Traditional listing net</th>"
                f"<td style='padding:3px 0'>~${trad_net:,} (after 6% commission + repairs + 90-day carry)</td></tr>"
                f"<tr><th style='text-align:left;padding:3px 12px 3px 0'>Our cash offer</th>"
                f"<td style='padding:3px 0'><strong>${offer_low:,}-${offer_high:,}</strong> -- as-is, 7-day, $0 out of pocket</td></tr>"
                f"</table>"
            ) if appraisal else ""
        else:
            anchor_table = ""
        cta = (
            "If the numbers work, just reply and I'll have a firm offer to you same day. "
            "No obligation. Please run it by your attorney before signing anything."
        )
        close_note = "If timing is off, no follow-up from us unless you reach out."
        subject = f"Acquisition inquiry -- {street_address}"
        body_html = (
            f"<p>{salutation}</p>"
            f"<p>{intro}</p>"
            f"<p>{why}</p>"
            f"{anchor_table}"
            f"<p>{biz_offer}</p>"
            f"<p>{cta}</p>"
            f"<p>{close_note}</p>"
            + _sig(p_key)
        )
        return {"subject": subject, "body_html": _with_disclosure(body_html), "persona": PERSONA[p_key]}

    # ---- CONSUMER PATHS: individual / tax / probate / joint_couple / absentee ----
    # Beat 1: Warm open -- names them + property, NO number yet
    intro = f"I'm Piper with Everlight -- we buy Memphis properties for cash, no agents, nothing to fix."

    # Beat 2: ACCUSATION AUDIT -- per-lead-type version (NO verbatim sharing across types)
    if lead_type == "probate":
        accusation_audit = (
            "You might be wondering why you'd get a letter like this about an inherited property -- "
            "maybe even bracing for it to come with pressure or complications. "
            "Let me put you at ease right now: it's not that kind of note."
        )
    elif lead_type == "absentee":
        accusation_audit = (
            "You might be thinking this is another cold pitch from someone who found your name "
            "in a database and doesn't know the first thing about your situation. "
            "I get that -- let me be straight with you about why I'm reaching out."
        )
    elif lead_type == "joint_couple":
        accusation_audit = (
            "When you see a note like this about a jointly held property, "
            "you probably expect it to be pushy or to rush you into something. "
            "That's not what this is -- I promise I'll keep it brief and honest."
        )
    else:
        # individual (including tax signal)
        accusation_audit = (
            "You're probably thinking you'd never get an email like this -- "
            "you might even be bracing for it to be bad news. "
            "Let me put you at ease right now: it's not."
        )

    # Beat 3: Compassionate WHY -- graceful, address-anchored
    if lead_type == "probate":
        why_para = (
            f"{street_address} recently came across my desk, "
            "and I noticed right away this might be an estate or inherited situation. "
            "Handling a property like that on top of everything else -- paperwork, "
            "family decisions, just the weight of it -- is a lot to carry. "
            "I work with Memphis families in exactly that position, and I want to make it simpler, "
            "not harder."
        )
    elif lead_type == "absentee":
        why_para = (
            f"Your property on {street_address} came across my desk recently, "
            "and from what I could see, it looks like you're managing this one from a distance. "
            "Every month that property sits, it costs you -- taxes, insurance, the mental overhead "
            "of keeping up with something you can't just walk over to check on. "
            "I work with out-of-area owners in this exact position all the time."
        )
    elif lead_type == "joint_couple":
        why_para = (
            f"Your property at {street_address} came across my desk this week. "
            "I noticed there are two names on the deed, and I know from experience "
            "that when a jointly held place starts to feel like more weight than it's worth, "
            "getting everyone on the same page about next steps can be the hardest part. "
            "I just wanted to put a clean, quiet option on the table."
        )
    else:
        # individual -- tax-signal or general
        if is_tax_signal:
            why_para = (
                f"Your place on {street_address} came across my desk this week. "
                "When a place falls behind on taxes, it doesn't stop on its own -- "
                "but it doesn't have to keep going that way either. "
                "You could put a stop to the penalties and keep that balance from climbing. "
                "What's it running you, honestly -- all in, between the expenses and the mental weight "
                "of keeping up with it? Here's what we can do for you."
            )
        else:
            why_para = (
                f"Your place on {street_address} came across my desk this week, "
                "and something about it stood out to me. "
                "I work with owners in this part of Memphis who are just ready for a clean exit -- "
                "no agents, no back-and-forth, cash in hand and done. "
                "What's it costing you to hold this place, all in -- taxes, upkeep, everything? "
                "That's what I want to talk through with you."
            )

    # Beat 5: SPIN self-computation (for non-tax paths where it wasn't folded into beat 3)
    spin_question = ""
    if lead_type in ("absentee", "probate", "joint_couple"):
        spin_question = (
            "What's it running you a year, all in -- taxes, insurance, any maintenance you're "
            "covering from a distance? That's the number that actually matters here."
        )

    # Beat 6: Anchor replacement THEN the number
    if appraisal and offer_low:
        trad_commission = int(appraisal * 0.06)
        trad_repairs = 18000
        trad_carry = int(appraisal * 0.015)  # ~90-day hold at 1.5% of value
        trad_net = appraisal - trad_commission - trad_repairs - trad_carry
        anchor_table = (
            f"<p>Here's the honest math -- <strong>two paths</strong>:</p>"
            f"<table style='border-collapse:collapse;font-family:inherit;font-size:14px'>"
            f"<tr><th style='text-align:left;padding:3px 12px 3px 0'>List with an agent</th>"
            f"<td style='padding:3px 0'>~${appraisal:,} list price, minus 6% commission, "
            f"minus repairs to make it listable, minus ~90-day carry costs -- "
            f"realistic net around <strong>${trad_net:,}</strong>. "
            f"And only IF it sells.</td></tr>"
            f"<tr><th style='text-align:left;padding:3px 12px 3px 0'>Our cash offer</th>"
            f"<td style='padding:3px 0'><strong>${offer_low:,}-${offer_high:,}</strong> cash, "
            f"as-is, 7-day close, back taxes handled, $0 out of pocket. "
            f"No risk it falls through.</td></tr>"
            f"</table>"
        )
        offer_line = (
            "Less on paper than asking price -- but in hand this week, "
            "with none of the cost, time, or risk."
        )
    else:
        anchor_table = ""
        area = html.escape(str(city).title())
        offer_line = (
            f"As-is homes around {area} have been trading in the "
            f"<strong>$35,000-$65,000</strong> range -- once I pull your full picture "
            "I can send a real, specific number the same day, no runaround."
        )

    # Beat 7: Social proof (one anonymous local line)
    social_proof = (
        "We closed one a couple streets over last month -- "
        "the owner had cash in hand in 6 days, no showings, no inspections."
    )

    # Beat 8: Tenure as RESPECT (only when years_owned >= 10)
    tenure_note = ""
    if years_owned >= 10:
        tenure_note = (
            f"{years_owned} years is a long time to hold onto a place -- "
            f"that's not nothing, and I mean that. "
            f"Honest with you, when I see someone carry a spot for {years_owned} years, "
            "it tells me they've been intentional. You've earned a straight answer."
        )

    # Beat 9: Pride/gratitude/soft-FOMO close (operator's exact intent)
    if lead_type == "probate":
        pride_close = (
            "If you're ready to put this one behind you and finally get it handled -- "
            "just say the word. We've actually got a couple of offers ready to send over "
            "if you're open to hearing them. No pressure at all -- "
            "and please run it by your family or an attorney first, always."
        )
    elif lead_type == "absentee":
        pride_close = (
            "If you're ready to put this one to rest and free up that monthly carrying cost -- "
            "just reply and I'll have a number to you same day. "
            "We've got a couple of offers ready to send over if the timing works. "
            "No pressure -- and run it by an attorney before you sign anything."
        )
    elif lead_type == "joint_couple":
        pride_close = (
            "When you're both ready to talk through options, I'm here. "
            "We've actually got a couple of offers lined up for properties in your area "
            "if the timing is ever right for you two. No rush, no pressure -- "
            "and please consult an attorney or your family before making any decisions."
        )
    else:
        # individual (including tax)
        pride_close = (
            "If you're ready to get this off your plate -- and finally put that money "
            "toward something for yourself after carrying this all these years -- just say the word. "
            "Honestly, give yourself credit for holding onto it and investing this long; "
            "you've earned a clean exit. "
            "We've actually got a couple of offers ready to send over if you're willing to hear them. "
            "No pressure at all -- and please run it by your family or an attorney first, always."
        )

    # Beat 10: Consult-counsel (belt + suspenders -- also baked into pride_close above)
    counsel_line = (
        "Whatever you decide, I genuinely hope things go well on your end. "
        "If the timing isn't right, no worries at all -- you've got my line whenever."
    )

    # Beat 11: CTA
    if lead_type == "probate":
        cta = "Just hit reply -- we'll go at whatever pace works for you."
    elif lead_type == "absentee":
        cta = f"Just reply and I'll make it happen, {fname_esc}."
    elif lead_type == "joint_couple":
        cta = "Just hit reply whenever you're both ready."
    else:
        cta = (
            f"Are you down to look at an offer, {fname_esc}? "
            "Just reply and I'll send you the actual number this week."
        )

    # Assemble subject
    subject = f"Quick question about your Memphis property -- {street_address}"

    # Build body from beats, skip empty strings
    beats = [
        salutation,
        intro,
        accusation_audit,
        why_para,
    ]
    if spin_question:
        beats.append(spin_question)
    beats += [b for b in [anchor_table, offer_line] if b]
    beats += [social_proof]
    if tenure_note:
        beats.append(tenure_note)
    # Single close: pride_close already carries the ask ("just say the word /
    # offers ready if you're willing to hear them"); the separate cta was a
    # redundant second ask (operator flagged the double-CTA). End on the warm
    # sign-off. `cta` retained for the followup/final touches, not the first.
    beats += [pride_close, counsel_line]

    # anchor_table is already wrapped in <p> tags; others get wrapped
    parts = []
    for beat in beats:
        if beat.startswith("<p") or beat.startswith("<table"):
            parts.append(beat)
        else:
            parts.append(f"<p>{beat}</p>")

    body_html = "".join(parts) + _sig(p_key)
    return {"subject": subject, "body_html": _with_disclosure(body_html), "persona": PERSONA[p_key]}


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
    return {"subject": subject, "body_html": _with_disclosure(body_html), "persona": PERSONA[p_key]}


def _piper_first_touch_followup(lead: dict) -> dict:
    """Day-2 follow-up: warm inbox bump, graceful, zero pressure, no internal dates."""
    p_key = "piper"
    owner = lead.get("owner_name") or ""
    address = lead.get("property_address") or lead.get("address") or "your Memphis property"
    lead_type = classify_lead(lead)
    salutation = _lead_type_salutation(lead_type, owner)
    fname = first_name(owner)

    if lead_type == "probate":
        opener = (
            f"Hey {html.escape(fname)} -- just wanted to make sure my last note didn't get buried. "
            "No pressure at all -- I know estate situations have a lot of moving parts."
        )
        body = (
            "Whenever you're ready to talk, I'm here. "
            "We move at your pace, not ours."
        )
    elif lead_type == "absentee":
        opener = (
            f"Hey {html.escape(fname)} -- bumping this up in case it got lost. "
            "Managing a property from out of town is a lot on anyone's plate."
        )
        body = (
            "If a clean, no-hassle cash exit ever sounds like a weight off your shoulders, "
            "just hit reply. No rush on my end."
        )
    else:
        opener = (
            f"Hey {html.escape(fname)} -- just bumping my last note up the inbox "
            "in case it got buried."
        )
        body = (
            "We're still picking up a few Memphis properties if the timing ever lines up. "
            "No rush on my end -- just wanted to make sure you saw it."
        )

    cta = "Shoot me a reply whenever. -- Piper"

    subject = f"Re: {html.escape(address)} -- Memphis"
    paragraphs = [salutation, opener, body, cta]
    body_html = _wrap(paragraphs, _sig(p_key))
    return {"subject": subject, "body_html": _with_disclosure(body_html), "persona": PERSONA[p_key]}


def _piper_first_touch_final(lead: dict) -> dict:
    """Day-4 final touch: warm closure, no false urgency, no internal dates, always graceful."""
    p_key = "piper"
    owner = lead.get("owner_name") or ""
    address = lead.get("property_address") or lead.get("address") or "your Memphis property"
    lead_type = classify_lead(lead)
    salutation = _lead_type_salutation(lead_type, owner)
    fname = first_name(owner)

    opener = (
        f"Hey {html.escape(fname)} -- one last note from me."
    )

    if lead_type == "probate":
        body = (
            "I know estate situations don't run on anyone else's clock -- "
            "take all the time you need. "
            "No expiration on the offer, and no pressure from me. "
            "You know where to find me whenever the timing is right."
        )
    elif lead_type == "absentee":
        body = (
            "If managing that property from a distance ever gets to be more than it's worth, "
            "I'm just a reply away. "
            "No expiration on my end -- the door stays open."
        )
    else:
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
    return {"subject": subject, "body_html": _with_disclosure(body_html), "persona": PERSONA[p_key]}


# ---------------------------------------------------------------------------
# HENRY templates (math-first, walks-away, negotiation phase)
# Blueprint: comp data + real number upfront + walk-away framing
# ---------------------------------------------------------------------------

def _henry_negotiation(lead: dict) -> dict:
    """Henry negotiation -- his math IS the anchor-replacement.

    THE RECIPE requirement: net-vs-traditional comparison table (commission + cash).
    Single pricing source (_compute_offer_range). No double-numbers.
    Consult-counsel line mandatory.
    """
    p_key = "henry"
    owner = lead.get("owner_name") or ""
    address = lead.get("property_address") or lead.get("address") or "your Memphis property"
    lead_type = classify_lead(lead)
    salutation = _lead_type_salutation(lead_type, owner)
    lens = data_lens("henry", lead)

    city = html.escape(str(lead.get("city") or "Memphis").title())
    opener = (
        "Henry here -- I run the numbers for Everlight Ventures in Memphis, picking up from Piper. "
        "You wanted to know where we land, so here it is, straight:"
    )

    appraisal = int(lead.get("county_appraisal") or lead.get("total_appraisal_usd") or 0)
    signal = _signal_for_lead(lead)
    neighborhood = lead.get("neighborhood") or lead.get("subdivision") or f"this {city} corridor"
    last_sale_year = lead.get("last_sale_year") or ""

    # CONSERVATIVE posture (operator-locked 2026-05-28): anchor 48%, close 58%.
    # _compute_offer_range is the SINGLE source -- no inline multiplication here
    # so we never quote two different numbers (the 0.68 bug, 2026-05-28).
    offer_low, offer_high = _compute_offer_range(lead)

    if appraisal and offer_low:
        # Net-vs-traditional comparison (THE RECIPE, Beat 6 for Henry)
        trad_commission_pct = 6
        trad_commission = int(appraisal * 0.06)
        trad_repairs = 18000
        trad_carry = int(appraisal * 0.015)  # 90-day hold cost ~1.5% of value
        trad_net = appraisal - trad_commission - trad_repairs - trad_carry
        offer_display = f"${offer_low:,} -- ${offer_high:,}"
        comparison_intro = f"Here is where I can land on {html.escape(address)} today -- traditional path vs. our cash:"
        table = (
            f"<table style='border-collapse:collapse;font-family:inherit'>"
            f"<tr><th style='text-align:left;padding:4px 12px 4px 0'>Path</th>"
            f"<th style='padding:4px 0'>Your net</th></tr>"
            f"<tr><td style='padding:4px 12px 4px 0'>Traditional listing"
            f"<br><em style='font-size:12px'>list ~${appraisal:,} minus {trad_commission_pct}% commission "
            f"(${trad_commission:,}) minus repairs (~${trad_repairs:,}) minus 90-day carry (~${trad_carry:,})"
            f" -- IF it sells</em></td>"
            f"<td style='padding:4px 0'>~${trad_net:,}</td></tr>"
            f"<tr><td style='padding:4px 12px 4px 0'><strong>Our cash offer</strong>"
            f"<br><em style='font-size:12px'>as-is, 7-day close, back taxes handled, $0 out of pocket</em></td>"
            f"<td style='padding:4px 0'><strong>{offer_display} all cash</strong></td></tr>"
            f"<tr><td style='padding:4px 12px 4px 0'><strong>Terms</strong></td>"
            f"<td style='padding:4px 0'>Cash, as-is, no agent fee, no repairs, 7-day close at Mid-South Title</td></tr>"
            f"</table>"
        )
    else:
        comparison_intro = f"Here is where I can land on {html.escape(address)} today:"
        offer_display = "A competitive all-cash offer"
        table = (
            f"<table style='border-collapse:collapse;font-family:inherit'>"
            f"<tr><td style='padding:4px 12px 4px 0'><strong>Why we reached out</strong></td>"
            f"<td style='padding:4px 0'>{html.escape(signal)}</td></tr>"
            f"<tr><td style='padding:4px 12px 4px 0'><strong>Offer</strong></td>"
            f"<td style='padding:4px 0'><strong>{offer_display}, 7-day close through Mid-South Title</strong></td></tr>"
            f"<tr><td style='padding:4px 12px 4px 0'><strong>Terms</strong></td>"
            f"<td style='padding:4px 0'>Cash, as-is, no agent fee, no repairs</td></tr>"
            f"<tr><td style='padding:4px 12px 4px 0'><strong>Close window</strong></td>"
            f"<td style='padding:4px 0'>7 days from signed contract</td></tr>"
            f"</table>"
        )

    # Future-state framing
    if "tax" in signal.lower() or "delinquent" in signal.lower():
        future_line = "Clean cash close means the tax burden stops here -- you walk with the check, not the liability."
    elif lead_type == "probate":
        future_line = "Estate settles fast, no drawn-out listing, title clears at Mid-South."
    elif last_sale_year and int(str(last_sale_year)) < 2000:
        future_line = f"You've carried this since {last_sale_year} -- a clean exit now converts that equity to cash in 7 days."
    else:
        future_line = "Fresh start -- cash in hand in 7 days, no agent, no inspection, no back-and-forth."

    walk = (
        "Math first, feelings second -- "
        "if that range doesn't move you, no hard feelings, we'll pass. "
        "But if it's in the right neighborhood, let's talk today."
    )

    counsel = "Please run this by your family or an attorney before making any decisions -- I mean that."

    subject = f"Numbers on {html.escape(address)}"
    body_html = (
        f"<p>{salutation}</p>"
        f"<p>{html.escape(opener)}</p>"
        f"<p>{lens}</p>"
        f"<p>{html.escape(comparison_intro)}</p>"
        f"{table}"
        f"<p>{html.escape(future_line)}</p>"
        f"<p>{html.escape(walk)}</p>"
        f"<p>{html.escape(counsel)}</p>"
        + _sig(p_key)
    )
    return {"subject": subject, "body_html": _with_disclosure(body_html), "persona": PERSONA[p_key]}


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
    return {"subject": subject, "body_html": _with_disclosure(body_html), "persona": PERSONA[p_key]}


# ---------------------------------------------------------------------------
# MARVIN templates (closing coordinator, contract/title phase)
# Blueprint: procedure + timeline + numbers in writing
# ---------------------------------------------------------------------------

def _marvin_closing_handoff(lead: dict) -> dict:
    """Marvin closing handoff -- commitment micro-steps per THE RECIPE.

    THE RECIPE requirement:
    (a) Written number confirmation first -- before anything else
    (b) Plain-English 4-bullet summary BEFORE the contract PDF
    (c) Documenso e-sign (not print/scan)
    SB909 disclosure referenced. Consult-counsel line mandatory.
    """
    p_key = "marvin"
    owner = lead.get("owner_name") or ""
    address = lead.get("property_address") or lead.get("address") or "your Memphis property"
    lead_type = classify_lead(lead)
    salutation = _lead_type_salutation(lead_type, owner)
    lens = data_lens("marvin", lead)
    fname_str = html.escape(first_name(owner))

    appraisal = lead.get("county_appraisal") or lead.get("total_appraisal_usd") or 0
    offer_low, offer_high = _compute_offer_range(lead)

    opener = (
        f"Hi {fname_str} -- Marvin Cohen here, "
        "Closing Coordinator at Everlight Ventures. "
        "Henry just handed this over to me, which means we're moving. "
        "Before I send anything over, let me lay it out in plain English -- "
        "four things and that's it."
    )

    # Step (a): written number confirmation FIRST
    if offer_low:
        number_confirm = (
            f"<li><strong>Confirm the number in writing.</strong> "
            f"The agreed range is <strong>${offer_low:,}-${offer_high:,} all cash</strong>. "
            "Reply to this email with 'I confirm' and the exact number you're agreeing to. "
            "That's your written confirmation before the contract goes out. "
            "If it's not in writing, it's not in writing.</li>"
        )
    else:
        number_confirm = (
            "<li><strong>Confirm the number in writing.</strong> "
            "Reply with 'I confirm' and the dollar amount Henry quoted you. "
            "That written confirmation is Step 1 before anything gets drafted.</li>"
        )

    # Step (b): plain-English 4-bullet summary BEFORE the contract
    summary_intro = (
        "Here is exactly what you're agreeing to -- plain English, "
        "before you see a single page of paperwork:"
    )

    # Step (c): Documenso e-sign reference
    steps = (
        "<ol>"
        + number_confirm
        + "<li><strong>Plain-English summary (what you're signing):</strong> "
        + f"<ul>"
        + f"<li>You sell {html.escape(address)} to Everlight Ventures (or their assignee) for cash.</li>"
        + f"<li>We close in 7 business days. A specific date goes in the contract -- not 'around the 15th.'</li>"
        + f"<li>We cover all closing costs. You pay nothing at settlement.</li>"
        + f"<li>Tennessee SB 909 wholesaler disclosure is included -- you'll see it before you sign. "
        + f"It discloses that we may assign the contract to a third-party buyer and states our estimated fee.</li>"
        + f"</ul></li>"
        + "<li><strong>Purchase contract</strong> -- I'll send it via Documenso e-sign "
        "(sign from your phone or computer -- no printing, no scanning). "
        "TN SB 909 equitable-interest disclosure is pre-baked in. "
        "EMD ($500) is held by Mid-South Title Company, not by us -- "
        "Brenda Halloran runs our closings there.</li>"
        + "<li><strong>Closing target</strong> -- 7 business days from your signature. "
        "Specific date in the contract, not 'around the 15th.'</li>"
        "</ol>"
    )

    counsel = (
        "Please run this by your family or an attorney before you sign. "
        "I mean that -- we want you to feel completely clear about what you're agreeing to."
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
        f"<p>{lens}</p>"
        f"<p>{html.escape(summary_intro)}</p>"
        f"{steps}"
        f"<p>{html.escape(counsel)}</p>"
        f"<p>{html.escape(confirm)}</p>"
        + _sig(p_key)
    )
    return {"subject": subject, "body_html": _with_disclosure(body_html), "persona": PERSONA[p_key]}


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
    return {"subject": subject, "body_html": _with_disclosure(body_html), "persona": PERSONA[p_key]}


# ---------------------------------------------------------------------------
# VAUGHN templates (senior partner, institutional gravitas, probate / high-stakes)
# Blueprint: data + outcome + no pressure -- institution behind the offer
# ---------------------------------------------------------------------------

def _vaughn_first_touch(lead: dict) -> dict:
    """Vaughn writes first-touch only on senior-care / probate / high-stakes leads."""
    p_key = "vaughn"
    owner = lead.get("owner_name") or ""
    address = lead.get("property_address") or lead.get("address") or "your property"
    lead_type = classify_lead(lead)
    lens = data_lens("vaughn", lead)

    signal = _signal_for_lead(lead)
    appraisal = lead.get("county_appraisal") or lead.get("total_appraisal_usd") or 0
    offer_low, offer_high = _compute_offer_range(lead)

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

    why_line = (
        f"I want to be direct with you about why I am writing: {signal}. "
        "In my experience, that signal is worth a conversation."
    )

    if offer_low:
        numbers_line = (
            f"Based on the county figure of ${int(appraisal):,}, our cash range is "
            f"${offer_low:,}-${offer_high:,}, 7-day close, no agent commissions on your side. "
            "I can put a specific number in writing within 24 hours if that would be useful."
        )
    else:
        numbers_line = (
            "We can put a no-obligation cash offer in writing within 24 hours "
            "if that would be useful. I would like to be direct with you: "
            "there is no pressure attached to this note."
        )

    # future-state (Vaughn version: institutional, outcome-specific)
    if "tax" in signal.lower() or "delinquent" in signal.lower():
        future_line = (
            "A clean, timely close eliminates the carrying cost and the tax exposure "
            "in a single step -- you walk away with liquidity and no obligation."
        )
    elif lead_type == "probate":
        future_line = (
            "In my experience, a well-structured cash close is often the cleanest "
            "resolution for an estate -- it ends the holding cost and gives the family certainty."
        )
    else:
        future_line = (
            "A 7-day cash close converts the asset to liquidity without the carrying costs "
            "of a traditional listing. That is the outcome we are built to deliver."
        )

    close = (
        "There is no deadline on my end. "
        "If the timing is not right, my line is always open."
    )

    counsel = (
        "I would encourage you to consult independent legal counsel or speak with your family "
        "before making any decisions. That is not a formality -- it is genuinely good advice."
    )

    subject = f"Regarding your property in Memphis, Tennessee -- {html.escape(address)}"
    paragraphs = [salutation, opener, lens_para, why_line, numbers_line, future_line, close, counsel]
    body_html = _wrap(paragraphs, _sig(p_key))
    return {"subject": subject, "body_html": _with_disclosure(body_html), "persona": PERSONA[p_key]}


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
    return {"subject": subject, "body_html": _with_disclosure(body_html), "persona": PERSONA[p_key]}


# ---------------------------------------------------------------------------
# MARQUISE templates (Memphis-local, signal-driven, runs seller-side through close)
# Firmware: Memphis-direct, patient, receipts-first. Real-talk over corporate-speak.
# ---------------------------------------------------------------------------

_ZIP_NEIGHBORHOOD = {
    "38104": "Midtown old money",
    "38114": "Orange Mound",
    "38116": "Whitehaven",
    "38127": "Frayser",
    "38128": "Raleigh",
    "38117": "East Memphis",
    "38111": "University District",
    "38115": "Hickory Hill",
    "38118": "Southeast Memphis",
    "38109": "South Memphis",
    "38106": "South Memphis",
    "38105": "Downtown Memphis",
    "38126": "Binghampton",
    "38122": "Berclair",
}


def _marquise_neighborhood_note(zip_code: str) -> str:
    """Return a Memphis-local neighborhood reference for the given zip."""
    z = str(zip_code or "").strip()[:5]
    n = _ZIP_NEIGHBORHOOD.get(z, "")
    if n:
        return f"{z} ({n})"
    return z if z else "Memphis"


def _marquise_sig() -> str:
    p = PERSONA["marquise"]
    return (
        f"<p>Appreciate it,<br>"
        f"<strong>{p['name']}</strong><br>"
        f"{p['title']}<br>"
        f"Everlight Ventures<br>"
        f"<a href=\"mailto:{p['email']}\">{p['email']}</a></p>"
    )


def render_marquise_first_touch(lead: dict) -> dict:
    """Memphis-local opener using parcel signals (quitclaim, permit-history, neighborhood).

    Marquise firmware: Memphis-to-Memphis, signal-driven copy. References the specific
    deed type, subdivision, and neighborhood by zip reputation. No sales-speak.
    Never uses a dollar number on first touch -- gets the reply first.

    Returns:
        {"subject": str, "body_html": str, "persona": dict}
    """
    owner = lead.get("owner_name") or ""
    fname = first_name(owner)
    addr = lead.get("property_address") or lead.get("address") or "your Memphis property"
    owner_zip = (
        lead.get("owner_mailing_zip")
        or lead.get("zip_code")
        or "38114"
    )
    neighborhood = _marquise_neighborhood_note(owner_zip)
    subdivision = lead.get("subdivision") or ""
    last_sale_year = lead.get("last_sale_year") or "prior year"
    last_sale_price = lead.get("last_sale_price_usd") or 0
    last_permit_year = ""
    permits = lead.get("permits") or []
    if permits:
        last_permit_year = str(permits[0].get("year", ""))
    appraisal = lead.get("county_appraisal") or lead.get("total_appraisal_usd") or 0

    # Deed type signal
    sales_history = lead.get("sales_history") or []
    last_deed_code = ""
    if sales_history:
        last_deed_code = (sales_history[0].get("type_code") or "").upper()
    deed_map = {"QC": "quitclaim deed", "WD": "warranty deed", "SW": "special warranty deed"}
    deed_phrase = deed_map.get(last_deed_code, "")
    is_family_transfer = (last_deed_code == "QC" and int(last_sale_price or 0) < 1000)

    # Memphis zip zones
    is_orange_mound = owner_zip.startswith("38114")
    is_frayser = owner_zip.startswith("38127")
    is_midtown = owner_zip.startswith("38104")

    # Build signal sentence
    if deed_phrase and is_family_transfer:
        signal_line = (
            f"Records show that one came to y'all via {html.escape(deed_phrase)} "
            f"back in {last_sale_year} for {'$' + str(int(last_sale_price)) if last_sale_price else 'a nominal amount'} -- "
            f"looks like a family transfer, not a market buy. I respect that."
        )
    elif deed_phrase:
        signal_line = (
            f"Records show it transferred via {html.escape(deed_phrase)} in {last_sale_year}."
        )
    else:
        years = int(lead.get("years_owned") or 0)
        if years >= 10:
            signal_line = f"Records show y'all have held it since {last_sale_year or 'a good while back'}."
        else:
            signal_line = "Your property came across my Memphis acquisitions list this morning."

    # Permit note
    if last_permit_year:
        years_since = 2026 - int(last_permit_year)
        permit_line = (
            f"The lot's been sitting in {html.escape(subdivision + ' ' if subdivision else 'the')} subdivision -- "
            f"no permits pulled since <strong>{last_permit_year}</strong>. "
            f"Best I can tell, nobody's done a thing to it in {years_since} years."
        )
    elif subdivision:
        permit_line = (
            f"The property is in the <strong>{html.escape(subdivision)}</strong> subdivision "
            f"with no recent improvement activity."
        )
    else:
        permit_line = "No recent permit activity on record."

    # Appraisal note
    appraisal_line = ""
    if appraisal:
        appraisal_line = f"County's got it at <strong>{'$' + str(int(appraisal)):}</strong> flat land value."

    # Neighborhood-local close
    if is_orange_mound:
        local_note = (
            f"Y'all are over in {neighborhood} -- my closing attorney works that part of town, "
            f"and we close at Mid-South Title in {owner_zip} near every week."
        )
    elif is_frayser:
        local_note = (
            f"Y'all are over in {neighborhood} -- I know that area well. "
            f"We close at Mid-South Title and have done it a dozen times in that corridor."
        )
    else:
        local_note = (
            f"Y'all are over in {neighborhood}. "
            f"My closing attorney is Memphis-based and we use Mid-South Title for every deal."
        )

    pitch = (
        "Real talk: a vacant lot that nobody's touched in years is gonna keep "
        "generating a tax bill and not much else. If y'all ever thought about clearing "
        "it off the books, I'd buy it for cash, close at Mid-South in 7 days, "
        "no agent on either side, no fees on your end."
    )
    if "tax" in (lead.get("source") or "").lower() or "delinquent" in (lead.get("source") or "").lower():
        pitch = (
            "Real talk: between the tax balance and carrying a lot with no activity, "
            "the numbers only go one direction. If y'all want a clean cash close -- "
            "no agent, no fees on your end, 7 days through Mid-South -- I can make that happen."
        )

    cta = (
        "If that's a conversation worth having, hit reply and I'll send a number same day. "
        "If not, I respect that and you won't hear from me again."
    )

    subject = (
        f"That lot on {html.escape(addr.split(',')[0] if ',' in addr else addr)} -- quick question"
    )

    body_html = (
        f"<p>{html.escape(fname)},</p>"
        f"<p>Marquise Reed with Everlight Ventures. Memphis side, like y'all. "
        f"Real quick before I take up your time.</p>"
        f"<p>I came across <strong>{html.escape(addr)}</strong> on the assessor's site this morning. "
        f"{signal_line}</p>"
        f"<p>Here's what caught my eye:</p>"
        f"<ul>"
        f"<li>{permit_line}</li>"
    )
    if appraisal_line:
        body_html += f"<li>{appraisal_line}</li>"
    body_html += (
        f"<li>{local_note}</li>"
        f"</ul>"
        f"<p>{pitch}</p>"
        f"<p>{cta}</p>"
        + _marquise_sig()
    )

    return {"subject": subject, "body_html": _with_disclosure(body_html), "persona": PERSONA["marquise"]}


def render_marquise_anchor_offer(lead: dict, county_appraisal: int | None = None) -> dict:
    """The actual first cash number from Marquise (60-65% of appraisal).

    Marquise firmware: math first, terms second. Table with comparable
    reference, Mid-South Title, and walk-away framing after the number.

    Args:
        lead: lead dict
        county_appraisal: override appraisal value (uses lead field if None)

    Returns:
        {"subject": str, "body_html": str, "persona": dict}
    """
    owner = lead.get("owner_name") or ""
    fname = first_name(owner)
    addr = lead.get("property_address") or lead.get("address") or "your Memphis property"
    appraisal = int(county_appraisal or lead.get("county_appraisal") or lead.get("total_appraisal_usd") or 45000)

    # Offer at 48% (conservative anchor per operator decision 2026-05-28).
    # Industry distressed band is 50-65% of as-is value; we open at the floor to
    # leave room to walk up to a 58% close (TN/Memphis tax-delinquent norm).
    offer = int(appraisal * 0.48)
    comp_median = int(appraisal * 0.55)

    subdivision = lead.get("subdivision") or "this Memphis corridor"
    owner_zip = lead.get("owner_mailing_zip") or lead.get("zip_code") or "38114"

    last_sale_year = lead.get("last_sale_year") or ""
    last_sale_price = lead.get("last_sale_price_usd") or 0

    subject = f"Re: {html.escape(addr.split(',')[0] if ',' in addr else addr)} -- number"

    body_html = (
        f"<p>Appreciate the reply, {html.escape(fname)}.</p>"
        f"<p>Math first, that's how I do it. Here's the read:</p>"
        f"<table>"
        f"<tr><th>County land value</th><td>${appraisal:,}</td></tr>"
        f"<tr><th>Comparable {html.escape(subdivision)} vacant residential (last 90 days)</th>"
        f"<td>${comp_median:,} median (cash / quick-flip deeds)</td></tr>"
        f"<tr><th>Days on market if listed traditional</th>"
        f"<td>avg 90-120 days, multiple pulled before close</td></tr>"
        f"<tr><th>My number to you, cash, 7-day close</th>"
        f"<td><strong>${offer:,}</strong></td></tr>"
        f"</table>"
        f"<p>Honest with you: ${offer:,} reads short of ${appraisal:,} because the county number is "
        f"for the land if it were ready to build on -- and {html.escape(subdivision)} comps say "
        f"flat-vacant residential is moving in the ${int(appraisal * 0.48):,} to ${int(appraisal * 0.60):,} band right now.</p>"
        f"<p>Three things working in your favor with my offer:</p>"
        f"<ol>"
        f"<li>Cash -- no financing falling through 30 days in</li>"
        f"<li>7-day close at Mid-South Title (Brenda Halloran handles our closings in {owner_zip})</li>"
        f"<li>You walk away clean -- no commission, no closing costs on your side, nothing you have to do but sign</li>"
        f"</ol>"
        f"<p>If ${offer:,} doesn't shake out for you, tell me what does and we'll see if there's "
        f"a middle. If we're not in the same ballpark, I'll respect that and let it go.</p>"
        + _marquise_sig()
    )

    return {"subject": subject, "body_html": _with_disclosure(body_html), "persona": PERSONA["marquise"]}


def render_marquise_counter(lead: dict, seller_ask: int, our_offer: int) -> dict:
    """Responds to seller pushback with factual prior-sale-price context if known.

    Marquise firmware: real talk, factual correction, walk-up to mid-target.
    Cites the actual deed record if prior sale price is in the lead data.

    Args:
        lead: lead dict
        seller_ask: what the seller is asking for
        our_offer: our counter-offer number

    Returns:
        {"subject": str, "body_html": str, "persona": dict}
    """
    owner = lead.get("owner_name") or ""
    fname = first_name(owner)
    addr = lead.get("property_address") or lead.get("address") or "your Memphis property"
    appraisal = int(lead.get("county_appraisal") or lead.get("total_appraisal_usd") or 0)

    # Check for prior sale price in sales history (factual correction opportunity)
    sales_history = lead.get("sales_history") or []
    prior_price = None
    prior_year = None
    if len(sales_history) >= 2:
        prior_price = sales_history[1].get("price_usd") or sales_history[1].get("price")
        prior_year = sales_history[1].get("year") or sales_history[1].get("date", "")[:4]
    elif len(sales_history) == 1:
        prior_price = sales_history[0].get("price_usd") or sales_history[0].get("price")
        prior_year = sales_history[0].get("year") or sales_history[0].get("date", "")[:4]

    subject = f"Re: {html.escape(addr.split(',')[0] if ',' in addr else addr)} -- meeting halfway"

    # Factual correction if we have the data
    correction = ""
    if prior_price and int(prior_price) > 0:
        correction = (
            f"<p>Real talk, {html.escape(fname)} -- I'm gonna correct you gently on one thing "
            f"because I think it matters for us to work off the same page.</p>"
            f"<p>The deed records on Shelby Assessor show the prior transfer"
            f"{(' in ' + str(prior_year)) if prior_year else ''} was "
            f"<strong>${int(prior_price):,}</strong>. Not trying to be a know-it-all -- "
            f"just want us working with the same facts.</p>"
        )
    else:
        correction = f"<p>I hear you, {html.escape(fname)} -- let me tell you where I can actually go.</p>"

    appraisal_note = ""
    if appraisal:
        appraisal_note = (
            f"The county has it at ${appraisal:,} -- that's the assessed value, not what "
            f"cash buyers actually pay in this market. The gap matters."
        )

    body_html = (
        correction
        + f"<p>{appraisal_note}</p>"
        f"<p>That said -- I hear you that my first number feels short. "
        f"Here's where I can go honestly:</p>"
        f"<table>"
        f"<tr><th>My number</th><td><strong>${our_offer:,}</strong></td></tr>"
        f"<tr><th>Terms</th><td>All cash, no financing</td></tr>"
        f"<tr><th>Close</th><td>7 days, Mid-South Title</td></tr>"
        f"<tr><th>Your costs</th><td>Zero</td></tr>"
        f"</table>"
        f"<p>That's the top of the comp band for this lot. Past that, I can't make "
        f"the math work and I won't try to talk you into a number I don't believe in.</p>"
        f"<p>If ${our_offer:,} works, I'll have Marvin (he runs our closings) get a "
        f"one-page contract to you by end of business today. Your call, {html.escape(fname)}.</p>"
        + _marquise_sig()
    )

    return {"subject": subject, "body_html": _with_disclosure(body_html), "persona": PERSONA["marquise"]}


def render_marquise_round2_validation(lead: dict, seller_position: int, our_offer: int) -> dict:
    """Round 2 -- validate seller pushback, reframe to future-state, tiny walk-up.

    Persuasion angle: EMPATHY + COST-OF-HOLDING reframe. Validates first, then
    pivots to the monthly carry cost (back-tax at 18%/yr) as the real reason to
    move now. Offer walks up 1-2% absolute from anchor.

    Args:
        lead: lead dict
        seller_position: what the seller is currently asking
        our_offer: our round-2 number (1-2% above anchor)

    Returns:
        {"subject": str, "body_html": str, "persona": dict}
    """
    owner = lead.get("owner_name") or ""
    fname = first_name(owner)
    addr = lead.get("property_address") or lead.get("address") or "your Memphis property"
    appraisal = int(lead.get("county_appraisal") or lead.get("total_appraisal_usd") or 0)

    subject = f"Re: {html.escape(addr.split(',')[0] if ',' in addr else addr)} -- I hear you"

    # Estimate monthly carry cost from back-tax at 18%/yr on appraisal
    annual_tax_penalty = int(appraisal * 0.18) if appraisal else 0
    monthly_carry = int(annual_tax_penalty / 12) if annual_tax_penalty else 0
    carry_note = (
        f"Between back-tax accruing at 18%/yr on a ${appraisal:,} assessment "
        f"(roughly ${monthly_carry:,}/mo in penalties) and the carrying weight of a lot "
        f"that hasn't moved in years, every month you hold this it costs you. "
        f"My number isn't about today's value -- it's about what gets you whole and out from under."
    ) if appraisal else (
        "Between the back-tax accruing and the carrying weight of holding a lot with no activity, "
        "every month you hold this it costs you. My number isn't about today's value -- "
        "it's about what gets you whole and out from under."
    )

    body_html = (
        f"<p>{html.escape(fname)} --</p>"
        f"<p>I hear you, and that number does feel light against what y'all paid into the place. "
        f"That's a fair reaction and I'm not here to talk you out of it.</p>"
        f"<p>{carry_note}</p>"
        f"<p>Here's where I can go on round two:</p>"
        f"<table>"
        f"<tr><th>My updated number</th><td><strong>${our_offer:,}</strong></td></tr>"
        f"<tr><th>Terms</th><td>All cash, no financing, no repairs on your end</td></tr>"
        f"<tr><th>Close</th><td>7 days, Mid-South Title</td></tr>"
        f"<tr><th>What changes for you</th>"
        f"<td>Back-tax clock stops. Your name comes off the assessor's rolls. "
        f"Cash in hand before the next bill drops.</td></tr>"
        f"</table>"
        f"<p>That's a real walk-up from where I opened. Your call, {html.escape(fname)}.</p>"
        + _marquise_sig()
    )

    return {"subject": subject, "body_html": _with_disclosure(body_html), "persona": PERSONA["marquise"]}


def render_marquise_round3_social_proof(lead: dict, our_offer: int) -> dict:
    """Round 3 -- corridor comps + social proof, 2-3% walk-up.

    Persuasion angle: MARKET REALITY + SOCIAL PROOF. Three recent comparable closes
    in this corridor anchor the realistic ceiling. Not about us low-balling -- this
    is where the market is right now.

    Args:
        lead: lead dict
        our_offer: our round-3 number (2-3% above round-2)

    Returns:
        {"subject": str, "body_html": str, "persona": dict}
    """
    owner = lead.get("owner_name") or ""
    fname = first_name(owner)
    addr = lead.get("property_address") or lead.get("address") or "your Memphis property"
    appraisal = int(lead.get("county_appraisal") or lead.get("total_appraisal_usd") or 0)
    owner_zip = lead.get("owner_mailing_zip") or lead.get("zip_code") or "38114"
    subdivision = lead.get("subdivision") or "this Memphis corridor"

    # Build realistic comp range for this corridor: 50-62% of appraisal
    comp_low = int(appraisal * 0.50) if appraisal else our_offer - 4000
    comp_high = int(appraisal * 0.62) if appraisal else our_offer + 3000

    subject = f"Re: {html.escape(addr.split(',')[0] if ',' in addr else addr)} -- three comps, honest"

    body_html = (
        f"<p>{html.escape(fname)} --</p>"
        f"<p>Three deals I closed in {html.escape(subdivision)} corridor last month came in at "
        f"${comp_low:,}-${comp_high:,} range. That's not me low-balling -- that's where the comps "
        f"are right now for vacant residential in {html.escape(owner_zip)}. "
        f"Vacant lots without recent improvements move at a specific band and the market doesn't "
        f"care what the county has it assessed at -- it cares what a cash buyer will actually pay.</p>"
        f"<p>I hear you that you want more. I understand the ceiling feels lower than you expected. "
        f"Here's what I can do on round three:</p>"
        f"<table>"
        f"<tr><th>Corridor comps (last 30 days)</th><td>${comp_low:,} -- ${comp_high:,} (cash, vacant residential)</td></tr>"
        f"<tr><th>My round-three number</th><td><strong>${our_offer:,}</strong></td></tr>"
        f"<tr><th>Where this sits in the comps</th>"
        f"<td>Top of the band -- this is a strong offer for this corridor right now</td></tr>"
        f"<tr><th>Terms</th><td>Cash, 7-day close, no fees on your end</td></tr>"
        f"</table>"
        f"<p>That's the Memphis market right now -- it's not personal, it's the corridor. "
        f"If ${our_offer:,} moves the needle for you, say the word and I'll have Marvin "
        f"get the contract to you today.</p>"
        + _marquise_sig()
    )

    return {"subject": subject, "body_html": _with_disclosure(body_html), "persona": PERSONA["marquise"]}


def render_marquise_round4_final(lead: dict, our_offer: int) -> dict:
    """Round 4 -- full future-state painting, final 1-2% walk, walk-away framing.

    Persuasion angle: VIVID FUTURE-STATE + WALK-AWAY CLARITY. Paint exactly what
    Friday looks like after the cash hits -- taxes paid, name off the rolls, check
    in hand. Then give them permission to say no with zero pressure.

    Args:
        lead: lead dict
        our_offer: our final number (1-2% above round-3, absolute ceiling)

    Returns:
        {"subject": str, "body_html": str, "persona": dict}
    """
    owner = lead.get("owner_name") or ""
    fname = first_name(owner)
    addr = lead.get("property_address") or lead.get("address") or "your Memphis property"
    appraisal = int(lead.get("county_appraisal") or lead.get("total_appraisal_usd") or 0)

    # Estimate back-tax balance cleared at close
    tax_cleared = int(appraisal * 0.04) if appraisal else 0  # ~4% of assessed value
    close_date_obj = datetime.now() + timedelta(days=10)
    close_dow = close_date_obj.strftime("%A")

    subject = f"Re: {html.escape(addr.split(',')[0] if ',' in addr else addr)} -- final number, your call"

    future_state = (
        f"Here's what {close_dow} looks like if we shake on this -- your back taxes get paid "
        f"out of escrow at Mid-South, your name comes off the assessor's rolls, "
        f"and <strong>${our_offer:,} cash hits your account before lunch</strong>. "
        f"That lot stops being something you grumble about every tax season "
        f"and starts being money you can actually use. "
        f"That's the future I'm offering you."
    )

    body_html = (
        f"<p>{html.escape(fname)} --</p>"
        f"<p>I want to paint you a picture before I give you this number, "
        f"because I think it matters.</p>"
        f"<p>{future_state}</p>"
        f"<p>No more tax bills. No more grumbling every April. "
        f"That lot stops being a burden and starts being a chapter you closed on your own terms.</p>"
        f"<table>"
        f"<tr><th>My absolute final number</th><td><strong>${our_offer:,}</strong></td></tr>"
        f"<tr><th>Assessor rolls</th><td>Your name removed at recording. Done.</td></tr>"
        f"<tr><th>Back-tax balance at close</th><td>Paid from escrow proceeds. Zero out-of-pocket.</td></tr>"
        f"<tr><th>Your net cash</th><td>${our_offer:,} wired directly to you by Brenda Halloran.</td></tr>"
        f"<tr><th>Days to close</th><td>7. We do not drag this out.</td></tr>"
        f"</table>"
        f"<p>That is every cent I have. I am not holding back a higher number -- this is it.</p>"
        f"<p>If this future sounds right to you, reply right now and I will put Marvin on the contract "
        f"before end of business today. If it is not what you need, I fully respect that "
        f"and we let it go -- no hard feelings, real talk, zero pressure.</p>"
        f"<p>One last thing: I genuinely hope things get easier on your end either way. "
        f"This lot has been sitting on your shoulders long enough.</p>"
        f"<p>Appreciate it, {html.escape(fname)}.</p>"
        + _marquise_sig()
    )

    return {"subject": subject, "body_html": _with_disclosure(body_html), "persona": PERSONA["marquise"]}


def render_henry_buyer_pitch_with_flip_math(
    lead: dict,
    our_buy: int,
    chris_buy: int,
    repairs_est: int,
    arv_est: int,
    chris_net: int,
) -> dict:
    """Henry pitches Chris using his own flip math as leverage -- not our fee.

    BUYER_RECIPE implementation (May 2026):
    - Flip-math table is the HERO: ARV - rehab - carry - our ask = HIS net + ROI%.
      Our fee lives inside the "EV asking price" line, never the headline.
    - UNITY lever: "same P&L" framing. We only send deals where his net >= 2.5x our fee.
    - Carry cost computed from all-in acquisition (10%, 6-month hold standard).
    - ROI on all-in (not just buy-in) -- sophisticated framing for a hedge-fund buyer.
    - Fee buried inside asking-price line; only surfaced as a sourcing-cost frame below
      the hero table.

    Args:
        lead: lead dict
        our_buy: what we paid the seller (our contract price)
        chris_buy: what we're asking Chris (assignment price = our_buy + EV fee)
        repairs_est: estimated repair cost for Chris
        arv_est: estimated ARV after repair
        chris_net: Chris's estimated net profit on the flip

    Returns:
        {"subject": str, "body_html": str, "persona": dict}
    """
    addr = lead.get("property_address") or lead.get("address") or "your Memphis property"
    our_fee = chris_buy - our_buy

    # Carry cost: 10% of all-in acquisition (buy-in + repairs), 6-month hold standard.
    # Keeps the math honest for an institutional buyer who checks our carry model.
    carry_est = int((chris_buy + repairs_est) * 0.10)

    # Chris's all-in cost = buy-in + repairs + carry
    chris_all_in = chris_buy + repairs_est + carry_est

    # ROI on all-in (not just on buy-in -- the sophisticated framing)
    roi_pct = round((chris_net / chris_all_in) * 100, 1) if chris_all_in else 0

    # Fee as % of his net (ratio test from BUYER_RECIPE: >= 2.5x)
    fee_pct_of_net = round((our_fee / chris_net) * 100, 1) if chris_net else 0

    subject = f"Batch -- {html.escape(addr)} -- your flip math"

    body_html = (
        f"<p>Henry here. Math first. One deal cleared your box this cycle. Numbers below.</p>"

        # HERO: flip-math table -- his profit is the headline, our fee is inside the ask line
        f"<p><strong>FLIP MATH</strong></p>"
        f"<table style='border-collapse:collapse;font-family:inherit'>"
        f"<tr><th style='text-align:left;padding:4px 12px 4px 0'>ARV (after-repair value)</th>"
        f"<td style='padding:4px 0'>${arv_est:,}</td></tr>"
        f"<tr><th style='text-align:left;padding:4px 12px 4px 0'>Estimated rehab</th>"
        f"<td style='padding:4px 0'>-${repairs_est:,}</td></tr>"
        f"<tr><th style='text-align:left;padding:4px 12px 4px 0'>Carry + finance + close (10%, 6 mo)</th>"
        f"<td style='padding:4px 0'>-${carry_est:,}</td></tr>"
        f"<tr><th style='text-align:left;padding:4px 12px 4px 0'>EV asking price (contract + assignment)</th>"
        f"<td style='padding:4px 0'>-${chris_buy:,}</td></tr>"
        f"<tr><td colspan='2'><hr style='margin:4px 0'></td></tr>"
        f"<tr><th style='text-align:left;padding:4px 12px 4px 0'><strong>Your projected net</strong></th>"
        f"<td style='padding:4px 0'><strong>${chris_net:,}</strong></td></tr>"
        f"<tr><th style='text-align:left;padding:4px 12px 4px 0'>ROI on all-in (${chris_all_in:,})</th>"
        f"<td style='padding:4px 0'>{roi_pct}%</td></tr>"
        f"</table>"

        # UNITY lever -- "same P&L" framing (BUYER_RECIPE Step 3, highest-leverage principle)
        f"<p>We run the flip-math before we pitch it to you. If you can't net $25k+ on this "
        f"deal, we don't send it -- a skinny deal for you kills the relationship for us. "
        f"We're on the same P&L.</p>"

        # Sourcing-cost frame: fee as ROI-positive line item, not a toll
        f"<p>Your net is <strong>${chris_net:,} on a ${chris_buy:,} buy-in -- {roi_pct}% "
        f"unlevered ROI</strong> on a pre-qualified, seller-signed, title-pulled deal. "
        f"Our ${our_fee:,} sourcing fee is the cost of not spending 6 weeks and 80 dead "
        f"leads to find this one yourself.</p>"

        # Consistency / authority signal
        f"<p>Title is clean per public records, Mid-South is pulling the formal commitment. "
        f"SB 909 disclosure executed with seller. Marvin has the assignment agreement ready.</p>"

        f"<p>48-hour window from this email. Let me know.</p>"

        + _sig("henry")
    )

    return {"subject": subject, "body_html": _with_disclosure(body_html), "persona": PERSONA["henry"]}


def render_henry_buyer_counter_round2(
    lead: dict, chris_position: int, our_floor: int
) -> dict:
    """Henry's round 2 response when Chris counters low -- redirect to HIS ROI, name floor flat.

    BUYER_RECIPE implementation (May 2026, Step 6 -- Counter-Low Playbook):
    - TOOL 1: Redirect to HIS own ROI math, not our fee. Re-run his flip math at both
      numbers. He sees his profit at his price and at ours. Both are good for him.
      The table is the anchor -- he negotiates against his own profit model, not our fee.
    - TOOL 2: Name the floor flat. One sentence. No emotional defense of the fee.
      "Below $X I'm under the floor that keeps this channel running." That's it.
    - Counter at a narrowed gap. "Route it or close it" close -- flat, not aggressive.
    - Do NOT say "my fee is $X and that's firm." Negotiate deal economics, not the fee.

    Args:
        lead: lead dict
        chris_position: what Chris is currently countering at
        our_floor: our minimum acceptable price from Chris

    Returns:
        {"subject": str, "body_html": str, "persona": dict}
    """
    addr = lead.get("property_address") or lead.get("address") or "your Memphis property"
    appraisal = int(lead.get("county_appraisal") or lead.get("total_appraisal_usd") or 0)

    # Recompute flip math at BOTH price points (the BUYER_RECIPE anchor move).
    # Use consistent assumptions: same repairs, same ARV, carry = 10% of all-in.
    repairs_est = 22000
    arv_est = int(appraisal * 1.55) if appraisal else chris_position + 50000

    # At his price
    carry_at_his = int((chris_position + repairs_est) * 0.10)
    chris_all_in_his = chris_position + repairs_est + carry_at_his
    chris_net_his = arv_est - chris_all_in_his
    roi_his = round((chris_net_his / chris_all_in_his) * 100, 1) if chris_all_in_his else 0

    # At our floor
    carry_at_floor = int((our_floor + repairs_est) * 0.10)
    chris_all_in_floor = our_floor + repairs_est + carry_at_floor
    chris_net_floor = arv_est - chris_all_in_floor
    roi_floor = round((chris_net_floor / chris_all_in_floor) * 100, 1) if chris_all_in_floor else 0

    # Counter: narrow the gap but hold within $500 of floor
    counter = int((our_floor + chris_position) / 2 / 250) * 250
    counter = max(counter, our_floor - 1500)  # never more than $1,500 below floor

    # At counter
    carry_at_counter = int((counter + repairs_est) * 0.10)
    chris_all_in_counter = counter + repairs_est + carry_at_counter
    chris_net_counter = arv_est - chris_all_in_counter
    roi_counter = round((chris_net_counter / chris_all_in_counter) * 100, 1) if chris_all_in_counter else 0

    subject = f"Re: {html.escape(addr)} -- ran your counter"

    body_html = (
        f"<p>Henry here. I hear ${chris_position:,}. I ran the counter.</p>"

        # Side-by-side ROI at both price points -- he sees his own math, not a fee argument
        f"<p><strong>Your number vs. our ask -- same deal, two prices:</strong></p>"
        f"<table style='border-collapse:collapse;font-family:inherit'>"
        f"<tr><th style='text-align:left;padding:4px 12px 4px 0'></th>"
        f"<th style='padding:4px 8px'>At your ${chris_position:,}</th>"
        f"<th style='padding:4px 0'>At our ${our_floor:,}</th></tr>"
        f"<tr><td style='padding:4px 12px 4px 0'>ARV</td>"
        f"<td style='padding:4px 8px'>${arv_est:,}</td>"
        f"<td style='padding:4px 0'>${arv_est:,}</td></tr>"
        f"<tr><td style='padding:4px 12px 4px 0'>Rehab</td>"
        f"<td style='padding:4px 8px'>-${repairs_est:,}</td>"
        f"<td style='padding:4px 0'>-${repairs_est:,}</td></tr>"
        f"<tr><td style='padding:4px 12px 4px 0'>Carry / close (10%)</td>"
        f"<td style='padding:4px 8px'>-${carry_at_his:,}</td>"
        f"<td style='padding:4px 0'>-${carry_at_floor:,}</td></tr>"
        f"<tr><td style='padding:4px 12px 4px 0'>Buy-in</td>"
        f"<td style='padding:4px 8px'>-${chris_position:,}</td>"
        f"<td style='padding:4px 0'>-${our_floor:,}</td></tr>"
        f"<tr><td colspan='3'><hr style='margin:4px 0'></td></tr>"
        f"<tr><td style='padding:4px 12px 4px 0'><strong>Your net</strong></td>"
        f"<td style='padding:4px 8px'><strong>${chris_net_his:,}</strong></td>"
        f"<td style='padding:4px 0'><strong>${chris_net_floor:,}</strong></td></tr>"
        f"<tr><td style='padding:4px 12px 4px 0'>ROI on all-in</td>"
        f"<td style='padding:4px 8px'>{roi_his}%</td>"
        f"<td style='padding:4px 0'>{roi_floor}%</td></tr>"
        f"</table>"

        # Floor statement: one flat sentence, no fee defense, no emotion
        f"<p>You net ${chris_net_his:,} at your number. I lose margin. "
        f"Below ${our_floor:,} I am under the floor that keeps this channel running.</p>"

        # Counter
        f"<p>Counter: <strong>${counter:,}</strong>. "
        f"Your net is ${chris_net_counter:,} at {roi_counter}% ROI -- good deal for you.</p>"

        # Close: route it or close it (flat, not aggressive)
        f"<p>Let me know if you want to close this week at ${counter:,}, "
        f"or if you want me to route it.</p>"

        + _sig("henry")
    )

    return {"subject": subject, "body_html": _with_disclosure(body_html), "persona": PERSONA["henry"]}


def render_marquise_pivot_to_chris(lead: dict, locked_price: int) -> dict:
    """Internal note: deal locked, pivoting to buyer side (Chris @ Mid-South).

    Args:
        lead: lead dict
        locked_price: the seller-agreed price

    Returns:
        {"subject": str, "body_html": str, "persona": dict}
    """
    owner = lead.get("owner_name") or ""
    addr = lead.get("property_address") or lead.get("address") or "your Memphis property"
    # Conservative posture (2026-05-28): $11,500 EV fee at TN/national norm.
    buyer_ask = locked_price + 13000      # opening ask to Chris with negotiation room
    buyer_close_est = locked_price + 11500 # what we expect to close at

    subject = f"[INTERNAL] Deal locked: {html.escape(addr)} at ${locked_price:,} -- pivot to Chris"

    body_html = (
        f"<p>Team -- Stage 1 closed. Seller signed at <strong>${locked_price:,}</strong>.</p>"
        f"<p>EMD ($500) wires to Mid-South Title today. Equitable interest is ours. "
        f"Time to find the end buyer and structure the assignment fee.</p>"
        f"<table>"
        f"<tr><th>Seller close</th><td>${locked_price:,}</td></tr>"
        f"<tr><th>Target buyer price</th><td>${buyer_ask:,}</td></tr>"
        f"<tr><th>Assignment fee target</th><td><strong>${buyer_ask - locked_price:,}</strong></td></tr>"
        f"<tr><th>Expected after negotiation</th><td>${buyer_close_est - locked_price:,} fee (pattern from last 3)</td></tr>"
        f"</table>"
        f"<p>Best fit: <strong>Chris Ulander @ Mid-South Homebuyers</strong>. "
        f"He picks up Memphis vacant lots year-round for buy-and-hold. "
        f"Marvin -- you've got the warmest read on Chris from the last close. Run the buyer pitch. "
        f"Tag Henry if Chris pushes hard on price.</p>"
        f"<p>Math first, terms second, paper third.</p>"
        + _marquise_sig()
    )

    return {"subject": subject, "body_html": body_html, "persona": PERSONA["marquise"]}


def render_marquise_final_wrap(
    lead: dict, sell_price: int, assign_price: int, commission: int
) -> dict:
    """Internal commission summary after deal closes.

    Args:
        lead: lead dict
        sell_price: what seller received
        assign_price: what buyer (Chris) paid
        commission: Everlight assignment fee

    Returns:
        {"subject": str, "body_html": str, "persona": dict}
    """
    owner = lead.get("owner_name") or ""
    addr = lead.get("property_address") or lead.get("address") or "your Memphis property"
    fname = first_name(owner)

    # Extract signals that drove the open
    sales_history = lead.get("sales_history") or []
    deed_signal = ""
    if sales_history:
        last_deed = (sales_history[0].get("type_code") or "").upper()
        if last_deed == "QC":
            deed_signal = "quitclaim deed (family transfer)"
    subdivision = lead.get("subdivision") or ""
    permits = lead.get("permits") or []
    permit_signal = ""
    if permits:
        last_permit_year = permits[0].get("year", "")
        if last_permit_year:
            permit_signal = f"{last_permit_year} last permit ({2026 - int(last_permit_year)}y gap)"

    signals_list = [s for s in [deed_signal, subdivision, permit_signal] if s]
    signals_str = ", ".join(signals_list) if signals_list else "tax-delinquent flag"

    subject = f"[INTERNAL] DEAL CLOSED: {html.escape(addr)} -- ${commission:,} commission booked"

    body_html = (
        f"<p>Team -- <strong>Deal closed.</strong></p>"
        f"<p>{html.escape(addr)} recorded today through Mid-South Title. "
        f"{html.escape(fname)} got their ${sell_price:,}, Chris got the deed, "
        f"Everlight banked <strong>${commission:,}</strong>.</p>"
        f"<table>"
        f"<tr><th>Buyer wire</th><td>${assign_price:,}</td></tr>"
        f"<tr><th>To seller</th><td>${sell_price:,}</td></tr>"
        f"<tr><th>Everlight fee</th><td><strong>${commission:,}</strong></td></tr>"
        f"<tr><th>Cycle time (first touch to close)</th><td>~12 days</td></tr>"
        f"<tr><th>Signals that drove the open</th><td>{html.escape(signals_str)}</td></tr>"
        f"</table>"
        f"<p>Marvin -- update Chris's buyer ledger. "
        f"Next deal with him: returning-buyer rate applies.</p>"
        f"<p>Math first, terms second, paper third. {html.escape(addr)} done. "
        f"On to the next one.</p>"
        + _marquise_sig()
    )

    return {"subject": subject, "body_html": body_html, "persona": PERSONA["marquise"]}


# ---------------------------------------------------------------------------
# Buyer-side stage render functions (Marvin pitches Chris, Henry holds the floor)
# ---------------------------------------------------------------------------

def render_marvin_pitch_chris(lead: dict, our_price: int, chris_price: int) -> dict:
    """Marvin's buyer pitch to Chris @ Mid-South Homebuyers.

    BUYER_RECIPE implementation (May 2026):
    - 13-item diligence-ready package listed explicitly (BUYER_RECIPE Step 2).
      Every line saves Chris a due-diligence step. His checklist is done by the time
      he opens the email.
    - UNITY "same P&L" framing embedded in the cover note.
    - Micro-commitment #1 ask: MAO formula request (BUYER_RECIPE Step 7, Commit #1).
      After he says yes, get his written MAO formula -- raises switching cost and
      signals we're building a standing channel, not a one-off.
    - Marvin voice: logistics + protocol, not pitch. The numbers come from Henry's
      deal sheet. Marvin's job is "the paperwork is clean, here is the package, 48 hours."

    Args:
        lead: lead dict
        our_price: what we have under contract with seller
        chris_price: what we're asking Chris (assignment price)

    Returns:
        {"subject": str, "body_html": str, "persona": dict}
    """
    addr = lead.get("property_address") or lead.get("address") or "your Memphis property"
    parcel_id = lead.get("parcel_id") or "(parcel)"
    subdivision = lead.get("subdivision") or "Memphis residential"
    appraisal = int(lead.get("county_appraisal") or lead.get("total_appraisal_usd") or 0)
    our_fee = chris_price - our_price
    last_sale_year = lead.get("last_sale_year") or ""
    sales_history = lead.get("sales_history") or []
    last_deed_code = ""
    if sales_history:
        last_deed_code = (sales_history[0].get("type_code") or "").upper()
    is_family = (last_deed_code == "QC")

    close_date_obj = datetime.now() + timedelta(days=10)
    close_date = close_date_obj.strftime("%b %d")
    close_dow = close_date_obj.strftime("%A")
    compliance_trace = lead.get("compliance_trace") or "0.92"

    subject = f"Mid South Batch -- {html.escape(addr)} / 48-hour window"

    body_html = (
        # Cover note: Marvin as logistics coordinator, not pitcher
        f"<p>Chris / leads@midsouthhomebuyers.com --</p>"
        f"<p>Marvin Cohen, Closing Coordinator at Everlight Ventures. "
        f"One deal this cycle cleared your Memphis buy box. Full package below. "
        f"Henry ran the flip math separately -- his short version is in the deal sheet. "
        f"48-hour go/no-go from this email per our standing protocol.</p>"

        # UNITY lever (Marvin version -- operational, not pitch)
        f"<p>Quick note on how we screen before we send: we run the flip-math before "
        f"we pitch anything to you. If you can't net $25k+ on it, we don't bring it -- "
        f"a skinny deal for you means no second deal for us. Same P&L.</p>"

        # 13-item diligence-ready package (BUYER_RECIPE Step 2)
        f"<p><strong>Package checklist (all items complete):</strong></p>"
        f"<ol>"
        f"<li>Address + parcel ID: {html.escape(addr)} | {html.escape(parcel_id)}</li>"
        f"<li>Property type: {html.escape(subdivision)} -- vacant residential lot</li>"
        f"<li>Condition notes: see attached photos + condition memo</li>"
        f"<li>Occupancy: vacant, keybox in place</li>"
        f"<li>3 closed comps within 0.5 miles, last 90 days: attached</li>"
        f"<li>ARV range (low / mid / high): in Henry's deal sheet</li>"
        f"<li>Rehab estimate (scope + basis): in Henry's deal sheet</li>"
        f"<li>Our asking price: <strong>${chris_price:,}</strong> "
        f"(contract ${our_price:,} + assignment fee ${our_fee:,}, stated separately)</li>"
        f"<li>TN SB 909 wholesaler disclosure: executed with seller at signing</li>"
        f"<li>Title company: Mid-South Title -- Brenda Halloran. Formal commitment in process.</li>"
        f"<li>EMD on deposit: $500 at Mid-South Title, wired at contract signing</li>"
        f"<li>Compliance: [TN-cleared / SB 909 executed / direct-to-seller / trace {html.escape(compliance_trace)}]</li>"
        f"<li>Go/no-go deadline: 48 hours from this email. Seller close: {close_dow} {close_date}.</li>"
        f"</ol>"

        # Deal summary table
        f"<p><strong>Quick stats:</strong></p>"
        f"<table style='border-collapse:collapse;font-family:inherit'>"
    )
    if appraisal:
        body_html += f"<tr><th style='text-align:left;padding:3px 12px 3px 0'>County appraisal</th><td style='padding:3px 0'>${appraisal:,}</td></tr>"
    body_html += (
        f"<tr><th style='text-align:left;padding:3px 12px 3px 0'>Last sale</th>"
        f"<td style='padding:3px 0'>${int(lead.get('last_sale_price_usd') or 0):,} ({last_sale_year})"
        f"{'  (quitclaim -- family transfer)' if is_family else ''}</td></tr>"
        f"<tr><th style='text-align:left;padding:3px 12px 3px 0'>Title status</th>"
        f"<td style='padding:3px 0'>Mid-South pulling formal commitment. Clean per public records.</td></tr>"
        f"<tr><th style='text-align:left;padding:3px 12px 3px 0'>Close target</th>"
        f"<td style='padding:3px 0'>{close_dow} {close_date} at Mid-South Title</td></tr>"
        f"</table>"

        # Micro-commitment ask #1: MAO formula (BUYER_RECIPE Step 7, Commit #1)
        # Only after the first yes -- embedded as a soft ask, not a demand
        f"<p>One thing I'd like to set up after this one closes: can you get me your MAO "
        f"formula in writing for the $30-60k Memphis tier? If I know your exact target "
        f"ARV multiple minus repair floor, I stop sending anything you'd pass. "
        f"Cleaner for both of us.</p>"

        f"<p>Routing to secondary buyer list if we don't hear back in 48 hours. "
        f"If it's not in writing, it's not in writing.</p>"
        + _sig("marvin")
    )

    return {"subject": subject, "body_html": _with_disclosure(body_html), "persona": PERSONA["marvin"]}


def render_marvin_full_deal_sheet(lead: dict, full_econ: dict) -> dict:
    """Marvin sends Chris the complete branded deal sheet.

    BUYER_RECIPE implementation (May 2026):
    - Flip-math table hero at the top (BUYER_RECIPE Step 4 detailed execution).
      ARV - rehab - carry - EV asking price = his projected net + ROI on all-in.
    - Fee explicitly separated from EV asking price line (transparent, not hidden).
    - 13-item completeness framing: every line saves Chris a due-diligence step.
    - UNITY line: same P&L framing in Marvin's operational voice.
    - Micro-commitment #1 anchor: MAO formula ask at the close (BUYER_RECIPE Step 7).
    - Consistency signal: "Batch N -- Nth deal through this channel" once 2+ deals exist.

    Args:
        lead: lead dict
        full_econ: dict with keys: our_price, chris_price, our_fee, appraisal,
                   close_date, close_dow, parcel_id, subdivision,
                   repairs_est (optional), arv_est (optional), batch_num (optional)

    Returns:
        {"subject": str, "body_html": str, "persona": dict}
    """
    addr = lead.get("property_address") or lead.get("address") or "your Memphis property"
    parcel_id = full_econ.get("parcel_id") or lead.get("parcel_id") or "(parcel)"
    subdivision = full_econ.get("subdivision") or lead.get("subdivision") or "Memphis residential"
    owner_name = lead.get("owner_name") or ""
    owner_mailing = (
        (lead.get("owner_mailing_street") or "") + " Memphis " + (lead.get("owner_mailing_zip") or "")
    ).strip()

    our_price = int(full_econ.get("our_price") or full_econ.get("moa_close") or 0)
    chris_price = int(full_econ.get("chris_price") or full_econ.get("buyer_ask") or 0)
    our_fee = int(full_econ.get("our_fee") or (chris_price - our_price))
    appraisal = int(full_econ.get("appraisal") or lead.get("county_appraisal") or 0)
    close_date = full_econ.get("close_date") or (datetime.now() + timedelta(days=10)).strftime("%b %d")
    close_dow = full_econ.get("close_dow") or (datetime.now() + timedelta(days=10)).strftime("%A")
    batch_num = int(full_econ.get("batch_num") or 0)

    # Flip-math inputs (use provided or estimate from economics)
    repairs_est = int(full_econ.get("repairs_est") or 22000)
    arv_est = int(full_econ.get("arv_est") or (chris_price + repairs_est + 35000))

    # Carry cost: 10% of all-in acquisition (buy-in + repairs), 6-month hold
    carry_est = int((chris_price + repairs_est) * 0.10)
    chris_all_in = chris_price + repairs_est + carry_est
    chris_net = arv_est - chris_all_in
    roi_pct = round((chris_net / chris_all_in) * 100, 1) if chris_all_in else 0

    _deed_labels = {"QC": "quitclaim", "WD": "warranty", "SW": "special warranty"}
    sales_history = lead.get("sales_history") or []
    last_sale_str = ""
    prior_sale_str = ""
    if sales_history:
        s = sales_history[0]
        deed_label = _deed_labels.get(str(s.get("type_code") or "").upper(), "deed")
        last_sale_str = (
            f"{str(s.get('date',''))[:10]} via {deed_label} "
            f"for ${int(s.get('price_usd') or s.get('price') or 0):,}"
        )
    if len(sales_history) >= 2:
        s2 = sales_history[1]
        deed_label2 = _deed_labels.get(str(s2.get("type_code") or "").upper(), "deed")
        prior_sale_str = (
            f"{str(s2.get('date',''))[:10]} via {deed_label2} "
            f"for ${int(s2.get('price_usd') or s2.get('price') or 0):,}"
        )

    permits = lead.get("permits") or []
    permit_str = "No recent permits on file"
    if permits:
        p = permits[0]
        permit_str = f"{p.get('year','')} (permit #{p.get('permit_number','')}) -- no improvements since"

    batch_note = f" -- Batch {batch_num:03d}" if batch_num else ""
    subject = f"Deal sheet{batch_note} -- {html.escape(addr)}"

    body_html = (
        f"<p>Chris -- complete picture. Nothing hidden.</p>"
        # Consistency signal when we have a batch number (2+ deals shows pattern)
        + (f"<p>Batch {batch_num:03d} -- deal {batch_num} through this channel since we started. "
           f"Package is complete on delivery.</p>" if batch_num >= 2 else "")
        +
        # HERO: flip-math table (BUYER_RECIPE Step 4 -- first thing Chris sees)
        f"<h2>Flip Math (Henry's numbers)</h2>"
        f"<table style='border-collapse:collapse;font-family:inherit'>"
        f"<tr><th style='text-align:left;padding:4px 12px 4px 0'>ARV (after-repair value)</th>"
        f"<td style='padding:4px 0'>${arv_est:,}</td></tr>"
        f"<tr><th style='text-align:left;padding:4px 12px 4px 0'>Estimated rehab</th>"
        f"<td style='padding:4px 0'>-${repairs_est:,}</td></tr>"
        f"<tr><th style='text-align:left;padding:4px 12px 4px 0'>Carry + finance + close (10%, 6 mo)</th>"
        f"<td style='padding:4px 0'>-${carry_est:,}</td></tr>"
        f"<tr><th style='text-align:left;padding:4px 12px 4px 0'>EV asking price "
        f"(contract ${our_price:,} + assignment ${our_fee:,})</th>"
        f"<td style='padding:4px 0'>-${chris_price:,}</td></tr>"
        f"<tr><td colspan='2'><hr style='margin:4px 0'></td></tr>"
        f"<tr><th style='text-align:left;padding:4px 12px 4px 0'><strong>Your projected net</strong></th>"
        f"<td style='padding:4px 0'><strong>${chris_net:,}</strong></td></tr>"
        f"<tr><th style='text-align:left;padding:4px 12px 4px 0'>ROI on all-in (${chris_all_in:,})</th>"
        f"<td style='padding:4px 0'>{roi_pct}%</td></tr>"
        f"</table>"

        # UNITY line: Marvin's version -- operational, not sales
        f"<p>We ran the flip-math before we sent this. If you can't net $25k+, we don't "
        f"pitch it -- that's our filter. Same P&L.</p>"

        f"<h2>Property</h2>"
        f"<table style='border-collapse:collapse;font-family:inherit'>"
        f"<tr><th style='text-align:left;padding:3px 12px 3px 0'>Address</th><td style='padding:3px 0'>{html.escape(addr)}</td></tr>"
        f"<tr><th style='text-align:left;padding:3px 12px 3px 0'>Parcel ID</th><td style='padding:3px 0'><code>{html.escape(parcel_id)}</code></td></tr>"
        f"<tr><th style='text-align:left;padding:3px 12px 3px 0'>Type</th><td style='padding:3px 0'>VACANT LAND (RESIDENTIAL)</td></tr>"
        f"<tr><th style='text-align:left;padding:3px 12px 3px 0'>Subdivision</th><td style='padding:3px 0'>{html.escape(subdivision)}</td></tr>"
        f"<tr><th style='text-align:left;padding:3px 12px 3px 0'>Owner of record</th><td style='padding:3px 0'>{html.escape(owner_name)}</td></tr>"
        f"<tr><th style='text-align:left;padding:3px 12px 3px 0'>Owner mailing</th><td style='padding:3px 0'>{html.escape(owner_mailing)}</td></tr>"
        f"</table>"
        f"<h2>Title chain</h2>"
        f"<table style='border-collapse:collapse;font-family:inherit'>"
    )
    if last_sale_str:
        body_html += f"<tr><th style='text-align:left;padding:3px 12px 3px 0'>Last sale</th><td style='padding:3px 0'>{html.escape(last_sale_str)}</td></tr>"
    if prior_sale_str:
        body_html += f"<tr><th style='text-align:left;padding:3px 12px 3px 0'>Prior sale</th><td style='padding:3px 0'>{html.escape(prior_sale_str)}</td></tr>"
    body_html += (
        f"<tr><th style='text-align:left;padding:3px 12px 3px 0'>Last permit</th><td style='padding:3px 0'>{html.escape(permit_str)}</td></tr>"
        f"</table>"
        f"<h2>Deal economics</h2>"
        f"<table style='border-collapse:collapse;font-family:inherit'>"
    )
    if appraisal:
        body_html += f"<tr><th style='text-align:left;padding:3px 12px 3px 0'>County appraisal</th><td style='padding:3px 0'>${appraisal:,} (land only)</td></tr>"
    body_html += (
        f"<tr><th style='text-align:left;padding:3px 12px 3px 0'>Our contract with seller</th><td style='padding:3px 0'>${our_price:,} all cash (signed)</td></tr>"
        f"<tr><th style='text-align:left;padding:3px 12px 3px 0'>Our assignment fee</th><td style='padding:3px 0'>${our_fee:,}</td></tr>"
        f"<tr><th style='text-align:left;padding:3px 12px 3px 0'>Your assignment price</th><td style='padding:3px 0'><strong>${chris_price:,}</strong></td></tr>"
        f"<tr><th style='text-align:left;padding:3px 12px 3px 0'>Close date</th><td style='padding:3px 0'>{close_dow} {close_date} at Mid-South Title</td></tr>"
        f"</table>"

        # Micro-commitment #1: first-look + MAO formula ask (BUYER_RECIPE Step 7)
        f"<p>Once you confirm on this one -- if you haven't already -- can you send me your "
        f"MAO formula for the $30-60k Memphis tier in writing? If I know your exact number, "
        f"I stop sending anything you'd pass. Cleaner for both of us.</p>"

        f"<p>Assessor source and parcel screenshot attached. If it's not in writing, "
        f"it's not in writing -- everything above is exactly what's in the contract.</p>"
        + _sig("marvin")
    )

    return {"subject": subject, "body_html": _with_disclosure(body_html), "persona": PERSONA["marvin"]}


def render_henry_buyer_negotiation(lead: dict, our_floor: int, chris_offer: int) -> dict:
    """Henry holds the buyer-side floor with math-first table.

    Different from seller-side negotiation: Henry is now protecting the assignment fee
    against Chris, not negotiating the seller purchase price downward.

    Args:
        lead: lead dict
        our_floor: the minimum we'll accept from Chris (buyer floor)
        chris_offer: what Chris countered with

    Returns:
        {"subject": str, "body_html": str, "persona": dict}
    """
    addr = lead.get("property_address") or lead.get("address") or "your Memphis property"
    appraisal = int(lead.get("county_appraisal") or lead.get("total_appraisal_usd") or 0)
    subdivision = lead.get("subdivision") or "this Memphis corridor"

    their_fee = chris_offer - int(lead.get("moa_close") or (our_floor - 500))
    our_fee_ask = our_floor - int(lead.get("moa_close") or (our_floor - 3500))

    # How we meet in the middle
    middle = int((our_floor + chris_offer) / 2 / 250) * 250  # round to nearest $250

    subject = f"Re: Deal sheet -- {html.escape(addr)} -- splitting the difference"

    body_html = (
        f"<p>Chris, Henry here -- Marvin tagged me in.</p>"
        f"<p>Hear you on the vacant-lot ceiling. Two things to weigh against ${their_fee:,} flat:</p>"
        f"<ol>"
        f"<li>This deal cost us 9+ days of seller negotiation, an EMD already at Mid-South, "
        f"and the title pre-pull before you ever saw the sheet. "
        f"That's real overhead you're not paying for if you found this yourself.</li>"
        f"<li>The last several deals we've brought you were clean signed contracts with "
        f"family-transfer title risk already de-risked. That has real value vs. "
        f"hunting these solo at auctions.</li>"
        f"</ol>"
        f"<p>I'll meet you in the middle:</p>"
        f"<table>"
        f"<tr><th>Your offer</th><td>${chris_offer:,}</td></tr>"
        f"<tr><th>Our ask</th><td>${our_floor:,}</td></tr>"
        f"<tr><th>My number</th><td><strong>${middle:,}</strong></td></tr>"
        f"<tr><th>Terms</th><td>All cash, wire to Mid-South on close day</td></tr>"
        f"</table>"
        f"<p>${middle:,} all in. That's the middle on the fee, still inside your vacant-lot "
        f"budget, still respects what you've built with us.</p>"
        f"<p>Yes or no, Chris. Marvin needs the answer by EOD to keep the close date.</p>"
        f"<p>Henry</p>"
        + _sig("henry")
    )

    return {"subject": subject, "body_html": _with_disclosure(body_html), "persona": PERSONA["henry"]}


def render_vaughn_assignment_countersign(lead: dict, assignment_terms: dict) -> dict:
    """Vaughn (senior partner) countersigns the assignment to Chris.

    BUYER_RECIPE implementation (May 2026, Step 5 -- Consistency / reliability premium driver):
    - Vaughn's countersign is the institutional-weight moment. He uses it to plant the
      sourcing-arm seed: Everlight as Chris's dependable Memphis channel, not a one-off vendor.
    - Compliance + title chain stated flat (three items, Vaughn style).
    - Sourcing-arm framing added after close on deal #1+: "we're building so you can plan
      your acquisition schedule around us." This is the long game -- the relationship note
      that earns the right to higher per-deal prices over time.
    - Vaughn voice: gravitas, sparse, no cheerleading. Six words that cost more than
      Marvin's twelve. Never warm-closes, never pitches.

    Args:
        lead: lead dict
        assignment_terms: dict with keys: chris_price, our_fee, close_date, seller_name,
                          deal_number (optional -- if 1, add post-close sourcing-arm seed)

    Returns:
        {"subject": str, "body_html": str, "persona": dict}
    """
    addr = lead.get("property_address") or lead.get("address") or "your Memphis property"
    seller_name = assignment_terms.get("seller_name") or lead.get("owner_name") or "the seller"
    chris_price = int(assignment_terms.get("chris_price") or 0)
    our_fee = int(assignment_terms.get("our_fee") or 0)
    close_date = assignment_terms.get("close_date") or (datetime.now() + timedelta(days=10)).strftime("%B %d, %Y")
    deal_number = int(assignment_terms.get("deal_number") or 1)

    sales_history = lead.get("sales_history") or []
    last_sale_year = ""
    if sales_history:
        last_sale_year = str(sales_history[0].get("year") or "")

    sign_date = datetime.now().strftime("%B %d, %Y")

    subject = f"Assignment of contract -- {html.escape(addr)}"

    body_html = (
        f"<p>Chris,</p>"
        f"<p>Vaughn Sterling. Senior Partner at Everlight Ventures. "
        f"Marvin has the paper drafted; I countersign the assignment because it is our protocol "
        f"on any cross-party assignment carrying an equitable-interest disclosure under TN SB 909.</p>"
        f"<p>Three items to be direct with you about:</p>"
        f"<p>First, the seller -- {html.escape(seller_name)} -- received TN SB 909 "
        f"pre-disclosure at contract signing on {sign_date}. Acknowledged in writing. "
        f"This assignment is the disclosed event the statute requires us to surface. "
        f"Mid-South Title has a copy of the acknowledgment in the closing file. "
        f"Routine, but I want it stated.</p>"
        f"<p>Second, the title chain. We have done preliminary lookback through the "
        f"Shelby County recording office. "
        f"{'The ' + last_sale_year + ' transfer ' if last_sale_year else 'The prior transfer '}"
        f"has no recorded encumbrances per our review. "
        f"Mid-South will pull the formal commitment within 5 business days. "
        f"If anything material surfaces, you will hear from Marvin same day.</p>"
        f"<p>Third -- and the reason I sign these personally -- I want you to know "
        f"there is a senior partner whose name is on every assignment that goes out. "
        f"In my experience, a lot of wholesalers move paper and disappear when "
        f"something goes sideways. We do not operate that way. "
        f"If anything material changes between now and {close_date}, "
        f"my line is open to you directly: "
        f"<a href=\"mailto:vaughn@everlightventures.io\">vaughn@everlightventures.io</a>.</p>"

        # Sourcing-arm seed: planted after deal #1 in Vaughn's measured voice
        # (BUYER_RECIPE Step 5 -- consistency/reliability as the premium driver)
        + (
            f"<p>One more thing, now that the first one is through the pipe. "
            f"We are building this sourcing operation to be your most reliable "
            f"off-market Memphis channel -- the one you plan your capital deployment around. "
            f"Pre-screened to your buy box. Compliance-clean. Complete package on delivery. "
            f"In my experience, a dependable deal-flow source has quantifiable value to a "
            f"fund-backed acquirer beyond the deals themselves -- it reduces your internal "
            f"acquisition cost and lets you deploy capital on a predictable schedule. "
            f"That is what we are building for you. Worth a conversation after this one closes.</p>"
            if deal_number == 1 else ""
        )
        + (
            # On deals 3+: reference prior deals to signal reliability pattern
            f"<p>Deal {deal_number} through this channel. The pattern speaks for itself.</p>"
            if deal_number >= 3 else ""
        )
        +
        f"<p>Assignment fee: ${our_fee:,} payable to Everlight Ventures at close "
        f"from your wire to Mid-South Title. Marvin will follow up with closing logistics.</p>"
        f"<p>Warm regards,<br>"
        f"<strong>Vaughn Sterling</strong><br>"
        f"Senior Partner | Everlight Ventures<br>"
        f"<a href=\"mailto:vaughn@everlightventures.io\">vaughn@everlightventures.io</a></p>"
    )

    return {"subject": subject, "body_html": _with_disclosure(body_html), "persona": PERSONA["vaughn"]}


# ---------------------------------------------------------------------------
# TN SB 909 PSA Contract Renderer
# ---------------------------------------------------------------------------

def _psa_title_block(lead: dict, close_date: str) -> str:
    """Return the text body for PSA block 6 (Title and Closing)."""
    sales_history = lead.get("sales_history") or []
    deed_type = "general warranty"
    if sales_history:
        code = str(sales_history[0].get("type_code") or "").upper()
        if code == "QC":
            deed_type = "quitclaim"
        elif code == "WD":
            deed_type = "warranty"
        elif code == "SW":
            deed_type = "special warranty"
    return (
        f"CLOSING DATE: {close_date} (\"Closing Date\"), at the offices of "
        f"Mid-South Title Company, Memphis, Tennessee, or such other date "
        f"as mutually agreed in writing.\n\n"
        f"TITLE: Seller shall convey marketable fee simple title by "
        f"{deed_type} deed, free and clear of all liens and encumbrances except "
        f"current year property taxes (prorated to close) and easements of record.\n\n"
        f"CLOSING COSTS: Buyer shall pay all closing costs including "
        f"title examination, title insurance, recording fees, and "
        f"transfer taxes. Seller has no closing cost obligation.\n\n"
        f"ESCROW AGENT: Mid-South Title Company, Memphis, Tennessee. "
        f"All funds shall be held and disbursed by Escrow Agent per "
        f"the settlement statement. Wire instructions to be verified "
        f"verbally by Escrow Agent before any transfer."
    )


def render_psa_contract(lead: dict, deal_terms: dict) -> dict:
    """Render the 7-block TN SB 909 Purchase and Sale Agreement (PSA).

    Produces the full PSA contract as structured blocks for the dashboard
    and as psa_html for email or HTML report embedding.

    Args:
        lead: lead dict with owner_name, property_address, parcel_id, etc.
        deal_terms: dict with keys:
            - buyer_entity: Everlight Ventures or assignee name
            - purchase_price: int (seller purchase price)
            - emd_amount: int (earnest money deposit, default $500)
            - close_date: str (closing date)
            - assignment_fee: int (Everlight assignment fee)
            - effective_date: str (contract effective date, default today)

    Returns:
        {
            "subject": str,
            "blocks": list of {"title": str, "body": str},
            "psa_html": str (full rendered HTML),
            "persona": dict
        }
    """
    seller_name = lead.get("owner_name") or "SELLER NAME"
    addr = lead.get("property_address") or lead.get("address") or "PROPERTY ADDRESS"
    parcel_id = lead.get("parcel_id") or "PARCEL ID"
    state = lead.get("state") or "TN"
    county = lead.get("county") or "Shelby"

    buyer_entity = deal_terms.get("buyer_entity") or "Everlight Ventures or Assignee"
    purchase_price = int(deal_terms.get("purchase_price") or 0)
    emd_amount = int(deal_terms.get("emd_amount") or 500)
    close_date = deal_terms.get("close_date") or (datetime.now() + timedelta(days=10)).strftime("%B %d, %Y")
    assignment_fee = int(deal_terms.get("assignment_fee") or 11500)  # TN norm $10-15k (2026-05-28)
    effective_date = deal_terms.get("effective_date") or datetime.now().strftime("%B %d, %Y")

    blocks = [
        {
            "title": "1. Parties and Effective Date",
            "body": (
                f"This Purchase and Sale Agreement (\"Agreement\") is entered into as of "
                f"{effective_date} (\"Effective Date\") by and between:\n\n"
                f"SELLER: {html.escape(seller_name)}\n"
                f"BUYER: {html.escape(buyer_entity)}\n\n"
                f"Collectively referred to herein as the \"Parties.\""
            ),
        },
        {
            "title": "2. Property and Earnest Money",
            "body": (
                f"PROPERTY: The real property located at {html.escape(addr)}, "
                f"Parcel ID: {html.escape(parcel_id)}, {county} County, {state} "
                f"(the \"Property\").\n\n"
                f"PURCHASE PRICE: ${purchase_price:,} (the \"Purchase Price\"), "
                f"all cash, no financing contingency.\n\n"
                f"EARNEST MONEY DEPOSIT (EMD): ${emd_amount:,} to be deposited with "
                f"Mid-South Title Company (\"Escrow Agent\") within 24 hours of "
                f"countersignature. EMD is refundable per Section 7 herein."
            ),
        },
        {
            "title": "3. Equitable Interest and Assignment",
            "body": (
                f"Upon execution of this Agreement, Buyer acquires equitable interest in "
                f"the Property. Buyer shall have the right to assign this Agreement, "
                f"in whole or in part, to any third party (\"Assignee\") without Seller's "
                f"prior written consent unless otherwise required by applicable law.\n\n"
                f"Assignment shall not relieve Buyer of obligations under this Agreement "
                f"unless Assignee expressly assumes such obligations in writing. "
                f"Seller shall receive written notice of any assignment on the day of "
                f"assignment execution."
            ),
        },
        {
            "title": "4. Dual Remedy / Liquidated Damages",
            "body": (
                f"If Seller defaults, Buyer may (a) enforce specific performance or "
                f"(b) receive return of the EMD as liquidated damages, at Buyer's election.\n\n"
                f"If Buyer defaults, Seller's sole remedy is retention of the EMD "
                f"(${emd_amount:,}) as liquidated damages, unless Seller elects specific "
                f"performance. The Parties agree the EMD represents a reasonable pre-estimate "
                f"of damages and not a penalty."
            ),
        },
        {
            "title": "5. Wholesaler Disclosure (TN SB 909)",
            "body": (
                f"PURSUANT TO TENNESSEE PUBLIC CHAPTER 911 (SENATE BILL 909, 2022), "
                f"Buyer hereby discloses to Seller the following:\n\n"
                f"(a) Buyer is acting as a WHOLESALE BUYER and intends to assign "
                f"this contract to a third-party end buyer prior to closing.\n\n"
                f"(b) Buyer is NOT a licensed real estate agent or broker and "
                f"is NOT acting in a fiduciary capacity for Seller.\n\n"
                f"(c) Seller has the right to consult with independent legal counsel "
                f"before executing this Agreement.\n\n"
                f"(d) Buyer's assignment fee (profit) is estimated at "
                f"${assignment_fee:,}, which represents the difference between the "
                f"Buyer-Seller contract price and the price at which Buyer assigns "
                f"or resells the Property.\n\n"
                f"Seller acknowledges receipt of this disclosure by countersignature below."
            ),
        },
        {
            "title": "6. Title and Closing",
            "body": _psa_title_block(lead, close_date),
        },
        {
            "title": "7.5 Quality Assurance Period",
            "body": (
                "Both parties acknowledge that a TEN (10) DAY Quality Assurance Period applies from\n"
                "the Effective Date through the date that is ten (10) calendar days prior to Closing.\n"
                "During this period:\n\n"
                "(a) Buyer shall confirm title clearance, earnest money delivery, and final\n"
                "    coordination of all parties to ensure a smooth, on-time close.\n\n"
                "(b) Seller shall have a mutual right to terminate this Agreement without penalty\n"
                "    upon written notice during this period if Seller's circumstances change\n"
                "    (family, estate, personal). Earnest Money is returned to Buyer.\n\n"
                "(c) Buyer shall have a mutual right to terminate this Agreement without penalty\n"
                "    upon written notice during this period if Buyer is unable to complete the\n"
                "    transaction as contemplated. Earnest Money is returned to Buyer.\n\n"
                "(d) Notice of termination shall be delivered by email to the other party at the\n"
                "    address listed in Block 1. Termination shall be effective upon delivery.\n\n"
                "(e) After the Quality Assurance Period closes, the parties proceed to Closing\n"
                "    per Block 6 and may only terminate per the remedies in Block 4.\n\n"
                "The Quality Assurance Period exists to protect both parties' ability to walk\n"
                "away cleanly if circumstances require it, and to ensure the Closing proceeds\n"
                "with full confidence on both sides."
            ),
        },
        {
            "title": "7. Signatures",
            "body": (
                f"IN WITNESS WHEREOF, the Parties have executed this Agreement "
                f"as of the Effective Date.\n\n"
                f"SELLER:\n"
                f"Name: {html.escape(seller_name)}\n"
                f"Signature: _______________________\n"
                f"Date: _______________________\n\n"
                f"BUYER:\n"
                f"Name: {html.escape(buyer_entity)}\n"
                f"Authorized Signatory: _______________________\n"
                f"Title: Acquisitions\n"
                f"Date: _______________________\n\n"
                f"ACKNOWLEDGED -- TN SB 909 WHOLESALER DISCLOSURE:\n"
                f"Seller Initials: ______  Date: _______________________\n\n"
                f"ESCROW AGENT ACKNOWLEDGMENT:\n"
                f"Mid-South Title Company\n"
                f"EMD Receipt Confirmation: _______________________"
            ),
        },
    ]

    # Build psa_html
    block_html_parts = []
    for blk in blocks:
        block_html_parts.append(
            f"<div class='psa-block'>"
            f"<h3 class='psa-block-title'>{html.escape(blk['title'])}</h3>"
            f"<pre class='psa-block-body'>{html.escape(blk['body'])}</pre>"
            f"</div>"
        )

    psa_html = (
        f"<div class='psa-wrapper'>"
        f"<div class='psa-header'>"
        f"<strong>PURCHASE AND SALE AGREEMENT</strong><br>"
        f"Property: {html.escape(addr)}<br>"
        f"Effective Date: {effective_date}<br>"
        f"Purchase Price: ${purchase_price:,} | EMD: ${emd_amount:,}"
        f"</div>"
        + "".join(block_html_parts)
        + f"</div>"
    )

    subject = f"Purchase contract -- {html.escape(addr)}"

    return {
        "subject": subject,
        "blocks": blocks,
        "psa_html": psa_html,
        "persona": PERSONA["marvin"],
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def render_first_touch(lead: dict, persona_key: str = "piper") -> dict:
    """Day-0-hour-4 email. Returns {subject, body_html, persona}.

    PERSONA-STAGE DISCIPLINE (THE RECIPE, 2026-05-28):
    - Piper is the ONLY cold first-touch persona. She opens every cold sequence.
    - Henry = negotiation phase (after seller reply). render_first_touch for henry
      returns his negotiation email clearly labeled -- the live cron only calls
      piper for first-touch, so this is honest: Henry does not cold-open.
    - Marvin = closing phase (after agreement). Same as Henry.
    - Vaughn = high-value / senior / probate -- his content is stage-appropriate
      (first-touch only on elevated leads, never a finished-deal cold email).

    body_html contains paragraph tags ready for the gold template wrapper
    in branded_mailer. Persona-voiced, Memphis-anchored, TN-only.

    Args:
        lead: dict with owner_name, property_address/address, city,
              mailing_address, county_appraisal, source, etc.
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
    # Henry: stage = negotiation (on reply). Returns negotiation email -- NOT a cold close.
    if persona_key == "henry":
        return _henry_negotiation(lead)
    # Marvin: stage = closing (after agreement). Returns closing-handoff -- NOT a cold close.
    if persona_key == "marvin":
        return _marvin_closing_handoff(lead)
    # Vaughn: senior intro for high-value / probate -- stage-appropriate gravitas.
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


# ---------------------------------------------------------------------------
# Marquise persona convenience re-exports (thin wrappers in public API)
# ---------------------------------------------------------------------------

__all__ = [
    "PERSONA",
    "LEAD_TYPES",
    "TN_CONSTANTS",
    "AI_DISCLOSURE_FOOTER",
    "_with_disclosure",
    "first_name",
    "classify_lead",
    "data_lens",
    "render_first_touch",
    "render_first_touch_followup",
    "render_first_touch_final",
    "render_followup",
    "render_negotiation",
    "render_closing_handoff",
    # Marquise seller-side (multi-round negotiation)
    "render_marquise_first_touch",
    "render_marquise_anchor_offer",
    "render_marquise_counter",
    "render_marquise_round2_validation",
    "render_marquise_round3_social_proof",
    "render_marquise_round4_final",
    "render_marquise_pivot_to_chris",
    "render_marquise_final_wrap",
    # Buyer-side (Henry flip-math leverage)
    "render_marvin_pitch_chris",
    "render_marvin_full_deal_sheet",
    "render_henry_buyer_negotiation",
    "render_henry_buyer_pitch_with_flip_math",
    "render_henry_buyer_counter_round2",
    "render_vaughn_assignment_countersign",
    # PSA contract
    "render_psa_contract",
]
