"""
Broker OS - Views

Dashboard + JSON API endpoints + Stripe payment integration + Wholesale pipeline.
"""
import json
import logging
import os
from decimal import Decimal

from django.utils import timezone
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.db.models import Avg, Count, Q, Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from hive_dashboard.security import internal_api_required, staff_or_internal_required
from .models import BrokerMatch, ClientDocument, ClientFile, Deal, InvestorBuyer, LeadProfile, OfferListing, OutreachSequence, PropertyLead
from .wholesale import (
    generate_buyer_blast,
    generate_outreach_sms,
    import_csv_leads_from_upload,
    match_property_to_buyers,
    score_property,
)
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

@login_required
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
@internal_api_required
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
@internal_api_required
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

@staff_or_internal_required
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
@staff_or_internal_required
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
@staff_or_internal_required
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

@staff_or_internal_required
def api_commission_summary(request):
    return JsonResponse(get_commission_summary())


@staff_or_internal_required
@require_GET
def api_deal_history(request, deal_id):
    """Full deal timeline: events + calls + documents merged chronologically."""
    deal = get_object_or_404(Deal, id=deal_id)
    from .services import get_deal_history
    timeline = get_deal_history(deal)
    # Serialize timestamps
    for entry in timeline:
        entry["timestamp"] = entry["timestamp"].isoformat() if entry.get("timestamp") else None
    return JsonResponse({"ok": True, "deal_id": str(deal.id), "stage": deal.stage,
                          "timeline": timeline, "count": len(timeline)})


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
# EVENT WEBHOOKS: inbound triggers from n8n, Gmail, external systems
# ---------------------------------------------------------------------------

@csrf_exempt
@require_POST
def webhook_email_reply(request):
    """Webhook for email reply detection. Called by n8n Gmail monitor or broker_gmail_monitor.

    POST /broker/webhook/email-reply/
    Body: {
        "from_email": "seller@example.com",
        "from_name": "John Doe",
        "subject": "Re: ...",
        "body": "I'm interested...",
        "in_reply_to": "original-message-id",
        "reply_type": "seller" | "buyer" | "title_company",
        "sentiment": "positive" | "neutral" | "negative",
        "interest_level": "high" | "medium" | "low" | "none"
    }
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "Invalid JSON"}, status=400)

    from_email = data.get("from_email", "").strip().lower()
    from_name = data.get("from_name", "")
    reply_type = data.get("reply_type", "seller")
    sentiment = data.get("sentiment", "neutral")
    interest = data.get("interest_level", "medium")
    subject = data.get("subject", "")

    if not from_email:
        return JsonResponse({"ok": False, "error": "from_email required"}, status=400)

    logger.info(f"[WEBHOOK] Email reply from {from_email} ({reply_type}, {sentiment})")

    results = {"matched": False, "action_taken": "none"}

    if reply_type == "seller":
        # Match to PropertyLead by owner_email
        props = PropertyLead.objects.filter(
            owner_email__iexact=from_email,
            status__in=["new", "contacted"],
        )
        if props.exists():
            prop = props.first()
            # Advance status based on sentiment
            if interest in ("high", "medium") and sentiment != "negative":
                prop.status = "negotiating"
                prop.contact_count = (prop.contact_count or 0) + 1
                prop.last_contacted = timezone.now()
                prop.notes = (prop.notes or "") + f"\n[{timezone.now():%Y-%m-%d}] Reply: {subject[:100]} (sentiment={sentiment})"
                prop.save(update_fields=["status", "contact_count", "last_contacted", "notes"])
                results = {"matched": True, "action_taken": "advanced_to_negotiating",
                           "property": prop.address, "lead_id": str(prop.id)}
            else:
                prop.notes = (prop.notes or "") + f"\n[{timezone.now():%Y-%m-%d}] Reply (negative/low interest): {subject[:100]}"
                prop.save(update_fields=["notes"])
                results = {"matched": True, "action_taken": "noted_negative",
                           "property": prop.address}
        else:
            # Try matching to LeadProfile (B2B)
            leads = LeadProfile.objects.filter(email__iexact=from_email)
            if leads.exists():
                lead = leads.first()
                lead.intent = "hot" if interest == "high" else "warm"
                lead.contact_count = (lead.contact_count or 0) + 1
                lead.last_contacted = timezone.now()
                lead.save(update_fields=["intent", "contact_count", "last_contacted"])

                # Check for outreach sequence
                outreach = OutreachSequence.objects.filter(
                    to_email__iexact=from_email,
                    status="sent",
                ).order_by("-sent_at").first()
                if outreach:
                    outreach.status = "replied"
                    outreach.save(update_fields=["status"])  # This triggers the signal!

                results = {"matched": True, "action_taken": "lead_updated",
                           "lead_id": str(lead.id)}

    elif reply_type == "buyer":
        # Match to InvestorBuyer
        buyers = InvestorBuyer.objects.filter(email__iexact=from_email)
        if buyers.exists():
            buyer = buyers.first()
            buyer.notes = (buyer.notes or "") + f"\n[{timezone.now():%Y-%m-%d}] Reply: {subject[:100]}"
            buyer.save(update_fields=["notes"])
            results = {"matched": True, "action_taken": "buyer_reply_logged",
                       "buyer_id": str(buyer.id)}

    return JsonResponse({"ok": True, **results})


@csrf_exempt
@require_POST
def webhook_deal_advance(request):
    """Push a deal through the pipeline stages. Called by n8n, crons, or human approval.

    POST /broker/webhook/deal-advance/
    Body: {
        "deal_id": "uuid",
        "action": "legal_review" | "approve_legal" | "engage_title" | "close_won" | "close_lost",
        "title_company": "First American Title",  (optional, for engage_title)
        "title_contact": "Jane Smith",
        "title_email": "jane@firstam.com",
        "agent": "Marcus Cole"  (who triggered this)
    }
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "Invalid JSON"}, status=400)

    deal_id = data.get("deal_id", "")
    action = data.get("action", "")
    agent = data.get("agent", "system")

    if not deal_id or not action:
        return JsonResponse({"ok": False, "error": "deal_id and action required"}, status=400)

    import uuid as _uuid
    try:
        _uuid.UUID(str(deal_id))
    except ValueError:
        return JsonResponse({"ok": False, "error": "Invalid deal_id (must be UUID)"}, status=400)

    deal = Deal.objects.filter(id=deal_id).first()
    if not deal:
        return JsonResponse({"ok": False, "error": f"Deal {deal_id} not found"}, status=404)

    from .services import (
        advance_to_legal_review,
        approve_legal_and_send_for_signing,
        close_deal as svc_close_deal,
        engage_title_company,
        _log_deal_event,
    )

    logger.info(f"[WEBHOOK] Deal advance: {deal_id} action={action} by {agent}")

    try:
        if action == "legal_review":
            deal = advance_to_legal_review(deal)
        elif action == "approve_legal":
            deal = approve_legal_and_send_for_signing(deal)
        elif action == "engage_title":
            deal = engage_title_company(
                deal,
                title_company=data.get("title_company", ""),
                title_contact=data.get("title_contact", ""),
                title_email=data.get("title_email", ""),
            )
        elif action == "close_won":
            deal = svc_close_deal(deal, won=True)
        elif action == "close_lost":
            deal = svc_close_deal(deal, won=False)
        else:
            return JsonResponse({"ok": False, "error": f"Unknown action: {action}"}, status=400)

        return JsonResponse({
            "ok": True,
            "deal_id": str(deal.id),
            "new_stage": deal.stage,
            "action": action,
            "triggered_by": agent,
        })

    except Exception as e:
        logger.error(f"[WEBHOOK] Deal advance failed: {e}")
        return JsonResponse({"ok": False, "error": str(e)}, status=500)


@csrf_exempt
@require_POST
def webhook_event_trigger(request):
    """Generic event trigger. n8n or any system can fire events into the pipeline.

    POST /broker/webhook/event/
    Body: {
        "event": "seller_replied" | "buyer_interested" | "document_signed" | "payment_received" | "call_completed",
        "deal_id": "uuid" (optional),
        "property_id": "uuid" (optional),
        "data": { ...arbitrary payload... },
        "agent": "Piper Reeves"
    }
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "Invalid JSON"}, status=400)

    event = data.get("event", "")
    deal_id = data.get("deal_id")
    property_id = data.get("property_id")
    payload = data.get("data", {})
    agent = data.get("agent", "system")

    if not event:
        return JsonResponse({"ok": False, "error": "event required"}, status=400)

    logger.info(f"[WEBHOOK] Event trigger: {event} agent={agent}")

    from .services import _log_deal_event, log_call

    result = {"event": event, "processed": True}

    if event == "call_completed" and deal_id:
        deal = Deal.objects.filter(id=deal_id).first()
        prop = PropertyLead.objects.filter(id=property_id).first() if property_id else None

        call = log_call(
            deal=deal,
            property_lead=prop,
            call_type=payload.get("call_type", "other"),
            direction=payload.get("direction", "outbound"),
            caller_agent=agent,
            contact_name=payload.get("contact_name", ""),
            contact_phone=payload.get("contact_phone", ""),
            duration_secs=payload.get("duration_secs", 0),
            notes=payload.get("notes", ""),
            seller_mood=payload.get("seller_mood", ""),
            price_discussed=payload.get("price_discussed"),
            objections=payload.get("objections", []),
            commitments=payload.get("commitments", []),
            outcome=payload.get("outcome", ""),
            followup_action=payload.get("followup_action", ""),
        )
        result["call_id"] = str(call.id)

    elif event == "seller_replied" and property_id:
        prop = PropertyLead.objects.filter(id=property_id).first()
        if prop and prop.status in ("new", "contacted"):
            prop.status = "negotiating"
            prop.save(update_fields=["status"])
            result["new_status"] = "negotiating"

    elif event == "buyer_interested" and deal_id:
        deal = Deal.objects.filter(id=deal_id).first()
        if deal and deal.stage in ("negotiating", "contracted"):
            deal.stage = "contracted"
            deal.save(update_fields=["stage"])  # Signal fires automatically
            result["new_stage"] = "contracted"

    elif event == "document_signed":
        doc_id = payload.get("document_id")
        if doc_id:
            from .models import ClientDocument
            doc = ClientDocument.objects.filter(id=doc_id).first()
            if doc:
                doc.status = "signed"
                doc.save(update_fields=["status"])  # Signal fires automatically
                result["document"] = doc.title

    elif event == "payment_received" and deal_id:
        deal = Deal.objects.filter(id=deal_id).first()
        if deal:
            from .services import record_commission
            record_commission(
                deal, "paid",
                Decimal(str(payload.get("amount", deal.commission_due))),
                description=f"Payment received via {payload.get('method', 'stripe')}",
                stripe_payout_id=payload.get("stripe_payout_id", ""),
            )
            result["commission_recorded"] = True

    else:
        # Log as generic deal event
        if deal_id:
            deal = Deal.objects.filter(id=deal_id).first()
            if deal:
                _log_deal_event(deal, "note", f"External event: {event}",
                                 json.dumps(payload)[:500], agent_name=agent)

    return JsonResponse({"ok": True, **result})


# ---------------------------------------------------------------------------
# STRIPE: Create invoice for a deal (staff only)
# ---------------------------------------------------------------------------

@csrf_exempt
@require_POST
@staff_or_internal_required
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
@staff_or_internal_required
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

@staff_or_internal_required
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
@staff_or_internal_required
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


# ===========================================================================
# WHOLESALE PIPELINE
# ===========================================================================

# ---------------------------------------------------------------------------
# Wholesale Dashboard
# ---------------------------------------------------------------------------

@login_required
@staff_member_required
def wholesale_dashboard(request):
    """
    Wholesale real estate pipeline dashboard.

    Shows property leads by status, top-scored leads, buyer count,
    and pipeline value stats.
    """
    leads = PropertyLead.objects.all()

    # Status counts
    status_counts = {}
    for row in leads.values("status").annotate(count=Count("id")):
        status_counts[row["status"]] = row["count"]

    # Aggregated stats
    total_leads = leads.count()
    avg_score = leads.aggregate(avg=Avg("motivation_score"))["avg"] or 0
    total_buyers = InvestorBuyer.objects.filter(is_active=True).count()

    # Pipeline value -- sum of assignment fees for leads that are under_contract or assigned
    pipeline_qs = leads.filter(status__in=["under_contract", "assigned"])
    pipeline_value = pipeline_qs.aggregate(total=Sum("assignment_fee"))["total"] or 0

    # Top 10 highest-scored leads
    top_leads = leads.order_by("-motivation_score", "-created_at")[:10]

    # All leads for table (with optional filters)
    filter_status = request.GET.get("status", "")
    filter_lead_type = request.GET.get("lead_type", "")
    filter_state = request.GET.get("state", "")
    filter_min_score = request.GET.get("min_score", "")

    filtered_leads = leads
    if filter_status:
        filtered_leads = filtered_leads.filter(status=filter_status)
    if filter_lead_type:
        filtered_leads = filtered_leads.filter(lead_type=filter_lead_type)
    if filter_state:
        filtered_leads = filtered_leads.filter(state__iexact=filter_state)
    if filter_min_score:
        try:
            filtered_leads = filtered_leads.filter(motivation_score__gte=int(filter_min_score))
        except ValueError:
            pass

    filtered_leads = filtered_leads.order_by("-motivation_score", "-created_at")[:100]

    # Recent outreach emails sent
    recent_outreach = OutreachSequence.objects.filter(
        sent_at__isnull=False,
    ).select_related("match", "match__lead", "match__offer").order_by("-sent_at")[:20]

    # Outreach stats
    from django.utils.timezone import now as tz_now
    from datetime import timedelta as _td
    _today = tz_now().date()
    emails_today = OutreachSequence.objects.filter(sent_at__date=_today).count()
    emails_7d = OutreachSequence.objects.filter(sent_at__gte=tz_now() - _td(days=7)).count()
    emails_total = OutreachSequence.objects.filter(sent_at__isnull=False).count()
    emails_replied = OutreachSequence.objects.filter(reply_count__gt=0).count()

    return render(request, "broker_ops/wholesale.html", {
        "active_page": "wholesale",
        "status_counts": status_counts,
        "total_leads": total_leads,
        "avg_score": avg_score,
        "total_buyers": total_buyers,
        "pipeline_value": pipeline_value,
        "top_leads": top_leads,
        "leads": filtered_leads,
        "recent_outreach": recent_outreach,
        "emails_today": emails_today,
        "emails_7d": emails_7d,
        "emails_total": emails_total,
        "emails_replied": emails_replied,
        # Current filters for the template
        "filter_status": filter_status,
        "filter_lead_type": filter_lead_type,
        "filter_state": filter_state,
        "filter_min_score": filter_min_score,
        # Choices for filter dropdowns
        "status_choices": PropertyLead.STATUS_CHOICES,
        "lead_type_choices": PropertyLead.LEAD_TYPE_CHOICES,
    })


# ---------------------------------------------------------------------------
# API: Import CSV leads
# ---------------------------------------------------------------------------

@csrf_exempt
@require_POST
@staff_or_internal_required
def api_import_leads(request):
    """
    Staff endpoint to import property leads from a CSV file upload.

    POST /broker/api/import-leads/
    Content-Type: multipart/form-data with a 'file' field.
    Optional form field 'source' (default: "propstream").
    """
    csv_file = request.FILES.get("file")
    if not csv_file:
        return JsonResponse({"error": "No file uploaded. Include a 'file' field."}, status=400)

    if not csv_file.name.lower().endswith(".csv"):
        return JsonResponse({"error": "File must be a .csv"}, status=400)

    # Cap file size at 10MB
    if csv_file.size > 10 * 1024 * 1024:
        return JsonResponse({"error": "File too large. Max 10MB."}, status=400)

    source = request.POST.get("source", "propstream")
    result = import_csv_leads_from_upload(csv_file, source=source)
    return JsonResponse({"ok": True, **result})


# ---------------------------------------------------------------------------
# API: Re-score a property lead
# ---------------------------------------------------------------------------

@csrf_exempt
@require_POST
@staff_or_internal_required
def api_score_lead(request, lead_id):
    """
    Staff endpoint to re-score a property lead's motivation score.

    POST /broker/api/score-lead/<uuid>/
    """
    lead = get_object_or_404(PropertyLead, id=lead_id)
    old_score = lead.motivation_score
    new_score = score_property(lead)
    lead.motivation_score = new_score
    lead.save(update_fields=["motivation_score", "updated_at"])

    return JsonResponse({
        "ok": True,
        "lead_id": str(lead.id),
        "old_score": old_score,
        "new_score": new_score,
    })


# ---------------------------------------------------------------------------
# API: Match buyers for a property
# ---------------------------------------------------------------------------

@staff_or_internal_required
def api_match_buyers(request, lead_id):
    """
    Staff endpoint to find matching cash buyers for a property lead.

    GET /broker/api/match-buyers/<uuid>/
    """
    lead = get_object_or_404(PropertyLead, id=lead_id)
    matches = match_property_to_buyers(lead)

    return JsonResponse({
        "ok": True,
        "lead_id": str(lead.id),
        "address": lead.address,
        "match_count": len(matches),
        "matches": matches,
    })


# ---------------------------------------------------------------------------
# API: Generate outreach SMS
# ---------------------------------------------------------------------------

@staff_or_internal_required
def api_generate_outreach(request, lead_id):
    """
    Staff endpoint to generate an SMS outreach message for a property lead.

    GET /broker/api/outreach/<uuid>/
    """
    lead = get_object_or_404(PropertyLead, id=lead_id)
    sms = generate_outreach_sms(lead)

    return JsonResponse({
        "ok": True,
        "lead_id": str(lead.id),
        "owner_name": lead.owner_name,
        "owner_phone": lead.owner_phone,
        "sms_text": sms,
        "char_count": len(sms),
    })


# ---------------------------------------------------------------------------
# PUBLIC: Investor buyer signup (no auth required)
# ---------------------------------------------------------------------------

@csrf_exempt
@require_POST
def public_investor_signup(request):
    """
    Public endpoint for cash buyers / investors to join our buyer list.

    POST /broker/investor-signup/
    Accepts JSON body with buyer details.
    Also pushes to Supabase broker_leads table.
    """
    rate_limited = _check_rate_limit(request, "public_investor_signup")
    if rate_limited:
        return rate_limited

    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    required = ["name", "email"]
    missing = [f for f in required if not payload.get(f)]
    if missing:
        return JsonResponse({"error": f"Missing fields: {missing}"}, status=400)

    # Sanitize inputs
    name = str(payload.get("name", ""))[:200].strip()
    email = str(payload.get("email", "")).strip().lower()[:254]
    phone = str(payload.get("phone", ""))[:20].strip()
    company = str(payload.get("company", ""))[:200].strip()

    # Validate buyer_type against choices
    valid_buyer_types = [c[0] for c in InvestorBuyer.BUYER_TYPE_CHOICES]
    buyer_type = str(payload.get("buyer_type", "fix_flip"))[:20]
    if buyer_type not in valid_buyer_types:
        buyer_type = "fix_flip"

    markets = payload.get("markets", [])
    if not isinstance(markets, list):
        markets = []
    markets = [str(m)[:100] for m in markets[:50]]

    property_types = payload.get("property_types", [])
    if not isinstance(property_types, list):
        property_types = []
    valid_ptypes = [c[0] for c in PropertyLead.PROPERTY_TYPE_CHOICES]
    property_types = [p for p in property_types if p in valid_ptypes][:10]

    budget_min = min(float(payload.get("budget_min", 0) or 0), 99999999)
    budget_max = min(float(payload.get("budget_max", 0) or 0), 99999999)
    cash_buyer = bool(payload.get("cash_buyer", True))

    # Check for existing buyer by email
    existing = InvestorBuyer.objects.filter(email=email).first()
    if existing:
        return JsonResponse({
            "ok": True,
            "buyer_id": str(existing.id),
            "message": "You are already on our buyer list. We will reach out with matching deals.",
        })

    buyer = InvestorBuyer.objects.create(
        name=name,
        email=email,
        phone=phone,
        company=company,
        buyer_type=buyer_type,
        markets=markets,
        property_types=property_types,
        budget_min=Decimal(str(budget_min)),
        budget_max=Decimal(str(budget_max)),
        cash_buyer=cash_buyer,
        source="investor_signup",
    )

    # Push to Supabase broker_leads table
    try:
        from hive_dashboard.supabase_client import supabase_rest
        supabase_rest("broker_leads", method="POST", data={
            "name": name,
            "email": email,
            "phone": phone,
            "company": company,
            "buyer_type": buyer_type,
            "markets": markets,
            "property_types": property_types,
            "budget_min": budget_min,
            "budget_max": budget_max,
            "cash_buyer": cash_buyer,
            "source": "investor_signup",
            "lead_type": "investor_buyer",
        })
    except Exception as exc:
        # Non-fatal -- local record is saved, Supabase sync is best-effort
        logger.warning("Supabase push failed for investor signup %s: %s", email, exc)

    return JsonResponse({
        "ok": True,
        "buyer_id": str(buyer.id),
        "message": "You are on the list. We will send you matching deals.",
    })


# ---------------------------------------------------------------------------
# CLIENT FILES: A-to-Z deal document management
# ---------------------------------------------------------------------------

@staff_or_internal_required
def client_files_dashboard(request):
    """
    Client Files dashboard: shows all deals as cards with document timelines.
    Filter by status: active, under_contract, closing, closed, dead.
    """
    files = ClientFile.objects.all()

    # Filters
    filter_status = request.GET.get("status", "")
    if filter_status:
        files = files.filter(status=filter_status)

    filter_state = request.GET.get("state", "")
    if filter_state:
        files = files.filter(state=filter_state.upper())

    # Stats
    total = ClientFile.objects.count()
    status_counts = {}
    for row in ClientFile.objects.values("status").annotate(count=Count("id")):
        status_counts[row["status"]] = row["count"]

    total_fees = ClientFile.objects.filter(
        status__in=["under_contract", "closing", "closed"]
    ).aggregate(total=Sum("assignment_fee"))["total"] or 0

    closed_revenue = ClientFile.objects.filter(
        status="closed"
    ).aggregate(total=Sum("assignment_fee"))["total"] or 0

    context = {
        "files": files[:50],
        "total": total,
        "status_counts": status_counts,
        "total_fees": total_fees,
        "closed_revenue": closed_revenue,
        "filter_status": filter_status,
        "filter_state": filter_state,
    }
    return render(request, "broker_ops/client_files.html", context)


@staff_or_internal_required
def client_file_detail(request, file_id):
    """
    Client File detail: document timeline for a single deal.
    Shows all documents in chronological order with branded HTML previews.
    """
    cf = get_object_or_404(ClientFile, id=file_id)
    documents = cf.documents.all()

    # Document type progress tracker
    doc_types = [c[0] for c in ClientDocument.DOC_TYPE_CHOICES[:8]]  # Core 8 steps
    doc_type_labels = dict(ClientDocument.DOC_TYPE_CHOICES)
    existing_types = set(documents.values_list("doc_type", flat=True))

    timeline = []
    for i, dt in enumerate(doc_types, 1):
        doc = documents.filter(doc_type=dt).first()
        timeline.append({
            "step": i,
            "type": dt,
            "label": doc_type_labels.get(dt, dt),
            "doc": doc,
            "completed": dt in existing_types,
        })

    context = {
        "cf": cf,
        "documents": documents,
        "timeline": timeline,
        "doc_count": documents.count(),
    }
    return render(request, "broker_ops/client_file_detail.html", context)


@staff_or_internal_required
def client_file_document_preview(request, doc_id):
    """Serve a branded HTML document as a standalone page."""
    doc = get_object_or_404(ClientDocument, id=doc_id)
    return HttpResponse(doc.html_content, content_type="text/html")


@staff_or_internal_required
@require_POST
def api_create_client_file(request, lead_id):
    """Create a client file from a property lead, generating initial docs."""
    from .client_files import generate_full_client_file, sync_client_file_to_supabase

    lead = get_object_or_404(PropertyLead, id=lead_id)
    cf = generate_full_client_file(lead)
    sync_client_file_to_supabase(cf)

    return JsonResponse({
        "ok": True,
        "client_file_id": str(cf.id),
        "address": cf.property_address,
        "documents": cf.document_count,
    })


@staff_or_internal_required
@require_POST
def api_generate_document(request, file_id):
    """Generate a specific document type for a client file."""
    from .client_files import (
        generate_assignment_contract,
        generate_buyer_pitch,
        generate_closing_statement,
        generate_deal_sheet,
        generate_payment_receipt,
        generate_seller_outreach,
        sync_client_file_to_supabase,
    )

    cf = get_object_or_404(ClientFile, id=file_id)

    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    doc_type = payload.get("doc_type", "")
    generators = {
        "seller_outreach": lambda: generate_seller_outreach(cf),
        "deal_sheet": lambda: generate_deal_sheet(cf),
        "assignment_contract": lambda: generate_assignment_contract(cf),
        "closing_statement": lambda: generate_closing_statement(cf),
        "payment_receipt": lambda: generate_payment_receipt(cf),
    }

    if doc_type == "buyer_pitch":
        buyer_id = payload.get("buyer_id")
        if not buyer_id:
            return JsonResponse({"error": "buyer_id required for buyer_pitch"}, status=400)
        buyer = get_object_or_404(InvestorBuyer, id=buyer_id)
        doc = generate_buyer_pitch(cf, buyer)
    elif doc_type in generators:
        doc = generators[doc_type]()
    else:
        return JsonResponse({"error": f"Unknown doc_type: {doc_type}"}, status=400)

    sync_client_file_to_supabase(cf)

    return JsonResponse({
        "ok": True,
        "document_id": str(doc.id),
        "doc_type": doc.doc_type,
        "title": doc.title,
    })


@staff_or_internal_required
@require_POST
def api_update_client_file_status(request, file_id):
    """Update client file status."""
    from .client_files import sync_client_file_to_supabase, update_client_file_status

    cf = get_object_or_404(ClientFile, id=file_id)

    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    new_status = payload.get("status", "")
    valid = [c[0] for c in ClientFile.STATUS_CHOICES]
    if new_status not in valid:
        return JsonResponse({"error": f"Invalid status. Use: {valid}"}, status=400)

    update_client_file_status(cf, new_status)
    sync_client_file_to_supabase(cf)

    return JsonResponse({"ok": True, "status": cf.status})


# ---------------------------------------------------------------------------
# API: Piper Outreach -- sends personalized seller email
# ---------------------------------------------------------------------------

@csrf_exempt
@require_POST
@staff_or_internal_required
def api_piper_outreach(request, lead_id):
    """
    Have Piper Reeves send a personalized outreach email to a property lead.

    POST /broker/api/piper-outreach/<lead_id>/

    Piper's style: Nashville warmth, empathetic, uses "y'all", gentle persuader.
    She personalizes based on lead_type, city, and property details.
    """
    import smtplib
    import os
    import random
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    try:
        lead = PropertyLead.objects.get(pk=lead_id)
    except PropertyLead.DoesNotExist:
        return JsonResponse({"error": "Lead not found"}, status=404)

    if not lead.owner_email:
        return JsonResponse({"error": "No email address for this lead"}, status=400)

    # Piper's personality
    piper_hooks = [
        f"I came across your property on {lead.address.split(',')[0] if lead.address else 'your street'} while doing some research in {lead.city}, and I wanted to reach out personally.",
        f"I know this might come out of the blue, but I've been working with homeowners in {lead.city} who are looking for simple, no-hassle solutions for their properties.",
        f"A colleague of mine flagged your property at {lead.address.split(',')[0] if lead.address else 'your address'} and I thought I'd reach out -- sometimes the timing just works out for everyone.",
    ]

    lead_context = {
        "pre_foreclosure": "I understand you might be dealing with some financial pressure on the property, and I want you to know there are options that don't involve the bank taking over.",
        "tax_lien": "Tax situations can be stressful -- y'all shouldn't have to lose a property over back taxes when there are people ready to help.",
        "probate": "I know dealing with an inherited property on top of everything else can feel overwhelming. My family went through something similar.",
        "absentee": "Managing a property from a distance is no small thing. A lot of the folks I work with just want a clean, simple transaction.",
        "divorce": "I completely understand that this is a difficult time. My goal is to make the property side of things as stress-free as possible.",
        "code_violation": "Code violations can pile up fast. The good news is, our buyers take properties as-is -- no repairs needed on your end.",
        "vacant": "Vacant properties can become a real headache with maintenance, taxes, and liability. I'd love to take that off your plate.",
        "expired_listing": "I noticed your listing didn't work out on the MLS. That happens more than you'd think. Our approach is different -- direct, fast, and no agent commissions.",
    }

    context_line = lead_context.get(lead.lead_type, "I'd love to chat about your property and see if we might be a good fit to work together.")
    hook = random.choice(piper_hooks)

    owner_first = lead.owner_name.split()[0] if lead.owner_name else "there"

    body_text = f"""Hi {owner_first},

{hook}

{context_line}

We work with cash buyers who can close quickly -- usually 10 to 14 days -- and we handle all the paperwork and closing costs. No repairs, no showings, no agent fees. Just a fair offer and a simple close.

If you'd be open to a quick conversation about what that might look like for your property, I'd love to hear from you. No pressure at all -- I'm here whenever the timing feels right.

Best,
Piper Reeves
Outreach Specialist | Everlight Ventures
piper@everlightventures.io | everlightventures.io"""

    subject_lines = [
        f"Quick question about {lead.address.split(',')[0] if lead.address else 'your property'}",
        f"Reaching out about your {lead.city} property",
        f"Cash offer for {lead.address.split(',')[0] if lead.address else 'your property'} -- no obligation",
    ]
    subject = random.choice(subject_lines)

    # Build HTML email
    body_html = body_text.replace("\n\n", "</p><p>").replace("\n", "<br>")
    html_email = f"""<!DOCTYPE html><html><body style="font-family:Georgia,serif;font-size:15px;color:#333;line-height:1.7;max-width:600px;margin:0 auto;padding:20px;">
<p>{body_html}</p>
<div style="margin-top:30px;padding-top:15px;border-top:1px solid #ddd;font-size:12px;color:#888;">
<p>Everlight Ventures | Sacramento, CA</p>
<p><a href="mailto:unsubscribe@everlightventures.io" style="color:#888;">Unsubscribe</a></p>
</div>
</body></html>"""

    # Load SMTP credentials from env
    for env_path in ["/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/03_Credentials/.env", "/home/opc/.env"]:
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    if "=" in line and not line.startswith("#"):
                        k, v = line.strip().split("=", 1)
                        os.environ.setdefault(k.strip(), v.strip())
            break

    smtp_host = os.environ.get("SMTP_HOST", "smtp.resend.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "465"))
    smtp_user = os.environ.get("SMTP_USER", "resend")
    smtp_pass = os.environ.get("SMTP_PASS", os.environ.get("RESEND_API_KEY", ""))

    if not smtp_pass:
        return JsonResponse({"error": "SMTP credentials not configured"}, status=500)

    # Send email
    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = "Piper Reeves <piper@everlightventures.io>"
        msg["To"] = lead.owner_email
        msg["Reply-To"] = "piper@everlightventures.io"
        msg["Subject"] = subject
        msg.attach(MIMEText(body_text, "plain"))
        msg.attach(MIMEText(html_email, "html"))

        with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
            server.login(smtp_user, smtp_pass)
            server.sendmail("piper@everlightventures.io", [lead.owner_email], msg.as_string())

        # Update lead status
        if lead.status == "new":
            lead.status = "contacted"
        lead.notes = (lead.notes or "") + f"\n[PIPER_OUTREACH] {datetime.now(tz=timezone.get_current_timezone()).strftime('%Y-%m-%d %H:%M')} | Subject: {subject}"
        lead.save(update_fields=["status", "notes", "updated_at"])

        # Save styled HTML report of the email + post to Slack with link
        try:
            import sys as _sys
            for _p in ["/home/opc/wholesale_agent", "/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Broker_OS/wholesale_agent"]:
                if os.path.isdir(_p) and _p not in _sys.path:
                    _sys.path.insert(0, _p)
            from gdocs_bridge import publish_report as _publish
            _report_content = (
                f"## Seller Outreach Email\n\n"
                f"**To:** {lead.owner_email}\n"
                f"**Subject:** {subject}\n"
                f"**Property:** {lead.address}, {lead.city}, {lead.state}\n"
                f"**Lead Type:** {lead.get_lead_type_display()}\n"
                f"**Motivation Score:** {lead.motivation_score}/100\n\n"
                f"---\n\n"
                f"{body_text}"
            )
            _publish(
                title=f"Piper Outreach -- {lead.city}, {lead.state}",
                content=_report_content,
                folder="01_Broker_OS/Outreach_Logs",
                slack_channel="#wholesale-deals",
                summary=f"Piper sent outreach to {lead.owner_name or lead.owner_email} re: {lead.address[:30]}",
                agent="piper_reeves",
                app="warroom",
            )
        except Exception:
            pass  # never block the response on Slack/report failure

        return JsonResponse({
            "ok": True,
            "to_email": lead.owner_email,
            "subject": subject,
            "preview": body_text[:300],
            "agent": "Piper Reeves",
        })

    except Exception as e:
        return JsonResponse({"error": f"Email send failed: {str(e)}"}, status=500)
