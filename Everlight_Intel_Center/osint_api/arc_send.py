"""
arc_send.py -- thin wrapper that fires the next email in a deal arc.

Called by:
  - inbound_watch_daemon.py / phone_imap_poller.py when a counterparty replies
  - intel deal launch CLI when kicking off a fresh deal
  - hive_deal_orchestrator.py when polling deal state and finding stale stage

Architecture:
  - Each arc step is a function that takes (deal_key, **ctx) and returns dict
    {ok, message_id, next_stage}
  - Arc state lives in deal_execution_log (last event for this deal_key)
  - Counterparty addresses + names live in deal_meta.json (per-deal config)

Stage flow (for a normal arc):
  m1_intro -> m3_open -> m5_meet -> m7_contract -> m8_emd -> c1_pitch ->
  c3_meet -> c4_assignment -> c5_settlement_preview -> t2_close

The watcher classifies inbound replies (counter / accept / question / STOP)
and chooses which next stage to fire.
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

ROOT = Path("/mnt/sdcard/AA_MY_DRIVE")
DEALS_DIR = ROOT / "09_DASHBOARD" / "reports" / "deals"

# Make imports work
sys.path.insert(0, str(ROOT / "03_AUTOMATION_CORE" / "01_Scripts" / "content_tools"))
sys.path.insert(0, str(ROOT / "01_BUSINESSES" / "Everlight_Ventures" / "Wholesale" / "audit"))
sys.path.insert(0, str(ROOT / "Everlight_Intel_Center"))

from branded_mailer import send_branded_email  # noqa: E402
from deal_execution_log import log_event, deal_history  # noqa: E402
from osint_api.voice_extractor import load_agent  # noqa: E402

OPERATOR_EMAIL = "1m.rich.gee@gmail.com"

# ---------- helpers ----------

HYPHEN_OK = {"mid-south", "self-help", "co-op"}
def strip_hyphens(text: str) -> str:
    out = text.replace("--", ",").replace("—", ",")
    def repl(m):
        a, b = m.group(1), m.group(2)
        if a.isdigit() and b.isdigit(): return m.group(0)
        if f"{a.lower()}-{b.lower()}" in HYPHEN_OK: return m.group(0)
        return f"{a} {b}"
    return re.sub(r"\b(\w+)-(\w+)\b", repl, out)


def load_deal_meta(deal_key: str) -> dict:
    """Load per-deal config from deal_meta.json or fall back to defaults."""
    meta_path = DEALS_DIR / deal_key / "deal_meta.json"
    if meta_path.exists():
        return json.loads(meta_path.read_text())
    # Sane defaults for the 1536 S Third reference deal
    return {
        "deal_key": deal_key,
        "property_address": "1536 S THIRD ST, MEMPHIS, TN",
        "parcel_id": "035093 00032",
        "seller_name": "Mikal L. Hakeem",
        "seller_email": "mhakeem@timemphis.org",
        "buyer_name": "Chris Ulander",
        "buyer_email": "leads@midsouthhomebuyers.com",
        "opening_to_seller": 6500,
        "final_to_seller": 9500,
        "opening_to_buyer": 14500,
        "final_to_buyer": 13090,
        "emd_usd": 250,
        "gfad_usd": 1000,
        "inspection_days": 14,
        "test_mode": False,  # set true to redirect all sends to operator inbox
    }


def write_deal_meta(deal_key: str, meta: dict) -> None:
    DEALS_DIR.mkdir(parents=True, exist_ok=True)
    (DEALS_DIR / deal_key).mkdir(parents=True, exist_ok=True)
    (DEALS_DIR / deal_key / "deal_meta.json").write_text(json.dumps(meta, indent=2))


def _send(meta: dict, subject: str, body_text: str, alias: str,
          recip_real: str, recip_name: str, lead_type: str = "seller") -> dict:
    """Send via branded_mailer with arc tagging. Test mode redirects to operator inbox."""
    body_text = strip_hyphens(body_text)
    body_html = "<p>" + body_text.replace("\n\n", "</p><p>").replace("\n", "<br>") + "</p>"

    # Test-mode redirect
    real_to = recip_real
    if meta.get("test_mode"):
        body_html = (
            f'<p style="background:#fff5d6;border-left:4px solid #d4a843;padding:12px;'
            f'margin-bottom:18px;font-size:.9rem;color:#5a4400;">'
            f'<strong>[TEST MODE]</strong> Real send: from {alias} to {recip_real} ({recip_name}). '
            f'Redirected to operator inbox for testing.</p>' + body_html
        )
        real_to = OPERATOR_EMAIL

    voice = load_agent({
        "marquise@everlightventures.io": "marquise_reed_acquisitions",
        "hammer@everlightventures.io": "marquise_reed_acquisitions",  # fallback until hammer firmware exists
    }.get(alias, "marquise_reed_acquisitions"))

    sender_name = "Marquise Reed" if "marquise" in alias else "Hammer Knox"
    sender_title = ("Acquisitions Lead, Memphis / West Tennessee"
                    if "marquise" in alias
                    else "Deal Closer, Buyer Side")

    res = send_branded_email(
        to=real_to, subject=subject, content_html=body_html, title=subject,
        from_name=sender_name, from_email=alias, reply_to=alias,
        agent_name=sender_name, agent_title=sender_title, agent_email=alias,
        budget_category="vip_reply", recipient_state="TN",
        lead_type=lead_type, state_disclaimer=False,
    )
    return {"ok": res.ok, "message_id": getattr(res, "message_id", ""), "error": res.error or ""}


# ---------- arc steps ----------

def m1_intro(deal_key: str) -> dict:
    """Marquise cold intro to seller, OSINT-tailored."""
    m = load_deal_meta(deal_key)
    subject = f"About {m['property_address'].split(',')[0]}, Memphis"
    body = f"""Hi {m['seller_name'].split()[0]},

Investor to investor here, no fluff. Pulled the deed history on {m['property_address'].split(',')[0]} and the pattern reads like portfolio activity.

Marquise Reed with Everlight Ventures, small Memphis group that buys properties direct from owners. No agents, no fees on your side.

Worth a quick conversation? Just reply with a time that works. Email is fine too. If you're not selling, reply STOP and I'm gone.

Marquise Reed
Acquisitions Lead, Memphis / West Tennessee
Everlight Ventures
marquise@everlightventures.io"""
    out = _send(m, subject, body, "marquise@everlightventures.io",
                m["seller_email"], m["seller_name"], "seller")
    if out["ok"]:
        log_event(deal_key=deal_key, event="email_sent",
                  actor="Marquise Reed",
                  counterparty=f"{m['seller_name']} <{m['seller_email']}>",
                  artifact_ref=f"resend:{out['message_id']}",
                  notes="M1 cold intro (OSINT tailored)")
    return out


def m3_open(deal_key: str) -> dict:
    """Marquise opens at low number after seller asks for one."""
    m = load_deal_meta(deal_key)
    subject = f"Cash offer for {m['property_address'].split(',')[0]}, opening number"
    body = f"""Hi {m['seller_name'].split()[0]},

Glad to talk numbers.

Where I'm starting:
  ◆ Purchase price: ${m['opening_to_seller']:,} cash
  ◆ Earnest money deposit: ${m['emd_usd']} into Mid South Title escrow within 3 business days of signed PSA
  ◆ Inspection period: {m['inspection_days']} days from contract
  ◆ Back property tax + penalties: handled at the title firm out of OUR side at closing
  ◆ Target close: {m['inspection_days']} days from PSA effective date

I'll be honest, that's our opening, not our last. Tell me what number you'd take and we'll see how close we can get.

Marquise Reed
Acquisitions Lead, Memphis / West Tennessee
Everlight Ventures
marquise@everlightventures.io"""
    out = _send(m, subject, body, "marquise@everlightventures.io",
                m["seller_email"], m["seller_name"], "seller")
    if out["ok"]:
        log_event(deal_key=deal_key, event="email_sent", actor="Marquise Reed",
                  counterparty=f"{m['seller_name']} <{m['seller_email']}>",
                  artifact_ref=f"resend:{out['message_id']}",
                  amount_usd=m["opening_to_seller"],
                  notes=f"M3 opening offer ${m['opening_to_seller']:,}")
    return out


def _seller_round_offer(m: dict, round_n: int) -> int:
    """Compute the offer amount for round 1/2/3.
    Round 1 = opening (low). Round 3 = final target. Round 2 = midpoint.
    """
    opening = int(m["opening_to_seller"])
    final = int(m["final_to_seller"])
    if round_n <= 1: return opening
    if round_n >= 3: return final
    return round((opening + final) / 2)


def m3_open_replaced(deal_key: str) -> dict:  # kept for backward CLI compat, unused
    return m_negotiate_seller(deal_key, round_n=1)


def m_negotiate_seller(deal_key: str, round_n: int = 1, counter_amount: int = 0) -> dict:
    """Marquise sends round-N negotiation offer.
    Round 1 = opening, Round 2 = midpoint, Round 3 = final.
    Each round logs as M{2*round_n+1} (M3, M5, M7) for backwards-compat with status parsing.
    """
    m = load_deal_meta(deal_key)
    offer = _seller_round_offer(m, round_n)
    final = int(m["final_to_seller"])
    opening = int(m["opening_to_seller"])
    target_close = (datetime.now() + timedelta(days=m["inspection_days"])).strftime("%B %d, %Y")
    addr_short = m['property_address'].split(',')[0]

    if round_n == 1:
        subject = f"Cash offer for {addr_short}, opening number"
        intro = "Glad to talk numbers."
        body_mid = (
            f"Where I'm starting:\n"
            f"  ◆ Purchase price: ${offer:,} cash\n"
            f"  ◆ Earnest money deposit: ${m['emd_usd']} into Mid South Title escrow within 3 business days of signed PSA\n"
            f"  ◆ Inspection period: {m['inspection_days']} days from contract\n"
            f"  ◆ Back property tax + penalties: handled at the title firm out of OUR side at closing\n"
            f"  ◆ Target close: {m['inspection_days']} days from PSA effective date\n\n"
            "I'll be honest, that's our opening, not our last. Tell me what number you'd take and we'll see how close we can get."
        )
    elif round_n == 2:
        subject = f"Re: cash offer for {addr_short}, working toward your number"
        intro = "Heard you. Let me see what I can do."
        body_mid = (
            f"I can stretch to ${offer:,} cash{f' (you came in at ${counter_amount:,})' if counter_amount > 0 else ''}. That's already ${offer - opening:,} above where I started.\n\n"
            "Here's what doesn't change:\n"
            f"  ◆ Earnest money: ${m['emd_usd']} to Mid South Title escrow within 3 business days\n"
            f"  ◆ DD period: {m['inspection_days']} days\n"
            "  ◆ Back property tax: handled at the title firm out of our side\n"
            f"  ◆ Target close: on or before {target_close}\n\n"
            "If you can come down to meet me here, I'll send the paperwork today. Otherwise let me know what you need and I'll see if there's room for one more pass."
        )
    else:  # round 3 = FINAL
        subject = f"Final offer for {addr_short}: ${offer:,}"
        intro = "Last pass on this one."
        body_mid = (
            f"Final number: ${offer:,} cash{f' (you came in at ${counter_amount:,}, we were at ${opening:,} to start)' if counter_amount > 0 else ''}.\n\n"
            f"At ${offer:,} I'm at the wall. Below this the deal doesn't pencil for our cash buyer. I get it if it's not your number, no hard feelings.\n\n"
            "Same terms as before:\n"
            f"  ◆ Earnest money: ${m['emd_usd']} to Mid South Title escrow within 3 business days\n"
            f"  ◆ DD period: {m['inspection_days']} days\n"
            "  ◆ Back property tax: handled at the title firm out of our side\n"
            f"  ◆ Target close: on or before {target_close}\n\n"
            "Reply yes and I'll send the contract package over today. Otherwise I'll move on with no hard feelings."
        )

    body = f"""Hi {m['seller_name'].split()[0]},

{intro}

{body_mid}

Marquise Reed
Acquisitions Lead, Memphis / West Tennessee
Everlight Ventures
marquise@everlightventures.io"""

    out = _send(m, subject, body, "marquise@everlightventures.io",
                m["seller_email"], m["seller_name"], "seller")
    stage_label = {1: "M3", 2: "M5", 3: "M7"}[round_n]
    if out["ok"]:
        log_event(deal_key=deal_key, event="email_sent", actor="Marquise Reed",
                  counterparty=f"{m['seller_name']} <{m['seller_email']}>",
                  artifact_ref=f"resend:{out['message_id']}",
                  amount_usd=offer,
                  notes=f"{stage_label} negotiation round {round_n} offer ${offer:,}")
    out["round_n"] = round_n
    out["offer"] = offer
    return out


def m3_open(deal_key: str) -> dict:
    """Round 1 (opening). Backwards-compat alias."""
    return m_negotiate_seller(deal_key, round_n=1)


def m5_meet(deal_key: str, counter_amount: int = 0) -> dict:
    """Round 2 (meet). Backwards-compat alias."""
    return m_negotiate_seller(deal_key, round_n=2, counter_amount=counter_amount)


def m7_final(deal_key: str, counter_amount: int = 0) -> dict:
    """Round 3 (final offer). Last pass before walking away."""
    return m_negotiate_seller(deal_key, round_n=3, counter_amount=counter_amount)


def m_question_response(deal_key: str, question_text: str = "") -> dict:
    """Acknowledge a seller question without advancing the round counter.
    Buys us time + makes them feel heard before the next negotiation step."""
    m = load_deal_meta(deal_key)
    addr_short = m['property_address'].split(',')[0]
    subject = f"Re: {addr_short} — quick answer + next step"
    body = f"""Hi {m['seller_name'].split()[0]},

Good question. Quick answer: I'll cover that detail in the offer paperwork (or sooner if it's a deal-breaker, just let me know).

The short version: we're a small Memphis cash buyer. Mid South Title handles the closing. You don't write a check for back tax. Inspection period is {m['inspection_days']} days. Standard wholesale flow you may have seen before.

Want me to send the number now or do you want to talk through anything else first?

Marquise Reed
Acquisitions Lead, Memphis / West Tennessee
Everlight Ventures
marquise@everlightventures.io"""
    out = _send(m, subject, body, "marquise@everlightventures.io",
                m["seller_email"], m["seller_name"], "seller")
    if out["ok"]:
        log_event(deal_key=deal_key, event="email_sent", actor="Marquise Reed",
                  counterparty=f"{m['seller_name']} <{m['seller_email']}>",
                  artifact_ref=f"resend:{out['message_id']}",
                  notes="Q&A response (does NOT advance round counter)")
    return out


# ====================================================================
# C-ARC (BUYER SIDE -- Hammer Knox to Chris @ Mid South Homebuyers)
# Mirror of seller arc but anchor HIGH instead of LOW.
# ====================================================================

def _buyer_round_offer(m: dict, round_n: int) -> int:
    """Round 1 = anchor near our target with small premium. Round 3 = our final target.

    PREMIUM ANCHOR DOCTRINE (memory: feedback_premium_anchor_max_concession.md):
    Total spread opening-to-final must be SMALL ($300-500 typical, never $1000+).
    Chris is institutional capital and respects sellers who don't fold. Big concessions
    train him to ask for bigger ones next deal. Small spreads protect brand + margin.

    If deal_meta.opening_to_buyer would imply a wider spread than max_buyer_spread
    (default $500), we cap it. Prevents legacy meta from leaking the old wide-walk.
    """
    final = int(m.get("final_to_buyer", 13090))
    raw_high = int(m.get("opening_to_buyer", final + 400))
    MAX_BUYER_SPREAD = int(m.get("max_buyer_spread", 500))
    high = min(raw_high, final + MAX_BUYER_SPREAD)
    if round_n <= 1: return high
    if round_n >= 3: return final
    return round((high + final) / 2)


def c_negotiate_buyer(deal_key: str, round_n: int = 1, counter_amount: int = 0) -> dict:
    """Hammer sends round-N pitch to Chris. Anchor high, walk down toward final target."""
    m = load_deal_meta(deal_key)
    offer = _buyer_round_offer(m, round_n)
    target_close = (datetime.now() + timedelta(days=m["inspection_days"])).strftime("%B %d, %Y")
    addr_short = m['property_address'].split(',')[0]

    if round_n == 1:
        subject = f"Memphis SFR for your buy-box, {addr_short}"
        intro_body = (
            f"Got one for your Memphis box. Single family, owner under contract today, ready to assign.\n\n"
            f"Property: {m['property_address']}, parcel {m.get('parcel_id', '')}\n"
            f"Owner: {m.get('seller_name')}, signed PSA at ${m['final_to_seller']:,}\n\n"
            f"Where I'm starting: ${offer:,} all in, includes ${m['final_to_seller']:,} to seller + ${offer - m['final_to_seller']:,} assignment fee.\n"
            f"GFAD: ${m.get('gfad_usd', 1000)} to Mid South Title escrow within 48 hrs of signing.\n"
            f"DD period: {m['inspection_days']} days. Target close: on or before {target_close}.\n\n"
            "I know you're going to push back. Send me a number, otherwise I'll take it and the assignment goes out today."
        )
    elif round_n == 2:
        subject = f"Re: {addr_short}, working with you on the spread"
        intro_body = (
            f"Heard you. Can land at ${offer:,} all in.\n\n"
            f"That's ${m.get('opening_to_buyer', 14500) - offer:,} below where I started{f' (you came in at ${counter_amount:,})' if counter_amount > 0 else ''}.\n"
            "Same flow you and I have run before. Mid South Title escrows everything, GFAD hits 48 hrs after you sign, balance at close.\n\n"
            "If that works, reply yes and the assignment goes out today."
        )
    else:  # round 3 = final
        subject = f"Final on {addr_short}: ${offer:,}"
        intro_body = (
            f"Last pass.\n\n"
            f"${offer:,} all in. Below this we eat the seller risk we already absorbed plus the cycle time. ${m.get('opening_to_buyer', 14500) - offer:,} below where I opened, ${offer - m['final_to_seller']:,} margin for us.\n\n"
            f"GFAD ${m.get('gfad_usd', 1000)}, {m['inspection_days']} day DD, close on or before {target_close}.\n\n"
            "Yes or no, I'm fine either way. If no I package it for the next buyer in line."
        )

    body = f"""Chris,

{intro_body}

Hammer Knox
Deal Closer, Buyer Side
Everlight Ventures
hammer@everlightventures.io"""

    out = _send(m, subject, body, "hammer@everlightventures.io",
                m["buyer_email"], m["buyer_name"], "buyer")
    stage_label = {1: "C1", 2: "C3", 3: "C5"}[round_n]
    if out["ok"]:
        log_event(deal_key=deal_key, event="email_sent", actor="Hammer Knox",
                  counterparty=f"{m['buyer_name']} <{m['buyer_email']}>",
                  artifact_ref=f"resend:{out['message_id']}",
                  amount_usd=offer,
                  notes=f"{stage_label} buyer negotiation round {round_n} offer ${offer:,}")
    out["round_n"] = round_n
    out["offer"] = offer
    return out


def c1_pitch(deal_key: str) -> dict:
    """Round 1 buyer pitch (high anchor). Backwards-compat alias."""
    return c_negotiate_buyer(deal_key, round_n=1)


def c3_meet(deal_key: str, counter_amount: int = 0) -> dict:
    """Round 2 buyer meet. Backwards-compat alias."""
    return c_negotiate_buyer(deal_key, round_n=2, counter_amount=counter_amount)


def c5_final(deal_key: str, counter_amount: int = 0) -> dict:
    """Round 3 buyer final. Backwards-compat alias."""
    return c_negotiate_buyer(deal_key, round_n=3, counter_amount=counter_amount)


def c_assignment(deal_key: str) -> dict:
    """Hammer sends Chris the assignment package + GFAD wire instructions."""
    from osint_api.esign_server import make_token

    m = load_deal_meta(deal_key)
    chris_pays = int(m.get("final_to_buyer", 13090))
    final_to_seller = int(m.get("final_to_seller", 9500))
    assignment_fee = chris_pays - final_to_seller
    gfad = int(m.get("gfad_usd", 1000))
    target_close = (datetime.now() + timedelta(days=m["inspection_days"])).strftime("%B %d, %Y")

    token = make_token(deal_key, "04_Assignment_Agreement_Chris", m["buyer_email"], m["buyer_name"], ttl_hours=168)
    sign_url = f"http://127.0.0.1:2302/sign/{token}"

    subject = f"Assignment package for {m['property_address'].split(',')[0]}, ${chris_pays:,} agreed"
    body = f"""Chris,

Confirming ${chris_pays:,}. Assignment package ready to sign.

  Sign here: {sign_url}

Once you sign:
  T+0   Assignment Agreement signed.
  T+2   You wire ${gfad:,} GFAD to Mid South Title escrow.
  T+0..14   DD clock. Either side walks on material defect.
  T+14  Close on or before {target_close}.
        You wire balance ${chris_pays - gfad:,} (plus closing costs).
        Title firm disburses: ${final_to_seller:,} to seller, ${assignment_fee:,} to us, plus back tax + recording.
        Deed records to Mid South Homebuyers, LLC.

Settlement statement preview lands 24 hrs before close.

Hammer Knox
Deal Closer, Buyer Side
Everlight Ventures
hammer@everlightventures.io"""
    out = _send(m, subject, body, "hammer@everlightventures.io",
                m["buyer_email"], m["buyer_name"], "buyer")
    if out["ok"]:
        log_event(deal_key=deal_key, event="doc_delivered", actor="Hammer Knox",
                  counterparty=f"{m['buyer_name']} <{m['buyer_email']}>",
                  artifact_ref=f"resend:{out['message_id']}",
                  notes="C7 assignment package delivered (esign token)",
                  statute_ref="TN_ASSIGNMENT")
    return out


def m7_contract(deal_key: str) -> dict:
    """Marquise sends contract package with esign URLs."""
    from osint_api.esign_server import make_token

    m = load_deal_meta(deal_key)
    deal_url = f"http://127.0.0.1:2200/reports/deals/{deal_key}/"

    # Generate signing tokens for the 3 seller-side docs
    docs = ["01_PSA", "02_Schedule_A_TN_SB909", "03_EMD_Wire_Acknowledgment"]
    signing_lines = []
    for doc in docs:
        token = make_token(deal_key, doc, m["seller_email"], m["seller_name"], ttl_hours=168)
        signing_lines.append(f"  {doc}: http://127.0.0.1:2302/sign/{token}")

    target_close = (datetime.now() + timedelta(days=m["inspection_days"])).strftime("%B %d, %Y")

    subject = f"3 documents to sign for {m['property_address'].split(',')[0]}"
    body = f"""Hi {m['seller_name'].split()[0]},

Three documents below, all in one DocuSign-style envelope. Click each link to sign.

{chr(10).join(signing_lines)}

Once all three are signed, I wire ${m['emd_usd']} EMD to Mid South Title within 3 business days. Title firm pulls preliminary title and we begin the {m['inspection_days']} day due diligence clock. If anything material comes up, EMD refunds and we both walk. Otherwise we close on or before {target_close}.

Reply if anything's unclear.

Marquise Reed
Acquisitions Lead, Memphis / West Tennessee
Everlight Ventures
marquise@everlightventures.io"""
    out = _send(m, subject, body, "marquise@everlightventures.io",
                m["seller_email"], m["seller_name"], "seller")
    if out["ok"]:
        log_event(deal_key=deal_key, event="doc_delivered", actor="Marquise Reed",
                  counterparty=f"{m['seller_name']} <{m['seller_email']}>",
                  artifact_ref=f"resend:{out['message_id']}",
                  notes="M7 contract package delivered (3 esign tokens)",
                  statute_ref="TN_SB909")
    return out


# ---------- classifier (used by inbound watcher) ----------

ACCEPT_SIGNALS = re.compile(r"\b(yes|agreed|works|deal|sounds good|let'?s do it|sign(ed)?|i'?m in|that works)\b", re.I)
# COUNTER signals: split into two patterns -- a money pattern (which can't use \b before $)
# and a phrase pattern (uses \b normally).
COUNTER_MONEY = re.compile(r"\$\s*[\d,]+", re.I)
COUNTER_SIGNALS = re.compile(
    r"\b(counter|how about|i'?d take|i would take|i'?ll take|won'?t go below|need more|but i)\b", re.I)
QUESTION_SIGNALS = re.compile(r"\?|when|where|what|who|how|why", re.I)
STOP_SIGNALS = re.compile(r"\b(stop|unsubscribe|remove|don'?t contact|leave me alone|not interested)\b", re.I)


def classify_reply(body: str) -> str:
    """Classify an inbound reply into one of: accept, counter, question, stop, neutral."""
    if STOP_SIGNALS.search(body):
        return "stop"
    if ACCEPT_SIGNALS.search(body):
        return "accept"
    if COUNTER_SIGNALS.search(body) or COUNTER_MONEY.search(body):
        return "counter"
    if QUESTION_SIGNALS.search(body):
        return "question"
    return "neutral"


DOUBLE_EMAIL_WINDOW_MIN = 30  # Minutes -- if 2+ inbounds within this window, treat as one


def _recent_inbound_count(deal_key: str, minutes: int = DOUBLE_EMAIL_WINDOW_MIN) -> int:
    """Count how many email_received events are in the last N minutes for this deal."""
    cutoff = (datetime.utcnow() - timedelta(minutes=minutes)).isoformat()
    n = 0
    for e in deal_history(deal_key):
        if e["event"] == "email_received" and e["ts"] > cutoff:
            n += 1
    return n


def next_step_for_seller(deal_key: str, last_stage: str, reply_class: str) -> Optional[str]:
    """Decide what to fire next based on prior stage + classifier.
    Supports 3 negotiation rounds before contract delivery.
    """
    if reply_class == "stop":
        return None  # halt arc

    # Question handling: at any negotiation stage, answer the question first WITHOUT
    # advancing the round counter. The next inbound after this should advance.
    if reply_class == "question" and last_stage in ("M1", "M3", "M5"):
        return "m_question_response"

    table = {
        # (last_stage, reply_class) : next_function
        # Cold intro -> opening
        ("M1", "neutral"):  "m3_open",
        ("M1", "counter"):  "m3_open",
        ("M1", "accept"):   "m3_open",
        # Opening -> round 2 or contract
        ("M3", "counter"):  "m5_meet",
        ("M3", "accept"):   "m7_contract",
        ("M3", "neutral"):  "m5_meet",   # re-engage with a meet
        # Round 2 -> round 3 or contract
        ("M5", "counter"):  "m7_final",  # was m5_meet again; now goes to final
        ("M5", "accept"):   "m7_contract",
        # Round 3 -> contract or done
        ("M7", "accept"):   "m7_contract",
        ("M7", "counter"):  None,  # hit our wall; escalate to operator
    }
    return table.get((last_stage, reply_class))


def next_step_for_buyer(deal_key: str, last_stage: str, reply_class: str) -> Optional[str]:
    """C-arc routing for the buyer side (Chris)."""
    if reply_class == "stop":
        return None
    if reply_class == "question" and last_stage in ("C1", "C3"):
        # Re-use seller Q&A response (could add buyer-specific later)
        return "m_question_response"
    table = {
        # (last_stage, reply_class) : next_function
        ("C1", "counter"):  "c3_meet",
        ("C1", "accept"):   "c_assignment",
        ("C1", "neutral"):  "c3_meet",
        ("C3", "counter"):  "c5_final",
        ("C3", "accept"):   "c_assignment",
        ("C5", "accept"):   "c_assignment",
        ("C5", "counter"):  None,  # walked away from us, escalate
    }
    return table.get((last_stage, reply_class))


def next_step(deal_key: str, last_stage: str, reply_class: str, role: str = "seller") -> Optional[str]:
    """Unified router: dispatches to seller or buyer state machine based on role."""
    if role == "buyer":
        return next_step_for_buyer(deal_key, last_stage, reply_class)
    return next_step_for_seller(deal_key, last_stage, reply_class)


def should_throttle_inbound(deal_key: str) -> bool:
    """Return True if we just sent something + got 2+ inbounds quickly (double-email).
    The poller can use this to combine inbounds + delay the next outbound."""
    return _recent_inbound_count(deal_key, minutes=DOUBLE_EMAIL_WINDOW_MIN) >= 2


def should_escalate(deal_key: str, last_stage: str, reply_class: str, role: str = "seller") -> bool:
    """Return True when nothing in the routing table fires AND it's not a STOP.
    Operator (Rich) gets a Slack ping to take over."""
    if reply_class == "stop":
        return False  # not an escalation, just a clean halt
    if next_step(deal_key, last_stage, reply_class, role) is None:
        return True
    return False


# ---------- public API ----------

ARC_FUNCTIONS = {
    "m1_intro": m1_intro,
    "m3_open": m3_open,
    "m5_meet": m5_meet,
    "m7_final": m7_final,
    "m7_contract": m7_contract,
    "m_question_response": m_question_response,
    "c1_pitch": c1_pitch,
    "c3_meet": c3_meet,
    "c5_final": c5_final,
    "c_assignment": c_assignment,
}


def fire_step(deal_key: str, step: str, **kwargs) -> dict:
    """Fire a named arc step."""
    fn = ARC_FUNCTIONS.get(step)
    if not fn:
        return {"ok": False, "error": f"unknown step: {step}"}
    return fn(deal_key, **kwargs)


def deal_status(deal_key: str) -> dict:
    """Return the current arc status for a deal."""
    events = deal_history(deal_key)
    last = events[-1] if events else None
    return {
        "deal_key": deal_key,
        "event_count": len(events),
        "last_event": last,
        "last_event_stage": _extract_stage(last) if last else None,
    }


def _extract_stage(event: dict) -> Optional[str]:
    """Pull stage label (M1/M3/M5/...) from event notes."""
    notes = event.get("notes", "") or ""
    m = re.search(r"\b(M\d|C\d)\b", notes)
    return m.group(1) if m else None


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd")

    p_fire = sp.add_parser("fire")
    p_fire.add_argument("deal_key")
    p_fire.add_argument("step", choices=list(ARC_FUNCTIONS.keys()))

    p_stat = sp.add_parser("status")
    p_stat.add_argument("deal_key")

    args = ap.parse_args()
    if args.cmd == "fire":
        print(json.dumps(fire_step(args.deal_key, args.step), indent=2))
    elif args.cmd == "status":
        print(json.dumps(deal_status(args.deal_key), indent=2, default=str))
    else:
        ap.print_help()
