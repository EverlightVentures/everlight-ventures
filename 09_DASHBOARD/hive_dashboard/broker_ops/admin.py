from django.contrib import admin
from django.utils.html import format_html

from .models import BrokerMatch, CommissionRecord, Deal, LeadProfile, OfferListing, OutreachSequence


@admin.register(OfferListing)
class OfferListingAdmin(admin.ModelAdmin):
    list_display  = ("title", "seller_name", "category", "price_min", "price_max",
                     "commission_pct", "status", "source", "created_at")
    list_filter   = ("category", "status", "pricing_model", "source")
    search_fields = ("title", "seller_name", "seller_email", "description")
    readonly_fields = ("id", "created_at", "updated_at")
    list_editable  = ("status",)


@admin.register(LeadProfile)
class LeadProfileAdmin(admin.ModelAdmin):
    list_display  = ("name", "company", "role", "intent", "lead_source",
                     "contact_count", "unsubscribed", "created_at")
    list_filter   = ("intent", "lead_source", "unsubscribed", "company_size")
    search_fields = ("name", "email", "company", "need_description")
    readonly_fields = ("id", "created_at", "updated_at")
    list_editable  = ("intent", "unsubscribed")


@admin.register(BrokerMatch)
class BrokerMatchAdmin(admin.ModelAdmin):
    list_display  = ("offer", "lead", "match_score", "status", "matched_by",
                     "outreach_sent_at", "created_at")
    list_filter   = ("status", "matched_by")
    search_fields = ("offer__title", "lead__name", "match_reasoning")
    readonly_fields = ("id", "created_at", "updated_at")
    list_editable  = ("status",)
    ordering = ["-match_score"]


@admin.register(Deal)
class DealAdmin(admin.ModelAdmin):
    list_display  = ("offer", "lead", "stage", "deal_value", "commission_pct",
                     "commission_due", "started_at", "closed_at")
    list_filter   = ("stage",)
    search_fields = ("offer__title", "lead__name", "notes")
    readonly_fields = ("id", "commission_due", "created_at")
    list_editable  = ("stage",)


@admin.register(OutreachSequence)
class OutreachSequenceAdmin(admin.ModelAdmin):
    list_display  = ("match", "step", "to_email", "status", "scheduled_at", "sent_at")
    list_filter   = ("step", "status")
    search_fields = ("to_email", "subject")
    readonly_fields = ("id", "created_at")
    list_editable  = ("status",)


@admin.register(CommissionRecord)
class CommissionRecordAdmin(admin.ModelAdmin):
    list_display  = ("deal", "record_type", "amount", "currency", "description", "created_at")
    list_filter   = ("record_type", "currency")
    search_fields = ("description", "reference", "stripe_payout_id")
    readonly_fields = ("id", "created_at")
