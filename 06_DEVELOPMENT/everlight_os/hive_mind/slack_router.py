"""Slack routing helper for agent-style posting with a single bot token."""
from __future__ import annotations

import json
import logging
import os
import urllib.request
from functools import lru_cache
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None

log = logging.getLogger(__name__)

ROUTING_PATH = Path(__file__).with_name("slack_routing.yaml")
DEFAULT_BOT = "warroom"

AGENT_ALIASES = {
    "Chart Dawson": "Charles Dawson",
    "Forge Steele": "Franklin Steele",
    "Rocket Kim": "Ryan Kim",
    "Cupid Osei": "Calvin Osei",
    "Hammer Knox": "Harrison Knox",
}

AGENT_STYLES = {
    "Marcus Cole": "Command brief. Direct and operational.",
    "Piper Reeves": "Seller-side signal only. Hunt fast, act clean.",
    "Calvin Osei": "Broker pipeline update. Match quality first.",
    "Harrison Knox": "Revenue event. Focus on money and movement.",
    "Quinn Sharp": "Health alert. State the issue and next action.",
    "Franklin Steele": "Deploy update. What changed, what restarted.",
    "Charles Dawson": "Pipeline analytics. Trends first, noise stripped out.",
    "Ryan Kim": "Growth update. Pipeline movement, conversion, next action.",
    "Penny Vance": "Revenue update. Money in, money out, no fluff.",
}


@lru_cache(maxsize=1)
def load_routing_config(path: str | Path | None = None) -> dict[str, Any]:
    """Load Slack routing YAML once per process."""
    routing_path = Path(path) if path else ROUTING_PATH
    if not routing_path.exists():
        log.warning("Slack routing file missing: %s", routing_path)
        return {}
    if yaml is None:
        log.warning("PyYAML not installed; Slack routing helper disabled.")
        return {}
    try:
        return yaml.safe_load(routing_path.read_text()) or {}
    except Exception as exc:
        log.warning("Failed loading Slack routing config: %s", exc)
        return {}


def get_route(route_name: str, config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return a named route from the routing config."""
    cfg = config or load_routing_config()
    return (cfg.get("routing") or {}).get(route_name, {})


def resolve_channel(channel: str, config: dict[str, Any] | None = None) -> str:
    """Resolve a route name or channel alias to a Slack channel ID."""
    if not channel:
        return ""
    cfg = config or load_routing_config()
    channels = cfg.get("channels") or {}
    if channel in channels:
        return str(channels[channel])
    route = get_route(channel, cfg)
    route_channel = route.get("channel")
    if route_channel:
        return str(channels.get(route_channel, route_channel))
    return str(channel)


def _bot_token(bot_name: str | None, config: dict[str, Any]) -> str:
    """Prefer the single war-room bot token, then fall back to route-specific tokens."""
    tokens = config.get("bot_tokens") or {}
    env_candidates = [
        os.environ.get("SLACK_BOT_TOKEN", ""),
        os.environ.get("SLACK_WARROOM_TOKEN", ""),
        os.environ.get("SLACK_TOKEN_WARROOM", ""),
        os.environ.get("SLACK_WARROOM_BOT_TOKEN", ""),
    ]
    for candidate in env_candidates:
        if candidate:
            return candidate

    for token_name in (DEFAULT_BOT, bot_name):
        if token_name and tokens.get(token_name):
            return str(tokens[token_name])
    return ""


def _format_message(agent_name: str, message: str) -> str:
    agent = AGENT_ALIASES.get((agent_name or "").strip(), (agent_name or "Everlight Agent").strip())
    style = AGENT_STYLES.get(agent)
    if style:
        return f"*{agent}*\n{message}\n_{style}_"
    return f"*{agent}*\n{message}"


def send_as_agent(
    agent_name: str | None,
    channel: str,
    message: str,
    route_name: str | None = None,
) -> bool:
    """Send a message through Slack using route config and agent-style formatting."""
    config = load_routing_config()
    route = get_route(route_name or channel, config) if (route_name or channel) else {}
    effective_agent = agent_name or route.get("agent") or "Everlight Agent"
    channel_id = resolve_channel(channel, config)
    token = _bot_token(route.get("bot"), config)

    if not channel_id or not token:
        return False

    payload = json.dumps({
        "channel": channel_id,
        "text": _format_message(effective_agent, message),
    }).encode()

    try:
        req = urllib.request.Request(
            "https://slack.com/api/chat.postMessage",
            data=payload,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
        if not result.get("ok"):
            log.error("Slack route post failed: %s", result.get("error"))
            return False
        return True
    except Exception as exc:
        log.error("Slack route post error: %s", exc)
        return False
