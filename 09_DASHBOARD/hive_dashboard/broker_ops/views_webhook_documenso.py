"""views_webhook_documenso -- inbound webhook from self-hosted Documenso.

Documenso (https://sign.everlightventures.io) fires this webhook when a buyer
or seller signs a document. Payload is JSON of the shape::

    {
      "event": "document.signed" | "document.completed" | ...,
      "payload": {
        "id": "<documenso doc id>",
        "title": "...",
        "recipients": [{"email": "...", "name": "...", "signedAt": "..."}],
        ...
      }
    }

Documenso signs the body with HMAC-SHA256 using a shared secret. The signature
arrives in the `X-Documenso-Signature` header (Documenso also uses
`X-Documenso-Signing-Secret` in some deployments, we accept either).

On a verified `document.signed` (or `document.completed`) event:

  1. Match `payload.id` to a Deal via `Deal.documenso_doc_id` (set when
     pdf_autofill.maybe_send_to_documenso() creates the document).
     Fallback: scan `Deal.agreement_url` for the doc id substring.
  2. Advance the Deal via services_closeout.advance_stage(deal, "psa_signed")
     -- this sets Deal.stage="signing" and writes a stage_change DealEvent.
  3. Write an additional DealEvent of event_type "doc_signed" with the
     signer email + timestamp for audit clarity.
  4. Post a branded Slack card to #broker-pipeline announcing the signature.

The view is csrf_exempt (webhook is public POST). HMAC is the only auth.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import sys
from pathlib import Path

from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

# Allow `from content_tools.branded_slack import post_branded_slack` on Oracle
for _d in ("/home/opc",):
    if _d not in sys.path and Path(_d).exists():
        sys.path.insert(0, _d)

try:
    from content_tools.branded_slack import post_branded_slack  # type: ignore
except Exception:  # pragma: no cover -- absent in some test envs
    post_branded_slack = None  # type: ignore

from .models import Deal, DealEvent
from . import services_closeout

log = logging.getLogger(__name__)

# Header names Documenso may use to ship the signature
SIG_HEADERS = (
    "HTTP_X_DOCUMENSO_SIGNATURE",
    "HTTP_X_DOCUMENSO_SIGNING_SECRET",
    "HTTP_X_HOOK_SIGNATURE",
)

# Events that should advance the Deal to psa_signed
SIGNED_EVENTS = {"document.signed", "document.completed", "DOCUMENT_SIGNED", "DOCUMENT_COMPLETED"}


def _verify_hmac(raw_body: bytes, header_sig: str, secret: str) -> bool:
    """Constant-time compare of HMAC-SHA256(secret, raw_body).

    Accepts either bare hex digest or `sha256=<hex>` prefixed form.
    """
    if not secret or not header_sig:
        return False
    sig = header_sig.strip()
    if sig.lower().startswith("sha256="):
        sig = sig.split("=", 1)[1].strip()
    computed = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    try:
        return hmac.compare_digest(computed, sig)
    except Exception:
        return False


def _extract_doc_id(payload: dict) -> str:
    """Pull the document id from the Documenso payload, regardless of shape."""
    inner = payload.get("payload") or payload.get("data") or {}
    if isinstance(inner, dict):
        for k in ("id", "documentId", "document_id"):
            v = inner.get(k)
            if v:
                return str(v)
        doc = inner.get("document") or {}
        if isinstance(doc, dict) and doc.get("id"):
            return str(doc["id"])
    # Top-level fallback
    for k in ("id", "documentId", "document_id"):
        v = payload.get(k)
        if v:
            return str(v)
    return ""


def _extract_signer(payload: dict) -> tuple[str, str, str]:
    """Return (email, name, signed_at) from the first recipient with signed_at set."""
    inner = payload.get("payload") or payload.get("data") or payload
    if not isinstance(inner, dict):
        return "", "", ""
    recipients = inner.get("recipients") or inner.get("Recipient") or []
    if not isinstance(recipients, list):
        recipients = []
    for r in recipients:
        if not isinstance(r, dict):
            continue
        signed_at = r.get("signedAt") or r.get("signed_at") or r.get("completedAt") or ""
        email = r.get("email") or ""
        name = r.get("name") or ""
        if signed_at or email:
            return str(email), str(name), str(signed_at)
    return "", "", str(inner.get("signedAt") or inner.get("signed_at") or "")


def _match_deal(doc_id: str) -> Deal | None:
    """Find a Deal for this Documenso document id."""
    if not doc_id:
        return None
    deal = Deal.objects.filter(documenso_doc_id=doc_id).first()
    if deal:
        return deal
    # Fallback: pdf_autofill stored signing URL like .../sign/<doc_id>
    return Deal.objects.filter(agreement_url__icontains=doc_id).first()


def _post_signed_slack(deal: Deal, signer_email: str, signer_name: str) -> None:
    """Branded post to #broker-pipeline announcing the signature."""
    if post_branded_slack is None:
        log.info("branded_slack unavailable; skipping Slack post for deal %s", deal.id)
        return
    address = ""
    try:
        if deal.lead is not None:
            for attr in ("address", "company", "name"):
                v = getattr(deal.lead, attr, "")
                if v:
                    address = str(v)
                    break
    except Exception:
        address = ""
    if not address and deal.offer:
        address = str(deal.offer)
    address = address or f"deal {deal.id}"

    buyer = signer_name or signer_email or "Signer"
    summary = f":handshake: {buyer} signed assignment for {address}. EMD next."
    fields = {
        "Deal": str(deal.id),
        "Stage": deal.stage,
        "Signer": signer_email or "(unknown)",
        "Value": f"${deal.deal_value:,.0f}",
    }
    body = (
        f"Assignment agreement signed via Documenso. "
        f"Deal advanced to `psa_signed` (Deal.stage=signing). "
        f"Next checkpoint: earnest money deposit received."
    )
    try:
        post_branded_slack(
            channel="#broker-pipeline",
            title="Assignment Signed",
            summary=summary,
            body=body,
            fields=fields,
            agent_name="Backend Hand",
            agent_title="Documenso webhook",
            category="deal",
            fallback_text=summary,
        )
    except Exception as exc:  # pragma: no cover -- Slack is best-effort
        log.warning("Slack post failed for deal %s: %s", deal.id, exc)


@csrf_exempt
@require_POST
def webhook_documenso(request):
    """POST /broker/webhook/documenso/ -- Documenso e-sign webhook.

    Verifies HMAC. On `document.signed`, advances the matched Deal to
    `psa_signed`, writes a `doc_signed` DealEvent, and posts to Slack.
    """
    secret = os.environ.get("DOCUMENSO_WEBHOOK_SECRET", "")
    raw = request.body or b""

    # 1) HMAC verification -- mandatory in prod.
    header_sig = ""
    for h in SIG_HEADERS:
        v = request.META.get(h, "")
        if v:
            header_sig = v
            break

    if not secret:
        log.error("DOCUMENSO_WEBHOOK_SECRET not set; refusing webhook")
        return HttpResponse(status=503, content=b"webhook secret not configured")

    if not _verify_hmac(raw, header_sig, secret):
        log.warning("Documenso webhook HMAC verification FAILED (sig_present=%s, body=%db)",
                    bool(header_sig), len(raw))
        return HttpResponse(status=403, content=b"invalid signature")

    # 2) Parse JSON
    try:
        payload = json.loads(raw.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "invalid json"}, status=400)

    event = (payload.get("event") or payload.get("type") or "").strip()
    log.info("Documenso webhook received: event=%s", event)

    # 3) Only act on signed/completed events. Other events ack OK so Documenso stops retrying.
    if event not in SIGNED_EVENTS:
        return JsonResponse({"ok": True, "ignored": event})

    doc_id = _extract_doc_id(payload)
    if not doc_id:
        log.warning("Documenso webhook missing document id; payload keys=%s", list(payload.keys()))
        return JsonResponse({"ok": False, "error": "no document id"}, status=400)

    deal = _match_deal(doc_id)
    if deal is None:
        log.warning("No Deal matches Documenso doc_id=%s", doc_id)
        return JsonResponse({"ok": False, "error": "deal not found", "doc_id": doc_id}, status=404)

    signer_email, signer_name, signed_at = _extract_signer(payload)
    detail = (
        f"Signer: {signer_email or '(unknown)'} ({signer_name or 'no name'}) "
        f"at {signed_at or timezone.now().isoformat()}. "
        f"Documenso doc_id={doc_id}."
    )

    # 4) Backfill documenso_doc_id if it was matched via agreement_url
    if not deal.documenso_doc_id:
        deal.documenso_doc_id = doc_id
        deal.save(update_fields=["documenso_doc_id"])

    # 5) Advance the close-out stage. Idempotent: advance_stage de-dupes by target.
    try:
        services_closeout.advance_stage(
            deal,
            "psa_signed",
            agent="Backend Hand",
            detail=detail,
            metadata={
                "documenso_doc_id": doc_id,
                "event": event,
                "signer_email": signer_email,
                "signer_name": signer_name,
                "signed_at": signed_at,
                "source": "documenso_webhook",
            },
        )
    except Exception as exc:
        log.exception("advance_stage(psa_signed) failed for deal %s: %s", deal.id, exc)
        return JsonResponse({"ok": False, "error": "advance_stage failed"}, status=500)

    # 6) Audit DealEvent of type doc_signed (in addition to stage_change row)
    DealEvent.objects.create(
        deal=deal,
        event_type="doc_signed",
        title="Assignment agreement signed",
        detail=detail,
        agent_name="Documenso webhook",
        metadata={
            "documenso_doc_id": doc_id,
            "event": event,
            "signer_email": signer_email,
            "signer_name": signer_name,
            "signed_at": signed_at,
        },
    )

    # 7) Branded Slack to #broker-pipeline
    _post_signed_slack(deal, signer_email, signer_name)

    return JsonResponse({
        "ok": True,
        "deal_id": str(deal.id),
        "stage": deal.stage,
        "doc_id": doc_id,
    })
