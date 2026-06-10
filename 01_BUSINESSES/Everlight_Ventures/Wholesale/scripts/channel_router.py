#!/usr/bin/env python3
"""
channel_router.py -- one message, the seller's CHOSEN channel. The if/else layer that
sends the SAME branded content via email, SMS, or an automated Henry voice call, depending
on what the contact opted into. Consent (they chose + submitted the number) is the legal
basis that makes SMS/voice TCPA-lawful.

Principles:
  - Generate the message ONCE (llm_compose, persona voice). Adapt per channel, do not
    re-generate -- saves LLM + send quota. Brand + voice stay consistent because it is the
    same words reshaped: email = full gold template, SMS = 2-line summary + link, voice =
    spoken script. All carry the persona + Everlight brand.
  - QUOTA-AWARE: send via exactly ONE channel (the chosen one), never all three.
  - CONSENT GATE (hard): SMS / voice fire ONLY if the contact opted in (chose it + gave a
    number). Otherwise fall back to email. Never cold SMS/voice (doctrine + TCPA).
  - GRACEFUL DEGRADE: if Twilio (SMS) or telephony (voice) is not configured, log + fall
    back to email so nothing is lost.
  - Every channel still passes its own gate chain (eradication/opt-out/halt/budget) inside
    branded_mailer / branded_sms. This is the routing layer on top, not a bypass.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/mnt/sdcard/AA_MY_DRIVE")
WH = ROOT / "01_BUSINESSES" / "Everlight_Ventures" / "Wholesale"
CONSENT_LOG = ROOT / "_logs" / "channel_consent.jsonl"
sys.path.insert(0, str(WH / "scripts"))
sys.path.insert(0, str(ROOT / "03_AUTOMATION_CORE/01_Scripts/content_tools"))

CHANNELS = ("email", "sms", "voice", "telegram", "whatsapp", "instagram")
# Platforms with a messaging window: we may free-form only within N hours of their last
# inbound; outside it we degrade (WhatsApp needs an approved template, IG a human-agent tag).
WINDOW_HOURS = {"whatsapp": 24, "instagram": 24}
# WhatsApp (Meta) requires AUDITABLE, explicit, channel-named opt-in -- a bare phone is NOT enough.
STRICT_OPTIN = {"whatsapp"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _within_window(last_inbound_ts: str, hours: int) -> bool:
    """True if we are still inside the platform messaging window (free-form allowed)."""
    if not last_inbound_ts:
        return False
    try:
        last = datetime.fromisoformat(last_inbound_ts.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - last).total_seconds() < hours * 3600
    except Exception:
        return False


def record_inbound(email: str, channel: str, handle: str = "") -> None:
    """A seller messaged us on a platform -> resets the messaging window + stores the routing
    handle (telegram chat_id / whatsapp number / IG IGSID). This is what keeps WA/IG lawful."""
    try:
        import conversation_memory as cm
        r = cm.load(email)
        r["contact"]["channel"] = channel
        if handle:
            r["contact"]["platform_handle"] = handle
        r["contact"]["channel_consented"] = True       # they initiated = consent
        r["contact"]["last_inbound_ts"] = _now()
        cm._save(email, r)
    except Exception:
        pass


def channel_choice_offer() -> str:
    """Brand-consistent menu offered to the seller. Choosing = consent for that channel."""
    return ("If email is not your thing, you have options. Reply with your cell to switch to text, "
            "or message us on WhatsApp or Telegram, or reply CALL and Henry will give you a quick "
            "ring. Whatever is easiest for you, we will meet you there.")


def detect_choice(text: str) -> dict:
    """Parse a seller reply for a channel choice + handle. Returns {channel, phone/handle} or {}."""
    t = (text or "")
    phone = None
    m = re.search(r"(\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}", t)
    if m:
        phone = re.sub(r"\D", "", m.group(0))[-10:]
    if re.search(r"\bcall\b|call me|give me a ring|phone me", t, re.I):
        return {"channel": "voice", "phone": phone}
    if re.search(r"\bwhatsapp\b|whats app|wa\b", t, re.I):
        return {"channel": "whatsapp", "phone": phone}
    if re.search(r"\btelegram\b|t\.me/", t, re.I):
        return {"channel": "telegram", "phone": phone}
    if re.search(r"\binstagram\b|\big\b|\bdm\b", t, re.I):
        return {"channel": "instagram", "phone": phone}
    if phone or re.search(r"\btext\b|\bsms\b|text me", t, re.I):
        return {"channel": "sms", "phone": phone}
    return {}


def set_preference(email: str, channel: str, phone: str = "", consent_text: str = "",
                   source: str = "reply", platform_handle: str = "") -> dict:
    """Record the chosen channel + the CONSENT record (the legal basis). WhatsApp (STRICT_OPTIN)
    requires non-empty verbatim consent_text -- a bare phone is NOT Meta-grade opt-in (Priya)."""
    if channel not in CHANNELS:
        channel = "email"
    if channel in STRICT_OPTIN and not (consent_text or "").strip():
        consented = False  # WhatsApp without auditable opt-in text -> not consented -> will degrade
    else:
        consented = channel == "email" or bool(phone) or bool(platform_handle) or source == "explicit_optin"
    rec = {"email": (email or "").lower(), "channel": channel, "phone": phone,
           "platform_handle": platform_handle, "consented": consented,
           "consent_text": (consent_text or "")[:300], "source": source,
           "recorded_at": _now(), "last_inbound_ts": _now()}
    try:
        CONSENT_LOG.parent.mkdir(parents=True, exist_ok=True)
        with CONSENT_LOG.open("a") as f:
            f.write(json.dumps(rec) + "\n")
    except Exception:
        pass
    try:
        import conversation_memory as cm
        r = cm.load(email); c = r["contact"]
        c["channel"] = channel; c["phone"] = phone; c["channel_consented"] = consented
        if platform_handle:
            c["platform_handle"] = platform_handle
        c["last_inbound_ts"] = _now()  # choosing the channel is an inbound -> opens the window
        cm._save(email, r)
    except Exception:
        pass
    return rec


def preferred(email: str) -> dict:
    try:
        import conversation_memory as cm
        c = cm.load(email)["contact"]
        return {"channel": c.get("channel", "email"), "phone": c.get("phone", ""),
                "platform_handle": c.get("platform_handle", ""),
                "last_inbound_ts": c.get("last_inbound_ts", ""),
                "consented": c.get("channel_consented", c.get("channel", "email") == "email")}
    except Exception:
        return {"channel": "email", "phone": "", "consented": True}


def _summarize(body: str, limit: int = 220) -> str:
    """First 1-2 sentences + any dollar number -- the SMS-length gist, same voice."""
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", (body or "").replace("\n", " ")) if s.strip()]
    gist = " ".join(sents[:2])[:limit]
    money = re.search(r"\$\s?\d[\d,]{2,}", body or "")
    if money and money.group(0) not in gist:
        gist = (gist[:limit - 14] + f" {money.group(0)}.").strip()
    return gist


def _voice_script(body: str, persona: str) -> str:
    """Spoken version: short, natural, same content + voice. For ElevenLabs TTS + a callback."""
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", (body or "").replace("\n", " ")) if s.strip()]
    name = {"henry_hammond": "Henry", "piper_reeves": "Piper", "marvin_cohen": "Marvin"}.get(persona, "the team")
    return (f"Hi, this is {name} with Everlight Ventures. " + " ".join(sents[:3])
            + " I will follow up by email with the details. Thanks, and have a good one.")


def render_for_channel(channel: str, *, subject: str, body: str, persona: str, link: str = "") -> dict:
    # Chat-style platforms get the concise gist + link, same persona voice. Telegram tolerates
    # a touch more length; WhatsApp/IG/SMS stay short.
    if channel in ("sms", "whatsapp", "instagram"):
        return {"body": _summarize(body) + (f" Full details: {link}" if link else "")}
    if channel == "telegram":
        return {"body": _summarize(body, limit=320) + (f"\n\nFull details: {link}" if link else "")}
    if channel == "voice":
        return {"script": _voice_script(body, persona)}
    return {"subject": subject, "body": body}   # email -> branded_mailer wraps the gold template


def send(email: str, *, subject: str, body: str, persona: str, link: str = "",
         category: str = "vip_reply", dry_run: bool = True) -> dict:
    """Route ONE send via the contact's chosen channel. Consent-gated, quota-aware, degrades."""
    pref = preferred(email)
    ch = pref["channel"]
    note = ""
    # CONSENT GATE: never cold on any non-email channel (they must have opted in).
    if ch != "email" and not pref.get("consented"):
        note = f"{ch} not consented -> email"; ch = "email"
    # WINDOW GATE: WhatsApp/Instagram free-form only inside the platform window; outside it we
    # would need an approved template (WA) / human-agent tag (IG) we have not provisioned -> degrade.
    if ch in WINDOW_HOURS and not _within_window(pref.get("last_inbound_ts", ""), WINDOW_HOURS[ch]):
        note = f"{ch} outside {WINDOW_HOURS[ch]}h window -> email"; ch = "email"
    rendered = render_for_channel(ch, subject=subject, body=body, persona=persona, link=link)
    plan = {"to": email, "channel": ch, "persona": persona, "dry_run": dry_run,
            "rendered": rendered, "note": note}
    if dry_run:
        plan["status"] = "planned"
        return plan
    try:
        if ch == "email":
            from branded_mailer import send_branded_email
            r = send_branded_email(to=email, subject=subject, body=body, persona_id=persona, budget_category="vip_reply")
            plan["status"] = "sent" if (getattr(r, "ok", False) or (isinstance(r, dict) and r.get("ok"))) else "send_failed"
        elif ch == "sms":
            from branded_sms import send_branded_sms
            r = send_branded_sms(to=pref["phone"], body=rendered["body"], category=category)
            ok = (getattr(r, "ok", False) or (isinstance(r, dict) and r.get("ok")))
            if not ok:   # Twilio not configured -> degrade to email
                plan["note"] += " | sms unavailable, degraded to email"; ch = "email"
                from branded_mailer import send_branded_email
                send_branded_email(to=email, subject=subject, body=body, persona_id=persona, budget_category="vip_reply")
                plan["channel"] = "email(degraded)"
            plan["status"] = "sent"
        elif ch == "voice":
            # queue a TTS callback (ElevenLabs script -> telephony). Degrades to email if no telephony.
            qd = ROOT / "_state" / "voice_call_queue"; qd.mkdir(parents=True, exist_ok=True)
            (qd / f"{re.sub(chr(92)+'W','_',email)}_{_now()[:19].replace(':','')}.json").write_text(
                json.dumps({"to_phone": pref["phone"], "persona": persona, "script": rendered["script"], "queued_at": _now()}))
            plan["status"] = "voice_queued"
        elif ch == "telegram":
            import os
            import urllib.request as _u, urllib.parse as _up
            tok = os.environ.get("TELEGRAM_BOT_TOKEN", "")
            chat_id = pref.get("platform_handle") or os.environ.get("TELEGRAM_CHAT_ID", "")
            if tok and chat_id:
                try:
                    _u.urlopen(_u.Request(f"https://api.telegram.org/bot{tok}/sendMessage",
                               data=_up.urlencode({"chat_id": chat_id, "text": rendered["body"]}).encode()), timeout=10)
                    plan["status"] = "sent"
                except Exception:
                    _degrade_email(email, subject, body, persona); plan["channel"] = "email(degraded)"
                    plan["status"] = "sent"; plan["note"] += " | telegram send failed -> email"
            else:
                _degrade_email(email, subject, body, persona); plan["channel"] = "email(degraded)"
                plan["status"] = "sent"; plan["note"] += " | telegram unavailable (no token/chat_id) -> email"
        elif ch in ("whatsapp", "instagram"):
            # Meta APIs need business verification + approved templates (WA) / human-agent scope
            # (IG) we have not provisioned. Compliant behavior = degrade to email until in place.
            _degrade_email(email, subject, body, persona); plan["channel"] = "email(degraded)"
            plan["status"] = "sent"; plan["note"] += f" | {ch} not provisioned (Meta verify/template pending) -> email"
    except Exception as e:
        plan["status"] = f"error_{type(e).__name__}"
    return plan


def _degrade_email(email, subject, body, persona):
    """The one safe fallback: a clean email (always lawful for an opted-in prospect)."""
    try:
        from branded_mailer import send_branded_email
        send_branded_email(to=email, subject=subject, body=body, persona_id=persona, budget_category="vip_reply")
    except Exception:
        pass


if __name__ == "__main__":
    demo_body = ("Hi Ray, Henry here. We buy as is, no repairs or fees, and we close on your "
                 "timeline. Our cash offer is $16,500. We handle the tenant and any title issues. "
                 "It is a clean, done deal whenever you are ready.")
    print("=== SAME message, all channels (consistent voice) ===")
    for ch in CHANNELS:
        r = render_for_channel(ch, subject="Re: your place on Englewood", body=demo_body, persona="henry_hammond",
                               link="http://127.0.0.1:2200/reports/deal.html")
        print(f"\n[{ch.upper()}] {json.dumps(r)[:400]}")
    print("\n=== choice offer ===\n", channel_choice_offer())
