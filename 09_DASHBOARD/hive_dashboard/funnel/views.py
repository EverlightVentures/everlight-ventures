import json
import os
import logging
from datetime import datetime, timezone as dt_timezone

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import timezone

from business_os.services import get_trading_watchtower

from .models import Lead, FunnelEvent

log = logging.getLogger(__name__)


def _format_age_label(minutes) -> str:
    try:
        value = float(minutes)
    except Exception:
        return "Unavailable"
    if value < 1:
        return "Updated just now"
    if value < 60:
        return f"Updated {int(round(value))} min ago"
    hours = value / 60.0
    return f"Updated {hours:.1f}h ago"


def _format_price(price) -> str:
    try:
        return f"${float(price):.6f}"
    except Exception:
        return "Unavailable"


def _format_price_age(ts_value: str | None) -> str:
    if not ts_value:
        return "Timestamp unavailable"
    try:
        parsed = datetime.fromisoformat(str(ts_value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt_timezone.utc)
        age_sec = max(0, int((datetime.now(dt_timezone.utc) - parsed.astimezone(dt_timezone.utc)).total_seconds()))
        if age_sec < 60:
            return f"{age_sec}s ago"
        return f"{int(round(age_sec / 60.0))} min ago"
    except Exception:
        return "Timestamp unavailable"


def _public_state_label(value: str) -> str:
    mapping = {
        "IDLE": "Waiting for a valid setup",
        "FLAT": "Flat and waiting",
        "OPEN_POSITION": "Managing an open trade",
        "OPEN": "Managing an open trade",
        "IN_POSITION": "Managing an open trade",
    }
    raw = str(value or "").strip()
    return mapping.get(raw.upper(), raw.replace("_", " ").title() if raw else "Unknown")


def _public_signal_label(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return "No trade setup confirmed"
    return raw.replace("_", " ").title()


def _public_quality_label(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return "Monitoring"
    return raw.replace("_", " ").title()


def onyx_landing(request):
    return render(request, "funnel/onyx_landing.html")


def hivemind_landing(request):
    return render(request, "funnel/hivemind_landing.html")


def dashboard_landing(request):
    try:
        watchtower = get_trading_watchtower()
    except Exception as exc:
        log.warning("Trading watchtower unavailable for public dashboard: %s", exc)
        watchtower = {}

    public_summary = {
        "system_state": watchtower.get("public_system_state") or _public_state_label(watchtower.get("bot_state")),
        "setup_state": watchtower.get("public_setup_state") or _public_signal_label(watchtower.get("entry_signal")),
        "quality_tier": _public_quality_label(watchtower.get("quality_tier")),
        "market_climate": watchtower.get("public_market_climate") or str(watchtower.get("pulse_regime") or "unknown").replace("_", " ").title(),
        "live_price": _format_price(watchtower.get("price")),
        "live_price_age": watchtower.get("public_price_age_label") or _format_price_age(watchtower.get("price_ts")),
        "decision_age": watchtower.get("public_decision_age_label") or _format_age_label(watchtower.get("decision_age_min")),
        "research_age": watchtower.get("public_brief_age_label") or _format_age_label(watchtower.get("brief_age_min")),
        "runtime_label": f"{watchtower.get('runtime_data_dir') or 'data'} / {watchtower.get('runtime_logs_dir') or 'logs'}",
        "status_blurb": watchtower.get("public_status_blurb") or (
            "Data looks healthy and current."
            if str(watchtower.get("data_quality_status") or "").lower() == "healthy"
            else "Some telemetry is stale or degraded. Treat this page as informational until the feed recovers."
        ),
    }

    return render(
        request,
        "funnel/dashboard_landing.html",
        {
            "watchtower": watchtower,
            "public_summary": public_summary,
            "quality_flags": watchtower.get("quality_flags") or [],
            "last_trade": watchtower.get("last_trade") or {},
            "open_alert": watchtower.get("open_alert") or {},
            "telemetry_source_label": (
                "Supabase live telemetry"
                if watchtower.get("telemetry_source") == "supabase"
                else "Workspace telemetry"
            ),
        },
    )


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
    if product not in ("onyx", "hivemind", "dashboard"):
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
        metadata={
            "source": data.get("source", "landing_page"),
            "product": product,
        },
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
