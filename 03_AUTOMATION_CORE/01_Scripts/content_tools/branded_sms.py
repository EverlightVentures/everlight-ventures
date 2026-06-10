"""branded_sms -- the canonical SMS sender for Everlight.

Why this exists
---------------
SMS is the most space-constrained channel we ship. 160 characters per
segment; if you spend 60 of them on inconsistent micro-copy, you're
paying for noise. This module enforces:

  - A 1-character brand prefix (so recipients can identify Everlight texts)
  - Required STOP-to-opt-out compliance footer for cold outbound (CAN-SPAM
    equivalent for SMS / TCPA safe harbor)
  - Deliberate truncation so the body fits one segment when possible
  - Channel-aware routing (Twilio first, fallback to nothing)

State of the SMS stack
----------------------
There is no Twilio account wired in yet (per CLAUDE.md, "future" channel).
This module is built so that THE MOMENT a Twilio account exists, every
caller already routes through the brand contract. Add `TWILIO_*` env vars
and the `_twilio_send` path goes live with no caller changes.

Public API
----------
    from content_tools.branded_sms import send_branded_sms

    res = send_branded_sms(
        to="+15555550100",
        body="Quick check -- got the Loom you sent. Will reply tonight.",
        agent_name="Piper",
        category="vip_reply",   # vip_reply | nurture | bulk | transactional
        require_optout=True,    # auto-appends "STOP=opt out" if cold/bulk
    )
    # -> {"ok": True, "sid": "...", "segments": 1, "error": ""}

Categories
----------
  - "vip_reply"     -- replies to engaged contacts, no STOP footer required
  - "nurture"       -- warm follow-ups, STOP footer recommended
  - "bulk"          -- cold outbound, STOP footer MANDATORY
  - "transactional" -- booking confirmations / invoice paid receipts, no STOP

The micro-brand prefix used is "EV:" -- short, distinctive, fits in 3 chars.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

log = logging.getLogger("branded_sms")

# Brand micro-prefix and footer
BRAND_PREFIX = "EV: "
OPT_OUT_FOOTER = "  Reply STOP=optout"

# Single-segment SMS budget after prefix and footer
SEGMENT_LIMIT = 160


@dataclass
class SmsResult:
    ok: bool
    sid: str = ""
    segments: int = 0
    error: str = ""
    sent_body: str = ""


def _build_body(
    raw: str,
    *,
    require_optout: bool,
    category: str,
) -> str:
    """Assemble the final SMS body with brand prefix and (if needed) footer."""
    body = (raw or "").strip()
    if not body:
        return ""
    if not body.startswith(BRAND_PREFIX):
        body = BRAND_PREFIX + body

    needs_optout = require_optout or category in {"bulk", "nurture"}
    if needs_optout and "STOP" not in body.upper():
        # Trim body so prefix+body+footer fits one segment if possible
        slack = SEGMENT_LIMIT - len(OPT_OUT_FOOTER)
        if len(body) > slack:
            body = body[:slack - 1].rstrip() + "…"
        body = body + OPT_OUT_FOOTER

    return body


def _segment_count(body: str) -> int:
    """Return number of SMS segments the body will use."""
    if not body:
        return 0
    n = len(body)
    if n <= 160:
        return 1
    return (n + 152) // 153  # concat-SMS uses 153 chars per segment


def _twilio_send(to: str, body: str) -> dict[str, Any]:
    """POST to Twilio Messages API. Returns parsed response or error dict."""
    sid = os.environ.get("TWILIO_ACCOUNT_SID", "")
    token = os.environ.get("TWILIO_AUTH_TOKEN", "")
    from_num = os.environ.get("TWILIO_FROM_NUMBER", "")
    if not (sid and token and from_num):
        return {"ok": False, "error": "twilio_not_configured"}

    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
    data = urlencode({"To": to, "From": from_num, "Body": body}).encode()
    auth = f"{sid}:{token}".encode()
    import base64
    auth_b64 = base64.b64encode(auth).decode()
    req = Request(
        url, data=data,
        headers={
            "Authorization": f"Basic {auth_b64}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    try:
        with urlopen(req, timeout=15) as resp:
            payload = json.loads(resp.read().decode("utf-8") or "{}")
            return {"ok": True, "sid": payload.get("sid", ""), "raw": payload}
    except Exception as exc:
        return {"ok": False, "error": repr(exc)[:200]}


def send_branded_sms(
    *,
    to: str,
    body: str,
    agent_name: str = "Hive",
    category: str = "transactional",
    require_optout: bool = False,
) -> SmsResult:
    """Send one branded SMS. Returns SmsResult, never raises.

    Today Twilio is not configured -- this returns ok=False with a clear
    reason so callers can degrade gracefully (e.g. fall back to email).
    Once TWILIO_* env vars exist on Oracle, this becomes a real send.
    """
    final = _build_body(body, require_optout=require_optout, category=category)
    if not final:
        return SmsResult(ok=False, error="empty_body", sent_body="")

    res = _twilio_send(to, final)
    if not res.get("ok"):
        return SmsResult(
            ok=False,
            error=str(res.get("error", "unknown")),
            segments=_segment_count(final),
            sent_body=final,
        )
    return SmsResult(
        ok=True,
        sid=str(res.get("sid", "")),
        segments=_segment_count(final),
        sent_body=final,
    )


def preview_branded_sms(
    body: str,
    *,
    require_optout: bool = False,
    category: str = "transactional",
) -> dict[str, Any]:
    """Preview what the SMS will look like without sending. Useful for tests."""
    final = _build_body(body, require_optout=require_optout, category=category)
    return {
        "body": final,
        "char_count": len(final),
        "segments": _segment_count(final),
        "fits_single_segment": _segment_count(final) <= 1,
    }


def _cli() -> int:
    import argparse, sys
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")

    pp = sub.add_parser("preview")
    pp.add_argument("--body", required=True)
    pp.add_argument("--category", default="transactional")
    pp.add_argument("--require-optout", action="store_true")

    ps = sub.add_parser("send")
    ps.add_argument("--to", required=True)
    ps.add_argument("--body", required=True)
    ps.add_argument("--category", default="transactional")
    ps.add_argument("--require-optout", action="store_true")

    args = ap.parse_args()
    if args.cmd == "preview":
        out = preview_branded_sms(args.body, require_optout=args.require_optout, category=args.category)
        print(json.dumps(out, indent=2))
        return 0
    if args.cmd == "send":
        res = send_branded_sms(
            to=args.to, body=args.body,
            category=args.category, require_optout=args.require_optout,
        )
        print(json.dumps({
            "ok": res.ok, "sid": res.sid, "segments": res.segments,
            "error": res.error, "sent_body": res.sent_body,
        }, indent=2))
        return 0 if res.ok else 1
    ap.print_help()
    return 1


if __name__ == "__main__":
    import sys
    sys.exit(_cli())
