#!/usr/bin/env python3
"""
llm_compose.py -- the cohesive collage. ONE intelligent message from ALL the pieces:
  persona voice/characteristics (.claude/agents dossier)
  + conversation memory (what was said, open threads, commitments via conversation_memory)
  + market / OSINT intel (Memphis economics via piper_market_data)
  + Everlight brand voice constraints (no hyphens, straight to the point, STOP line)
  -> a live LLM (Anthropic) writes the actual reply, grounded in every input.

Frugal + resilient: the live key resolves dynamically from the SECURED mirror (it was
rotated + remapped out of the public path), with fallbacks. If the LLM is unreachable the
caller falls back to the heuristic template, so generation never hard fails.

Key resolution order (never hardcode a path, survives the next rotation):
  env ANTHROPIC_API_KEY -> _state/cloud_mirror_secrets/e5_data.env -> /root/.config/ai/keys.env
"""
from __future__ import annotations

import json
import os
import re
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path("/mnt/sdcard/AA_MY_DRIVE")
AGENTS_DIR = ROOT / ".claude" / "agents"
# Order matters: the secured mirror is the canonical LIVE source post key-rotation. The
# ambient env (and the public flat files) can carry a STALE rotated key, so they rank below it.
KEY_SOURCES = [
    ROOT / "_state" / "cloud_mirror_secrets" / "e5_data.env",  # canonical live
    None,  # os.environ (may be stale)
    Path("/root/.config/ai/keys.env"),
    ROOT / "03_AUTOMATION_CORE" / "03_Credentials" / ".env",
]
MODEL = os.environ.get("EV_LLM_MODEL", "claude-haiku-4-5-20251001")

PERSONA_DOSSIER = {
    "piper_reeves": "piper_reeves_outreach.md",
    "henry_hammond": "henry_hammond_negotiator.md",
    "marvin_cohen": "marvin_cohen_closer.md",
    "vaughn_sterling": "vaughn_sterling_partner.md",
}
PERSONA_SIG = {
    "piper_reeves": "Piper Reeves\nOutreach, Everlight Ventures",
    "henry_hammond": "Henry Hammond\nAcquisitions, Everlight Ventures",
    "marvin_cohen": "Marvin Cohen\nClosing Coordinator, Everlight Ventures",
    "vaughn_sterling": "Vaughn Sterling\nSenior Partner, Everlight Ventures",
}

# long dash glyphs (built via chr to keep them out of source); collapsed by the brand guard
_DASHES = [chr(0x2014), chr(0x2013)]


def _resolve_key() -> str:
    """Resolve the live key, secured-mirror-first (env may hold a stale rotated key)."""
    for src in KEY_SOURCES:
        if src is None:
            v = os.environ.get("ANTHROPIC_API_KEY", "").strip()
            if v:
                return v
            continue
        if not Path(src).exists():
            continue
        try:
            for line in Path(src).read_text().splitlines():
                line = line.strip()
                if line.startswith("export "):
                    line = line[7:]
                if line.startswith("ANTHROPIC_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
        except Exception:
            continue
    return ""


def persona_voice(persona_id: str) -> str:
    """Pull the persona's voice/characteristics from their dossier (trimmed)."""
    f = AGENTS_DIR / PERSONA_DOSSIER.get(persona_id, "")
    if f.exists():
        return f.read_text()[:1600]
    return f"{persona_id}: warm, sharp, straight to the point real estate acquisitions pro."


def _memphis_market() -> dict:
    try:
        import sys
        sys.path.insert(0, str(ROOT / "01_BUSINESSES/Everlight_Ventures/Broker_OS/wholesale_agent"))
        from piper_market_data import get_market_data
        return get_market_data("Memphis", "TN") or {}
    except Exception:
        return {}


def compose(persona_id: str, ctx: dict, property_facts: dict | None = None) -> str | None:
    """Write the reply via the live LLM, grounded in persona + memory + intel + brand.
    Returns the message body, or None if the LLM is unavailable (caller falls back)."""
    key = _resolve_key()
    if not key:
        return None
    mkt = _memphis_market()
    voice = persona_voice(persona_id)
    first_from_persona = persona_id not in (ctx.get("personas_already_introduced") or [])

    system = (
        "You are writing a single email reply on behalf of an Everlight Ventures wholesale "
        "acquisitions persona. Embody this persona's voice and characteristics EXACTLY:\n\n"
        f"{voice}\n\n"
        "BRAND + STYLE RULES (hard):\n"
        "- Warm, human, straight to the point. A real person typed this on a phone.\n"
        "- NO hyphens between words and NO long dashes. Use short sentences instead.\n"
        "- No 'we buy houses' spam tone, no ALL CAPS, no exclamation spam.\n"
        "- Reference what they actually said; answer their open question first if there is one.\n"
        "- Never repeat a point we already made. Advance the relationship by one concrete step.\n"
        "- Ground any market claim ONLY in the provided Memphis stats. Invent nothing.\n"
        "- INVENT NO FACTS beyond the inputs: no neighborhood/subdivision names, no lot or "
        "  property features (corner lot, beds, baths), no phone numbers or area codes, no "
        "  details not explicitly given. If you do not have it, do not mention it. No placeholders.\n"
        "- Do NOT include a phone number or 'area code' unless one is provided in the inputs.\n"
        "- If a 'negotiation' block is given, you are mid price-talk: state OUR number "
        "  (negotiation.our_offer), justify it briefly with the math/market, acknowledge their "
        "  counter, then COUNTER or ACCEPT per negotiation.action. Never go past our walk_away. "
        "  Hold the line warmly, do not cave. One number, one clear next step.\n"
        "\nHANDOFF INTRODUCTION RULE:\n"
        "You introduce yourself exactly ONCE, on your FIRST message to a given person. The input "
        "'first_message_from_you' tells you. If it is TRUE, one brief handoff line is allowed "
        "(e.g. 'Henry here, picking up from Piper'), then proceed. If it is FALSE, you are already "
        "known: do NOT reintroduce, do NOT say 'picking up from Piper', 'taking over for Piper', "
        "'this is Henry again', or restate your role. Open later messages by referencing the live "
        "conversation (their last reply, the number on the table, the next step).\n"
        "\nOFFER FRAMING RULE (when presenting a price):\n"
        "Present every cash number as the strong, smart move, confident and positive. You are "
        "offering certainty, speed, and zero hassle, and you believe in the number. Never "
        "apologize for it, never undercut it, never compare it down against the appraisal or "
        "retail. Frame on VALUE not discount: cash close on their timeline, as-is (no repairs, no "
        "cleanup), no agent commissions or fees, we handle tenants/liens/problems, no months of "
        "showings or buyers backing out. Lead with what they GAIN.\n"
        "BANNED phrases (never write these or close variants): 'looks off the appraisal', 'the "
        "numbers don't work', 'it's low but', 'not what you were hoping for', 'sorry it's not "
        "higher', 'wish I could offer more', 'this might seem low', 'don't be offended', any "
        "apology/hedge/downward-comparison on the offer; fake urgency ('expires tonight', 'last "
        "chance') unless a real written deadline exists; guarantees ('guaranteed to close', '100%'). "
        "Say 'we can typically close in X' never 'guaranteed by X'. Confident is the floor, "
        "dishonest is the ceiling you never touch (CAN-SPAM + TN-UDAP clean).\n"
        "- End with the persona signature provided. Include a soft 'reply STOP to opt out' line.\n"
        "- Output ONLY the email body. No subject, no preamble, no markdown."
    )
    user = {
        "reply_to": ctx.get("name") or "there",
        "their_role": ctx.get("role"),
        "first_message_from_you": first_from_persona,
        "message_count_with_this_person": ctx.get("message_count", 0),
        "their_open_questions_answer_these": ctx.get("must_answer") or [],
        "facts_they_told_us_reference_for_rapport": ctx.get("facts_we_know") or [],
        "we_already_asked_do_not_repeat": ctx.get("we_already_asked") or [],
        "our_commitments_to_honor": ctx.get("our_commitments") or [],
        "objections_to_handle": ctx.get("objections") or [],
        "next_action_goal": ctx.get("next_action"),
        "memphis_market_intel": {
            "median_price": mkt.get("median_home_price"),
            "days_on_market": mkt.get("days_on_market"),
            "price_change_yoy_pct": mkt.get("price_change_yoy_pct"),
            "monthly_holding_cost": mkt.get("monthly_holding_cost"),
        },
        "property": property_facts or {},
        "negotiation": ctx.get("negotiation"),  # {our_offer, their_counter, action, round, walk_away}
        "persona_signature": PERSONA_SIG.get(persona_id, "Everlight Ventures"),
    }
    body = json.dumps({
        "model": MODEL, "max_tokens": 600, "system": system,
        "messages": [{"role": "user", "content":
            "Write the reply now using these inputs:\n" + json.dumps(user, indent=2)}],
    }).encode()
    try:
        req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body,
              headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                       "content-type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=40) as r:
            d = json.load(r)
        text = "".join(b.get("text", "") for b in d.get("content", []))
        return _strip_dashes(text.strip()) or None
    except Exception:
        return None


def _strip_dashes(t: str) -> str:
    # brand guard: collapse any stray inter-word hyphens / long dashes the model slipped in
    for ch in _DASHES:
        t = t.replace(ch, " ")
    return re.sub(r"(?<=\w)-(?=\w)", " ", t)


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        print("key resolved:", "yes" if _resolve_key() else "NO")
        demo_ctx = {"name": "Chris", "role": "buyer",
                    "facts_we_know": ["sent their buying criteria; wants leads at leads@midsouthhomebuyers.com"],
                    "must_answer": [], "we_already_asked": [], "our_commitments": [],
                    "next_action": "confirm we logged their box + ask proof of funds and ZIP set"}
        out = compose("henry_hammond", demo_ctx)
        print("\n--- composed reply ---\n", out or "(LLM unavailable, caller uses template)")
