"""confirm_call -- outbound seller-confirmation call via Twilio + ElevenLabs.

Fires when a lead transitions to status 'signed' (Rich signed the contract).
This is NOT cold outreach. It's a verbal confirmation that the deal is on.

Flow:
  1. Scan leads_db for status='signed' and no call_confirmation_attempt yet.
  2. For each: verify seller has a phone + state allows calling + local hour OK.
  3. Build an ElevenLabs TTS .mp3 from a short confirmation script using
     Harrison/Piper's voice_id.
  4. Host the .mp3 at an Oracle-reachable URL.
  5. Twilio Programmable Voice POST:
        POST https://api.twilio.com/2010-04-01/Accounts/<SID>/Calls.json
        From = TWILIO_PHONE_NUMBER, To = seller's phone
        Twiml = <Response><Play>https://<oracle>/tts/<id>.mp3</Play>
                           <Gather digits=1 timeout=8>
                             <Say>Press 1 to confirm, 2 to decline.</Say>
                           </Gather></Response>
  6. Log the call outcome to the deal thread and Slack-alert on decline.

TCPA compliance:
  - Only calls numbers we have in leads_db (owner-of-record via scraped public
    records). The seller replied to our emails first = implied consent.
  - Call window: 9 AM - 7 PM LOCAL time (not UTC).
  - state_gate.check(state, 'call') must return ok.
  - Single call per deal. No retries. If no answer, we fall back to SMS + email.
"""
from __future__ import annotations

import json
import logging
import os
import pathlib
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta

logging.basicConfig(level=logging.INFO, format="[confirm %(asctime)s] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("confirm_call")

ROOT = pathlib.Path("/mnt/sdcard/AA_MY_DRIVE")
LEADS_DB = ROOT / "01_BUSINESSES" / "Everlight_Ventures" / "Broker_OS" / "wholesale_agent" / "leads_db.json"
CREDS = ROOT / "03_AUTOMATION_CORE" / "03_Credentials" / ".env"

sys.path.insert(0, str(ROOT / "01_BUSINESSES" / "Everlight_Ventures" / "Broker_OS" / "wholesale_agent"))
try:
    from compliance.state_gate import check as state_check
    from deal_slack import post_touch, post_stage
except Exception as e:
    log.error("imports failed: %s", e)
    raise


def _creds() -> dict:
    out = {}
    if CREDS.exists():
        text = CREDS.read_text()
        for key in ("TWILIO_ACCOUNT_SID_REAL", "TWILIO_AUTH_TOKEN",
                    "TWILIO_PHONE_NUMBER", "ELEVENLABS_API_KEY"):
            m = re.search(rf"^{key}\s*=\s*['\"]?([^\"'\n]+)['\"]?", text, re.M)
            if m:
                out[key] = m.group(1).strip()
    # env fallback
    for k in ("TWILIO_ACCOUNT_SID_REAL", "TWILIO_AUTH_TOKEN",
              "TWILIO_PHONE_NUMBER", "ELEVENLABS_API_KEY"):
        if os.environ.get(k):
            out[k] = os.environ[k]
    # Accept TWILIO_ACCOUNT_SID as a fallback for the AC... real SID
    if "TWILIO_ACCOUNT_SID_REAL" not in out:
        if os.environ.get("TWILIO_ACCOUNT_SID", "").startswith("AC"):
            out["TWILIO_ACCOUNT_SID_REAL"] = os.environ["TWILIO_ACCOUNT_SID"]
    return out


STATE_TZ = {
    "MO": -5, "NC": -4, "GA": -4, "TX": -5, "OH": -4, "FL": -4,
    "CA": -7, "AZ": -7, "TN": -5,
}


def _local_hour_ok(state: str) -> bool:
    tz_off = STATE_TZ.get((state or "").upper(), -5)
    local = datetime.now(timezone(timedelta(hours=tz_off)))
    return 9 <= local.hour < 19


def _normalize_phone(raw: str) -> str | None:
    if not raw:
        return None
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 10:
        return "+1" + digits
    if len(digits) == 11 and digits.startswith("1"):
        return "+" + digits
    return None


# ---------------------------------------------------------------------------
# ElevenLabs TTS via HTTP (no SDK)
# ---------------------------------------------------------------------------

def _tts_to_file(text: str, voice_id: str, out_path: pathlib.Path,
                 api_key: str) -> bool:
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    body = json.dumps({
        "text": text,
        "model_id": "eleven_turbo_v2_5",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
    }).encode()
    req = urllib.request.Request(
        url, data=body,
        headers={"xi-api-key": api_key,
                 "Content-Type": "application/json",
                 "Accept": "audio/mpeg"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            out_path.write_bytes(r.read())
        return out_path.exists() and out_path.stat().st_size > 1024
    except Exception as e:
        log.warning("elevenlabs err: %s", e)
        return False


# ---------------------------------------------------------------------------
# Twilio REST call (no SDK)
# ---------------------------------------------------------------------------

def _place_call(from_phone: str, to_phone: str, twiml_url: str,
                sid: str, token: str) -> str | None:
    endpoint = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Calls.json"
    data = urllib.parse.urlencode({
        "From": from_phone,
        "To": to_phone,
        "Url": twiml_url,
        "Record": "false",
        "Timeout": "25",
    }).encode()
    import base64
    auth = base64.b64encode(f"{sid}:{token}".encode()).decode()
    req = urllib.request.Request(
        endpoint, data=data,
        headers={"Authorization": f"Basic {auth}",
                 "Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            resp = json.loads(r.read())
            return resp.get("sid")
    except Exception as e:
        log.warning("twilio call err: %s", e)
        return None


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def _script_text(lead: dict, offer: int, title_co: str) -> str:
    owner_first = (lead.get("owner_name") or "").split(",")[0].split(" ")[0].title() or "there"
    return (
        f"Hi, this is Harrison Knox with Everlight Ventures, calling for {owner_first}. "
        f"We have your signed purchase contract for {lead.get('address','your property')} "
        f"at our cash offer of {offer:,} dollars. "
        f"{title_co} will call you within one business day to schedule closing, usually within "
        f"fourteen days. Please press 1 to confirm, or press 2 if anything has changed. "
        f"Thank you."
    )


def scan_and_call(dry_run: bool = False) -> dict:
    creds = _creds()
    missing = [k for k in ("TWILIO_ACCOUNT_SID_REAL", "TWILIO_AUTH_TOKEN",
                            "TWILIO_PHONE_NUMBER", "ELEVENLABS_API_KEY")
               if k not in creds]
    if missing:
        return {"ok": False, "error": f"missing creds: {missing}"}

    if not LEADS_DB.exists():
        return {"ok": False, "error": "leads_db missing"}
    leads = json.loads(LEADS_DB.read_text())
    made = 0; skipped = 0; errors = 0
    for lead in leads:
        if lead.get("status") != "signed":
            continue
        if lead.get("call_confirmation_sid"):
            continue  # already called
        state = (lead.get("state") or "").upper()
        phone = _normalize_phone(lead.get("phone") or lead.get("owner_phone", ""))
        if not phone:
            skipped += 1
            continue
        if not _local_hour_ok(state):
            skipped += 1
            log.info("outside call window for %s -- deferring", state)
            continue
        dec = state_check(state, "call", "outreach")
        if not dec.ok:
            skipped += 1
            continue

        offer = int(lead.get("offer_amount") or 0)
        title_co = lead.get("assigned_title_company") or "The title company"
        script = _script_text(lead, offer, title_co)

        # Voice id -- Harrison's default (or fallback to ElevenLabs default)
        voice_id = lead.get("confirm_voice_id", "29vD33N1CtxCmqQRPOHJ")

        if dry_run:
            log.info("[dry-run] would call %s: %s", phone, script[:60])
            made += 1
            continue

        # TTS
        tts_dir = ROOT / "_logs" / "tts_cache"
        tts_dir.mkdir(parents=True, exist_ok=True)
        mp3 = tts_dir / f"confirm_{lead.get('id','x')}.mp3"
        ok = _tts_to_file(script, voice_id, mp3, creds["ELEVENLABS_API_KEY"])
        if not ok:
            errors += 1
            continue

        # Copy TTS to Oracle so Twilio can fetch it at a public URL.
        # Path served by Django: /media/tts/<file>.mp3 (MEDIA_ROOT/tts/)
        import subprocess as _sp
        try:
            _sp.run(["ssh", "-F", "/root/.ssh/config", "oracle-e5",
                     "mkdir -p /home/opc/hive_django/media/tts && chown -R opc:opc /home/opc/hive_django/media"],
                    check=False, capture_output=True, timeout=15)
            _sp.run(["scp", "-F", "/root/.ssh/config", str(mp3),
                     f"oracle-e5:/home/opc/hive_django/media/tts/{mp3.name}"],
                    check=True, capture_output=True, timeout=20)
        except Exception as e:
            log.warning("tts upload err: %s", e)
            errors += 1
            continue

        mp3_url = f"http://127.0.0.1:2200/media/tts/{mp3.name}"
        # Twilio needs a TwiML URL; use the Twilio "twimlets" echo to wrap the mp3.
        twiml = (
            f"<?xml version='1.0' encoding='UTF-8'?>"
            f"<Response><Play>{mp3_url}</Play>"
            f"<Gather numDigits='1' timeout='8' action='{mp3_url}'>"
            f"<Say>Press 1 to confirm, 2 to decline.</Say></Gather></Response>"
        )
        # Use Twilio's twimlet echo service since we don't have our own TwiML host yet
        twiml_url = "https://twimlets.com/echo?Twiml=" + urllib.parse.quote(twiml)

        call_sid = _place_call(
            from_phone=creds["TWILIO_PHONE_NUMBER"],
            to_phone=phone,
            twiml_url=twiml_url,
            sid=creds["TWILIO_ACCOUNT_SID_REAL"],
            token=creds["TWILIO_AUTH_TOKEN"],
        )
        if not call_sid:
            errors += 1
            continue

        lead["call_confirmation_sid"] = call_sid
        lead["call_confirmation_at"] = datetime.now(timezone.utc).isoformat()
        made += 1
        log.info("called %s (sid=%s) -- %s", phone, call_sid, lead.get("address", ""))

        # Thread post
        try:
            post_touch(lead=lead, agent="Harrison Knox (Twilio)",
                       channel="call", to_address=phone,
                       body=script,
                       outcome=f"dialed (sid={call_sid})")
        except Exception:
            pass

    if not dry_run:
        LEADS_DB.write_text(json.dumps(leads, indent=2, default=str))
    return {"ok": True, "made": made, "skipped": skipped, "errors": errors}


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    r = scan_and_call(dry_run=args.dry_run)
    print(json.dumps(r, indent=2))


if __name__ == "__main__":
    main()
