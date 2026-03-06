from django.db import models


class Lead(models.Model):
    PRODUCT_CHOICES = [
        ("onyx", "Onyx POS"),
        ("hivemind", "Hive Mind SaaS"),
    ]
    STAGE_CHOICES = [
        ("captured", "Captured"),
        ("welcome_sent", "Welcome Sent"),
        ("nurturing", "Nurturing"),
        ("trial_started", "Trial Started"),
        ("converted", "Converted"),
        ("churned", "Churned"),
    ]

    name = models.CharField(max_length=200, blank=True)
    email = models.EmailField(unique=True)
    product = models.CharField(max_length=20, choices=PRODUCT_CHOICES)
    source = models.CharField(max_length=100, blank=True, help_text="e.g. tiktok, twitter, direct")
    funnel_stage = models.CharField(max_length=20, choices=STAGE_CHOICES, default="captured")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    emails_sent = models.IntegerField(default=0)
    last_email_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.email} ({self.product} / {self.funnel_stage})"


class FunnelEvent(models.Model):
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="events")
    event_type = models.CharField(max_length=50, help_text="e.g. page_view, signup, email_sent, email_opened, trial_start")
    metadata = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.lead.email}: {self.event_type} @ {self.timestamp}"
