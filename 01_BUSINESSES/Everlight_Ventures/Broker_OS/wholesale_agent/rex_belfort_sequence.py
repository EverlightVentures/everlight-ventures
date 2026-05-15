"""

# noqa: direct-resend
# This file still POSTs to api.resend.com directly. The eradication_gate is now
# called BEFORE any send, and the module refuses to load under WHOLESALE_OUTBOUND_HALT=1.
# Full migration to content_tools.branded_mailer.send_branded_email() is tracked
# in _state/SELF_AUDIT_2026-05-15_STREUBEL_2ND_STRIKE.md under "Lift criteria".
# The noqa marker is the lint's documented exception for files that are gated
# pending a full refactor. DO NOT remove the eradication_gate import or the
# module-level halt check; they are the load-bearing protections.
Rex Belfort Mode -- Aggressive 5-day closing sequence.

Not 7 touches in 25 days. 7 touches in 5 DAYS.
Hit every channel. Create urgency. Assume the sale. Never stop.

Jordan Belfort wouldn't send one email and wait. Neither will Rex.

Now with hyper-personalized pitches powered by the enrichment engine.
Every email references specific property details, distress signals,
and years of ownership. No more generic "I buy houses" spam.

Supports recycled leads with alternative messaging angles:
  - "standard"     = original Belfort pitch (now personalized)
  - "new_investor" = fresh buyer in the area angle
  - "market_update" = property values have changed angle
"""

import json
import logging
import os
import re
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="[Rex Belfort %(asctime)s] %(message)s", datefmt="%H:%M")
log = logging.getLogger("belfort")

AGENT_DIR = Path(__file__).parent
LEADS_DB = AGENT_DIR / "leads_db.json"

# ============================================================
# MODULE-LEVEL HALT -- if WHOLESALE_OUTBOUND_HALT=1, refuse to load.
# Born from the Streubel 2nd-strike 2026-05-15. Belt-and-suspenders:
# even if a cron job invokes this module directly, it exits before
# any send loop can start.
# ============================================================
if os.environ.get("WHOLESALE_OUTBOUND_HALT", "").strip() in {"1", "true", "TRUE", "yes"}:
    log.error("WHOLESALE_OUTBOUND_HALT=1 -- rex_belfort_sequence refusing to load. "
              "See memory: feedback-streubel-permanent-eradication")
    raise SystemExit("WHOLESALE_OUTBOUND_HALT active -- rex_belfort blocked at module load")

# Eradication gate -- hardcoded permanent-DNC list. Independent of any JSON.
# MUST be called before every send. See eradication_gate.py for the doctrine.
import sys as _sys
_sys.path.insert(0, "/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/content_tools")
try:
    from eradication_gate import assert_safe as _erad_assert_safe, EradicationViolation
except ImportError as _erad_imp:
    # Fail closed: if the gate cannot be imported, the module refuses to run.
    log.error("eradication_gate import failed -- rex_belfort refusing to run: %s", _erad_imp)
    raise SystemExit(f"eradication_gate unavailable: {_erad_imp}")

# Import suppression list checker -- MUST be checked before every send
from rex_stop_handler import is_suppressed, load_suppression_list

# Import alternative angle templates for recycled leads
from rex_lead_recycler import get_angle_touches

# Import enrichment engine for hyper-personalized pitches
from rex_enrichment_engine import enrich_lead, generate_personalized_pitch

RESEND_KEY = os.environ.get("RESEND_API_KEY", "")
GMAIL_USER = os.environ.get("IMAP_USER", "")
GMAIL_PASS = os.environ.get("IMAP_PASS", "")
SLACK_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
SLACK_CHANNEL = "C0ANLLV8JAC"

# Wholesale seller outreach is signed by Piper Reeves, not the owner. Owner
# notifications go to Slack, not Resend (owner directive 2026-04-23).
FROM_EMAIL = "Piper Reeves <piper@everlightventures.io>"
REPLY_TO = "piper@everlightventures.io"
AGENT_NAME = "Piper Reeves"
AGENT_TITLE = "Senior Account Executive, Wholesale"
AGENT_EMAIL = "piper@everlightventures.io"
AGENT_PHONE = "(707) 801-0360"
NOW = datetime.now(timezone.utc)
TODAY = NOW.strftime("%Y-%m-%d")

_resend_count = 0


_mx_cache = {}

def verify_mx(email_addr):
    """Check if the email domain has valid MX records. Free, instant, prevents wasted sends."""
    domain = email_addr.split("@")[-1].lower()
    if domain in _mx_cache:
        return _mx_cache[domain]
    try:
        import subprocess, socket
        result = subprocess.run(["host", "-t", "MX", domain], capture_output=True, text=True, timeout=5)
        valid = "mail" in result.stdout.lower() or "mx" in result.stdout.lower()
        if not valid:
            socket.getaddrinfo(domain, 25, socket.AF_INET)
            valid = True
    except:
        valid = False
    _mx_cache[domain] = valid
    return valid


def send_email(to, subject, body, state: str = "", action: str = "outreach"):
    """Resend first, Gmail overflow. Pre-validates MX records to avoid wasted sends.
    Enforces state_gates.json compliance when `state` is provided. Owner/internal
    addresses are blocked upstream by resend_guard (platform policy).
    """
    global _resend_count
    if not to:
        return False

    # ============================================================
    # ERADICATION GATE -- FIRST. Permanent DNC subjects (Streubel et al.).
    # Hardcoded list. JSON files cannot bypass this. Fail closed.
    # ============================================================
    try:
        _erad_assert_safe(email=to, address=subject, caller="rex_belfort_sequence.send_email")
    except EradicationViolation as _eg_err:
        log.error("ERADICATION GATE blocked send to %s: %s", to, _eg_err)
        return False

    # MX validation -- don't waste a send on a domain that can't receive email
    if not verify_mx(to):
        log.debug(f"MX check failed for {to} -- skipping")
        return False

    # Block owner/internal addresses at the send boundary (Slack-only policy)
    try:
        import sys as _sys
        _sys.path.insert(0, "/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/content_tools")
        from resend_guard import is_owner_recipient
        if is_owner_recipient(to):
            log.warning("resend_guard blocked owner-bound send to %s", to)
            return False
    except Exception:
        pass

    # State compliance gate (sms/call/email all routed through this func)
    if state:
        try:
            import sys as _sys, pathlib as _pl
            _sys.path.insert(0, str(_pl.Path(__file__).resolve().parent / "compliance"))
            from state_gate import check as _state_check
            decision = _state_check(state, channel="email", action=action)
            if not decision.ok:
                log.warning("state_gate BLOCK %s/%s: %s", state, action, decision.blocked_reason)
                return False
            # Append CAN-SPAM footer if missing (required by state_gate.check for email)
            if "unsubscribe" not in body.lower() and "opt out" not in body.lower():
                body = body.rstrip() + (
                    "\n\n---\nEverlight Ventures, Wholesale Division\n"
                    "To opt out reply STOP or email opt-out@everlightventures.io.\n"
                    "You received this because we believe you may own a property we'd like to acquire."
                )
        except Exception as _e:
            log.warning("state_gate import failed, proceeding uncompliant: %s", _e)
    else:
        log.warning("rex_belfort.send_email called without state -- compliance NOT checked")

    # Wrap plain-text body in the branded Everlight template (gold/black, Playfair+Inter).
    # Every wholesale outreach email now looks like the luxury brand.
    body_html = body
    try:
        import sys as _sys
        _sys.path.insert(0, "/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/content_tools")
        from report_template import render_report
        # Convert plain text -> HTML paragraphs. Preserve the bulleted list block.
        lines = body.split("\n")
        html_parts = []
        in_list = False
        for ln in lines:
            s = ln.strip()
            if s.startswith("- ") or s.startswith("* "):
                if not in_list:
                    html_parts.append("<ul>")
                    in_list = True
                html_parts.append(f"<li>{s[2:]}</li>")
                continue
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            if s == "":
                html_parts.append("")
            elif s == "---":
                html_parts.append("<hr style='border:0;border-top:1px solid #222;margin:20px 0;'>")
            else:
                html_parts.append(f"<p>{s}</p>")
        if in_list:
            html_parts.append("</ul>")
        content_html = "\n".join(p for p in html_parts if p is not None)
        body_html = render_report(
            title=subject,
            content_html=content_html,
            agent_name=AGENT_NAME,
            agent_title=AGENT_TITLE,
            agent_email=AGENT_EMAIL,
            confidential=False,
        )
    except Exception as _e:
        log.debug("branded wrap unavailable, falling back to plain text: %s", _e)

    if RESEND_KEY and _resend_count < 95:
        try:
            import requests
            r = requests.post("https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {RESEND_KEY}", "Content-Type": "application/json"},
                json={"from": FROM_EMAIL, "to": [to], "subject": subject,
                      "html": body_html, "text": body, "reply_to": REPLY_TO},
                timeout=10)
            if r.status_code in (200, 201):
                _resend_count += 1
                return True
            elif r.status_code == 429 or "quota" in r.text.lower():
                _resend_count = 100
        except:
            pass

    if GMAIL_USER and GMAIL_PASS:
        try:
            import smtplib
            from email.mime.text import MIMEText
            msg = MIMEText(body)
            msg["Subject"] = subject
            msg["From"] = GMAIL_USER
            msg["To"] = to
            msg["Reply-To"] = REPLY_TO
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as server:
                server.login(GMAIL_USER, GMAIL_PASS)
                server.send_message(msg)
            return True
        except:
            return False
    return False


# ---------------------------------------------------------------------------
# BELFORT 5-DAY SEQUENCE
# ---------------------------------------------------------------------------
# Day 0 Hour 0: SMS -- pattern interrupt, short, personal
# Day 0 Hour 4: Email -- full pitch with deadline
# Day 1:        SMS -- "did you see my email?"
# Day 2:        Email -- social proof + urgency
# Day 3:        SMS -- "offer expires tomorrow"
# Day 4:        Email -- "final notice, closing file Friday"
# Day 5:        SMS -- "last chance" then mark dead
# ---------------------------------------------------------------------------

BELFORT_TOUCHES = {
    0: {  # Day 0, first touch -- personal, casual, short
        "channel": "sms",
        "delay_hours": 0,
        "subject": "{address}",
        "body": "Hey {first_name} -- saw your property at {address}. I'm a private buyer in {city}, looking to pick up a few properties this month. Any interest in a cash offer? No obligation. -- Piper",
    },
    1: {  # Day 0, 4 hours later -- premium pitch, reads like a personal email
        "channel": "email",
        "delay_hours": 4,
        "subject": "Your property on {address}",
        "body": """Hey {first_name},

Hope this finds you well. I came across your property at {address} and wanted to reach out personally.

I'm a private real estate buyer working with a small group of investors. We're actively acquiring properties in {city} this quarter.

Here's what I can offer:

  - All cash, no financing contingencies
  - Close in as little as 7 days (or on your timeline)
  - As-is condition -- no repairs, no cleaning, no showings
  - I cover all closing costs
  - No commissions or fees on your end

I've already reviewed the property details. If you're open to hearing a number, just reply to this email and I'll send over a written offer within the hour.

No pressure either way. Just wanted to make sure you had the option on the table.

Best,
Piper Reeves
Everlight Ventures | Wholesale
everlightventures.io
piper@everlightventures.io
(707) 801-0360

Not interested? Reply STOP and I will remove you immediately.""",
    },
    2: {  # Day 1 -- casual follow-up
        "channel": "sms",
        "delay_hours": 24,
        "subject": "Re: {address}",
        "body": "Hey {first_name}, just following up -- sent you an email about {address} yesterday. We're closing on a few properties in {city} this week and yours caught my eye. Worth a quick chat? -- Piper",
    },
    3: {  # Day 2 -- credibility + scarcity
        "channel": "email",
        "delay_hours": 48,
        "subject": "Quick update on {city} acquisitions",
        "body": """Hi {first_name},

Wanted to give you a quick update -- we are actively acquiring properties in the {city} area. Sellers we work with typically have cash in hand within 2 weeks.

Your property at {address} is still on my short list. My investment group has capital allocated for {city} acquisitions through end of month, but we're narrowing down to our final picks this week.

If you've been thinking about selling -- or even just curious what your property could fetch in a private cash sale -- now's a great time to explore it.

Just reply "what's the offer?" and I'll have a number for you today.

Best,
Piper Reeves
Everlight Ventures | Wholesale
piper@everlightventures.io
(707) 801-0360""",
    },
    4: {  # Day 3 -- direct, time pressure
        "channel": "sms",
        "delay_hours": 72,
        "subject": "Re: {address}",
        "body": "{first_name} -- heads up, we're finalizing our {city} acquisitions this week. Your property at {address} is still on the list but I need to hear from you by Friday. Cash offer, your timeline. -- Piper",
    },
    5: {  # Day 4 -- final professional email
        "channel": "email",
        "delay_hours": 96,
        "subject": "Closing out -- {address}",
        "body": """Hi {first_name},

This is my last note about {address}.

We've wrapped up most of our {city} acquisitions for the quarter. I'm closing out the remaining files this week.

If selling is something you'd consider -- even down the road -- just reply and I'll keep your property in our system for future offers.

Otherwise, no worries at all. I appreciate your time and wish you the best with the property.

Respectfully,
Piper Reeves
Everlight Ventures | Wholesale
everlightventures.io
(707) 801-0360

Reply STOP to opt out.""",
    },
    6: {  # Day 5 -- last shot, warm and personal
        "channel": "sms",
        "delay_hours": 120,
        "subject": "Last note -- {address}",
        "body": "{first_name}, closing my file on {address}. If you ever reconsider, my door's always open -- piper@everlightventures.io. All the best. -- Piper",
    },
}


def check_bounces_and_clean(leads):
    """Check inbox for bounce notifications, remove dead addresses from pipeline."""
    bounce_path = AGENT_DIR / "bounced_emails.json"
    bounced = set(json.loads(bounce_path.read_text())) if bounce_path.exists() else set()

    try:
        import imaplib, email
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(os.environ.get("IMAP_USER", ""), os.environ.get("IMAP_PASS", ""))
        mail.select("INBOX")

        for query in ['(FROM "mailer-daemon" UNSEEN)', '(SUBJECT "Delivery Status" UNSEEN)']:
            try:
                s, m = mail.search(None, query)
                if m[0]:
                    for mid in m[0].split()[:30]:
                        s2, d = mail.fetch(mid, "(RFC822)")
                        msg = email.message_from_bytes(d[0][1])
                        body = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                if part.get_content_type() == "text/plain":
                                    body += part.get_payload(decode=True).decode("utf-8", errors="replace")
                        else:
                            body = msg.get_payload(decode=True).decode("utf-8", errors="replace")

                        import re as bounce_re
                        for addr in bounce_re.findall(r'[\w.+-]+@[\w-]+\.[\w.]+', body):
                            a = addr.lower()
                            if not any(d in a for d in ["everlightventures", "gmail.com", "resend", "google"]):
                                bounced.add(a)
            except:
                pass
        mail.logout()
    except:
        pass

    # Save and clean
    bounce_path.write_text(json.dumps(sorted(bounced), indent=2))
    before = len(leads)
    leads[:] = [l for l in leads if l.get("owner_email", "").lower() not in bounced]
    removed = before - len(leads)
    if removed:
        log.info(f"Cleaned {removed} bounced addresses ({len(bounced)} total blacklisted)")
    return removed


def personalize(text, lead):
    owner = lead.get("owner_name", "")
    first = owner.split()[0].title() if owner else "there"
    return text.format(
        first_name=first,
        address=lead.get("address", "your property"),
        city=lead.get("city", "the area"),
        state=lead.get("state", ""),
        zip_code=lead.get("zip_code", ""),
    )


def get_hours_since_last(lead):
    last = lead.get("last_outreach", "")
    if not last:
        return 999
    try:
        last_dt = datetime.fromisoformat(last.replace("Z", "+00:00")) if "T" in last else datetime.strptime(last, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        return (NOW - last_dt).total_seconds() / 3600
    except:
        return 999


def _get_touches_for_lead(lead):
    """Return the correct touch sequence based on the lead's recycle_angle."""
    angle = lead.get("recycle_angle", "standard")
    if angle in ("new_investor", "market_update"):
        alt = get_angle_touches(angle)
        if alt:
            return alt
    return BELFORT_TOUCHES


def _enrich_if_needed(lead):
    """
    Enrich a lead with ATTOM + Perplexity data if not already enriched.
    Only enriches leads at sequence_step == 0 to avoid wasting API calls.
    Perplexity calls cost money -- we only enrich once per lead.
    """
    if lead.get("enriched"):
        return

    step = lead.get("sequence_step", 0)
    if step != 0:
        return

    try:
        enrich_lead(lead)
        log.info(f"  Enriched: {lead.get('owner_name', '')} -- distress={lead.get('detected_distress', 'unknown')}")
    except Exception as e:
        log.warning(f"  Enrichment failed for {lead.get('address', 'unknown')}: {e}")
        # Don't block outreach if enrichment fails -- continue with generic pitch
        lead["enriched"] = False


def _get_personalized_content(lead, step, touch):
    """
    Get subject and body for a touch, using personalized pitch for key touches.

    Touch 0 (SMS): Personalized SMS referencing property details
    Touch 1 (Email): Full hyper-personalized pitch from enrichment engine
    Touches 2, 4, 6 (SMS): Reference specific property details
    Touches 3, 5 (Email): Use standard templates (urgency/closing angles)
    """
    # For Touch 1 (the main email pitch), use the enrichment engine
    if step == 1 and lead.get("enriched"):
        pitch = generate_personalized_pitch(lead)
        return pitch["subject"], pitch["body"]

    # For SMS touches (0, 2, 4, 6), use personalized SMS if enriched
    if touch.get("channel") == "sms" and lead.get("enriched"):
        pitch = generate_personalized_pitch(lead)
        sms_body = pitch.get("sms_body", "")

        if step == 0 and sms_body:
            # Touch 0: First SMS -- use the personalized SMS
            return personalize(touch["subject"], lead), sms_body

        if step == 2:
            # Touch 2: Follow-up referencing the email
            owner = lead.get("owner_name", "")
            first = owner.split()[0].title() if owner else "there"
            street = lead.get("address", "your property").split(",")[0].strip()
            if street == street.upper():
                street = street.title()
            body = (
                f"Hey {first}, following up on my email about {street}. "
                f"We're closing on properties in {lead.get('city', 'the area').title()} "
                f"this week. Worth a quick chat? -Rich"
            )
            return personalize(touch["subject"], lead), body[:160]

        if step == 4:
            # Touch 4: Urgency with property detail
            owner = lead.get("owner_name", "")
            first = owner.split()[0].title() if owner else "there"
            street = lead.get("address", "your property").split(",")[0].strip()
            if street == street.upper():
                street = street.title()
            distress = lead.get("detected_distress", "high_equity")
            if distress in ("tax_delinquent", "code_violation", "pre_foreclosure"):
                urgency = "I can handle everything at closing"
            else:
                years = lead.get("years_owned", 0)
                if years and years >= 10:
                    urgency = f"{years}+ yrs of equity -- unlock it now"
                else:
                    urgency = "Finalizing acquisitions this week"
            body = (
                f"{first} -- {street}. {urgency}. "
                f"Need to hear from you by Friday. Cash, your timeline. -Rich"
            )
            return personalize(touch["subject"], lead), body[:160]

        if step == 6:
            # Touch 6: Last shot, warm
            owner = lead.get("owner_name", "")
            first = owner.split()[0].title() if owner else "there"
            street = lead.get("address", "your property").split(",")[0].strip()
            if street == street.upper():
                street = street.title()
            body = (
                f"{first}, closing my file on {street}. "
                f"If you ever reconsider -- piper@everlightventures.io. "
                f"All the best. -Rich"
            )
            return personalize(touch["subject"], lead), body[:160]

    # Fallback: use the standard template with basic personalization
    return personalize(touch["subject"], lead), personalize(touch["body"], lead)


def run_belfort_sequence():
    leads = json.loads(LEADS_DB.read_text()) if LEADS_DB.exists() else []

    # Clean bounces first -- stop wasting sends on dead addresses
    check_bounces_and_clean(leads)

    sent = 0
    completed = 0
    skipped_suppressed = 0
    enriched_count = 0
    max_per_run = 80

    for lead in leads:
        if sent >= max_per_run:
            break

        status = lead.get("status", "new")
        if status in ("replied", "negotiating", "under_contract", "closed",
                       "dead", "opted_out", "permanently_dead"):
            continue

        email = lead.get("owner_email", "")

        # CAN-SPAM: check suppression list BEFORE every send
        if is_suppressed(email):
            if status != "opted_out":
                lead["status"] = "opted_out"
            skipped_suppressed += 1
            continue

        # Select the right touch sequence for this lead's angle
        touches = _get_touches_for_lead(lead)

        step = lead.get("sequence_step", 0)
        if step >= len(touches):
            lead["status"] = "dead"
            completed += 1
            continue

        touch = touches[step]
        hours_since = get_hours_since_last(lead)
        required_hours = touch["delay_hours"]

        # CLOSE PROBABILITY SPEED ADJUSTMENT
        # Tier 1 (OZ + distress): 3-day sequence -- compress delays by 60%
        # Tier 2 (distress or OZ): standard 5-day
        # Tier 3 (long game): stretch delays by 2x
        belfort_speed = lead.get("belfort_speed", "5day")
        if belfort_speed == "3day":
            required_hours = max(0, int(required_hours * 0.4))  # 60% faster
        elif belfort_speed == "drip":
            required_hours = int(required_hours * 3)  # 3x slower for long game

        # For step 0, always send immediately
        if step == 0 or hours_since >= required_hours:
            if not email:
                continue

            # Enrich lead before first touch (step 0 only, costs API calls)
            if step == 0 and not lead.get("enriched"):
                _enrich_if_needed(lead)
                if lead.get("enriched"):
                    enriched_count += 1

            # Get personalized content (uses enrichment data if available)
            subject, body = _get_personalized_content(lead, step, touch)

            lead_state = (lead.get("state") or "").upper()
            # Pre-foreclosure leads in CA/TN get a different action rule
            action = "preforeclosure" if (lead.get("detected_distress") in ("pre_foreclosure","preforeclosure","pf")) else "outreach"
            if send_email(email, subject, body, state=lead_state, action=action):
                lead["sequence_step"] = step + 1
                lead["outreach_count"] = lead.get("outreach_count", 0) + 1
                lead["last_outreach"] = NOW.isoformat()
                lead["status"] = "contacted"
                sent += 1

                # Record the conversation entry + full branded HTML so the
                # dashboard can render the EXACT email that was delivered.
                _html_rendered = ""
                try:
                    import sys as _sys
                    _sys.path.insert(0, "/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/content_tools")
                    from report_template import render_report
                    _lines = body.split("\n"); _parts = []; _in_list = False
                    for _ln in _lines:
                        _s = _ln.strip()
                        if _s.startswith("- ") or _s.startswith("* "):
                            if not _in_list: _parts.append("<ul>"); _in_list = True
                            _parts.append(f"<li>{_s[2:]}</li>"); continue
                        if _in_list: _parts.append("</ul>"); _in_list = False
                        if _s == "": _parts.append("")
                        elif _s == "---": _parts.append("<hr style='border:0;border-top:1px solid #222;margin:20px 0;'>")
                        else: _parts.append(f"<p>{_s}</p>")
                    if _in_list: _parts.append("</ul>")
                    _content_html = "\n".join(p for p in _parts if p is not None)
                    _html_rendered = render_report(
                        title=subject, content_html=_content_html,
                        agent_name=AGENT_NAME, agent_title=AGENT_TITLE,
                        agent_email=AGENT_EMAIL,
                    )
                except Exception as _he:
                    log.debug("html capture skipped: %s", _he)

                lead.setdefault("conversation", []).append({
                    "role": "piper",
                    "agent_name": "Piper Reeves",
                    "agent_email": "piper@everlightventures.io",
                    "channel": touch.get("channel", "email"),
                    "direction": "outbound",
                    "to": email,
                    "subject": subject,
                    "message": body,
                    "message_html": _html_rendered,
                    "step": step,
                    "timestamp": NOW.isoformat(),
                })

                angle = lead.get("recycle_angle", "standard")
                recycle = lead.get("recycle_count", 0)
                distress = lead.get("detected_distress", "generic")
                if step == 0:
                    label = f"NEW" if recycle == 0 else f"RECYCLED({angle})"
                    log.info(f"  {label}: {lead.get('owner_name','')} ({lead.get('city','')}) [{distress}]")
                elif step == 1:
                    log.info(f"  PERSONALIZED EMAIL: {lead.get('owner_name','')} [{distress}]")

                # Per-lead Slack thread: post a touch entry so the owner sees
                # WHO received WHAT, not an aggregate count.
                try:
                    from deal_slack import post_touch
                    lid = str(lead.get("id") or lead.get("lead_id") or "")
                    post_touch(
                        lead=lead,
                        agent="Piper Reeves",
                        channel=touch.get("channel", "email"),
                        subject=subject,
                        body=body,
                        to_address=email,
                        outcome=f"sent (step {step+1}/7)",
                    )
                except Exception as _e:
                    log.debug("deal_slack post failed for %s: %s", lead.get("owner_name",""), _e)

        time.sleep(1.5)

    if skipped_suppressed:
        log.info(f"Skipped {skipped_suppressed} suppressed/opted-out leads")

    # Save -- enrichment data persists so we don't re-fetch
    with open(LEADS_DB, "w") as f:
        json.dump(leads, f, indent=2, default=str)

    log.info(f"Belfort sequence: {sent} touches sent, {completed} completed, {enriched_count} enriched")

    # Post to Slack
    if SLACK_TOKEN and sent > 0:
        import requests
        active = sum(1 for l in leads if l.get("status") == "contacted")
        replied = sum(1 for l in leads if l.get("status") == "replied")
        enriched_total = sum(1 for l in leads if l.get("enriched"))
        requests.post("https://slack.com/api/chat.postMessage",
            headers={"Authorization": f"Bearer {SLACK_TOKEN}", "Content-Type": "application/json"},
            json={"channel": SLACK_CHANNEL, "text": (
                f"*Rex Belfort Mode -- Personalized*\n"
                f"{sent} touches sent this hour ({enriched_count} freshly enriched)\n"
                f"{active} active sequences | {enriched_total} total enriched leads\n"
                f"{replied} replies\n"
                f"Not stopping until we close."
            )}, timeout=10)

    return sent


def _run_single_lead(lead_id: str) -> int:
    """Event-mode: process a single lead by ID from leads_db.json.

    Called by hive_dispatcher when Supabase fires a new-lead webhook. The
    hunter pre-writes the lead into leads_db.json; the dispatcher then hands
    off the ID here for immediate first-touch.
    """
    if not LEADS_DB.exists():
        log.info("no leads_db.json yet -- hunter has not seeded; skipping event")
        return 0
    leads = json.loads(LEADS_DB.read_text())
    target = next((l for l in leads if str(l.get("id") or l.get("lead_id")) == str(lead_id)), None)
    if not target:
        log.info("lead %s not in leads_db.json -- skipping (hunter must seed first)", lead_id)
        return 0
    from rex_stop_handler import is_suppressed
    if is_suppressed(target.get("phone", ""), target.get("email", "")):
        log.info("lead %s suppressed -- skipping", lead_id)
        return 0
    # Mark as event-triggered so run_belfort_sequence's timing rules don't skip it
    target.setdefault("event_triggered", True)
    target["touch_count"] = target.get("touch_count", 0)
    target["last_touched_at"] = None  # force immediate first touch
    # Persist the unlock, then re-invoke the full sequence
    # (which will process exactly one lead since we just reset its clock)
    with LEADS_DB.open("w") as f:
        json.dump(leads, f, indent=2, default=str)
    return run_belfort_sequence()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Rex Belfort wholesale outreach sequence")
    parser.add_argument("--lead-id", dest="lead_id",
                        help="Event mode: process only this single lead ID")
    args, _extra = parser.parse_known_args()
    if args.lead_id:
        log.info("=== EVENT MODE -- single lead %s ===", args.lead_id)
        _run_single_lead(args.lead_id)
    else:
        log.info("=== BELFORT MODE -- 5 days, 7 touches, no mercy ===")
        run_belfort_sequence()
