"""
Hive Mind Agent-to-Agent Messaging System (Meta "My Claw" pattern).

Lightweight file-based message bus for inter-agent communication during
Hive Mind sessions. Messages persist for the session duration and are
injected into agent prompts so agents can reference each other mid-session.

Storage: _logs/.hive_messages/<session_id>/<from>_to_<to>_<ts>.json
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path

from .config import WORKSPACE

MESSAGES_DIR = WORKSPACE / "_logs" / ".hive_messages"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ts_slug() -> str:
    return str(int(time.time() * 1000))


def send_message(
    from_agent: str,
    to_agent: str,
    content: str,
    msg_type: str = "response",
    session_id: str = "global",
) -> Path:
    """Send a message from one agent to another.

    Args:
        from_agent: Sender agent key (e.g., "gemini", "codex", "perplexity")
        to_agent: Recipient agent key or "all" for broadcast
        content: Message content
        msg_type: One of "request", "response", "broadcast", "handoff"
        session_id: Hive session ID for grouping

    Returns:
        Path to the written message file.
    """
    session_dir = MESSAGES_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    msg = {
        "from": from_agent,
        "to": to_agent,
        "type": msg_type,
        "content": content,
        "session_id": session_id,
        "timestamp": _now_iso(),
    }

    filename = f"{from_agent}_to_{to_agent}_{_ts_slug()}.json"
    msg_file = session_dir / filename
    msg_file.write_text(json.dumps(msg, indent=2), encoding="utf-8")
    return msg_file


def broadcast(from_agent: str, content: str, session_id: str = "global") -> Path:
    """Broadcast a message to all agents in a session."""
    return send_message(from_agent, "all", content, "broadcast", session_id)


def get_messages(
    agent_id: str,
    session_id: str,
    since: float | None = None,
) -> list[dict]:
    """Get all messages addressed to an agent (or broadcast) in a session.

    Args:
        agent_id: The recipient agent key
        session_id: Hive session ID
        since: Optional Unix timestamp; only return messages after this time

    Returns:
        List of message dicts, sorted chronologically.
    """
    session_dir = MESSAGES_DIR / session_id
    if not session_dir.is_dir():
        return []

    messages = []
    for f in session_dir.iterdir():
        if not f.suffix == ".json":
            continue
        try:
            msg = json.loads(f.read_text(encoding="utf-8"))
            # Include if addressed to this agent or broadcast
            if msg.get("to") in (agent_id, "all"):
                if since and msg.get("timestamp"):
                    msg_ts = datetime.fromisoformat(msg["timestamp"]).timestamp()
                    if msg_ts <= since:
                        continue
                messages.append(msg)
        except (json.JSONDecodeError, OSError):
            continue

    messages.sort(key=lambda m: m.get("timestamp", ""))
    return messages


def get_thread(session_id: str) -> list[dict]:
    """Get the full message thread for a session, sorted chronologically."""
    session_dir = MESSAGES_DIR / session_id
    if not session_dir.is_dir():
        return []

    messages = []
    for f in session_dir.iterdir():
        if not f.suffix == ".json":
            continue
        try:
            messages.append(json.loads(f.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            continue

    messages.sort(key=lambda m: m.get("timestamp", ""))
    return messages


def format_messages_for_prompt(messages: list[dict], max_chars: int = 2000) -> str:
    """Format messages into a text block suitable for injection into agent prompts."""
    if not messages:
        return ""

    lines = ["--- INTER-AGENT MESSAGES ---"]
    total = 0
    for msg in messages:
        line = f"[{msg.get('from', '?')} -> {msg.get('to', '?')}] {msg.get('content', '')[:500]}"
        if total + len(line) > max_chars:
            lines.append(f"... ({len(messages) - len(lines) + 1} more messages)")
            break
        lines.append(line)
        total += len(line)
    lines.append("--- END MESSAGES ---")
    return "\n".join(lines)
