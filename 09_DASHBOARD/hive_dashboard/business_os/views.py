from django.http import JsonResponse
from django.views.generic import TemplateView

from broker_ops.models import BrokerMatch, Deal

from .services import get_ceo_snapshot


class BusinessOSDashboardView(TemplateView):
    template_name = "business_os/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        snapshot = get_ceo_snapshot()
        ctx.update(snapshot)
        ctx["active_page"] = "business_os"
        ctx["broker_matches"] = (
            BrokerMatch.objects.select_related("offer", "lead")
            .filter(status__in=["pending", "approved"])
            .order_by("-match_score", "-created_at")[:8]
        )
        ctx["broker_deals"] = (
            Deal.objects.select_related("offer", "lead")
            .order_by("-created_at")[:8]
        )
        return ctx


def api_snapshot(request):
    snapshot = get_ceo_snapshot()
    payload = {
        "cash_today": float(snapshot["cash_today"]),
        "mrr_total": float(snapshot["mrr_total"]),
        "affiliate_today": float(snapshot["affiliate_today"]),
        "pending_pipeline": float(snapshot["pending_pipeline"]),
        "failed_workflows": snapshot["failed_workflows"],
        "open_approvals": snapshot["open_approvals"],
        "active_incidents": snapshot["active_incidents"],
        "events_today": snapshot["events_today"],
        "status_counts": snapshot["status_counts"],
        "streams": [
            {
                "slug": stream.slug,
                "name": stream.name,
                "status": stream.status,
                "owner_agent": stream.owner_agent,
                "mrr_usd": float(stream.mrr_usd),
                "cash_today_usd": float(stream.cash_today_usd),
                "cash_30d_usd": float(stream.cash_30d_usd),
                "pending_pipeline_usd": float(stream.pending_pipeline_usd),
                "notes": stream.notes,
            }
            for stream in snapshot["streams"]
        ],
        "trading_watchtower": snapshot["trading_watchtower"],
        "blackjack_watchtower": snapshot["blackjack_watchtower"],
        "trading_reports": snapshot["trading_reports"],
    }
    return JsonResponse(payload)
