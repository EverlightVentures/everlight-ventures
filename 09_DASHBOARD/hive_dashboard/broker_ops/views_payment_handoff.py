"""views_payment_handoff -- Django views for the JWT-gated approval flow.

URL routes (added to broker_ops/urls.py):
  /broker/approve/<token>/                   -- GET shows landing page + recap
  /broker/approve/<token>/?path=call         -- GET shows confirm page for call channel
  /broker/approve/<token>/?path=title        -- GET shows confirm page for title channel
  /broker/approve/<token>/confirm/           -- POST executes the chosen action

Public-no-login: the JWT IS the auth. If you have the token, you tapped the
Slack message. If the token is forged or expired, verification fails and the
view returns a generic "this approval has expired or is invalid" page so we
do not leak deal details to a phisher.
"""

from __future__ import annotations

import sys
from pathlib import Path

from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

# Allow the Django process to import payment_handoff from /home/opc/
for d in ("/home/opc", "/home/opc/03_AUTOMATION_CORE/01_Scripts"):
    if d not in sys.path and Path(d).exists():
        sys.path.insert(0, d)

from broker_ops.models import Deal, DealEvent  # noqa: E402

try:
    from payment_handoff import (  # type: ignore
        verify_approval_token,
        execute_handoff,
    )
except ImportError:
    verify_approval_token = None  # type: ignore
    execute_handoff = None  # type: ignore


_GOLD = "#D4A843"
_DARK = "#0A0A0A"

_LANDING_HTML = """<!doctype html>
<html><head><meta charset="utf-8"><title>Payment Handoff -- Confirm</title>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Inter:wght@300;400;600&display=swap" rel="stylesheet">
<style>
  body {{ font-family: Inter, system-ui, sans-serif; background: {DARK}; color: #E8E8E8;
         margin: 0; min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 24px; }}
  .card {{ max-width: 560px; width: 100%; background: #111; border: 1px solid #2a2a2a;
           border-radius: 12px; padding: 32px; box-shadow: 0 30px 80px rgba(0,0,0,0.5); }}
  .wordmark {{ color: {GOLD}; letter-spacing: 5px; font-size: 11px; font-weight: 600; }}
  h1 {{ font-family: 'Playfair Display', serif; color: #fff; font-size: 28px;
        margin: 14px 0 8px; line-height: 1.2; }}
  .sub {{ color: #888; font-size: 14px; margin-bottom: 24px; }}
  .recap {{ background: #1a1a1a; border-left: 3px solid {GOLD}; padding: 16px 18px;
            border-radius: 4px; margin: 18px 0 24px; font-size: 14px; line-height: 1.6; }}
  .field {{ display: flex; justify-content: space-between; padding: 4px 0; }}
  .field .k {{ color: #888; }}
  .field .v {{ color: #E8E8E8; font-weight: 500; }}
  .channel {{ background: #1a1a1a; border-radius: 8px; padding: 16px;
              margin-bottom: 16px; border: 1px solid #2a2a2a; }}
  .channel h3 {{ margin: 0 0 4px; color: {GOLD}; font-size: 16px; }}
  .channel p {{ margin: 0; color: #aaa; font-size: 13px; line-height: 1.5; }}
  .btn {{ display: block; width: 100%; padding: 14px 20px; margin-top: 12px;
          background: {GOLD}; color: {DARK}; border: 0; border-radius: 8px;
          font-size: 15px; font-weight: 600; cursor: pointer; text-decoration: none;
          text-align: center; transition: opacity 0.2s; }}
  .btn:hover {{ opacity: 0.85; }}
  .btn.ghost {{ background: transparent; color: #aaa; border: 1px solid #333; margin-top: 18px; }}
  .footer {{ text-align: center; color: #555; font-size: 11px; margin-top: 22px;
             letter-spacing: 0.5px; }}
</style></head>
<body>
<div class="card">
  <div class="wordmark">EVERLIGHT VENTURES</div>
  <h1>Confirm payment handoff</h1>
  <div class="sub">{path_label}</div>

  <div class="recap">
    <div class="field"><span class="k">Property</span><span class="v">{addr}</span></div>
    <div class="field"><span class="k">Buyer</span><span class="v">{buyer}</span></div>
    <div class="field"><span class="k">Deal value</span><span class="v">${deal_value}</span></div>
    <div class="field"><span class="k">Stage</span><span class="v">{stage}</span></div>
  </div>

  <div class="channel">
    <h3>{channel_title}</h3>
    <p>{channel_blurb}</p>
  </div>

  <form method="POST" action="{confirm_url}">
    <input type="hidden" name="token" value="{token}">
    <input type="hidden" name="path" value="{path}">
    <button type="submit" class="btn">Confirm and fire</button>
  </form>
  <a class="btn ghost" href="javascript:window.close()">Not yet, close this</a>

  <div class="footer">Token expires 24h after issue. One-tap. Audit-logged to DealEvent.</div>
</div>
</body></html>"""


_CONFIRMED_HTML = """<!doctype html>
<html><head><meta charset="utf-8"><title>Payment handoff fired</title>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Inter:wght@300;400;600&display=swap" rel="stylesheet">
<style>
  body {{ font-family: Inter, system-ui, sans-serif; background: {DARK}; color: #E8E8E8;
         margin: 0; min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 24px; }}
  .card {{ max-width: 560px; width: 100%; background: #111; border: 1px solid {GOLD};
           border-radius: 12px; padding: 40px; text-align: center;
           box-shadow: 0 30px 80px {GOLD_GLOW}; }}
  .icon {{ font-size: 56px; margin-bottom: 12px; }}
  .wordmark {{ color: {GOLD}; letter-spacing: 5px; font-size: 11px; font-weight: 600; }}
  h1 {{ font-family: 'Playfair Display', serif; color: {GOLD}; font-size: 32px;
        margin: 14px 0 12px; }}
  .sub {{ color: #ccc; font-size: 15px; margin-bottom: 24px; line-height: 1.5; }}
  .status {{ background: #0f1f0f; border: 1px solid #1f4a1f; color: #cfeed3;
             padding: 14px 18px; border-radius: 6px; font-size: 14px; }}
  .footer {{ color: #555; font-size: 11px; margin-top: 28px; letter-spacing: 0.5px; }}
</style></head>
<body>
<div class="card">
  <div class="icon">🎯</div>
  <div class="wordmark">EVERLIGHT VENTURES</div>
  <h1>Money handoff armed</h1>
  <div class="sub">{message}</div>
  <div class="status">{status}</div>
  <div class="footer">Logged. The Hive moves on. -- LUCREX</div>
</div>
</body></html>"""


_INVALID_HTML = """<!doctype html><html><head><title>Approval invalid</title>
<style>body{{font-family:system-ui;background:#0A0A0A;color:#888;
display:flex;align-items:center;justify-content:center;min-height:100vh;}}
.box{{max-width:480px;text-align:center;padding:32px;}}
h1{{color:#D4A843;font-size:22px;}}
</style></head><body><div class="box"><h1>This approval is no longer valid</h1>
<p>The token has expired or is malformed. Open a fresh approval card from the Slack thread.</p>
</div></body></html>"""


def _fmt(value, n=2):
    try:
        return f"{float(value):,.{n}f}"
    except Exception:
        return str(value)


def approve_payment_handoff(request, token: str):
    """GET: show landing page with recap + confirm button.
    Path query param decides which channel ('call' or 'title').
    """
    if verify_approval_token is None:
        return HttpResponse("payment_handoff module not available", status=500)

    deal_id = verify_approval_token(token)
    if not deal_id:
        return HttpResponse(_INVALID_HTML, status=403)

    try:
        deal = Deal.objects.select_related("lead").get(id=deal_id)
    except Deal.DoesNotExist:
        return HttpResponse(_INVALID_HTML, status=404)

    path = request.GET.get("path", "")
    if path not in ("call", "title"):
        # Show both options. For MVP, we redirect to the title channel by default.
        # The Slack card always passes ?path=...
        return HttpResponse(
            "Open this approval from the Slack card so the channel is set.",
            status=400,
        )

    channel_title, channel_blurb, path_label = {
        "call": (
            "📞 Schedule a 15-min call",
            "Send the buyer a calendar invite. You'll walk wire details on the call. The buyer gets a tokenized one-time HTML page with the info after the call lands.",
            "Channel: in-person call. The safest path.",
        ),
        "title": (
            "🏢 Route through title escrow",
            "Reply to the buyer with your top-pick title company's contact. The buyer wires EMD to the title company's escrow account, never directly to you. Title company sends you the assignment fee at close on a HUD-1.",
            "Channel: title-company escrow. The compliance-correct path.",
        ),
    }[path]

    lead = deal.lead
    body = _LANDING_HTML.format(
        DARK=_DARK, GOLD=_GOLD,
        path=path,
        path_label=path_label,
        addr=getattr(lead, "address", "address pending") if lead else "address pending",
        buyer=(getattr(lead, "owner_name", "") or "buyer").strip() if lead else "buyer",
        deal_value=_fmt(getattr(deal, "deal_value", 0), 0),
        stage=getattr(deal, "stage", "?"),
        channel_title=channel_title,
        channel_blurb=channel_blurb,
        confirm_url=f"/broker/approve/{token}/confirm/",
        token=token,
    )
    return HttpResponse(body)


@csrf_exempt
@require_http_methods(["POST"])
def approve_payment_handoff_confirm(request, token: str):
    """POST: actually fire the action. Verifies token + path, runs handler,
    logs DealEvent, renders celebratory page."""
    if execute_handoff is None or verify_approval_token is None:
        return HttpResponseBadRequest("payment_handoff module not available")

    deal_id = verify_approval_token(token)
    if not deal_id:
        return HttpResponse(_INVALID_HTML, status=403)

    path = request.POST.get("path", "")
    if path not in ("call", "title"):
        return HttpResponseBadRequest("missing or invalid path")

    try:
        deal = Deal.objects.select_related("lead").get(id=deal_id)
    except Deal.DoesNotExist:
        return HttpResponse(_INVALID_HTML, status=404)

    status = execute_handoff(deal, path)

    # Audit log
    try:
        DealEvent.objects.create(
            deal=deal,
            event_type="payment_handoff_approved",
            title=f"Payment handoff approved -- {path}",
            detail=str(status),
            agent_name="Marquise (via approval URL)",
            metadata={"path": path, "token_partial": token[:24]},
        )
    except Exception:
        pass

    message = {
        "call": "Buyer is being booked for a call. Wire details get walked verbally + tokenized HTML page after the call.",
        "title": "Title company escrow contact has been emailed to the buyer. They wire to the title company. You wire-fraud-proof.",
    }[path]

    return HttpResponse(_CONFIRMED_HTML.format(
        DARK=_DARK, GOLD=_GOLD, GOLD_GLOW="rgba(212, 168, 67, 0.25)",
        message=message, status=status,
    ))
