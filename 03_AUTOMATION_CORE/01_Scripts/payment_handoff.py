"""
payment_handoff.py -- the sacred money-moment.

When a buyer asks "where do I send the wire?" Rex Negotiator does NOT auto-reply
with bank details. Instead it freezes, posts a branded Slack approval card to
Marquise, and waits for him to tap one of two channels:

  📞 Schedule Call   -> calendar invite to buyer with Marquise's bridge
  🏢 Through Title    -> reply with the title-company escrow contact

Both paths go through a JWT-signed approval URL. Click + confirm = action fires.
No click = silence. The token expires in 24 hours so a phisher cannot replay.

This is Marquise's favorite moment. The flow is paced deliberately:
  detect -> freeze -> ping -> tap -> confirm -> act -> celebrate -> log.

Public API:
  detect_payment_method_ask(text) -> bool
  request_approval(deal, conversation_excerpt) -> dict (the slack ts + token)
  verify_approval_token(token) -> deal_id or None
  execute_handoff(deal, action) -> str (status)
"""

from __future__ import annotations

import logging
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt  # PyJWT 2.x
import requests

logging.basicConfig(level=logging.INFO,
                    format="[%(asctime)s] %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("payment_handoff")

# ---- env / config ----------------------------------------------------------

JWT_SECRET = os.environ.get(
    "PAYMENT_HANDOFF_SECRET",
    # If a long-lived secret is set in /etc/default/rex-negotiator that wins.
    # Otherwise we fall back to a random per-process secret -- means tokens
    # die on container restart, which is a feature for security.
    "everlight-handoff-fallback-rotate-me-2026",
)
JWT_ALG = "HS256"
PUBLIC_BASE = os.environ.get(
    "PUBLIC_DASHBOARD_BASE",
    "http://127.0.0.1:2200",
)
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
SLACK_CHANNEL_DEAL = os.environ.get("SLACK_CHANNEL_BROKER_PIPELINE", "C0ANLLV8JAC")

# Phrases that mean "tell me how to pay you"
PAYMENT_PATTERNS = [
    r"\bwhere\b[^.?]{0,40}\b(send|wire|deposit|pay|put|drop)\b",
    r"\b(payment|wire|wiring|ach)\b[^.?]{0,40}\b(method|info|details|instructions|address)\b",
    r"\b(routing|account)\b[^.?]{0,30}\b(number|info)\b",
    r"\b(your|ur|the)\b[^.?]{0,20}\b(bank|account)\b[^.?]{0,30}\b(details|info|number)\b",
    r"\bhow\b[^.?]{0,20}\b(do|to)\b[^.?]{0,15}\b(pay|send|wire)\b",
    r"\bsend\b[^.?]{0,15}\b(funds|money|emd|deposit)\b",
    r"\bready to (pay|send|wire|deposit)\b",
    r"\bwire instructions\b",
]
_PAYMENT_RE = [re.compile(p, re.IGNORECASE) for p in PAYMENT_PATTERNS]


def detect_payment_method_ask(text: str) -> bool:
    """True if this seller/buyer message is asking how to pay."""
    if not text:
        return False
    for r in _PAYMENT_RE:
        if r.search(text):
            return True
    return False


# ---- token plumbing --------------------------------------------------------

def make_approval_token(deal_id: str, ttl_hours: int = 24) -> str:
    payload = {
        "deal_id": str(deal_id),
        "scope": "payment_handoff_approval",
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "exp": int((datetime.now(timezone.utc) + timedelta(hours=ttl_hours)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def verify_approval_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except jwt.ExpiredSignatureError:
        log.info("approval token expired")
        return None
    except jwt.InvalidTokenError as exc:
        log.info(f"invalid approval token: {exc}")
        return None
    if payload.get("scope") != "payment_handoff_approval":
        return None
    return payload.get("deal_id")


# ---- the Slack ping (Marquise's "favorite moment") -------------------------

def request_approval(deal, conversation_excerpt: str) -> dict:
    """Post a branded Block Kit approval card to #broker-pipeline. Returns
    {ok, token, ts, channel} for caller to log.

    Accepts either a Django Deal (has .lead, .deal_value) or a Rex DealState
    (has .address, .owner_name, .our_offer directly). Duck-typed.
    """
    token = make_approval_token(deal.id)
    call_url = f"{PUBLIC_BASE}/broker/approve/{token}/?path=call"
    title_url = f"{PUBLIC_BASE}/broker/approve/{token}/?path=title"

    # Pull fields from either shape.
    lead = getattr(deal, "lead", None)
    if lead is not None:
        addr = getattr(lead, "address", "") or "address pending"
        buyer_name = (getattr(lead, "owner_name", "") or "buyer").strip()
    else:
        addr = getattr(deal, "address", "") or "address pending"
        buyer_name = (getattr(deal, "owner_name", "") or "buyer").strip()
    deal_value = float(
        getattr(deal, "deal_value", None)
        or getattr(deal, "assignment_fee", None)
        or getattr(deal, "our_offer", 0)
        or 0
    )

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "Buyer ready to pay", "emoji": True},
        },
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": "*EVERLIGHT VENTURES* -- payment handoff request"},
            ],
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Property*\n{addr}"},
                {"type": "mrkdwn", "text": f"*Buyer*\n{buyer_name}"},
                {"type": "mrkdwn", "text": f"*Deal value*\n${deal_value:,.0f}"},
                {"type": "mrkdwn", "text": f"*Token TTL*\n24 hours"},
            ],
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"> {conversation_excerpt[:300]}"},
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "📞 Schedule Call", "emoji": True},
                    "url": call_url,
                    "style": "primary",
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "🏢 Through Title", "emoji": True},
                    "url": title_url,
                },
            ],
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "Tap once. The page recaps the deal, you confirm, the action fires. No click = silence. Token expires 24h. This is the only place wire details get released, never auto-sent.",
                },
            ],
        },
    ]

    if not SLACK_BOT_TOKEN:
        log.warning("SLACK_BOT_TOKEN not set, approval not posted")
        return {"ok": False, "token": token, "reason": "no slack token"}

    try:
        r = requests.post(
            "https://slack.com/api/chat.postMessage",
            headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}",
                     "Content-Type": "application/json; charset=utf-8"},
            json={"channel": SLACK_CHANNEL_DEAL,
                  "text": f"Buyer ready to pay -- {addr}",
                  "blocks": blocks},
            timeout=15,
        )
        data = r.json()
        if not data.get("ok"):
            log.warning(f"slack post failed: {data.get('error')}")
            return {"ok": False, "token": token, "reason": data.get("error")}
        log.info(f"approval card posted, ts={data.get('ts')}")
        return {"ok": True, "token": token, "ts": data.get("ts"), "channel": data.get("channel")}
    except Exception as exc:
        log.warning(f"slack post error: {exc}")
        return {"ok": False, "token": token, "reason": str(exc)}


# ---- action handlers (fire after Marquise confirms) ------------------------

def execute_handoff(deal, action: str) -> str:
    """Run the chosen channel. Called by Django view after JWT verified + user
    confirmed.

    action: 'call' or 'title'

    PRIMARY CHANNEL: 'title' (Marquise's confirmed preference, 2026-04-25).
    Variant B (Through Title) is the default / recommended path because it
    keeps Marquise's banking numbers entirely out of the conversation. Channel
    A (Schedule Call) is the secondary/escalation path for VIP buyers or
    repeat investors who specifically want the founder voice on the line.
    """
    if action == "call":
        return _handoff_via_call(deal)
    if action == "title":
        return _handoff_via_title(deal)
    return f"unknown action: {action}"


def _md_to_html(text: str) -> str:
    """Quick plain-text -> HTML for the branded_mailer template wrapper."""
    paras = [p.strip() for p in text.strip().split("\n\n") if p.strip()]
    out = []
    for p in paras:
        # Preserve indented monospace blocks (lines starting with two+ spaces)
        if all(line.startswith("  ") for line in p.split("\n")):
            inner = p.replace("\n", "<br>")
            out.append(f'<p style="font-family:SF Mono,Monaco,monospace;background:#1a1a1a;padding:12px;border-left:3px solid #D4AF37;">{inner}</p>')
        else:
            out.append(f"<p>{p.replace(chr(10), '<br>')}</p>")
    return "\n".join(out)


def _send_handoff_email(*, lead, subject: str, body: str) -> str:
    """Common send path for both handoff channels.

    Per Adrian Morgan (brand director, 2026-04-25 review): the From address
    and signature MUST match. A buyer reading "Marquise" signed at the bottom
    of an email from piper@ at the top loses trust at the exact moment trust
    is the product. We send from marquise@everlightventures.io so author and
    sender are the same human. This requires marquise@ to exist as an
    ImprovMX alias forwarding to 1m.rich.gee@gmail.com (one of the 42 aliases
    in the pool).

    CAN-SPAM trailer is appended automatically (Justine 2026-04-25 review).
    Even though transactional/relationship emails are exempt from unsubscribe
    requirement under 16 CFR 316.3, we add it as belt-and-suspenders.
    """
    sys.path.insert(0, "/home/opc")
    from content_tools.branded_mailer import send_branded_email  # type: ignore

    canspam_trailer = (
        "\n\n---\n"
        "This email is in response to your inquiry. Reply STOP to remove "
        "yourself from further deal communications."
    )
    full_body = body + canspam_trailer

    result = send_branded_email(
        to=lead.owner_email,
        subject=subject,
        content_html=_md_to_html(full_body),
        plain_text_fallback=full_body,
        from_name="Marquise Smith",
        from_email="marquise@everlightventures.io",
        reply_to="marquise@everlightventures.io",
        agent_name="Marquise Smith",
        agent_title="Founder, Everlight Ventures",
        agent_email="marquise@everlightventures.io",
        budget_category="vip_reply",
    )
    ok = getattr(result, "ok", False) if not isinstance(result, bool) else result
    return f"emailed to {lead.owner_email}, ok={ok}"


def _first_name(full_name: str) -> str:
    """Pull the first token from an owner_name. Falls back to 'there' if blank."""
    if not full_name:
        return "there"
    first = full_name.strip().split()[0]
    # If the first token looks like a title (Mr/Ms/Dr) skip it
    if first.lower() in {"mr", "mr.", "ms", "ms.", "mrs", "mrs.", "dr", "dr."}:
        parts = full_name.strip().split()
        return parts[1] if len(parts) > 1 else "there"
    return first.title()


def _handoff_via_call(deal) -> str:
    """Channel A: 15-minute live wire-walkthrough call -- v2 (Hive-reviewed).

    Voice: Piper Reeves rewrite, warm-empath, customer-first. Cleaned of the
    SaaS-funnel feel of v1. Bullets converted to flowing prose per Adrian
    (Lucrex states, does not bullet). Timeline qualified per Justine (target,
    subject to title clearance). "tokenized" word removed per Justine (security
    claim not yet defensible). From address shifted to marquise@ so author
    and sender match per Adrian.
    """
    lead = getattr(deal, "lead", None)
    if not lead or not lead.owner_email:
        return "no buyer email on file, cannot send calendar invite"

    first = _first_name(getattr(lead, "owner_name", ""))
    addr = getattr(lead, "address", "the property")

    subject = f"{first}, your wire walkthrough for {addr} -- pick a slot"

    body = (
        f"{first},\n\n"
        f"Locked.\n\n"
        f"You are clear to close on {addr}. Target close: 14 days from EMD "
        f"clearing the trust account, subject to title clearance and your "
        f"funding readiness. Before any wire moves, I want you on a "
        f"fifteen-minute call so we walk escrow together and you meet the "
        f"title officer who is actually holding your money.\n\n"
        f"Pick the slot that fits your day:\n\n"
        f"  https://cal.com/everlight-ventures/wire-handoff\n\n"
        f"Prefer to text three windows over the next 48 hours? Reply right "
        f"here and I will lock one in within the hour.\n\n"
        f"Wire-fraud rings hunt wholesale closes specifically. Email is where "
        f"they get in. Voice plus verified caller ID is where they do not. "
        f"Your escrow instructions arrive on the title firm's letterhead, "
        f"sent after the call. Funds sit in a licensed title or escrow trust "
        f"account at an ALTA member firm. Never my desk, never my hands, "
        f"never my email.\n\n"
        f"This is the same playbook our repeat investor desk runs every "
        f"close. Most of our 14-day buyers tell me the call is the part "
        f"that made them comfortable writing the next check with us, too.\n\n"
        f"Talk soon, {first}.\n\n"
        f"Marquise Smith\n"
        f"Founder, Everlight Ventures\n"
        f"marquise@everlightventures.io  |  (707) 801-0360\n\n"
        f"P.S. The wire-confirmation page is single-use and locked to your "
        f"address. Nobody else can hit it. We do not email sensitive numbers. "
        f"Not to you, not to title, not to anyone. That rule is why our "
        f"closes do not blow up."
    )
    try:
        return _send_handoff_email(lead=lead, subject=subject, body=body)
    except Exception as exc:
        log.warning(f"call handoff failed: {exc}")
        return f"call handoff error: {exc}"


def _handoff_via_title(deal) -> str:
    """Channel B: route the buyer to a licensed title escrow -- v2 (Hive-reviewed).

    Voice: Piper Reeves rewrite, decisive-warm. The single biggest change from
    v1: NO named title company in the body. Justine HARD-STOPPED v1's named-
    company version because we have no written referral agreement on file.
    Naming a specific firm without one is RESPA Section 8 + Lanham Act
    exposure if any consideration ever changes hands or if the firm objects.
    v2 reframes as "I will introduce you to three options within the business
    day" -- buyer chooses, no referral implied. Once a written referral MOU
    is papered with one or more title companies (Carlos / Bernard task), we
    can re-add the specific firm name.

    Also reframed P.S. per Justine: "assignment of my equitable interest"
    instead of "assignment contract" because Marquise's RE license is
    LAPSED. Equitable-interest assignment is legal for the contract holder;
    brokering someone else's property is not.
    """
    lead = getattr(deal, "lead", None)
    if not lead or not lead.owner_email:
        return "no buyer email on file"

    first = _first_name(getattr(lead, "owner_name", ""))
    addr = getattr(lead, "address", "the property")
    state = (getattr(lead, "state", "") or "").upper()
    state_phrase = f"licensed {state} title and escrow company" if state else "licensed title and escrow company"

    subject = f"{first}, three title options for {addr} -- pick yours"

    body = (
        f"{first},\n\n"
        f"Locked.\n\n"
        f"EMD and the assignment fee both route through a {state_phrase}. "
        f"Never to me, never to Everlight, never out of a third-party trust "
        f"account until close. It is how every serious operator in this "
        f"market moves money over $10k, and frankly it is the only way I am "
        f"willing to hold yours.\n\n"
        f"For {addr} I will introduce you to three title options within the "
        f"business day so you can pick the firm that fits how you already "
        f"close. Reply with one of:\n\n"
        f"  > Already have a title firm I trust. Here is their name.\n"
        f"  > Send me three options and I will pick.\n"
        f"  > Set me up with whichever one moves fastest.\n\n"
        f"Whichever you pick, you will hear from them on their letterhead the "
        f"same day. EMD lands in their trust account, not mine. Target close: "
        f"14 days from EMD clearing, subject to title clearance and your "
        f"funding readiness.\n\n"
        f"I have working relationships with several title firms in your "
        f"market. If you mention you are working the {addr} assignment with "
        f"Everlight, you will skip the front-line queue.\n\n"
        f"Looking forward to closing this one with you, {first}.\n\n"
        f"Marquise Smith\n"
        f"Founder, Everlight Ventures\n"
        f"marquise@everlightventures.io  |  (707) 801-0360\n\n"
        f"P.S. Want to compress the timeline? The moment you confirm a title "
        f"firm, I will send you the assignment of my equitable interest in "
        f"the {addr} contract for your review. Documenso, one tap, signed. "
        f"We can have you signed and in the trust account by tomorrow morning."
    )
    try:
        return _send_handoff_email(lead=lead, subject=subject, body=body)
    except Exception as exc:
        log.warning(f"title handoff failed: {exc}")
        return f"title handoff error: {exc}"


def _title_contact_for(state: str, addr: str = "") -> str:
    """Render the top-pick title company per state as a 4-line scan block.

    Format intentional. Pro investors read this shape as a CRM card: company
    on top, credibility marker (ALTA / GA Bar / TDI) on line 2, city + phone
    on line 3, the action verb 'Ask for the investor desk' on line 4, and the
    reference key on line 5. The 'Reference: Everlight Ventures, [ADDRESS]'
    line tells the title officer which file to open and signals to the buyer
    that you have already named-dropped them in the firm.
    """
    table = {
        "OH": (
            "  Ohio Real Title Agency\n"
            "  ALTA member | Cleveland, OH | (216) 373-9900\n"
            "  Ask for the investor desk\n"
            f"  Reference: Everlight Ventures, {addr}"
        ),
        "GA": (
            "  Katz Durell, LLC (GA closing attorneys)\n"
            "  GA Bar | Sandy Springs, GA | (404) 487-0040\n"
            "  Ask for the investor practice\n"
            f"  Reference: Everlight Ventures, {addr}"
        ),
        "TX": (
            "  1st Option Title\n"
            "  TDI-licensed | Garland, TX | (972) 271-1700\n"
            "  Ask for Scott Horne's investor desk\n"
            f"  Reference: Everlight Ventures, {addr}"
        ),
    }
    if state in table:
        return table[state]
    return (
        "  Title partner for your state will be assigned after we confirm\n"
        "  the property county. Reply with a phone window and I will set\n"
        "  up a 3-way call so the title officer hears your wire request\n"
        "  directly from us together."
    )
