"""
Broker OS - Views

Dashboard + JSON API endpoints + Stripe payment integration + Wholesale pipeline.
"""
import json
import logging
import os
from decimal import Decimal

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.db.models import Avg, Count, Q, Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from hive_dashboard.security import internal_api_required, staff_or_internal_required
from .models import BrokerMatch, ClientDocument, ClientFile, Deal, InvestorBuyer, LeadProfile, OfferListing, PropertyLead
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

    return render(request, "broker_ops/wholesale.html", {
        "active_page": "wholesale",
        "status_counts": status_counts,
        "total_leads": total_leads,
        "avg_score": avg_score,
        "total_buyers": total_buyers,
        "pipeline_value": pipeline_value,
        "top_leads": top_leads,
        "leads": filtered_leads,
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
