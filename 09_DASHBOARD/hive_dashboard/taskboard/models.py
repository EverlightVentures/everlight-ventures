import json
import base64
import os
try:
    from cryptography.fernet import Fernet
except ImportError:
    Fernet = None
from django.db import models
from django.utils import timezone


def _get_fernet():
    """Get or create encryption key for credential storage."""
    if Fernet is None:
        raise ImportError(
            "cryptography package required for taskboard encryption. "
            "Install it: pip install cryptography"
        )
    key = os.environ.get("TASKBOARD_ENCRYPT_KEY")
    if not key:
        key_file = os.path.join(os.path.dirname(__file__), ".encrypt_key")
        if os.path.exists(key_file):
            key = open(key_file).read().strip()
        else:
            key = Fernet.generate_key().decode()
            with open(key_file, "w") as f:
                f.write(key)
            os.chmod(key_file, 0o600)
    return Fernet(key.encode() if isinstance(key, str) else key)


class TaskTemplate(models.Model):
    """
    Defines a reusable form schema for a category of tasks.
    AI or humans create these once; they get reused across task instances.

    Example schema:
    {
      "fields": [
        {"name": "api_key", "label": "API Key", "type": "secret", "required": true},
        {"name": "voice_id", "label": "Voice ID", "type": "text", "required": false},
        {"name": "plan", "label": "Plan Tier", "type": "select", "options": ["free", "pro"], "required": true}
      ]
    }

    Field types: text, secret, email, url, select, textarea, checkbox, file_note
    """
    CATEGORY_CHOICES = [
        ("api_credential", "API / Credential Setup"),
        ("social_media", "Social Media Account"),
        ("email_account", "Email Account"),
        ("domain", "Domain / Hosting"),
        ("payment", "Payment / Billing"),
        ("ai_agent", "AI Agent Config"),
        ("general", "General Task"),
    ]

    name = models.CharField(max_length=200, unique=True)
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default="general")
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, default="fa-solid fa-clipboard-list",
                            help_text="Font Awesome icon class")
    schema = models.JSONField(help_text="Form field definitions (JSON array)")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["category", "name"]

    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"

    def get_fields(self):
        return self.schema.get("fields", []) if isinstance(self.schema, dict) else self.schema


class TaskItem(models.Model):
    """
    A single todo item created by AI for human completion.
    Links to a template for form rendering. Stores submitted data encrypted.
    """
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("blocked", "Blocked"),
        ("skipped", "Skipped"),
    ]
    PRIORITY_CHOICES = [
        (1, "Critical"),
        (2, "High"),
        (3, "Normal"),
        (4, "Low"),
        (5, "Optional"),
    ]

    template = models.ForeignKey(TaskTemplate, on_delete=models.CASCADE, related_name="tasks")
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True, help_text="AI-provided context for the task")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    priority = models.IntegerField(choices=PRIORITY_CHOICES, default=3)
    source_agent = models.CharField(max_length=100, blank=True, help_text="Which AI agent created this")
    target_agent = models.CharField(max_length=100, blank=True, help_text="Which agent should receive the data")
    batch_id = models.CharField(max_length=100, blank=True, help_text="Groups related tasks together")
    data_encrypted = models.TextField(blank=True, help_text="Encrypted submitted form data")
    notes = models.TextField(blank=True, help_text="Human notes during completion")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    retrieved_by_agent = models.BooleanField(default=False)
    retrieved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["priority", "-created_at"]

    def __str__(self):
        return f"[{self.get_status_display()}] {self.title}"

    def set_data(self, data: dict):
        """Encrypt and store form submission data."""
        f = _get_fernet()
        raw = json.dumps(data).encode()
        self.data_encrypted = f.encrypt(raw).decode()

    def get_data(self) -> dict:
        """Decrypt and return stored form data."""
        if not self.data_encrypted:
            return {}
        f = _get_fernet()
        raw = f.decrypt(self.data_encrypted.encode())
        return json.loads(raw.decode())

    def mark_completed(self):
        self.status = "completed"
        self.completed_at = timezone.now()
        self.save()

    def mark_retrieved(self):
        self.retrieved_by_agent = True
        self.retrieved_at = timezone.now()
        self.save()
