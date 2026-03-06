from django.contrib import admin
from .models import Lead, FunnelEvent


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ["email", "product", "funnel_stage", "source", "emails_sent", "created_at"]
    list_filter = ["product", "funnel_stage", "source"]
    search_fields = ["email", "name"]


@admin.register(FunnelEvent)
class FunnelEventAdmin(admin.ModelAdmin):
    list_display = ["lead", "event_type", "timestamp"]
    list_filter = ["event_type"]
