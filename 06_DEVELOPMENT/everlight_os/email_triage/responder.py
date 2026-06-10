"""responder -- drafts a response to an inbound email based on its classifier
tag. Per Rich's halt-policy v2, opt_out replies get an immediate confirmation;
positive_reply gets a drafted next-step; question gets a flag for Rich.

This module produces the BODY + decision (auto_send / queue_for_approval).
The actual send is done via Resend in the daemon (so we can dry-run here).
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


def _bootstrap_env() -> None:
    if os.environ.get("LUCREX_ANTHROPIC_KEY") or os.environ.get("ANTHROPIC_API_KEY"):
        return
    p = Path("/AA_MY_DRIVE/.env")
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip().strip("'\""))


_bootstrap_env()

OPT_OUT_TEMPLATE = """Hi{name_part},

You've been removed from our outreach. We won't contact you again.

If this was a mistake or you ever change your mind, just reply with your
preferred channel and we'll route accordingly.

-- Everlight Ventures"""

LEGAL_THREAT_AUTOREPLY = """Hi{name_part},

Thanks for reaching out. We've removed all addresses associated with this
matter from our outreach immediately. No further contact will be made.

If there's documentation you need from us, please direct it to
legal@everlightventures.io and we will respond within 24 hours.

-- Everlight Ventures"""

POSITIVE_REPLY_DRAFT_HEADER = "[DRAFT for Rich's review -- positive_reply]"


def _name_from_sender(sender: str) -> str:
    """Extract a friendly name from "Name <email@x>" or just email. Returns
    empty string if no clear name."""
    if not sender:
        return ""
    if "<" in sender:
        name = sender.split("<", 1)[0].strip().strip('"').strip("'")
        return name if name else ""
    return ""


def draft(tag: str, sender: str, subject: str, body: str,
          confidence: float = 0.7) -> dict:
    """Returns:
      {
        action: 'auto_send' | 'queue_for_approval' | 'archive' | 'flag_only',
        reply_subject: <str or None>,
        reply_body: <str or None>,
        reason: <str>,
      }
    """
    name = _name_from_sender(sender)
    name_part = f" {name}" if name else ""

    if tag == "opt_out":
        return {
            "action": "auto_send",
            "reply_subject": f"Re: {subject}" if subject else "Removed from outreach",
            "reply_body": OPT_OUT_TEMPLATE.format(name_part=name_part),
            "reason": "opt_out -- immediate confirmation, then DNC",
        }

    if tag == "legal_threat":
        return {
            "action": "queue_for_approval",  # Rich must see legal threats
            "reply_subject": f"Re: {subject}" if subject else "Removed from outreach",
            "reply_body": LEGAL_THREAT_AUTOREPLY.format(name_part=name_part),
            "reason": ("legal_threat -- auto-DNC, draft a defensible reply, "
                       "but DO NOT send without Rich + legal review"),
        }

    if tag == "positive_reply" and confidence >= 0.85:
        return {
            "action": "queue_for_approval",  # even high-confidence positive needs Rich
            "reply_subject": f"Re: {subject}",
            "reply_body": _draft_positive_reply(subject, body, name_part),
            "reason": "positive_reply -- LLM-drafted next-step, Rich approves before send",
        }

    if tag == "question":
        return {
            "action": "queue_for_approval",
            "reply_subject": f"Re: {subject}",
            "reply_body": _draft_question_reply(subject, body, name_part),
            "reason": "question -- LLM-drafted clarifier, Rich approves before send",
        }

    if tag == "bounce":
        return {
            "action": "flag_only",
            "reply_subject": None,
            "reply_body": None,
            "reason": "bounce -- log + flag sender as suspicious, no reply",
        }

    if tag == "spam":
        return {
            "action": "archive",
            "reply_subject": None,
            "reply_body": None,
            "reason": "spam -- archive, no reply",
        }

    return {
        "action": "queue_for_approval",
        "reply_subject": None,
        "reply_body": None,
        "reason": f"tag={tag} -- doesn't match a known action, flagging for Rich",
    }


def _draft_positive_reply(subject: str, body: str, name_part: str) -> str:
    """LLM-drafted next-step for engaged sellers. Falls back to a template if
    no API key."""
    api_key = (os.environ.get("LUCREX_ANTHROPIC_KEY")
               or os.environ.get("ANTHROPIC_API_KEY"))
    if not api_key:
        return _positive_reply_template(name_part)
    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=api_key)
        r = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=400,
            system=(
                "You are Piper Reeves, Everlight Ventures' wholesale outreach "
                "lead. Warm, Nashville drawl, says 'y'all' naturally. Draft a "
                "concise reply (under 120 words) to a property owner who just "
                "expressed interest in our cash offer. Confirm interest, "
                "propose a 15-min discovery call, give a specific time window "
                "(within next 3 business days). Do NOT make up details about "
                "the offer terms. Sign off as 'Piper at Everlight'.\n"
                "Output ONLY the email body. No subject. No quoted block."
            ),
            messages=[{"role": "user", "content":
                       f"Their subject was: {subject}\n\nTheir reply:\n{body[:1500]}\n\nDraft my response."}],
        )
        return r.content[0].text.strip()
    except Exception:
        return _positive_reply_template(name_part)


def _draft_question_reply(subject: str, body: str, name_part: str) -> str:
    api_key = (os.environ.get("LUCREX_ANTHROPIC_KEY")
               or os.environ.get("ANTHROPIC_API_KEY"))
    if not api_key:
        return _question_reply_template(name_part)
    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=api_key)
        r = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            system=(
                "You are Piper Reeves, Everlight Ventures' wholesale outreach "
                "lead. The recipient asked a question that's not yet a "
                "yes/no on our offer. Draft a short (under 90 words) reply "
                "that answers what you can confidently answer (we're a real "
                "estate cash buyer based in Memphis area, we make all-cash "
                "offers on residential properties, no obligation), then asks "
                "ONE clarifying question to move them forward. Sign off as "
                "'Piper at Everlight'.\n"
                "Output ONLY the email body."
            ),
            messages=[{"role": "user", "content":
                       f"Their subject: {subject}\n\nTheir question:\n{body[:1500]}\n\nDraft my reply."}],
        )
        return r.content[0].text.strip()
    except Exception:
        return _question_reply_template(name_part)


def _positive_reply_template(name_part: str) -> str:
    return (f"Hi{name_part},\n\nGreat to hear from you. I'd like to set up a "
            "quick 15-minute call to walk you through the offer specifics. "
            "Are you free in the next 3 business days? Just hit reply with "
            "a couple windows that work and I'll lock one in.\n\n"
            "-- Piper at Everlight")


def _question_reply_template(name_part: str) -> str:
    return (f"Hi{name_part},\n\nThanks for reaching out. We're Everlight "
            "Ventures, a cash buyer for residential properties (Memphis "
            "area + surrounding states). No obligation, no commission, "
            "fast close. To give you a useful number, can you share the "
            "address you have in mind?\n\n-- Piper at Everlight")


if __name__ == "__main__":
    samples = [
        ("opt_out", "owner@x.com", "Re: 942 MELROSE", "remove me", 0.92),
        ("legal_threat", "atty@x.com", "Cease and desist", "I am attorney...", 0.85),
        ("positive_reply", "seller@x.com", "Re: cash offer", "Yes interested!", 0.9),
        ("question", "person@x.com", "Curious", "Who are you?", 0.7),
        ("bounce", "mailer-daemon@x", "Delivery failure", "550", 0.95),
        ("spam", "spam@x", "FREE IPHONE", "click", 0.95),
    ]
    for tag, sender, subj, body, conf in samples:
        r = draft(tag, sender, subj, body, conf)
        print(f"\n[{tag:14}] action={r['action']}")
        print(f"  reason: {r['reason']}")
        if r['reply_body']:
            print(f"  body preview: {r['reply_body'][:140]!r}")
