"""
pitch_narrative -- multi-touchpoint, implicit-resonance pitch generator.

REPLACES the old pitch_hooks.py one-liners. Per operator feedback:
  - DON'T explicitly cite the source signal ("I saw your MMA interest")
  - DO speak in language that resonates with people in that tribe
  - DO build a 3-touchpoint story arc, not a one-liner
  - DO match TONE to detected communication style + life-event sensitivity
  - DON'T sound like surveillance ("we noticed your gardening")
  - DO feel like recognition ("properties like yours deserve a buyer who...")

Output is a dict with per-channel (email/sms/voicemail/mail) copy + the
3-touchpoint sequence (initial -> follow-up -> nudge).
"""
from __future__ import annotations

import re

# Tone profiles -> opening cadence + sentence rhythm
TONE_OPENERS = {
    "gentle_unhurried": {
        "openers": [
            "Hi {first} -- no pressure on this, just wanted to reach out.",
            "{first}, hope this finds you well.",
            "{first}, taking a moment to introduce myself rather than rush in.",
        ],
        "ctas": [
            "When you're ready -- a 10-minute call works for me whenever you have time.",
            "No timeline on my end. Reach out if and when you'd like to talk.",
        ],
        "signoff": "Take care,",
    },
    "discreet_direct": {
        "openers": [
            "{first} -- direct note, your time is valuable.",
            "Hi {first}, keeping this short and confidential.",
            "{first}, brief note that respects your privacy.",
        ],
        "ctas": [
            "If a confidential 15-minute call helps, my line is below.",
            "Reply or call when convenient -- discretion guaranteed.",
        ],
        "signoff": "Confidentially,",
    },
    "professional_concise": {
        "openers": [
            "{first} --",
            "Mr./Ms. {last},",
            "{first}, brief overview of what we do and why I'm reaching out.",
        ],
        "ctas": [
            "Could we schedule a 20-minute call this week?",
            "Available for a call at your convenience -- please reply with a time that works.",
        ],
        "signoff": "Best regards,",
    },
    "warm_direct": {
        "openers": [
            "Hey {first} --",
            "{first}, quick note from one operator to another.",
            "{first}, hope your week is going well.",
        ],
        "ctas": [
            "Worth a quick call this week? Numbers below.",
            "Open to talking? 60 seconds tells you if we're a fit.",
        ],
        "signoff": "Talk soon,",
    },
    "neighborly_clear": {
        "openers": [
            "Hi {first},",
            "{first}, hope this finds you well.",
            "{first}, real quick:",
        ],
        "ctas": [
            "Worth a quick call this week?",
            "Happy to share the math if you'd like to see it.",
        ],
        "signoff": "Best,",
    },
}


# Body templates -- the ANGLE goes in here, the values get woven in.
# IMPORTANT: never name the interest. ASSOCIATE with the value.
BODY_TEMPLATES = {
    "initial": [
        "I work with property owners {state_phrase} who want a clean direct sale -- "
        "cash, your timeline, no showings, no third parties. {angle_1}",
        "Quick context: we make direct cash offers on properties {state_phrase}. "
        "{angle_1} What that looks like in practice: written offer within 48 hours of "
        "a 10-minute property walk, close on a date you choose, no buyer-financing risk.",
        "Reaching out because we work with sellers {state_phrase} who value "
        "{value_word_1} and {value_word_2}. {angle_1}",
    ],
    "followup_3d": [
        "{first}, following up on my note from earlier this week. {angle_2} "
        "If the property isn't something you want to move on right now, I'll respect that "
        "and step back -- just wanted to make the door open in case the timing changes.",
        "{first} -- circling back. {angle_2} A quick reply (yes / no / not now) "
        "is all I need.",
    ],
    "nudge_10d": [
        "{first}, last note from me on this. {angle_3} If now isn't the right "
        "time, I won't keep reaching out. The door stays open if anything changes -- "
        "my contact info is in the previous email.",
        "{first}, final touch. {angle_3} I appreciate your time either way.",
    ],
}

# Map values -> warm one-word phrase to weave in
VALUE_WORDS = {
    "craftsmanship": "craft",
    "freedom": "freedom",
    "legacy": "legacy",
    "stewardship": "stewardship",
    "discipline": "discipline",
    "consistency": "consistency",
    "results": "results",
    "integrity": "integrity",
    "service": "service",
    "security": "security",
    "stability": "stability",
    "protection": "discretion",
    "operator-to-operator": "directness",
    "efficiency": "efficiency",
    "directness": "straightforwardness",
    "clarity": "clarity",
    "process": "process",
    "documentation": "documentation",
    "patience": "patience",
    "taste": "taste",
    "experience": "experience",
    "quality": "quality",
    "intentionality": "intention",
    "health": "well-being",
    "ritual": "rhythm",
    "movement": "movement",
    "second chances": "fresh starts",
    "growth": "growth",
    "care": "care",
    "respect for time": "respect for your time",
    "mastery": "mastery",
    "strategy": "strategy",
    "fairness": "fairness",
    "depth": "depth",
    "insight": "insight",
    "story": "story",
    "narrative": "story",
    "self-reliance": "self-reliance",
    "tradition": "tradition",
    "loyalty": "loyalty",
    "responsibility": "responsibility",
    "principle": "principle",
    "transparency": "transparency",
    "balance": "balance",
    "white-glove": "white-glove handling",
    "no waste": "no waste",
    "fresh start": "a fresh start",
    "simplicity": "simplicity",
    "logistics simplicity": "smooth logistics",
    "fast resolution": "fast resolution",
    "exit": "a clean exit",
    "discretion": "discretion",
    "no judgment": "no judgment",
    "speed": "speed",
    "clean exit": "a clean exit",
    "no pressure": "no pressure",
    "rest": "rest",
    "transition": "smooth transitions",
    "future": "what's next",
    "family": "the family",
    "recognition of work": "recognition of what was built",
    "respect": "respect",
}


def _first_name(name: str) -> str:
    if not name: return "there"
    parts = name.replace(",", " ").split()
    if not parts: return "there"
    if "," in name and len(parts) >= 2: return parts[1].title()
    return parts[0].title()


def _last_name(name: str) -> str:
    if not name: return ""
    parts = name.replace(",", " ").split()
    if "," in name and len(parts) >= 1: return parts[0].title()
    if len(parts) >= 2: return parts[-1].title()
    return ""


def _state_phrase(state: str) -> str:
    if not state: return "in your area"
    name = {
        "CA": "in California", "TX": "in Texas", "FL": "in Florida",
        "NY": "in New York", "MO": "in Missouri", "GA": "in Georgia",
        "OH": "in Ohio", "TN": "in Tennessee", "NC": "in North Carolina",
        "AZ": "in Arizona", "IL": "in Illinois",
    }.get(state.upper(), f"in {state.upper()}")
    return name


def _select_template(templates: list, key: int) -> str:
    return templates[key % len(templates)]


def build_narrative(personality: dict, resonance: dict, strategy: dict,
                     lead_context: dict | None = None,
                     agent_slug: str | None = None) -> dict:
    """
    Build a 3-touchpoint pitch sequence with channel-specific copy.

    Returns:
        {
          "tone": "warm_direct",
          "positioning": "...",
          "touchpoints": [
            {
              "step": 1, "name": "initial", "send_after_days": 0,
              "channel_copy": {
                "email": {"subject": "...", "body": "..."},
                "sms":   {"body": "..."},  # short
                "voicemail": {"script": "..."},
                "mail":  {"body": "..."},  # longer letter
              },
              "rationale": "why this opening lands",
            },
            ...
          ],
        }
    """
    if not isinstance(lead_context, dict): lead_context = {}
    if not isinstance(personality, dict): personality = {}

    target = lead_context.get("owner_name") or lead_context.get("target", "")
    first = _first_name(target)
    last = _last_name(target)
    state = (lead_context.get("state", "") or "").upper()
    state_phrase = _state_phrase(state)

    tone = resonance.get("tone", "neighborly_clear")
    tone_pkg = TONE_OPENERS.get(tone, TONE_OPENERS["neighborly_clear"])

    # ===== AGENT VOICE OVERRIDE =====
    # If an agent_slug is supplied, pull the voice from .claude/agents/<slug>.md
    # and override the generic templates with the agent's actual personality.
    agent_voice = None
    if agent_slug:
        try:
            from .voice_extractor import load_agent
            agent_voice = load_agent(agent_slug)
            # Override openers with the agent's actual voice
            if agent_voice.get("openers"):
                tone_pkg = {
                    **tone_pkg,
                    "openers": agent_voice["openers"],
                    "signoff": agent_voice.get("signoff", tone_pkg.get("signoff", "Best,")),
                }
        except Exception:
            pass

    angles = strategy.get("positioning_angles", [])
    values = resonance.get("values", [])
    angle_1 = angles[0]["angle"] if len(angles) >= 1 else \
              "We make cash offers, close on your timeline, no agents."
    angle_2 = angles[1]["angle"] if len(angles) >= 2 else \
              "If timing isn't right, I respect that completely."
    angle_3 = angles[2]["angle"] if len(angles) >= 3 else \
              "Door stays open."

    value_word_1 = VALUE_WORDS.get(values[0], "directness") if values else "directness"
    value_word_2 = VALUE_WORDS.get(values[1], "respect") if len(values) > 1 else "clarity"

    fmt = {
        "first": first, "last": last,
        "state_phrase": state_phrase,
        "value_word_1": value_word_1, "value_word_2": value_word_2,
        "angle_1": angle_1, "angle_2": angle_2, "angle_3": angle_3,
    }

    # === TOUCHPOINT 1: INITIAL ===
    opener = tone_pkg["openers"][0].format(**fmt)
    body_init = _select_template(BODY_TEMPLATES["initial"], 0).format(**fmt)
    cta_init = tone_pkg["ctas"][0]
    sign = tone_pkg["signoff"]

    # Use the agent's signature block if we have it (instead of [Agent Name] placeholder)
    sig_lines = "[Agent Name]"
    if agent_voice and agent_voice.get("signature_block"):
        sig_lines = agent_voice["signature_block"]
    email_body = f"{opener}\n\n{body_init}\n\n{cta_init}\n\n{sign}\n{sig_lines}"
    sms_body = (
        f"{first}, this is [Agent] from Everlight. "
        f"{angle_1[:140]} "
        f"{cta_init[:80]}"
    )
    vm_script = (
        f"{opener} This is [Agent Name] with Everlight Ventures. "
        f"{angle_1} "
        f"{cta_init} "
        f"You can reach me at [number]. Have a good day."
    )
    mail_body = (
        f"{opener}\n\n{body_init}\n\n"
        f"What this means for you, plain English:\n"
        f" - One conversation tells you if we're a fit (no commitment)\n"
        f" - Written cash offer within 48 hours of a property walk\n"
        f" - You pick the close date -- we work back from your timeline\n"
        f" - Direct sale to us as a buyer (we are not a brokerage, no third party in between)\n\n"
        f"{cta_init}\n\n{sign}\n{sig_lines}"
    )

    # SUBJECT lines -- value-resonant, never explicit
    subj_options = {
        "gentle_unhurried":   f"For when the timing is right",
        "discreet_direct":    f"Confidential note re: your property",
        "professional_concise": f"Property inquiry -- {state_phrase.replace('in ', '').title()}",
        "warm_direct":        f"Quick note about your property",
        "neighborly_clear":   f"Quick property note for {first}",
    }
    subject = subj_options.get(tone, subj_options["neighborly_clear"])

    touch1 = {
        "step": 1, "name": "initial", "send_after_days": 0,
        "channel_copy": {
            "email":     {"subject": subject, "body": email_body},
            "sms":       {"body": sms_body},
            "voicemail": {"script": vm_script},
            "mail":      {"body": mail_body},
        },
        "rationale": (
            f"Tone: {tone} (matched to detected communication style + life-event "
            f"sensitivities). Opens with {value_word_1} -- a value the recipient "
            f"appears to operate by. Positioning angle invokes '{angles[0]['value'] if angles else 'directness'}'."
        ),
    }

    # === TOUCHPOINT 2: FOLLOW-UP (3-7 days) ===
    cadence = strategy.get("recommended_cadence", "three_touch_over_14d")
    if cadence == "single_touch_then_wait_60d":
        touchpoints = [touch1]  # respect grief / stop after one
    else:
        days_2 = 7 if cadence == "two_touch_within_7d" else 4
        opener_2 = tone_pkg["openers"][1].format(**fmt) if len(tone_pkg["openers"]) > 1 else f"{first},"
        body_2 = _select_template(BODY_TEMPLATES["followup_3d"], 0).format(**fmt)
        cta_2 = tone_pkg["ctas"][-1]
        email_2 = f"{opener_2}\n\n{body_2}\n\n{cta_2}\n\n{sign}\n[Agent Name]"
        sms_2 = f"{first}, circling back. {angle_2[:120]} Reply yes/no/not-now?"
        vm_2 = f"{opener_2} {body_2} Talk to you soon -- [number]."

        touch2 = {
            "step": 2, "name": "followup", "send_after_days": days_2,
            "channel_copy": {
                "email":     {"subject": f"Re: {subject}", "body": email_2},
                "sms":       {"body": sms_2},
                "voicemail": {"script": vm_2},
            },
            "rationale": f"Soft re-engage. Cadence: {cadence}. Repeats the angle in different words.",
        }
        touchpoints = [touch1, touch2]

        # === TOUCHPOINT 3: NUDGE (10-14 days) ===
        if cadence == "three_touch_over_14d":
            opener_3 = tone_pkg["openers"][-1].format(**fmt)
            body_3 = _select_template(BODY_TEMPLATES["nudge_10d"], 0).format(**fmt)
            email_3 = f"{opener_3}\n\n{body_3}\n\n{sign}\n[Agent Name]"
            sms_3 = f"{first}, last note. {angle_3[:100]} Door stays open."
            touch3 = {
                "step": 3, "name": "nudge", "send_after_days": 14,
                "channel_copy": {
                    "email":     {"subject": f"Final note re: {subject}", "body": email_3},
                    "sms":       {"body": sms_3},
                },
                "rationale": "Respectful close. Opens the door without pressure.",
            }
            touchpoints.append(touch3)

    return {
        "tone": tone,
        "positioning_value": angles[0]["value"] if angles else "directness",
        "touchpoints": touchpoints,
        "channels_in_priority_order": strategy.get("channel_priority", ["email"]),
    }
