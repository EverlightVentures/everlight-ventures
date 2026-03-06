import json
import os
import logging

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import timezone

from .models import Lead, FunnelEvent

log = logging.getLogger(__name__)


def onyx_landing(request):
    return render(request, "funnel/onyx_landing.html")


def hivemind_landing(request):
    return render(request, "funnel/hivemind_landing.html")


def thank_you(request):
    product = request.GET.get("product", "")
    return render(request, "funnel/thank_you.html", {"product": product})


@csrf_exempt
@require_POST
def capture_lead(request):
    """API endpoint for lead capture. Accepts JSON or form POST."""
    if request.content_type == "application/json":
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
    else:
        data = request.POST

    email = data.get("email", "").strip().lower()
    if not email or "@" not in email:
        return JsonResponse({"error": "Valid email required"}, status=400)

    product = data.get("product", "onyx")
    if product not in ("onyx", "hivemind"):
        return JsonResponse({"error": "Invalid product"}, status=400)

    lead, created = Lead.objects.get_or_create(
        email=email,
        defaults={
            "name": data.get("name", "").strip(),
            "product": product,
            "source": data.get("source", "landing_page"),
        },
    )

    FunnelEvent.objects.create(
        lead=lead,
        event_type="signup" if created else "repeat_visit",
        metadata={"source": data.get("source", "landing_page")},
    )

    if created:
        _notify_slack(lead)
        log.info(f"New lead captured: {email} for {product}")

    return JsonResponse({
        "status": "ok",
        "created": created,
        "redirect": f"/funnel/thank-you/?product={product}",
    })


def _notify_slack(lead: Lead):
    """Post new lead notification to Slack #04-content-factory."""
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook_url:
        return

    try:
        import requests
        requests.post(webhook_url, json={
            "text": f"New lead: {lead.email} | Product: {lead.product} | Source: {lead.source}",
            "channel": "#04-content-factory",
        }, timeout=5)
    except Exception as e:
        log.warning(f"Slack notification failed: {e}")


def funnel_stats(request):
    """Dashboard-facing stats endpoint (JSON)."""
    today = timezone.now().date()
    from django.db.models import Count
    from datetime import timedelta

    week_ago = today - timedelta(days=7)
    stats = {
        "leads_today": Lead.objects.filter(created_at__date=today).count(),
        "leads_this_week": Lead.objects.filter(created_at__date__gte=week_ago).count(),
        "leads_total": Lead.objects.count(),
        "by_product": dict(
            Lead.objects.values_list("product").annotate(c=Count("id")).values_list("product", "c")
        ),
        "by_stage": dict(
            Lead.objects.values_list("funnel_stage").annotate(c=Count("id")).values_list("funnel_stage", "c")
        ),
    }
    return JsonResponse(stats)
