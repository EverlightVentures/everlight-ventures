"""
Hive Mind Dashboard - Views
Luxurious AI command center for the Hive Mind triad.
"""
import json
import logging
import os
import subprocess
import sys
import uuid
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

from django.conf import settings
from django.db.models import Avg, Count, F, Max, Q, Sum
from django.db.models.functions import TruncDate
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView, ListView, TemplateView

from django.views.decorators.csrf import csrf_exempt

from .models import Agent, AgentResponse, HiveSession, QueryLog, SystemEvent

# Progress tracking directory (shared with dispatcher)
HIVE_WORKSPACE = Path(
    getattr(settings, 'HIVE_WORKSPACE', '/mnt/sdcard/AA_MY_DRIVE')
)
HIVE_PROGRESS_DIR = HIVE_WORKSPACE / '_logs' / '.hive_active'
XLM_BOT_DIR = HIVE_WORKSPACE / 'xlm_bot'

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_htmx(request):
    """Check for HTMX request. Works with django-htmx middleware."""
    return getattr(request, 'htmx', False)


def _pick_template(request, full, partial):
    """Return partial template for HTMX requests, full otherwise."""
    if _is_htmx(request):
        return partial
    return full


# ---------------------------------------------------------------------------
# 1. DashboardView - Home page
# ---------------------------------------------------------------------------

class DashboardView(TemplateView):
    template_name = 'hive/dashboard.html'

    def get_template_names(self):
        if _is_htmx(self.request):
            return ['hive/partials/dashboard_content.html']
        return [self.template_name]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        sessions = HiveSession.objects.all()
        total = sessions.count()
        successful = sessions.filter(status='done').count()

        # Aggregate stats
        agg = sessions.aggregate(
            avg_duration=Avg('duration_seconds'),
            total_duration=Sum('duration_seconds'),
        )
        today_count = sessions.filter(created_at__gte=today_start).count()

        ctx['active_page'] = 'dashboard'
        ctx.update({
            'total_sessions': total,
            'today_sessions': today_count,
            'success_rate': round((successful / total * 100), 1) if total else 0,
            'avg_duration': round(agg['avg_duration'] or 0, 1),
            'total_duration': round(agg['total_duration'] or 0, 1),

            # Active agents
            'active_agents': Agent.objects.active(),
            'active_agents_count': Agent.objects.active().count(),
            'total_agents': Agent.objects.count(),

            # Recent sessions (last 5)
            'recent_sessions': sessions.prefetch_related(
                'responses__agent'
            ).order_by('-created_at')[:5],

            # Recent events
            'recent_events': SystemEvent.objects.all()[:8],

            # Agent status cards with inline stats
            'agent_cards': self._agent_cards(),

            # Quick stats for sparkline or counters
            'sessions_by_status': {
                s['status']: s['count']
                for s in sessions.values('status').annotate(
                    count=Count('id')
                )
            },

            # Modes distribution
            'sessions_by_mode': {
                m['mode']: m['count']
                for m in sessions.values('mode').annotate(
                    count=Count('id')
                )
            },
        })

        # 7-day activity chart
        seven_days_ago = now - timedelta(days=7)
        daily_data = (
            HiveSession.objects
            .filter(created_at__gte=seven_days_ago)
            .annotate(date=TruncDate('created_at'))
            .values('date')
            .annotate(
                count=Count('id'),
                successes=Count('id', filter=Q(status='done')),
            )
            .order_by('date')
        )
        date_map = {d['date']: d for d in daily_data}
        chart_days, chart_counts, chart_successes = [], [], []
        for i in range(6, -1, -1):
            day = (now - timedelta(days=i)).date()
            entry = date_map.get(day, {})
            chart_days.append(day.strftime('%b %d'))
            chart_counts.append(entry.get('count', 0))
            chart_successes.append(entry.get('successes', 0))
        ctx['chart_7d_labels'] = json.dumps(chart_days)
        ctx['chart_7d_counts'] = json.dumps(chart_counts)
        ctx['chart_7d_successes'] = json.dumps(chart_successes)

        return ctx

    def _agent_cards(self):
        """Build per-agent stat cards using a single query."""
        agents = Agent.objects.all()
        stats = AgentResponse.objects.values('agent_id').annotate(
            total=Count('id'),
            successes=Count('id', filter=Q(status='done')),
            avg_dur=Avg('duration_seconds', filter=Q(
                status='done', duration_seconds__isnull=False
            )),
        )
        stat_map = {s['agent_id']: s for s in stats}

        # Get last status per agent (SQLite-compatible, no DISTINCT ON)
        latest_ids = (
            AgentResponse.objects
            .values('agent_id')
            .annotate(latest_id=Max('id'))
            .values_list('latest_id', flat=True)
        )
        last_responses = (
            AgentResponse.objects
            .filter(id__in=list(latest_ids))
            .values('agent_id', 'status')
        )
        last_status_map = {r['agent_id']: r['status'] for r in last_responses}

        cards = []
        for agent in agents:
            s = stat_map.get(agent.id, {
                'total': 0, 'successes': 0, 'avg_dur': None
            })
            total = s['total']
            cards.append({
                'agent': agent,
                # Flat keys so template can use ac.color, ac.display_name etc.
                'display_name': agent.display_name,
                'color': agent.color,
                'icon_class': agent.icon_class,
                'last_status': last_status_map.get(agent.id, ''),
                'total_responses': total,
                'success_rate': round(
                    (s['successes'] / total * 100), 1
                ) if total else 0,
                'avg_duration': round(s['avg_dur'] or 0, 1),
            })
        return cards


# ---------------------------------------------------------------------------
# 2. SessionListView - Paginated, searchable, filterable
# ---------------------------------------------------------------------------

class SessionListView(ListView):
    model = HiveSession
    template_name = 'hive/sessions.html'
    context_object_name = 'sessions'
    paginate_by = 15

    def get_template_names(self):
        if _is_htmx(self.request):
            return ['hive/partials/session_list.html']
        return [self.template_name]

    def get_queryset(self):
        qs = HiveSession.objects.prefetch_related('responses__agent')

        # Search
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(query__icontains=q) |
                Q(session_id__icontains=q) |
                Q(combined_summary__icontains=q) |
                Q(category__icontains=q)
            )

        # Status filter
        status = self.request.GET.get('status', '').strip()
        if status and status in dict(HiveSession.STATUS_CHOICES):
            qs = qs.filter(status=status)

        # Mode filter
        mode = self.request.GET.get('mode', '').strip()
        if mode and mode in dict(HiveSession.MODE_CHOICES):
            qs = qs.filter(mode=mode)

        # Date range filter
        date_from = self.request.GET.get('date_from', '').strip()
        date_to = self.request.GET.get('date_to', '').strip()
        if date_from:
            try:
                qs = qs.filter(created_at__date__gte=datetime.strptime(date_from, '%Y-%m-%d').date())
            except ValueError:
                pass
        if date_to:
            try:
                qs = qs.filter(created_at__date__lte=datetime.strptime(date_to, '%Y-%m-%d').date())
            except ValueError:
                pass

        # Sort
        sort = self.request.GET.get('sort', 'newest')
        if sort == 'oldest':
            qs = qs.order_by('created_at')
        elif sort == 'duration_desc':
            qs = qs.order_by(F('duration_seconds').desc(nulls_last=True))
        elif sort == 'duration_asc':
            qs = qs.order_by(F('duration_seconds').asc(nulls_last=True))
        else:
            qs = qs.order_by('-created_at')

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_page'] = 'sessions'
        ctx['search_query'] = self.request.GET.get('q', '')
        ctx['active_status'] = self.request.GET.get('status', '')
        ctx['active_mode'] = self.request.GET.get('mode', '')
        ctx['active_sort'] = self.request.GET.get('sort', 'newest')
        ctx['date_from'] = self.request.GET.get('date_from', '')
        ctx['date_to'] = self.request.GET.get('date_to', '')

        # Filter counts for sidebar badges
        all_sessions = HiveSession.objects.all()
        ctx['filter_counts'] = {
            'status': {
                st: all_sessions.filter(status=st).count()
                for st, _ in HiveSession.STATUS_CHOICES
                if all_sessions.filter(status=st).exists()
            },
            'mode': {
                md: all_sessions.filter(mode=md).count()
                for md, _ in HiveSession.MODE_CHOICES
                if all_sessions.filter(mode=md).exists()
            },
        }

        # Status and mode choices for the filter dropdowns
        ctx['status_choices'] = HiveSession.STATUS_CHOICES
        ctx['mode_choices'] = HiveSession.MODE_CHOICES

        return ctx


# ---------------------------------------------------------------------------
# 3. SessionDetailView
# ---------------------------------------------------------------------------

class SessionDetailView(DetailView):
    model = HiveSession
    template_name = 'hive/session_detail.html'
    context_object_name = 'session'
    slug_field = 'session_id'
    slug_url_kwarg = 'session_id'

    def get_queryset(self):
        return HiveSession.objects.prefetch_related('responses__agent')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        session = self.object
        responses = session.responses.select_related('agent').order_by(
            'created_at'
        )
        ctx['active_page'] = 'sessions'
        ctx['responses'] = responses
        ctx['agents_routed'] = session.routed_to or []

        # Timeline data for visualization
        ctx['timeline'] = [
            {
                'agent_name': r.agent.display_name,
                'agent_color': r.agent.color,
                'status': r.status,
                'duration': r.duration_seconds,
                'icon_class': r.agent.icon_class,
            }
            for r in responses
        ]

        # War room files (if directory exists)
        war_dir = session.war_room_dir
        ctx['war_room_files'] = []
        if war_dir and Path(war_dir).is_dir():
            ctx['war_room_files'] = sorted(
                [f.name for f in Path(war_dir).iterdir() if f.is_file()]
            )

        return ctx


# ---------------------------------------------------------------------------
# 4. AgentListView
# ---------------------------------------------------------------------------

class AgentListView(ListView):
    model = Agent
    template_name = 'hive/agents.html'
    context_object_name = 'agents'

    def get_template_names(self):
        if _is_htmx(self.request):
            return ['hive/partials/agent_list.html']
        return [self.template_name]

    def get_queryset(self):
        return Agent.objects.all()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        # Batch stats via single query
        stats = AgentResponse.objects.values('agent_id').annotate(
            total=Count('id'),
            successes=Count('id', filter=Q(status='done')),
            failures=Count('id', filter=Q(status='failed')),
            timeouts=Count('id', filter=Q(status='timeout')),
            avg_dur=Avg('duration_seconds', filter=Q(
                status='done', duration_seconds__isnull=False
            )),
        )
        ctx['active_page'] = 'agents'
        ctx['agent_stats'] = {s['agent_id']: s for s in stats}

        # Global averages for comparison bars
        global_agg = AgentResponse.objects.filter(status='done').aggregate(
            global_avg_dur=Avg('duration_seconds'),
        )
        ctx['global_avg_duration'] = round(
            global_agg['global_avg_dur'] or 0, 1
        )

        return ctx


# ---------------------------------------------------------------------------
# 5. AgentDetailView
# ---------------------------------------------------------------------------

class AgentDetailView(DetailView):
    model = Agent
    template_name = 'hive/agent_detail.html'
    context_object_name = 'agent'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        agent = self.object
        responses = agent.responses.select_related('session').order_by(
            '-created_at'
        )

        ctx['active_page'] = 'agents'
        ctx['responses'] = responses[:50]
        ctx['total_responses'] = responses.count()

        # Overall stats
        done = responses.filter(status='done')
        ctx['success_count'] = done.count()
        ctx['failure_count'] = responses.filter(status='failed').count()
        ctx['timeout_count'] = responses.filter(status='timeout').count()
        ctx['success_rate'] = agent.success_rate
        ctx['avg_duration'] = agent.avg_duration

        # Success rate trend: last 14 days, day by day
        now = timezone.now()
        fourteen_days_ago = now - timedelta(days=14)
        daily = (
            responses
            .filter(created_at__gte=fourteen_days_ago)
            .annotate(day=TruncDate('created_at'))
            .values('day')
            .annotate(
                total=Count('id'),
                successes=Count('id', filter=Q(status='done')),
            )
            .order_by('day')
        )
        ctx['trend_labels'] = [
            d['day'].strftime('%b %d') for d in daily
        ]
        ctx['trend_success_rates'] = [
            round(d['successes'] / d['total'] * 100, 1) if d['total'] else 0
            for d in daily
        ]

        # Employees consulted (aggregated from JSONField)
        all_employees = []
        for r in responses.exclude(employees_consulted=[]):
            if r.employees_consulted:
                all_employees.extend(r.employees_consulted)
        emp_counts = defaultdict(int)
        for e in all_employees:
            emp_counts[e] += 1
        ctx['top_employees'] = sorted(
            emp_counts.items(), key=lambda x: x[1], reverse=True
        )[:10]

        return ctx


# ---------------------------------------------------------------------------
# 6. AnalyticsView - Chart data for JS
# ---------------------------------------------------------------------------

class AnalyticsView(TemplateView):
    template_name = 'hive/analytics.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        now = timezone.now()
        fourteen_days_ago = now - timedelta(days=14)

        ctx['active_page'] = 'analytics'

        # ---- Sessions per day (last 14 days) ----
        daily_sessions = (
            HiveSession.objects
            .filter(created_at__gte=fourteen_days_ago)
            .annotate(day=TruncDate('created_at'))
            .values('day')
            .annotate(
                count=Count('id'),
                successes=Count('id', filter=Q(status='done')),
                avg_dur=Avg('duration_seconds'),
            )
            .order_by('day')
        )
        ctx['chart_daily_labels'] = json.dumps([
            d['day'].strftime('%b %d') for d in daily_sessions
        ])
        ctx['chart_daily_counts'] = json.dumps([
            d['count'] for d in daily_sessions
        ])
        ctx['chart_daily_successes'] = json.dumps([
            d['successes'] for d in daily_sessions
        ])
        ctx['chart_daily_avg_dur'] = json.dumps([
            round(d['avg_dur'] or 0, 1) for d in daily_sessions
        ])

        # ---- Agent success rates ----
        agent_stats = (
            AgentResponse.objects
            .values('agent__display_name', 'agent__color')
            .annotate(
                total=Count('id'),
                successes=Count('id', filter=Q(status='done')),
                avg_dur=Avg('duration_seconds', filter=Q(
                    status='done', duration_seconds__isnull=False
                )),
            )
        )
        ctx['chart_agent_labels'] = json.dumps([
            s['agent__display_name'] for s in agent_stats
        ])
        ctx['chart_agent_colors'] = json.dumps([
            s['agent__color'] for s in agent_stats
        ])
        ctx['chart_agent_success_rates'] = json.dumps([
            round(s['successes'] / s['total'] * 100, 1) if s['total'] else 0
            for s in agent_stats
        ])
        ctx['chart_agent_avg_durations'] = json.dumps([
            round(s['avg_dur'] or 0, 1) for s in agent_stats
        ])
        ctx['chart_agent_totals'] = json.dumps([
            s['total'] for s in agent_stats
        ])

        # ---- Mode distribution (pie chart) ----
        mode_dist = (
            HiveSession.objects
            .values('mode')
            .annotate(count=Count('id'))
            .order_by('-count')
        )
        mode_labels = dict(HiveSession.MODE_CHOICES)
        ctx['chart_mode_labels'] = json.dumps([
            mode_labels.get(m['mode'], m['mode']) for m in mode_dist
        ])
        ctx['chart_mode_counts'] = json.dumps([
            m['count'] for m in mode_dist
        ])

        # ---- Category distribution (bar chart) ----
        cat_dist = (
            HiveSession.objects
            .exclude(category='')
            .values('category')
            .annotate(count=Count('id'))
            .order_by('-count')[:12]
        )
        ctx['chart_category_labels'] = json.dumps([
            c['category'] for c in cat_dist
        ])
        ctx['chart_category_counts'] = json.dumps([
            c['count'] for c in cat_dist
        ])

        # ---- Summary stats ----
        total = HiveSession.objects.count()
        successful = HiveSession.objects.filter(status='done').count()
        ctx['analytics_total'] = total
        ctx['analytics_success_rate'] = round(
            successful / total * 100, 1
        ) if total else 0
        ctx['analytics_avg_duration'] = round(
            HiveSession.objects.aggregate(
                v=Avg('duration_seconds')
            )['v'] or 0, 1
        )

        # ---- Busiest hour (0-23) ----
        from django.db.models.functions import ExtractHour
        hourly = (
            HiveSession.objects
            .annotate(hour=ExtractHour('created_at'))
            .values('hour')
            .annotate(count=Count('id'))
            .order_by('hour')
        )
        ctx['chart_hourly_labels'] = json.dumps([
            f"{h['hour']:02d}:00" for h in hourly
        ])
        ctx['chart_hourly_counts'] = json.dumps([
            h['count'] for h in hourly
        ])

        return ctx


# ---------------------------------------------------------------------------
# 7. LaunchQueryView - Dispatch a new hive query
# ---------------------------------------------------------------------------

class LaunchQueryView(View):
    """GET: render query launch form. POST: dispatch hive command."""

    def get(self, request):
        template = _pick_template(
            request,
            'hive/launch.html',
            'hive/partials/launch_form.html',
        )
        from django.shortcuts import render
        return render(request, template, {
            'active_page': 'launch',
        })

    def post(self, request):
        # Handle both JSON body (fetch) and form-encoded (regular POST)
        content_type = request.content_type or ''
        if 'json' in content_type:
            try:
                body = json.loads(request.body)
                query = body.get('query', '').strip()
                mode = body.get('mode', 'full')
            except (json.JSONDecodeError, ValueError):
                query = ''
                mode = 'full'
        else:
            query = request.POST.get('query', '').strip()
            mode = request.POST.get('mode', 'full')
        if not query:
            return JsonResponse({
                'status': 'error',
                'message': 'Query cannot be empty.',
            }, status=400)

        # Generate a trackable session ID
        session_id = uuid.uuid4().hex[:8]

        # Write initial progress file so polling starts immediately
        HIVE_PROGRESS_DIR.mkdir(parents=True, exist_ok=True)
        progress_file = HIVE_PROGRESS_DIR / f"{session_id}.json"
        progress_file.write_text(json.dumps({
            "session_id": session_id,
            "status": "dispatched",
            "phase": "starting",
            "query": query[:200],
            "mode": mode,
            "routed_to": [],
            "agents": {},
        }), encoding="utf-8")

        # Log the query
        log_entry = QueryLog.objects.create(
            query=query,
            source='dashboard',
        )

        # Dispatch hive command as detached subprocess WITH session ID
        hive_script = (
            '/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE'
            '/01_Scripts/ai_workers/hive_cmd.py'
        )
        cmd = [
            'python3', hive_script,
            '--session-id', session_id,
            '--mode', mode,
            query,
        ]

        try:
            env = os.environ.copy()
            # Remove Claude Code nesting vars if present
            env.pop('CLAUDECODE', None)
            env.pop('CLAUDE_CODE', None)

            subprocess.Popen(
                cmd,
                env=env,
                cwd='/mnt/sdcard/AA_MY_DRIVE',
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            dispatched = True
            message = 'Query dispatched to the Hive Mind.'
        except Exception as e:
            logger.error("Failed to dispatch hive command: %s", e)
            dispatched = False
            message = f'Dispatch failed: {e}'

            # Update progress file with failure
            progress_file.write_text(json.dumps({
                "session_id": session_id,
                "status": "failed",
                "phase": "dispatch_error",
                "error": str(e),
            }), encoding="utf-8")

            SystemEvent.objects.create(
                level='error',
                title='Hive dispatch failed',
                detail=f'Query: {query}\nError: {e}',
            )

        return JsonResponse({
            'status': 'ok' if dispatched else 'error',
            'message': message,
            'session_id': session_id,
            'query_log_id': log_entry.id,
        })


# ---------------------------------------------------------------------------
# 8. api_session_status - AJAX polling endpoint
# ---------------------------------------------------------------------------

def api_session_status(request, session_id):
    """Return session status + responses as JSON for polling."""
    session = get_object_or_404(HiveSession, session_id=session_id)
    responses = session.responses.select_related('agent').order_by(
        'created_at'
    )

    return JsonResponse({
        'session_id': session.session_id,
        'status': session.status,
        'query': session.query,
        'mode': session.mode,
        'duration_seconds': session.duration_seconds,
        'duration_display': session.duration_display,
        'created_at': session.created_at.isoformat(),
        'category': session.category,
        'combined_summary': session.combined_summary,
        'intel_summary': session.intel_summary,
        'success_pct': session.success_pct,
        'agents_total': session.agents_total,
        'agents_succeeded': session.agents_succeeded,
        'agents_failed': session.agents_failed,
        'responses': [
            {
                'agent_name': r.agent.display_name,
                'agent_color': r.agent.color,
                'agent_icon': r.agent.icon_class,
                'status': r.status,
                'duration_seconds': r.duration_seconds,
                'duration_display': r.duration_display,
                'response_preview': r.response_preview,
                'error_message': r.error_message,
                'employees_consulted': r.employees_consulted or [],
            }
            for r in responses
        ],
    })


# ---------------------------------------------------------------------------
# 9. api_live_feed - Read hive_sessions.jsonl directly
# ---------------------------------------------------------------------------

def api_live_feed(request):
    """
    Return the latest 20 entries from hive_sessions.jsonl as JSON.
    Reads the file directly for real-time feed without DB dependency.
    """
    jsonl_path = getattr(
        settings, 'HIVE_SESSIONS_JSONL',
        '/mnt/sdcard/AA_MY_DRIVE/_logs/hive_sessions.jsonl'
    )
    entries = []

    try:
        path = Path(jsonl_path)
        if path.exists():
            # Read last 20 lines efficiently
            lines = path.read_text(encoding='utf-8').strip().splitlines()
            tail = lines[-20:] if len(lines) > 20 else lines
            for line in reversed(tail):
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    entries.append(entry)
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        logger.error("Error reading live feed from %s: %s", jsonl_path, e)
        return JsonResponse({
            'status': 'error',
            'message': str(e),
            'entries': [],
        }, status=500)

    return JsonResponse({
        'status': 'ok',
        'count': len(entries),
        'entries': entries,
    })


# ---------------------------------------------------------------------------
# 10. EventsView - System events paginated
# ---------------------------------------------------------------------------

class EventsView(ListView):
    model = SystemEvent
    template_name = 'hive/events.html'
    context_object_name = 'events'
    paginate_by = 25

    def get_template_names(self):
        if _is_htmx(self.request):
            return ['hive/partials/event_list.html']
        return [self.template_name]

    def get_queryset(self):
        qs = SystemEvent.objects.all()

        # Level filter
        level = self.request.GET.get('level', '').strip()
        if level and level in dict(SystemEvent.LEVEL_CHOICES):
            qs = qs.filter(level=level)

        # Search
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(title__icontains=q) | Q(detail__icontains=q)
            )

        return qs.order_by('-created_at')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_page'] = 'events'
        ctx['search_query'] = self.request.GET.get('q', '')
        ctx['active_level'] = self.request.GET.get('level', '')
        ctx['level_choices'] = SystemEvent.LEVEL_CHOICES

        # Level counts for badges
        ctx['level_counts'] = {
            e['level']: e['count']
            for e in SystemEvent.objects.values('level').annotate(
                count=Count('id')
            )
        }

        return ctx


# ---------------------------------------------------------------------------
# 11. api_poll_session - Real-time progress polling for active sessions
# ---------------------------------------------------------------------------

def api_poll_session(request, session_id):
    """
    Poll a hive session's progress by reading the filesystem progress file.
    Returns real-time status updates including per-agent results.
    """
    # Sanitize session_id (hex chars only, max 8)
    clean_id = ''.join(c for c in session_id if c in '0123456789abcdef')[:8]
    if not clean_id:
        return JsonResponse(
            {'status': 'error', 'message': 'Invalid session ID'}, status=400
        )

    progress_file = HIVE_PROGRESS_DIR / f"{clean_id}.json"

    if not progress_file.exists():
        return JsonResponse({
            'status': 'not_found',
            'message': 'Session not found. It may still be starting.',
            'session_id': clean_id,
        })

    try:
        data = json.loads(progress_file.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, OSError) as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Error reading progress: {e}',
        }, status=500)

    return JsonResponse(data)


# ---------------------------------------------------------------------------
# 12. api_export_session - Download session as markdown
# ---------------------------------------------------------------------------

def api_bot_intel(request):
    """
    Return XLM bot intelligence status: state, AI insight, daily brief,
    contract context. Reads directly from bot data files.
    """
    result = {}

    # Bot state
    state_file = XLM_BOT_DIR / 'data' / 'state.json'
    if state_file.exists():
        try:
            state = json.loads(state_file.read_text(encoding='utf-8'))
            result['state'] = {
                'day': state.get('day'),
                'trades_today': state.get('trades', 0),
                'losses_today': state.get('losses', 0),
                'pnl_today_usd': state.get('pnl_today_usd', 0),
                'equity_start_usd': state.get('equity_start_usd', 0),
                'exchange_pnl_today_usd': state.get('exchange_pnl_today_usd', 0),
                'vol_state': state.get('vol_state', 'UNKNOWN'),
                'recovery_mode': state.get('recovery_mode', 'NORMAL'),
                'safe_mode': state.get('_safe_mode', False),
                'safe_mode_reason': state.get('safe_mode_reason'),
                'overnight_ok': state.get('_overnight_trading_ok', 'no'),
                'consecutive_losses': state.get('consecutive_losses', 0),
                'consecutive_wins': state.get('consecutive_wins', 0),
                'loss_debt_usd': state.get('loss_debt_usd', 0),
                'open_position': state.get('open_position'),
                'last_cycle_ts': state.get('last_cycle_ts'),
                'spot_usdc': (state.get('last_spot_cash_map') or {}).get('USDC', 0),
            }
        except (json.JSONDecodeError, OSError):
            result['state'] = None
    else:
        result['state'] = None

    # AI Insight (Claude/Codex directives)
    insight_file = XLM_BOT_DIR / 'data' / 'ai_insight.json'
    if insight_file.exists():
        try:
            insight = json.loads(insight_file.read_text(encoding='utf-8'))
            # Extract key directive info
            directive = insight.get('directive', {}).get('result', {})
            codex_dir = insight.get('codex_directive', {}).get('result', {})
            regime = insight.get('regime_eval', {}).get('result', {})
            result['ai'] = {
                'claude_action': directive.get('action', 'N/A'),
                'claude_confidence': directive.get('confidence', 0),
                'claude_reasoning': directive.get('reasoning', ''),
                'claude_market_read': directive.get('market_read', ''),
                'codex_action': codex_dir.get('action', 'N/A'),
                'codex_confidence': codex_dir.get('confidence', 0),
                'codex_reasoning': codex_dir.get('reasoning', ''),
                'regime_confidence': regime.get('regime_confidence', 0),
                'trading_bias': regime.get('trading_bias', 'N/A'),
                'regime_reasoning': regime.get('reasoning', ''),
            }
        except (json.JSONDecodeError, OSError):
            result['ai'] = None
    else:
        result['ai'] = None

    # Daily brief
    brief_file = XLM_BOT_DIR / 'data' / 'daily_brief.json'
    if brief_file.exists():
        try:
            brief = json.loads(brief_file.read_text(encoding='utf-8'))
            result['daily_brief'] = {
                'last_3_days': brief.get('last_3_days', []),
                'total_3day_pnl': brief.get('total_3day_pnl_usd', 0),
                'equity_trend': brief.get('equity_trend', 'unknown'),
                'suggested_posture': brief.get('suggested_posture', 'unknown'),
            }
        except (json.JSONDecodeError, OSError):
            result['daily_brief'] = None
    else:
        result['daily_brief'] = None

    # Contract context
    ctx_file = XLM_BOT_DIR / 'data' / 'contract_context.json'
    if ctx_file.exists():
        try:
            ctx = json.loads(ctx_file.read_text(encoding='utf-8'))
            result['contract'] = {
                'mark_price': ctx.get('mark_price'),
                'index_price': ctx.get('index_price'),
                'basis_bps': ctx.get('basis_bps'),
                'open_interest': ctx.get('open_interest'),
                'funding_rate_hr': ctx.get('funding_rate_hr'),
                'funding_bias': ctx.get('funding_bias'),
                'volume_24h': ctx.get('volume_24h'),
            }
        except (json.JSONDecodeError, OSError):
            result['contract'] = None
    else:
        result['contract'] = None

    # Heartbeat check
    heartbeat_file = XLM_BOT_DIR / 'data' / '.heartbeat'
    if heartbeat_file.exists():
        try:
            import time
            age_seconds = time.time() - heartbeat_file.stat().st_mtime
            result['heartbeat_age_s'] = round(age_seconds, 1)
            result['bot_alive'] = age_seconds < 120  # alive if <2 min old
        except OSError:
            result['heartbeat_age_s'] = None
            result['bot_alive'] = False
    else:
        result['heartbeat_age_s'] = None
        result['bot_alive'] = False

    return JsonResponse({'status': 'ok', **result})


@csrf_exempt
def api_upload_analyze(request):
    """
    Accept file/image upload(s) and dispatch to the Hive Mind for analysis.
    Supports images (jpg, png, webp, gif), text, markdown, JSON, CSV, PDF.
    POST params: file (multipart), file_1..file_N (additional), query (text), mode (full|lite)
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST only'}, status=405)

    query_text = request.POST.get('query', '').strip() or 'Analyze this file and provide key insights.'
    mode = request.POST.get('mode', 'full')

    # Collect all uploaded files (file, file_1, file_2, ...)
    all_files = []
    primary = request.FILES.get('file')
    if primary:
        all_files.append(primary)
    for key in sorted(request.FILES.keys()):
        if key.startswith('file_') and request.FILES[key]:
            all_files.append(request.FILES[key])

    if not all_files:
        return JsonResponse({'status': 'error', 'message': 'No file provided'}, status=400)

    # Validate sizes
    total_size = sum(f.size for f in all_files)
    if total_size > 50 * 1024 * 1024:
        return JsonResponse({'status': 'error', 'message': 'Total upload too large (max 50MB)'}, status=400)
    for f in all_files:
        if f.size > 20 * 1024 * 1024:
            return JsonResponse({
                'status': 'error',
                'message': f'File too large: {f.name} (max 20MB per file)'
            }, status=400)

    import time as _time
    import base64 as _b64
    uploads_dir = HIVE_WORKSPACE / '_uploads'
    uploads_dir.mkdir(parents=True, exist_ok=True)

    ts = int(_time.time())
    file_names = []
    query_parts = [query_text, ""]

    for idx, uploaded_file in enumerate(all_files):
        raw_name = uploaded_file.name or f'upload_{idx}'
        safe_name = f"{ts}_{idx}_{''.join(c for c in raw_name if c.isalnum() or c in '._- ')[:80]}"
        dest = uploads_dir / safe_name

        with open(dest, 'wb') as fout:
            for chunk in uploaded_file.chunks():
                fout.write(chunk)

        file_type = (uploaded_file.content_type or '').lower()
        name_lower = raw_name.lower()
        file_names.append(raw_name)

        is_image = (
            file_type.startswith('image/')
            or name_lower.endswith(('.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp', '.tiff'))
        )
        is_text = (
            file_type in ('text/plain', 'text/markdown', 'text/csv', 'application/json')
            or name_lower.endswith(('.txt', '.md', '.log', '.json', '.csv', '.yaml', '.yml', '.py', '.js', '.sh'))
        )

        if is_image:
            # Auto-compress large images to prevent argv overflow
            try:
                _scripts = '/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts'
                if _scripts not in sys.path:
                    sys.path.insert(0, _scripts)
                from compress_upload import compress as _compress_img
                compressed = _compress_img(Path(str(dest)))
                if compressed != Path(str(dest)):
                    dest = uploads_dir / compressed.name
            except Exception as _ce:
                logger.warning("Image compress failed for %s: %s", raw_name, _ce)
            # Reference by file path (NOT base64) to avoid Errno 7
            query_parts.append(
                f"[ATTACHED IMAGE {idx+1}: {raw_name}]\n"
                f"Image file path (absolute): {dest}\n"
                f"Content type: {file_type or 'image/jpeg'}"
            )
        elif is_text:
            with open(dest, 'r', errors='replace') as fin:
                content = fin.read(8000)
            truncated = len(content) >= 8000
            query_parts.append(
                f"[ATTACHED FILE {idx+1}: {raw_name}]"
                + ("\n[NOTE: content truncated to 8KB]" if truncated else "")
                + f"\n```\n{content}\n```"
            )
        else:
            query_parts.append(
                f"[ATTACHED FILE {idx+1}: {raw_name} ({file_type or 'unknown type'}) saved to {dest}]"
            )

    full_query = "\n\n".join(query_parts)
    names_str = ", ".join(file_names)

    session_id = uuid.uuid4().hex[:8]
    HIVE_PROGRESS_DIR.mkdir(parents=True, exist_ok=True)
    progress_file = HIVE_PROGRESS_DIR / f"{session_id}.json"
    progress_file.write_text(json.dumps({
        "session_id": session_id,
        "status": "dispatched",
        "phase": "starting",
        "query": f"[{len(all_files)} FILE(S): {names_str}] {query_text}"[:200],
        "mode": mode,
        "routed_to": [],
        "agents": {},
        "attachments": file_names,
    }), encoding="utf-8")

    QueryLog.objects.create(
        query=f"[UPLOAD: {names_str}] {query_text}"[:500],
        source='dashboard',
    )

    hive_script = (
        '/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE'
        '/01_Scripts/ai_workers/hive_cmd.py'
    )
    # Write query to temp file to avoid OS argv size limit (Errno 7)
    import tempfile as _tempfile
    query_file = Path(_tempfile.mktemp(
        suffix='.txt', prefix='.hive_query_',
        dir=str(uploads_dir),
    ))
    query_file.write_text(full_query, encoding='utf-8')
    cmd = [
        'python3', hive_script,
        '--session-id', session_id,
        '--mode', mode,
        '--query-file', str(query_file),
    ]

    try:
        env = os.environ.copy()
        env.pop('CLAUDECODE', None)
        env.pop('CLAUDE_CODE', None)
        subprocess.Popen(
            cmd, env=env, cwd='/mnt/sdcard/AA_MY_DRIVE',
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return JsonResponse({
            'status': 'ok',
            'session_id': session_id,
            'filenames': file_names,
            'file_count': len(all_files),
        })
    except Exception as e:
        logger.error("Upload analyze dispatch failed: %s", e)
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


def api_export_session(request, session_id):
    """Return a session as a downloadable markdown file."""
    session = get_object_or_404(HiveSession, session_id=session_id)
    responses = session.responses.select_related('agent').order_by('created_at')

    lines = [
        '# Hive Mind Session Export',
        '',
        f'**Session ID:** `{session.session_id}`',
        f'**Query:** {session.query}',
        f'**Mode:** {session.mode}',
        f'**Status:** {session.status}',
        f'**Duration:** {session.duration_display}',
        f'**Date:** {session.created_at.strftime("%Y-%m-%d %H:%M UTC")}',
        '',
        '---',
        '',
    ]

    if session.intel_summary:
        lines += ['## Intel Summary', '', session.intel_summary, '', '---', '']

    lines += ['## Agent Responses', '']

    for resp in responses:
        lines += [
            f'### {resp.agent.display_name}',
            f'**Status:** {resp.status} | **Duration:** {resp.duration_display}',
            '',
        ]
        if resp.employees_consulted:
            lines.append(f'*Team: {", ".join(resp.employees_consulted)}*')
            lines.append('')
        if resp.error_message:
            lines += [f'> **Error:** {resp.error_message}', '']
        if resp.response_text:
            lines += [resp.response_text, '']
        lines += ['---', '']

    if session.combined_summary:
        lines += ['## Combined Summary', '', session.combined_summary, '']

    content = '\n'.join(lines)
    filename = f'hive_session_{session.session_id}.md'
    resp_http = HttpResponse(content, content_type='text/markdown; charset=utf-8')
    resp_http['Content-Disposition'] = f'attachment; filename="{filename}"'
    return resp_http
