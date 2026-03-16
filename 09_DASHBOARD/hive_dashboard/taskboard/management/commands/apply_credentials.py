"""
apply_credentials -- Auto-wire completed taskboard credentials into .env

When you complete a task on the taskboard dashboard, this command reads
the encrypted data, maps fields to environment variable names, and writes
them to the project .env file. Your AI agents can then use them immediately.

Usage:
    python manage.py apply_credentials              # apply all completed, unretrieved
    python manage.py apply_credentials --dry-run    # preview without writing
    python manage.py apply_credentials --batch content_engine_setup
"""

import os
from pathlib import Path
from django.core.management.base import BaseCommand
from taskboard.models import TaskItem

WORKSPACE = Path("/mnt/sdcard/AA_MY_DRIVE")
ENV_FILE = WORKSPACE / ".env"

# Maps template_name -> {field_name: ENV_VAR_NAME}
CREDENTIAL_MAP = {
    "elevenlabs_api": {
        "api_key": "ELEVENLABS_API_KEY",
        "voice_id_1": "ELEVENLABS_VOICE_ID",
        "voice_id_2": "ELEVENLABS_VOICE_ID_2",
    },
    "smtp_credentials": {
        "provider": "SMTP_PROVIDER",
        "smtp_host": "SMTP_HOST",
        "smtp_port": "SMTP_PORT",
        "smtp_user": "SMTP_USER",
        "smtp_pass": "SMTP_PASS",
        "from_email": "SMTP_FROM_EMAIL",
    },
    "stripe_account": {
        "publishable_key": "STRIPE_PUBLISHABLE_KEY",
        "secret_key": "STRIPE_SECRET_KEY",
        "webhook_secret": "STRIPE_WEBHOOK_SECRET",
    },
    "twitter_api": {
        "api_key": "TWITTER_API_KEY",
        "api_secret": "TWITTER_API_SECRET",
        "access_token": "TWITTER_ACCESS_TOKEN",
        "access_secret": "TWITTER_ACCESS_SECRET",
        "bearer_token": "TWITTER_BEARER_TOKEN",
    },
    "did_api": {
        "api_key": "DID_API_KEY",
    },
    "ai_agent_credential": {
        "api_key": "_API_KEY",  # prefixed by service_name
        "api_secret": "_API_SECRET",
    },
}


class Command(BaseCommand):
    help = "Apply completed taskboard credentials to .env file"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--batch", type=str, default="")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        batch = options["batch"]

        tasks = TaskItem.objects.filter(
            status="completed",
        ).select_related("template")

        if batch:
            tasks = tasks.filter(batch_id=batch)

        # Load existing .env
        env_lines = {}
        if ENV_FILE.exists():
            for line in ENV_FILE.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, val = line.partition("=")
                    env_lines[key.strip()] = val.strip()

        new_vars = {}
        applied_tasks = []

        for task in tasks:
            template_name = task.template.name
            mapping = CREDENTIAL_MAP.get(template_name)
            if not mapping:
                continue

            try:
                data = task.get_data()
            except Exception as e:
                self.stderr.write(f"  [ERROR] Cannot decrypt {task.title}: {e}")
                continue

            if not data:
                continue

            for field_name, env_var in mapping.items():
                value = data.get(field_name, "")
                if not value:
                    continue

                # Special: AI agent credentials get prefixed
                if template_name == "ai_agent_credential" and env_var.startswith("_"):
                    service = data.get("service_name", "UNKNOWN").upper().replace(" ", "_")
                    env_var = f"{service}{env_var}"

                new_vars[env_var] = value

            applied_tasks.append(task)

        if not new_vars:
            self.stdout.write("No new credentials to apply.")
            return

        # Show what will be written
        self.stdout.write(self.style.SUCCESS(f"\n{'[DRY RUN] ' if dry_run else ''}Credentials to apply:"))
        for key, val in sorted(new_vars.items()):
            masked = val[:4] + "..." + val[-4:] if len(val) > 12 else "****"
            status = "UPDATE" if key in env_lines else "NEW"
            self.stdout.write(f"  [{status}] {key}={masked}")

        if dry_run:
            self.stdout.write(self.style.WARNING("\nDry run -- nothing written."))
            return

        # Merge and write
        env_lines.update(new_vars)
        output = "\n".join(f"{k}={v}" for k, v in sorted(env_lines.items()))
        ENV_FILE.write_text(output + "\n")
        os.chmod(str(ENV_FILE), 0o600)

        # Mark tasks as retrieved
        for task in applied_tasks:
            task.mark_retrieved()

        self.stdout.write(self.style.SUCCESS(
            f"\nWrote {len(new_vars)} variables to {ENV_FILE}"
            f"\nMarked {len(applied_tasks)} tasks as retrieved."
        ))
