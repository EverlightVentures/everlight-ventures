"""
Everlight OS — Slack client.
Posts messages, approval requests, and summaries via webhook.
Falls back to console logging if no webhook configured.
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, List

try:
    import requests
except ImportError:
    requests = None

try:
    import yaml
except ImportError:
    yaml = None

logger = logging.getLogger(__name__)

CONFIG_PATH = Path("/mnt/sdcard/AA_MY_DRIVE/everlight_os/configs/everlight.yaml")


def _load_webhook_url() -> str:
    """Load Slack webhook URL from config."""
    if yaml and CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            config = yaml.safe_load(f) or {}
        return config.get("slack", {}).get("webhook_url", "")
    # Fallback: check env
    return os.environ.get("SLACK_WEBHOOK_URL", "")


class SlackClient:
    """Post to Slack via incoming webhook."""

    def __init__(self, webhook_url: str = None):
        self.webhook_url = webhook_url or _load_webhook_url()
        self.enabled = bool(self.webhook_url and requests)
        if not self.enabled:
            logger.info("Slack not configured — messages will print to console")

    def post(self, text: str, title: str = None, blocks: list = None) -> bool:
        """Post a message to Slack. Returns True on success."""
        # Always log to console
        if title:
            print(f"\n[Slack] {title}")
        print(f"[Slack] {text[:200]}{'...' if len(text) > 200 else ''}")

        if not self.enabled:
            return False

        payload = {"text": title or text[:200]}
        if blocks:
            payload["blocks"] = blocks
        elif title or text:
            payload["blocks"] = self._text_to_blocks(text, title)

        try:
            resp = requests.post(self.webhook_url, json=payload, timeout=10)
            ok = resp.status_code == 200
            if not ok:
                logger.error(f"Slack post failed: {resp.status_code} {resp.text}")
            return ok
        except Exception as e:
            logger.error(f"Slack post error: {e}")
            return False

    def _text_to_blocks(self, text: str, title: str = None) -> list:
        """Convert text + optional title to Slack Block Kit blocks."""
        blocks = []
        if title:
            blocks.append({
                "type": "header",
                "text": {"type": "plain_text", "text": title[:150], "emoji": True}
            })
        # Split long text into sections (Slack limit ~3000 chars per block)
        chunks = [text[i:i+2900] for i in range(0, len(text), 2900)]
        for chunk in chunks:
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": chunk}
            })
        return blocks

    def post_approval(self, project_id: str, summary: str, engine: str) -> bool:
        """Post an approval request for a completed project."""
        text = f"*{engine.upper()} — Ready for Review*\n\n"
        text += summary + "\n\n"
        text += f"Project ID: `{project_id}`\n"
        text += f"Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n\n"
        text += "Reply `APPROVE {pid}` or `REJECT {pid}`".format(pid=project_id)
        return self.post(text, title=f"Approval: {engine}")

    def post_progress(self, project_id: str, step_name: str, step_num: int, total: int) -> bool:
        """Post a step progress update."""
        text = f"Step {step_num}/{total}: *{step_name}* completed"
        return self.post(text)

    def post_report(self, title: str, body: str) -> bool:
        """Post a report (trading daily, content summary, etc.)."""
        return self.post(body, title=title)

    def post_error(self, project_id: str, error: str) -> bool:
        """Post an error notification."""
        text = f"Project `{project_id}` failed:\n```{error}```"
        return self.post(text, title="Error")


# Convenience: module-level default client
_default_client = None


def get_client() -> SlackClient:
    """Get or create the default Slack client."""
    global _default_client
    if _default_client is None:
        _default_client = SlackClient()
    return _default_client
