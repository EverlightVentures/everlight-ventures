"""
Rewards Engine -- Django Admin
Configured for operator management of tiers, comps, and player accounts.
"""
from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html

from rewards.models import (
    LoyaltyAccount,
    LoyaltyTransaction,
    CompThreshold,
    CompReward,
    ReferralUse,
    DailyLoginReward,
)


@admin.register(LoyaltyAccount)
class LoyaltyAccountAdmin(admin.ModelAdmin):
    list_display = [
        "customer_email", "tier", "points_balance", "points_lifetime",
        "total_spent_display", "login_streak", "referral_count", "referral_code",
    ]
    list_filter = ["tier"]
    search_fields = ["customer__email", "customer__name", "referral_code"]
    readonly_fields = ["referral_code", "created_at", "updated_at"]
    ordering = ["-points_lifetime"]

    def customer_email(self, obj):
        return obj.customer.email
    customer_email.short_description = "Email"
    customer_email.admin_order_field = "customer__email"

    def total_spent_display(self, obj):
        return f"${obj.total_spent_cents / 100:.2f}"
    total_spent_display.short_description = "Total Spent"
    total_spent_display.admin_order_field = "total_spent_cents"


@admin.register(LoyaltyTransaction)
class LoyaltyTransactionAdmin(admin.ModelAdmin):
    list_display = [
        "customer_email", "transaction_type", "points_display",
        "balance_after", "description", "created_at",
    ]
    list_filter = ["transaction_type"]
    search_fields = ["account__customer__email", "description", "reference_id"]
    readonly_fields = ["created_at"]
    ordering = ["-created_at"]

    def customer_email(self, obj):
        return obj.account.customer.email
    customer_email.short_description = "Email"

    def points_display(self, obj):
        color = "green" if obj.points >= 0 else "red"
        sign = "+" if obj.points >= 0 else ""
        return format_html(
            '<span style="color: {};">{}{}</span>', color, sign, obj.points
        )
    points_display.short_description = "Points"


@admin.register(CompThreshold)
class CompThresholdAdmin(admin.ModelAdmin):
    list_display = [
        "name", "spend_threshold_display", "comp_type", "comp_value",
        "points_cost", "is_repeating", "is_active",
    ]
    list_filter = ["comp_type", "is_active", "is_repeating", "product_filter"]
    search_fields = ["name", "description"]
    ordering = ["spend_threshold_cents"]

    def spend_threshold_display(self, obj):
        return f"${obj.spend_threshold_cents / 100:.0f}"
    spend_threshold_display.short_description = "Spend Threshold"
    spend_threshold_display.admin_order_field = "spend_threshold_cents"


@admin.register(CompReward)
class CompRewardAdmin(admin.ModelAdmin):
    list_display = [
        "customer_email", "comp_type", "value", "status",
        "triggered_at", "fulfilled_at", "expires_at",
    ]
    list_filter = ["status", "comp_type"]
    search_fields = ["account__customer__email", "description", "value"]
    readonly_fields = ["triggered_at"]
    ordering = ["-triggered_at"]
    actions = ["mark_fulfilled", "mark_notified"]

    def customer_email(self, obj):
        return obj.account.customer.email
    customer_email.short_description = "Email"

    def mark_fulfilled(self, request, queryset):
        queryset.update(status="fulfilled", fulfilled_at=timezone.now())
        self.message_user(request, f"{queryset.count()} comps marked as fulfilled.")
    mark_fulfilled.short_description = "Mark selected as fulfilled"

    def mark_notified(self, request, queryset):
        queryset.update(status="notified")
        self.message_user(request, f"{queryset.count()} comps marked as notified.")
    mark_notified.short_description = "Mark selected as notified"


@admin.register(ReferralUse)
class ReferralUseAdmin(admin.ModelAdmin):
    list_display = [
        "referrer_email", "referee_email", "converted",
        "referrer_points_awarded", "signed_up_at", "converted_at",
    ]
    list_filter = ["converted"]
    search_fields = ["referrer__customer__email", "referee_email"]
    readonly_fields = ["signed_up_at"]
    ordering = ["-signed_up_at"]

    def referrer_email(self, obj):
        return obj.referrer.customer.email
    referrer_email.short_description = "Referrer"


@admin.register(DailyLoginReward)
class DailyLoginRewardAdmin(admin.ModelAdmin):
    list_display = [
        "streak_day", "points_reward", "is_milestone",
        "chips_bonus", "gems_bonus", "label",
    ]
    list_filter = ["is_milestone"]
    ordering = ["streak_day"]
