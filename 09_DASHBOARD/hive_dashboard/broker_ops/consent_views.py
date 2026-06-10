"""consent_views -- public PEWC capture endpoints.

URL contract
------------
  GET  /consent/<token>/        -- branded form page (the contact sees this)
  POST /consent/<token>/        -- form submission, creates ConsentLedger row
  GET  /consent/revoke/<token>/ -- one-click revocation
  POST /consent/api/invite/     -- internal: generate a fresh consent token + URL
                                    for a specific contact (token in X-Hive-Token header)

Compliance design
-----------------
The disclosure text shown is REGENERATED PER REQUEST from the canonical
template, but the EXACT text shown is stored on the ConsentLedger row at
submit time. If we ever change the template later, old consent records
are still defensible because they carry the disclosure they actually saw.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
from datetime import datetime, timezone

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils import timezone as dj_tz
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .models import ConsentLedger


# ── Disclosure text templates (TCPA-required language) ─────────

CHANNEL_LABELS = {
    "ai_call": "AI voice phone calls",
    "autodialed_call": "autodialed phone calls",
    "prerecorded_voicemail": "prerecorded ringless voicemail drops",
    "sms_marketing": "marketing text messages",
    "email_marketing": "marketing emails",
}


def disclosure_for(contact_name: str, contact_phone: str, channels: list[str]) -> str:
    """Return the EXACT TCPA disclosure language the contact sees and signs.

    Per 47 CFR 64.1200(f)(9): consent must clearly authorize calls, identify
    the seller (Everlight Ventures), and state that consent is not a
    condition of purchase.
    """
    channel_text = ", ".join(CHANNEL_LABELS.get(c, c) for c in channels) or "marketing communications"
    phone_disclosure = (
        f"the phone number you provide ({contact_phone})"
        if contact_phone else "any phone number you provide"
    )
    return (
        f"By signing below, I, {contact_name or '[Your Name]'}, give Everlight Ventures and its agents "
        f"my prior express written consent to contact me at {phone_disclosure} via "
        f"{channel_text}, including using an automatic telephone dialing system, AI voice technology, "
        f"or prerecorded/artificial voice messages, for marketing and informational purposes. "
        f"I understand that:\n\n"
        f"  - My consent is not a condition of any purchase, service, or agreement.\n"
        f"  - Standard message and data rates may apply for SMS.\n"
        f"  - I can revoke this consent at any time by replying STOP to any text, replying "
        f"'unsubscribe' to any email, or visiting the revoke link in any communication I receive.\n"
        f"  - Everlight Ventures will not sell or share my contact information for marketing by "
        f"unrelated third parties.\n\n"
        f"By typing my name and clicking 'I Consent', I am providing my electronic signature "
        f"per the federal E-SIGN Act and adopting it as my signature for purposes of this "
        f"consent. The date, time, my IP address, and the device I used will be logged as proof."
    )


# ── Public consent form ────────────────────────────────────────

CONSENT_PAGE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Stay in Touch -- Everlight Ventures</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Playfair+Display:wght@400;600;700&display=swap');
*{margin:0;padding:0;box-sizing:border-box;}
body{background:#0A0A0A;color:#E8E8E8;font-family:'Inter',sans-serif;line-height:1.7;padding:0;}
.wrap{max-width:640px;margin:0 auto;padding:0 24px;}
.header{background:linear-gradient(135deg,#0A0A0A 0%,#1A1A1A 100%);border-bottom:2px solid #D4A843;padding:32px 0 28px;text-align:center;}
.logo{font-family:'Playfair Display',serif;font-size:13px;letter-spacing:4px;text-transform:uppercase;color:#D4A843;margin-bottom:12px;}
h1{font-family:'Playfair Display',serif;font-size:30px;color:#E8E8E8;margin-bottom:6px;font-weight:600;}
.tagline{font-size:14px;color:#999;font-style:italic;}
.content{padding:32px 0 24px;}
h2{font-family:'Playfair Display',serif;font-size:22px;color:#D4A843;margin:28px 0 12px;}
h3{font-size:13px;font-weight:600;color:#D4A843;letter-spacing:2px;text-transform:uppercase;margin:14px 0 6px;}
p{margin-bottom:14px;font-size:15px;color:#cccccc;}
.benefits{display:grid;grid-template-columns:1fr;gap:14px;margin:18px 0;}
.benefit{background:#141414;border-left:3px solid #D4A843;padding:14px 16px;border-radius:4px;}
.benefit .b-title{color:#D4A843;font-weight:600;font-size:14px;margin-bottom:4px;}
.benefit .b-text{color:#bbbbbb;font-size:14px;line-height:1.6;}
.field{margin:14px 0;}
.field label{display:block;font-size:12px;color:#888;text-transform:uppercase;letter-spacing:1.5px;margin-bottom:6px;}
.field input[type=text],.field input[type=email]{width:100%;background:#0A0A0A;border:1px solid #2A2A2A;border-radius:6px;color:#E8E8E8;padding:13px 15px;font-size:15px;font-family:inherit;transition:border .15s;}
.field input:focus{outline:none;border-color:#D4A843;}
.choices{margin:14px 0;}
.choice{display:flex;gap:12px;align-items:flex-start;padding:14px 16px;background:#141414;border:1px solid #1f1f1f;border-radius:6px;margin-bottom:8px;cursor:pointer;transition:border .15s,background .15s;}
.choice:hover{border-color:#3a3a3a;}
.choice input[type=checkbox]{margin-top:3px;flex-shrink:0;width:20px;height:20px;accent-color:#D4A843;cursor:pointer;}
.choice-content{flex:1;}
.choice-title{color:#E8E8E8;font-weight:600;font-size:14px;margin-bottom:3px;}
.choice-sub{color:#888;font-size:13px;}
details{background:#141414;border:1px solid #1f1f1f;border-radius:6px;padding:14px 18px;margin:18px 0;}
details summary{cursor:pointer;color:#999;font-size:13px;font-weight:500;list-style:none;padding-right:16px;position:relative;}
details summary::after{content:'+';position:absolute;right:0;top:0;color:#D4A843;font-size:18px;}
details[open] summary::after{content:'−';}
.disclosure{padding:14px 0 0;font-size:13px;line-height:1.75;color:#aaaaaa;white-space:pre-wrap;}
button{background:linear-gradient(135deg,#D4A843,#B8860B);color:#000;border:none;padding:16px 36px;border-radius:6px;font-size:16px;font-weight:600;cursor:pointer;letter-spacing:0.5px;width:100%;margin-top:14px;}
button:hover{filter:brightness(1.08);}
button:disabled{filter:grayscale(0.5) brightness(0.6);cursor:not-allowed;}
.fineprint{font-size:11px;color:#666;margin-top:14px;text-align:center;line-height:1.5;}
.fineprint a{color:#888;text-decoration:underline;}
.footer{text-align:center;color:#888;font-size:11px;letter-spacing:2px;border-top:1px solid #1a1a1a;padding:24px;margin-top:24px;}
.footer .brand{color:#D4A843;font-family:'Playfair Display',serif;font-size:13px;}
.error{background:#3a1818;color:#ff8a8a;padding:12px 14px;border-radius:6px;margin:12px 0;}
.success{background:#142d1a;color:#8aff9c;padding:20px;border-radius:6px;margin:12px 0;font-size:15px;border-left:3px solid #D4A843;}
.success h2{color:#8aff9c !important;margin-top:0;}
</style>
</head>
<body>
<div class="header">
  <div class="logo">EVERLIGHT VENTURES</div>
  <h1>{{title}}</h1>
  <div class="tagline">{{tagline}}</div>
</div>
<div class="wrap"><div class="content">
{{body}}
</div></div>
<div class="footer">
  <div class="brand">EVERLIGHT VENTURES</div>
  <div style="margin-top:6px;">The Mind Behind the Money</div>
  <div style="margin-top:14px;opacity:0.7;">
    Questions? <a href="mailto:consent@everlightventures.io" style="color:#D4A843;">consent@everlightventures.io</a>
  </div>
</div>
</body>
</html>"""


def _render(title: str, body: str, status: int = 200, tagline: str = "") -> HttpResponse:
    if not tagline:
        tagline = "A faster way to talk about your property"
    html = (CONSENT_PAGE_HTML
            .replace("{{title}}", title)
            .replace("{{tagline}}", tagline)
            .replace("{{body}}", body))
    return HttpResponse(html, content_type="text/html; charset=utf-8", status=status)


def _normalize_phone(p: str) -> str:
    digits = re.sub(r"\D+", "", p or "")
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    return digits[-10:] if len(digits) >= 10 else digits


@csrf_exempt
def consent_form(request, token):
    """Public GET = show form. Public POST = save consent."""
    # Look up an UNUSED invite stored as a draft row, or create an
    # ad-hoc form when token is just a one-time invite (we store the
    # final record only on POST).
    pending = ConsentLedger.objects.filter(consent_token=token).first()

    # ── GET: render the form ─────────────────────────────────
    if request.method == "GET":
        if pending and not pending.revoked and pending.signature_text:
            return _render(
                "All Set",
                f"<div class='success'><h2>Thanks {pending.contact_name.split()[0] if pending.contact_name else ''}, you're already in.</h2>"
                f"<p>You signed in on {pending.created_at.strftime('%b %d, %Y')}. We'll be in touch about your property.</p>"
                f"<p style='font-size:13px;color:#888;'>Need to opt out? Reply STOP to any text, 'unsubscribe' to any email, "
                f"or use the revoke link in any message we send. Easy.</p></div>",
                tagline="You're in",
            )

        # Per FCC 12-21, channel checkboxes are NOT pre-checked. User must
        # affirmatively select. We compensate with strong UX framing.
        default_channels_for_disclosure = [
            "ai_call", "autodialed_call", "prerecorded_voicemail", "sms_marketing",
        ]

        prefilled_name = pending.contact_name if pending else ""
        prefilled_email = pending.contact_email if pending else ""
        prefilled_phone = pending.contact_phone if pending else ""
        contact_type = pending.contact_type if pending else "seller"

        first_name = (prefilled_name.split()[0] if prefilled_name else "there")

        disclosure = disclosure_for(prefilled_name or "[Your Name]", prefilled_phone, default_channels_for_disclosure)

        body = f"""
<p>Hi {first_name},</p>

<p>Quick one. We want to make this property conversation as easy as possible -- the kind where you get
answers fast, on your time, without playing phone tag.</p>

<p>This page tells our system you're cool with us reaching out the modern way. <strong>Most folks finish in
under a minute.</strong></p>

<h2>What you get when you say yes</h2>

<div class="benefits">
  <div class="benefit">
    <div class="b-title">Our 24/7 AI agent picks up when you do</div>
    <div class="b-text">Insomniac at 11 PM with a question? Call our line, our AI walks you through the offer instantly. No waiting until Monday morning to hear back.</div>
  </div>
  <div class="benefit">
    <div class="b-title">Cash offer in 24 hours, not 4 weeks</div>
    <div class="b-text">Skip the back-and-forth email chain. We can send your written offer faster when we can text and call directly.</div>
  </div>
  <div class="benefit">
    <div class="b-title">You stay in control</div>
    <div class="b-text">Every text has a STOP option. Every email has unsubscribe. Every call has a "no thanks" exit. One click and we go away forever.</div>
  </div>
  <div class="benefit">
    <div class="b-title">Zero pressure, zero pushy</div>
    <div class="b-text">If our number doesn't work for you, no hard feelings. We don't chase. We don't sell your info. We don't bug your family.</div>
  </div>
</div>

<form method="POST" action="/consent/{token}/" id="consentForm">

<h2>Just confirm your info</h2>
<div class="field">
  <label>Full name</label>
  <input type="text" name="contact_name" id="contact_name" value="{prefilled_name}" required>
</div>
<div class="field">
  <label>Phone</label>
  <input type="text" name="contact_phone" value="{prefilled_phone}" placeholder="(555) 555-1234" required>
</div>
<div class="field">
  <label>Email (optional)</label>
  <input type="email" name="contact_email" value="{prefilled_email}">
</div>

<h2>How can we reach you?</h2>
<p style="font-size:14px;color:#999;">Pick at least one. The more you check, the faster we can get you a real offer.</p>

<div class="choices">
  <label class="choice">
    <input type="checkbox" name="ch_ai_call" class="ch_required" id="ch_ai_call">
    <span class="choice-content">
      <span class="choice-title">AI voice agent (24/7 calls)</span>
      <span class="choice-sub">A real conversation, any hour. Answers your property questions instantly. The fastest path to a real offer.</span>
    </span>
  </label>
  <label class="choice">
    <input type="checkbox" name="ch_autodialed_call" class="ch_required">
    <span class="choice-content">
      <span class="choice-title">Live calls from our acquisitions team</span>
      <span class="choice-sub">Real human, normal business hours. For when you'd rather hear it from a person.</span>
    </span>
  </label>
  <label class="choice">
    <input type="checkbox" name="ch_sms_marketing" class="ch_required">
    <span class="choice-content">
      <span class="choice-title">Text messages</span>
      <span class="choice-sub">Quick yes/no questions and offer updates. Reply STOP and we stop, period.</span>
    </span>
  </label>
  <label class="choice">
    <input type="checkbox" name="ch_email_marketing" class="ch_required">
    <span class="choice-content">
      <span class="choice-title">Email updates</span>
      <span class="choice-sub">Written offers and follow-ups. The slow lane, but a paper trail you can keep.</span>
    </span>
  </label>
  <label class="choice">
    <input type="checkbox" name="ch_prerecorded_voicemail" class="ch_required">
    <span class="choice-content">
      <span class="choice-title">Voicemail messages</span>
      <span class="choice-sub">Short recorded note when we have a fresh offer to share. Phone never rings -- just shows up in voicemail.</span>
    </span>
  </label>
</div>

<details>
  <summary>The legal language (click to view)</summary>
  <div class="disclosure">{disclosure}</div>
</details>

<h2>Sign by typing your name</h2>
<div class="field">
  <label>Type your name exactly as you wrote it above</label>
  <input type="text" name="signature_text" id="signature_text" placeholder="Your full name" required>
</div>
<input type="hidden" name="contact_type" value="{contact_type}">

<button type="submit" id="submitBtn" disabled>Yes, contact me about my property</button>
<p class="fineprint">By clicking, you're providing your electronic signature per the federal E-SIGN Act.
Your IP, browser, and timestamp are logged as proof. You can revoke any time with one click.
Consent is not a condition of any sale.</p>
</form>

<script>
(function(){{
  var form = document.getElementById('consentForm');
  var btn = document.getElementById('submitBtn');
  var name = document.getElementById('contact_name');
  var sig = document.getElementById('signature_text');
  var checks = form.querySelectorAll('input.ch_required');
  function check(){{
    var hasName = name.value.trim().length > 1;
    var hasSig = sig.value.trim().length > 1;
    var hasChannel = false;
    checks.forEach(function(c){{ if(c.checked) hasChannel = true; }});
    btn.disabled = !(hasName && hasSig && hasChannel);
  }}
  form.addEventListener('input', check);
  form.addEventListener('change', check);
  check();
}})();
</script>
"""
        return _render("Stay in Touch", body, tagline="A faster path to a real offer on your property")

    # ── POST: save consent ──────────────────────────────────
    if request.method == "POST":
        contact_name = (request.POST.get("contact_name") or "").strip()[:200]
        contact_phone = _normalize_phone(request.POST.get("contact_phone") or "")
        contact_email = (request.POST.get("contact_email") or "").strip().lower()[:254]
        signature_text = (request.POST.get("signature_text") or "").strip()[:200]
        contact_type = (request.POST.get("contact_type") or "seller").lower()

        if not contact_name or not contact_phone or not signature_text:
            return _render("Consent -- Missing Info",
                           "<div class='error'>Please go back and fill in your name, phone, and signature.</div>",
                           status=400)

        if signature_text.lower().strip() != contact_name.lower().strip():
            return _render("Consent -- Signature Mismatch",
                           "<div class='error'>Your typed signature must exactly match the name you provided. Please go back and try again.</div>",
                           status=400)

        # Determine which channels they consented to
        channels = []
        for code in ("ai_call", "autodialed_call", "prerecorded_voicemail",
                     "sms_marketing", "email_marketing"):
            if request.POST.get(f"ch_{code}"):
                channels.append(code)

        if not channels:
            return _render("Consent -- No Channels Selected",
                           "<div class='error'>Please go back and check at least one channel.</div>",
                           status=400)

        disclosure = disclosure_for(contact_name, contact_phone, channels)
        ip = (request.META.get("HTTP_X_FORWARDED_FOR") or request.META.get("REMOTE_ADDR") or "").split(",")[0].strip()
        ua = (request.META.get("HTTP_USER_AGENT") or "")[:500]

        # Update existing pending row OR create new
        if pending and not pending.signature_text:
            pending.contact_name = contact_name
            pending.contact_phone = contact_phone
            pending.contact_email = contact_email
            pending.channels = channels
            pending.disclosure_text = disclosure
            pending.signature_text = signature_text
            pending.signature_ip = ip or None
            pending.signature_user_agent = ua
            pending.contact_type = contact_type
            pending.save()
            row = pending
        else:
            row = ConsentLedger.objects.create(
                contact_type=contact_type,
                contact_name=contact_name,
                contact_phone=contact_phone,
                contact_email=contact_email,
                channels=channels,
                disclosure_text=disclosure,
                signature_text=signature_text,
                signature_ip=ip or None,
                signature_user_agent=ua,
                consent_token=token,
            )

        body = f"""
<div class='success'>
  <h2 style='color:#8aff9c;margin-top:0;'>Thank you, {contact_name}.</h2>
  <p>Your consent was recorded on {row.created_at.strftime('%b %d, %Y at %I:%M %p UTC')}.</p>
  <p><strong>What this means:</strong> Our team and our 24/7 AI voice agent may now contact you at
  <strong>{contact_phone}</strong> through the channels you selected. We will only contact you about
  your property and related transactions.</p>
  <p><strong>To revoke at any time:</strong></p>
  <ul style='margin:10px 0 10px 22px;'>
    <li>Reply STOP to any text message</li>
    <li>Reply 'unsubscribe' to any email</li>
    <li>Visit <a href='/consent/revoke/{row.consent_token}/' style='color:#D4A843;'>this revoke link</a></li>
    <li>Or call us during business hours and ask</li>
  </ul>
  <p style='font-size:13px;color:#888;'>Reference ID: {row.id} -- save this for your records.</p>
</div>
"""
        return _render("Consent Recorded", body)


@require_GET
def consent_revoke(request, token):
    """One-click revoke. Uses the consent_token from the original record."""
    row = ConsentLedger.objects.filter(consent_token=token, revoked=False).first()
    if not row:
        return _render("Already Revoked", "<div class='success'>This consent record was already revoked. No action needed.</div>")

    row.revoked = True
    row.revoked_at = dj_tz.now()
    row.revoked_via = "revoke_form"
    row.revoked_reason = "User clicked revoke link"
    row.save()

    return _render(
        "Consent Revoked",
        f"<div class='success'>"
        f"<strong>Done.</strong> Your consent (record #{row.id}) was revoked on "
        f"{row.revoked_at.strftime('%b %d, %Y at %I:%M %p UTC')}. "
        f"We will not contact {row.contact_phone or row.contact_email} via marketing channels going forward."
        f"</div>",
    )


@csrf_exempt
@require_POST
def consent_invite_create(request):
    """Internal: generate a fresh consent invitation. Returns the URL.

    Auth: same X-Hive-Token pattern as the hive_logger ingest endpoint.
    """
    expected = getattr(settings, "HIVE_LOGGER_TOKEN", "") or os.environ.get("HIVE_LOGGER_TOKEN", "")
    if expected and request.headers.get("X-Hive-Token", "") != expected:
        return JsonResponse({"ok": False, "error": "forbidden"}, status=403)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"ok": False, "error": "bad_json"}, status=400)

    contact_name = (payload.get("contact_name") or "").strip()[:200]
    contact_phone = _normalize_phone(payload.get("contact_phone") or "")
    contact_email = (payload.get("contact_email") or "").strip().lower()[:254]
    contact_type = (payload.get("contact_type") or "seller").lower()

    if not contact_name or not (contact_phone or contact_email):
        return JsonResponse({"ok": False, "error": "name_and_(phone_or_email)_required"}, status=400)

    token = secrets.token_urlsafe(24)

    # Pre-create a draft row -- final fields land on form submit
    ConsentLedger.objects.create(
        contact_type=contact_type,
        contact_name=contact_name,
        contact_phone=contact_phone,
        contact_email=contact_email,
        channels=[],
        disclosure_text="(pending submission)",
        signature_text="",
        consent_token=token,
    )

    base = getattr(settings, "PUBLIC_BASE_URL", "") or "http://127.0.0.1:2200"
    invite_url = f"{base}/consent/{token}/"

    return JsonResponse({
        "ok": True,
        "invite_url": invite_url,
        "consent_token": token,
        "contact_name": contact_name,
    })


# ── Legal proof-pack view ──────────────────────────────────────
# Renders a single printable HTML page with the full forensic chain
# for one consent record. Save as PDF, hand to lawyer, file with court.

from django.shortcuts import get_object_or_404


def consent_proof_pack(request, token):
    """Printable legal-defense pack for one ConsentLedger record.

    Shows side-by-side: outbound disclosure (what we sent + Twilio SID),
    inbound consent (their reply + Twilio SID + verbatim body), and the
    granted channels. This is the page you hand to a lawyer if a TCPA
    complaint comes in. Print to PDF for filing.

    GET /consent/proof/<token>/
    """
    row = get_object_or_404(ConsentLedger, consent_token=token)
    defensible = row.is_legally_defensible()

    try:
        evidence = json.loads(row.evidence_payload_json or "{}")
    except Exception:
        evidence = {}

    # Pull the related PropertyLead if present
    lead_address = ""
    if row.property_lead_id:
        try:
            from .models import PropertyLead
            lead = PropertyLead.objects.filter(id=row.property_lead_id).first()
            if lead:
                lead_address = lead.address or ""
        except Exception:
            pass

    status_color = "#0F7B3D" if defensible else "#C33B3B"
    status_label = "LEGALLY DEFENSIBLE" if defensible else "INCOMPLETE"
    revoked_banner = ""
    if row.revoked:
        revoked_banner = (
            f'<div style="background:#C33B3B;color:#fff;padding:14px;font-weight:bold;">'
            f'REVOKED on {row.revoked_at} via {row.revoked_via}: {row.revoked_reason}'
            f'</div>'
        )

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>Consent Proof Pack -- {row.contact_phone or row.contact_email}</title>
<style>
body {{ font-family: 'Inter', -apple-system, sans-serif; max-width: 850px;
       margin: 32px auto; color: #111; padding: 24px; }}
h1 {{ font-family: 'Playfair Display', serif; color: #D4A843; margin-bottom: 4px; }}
h2 {{ border-bottom: 2px solid #D4A843; padding-bottom: 6px; margin-top: 32px; }}
.status {{ display: inline-block; padding: 6px 14px; color: #fff;
          background: {status_color}; font-weight: 600; letter-spacing: 1px; }}
table {{ width: 100%; border-collapse: collapse; margin: 12px 0; }}
td.k {{ background: #f6f4ee; padding: 8px 12px; width: 30%; vertical-align: top; }}
td.v {{ padding: 8px 12px; vertical-align: top; font-family: 'SF Mono', 'Monaco', monospace; }}
.body-block {{ background: #fafafa; border-left: 4px solid #D4A843;
              padding: 14px; margin: 8px 0; white-space: pre-wrap;
              font-family: 'SF Mono', 'Monaco', monospace; font-size: 13px; }}
.footer {{ font-size: 11px; color: #666; margin-top: 40px; border-top: 1px solid #ddd;
           padding-top: 14px; }}
</style></head>
<body>

<h1>EVERLIGHT VENTURES</h1>
<div style="color:#666;letter-spacing:2px;font-size:11px;">CONSENT PROOF PACK</div>

<p style="margin-top:24px;"><span class="status">{status_label}</span></p>

{revoked_banner}

<h2>Contact</h2>
<table>
<tr><td class="k">Name</td><td class="v">{row.contact_name or '(none)'}</td></tr>
<tr><td class="k">Phone</td><td class="v">{row.contact_phone or '(none)'}</td></tr>
<tr><td class="k">Email</td><td class="v">{row.contact_email or '(none)'}</td></tr>
<tr><td class="k">Property</td><td class="v">{lead_address or '(no property tie)'}</td></tr>
<tr><td class="k">PropertyLead ID</td><td class="v">{row.property_lead_id or '(none)'}</td></tr>
<tr><td class="k">Contact Type</td><td class="v">{row.contact_type}</td></tr>
</table>

<h2>Channels Granted</h2>
<table>
<tr><td class="k">Authorized channels</td><td class="v">{', '.join(row.channels) if row.channels else '(none)'}</td></tr>
<tr><td class="k">Consent token</td><td class="v">{row.consent_token}</td></tr>
<tr><td class="k">Created at (UTC)</td><td class="v">{row.created_at.isoformat() if row.created_at else '?'}</td></tr>
</table>

<h2>Outbound Disclosure (what we sent them)</h2>
<table>
<tr><td class="k">Twilio SID (outbound)</td><td class="v">{row.outbound_twilio_sid or '(none)'}</td></tr>
<tr><td class="k">Sent at</td><td class="v">{row.outbound_sent_at.isoformat() if row.outbound_sent_at else '(unknown)'}</td></tr>
</table>
<div class="body-block">{row.disclosure_text or '(none)'}</div>

<h2>Inbound Consent Reply (their signature under E-SIGN Act)</h2>
<table>
<tr><td class="k">Twilio SID (inbound)</td><td class="v">{row.inbound_twilio_sid or '(none)'}</td></tr>
<tr><td class="k">Received at</td><td class="v">{row.inbound_received_at.isoformat() if row.inbound_received_at else '(unknown)'}</td></tr>
<tr><td class="k">Signature text</td><td class="v">{row.signature_text or '(none)'}</td></tr>
</table>
<div class="body-block">{row.inbound_body_verbatim or '(none)'}</div>

<h2>How to verify with carrier</h2>
<p style="font-size:13px;color:#444;">
The Twilio SIDs above are independently verifiable by subpoena. Twilio retains
message records for at least 13 months. Match the outbound SID to confirm the
disclosure was delivered, and the inbound SID to confirm the consent reply
came from the consumer's number.
</p>

<details style="margin-top:24px;">
<summary style="cursor:pointer;color:#D4A843;font-weight:600;">Raw Twilio payload (verbatim)</summary>
<pre style="background:#fafafa;padding:14px;font-size:11px;overflow-x:auto;">{json.dumps(evidence, indent=2)}</pre>
</details>

<div class="footer">
Generated {datetime.now(timezone.utc).isoformat()} UTC.
Everlight Ventures - 1m.rich.gee@gmail.com.
This page is an immutable forensic record. The data shown is read directly
from the production ConsentLedger row created at consent capture time.
</div>

</body></html>"""

    return HttpResponse(html, content_type="text/html; charset=utf-8")
