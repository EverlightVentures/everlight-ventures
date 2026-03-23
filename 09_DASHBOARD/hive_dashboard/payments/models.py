import os
from django.db import models
from django.utils import timezone


class Customer(models.Model):
    """A customer across any Everlight product."""
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=200, blank=True)
    stripe_customer_id = models.CharField(max_length=100, blank=True, db_index=True)
    source = models.CharField(max_length=50, blank=True, help_text="Which product brought them in")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    metadata = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"{self.name or self.email} ({self.source})"

    class Meta:
        ordering = ["-created_at"]


class Subscription(models.Model):
    """Active subscriptions (Onyx POS, Hive Mind, etc.)."""
    STATUS_CHOICES = [
        ("trialing", "Trialing"),
        ("active", "Active"),
        ("past_due", "Past Due"),
        ("canceled", "Canceled"),
        ("paused", "Paused"),
    ]
    PRODUCT_CHOICES = [
        ("onyx_pro", "Onyx POS Pro -- $49/mo"),
        ("hivemind_starter", "Hive Mind Starter -- $29/mo"),
        ("hivemind_pro", "Hive Mind Pro -- $79/mo"),
        ("hivemind_enterprise", "Hive Mind Enterprise -- $149/mo"),
        ("alley_kingz_vip", "Alley Kingz VIP -- $4.99/mo"),
        ("ai_consulting_retainer", "AI Consulting Retainer -- $2,000/mo"),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="subscriptions")
    stripe_subscription_id = models.CharField(max_length=100, unique=True)
    product = models.CharField(max_length=50, choices=PRODUCT_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="trialing")
    amount_cents = models.IntegerField(help_text="Monthly amount in cents")
    trial_end = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    canceled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.customer.email} -- {self.get_product_display()} [{self.status}]"

    @property
    def mrr_dollars(self):
        if self.status in ("active", "trialing"):
            return self.amount_cents / 100
        return 0

    class Meta:
        ordering = ["-created_at"]


class Payment(models.Model):
    """Every payment event from Stripe."""
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="payments")
    stripe_payment_id = models.CharField(max_length=100, unique=True)
    product = models.CharField(max_length=100)
    amount_cents = models.IntegerField()
    currency = models.CharField(max_length=10, default="usd")
    status = models.CharField(max_length=30, default="succeeded")
    payment_type = models.CharField(max_length=30, default="subscription",
                                     help_text="subscription, one_time, invoice")
    description = models.TextField(blank=True)
    receipt_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    stripe_created = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"${self.amount_cents/100:.2f} -- {self.product} -- {self.customer.email}"

    @property
    def amount_dollars(self):
        return self.amount_cents / 100

    class Meta:
        ordering = ["-created_at"]


class ConsultingProject(models.Model):
    """AI Consulting project pipeline tracker."""
    STATUS_CHOICES = [
        ("discovery", "Discovery Call"),
        ("proposal", "Proposal Sent"),
        ("building", "Building"),
        ("delivered", "Delivered"),
        ("retainer", "Active Retainer"),
        ("churned", "Churned"),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="consulting_projects")
    business_name = models.CharField(max_length=200)
    vertical = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="discovery")
    discovery_date = models.DateTimeField(null=True, blank=True)
    build_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    retainer_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    solutions_deployed = models.JSONField(default=list, blank=True,
                                           help_text='["lead_gen_bot", "support_bot"]')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.business_name} [{self.get_status_display()}]"

    @property
    def total_value(self):
        return float(self.build_amount) + float(self.retainer_amount)

    class Meta:
        ordering = ["-updated_at"]


class RevenueSnapshot(models.Model):
    """Daily revenue snapshot for dashboard charts."""
    date = models.DateField(unique=True)
    mrr_cents = models.IntegerField(default=0, help_text="Monthly Recurring Revenue")
    total_revenue_cents = models.IntegerField(default=0, help_text="Total revenue that day")
    new_customers = models.IntegerField(default=0)
    churned = models.IntegerField(default=0)
    active_subscriptions = models.IntegerField(default=0)
    breakdown = models.JSONField(default=dict, blank=True,
                                  help_text="Revenue per product")

    def __str__(self):
        return f"{self.date} -- MRR ${self.mrr_cents/100:.0f}"

    class Meta:
        ordering = ["-date"]
