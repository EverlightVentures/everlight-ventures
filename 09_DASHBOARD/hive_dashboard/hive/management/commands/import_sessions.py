"""
Hive Mind Dashboard - Import Sessions from JSONL
Reads hive_sessions.jsonl and war room directories into the Django database.

Usage:
    python manage.py import_sessions
    python manage.py import_sessions --file /path/to/sessions.jsonl
    python manage.py import_sessions --clear  # wipe existing data first
"""
import json
from datetime import datetime, timezone as dt_timezone
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from hive.models import Agent, AgentResponse, HiveSession, SystemEvent


# ---------------------------------------------------------------------------
# Default agent definitions
# ---------------------------------------------------------------------------

DEFAULT_AGENTS = [
    {
        'name': 'claude',
        'display_name': 'Claude',
        'role': 'Chief Operator / Strategist',
        'color': '#8b5cf6',
        'icon_class': 'fa-brain',
    },
    {
        'name': 'gemini',
        'display_name': 'Gemini',
        'role': 'Logistics Commander / Executor',
        'color': '#22d3ee',
        'icon_class': 'fa-gem',
    },
    {
        'name': 'codex',
        'display_name': 'Codex',
        'role': 'Engineering Foreman / Profit Maximizer',
        'color': '#22c55e',
        'icon_class': 'fa-code',
    },
    {
        'name': 'perplexity',
        'display_name': 'Perplexity',
        'role': 'Intelligence Anchor / News Desk',
        'color': '#f59e0b',
        'icon_class': 'fa-search',
    },
]


class Command(BaseCommand):
    help = "Import Hive Mind sessions from hive_sessions.jsonl into the database."

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default=None,
            help='Path to hive_sessions.jsonl (default: settings.HIVE_SESSIONS_JSONL)',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear all existing session data before importing',
        )

    def handle(self, *args, **options):
        jsonl_path = options['file'] or getattr(
            settings, 'HIVE_SESSIONS_JSONL',
            '/mnt/sdcard/AA_MY_DRIVE/_logs/hive_sessions.jsonl',
        )
        path = Path(jsonl_path)

        if not path.exists():
            raise CommandError(f"JSONL file not found: {jsonl_path}")

        self.stdout.write(self.style.NOTICE(
            f"Importing from: {jsonl_path}"
        ))

        # Optionally clear existing data
        if options['clear']:
            self.stdout.write(self.style.WARNING("Clearing existing data..."))
            AgentResponse.objects.all().delete()
            HiveSession.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("Cleared."))

        # Ensure default agents exist
        self._ensure_default_agents()

        # Cache agent objects
        agent_map = {a.name: a for a in Agent.objects.all()}

        # Read and parse JSONL
        lines = path.read_text(encoding='utf-8').strip().splitlines()
        self.stdout.write(f"Found {len(lines)} lines in JSONL file.")

        created_count = 0
        updated_count = 0
        skipped_count = 0
        error_count = 0

        with transaction.atomic():
            for i, line in enumerate(lines, start=1):
                line = line.strip()
                if not line:
                    continue

                try:
                    entry = json.loads(line)
                except json.JSONDecodeError as e:
                    self.stdout.write(self.style.ERROR(
                        f"  Line {i}: JSON parse error: {e}"
                    ))
                    error_count += 1
                    continue

                session_id = entry.get('id', '').strip()
                if not session_id:
                    self.stdout.write(self.style.ERROR(
                        f"  Line {i}: Missing session id, skipping."
                    ))
                    skipped_count += 1
                    continue

                # Parse timestamp
                created_at = self._parse_timestamp(
                    entry.get('timestamp', '')
                )

                # Get or create the HiveSession
                session, was_created = HiveSession.objects.get_or_create(
                    session_id=session_id,
                    defaults={
                        'query': entry.get('prompt', ''),
                        'mode': entry.get('mode', 'full'),
                        'status': entry.get('status', 'done'),
                        'routed_to': entry.get('routed_to', []),
                        'created_at': created_at,
                        'duration_seconds': entry.get('total_duration_s'),
                        'war_room_dir': entry.get('war_room_dir', ''),
                    },
                )

                if was_created:
                    created_count += 1
                    self.stdout.write(f"  + Session {session_id[:8]} created")
                else:
                    updated_count += 1
                    self.stdout.write(f"  ~ Session {session_id[:8]} already exists")

                # Import agent responses from manager_statuses
                manager_statuses = entry.get('manager_statuses', {})
                self._import_responses_from_statuses(
                    session, manager_statuses, agent_map
                )

                # Try to enrich from war room directory
                war_room_dir = entry.get('war_room_dir', '')
                if war_room_dir:
                    self._enrich_from_war_room(
                        session, war_room_dir, agent_map
                    )

        # Summary
        total_imported = created_count + updated_count
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"Import complete: {created_count} created, "
            f"{updated_count} existing, {skipped_count} skipped, "
            f"{error_count} errors"
        ))

        # Log a SystemEvent
        SystemEvent.objects.create(
            level='info',
            title='Sessions imported from JSONL',
            detail=(
                f"File: {jsonl_path}\n"
                f"Lines: {len(lines)}\n"
                f"Created: {created_count}\n"
                f"Existing: {updated_count}\n"
                f"Skipped: {skipped_count}\n"
                f"Errors: {error_count}"
            ),
        )
        self.stdout.write(self.style.SUCCESS("SystemEvent logged."))

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    def _ensure_default_agents(self):
        """Create the 4 default agents if they do not exist."""
        for agent_def in DEFAULT_AGENTS:
            agent, created = Agent.objects.get_or_create(
                name=agent_def['name'],
                defaults={
                    'display_name': agent_def['display_name'],
                    'role': agent_def['role'],
                    'color': agent_def['color'],
                    'icon_class': agent_def['icon_class'],
                    'is_active': True,
                },
            )
            if created:
                self.stdout.write(self.style.SUCCESS(
                    f"  Created agent: {agent.display_name} "
                    f"({agent.role})"
                ))
            else:
                self.stdout.write(
                    f"  Agent exists: {agent.display_name}"
                )

    def _parse_timestamp(self, ts_str):
        """Parse ISO timestamp string, return timezone-aware datetime."""
        if not ts_str:
            return timezone.now()
        try:
            # Handle both Z suffix and +00:00
            ts_str = ts_str.replace('Z', '+00:00')
            dt = datetime.fromisoformat(ts_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=dt_timezone.utc)
            return dt
        except (ValueError, TypeError):
            return timezone.now()

    def _import_responses_from_statuses(self, session, manager_statuses,
                                         agent_map):
        """Create AgentResponse records from the manager_statuses dict."""
        for agent_name, status_info in manager_statuses.items():
            agent_name_lower = agent_name.lower().strip()
            agent = agent_map.get(agent_name_lower)

            if not agent:
                # Auto-create unknown agents
                agent, _ = Agent.objects.get_or_create(
                    name=agent_name_lower,
                    defaults={
                        'display_name': agent_name.title(),
                        'role': '',
                        'color': '#6b7280',
                        'icon_class': 'fa-robot',
                    },
                )
                agent_map[agent_name_lower] = agent

            # Get or create the response
            response, created = AgentResponse.objects.get_or_create(
                session=session,
                agent=agent,
                defaults={
                    'status': status_info.get('status', 'done'),
                    'duration_seconds': status_info.get('duration_s'),
                },
            )
            if not created:
                # Update duration if we have it now and didn't before
                if (response.duration_seconds is None
                        and status_info.get('duration_s') is not None):
                    response.duration_seconds = status_info['duration_s']
                    response.save(update_fields=['duration_seconds'])

    def _enrich_from_war_room(self, session, war_room_dir, agent_map):
        """
        Read session.json and combined_summary.md from the war room
        directory to fill in response_text, intel_summary, etc.
        """
        war_path = Path(war_room_dir)
        if not war_path.is_dir():
            return

        # Read session.json for full manager response texts
        session_json_path = war_path / 'session.json'
        if session_json_path.exists():
            try:
                session_data = json.loads(
                    session_json_path.read_text(encoding='utf-8')
                )
            except (json.JSONDecodeError, OSError):
                session_data = {}

            # Update intel_summary on the session
            intel = session_data.get('intel_summary', '')
            if intel and not session.intel_summary:
                session.intel_summary = intel
                session.save(update_fields=['intel_summary'])

            # Update agent responses with full text from managers array
            managers = session_data.get('managers', [])
            for mgr in managers:
                mgr_name = mgr.get('manager', '').lower().strip()
                agent = agent_map.get(mgr_name)
                if not agent:
                    continue

                try:
                    response = AgentResponse.objects.get(
                        session=session, agent=agent
                    )
                except AgentResponse.DoesNotExist:
                    continue

                # Fill response_text if empty
                if not response.response_text and mgr.get('response_text'):
                    response.response_text = mgr['response_text']

                # Fill error_message if empty
                if not response.error_message and mgr.get('error'):
                    response.error_message = mgr['error']

                # Fill employees_consulted
                if (not response.employees_consulted
                        and mgr.get('employees_consulted')):
                    response.employees_consulted = mgr['employees_consulted']

                response.save(update_fields=[
                    'response_text', 'error_message', 'employees_consulted',
                ])

        # Read combined_summary.md
        summary_path = war_path / 'combined_summary.md'
        if summary_path.exists() and not session.combined_summary:
            try:
                session.combined_summary = summary_path.read_text(
                    encoding='utf-8'
                )
                session.save(update_fields=['combined_summary'])
            except OSError:
                pass
