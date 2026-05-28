"""agent_outreach_templates -- shared outreach copy, boomerang / reverse-magnet framing.

Every agent (Piper, Harrison, Cupid, Justine) shares one source of truth for
touch sequences. Each sequence is a list of (template_fn, days_after_prev).
Templates return (subject, body_text, body_html).

Boomerang method (2026 upgrade):
  - touch 1: "Should I build you <magnet_name> for <specific context>?"
  - touch 2: "Here you go -> <magnet_url>" (only if they said yes)
  - touches 3-7: friendly nudges referencing the deliverable

The magnet URL is a per-lead, pre-filled link to a micro-app (e.g.
cashofferscan.everlightventures.io/?lead_id=X) that delivers value in <60s.

Agent personas each write in their voice -- see AGENTS registry.

All copy ends in a Slack mention of the magnet when the lead replies yes,
so the receiving human (Piper in Nashville, Harrison in deal-ops) can jump in.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal, Optional


# ---------------------------------------------------------------------------
# Agent personas -- sender identity and voice cues.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AgentPersona:
    id: str
    display_name: str
    from_email: str
    title: str
    phone: str
    voice: str          # cue for template authors


AGENTS: dict[str, AgentPersona] = {
    "piper": AgentPersona(
        id="piper",
        display_name="Piper Reeves",
        from_email="piper@everlightventures.io",
        title="Senior Account Executive, Wholesale",
        phone="(707) 801-0360",
        voice="warm, Nashville, y'all, first-name, never pushy, refers to owner's house like a real place",
    ),
    "harrison": AgentPersona(
        id="harrison",
        display_name="Harrison Knox",
        from_email="hammer@everlightventures.io",
        title="Director, Deal Operations",
        phone="(888) 896-6772",
        voice="sharp, direct, numbers-first, opens with the math, earns trust with specificity",
    ),
    "cupid": AgentPersona(
        id="cupid",
        display_name="Cupid Morales",
        from_email="cupid@everlightventures.io",
        title="Broker OS -- Buyer Matching",
        phone="(888) 896-6772",
        voice="enthusiast, opener-style, fast and confident, SaaS-to-SaaS tone",
    ),
    "justine": AgentPersona(
        id="justine",
        display_name="Justine Park",
        from_email="justine@everlightventures.io",
        title="Compliance Officer",
        phone="(888) 896-6772",
        voice="careful, short, disclosure-forward, only sends when a legal step is required",
    ),
}


# ---------------------------------------------------------------------------
# Magnet registry -- each vertical has one micro-SaaS deliverable.
# ---------------------------------------------------------------------------

MAGNETS: dict[str, dict] = {
    "wholesale_seller": {
        "name": "CashOfferScan",
        "base_url": "https://everlightventures.io/cashoffer",
        "describe_ask": "a custom cash-offer breakdown for {{address}}",
        "describe_deliver": "a live breakdown of {{address}} -- ARV, current equity, and the offer range we'd actually pay",
        "agent_default": "piper",
        "vertical": "wholesale_seller",
    },
    "wholesale_buyer": {
        "name": "DealPreviewPack",
        "base_url": "https://everlightventures.io/dealpreview",
        "describe_ask": "a pre-vetted 5-property preview in your buy-box ({{market}}, {{price_band}})",
        "describe_deliver": "5 pre-screened properties in {{market}} with ARV, repair estimate, and cap rate already filled",
        "agent_default": "harrison",
        "vertical": "wholesale_buyer",
    },
    "broker_saas": {
        "name": "BuyerMatchPreview",
        "base_url": "https://everlightventures.io/buyermatch",
        "describe_ask": "3 qualified acquirers for {{company}} with the messaging angles already drafted",
        "describe_deliver": "3 acquirer leads for {{company}} and drafted outreach you can send tonight",
        "agent_default": "cupid",
        "vertical": "broker_saas",
    },
    "consulting_ai": {
        "name": "StackScanner",
        "base_url": "https://everlightventures.io/stackscan",
        "describe_ask": "a custom automation stack for your {{detected_stack}} setup",
        "describe_deliver": "3 importable automations for your {{detected_stack}} -- one-click install",
        "agent_default": "harrison",
        "vertical": "consulting_ai",
    },
    "title_company": {
        "name": "ClosingChecklistPreview",
        "base_url": "https://everlightventures.io/closingprep",
        "describe_ask": "a closing-ready checklist for {{address}}",
        "describe_deliver": "the full closing checklist + title docs for {{address}} ready to pull",
        "agent_default": "harrison",
        "vertical": "title_company",
    },
}


# ---------------------------------------------------------------------------
# Touch sequence -- 7 touches over 5 days (the Belfort cadence).
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Touch:
    step: int
    hours_after_prev: int
    channel: Literal["email", "sms", "call"]
    template_id: str


SEQUENCE: list[Touch] = [
    Touch(0, 0,    "email", "ask_v1"),          # day 1 -- boomerang ask
    Touch(1, 18,   "email", "nudge_v1"),        # day 2 -- "hey, still good?"
    Touch(2, 22,   "email", "angle_market"),    # day 3 -- different angle
    Touch(3, 20,   "sms",   "sms_short"),       # day 3/4 -- SMS (where allowed)
    Touch(4, 22,   "email", "angle_timeline"),  # day 4 -- urgency
    Touch(5, 20,   "email", "angle_proof"),     # day 5 -- social proof
    Touch(6, 20,   "email", "breakup"),         # day 5/6 -- graceful last ask
]


# ---------------------------------------------------------------------------
# Helpers -- fill-in + render.
# ---------------------------------------------------------------------------

def _fill(template: str, ctx: dict) -> str:
    """Tiny mustache-like renderer so we don't pull in jinja for 6 variables."""
    out = template
    for k, v in ctx.items():
        out = out.replace("{{" + k + "}}", str(v or ""))
    return out


def _magnet_for(vertical: str, lead: dict) -> dict:
    m = MAGNETS.get(vertical)
    if not m:
        raise KeyError(f"no magnet registered for vertical {vertical!r}")
    m2 = dict(m)
    lead_id = str(lead.get("id") or lead.get("lead_id") or "")
    m2["url"] = f"{m['base_url']}/?lead_id={lead_id}"
    return m2


# ---------------------------------------------------------------------------
# Template library -- seller-facing (Piper's book)
# ---------------------------------------------------------------------------

def _seller_ask(lead: dict, persona: AgentPersona, magnet: dict) -> tuple[str, str, str]:
    first = (lead.get("owner_name") or "").split(",")[0].split(" ")[0].title() or "there"
    ctx = {
        "first": first,
        "address": lead.get("address", ""),
        "city": lead.get("city", ""),
        "state": lead.get("state", ""),
    }
    subject = f"Should I build this for {ctx['address']}?"
    body = _fill(
        "Hey {{first}},\n\n"
        "I spent some time on your place at {{address}} in {{city}} and I can put together "
        "a real cash-offer breakdown -- ARV, current equity, repair estimate, and the exact number "
        "we'd pay.\n\n"
        "Want me to send the link? Just reply YES and I'll kick it over.\n\n"
        "-- Piper\n"
        "Everlight Ventures, Wholesale\n"
        "{{phone_line}}",
        {**ctx, "phone_line": persona.phone},
    )
    return subject, body, ""  # plain text; HTML wrapping handled by branded_mailer


def _seller_deliver(lead: dict, persona: AgentPersona, magnet: dict) -> tuple[str, str, str]:
    first = (lead.get("owner_name") or "").split(",")[0].split(" ")[0].title() or "there"
    ctx = {
        "first": first,
        "address": lead.get("address", ""),
        "magnet_url": magnet["url"],
        "phone": persona.phone,
    }
    subject = f"Your cash-offer breakdown for {ctx['address']}"
    body = _fill(
        "Hey {{first}} -- here's the page I put together for {{address}}:\n\n"
        "{{magnet_url}}\n\n"
        "It has the offer range, the comps I used, and the expected net-to-you after closing "
        "costs. If the number looks close, I can have a contract ready the same day.\n\n"
        "Happy to jump on a quick call to walk you through it: {{phone}}\n\n"
        "-- Piper",
        ctx,
    )
    return subject, body, ""


def _seller_nudge(lead: dict, persona: AgentPersona, magnet: dict) -> tuple[str, str, str]:
    first = (lead.get("owner_name") or "").split(",")[0].split(" ")[0].title() or "there"
    ctx = {"first": first, "address": lead.get("address", ""), "magnet_url": magnet["url"]}
    subject = f"Saw you haven't opened the offer yet"
    body = _fill(
        "Hey {{first}} -- wanted to make sure this didn't get buried.\n\n"
        "The breakdown for {{address}} is still live here: {{magnet_url}}\n\n"
        "If the timing isn't right, no worries at all. Just say the word and I'll leave "
        "you alone.\n\n"
        "-- Piper",
        ctx,
    )
    return subject, body, ""


def _seller_market_angle(lead: dict, persona: AgentPersona, magnet: dict) -> tuple[str, str, str]:
    first = (lead.get("owner_name") or "").split(",")[0].split(" ")[0].title() or "there"
    ctx = {
        "first": first, "city": lead.get("city", ""),
        "address": lead.get("address", ""), "magnet_url": magnet["url"],
    }
    subject = f"{ctx['city']} market moved -- want me to re-run the number?"
    body = _fill(
        "Hey {{first}} -- comps in {{city}} shifted this week. I can refresh the offer "
        "breakdown for {{address}} with the latest numbers if that's helpful.\n\n"
        "Updated version lives here: {{magnet_url}}\n\n"
        "-- Piper",
        ctx,
    )
    return subject, body, ""


def _seller_breakup(lead: dict, persona: AgentPersona, magnet: dict) -> tuple[str, str, str]:
    first = (lead.get("owner_name") or "").split(",")[0].split(" ")[0].title() or "there"
    ctx = {"first": first, "address": lead.get("address", "")}
    subject = f"Last one, promise"
    body = _fill(
        "Hey {{first}} -- I'll stop reaching out after this. If {{address}} is off "
        "the table, totally fine.\n\n"
        "If anything changes -- maybe in 6 months, maybe next year -- my number is in "
        "my signature. No pressure. Good luck out there.\n\n"
        "-- Piper",
        ctx,
    )
    return subject, body, ""


def _seller_sms_short(lead: dict, persona: AgentPersona, magnet: dict) -> tuple[str, str, str]:
    # SMS is subject='', body=short text (<=160 with STOP)
    subject = ""
    body = (
        f"Hi, this is Piper w/ Everlight. I put together a cash-offer "
        f"for your place at {lead.get('address','')}. Want the link? "
        f"Reply Y. Reply STOP to opt out."
    )
    return subject, body, ""


# ---------------------------------------------------------------------------
# Template library -- buyer-facing (Harrison's book)
# ---------------------------------------------------------------------------

def _buyer_ask(lead: dict, persona: AgentPersona, magnet: dict) -> tuple[str, str, str]:
    first = (lead.get("owner_name") or "").split(",")[0].split(" ")[0].title() or "there"
    ctx = {
        "first": first,
        "market": lead.get("buy_box_market") or lead.get("city", "your market"),
        "price_band": lead.get("buy_box_price_band", "$80k-300k"),
    }
    subject = f"5 pre-vetted deals in {ctx['market']} -- want me to send?"
    body = _fill(
        "Hey {{first}},\n\n"
        "I pulled 5 properties that match your buy-box in {{market}} "
        "({{price_band}}). Each one comes with ARV, repair estimate, and cap rate "
        "already filled in.\n\n"
        "Want me to send the link? Reply YES and I'll kick it over.\n\n"
        "-- Harrison\n"
        "Everlight, Deal Ops",
        ctx,
    )
    return subject, body, ""


def _buyer_deliver(lead: dict, persona: AgentPersona, magnet: dict) -> tuple[str, str, str]:
    subject = "Your deal preview -- 5 properties ready to review"
    body = (
        f"Here's the preview: {magnet['url']}\n\n"
        "All 5 have ARV + repair est + projected cap rate pre-loaded. "
        "If two or three look interesting, I can have the full disposition "
        "packs over within the hour.\n\n"
        "-- Harrison"
    )
    return subject, body, ""


# ---------------------------------------------------------------------------
# Dispatch -- single entry point.
# ---------------------------------------------------------------------------

TEMPLATE_LIBRARY: dict[tuple[str, str], Callable] = {
    # (vertical, template_id) -> function
    ("wholesale_seller", "ask_v1"):        _seller_ask,
    ("wholesale_seller", "nudge_v1"):      _seller_nudge,
    ("wholesale_seller", "angle_market"):  _seller_market_angle,
    ("wholesale_seller", "sms_short"):     _seller_sms_short,
    ("wholesale_seller", "angle_timeline"):_seller_nudge,   # alias for now
    ("wholesale_seller", "angle_proof"):   _seller_nudge,   # alias for now
    ("wholesale_seller", "breakup"):       _seller_breakup,
    # boomerang deliver (touch after YES reply)
    ("wholesale_seller", "deliver"):       _seller_deliver,

    ("wholesale_buyer",  "ask_v1"):        _buyer_ask,
    ("wholesale_buyer",  "deliver"):       _buyer_deliver,
}


def render(vertical: str, template_id: str, lead: dict,
           agent_id: Optional[str] = None) -> tuple[str, str, str, AgentPersona, dict]:
    """Render a touch for (vertical, template_id) using `lead` context.

    Returns: (subject, body_text, body_html, agent_persona, magnet_info)
    """
    magnet = _magnet_for(vertical, lead)
    agent = AGENTS[(agent_id or magnet["agent_default"])]
    fn = TEMPLATE_LIBRARY.get((vertical, template_id))
    if not fn:
        raise KeyError(f"no template for {vertical}/{template_id}")
    subject, body_text, body_html = fn(lead, agent, magnet)
    return subject, body_text, body_html, agent, magnet


__all__ = [
    "AgentPersona", "AGENTS", "MAGNETS", "SEQUENCE",
    "render", "TEMPLATE_LIBRARY",
]
