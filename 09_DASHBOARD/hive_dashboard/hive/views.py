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
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Avg, Count, F, Max, Q, Sum
from django.db.models.functions import TruncDate
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView, ListView, TemplateView

from .models import Agent, AgentResponse, HiveArtifact, HiveSession, QueryLog, SystemEvent

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

def hive_login(request):
    next_url = request.GET.get('next') or request.POST.get('next') or '/'
    if request.user.is_authenticated:
        return redirect(next_url)
    error = ''
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect(next_url)
        error = 'Invalid credentials'
    return render(request, 'hive/login.html', {'next': next_url, 'error': error})


def hive_logout(request):
    logout(request)
    return redirect(settings.LOGIN_URL)

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

class DashboardView(LoginRequiredMixin, TemplateView):
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

class SessionListView(LoginRequiredMixin, ListView):
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

class SessionDetailView(LoginRequiredMixin, DetailView):
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

class AgentListView(LoginRequiredMixin, ListView):
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

class AgentDetailView(LoginRequiredMixin, DetailView):
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

class AnalyticsView(LoginRequiredMixin, TemplateView):
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

class LaunchQueryView(LoginRequiredMixin, View):
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

@login_required
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

@login_required
def api_live_feed(request):
    """
    Return the latest live sessions using the database as the source of truth,
    supplemented by active progress files for in-flight runs.
    """
    entries = []
    seen_session_ids = set()

    try:
        recent_sessions = HiveSession.objects.order_by("-created_at")[:15]
        for session in recent_sessions:
            entries.append({
                "session_id": session.session_id,
                "prompt": session.query,
                "status": session.status,
                "mode": session.mode,
                "category": session.category,
                "total_duration_s": session.duration_seconds or 0,
                "created_at": session.created_at.isoformat(),
            })
            seen_session_ids.add(session.session_id)

        if HIVE_PROGRESS_DIR.exists():
            progress_files = sorted(
                HIVE_PROGRESS_DIR.glob("*.json"),
                key=lambda path: path.stat().st_mtime,
                reverse=True,
            )
            for progress_file in progress_files[:15]:
                data = json.loads(progress_file.read_text(encoding="utf-8"))
                sid = str(data.get("session_id") or "").strip()
                if not sid or sid in seen_session_ids:
                    continue
                entries.append({
                    "session_id": sid,
                    "prompt": data.get("query", ""),
                    "status": data.get("status", "running"),
                    "mode": data.get("mode", "full"),
                    "category": data.get("category", ""),
                    "total_duration_s": data.get("total_duration_s", 0),
                    "created_at": data.get("started_at", ""),
                })
    except Exception as e:
        logger.error("Error building live feed: %s", e)
        return JsonResponse({
            'status': 'error',
            'message': str(e),
            'entries': [],
        }, status=500)

    entries.sort(key=lambda item: item.get("created_at", ""), reverse=True)

    return JsonResponse({
        'status': 'ok',
        'count': len(entries[:20]),
        'entries': entries[:20],
    })


# ---------------------------------------------------------------------------
# 10. EventsView - System events paginated
# ---------------------------------------------------------------------------

class EventsView(LoginRequiredMixin, ListView):
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

@login_required
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

@login_required
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


@login_required
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


def api_hub_status(request):
    """Health check endpoint for action engine. No auth required."""
    return JsonResponse({"status": "ok", "service": "hive-django"})


@login_required
def api_agent_status(request):
    """
    Return JSON with agent status, active sessions, and recent activity.
    Reads from _logs/ai_war_room/ and _logs/hive_sessions.jsonl, plus the DB.
    Also pushes loaded sessions to Supabase hive_sessions table.
    """
    war_room_dir = HIVE_WORKSPACE / '_logs' / 'ai_war_room'
    sessions_jsonl = HIVE_WORKSPACE / '_logs' / 'hive_sessions.jsonl'

    # Agent definitions with their colors
    agent_defs = {
        'claude': {'color': '#8b5cf6', 'icon': 'fa-brain'},
        'gemini': {'color': '#22d3ee', 'icon': 'fa-gem'},
        'codex': {'color': '#22c55e', 'icon': 'fa-code'},
        'perplexity': {'color': '#f59e0b', 'icon': 'fa-search'},
    }

    agents_status = {}
    for name, meta in agent_defs.items():
        agents_status[name] = {
            'name': name,
            'display_name': name.capitalize(),
            'color': meta['color'],
            'icon': meta['icon'],
            'status': 'idle',
            'last_active': None,
            'current_task': None,
        }

    # Read recent war room sessions (last 20 by mtime)
    active_sessions = []
    if war_room_dir.is_dir():
        session_dirs = sorted(
            [d for d in war_room_dir.iterdir() if d.is_dir() and d.name.startswith('hive_')],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )[:20]

        for sdir in session_dirs:
            session_file = sdir / 'session.json'
            if not session_file.exists():
                continue
            try:
                data = json.loads(session_file.read_text(encoding='utf-8'))
            except (json.JSONDecodeError, OSError):
                continue

            files_in_dir = [f.name for f in sdir.iterdir() if f.is_file()]
            session_entry = {
                'session_id': data.get('id', ''),
                'prompt': (data.get('prompt', '') or '')[:120],
                'status': data.get('status', 'unknown'),
                'mode': data.get('mode', 'full'),
                'routed_to': data.get('routed_to', []),
                'total_duration_s': data.get('total_duration_s', 0),
                'created_at': data.get('created', data.get('timestamp', '')),
                'war_room_dir': str(sdir),
                'files': files_in_dir,
                'managers': [],
            }

            for mgr in data.get('managers', []):
                mgr_name = mgr.get('manager', '')
                mgr_entry = {
                    'agent': mgr_name,
                    'status': mgr.get('status', 'unknown'),
                    'duration_s': mgr.get('duration_s', 0),
                    'employees_consulted': mgr.get('employees_consulted', []),
                    'started_at': mgr.get('started_at', ''),
                    'finished_at': mgr.get('finished_at', ''),
                }
                session_entry['managers'].append(mgr_entry)

                # Update agent last-active
                if mgr_name in agents_status:
                    finished = mgr.get('finished_at') or mgr.get('started_at', '')
                    current_last = agents_status[mgr_name]['last_active']
                    if finished and (not current_last or finished > current_last):
                        agents_status[mgr_name]['last_active'] = finished
                    if mgr.get('status') == 'running':
                        agents_status[mgr_name]['status'] = 'active'
                        agents_status[mgr_name]['current_task'] = (
                            data.get('prompt', '')[:80]
                        )

            active_sessions.append(session_entry)

    # Also check progress dir for in-flight sessions
    if HIVE_PROGRESS_DIR.exists():
        for pf in sorted(
            HIVE_PROGRESS_DIR.glob('*.json'),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )[:5]:
            try:
                pdata = json.loads(pf.read_text(encoding='utf-8'))
            except (json.JSONDecodeError, OSError):
                continue
            if pdata.get('status') in ('dispatched', 'running'):
                for ag_name in pdata.get('routed_to', []):
                    if ag_name in agents_status:
                        ag_info = pdata.get('agents', {}).get(ag_name, {})
                        if ag_info.get('status') == 'running':
                            agents_status[ag_name]['status'] = 'active'
                            agents_status[ag_name]['current_task'] = (
                                pdata.get('query', '')[:80]
                            )

    # Mark agents with recent activity as 'ready' if not actively running
    for name, info in agents_status.items():
        if info['status'] == 'idle' and info['last_active']:
            info['status'] = 'ready'

    # Read recent entries from hive_sessions.jsonl for supplementary data
    jsonl_entries = []
    if sessions_jsonl.exists():
        try:
            lines = sessions_jsonl.read_text(encoding='utf-8').strip().split('\n')
            for line in lines[-20:]:
                line = line.strip()
                if not line:
                    continue
                try:
                    jsonl_entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        except OSError:
            pass

    # Push to Supabase (best-effort, non-blocking)
    _sync_sessions_to_supabase(active_sessions)

    return JsonResponse({
        'status': 'ok',
        'agents': agents_status,
        'active_sessions': active_sessions[:15],
        'recent_jsonl': jsonl_entries[-10:],
        'total_war_room_sessions': len(active_sessions),
    })


def _sync_sessions_to_supabase(sessions):
    """
    Push session data to Supabase hive_sessions table.
    Best-effort -- errors are logged but do not break the response.
    """
    try:
        from hive_dashboard.supabase_client import supabase_rest, is_configured
        if not is_configured():
            return
        for sess in sessions[:5]:  # Only sync the 5 most recent
            row = {
                'session_id': sess.get('session_id', ''),
                'prompt': (sess.get('prompt', '') or '')[:200],
                'status': sess.get('status', 'unknown'),
                'mode': sess.get('mode', 'full'),
                'routed_to': sess.get('routed_to', []),
                'total_duration_s': sess.get('total_duration_s', 0),
                'created_at': sess.get('created_at', ''),
            }
            try:
                supabase_rest(
                    'hive_sessions',
                    method='POST',
                    data=row,
                    extra_headers={'Prefer': 'resolution=merge-duplicates'},
                    timeout=3.0,
                )
            except Exception as e:
                logger.debug("Supabase sync failed for session %s: %s", row.get('session_id'), e)
    except ImportError:
        logger.debug("supabase_client not available, skipping sync")
    except Exception as e:
        logger.debug("Supabase sync batch error: %s", e)


# ---------------------------------------------------------------------------
# 14. ProcessesView -- Detailed process viewer
# ---------------------------------------------------------------------------

class ProcessesView(LoginRequiredMixin, TemplateView):
    """Detailed view of all running/recent hive processes."""
    template_name = 'hive/processes.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_page'] = 'processes'

        war_room_dir = HIVE_WORKSPACE / '_logs' / 'ai_war_room'
        sessions = []

        # Filters from query params
        agent_filter = self.request.GET.get('agent', '').strip().lower()
        status_filter = self.request.GET.get('status', '').strip().lower()
        date_from = self.request.GET.get('date_from', '').strip()
        date_to = self.request.GET.get('date_to', '').strip()

        if war_room_dir.is_dir():
            session_dirs = sorted(
                [d for d in war_room_dir.iterdir()
                 if d.is_dir() and d.name.startswith('hive_')],
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )[:50]

            for sdir in session_dirs:
                session_file = sdir / 'session.json'
                if not session_file.exists():
                    continue
                try:
                    data = json.loads(session_file.read_text(encoding='utf-8'))
                except (json.JSONDecodeError, OSError):
                    continue

                created = data.get('created', data.get('timestamp', ''))

                # Date filtering
                if date_from and created:
                    if created[:10] < date_from:
                        continue
                if date_to and created:
                    if created[:10] > date_to:
                        continue

                # Status filtering
                if status_filter and data.get('status', '') != status_filter:
                    continue

                files_in_dir = sorted([f.name for f in sdir.iterdir() if f.is_file()])
                managers = data.get('managers', [])

                # Agent filtering
                if agent_filter:
                    routed = data.get('routed_to', [])
                    if agent_filter not in routed:
                        continue

                # Calculate total tokens (estimate from duration)
                total_duration = data.get('total_duration_s', 0)

                entry = {
                    'session_id': data.get('id', ''),
                    'prompt': data.get('prompt', ''),
                    'status': data.get('status', 'unknown'),
                    'mode': data.get('mode', 'full'),
                    'routed_to': data.get('routed_to', []),
                    'total_duration_s': total_duration,
                    'created_at': created,
                    'war_room_dir': str(sdir),
                    'dir_name': sdir.name,
                    'files': files_in_dir,
                    'managers': [],
                }

                for mgr in managers:
                    entry['managers'].append({
                        'agent': mgr.get('manager', ''),
                        'role': mgr.get('role', ''),
                        'status': mgr.get('status', 'unknown'),
                        'duration_s': mgr.get('duration_s', 0),
                        'employees_consulted': mgr.get('employees_consulted', []),
                        'error': mgr.get('error', ''),
                    })

                sessions.append(entry)

        ctx['sessions'] = sessions
        ctx['agent_filter'] = agent_filter
        ctx['status_filter'] = status_filter
        ctx['date_from'] = date_from
        ctx['date_to'] = date_to
        ctx['agent_choices'] = ['claude', 'gemini', 'codex', 'perplexity']
        ctx['status_choices'] = ['done', 'running', 'partial', 'failed', 'timeout']
        return ctx


# ---------------------------------------------------------------------------
# 15. api_export_session
# ---------------------------------------------------------------------------

@login_required
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


# ---------------------------------------------------------------------------
# Premium Reports - Unified Dashboard (merged from :8080)
# ---------------------------------------------------------------------------

class ReportsListView(LoginRequiredMixin, TemplateView):
    template_name = 'hive/reports_list.html'

    def get_context_data(self, **kwargs):
        import re as _re
        ctx = super().get_context_data(**kwargs)
        ctx['active_page'] = 'reports'
        # Check both report directories (hive_reports is primary, reports is legacy)
        report_dirs = [
            Path(getattr(settings, 'REPORTS_DIR', '/home/opc/hive_reports')),
            Path('/home/opc/reports'),
        ]
        seen = set()
        reports = []
        for reports_dir in report_dirs:
            if not reports_dir.is_dir():
                continue
            for f in reports_dir.iterdir():
                if f.suffix == '.html' and f.is_file() and f.name not in seen:
                    seen.add(f.name)
                    stat = f.stat()
                    # Extract title from HTML <title> tag
                    title = f.stem.replace('_', ' ').title()
                    try:
                        head = f.read_text(encoding='utf-8')[:2000]
                        m = _re.search(r'<title>([^<]+)', head)
                        if m:
                            raw_title = m.group(1).replace(' | Everlight Ventures', '').strip()
                            if raw_title:
                                title = raw_title
                    except Exception:
                        pass
                    # Determine category from filename or content
                    category = 'general'
                    fname_lower = f.name.lower()
                    if 'pipeline' in fname_lower or 'wholesale' in fname_lower:
                        category = 'pipeline'
                    elif 'deal' in fname_lower or 'contract' in fname_lower:
                        category = 'deals'
                    elif 'outreach' in fname_lower or 'email' in fname_lower:
                        category = 'outreach'
                    elif 'lucrex' in fname_lower or 'operations' in fname_lower:
                        category = 'operations'
                    elif 'intel' in fname_lower or 'bot' in fname_lower:
                        category = 'trading'
                    elif 'landing' in fname_lower:
                        category = 'landing'
                    reports.append({
                        'hash': f.stem,
                        'filename': f.name,
                        'title': title,
                        'category': category,
                        'size_kb': round(stat.st_size / 1024, 1),
                        'modified': datetime.fromtimestamp(
                            stat.st_mtime, tz=timezone.get_current_timezone()
                        ),
                        'dir': str(reports_dir),
                    })
        reports.sort(key=lambda r: r['modified'], reverse=True)
        ctx['reports'] = reports[:100]
        ctx['total_reports'] = len(reports)
        # Category counts for filter tabs
        cats = {}
        for r in reports:
            cats[r['category']] = cats.get(r['category'], 0) + 1
        ctx['categories'] = cats
        return ctx


def report_detail(request, report_hash):
    """Serve a premium HTML report -- raw or wrapped in base layout.

    Public (no login required) so branded Slack links work for any team
    member who taps them, including from a phone Slack client that may
    not have a Django session. Path traversal is blocked by the
    safe_hash regex below.
    """
    import re as _re
    safe_hash = _re.sub(r'[^a-zA-Z0-9_.-]', '', report_hash)
    report_file = None
    for d in [Path('/home/opc/hive_reports'), Path(getattr(settings, 'REPORTS_DIR', '/home/opc/reports'))]:
        candidate = d / f'{safe_hash}.html'
        if candidate.is_file():
            report_file = candidate
            break

    if not report_file or not report_file.is_file():
        return HttpResponse('Report not found', status=404)

    # Raw mode: serve the HTML directly (for iframe embedding)
    if request.GET.get('raw') == '1':
        return HttpResponse(
            report_file.read_text(encoding='utf-8'),
            content_type='text/html; charset=utf-8',
        )

    # Wrapped mode: render in base.html layout with iframe
    return render(request, 'hive/report_detail.html', {
        'active_page': 'reports',
        'report_hash': safe_hash,
        'report_file': report_file.name,
    })


# ---------------------------------------------------------------------------
# Blinko RAG Search - Knowledge Base
# ---------------------------------------------------------------------------

class BlinkoSearchView(LoginRequiredMixin, TemplateView):
    template_name = 'hive/blinko_search.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_page'] = 'blinko'
        ctx['query'] = ''
        ctx['results'] = []
        ctx['searched'] = False
        return ctx

    def post(self, request, *args, **kwargs):
        import urllib.request
        import urllib.parse

        query = request.POST.get('q', '').strip()
        results = []
        error = None

        if query:
            blinko_url = getattr(settings, 'BLINKO_API_URL', 'http://129.159.38.250:1111')
            api_url = f'{blinko_url}/api/v1/note/list'
            payload = json.dumps({
                'searchText': query,
                'page': 1,
                'size': 20,
            }).encode('utf-8')
            req = urllib.request.Request(
                api_url,
                data=payload,
                headers={'Content-Type': 'application/json'},
                method='POST',
            )
            try:
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode('utf-8'))
                    notes = data if isinstance(data, list) else data.get('items', data.get('notes', []))
                    for note in notes[:20]:
                        content = note.get('content', '')
                        results.append({
                            'id': note.get('id'),
                            'content': content[:500] + ('...' if len(content) > 500 else ''),
                            'tags': [t.get('name', t) if isinstance(t, dict) else t
                                     for t in note.get('tags', [])],
                            'created_at': note.get('createdAt', note.get('created_at', '')),
                            'type': note.get('type', 0),
                        })
            except Exception as e:
                error = f'Blinko unreachable: {e}'

        return render(request, self.template_name, {
            'active_page': 'blinko',
            'query': query,
            'results': results,
            'searched': True,
            'error': error,
        })


# ---------------------------------------------------------------------------
# Bot Intel - Full Page View (merged from :8080)
# ---------------------------------------------------------------------------

class BotIntelPageView(LoginRequiredMixin, TemplateView):
    template_name = 'hive/bot_intel.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_page'] = 'bot_intel'

        # Reuse the same data extraction logic from api_bot_intel
        state_file = XLM_BOT_DIR / 'data' / 'state.json'
        if state_file.exists():
            try:
                state = json.loads(state_file.read_text(encoding='utf-8'))
                ctx['bot_state'] = {
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
                    'spot_usdc': (state.get('last_spot_cash_map') or {}).get('USDC', 0),
                }
            except (json.JSONDecodeError, OSError):
                ctx['bot_state'] = None
        else:
            ctx['bot_state'] = None

        # AI Insight
        insight_file = XLM_BOT_DIR / 'data' / 'ai_insight.json'
        if insight_file.exists():
            try:
                insight = json.loads(insight_file.read_text(encoding='utf-8'))
                directive = insight.get('directive', {}).get('result', {})
                codex_dir = insight.get('codex_directive', {}).get('result', {})
                regime = insight.get('regime_eval', {}).get('result', {})
                ctx['ai_insight'] = {
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
                ctx['ai_insight'] = None
        else:
            ctx['ai_insight'] = None

        # Daily brief
        brief_file = XLM_BOT_DIR / 'data' / 'daily_brief.json'
        if brief_file.exists():
            try:
                brief = json.loads(brief_file.read_text(encoding='utf-8'))
                ctx['daily_brief'] = {
                    'last_3_days': brief.get('last_3_days', []),
                    'total_3day_pnl': brief.get('total_3day_pnl_usd', 0),
                    'equity_trend': brief.get('equity_trend', 'unknown'),
                    'suggested_posture': brief.get('suggested_posture', 'unknown'),
                }
            except (json.JSONDecodeError, OSError):
                ctx['daily_brief'] = None
        else:
            ctx['daily_brief'] = None

        # Contract context
        ctx_file = XLM_BOT_DIR / 'data' / 'contract_context.json'
        if ctx_file.exists():
            try:
                cdata = json.loads(ctx_file.read_text(encoding='utf-8'))
                ctx['contract'] = {
                    'mark_price': cdata.get('mark_price'),
                    'index_price': cdata.get('index_price'),
                    'basis_bps': cdata.get('basis_bps'),
                    'open_interest': cdata.get('open_interest'),
                    'funding_rate_hr': cdata.get('funding_rate_hr'),
                    'funding_bias': cdata.get('funding_bias'),
                    'volume_24h': cdata.get('volume_24h'),
                }
            except (json.JSONDecodeError, OSError):
                ctx['contract'] = None
        else:
            ctx['contract'] = None

        # Heartbeat
        heartbeat_file = XLM_BOT_DIR / 'data' / '.heartbeat'
        if heartbeat_file.exists():
            try:
                import time
                age_seconds = time.time() - heartbeat_file.stat().st_mtime
                ctx['heartbeat_age_s'] = round(age_seconds, 1)
                ctx['bot_alive'] = age_seconds < 120
            except OSError:
                ctx['heartbeat_age_s'] = None
                ctx['bot_alive'] = False
        else:
            ctx['heartbeat_age_s'] = None
            ctx['bot_alive'] = False

        return ctx


# ---------------------------------------------------------------------------
# Agent Performance Leaderboard (Meta performance review pattern)
# ---------------------------------------------------------------------------

class AgentPerformanceView(LoginRequiredMixin, TemplateView):
    template_name = 'hive/agent_performance.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_page'] = 'agent_performance'

        days = int(self.request.GET.get('days', 30))
        ctx['days'] = days

        # Try Supabase first
        scorecards = []
        try:
            import sys
            metrics_path = str(Path('/mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/everlight_os'))
            if metrics_path not in sys.path:
                sys.path.insert(0, metrics_path)
            from hive_mind.agent_metrics import get_all_agent_scorecards
            scorecards = get_all_agent_scorecards(days=days)
        except Exception:
            pass

        # Fallback to local telemetry JSONL
        if not scorecards:
            telemetry_file = Path('/mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/hive_mind/telemetry.jsonl')
            if telemetry_file.exists():
                try:
                    from collections import defaultdict
                    by_agent = defaultdict(list)
                    for line in telemetry_file.read_text(encoding='utf-8').strip().splitlines()[-500:]:
                        entry = json.loads(line)
                        by_agent[entry.get('specialist', 'unknown')].append(entry)

                    for name, rows in by_agent.items():
                        total = len(rows)
                        active = sum(1 for r in rows if r.get('specialist_status') == 'ACTIVE')
                        findings = sum(r.get('findings_count', 0) for r in rows)
                        recs = sum(1 for r in rows if r.get('has_recommendation'))
                        scorecards.append({
                            'agent_name': name,
                            'department': rows[0].get('manager', 'unknown'),
                            'total_tasks': total,
                            'success_rate': round(active / total * 100, 1) if total else 0,
                            'avg_duration_s': round(
                                sum(r.get('manager_duration_s', 0) for r in rows) / total, 1
                            ) if total else 0,
                            'total_findings': findings,
                            'total_recommendations': recs,
                        })
                    scorecards.sort(key=lambda s: s['success_rate'], reverse=True)
                except Exception:
                    pass

        ctx['scorecards'] = scorecards
        ctx['total_agents'] = len(scorecards)

        # Department summary
        dept_stats = {}
        for sc in scorecards:
            dept = sc.get('department', 'unknown')
            if dept not in dept_stats:
                dept_stats[dept] = {'count': 0, 'tasks': 0, 'success_sum': 0}
            dept_stats[dept]['count'] += 1
            dept_stats[dept]['tasks'] += sc.get('total_tasks', 0)
            dept_stats[dept]['success_sum'] += sc.get('success_rate', 0)

        ctx['departments'] = [
            {
                'name': dept,
                'agent_count': s['count'],
                'total_tasks': s['tasks'],
                'avg_success_rate': round(s['success_sum'] / s['count'], 1) if s['count'] else 0,
            }
            for dept, s in sorted(dept_stats.items())
        ]

        return ctx


# ===========================================================================
# ONBOARDING - Self-service Hive Mind deployment for customers
# ===========================================================================

def onboard_page(request):
    """Public onboarding page -- no login required."""
    from django.shortcuts import render
    return render(request, 'hive/onboard.html')


def onboard_submit(request):
    """Process onboarding form submission."""
    from django.shortcuts import render
    if request.method != 'POST':
        return render(request, 'hive/onboard.html')

    company = request.POST.get('company_name', '')
    contact = request.POST.get('contact_name', '')
    email = request.POST.get('email', '')
    desc = request.POST.get('business_desc', '')
    slack_url = request.POST.get('slack_workspace', '')
    agents = request.POST.getlist('agents')
    integrations = request.POST.getlist('integrations')

    # Log to Blinko
    try:
        import urllib.request
        note = (
            f"# New Hive Mind Customer: {company}\n"
            f"#hive/onboard #hive/customer\n\n"
            f"Contact: {contact} ({email})\n"
            f"Business: {desc}\n"
            f"Slack: {slack_url}\n"
            f"Agents: {', '.join(agents)}\n"
            f"Integrations: {', '.join(integrations)}\n"
        )
        payload = json.dumps({"content": note, "type": 1}).encode()
        req = urllib.request.Request(
            "http://129.159.38.250:1111/api/v1/note/upsert",
            data=payload, method="POST",
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception:
        pass

    # Post to Slack #ai-consulting
    try:
        import urllib.request
        slack_token_env = os.environ.get('SLACK_BOT_TOKEN', '')
        if slack_token_env:
            msg = (
                f":tada: *New Hive Mind Customer*\n"
                f"Company: {company}\n"
                f"Contact: {contact} ({email})\n"
                f"Agents: {', '.join(agents)}\n"
                f"Integrations: {', '.join(integrations)}"
            )
            payload = json.dumps({"channel": "C0AN8SGAS22", "text": msg}).encode()
            req = urllib.request.Request(
                "https://slack.com/api/chat.postMessage",
                data=payload, method="POST",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {slack_token_env}",
                },
            )
            urllib.request.urlopen(req, timeout=10)
    except Exception:
        pass

    return render(request, 'hive/onboard.html', {
        'success': True,
        'company': company,
    })


# =====================================================================
# INFRA HUB -- Proxmox-style server dashboard
# =====================================================================

ORACLE_SERVICES = [
    {"id": "xlm-bot", "name": "XLM Bot", "icon": "fa-robot", "port": None, "desc": "Sniper trading engine"},
    {"id": "xlm-dash-react", "name": "Lucrex Dashboard", "icon": "fa-chart-line", "port": 8502, "desc": "React trading dashboard"},
    {"id": "xlm-ws", "name": "WS Price Feed", "icon": "fa-bolt", "port": None, "desc": "WebSocket spot price feed"},
    {"id": "xlm-liqfeed", "name": "Liquidation Feed", "icon": "fa-water", "port": None, "desc": "Liquidation heatmap data"},
    {"id": "n8n", "name": "n8n Automation", "icon": "fa-gears", "port": 5678, "desc": "Workflow automation engine"},
    {"id": "blinko", "name": "Blinko RAG", "icon": "fa-brain", "port": 1111, "desc": "Knowledge base (458+ notes)"},
    {"id": "hive-voice", "name": "Voice Handler", "icon": "fa-microphone", "port": 8200, "desc": "Marcus phone actions"},
    {"id": "hive-django", "name": "Hive Dashboard", "icon": "fa-gauge-high", "port": 8504, "desc": "Ops command center"},
    {"id": "hive-dashboard", "name": "Hive Dashboard (alt)", "icon": "fa-table-columns", "port": None, "desc": "Legacy dashboard"},
    {"id": "hive-slack-agent", "name": "Slack Agent", "icon": "fa-hashtag", "port": None, "desc": "Slack bot with backoff"},
    {"id": "wholesale-pipeline", "name": "Wholesale Pipeline", "icon": "fa-house-chimney", "port": None, "desc": "RE wholesale scout (2h cycles)"},
]

DASHBOARD_LINKS = [
    {"name": "Lucrex Trading", "url": "http://129.159.38.250:8502", "icon": "fa-chart-candlestick", "color": "#c9a84c"},
    {"name": "Hive Ops", "url": "http://129.159.38.250:8504", "icon": "fa-gauge-high", "color": "#8b5cf6"},
    {"name": "n8n Workflows", "url": "http://129.159.38.250:5678", "icon": "fa-gears", "color": "#22c55e"},
    {"name": "Blinko RAG", "url": "http://129.159.38.250:1111", "icon": "fa-brain", "color": "#22d3ee"},
    {"name": "Voice Handler", "url": "http://129.159.38.250:8200", "icon": "fa-microphone", "color": "#f59e0b"},
]


class InfraHubView(LoginRequiredMixin, TemplateView):
    template_name = 'hive/infra_hub.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_page'] = 'infra_hub'
        ctx['services'] = ORACLE_SERVICES
        ctx['dashboard_links'] = DASHBOARD_LINKS
        ctx['oracle_ip'] = '129.159.38.250'
        return ctx


@login_required
def api_infra_status(request):
    """API endpoint: check Oracle service status via SSH."""
    import shlex

    oracle_ip = '129.159.38.250'
    results = {}

    for svc in ORACLE_SERVICES:
        sid = svc['id']
        try:
            cmd = f"ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no opc@{oracle_ip} systemctl is-active {shlex.quote(sid)}"
            proc = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=8,
            )
            status = proc.stdout.strip()
            results[sid] = {
                'status': status if status in ('active', 'inactive', 'failed', 'activating') else 'unknown',
                'port': svc.get('port'),
            }
        except subprocess.TimeoutExpired:
            results[sid] = {'status': 'timeout', 'port': svc.get('port')}
        except Exception as e:
            results[sid] = {'status': 'error', 'port': svc.get('port'), 'error': str(e)[:100]}

    # Disk + RAM (single SSH call)
    try:
        cmd = f"ssh -o ConnectTimeout=5 opc@{oracle_ip} 'df -h / --output=pcent | tail -1; free -m | grep Mem'"
        proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=8)
        lines = proc.stdout.strip().split('\n')
        disk_pct = lines[0].strip().replace('%', '') if lines else '?'
        mem_parts = lines[1].split() if len(lines) > 1 else []
        mem_total = mem_parts[1] if len(mem_parts) > 1 else '?'
        mem_used = mem_parts[2] if len(mem_parts) > 2 else '?'
    except Exception:
        disk_pct, mem_total, mem_used = '?', '?', '?'

    return JsonResponse({
        'services': results,
        'disk_pct': disk_pct,
        'mem_total_mb': mem_total,
        'mem_used_mb': mem_used,
        'oracle_ip': oracle_ip,
        'ts': timezone.now().isoformat(),
    })


# =====================================================================
# TEAM DIRECTORY + CO-PILOT DASHBOARD
# =====================================================================

class TeamDirectoryView(LoginRequiredMixin, TemplateView):
    """Team directory showing all 78 agents with profiles and activity."""
    template_name = 'hive/team_directory.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_page'] = 'team'

        # Load agent profiles
        profiles_path = Path('/mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/hive_mind/agent_profiles/all_profiles.json')
        if not profiles_path.exists():
            profiles_path = Path('/home/opc/06_DEVELOPMENT/everlight_os/hive_mind/agent_profiles/all_profiles.json')

        agents = []
        if profiles_path.exists():
            try:
                agents = json.loads(profiles_path.read_text())
            except Exception:
                pass

        ctx['agents'] = agents
        ctx['total_agents'] = len(agents)
        ctx['with_voice'] = sum(1 for a in agents if a.get('has_voice'))
        ctx['with_email'] = sum(1 for a in agents if a.get('email'))
        return ctx


@login_required
def api_team_roster(request):
    """API: Full agent roster with profiles."""
    profiles_path = Path('/mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/hive_mind/agent_profiles/all_profiles.json')
    if not profiles_path.exists():
        profiles_path = Path('/home/opc/06_DEVELOPMENT/everlight_os/hive_mind/agent_profiles/all_profiles.json')

    if profiles_path.exists():
        agents = json.loads(profiles_path.read_text())
    else:
        agents = []

    return JsonResponse({'agents': agents, 'total': len(agents)})


@login_required
def api_agent_copilot(request, slug):
    """API: Co-pilot data for a specific agent -- calls, meetings, logs."""
    # Load agent profile
    profiles_path = Path('/mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/hive_mind/agent_profiles/all_profiles.json')
    if not profiles_path.exists():
        profiles_path = Path('/home/opc/06_DEVELOPMENT/everlight_os/hive_mind/agent_profiles/all_profiles.json')

    agent = None
    if profiles_path.exists():
        for a in json.loads(profiles_path.read_text()):
            if a.get('slug') == slug:
                agent = a
                break

    if not agent:
        return JsonResponse({'error': 'agent_not_found'}, status=404)

    # Gather co-pilot data from various sources
    copilot = {
        'agent': agent,
        'recent_sessions': [],
        'call_log': [],
        'meetings': [],
        'outreach_stats': {'sent': 0, 'replied': 0, 'booked': 0},
        'activity_feed': [],
    }

    # Pull recent sessions for this agent from Hive sessions
    try:
        from .models import HiveSession, AgentResponse
        sessions = HiveSession.objects.filter(
            agent_responses__agent__name__icontains=agent['name']
        ).distinct().order_by('-created_at')[:10]
        copilot['recent_sessions'] = [
            {'id': s.session_id, 'query': s.query[:100], 'created': s.created_at.isoformat()}
            for s in sessions
        ]
    except Exception:
        pass

    return JsonResponse(copilot)


# =====================================================================
# PUBLIC BOOKING PAGE -- prospects can book meetings with agents
# =====================================================================

def agent_booking_page(request, agent_slug):
    """Public booking page for an agent. No auth required."""
    profiles_path = Path('/mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/hive_mind/agent_profiles/all_profiles.json')
    if not profiles_path.exists():
        profiles_path = Path('/home/opc/06_DEVELOPMENT/everlight_os/hive_mind/agent_profiles/all_profiles.json')

    agent = None
    if profiles_path.exists():
        for a in json.loads(profiles_path.read_text()):
            if a.get('slug') == agent_slug:
                agent = a
                break

    if not agent:
        return render(request, 'hive/booking_404.html', status=404)

    return render(request, 'hive/booking.html', {
        'agent': agent,
        'success': request.GET.get('booked') == '1',
    })


@require_POST
def agent_booking_submit(request, agent_slug):
    """Handle booking form submission."""
    profiles_path = Path('/mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/hive_mind/agent_profiles/all_profiles.json')
    if not profiles_path.exists():
        profiles_path = Path('/home/opc/06_DEVELOPMENT/everlight_os/hive_mind/agent_profiles/all_profiles.json')

    agent = None
    if profiles_path.exists():
        for a in json.loads(profiles_path.read_text()):
            if a.get('slug') == agent_slug:
                agent = a
                break

    if not agent:
        return HttpResponse(status=404)

    # Get form data
    prospect_name = request.POST.get('name', '')
    prospect_email = request.POST.get('email', '')
    date_time = request.POST.get('datetime', '')
    notes = request.POST.get('notes', '')

    if not prospect_name or not prospect_email or not date_time:
        return redirect(f'/book/{agent_slug}/?error=missing_fields')

    # Book via our lightweight system
    try:
        import sys
        neuro_path = '/mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/neuromorphic'
        if not os.path.exists(neuro_path):
            neuro_path = '/home/opc/06_DEVELOPMENT/everlight_os/neuromorphic'
        if neuro_path not in sys.path:
            sys.path.insert(0, neuro_path)

        from booking_system import book_meeting
        result = book_meeting(
            agent_slug=agent_slug,
            agent_name=agent.get('name', agent_slug),
            prospect_name=prospect_name,
            prospect_email=prospect_email,
            start_time=date_time,
            notes=notes,
        )
    except Exception as e:
        log.warning(f"Booking failed: {e}")

    return redirect(f'/book/{agent_slug}/?booked=1')


# ---------------------------------------------------------------------------
# Hive Logger API: ingest + artifact search
# ---------------------------------------------------------------------------

def _check_hive_token(request) -> bool:
    """Validate the X-Hive-Token header against settings.HIVE_LOGGER_TOKEN.

    When no token is configured in settings, the endpoint is open. This is the
    expected state during Phase A rollout before secrets are rotated in. Once
    `HIVE_LOGGER_TOKEN` is set in prod env, the header becomes required.
    """
    expected = getattr(settings, 'HIVE_LOGGER_TOKEN', '') or os.environ.get('HIVE_LOGGER_TOKEN', '')
    if not expected:
        return True
    presented = request.headers.get('X-Hive-Token', '') or request.META.get('HTTP_X_HIVE_TOKEN', '')
    return presented == expected


@csrf_exempt
@require_POST
def api_hive_log_ingest(request):
    """Accept one canonical hive_logger log line and upsert HiveSession + artifacts.

    Request body (JSON): see hive_logger.py finish() for schema.
    Response: {"ok": true, "session_id": str, "artifacts_created": int}

    Never raises; invalid payloads return {"ok": false, "error": "..."} with
    an appropriate status code so bots know to keep going.
    """
    if not _check_hive_token(request):
        return JsonResponse({"ok": False, "error": "forbidden"}, status=403)
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except Exception as exc:
        return JsonResponse({"ok": False, "error": f"bad json: {exc}"}, status=400)

    session_id = (payload.get('session_id') or '').strip()
    if not session_id:
        return JsonResponse({"ok": False, "error": "session_id required"}, status=400)

    def _parse_dt(v):
        if not v:
            return None
        try:
            return datetime.fromisoformat(str(v).replace('Z', '+00:00'))
        except Exception:
            return None

    created_at = _parse_dt(payload.get('started_at')) or timezone.now()

    defaults = {
        'query': (payload.get('task') or payload.get('summary') or '')[:10000] or '(no task)',
        'mode': payload.get('mode', 'full') if payload.get('mode') in {'full', 'lite', 'all'} else 'full',
        'status': payload.get('status', 'done') if payload.get('status') in {'running', 'done', 'partial', 'failed'} else 'done',
        'routed_to': payload.get('routed_to') or [],
        'created_at': created_at,
        'duration_seconds': payload.get('duration_seconds'),
        'combined_summary': (payload.get('summary') or '')[:20000],
        'agent': (payload.get('agent') or '')[:64],
        'task': (payload.get('task') or '')[:255],
    }

    session, _ = HiveSession.objects.update_or_create(
        session_id=session_id,
        defaults=defaults,
    )

    artifacts_created = 0
    for a in (payload.get('artifacts') or [])[:50]:
        try:
            HiveArtifact.objects.create(
                session=session,
                agent=session.agent or '',
                kind=(a.get('kind') or 'file')[:32],
                title=(a.get('title') or '')[:255],
                url=(a.get('url') or '')[:1024],
                path=(a.get('path') or '')[:1024],
                tags=a.get('tags') or [],
            )
            artifacts_created += 1
        except Exception as exc:
            logger.warning(f"hive_logger: artifact create failed: {exc}")

    session.artifacts_count = session.artifacts.count()
    session.save(update_fields=['artifacts_count'])

    return JsonResponse({
        "ok": True,
        "session_id": session_id,
        "artifacts_created": artifacts_created,
    })


@require_GET
def api_hive_artifact_search(request):
    """Search bot-created artifacts. Query params: kind, agent, q, since_days, limit."""
    qs = HiveArtifact.objects.all().select_related('session')
    kind = request.GET.get('kind', '').strip()
    agent = request.GET.get('agent', '').strip()
    q = request.GET.get('q', '').strip()
    since_days = request.GET.get('since_days', '').strip()
    limit = request.GET.get('limit', '50').strip()

    if kind:
        qs = qs.filter(kind=kind)
    if agent:
        qs = qs.filter(agent=agent)
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(url__icontains=q) | Q(path__icontains=q))
    if since_days:
        try:
            days = int(since_days)
            qs = qs.filter(created_at__gte=timezone.now() - timedelta(days=days))
        except ValueError:
            pass

    try:
        limit_i = max(1, min(500, int(limit)))
    except ValueError:
        limit_i = 50

    results = []
    for a in qs[:limit_i]:
        results.append({
            'id': a.id,
            'kind': a.kind,
            'agent': a.agent,
            'title': a.title,
            'url': a.url,
            'path': a.path,
            'tags': a.tags,
            'created_at': a.created_at.isoformat(),
            'session_id': a.session.session_id if a.session else None,
        })

    return JsonResponse({'ok': True, 'count': len(results), 'results': results})

