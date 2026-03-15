from django.contrib import admin

from .models import BusinessAlert, BusinessEvent, RevenueStream


@admin.register(BusinessEvent)
class BusinessEventAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "event_type",
        "source",
        "status",
        "priority",
        "entity_type",
        "entity_id",
        "requires_approval",
    )
    list_filter = ("status", "priority", "source", "entity_type", "requires_approval")
    search_fields = ("event_type", "summary", "entity_id", "owner_agent")
    readonly_fields = ("event_id", "created_at", "updated_at")


@admin.register(BusinessAlert)
class BusinessAlertAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "severity",
        "state",
        "source",
        "summary",
        "requires_approval",
    )
    list_filter = ("severity", "state", "source", "requires_approval")
    search_fields = ("summary", "detail", "entity_id", "alert_key")
    readonly_fields = ("created_at", "resolved_at")


@admin.register(RevenueStream)
class RevenueStreamAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "status",
        "owner_agent",
        "mrr_usd",
        "cash_today_usd",
        "cash_30d_usd",
        "pending_pipeline_usd",
        "last_event_at",
    )
    list_filter = ("status", "owner_agent", "category")
    search_fields = ("name", "slug", "notes")
    readonly_fields = ("created_at", "updated_at", "last_event_at")

