from django.contrib import admin
from .models import Customer, Subscription, Payment, RevenueSnapshot


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("email", "name", "source", "stripe_customer_id", "created_at")
    search_fields = ("email", "name")
    list_filter = ("source",)


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("customer", "product", "status", "amount_cents", "created_at")
    list_filter = ("product", "status")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("customer", "product", "amount_cents", "status", "payment_type", "created_at")
    list_filter = ("product", "status", "payment_type")
    search_fields = ("customer__email",)


@admin.register(RevenueSnapshot)
class RevenueSnapshotAdmin(admin.ModelAdmin):
    list_display = ("date", "mrr_cents", "total_revenue_cents", "new_customers", "active_subscriptions")
