import uuid

from django.db import models


class BusinessEvent(models.Model):
    STATUS_CHOICES = [
        ("running", "Running"),
        ("success", "Success"),
        ("warning", "Warning"),
        ("failed", "Failed"),
        ("info", "Info"),
    ]
    PRIORITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("critical", "Critical"),
    ]

    event_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    event_type = models.CharField(max_length=100, db_index=True)
    source = models.CharField(max_length=64, db_index=True)
    entity_type = models.CharField(max_length=64, blank=True, db_index=True)
    entity_id = models.CharField(max_length=128, blank=True, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="info", db_index=True)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default="medium", db_index=True)
    revenue_impact_usd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    requires_approval = models.BooleanField(default=False, db_index=True)
    owner_agent = models.CharField(max_length=100, blank=True, db_index=True)
    summary = models.CharField(max_length=255)
    payload = models.JSONField(default=dict, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.event_type} [{self.status}]"


class BusinessAlert(models.Model):
    SEVERITY_CHOICES = [
        ("info", "Info"),
        ("warning", "Warning"),
        ("error", "Error"),
        ("critical", "Critical"),
    ]
    STATE_CHOICES = [
        ("open", "Open"),
        ("acknowledged", "Acknowledged"),
        ("resolved", "Resolved"),
    ]

    alert_key = models.CharField(max_length=160, blank=True, db_index=True)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default="warning", db_index=True)
    state = models.CharField(max_length=20, choices=STATE_CHOICES, default="open", db_index=True)
    source = models.CharField(max_length=64, db_index=True)
    summary = models.CharField(max_length=255)
    detail = models.TextField(blank=True)
    entity_type = models.CharField(max_length=64, blank=True, db_index=True)
    entity_id = models.CharField(max_length=128, blank=True, db_index=True)
    requires_approval = models.BooleanField(default=False, db_index=True)
    related_event = models.ForeignKey(
        BusinessEvent,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="alerts",
    )
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.severity}: {self.summary}"


class RevenueStream(models.Model):
    STATUS_CHOICES = [
        ("building", "Building"),
        ("pilot", "Pilot"),
        ("active", "Active"),
        ("watch", "Watch"),
        ("paused", "Paused"),
    ]

    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=120)
    owner_agent = models.CharField(max_length=100, blank=True)
    category = models.CharField(max_length=50, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="building", db_index=True)
    monthly_target_usd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    mrr_usd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    cash_today_usd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    cash_30d_usd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    pending_pipeline_usd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    last_event_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

