"""
pitch_hooks -- generate wholesale-pitch hook lines from a personality profile.

Takes the output of personality_synth.synthesize_personality() and emits 3-7
specific opening lines the operator can paste into Piper's outreach. Each
hook cites the SOURCE (which finding produced this hook) so the operator
can verify before using.

The vibe: if Google can target ads from your interests, we can target a
wholesale pitch from public-record interests + life events. Same data model,
narrower output (one pitch instead of thousand-impression campaign).

Per Operator Truth: never invent a hook without a citation. If we have no
signals, we say "no pitch hooks available -- use generic foreclosure-relief
opener and verify owner directly."
"""
from __future__ import annotations


# Hook templates per interest category. {target_first_name} interpolated by caller.
HOOK_TEMPLATES = {
    "Cars / Vehicles": [
        "{first}, saw your {keyword} interest -- happens the property has an oversized garage. Worth a quick call?",
        "Hey {first}, noticed you're into {keyword}. We've got a deal where the new owner is keeping the workshop -- pass it along?",
    ],
    "Sports & Fitness": [
        "{first}, fellow {keyword} person here. Quick question about the property -- 60-second call work?",
    ],
    "Faith / Community": [
        "{first}, I serve in my community too. Wanted to reach out personally about your property -- ok if I call this week?",
    ],
    "Family / Parenting": [
        "{first}, I know managing family + property is a lot. We make this part simple. Worth 60 seconds?",
    ],
    "Entrepreneurship": [
        "{first}, fellow operator -- I'll be direct: cash offer on the property, close on your timeline. Worth a call?",
        "{first}, as a {keyword} you'll appreciate this is operator-to-operator. Quick offer ready when you are.",
    ],
    "Tech / Engineering": [
        "{first}, you'll like this -- everything in writing, no realtor games, no listing chaos. Want the numbers?",
    ],
    "Art / Music": [
        "{first}, saw your creative side. I'll keep this offer creative-friendly -- no listings, no showings, no chaos. Worth talking?",
    ],
    "Food / Travel": [
        "{first}, I'll keep this short so you can get back to enjoying life. Cash offer, your timeline. Worth 30 seconds?",
    ],
    "Causes / Politics": [
        "{first}, saw your civic side. I'll be straightforward: cash offer, your terms, no listing circus. Open to a call?",
    ],
    "Pets / Animals": [
        "{first}, I noticed you're a fellow {keyword} person. We'll structure the move easy for you and the family. Worth 60 seconds?",
    ],
    "Real Estate": [
        "{first}, as someone who clearly knows real estate -- I'll skip the small talk. Net offer on the property, close on your timeline. Email or call?",
    ],
    # === NEW CATEGORIES ===
    "Foodie / Restaurants": [
        "{first}, fellow {keyword} person. I'll keep this short so you can get back to dinner. Cash offer on the property, your timeline -- 60 seconds?",
    ],
    "Diet / Lifestyle": [
        "{first}, saw the {keyword} life. We work with folks who keep things simple -- one call, cash offer, no listing chaos. Worth a quick reply?",
    ],
    "Drinks / Beverage": [
        "{first}, fellow {keyword} fan. Quick property question -- 60-second call this week?",
    ],
    "Travel / Adventure": [
        "{first}, see you're a {keyword} type. If the property is anchoring you down, we close fast and cash so you can keep moving. Worth a call?",
    ],
    "Recovery / Sobriety": [
        "{first}, I work with folks navigating life transitions. Property sale doesn't need to add stress -- one call, cash, your timeline. Open to talk when you're ready?",
    ],
    "Medical / Patient": [
        "{first}, I help families navigating health journeys -- selling property shouldn't add weight. Cash offer, your timeline. When you're ready, we're here.",
    ],
    "Gaming": [
        "{first}, fellow gamer. I'll keep this concise: cash offer on the property, close in 10-21 days, no agents. Want the numbers?",
    ],
    "Reading / Books": [
        "{first}, I respect a fellow {keyword}. Quick property note -- cash offer, your timeline, no listing chaos. Worth 60 seconds?",
    ],
    "Film / TV": [
        "{first}, I see the {keyword} interest. Real-life version: we cut the chaos, cash offer, close on your timeline. Want details?",
    ],
    "Crafts / DIY": [
        "{first}, fellow {keyword} -- saw the work, beautiful stuff. Quick on the property: cash offer, your timeline, no listing. Open to a call?",
    ],
    "Hunting / Fishing": [
        "{first}, fellow {keyword}. I'll be direct: cash offer on the property, close on your terms, no agents. Want the numbers?",
    ],
    "Gardening": [
        "{first}, the {keyword} setup looks incredible. We work with folks who care about their land -- next buyer can keep or repurpose. Cash offer, your timeline. Worth a call?",
    ],
    "Luxury / Fashion": [
        "{first}, I'll match your standards -- premium offer, white-glove closing, no listing/showings/chaos. Open to a call?",
    ],
    "Frugal / Budget": [
        "{first}, fellow {keyword}-minded -- no commissions, no listing fees, no surprises. Cash offer on the property. Worth a 60-second call?",
    ],
    "Higher Education": [
        "{first}, given your background you'll appreciate the structure: everything in writing, due diligence done, cash offer, close on your timeline. Open to numbers?",
    ],
    "Veteran / Military": [
        "{first}, thank you for your service. I work with veterans on simple property sales -- one call, cash, your timeline. Worth talking?",
    ],
    "Causes / Politics": [
        "{first}, saw your civic side. I'll be straightforward: cash offer, your terms, no listing circus. Open to a call?",
    ],
    "Politics / Left": [
        "{first}, quick property note. We're an Everlight-based wholesaler -- cash offer, your timeline, no chaos. Worth a brief call?",
    ],
    "Politics / Right": [
        "{first}, quick property note. We're an Everlight-based wholesaler -- cash offer, your timeline, no chaos. Worth a brief call?",
    ],
}

# Life-event-driven hooks (take priority -- highest emotional resonance)
LIFE_EVENT_HOOKS = {
    "recently_divorced": "{first}, I work with a lot of folks navigating a life transition. We make the property part simple -- cash offer, your timeline, no agents. Worth a quick call?",
    "recently_widowed":  "{first}, very sorry for your loss. When you're ready, we make selling the property the easy part -- one call, cash offer, your timeline. No pressure on timing.",
    "recent_retirement": "{first}, congratulations on retirement. We work with retirees often -- cash offer on the property, simple paperwork, close when you're ready.",
    "recent_move":       "{first}, saw you've made a move recently. We close on properties left behind in 10-21 days, cash, no agents. Worth a call?",
    "recent_job_change": "{first}, I work with folks managing a transition. The property doesn't need to be a stressor -- one call, cash offer, your timeline.",
    "foreclosure":       "{first}, this is sensitive -- I work with homeowners facing foreclosure to find an exit before auction. No realtor, no listing. Want me to walk you through options?",
    "bankruptcy":        "{first}, I work with families post-bankruptcy on selling property quickly with cash. No agents, no commission. Worth a confidential call?",
    "recent_death_in_family": "{first}, I'm sorry for your loss. When you're ready to talk about the property, we make it simple -- one call, cash, your timeline.",
}

# Financial-signal hooks
FINANCIAL_HOOKS = {
    "multi_property_signal": "{first}, as a multi-property owner you know the drill -- straightforward cash offer, close on your timeline, no listing or commission. Open to numbers?",
    "distress_signal":       "{first}, I work with property owners navigating financial pressure -- discreet, fast, cash. Confidential 15-minute call this week?",
}

# Generic fallback (always last)
GENERIC_HOOKS = [
    "{first}, quick note about your property -- we make cash offers, close in 10-21 days, no agents, no commissions. Worth a 60-second call?",
    "{first}, this is {agent} from Everlight. We work with property owners in {state_name} on cash-offer sales. Open to a brief call?",
]


def _first_name(name: str) -> str:
    if not name: return "there"
    parts = name.replace(",", " ").split()
    if not parts: return "there"
    # Handle "LAST, FIRST" pattern
    if "," in name and len(parts) >= 2:
        return parts[1].title()
    return parts[0].title()


def generate_hooks(personality: dict, lead_context: dict | None = None,
                   max_hooks: int = 5) -> list[dict]:
    """
    Returns a list of hook objects:
        {
          "hook": "...",
          "rationale": "matched because: ...",
          "category": "life_event" | "interest" | "financial" | "generic",
          "tag": "recently_divorced" / "Cars / Vehicles" / etc.,
          "source": investigator that produced the signal,
          "source_url": "...",
          "priority": int (lower = run first),
        }
    """
    if not isinstance(personality, dict):
        personality = {}
    if not isinstance(lead_context, dict):
        lead_context = {}

    first = _first_name(lead_context.get("owner_name", "") or
                         lead_context.get("target", ""))
    state = (lead_context.get("state", "") or "").upper()
    state_name = {
        "CA": "California", "TX": "Texas", "FL": "Florida", "NY": "New York",
        "MO": "Missouri", "GA": "Georgia", "OH": "Ohio", "TN": "Tennessee",
        "NC": "North Carolina", "AZ": "Arizona", "IL": "Illinois",
    }.get(state, state or "your area")

    hooks: list[dict] = []

    # Life-event hooks first -- highest priority
    for tag, evs in (personality.get("life_events") or {}).items():
        if tag not in LIFE_EVENT_HOOKS: continue
        tpl = LIFE_EVENT_HOOKS[tag]
        for ev in evs[:1]:
            hooks.append({
                "hook": tpl.format(first=first),
                "rationale": f"matched life event '{tag.replace('_',' ')}' from {ev['source']} -- '{ev['snippet'][:80]}...'",
                "category": "life_event",
                "tag": tag,
                "source": ev["source"],
                "source_url": ev.get("source_url", ""),
                "priority": 1,
            })

    # Financial hooks next
    for fin in personality.get("financial_signals", [])[:2]:
        kind = fin.get("kind", "")
        if kind not in FINANCIAL_HOOKS: continue
        hooks.append({
            "hook": FINANCIAL_HOOKS[kind].format(first=first),
            "rationale": f"matched financial signal '{kind}' from {fin['source']} -- '{fin['snippet'][:80]}'",
            "category": "financial",
            "tag": kind,
            "source": fin["source"],
            "source_url": fin.get("url", ""),
            "priority": 2,
        })

    # Interest hooks
    for cat, hits in (personality.get("interests") or {}).items():
        if cat not in HOOK_TEMPLATES: continue
        templates = HOOK_TEMPLATES[cat]
        top = hits[0] if hits else {}
        kw = top.get("keyword", "").lower()
        hooks.append({
            "hook": templates[0].format(first=first, keyword=kw),
            "rationale": f"matched interest '{cat}' (keyword '{kw}') from {top.get('source','?')}",
            "category": "interest",
            "tag": cat,
            "source": top.get("source", ""),
            "source_url": top.get("source_url", ""),
            "priority": 3,
        })

    # Always include one generic as fallback (priority lowest)
    hooks.append({
        "hook": GENERIC_HOOKS[0].format(first=first),
        "rationale": "fallback hook -- always available even when no personality signals",
        "category": "generic",
        "tag": "generic",
        "source": "fallback",
        "source_url": "",
        "priority": 9,
    })

    hooks.sort(key=lambda h: h["priority"])
    return hooks[:max_hooks]
