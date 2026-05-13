"""
marketing_pipeline -- the 5-stage processor that turns raw OSINT into a pitch package.

Old model: personality_synth -> pitch_hooks -> one-liner. Feels like surveillance.

New model: 5 stages, each builds on the last:

  1. PROFILE          (what we know about them)            -- from personality_synth
  2. RESONANCE        (what language/values RESONATE)      -- value-tag inference
  3. MARKET STRATEGY  (positioning angle for the property) -- niche / motivation match
  4. NARRATIVE        (the actual pitch story)             -- multi-touchpoint, implicit
  5. ROUTING          (which closer agent handles it)      -- state-specific assignment

The output is a "pitch package" -- a multi-channel, multi-touchpoint narrative
sequence ready for the state-specific closer to send. Not a one-liner.

Critical doctrine (per operator feedback 2026-05-12):
  - NEVER explicitly reference the source signal ("I saw you on Strava")
  - INSTEAD, ASSOCIATE Everlight with the value/imagery that resonates
  - The pitch should feel like it could be addressed to ANYONE in their tribe,
    so it lands as recognition rather than surveillance
"""
from __future__ import annotations

import re
from typing import Any


# ============== STAGE 2: RESONANCE -- map interests/events to VALUES ==============
# These are the values that, when invoked, RESONATE with the detected personality.
# We never say "I saw you do X." We just speak in language that matches the
# value-set of someone whose findings matched X.
INTEREST_TO_VALUES = {
    # Identity values per interest cluster
    "Cars / Vehicles":        ["craftsmanship", "freedom", "legacy"],
    "Sports & Fitness":       ["discipline", "consistency", "results"],
    "Faith / Community":      ["integrity", "service", "stewardship"],
    "Family / Parenting":     ["security", "stability", "protection"],
    "Entrepreneurship":       ["operator-to-operator", "efficiency", "directness"],
    "Tech / Engineering":     ["clarity", "process", "documentation"],
    "Art / Music":            ["craftsmanship", "expression", "patience"],
    "Foodie / Restaurants":   ["taste", "experience", "quality"],
    "Diet / Lifestyle":       ["intentionality", "discipline", "health"],
    "Drinks / Beverage":      ["taste", "ritual", "good company"],
    "Travel / Adventure":     ["freedom", "movement", "experience"],
    "Recovery / Sobriety":    ["clarity", "second chances", "growth"],
    "Medical / Patient":      ["care", "patience", "respect for time"],
    "Gaming":                 ["mastery", "strategy", "fairness"],
    "Reading / Books":        ["depth", "patience", "insight"],
    "Film / TV":              ["story", "craft", "narrative"],
    "Crafts / DIY":           ["craftsmanship", "self-reliance", "patience"],
    "Hunting / Fishing":      ["self-reliance", "patience", "tradition"],
    "Gardening":              ["patience", "stewardship", "legacy"],
    "Pets / Animals":         ["care", "loyalty", "responsibility"],
    "Real Estate":            ["operator-to-operator", "directness", "numbers"],
    "Causes / Politics":      ["principle", "service", "clarity"],
    "Politics / Left":        ["fairness", "community", "transparency"],
    "Politics / Right":       ["self-reliance", "tradition", "clarity"],
    "Health / Wellness":      ["care", "intentionality", "balance"],
    "Luxury / Fashion":       ["craftsmanship", "taste", "white-glove"],
    "Frugal / Budget":        ["clarity", "directness", "no waste"],
    "Higher Education":       ["depth", "documentation", "process"],
    "Veteran / Military":     ["service", "directness", "respect for time"],
}

# Life events overrule interest-based values -- they're the strongest signal
LIFE_EVENT_TO_VALUES = {
    "recently_divorced":       ["simplicity", "fresh start", "respect for time"],
    "recently_widowed":        ["care", "patience", "no pressure"],
    "recent_marriage":         ["fresh start", "future", "simplicity"],
    "recent_birth_in_family":  ["family", "security", "simplicity"],
    "recent_move":             ["fresh start", "logistics simplicity"],
    "recent_retirement":       ["freedom", "rest", "stewardship"],
    "recent_job_change":       ["transition", "logistics simplicity"],
    "recent_death_in_family":  ["care", "patience", "no pressure", "respect"],
    "foreclosure":             ["discretion", "fast resolution", "exit"],
    "bankruptcy":              ["discretion", "fresh start", "no judgment"],
    "lawsuit":                 ["discretion", "speed", "clean exit"],
    "award_recognition":       ["recognition of work", "respect"],
}


def stage2_resonance(personality: dict) -> dict:
    """Returns the value-set + sensitivities + tone profile this person responds to."""
    values: list[str] = []
    sensitivities: list[str] = []
    interests = personality.get("interests", {}) or {}
    life_events = personality.get("life_events", {}) or {}

    # Life events FIRST (they overrule everything else)
    for tag in life_events:
        if tag in LIFE_EVENT_TO_VALUES:
            for v in LIFE_EVENT_TO_VALUES[tag]:
                if v not in values: values.append(v)
            # Sensitivities -- handle these topics gently or not at all
            if tag in ("recently_widowed", "recent_death_in_family"):
                sensitivities.append("recent_loss")
            if tag == "foreclosure":
                sensitivities.append("financial_distress")
            if tag == "bankruptcy":
                sensitivities.append("financial_distress")
            if tag in ("Recovery / Sobriety", "Medical / Patient"):
                sensitivities.append("health_topic")

    # Interests next
    for cat in interests:
        if cat in INTEREST_TO_VALUES:
            for v in INTEREST_TO_VALUES[cat]:
                if v not in values:
                    values.append(v)

    # Tone derived from comm style + life events
    comm = personality.get("communication_style", "neutral")
    if "recent_loss" in sensitivities:
        tone = "gentle_unhurried"
    elif "financial_distress" in sensitivities:
        tone = "discreet_direct"
    elif comm == "formal":
        tone = "professional_concise"
    elif comm == "casual":
        tone = "warm_direct"
    else:
        tone = "neighborly_clear"

    return {
        "values": values[:8],
        "sensitivities": sensitivities,
        "tone": tone,
    }


# ============== STAGE 3: MARKET STRATEGY ==============
# Positioning angle = how we frame the offer to land in this person's worldview.
POSITIONING_ANGLES = {
    # value-tag -> positioning angle
    "craftsmanship":         "We work with sellers who built or maintained something worth honoring -- the next owner inherits what you preserved.",
    "freedom":               "Cash close means you can move on your own timeline -- no public market exposure, no chain, no waiting.",
    "legacy":                "The property carries your fingerprint -- we close it cleanly so the chapter ends well.",
    "stewardship":           "We respect what's been kept. Cash close, your timeline, the next owner takes care.",
    "discipline":            "Clean process: written offer, due diligence done, close in 10-21 days.",
    "consistency":           "Predictable: cash, no contingencies, paperwork in writing, close on schedule.",
    "results":               "Net offer in your hand within 48 hours of a property walk.",
    "integrity":             "We tell you the offer math. If it doesn't work for you, walk -- no pressure.",
    "service":               "We're the buyer side, not a middleman -- direct seller-to-buyer transaction.",
    "security":              "Cash means certainty. No buyer financing falling through at the eleventh hour.",
    "stability":             "Close on a date you choose. We'll work backwards from your moving timeline.",
    "protection":            "Discreet -- no for-sale sign, no showings parading through the family's privacy.",
    "operator-to-operator":  "Direct: numbers, terms, close. Skip the small talk.",
    "efficiency":            "One call, one offer, one close. We won't waste your time.",
    "directness":            "Straight numbers. Cash. Your timeline.",
    "clarity":               "Everything in writing. You see the math we use to land at our offer.",
    "process":               "Documented from the first touch to closing -- no surprises.",
    "documentation":         "Title work + survey + walk-through paperwork shared in advance.",
    "expression":            "We don't strip the property of what makes it the place. Whatever the next owner does, your version stays the version that built it.",
    "patience":              "No pressure on timing. We move when you move.",
    "taste":                 "We work with properties that deserve the next owner to actually appreciate them.",
    "experience":            "Smooth process from first call to keys -- you'll know what's happening at each step.",
    "quality":               "We don't lowball -- we offer what the math supports and we show our work.",
    "intentionality":        "You've been deliberate about life choices -- this should match. Cash, your terms, your timeline.",
    "health":                "We make this part low-stress. One call, one offer, your timeline.",
    "ritual":                "Property sales don't need to be chaos. We bring order.",
    "good company":          "Real conversations, real numbers, no pitch theater.",
    "movement":              "We close fast so you're not anchored.",
    "second chances":        "Fresh page on the property -- yours and the next owner's.",
    "growth":                "We make selling the property the easiest thing on your plate this season.",
    "care":                  "We respect that this isn't just a transaction.",
    "respect for time":      "60 seconds to know if we're a fit. 30 minutes from there to a written offer.",
    "mastery":               "We're operators -- we don't run a script.",
    "strategy":              "Pricing math + market context shared up front so you can pressure-test the offer.",
    "fairness":              "Net to you is what we discuss -- no shocks at the closing table.",
    "depth":                 "Comps, repair estimates, ARV math -- all in writing before you decide.",
    "insight":               "We share what we see in the market for properties like yours, even if you don't sell to us.",
    "story":                 "Properties have arcs. We help close yours cleanly.",
    "narrative":             "Property handover should feel like a chapter ending, not a fight.",
    "self-reliance":         "You don't need us. We're an option. Take it or pass.",
    "tradition":             "Keep what works -- cash, clear terms, hand-shake-grade trust.",
    "loyalty":               "We stick to what we said. Written offer is the offer.",
    "responsibility":        "We close clean -- title, taxes, prorations all handled.",
    "principle":             "We work the same way regardless of who's across the table.",
    "transparency":          "Comps + math shared up front, no withheld info.",
    "balance":               "Property sale shouldn't dominate your week. One call, then you decide.",
    "white-glove":           "Concierge close: title, paperwork, coordination handled by us.",
    "no waste":              "No third-party fees, no public-market overhead, nothing taken off the top. Net to you.",
    "fresh start":           "Clean exit so the next chapter can start.",
    "simplicity":            "One call, written offer, your close date. That's it.",
    "logistics simplicity":  "We'll work around your move logistics -- close-on-funded-date if needed.",
    "fast resolution":       "We close in 10-21 days. Fastest path to resolution.",
    "exit":                  "We can move quickly when timing matters.",
    "discretion":            "No yard sign, no public exposure, no neighbors talking.",
    "no judgment":           "We don't ask why you're selling.",
    "speed":                 "Cash close. No financing, no appraisal contingency.",
    "clean exit":            "Title work and prorations handled at our cost.",
    "no pressure":           "Take the offer or don't -- we won't follow up if you ask us not to.",
    "rest":                  "We make this the easy part of your week.",
    "transition":            "We close around your other transitions.",
    "future":                "Cash to fund the next chapter.",
    "family":                "We work fast and discreetly so the family isn't disrupted.",
    "recognition of work":   "What you built deserves to be sold to someone who recognizes it.",
    "respect":               "Your timeline. Your terms. Your call.",
}


def stage3_strategy(resonance: dict, lead_context: dict | None) -> dict:
    """Pick the top 3 positioning angles for this person."""
    if not isinstance(lead_context, dict):
        lead_context = {}
    values = resonance.get("values", []) or []
    angles = []
    used_angles_text = set()
    for v in values:
        angle = POSITIONING_ANGLES.get(v)
        if angle and angle not in used_angles_text:
            angles.append({"value": v, "angle": angle})
            used_angles_text.add(angle)
        if len(angles) >= 3:
            break
    # Always have at least one
    if not angles:
        angles.append({"value": "directness",
                        "angle": POSITIONING_ANGLES["directness"]})
    return {
        "positioning_angles": angles,
        "recommended_cadence": _recommended_cadence(resonance),
        "channel_priority": _channel_priority(resonance, lead_context),
    }


def _recommended_cadence(resonance: dict) -> str:
    sens = resonance.get("sensitivities", [])
    if "recent_loss" in sens:
        return "single_touch_then_wait_60d"
    if "financial_distress" in sens:
        return "two_touch_within_7d"
    return "three_touch_over_14d"


def _channel_priority(resonance: dict, lead_context: dict) -> list[str]:
    sens = resonance.get("sensitivities", [])
    tone = resonance.get("tone", "")
    if "recent_loss" in sens:
        return ["mail", "email"]  # never SMS/call after a loss
    if "financial_distress" in sens:
        return ["mail", "voicemail", "email"]  # discreet, no SMS
    if tone in ("warm_direct", "neighborly_clear"):
        return ["sms", "call", "email"]
    return ["email", "mail", "sms"]


# ============== STAGE 5: ROUTING -- which closer agent handles which state ==============
# Closer roster (4 firmware files exist):
#   31_outreach_agent          -- Piper (warm, Nashville voice; default)
#   marquise_reed_acquisitions -- Marquise (Memphis local; TN only)
#   36_rex_wholesale           -- Rex (wholesale grit; Rust Belt + Mountain West)
#   34_compliance_gate         -- Justine (license-required hard blocks)
#
# Mapped by region. Hard-block states route to compliance gate, not a closer.
STATE_TO_CLOSER = {
    # --- TN local ---
    "TN": "marquise_reed_acquisitions",

    # --- South (Piper voice) ---
    "TX": "31_outreach_agent",
    "FL": "31_outreach_agent",
    "GA": "31_outreach_agent",
    "AL": "31_outreach_agent",
    "MS": "31_outreach_agent",
    "LA": "31_outreach_agent",
    "AR": "31_outreach_agent",
    "SC": "31_outreach_agent",
    "OK": "31_outreach_agent",
    "KY": "31_outreach_agent",
    "VA": "31_outreach_agent",
    "WV": "31_outreach_agent",

    # --- Northeast + Mid-Atlantic (Piper) ---
    "NY": "31_outreach_agent",
    "NJ": "31_outreach_agent",
    "PA": "31_outreach_agent",
    "MA": "31_outreach_agent",
    "CT": "31_outreach_agent",
    "RI": "31_outreach_agent",
    "VT": "31_outreach_agent",
    "NH": "31_outreach_agent",
    "ME": "31_outreach_agent",
    "MD": "31_outreach_agent",
    "DE": "31_outreach_agent",
    "DC": "31_outreach_agent",

    # --- Pacific (Piper) ---
    "OR": "31_outreach_agent",
    "WA": "31_outreach_agent",
    "AK": "31_outreach_agent",
    "HI": "31_outreach_agent",

    # --- Midwest / Rust Belt (Rex) ---
    "OH": "36_rex_wholesale",
    "MI": "36_rex_wholesale",
    "IN": "36_rex_wholesale",
    "WI": "36_rex_wholesale",
    "MN": "36_rex_wholesale",
    "IA": "36_rex_wholesale",
    "MO": "36_rex_wholesale",
    "KS": "36_rex_wholesale",
    "NE": "36_rex_wholesale",
    "ND": "36_rex_wholesale",
    "SD": "36_rex_wholesale",

    # --- Mountain West + SW (Rex) ---
    "AZ": "36_rex_wholesale",
    "NV": "36_rex_wholesale",
    "NM": "36_rex_wholesale",
    "UT": "36_rex_wholesale",
    "CO": "36_rex_wholesale",
    "WY": "36_rex_wholesale",
    "MT": "36_rex_wholesale",
    "ID": "36_rex_wholesale",

    # --- Hard-block: license required / pre-foreclosure restrictions ---
    "NC": "34_compliance_gate",   # NC HB 797 wholesale block
    "IL": "34_compliance_gate",   # IL license required >1 deal
    "CA": "34_compliance_gate",   # CC 2945/1695 pre-foreclosure restrictions
}


def stage5_routing(lead_context: dict | None, resonance: dict) -> dict:
    if not isinstance(lead_context, dict):
        lead_context = {}
    state = (lead_context.get("state", "") or "").upper()
    closer = STATE_TO_CLOSER.get(state, "31_outreach_agent")  # Piper as default
    handoff_steps = [
        f"1. SEO/keyword resonance scan -> 17_content_strategy.md",
        f"2. Market intel pull -> 35_broker_analytics.md (per-{state} comp data)",
        f"3. Marketing strategy review -> 19_platform_copywriter.md (positioning sign-off)",
        f"4. Pitch narrative draft -> 31_outreach_agent.md (Piper drafts in voice)",
        f"5. Compliance gate -> 34_compliance_gate.md (state rules + DNC check)",
        f"6. Closer dispatch -> .claude/agents/{closer}.md",
    ]
    return {
        "primary_closer_agent": closer,
        "state_routing_chain": handoff_steps,
        "compliance_check_required": state in ("NC", "IL", "CA"),
    }


# ============== ORCHESTRATOR ==============
def run_pipeline(personality: dict, lead_context: dict | None = None) -> dict:
    """Run all 5 stages, return the full pitch package."""
    if not isinstance(personality, dict):
        personality = {}
    if not isinstance(lead_context, dict):
        lead_context = {}

    resonance = stage2_resonance(personality)
    strategy = stage3_strategy(resonance, lead_context)
    routing = stage5_routing(lead_context, resonance)

    # Stage 4 builds the actual narrative -- delegated to pitch_narrative module.
    # The closer agent's slug from Stage 5 is used as the VOICE for the narrative.
    try:
        from .pitch_narrative import build_narrative
        narrative = build_narrative(personality, resonance, strategy, lead_context,
                                     agent_slug=routing.get("primary_closer_agent"))
    except Exception as e:
        narrative = {"error": str(e)[:200], "touchpoints": []}

    return {
        "stage1_profile": {
            "interest_count": sum(len(v) for v in personality.get("interests", {}).values()),
            "life_event_count": len(personality.get("life_events", {})),
            "comm_style": personality.get("communication_style", "neutral"),
        },
        "stage2_resonance": resonance,
        "stage3_strategy": strategy,
        "stage4_narrative": narrative,
        "stage5_routing": routing,
    }
