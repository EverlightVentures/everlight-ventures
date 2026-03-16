"""Configuration loader for Slack org tooling."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent
DEFAULT_CHANNEL_MAP_PATH = ROOT_DIR / "config" / "channel_map.json"
DEFAULT_CHANNEL_REGISTRY_PATH = ROOT_DIR / "config" / "channel_registry.json"
DEFAULT_THREAD_REGISTRY_PATH = ROOT_DIR / "config" / "task_threads.json"
DEFAULT_FAILURE_LOG_PATH = ROOT_DIR / "config" / "slack_failures.jsonl"


def _to_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class SlackOrgConfig:
    """Runtime config for Slack API + logger workflows."""

    bot_token: str
    signing_secret: str
    channel_map_path: Path
    channel_registry_path: Path
    thread_registry_path: Path
    failure_log_path: Path
    errors_channel_name: str
    max_text_chars: int
    max_retries: int
    base_backoff_seconds: float
    request_timeout_seconds: float
    dry_run: bool

    @classmethod
    def from_env(cls) -> "SlackOrgConfig":
        channel_map_path = Path(
            os.environ.get("SLACK_CHANNEL_MAP_PATH", str(DEFAULT_CHANNEL_MAP_PATH))
        )
        channel_registry_path = Path(
            os.environ.get("SLACK_CHANNEL_REGISTRY_PATH", str(DEFAULT_CHANNEL_REGISTRY_PATH))
        )
        thread_registry_path = Path(
            os.environ.get("SLACK_THREAD_REGISTRY_PATH", str(DEFAULT_THREAD_REGISTRY_PATH))
        )
        failure_log_path = Path(
            os.environ.get("SLACK_FAILURE_LOG_PATH", str(DEFAULT_FAILURE_LOG_PATH))
        )
        return cls(
            bot_token=os.environ.get("SLACK_BOT_TOKEN", "").strip(),
            signing_secret=os.environ.get("SLACK_SIGNING_SECRET", "").strip(),
            channel_map_path=channel_map_path,
            channel_registry_path=channel_registry_path,
            thread_registry_path=thread_registry_path,
            failure_log_path=failure_log_path,
            errors_channel_name=os.environ.get("SLACK_ERRORS_CHANNEL", "agent-errors").strip(),
            max_text_chars=int(os.environ.get("SLACK_MAX_TEXT_CHARS", "3900")),
            max_retries=int(os.environ.get("SLACK_MAX_RETRIES", "5")),
            base_backoff_seconds=float(os.environ.get("SLACK_BASE_BACKOFF_SECONDS", "1.0")),
            request_timeout_seconds=float(os.environ.get("SLACK_REQUEST_TIMEOUT_SECONDS", "20")),
            dry_run=_to_bool(os.environ.get("SLACK_DRY_RUN"), default=False),
        )

    def ensure_parent_dirs(self) -> None:
        self.channel_registry_path.parent.mkdir(parents=True, exist_ok=True)
        self.thread_registry_path.parent.mkdir(parents=True, exist_ok=True)
        self.failure_log_path.parent.mkdir(parents=True, exist_ok=True)

