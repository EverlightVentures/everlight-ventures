"""
Hive Mind Dashboard - Django Admin Customization
Everlight Ventures OS
"""
from django.contrib import admin
from django.utils.html import format_html

from .models import Agent, AgentResponse, HiveSession, QueryLog, SystemEvent

# ---------------------------------------------------------------------------
# Admin site branding
# ---------------------------------------------------------------------------
admin.site.site_header = "Hive Mind Admin | Everlight"
admin.site.site_title = "Hive Mind Admin"
admin.site.index_title = "Dashboard"


# ---------------------------------------------------------------------------
# Inlines
# ---------------------------------------------------------------------------

class AgentResponseInline(admin.TabularInline):
    model = AgentResponse
    extra = 0
    readonly_fields = (
        'agent', 'status', 'duration_seconds', 'error_message',
        'employees_consulted', 'created_at', 'response_preview_short',
    )
    fields = (
        'agent', 'status', 'duration_seconds', 'error_message',
        'employees_consulted', 'created_at', 'response_preview_short',
    )

    def response_preview_short(self, obj):
        text = obj.response_text or ""
        if len(text) > 120:
            return text[:120] + "..."
        return text or "-"
    response_preview_short.short_description = "Response preview"

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# ---------------------------------------------------------------------------
# HiveSession
# ---------------------------------------------------------------------------

@admin.register(HiveSession)
class HiveSessionAdmin(admin.ModelAdmin):
    list_display = (
        'session_id', 'query_short', 'mode', 'status_badge',
        'agents_succeeded_display', 'agents_total', 'duration_display',
        'created_at',
    )
    list_filter = ('status', 'mode', 'category')
    search_fields = ('query', 'session_id')
    date_hierarchy = 'created_at'
    readonly_fields = (
        'session_id', 'query', 'mode', 'status', 'routed_to',
        'created_at', 'duration_seconds', 'war_room_dir',
        'combined_summary', 'intel_summary', 'category',
        'agents_succeeded', 'agents_failed', 'agents_total',
        'success_pct', 'duration_display',
    )
    inlines = [AgentResponseInline]
    list_per_page = 30

    def query_short(self, obj):
        q = obj.query or ""
        if len(q) > 50:
            return q[:50] + "..."
        return q
    query_short.short_description = "Query"

    def status_badge(self, obj):
        colors = {
            'done': '#22c55e',
            'failed': '#ef4444',
            'running': '#6c3fa0',
            'partial': '#eab308',
        }
        color = colors.get(obj.status, '#888')
        return format_html(
            '<span style="background:{}; color:#fff; padding:2px 8px; '
            'border-radius:4px; font-size:11px; font-weight:600;">{}</span>',
            color, obj.get_status_display(),
        )
    status_badge.short_description = "Status"
    status_badge.admin_order_field = 'status'

    def agents_succeeded_display(self, obj):
        return obj.agents_succeeded
    agents_succeeded_display.short_description = "Succeeded"


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'display_name', 'role', 'is_active',
        'success_rate_display', 'avg_duration_display',
    )
    list_filter = ('is_active',)
    search_fields = ('name', 'display_name')

    def success_rate_display(self, obj):
        rate = obj.success_rate
        if rate >= 80:
            color = '#22c55e'
        elif rate >= 50:
            color = '#eab308'
        else:
            color = '#ef4444'
        return format_html(
            '<span style="color:{}; font-weight:600;">{:.1f}%</span>',
            color, rate,
        )
    success_rate_display.short_description = "Success Rate"

    def avg_duration_display(self, obj):
        d = obj.avg_duration
        if d < 60:
            return f"{d:.1f}s"
        return f"{d / 60:.1f}m"
    avg_duration_display.short_description = "Avg Duration"


# ---------------------------------------------------------------------------
# AgentResponse (standalone view)
# ---------------------------------------------------------------------------

@admin.register(AgentResponse)
class AgentResponseAdmin(admin.ModelAdmin):
    list_display = (
        'agent', 'session_link', 'status', 'duration_seconds', 'created_at',
    )
    list_filter = ('status', 'agent')
    search_fields = ('session__session_id', 'agent__name', 'response_text')
    readonly_fields = (
        'session', 'agent', 'status', 'response_text',
        'duration_seconds', 'error_message', 'employees_consulted',
        'created_at',
    )
    list_per_page = 30

    def session_link(self, obj):
        return format_html(
            '<a href="/admin/hive/hivesession/{}/">{}</a>',
            obj.session.pk, obj.session.session_id[:12],
        )
    session_link.short_description = "Session"


# ---------------------------------------------------------------------------
# QueryLog
# ---------------------------------------------------------------------------

@admin.register(QueryLog)
class QueryLogAdmin(admin.ModelAdmin):
    list_display = ('query_short', 'source', 'session', 'created_at')
    list_filter = ('source',)
    search_fields = ('query',)
    list_per_page = 30

    def query_short(self, obj):
        q = obj.query or ""
        if len(q) > 60:
            return q[:60] + "..."
        return q
    query_short.short_description = "Query"


# ---------------------------------------------------------------------------
# SystemEvent
# ---------------------------------------------------------------------------

@admin.register(SystemEvent)
class SystemEventAdmin(admin.ModelAdmin):
    list_display = ('level_badge', 'title', 'created_at')
    list_filter = ('level',)
    search_fields = ('title', 'detail')
    list_per_page = 30

    def level_badge(self, obj):
        colors = {
            'info': '#3b82f6',
            'warning': '#eab308',
            'error': '#ef4444',
            'success': '#22c55e',
        }
        color = colors.get(obj.level, '#888')
        return format_html(
            '<span style="background:{}; color:#fff; padding:2px 8px; '
            'border-radius:4px; font-size:11px; font-weight:600;">{}</span>',
            color, obj.get_level_display(),
        )
    level_badge.short_description = "Level"
    level_badge.admin_order_field = 'level'
