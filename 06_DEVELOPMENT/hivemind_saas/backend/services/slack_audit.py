"""
Slack Audit Pipeline - structured Block Kit messages to audit channels.

Replaces raw log dumps with formatted, actionable Slack blocks.
All hive events flow through here for full observability.
"""

import httpx
import logging
from datetime import datetime, timezone
from typing import Optional
from enum import Enum

from core.config import settings

logger = logging.getLogger(__name__)


class AuditEvent(str, Enum):
    SESSION_STARTED = "session_started"
    SESSION_COMPLETED = "session_completed"
    SESSION_FAILED = "session_failed"
    INTEGRATION_CONNECTED = "integration_connected"
    INTEGRATION_FAILED = "integration_failed"
    USER_SIGNED_UP = "user_signed_up"
    SUBSCRIPTION_CREATED = "subscription_created"
    SUBSCRIPTION_CANCELLED = "subscription_cancelled"
    BILLING_PAYMENT = "billing_payment"
    BILLING_FAILED = "billing_failed"
    AGENT_ERROR = "agent_error"
    SECURITY_ALERT = "security_alert"


# Map events to Slack channels
CHANNEL_MAP = {
    AuditEvent.SESSION_STARTED: settings.slack_audit_channel,
    AuditEvent.SESSION_COMPLETED: settings.slack_audit_channel,
    AuditEvent.SESSION_FAILED: settings.slack_alerts_channel,
    AuditEvent.INTEGRATION_CONNECTED: settings.slack_audit_channel,
    AuditEvent.INTEGRATION_FAILED: settings.slack_alerts_channel,
    AuditEvent.USER_SIGNED_UP: settings.slack_sales_channel,
    AuditEvent.SUBSCRIPTION_CREATED: settings.slack_sales_channel,
    AuditEvent.SUBSCRIPTION_CANCELLED: settings.slack_sales_channel,
    AuditEvent.BILLING_PAYMENT: settings.slack_sales_channel,
    AuditEvent.BILLING_FAILED: settings.slack_alerts_channel,
    AuditEvent.AGENT_ERROR: settings.slack_alerts_channel,
    AuditEvent.SECURITY_ALERT: settings.slack_alerts_channel,
}

# Map events to emoji indicators
EVENT_EMOJI = {
    AuditEvent.SESSION_STARTED: ":beehive:",
    AuditEvent.SESSION_COMPLETED: ":white_check_mark:",
    AuditEvent.SESSION_FAILED: ":x:",
    AuditEvent.INTEGRATION_CONNECTED: ":electric_plug:",
    AuditEvent.INTEGRATION_FAILED: ":warning:",
    AuditEvent.USER_SIGNED_UP: ":wave:",
    AuditEvent.SUBSCRIPTION_CREATED: ":moneybag:",
    AuditEvent.SUBSCRIPTION_CANCELLED: ":broken_heart:",
    AuditEvent.BILLING_PAYMENT: ":dollar:",
    AuditEvent.BILLING_FAILED: ":rotating_light:",
    AuditEvent.AGENT_ERROR: ":robot_face:",
    AuditEvent.SECURITY_ALERT: ":lock:",
}


async def post_audit(
    event: AuditEvent,
    tenant_name: str,
    tenant_id: str,
    summary: str,
    details: Optional[dict] = None,
    session_id: Optional[str] = None,
) -> bool:
    """
    Post a structured Slack Block Kit message to the appropriate audit channel.
    Returns True on success.
    """
    if not settings.slack_bot_token:
        logger.debug("Slack bot token not configured, skipping audit post")
        return False

    channel = CHANNEL_MAP.get(event, settings.slack_audit_channel)
    emoji = EVENT_EMOJI.get(event, ":information_source:")
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{emoji} {event.value.replace('_', ' ').title()}",
            },
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Tenant:*\n{tenant_name}"},
                {"type": "mrkdwn", "text": f"*Time:*\n{ts}"},
            ],
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": summary},
        },
    ]

    if details:
        detail_lines = [f"- *{k}:* {v}" for k, v in details.items()]
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "\n".join(detail_lines)},
        })

    if session_id:
        blocks.append({
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"Session: `{session_id}` | Tenant: `{tenant_id}`"},
            ],
        })

    blocks.append({"type": "divider"})

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                "https://slack.com/api/chat.postMessage",
                headers={"Authorization": f"Bearer {settings.slack_bot_token}"},
                json={"channel": channel, "blocks": blocks},
            )
            data = resp.json()
            if not data.get("ok"):
                logger.warning(f"Slack audit post failed: {data.get('error')}")
                return False
            return True
    except Exception as e:
        logger.error(f"Slack audit post exception: {e}")
        return False


async def post_daily_summary(
    total_sessions: int,
    total_tenants: int,
    mrr_usd: float,
    new_signups: int,
    top_events: list[str],
) -> bool:
    """Post a daily business summary to the sales channel."""
    if not settings.slack_bot_token:
        return False

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f":bar_chart: Daily Hive Summary - {ts}"},
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Active Tenants:*\n{total_tenants:,}"},
                {"type": "mrkdwn", "text": f"*Sessions Today:*\n{total_sessions:,}"},
                {"type": "mrkdwn", "text": f"*MRR:*\n${mrr_usd:,.2f}"},
                {"type": "mrkdwn", "text": f"*New Signups:*\n{new_signups}"},
            ],
        },
    ]

    if top_events:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Top Events Today:*\n" + "\n".join(f"- {e}" for e in top_events),
            },
        })

    blocks.append({"type": "divider"})

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                "https://slack.com/api/chat.postMessage",
                headers={"Authorization": f"Bearer {settings.slack_bot_token}"},
                json={"channel": settings.slack_sales_channel, "blocks": blocks},
            )
            return resp.json().get("ok", False)
    except Exception as e:
        logger.error(f"Daily summary Slack post failed: {e}")
        return False
