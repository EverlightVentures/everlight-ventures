"""Reusable Slack logger for multi-agent operations."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List
from zoneinfo import ZoneInfo

from .channel_registry import ChannelRegistry
from .config import SlackOrgConfig
from .slack_api import SlackApiClient


PACIFIC_TZ = ZoneInfo("America/Los_Angeles")


def _ts_pt() -> str:
    return datetime.now(PACIFIC_TZ).isoformat(timespec="seconds")


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 14] + "\n...[truncated]"


def _bullets(items: Iterable[str], fallback: str = "none") -> List[str]:
    cleaned = [str(item).strip() for item in items if str(item).strip()]
    if cleaned:
        return cleaned
    return [fallback]


class SlackLogger:
    """Posts standardized task logs and updates with per-task thread routing."""

    def __init__(
        self,
        config: SlackOrgConfig | None = None,
        registry: ChannelRegistry | None = None,
        api: SlackApiClient | None = None,
    ):
        self.config = config or SlackOrgConfig.from_env()
        self.registry = registry or ChannelRegistry(
            channel_map_path=self.config.channel_map_path,
            registry_path=self.config.channel_registry_path,
        )
        self.api = api or SlackApiClient(self.config)
        self.config.ensure_parent_dirs()

    def _load_threads(self) -> Dict[str, Dict[str, str]]:
        path = self.config.thread_registry_path
        if not path.exists():
            return {}
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def _save_threads(self, data: Dict[str, Dict[str, str]]) -> None:
        self.config.thread_registry_path.parent.mkdir(parents=True, exist_ok=True)
        with self.config.thread_registry_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=True)
            f.write("\n")

    def _resolve_channel_id(self, channel: str) -> str:
        # Accept key path, name, #name, or direct id.
        channel_id = self.registry.resolve_channel_ref(channel)
        if channel_id:
            return channel_id
        channel_name = self.registry.get_channel_name(channel)
        raise ValueError(
            f"Channel '{channel_name}' has no known ID. Run create_channels.py to populate registry."
        )

    def _ensure_parent_thread(self, task_obj: Dict[str, object], channel: str, header: str) -> str:
        task_id = str(task_obj.get("task_id", "")).strip()
        if not task_id:
            raise ValueError("task_obj.task_id is required")

        threads = self._load_threads()
        channel_id = self._resolve_channel_id(channel)

        task_threads = threads.setdefault(task_id, {})
        existing = task_threads.get(channel_id, "")
        if existing:
            return existing

        parent_text = _truncate(header, self.config.max_text_chars)
        result = self.api.chat_post_message(channel=channel_id, text=parent_text)
        thread_ts = str(result.get("ts", ""))
        if not thread_ts:
            raise RuntimeError(f"Slack returned no ts for parent thread in channel {channel_id}")

        task_threads[channel_id] = thread_ts
        self._save_threads(threads)
        return thread_ts

    def _post_in_task_thread(
        self,
        channel: str,
        task_obj: Dict[str, object],
        header: str,
        body: str,
    ) -> Dict[str, object]:
        thread_ts = self._ensure_parent_thread(task_obj=task_obj, channel=channel, header=header)
        channel_id = self._resolve_channel_id(channel)
        text = _truncate(body, self.config.max_text_chars)
        return self.api.chat_post_message(channel=channel_id, text=text, thread_ts=thread_ts)

    def post_agent_log(
        self,
        channel: str,
        task_obj: Dict[str, object],
        actions: List[str],
        decisions: List[str],
        blockers: List[str],
        artifacts: List[str],
    ) -> Dict[str, object]:
        delegated_lines = [
            f"- {d.get('to_agent', 'unknown')} ({d.get('reason', 'no reason')})"
            for d in task_obj.get("delegations", []) or []
        ]
        if not delegated_lines:
            delegated_lines = ["- none"]

        text = "\n".join(
            [
                "[AGENT LOG]",
                f"Agent: {task_obj.get('owner_agent', 'unknown')}",
                f"LLM: {task_obj.get('assigned_llm', 'unknown')}",
                f"Channel: {channel}",
                f"Task ID: {task_obj.get('task_id', 'unknown')}",
                f"Task Type: {task_obj.get('task_type', 'unknown')}",
                f"Status: {task_obj.get('status', 'unknown')}",
                f"Priority: {task_obj.get('priority', 'unknown')}",
                "",
                "Objective:",
                str(task_obj.get("objective", "")),
                "",
                "Actions Taken:",
                *[f"- {item}" for item in _bullets(actions)],
                "",
                "Decisions:",
                *[f"- {item}" for item in _bullets(decisions)],
                "",
                "Delegated To:",
                *delegated_lines,
                "",
                "Artifacts:",
                *[f"- {item}" for item in _bullets(artifacts)],
                "",
                "Blockers:",
                *[f"- {item}" for item in _bullets(blockers)],
                "",
                "Next Action:",
                str(task_obj.get("next_action", "none")),
                "",
                "ETA:",
                str(task_obj.get("eta", "unknown")),
                "",
                "Timestamp (PT):",
                _ts_pt(),
            ]
        )
        header = f"[TASK THREAD] {task_obj.get('task_id', 'unknown')} | {task_obj.get('task_type', 'unknown')}"
        return self._post_in_task_thread(channel=channel, task_obj=task_obj, header=header, body=text)

    def post_war_room_update(self, task_obj: Dict[str, object], summary: str) -> Dict[str, object]:
        text = "\n".join(
            [
                f"[WAR ROOM UPDATE] {task_obj.get('owner_agent', 'unknown')}",
                f"Task: {task_obj.get('task_id', 'unknown')} | {task_obj.get('task_type', 'unknown')}",
                f"Status: {task_obj.get('status', 'unknown')}",
                f"Done: {summary}",
                f"Need: {', '.join(task_obj.get('blockers', []) or []) or 'none'}",
                "Delegated: "
                + (
                    ", ".join(d.get("to_agent", "unknown") for d in (task_obj.get("delegations") or []))
                    or "none"
                ),
                f"Risk: {task_obj.get('risk_level', 'unknown')}",
                f"Next: {task_obj.get('next_action', 'none')}",
                f"ETA: {task_obj.get('eta', 'unknown')}",
            ]
        )
        header = f"[TASK THREAD] {task_obj.get('task_id', 'unknown')} | war-room"
        return self._post_in_task_thread(
            channel="war_room",
            task_obj=task_obj,
            header=header,
            body=text,
        )

    def post_thread_update(self, channel: str, thread_ts: str, text: str) -> Dict[str, object]:
        channel_id = self._resolve_channel_id(channel)
        return self.api.chat_post_message(
            channel=channel_id,
            thread_ts=thread_ts,
            text=_truncate(text, self.config.max_text_chars),
        )

    def post_approval_request(self, channel: str, payload: Dict[str, str]) -> Dict[str, object]:
        text = "\n".join(
            [
                f"[APPROVAL REQUEST] {payload.get('agent_slug', 'unknown')}",
                f"Task: {payload.get('task_id', 'unknown')}",
                f"Decision Needed: {payload.get('decision_needed', 'n/a')}",
                "Options:",
                f"1) {payload.get('option_1', 'n/a')}",
                f"2) {payload.get('option_2', 'n/a')}",
                f"Recommendation: {payload.get('recommended_option', 'n/a')}",
                f"Impact: {payload.get('impact_note', 'n/a')}",
                f"Deadline: {payload.get('deadline', 'n/a')}",
            ]
        )
        channel_id = self._resolve_channel_id(channel)
        return self.api.chat_post_message(channel=channel_id, text=_truncate(text, self.config.max_text_chars))

    def post_escalation(self, channel: str, payload: Dict[str, object]) -> Dict[str, object]:
        attempts = _bullets(payload.get("attempts", []) or [], fallback="none")
        needs = str(payload.get("need_from_target_agent", "n/a"))
        text = "\n".join(
            [
                f"[ESCALATION] {payload.get('agent_slug', 'unknown')}",
                f"Task: {payload.get('task_id', 'unknown')}",
                f"Issue: {payload.get('issue', 'n/a')}",
                "What I tried:",
                *[f"- {item}" for item in attempts],
                "Blocked by:",
                f"- {payload.get('blocked_by', 'n/a')}",
                f"Need from {payload.get('target_agent', 'target_agent')}:",
                needs,
            ]
        )
        channel_id = self._resolve_channel_id(channel)
        return self.api.chat_post_message(channel=channel_id, text=_truncate(text, self.config.max_text_chars))
