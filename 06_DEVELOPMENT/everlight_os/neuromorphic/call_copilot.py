"""
Call Co-Pilot -- Live call intelligence for Hive agents.

When an agent is on a call (via voice handler or phone system):
1. Transcribes the conversation (live or post-call)
2. Generates real-time coaching suggestions
3. Creates call summary + action items
4. Posts to Slack + logs to Django dashboard
5. Updates CRM with call outcome

Integrates with:
- ElevenLabs (TTS for agent voice)
- Ollama (local reasoning for responses)
- Langfuse (call tracing)
- Slack (notifications)
- Django (call log storage)
- Blinko (knowledge retrieval for context)

All processing happens on Oracle. No external API needed except ElevenLabs for voice.
"""
from __future__ import annotations

import json
import logging
import os
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

SLACK_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "xoxb-8645963765681-10594020158069-eJRt13YP8qedI6DnQwupuFfy")
ELEVEN_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")

# Slack channel mapping for call notifications
CALL_CHANNELS = {
    "broker": "C0AN4GSTMT5",      # #deploy-log (fallback)
    "consulting": "C0AN4GSTMT5",
    "trading": "C0AN4GSTMT5",
    "default": "C0AN4GSTMT5",
}

# Call log storage
CALL_LOG_DIR = Path("/home/opc/xlm-bot/logs") if Path("/home/opc").exists() else Path("/tmp")


def generate_call_summary(
    agent_name: str,
    agent_voice_id: str,
    prospect_name: str,
    call_transcript: str,
    call_duration_sec: int = 0,
    call_type: str = "outbound",
) -> dict:
    """Generate a structured call summary with action items.

    Uses Ollama for local reasoning -- no API cost.
    """
    from langfuse_bridge import call_ollama, trace_agent_action

    prompt = f"""You are {agent_name} from Everlight Ventures. Summarize this {call_type} call with {prospect_name}.

Call transcript:
{call_transcript[:3000]}

Provide:
1. SUMMARY (2-3 sentences)
2. KEY POINTS (bullet points)
3. PROSPECT SENTIMENT (positive/neutral/negative)
4. ACTION ITEMS (numbered list)
5. FOLLOW UP DATE (suggested)
6. DEAL PROBABILITY (0-100%)

Be concise and actionable."""

    t0 = time.time()
    response = call_ollama(prompt, agent_name=agent_name, model="phi3:mini")
    duration = (time.time() - t0) * 1000

    summary = {
        "agent": agent_name,
        "prospect": prospect_name,
        "call_type": call_type,
        "duration_sec": call_duration_sec,
        "summary": response,
        "timestamp": datetime.utcnow().isoformat(),
        "voice_id": agent_voice_id,
    }

    # Trace to Langfuse
    trace_agent_action(
        agent_name=agent_name,
        action="call_summary",
        input_data={"prospect": prospect_name, "duration": call_duration_sec},
        output_data={"summary_length": len(response)},
        duration_ms=duration,
    )

    return summary


def post_call_to_slack(summary: dict, channel_type: str = "default") -> bool:
    """Post call summary to the appropriate Slack channel."""
    channel = CALL_CHANNELS.get(channel_type, CALL_CHANNELS["default"])

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"Call: {summary['agent']} -> {summary['prospect']}"}
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Agent:* {summary['agent']}"},
                {"type": "mrkdwn", "text": f"*Prospect:* {summary['prospect']}"},
                {"type": "mrkdwn", "text": f"*Type:* {summary['call_type']}"},
                {"type": "mrkdwn", "text": f"*Duration:* {summary['duration_sec']}s"},
            ]
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": summary.get("summary", "No summary available")[:2900]}
        },
    ]

    payload = {
        "channel": channel,
        "text": f"Call summary: {summary['agent']} -> {summary['prospect']}",
        "blocks": blocks,
    }

    try:
        req = urllib.request.Request(
            "https://slack.com/api/chat.postMessage",
            data=json.dumps(payload).encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {SLACK_TOKEN}",
            },
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            return result.get("ok", False)
    except Exception as e:
        log.warning(f"Slack post failed: {e}")
        return False


def log_call(summary: dict) -> Path:
    """Save call log to persistent storage."""
    log_path = CALL_LOG_DIR / "call_log.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    with open(log_path, "a") as f:
        f.write(json.dumps(summary, default=str) + "\n")

    return log_path


def get_recent_calls(limit: int = 20) -> list[dict]:
    """Get recent call logs."""
    log_path = CALL_LOG_DIR / "call_log.jsonl"
    if not log_path.exists():
        return []

    calls = []
    with open(log_path) as f:
        for line in f:
            try:
                calls.append(json.loads(line.strip()))
            except Exception:
                continue

    return calls[-limit:]


def process_completed_call(
    agent_name: str,
    agent_voice_id: str,
    prospect_name: str,
    transcript: str,
    duration_sec: int = 0,
    call_type: str = "outbound",
    channel_type: str = "broker",
) -> dict:
    """Full post-call pipeline: summarize -> log -> Slack -> Blinko.

    This is the main entry point. Call this after any agent call completes.
    """
    # 1. Generate summary
    summary = generate_call_summary(
        agent_name=agent_name,
        agent_voice_id=agent_voice_id,
        prospect_name=prospect_name,
        call_transcript=transcript,
        call_duration_sec=duration_sec,
        call_type=call_type,
    )

    # 2. Log to file
    log_call(summary)

    # 3. Post to Slack
    post_call_to_slack(summary, channel_type=channel_type)

    # 4. Log to Blinko
    try:
        blinko_payload = {
            "content": (
                f"# Call Log: {agent_name} -> {prospect_name}\n"
                f"#hive/call #{channel_type}\n\n"
                f"Duration: {duration_sec}s | Type: {call_type}\n\n"
                f"{summary.get('summary', '')[:500]}"
            ),
            "type": 1,
        }
        req = urllib.request.Request(
            "http://localhost:1111/api/v1/note/upsert",
            data=json.dumps(blinko_payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass

    return summary


def get_agent_voice_config(agent_slug: str) -> dict:
    """Get ElevenLabs voice config for an agent."""
    profiles_path = Path("/home/opc/06_DEVELOPMENT/everlight_os/hive_mind/agent_profiles/all_profiles.json")
    if not profiles_path.exists():
        profiles_path = Path("/mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/hive_mind/agent_profiles/all_profiles.json")

    if not profiles_path.exists():
        return {"voice_id": "", "name": agent_slug}

    for agent in json.loads(profiles_path.read_text()):
        if agent.get("slug") == agent_slug:
            return {
                "voice_id": agent.get("voice_id", ""),
                "name": agent.get("name", agent_slug),
                "has_voice": agent.get("has_voice", False),
            }

    return {"voice_id": "", "name": agent_slug}
