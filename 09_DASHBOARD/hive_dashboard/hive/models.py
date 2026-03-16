"""
Hive Mind Dashboard - Data Models
"""
from django.db import models
from django.urls import reverse
from django.utils import timezone


class AgentQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)


class Agent(models.Model):
    """An AI agent in the Hive Mind triad (Claude, Gemini, Codex, Perplexity)."""
    AGENT_CHOICES = [
        ('claude', 'Claude'),
        ('gemini', 'Gemini'),
        ('codex', 'Codex'),
        ('perplexity', 'Perplexity'),
    ]
    name = models.CharField(max_length=50, unique=True, db_index=True)
    display_name = models.CharField(max_length=100)
    role = models.CharField(max_length=200, blank=True)
    color = models.CharField(max_length=7, default='#c9a84c')
    icon_class = models.CharField(max_length=50, default='fa-robot')
    is_active = models.BooleanField(default=True)

    objects = AgentQuerySet.as_manager()

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.display_name

    @property
    def success_rate(self):
        total = self.responses.count()
        if total == 0:
            return 0
        wins = self.responses.filter(status='done').count()
        return round((wins / total) * 100, 1)

    @property
    def avg_duration(self):
        from django.db.models import Avg
        result = self.responses.filter(
            status='done', duration_seconds__isnull=False
        ).aggregate(avg=Avg('duration_seconds'))
        return round(result['avg'] or 0, 1)


class SessionQuerySet(models.QuerySet):
    def recent(self, limit=10):
        return self.order_by('-created_at')[:limit]

    def successful(self):
        return self.exclude(status='failed')

    def today(self):
        now = timezone.now()
        return self.filter(created_at__date=now.date())


class HiveSession(models.Model):
    """A single hive dispatch session with query + agent responses."""
    STATUS_CHOICES = [
        ('running', 'Running'),
        ('done', 'Completed'),
        ('partial', 'Partial'),
        ('failed', 'Failed'),
    ]
    MODE_CHOICES = [
        ('full', 'Full Dispatch'),
        ('lite', 'Lite (Perplexity Only)'),
        ('all', 'All Agents Forced'),
    ]
    session_id = models.CharField(max_length=64, unique=True, db_index=True)
    query = models.TextField()
    mode = models.CharField(max_length=20, choices=MODE_CHOICES, default='full')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='running')
    routed_to = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(db_index=True)
    duration_seconds = models.FloatField(null=True, blank=True)
    war_room_dir = models.CharField(max_length=500, blank=True)
    combined_summary = models.TextField(blank=True)
    intel_summary = models.TextField(blank=True)
    category = models.CharField(max_length=50, blank=True, db_index=True)

    objects = SessionQuerySet.as_manager()

    class Meta:
        ordering = ['-created_at']
        get_latest_by = 'created_at'

    def __str__(self):
        return f"[{self.session_id[:8]}] {self.query[:60]}"

    def get_absolute_url(self):
        return reverse('hive:session_detail', kwargs={'session_id': self.session_id})

    @property
    def agents_succeeded(self):
        return self.responses.filter(status='done').count()

    @property
    def agents_failed(self):
        return self.responses.filter(status='failed').count()

    @property
    def agents_total(self):
        return self.responses.count()

    @property
    def success_pct(self):
        total = self.agents_total
        if total == 0:
            return 0
        return round((self.agents_succeeded / total) * 100)

    @property
    def duration_display(self):
        if self.duration_seconds is None:
            return "N/A"
        s = self.duration_seconds
        if s < 60:
            return f"{s:.1f}s"
        return f"{s / 60:.1f}m"

    @property
    def status_color(self):
        return {
            'running': '#6c3fa0',
            'done': '#22c55e',
            'partial': '#eab308',
            'failed': '#ef4444',
        }.get(self.status, '#888')


class AgentResponse(models.Model):
    """One agent's response within a hive session."""
    STATUS_CHOICES = [
        ('done', 'Success'),
        ('failed', 'Failed'),
        ('timeout', 'Timeout'),
        ('skipped', 'Skipped'),
    ]
    session = models.ForeignKey(
        HiveSession, on_delete=models.CASCADE, related_name='responses'
    )
    agent = models.ForeignKey(
        Agent, on_delete=models.CASCADE, related_name='responses'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    response_text = models.TextField(blank=True)
    duration_seconds = models.FloatField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    employees_consulted = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        unique_together = [('session', 'agent')]

    def __str__(self):
        return f"{self.agent.name} -> {self.session.session_id[:8]} ({self.status})"

    @property
    def duration_display(self):
        if self.duration_seconds is None:
            return "N/A"
        return f"{self.duration_seconds:.1f}s"

    @property
    def response_preview(self):
        text = self.response_text or ""
        if len(text) > 200:
            return text[:200] + "..."
        return text


class QueryLog(models.Model):
    """Log of all queries dispatched through the hive, including from dashboard."""
    SOURCE_CHOICES = [
        ('cli', 'CLI (hive command)'),
        ('dashboard', 'Dashboard'),
        ('api', 'API'),
        ('bot', 'XLM Bot'),
    ]
    query = models.TextField()
    source = models.CharField(max_length=50, choices=SOURCE_CHOICES, default='cli')
    session = models.ForeignKey(
        HiveSession, on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.source}] {self.query[:60]}"


class SystemEvent(models.Model):
    """System-level events: agent crashes, sync errors, milestones."""
    LEVEL_CHOICES = [
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('success', 'Success'),
    ]
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default='info')
    title = models.CharField(max_length=200)
    detail = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.level}] {self.title}"
