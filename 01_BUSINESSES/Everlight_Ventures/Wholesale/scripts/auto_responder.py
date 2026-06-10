#!/usr/bin/env python3
"""
auto_responder.py -- the always-loaded salesman. REACTIVE half of the pipeline.

When a contacted-list reply lands (inbox_router matched it), this AUTOMATICALLY generates
the owning agent's response and ARMS it as a gated "draft" -- no asking, no human in the loop
for generation. The gate (HALT + CAN-SPAM address) controls only the FIRE, never the
readiness. So the moment the system unblocks, a backlog of aimed responses launches instantly.

Flow (auto, triggered by a reply):
  match (inbox_router) -> classify intent -> generate agent response (voiced) -> STAGE draft
  ... draft sits in _state/staged_drafts/ as "armed" ...
  fire_drafts() (gated) -> sends armed drafts the instant HALT lifts + address is set.

Pairs with pipeline_phase_manager (PROACTIVE half: follow-ups / re-engagement on a sweep).
Together: adaptive, dynamic, proactive AND reactive.

Usage:
  python3 auto_responder.py --demo               # stage drafts for known warm replies (Chris/JWB)
  python3 auto_responder.py --list               # show armed drafts
  python3 auto_responder.py --fire --dry-run     # what WOULD fire (default safe)
  python3 auto_responder.py --fire               # live: send armed drafts IF unblocked
"""
from __future__ import annotations

import json
import os
import re
import sys
import hashlib
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/mnt/sdcard/AA_MY_DRIVE")
WH = ROOT / "01_BUSINESSES" / "Everlight_Ventures" / "Wholesale"
DRAFTS = ROOT / "_state" / "staged_drafts"
sys.path.insert(0, str(WH / "scripts"))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# Intent classifier (lightweight, keyword-based -- adaptive without an API call).
def classify_intent(text: str) -> str:
    t = (text or "").lower()
    if re.search(r"\b(stop|unsubscribe|not interested|remove me|do not contact)\b", t):
        return "opt_out"
    if re.search(r"\b(criteria|buy box|buying|we buy|we are looking|send (me|us) (the )?(leads|deals|properties))\b", t):
        return "buyer_criteria"
    if (re.search(r"\$\s?\d[\d,]{2,}|\b\d{2,3}\s?k\b", t)
            or re.search(r"\b(too low|counter|i (need|want|was thinking)|can you (do|go|come up)|"
                         r"lowest|best (you can|offer)|come up|not enough|asking)\b", t)):
        return "counter"
    if re.search(r"\b(interested|how much|what.s the (price|number)|make an offer|cash offer|call|talk)\b", t):
        return "seller_warm"
    if "?" in t:
        return "question"
    return "neutral"


def _buybox() -> dict:
    try:
        return json.loads((Path("/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale/config/chris_buy_box.json")).read_text())
    except Exception:
        return {}


def _lead_appraisal(email: str) -> int:
    """Resolve the property's appraisal for this contact (for negotiation math)."""
    try:
        t = json.loads((Path("/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale/tn_deal_tracker.json")).read_text())
        for v in t.values():
            if (v.get("email") or "").lower() == (email or "").lower():
                return int(v.get("total_appraisal_usd") or 0)
    except Exception:
        pass
    return 0


def _negotiation_block(from_addr: str, role: str, text: str):
    """Compute the next offer via the SHARED negotiation engine. Real life uses the same
    math as the sim. Returns None if we can't resolve the deal economics (graceful)."""
    appr = _lead_appraisal(from_addr)
    if not appr:
        return None
    nums = re.findall(r"\$?\s?(\d{2,3}(?:,\d{3})|\d{4,6})", (text or "").replace(" ", ""))
    their = int(nums[0].replace(",", "")) if nums else None
    mk = re.search(r"\b(\d{2,3})\s?k\b", (text or "").lower())
    if mk and not their:
        their = int(mk.group(1)) * 1000
    try:
        import negotiation, conversation_memory as cm
        box = _buybox().get("exit", {})
        exit_pct = box.get("all_in_target_pct_of_appraisal", 0.55)
        mm = box.get("min_margin_to_us_usd", 3000)
        rounds = max(1, sum(1 for m in cm.load(from_addr)["messages"] if m["dir"] == "out"))
        if role == "buyer":
            ask = round(exit_pct * appr); floor = ask - 1500
            n = negotiation.buyer_next(rounds, ask, floor, their)
            walk = n.get("floor")
        else:
            ceiling = round(exit_pct * appr) - mm; opening = round(ceiling * 0.88)
            n = negotiation.seller_next(rounds, opening, ceiling, their)
            walk = n.get("ceiling")
        return {"our_offer": n["offer"], "their_counter": their, "action": n["action"],
                "round": n["round"], "walk_away": walk}
    except Exception:
        return None


# Agent voices -- response generators per (agent, intent). Real drafts, brand voice,
# CAN-SPAM clean (STOP line + footer added by branded_mailer at fire time).
def _context_opener(ctx: dict) -> str:
    """Make the reply INTELLIGENT: answer their open question first, or show we heard a
    specific thing they said. Empty if nothing to ground on. Keeps us out of repeat-canned-land."""
    must = ctx.get("must_answer") or []
    if must:
        return f"On your question -- \"{must[0].strip()[:90]}\" -- here's the straight answer: "
    facts = ctx.get("facts_we_know") or []
    if facts:
        return f"Got what you said about \"{facts[0].strip()[:80]}\" -- noted and logged. "
    return ""


def generate_response(agent: str, intent: str, ctx: dict) -> dict:
    # COHESIVE COLLAGE (the upgrade): persona voice + conversation memory + market intel +
    # brand, composed by the live LLM. Falls back to the voiced template if LLM is unavailable.
    if intent != "opt_out":
        try:
            import llm_compose
            body = llm_compose.compose(agent, ctx)
            if body:
                return {"persona": agent, "subject": f"Re: {ctx.get('subject','your note')}",
                        "body": body, "engine": "llm"}
        except Exception:
            pass
    who = (ctx.get("who") or "there").split()[0].title() if ctx.get("who") else "there"
    opener = _context_opener(ctx)  # grounds the reply in what was actually said
    if intent == "buyer_criteria":
        # A cash buyer sent their box -> Henry locks them in + promises matching Memphis deals.
        subj = f"Re: {ctx.get('subject','your buy box')}"
        body = (
            f"Hey {who},\n\n"
            f"{opener}Appreciate you sending the box over, that's exactly what I needed. I've logged "
            f"your criteria on our end so the only deals you'll ever see from us are ones that "
            f"actually fit it. No noise.\n\n"
            f"We work Memphis direct to seller, so when something lands in your box, you'll get "
            f"it with the numbers, the condition, and the spread already laid out. First one or "
            f"two I'll walk you through personally so you know how we run.\n\n"
            f"Quick one so I tag your file right: proof of funds on file, and is there a max "
            f"door count or ZIP set you want me to hold to beyond what you sent?\n\n"
            f"Talk soon,\nHenry Hammond\nAcquisitions, Everlight Ventures"
        )
        return {"persona": "henry_hammond", "subject": subj, "body": body}
    if intent == "seller_warm":
        subj = f"Re: {ctx.get('subject','your property')}"
        body = (
            f"Hey {who},\n\n"
            f"{opener}Glad you wrote back. I'm Henry, I run the numbers side for our small Memphis team. "
            f"No pressure and no obligation on this, I'd just rather give you a real figure than "
            f"waste your time.\n\n"
            f"Two quick things and I can get you a cash number: roughly what kind of shape is the "
            f"place in right now, and is there a timeline that would actually work for you?\n\n"
            f"Whatever you tell me stays between us.\n\nHenry Hammond\nEverlight Ventures"
        )
        return {"persona": "henry_hammond", "subject": subj, "body": body}
    if intent == "question":
        subj = f"Re: {ctx.get('subject','your question')}"
        body = (f"Hey {who},\n\nGood question, happy to answer straight. "
                f"[Henry answers the specific question, then re-opens with a soft next step.]\n\n"
                f"Henry Hammond\nEverlight Ventures")
        return {"persona": "henry_hammond", "subject": subj, "body": body}
    # opt_out is handled by rex_stop_handler/eradication, never auto-replied with a pitch
    return {"persona": agent, "subject": f"Re: {ctx.get('subject','')}", "body": "[no auto-response for this intent]"}


def _gate_status() -> dict:
    halt = os.environ.get("WHOLESALE_OUTBOUND_HALT", "").strip() in {"1", "true", "TRUE", "yes"}
    addr_ok = True
    try:
        import tn_deal_tracker as t
        addr_ok = t.compliant_sender()[0]
    except Exception:
        addr_ok = False
    armed = (not halt) and addr_ok
    reason = "READY TO FIRE" if armed else (
        "halt active" if halt else "no CAN-SPAM address")
    return {"armed": armed, "halt": halt, "address_ok": addr_ok, "reason": reason}


def stage_draft(from_addr: str, who: str, subject: str, snippet: str, agent: str = "") -> dict:
    """AUTO: record the inbound to conversation memory, then generate the agent's response
    FROM the full conversation context (answers open questions, references facts, no repeats)
    and arm it as a gated draft. No asking."""
    intent = classify_intent(snippet + " " + subject)
    if intent == "opt_out":
        return {"staged": False, "reason": "opt_out -> eradication gate, no auto-reply"}
    if not agent:
        try:
            import inbox_router as ir
            agent = ir.classify_incoming(from_addr).get("agent") or "henry_hammond"
        except Exception:
            agent = "henry_hammond"
    # Stateful memory: record the inbound + pull the context the reply is built from.
    role = "buyer" if intent == "buyer_criteria" else "seller"
    ctx = {"who": who, "subject": subject}
    try:
        import conversation_memory as cm
        cm.record(from_addr, "in", snippet, name=who, subject=subject, role=role)
        ctx.update(cm.context_pack(from_addr))
        role = ctx.get("role") or role
    except Exception:
        pass
    # CHANNEL CHOICE: a seller choosing text/call (+ giving a number) is opt-in CONSENT.
    # Record it so future sends route via their chosen channel (channel_router.send).
    try:
        import channel_router as _cr
        _choice = _cr.detect_choice(snippet)
        if _choice:
            _cr.set_preference(from_addr, _choice["channel"], phone=_choice.get("phone") or "",
                               consent_text=snippet, source="reply")
            ctx["channel_chosen"] = _choice["channel"]
    except Exception:
        pass
    # LIVE negotiation: a counter triggers a real round-aware offer (shared engine).
    if intent == "counter":
        nb = _negotiation_block(from_addr, role, snippet)
        if nb:
            ctx["negotiation"] = nb
    resp = generate_response(agent, intent, ctx)
    gate = _gate_status()
    draft = {
        "id": hashlib.md5(f"{from_addr}|{subject}".encode()).hexdigest()[:12],
        "to": from_addr, "to_name": who, "intent": intent,
        "persona": resp["persona"], "subject": resp["subject"], "body": resp["body"],
        "engine": resp.get("engine", "template"),
        "trigger_snippet": (snippet or "")[:200],
        "status": "armed" if gate["armed"] else "staged_until_unblocked",
        "gate": gate, "generated_at": _now(),
    }
    DRAFTS.mkdir(parents=True, exist_ok=True)
    (DRAFTS / f"{draft['id']}.json").write_text(json.dumps(draft, indent=2))
    return {"staged": True, "draft_id": draft["id"], "persona": resp["persona"],
            "intent": intent, "status": draft["status"]}


def list_drafts() -> list:
    if not DRAFTS.exists():
        return []
    return [json.loads(p.read_text()) for p in sorted(DRAFTS.glob("*.json"))]


def fire_drafts(dry_run: bool = True) -> dict:
    gate = _gate_status()
    drafts = list_drafts()
    out = {"armed_drafts": len(drafts), "gate": gate, "dry_run": dry_run, "fired": 0, "would_fire": []}
    for tr in drafts:
        if tr.get("status") == "sent":
            continue
        out["would_fire"].append({"to": tr["to"], "persona": tr["persona"], "subject": tr["subject"]})
        if not dry_run and gate["armed"]:
            try:
                sys.path.insert(0, str(ROOT / "03_AUTOMATION_CORE/01_Scripts/content_tools"))
                from branded_mailer import send_branded_email
                r = send_branded_email(to=tr["to"], subject=tr["subject"], body=tr["body"],
                                       persona_id=tr["persona"], budget_category="vip_reply")
                if getattr(r, "ok", False) or (isinstance(r, dict) and r.get("ok")):
                    tr["status"] = "sent"; tr["sent_at"] = _now()
                    (DRAFTS / f"{tr['id']}.json").write_text(json.dumps(tr, indent=2))
                    out["fired"] += 1
                    try:  # remember what WE said -- the conversation stays whole
                        import conversation_memory as cm
                        cm.record(tr["to"], "out", tr["body"], persona=tr["persona"], subject=tr["subject"])
                    except Exception:
                        pass
            except Exception as e:
                out.setdefault("errors", []).append(f"{tr['id']}: {type(e).__name__}")
    return out


def demo() -> dict:
    """Stage drafts for the two real warm buyer replies sitting in the inbox."""
    staged = []
    staged.append(stage_draft("chris@midsouthhomebuyers.com", "Chris Ulander",
        "Re: Private deal flow for Memphis investors",
        "Nice to e-meet you. Send all leads to leads@midsouthhomebuyers.com. Here is our buying criteria", "henry_hammond"))
    staged.append(stage_draft("mj@jwbcompanies.com", "MJ",
        "RE: Off-Market Jacksonville Properties -- Cash Buyer Inventory",
        "Thanks for reaching out, happy to jump on a call. Here is our buying criteria, we want homes and infill lots", "henry_hammond"))
    return {"staged": staged, "gate": _gate_status()}


if __name__ == "__main__":
    if "--demo" in sys.argv:
        print(json.dumps(demo(), indent=2))
    elif "--list" in sys.argv:
        for t in list_drafts():
            print(f"[{t['status']}] -> {t['to']} ({t['persona']}, intent={t['intent']})  subj={t['subject']}")
    elif "--fire" in sys.argv:
        print(json.dumps(fire_drafts(dry_run="--run" not in sys.argv), indent=2))
    else:
        print(__doc__)
