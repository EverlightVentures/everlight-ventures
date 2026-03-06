import json
import logging
import os
import platform
import shutil
from pathlib import Path

from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from django.utils import timezone
from django.db.models import Sum

from .models import TaskTemplate, TaskItem

log = logging.getLogger(__name__)

WORKSPACE = Path("/mnt/sdcard/AA_MY_DRIVE")


def board(request):
    """Main taskboard dashboard -- shows all pending/in-progress tasks."""
    status_filter = request.GET.get("status", "")
    category_filter = request.GET.get("category", "")
    batch_filter = request.GET.get("batch", "")

    tasks = TaskItem.objects.select_related("template").all()
    if status_filter:
        tasks = tasks.filter(status=status_filter)
    else:
        tasks = tasks.exclude(status="skipped")
    if category_filter:
        tasks = tasks.filter(template__category=category_filter)
    if batch_filter:
        tasks = tasks.filter(batch_id=batch_filter)

    pending = tasks.filter(status="pending")
    in_progress = tasks.filter(status="in_progress")
    completed = tasks.filter(status="completed").order_by("-completed_at")[:20]
    blocked = tasks.filter(status="blocked")

    batches = (
        TaskItem.objects.exclude(batch_id="")
        .values_list("batch_id", flat=True)
        .distinct()
    )

    stats = {
        "pending": TaskItem.objects.filter(status="pending").count(),
        "in_progress": TaskItem.objects.filter(status="in_progress").count(),
        "completed_today": TaskItem.objects.filter(
            status="completed", completed_at__date=timezone.now().date()
        ).count(),
        "total_completed": TaskItem.objects.filter(status="completed").count(),
        "awaiting_retrieval": TaskItem.objects.filter(
            status="completed", retrieved_by_agent=False
        ).count(),
    }

    return render(request, "taskboard/board.html", {
        "pending": pending,
        "in_progress": in_progress,
        "completed": completed,
        "blocked": blocked,
        "batches": batches,
        "stats": stats,
        "status_filter": status_filter,
        "category_filter": category_filter,
        "batch_filter": batch_filter,
        "categories": TaskTemplate.CATEGORY_CHOICES,
    })


def task_form(request, task_id):
    """Render dynamic form for a specific task based on its template schema."""
    task = get_object_or_404(TaskItem.objects.select_related("template"), id=task_id)

    if task.status == "pending":
        task.status = "in_progress"
        task.save()

    fields = task.template.get_fields()
    existing_data = task.get_data() if task.data_encrypted else {}

    return render(request, "taskboard/task_form.html", {
        "task": task,
        "fields": fields,
        "existing_data": existing_data,
    })


@require_POST
def task_submit(request, task_id):
    """Process form submission for a task."""
    task = get_object_or_404(TaskItem.objects.select_related("template"), id=task_id)
    fields = task.template.get_fields()

    data = {}
    for field in fields:
        name = field["name"]
        value = request.POST.get(name, "").strip()
        if field.get("type") == "checkbox":
            value = name in request.POST
        data[name] = value

    task.set_data(data)
    task.notes = request.POST.get("_notes", "").strip()

    action = request.POST.get("_action", "save")
    if action == "complete":
        task.mark_completed()
    else:
        task.status = "in_progress"
        task.save()

    return redirect("taskboard:board")


@require_POST
def task_skip(request, task_id):
    """Skip a task."""
    task = get_object_or_404(TaskItem, id=task_id)
    task.status = "skipped"
    task.save()
    return redirect("taskboard:board")


@require_POST
def task_block(request, task_id):
    """Mark a task as blocked."""
    task = get_object_or_404(TaskItem, id=task_id)
    task.status = "blocked"
    task.notes = request.POST.get("reason", task.notes)
    task.save()
    return redirect("taskboard:board")


# ── AI API Endpoints ──────────────────────────────────────────────────

@csrf_exempt
@require_POST
def api_create_tasks(request):
    """
    AI agents call this to create tasks for human completion.

    POST JSON:
    {
      "batch_id": "content_engine_setup_20260305",
      "source_agent": "claude",
      "target_agent": "avatar_orchestrator",
      "tasks": [
        {
          "template": "elevenlabs_api",
          "title": "ElevenLabs: Sign up free tier, get API key + voice IDs",
          "description": "Needed for TTS audio generation in avatar pipeline",
          "priority": 2
        },
        ...
      ]
    }

    If a template doesn't exist, creates it from inline schema:
    {
      "template": "elevenlabs_api",
      "template_schema": {
        "fields": [
          {"name": "api_key", "label": "API Key", "type": "secret", "required": true},
          {"name": "voice_id_1", "label": "Voice ID #1", "type": "text", "required": true}
        ]
      },
      "template_category": "api_credential",
      "template_icon": "fa-solid fa-microphone",
      ...
    }
    """
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    batch_id = payload.get("batch_id", "")
    source_agent = payload.get("source_agent", "")
    target_agent = payload.get("target_agent", "")
    tasks_data = payload.get("tasks", [])

    if not tasks_data:
        return JsonResponse({"error": "No tasks provided"}, status=400)

    created = []
    for td in tasks_data:
        template_name = td.get("template", "")
        if not template_name:
            continue

        # Get or create template
        template = TaskTemplate.objects.filter(name=template_name).first()
        if not template and td.get("template_schema"):
            template = TaskTemplate.objects.create(
                name=template_name,
                category=td.get("template_category", "general"),
                description=td.get("template_description", ""),
                icon=td.get("template_icon", "fa-solid fa-clipboard-list"),
                schema=td["template_schema"],
            )
        elif not template:
            continue

        task = TaskItem.objects.create(
            template=template,
            title=td.get("title", template_name),
            description=td.get("description", ""),
            priority=td.get("priority", 3),
            source_agent=td.get("source_agent", source_agent),
            target_agent=td.get("target_agent", target_agent),
            batch_id=td.get("batch_id", batch_id),
        )
        created.append({"id": task.id, "title": task.title})

    return JsonResponse({"created": len(created), "tasks": created})


@csrf_exempt
@require_GET
def api_retrieve_completed(request):
    """
    AI agents call this to retrieve completed task data.

    GET /taskboard/api/completed/?target_agent=avatar_orchestrator&batch_id=...

    Returns decrypted data for completed, unretrieved tasks.
    Marks them as retrieved after returning.
    """
    target = request.GET.get("target_agent", "")
    batch = request.GET.get("batch_id", "")

    tasks = TaskItem.objects.filter(status="completed", retrieved_by_agent=False)
    if target:
        tasks = tasks.filter(target_agent=target)
    if batch:
        tasks = tasks.filter(batch_id=batch)

    results = []
    for task in tasks:
        results.append({
            "id": task.id,
            "template": task.template.name,
            "category": task.template.category,
            "title": task.title,
            "data": task.get_data(),
            "notes": task.notes,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        })
        task.mark_retrieved()

    return JsonResponse({"count": len(results), "tasks": results})


@csrf_exempt
@require_GET
def api_status(request):
    """Quick status check for agents to see if there's pending work."""
    return JsonResponse({
        "pending": TaskItem.objects.filter(status="pending").count(),
        "in_progress": TaskItem.objects.filter(status="in_progress").count(),
        "completed_unretrieved": TaskItem.objects.filter(
            status="completed", retrieved_by_agent=False
        ).count(),
    })


# ── Nerve Center ──────────────────────────────────────────────────────

# Required env vars for the full system
REQUIRED_ENV_VARS = [
    ("ANTHROPIC_API_KEY", "Claude API"),
    ("ELEVENLABS_API_KEY", "ElevenLabs TTS"),
    ("ELEVENLABS_VOICE_ID", "ElevenLabs Voice"),
    ("SMTP_HOST", "Email SMTP Host"),
    ("SMTP_USER", "Email SMTP User"),
    ("SMTP_PASS", "Email SMTP Password"),
    ("STRIPE_SECRET_KEY", "Stripe Payments"),
    ("TWITTER_API_KEY", "X/Twitter API"),
    ("SLACK_WEBHOOK_URL", "Slack Notifications"),
    ("DID_API_KEY", "D-ID Lip-sync (opt)"),
]


def nerve_center(request):
    """System-wide status dashboard -- the brain of the operation."""
    now = timezone.now()

    # -- Taskboard stats --
    tb_pending = TaskItem.objects.filter(status="pending").count()
    tb_in_progress = TaskItem.objects.filter(status="in_progress").count()
    tb_completed = TaskItem.objects.filter(status="completed").count()
    tb_total = TaskItem.objects.exclude(status="skipped").count()
    tb_pct = int((tb_completed / tb_total * 100)) if tb_total > 0 else 0

    taskboard_health = "ok" if tb_pending == 0 else ("warn" if tb_pending <= 3 else "err")

    # -- Environment / Credentials --
    env_vars = []
    set_count = 0
    for var_name, label in REQUIRED_ENV_VARS:
        is_set = bool(os.environ.get(var_name))
        if not is_set:
            # Also check .env file
            env_file = WORKSPACE / ".env"
            if env_file.exists():
                for line in env_file.read_text().splitlines():
                    if line.startswith(f"{var_name}=") and len(line.split("=", 1)[1].strip()) > 0:
                        is_set = True
                        break
        if is_set:
            set_count += 1
        env_vars.append({"name": var_name, "label": label, "is_set": is_set})

    total_env = len(REQUIRED_ENV_VARS)
    env_health = "ok" if set_count >= total_env - 2 else ("warn" if set_count >= 3 else "err")

    # -- Content Pipeline checks --
    portraits_dir = WORKSPACE / "01_BUSINESSES/Everlight_Ventures/03_Content/Avatar_Assets/base_portraits"
    portrait_count = len(list(portraits_dir.glob("*.jpg")) + list(portraits_dir.glob("*.png"))) if portraits_dir.exists() else 0
    output_queue = WORKSPACE / "02_CONTENT_FACTORY/01_Queue/avatar_output"
    queued_videos = len(list(output_queue.iterdir())) if output_queue.exists() else 0

    ffmpeg_ok = shutil.which("ffmpeg") is not None
    ffprobe_ok = shutil.which("ffprobe") is not None

    pipeline_checks = [
        {"label": "ffmpeg installed", "color": "green" if ffmpeg_ok else "red",
         "detail": "OK" if ffmpeg_ok else "MISSING"},
        {"label": "ffprobe installed", "color": "green" if ffprobe_ok else "red",
         "detail": "OK" if ffprobe_ok else "MISSING"},
        {"label": "Avatar portraits", "color": "green" if portrait_count >= 3 else ("yellow" if portrait_count > 0 else "red"),
         "detail": f"{portrait_count} images"},
        {"label": "Videos in queue", "color": "green" if queued_videos > 0 else "gray",
         "detail": str(queued_videos)},
        {"label": "avatar_orchestrator.py", "color": "green" if (WORKSPACE / "03_AUTOMATION_CORE/01_Scripts/avatar_orchestrator.py").exists() else "red",
         "detail": "exists" if (WORKSPACE / "03_AUTOMATION_CORE/01_Scripts/avatar_orchestrator.py").exists() else "MISSING"},
        {"label": "social_poster.py", "color": "green" if (WORKSPACE / "03_AUTOMATION_CORE/01_Scripts/social_poster.py").exists() else "red",
         "detail": "exists" if (WORKSPACE / "03_AUTOMATION_CORE/01_Scripts/social_poster.py").exists() else "MISSING"},
    ]
    pipeline_health = "ok" if ffmpeg_ok and portrait_count >= 3 else ("warn" if ffmpeg_ok else "err")

    # -- Funnel stats --
    try:
        from funnel.models import Lead, FunnelEvent
        total_leads = Lead.objects.count()
        today_leads = Lead.objects.filter(created_at__date=now.date()).count()
        emails_sent = FunnelEvent.objects.filter(event_type="email_sent").count()
    except Exception:
        total_leads = today_leads = emails_sent = 0

    funnel_health = "ok" if total_leads > 0 else "info"

    # -- Infrastructure --
    db_path = WORKSPACE / "09_DASHBOARD/hive_dashboard/db.sqlite3"
    db_size_mb = f"{db_path.stat().st_size / 1024 / 1024:.1f} MB" if db_path.exists() else "N/A"

    infra_checks = [
        {"label": "Django server", "color": "green", "detail": "running"},
        {"label": "SQLite database", "color": "green" if db_path.exists() else "red",
         "detail": db_size_mb},
        {"label": "Python version", "color": "green",
         "detail": platform.python_version()},
        {"label": "Platform", "color": "green",
         "detail": platform.machine()},
        {"label": "funnel_nurture.py", "color": "green" if (WORKSPACE / "03_AUTOMATION_CORE/01_Scripts/funnel_nurture.py").exists() else "red",
         "detail": "exists" if (WORKSPACE / "03_AUTOMATION_CORE/01_Scripts/funnel_nurture.py").exists() else "MISSING"},
    ]
    infra_health = "ok"

    # -- Recent activity from taskboard + funnel --
    recent_events = []
    for task in TaskItem.objects.exclude(status="pending").order_by("-updated_at")[:5]:
        color = {"completed": "green", "in_progress": "yellow", "blocked": "red", "skipped": "gray"}.get(task.status, "gray")
        recent_events.append({
            "text": f"[{task.get_status_display()}] {task.title[:50]}",
            "time": task.updated_at,
            "color": color,
        })
    try:
        from funnel.models import FunnelEvent
        for event in FunnelEvent.objects.order_by("-timestamp")[:5]:
            recent_events.append({
                "text": f"{event.event_type}: {event.lead.email}",
                "time": event.timestamp,
                "color": "green",
            })
    except Exception:
        pass
    recent_events.sort(key=lambda x: x["time"], reverse=True)
    recent_events = recent_events[:10]

    # Overall status
    healths = [taskboard_health, env_health, pipeline_health, funnel_health, infra_health]
    if "err" in healths:
        overall_status = "dead"
    elif "warn" in healths:
        overall_status = "warn"
    else:
        overall_status = "live"

    return render(request, "taskboard/nerve_center.html", {
        "overall_status": overall_status,
        "taskboard": {
            "pending": tb_pending, "in_progress": tb_in_progress,
            "completed": tb_completed, "total": tb_total, "pct_done": tb_pct,
        },
        "taskboard_health": taskboard_health,
        "env_vars": env_vars,
        "env_stats": {"set_count": set_count, "total": total_env},
        "env_health": env_health,
        "pipeline_checks": pipeline_checks,
        "pipeline_health": pipeline_health,
        "funnel": {"total_leads": total_leads, "today_leads": today_leads, "emails_sent": emails_sent},
        "funnel_health": funnel_health,
        "infra_checks": infra_checks,
        "infra_health": infra_health,
        "platform": platform.machine(),
        "recent_events": recent_events,
    })
