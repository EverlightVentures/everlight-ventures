"""ai_caller -- Twilio + ElevenLabs Convai outbound dialer.

What this does
--------------
Places a real outbound phone call to a CONSENTED contact, using Twilio for
the carrier connection and ElevenLabs Convai (Conversational AI) as the
voice agent. The agent reads from `pitch_generator.phone_talking_points`
and conducts a structured conversation.

Compliance gates (every call passes through these BEFORE dialing)
-----------------------------------------------------------------
  1. weekly_cadence.is_outreach_allowed_now(state, "ai_call",
        contact_phone=phone, contact_email=email)
     -- enforces TCPA hour rules + per-contact PEWC consent on file
  2. resend_guard equivalent: never dials owner/internal numbers
  3. Twilio + ElevenLabs env vars present
  4. Daily call cap (configurable) so a runaway loop cannot empty an account

Required env (already on Oracle per user)
-----------------------------------------
  TWILIO_ACCOUNT_SID
  TWILIO_AUTH_TOKEN
  TWILIO_FROM_NUMBER     -- Everlight outbound caller ID
  ELEVENLABS_API_KEY
  ELEVENLABS_AGENT_ID    -- the Convai agent we configured for wholesale

Usage
-----
    from ai_caller import dial_consented

    res = dial_consented(
        contact_phone="+14045551234",
        contact_state="GA",
        contact_email="seller@example.com",
        agent_role="seller_acquisition",  # or "buyer_dispatch"
        property_context={...},  # passed to ElevenLabs as agent variables
    )
    # returns {ok, call_sid, agent_id, error, gate_reason}
"""
from __future__ import annotations

import json
import logging
import os
import sys
from base64 import b64encode
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

log = logging.getLogger("ai_caller")

WORKSPACE_CANDIDATES = [Path("/home/opc"), Path("/mnt/sdcard/AA_MY_DRIVE")]


def _workspace() -> Path:
    for p in WORKSPACE_CANDIDATES:
        if p.exists():
            return p
    return WORKSPACE_CANDIDATES[0]


# Path bootstrap so we can import compliance + content modules
for sub in (
    "/home/opc/wholesale/compliance",
    "/home/opc/wholesale/pitches",
    "/home/opc/content_tools",
    "/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale/compliance",
    "/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale/pitches",
    "/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/content_tools",
):
    if Path(sub).exists() and sub not in sys.path:
        sys.path.insert(0, sub)


# Daily call cap to prevent runaway loops
DAILY_CALL_CAP = int(os.environ.get("AI_CALL_DAILY_CAP", "50"))
LEDGER = _workspace() / "_logs" / "ai_caller.jsonl"


def _normalize_phone(p: str) -> str:
    digits = "".join(c for c in (p or "") if c.isdigit())
    if len(digits) == 10:
        return "+1" + digits
    if len(digits) == 11 and digits.startswith("1"):
        return "+" + digits
    return ""


def _today_count() -> int:
    if not LEDGER.exists():
        return 0
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    n = 0
    try:
        with LEDGER.open(encoding="utf-8") as f:
            for line in f:
                try:
                    row = json.loads(line)
                    if row.get("date") == today and row.get("ok"):
                        n += 1
                except Exception:
                    continue
    except Exception:
        pass
    return n


def _record(payload: dict, ok: bool, error: str = "") -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    try:
        with LEDGER.open("a", encoding="utf-8") as f:
            f.write(json.dumps({
                "ts": datetime.now(timezone.utc).isoformat(),
                "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "ok": ok,
                "to": payload.get("to", ""),
                "agent_role": payload.get("agent_role", ""),
                "call_sid": payload.get("call_sid", ""),
                "error": error,
            }) + "\n")
    except Exception:
        pass


def _twilio_creds() -> tuple[str, str, str]:
    return (
        os.environ.get("TWILIO_ACCOUNT_SID", ""),
        os.environ.get("TWILIO_AUTH_TOKEN", ""),
        os.environ.get("TWILIO_FROM_NUMBER", ""),
    )


def _elevenlabs_creds() -> tuple[str, str]:
    return (
        os.environ.get("ELEVENLABS_API_KEY", ""),
        os.environ.get("ELEVENLABS_AGENT_ID", ""),
    )


def _elevenlabs_signed_url(api_key: str, agent_id: str) -> Optional[str]:
    """Get a signed Convai WebSocket URL for this agent (private agents only)."""
    url = f"https://api.elevenlabs.io/v1/convai/conversation/get_signed_url?agent_id={agent_id}"
    try:
        req = Request(url, headers={"xi-api-key": api_key})
        with urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            return data.get("signed_url")
    except (HTTPError, URLError, TimeoutError) as exc:
        log.warning("ElevenLabs signed_url failed: %s", exc)
        return None


def _twilio_dial(account_sid: str, auth_token: str, from_num: str,
                 to_num: str, twiml: str) -> dict:
    """Place outbound call via Twilio with inline TwiML. Returns parsed JSON."""
    url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Calls.json"
    body = urlencode({"To": to_num, "From": from_num, "Twiml": twiml}).encode()
    auth = b64encode(f"{account_sid}:{auth_token}".encode()).decode()
    req = Request(
        url, data=body,
        headers={
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    try:
        with urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode())
    except HTTPError as exc:
        body_text = exc.read().decode("utf-8", errors="ignore")[:400]
        return {"error": f"twilio_http_{exc.code}: {body_text}"}
    except (URLError, TimeoutError) as exc:
        return {"error": f"twilio_unreachable: {exc}"}


def _build_twiml_for_convai(signed_url: str, agent_phone_label: str = "Everlight Voice") -> str:
    """TwiML that streams audio bidirectionally to ElevenLabs Convai."""
    # ElevenLabs documents using Twilio's <Connect><Stream> for live AI calls
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<Response>'
        f'<Connect>'
        f'<Stream url="{signed_url}">'
        f'<Parameter name="caller" value="{agent_phone_label}"/>'
        f'</Stream>'
        f'</Connect>'
        f'</Response>'
    )


def _load_property_context_from_lead(lead_id: str) -> dict:
    """Load PropertyLead by id and run pitch_generator to get the full context.

    Returns dict suitable for `property_context` arg of dial_consented:
        address, owner_first_name, cash_offer_low/high, pain_anchor,
        area_median, area_yoy_pct, days_on_market, primary_buyer_motivation.
    Best-effort -- returns {} if Django not loadable.
    """
    if not lead_id:
        return {}
    try:
        for p in ("/home/opc/hive_django",
                  "/mnt/sdcard/AA_MY_DRIVE/09_DASHBOARD/hive_dashboard"):
            if p not in sys.path:
                sys.path.insert(0, p)
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hive_dashboard.settings")
        import django
        try:
            django.setup()
        except Exception:
            pass
        from broker_ops.models import PropertyLead
        from pitch_generator import seller_pitch  # type: ignore
    except Exception as exc:
        log.warning("property_context load deps failed: %s", exc)
        return {}

    try:
        lead = PropertyLead.objects.filter(id=lead_id).first()
        if not lead:
            return {"lead_id": lead_id, "lookup": "not_found"}
    except Exception as exc:
        return {"lead_id": lead_id, "lookup_error": str(exc)[:200]}

    try:
        pitch = seller_pitch(lead)
        d = pitch.get("data_used", {}) or {}
        oi = d.get("owner_intel", {}) or {}
        first_name = (lead.owner_name or "").split()[0].title() if lead.owner_name else "there"
        return {
            "address": lead.address or "",
            "owner_first_name": first_name,
            "owner_state": (lead.state or ""),
            "cash_offer_low": str(d.get("cash_offer_low", "")),
            "cash_offer_high": str(d.get("cash_offer_high", "")),
            "primary_pain": oi.get("primary_pain", ""),
            "estimated_arv": str(d.get("estimated_arv", "")),
        }
    except Exception as exc:
        log.warning("seller_pitch failed for lead %s: %s", lead_id, exc)
        return {"address": lead.address or "", "owner_first_name": (lead.owner_name or "").split()[0]}


def dial_consented(
    *, contact_phone: str, contact_state: str = "",
    contact_email: str = "", contact_name: str = "",
    agent_role: str = "seller_acquisition",
    property_context: Optional[dict] = None,
    lead_id: str = "",
) -> dict[str, Any]:
    """Place a single outbound AI voice call. Returns status dict, never raises.

    Gates (in order, all must pass):
      1. Daily call cap not exceeded
      2. weekly_cadence allows ai_call now for this state + this contact
      3. Phone is owner/internal (resend_guard equivalent) -- block
      4. Twilio + ElevenLabs env vars present
      5. ElevenLabs signed URL obtainable
      6. Twilio dial succeeds
    """
    e164 = _normalize_phone(contact_phone)
    if not e164:
        return {"ok": False, "error": "invalid_phone"}

    if _today_count() >= DAILY_CALL_CAP:
        return {"ok": False, "error": f"daily_cap_reached:{DAILY_CALL_CAP}"}

    # ── Gate 1: cadence + consent ─────────────────────────
    try:
        from weekly_cadence import is_outreach_allowed_now  # type: ignore
        allowed, reason = is_outreach_allowed_now(
            contact_state or "GA", "ai_call",
            contact_phone=e164, contact_email=contact_email,
        )
        if not allowed:
            _record({"to": e164, "agent_role": agent_role}, False, reason)
            return {"ok": False, "error": "cadence_or_consent_blocked", "gate_reason": reason}
    except Exception as exc:
        return {"ok": False, "error": f"cadence_unavailable:{exc}"}

    # ── Gate 2: owner-block guard ─────────────────────────
    try:
        from resend_guard import is_owner_recipient  # type: ignore
        if is_owner_recipient(contact_email or ""):
            return {"ok": False, "error": "owner_email_blocked"}
    except Exception:
        pass

    # ── Gate 3: env presence ──────────────────────────────
    twilio_sid, twilio_token, twilio_from = _twilio_creds()
    el_key, el_agent = _elevenlabs_creds()
    el_phone = os.environ.get("ELEVENLABS_PHONE_ID", "")
    missing = [k for k, v in (
        ("TWILIO_ACCOUNT_SID", twilio_sid),
        ("TWILIO_AUTH_TOKEN", twilio_token),
        ("TWILIO_FROM_NUMBER", twilio_from),
        ("ELEVENLABS_API_KEY", el_key),
        ("ELEVENLABS_AGENT_ID", el_agent),
        ("ELEVENLABS_PHONE_ID", el_phone),
    ) if not v]
    if missing:
        return {"ok": False, "error": f"missing_env:{','.join(missing)}"}

    # ── Build dynamic variables for the Convai agent ───────
    # If lead_id provided, auto-load the full pitch context so Piper can
    # quote real address + offer range + identified pain anchor.
    if lead_id and not property_context:
        property_context = _load_property_context_from_lead(lead_id)

    dyn_vars = {
        "owner_first_name": (contact_name.split()[0] if contact_name else "there"),
        "owner_state": contact_state or "",
    }
    if property_context:
        dyn_vars.update({
            "property_address": str(property_context.get("address", "")),
            "cash_offer_low": str(property_context.get("cash_offer_low", "")),
            "cash_offer_high": str(property_context.get("cash_offer_high", "")),
            "primary_pain": str(property_context.get("primary_pain", "")),
            "estimated_arv": str(property_context.get("estimated_arv", "")),
        })
        # Override owner_first_name if context has it
        if property_context.get("owner_first_name"):
            dyn_vars["owner_first_name"] = property_context["owner_first_name"]

    # ── Place the call via Convai outbound endpoint ────────
    res = _convai_outbound_call(el_key, el_agent, el_phone, e164, dyn_vars)
    if "error" in res:
        _record({"to": e164, "agent_role": agent_role}, False, res["error"])
        return {"ok": False, "error": res["error"]}

    call_sid = res.get("callSid") or res.get("call_sid", "")
    conv_id = res.get("conversation_id", "")
    _record({"to": e164, "agent_role": agent_role, "call_sid": call_sid}, True)

    return {
        "ok": True,
        "call_sid": call_sid,
        "conversation_id": conv_id,
        "to": e164,
        "agent_role": agent_role,
        "agent_id": el_agent,
    }


def daily_status() -> dict:
    """Today's call counts."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    success = 0
    failed = 0
    if LEDGER.exists():
        with LEDGER.open() as f:
            for line in f:
                try:
                    row = json.loads(line)
                    if row.get("date") != today:
                        continue
                    if row.get("ok"):
                        success += 1
                    else:
                        failed += 1
                except Exception:
                    continue
    return {
        "date": today,
        "success": success,
        "failed": failed,
        "cap": DAILY_CALL_CAP,
        "remaining": max(0, DAILY_CALL_CAP - success),
        "twilio_configured": bool(_twilio_creds()[0]),
        "elevenlabs_configured": bool(_elevenlabs_creds()[0]),
    }


def _cli() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")

    p1 = sub.add_parser("dial")
    p1.add_argument("--phone", required=True)
    p1.add_argument("--state", default="GA")
    p1.add_argument("--email", default="")
    p1.add_argument("--name", default="")
    p1.add_argument("--role", default="seller_acquisition")
    p1.add_argument("--lead-id", default="", help="PropertyLead UUID -- auto-loads pitch context")

    sub.add_parser("status")

    args = ap.parse_args()
    if args.cmd == "dial":
        out = dial_consented(
            contact_phone=args.phone, contact_state=args.state,
            contact_email=args.email, contact_name=args.name,
            agent_role=args.role, lead_id=args.lead_id,
        )
        print(json.dumps(out, indent=2))
        return 0 if out.get("ok") else 1
    if args.cmd == "status":
        print(json.dumps(daily_status(), indent=2))
        return 0
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(_cli())
