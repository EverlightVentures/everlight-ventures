"""
Hive Mind Dashboard - Custom Template Tags & Filters
Everlight Ventures OS
"""
import json

from django import template
from django.utils.safestring import mark_safe

register = template.Library()

# ---------------------------------------------------------------------------
# Color / icon maps (single source of truth)
# ---------------------------------------------------------------------------

AGENT_COLORS = {
    'claude': '#8b5cf6',
    'gemini': '#22d3ee',
    'codex': '#22c55e',
    'perplexity': '#f59e0b',
}

AGENT_ICONS = {
    'claude': 'fa-brain',
    'gemini': 'fa-gem',
    'codex': 'fa-code',
    'perplexity': 'fa-search',
}

STATUS_COLORS = {
    'done': '#22c55e',
    'failed': '#ef4444',
    'running': '#6c3fa0',
    'partial': '#eab308',
    'timeout': '#f97316',
    'skipped': '#6b7280',
}

STATUS_LABELS = {
    'done': 'Done',
    'failed': 'Failed',
    'running': 'Running',
    'partial': 'Partial',
    'timeout': 'Timeout',
    'skipped': 'Skipped',
}


# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------

@register.filter(name='status_badge')
def status_badge(status):
    """Return an HTML span badge colored by status string."""
    color = STATUS_COLORS.get(status, '#6b7280')
    label = STATUS_LABELS.get(status, status.title() if status else 'Unknown')
    return mark_safe(
        f'<span style="display:inline-block; background:{color}; color:#fff; '
        f'padding:2px 10px; border-radius:9999px; font-size:0.75rem; '
        f'font-weight:600; letter-spacing:0.02em;">{label}</span>'
    )


@register.filter(name='duration_fmt')
def duration_fmt(seconds):
    """Format seconds to human-readable: '12.3s' or '2m 15s'."""
    if seconds is None:
        return "N/A"
    try:
        s = float(seconds)
    except (TypeError, ValueError):
        return "N/A"
    if s < 60:
        return f"{s:.1f}s"
    minutes = int(s // 60)
    remaining = int(s % 60)
    return f"{minutes}m {remaining}s"


@register.filter(name='truncate_middle')
def truncate_middle(value, length=40):
    """Truncate a string with '...' in the middle if it exceeds length."""
    if not value:
        return ""
    value = str(value)
    try:
        length = int(length)
    except (TypeError, ValueError):
        length = 40
    if len(value) <= length:
        return value
    # Split: slightly more on the left side
    left = (length - 3) // 2 + (length - 3) % 2
    right = (length - 3) // 2
    return value[:left] + "..." + value[-right:]


@register.filter(name='agent_color')
def agent_color(name):
    """Map agent name (lowercase) to its hex color."""
    if not name:
        return '#6b7280'
    return AGENT_COLORS.get(str(name).lower().strip(), '#6b7280')


@register.filter(name='agent_icon')
def agent_icon(name):
    """Map agent name to Font Awesome icon class."""
    if not name:
        return 'fa-robot'
    return AGENT_ICONS.get(str(name).lower().strip(), 'fa-robot')


@register.filter(name='pct_bar_width')
def pct_bar_width(value):
    """Convert a 0-100 float to a CSS width string like '72.5%'."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        v = 0
    v = max(0.0, min(100.0, v))
    return f"{v:.1f}%"


@register.filter(name='json_pretty')
def json_pretty(value):
    """Pretty-print a JSON-serializable value (dict, list, or JSON string)."""
    if value is None:
        return ""
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value
    try:
        formatted = json.dumps(value, indent=2, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return str(value)
    # Wrap in <pre> for display
    escaped = (
        formatted
        .replace('&', '&amp;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
    )
    return mark_safe(
        f'<pre style="background:#1a1a2e; color:#e0e0e0; padding:12px; '
        f'border-radius:8px; font-size:0.8rem; overflow-x:auto; '
        f'max-height:400px;">{escaped}</pre>'
    )


# ---------------------------------------------------------------------------
# Simple tags
# ---------------------------------------------------------------------------

@register.simple_tag(name='agent_pulse')
def agent_pulse(agent_name):
    """Return HTML for an animated pulse dot using the agent's color."""
    color = AGENT_COLORS.get(
        str(agent_name).lower().strip() if agent_name else '', '#6b7280'
    )
    return mark_safe(
        f'<span style="display:inline-block; position:relative; '
        f'width:10px; height:10px;">'
        f'<span style="position:absolute; inset:0; border-radius:50%; '
        f'background:{color}; opacity:0.6; '
        f'animation:hive-pulse 1.5s ease-in-out infinite;"></span>'
        f'<span style="position:absolute; inset:2px; border-radius:50%; '
        f'background:{color};"></span>'
        f'</span>'
        f'<style>'
        f'@keyframes hive-pulse {{'
        f'  0%, 100% {{ transform: scale(1); opacity: 0.6; }}'
        f'  50% {{ transform: scale(1.8); opacity: 0; }}'
        f'}}'
        f'</style>'
    )


# ---------------------------------------------------------------------------
# Inclusion tags
# ---------------------------------------------------------------------------

@register.inclusion_tag('hive/partials/agent_card.html')
def render_agent_card(agent):
    """
    Render an agent card partial.

    Args:
        agent: dict with keys like 'agent' (Agent model or dict with
               name/display_name/color/icon_class), 'total_responses',
               'success_rate', 'avg_duration'.
    """
    # Support both Agent model instances and plain dicts
    if hasattr(agent, 'get'):
        # It is a dict (from DashboardView._agent_cards)
        agent_obj = agent.get('agent')
        name = getattr(agent_obj, 'name', '') if agent_obj else agent.get('name', '')
        display_name = getattr(agent_obj, 'display_name', '') if agent_obj else agent.get('display_name', name)
        color = getattr(agent_obj, 'color', '') if agent_obj else agent.get('color', '')
        icon_class = getattr(agent_obj, 'icon_class', '') if agent_obj else agent.get('icon_class', '')
        is_active = getattr(agent_obj, 'is_active', True) if agent_obj else agent.get('is_active', True)
        total_responses = agent.get('total_responses', 0)
        success_rate = agent.get('success_rate', 0)
        avg_duration = agent.get('avg_duration', 0)
    else:
        # It is an Agent model instance
        name = agent.name
        display_name = agent.display_name
        color = agent.color
        icon_class = agent.icon_class
        is_active = agent.is_active
        total_responses = 0
        success_rate = agent.success_rate
        avg_duration = agent.avg_duration

    name_lower = str(name).lower().strip()

    return {
        'agent_name': name,
        'agent_display_name': display_name,
        'agent_color': color or AGENT_COLORS.get(name_lower, '#6b7280'),
        'agent_icon': icon_class or AGENT_ICONS.get(name_lower, 'fa-robot'),
        'agent_is_active': is_active,
        'agent_total_responses': total_responses,
        'agent_success_rate': success_rate,
        'agent_avg_duration': avg_duration,
    }
