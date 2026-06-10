"""classifier -- tags an inbound email thread as one of:
  opt_out         | sender wants off the list (any of: stop, unsubscribe, DNC,
                  | "remove me", "do not contact", legal cease-and-desist).
                  | -> auto-add to DNC + send confirmation reply.
  legal_threat    | attorney letter, BBB complaint, regulator threat.
                  | -> hard DNC + escalate to Rich + freeze all sends to
                  |    associated address.
  positive_reply  | interested, asking about price/details/timeline.
                  | -> draft a reply, queue for auto-send if confidence high.
  question        | asking for info but not yet engaged. ambiguous.
                  | -> draft + flag for Rich's quick approval.
  spam            | clearly unrelated / phishing / promotional.
                  | -> archive, do nothing.
  bounce          | NDR / mailer-daemon / address rejected.
                  | -> log + flag suspicious sender.
  other           | doesn't fit above. flag for Rich.

Cheap path first: regex hits for opt_out + bounce kill 80% of triage cost
without an LLM call. Only ambiguous cases hit Haiku 4.5.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Optional


def _bootstrap_env() -> None:
    """Source /AA_MY_DRIVE/.env for daemon subprocesses that don't inherit
    the user shell env. Same pattern as bash_auto_approver."""
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

# fast-path regex: case-insensitive, anchored to word boundaries where useful
# CRITICAL: opt_out patterns must be FIRST-PERSON imperatives. Marketing
# emails contain "unsubscribe" in their footers -- those are NOT opt-outs.
# A real opt-out reply says "remove ME", "stop emailing ME", "DON'T contact ME".
# Bare "unsubscribe" is rejected; only "unsubscribe me", "please unsubscribe",
# or single-word "unsubscribe" as the entire body counts.
_OPT_OUT_PATTERNS = [
    r"\b(?:please\s+)?unsubscribe\s+me\b",
    r"\bstop\s+(?:emailing|contacting|messaging|sending)\s+(?:me|us)\b",
    r"\bremove\s+(?:me|us|my\s+\w+)\s+from\b",
    r"\btake\s+(?:me|us|my\s+name)\s+off\b",
    r"\bdo\s+not\s+(?:contact|email|message)\s+(?:me|us|this\s+\w+)\b",
    r"\bdon'?t\s+(?:contact|email|message|reply\s+to)\s+(?:me|us)\b",
    r"\b(?:I|we)\s+(?:do\s+not|don'?t)\s+(?:want|wish)\s+(?:to\s+be\s+contacted|further)\b",
    r"\b(?:I|we)\s+(?:am|are)\s+no\s+longer\s+interested\b",
    r"\bI\s+want\s+(?:off|to\s+be\s+removed)\b",
    r"\b(?:please\s+)?(?:DNC|opt[- ]?out)\s+(?:me|this|our|my)\b",
]
_OPT_OUT_RE = re.compile("|".join(_OPT_OUT_PATTERNS), re.IGNORECASE)

# Pure single-word opt-out replies (when the entire body is just one word).
_BARE_OPT_OUT_BODIES = {"unsubscribe", "stop", "remove", "dnc", "opt out", "optout"}

_LEGAL_PATTERNS = [
    r"\battorney\b",
    r"\blegal\s+counsel\b",
    r"\blawsuit\b",
    r"\bBBB\b|better\s+business\s+bureau",
    r"\bFTC\b|federal\s+trade\s+commission",
    r"\bcease\s+and\s+desist\b",
    r"\bsue\b|\bsuing\b",
    r"\bdamages\b.*\b(?:claim|seek)\b",
    r"\bregulatory\s+complaint\b",
]
_LEGAL_RE = re.compile("|".join(_LEGAL_PATTERNS), re.IGNORECASE)

_BOUNCE_PATTERNS = [
    r"mailer-daemon",
    r"undelivered\s+mail",
    r"delivery\s+(?:status|failure)",
    r"address\s+(?:rejected|not\s+found)",
    r"550\s+",  # SMTP reject code
]
_BOUNCE_RE = re.compile("|".join(_BOUNCE_PATTERNS), re.IGNORECASE)


def _llm_classify(subject: str, body: str, sender: str) -> dict:
    api_key = (os.environ.get("LUCREX_ANTHROPIC_KEY")
               or os.environ.get("ANTHROPIC_API_KEY"))
    if not api_key:
        return {"tag": "other", "confidence": 0.0,
                "reasoning": "no api key, defaulting to other"}
    try:
        from anthropic import Anthropic
    except ImportError:
        return {"tag": "other", "confidence": 0.0,
                "reasoning": "anthropic SDK missing"}

    client = Anthropic(api_key=api_key)
    system = (
        "You are Rich Gee's email triage classifier for Everlight Ventures' "
        "wholesale outreach inbox. Tag each inbound email as exactly one of:\n"
        "  opt_out       -- they want off the list\n"
        "  legal_threat  -- attorney/BBB/regulator\n"
        "  positive_reply -- engaged, interested, asking about offer/price\n"
        "  question      -- ambiguous, asking for info\n"
        "  spam          -- unrelated / phishing / promo\n"
        "  bounce        -- NDR / mailer-daemon / delivery failure\n"
        "  other         -- doesn't fit\n\n"
        "Output ONLY valid JSON: {\"tag\": \"<one>\", \"confidence\": "
        "<0.0-1.0>, \"reasoning\": \"<one short sentence>\"}.\n"
        "Confidence above 0.85 means safe to auto-respond. Below 0.6 means "
        "flag for Rich. Default confidence 0.7 if unsure."
    )
    user_msg = (
        f"Sender: {sender}\nSubject: {subject}\n\nBody (first 1500 chars):\n"
        f"{body[:1500]}\n\nClassify."
    )
    try:
        r = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            system=system,
            messages=[{"role": "user", "content": user_msg}],
        )
        text = r.content[0].text.strip()
        s, e = text.find("{"), text.rfind("}")
        if s >= 0 and e > s:
            import json
            obj = json.loads(text[s:e + 1])
            tag = obj.get("tag", "other")
            if tag in ("opt_out", "legal_threat", "positive_reply", "question",
                       "spam", "bounce", "other"):
                return {
                    "tag": tag,
                    "confidence": float(obj.get("confidence", 0.7)),
                    "reasoning": obj.get("reasoning", ""),
                }
    except Exception as e:
        return {"tag": "other", "confidence": 0.0,
                "reasoning": f"LLM error: {e}"}
    return {"tag": "other", "confidence": 0.0,
            "reasoning": "LLM output unparseable"}


_MARKETING_DOMAIN_HINTS = (
    "noreply", "no-reply", "do-not-reply", "mailer", "newsletter",
    "marketing", "notifications", "alerts", "info@", "support@",
    "@email.", "@mail.", "@em.", "@e.", "@news.", "@em-", "-noreply",
)


def _looks_like_marketing(sender: str, body: str) -> bool:
    """Heuristic: is this a vendor/marketing email rather than a personal
    reply from a wholesale prospect? Reject opt_out classification on these."""
    s = (sender or "").lower()
    if any(h in s for h in _MARKETING_DOMAIN_HINTS):
        return True
    # Marketing emails are typically long with HTML structure
    if len(body) > 1500 and ("<table" in body.lower() or "<!doctype" in body.lower()):
        return True
    return False


def classify(subject: str, body: str, sender: str = "",
             skip_llm: bool = False) -> dict:
    """Classify one email. Fast-path regex first, LLM only if ambiguous.

    Returns dict with: tag, confidence, reasoning, fast_path (bool).
    """
    text = f"{subject}\n\n{body}"
    body_stripped = (body or "").strip().lower()

    # Order matters: bounce -> legal_threat (escalation) -> opt_out -> llm.
    if _BOUNCE_RE.search(text):
        return {"tag": "bounce", "confidence": 0.95, "fast_path": True,
                "reasoning": "matched bounce pattern"}

    if _LEGAL_RE.search(text):
        # Newsletters and marketing emails frequently mention "FTC", "lawsuit",
        # "attorney" in their content -- those are NOT threats directed at us.
        # A real legal threat is short, addressed-at-us, and from an
        # individual sender, not a marketing domain.
        if _looks_like_marketing(sender, body):
            pass  # fall through to LLM
        else:
            return {"tag": "legal_threat", "confidence": 0.88, "fast_path": True,
                    "reasoning": "matched legal-threat pattern (non-marketing sender)"}

    # Bare-body opt-out: a one-word reply ("unsubscribe", "stop", "remove")
    # is unambiguous opt-out IF body is short AND single-token.
    if (len(body_stripped) <= 30 and
            body_stripped in _BARE_OPT_OUT_BODIES):
        return {"tag": "opt_out", "confidence": 0.95, "fast_path": True,
                "reasoning": f"bare body opt-out: {body_stripped!r}"}

    # First-person opt-out language. Reject if it looks like a marketing
    # email (the regex would have matched on a footer "unsubscribe me from
    # this list" inside a marketing template).
    if _OPT_OUT_RE.search(text):
        if _looks_like_marketing(sender, body):
            # don't treat marketing emails as opt-outs, fall through to LLM
            pass
        else:
            return {"tag": "opt_out", "confidence": 0.90, "fast_path": True,
                    "reasoning": "matched first-person opt-out pattern"}

    if skip_llm:
        return {"tag": "other", "confidence": 0.5, "fast_path": True,
                "reasoning": "skip_llm=True; no fast-path match"}

    result = _llm_classify(subject, body, sender)
    result["fast_path"] = False
    return result


if __name__ == "__main__":
    import json, sys
    samples = [
        ("Subject: Re: 942 MELROSE offer", "Please remove me from your list. Don't contact me again.", "owner@example.com"),
        ("Subject: ATTORNEY -- David A Streubel", "I am the legal counsel for the property owner. Cease and desist immediately.", "streubel@law.example"),
        ("Subject: Re: cash offer", "Yes I'm interested. What's the timeline?", "seller@example.com"),
        ("Subject: Just curious", "How did you find my address?", "person@example.com"),
        ("Subject: WIN A FREE IPHONE", "Click here to win!", "spam@malicious.example"),
        ("Subject: Mail Delivery Failure", "Your message to user@example.com was not delivered. 550 5.1.1 Address rejected.", "mailer-daemon@example.com"),
    ]
    for subj, body, sender in samples:
        r = classify(subj, body, sender, skip_llm="--no-llm" in sys.argv)
        print(f"  [{r['tag']:14}] conf={r['confidence']:.2f} fast={r.get('fast_path',False)} | {sender:30}")
        print(f"     reason: {r['reasoning']}")
