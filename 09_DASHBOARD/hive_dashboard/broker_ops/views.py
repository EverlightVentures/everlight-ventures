"""
Broker OS - Views

Dashboard + JSON API endpoints + Stripe payment integration.
"""
import json
import logging
import os
from decimal import Decimal

from django.contrib.admin.views.decorators import staff_member_required
from django.core.cache import cache
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import BrokerMatch, Deal, LeadProfile, OfferListing
from .services import (
    check_stripe_payment_status,
    close_deal,
    create_deal_from_match,
    create_stripe_checkout_link,
    create_stripe_invoice,
    generate_contract,
    generate_deal_memo,
    get_commission_summary,
    handle_broker_checkout_completed,
    handle_broker_invoice_paid,
    ingest_lead,
    ingest_offer,
    run_matching,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# DASHBOARD
# ---------------------------------------------------------------------------

@staff_member_required
def dashboard(request):
    summary = get_commission_summary()
    recent_matches = BrokerMatch.objects.filter(status="pending").order_by("-match_score")[:20]
    recent_deals   = Deal.objects.select_related("offer", "lead").order_by("-created_at")[:10]
    top_offers     = OfferListing.objects.filter(status="active").order_by("-created_at")[:10]
    hot_leads      = LeadProfile.objects.filter(intent="hot", unsubscribed=False).order_by("-created_at")[:10]

    return render(request, "broker_ops/dashboard.html", {
        "active_page": "broker_ops",
        "summary": summary,
        "recent_matches": recent_matches,
        "recent_deals": recent_deals,
        "top_offers": top_offers,
        "hot_leads": hot_leads,
    })


# ---------------------------------------------------------------------------
# API: Lead ingest
# ---------------------------------------------------------------------------

@csrf_exempt
@require_POST
def api_ingest_lead(request):
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "invalid JSON"}, status=400)

    required = ["name", "need_description"]
    missing = [f for f in required if not payload.get(f)]
    if missing:
        return JsonResponse({"error": f"missing fields: {missing}"}, status=400)

    lead = ingest_lead(payload)
    return JsonResponse({"ok": True, "lead_id": str(lead.id), "lead": str(lead)})


# ---------------------------------------------------------------------------
# API: Offer ingest
# ---------------------------------------------------------------------------

@csrf_exempt
@require_POST
def api_ingest_offer(request):
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "invalid JSON"}, status=400)

    required = ["seller_name", "seller_email", "title", "description"]
    missing = [f for f in required if not payload.get(f)]
    if missing:
        return JsonResponse({"error": f"missing fields: {missing}"}, status=400)

    offer = ingest_offer(payload)
    return JsonResponse({"ok": True, "offer_id": str(offer.id), "offer": str(offer)})


# ---------------------------------------------------------------------------
# API: Run matching engine
# ---------------------------------------------------------------------------

@staff_member_required
def api_run_matching(request):
    min_score = float(request.GET.get("min_score", 40.0))
    dry_run   = request.GET.get("dry_run", "false").lower() == "true"
    results   = run_matching(min_score=min_score, dry_run=dry_run)
    return JsonResponse({"ok": True, "matches": len(results), "results": results[:50]})


# ---------------------------------------------------------------------------
# API: Approve match + create deal
# ---------------------------------------------------------------------------

@csrf_exempt
@require_POST
@staff_member_required
def api_approve_match(request, match_id):
    match = get_object_or_404(BrokerMatch, id=match_id)
    try:
        body = json.loads(request.body)
        deal_value = Decimal(str(body.get("deal_value", 0)))
        notes = body.get("notes", "")
    except (json.JSONDecodeError, Exception):
        return JsonResponse({"error": "invalid body"}, status=400)

    if deal_value <= 0:
        return JsonResponse({"error": "deal_value required"}, status=400)

    match.status = "approved"
    match.save(update_fields=["status"])
    deal = create_deal_from_match(match, deal_value, notes)
    return JsonResponse({"ok": True, "deal_id": str(deal.id), "commission_due": float(deal.commission_due)})


# ---------------------------------------------------------------------------
# API: Close deal
# ---------------------------------------------------------------------------

@csrf_exempt
@require_POST
@staff_member_required
def api_close_deal(request, deal_id):
    deal = get_object_or_404(Deal, id=deal_id)
    body = {}
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        pass
    won  = body.get("won", True)
    deal = close_deal(deal, won=won)
    return JsonResponse({"ok": True, "stage": deal.stage, "commission_due": float(deal.commission_due)})


# ---------------------------------------------------------------------------
# API: Commission summary
# ---------------------------------------------------------------------------

@staff_member_required
def api_commission_summary(request):
    return JsonResponse(get_commission_summary())


# ---------------------------------------------------------------------------
# RATE LIMITING (IP-based, 5 submissions per hour per endpoint)
# ---------------------------------------------------------------------------

def _check_rate_limit(request, endpoint_name, max_requests=5, window_seconds=3600):
    """Return a 429 JsonResponse if rate limit exceeded, or None if OK."""
    ip = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip() or request.META.get("REMOTE_ADDR", "unknown")
    cache_key = f"ratelimit:{endpoint_name}:{ip}"
    hits = cache.get(cache_key, 0)
    if hits >= max_requests:
        return JsonResponse({"error": "Rate limit exceeded. Try again later."}, status=429)
    cache.set(cache_key, hits + 1, window_seconds)
    return None


# ---------------------------------------------------------------------------
# PUBLIC: Lead capture (no auth - for Lovable /find-tools page)
# ---------------------------------------------------------------------------

@csrf_exempt
@require_POST
def public_submit_lead(request):
    """Public endpoint for buyer intake from the Lovable site."""
    rate_limited = _check_rate_limit(request, "public_submit_lead")
    if rate_limited:
        return rate_limited
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "invalid JSON"}, status=400)

    required = ["name", "email", "need_description"]
    missing = [f for f in required if not payload.get(f)]
    if missing:
        return JsonResponse({"error": f"missing fields: {missing}"}, status=400)

    # Sanitize
    clean = {
        "name": str(payload.get("name", ""))[:200],
        "email": str(payload.get("email", "")).strip().lower()[:254],
        "company": str(payload.get("company", ""))[:200],
        "role": str(payload.get("role", ""))[:100],
        "company_size": str(payload.get("company_size", ""))[:20],
        "need_description": str(payload.get("need_description", ""))[:2000],
        "categories_needed": payload.get("categories_needed", [])[:5],
        "budget_max": min(float(payload.get("budget_max", 0) or 0), 999999),
        "intent": "warm",
        "lead_source": str(payload.get("lead_source", "website"))[:30],
    }

    lead = ingest_lead(clean)
    return JsonResponse({"ok": True, "lead_id": str(lead.id)})


# ---------------------------------------------------------------------------
# PUBLIC: Offer submission (no auth - for Lovable /list-your-tool page)
# ---------------------------------------------------------------------------

@csrf_exempt
@require_POST
def public_submit_offer(request):
    """Public endpoint for seller applications from the Lovable site."""
    rate_limited = _check_rate_limit(request, "public_submit_offer")
    if rate_limited:
        return rate_limited
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "invalid JSON"}, status=400)

    required = ["seller_name", "seller_email", "title", "description"]
    missing = [f for f in required if not payload.get(f)]
    if missing:
        return JsonResponse({"error": f"missing fields: {missing}"}, status=400)

    clean = {
        "seller_name": str(payload.get("seller_name", ""))[:200],
        "seller_email": str(payload.get("seller_email", "")).strip().lower()[:254],
        "seller_url": str(payload.get("seller_url", ""))[:200],
        "title": str(payload.get("title", ""))[:300],
        "category": str(payload.get("category", "other"))[:30],
        "description": str(payload.get("description", ""))[:2000],
        "price_min": min(float(payload.get("price_min", 0) or 0), 999999),
        "price_max": min(float(payload.get("price_max", 0) or 0), 999999),
        "pricing_model": str(payload.get("pricing_model", "monthly"))[:20],
        "source": "website_list_tool",
        "status": "active",
    }

    offer = ingest_offer(clean)
    return JsonResponse({"ok": True, "offer_id": str(offer.id)})


# ---------------------------------------------------------------------------
# STRIPE: Webhook handler for broker_ops events
# ---------------------------------------------------------------------------

@csrf_exempt
@require_POST
def stripe_webhook(request):
    """
    Stripe webhook handler for broker_ops payment events.
    Handles: invoice.paid, checkout.session.completed
    Only processes events tagged with metadata.source == "broker_ops".
    Other events are ignored (the payments app handles general Stripe events).
    """
    import stripe as stripe_lib

    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")
    endpoint_secret = os.environ.get("STRIPE_BROKER_WEBHOOK_SECRET", "")

    # Verify signature if we have the secret
    if endpoint_secret:
        try:
            event = stripe_lib.Webhook.construct_event(payload, sig_header, endpoint_secret)
        except (ValueError, stripe_lib.error.SignatureVerificationError) as e:
            logger.warning(f"Broker webhook signature verification failed: {e}")
            return HttpResponse(status=400)
    else:
        # No secret configured -- parse raw JSON (dev mode)
        try:
            event = json.loads(payload)
        except json.JSONDecodeError:
            return HttpResponse(status=400)

    event_type = event.get("type", "")
    data = event.get("data", {}).get("object", {})

    logger.info(f"Broker webhook received: {event_type}")

    handled = False

    if event_type == "invoice.paid":
        handled = handle_broker_invoice_paid(data)
    elif event_type == "checkout.session.completed":
        handled = handle_broker_checkout_completed(data)

    if handled:
        logger.info(f"Broker webhook processed: {event_type}")
    else:
        logger.debug(f"Broker webhook ignored (not broker_ops): {event_type}")

    return HttpResponse(status=200)


# ---------------------------------------------------------------------------
# STRIPE: Create invoice for a deal (staff only)
# ---------------------------------------------------------------------------

@csrf_exempt
@require_POST
@staff_member_required
def api_create_invoice(request, deal_id):
    """
    Staff endpoint to generate a Stripe invoice for a deal's finder fee.
    POST /broker/api/deal/<deal_id>/invoice/
    """
    deal = get_object_or_404(Deal, id=deal_id)

    if deal.stripe_invoice_id:
        return JsonResponse({
            "ok": False,
            "error": f"Deal already has invoice: {deal.stripe_invoice_id}",
        }, status=400)

    if deal.stage not in ("closed_won", "active", "contracted"):
        return JsonResponse({
            "ok": False,
            "error": f"Deal stage is '{deal.stage}' -- must be active, contracted, or closed_won to invoice",
        }, status=400)

    try:
        invoice_id = create_stripe_invoice(deal)
        return JsonResponse({
            "ok": True,
            "invoice_id": invoice_id,
            "deal_id": str(deal.id),
            "amount": float(deal.commission_due),
        })
    except Exception as e:
        logger.error(f"Invoice creation failed for deal {deal_id}: {e}")
        return JsonResponse({"ok": False, "error": str(e)}, status=500)


# ---------------------------------------------------------------------------
# STRIPE: Create checkout link for a deal (staff only)
# ---------------------------------------------------------------------------

@csrf_exempt
@require_POST
@staff_member_required
def api_create_checkout(request, deal_id):
    """
    Staff endpoint to create a Stripe Checkout link for a deal's finder fee.
    POST /broker/api/deal/<deal_id>/checkout/
    Returns the checkout URL the client can be sent to pay.
    """
    deal = get_object_or_404(Deal, id=deal_id)

    body = {}
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        pass

    success_url = body.get("success_url", "")
    cancel_url = body.get("cancel_url", "")

    try:
        checkout_url = create_stripe_checkout_link(deal, success_url, cancel_url)
        return JsonResponse({
            "ok": True,
            "checkout_url": checkout_url,
            "deal_id": str(deal.id),
            "amount": float(deal.commission_due),
        })
    except Exception as e:
        logger.error(f"Checkout creation failed for deal {deal_id}: {e}")
        return JsonResponse({"ok": False, "error": str(e)}, status=500)


# ---------------------------------------------------------------------------
# STRIPE: Check payment status for a deal (staff only)
# ---------------------------------------------------------------------------

@staff_member_required
def api_check_payment(request, deal_id):
    """
    Staff endpoint to check the Stripe payment status for a deal.
    GET /broker/api/deal/<deal_id>/payment-status/
    """
    deal = get_object_or_404(Deal, id=deal_id)

    try:
        result = check_stripe_payment_status(deal)
        return JsonResponse({"ok": True, "deal_id": str(deal.id), **result})
    except Exception as e:
        logger.error(f"Payment status check failed for deal {deal_id}: {e}")
        return JsonResponse({"ok": False, "error": str(e)}, status=500)


# ---------------------------------------------------------------------------
# CONTRACT GENERATION
# ---------------------------------------------------------------------------

@csrf_exempt
@require_POST
@staff_member_required
def api_generate_contract(request, deal_id):
    """
    Staff endpoint to generate a Finder Fee Agreement for a deal.
    POST /broker/api/deal/<deal_id>/contract/

    Optional JSON body:
        {"payment_method": "stripe" | "crypto"}

    Returns the file path and a preview of the first 500 characters.
    """
    deal = get_object_or_404(Deal, id=deal_id)

    body = {}
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        pass

    payment_method = body.get("payment_method", "stripe")

    try:
        contract_path = generate_contract(deal, payment_method=payment_method)

        # Read back first 500 chars as preview
        with open(contract_path, "r", encoding="utf-8") as f:
            preview = f.read(500)

        # Also generate the deal memo alongside the contract
        memo_path = generate_deal_memo(deal)

        return JsonResponse({
            "ok": True,
            "deal_id": str(deal.id),
            "contract_path": contract_path,
            "memo_path": memo_path,
            "preview": preview,
        })
    except FileNotFoundError as e:
        logger.error(f"Contract template missing for deal {deal_id}: {e}")
        return JsonResponse({"ok": False, "error": str(e)}, status=404)
    except Exception as e:
        logger.error(f"Contract generation failed for deal {deal_id}: {e}")
        return JsonResponse({"ok": False, "error": str(e)}, status=500)
