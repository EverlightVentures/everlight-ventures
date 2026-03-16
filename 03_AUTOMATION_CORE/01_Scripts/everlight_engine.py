#!/usr/bin/env python3
"""
everlight_engine.py -- Master Orchestrator CLI
Ties together: content pipeline + funnel + social posting + taskboard + credentials

This is the single entry point for the entire Everlight content/marketing system.

Commands:
    python everlight_engine.py status           # Nerve center status (CLI)
    python everlight_engine.py generate          # Generate content batch
    python everlight_engine.py post              # Post next item from queue
    python everlight_engine.py nurture           # Run email nurture cycle
    python everlight_engine.py apply-creds       # Apply completed taskboard credentials to .env
    python everlight_engine.py push-tasks FILE   # Push task definitions from JSON to taskboard
    python everlight_engine.py daily             # Full daily cycle (generate + post + nurture)
    python everlight_engine.py --dry-run CMD     # Dry run any command
"""

import os
import sys
import json
import argparse
import subprocess
import logging
from datetime import datetime
from pathlib import Path

WORKSPACE = Path("/mnt/sdcard/AA_MY_DRIVE")
SCRIPTS = WORKSPACE / "03_AUTOMATION_CORE/01_Scripts"
DJANGO_DIR = WORKSPACE / "09_DASHBOARD/hive_dashboard"
LOG_DIR = WORKSPACE / "_logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "everlight_engine.log"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("everlight_engine")

# ANSI colors for terminal output
C = {
    "g": "\033[92m", "y": "\033[93m", "r": "\033[91m",
    "b": "\033[94m", "m": "\033[95m", "c": "\033[96m",
    "w": "\033[97m", "d": "\033[90m", "0": "\033[0m",
    "bold": "\033[1m",
}


def _run(cmd, dry_run=False):
    """Run a subprocess and return (success, output)."""
    log.info(f"  {'[DRY] ' if dry_run else ''}$ {' '.join(cmd)}")
    if dry_run:
        return True, "[dry run]"
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(WORKSPACE))
    if result.returncode != 0:
        log.warning(f"  Exit {result.returncode}: {result.stderr[:200]}")
    return result.returncode == 0, result.stdout + result.stderr


def _django_setup():
    """Initialize Django for ORM access."""
    sys.path.insert(0, str(DJANGO_DIR))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hive_dashboard.settings")
    import django
    django.setup()


def _notify_slack(message):
    """Send to Slack if webhook is set."""
    webhook = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook:
        return
    try:
        import requests
        requests.post(webhook, json={"text": message, "channel": "#04-content-factory"}, timeout=5)
    except Exception:
        pass


# ── Commands ──────────────────────────────────────────────────────────

def cmd_status(args):
    """Show system-wide status in terminal."""
    _django_setup()
    from taskboard.models import TaskItem

    print(f"\n{C['bold']}{C['m']}  EVERLIGHT ENGINE -- NERVE CENTER{C['0']}")
    print(f"{C['d']}  {'=' * 50}{C['0']}\n")

    # Taskboard
    pending = TaskItem.objects.filter(status="pending").count()
    in_prog = TaskItem.objects.filter(status="in_progress").count()
    done = TaskItem.objects.filter(status="completed").count()
    total = TaskItem.objects.exclude(status="skipped").count()
    pct = int(done / total * 100) if total > 0 else 0

    dot = f"{C['g']}*{C['0']}" if pending == 0 else f"{C['y']}*{C['0']}"
    print(f"  {dot} {C['bold']}Taskboard{C['0']}  {pending} pending / {in_prog} active / {done} done ({pct}%)")

    # Environment
    env_file = WORKSPACE / ".env"
    env_data = {}
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                env_data[k.strip()] = v.strip()

    required = [
        "ANTHROPIC_API_KEY", "ELEVENLABS_API_KEY", "ELEVENLABS_VOICE_ID",
        "SMTP_HOST", "SMTP_USER", "STRIPE_SECRET_KEY", "TWITTER_API_KEY",
        "SLACK_WEBHOOK_URL",
    ]
    set_count = sum(1 for v in required if os.environ.get(v) or env_data.get(v))
    env_dot = f"{C['g']}*{C['0']}" if set_count >= len(required) - 2 else f"{C['r']}*{C['0']}"
    print(f"  {env_dot} {C['bold']}Credentials{C['0']}  {set_count}/{len(required)} env vars set")

    for v in required:
        is_set = bool(os.environ.get(v) or env_data.get(v))
        icon = f"{C['g']}OK{C['0']}" if is_set else f"{C['r']}--{C['0']}"
        print(f"      {icon}  {v}")

    # Pipeline files
    print(f"\n  {C['b']}*{C['0']} {C['bold']}Content Pipeline{C['0']}")
    scripts_check = [
        ("avatar_orchestrator.py", SCRIPTS / "avatar_orchestrator.py"),
        ("social_poster.py", SCRIPTS / "social_poster.py"),
        ("funnel_nurture.py", SCRIPTS / "funnel_nurture.py"),
    ]
    for name, path in scripts_check:
        icon = f"{C['g']}OK{C['0']}" if path.exists() else f"{C['r']}!!{C['0']}"
        print(f"      {icon}  {name}")

    portraits_dir = WORKSPACE / "01_BUSINESSES/Everlight_Ventures/03_Content/Avatar_Assets/base_portraits"
    p_count = len(list(portraits_dir.glob("*.*"))) if portraits_dir.exists() else 0
    icon = f"{C['g']}OK{C['0']}" if p_count >= 3 else f"{C['y']}{p_count}{C['0']}"
    print(f"      {icon}  Avatar portraits ({p_count} files)")

    import shutil
    ffmpeg_ok = shutil.which("ffmpeg") is not None
    icon = f"{C['g']}OK{C['0']}" if ffmpeg_ok else f"{C['r']}!!{C['0']}"
    print(f"      {icon}  ffmpeg {'installed' if ffmpeg_ok else 'MISSING'}")

    # Funnel
    try:
        from funnel.models import Lead, FunnelEvent
        leads = Lead.objects.count()
        emails = FunnelEvent.objects.filter(event_type="email_sent").count()
        print(f"\n  {C['c']}*{C['0']} {C['bold']}Funnel{C['0']}  {leads} leads / {emails} emails sent")
    except Exception:
        print(f"\n  {C['d']}*{C['0']} {C['bold']}Funnel{C['0']}  not initialized")

    print(f"\n{C['d']}  {'=' * 50}{C['0']}\n")


def cmd_generate(args):
    """Generate a content batch."""
    product = args.product or "onyx"
    persona = args.persona or ("founder" if product == "onyx" else "builder")
    count = args.count or 2

    log.info(f"=== Content Generation: product={product} persona={persona} count={count} ===")
    cmd = [
        sys.executable, str(SCRIPTS / "avatar_orchestrator.py"),
        "--product", product, "--persona", persona, "--count", str(count),
    ]
    if args.dry_run:
        cmd.append("--dry-run")

    ok, output = _run(cmd, dry_run=False)  # Actually run it (it has its own dry-run)
    if ok:
        _notify_slack(f"Content batch generated: {product} x{count}")
    return ok


def cmd_post(args):
    """Post next item from content queue."""
    log.info("=== Social Posting ===")
    cmd = [sys.executable, str(SCRIPTS / "social_poster.py"), "--from-queue"]
    if args.dry_run:
        cmd.append("--dry-run")
    ok, output = _run(cmd)
    return ok


def cmd_nurture(args):
    """Run email nurture cycle."""
    log.info("=== Funnel Nurture ===")
    cmd = [sys.executable, str(SCRIPTS / "funnel_nurture.py")]
    if args.dry_run:
        cmd.append("--dry-run")
    ok, output = _run(cmd)
    return ok


def cmd_apply_creds(args):
    """Apply completed taskboard credentials to .env."""
    log.info("=== Applying Credentials ===")
    cmd = [sys.executable, str(DJANGO_DIR / "manage.py"), "apply_credentials"]
    if args.dry_run:
        cmd.append("--dry-run")
    ok, output = _run(cmd)
    print(output)
    return ok


def cmd_push_tasks(args):
    """Push task definitions from a JSON file to the taskboard API."""
    if not args.file:
        log.error("No file specified. Usage: everlight_engine.py push-tasks tasks.json")
        return False

    task_file = Path(args.file)
    if not task_file.exists():
        log.error(f"File not found: {task_file}")
        return False

    payload = json.loads(task_file.read_text())
    log.info(f"Pushing {len(payload.get('tasks', []))} tasks to taskboard...")

    if args.dry_run:
        for t in payload.get("tasks", []):
            log.info(f"  [DRY] Would create: {t.get('title', t.get('template'))}")
        return True

    _django_setup()
    from taskboard.models import TaskTemplate, TaskItem

    batch_id = payload.get("batch_id", f"push_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    source = payload.get("source_agent", "everlight_engine")
    target = payload.get("target_agent", "")
    created = 0

    for td in payload.get("tasks", []):
        template = TaskTemplate.objects.filter(name=td["template"]).first()
        if not template:
            if td.get("template_schema"):
                template = TaskTemplate.objects.create(
                    name=td["template"],
                    category=td.get("template_category", "general"),
                    description=td.get("template_description", ""),
                    icon=td.get("template_icon", "fa-solid fa-clipboard-list"),
                    schema=td["template_schema"],
                )
            else:
                log.warning(f"  Template '{td['template']}' not found, skipping")
                continue

        TaskItem.objects.create(
            template=template,
            title=td.get("title", td["template"]),
            description=td.get("description", ""),
            priority=td.get("priority", 3),
            source_agent=td.get("source_agent", source),
            target_agent=td.get("target_agent", target),
            batch_id=td.get("batch_id", batch_id),
        )
        created += 1
        log.info(f"  Created: {td.get('title', td['template'])}")

    log.info(f"Pushed {created} tasks to taskboard (batch: {batch_id})")
    _notify_slack(f"Taskboard: {created} new tasks pushed (batch: {batch_id})")
    return True


def cmd_daily(args):
    """Full daily cycle: generate + post + nurture."""
    log.info(f"{'=' * 60}")
    log.info(f"=== EVERLIGHT DAILY CYCLE -- {datetime.now().strftime('%Y-%m-%d %H:%M PT')} ===")
    log.info(f"{'=' * 60}")

    results = []

    # 1. Generate content
    log.info("\n[1/3] Generating content batch...")
    results.append(("Content Gen", cmd_generate(args)))

    # 2. Post to social
    log.info("\n[2/3] Posting to social...")
    results.append(("Social Post", cmd_post(args)))

    # 3. Nurture emails
    log.info("\n[3/3] Running email nurture...")
    results.append(("Email Nurture", cmd_nurture(args)))

    # Summary
    log.info("\n=== Daily Cycle Complete ===")
    for name, ok in results:
        status = "OK" if ok else "FAILED"
        log.info(f"  {name}: {status}")

    all_ok = all(ok for _, ok in results)
    _notify_slack(
        f"Daily cycle {'complete' if all_ok else 'completed with errors'}: "
        + ", ".join(f"{n}={'OK' if ok else 'FAIL'}" for n, ok in results)
    )
    return all_ok


# ── CLI ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Everlight Engine -- Master Content & Funnel Orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--dry-run", action="store_true", help="Simulate without side effects")
    parser.add_argument("--product", default="onyx", help="Product for content gen (onyx/hivemind)")
    parser.add_argument("--persona", default="", help="Persona override")
    parser.add_argument("--count", type=int, default=2, help="Content batch size")

    sub = parser.add_subparsers(dest="command", help="Available commands")
    sub.add_parser("status", help="Show system status")
    sub.add_parser("generate", help="Generate content batch")
    sub.add_parser("post", help="Post to social media")
    sub.add_parser("nurture", help="Run email nurture")
    sub.add_parser("apply-creds", help="Apply taskboard credentials to .env")
    push_p = sub.add_parser("push-tasks", help="Push tasks from JSON file")
    push_p.add_argument("file", nargs="?", help="JSON task definition file")
    sub.add_parser("daily", help="Full daily cycle")

    args = parser.parse_args()

    commands = {
        "status": cmd_status,
        "generate": cmd_generate,
        "post": cmd_post,
        "nurture": cmd_nurture,
        "apply-creds": cmd_apply_creds,
        "push-tasks": cmd_push_tasks,
        "daily": cmd_daily,
    }

    if not args.command:
        parser.print_help()
        return

    fn = commands.get(args.command)
    if fn:
        fn(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
